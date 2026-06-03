"""
HTTP 路由处理器模块

MediaServer 类封装所有 HTTP 路由处理逻辑，包括：
- 页面路由：首页、文件浏览、播放器、管理后台
- 文件服务：原始文件下载、视频转码、缩略图
- API 接口：共享目录管理、EPUB/PDF 内容接口
- 用户认证：登录、登出、Cookie 鉴权

安全措施：
- 路径穿越防护：resolve_path 使用 Path.is_relative_to() 校验
- XSS 防护：文件名通过 html.escape() 转义后传入模板
- 限流防护：登录接口通过 RateLimiter 限制暴力破解
- 上传安全：流式写入磁盘，不在内存中拼接完整文件
"""

import asyncio
import html
import logging
import shutil
import string
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import unquote, quote

from aiohttp import web

from .config import load_config, load_shares, save_config, save_shares, get_password
from .auth import make_token, RateLimiter
from .utils import (
    get_file_type, format_size, CHUNK_SIZE, MAX_UPLOAD_SIZE,
    thumb_cache_key, generate_thumbnail, async_generate_thumbnail,
    async_generate_image_thumbnail,
    read_epub, read_pdf_page, get_local_ip, VIDEO_EXTS, _get_startupinfo,
)
from .pages import (
    build_login_html, build_home_html, build_browse_html,
    build_player_html, build_admin_html,
    build_epub_reader_html, build_pdf_reader_html,
    build_error_html,
)

logger = logging.getLogger('media_server')

# 缩略图缓存目录：与 media_server/ 包同级的 .thumbs/ 目录
THUMB_DIR = Path(__file__).parent.parent / '.thumbs'


async def async_probe_video_codec(path: str) -> dict:
    """
    异步探测视频文件的编码信息。

    使用 asyncio.create_subprocess_exec 运行 ffmpeg，解析 stderr 输出
    获取视频流和音频流的编码名称。不会阻塞事件循环。

    Args:
        path: 视频文件完整路径

    Returns:
        编码信息字典：
        - vcodec: 视频编码名称，如 'h264'、'hevc'（空字符串表示探测失败）
        - acodec: 音频编码名称，如 'aac'、'ac3'

    调用示例：
        info = await async_probe_video_codec('/path/to/video.mp4')
        if 'h264' in info.get('vcodec', '').lower():
            # 视频编码为 H.264，可以直接 copy
    """
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        ffmpeg = get_ffmpeg_exe()
    except Exception:
        logger.debug('imageio-ffmpeg 不可用，跳过编码探测')
        return {}
    try:
        proc = await asyncio.create_subprocess_exec(
            ffmpeg, '-i', path, '-hide_banner',
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            startupinfo=_get_startupinfo(),
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        info = stderr.decode('utf-8', errors='replace')
        vcodec = ''
        acodec = ''
        for line in info.split('\n'):
            if 'Video:' in line:
                vcodec = line.split('Video:')[1].split(',')[0].strip()
            if 'Audio:' in line:
                acodec = line.split('Audio:')[1].split(',')[0].strip()
        return {'vcodec': vcodec, 'acodec': acodec}
    except Exception as e:
        logger.warning('视频编码探测失败: %s -> %s', path, e)
        return {}


class MediaServer:
    """
    媒体服务器核心类。

    封装所有 HTTP 路由处理逻辑，管理共享目录列表、用户鉴权、
    限流器等服务端状态。

    属性：
        shares: 当前共享目录列表（list[dict]，每项含 name 和 path）
        password: 访问密码（4 位数字字符串）
        valid_token: 基于密码生成的合法 token
        limiter: 登录限流器实例

    使用方式：
        server = MediaServer()
        app = create_app(server)  # 注册路由和中间件
    """

    def __init__(self):
        self.shares = load_shares()
        self.password = get_password()
        self.valid_token = make_token(self.password)
        self.limiter = RateLimiter()
        self._start_time = time.time()
        self._active_ips: dict[str, float] = {}  # {ip: last_seen_timestamp}
        logger.info('MediaServer 初始化完成，共享目录 %d 个', len(self.shares))

    def get_share_root(self, idx: int) -> Path | None:
        """
        根据索引获取共享目录的根路径。

        Args:
            idx: 共享目录在 self.shares 中的索引

        Returns:
            目录的 resolved Path，索引越界或目录不存在时返回 None
        """
        if 0 <= idx < len(self.shares):
            p = Path(self.shares[idx]['path'])
            if p.is_dir():
                return p.resolve()
        return None

    def resolve_path(self, share_idx: int, rel: str) -> Path | None:
        """
        解析共享目录内的相对路径，防止路径穿越攻击。

        将 rel（URL 编码的相对路径）解析为共享目录 share_idx 下的
        绝对路径。使用 Path.is_relative_to() 确保结果不会逃逸出
        共享根目录。

        Args:
            share_idx: 共享目录索引
            rel: URL 编码的相对路径，支持 '/' 分隔的多级路径

        Returns:
            解析后的绝对 Path，路径无效或穿越时返回 None

        安全说明：
            '..' 跳转通过 is_relative_to(root) 校验，确保不会
            访问共享目录之外的文件。
        """
        root = self.get_share_root(share_idx)
        if not root:
            return None
        rel = unquote(rel).lstrip('/')
        if not rel:
            return root
        resolved = root
        for part in rel.split('/'):
            if part in ('', '.'):
                continue
            if part == '..':
                parent = resolved.parent
                # 使用 is_relative_to 确保不会逃逸出共享根目录
                if parent.is_relative_to(root):
                    resolved = parent
            else:
                resolved = resolved / part
        return resolved

    def update_activity(self, request: web.Request):
        """记录用户活跃时间，用于统计在线设备数。"""
        ip = request.remote or '0.0.0.0'
        self._active_ips[ip] = time.time()

    def get_online_count(self) -> int:
        """返回最近 5 分钟内活跃的设备数量。"""
        now = time.time()
        cutoff = now - 300  # 5 分钟
        # 清理过期记录
        expired = [ip for ip, ts in self._active_ips.items() if ts < cutoff]
        for ip in expired:
            del self._active_ips[ip]
        return len(self._active_ips)

    def is_authed(self, request: web.Request) -> bool:
        """
        检查请求是否已通过 Cookie 鉴权。

        比较请求中的 'token' cookie 与服务器生成的合法 token。

        Args:
            request: aiohttp 请求对象

        Returns:
            True 表示已认证，False 表示未认证
        """
        return request.cookies.get('token') == self.valid_token

    # ── 页面路由 ──────────────────────────────────────────────────────────────

    async def handle_index(self, request: web.Request) -> web.Response:
        """
        处理首页请求。

        GET /
        - 无 share 参数：显示共享目录列表（首页）
        - 有 share 参数：显示指定共享目录下的文件列表

        Query 参数：
            share: 共享目录索引（可选）
            path: 目录内相对路径（可选，默认根目录）

        Returns:
            HTML 页面响应

        错误码：
            400: share 参数格式错误
            404: 共享目录或子目录不存在
            403: 无权限访问目录
        """
        share_str = request.query.get('share')

        # 无 share 参数，显示共享目录列表首页
        if share_str is None:
            return web.Response(text=build_home_html(self.shares), content_type='text/html', charset='utf-8',
                                headers={'Cache-Control': 'no-store'})

        try:
            share_idx = int(share_str)
        except ValueError:
            raise web.HTTPBadRequest(text='参数错误')

        root = self.get_share_root(share_idx)
        if not root:
            raise web.HTTPNotFound(text='共享目录不存在或已被移除')

        rel_path = request.query.get('path', '')
        dir_path = self.resolve_path(share_idx, rel_path)
        if not dir_path or not dir_path.is_dir():
            raise web.HTTPNotFound(text='目录不存在')

        # 遍历目录内容，统计文件大小和修改时间
        entries = []
        try:
            for item in dir_path.iterdir():
                try:
                    stat = item.stat()
                    entries.append((item.name, stat.st_size, item.is_dir(), stat.st_mtime))
                except (PermissionError, OSError):
                    continue
        except PermissionError:
            raise web.HTTPForbidden(text='无权限')

        share_name = self.shares[share_idx]['name']
        html_content = build_browse_html(share_idx, share_name, rel_path, entries)
        return web.Response(text=html_content, content_type='text/html', charset='utf-8')

    async def handle_play(self, request: web.Request) -> web.Response:
        """
        处理播放/阅读页面请求。

        GET /play/{share}/{path}

        根据文件扩展名分发到不同的阅读器/播放器：
        - .epub → EPUB 阅读器
        - .pdf → PDF 阅读器
        - 视频/音频 → 媒体播放器（视频会探测编码判断是否需要转码）
        - 文本 → 纯文本阅读器

        路径参数：
            share: 共享目录索引
            path: 文件相对路径

        Returns:
            播放器/阅读器 HTML 页面

        错误码：
            400: share 参数格式错误
            404: 文件不存在
        """
        share_str = request.match_info.get('share', '')
        file_path_str = request.match_info.get('path', '')

        try:
            share_idx = int(share_str)
        except ValueError:
            raise web.HTTPBadRequest(text='参数错误')

        file_path = self.resolve_path(share_idx, file_path_str)
        if not file_path or not file_path.is_file():
            raise web.HTTPNotFound(text='文件不存在')

        ext = file_path.suffix.lower()
        parent = str(Path(file_path_str).parent)
        back = f'/?share={share_idx}&path={quote(parent, safe="/")}' if parent and parent != '.' else f'/?share={share_idx}'

        # EPUB 专用阅读器
        if ext == '.epub':
            safe_name = html.escape(file_path.name)
            html_content = build_epub_reader_html(safe_name, share_idx, file_path_str, back_href=back)
            return web.Response(text=html_content, content_type='text/html', charset='utf-8')

        # PDF 专用阅读器
        if ext == '.pdf':
            safe_name = html.escape(file_path.name)
            html_content = build_pdf_reader_html(safe_name, share_idx, file_path_str, back_href=back)
            return web.Response(text=html_content, content_type='text/html', charset='utf-8')

        ftype = get_file_type(file_path.name, False)
        if ftype == 'file':
            ftype = 'text'

        # 视频文件：探测编码，判断手机浏览器是否需要转码
        need_transcode = False
        if ftype == 'video':
            info = await async_probe_video_codec(str(file_path))
            vc = info.get('vcodec', '').lower()
            ac = info.get('acodec', '').lower()
            # 手机浏览器只支持 H.264 视频 + AAC 音频
            if vc and not ('h264' in vc or 'avc' in vc):
                need_transcode = True
            elif ac and 'aac' not in ac:
                need_transcode = True

        file_url = f'/raw/{share_idx}/{quote(file_path_str, safe="/")}'
        safe_name = html.escape(file_path.name)

        # 扫描同目录图片列表（用于画廊模式）
        gallery = None
        if ftype == 'image':
            gallery = []
            root = self.get_share_root(share_idx)
            if root:
                try:
                    for item in sorted(file_path.parent.iterdir(), key=lambda x: x.name.lower()):
                        if item.is_file() and get_file_type(item.name, False) == 'image':
                            rel = str(item.relative_to(root)).replace('\\', '/')
                            gallery.append({
                                'name': item.name,
                                'url': f'/raw/{share_idx}/{quote(rel, safe="/")}',
                            })
                except (PermissionError, OSError):
                    pass

        # 扫描同目录视频列表（用于上下集切换）
        video_list = None
        if ftype == 'video':
            video_list = []
            root = self.get_share_root(share_idx)
            if root:
                try:
                    for item in sorted(file_path.parent.iterdir(), key=lambda x: x.name.lower()):
                        if item.is_file() and get_file_type(item.name, False) == 'video':
                            rel = str(item.relative_to(root)).replace('\\', '/')
                            video_list.append({
                                'name': item.name,
                                'url': f'/raw/{share_idx}/{quote(rel, safe="/")}',
                                'play': f'/play/{share_idx}/{quote(rel, safe="/")}',
                            })
                except (PermissionError, OSError):
                    pass

        html_content = build_player_html(safe_name, file_url, ftype, back_href=back, need_transcode=need_transcode, gallery=gallery, video_list=video_list)
        return web.Response(text=html_content, content_type='text/html', charset='utf-8')

    async def handle_raw(self, request: web.Request) -> web.Response:
        """
        处理原始文件请求，支持 Range 请求（视频拖拽进度条）。

        GET /raw/{share}/{path}
        GET /raw/{share}/{path}?download=1  → 下载模式
        GET /raw/{share}/{path}?transcode=1 → 转码模式

        路径参数：
            share: 共享目录索引
            path: 文件相对路径

        Query 参数：
            download: 非空时设置 Content-Disposition 触发下载
            transcode: 非空时触发视频转码（仅视频文件有效）

        Returns:
            FileResponse（零拷贝文件传输，自动支持 HTTP Range）

        错误码：
            400: share 参数格式错误
            404: 文件不存在
            500: ffmpeg 不可用或转码失败
        """
        share_str = request.match_info.get('share', '')
        file_path_str = request.match_info.get('path', '')

        try:
            share_idx = int(share_str)
        except ValueError:
            raise web.HTTPBadRequest(text='参数错误')

        file_path = self.resolve_path(share_idx, file_path_str)
        if not file_path or not file_path.is_file():
            raise web.HTTPNotFound(text='文件不存在')

        headers = {'Cache-Control': 'public, max-age=3600'}

        # 下载模式：设置 Content-Disposition 触发浏览器下载
        if request.query.get('download'):
            safe_filename = file_path.name.replace('"', '\\"')
            headers['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            return web.FileResponse(path=file_path, headers=headers)

        # 转码模式：仅视频文件支持
        ext = file_path.suffix.lower()
        if ext in VIDEO_EXTS and request.query.get('transcode'):
            return await self._handle_transcode(request, file_path)

        return web.FileResponse(path=file_path, headers=headers)

    async def _handle_transcode(self, request: web.Request, file_path: Path) -> web.Response:
        """
        视频转码处理（内部方法）。

        采用三级策略链，按速度优先逐级尝试：
        1. H.264+AAC → 全部 copy（秒级，仅重封装容器）
        2. H.264+非AAC → 视频 copy + 音频转 AAC（快速）
        3. 非H.264 → 先试音频转码，失败则全量重编码（慢但保底）

        转码结果通过 FileResponse 推送，支持 HTTP Range 拖拽。
        临时文件在请求结束 10 分钟后自动清理。

        Args:
            request: aiohttp 请求对象
            file_path: 视频文件的绝对路径

        Returns:
            FileResponse 转码后的 MP4 文件

        Raises:
            HTTPInternalServerError: ffmpeg 不可用或所有策略均失败
        """
        try:
            from imageio_ffmpeg import get_ffmpeg_exe
            ffmpeg = get_ffmpeg_exe()
        except Exception:
            raise web.HTTPInternalServerError(text='ffmpeg 不可用')

        # 探测源文件编码信息
        info = await async_probe_video_codec(str(file_path))
        vcodec = info.get('vcodec', '').lower()
        acodec = info.get('acodec', '').lower()

        video_ok = ('h264' in vcodec or 'avc' in vcodec)
        audio_ok = 'aac' in acodec
        logger.info('[转码] %s | 视频:%s 音频:%s | 策略:%s',
                    file_path.name, vcodec or '未知', acodec or '未知',
                    'copy' if (video_ok and audio_ok) else 'audio_only' if video_ok else 'encode')

        # ffmpeg 公共参数：容错模式，忽略损坏帧
        base_cmd = [ffmpeg, '-y', '-fflags', '+discardcorrupt+genpts+igndts',
                    '-err_detect', 'ignore_err', '-i', str(file_path)]

        # 策略 1: 全部复制（最快，仅重封装容器格式）
        copy_args = ['-c', 'copy', '-movflags', '+faststart',
                     '-max_muxing_queue_size', '4096', '-avoid_negative_ts', 'make_zero']
        # 策略 2: 视频复制 + 音频转 AAC（快速，大多数情况够用）
        audio_only_args = ['-map', '0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k',
                           '-movflags', '+faststart', '-max_muxing_queue_size', '4096',
                           '-avoid_negative_ts', 'make_zero']
        # 策略 3: 全量重编码（最慢，最后手段）
        encode_args = ['-c:v', 'libx264', '-preset', 'fast', '-crf', '26',
                       '-vf', 'scale=1280:-2:force_original_aspect_ratio=decrease',
                       '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart']

        # 根据编码情况选择策略链
        if video_ok and audio_ok:
            args_list = [copy_args]
        elif video_ok and not audio_ok:
            args_list = [audio_only_args]
        else:
            args_list = [audio_only_args, encode_args]

        tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        tmp_path = tmp.name
        tmp.close()

        async def run_ffmpeg(args) -> int:
            """运行 ffmpeg 转码，返回进程退出码。"""
            cmd = base_cmd + args + [tmp_path]
            logger.info('[转码] 开始: %s', file_path.name)
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
            )
            # 持续读取 stderr 防止管道缓冲区满导致 ffmpeg 死锁
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
            return await proc.wait()

        # 依次尝试策略链
        for i, args in enumerate(args_list):
            code = await run_ffmpeg(args)
            if code == 0:
                break
            if i < len(args_list) - 1:
                logger.warning('[转码] 策略 %d 失败 (exit=%d)，尝试下一个', i + 1, code)
                Path(tmp_path).unlink(missing_ok=True)
                tmp2 = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
                tmp_path = tmp2.name
                tmp2.close()

        # 校验转码结果
        if not Path(tmp_path).exists() or Path(tmp_path).stat().st_size == 0:
            Path(tmp_path).unlink(missing_ok=True)
            logger.error('[转码] 所有策略均失败: %s', file_path.name)
            raise web.HTTPInternalServerError(text='转码失败')

        logger.info('[转码] 完成: %s (%.1f MB)',
                    file_path.name, Path(tmp_path).stat().st_size / 1024 / 1024)

        resp = web.FileResponse(
            path=tmp_path,
            headers={'Cache-Control': 'public, max-age=3600'},
        )

        # 延迟清理临时文件（10 分钟后），避免服务关闭时遗留孤儿文件
        async def cleanup():
            await asyncio.sleep(600)
            try:
                Path(tmp_path).unlink(missing_ok=True)
                logger.debug('[转码] 临时文件已清理: %s', tmp_path)
            except Exception:
                pass
        asyncio.ensure_future(cleanup())

        return resp

    async def handle_thumb(self, request: web.Request) -> web.Response:
        """
        处理视频缩略图请求。

        GET /thumb/{share}/{path}

        缩略图懒生成：首次访问时用 ffmpeg 提取视频第 5 秒帧，
        缩放至 320px 宽后缓存到 .thumbs/ 目录。后续请求直接
        读取缓存文件。

        路径参数：
            share: 共享目录索引
            path: 视频文件相对路径

        Returns:
            FileResponse 缩略图 JPEG 文件（缓存 24 小时）

        错误码：
            400: share 参数格式错误
            404: 文件不存在或缩略图生成失败
        """
        share_str = request.match_info.get('share', '')
        file_path_str = request.match_info.get('path', '')

        try:
            share_idx = int(share_str)
        except ValueError:
            raise web.HTTPBadRequest(text='参数错误')

        file_path = self.resolve_path(share_idx, file_path_str)
        if not file_path or not file_path.is_file():
            raise web.HTTPNotFound(text='文件不存在')

        cache_name = thumb_cache_key(str(file_path))
        cache_path = THUMB_DIR / cache_name

        # 缓存未命中时异步生成缩略图
        if not cache_path.is_file():
            ftype = get_file_type(file_path.name, False)
            if ftype == 'image':
                ok = await async_generate_image_thumbnail(str(file_path), str(cache_path))
            else:
                ok = await async_generate_thumbnail(str(file_path), str(cache_path))
            if not ok:
                raise web.HTTPNotFound(text='缩略图生成失败')

        return web.FileResponse(path=cache_path, headers={'Cache-Control': 'public, max-age=86400'})

    async def handle_epub(self, request: web.Request) -> web.Response:
        """
        处理 EPUB 内容 API 请求。

        GET /api/epub/{share}/{path}

        解析 EPUB 文件，返回章节目录和内容的 JSON 数据。
        首次解析可能较慢（大文件），结果不缓存。

        路径参数：
            share: 共享目录索引
            path: EPUB 文件相对路径

        Returns:
            JSON 响应：{ok: true, title, toc, chapters} 或 {ok: false, msg}
        """
        share_str = request.match_info.get('share', '')
        file_path_str = request.match_info.get('path', '')

        try:
            share_idx = int(share_str)
        except ValueError:
            raise web.HTTPBadRequest(text='参数错误')

        file_path = self.resolve_path(share_idx, file_path_str)
        if not file_path or not file_path.is_file():
            raise web.HTTPNotFound(text='文件不存在')

        try:
            data = read_epub(str(file_path))
        except Exception as e:
            logger.error('EPUB 解析失败: %s -> %s', file_path, e)
            return web.json_response({'ok': False, 'msg': str(e)}, status=500)

        return web.json_response({'ok': True, **data})

    async def handle_pdf_page(self, request: web.Request) -> web.Response:
        """
        处理 PDF 页面渲染请求。

        GET /api/pdf/{share}/{path}?page=N

        将 PDF 指定页渲染为 JPEG 图片返回。页码从 0 开始。

        路径参数：
            share: 共享目录索引
            path: PDF 文件相对路径

        Query 参数：
            page: 页码（从 0 开始，默认 0）

        Returns:
            JPEG 图片响应，附带 X-Total-Pages 响应头（总页数）

        错误码：
            400: 参数格式错误
            404: 文件不存在或页码超出范围
        """
        share_str = request.match_info.get('share', '')
        file_path_str = request.match_info.get('path', '')
        page_str = request.query.get('page', '0')

        try:
            share_idx = int(share_str)
            page_num = int(page_str)
        except ValueError:
            raise web.HTTPBadRequest(text='参数错误')

        file_path = self.resolve_path(share_idx, file_path_str)
        if not file_path or not file_path.is_file():
            raise web.HTTPNotFound(text='文件不存在')

        try:
            img_bytes, total = read_pdf_page(str(file_path), page_num)
        except Exception as e:
            logger.error('PDF 渲染失败: %s -> %s', file_path, e)
            raise web.HTTPNotFound(text='PDF 读取失败')

        if not img_bytes:
            raise web.HTTPNotFound(text='页码超出范围')

        return web.Response(
            body=img_bytes, content_type='image/jpeg',
            headers={'Cache-Control': 'public, max-age=3600', 'X-Total-Pages': str(total)},
        )

    async def handle_upload(self, request: web.Request) -> web.Response:
        """
        处理文件上传请求（流式写入，不占内存）。

        POST /upload (multipart/form-data)

        表单字段：
            file: 上传的文件（multipart）
            path: 目标目录的相对路径（可选，默认上传到共享根目录）
            share: 共享目录索引（可选，默认 0）

        安全说明：
            - 文件逐 chunk 写入磁盘，不在内存中拼接完整文件
            - 同名文件自动添加 _1, _2 后缀避免覆盖
            - 最大上传大小由 MAX_UPLOAD_SIZE（10GB）限制

        Returns:
            纯文本响应：'上传成功: 文件名 (大小)' 或错误信息

        错误码：
            400: 没有文件、共享目录不存在、目标目录不存在
        """
        reader = await request.multipart()
        filename = 'upload_file'
        target_path = ''
        share_idx = 0
        file_size = 0
        dest = None

        while True:
            field = await reader.next()
            if field is None:
                break
            if field.name == 'file':
                filename = field.filename or filename
                # 流式写入：逐 chunk 写入磁盘，不拼接到内存
                root_temp = self.get_share_root(share_idx)
                if root_temp:
                    dest_dir_temp = self.resolve_path(share_idx, target_path) if target_path else root_temp
                    if dest_dir_temp and dest_dir_temp.is_dir():
                        dest = dest_dir_temp / filename
                        counter = 1
                        stem, suffix = dest.stem, dest.suffix
                        while dest.exists():
                            dest = dest_dir_temp / f'{stem}_{counter}{suffix}'
                            counter += 1
                        with open(dest, 'wb') as f:
                            while True:
                                chunk = await field.read_chunk(CHUNK_SIZE)
                                if not chunk:
                                    break
                                f.write(chunk)
                                file_size += len(chunk)
            elif field.name == 'path':
                target_path = (await field.read()).decode('utf-8')
            elif field.name == 'share':
                try:
                    share_idx = int((await field.read()).decode('utf-8'))
                except ValueError:
                    pass

        if file_size == 0 or dest is None:
            return web.Response(text='没有文件', status=400)

        # 如果 share/path 字段在 file 之后才读取到，需要重新定位目标目录
        # （multipart 字段顺序不确定，上面的逻辑先假设 share=0, path=''）
        # 实际上 file 字段通常在最后，所以这里做一次校验
        if not dest.parent.is_dir():
            return web.Response(text='目标目录不存在', status=400)

        logger.info('文件上传成功: %s (%s)', dest.name, format_size(file_size))
        return web.Response(text=f'上传成功: {dest.name} ({format_size(file_size)})', content_type='text/plain')

    # ── 管理 API ─────────────────────────────────────────────────────────────

    async def handle_admin_page(self, request: web.Request) -> web.Response:
        """
        处理管理后台页面请求。

        GET /admin

        显示共享目录管理界面，包括：添加/删除共享目录、
        服务器访问地址和密码、文件夹选择器。

        Returns:
            管理后台 HTML 页面
        """
        html_content = build_admin_html(self.shares, get_local_ip(), request.url.port or 8080)
        return web.Response(text=html_content, content_type='text/html', charset='utf-8',
                            headers={'Cache-Control': 'no-store'})

    async def handle_api_list(self, request: web.Request) -> web.Response:
        """
        获取共享目录列表 API。

        GET /api/shares

        Returns:
            JSON 数组，每项包含 name 和 path
        """
        return web.json_response(self.shares)

    async def handle_api_add(self, request: web.Request) -> web.Response:
        """
        添加共享目录 API。

        POST /api/shares
        Content-Type: application/json

        请求体：{"path": "D:\\绝对路径\\文件夹"}

        校验规则：
        - 路径不能为空
        - 必须是绝对路径
        - 目录必须存在
        - 不能重复添加

        Returns:
            JSON: {ok: true} 或 {ok: false, msg: "错误信息"}
        """
        data = await request.json()
        path_str = data.get('path', '').strip()
        if not path_str:
            return web.json_response({'ok': False, 'msg': '路径不能为空'})

        target = Path(path_str)
        if not target.is_absolute():
            return web.json_response({'ok': False, 'msg': '请输入绝对路径'})
        if not target.is_dir():
            return web.json_response({'ok': False, 'msg': f'目录不存在: {path_str}'})

        # 检查是否重复添加（基于 resolved 路径比较）
        resolved = str(target.resolve())
        for s in self.shares:
            if str(Path(s['path']).resolve()) == resolved:
                return web.json_response({'ok': False, 'msg': '此目录已在共享列表中'})

        name = target.name or resolved
        self.shares.append({'name': name, 'path': resolved})
        save_shares(self.shares)
        logger.info('添加共享目录: %s -> %s', name, resolved)
        return web.json_response({'ok': True})

    async def handle_api_remove(self, request: web.Request) -> web.Response:
        """
        删除共享目录 API。

        DELETE /api/shares/{idx}

        路径参数：
            idx: 共享目录在列表中的索引

        Returns:
            JSON: {ok: true, removed: "目录名"} 或 {ok: false, msg: "错误信息"}
        """
        idx_str = request.match_info.get('idx', '')
        try:
            idx = int(idx_str)
        except ValueError:
            return web.json_response({'ok': False, 'msg': '参数错误'}, status=400)

        if 0 <= idx < len(self.shares):
            removed = self.shares.pop(idx)
            save_shares(self.shares)
            logger.info('删除共享目录: %s', removed['name'])
            return web.json_response({'ok': True, 'removed': removed['name']})
        return web.json_response({'ok': False, 'msg': '索引越界'}, status=400)

    async def handle_api_browse(self, request: web.Request) -> web.Response:
        """
        浏览服务器目录 API（文件夹选择器用）。

        GET /api/browse?path=...

        无 path 参数时返回根目录列表（Windows 返回盘符，Linux 返回 /）。
        有 path 参数时返回该目录下的子目录列表。

        Query 参数：
            path: 要浏览的目录绝对路径（可选）

        Returns:
            JSON: {ok: true, items: [{name, path, drive}]}

        安全说明：
            - 隐藏以 $ 或 . 开头的系统目录
            - 跳过无权限访问的目录（不报错）
        """
        browse_path = request.query.get('path', '').strip()
        items = []

        if not browse_path:
            # 根目录：Windows 枚举盘符，Linux 返回 /
            if sys.platform == 'win32':
                # ctypes 只导入一次，不在循环内重复导入
                try:
                    import ctypes
                    for letter in string.ascii_uppercase:
                        drive = f'{letter}:\\'
                        p = Path(drive)
                        if p.exists():
                            try:
                                vol = ''
                                try:
                                    buf = ctypes.create_unicode_buffer(256)
                                    ctypes.windll.kernel32.GetVolumeInformationW(
                                        drive, buf, 256, None, None, None, None, 0)
                                    vol = buf.value
                                except Exception:
                                    pass
                                name = f'{letter}:'
                                if vol:
                                    name = f'{letter}: {vol}'
                                items.append({'name': name, 'path': drive, 'drive': True})
                            except Exception:
                                pass
                except ImportError:
                    pass
            else:
                items.append({'name': '/', 'path': '/', 'drive': True})
            return web.json_response({'ok': True, 'items': items})

        target = Path(browse_path)
        if not target.is_dir():
            return web.json_response({'ok': False, 'msg': '目录不存在'})

        try:
            for child in sorted(target.iterdir(), key=lambda x: x.name.lower()):
                if child.is_dir():
                    try:
                        name = child.name
                        # 隐藏系统目录和隐藏目录
                        if name.startswith('$') or name.startswith('.'):
                            continue
                        items.append({'name': name, 'path': str(child.resolve()), 'drive': False})
                    except (PermissionError, OSError):
                        continue
        except PermissionError:
            return web.json_response({'ok': False, 'msg': '无权限访问此目录'})

        return web.json_response({'ok': True, 'items': items})

    async def handle_api_stats(self, request: web.Request) -> web.Response:
        """
        服务器状态统计 API。

        GET /api/stats

        Returns:
            JSON: {ok: true, uptime: "2小时15分", shares: 4, thumb_count: 120, thumb_size: "45.2 MB"}
        """
        from . import __version__
        # 运行时长
        elapsed = int(time.time() - self._start_time)
        h, m = divmod(elapsed // 60, 60)
        uptime = f'{h}小时{m}分' if h else f'{m}分钟'

        # 缩略图缓存
        thumb_count = 0
        thumb_size = 0
        if THUMB_DIR.is_dir():
            for f in THUMB_DIR.iterdir():
                if f.is_file():
                    thumb_count += 1
                    thumb_size += f.stat().st_size

        # 共享目录磁盘用量
        disk_info = []
        for s in self.shares:
            try:
                p = Path(s['path'])
                usage = shutil.disk_usage(str(p))
                disk_info.append({
                    'name': s['name'],
                    'total': format_size(usage.total),
                    'used': format_size(usage.used),
                    'free': format_size(usage.free),
                    'pct': round(usage.used / usage.total * 100, 1),
                })
            except Exception:
                disk_info.append({'name': s['name'], 'total': '?', 'used': '?', 'free': '?', 'pct': 0})

        return web.json_response({
            'ok': True,
            'version': __version__,
            'uptime': uptime,
            'share_count': len(self.shares),
            'thumb_count': thumb_count,
            'thumb_size': format_size(thumb_size),
            'online_count': self.get_online_count(),
            'disks': disk_info,
        })

    async def handle_api_change_password(self, request: web.Request) -> web.Response:
        """
        修改密码 API。

        POST /api/password
        Body: {"old": "旧密码", "new": "新密码"}

        Returns:
            JSON: {ok: true} 或 {ok: false, msg: "错误信息"}
        """
        try:
            data = await request.json()
        except Exception:
            return web.json_response({'ok': False, 'msg': '请求格式错误'}, status=400)

        old_pw = data.get('old', '')
        new_pw = data.get('new', '')

        if old_pw != self.password:
            return web.json_response({'ok': False, 'msg': '旧密码错误'}, status=403)

        if not new_pw or len(new_pw) < 1:
            return web.json_response({'ok': False, 'msg': '新密码不能为空'}, status=400)

        self.password = new_pw
        self.valid_token = make_token(new_pw)
        cfg = load_config()
        cfg['password'] = new_pw
        save_config(cfg)
        logger.info('密码已修改')
        return web.json_response({'ok': True})

    async def handle_api_clear_thumbs(self, request: web.Request) -> web.Response:
        """
        清理缩略图缓存 API。

        POST /api/clear-thumbs

        Returns:
            JSON: {ok: true, count: 120}
        """
        count = 0
        if THUMB_DIR.is_dir():
            for f in THUMB_DIR.iterdir():
                if f.is_file():
                    f.unlink()
                    count += 1
        logger.info('已清理 %d 个缩略图缓存', count)
        return web.json_response({'ok': True, 'count': count})

    async def handle_api_recent(self, request: web.Request) -> web.Response:
        """
        最近修改的文件 API。

        GET /api/recent?limit=20

        扫描所有共享目录，返回最近修改的文件列表（按时间倒序）。

        Returns:
            JSON: {ok: true, files: [{name, size, mtime, share_idx, path, type}]}
        """
        try:
            limit = int(request.query.get('limit', '20'))
        except ValueError:
            limit = 20
        limit = min(limit, 100)

        recent = []
        for idx, share in enumerate(self.shares):
            root = Path(share['path'])
            if not root.is_dir():
                continue
            try:
                for item in root.rglob('*'):
                    if item.is_file():
                        try:
                            stat = item.stat()
                            rel = str(item.relative_to(root)).replace('\\', '/')
                            recent.append({
                                'name': item.name,
                                'size': stat.st_size,
                                'mtime': stat.st_mtime,
                                'share_idx': idx,
                                'path': rel,
                                'type': get_file_type(item.name, False),
                            })
                        except (PermissionError, OSError):
                            continue
            except PermissionError:
                continue

        recent.sort(key=lambda x: x['mtime'], reverse=True)
        return web.json_response({'ok': True, 'files': recent[:limit]})

    async def handle_api_delete_file(self, request: web.Request) -> web.Response:
        """
        删除文件。

        DELETE /api/file?share=0&path=相对路径

        Returns:
            JSON: {"ok": true} 或 {"ok": false, "msg": "错误信息"}
        """
        share_str = request.query.get('share', '')
        file_path_str = request.query.get('path', '')

        try:
            share_idx = int(share_str)
        except ValueError:
            return web.json_response({'ok': False, 'msg': '参数错误'}, status=400)

        file_path = self.resolve_path(share_idx, file_path_str)
        if not file_path or not file_path.is_file():
            return web.json_response({'ok': False, 'msg': '文件不存在'}, status=404)

        try:
            file_path.unlink()
            logger.info('已删除文件: %s', file_path)
            return web.json_response({'ok': True})
        except PermissionError:
            return web.json_response({'ok': False, 'msg': '无权限删除此文件'}, status=403)
        except OSError as e:
            return web.json_response({'ok': False, 'msg': f'删除失败: {e}'}, status=500)

    # ── 登录认证 ─────────────────────────────────────────────────────────────

    async def handle_login_page(self, request: web.Request) -> web.Response:
        """
        处理登录页面请求。

        GET /login

        如果当前 IP 被限流，页面上会显示剩余等待时间。

        Returns:
            登录页面 HTML
        """
        ip = request.remote or '0.0.0.0'
        err = self.limiter.check(ip)
        return web.Response(text=build_login_html(err or ''), content_type='text/html', charset='utf-8')

    async def handle_login(self, request: web.Request) -> web.Response:
        """
        处理登录提交请求。

        POST /login
        Content-Type: application/x-www-form-urlencoded

        表单字段：
            password: 用户输入的密码

        流程：
        1. 检查 IP 是否被限流
        2. 验证密码
        3. 成功：设置 token cookie，重定向到首页
        4. 失败：记录失败次数，返回登录页显示错误

        Returns:
            成功: 302 重定向到首页（附带 Set-Cookie）
            失败: 登录页面 HTML（附带错误信息）
        """
        ip = request.remote or '0.0.0.0'

        # 检查限流
        err = self.limiter.check(ip)
        if err:
            return web.Response(text=build_login_html(err), content_type='text/html', charset='utf-8')

        data = await request.post()
        pw = data.get('password', '')
        remember = data.get('remember') == '1'
        if pw == self.password:
            self.limiter.record_success(ip)
            logger.info('登录成功: %s (记住=%s)', ip, remember)
            resp = web.HTTPFound('/')
            if remember:
                resp.set_cookie('token', self.valid_token, max_age=86400 * 30, httponly=True)
            else:
                resp.set_cookie('token', self.valid_token, httponly=True)
            return resp

        self.limiter.record_fail(ip)
        logger.info('登录失败: %s', ip)
        return web.Response(text=build_login_html('密码错误'), content_type='text/html', charset='utf-8')

    async def handle_logout(self, request: web.Request) -> web.Response:
        """
        处理登出请求。

        GET /logout

        清除 token cookie 并重定向到登录页面。

        Returns:
            302 重定向到 /login（附带删除 cookie）
        """
        resp = web.HTTPFound('/login')
        resp.del_cookie('token')
        return resp

"""
工具函数模块

提供文件类型检测、格式化、缩略图生成、文档解析等通用工具。

功能分组：
1. 文件类型常量与检测（VIDEO_EXTS, AUDIO_EXTS, get_file_type 等）
2. 通用格式化（format_size, get_mime）
3. 网络工具（get_local_ip）
4. 多媒体处理（generate_thumbnail, read_epub, read_pdf_page）
"""

import asyncio
import hashlib
import logging
import mimetypes
import socket
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger('media_server')

# ─── 文件类型常量 ─────────────────────────────────────────────────────────────
# 所有扩展名均为小写，用于文件类型检测和图标映射

# 视频格式：浏览器原生支持 mp4/webm，其他需要转码
VIDEO_EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.rmvb', '.3gp',
              '.mpg', '.mpeg', '.mts', '.m2ts', '.ogv', '.vob'}

# 音频格式：浏览器原生支持 mp3/aac/ogg/wav，其他需要转码
AUDIO_EXTS = {'.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', '.wma', '.ape', '.opus'}

# 文本格式：可直接在浏览器中展示的纯文本文件
TEXT_EXTS = {'.txt', '.md', '.json', '.xml', '.csv', '.log', '.py', '.js', '.html', '.css', '.srt', '.ass', '.sub',
             '.yaml', '.yml', '.toml', '.ini', '.sh', '.bat', '.sql', '.go', '.java', '.c', '.cpp', '.h',
             '.rs', '.rb', '.php', '.ts', '.tsx', '.jsx', '.vue', '.lua', '.r', '.swift', '.kt'}

# 图片格式：浏览器可直接渲染
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.heic', '.heif', '.avif'}

# 电子书格式：需要专用阅读器（EPUB 需解析，PDF 需逐页渲染）
EBOOK_EXTS = {'.epub', '.pdf'}

# 上传分块大小：1MB，用于流式读取上传文件
CHUNK_SIZE = 1024 * 1024

# 最大上传大小：10GB
MAX_UPLOAD_SIZE = 10 * 1024 * 1024 * 1024

# ─── MIME 类型映射 ────────────────────────────────────────────────────────────
# mimetypes 标准库无法正确识别的格式，手动指定 MIME 类型
MIME_MAP = {
    '.mkv': 'video/x-matroska',
    '.rmvb': 'application/vnd.rn-realmedia-vbr',
    '.flac': 'audio/flac',
    '.ape': 'audio/ape',
    '.ass': 'text/plain',
    '.srt': 'text/plain',
    '.3gp': 'video/3gpp',
    '.mpg': 'video/mpeg',
    '.mpeg': 'video/mpeg',
    '.mts': 'video/mp2t',
    '.m2ts': 'video/mp2t',
    '.ogv': 'video/ogg',
    '.vob': 'video/mpeg',
    '.opus': 'audio/ogg',
    '.heic': 'image/heic',
    '.heif': 'image/heif',
    '.avif': 'image/avif',
}


def get_mime(path: str) -> str:
    """
    获取文件的 MIME 类型。

    优先查 MIME_MAP 手动映射，再用 mimetypes 标准库猜测，
    最终兜底 application/octet-stream。

    Args:
        path: 文件路径

    Returns:
        MIME 类型字符串，如 'video/mp4'、'audio/flac'
    """
    ext = Path(path).suffix.lower()
    if ext in MIME_MAP:
        return MIME_MAP[ext]
    mime, _ = mimetypes.guess_type(path)
    return mime or 'application/octet-stream'


def get_file_icon(name: str, is_dir: bool) -> str:
    """
    根据文件名返回 Material Symbols 图标名称。

    用于前端文件列表展示对应的文件类型图标。

    Args:
        name: 文件名（含扩展名）
        is_dir: 是否为目录

    Returns:
        Material Symbols 图标名称，如 'movie'、'music_note'、'folder'
    """
    if is_dir:
        return 'folder'
    ext = Path(name).suffix.lower()
    if ext in VIDEO_EXTS:
        return 'movie'
    if ext in AUDIO_EXTS:
        return 'music_note'
    if ext in IMAGE_EXTS:
        return 'image'
    if ext in EBOOK_EXTS:
        return 'menu_book'
    if ext in TEXT_EXTS:
        return 'description'
    return 'insert_drive_file'


def get_file_type(name: str, is_dir: bool) -> str:
    """
    根据文件名返回文件类型字符串。

    用于播放器路由判断：不同类型走不同的处理逻辑。
    注意：EPUB/PDF 在 handle_play 中有单独的分支处理，
    此处统一归类为 'text' 仅作为兜底。

    Args:
        name: 文件名（含扩展名）
        is_dir: 是否为目录

    Returns:
        类型字符串：'folder' | 'video' | 'audio' | 'image' | 'text' | 'file'
    """
    if is_dir:
        return 'folder'
    ext = Path(name).suffix.lower()
    if ext in VIDEO_EXTS:
        return 'video'
    if ext in AUDIO_EXTS:
        return 'audio'
    if ext in IMAGE_EXTS:
        return 'image'
    if ext in TEXT_EXTS or ext in EBOOK_EXTS:
        return 'text'
    return 'file'


def format_size(size: int) -> str:
    """
    将字节数格式化为人类可读的文件大小字符串。

    自动选择合适的单位（B/KB/MB/GB/TB/PB），保留一位小数。

    Args:
        size: 文件大小（字节）

    Returns:
        格式化后的字符串，如 '1.5 GB'、'320.0 KB'
    """
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if size < 1024:
            return f'{size:.1f} {unit}' if unit != 'B' else f'{size} {unit}'
        size /= 1024
    return f'{size:.1f} PB'


def get_local_ip() -> str:
    """
    获取本机局域网 IP 地址。

    通过创建 UDP socket 连接公网 DNS（8.8.8.8:80）来探测
    本机出口 IP，不实际发送数据。失败时回退到 127.0.0.1。

    Returns:
        局域网 IP 地址字符串，如 '192.168.1.100'
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def thumb_cache_key(video_path: str) -> str:
    """
    生成视频缩略图的缓存文件名。

    使用视频文件路径的 MD5 哈希作为文件名，避免路径中的
    特殊字符和中文导致文件系统问题。

    Args:
        video_path: 视频文件的完整路径

    Returns:
        缓存文件名，如 'a1b2c3d4e5f6...jpg'
    """
    return hashlib.md5(video_path.encode()).hexdigest() + '.jpg'


def _get_startupinfo():
    """
    获取 Windows 平台的 subprocess STARTUPINFO。

    用于隐藏 ffmpeg 子进程的控制台窗口，避免弹出黑框。
    非 Windows 平台返回 None。

    Returns:
        subprocess.STARTUPINFO 或 None
    """
    if sys.platform == 'win32':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None


def generate_thumbnail(video_path: str, output_path: str, time_sec: int = 5) -> bool:
    """
    使用 ffmpeg 生成视频缩略图。

    提取视频第 time_sec 秒的帧，缩放至 320px 宽，保存为 JPEG。
    首次调用时会自动创建 .thumbs/ 缓存目录。

    Args:
        video_path: 视频文件完整路径
        output_path: 缩略图输出路径
        time_sec: 提取帧的时间点（秒），默认第 5 秒

    Returns:
        True: 缩略图生成成功
        False: ffmpeg 不可用或生成失败

    注意：此函数使用同步 subprocess.run，不应在 async 上下文中直接调用。
    """
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        ffmpeg = get_ffmpeg_exe()
    except Exception:
        logger.debug('imageio-ffmpeg 不可用，跳过缩略图生成')
        return False
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [ffmpeg, '-y', '-ss', str(time_sec), '-i', video_path,
             '-vframes', '1', '-vf', 'scale=320:-1', '-q:v', '4', output_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
            startupinfo=_get_startupinfo(),
        )
        ok = Path(output_path).is_file()
        if ok:
            logger.debug('缩略图已生成: %s', output_path)
        return ok
    except Exception as e:
        logger.warning('缩略图生成失败: %s -> %s', video_path, e)
        return False


async def async_generate_thumbnail(video_path: str, output_path: str, time_sec: int = 5) -> bool:
    """
    generate_thumbnail 的异步版本，不会阻塞事件循环。

    使用 asyncio.create_subprocess_exec 替代 subprocess.run，
    在后台线程池中执行 ffmpeg。

    Args:
        video_path: 视频文件完整路径
        output_path: 缩略图输出路径
        time_sec: 提取帧的时间点（秒），默认第 5 秒

    Returns:
        True/False
    """
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        ffmpeg = get_ffmpeg_exe()
    except Exception:
        return False
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        proc = await asyncio.create_subprocess_exec(
            ffmpeg, '-y', '-ss', str(time_sec), '-i', video_path,
            '-vframes', '1', '-vf', 'scale=320:-1', '-q:v', '4', output_path,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            startupinfo=_get_startupinfo(),
        )
        await asyncio.wait_for(proc.wait(), timeout=15)
        return Path(output_path).is_file()
    except Exception as e:
        logger.warning('异步缩略图生成失败: %s -> %s', video_path, e)
        return False


def generate_image_thumbnail(image_path: str, output_path: str, max_width: int = 320) -> bool:
    """
    使用 Pillow 生成图片缩略图。

    将图片等比缩放到 max_width 宽度，保存为 JPEG。支持 HEIC/HEIF/AVIF
    等现代格式（需要 pillow-heif 插件）。

    Args:
        image_path: 原始图片路径
        output_path: 缩略图输出路径
        max_width: 最大宽度，默认 320px

    Returns:
        True/False
    """
    try:
        from PIL import Image
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with Image.open(image_path) as img:
            # HEIC/HEIF 需要转换为 RGB
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            # 等比缩放
            if img.width > max_width:
                ratio = max_width / img.width
                new_size = (max_width, int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
            img.save(output_path, 'JPEG', quality=75, optimize=True)
        logger.debug('图片缩略图已生成: %s', output_path)
        return True
    except Exception as e:
        logger.warning('图片缩略图生成失败: %s -> %s', image_path, e)
        return False


async def async_generate_image_thumbnail(image_path: str, output_path: str, max_width: int = 320) -> bool:
    """
    generate_image_thumbnail 的异步版本，不阻塞事件循环。

    Args:
        image_path: 原始图片路径
        output_path: 缩略图输出路径
        max_width: 最大宽度，默认 320px

    Returns:
        True/False
    """
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None, generate_image_thumbnail, image_path, output_path, max_width
        )
    except Exception as e:
        logger.warning('异步图片缩略图生成失败: %s -> %s', image_path, e)
        return False


def read_epub(path: str) -> dict:
    """
    解析 EPUB 电子书，提取目录和章节内容。

    使用 ebooklib 读取 EPUB 结构，BeautifulSoup 清理 HTML 标签，
    提取纯文本内容用于前端展示。

    Args:
        path: EPUB 文件完整路径

    Returns:
        字典，包含：
        - title: 书籍标题（str）
        - toc: 目录列表（list[dict]），每项含 title 和 href
        - chapters: 章节列表（list[dict]），每项含 href、title、content

    Raises:
        Exception: 文件格式损坏或依赖库缺失时抛出异常
    """
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(path)

    # 提取目录（Table of Contents）
    toc = []
    for item in book.toc:
        if hasattr(item, 'title'):
            href = item.href if hasattr(item, 'href') else ''
            toc.append({'title': item.title, 'href': href})

    # 提取章节内容，清理 HTML 标签保留纯文本
    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        html = item.get_content().decode('utf-8', errors='replace')
        soup = BeautifulSoup(html, 'html.parser')
        # 移除 script/style/head 等非内容标签
        for tag in soup(['script', 'style', 'head']):
            tag.decompose()
        text = soup.get_text(separator='\n', strip=True)
        if text.strip():
            chapters.append({
                'href': item.get_name(),
                'title': soup.title.string if soup.title else item.get_name(),
                'content': text,
            })

    # 提取书名，优先从元数据获取，兜底用文件名
    title = book.get_metadata('DC', 'title')
    title_str = title[0][0] if title else Path(path).stem
    logger.debug('EPUB 解析完成: %s, %d 章', title_str, len(chapters))
    return {'title': title_str, 'toc': toc, 'chapters': chapters}


def read_pdf_page(path: str, page_num: int = 0) -> tuple[bytes, int]:
    """
    渲染 PDF 指定页为 JPEG 图片。

    使用 PyMuPDF（fitz）将 PDF 页面渲染为 2 倍分辨率的 JPEG 图片，
    用于前端逐页展示。

    Args:
        path: PDF 文件完整路径
        page_num: 页码（从 0 开始）

    Returns:
        (image_bytes, total_pages) 元组：
        - image_bytes: JPEG 图片字节，页码越界时为空 bytes
        - total_pages: PDF 总页数

    Raises:
        Exception: 文件格式损坏或依赖库缺失时抛出异常
    """
    import fitz

    with fitz.open(path) as doc:
        total = len(doc)
        if page_num < 0 or page_num >= total:
            return b'', total
        page = doc[page_num]
        # 2 倍分辨率渲染，平衡清晰度和文件大小
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        img_bytes = pix.tobytes('jpeg')
    return img_bytes, total

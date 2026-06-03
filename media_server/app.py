"""
应用工厂模块

负责创建和配置 aiohttp Web 应用，包括：
- 路由注册（14 个路由：页面、API、文件服务）
- 鉴权中间件（Cookie token 校验）
- CLI 入口（端口、密码、监听地址配置）

路由表：
  GET  /login                          登录页面
  POST /login                          登录处理
  GET  /logout                         退出
  GET  /                               首页/文件浏览
  GET  /play/{share}/{path}            播放器/阅读器
  GET  /raw/{share}/{path}             原始文件（Range、下载、转码）
  GET  /thumb/{share}/{path}           视频缩略图
  GET  /api/epub/{share}/{path}        EPUB 内容 JSON
  GET  /api/pdf/{share}/{path}?page=N  PDF 页面图片
  GET  /admin                          管理后台
  POST /upload                         文件上传
  GET  /api/shares                     共享目录列表
  POST /api/shares                     添加共享目录
  DELETE /api/shares/{idx}             删除共享目录
  GET  /api/browse                     浏览服务器目录
"""

import argparse
import logging

from aiohttp import web

from .config import load_config, save_config, load_shares, get_password
from .utils import get_local_ip, MAX_UPLOAD_SIZE
from .handlers import MediaServer
from .pages import build_error_html

logger = logging.getLogger('media_server')


def create_app(server: MediaServer) -> web.Application:
    """
    创建并配置 aiohttp Web 应用。

    注册所有路由和鉴权中间件。鉴权中间件对 /login 路径放行，
    其他路径需要有效的 token cookie。API 路径返回 JSON 401，
    页面路径重定向到 /login。

    Args:
        server: MediaServer 实例，包含所有路由处理方法

    Returns:
        配置完成的 aiohttp Application 实例
    """
    app = web.Application(client_max_size=MAX_UPLOAD_SIZE)

    # ── Gzip 压缩中间件 ──────────────────────────────────────────────────
    @web.middleware
    async def gzip_middleware(request, handler):
        resp = await handler(request)
        if isinstance(resp, (web.Response, web.FileResponse)):
            # 只压缩 HTML/JSON/JS/CSS，不压缩文件流
            ct = resp.content_type or ''
            if any(t in ct for t in ('text/html', 'application/json', 'text/css', 'javascript')):
                resp.enable_compression()
        return resp

    # ── 登录路由（无需鉴权）─────────────────────────────────────────────
    app.router.add_get('/login', server.handle_login_page)
    app.router.add_post('/login', server.handle_login)
    app.router.add_get('/logout', server.handle_logout)

    # ── 页面路由 ────────────────────────────────────────────────────────
    app.router.add_get('/', server.handle_index)
    app.router.add_get('/play/{share}/{path:.+}', server.handle_play)
    app.router.add_get('/raw/{share}/{path:.+}', server.handle_raw)
    app.router.add_get('/thumb/{share}/{path:.+}', server.handle_thumb)
    app.router.add_get('/api/epub/{share}/{path:.+}', server.handle_epub)
    app.router.add_get('/api/pdf/{share}/{path:.+}', server.handle_pdf_page)
    app.router.add_get('/admin', server.handle_admin_page)

    # ── 上传路由 ────────────────────────────────────────────────────────
    app.router.add_post('/upload', server.handle_upload)

    # ── 管理 API 路由 ──────────────────────────────────────────────────
    app.router.add_get('/api/shares', server.handle_api_list)
    app.router.add_post('/api/shares', server.handle_api_add)
    app.router.add_delete('/api/shares/{idx}', server.handle_api_remove)
    app.router.add_get('/api/browse', server.handle_api_browse)
    app.router.add_delete('/api/file', server.handle_api_delete_file)
    app.router.add_get('/api/stats', server.handle_api_stats)
    app.router.add_post('/api/password', server.handle_api_change_password)
    app.router.add_post('/api/clear-thumbs', server.handle_api_clear_thumbs)

    # ── 鉴权中间件 ─────────────────────────────────────────────────────
    # 对 /login 路径放行，其他路径需要有效的 token cookie
    # API 路径返回 JSON 401，页面路径重定向到 /login
    @web.middleware
    async def auth_middleware(request, handler):
        if request.path in ('/login',):
            return await handler(request)
        if not server.is_authed(request):
            if request.path.startswith('/api/'):
                return web.json_response({'ok': False, 'msg': '未登录'}, status=401)
            raise web.HTTPFound('/login')
        server.update_activity(request)
        return await handler(request)

    # ── 错误处理中间件 ─────────────────────────────────────────────────
    # 将 HTTP 异常从纯文本替换为深色主题 HTML 错误页面
    @web.middleware
    async def error_middleware(request, handler):
        try:
            return await handler(request)
        except web.HTTPException as ex:
            # API 路径和重定向保持原样
            if request.path.startswith('/api/') or ex.status in (301, 302, 303, 307, 308):
                raise
            # 返回样式化的错误页面
            html = build_error_html(ex.status, ex.reason or '未知错误')
            return web.Response(text=html, content_type='text/html', charset='utf-8', status=ex.status)
        except Exception:
            logger.exception('未处理的异常: %s %s', request.method, request.path)
            html = build_error_html(500, '服务器内部错误，请查看日志')
            return web.Response(text=html, content_type='text/html', charset='utf-8', status=500)

    app.middlewares.append(gzip_middleware)
    app.middlewares.append(error_middleware)
    app.middlewares.append(auth_middleware)
    return app


def main():
    """
    CLI 入口函数。

    解析命令行参数，配置密码，打印启动信息，启动 HTTP 服务器。

    命令行参数：
        --port / -p: 端口号（默认 8080）
        --host: 监听地址（默认 0.0.0.0）
        --password: 设置访问密码（默认自动生成）

    启动后在控制台打印：
        - 访问密码
        - 管理后台地址
        - 手机访问地址
        - 已共享的目录列表
    """
    parser = argparse.ArgumentParser(description='局域网媒体服务器')
    parser.add_argument('--port', '-p', type=int, default=8080, help='端口号 (默认8080)')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--password', default='', help='设置访问密码 (默认自动生成)')
    args = parser.parse_args()

    # 如果命令行指定了密码，写入配置文件
    if args.password:
        cfg = load_config()
        cfg['password'] = args.password
        save_config(cfg)

    local_ip = get_local_ip()
    password = get_password()

    logger.info('=' * 52)
    logger.info('  [Media Server] 局域网媒体服务器')
    logger.info('=' * 52)
    logger.info('  访问密码: %s', password)
    logger.info('  管理后台: http://127.0.0.1:%d/admin', args.port)
    logger.info('  手机访问: http://%s:%d', local_ip, args.port)
    logger.info('=' * 52)

    shares = load_shares()
    if shares:
        logger.info('  已共享 %d 个目录:', len(shares))
        for s in shares:
            logger.info('    - %s: %s', s["name"], s["path"])
    else:
        logger.info('  还没有共享目录，请通过管理后台添加')

    logger.info('=' * 52)
    logger.info('  Ctrl+C 停止服务器')
    logger.info('')

    server = MediaServer()
    app = create_app(server)

    # aiohttp 内置的 ConnectionResetError 处理已足够，
    # 无需全局 monkey-patch socket.socket.shutdown
    web.run_app(app, host=args.host, port=args.port, print=lambda _: None)


if __name__ == '__main__':
    main()

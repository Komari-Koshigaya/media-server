# Media Server - 局域网媒体服务器

## 项目简介
Python 异步 Web 服务器，通过局域网在 PC 和手机之间：
- 流式播放视频/音频（支持进度条拖拽、HTTP Range、播放进度记忆、倍速播放）
- 图片画廊浏览（左右翻页、滑动手势、网格/列表视图切换）
- 在线阅读小说/文本文件（TXT 章节检测、EPUB、PDF）
- 手机向 PC 上传文件（拖拽上传、进度条、最大 10GB）
- 文件浏览支持排序（名称/大小/时间）、类型筛选、搜索
- Web 管理后台（共享目录管理、修改密码、磁盘用量、缓存清理）

## 环境路径
- 项目根目录：`media_server/`（与 CLAUDE.md 同级）
- 配置文件：`shares.json`（项目根目录，自动生成）
- 缩略图缓存：`.thumbs/`（项目根目录）
- 日志文件：`media_server.log`（项目根目录）
- 测试目录：`tests/`

## 启动命令
```bash
python -m media_server                    # 默认端口 8080，密码自动生成
python -m media_server --port 18080       # 自定义端口
python -m media_server --password 1234    # 自定义密码
start.bat                                 # Windows 快捷启动（自动检测并杀掉占用端口的旧进程）
python -m pytest tests/ -v                # 运行全部测试（84 个）
python -m pytest tests/ -q                # 静默模式
```

## 技术栈
- **aiohttp** - 异步 HTTP 服务器
- **HTTP Range / 206** - 视频拖拽进度条、断点续传
- **FileResponse (sendfile)** - 零拷贝文件传输
- **Cookie + SHA256** - 鉴权，httponly cookie，30 天有效期
- **RateLimiter** - 每 IP 登录限制（5 次失败锁定 5 分钟）
- **imageio-ffmpeg** - 内置 ffmpeg 二进制，视频转码和缩略图
- **ebooklib** - EPUB 解析
- **PyMuPDF** (fitz) - PDF 渲染为 JPEG
- **beautifulsoup4** + **lxml** - EPUB HTML 清理

## 架构
```
media_server/
  __init__.py    - 日志系统（控制台 INFO + 文件 DEBUG）
  __main__.py    - python -m media_server 入口
  config.py      - shares.json 读写、密码管理
  utils.py       - 文件类型检测、MIME 映射、缩略图、EPUB/PDF 解析
  auth.py        - make_token(SHA256)、RateLimiter
  pages.py       - CSS 主题 + HTML 模板 + JS（上传、画廊、排序、文件夹选择器）
  handlers.py    - MediaServer 类，18 个路由处理器
  app.py         - create_app() 工厂、鉴权中间件、错误中间件、CLI
  static/        - 静态资源（favicon.svg、manifest.json、sw.js）
tests/
  conftest.py    - 测试夹具（tmp_config、mock_config）
  test_config.py - 配置模块测试（8 个）
  test_auth.py   - 鉴权模块测试（11 个）
  test_utils.py  - 工具模块测试（22 个）
  test_handlers.py - 路由处理器测试（24 个）
  test_pages.py  - 页面模板测试（11 个）
```

### 路由表（18 条）
| 路径 | 方法 | 说明 |
|------|------|------|
| `/login` | GET/POST | 登录页/登录处理 |
| `/logout` | GET | 退出 |
| `/` | GET | 首页或目录浏览 |
| `/play/{share}/{path}` | GET | 播放器/阅读器 |
| `/raw/{share}/{path}` | GET | 原始文件（Range/下载/转码） |
| `/thumb/{share}/{path}` | GET | 缩略图 |
| `/admin` | GET | 管理后台 |
| `/upload` | POST | 文件上传（支持拖拽） |
| `/api/shares` | GET/POST | 共享目录列表/添加 |
| `/api/shares/{idx}` | DELETE | 删除共享目录 |
| `/api/browse` | GET | 浏览服务器目录 |
| `/api/epub/{share}/{path}` | GET | EPUB 章节 JSON |
| `/api/pdf/{share}/{path}?page=N` | GET | PDF 页面图片 |
| `/api/file` | DELETE | 删除文件 |
| `/api/stats` | GET | 服务器统计 |
| `/api/password` | POST | 修改密码 |
| `/api/clear-thumbs` | POST | 清理缩略图缓存 |

## 支持的文件格式
- 视频（17）：mp4 mkv avi mov wmv flv webm m4v ts rmvb 3gp mpg mpeg mts m2ts ogv vob
- 音频（9）：mp3 flac wav aac ogg m4a wma ape opus
- 文本（35）：txt md json xml csv log py js html css srt ass sub yaml yml toml ini sh bat sql go java c cpp h rs rb php ts tsx jsx vue lua r swift kt
- 图片（10）：jpg jpeg png gif bmp webp svg heic heif avif（画廊模式）
- 电子书（2）：epub pdf

## 已知问题
- 只转音频的视频（`-c:v copy`）暂停恢复可能从头开始（关键帧稀疏），用户偏好：优先速度
- Windows 防火墙需放行端口：`netsh advfirewall firewall add rule name="Media Server" dir=in action=allow protocol=tcp localport=18080`
- 网络需设为"专用"配置文件：`Set-NetConnectionProfile -NetworkCategory Private`
- Service Worker 已移除，旧版浏览器可能仍注册了 sw.js，需手动清除：F12 → Application → Service Workers → Unregister

## 代码规范
- 中文注释和 UI 文案
- snake_case 函数/变量，PascalCase 类
- CSS 用变量统一主题色
- 异步 handler 用 `async def`，同步工具函数用 `def`
- 错误：路由 `raise web.HTTPXxx()`，API `web.json_response({'ok': ...})`
- XSS 防护：所有用户输入经 `html.escape()` 转义后插入 HTML
- 缓存控制：管理后台和首页 HTML 响应加 `Cache-Control: no-cache, no-store, must-revalidate` + `Pragma` + `Expires`，避免浏览器缓存旧数据
- 管理后台增删共享目录后直接 JS 更新 DOM，不跳转刷新

## 待办事项
- [ ] 图片缩略图：用 Pillow 生成 320px 缩略图缓存，大图片目录不再加载原图
- [ ] 视频字幕：自动检测同目录 .srt/.ass 文件，转 VTT 加载到播放器
- [ ] 文件夹下载：打包为 ZIP 流式下载
- [ ] 画廊底部缩略图条：快速跳转到指定图片

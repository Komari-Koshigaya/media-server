# Media Server

局域网媒体服务器，一个 Python 脚本让你在手机上直接看电脑里的视频、听音乐、看图片、读小说。

## 功能

- **视频播放** — ArtPlayer 播放器，支持倍速、手势控制、画中画、自动连播、进度记忆
- **音频播放** — 同样使用 ArtPlayer，支持倍速和进度记忆
- **图片画廊** — 左右翻页、滑动手势、网格/列表视图切换
- **在线阅读** — TXT 章节检测、EPUB、PDF 渲染
- **文件上传** — 手机向 PC 上传文件，拖拽上传，最大 10GB
- **文件管理** — 排序（名称/大小/时间）、类型筛选、搜索、删除
- **管理后台** — 共享目录管理、修改密码、磁盘用量、缓存清理
- **智能转码** — 不支持的编码自动调用 ffmpeg 转码播放

## 截图

> 手机浏览器访问，深色主题，适配移动端

## 快速开始

### 安装依赖

```bash
pip install aiohttp aiofiles imageio-ffmpeg ebooklib PyMuPDF beautifulsoup4 lxml
```

### 启动

```bash
python -m media_server
```

启动后终端会显示：
- 访问地址（如 `http://192.168.1.7:8080`）
- 自动生成的登录密码

### 命令行参数

```bash
python -m media_server                     # 默认端口 8080，密码自动生成
python -m media_server --port 18080        # 自定义端口
python -m media_server --password 1234     # 自定义密码
```

### 使用

1. 电脑启动服务器
2. 手机连同一个 WiFi
3. 手机浏览器访问 `http://<电脑IP>:8080`
4. 输入密码登录
5. 点击共享目录即可浏览、播放、上传

## 支持格式

| 类型 | 格式 |
|------|------|
| 视频 | mp4 mkv avi mov wmv flv webm m4v ts rmvb 3gp mpg mpeg mts m2ts ogv vob |
| 音频 | mp3 flac wav aac ogg m4a wma ape opus |
| 图片 | jpg jpeg png gif bmp webp svg heic heif avif |
| 文本 | txt md json xml csv log py js html css srt ass sub yaml yml toml ini sh bat sql 等 35 种 |
| 电子书 | epub pdf |

## 技术栈

- **aiohttp** — 异步 HTTP 服务器
- **ArtPlayer** — HTML5 视频/音频播放器（CDN 加载）
- **HTTP Range / 206** — 视频进度条拖拽、断点续传
- **ffmpeg** — 视频转码和缩略图生成
- **Cookie + SHA256** — 鉴权，30 天有效期

## 项目结构

```
media_server/
  __init__.py    — 日志系统
  __main__.py    — 启动入口
  config.py      — 配置文件读写
  utils.py       — 文件类型检测、缩略图、EPUB/PDF 解析
  auth.py        — 鉴权和登录限流
  pages.py       — HTML 页面模板
  handlers.py    — 路由处理器
  app.py         — 应用工厂和中间件
tests/           — 84 个测试用例
```

## 网络配置

如果手机访问不了：

```powershell
# 1. 防火墙放行端口
netsh advfirewall firewall add rule name="Media Server" dir=in action=allow protocol=tcp localport=8080

# 2. 网络设为"专用"
Set-NetConnectionProfile -NetworkCategory Private
```

确保手机和电脑在同一个 WiFi 网络。

## 开发

```bash
python -m pytest tests/ -v    # 运行测试
python -m pytest tests/ -q    # 静默模式
```

## License

MIT

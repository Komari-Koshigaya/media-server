"""
局域网媒体服务器 - Media Server

通过局域网在 PC 和手机之间实现：
- 视频/音频流式播放（支持进度条拖拽、HTTP Range）
- 在线阅读 TXT/EPUB/PDF 文档
- 手机向 PC 上传文件（带进度条）
- Web 管理后台可视化管理共享文件夹
"""

__version__ = '1.0.0'

import logging
import sys
from pathlib import Path

# ─── 日志配置 ─────────────────────────────────────────────────────────────────
# 日志格式：时间 [级别] 消息
# 输出目标：控制台 + 文件（media_server.log）
_LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
_LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
_LOG_FILE = Path(__file__).parent.parent / 'media_server.log'

# 创建全局 logger
logger = logging.getLogger('media_server')
logger.setLevel(logging.DEBUG)

# 控制台 handler（INFO 级别，适配 Windows GBK 控制台）
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATE_FORMAT))
logger.addHandler(_console_handler)

# 文件 handler（DEBUG 级别，记录详细信息）
try:
    _file_handler = logging.FileHandler(_LOG_FILE, encoding='utf-8')
    _file_handler.setLevel(logging.DEBUG)
    _file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATE_FORMAT))
    logger.addHandler(_file_handler)
except (PermissionError, OSError):
    # 日志文件无法创建时仅使用控制台输出，不影响服务启动
    logger.warning('无法创建日志文件 %s，仅使用控制台输出', _LOG_FILE)


def safe_print(msg: str):
    """
    Windows 控制台安全打印（兼容 GBK 编码）。

    Windows 默认控制台编码为 GBK，直接 print 中文或 emoji 会抛出
    UnicodeEncodeError。此函数通过 GBK round-trip 兜底处理。

    Args:
        msg: 要打印的消息内容
    """
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('gbk', errors='replace').decode('gbk', errors='replace'))

"""
配置管理模块

负责 shares.json 的读写、共享目录列表管理、访问密码管理。

配置文件格式（shares.json）：
{
  "shares": [
    {"name": "显示名称", "path": "D:\\绝对路径\\文件夹"},
    ...
  ],
  "password": "1234"
}

路径规则：
- CONFIG_FILE 与 media_server/ 包同级，位于项目根目录
- shares 中的 path 必须是存在的绝对路径，加载时自动过滤已删除的目录
- password 为 4 位数字字符串，首次访问时自动生成
"""

import json
import logging
import random
import string
from pathlib import Path

logger = logging.getLogger('media_server')

# 配置文件路径：media_server/config.py -> 上两级 -> shares.json
CONFIG_FILE = Path(__file__).parent.parent / 'shares.json'


def load_config() -> dict:
    """
    加载 shares.json 配置文件。

    Returns:
        配置字典，包含 'shares' 和 'password' 键。
        文件不存在或格式损坏时返回空字典 {}。

    异常处理：
        - FileNotFoundError: 文件不存在，返回 {}
        - json.JSONDecodeError: JSON 格式损坏，返回 {}
        - PermissionError/OSError: 文件权限问题，返回 {}
    """
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text('utf-8'))
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning('配置文件格式异常: %s', e)
        return {}
    except (PermissionError, OSError) as e:
        logger.error('配置文件读取失败: %s', e)
        return {}


def save_config(cfg: dict) -> None:
    """
    保存配置到 shares.json。

    Args:
        cfg: 完整的配置字典，将覆盖写入文件。

    注意：使用 ensure_ascii=False 保留中文字符，indent=2 格式化输出。
    """
    try:
        CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), 'utf-8')
        logger.debug('配置已保存: %s', CONFIG_FILE)
    except (PermissionError, OSError) as e:
        logger.error('配置文件写入失败: %s', e)


def load_shares() -> list[dict]:
    """
    加载共享目录列表，自动过滤已不存在的目录。

    Returns:
        共享目录列表，每项包含 'name' 和 'path' 键。
        只返回 path 指向的目录仍然存在的项。
    """
    cfg = load_config()
    shares = cfg.get('shares', [])
    valid = []
    for s in shares:
        try:
            if Path(s['path']).is_dir():
                valid.append(s)
            else:
                logger.info('共享目录已不存在，跳过: %s', s.get('path', ''))
        except (KeyError, TypeError):
            logger.warning('共享目录配置格式异常: %s', s)
    return valid


def save_shares(shares: list[dict]) -> None:
    """
    保存共享目录列表到配置文件。

    会先加载现有配置，合并 shares 字段后写回，保留 password 等其他字段。

    Args:
        shares: 共享目录列表，每项包含 'name' 和 'path' 键。
    """
    cfg = load_config()
    cfg['shares'] = shares
    save_config(cfg)
    logger.info('共享目录已更新，共 %d 个', len(shares))


def get_password() -> str:
    """
    获取访问密码，不存在时自动生成 4 位数字密码并持久化。

    Returns:
        4 位数字密码字符串。

    密码生成规则：
        - 使用 random.choices 从 digits 中随机选取 4 个字符
        - 生成后立即写入 shares.json，后续访问直接读取
        - 局域网场景下安全性足够，无需加密存储
    """
    cfg = load_config()
    pw = cfg.get('password')
    if not pw:
        pw = ''.join(random.choices(string.digits, k=4))
        cfg['password'] = pw
        save_config(cfg)
        logger.info('已自动生成访问密码: %s', pw)
    return pw

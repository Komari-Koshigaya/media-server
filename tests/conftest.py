"""
测试配置模块

提供共享的测试夹具（fixtures），包括：
- 临时目录和配置文件
- MediaServer 实例
- aiohttp 测试客户端
"""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_config(tmp_path):
    """创建临时 shares.json 配置文件，返回其路径。"""
    config_file = tmp_path / 'shares.json'
    config_file.write_text(json.dumps({
        'shares': [
            {'name': '测试目录', 'path': str(tmp_path / 'test_share')},
        ],
        'password': '1234',
    }, ensure_ascii=False), 'utf-8')
    # 创建对应的共享目录
    (tmp_path / 'test_share').mkdir(exist_ok=True)
    return config_file


@pytest.fixture
def mock_config(monkeypatch, tmp_config):
    """将 config 模块的 CONFIG_FILE 指向临时文件。"""
    import media_server.config as cfg
    monkeypatch.setattr(cfg, 'CONFIG_FILE', tmp_config)
    return tmp_config

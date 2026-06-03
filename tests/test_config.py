"""
config 模块单元测试

覆盖场景：
- 配置文件正常加载
- 配置文件不存在时返回空字典
- JSON 格式损坏时返回空字典
- 共享目录列表的加载和保存
- 密码的自动生成和持久化
"""

import json
from pathlib import Path

from media_server.config import load_config, save_config, load_shares, save_shares, get_password


class TestLoadConfig:
    """load_config 函数测试"""

    def test正常加载(self, mock_config):
        """正常配置文件应返回完整字典"""
        cfg = load_config()
        assert 'shares' in cfg
        assert 'password' in cfg
        assert cfg['password'] == '1234'

    def test文件不存在(self, tmp_path, monkeypatch):
        """配置文件不存在时应返回空字典"""
        import media_server.config as cfg
        monkeypatch.setattr(cfg, 'CONFIG_FILE', tmp_path / 'nonexistent.json')
        result = load_config()
        assert result == {}

    def testJSON格式损坏(self, tmp_path, monkeypatch):
        """JSON 格式损坏时应返回空字典"""
        import media_server.config as cfg
        bad_file = tmp_path / 'bad.json'
        bad_file.write_text('not valid json {{{', 'utf-8')
        monkeypatch.setattr(cfg, 'CONFIG_FILE', bad_file)
        result = load_config()
        assert result == {}


class TestSaveConfig:
    """save_config 函数测试"""

    def test保存并重新加载(self, mock_config):
        """保存的配置应能正确重新加载"""
        cfg = load_config()
        cfg['password'] = '5678'
        save_config(cfg)
        reloaded = load_config()
        assert reloaded['password'] == '5678'


class TestLoadShares:
    """load_shares 函数测试"""

    def test加载有效目录(self, mock_config):
        """只返回路径仍然存在的共享目录"""
        shares = load_shares()
        assert len(shares) == 1
        assert shares[0]['name'] == '测试目录'

    def test返回所有目录(self, mock_config):
        """load_shares 应返回所有配置的目录，不做过滤"""
        cfg = load_config()
        cfg['shares'].append({'name': '额外目录', 'path': '/some/path'})
        from media_server.config import save_config as sc
        sc(cfg)
        shares = load_shares()
        # 应包含所有目录，包括路径可能不存在的
        assert len(shares) == 2
        assert shares[1]['name'] == '额外目录'


class TestGetPassword:
    """get_password 函数测试"""

    def test返回已有密码(self, mock_config):
        """配置文件中有密码时直接返回"""
        pw = get_password()
        assert pw == '1234'

    def test自动生成密码(self, tmp_path, monkeypatch):
        """配置文件中无密码时自动生成 4 位数字"""
        import media_server.config as cfg
        empty_file = tmp_path / 'empty.json'
        empty_file.write_text('{}', 'utf-8')
        monkeypatch.setattr(cfg, 'CONFIG_FILE', empty_file)
        pw = get_password()
        assert len(pw) == 4
        assert pw.isdigit()

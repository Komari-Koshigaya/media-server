"""
handlers 模块单元测试

覆盖场景：
- resolve_path 路径解析和穿越防护
- get_share_root 共享目录索引
- is_authed Cookie 鉴权
- async_probe_video_codec 编码探测（mock）
- handle_api_delete_file 文件删除 API
- handle_api_stats 服务器统计 API
- handle_api_change_password 修改密码 API
- handle_api_clear_thumbs 清理缓存 API
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from media_server.handlers import MediaServer


class TestResolvePath:
    """resolve_path 方法测试 - 路径解析和安全防护"""

    @pytest.fixture
    def server(self, mock_config):
        """创建使用临时配置的 MediaServer 实例"""
        return MediaServer()

    def test空路径返回根目录(self, server):
        """空相对路径应返回共享根目录"""
        result = server.resolve_path(0, '')
        assert result is not None
        assert result.is_dir()

    def test正常子路径(self, server, tmp_path):
        """正常子路径应正确解析"""
        (tmp_path / 'test_share' / 'subdir').mkdir(exist_ok=True)
        result = server.resolve_path(0, 'subdir')
        assert result is not None
        assert result.name == 'subdir'

    def test路径穿越防护(self, server):
        """.. 路径穿越不应逃逸出共享根目录"""
        result = server.resolve_path(0, '../../../etc/passwd')
        if result is not None:
            # 结果必须在共享根目录内
            root = server.get_share_root(0)
            assert result.is_relative_to(root)

    def testURL编码路径(self, server, tmp_path):
        """URL 编码的路径应正确解码"""
        (tmp_path / 'test_share' / '中文目录').mkdir(exist_ok=True)
        from urllib.parse import quote
        encoded = quote('中文目录')
        result = server.resolve_path(0, encoded)
        assert result is not None
        assert result.name == '中文目录'

    def test无效索引返回None(self, server):
        """无效的共享目录索引应返回 None"""
        assert server.resolve_path(999, '') is None
        assert server.resolve_path(-1, '') is None

    def test点路径过滤(self, server):
        """单个 . 应被过滤"""
        result = server.resolve_path(0, '.')
        assert result is not None
        root = server.get_share_root(0)
        assert result == root


class TestGetShareRoot:
    """get_share_root 方法测试"""

    @pytest.fixture
    def server(self, mock_config):
        return MediaServer()

    def test有效索引(self, server):
        """有效索引应返回 resolved Path"""
        root = server.get_share_root(0)
        assert root is not None
        assert root.is_dir()

    def test越界索引(self, server):
        """越界索引应返回 None"""
        assert server.get_share_root(999) is None
        assert server.get_share_root(-1) is None


class TestIsAuthed:
    """is_authed 方法测试"""

    @pytest.fixture
    def server(self, mock_config):
        return MediaServer()

    def test有效token(self, server):
        """有效 token cookie 应返回 True"""
        from unittest.mock import MagicMock
        request = MagicMock()
        request.cookies = {'token': server.valid_token}
        assert server.is_authed(request) is True

    def test无效token(self, server):
        """无效 token 应返回 False"""
        from unittest.mock import MagicMock
        request = MagicMock()
        request.cookies = {'token': 'wrong_token'}
        assert server.is_authed(request) is False

    def test无cookie(self, server):
        """无 cookie 应返回 False"""
        from unittest.mock import MagicMock
        request = MagicMock()
        request.cookies = {}
        assert server.is_authed(request) is False


class TestApiDeleteFile:
    """handle_api_delete_file 测试 - 文件删除 API"""

    @pytest.fixture
    def server(self, mock_config):
        return MediaServer()

    def test删除文件成功(self, server, tmp_path):
        """删除存在的文件应返回 ok"""
        import asyncio
        test_file = tmp_path / 'test_share' / 'to_delete.txt'
        test_file.write_text('hello')
        request = MagicMock()
        request.query = {'share': '0', 'path': 'to_delete.txt'}
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_delete_file(request))
        data = json.loads(resp.text)
        assert data['ok'] is True
        assert not test_file.exists()

    def test路径穿越防护(self, server, tmp_path):
        """路径穿越尝试应被拒绝，不删除根目录外文件"""
        outside_file = tmp_path / 'secret.txt'
        outside_file.write_text('secret')
        request = MagicMock()
        request.query = {'share': '0', 'path': '../../secret.txt'}
        # resolve_path 会拦截穿越路径，返回 None -> 404
        import asyncio
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_delete_file(request))
        assert resp.status == 404
        assert outside_file.exists()  # 文件不应被删除

    def test删除不存在的文件(self, server):
        """删除不存在的文件应返回 404"""
        import asyncio
        request = MagicMock()
        request.query = {'share': '0', 'path': 'nonexistent.txt'}
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_delete_file(request))
        assert resp.status == 404

    def test无效share索引(self, server):
        """无效 share 索引应返回 404"""
        import asyncio
        request = MagicMock()
        request.query = {'share': '999', 'path': 'test.txt'}
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_delete_file(request))
        assert resp.status == 404


class TestApiStats:
    """handle_api_stats 测试 - 服务器统计 API"""

    @pytest.fixture
    def server(self, mock_config):
        return MediaServer()

    def test返回统计信息(self, server):
        """应返回包含 uptime、share_count 等字段的 JSON"""
        import asyncio
        request = MagicMock()
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_stats(request))
        data = json.loads(resp.text)
        assert data['ok'] is True
        assert 'uptime' in data
        assert 'share_count' in data
        assert 'thumb_count' in data
        assert 'thumb_size' in data
        assert 'disks' in data
        assert data['share_count'] == 1  # mock_config 创建了 1 个共享

    def test运行时长格式(self, server):
        """uptime 应为中文格式字符串"""
        import asyncio
        request = MagicMock()
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_stats(request))
        data = json.loads(resp.text)
        assert '分钟' in data['uptime'] or '小时' in data['uptime']

    def test磁盘信息包含共享目录(self, server):
        """disks 列表应包含共享目录的磁盘信息"""
        import asyncio
        request = MagicMock()
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_stats(request))
        data = json.loads(resp.text)
        assert len(data['disks']) == 1
        assert data['disks'][0]['name'] == '测试目录'
        assert 'total' in data['disks'][0]
        assert 'free' in data['disks'][0]


class TestApiChangePassword:
    """handle_api_change_password 测试 - 修改密码 API"""

    @pytest.fixture
    def server(self, mock_config):
        return MediaServer()

    def test修改密码成功(self, server, mock_config):
        """正确旧密码 + 有效新密码应修改成功"""
        import asyncio
        request = MagicMock()
        request.json = AsyncMock(return_value={'old': '1234', 'new': '5678'})
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_change_password(request))
        data = json.loads(resp.text)
        assert data['ok'] is True
        assert server.password == '5678'
        # 验证 token 已更新
        from media_server.auth import make_token
        assert server.valid_token == make_token('5678')

    def test旧密码错误(self, server):
        """错误旧密码应返回 403"""
        import asyncio
        request = MagicMock()
        request.json = AsyncMock(return_value={'old': 'wrong', 'new': '5678'})
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_change_password(request))
        assert resp.status == 403
        data = json.loads(resp.text)
        assert data['ok'] is False
        assert '旧密码' in data['msg']

    def test新密码为空(self, server):
        """空新密码应返回 400"""
        import asyncio
        request = MagicMock()
        request.json = AsyncMock(return_value={'old': '1234', 'new': ''})
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_change_password(request))
        assert resp.status == 400

    def test请求格式错误(self, server):
        """非 JSON 请求应返回 400"""
        import asyncio
        request = MagicMock()
        request.json = AsyncMock(side_effect=ValueError('bad json'))
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_change_password(request))
        assert resp.status == 400


class TestApiClearThumbs:
    """handle_api_clear_thumbs 测试 - 清理缓存 API"""

    @pytest.fixture
    def server(self, mock_config, tmp_path, monkeypatch):
        srv = MediaServer()
        # 用临时目录替换 THUMB_DIR，避免影响真实缓存
        import media_server.handlers as h
        fake_thumb_dir = tmp_path / '.thumbs'
        fake_thumb_dir.mkdir()
        monkeypatch.setattr(h, 'THUMB_DIR', fake_thumb_dir)
        # 创建一些假缩略图文件
        for i in range(3):
            (fake_thumb_dir / f'test_{i}.jpg').write_bytes(b'fake_thumb')
        return srv

    def test清理缓存成功(self, server, tmp_path):
        """应删除所有缓存文件并返回数量"""
        import asyncio
        import media_server.handlers as h
        request = MagicMock()
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_clear_thumbs(request))
        data = json.loads(resp.text)
        assert data['ok'] is True
        assert data['count'] == 3
        # 验证文件已删除
        remaining = list(h.THUMB_DIR.iterdir()) if h.THUMB_DIR.is_dir() else []
        assert len(remaining) == 0

    def test空缓存目录(self, server, tmp_path, monkeypatch):
        """空缓存目录应返回 count=0"""
        import asyncio
        import media_server.handlers as h
        # 用空目录替换
        empty_dir = tmp_path / '.thumbs_empty'
        empty_dir.mkdir()
        monkeypatch.setattr(h, 'THUMB_DIR', empty_dir)
        request = MagicMock()
        resp = asyncio.get_event_loop().run_until_complete(server.handle_api_clear_thumbs(request))
        data = json.loads(resp.text)
        assert data['ok'] is True
        assert data['count'] == 0

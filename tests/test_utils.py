"""
utils 模块单元测试

覆盖场景：
- 文件类型检测（get_file_type, get_file_icon）
- MIME 类型映射（get_mime）
- 文件大小格式化（format_size）
- 缩略图缓存键生成（thumb_cache_key）
- 本地 IP 获取（get_local_ip）
"""

from media_server.utils import (
    get_file_type, get_file_icon, get_mime, format_size,
    thumb_cache_key, get_local_ip, VIDEO_EXTS, AUDIO_EXTS,
)


class TestGetFileType:
    """get_file_type 函数测试"""

    def test目录(self):
        assert get_file_type('any_name', True) == 'folder'

    def test视频文件(self):
        for ext in ('.mp4', '.mkv', '.avi', '.mov', '.webm'):
            assert get_file_type(f'video{ext}', False) == 'video', f'{ext} 应为 video'

    def test音频文件(self):
        for ext in ('.mp3', '.flac', '.wav', '.aac', '.ogg'):
            assert get_file_type(f'audio{ext}', False) == 'audio', f'{ext} 应为 audio'

    def test图片文件(self):
        for ext in ('.jpg', '.png', '.gif', '.webp', '.svg'):
            assert get_file_type(f'image{ext}', False) == 'image', f'{ext} 应为 image'

    def test文本文件(self):
        for ext in ('.txt', '.md', '.json', '.py', '.html'):
            assert get_file_type(f'text{ext}', False) == 'text', f'{ext} 应为 text'

    def test电子书(self):
        assert get_file_type('book.epub', False) == 'text'
        assert get_file_type('doc.pdf', False) == 'text'

    def test未知扩展名(self):
        assert get_file_type('data.xyz', False) == 'file'

    def test无扩展名(self):
        assert get_file_type('Makefile', False) == 'file'

    def test大小写不敏感(self):
        assert get_file_type('VIDEO.MP4', False) == 'video'
        assert get_file_type('AUDIO.FLAC', False) == 'audio'


class TestGetFileIcon:
    """get_file_icon 函数测试"""

    def test目录(self):
        assert get_file_icon('dir', True) == 'folder'

    def test视频图标(self):
        assert get_file_icon('test.mp4', False) == 'movie'

    def test音频图标(self):
        assert get_file_icon('test.mp3', False) == 'music_note'

    def test图片图标(self):
        assert get_file_icon('test.jpg', False) == 'image'

    def test电子书图标(self):
        assert get_file_icon('test.epub', False) == 'menu_book'

    def test文本图标(self):
        assert get_file_icon('test.txt', False) == 'description'

    def test未知文件图标(self):
        assert get_file_icon('test.xyz', False) == 'insert_drive_file'


class TestGetMime:
    """get_mime 函数测试"""

    def test标准格式(self):
        assert 'video' in get_mime('test.mp4') or get_mime('test.mp4') == 'video/mp4'

    def test自定义映射(self):
        assert get_mime('test.mkv') == 'video/x-matroska'
        assert get_mime('test.flac') == 'audio/flac'
        assert get_mime('test.ass') == 'text/plain'

    def test未知格式(self):
        assert get_mime('test.xyz123') == 'application/octet-stream'


class TestFormatSize:
    """format_size 函数测试"""

    def test字节(self):
        assert format_size(0) == '0 B'
        assert format_size(512) == '512 B'

    def testKB(self):
        result = format_size(1024)
        assert 'KB' in result

    def testMB(self):
        result = format_size(1024 * 1024)
        assert 'MB' in result

    def testGB(self):
        result = format_size(1024 * 1024 * 1024)
        assert 'GB' in result

    def testTB(self):
        result = format_size(1024 ** 4)
        assert 'TB' in result


class TestThumbCacheKey:
    """thumb_cache_key 函数测试"""

    def test返回jpg后缀(self):
        key = thumb_cache_key('/path/to/video.mp4')
        assert key.endswith('.jpg')

    def test相同路径相同key(self):
        k1 = thumb_cache_key('/path/to/video.mp4')
        k2 = thumb_cache_key('/path/to/video.mp4')
        assert k1 == k2

    def test不同路径不同key(self):
        k1 = thumb_cache_key('/path/to/video1.mp4')
        k2 = thumb_cache_key('/path/to/video2.mp4')
        assert k1 != k2

    def test长度合理(self):
        key = thumb_cache_key('/path/to/video.mp4')
        # MD5 hex = 32 chars + '.jpg' = 36 chars
        assert len(key) == 36


class TestGetLocalIp:
    """get_local_ip 函数测试"""

    def test返回字符串(self):
        ip = get_local_ip()
        assert isinstance(ip, str)

    def test格式正确(self):
        ip = get_local_ip()
        # 应该是有效的 IP 格式（至少包含一个点）
        assert '.' in ip

"""
pages 模块单元测试

覆盖场景：
- XSS 防护：恶意文件名/路径在 HTML 中被正确转义
- 各页面生成函数的基本输出验证
"""

from media_server.pages import (
    build_home_html, build_browse_html, build_player_html,
    build_admin_html, build_login_html, build_epub_reader_html,
    build_pdf_reader_html, page_shell,
)


class TestXSSPrevention:
    """XSS 注入防护测试"""

    def test首页恶意共享名(self):
        """共享目录名含 <script> 标签时应被转义"""
        shares = [{'name': '<script>alert(1)</script>', 'path': 'C:\\test'}]
        html = build_home_html(shares)
        # 恶意 script 标签应被转义（页面有合法 script 标签，所以只检查恶意内容）
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
        assert '&lt;script&gt;' in html

    def test首页恶意路径(self):
        """共享目录路径含 HTML 标签时应被转义"""
        shares = [{'name': 'test', 'path': '"><img src=x onerror=alert(1)>'}]
        html = build_home_html(shares)
        # 尖括号和引号应被转义，使 onerror 无法作为 HTML 属性执行
        assert '&lt;img' in html or '&gt;' in html
        assert '&quot;' in html

    def test浏览页恶意文件名(self):
        """文件名含恶意 HTML 时应被转义"""
        entries = [
            ('<script>alert(1)</script>.txt', 100, False, 0),
            ('"><img onerror=alert(1) src=x>.mp4', 1024, False, 0),
        ]
        html = build_browse_html(0, 'test', '', entries)
        # script 标签不应以原始形式出现在文件名区域
        assert '<script>alert' not in html
        # 尖括号应被转义，使 img 标签无法执行
        assert '&lt;script&gt;' in html
        assert '&gt;' in html

    def test浏览页恶意共享名(self):
        """浏览页的共享名应被转义"""
        entries = []
        html = build_browse_html(0, '<b>bold</b>', '', entries)
        assert '<b>' not in html
        assert '&lt;b&gt;' in html

    def test播放器恶意标题(self):
        """播放器页面标题应被转义"""
        html = build_player_html(
            '<script>alert(1)</script>.mp4',
            '/raw/0/test.mp4', 'video'
        )
        # 标题中的 script 标签不应被执行
        assert '<script>alert' not in html

    def test管理页恶意共享名(self):
        """管理页面的共享名应被转义"""
        shares = [{'name': '<img onerror=alert(1) src=x>', 'path': 'C:\\test'}]
        html = build_admin_html(shares, '192.168.1.1', 8080)
        assert 'onerror' not in html or '&lt;' in html


class TestPageShell:
    """page_shell 基础测试"""

    def test基本结构(self):
        """输出应包含 HTML5 基本结构"""
        html = page_shell('Test', '<div>content</div>')
        assert '<!DOCTYPE html>' in html
        assert '<html' in html
        assert '</html>' in html
        assert 'Test' in html

    def test自定义CSS(self):
        """extra_css 参数应被注入到 style 标签中"""
        html = page_shell('Test', '<div>content</div>', extra_css='body{color:red}')
        assert 'body{color:red}' in html


class TestBuildLoginHtml:
    """build_login_html 测试"""

    def test无错误(self):
        html = build_login_html('')
        assert 'login' in html.lower() or '密码' in html

    def test有错误(self):
        html = build_login_html('密码错误')
        assert '密码错误' in html

    def test恶意错误消息(self):
        """错误消息中的 HTML 应被转义"""
        html = build_login_html('<script>alert(1)</script>')
        # 注意：login 页面的 error 是内部生成的，但也要确保安全
        # 如果模板没有转义，至少不应有可执行的 script
        assert '<script>' not in html or '&lt;script&gt;' in html

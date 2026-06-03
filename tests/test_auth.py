"""
auth 模块单元测试

覆盖场景：
- token 生成的确定性和唯一性
- RateLimiter 的限流触发、锁定过期、成功重置
- RateLimiter 的 IP 过期清理机制
"""

import time

from media_server.auth import make_token, RateLimiter


class TestMakeToken:
    """make_token 函数测试"""

    def test确定性(self):
        """相同密码应始终生成相同的 token"""
        t1 = make_token('1234')
        t2 = make_token('1234')
        assert t1 == t2

    def test唯一性(self):
        """不同密码应生成不同的 token"""
        t1 = make_token('1234')
        t2 = make_token('5678')
        assert t1 != t2

    def test长度(self):
        """token 应为 32 字符的十六进制字符串"""
        t = make_token('test')
        assert len(t) == 32
        assert all(c in '0123456789abcdef' for c in t)


class TestRateLimiter:
    """RateLimiter 类测试"""

    def test初始状态不限流(self):
        """新创建的限流器不应限制任何 IP"""
        limiter = RateLimiter()
        assert limiter.check('192.168.1.1') is None

    def test失败计数(self):
        """连续失败次数未达阈值时不应锁定"""
        limiter = RateLimiter()
        for _ in range(limiter.MAX_FAILS - 1):
            limiter.record_fail('192.168.1.1')
        assert limiter.check('192.168.1.1') is None

    def test触发锁定(self):
        """连续失败达到阈值后应触发锁定"""
        limiter = RateLimiter()
        for _ in range(limiter.MAX_FAILS):
            limiter.record_fail('192.168.1.1')
        err = limiter.check('192.168.1.1')
        assert err is not None
        assert '秒后重试' in err

    def test锁定期间拒绝(self):
        """锁定期间所有请求应被拒绝"""
        limiter = RateLimiter()
        for _ in range(limiter.MAX_FAILS):
            limiter.record_fail('192.168.1.1')
        # 多次 check 应持续拒绝
        assert limiter.check('192.168.1.1') is not None
        assert limiter.check('192.168.1.1') is not None

    def test成功重置(self):
        """登录成功后应清除该 IP 的所有失败记录"""
        limiter = RateLimiter()
        for _ in range(limiter.MAX_FAILS):
            limiter.record_fail('192.168.1.1')
        limiter.record_success('192.168.1.1')
        assert limiter.check('192.168.1.1') is None

    def test不同IP独立(self):
        """不同 IP 的失败计数应独立"""
        limiter = RateLimiter()
        for _ in range(limiter.MAX_FAILS):
            limiter.record_fail('192.168.1.1')
        # 另一个 IP 不应受影响
        assert limiter.check('192.168.1.2') is None

    def test锁定过期(self):
        """锁定过期后应恢复正常"""
        limiter = RateLimiter()
        # 手动设置一个即将过期的锁定
        limiter._records['192.168.1.1'] = limiter._records.get(
            '192.168.1.1') or type(limiter._records.get('192.168.1.1', None))()
        # 直接操作内部状态模拟过期
        from media_server.auth import _IPRecord
        limiter._records['192.168.1.1'] = _IPRecord(
            fail_count=0, lock_until=time.time() - 1, last_active=time.time()
        )
        assert limiter.check('192.168.1.1') is None

    def test过期清理(self):
        """长时间不活跃的 IP 记录应被清理"""
        limiter = RateLimiter()
        from media_server.auth import _IPRecord
        # 模拟一个很久以前活跃的 IP
        limiter._records['10.0.0.1'] = _IPRecord(
            fail_count=3, lock_until=0, last_active=time.time() - 3600
        )
        # 触发清理
        limiter.check('192.168.1.1')
        assert '10.0.0.1' not in limiter._records

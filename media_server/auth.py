"""
鉴权与限流模块

提供两个核心功能：
1. make_token(): 基于密码生成会话 token，用于 Cookie 鉴权
2. RateLimiter: 基于 IP 的登录失败限流器，防止暴力破解

安全策略：
- token = SHA256("media_server:{password}") 截取前 32 位
- 密码验证通过后设置 httponly cookie，有效期 30 天
- 同一 IP 连续失败 5 次后锁定 5 分钟
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger('media_server')


def make_token(password: str) -> str:
    """
    根据密码生成会话 token。

    使用 SHA-256 对 "media_server:{password}" 进行哈希，
    截取前 32 个十六进制字符作为 token。

    Args:
        password: 明文密码

    Returns:
        32 字符的十六进制 token 字符串
    """
    raw = f'media_server:{password}'.encode()
    return hashlib.sha256(raw).hexdigest()[:32]


@dataclass
class _IPRecord:
    """
    单个 IP 的登录失败记录。

    Attributes:
        fail_count: 当前连续失败次数（锁定后重置为 0）
        lock_until: 锁定截止时间戳（Unix timestamp），0 表示未锁定
        last_active: 最后一次活动时间戳，用于清理过期记录
    """
    fail_count: int = 0
    lock_until: float = 0
    last_active: float = field(default_factory=time.time)


class RateLimiter:
    """
    基于 IP 的登录限流器。

    策略：
    - 同一 IP 连续失败 MAX_FAILS 次后，锁定 LOCKOUT_SECS 秒
    - 锁定期间所有登录请求直接拒绝，返回剩余等待时间
    - 成功登录后清除该 IP 的所有失败记录
    - 定期清理长时间不活跃的 IP 记录，防止内存泄漏

    使用方式：
        limiter = RateLimiter()
        err = limiter.check(ip)
        if err:
            return error_response(err)
        if password_ok:
            limiter.record_success(ip)
        else:
            limiter.record_fail(ip)
    """

    # 连续失败次数阈值，达到后触发锁定
    MAX_FAILS = 5
    # 锁定时长（秒），5 分钟
    LOCKOUT_SECS = 300
    # IP 记录过期时间（秒），30 分钟无活动后清理
    _IDLE_EXPIRE_SECS = 1800
    # 每次 check 时最多清理的过期记录数，避免单次清理耗时过长
    _MAX_CLEANUP_PER_CHECK = 50

    def __init__(self):
        self._records: dict[str, _IPRecord] = {}

    def check(self, ip: str) -> str | None:
        """
        检查指定 IP 是否被限流。

        每次调用时顺带清理过期 IP 记录，防止内存泄漏。

        Args:
            ip: 客户端 IP 地址

        Returns:
            未限流返回 None；限流中返回错误提示消息（含剩余秒数）
        """
        self._cleanup_expired()
        rec = self._records.get(ip)
        if not rec:
            return None
        rec.last_active = time.time()

        now = time.time()
        if rec.lock_until and now < rec.lock_until:
            secs = int(rec.lock_until - now)
            return f'登录次数过多，请 {secs} 秒后重试'
        if rec.lock_until and now >= rec.lock_until:
            # 锁定已过期，重置失败计数
            rec.fail_count = 0
            rec.lock_until = 0
        return None

    def record_fail(self, ip: str) -> None:
        """
        记录一次登录失败。

        达到 MAX_FAILS 次后自动触发 LOCKOUT_SECS 秒锁定。

        Args:
            ip: 客户端 IP 地址
        """
        rec = self._records.get(ip)
        if not rec:
            rec = _IPRecord()
            self._records[ip] = rec
        rec.fail_count += 1
        rec.last_active = time.time()

        if rec.fail_count >= self.MAX_FAILS:
            rec.lock_until = time.time() + self.LOCKOUT_SECS
            logger.warning('IP %s 登录失败 %d 次，锁定 %d 秒',
                           ip, rec.fail_count, self.LOCKOUT_SECS)
        else:
            logger.info('IP %s 登录失败 %d/%d 次', ip, rec.fail_count, self.MAX_FAILS)

    def record_success(self, ip: str) -> None:
        """
        记录登录成功，清除该 IP 的所有失败记录。

        Args:
            ip: 客户端 IP 地址
        """
        if ip in self._records:
            del self._records[ip]
            logger.info('IP %s 登录成功，已清除限流记录', ip)

    def _cleanup_expired(self) -> None:
        """
        清理长时间不活跃的 IP 记录。

        遍历所有记录，删除超过 _IDLE_EXPIRE_SECS 秒未活动的条目。
        每次最多清理 _MAX_CLEANUP_PER_CHECK 条，避免在高并发场景下
        单次 check 调用耗时过长。
        """
        now = time.time()
        expired = []
        for ip, rec in self._records.items():
            if now - rec.last_active > self._IDLE_EXPIRE_SECS:
                expired.append(ip)
            if len(expired) >= self._MAX_CLEANUP_PER_CHECK:
                break
        for ip in expired:
            del self._records[ip]
        if expired:
            logger.debug('清理 %d 条过期 IP 限流记录', len(expired))

"""Public-site guards: input clipping, per-IP rate limit, daily budget, result cache."""
import hashlib
import math
import time
from collections import defaultdict, deque
from datetime import datetime
from zoneinfo import ZoneInfo

TPE = ZoneInfo("Asia/Taipei")


def clip_text(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n]


class RateLimiter:
    def __init__(self, per_hour: int, window_s: float = 3600.0, clock=time.monotonic):
        self.per_hour, self.window, self.clock = per_hour, window_s, clock
        self.hits: dict[str, deque] = defaultdict(deque)

    def _bucket(self, ip: str):
        now = self.clock()
        if len(self.hits) > 1000 or not self.hits.get(ip):  # drop buckets whose window has passed
            for k in [k for k, d in self.hits.items() if not d or now - d[-1] >= self.window]:
                del self.hits[k]
        q = self.hits[ip]
        while q and now - q[0] >= self.window:
            q.popleft()
        return q, now

    def check(self, ip: str, cost: int = 1) -> bool:
        if cost < 1:
            raise ValueError("cost must be positive")
        q, now = self._bucket(ip)
        if len(q) + cost > self.per_hour:
            return False  # atomic: reject the entire batch without consuming any allowance
        q.extend([now] * cost)
        return True

    def retry_after(self, ip: str, cost: int = 1) -> int:
        q, now = self._bucket(ip)
        if len(q) + cost <= self.per_hour:
            return 0
        index = len(q) + cost - self.per_hour - 1
        return max(1, math.ceil((q[index] if index < len(q) else now) + self.window - now))


class BudgetGuard:
    """Tracks Muse spend per Taipei calendar day from a monotonically increasing spent_usd counter."""

    def __init__(self, daily_usd: float, today=lambda: datetime.now(TPE).date()):
        self.daily_usd, self.today = daily_usd, today
        self.day, self.base = None, 0.0

    def allow(self, spent_total: float) -> bool:
        d = self.today()
        if self.day is None:
            self.day = d  # first day: count everything spent since process start
        elif d != self.day:
            self.day, self.base = d, spent_total
        return (spent_total - self.base) < self.daily_usd


class ResultCache:
    def __init__(self, ttl_s: float = 86400, clock=time.monotonic):
        self.ttl, self.clock = ttl_s, clock
        self.data: dict[str, tuple[float, object]] = {}

    @staticmethod
    def key(text: str, lang: str) -> str:
        return hashlib.sha256(f"{lang}\x00{text}".encode()).hexdigest()

    def get(self, key: str):
        hit = self.data.get(key)
        if not hit or self.clock() - hit[0] > self.ttl:
            return None
        return hit[1]

    def put(self, key: str, value, max_items: int = 2000) -> None:
        now = self.clock()
        for k in [k for k, (t, _) in self.data.items() if now - t > self.ttl]:
            del self.data[k]  # expired reports leave memory, matching the 24 h promise
        while len(self.data) >= max_items:
            del self.data[next(iter(self.data))]  # oldest first (dicts keep insertion order)
        self.data[key] = (now, value)

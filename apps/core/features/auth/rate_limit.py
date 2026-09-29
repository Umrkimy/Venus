from datetime import datetime, timedelta


class LoginRateLimiter:
    def __init__(
        self, max_failures: int = 5, window: timedelta = timedelta(minutes=15)
    ) -> None:
        self.max_failures = max_failures
        self.window = window
        self._failures: dict[str, list[datetime]] = {}

    def is_blocked(self, key: str, now: datetime) -> bool:
        failures = [t for t in self._failures.get(key, []) if now - t < self.window]
        self._failures[key] = failures
        return len(failures) >= self.max_failures

    def record_failure(self, key: str, now: datetime) -> None:
        self._failures.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)


_login_rate_limiter = LoginRateLimiter()


def get_login_rate_limiter() -> LoginRateLimiter:
    return _login_rate_limiter

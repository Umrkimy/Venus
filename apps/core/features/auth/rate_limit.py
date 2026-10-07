from datetime import datetime, timedelta

from fastapi import Request


def client_key(request: Request) -> str:
    """Who is trying to log in, so one phone's typos don't lock out the PC.

    Every browser reaches Core through the web app's proxy, so the connection
    address is always the proxy's. Tailscale replaces X-Forwarded-For with the
    phone's real tailnet address (a faked header is dropped), and Next.js passes
    it on, or adds the browser's address when the header is missing. Take the
    last entry: it was written by the proxy nearest Core. Core and the web app
    only listen on 127.0.0.1, so only programs on this PC could fake it.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    last = forwarded.split(",")[-1].strip()
    if last:
        return last
    return request.client.host if request.client else "unknown"


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

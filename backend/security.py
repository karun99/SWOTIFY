"""Security helpers for Swotify: admin auth token + lightweight rate limiting.

Admin auth uses a single shared bearer token. Set SWOTIFY_ADMIN_TOKEN to pin a
known value; otherwise one is generated on startup and printed to the log.
Rate limiting is an in-memory sliding window — enough to blunt beacon floods
and expensive AI audits without adding external dependencies.
"""

import logging
import os
import secrets
import threading
import time

log = logging.getLogger("swotify.security")

_TOKEN_LOCK = threading.Lock()
_admin_token: str | None = None


def get_admin_token() -> str:
    global _admin_token
    if _admin_token is not None:
        return _admin_token
    with _TOKEN_LOCK:
        if _admin_token is not None:
            return _admin_token
        token = os.environ.get("SWOTIFY_ADMIN_TOKEN", "").strip()
        if not token:
            token = secrets.token_urlsafe(32)
            log.warning(
                "SWOTIFY_ADMIN_TOKEN not set — generated an ephemeral admin token: %s "
                "(set the env var to use a stable one)",
                token,
            )
        _admin_token = token
        return token


def valid_token(token: str) -> bool:
    if not token:
        return False
    return secrets.compare_digest(token, get_admin_token())


class RateLimiter:
    """Sliding-window rate limiter. Thread-safe, self-cleaning."""

    def __init__(self, max_hits: int, window_s: float):
        self.max_hits = max_hits
        self.window_s = window_s
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            if len(self._hits) > 10_000:
                cutoff = now - self.window_s
                self._hits = {k: v for k, v in self._hits.items() if v and v[-1] >= cutoff}
            hits = [t for t in self._hits.get(key, []) if now - t < self.window_s]
            if len(hits) >= self.max_hits:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True


def client_ip(request) -> str:
    """Best-effort client IP: honour X-Forwarded-For, fall back to socket."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        first = fwd.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"

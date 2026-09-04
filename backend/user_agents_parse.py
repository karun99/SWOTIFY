"""Lightweight user-agent parsing (no external dependency)."""

import re

_MOBILE = re.compile(r"mobile|iphone|ipad|android|blackberry|opera mini", re.I)
_TABLET = re.compile(r"ipad|tablet|kindle|silk", re.I)
_BOTS = re.compile(r"bot|crawl|spider|slurp|bingpreview|duckduckbot", re.I)
_SMARTPHONE = re.compile(r"iphone|android.*mobile|samsung|pixel", re.I)

_BROWSERS = [
    (re.compile(r"edg/|edge/", re.I), "Edge"),
    (re.compile(r"opera|opr/", re.I), "Opera"),
    (re.compile(r"firefox", re.I), "Firefox"),
    (re.compile(r"chrome|crios", re.I), "Chrome"),
    (re.compile(r"safari", re.I), "Safari"),
]


def parse_device(ua: str) -> str:
    if not ua:
        return "desktop"
    if _BOTS.search(ua):
        return "bot"
    if _TABLET.search(ua):
        return "tablet"
    if _SMARTPHONE.search(ua) or ("mobile" in ua.lower() and "iphone" in ua.lower()) or ("android" in ua.lower() and "mobile" in ua.lower()):
        return "mobile"
    if _MOBILE.search(ua):
        return "mobile"
    return "desktop"


def parse_browser(ua: str) -> str:
    if not ua:
        return "unknown"
    for pattern, name in _BROWSERS:
        if pattern.search(ua):
            return name
    return "unknown"

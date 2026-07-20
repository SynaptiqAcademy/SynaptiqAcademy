"""Minimal user-agent parser — just enough to show "macOS · Chrome" style
labels for Active Sessions. No external dependency; regex-based, best-effort.
Returns honest fallbacks ("Unknown device") rather than guessing.
"""
from __future__ import annotations

import re

_OS_PATTERNS = [
    (re.compile(r"Windows NT 10\.0"), "Windows 10/11"),
    (re.compile(r"Windows NT"), "Windows"),
    (re.compile(r"Mac OS X"), "macOS"),
    (re.compile(r"iPhone"), "iOS"),
    (re.compile(r"iPad"), "iPadOS"),
    (re.compile(r"Android"), "Android"),
    (re.compile(r"Linux"), "Linux"),
]

_BROWSER_PATTERNS = [
    (re.compile(r"Edg/"), "Edge"),
    (re.compile(r"OPR/|Opera"), "Opera"),
    (re.compile(r"Chrome/"), "Chrome"),
    (re.compile(r"CriOS/"), "Chrome"),
    (re.compile(r"FxiOS/"), "Firefox"),
    (re.compile(r"Firefox/"), "Firefox"),
    (re.compile(r"Safari/"), "Safari"),
]


def parse_user_agent(ua: str) -> dict:
    ua = ua or ""
    os_name = next((label for pattern, label in _OS_PATTERNS if pattern.search(ua)), "Unknown OS")
    browser = next((label for pattern, label in _BROWSER_PATTERNS if pattern.search(ua)), "Unknown browser")
    is_mobile = bool(re.search(r"Mobile|iPhone|Android", ua))
    return {
        "os": os_name,
        "browser": browser,
        "label": f"{os_name} · {browser}",
        "is_mobile": is_mobile,
    }

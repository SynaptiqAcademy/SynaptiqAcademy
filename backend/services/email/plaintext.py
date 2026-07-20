"""Plain-text component helpers — the text-email mirror of components.py.

Every HTML component has a plain-text equivalent here so templates build
both versions from the same structured data, rather than stripping tags
from HTML (unreliable) or leaving the text part as an afterthought. Resend
accepts a `text` field alongside `html`; mail clients that prefer or require
plain text (accessibility tools, some corporate filters) get a real,
readable version rather than a stripped-down copy.
"""
from __future__ import annotations

from typing import Sequence

from . import tokens as tok

LINE = "─" * 44


def text_heading(overline: str, heading: str, subheading: str = "") -> str:
    parts = [overline.upper(), heading]
    if subheading:
        parts.append(subheading)
    return "\n".join(parts)


def text_paragraph(text: str) -> str:
    return text


def text_button(label: str, url: str) -> str:
    return f"{label}: {url}"


def text_feature_list(features: Sequence[tuple[str, str, str]]) -> str:
    return "\n".join(f"  - {title}: {desc}" for _icon, title, desc in features)


def text_step_list(steps: Sequence[tuple[str, str]]) -> str:
    return "\n".join(f"  {i}. {title} — {desc}" for i, (title, desc) in enumerate(steps, start=1))


def text_bullet_list(items: Sequence[str]) -> str:
    return "\n".join(f"  - {item}" for item in items)


def text_checklist(items: Sequence[tuple[str, bool]]) -> str:
    return "\n".join(f"  [{'x' if done else ' '}] {label}" for label, done in items)


def text_progress(percentage: int, label: str = "") -> str:
    pct = max(0, min(100, percentage))
    prefix = f"{label}: " if label else ""
    return f"{prefix}{pct}%"


def text_divider() -> str:
    return LINE


def text_footer(*, help_center_url: str, privacy_url: str, terms_url: str,
                security_url: str, year: int, unsubscribe_url: str | None = None) -> str:
    lines = [
        LINE,
        f"Need help? {help_center_url}",
        "",
        f"Privacy Policy: {privacy_url}",
        f"Terms of Service: {terms_url}",
        f"Help Center: {help_center_url}",
        f"Security Center: {security_url}",
    ]
    if unsubscribe_url:
        lines.append(f"Unsubscribe: {unsubscribe_url}")
    lines += ["", f"© {year} {tok.BRAND_NAME} · Research Operating System · synaptiq.academy"]
    return "\n".join(lines)


def render_text_email(*, sections: Sequence[str],
                      help_center_url: str = "https://synaptiq.academy/help-center",
                      privacy_url: str = "https://synaptiq.academy/privacy",
                      terms_url: str = "https://synaptiq.academy/terms",
                      security_url: str = "https://synaptiq.academy/security",
                      year: int | None = None,
                      unsubscribe_url: str | None = None) -> str:
    from datetime import datetime, timezone
    body = "\n\n".join(s for s in sections if s)
    footer = text_footer(
        help_center_url=help_center_url, privacy_url=privacy_url, terms_url=terms_url,
        security_url=security_url, year=year or datetime.now(timezone.utc).year,
        unsubscribe_url=unsubscribe_url,
    )
    return f"{tok.BRAND_NAME}\n{tok.TAGLINE}\n\n{body}\n\n{footer}"

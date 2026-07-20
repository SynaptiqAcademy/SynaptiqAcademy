"""Reusable email components — the building blocks every template composes.

Each function returns a self-contained HTML fragment (a <tr> or nested
<table>), styled with inline CSS for maximum client compatibility (Outlook
strips <style> blocks other than the ones layout.py injects for dark-mode/
responsive overrides). Never hand-roll a card/button/banner directly inside
a template module — add or extend a component here instead, so every email
shares one visual language and there is exactly one place to fix a rendering
bug across the whole system.

All text passed in is expected to already be HTML-escaped by the caller
where it originates from user input (see i18n.py / templates for the
trusted, static copy — user-controlled strings like a name should be run
through `html.escape` before being interpolated).
"""
from __future__ import annotations

from typing import Optional, Sequence

from . import tokens as tok


def component_header() -> str:
    """Brand wordmark header — text-based (not an image), so it always
    renders even with images blocked, matching the frontend AuthHeader."""
    return f"""\
<tr><td style="padding:28px 40px 20px;text-align:center;" class="sq-header">
  <div style="font-family:{tok.FONT_SANS};font-size:19px;font-weight:800;letter-spacing:-0.04em;color:{tok.NAVY};" class="sq-text-invert">
    {tok.BRAND_NAME}
  </div>
  <div style="font-family:{tok.FONT_SANS};font-size:10px;font-weight:500;letter-spacing:0.08em;text-transform:uppercase;color:{tok.TEXT_MUTED};margin-top:4px;" class="sq-text-muted">
    {tok.TAGLINE}
  </div>
</td></tr>"""


def component_hero(overline: str, heading: str, subheading: str = "") -> str:
    sub = (
        f'<p style="font-size:15px;line-height:1.6;color:{tok.TEXT_SECONDARY};margin:10px 0 0;" class="sq-text-secondary">{subheading}</p>'
        if subheading else ""
    )
    return f"""\
<tr><td style="padding:8px 40px 4px;">
  <div style="font-family:{tok.FONT_SANS};font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{tok.TEXT_MUTED};" class="sq-text-muted">{overline}</div>
  <h1 style="font-family:{tok.FONT_SERIF};font-size:26px;line-height:1.25;font-weight:normal;color:{tok.TEXT_PRIMARY};margin:10px 0 0;" class="sq-text-invert">{heading}</h1>
  {sub}
</td></tr>"""


def component_body_text(html: str) -> str:
    return f"""\
<tr><td style="padding:16px 40px 0;">
  <div style="font-size:15px;line-height:1.65;color:{tok.TEXT_SECONDARY};" class="sq-text-secondary">{html}</div>
</td></tr>"""


def component_divider() -> str:
    return f"""\
<tr><td style="padding:24px 40px;">
  <div style="border-top:1px solid {tok.BRD};" class="sq-border"></div>
</td></tr>"""


def component_cta_button(label: str, url: str, variant: str = "primary", full_width: bool = False) -> str:
    """One button. Use component_button_row() for primary+secondary pairs."""
    if variant == "primary":
        style = f"background:{tok.NAVY};color:{tok.WHITE};border:1px solid {tok.NAVY};"
    else:
        style = f"background:transparent;color:{tok.NAVY};border:1.5px solid {tok.NAVY};"
    width = "width:100%;" if full_width else ""
    return (
        f'<a href="{url}" style="display:inline-block;{width}{style}text-decoration:none;'
        f'font-family:{tok.FONT_SANS};font-size:14px;font-weight:600;letter-spacing:-0.01em;'
        f'padding:13px 26px;border-radius:{tok.RADIUS_SM};text-align:center;box-sizing:border-box;" '
        f'class="sq-btn-{variant}">{label}</a>'
    )


def component_button_row(primary: tuple[str, str], secondary: Optional[tuple[str, str]] = None) -> str:
    """primary/secondary are (label, url) tuples. Renders stacked on mobile via layout.py media query."""
    secondary_html = ""
    if secondary:
        secondary_html = f'<div style="margin-top:10px;">{component_cta_button(secondary[0], secondary[1], "secondary")}</div>'
    return f"""\
<tr><td style="padding:26px 40px 8px;" align="center" class="sq-btn-row">
  {component_cta_button(primary[0], primary[1], "primary")}
  {secondary_html}
</td></tr>"""


def component_link_fallback(url: str) -> str:
    return f"""\
<tr><td style="padding:8px 40px 0;">
  <div style="font-size:12px;color:{tok.TEXT_MUTED};word-break:break-all;" class="sq-text-muted">
    Or paste this link into your browser: <span style="color:{tok.NAVY};">{url}</span>
  </div>
</td></tr>"""


def component_info_card(title: str, body_html: str) -> str:
    return f"""\
<tr><td style="padding:8px 40px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{tok.SURF2};border:1px solid {tok.BRD};border-radius:{tok.RADIUS};" class="sq-card">
    <tr><td style="padding:18px 20px;">
      <div style="font-family:{tok.FONT_SANS};font-size:13px;font-weight:700;color:{tok.TEXT_PRIMARY};margin-bottom:6px;" class="sq-text-invert">{title}</div>
      <div style="font-size:13.5px;line-height:1.6;color:{tok.TEXT_SECONDARY};" class="sq-text-secondary">{body_html}</div>
    </td></tr>
  </table>
</td></tr>"""


def component_feature_grid(features: Sequence[tuple[str, str, str]]) -> str:
    """features: list of (emoji_icon, title, description). Renders as a 2-col
    table that collapses to 1 column on mobile (layout.py media query)."""
    cells = []
    for icon, title, desc in features:
        cells.append(f"""\
<td width="50%" valign="top" style="padding:10px;" class="sq-feature-cell">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{tok.SURF2};border:1px solid {tok.BRD};border-radius:{tok.RADIUS};" class="sq-card">
    <tr><td style="padding:16px 18px;">
      <div style="font-size:20px;line-height:1;margin-bottom:8px;">{icon}</div>
      <div style="font-family:{tok.FONT_SANS};font-size:13px;font-weight:700;color:{tok.TEXT_PRIMARY};" class="sq-text-invert">{title}</div>
      <div style="font-size:12.5px;line-height:1.5;color:{tok.TEXT_MUTED};margin-top:4px;" class="sq-text-muted">{desc}</div>
    </td></tr>
  </table>
</td>""")
    # pair up into rows of 2
    rows = []
    for i in range(0, len(cells), 2):
        pair = cells[i:i + 2]
        if len(pair) == 1:
            pair.append('<td width="50%"></td>')
        rows.append(f"<tr>{''.join(pair)}</tr>")
    return f"""\
<tr><td style="padding:10px 30px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    {''.join(rows)}
  </table>
</td></tr>"""


def component_step_list(steps: Sequence[tuple[str, str]]) -> str:
    """steps: list of (title, description) — rendered as a numbered quick-start list."""
    rows = []
    for i, (title, desc) in enumerate(steps, start=1):
        rows.append(f"""\
<tr>
  <td width="32" valign="top" style="padding:10px 0;">
    <div style="width:22px;height:22px;border-radius:50%;background:{tok.NAVY};color:{tok.WHITE};font-family:{tok.FONT_SANS};font-size:11px;font-weight:700;text-align:center;line-height:22px;">{i}</div>
  </td>
  <td valign="top" style="padding:10px 0 10px 12px;">
    <div style="font-family:{tok.FONT_SANS};font-size:13.5px;font-weight:700;color:{tok.TEXT_PRIMARY};" class="sq-text-invert">{title}</div>
    <div style="font-size:12.5px;line-height:1.5;color:{tok.TEXT_MUTED};margin-top:2px;" class="sq-text-muted">{desc}</div>
  </td>
</tr>""")
    return f"""\
<tr><td style="padding:8px 40px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    {''.join(rows)}
  </table>
</td></tr>"""


def component_bullet_list(items: Sequence[str]) -> str:
    """Plain bullet list for factual/informational points — distinct from
    component_checklist(), which implies trackable done/not-done tasks."""
    rows = []
    for item in items:
        rows.append(f"""\
<tr>
  <td width="14" valign="top" style="padding:4px 0;font-size:13px;color:{tok.TEXT_MUTED};">&#8226;</td>
  <td style="padding:4px 0 4px 6px;font-size:13.5px;line-height:1.5;color:{tok.TEXT_SECONDARY};" class="sq-text-secondary">{item}</td>
</tr>""")
    return f"""\
<tr><td style="padding:8px 40px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    {''.join(rows)}
  </table>
</td></tr>"""


def component_checklist(items: Sequence[tuple[str, bool]]) -> str:
    """items: list of (label, done). Rendered as a check/circle task list."""
    rows = []
    for label, done in items:
        mark = f'<span style="color:{tok.EMERALD};">&#10003;</span>' if done else f'<span style="color:{tok.TEXT_MUTED};">&#9675;</span>'
        color = tok.TEXT_MUTED if done else tok.TEXT_PRIMARY
        rows.append(f"""\
<tr>
  <td width="20" style="padding:5px 0;font-size:14px;">{mark}</td>
  <td style="padding:5px 0 5px 8px;font-size:13.5px;color:{color};{'text-decoration:line-through;' if done else ''}" class="sq-text-invert">{label}</td>
</tr>""")
    return f"""\
<tr><td style="padding:8px 40px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    {''.join(rows)}
  </table>
</td></tr>"""


def component_progress_bar(percentage: int, label: str = "") -> str:
    pct = max(0, min(100, percentage))
    label_html = (
        f'<div style="font-size:12px;color:{tok.TEXT_MUTED};margin-bottom:6px;" class="sq-text-muted">{label}</div>'
        if label else ""
    )
    return f"""\
<tr><td style="padding:16px 40px 0;">
  {label_html}
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{tok.BRD};border-radius:{tok.RADIUS_PILL};">
    <tr><td>
      <table role="presentation" width="{pct}%" cellpadding="0" cellspacing="0" style="background:{tok.NAVY};border-radius:{tok.RADIUS_PILL};">
        <tr><td style="height:8px;line-height:8px;font-size:1px;">&nbsp;</td></tr>
      </table>
    </td></tr>
  </table>
  <div style="font-family:{tok.FONT_SERIF};font-size:22px;color:{tok.TEXT_PRIMARY};margin-top:8px;" class="sq-text-invert">{pct}%</div>
</td></tr>"""


def component_success_banner(text: str) -> str:
    return f"""\
<tr><td style="padding:8px 40px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{tok.SUCCESS_BG};border:1px solid {tok.SUCCESS_BORDER};border-radius:{tok.RADIUS};">
    <tr><td style="padding:12px 16px;font-family:{tok.FONT_SANS};font-size:13px;font-weight:600;color:{tok.SUCCESS_TEXT};">&#10003; {text}</td></tr>
  </table>
</td></tr>"""


def component_alert_banner(text: str, variant: str = "warning") -> str:
    palette = {
        "warning": (tok.WARNING_BG, tok.WARNING_BORDER, tok.WARNING_TEXT, "!"),
        "info": (tok.INFO_BG, tok.INFO_BORDER, tok.INFO_TEXT, "i"),
        "danger": (tok.DANGER_BG, tok.DANGER_BORDER, tok.DANGER_TEXT, "!"),
    }.get(variant, (tok.WARNING_BG, tok.WARNING_BORDER, tok.WARNING_TEXT, "!"))
    bg, border, text_color, icon = palette
    return f"""\
<tr><td style="padding:8px 40px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{bg};border:1px solid {border};border-radius:{tok.RADIUS};">
    <tr><td style="padding:12px 16px;font-family:{tok.FONT_SANS};font-size:13px;color:{text_color};line-height:1.5;">{icon} {text}</td></tr>
  </table>
</td></tr>"""


def component_support_block(help_center_url: str) -> str:
    return f"""\
<tr><td style="padding:24px 40px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid {tok.BRD};padding-top:18px;" class="sq-border">
    <tr><td style="padding-top:18px;font-size:12.5px;line-height:1.6;color:{tok.TEXT_MUTED};" class="sq-text-muted">
      Need help? Visit the <a href="{help_center_url}" style="color:{tok.NAVY};">Help Center</a>
      or reply to this email — a real person reads every message.
    </td></tr>
  </table>
</td></tr>"""


def component_footer(*, help_center_url: str, privacy_url: str, terms_url: str,
                     security_url: str, year: int, unsubscribe_url: Optional[str] = None) -> str:
    unsub = (
        f' &middot; <a href="{unsubscribe_url}" style="color:{tok.TEXT_MUTED};text-decoration:underline;">Unsubscribe</a>'
        if unsubscribe_url else ""
    )
    return f"""\
<tr><td style="padding:28px 40px 32px;">
  <div style="font-size:11.5px;line-height:1.7;color:{tok.TEXT_MUTED};" class="sq-text-muted">
    <a href="{privacy_url}" style="color:{tok.TEXT_MUTED};text-decoration:underline;">Privacy Policy</a>
    &middot; <a href="{terms_url}" style="color:{tok.TEXT_MUTED};text-decoration:underline;">Terms of Service</a>
    &middot; <a href="{help_center_url}" style="color:{tok.TEXT_MUTED};text-decoration:underline;">Help Center</a>
    &middot; <a href="{security_url}" style="color:{tok.TEXT_MUTED};text-decoration:underline;">Security Center</a>{unsub}
  </div>
  <div style="font-size:11px;color:{tok.TEXT_MUTED};margin-top:10px;" class="sq-text-muted">
    &copy; {year} {tok.BRAND_NAME} &middot; Research Operating System &middot; synaptiq.academy
  </div>
</td></tr>"""

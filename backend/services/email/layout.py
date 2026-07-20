"""Email layout — assembles components into a complete, responsive,
dark-mode-aware HTML document. This is the ONLY place that owns the
<!doctype>/<html>/<style> shell; every template calls render_email() and
never builds its own outer document.

Design notes
------------
- Table-based layout throughout (email clients do not reliably support
  flexbox/grid) with inline styles as the baseline for every client,
  overridden by the injected <style> block for clients that honor it
  (Gmail, Apple Mail, Outlook.com, most modern mobile clients).
- Dark mode: `sq-*` classes + `prefers-color-scheme: dark` media query flip
  text/background colors. Clients that ignore <style> just render the light
  (inline-style) version, which is always legible.
- Responsive: a single `max-width:600px` media query stacks the two-column
  feature grid and button row on narrow viewports.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from . import tokens as tok
from .components import component_header, component_footer, component_support_block


def _style_block() -> str:
    return f"""\
<style>
  body {{ margin:0; padding:0; }}
  img {{ border:0; outline:none; text-decoration:none; }}
  a {{ transition: opacity 120ms ease; }}
  a:hover {{ opacity: 0.85; }}
  @media screen and (max-width: 600px) {{
    .sq-container {{ width: 100% !important; }}
    .sq-feature-cell {{ display:block !important; width:100% !important; padding:6px 0 !important; }}
    .sq-btn-row a {{ display:block !important; width:100% !important; }}
  }}
  @media (prefers-color-scheme: dark) {{
    .sq-body {{ background:{tok.BODY_BG_DARK} !important; }}
    .sq-card, .sq-container {{ background:{tok.CARD_BG_DARK} !important; }}
    .sq-border {{ border-color:{tok.BRD_DARK} !important; }}
    .sq-text-invert {{ color:{tok.TEXT_PRIMARY_DARK} !important; }}
    .sq-text-secondary {{ color:{tok.TEXT_SECONDARY_DARK} !important; }}
    .sq-text-muted {{ color:{tok.TEXT_MUTED_DARK} !important; }}
  }}
</style>"""


def render_email(*, preheader: str, sections: Sequence[str],
                 include_support: bool = True,
                 help_center_url: str = "https://synaptiq.academy/help-center",
                 privacy_url: str = "https://synaptiq.academy/privacy",
                 terms_url: str = "https://synaptiq.academy/terms",
                 security_url: str = "https://synaptiq.academy/security",
                 unsubscribe_url: str | None = None) -> str:
    """Assemble header + template body sections + support block + footer.

    `sections` is a list of pre-rendered <tr> fragments from components.py —
    templates own the ORDER and CHOICE of components, layout.py owns the
    outer document, dark mode, and responsiveness.
    """
    year = datetime.now(timezone.utc).year
    support = component_support_block(help_center_url) if include_support else ""
    footer = component_footer(
        help_center_url=help_center_url, privacy_url=privacy_url,
        terms_url=terms_url, security_url=security_url,
        year=year, unsubscribe_url=unsubscribe_url,
    )

    body = "\n".join(sections)

    return f"""\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{tok.BRAND_NAME}</title>
{_style_block()}
</head>
<body class="sq-body" style="margin:0;padding:0;background:{tok.WARM};font-family:{tok.FONT_SANS};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{preheader}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{tok.WARM};padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="{tok.CONTAINER_WIDTH}" cellpadding="0" cellspacing="0"
             class="sq-container" style="background:{tok.WHITE};border:1px solid {tok.BRD};border-radius:{tok.RADIUS};max-width:{tok.CONTAINER_WIDTH}px;width:100%;">
        {component_header()}
        {body}
        {support}
        {footer}
      </table>
      <div style="font-size:11px;color:{tok.TEXT_MUTED};margin-top:16px;">
        This is a transactional message from {tok.BRAND_NAME}.
      </div>
    </td></tr>
  </table>
</body>
</html>"""

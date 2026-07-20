"""Email design tokens — the email-safe mirror of frontend/src/lib/tokens.js.

Email clients (Outlook/Gmail/Apple Mail) need inline hex values, not CSS
variables, so these are plain string constants rather than a shared import
across the frontend/backend boundary. Keep values in sync with tokens.js by
hand when the platform palette changes — there are few enough of them that
drift is easy to catch in review.
"""
from __future__ import annotations

BRAND_NAME = "SYNAPTIQ"
TAGLINE = "AI-Powered Academic Collaboration"

# ── Core palette (mirrors frontend NAVY/EMERALD/AMBER/CRIMSON) ────────────────
NAVY = "#0F2847"
NAVY_LIGHT = "#1a3a5c"
EMERALD = "#059669"
AMBER = "#D97706"
CRIMSON = "#DC2626"
ACCENT = "#8A1538"

# ── Surfaces ───────────────────────────────────────────────────────────────────
WHITE = "#FFFFFF"
WARM = "#F4F6FA"          # page/body background
SURF2 = "#F8FAFC"         # card alt surface / feature card bg
CARD_BG_DARK = "#111827"  # dark-mode card background
BODY_BG_DARK = "#0B1220"  # dark-mode page background

# ── Borders ────────────────────────────────────────────────────────────────────
BRD = "#E2E8F0"
BRD_DARK = "#1F2937"

# ── Text hierarchy ─────────────────────────────────────────────────────────────
TEXT_PRIMARY = "#0F172A"
TEXT_SECONDARY = "#475569"
TEXT_MUTED = "#64748B"
TEXT_PRIMARY_DARK = "#F1F5F9"
TEXT_SECONDARY_DARK = "#CBD5E1"
TEXT_MUTED_DARK = "#94A3B8"

# ── Semantic ────────────────────────────────────────────────────────────────────
SUCCESS_BG = "#ECFDF5"
SUCCESS_BORDER = "#A7F3D0"
SUCCESS_TEXT = "#065F46"
WARNING_BG = "#FFFBEB"
WARNING_BORDER = "#FDE68A"
WARNING_TEXT = "#92400E"
DANGER_BG = "#FEF2F2"
DANGER_BORDER = "#FECACA"
DANGER_TEXT = "#991B1B"
INFO_BG = "#EFF6FF"
INFO_BORDER = "#BFDBFE"
INFO_TEXT = "#1D4ED8"

# ── Typography ─────────────────────────────────────────────────────────────────
FONT_SERIF = "Georgia, 'Times New Roman', serif"
FONT_SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

# ── Layout ─────────────────────────────────────────────────────────────────────
CONTAINER_WIDTH = 600
RADIUS = "8px"
RADIUS_SM = "4px"
RADIUS_PILL = "100px"

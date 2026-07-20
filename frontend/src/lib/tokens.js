/**
 * Synaptiq Design System V3 — Complete Design Token Library
 *
 * Single source of truth for all design decisions. This file and
 * `src/index.css`'s `:root` custom properties are ONE system expressed
 * through two mechanisms (inline-style components read the JS constants
 * below; Tailwind-className components read the matching `--sq-*` CSS
 * variables). The numeric scale is identical in both places — if you add
 * or change a value here, mirror it in index.css's token registry, and
 * vice versa. Never hardcode a color, spacing value, radius, shadow, or
 * animation outside this pairing.
 *
 * Usage:
 *   import { NAVY, TYPE, MOTION, Z, SPACE, ICON } from "@/lib/tokens";
 */

// ── Core palette ─────────────────────────────────────────────────────────────
export const NAVY         = "#0F2847";   // Primary identity — actions, headings
export const NAVY_LIGHT   = "#1a3a5c";   // Navy hover state
export const NAVY2        = "#0a1c34";   // Deeper navy — sidebar, focus (= --sq-navy-800)
export const ACCENT       = "#8A1538";   // Secondary — important badges, CTAs
export const ACCENT_DIM   = "#6d102c";   // Accent hover state
export const EMERALD      = "#059669";   // Positive, success, verified
export const AMBER        = "#D97706";   // Warning, caution, near-limit
export const CRIMSON      = "#DC2626";   // Error, destructive — never decorative

// ── Secondary accents (charts, AI surfaces, non-brand semantic color) ────────
// Named so pages stop inventing their own one-off purple/teal per file.
export const VIOLET       = "#8B5CF6";   // AI-surface accent — Copilot, Agents, AI panels (= Chart.jsx's pre-existing palette entry)
export const VIOLET_BG    = "#F5F3FF";
export const VIOLET_TEXT  = "#6D28D9";
export const TEAL         = "#14B8A6";   // Secondary data-viz accent, distinct from EMERALD=success (= Chart.jsx's pre-existing palette entry)
export const TEAL_BG      = "#F0FDFA";
export const TEAL_TEXT    = "#0F766E";

// ── Surfaces ─────────────────────────────────────────────────────────────────
export const WARM         = "#F4F6FA";   // Main app page background
export const ADMIN_BG     = "#F1F5F9";   // Admin page background
export const WHITE        = "#FFFFFF";   // Card, modal, header surfaces
export const SURF2        = "#F8FAFC";   // Secondary surface, table row hover

// ── Borders ──────────────────────────────────────────────────────────────────
export const BRD          = "rgba(15,23,42,0.08)";  // Default border
export const BRDH         = "rgba(15,23,42,0.14)";  // Hover border
export const BRDX         = "#E4E8EF";              // Structural dividers
export const BRD_SOFT     = "rgba(15,23,42,0.06)";  // Internal card/list/table-row dividers, lighter than BRD

// ── Text hierarchy ────────────────────────────────────────────────────────────
export const TEXT_PRIMARY   = "#0f172a";   // Headings, values, critical text
export const TEXT_STRONG    = "#374151";   // Hover/active state on secondary text (between primary and secondary)
export const TEXT_SECONDARY = "#475569";   // Supporting text, labels
export const TEXT_TERTIARY  = "#64748b";   // Nav items, body copy, secondary labels (slate-500)
export const TEXT_MUTED     = "#94a3b8";   // Timestamps, placeholders, captions
export const TEXT_DISABLED  = "#cbd5e1";   // Disabled state text

// ── Shadows ──────────────────────────────────────────────────────────────────
// Mirrors index.css's --sq-shadow-* custom properties exactly — pick whichever
// consumption mechanism (inline style vs Tailwind `shadow-sq-*`) suits the file.
export const SHADOW_CARD       = "0 1px 3px rgba(15,23,42,0.05), 0 1px 2px rgba(15,23,42,0.03)";
export const SHADOW_CARD_HOVER = "0 4px 12px rgba(15,23,42,0.09), 0 2px 4px rgba(15,23,42,0.04)";
export const SHADOW_MODAL      = "0 16px 48px rgba(15,23,42,0.18), 0 4px 16px rgba(15,23,42,0.08)";
export const SHADOW_DROPDOWN   = "0 4px 16px rgba(15,23,42,0.10), 0 2px 6px rgba(15,23,42,0.05)";
export const SHADOW_SM         = "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.03)";

// ── Hero section (full-bleed page header) ────────────────────────────────────
export const HERO_STYLE = {
  margin:       "-24px -24px 0",
  padding:      "20px 24px 0",
  background:   WHITE,
  borderBottom: `1px solid ${BRD}`,
};

// ── Radii ─────────────────────────────────────────────────────────────────────
export const RADIUS_BASE = "6px";   // Cards, inputs, buttons, tags
export const RADIUS_PILL = "100px"; // Badges, pills, counts

// ── Spacing rhythm (8px grid) ────────────────────────────────────────────────
export const SPACE = {
  micro: "4px",
  xs:    "8px",
  sm:    "12px",
  md:    "16px",
  lg:    "24px",   // ← rhythm unit (page padding, section gaps)
  xl:    "32px",
  xl2:   "48px",
  xl3:   "64px",
};

// ── Convenience aliases ───────────────────────────────────────────────────────
/** @deprecated use BRD */
export const BORDER = BRD;

// ═══════════════════════════════════════════════════════════════════════════════
// V2 TOKEN EXTENSIONS — All additive; existing tokens above are unchanged.
// ═══════════════════════════════════════════════════════════════════════════════

// ── Navy tints (alpha) ────────────────────────────────────────────────────────
export const NAVY_04  = "rgba(15,40,71,0.04)";
export const NAVY_06  = "rgba(15,40,71,0.06)";
export const NAVY_08  = "rgba(15,40,71,0.08)";
export const NAVY_12  = "rgba(15,40,71,0.12)";
export const NAVY_20  = "rgba(15,40,71,0.20)";
export const NAVY_40  = "rgba(15,40,71,0.40)";

// ── Accent tints ──────────────────────────────────────────────────────────────
export const ACCENT_05  = "rgba(138,21,56,0.05)";
export const ACCENT_10  = "rgba(138,21,56,0.10)";
export const ACCENT_20  = "rgba(138,21,56,0.20)";

// ── Semantic state colors ─────────────────────────────────────────────────────
// Mirrors index.css's --sq-success-*/--sq-warning-*/--sq-danger-*/--sq-info-*
// exactly — the ONE success/warning/danger/info palette. Every component
// with a status variant (Alert, Banner, Callout, Badge…) reads from here.
export const SUCCESS        = "#059669";  // = EMERALD
export const SUCCESS_BG     = "#ECFDF5";
export const SUCCESS_TEXT   = "#065F46";
export const SUCCESS_BORDER = "#A7F3D0";
export const WARNING_BG     = "#FFFBEB";
export const WARNING_TEXT   = "#92400E";
export const WARNING_BORDER = "#FDE68A";
export const DANGER_BG      = "#FEF2F2";
export const DANGER_TEXT    = "#991B1B";
export const DANGER_BORDER  = "#FECACA";
export const INFO           = "#3B82F6";
export const INFO_BG        = "#EFF6FF";
export const INFO_TEXT      = "#1D4ED8";
export const INFO_BORDER    = "#BFDBFE";

// ── Named chart palette ───────────────────────────────────────────────────────
// Import this instead of hardcoding a per-file color list for charts/legends.
export const CHART_PALETTE = [NAVY, EMERALD, AMBER, INFO, CRIMSON, VIOLET, TEAL];

// ── Extended shadow scale ────────────────────────────────────────────────────
// 5-step elevation scale, values identical to index.css's --sq-shadow-xs…xl.
export const SHADOW_XS  = "0 1px 2px rgba(15,23,42,0.04)";
export const SHADOW_MD  = "0 2px 8px rgba(15,23,42,0.08), 0 1px 3px rgba(15,23,42,0.04)";
export const SHADOW_LG  = "0 4px 16px rgba(15,23,42,0.10), 0 2px 6px rgba(15,23,42,0.05)";
export const SHADOW_XL  = "0 8px 28px rgba(15,23,42,0.12), 0 4px 12px rgba(15,23,42,0.06)";
export const SHADOW_2XL = "0 20px 60px rgba(15,23,42,0.18), 0 6px 20px rgba(15,23,42,0.08)"; // hero/marketing-scale only
export const SHADOW_FOCUS = "0 0 0 3px rgba(15,40,71,0.15)";

// ── Extended radius scale ─────────────────────────────────────────────────────
// Values identical to index.css's --sq-radius-xs…2xl.
export const RADIUS_XS   = "2px";
export const RADIUS_SM   = "4px";
export const RADIUS_MD   = "6px";   // = RADIUS_BASE
export const RADIUS_LG   = "8px";
export const RADIUS_XL   = "10px";
export const RADIUS_2XL  = "14px";
export const RADIUS_3XL  = "20px";  // hero/marketing-scale only — no CSS var equivalent
export const RADIUS_FULL = "9999px";

// ── Font families ─────────────────────────────────────────────────────────────
// FONT_SANS is the app-wide brand face (matches index.css's global h1–h6 rule
// and body font — Notion/Linear/Stripe-style clean grotesk, not serif).
// FONT_SERIF is reserved for marketing/editorial surfaces only (index.css's
// `.marketing-page` scope) — never use it in product UI/dashboard chrome.
export const FONT_SANS  = "'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', sans-serif";
export const FONT_SERIF = "'Merriweather', Georgia, 'Times New Roman', serif";
export const FONT_MONO  = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

// ── Typography scale ──────────────────────────────────────────────────────────
// Each entry is a style object you can spread into React's style prop.
export const TYPE = {
  // ── Display (hero, landing) ──────────────────────────────────────────────
  display: {
    fontFamily:    FONT_SANS,
    fontSize:      "clamp(2.25rem, 5vw, 3.5rem)",
    fontWeight:    700,
    lineHeight:    1.08,
    letterSpacing: "-0.045em",
    color:         "#0f172a",
  },

  // ── Page headings ────────────────────────────────────────────────────────
  h1: {
    fontFamily:    FONT_SANS,
    fontSize:      "clamp(1.5rem, 3vw, 2rem)",
    fontWeight:    700,
    lineHeight:    1.15,
    letterSpacing: "-0.035em",
    color:         "#0f172a",
  },
  h2: {
    fontFamily:    FONT_SANS,
    fontSize:      "clamp(1.15rem, 2.5vw, 1.5rem)",
    fontWeight:    700,
    lineHeight:    1.2,
    letterSpacing: "-0.025em",
    color:         "#0f172a",
  },
  h3: {
    fontSize:      "1.125rem",
    fontWeight:    600,
    lineHeight:    1.3,
    letterSpacing: "-0.015em",
    color:         "#0f172a",
  },
  h4: {
    fontSize:      "0.9375rem",
    fontWeight:    600,
    lineHeight:    1.4,
    letterSpacing: "-0.01em",
    color:         "#0f172a",
  },

  // ── Section label (uppercase overline) ──────────────────────────────────
  section: {
    fontSize:      "0.6875rem",
    fontWeight:    700,
    lineHeight:    1.3,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color:         "#94a3b8",
  },

  // ── Body copy ────────────────────────────────────────────────────────────
  bodyLg: {
    fontSize:   "1rem",
    fontWeight: 400,
    lineHeight: 1.65,
    color:      "#475569",
  },
  body: {
    fontSize:   "0.875rem",
    fontWeight: 400,
    lineHeight: 1.6,
    color:      "#475569",
  },
  bodySm: {
    fontSize:   "0.8125rem",
    fontWeight: 400,
    lineHeight: 1.55,
    color:      "#475569",
  },

  // ── Utility text ─────────────────────────────────────────────────────────
  caption: {
    fontSize:   "0.75rem",
    fontWeight: 400,
    lineHeight: 1.5,
    color:      "#94a3b8",
  },
  label: {
    fontSize:      "0.6875rem",
    fontWeight:    700,
    lineHeight:    1.3,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
    color:         "#94a3b8",
  },
  meta: {
    fontSize:      "0.625rem",
    fontWeight:    500,
    lineHeight:    1.3,
    letterSpacing: "0.04em",
    color:         "#94a3b8",
  },

  // ── Numeric display ──────────────────────────────────────────────────────
  number: {
    fontFamily:         FONT_SERIF,
    fontSize:           "1.5rem",
    fontWeight:         700,
    lineHeight:         1.1,
    letterSpacing:      "-0.03em",
    fontVariantNumeric: "tabular-nums",
    color:              "#0f172a",
  },
  numberLg: {
    fontFamily:         FONT_SERIF,
    fontSize:           "2.5rem",
    fontWeight:         700,
    lineHeight:         1,
    letterSpacing:      "-0.04em",
    fontVariantNumeric: "tabular-nums",
    color:              "#0f172a",
  },
  numberSm: {
    fontVariantNumeric: "tabular-nums",
    fontSize:           "1rem",
    fontWeight:         700,
    lineHeight:         1.2,
    letterSpacing:      "-0.02em",
    color:              "#0f172a",
  },
};

// ── Motion system ─────────────────────────────────────────────────────────────
export const MOTION = {
  // Durations
  instant: "75ms",
  fast:    "120ms",
  base:    "150ms",    // ← default for hover states
  smooth:  "200ms",
  enter:   "250ms",
  exit:    "150ms",
  slow:    "350ms",

  // Easings
  ease:    "cubic-bezier(0.16, 1, 0.3, 1)",       // general purpose
  easeIn:  "cubic-bezier(0.4, 0, 1, 1)",          // element leaving
  easeOut: "cubic-bezier(0, 0, 0.2, 1)",          // element entering
  spring:  "cubic-bezier(0.34, 1.56, 0.64, 1)",   // playful bounce
  snappy:  "cubic-bezier(0.2, 0, 0, 1)",          // Linear-style fast settle

  // Transition presets (ready to use in style={{ transition: ... }})
  hoverBase:   "border-color 150ms ease, box-shadow 150ms ease",
  hoverCard:   "border-color 150ms ease, box-shadow 150ms ease, transform 120ms ease",
  hoverButton: "opacity 120ms ease, background 150ms ease",
  fade:        "opacity 200ms cubic-bezier(0.16, 1, 0.3, 1)",
  slideUp:     "transform 200ms cubic-bezier(0.16, 1, 0.3, 1), opacity 200ms cubic-bezier(0.16, 1, 0.3, 1)",
};

// ── Z-index scale ─────────────────────────────────────────────────────────────
export const Z = {
  base:      0,
  raised:    10,
  sticky:    20,
  banner:    30,
  dropdown:  100,
  overlay:   200,
  modal:     300,
  toast:     400,
  tooltip:   500,
};

// ── Breakpoints (px) ─────────────────────────────────────────────────────────
export const BP = {
  sm:  640,
  md:  768,
  lg:  1024,
  xl:  1280,
  xl2: 1536,
};

// ── Icon system ───────────────────────────────────────────────────────────────
// All icons in Synaptiq must use these sizes and stroke widths.
export const ICON = {
  xs:  { size: 12, strokeWidth: 2 },
  sm:  { size: 14, strokeWidth: 1.75 },
  md:  { size: 16, strokeWidth: 1.75 },
  lg:  { size: 20, strokeWidth: 1.5 },
  xl:  { size: 24, strokeWidth: 1.5 },
};

// ── Global shell chrome ───────────────────────────────────────────────────────
// The one set of dimensions for the app shell — Sidebar, TopNav, and the page
// container every page renders inside. Mirrors index.css's --sq-header-height /
// --sq-sidebar-width / --sq-sidebar-width-collapsed / --sq-container-max.
// Shared by both the "app" and "admin" Sidebar/TopNav variants so chrome never
// disagrees between the two shells again.
export const HEADER_H              = 56;   // px — TopNav height, both variants
export const SIDEBAR_W             = 232;  // px — Sidebar expanded, both variants
export const SIDEBAR_W_COLLAPSED   = 56;   // px — Sidebar collapsed, both variants
export const CONTAINER_MAX         = 1280; // px — the one page-container max-width (= max-w-7xl)

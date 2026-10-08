# Authenticated app design system

The signed-in product uses the same visual language as the public site and the Sign In screens (see `public-language.md` → Visual system). This page records how that language maps onto product UI. The app is a workspace, so it is slightly denser than the public site.

## Where it lives

| Layer | File |
|---|---|
| Tokens (CSS) | `frontend/src/index.css` `:root` (`--sq-*`), mirrored by `tailwind.config.js` |
| Tokens (JS, inline styles) | `frontend/src/lib/tokens.js` |
| Shell | `components/layout/AppShell.jsx`, `components/ds/Sidebar.jsx`, `components/ds/TopNav.jsx`, `components/ds/ContentFrame.jsx` |
| Page header + layout | `components/ds/PageLayout.jsx` (used by every `layouts/*Layout`) |
| Primitives | `components/ds/*` (Button, Input, Textarea, FormSelect, EmptyState, StatCard/StatGrid, Badge, Modal, Drawer, DataTable…) |

## Colour

| Role | Value |
|---|---|
| Brand / primary action | `--sq-brand-navy` `#0F2847`; hover `--sq-brand-navy-deep` `#0A1C34` |
| Brand tints | navy-50 `#EEF2F8`, navy-100 `#D4DDE9`, navy-500 `#2F5486` (secondary marks, AI surfaces) |
| Page surface | `--sq-bg` `#FBFAF7` (= public `--paper`); cards `#FFFFFF`; secondary surface `#F6F5F1` |
| Text | `#10141C` primary, `#3A4250` secondary, `#5F6673` tertiary/muted; the lightest text colour allowed on white or paper is `#6B717D` (Tailwind `slate-400`/`slate-300` are lifted to it inside `main`) |
| Borders | `rgba(16,20,28,0.10)` default, `0.18` strong |
| Semantic | success green, warning amber `#B45309`, danger `#B42318`: destructive actions, errors, failed/rejected states, critical risk and failing grades only. Never use the brand navy to mean "bad". |
| Info | the navy family, not a separate blue |
| Data visualisation | `CHART_PALETTE` keeps distinct hues; nothing else does |

There is no second brand colour. The former burgundy accent, the violet "AI" accent and decorative cyan/sky/blue/pink are the navy family. Categories (activity types, roles, modes, recommendation types, search types) are labels, not status: they use navy, not green/amber/red.

## Type

- Page titles: Newsreader (serif), 400, `clamp(1.6rem, 2.4vw, 2rem)` — `.pl-hero-title`. The `.pl-*` title classes are global (`index.css`), so standalone states (access gates, payment results, onboarding, the AI workspace) use the same title.
- Eyebrow above a title: monospace, 11px, uppercase, navy — `.pl-eyebrow`.
- Section headings: sans 600, 1rem — `.sq-h2`; subsections 0.875rem — `.sq-h3`.
- Everything operational (navigation, forms, tables, buttons, metadata): Plus Jakarta Sans.
- Numbers in metrics: Newsreader 400, tabular.
- Text is left-aligned. No justification in the app.

## Shape and spacing

- Buttons, inputs, selects: 4px radius. Cards: 6px. Overlays: 8px. Pills only for counts.
- Content frame: 1280px max; padding 24px (phones), 24px (tablet), 28px/40px (≥1280px).
- Page header: title row, optional metrics row, one rule beneath; 20px below.

## Components

- **Button**: `primary` (navy; one per view), `secondary` (white, hairline border; `ghost`/`outline`/`hero` alias it), `subtle`, `link`, `danger`, `danger-outline` (a destructive action that is not the page's main action, e.g. Delete in a header). Never override a Button's background inline.
- **Page header** (`PageLayout`): no banner. Actions on the right; the page's main action (New / Create / Post / Add / Start…) is `variant="primary"`, others secondary. The metrics row hides values that failed to load and the whole row when every value is zero (`0`, `0%`, `+0%`, `0/0`, `0h`, `€0`, `—`). A page with its own greeting passes it as `header`.
- **Side columns** (`sidebar=`): only when they hold something the person can act on. A side column that only repeats counts, or is empty, is not rendered.
- **StatCard / StatGrid**: quiet cards; a grid of all-empty metrics renders nothing. `StatCard` marks itself `.sq-stat.is-empty`, and any wrapper whose children are all empty stat cards is hidden by CSS.
- **EmptyState**: compact and left-aligned — what is empty, why, what to do next; no dashed placeholder boxes.
- **Errors**: show what happened and what to do; never raw backend output (`safeErrorMessage`). Missing records show a "not available" state with a way back, never an endless skeleton: the API client emits `synaptiq:record-missing` for a GET 404/403, and `ContentFrame` replaces the page with `NotAvailable` when the failed URL ends with the route's own record id.
- **Upgrade states** (`RouteEntitlementGate`): name the plan the person has and what the required plan adds; never make a locked feature look available.

## Credits

One global indicator: the sidebar credit block (total available, plan, monthly/purchased split, renewal). The top bar and page headers do not repeat it. Every credit-consuming action shows its cost at the action, read from the server catalogue (`components/billing/creditCatalogue.js` → `loadCreditCatalogue()`, e.g. `ai_os_message`, `ai_marketplace_rerank`). Never hard-code a price or an estimate ("~12 cr"); while the catalogue loads, show the action without a number.

## People and matching

Synaptiq does not show match percentages for people. Search, recommendations, reviewer and mentor lists, team builders and collaboration intelligence rank people by relevance and explain the ranking with evidence (shared topics, complementary methods, "Why they may fit"), never a score, ring, bar or per-dimension percentage. Scores for things — journals, grants, venues, projects — may still be shown.

## Responsive

Below 640px fixed multi-column grids collapse to two columns, tab rows scroll inside themselves, button and chip rows wrap, flexible columns keep a readable minimum width, and in-page sidebars stack. Messages shows one pane at a time below 1024px.

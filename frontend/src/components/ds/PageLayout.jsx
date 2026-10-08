/* eslint-disable */
import React from "react";
import { BRD, WHITE, TEXT_PRIMARY } from "@/lib/tokens";
import { HeroRing } from "@/components/ds/HeroRing";

/**
 * PageLayout — the single universal page shell.
 *
 * Replaces all 11 layouts in src/layouts/:
 *   DashboardLayout, WorkspaceLayout, ResearchLayout, AnalyticsLayout,
 *   SettingsLayout, ProfileLayout, AIWorkspaceLayout, InstitutionLayout,
 *   AdministrationLayout, DiscoveryLayout, ArtifactLayout
 *
 * Props:
 *   title        string       page heading
 *   subtitle     string       page sub-heading
 *   eyebrow      string       small label above title
 *   icon         ReactNode    accepted for compatibility; headers no longer show a decorative icon
 *   actions      ReactNode    right side of hero bar
 *   stats        [{label,value}]  optional key-numbers ribbon under the hero — only
 *                              render when the page has real numbers to show
 *   ring         {value,max,label,color}  optional circular score/progress indicator
 *                              (HeroRing) shown right of actions — only for pages with
 *                              a real score (Trust Score, Reputation, Credits...)
 *   nav          ReactNode    tab row below hero (NavTabs)
 *   toolbar      ReactNode    tool row below nav
 *   banner       ReactNode    full-width alert / briefing bar
 *   aside        ReactNode    side panel content
 *   asideWidth   number       px width of side panel (default 320)
 *   asideLeft    boolean      put aside on left instead of right
 *   customHero   ReactNode    replaces entire hero bar (escape hatch for Profile/Artifact)
 *   header       ReactNode    a custom header built from the pl-* classes (e.g. Today)
 *   split        boolean      full-height split-pane mode (workspace/editor)
 *   noPad        boolean      skip content-area vertical padding
 *   children     ReactNode    main content
 */
/* A metrics row earns its space only when it carries information. Values
   that failed to load ("undefined", NaN) are never shown; when every
   remaining value is empty or zero the row is left out rather than shown as
   a row of zeros. */
const BROKEN = /undefined|NaN|null/;
const isBlank = (v) => {
  if (v === null || v === undefined) return true;
  if (typeof v === "object") return false;
  const t = String(v).trim();
  return t === "" || t === "—" || t === "-" || BROKEN.test(t);
};
const isZero = (v) => ["0", "0%", "+0%", "+0", "0.0", "0/0", "0h", "€0", "$0", "$0.00", "€0k"].includes(String(v).trim());
function cleanStats(stats) {
  if (!stats || !stats.length) return [];
  const shown = stats.filter((s) => s && !isBlank(s.value));
  return shown.some((s) => typeof s.value === "object" || !isZero(s.value)) ? shown : [];
}
const visibleStats = (stats) => cleanStats(stats).length > 0;

export function PageLayout({
  title,
  subtitle,
  eyebrow,
  icon,
  actions,
  stats,
  ring,
  nav,
  toolbar,
  banner,
  aside,
  asideWidth = 320,
  asideLeft = false,
  split = false,
  noPad = false,
  customHero,
  header,
  children,
}) {
  // The light header has no icon slot: an icon alone does not make a header.
  const hasHero = customHero || title || eyebrow || actions;

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: 0, flex: 1 }}>
      {/* Responsive aside: fixed-width side column on desktop, stacked full-width
          panel (capped height, scrollable) on narrow viewports — mirrors the
          collapse-to-stack pattern used by the primary Sidebar/MobileDrawer. */}
      <style>{`
        .pl-aside-left, .pl-aside-right {
          width: var(--pl-aside-w, 320px);
          flex-shrink: 0;
          overflow-y: auto;
          background: transparent;
          padding: 20px 0 20px 24px;
        }
        .pl-aside-left { border-right: 1px solid ${BRD}; padding: 20px 24px 20px 0; }
        .pl-aside-right { border-left: 1px solid ${BRD}; }
        @media (max-width: 1023px) {
          .pl-body-row { flex-direction: column; }
          .pl-aside-left, .pl-aside-right {
            width: 100%;
            max-height: 45vh;
            border-right: none;
            border-left: none;
            border-bottom: 1px solid ${BRD};
            padding: 16px 0;
          }
        }
        .pl-head { padding: 8px 0 20px; margin-bottom: 4px; border-bottom: 1px solid ${BRD}; }
        .pl-hero-row { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px 24px; flex-wrap: wrap; }
        .pl-hero-row > :first-child { flex: 1 1 20rem; }
        .pl-hero-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .pl-stats { display: flex; flex-wrap: wrap; gap: 8px 0; margin: 18px 0 0; padding: 0; }
        .pl-stats > div { padding: 0 24px; border-left: 1px solid ${BRD}; min-width: 0; }
        .pl-stats > div:first-child { padding-left: 0; border-left: none; }
        .pl-stats dd { margin: 0; font-family: 'Newsreader Variable', 'Newsreader', Georgia, serif; font-size: 22px; line-height: 1.1; color: ${TEXT_PRIMARY}; font-variant-numeric: tabular-nums; }
        .pl-stats dt { margin-top: 2px; font-size: 11px; letter-spacing: 0.04em; color: var(--sq-text-tertiary); }
        @media (max-width: 639px) {
          .pl-hero-row { align-items: flex-start; }
          .pl-hero-actions { width: 100%; }
          .pl-stats > div { padding: 0 16px; }
        }
      `}</style>

      {/* ── Page header ── the product page header shared by every page:
          eyebrow, serif title, one short line, actions on the right, and an
          optional quiet metrics row. It sits on the page surface (no banner),
          separated from the content by a single rule, like the public site's
          sections. customHero (Profile/Artifact) keeps its own band. */}
      {/* header: a page-specific header node in the shared pl-* language */}
      {header}
      {hasHero && customHero && (
        <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 6, overflow: "hidden", marginBottom: 8 }}>
          {customHero}
        </div>
      )}
      {hasHero && !customHero && (
        <header className="pl-head">
          <div className="pl-hero-row">
            <div style={{ minWidth: 0, flex: 1 }}>
              {eyebrow && <p className="pl-eyebrow">{eyebrow}</p>}
              {title && <h1 className="pl-hero-title">{title}</h1>}
              {subtitle && <p className="pl-sub">{subtitle}</p>}
            </div>
            {(actions || ring) && (
              <div style={{ display: "flex", alignItems: "center", gap: 16, flexShrink: 1, minWidth: 0, maxWidth: "100%" }}>
                {actions && <div className="pl-hero-actions">{actions}</div>}
                {ring && <HeroRing {...ring} />}
              </div>
            )}
          </div>
          {visibleStats(stats) && (
            <dl className="pl-stats">
              {cleanStats(stats).map((s) => (
                <div key={s.label}>
                  <dd>{s.value}</dd>
                  <dt>{s.label}</dt>
                </div>
              ))}
            </dl>
          )}
        </header>
      )}

      {/* ── Banner (full-width alert / AI briefing) */}
      {banner && (
        <div style={{ marginTop: 16 }}>
          {banner}
        </div>
      )}

      {/* ── Nav tabs */}
      {nav && (
        <div style={{ borderBottom: `1px solid ${BRD}`, marginTop: 4 }}>
          {nav}
        </div>
      )}

      {/* ── Toolbar */}
      {toolbar && (
        <div style={{
          padding: "10px 0",
          borderBottom: `1px solid ${BRD}`,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}>
          {toolbar}
        </div>
      )}

      {/* ── Body */}
      <div className="pl-body-row" style={{
        flex: 1,
        display: "flex",
        minHeight: 0,
        overflow: split ? "hidden" : undefined,
      }}>
        {/* Left aside */}
        {asideLeft && aside && (
          <aside className="pl-aside-left" style={{ "--pl-aside-w": `${asideWidth}px` }}>
            {aside}
          </aside>
        )}

        {/* Main content */}
        <div style={{
          flex: 1,
          minWidth: 0,
          overflowY: split ? "auto" : undefined,
          padding: noPad ? 0 : (split ? "24px" : "24px 0"),
        }}>
          {children}
        </div>

        {/* Right aside */}
        {!asideLeft && aside && (
          <aside className="pl-aside-right" style={{ "--pl-aside-w": `${asideWidth}px` }}>
            {aside}
          </aside>
        )}
      </div>
    </div>
  );
}

export default PageLayout;

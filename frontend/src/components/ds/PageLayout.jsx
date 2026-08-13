/* eslint-disable */
import React from "react";
import {
  NAVY, NAVY2, BRD, WHITE, WARM,
  TEXT_PRIMARY, TEXT_MUTED,
  NAVY_06, RADIUS_MD,
} from "@/lib/tokens";
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
 *   icon         ReactNode    icon rendered left of title
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
 *   split        boolean      full-height split-pane mode (workspace/editor)
 *   noPad        boolean      skip content-area vertical padding
 *   children     ReactNode    main content
 */
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
  children,
}) {
  const hasHero = customHero || title || eyebrow || actions || icon;

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
          background: ${WARM};
          padding: 20px;
        }
        .pl-aside-left { border-right: 1px solid ${BRD}; }
        .pl-aside-right { border-left: 1px solid ${BRD}; }
        @media (max-width: 1023px) {
          .pl-body-row { flex-direction: column; }
          .pl-aside-left, .pl-aside-right {
            width: 100%;
            max-height: 45vh;
            border-right: none;
            border-left: none;
            border-bottom: 1px solid ${BRD};
          }
        }
        /* Hero row: title + actions share one line on desktop; below sm they
           stack so the title never gets crushed into an ellipsis. */
        @media (max-width: 639px) {
          .pl-hero-row { flex-wrap: wrap; }
          .pl-hero-title {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
          }
          .pl-hero-actions { width: 100%; }
        }
      `}</style>

      {/* ── Hero ── standard hero is an inset navy card (matches Academic Passport /
          Billing's "Current Plan" card); customHero (Profile/Artifact/Home) keeps the
          old full-bleed white band and paints its own background internally. */}
      {hasHero && (
        <div style={{
          margin: customHero ? "0 -24px" : "4px 0 20px",
          padding: customHero ? 0 : "26px 28px 22px",
          borderRadius: customHero ? 0 : 16,
          background: customHero ? WHITE : `linear-gradient(135deg, ${NAVY} 0%, ${NAVY2} 100%)`,
          borderBottom: customHero ? `1px solid ${BRD}` : "none",
          boxSizing: "border-box",
          overflow: "hidden",
        }}>
          {/* Custom hero override — used by ProfileLayout, ArtifactLayout */}
          {customHero}

          {/* Standard hero */}
          {!customHero && eyebrow && (
            <p style={{
              margin: "0 0 6px",
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "rgba(255,255,255,0.55)",
            }}>
              {eyebrow}
            </p>
          )}
          {!customHero && <div className="pl-hero-row" style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 16,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0, flex: 1 }}>
              {icon && (
                <div style={{
                  width: 44, height: 44, borderRadius: "50%", flexShrink: 0,
                  background: "rgba(255,255,255,0.12)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {/* Callers hardcode icon color for the old white hero (usually NAVY) —
                      force it white here so it stays legible on the new navy background
                      without having to touch every caller's icon color. */}
                  <span style={{ display: "flex", filter: "brightness(0) invert(1)" }}>
                    {icon}
                  </span>
                </div>
              )}
              <div style={{ minWidth: 0 }}>
                {title && (
                  <h1 className="pl-hero-title" style={{
                    margin: 0,
                    fontSize: 19,
                    fontWeight: 700,
                    color: WHITE,
                    letterSpacing: "-0.02em",
                    lineHeight: 1.3,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}>
                    {title}
                  </h1>
                )}
                {subtitle && (
                  <p style={{ margin: "3px 0 0", fontSize: 12.5, color: "rgba(255,255,255,0.65)", lineHeight: 1.4 }}>
                    {subtitle}
                  </p>
                )}
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 20, flexShrink: 0 }}>
              {actions && (
                <div className="pl-hero-actions" style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                  {actions}
                </div>
              )}
              {ring && <HeroRing {...ring} />}
            </div>
          </div>}

          {/* Optional key-numbers ribbon — only rendered when the page passes real stats */}
          {!customHero && stats && stats.length > 0 && (
            <div
              className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-7 divide-x divide-y lg:divide-y-0 divide-white/10"
              style={{ marginTop: 22, marginLeft: -28, marginRight: -28, marginBottom: -22, background: "rgba(0,0,0,0.18)", borderTop: "1px solid rgba(255,255,255,0.1)" }}
            >
              {stats.map((s) => (
                <div key={s.label} style={{ padding: "14px 10px", textAlign: "center", minWidth: 0 }}>
                  <div style={{ fontFamily: "Georgia, serif", fontSize: 19, fontWeight: 700, color: WHITE }}>{s.value}</div>
                  <div style={{ fontSize: 9.5, color: "rgba(255,255,255,0.55)", textTransform: "uppercase", letterSpacing: "0.05em", marginTop: 3 }}>{s.label}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Banner (full-width alert / AI briefing) */}
      {banner && (
        <div style={{ margin: "0 -24px", borderBottom: `1px solid ${BRD}` }}>
          {banner}
        </div>
      )}

      {/* ── Nav tabs */}
      {nav && (
        <div style={{
          margin: "0 -24px",
          padding: "0 24px",
          background: WHITE,
          borderBottom: `1px solid ${BRD}`,
        }}>
          {nav}
        </div>
      )}

      {/* ── Toolbar */}
      {toolbar && (
        <div style={{
          margin: "0 -24px",
          padding: "8px 24px",
          background: WHITE,
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

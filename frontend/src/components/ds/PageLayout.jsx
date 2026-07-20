/* eslint-disable */
import React from "react";
import {
  NAVY, BRD, WHITE, WARM,
  TEXT_PRIMARY, TEXT_MUTED,
  NAVY_06, RADIUS_MD,
} from "@/lib/tokens";

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

      {/* ── Hero ── bleeds to AppShell container edges */}
      {hasHero && (
        <div style={{
          margin: "0 -24px",
          padding: customHero ? 0 : "16px 24px 18px",
          background: WHITE,
          borderBottom: `1px solid ${BRD}`,
        }}>
          {/* Custom hero override — used by ProfileLayout, ArtifactLayout */}
          {customHero}

          {/* Standard hero */}
          {!customHero && eyebrow && (
            <p style={{
              margin: "0 0 5px",
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: TEXT_MUTED,
            }}>
              {eyebrow}
            </p>
          )}
          {!customHero && <div className="pl-hero-row" style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
              {icon && (
                <div style={{
                  width: 32, height: 32, borderRadius: RADIUS_MD, flexShrink: 0,
                  background: NAVY_06,
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {icon}
                </div>
              )}
              <div style={{ minWidth: 0 }}>
                {title && (
                  <h1 className="pl-hero-title" style={{
                    margin: 0,
                    fontSize: 15,
                    fontWeight: 700,
                    color: TEXT_PRIMARY,
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
                  <p style={{ margin: "2px 0 0", fontSize: 12, color: TEXT_MUTED, lineHeight: 1.4 }}>
                    {subtitle}
                  </p>
                )}
              </div>
            </div>
            {actions && (
              <div className="pl-hero-actions" style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                {actions}
              </div>
            )}
          </div>}
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

import React from "react";
import { Link } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import {
  NAVY,
  BRD,
  WHITE,
  TEXT_SECONDARY,
  TEXT_MUTED,
  HERO_STYLE,
} from "@/lib/tokens";

/**
 * PageHeader — workspace page header with full-bleed layout.
 *
 * Slots:
 *   title            string     — large serif title (required)
 *   subtitle         string     — supporting description
 *   icon             ReactNode  — icon shown left of title (16×16 container)
 *   actions          ReactNode  — primary CTA (rightmost)
 *   secondaryActions ReactNode  — secondary CTAs (left of primary)
 *   meta             ReactNode  — badge/stat row below title
 *   nav              ReactNode  — sub-nav tabs (NavTabs or custom)
 *   back             { to, label } — back link above title
 */
export function PageHeader({
  title,
  subtitle,
  icon,
  actions,
  secondaryActions,
  meta,
  nav,
  back,
}) {
  const hasBottom = meta != null || nav != null;

  return (
    <header
      style={{
        ...HERO_STYLE,
        // HERO_STYLE bleeds to full width via margin: -24px -24px 0
        // padding: 20px 24px 0 — we control bottom padding per zone
      }}
    >
      {/* Back link */}
      {back && (
        <Link
          to={back.to}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
            fontSize: "0.72rem",
            color: TEXT_MUTED,
            textDecoration: "none",
            marginBottom: 10,
            letterSpacing: "0.01em",
            transition: "color 120ms ease",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = NAVY)}
          onMouseLeave={(e) => (e.currentTarget.style.color = TEXT_MUTED)}
        >
          <ChevronLeft size={12} strokeWidth={2.5} />
          {back.label || "Back"}
        </Link>
      )}

      {/* Title row */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 20,
          paddingBottom: hasBottom ? 12 : 20,
        }}
      >
        {/* Left: icon + title + subtitle */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, minWidth: 0 }}>
          {icon && (
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 7,
                background: "rgba(15,40,71,0.06)",
                border: `1px solid ${BRD}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                marginTop: 3,
              }}
            >
              {React.isValidElement(icon)
                ? React.cloneElement(icon, { size: 16, color: NAVY, strokeWidth: 1.75 })
                : icon}
            </div>
          )}

          <div style={{ minWidth: 0 }}>
            <h1
              style={{
                fontFamily: "Georgia, 'Times New Roman', serif",
                fontSize: "clamp(1.15rem, 2vw, 1.4rem)",
                fontWeight: 700,
                color: NAVY,
                letterSpacing: "-0.025em",
                lineHeight: 1.2,
                margin: 0,
                textWrap: "balance",
              }}
            >
              {title}
            </h1>

            {subtitle && (
              <p
                style={{
                  fontSize: "0.8rem",
                  color: TEXT_SECONDARY,
                  marginTop: 4,
                  lineHeight: 1.5,
                  maxWidth: 580,
                  margin: "4px 0 0",
                }}
              >
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {/* Right: secondary + primary actions */}
        {(actions || secondaryActions) && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexShrink: 0,
              paddingTop: 2,
            }}
          >
            {secondaryActions && (
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {secondaryActions}
              </div>
            )}
            {actions}
          </div>
        )}
      </div>

      {/* Meta row — badges, stats */}
      {meta && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            flexWrap: "wrap",
            paddingBottom: nav ? 12 : 16,
          }}
        >
          {meta}
        </div>
      )}

      {/* Sub-navigation tabs */}
      {nav && (
        <div style={{ marginTop: meta ? 0 : 4 }}>
          {nav}
        </div>
      )}
    </header>
  );
}

export default PageHeader;

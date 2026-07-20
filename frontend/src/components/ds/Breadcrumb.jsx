/* eslint-disable */
import React from "react";
import { Link } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";
import { TEXT_PRIMARY, TEXT_MUTED, NAVY } from "@/lib/tokens";

// ── Breadcrumb ────────────────────────────────────────────────────────────────
/**
 * Breadcrumb — horizontal path navigation.
 *
 * Array-based API (preferred):
 *   <Breadcrumb items={[{ label: "Home", to: "/" }, { label: "Research" }]} />
 *
 * Props:
 *   items      [{ label, to?, icon? }]   last item is current page (no link)
 *   showHome   bool   prepend a home icon item
 *   size       "sm"|"md"   default "md"
 */
export function Breadcrumb({ items = [], showHome = false, size = "md", style }) {
  const fontSize = size === "sm" ? "0.75rem" : "0.8125rem";
  const allItems = showHome ? [{ label: "Home", to: "/", icon: Home }, ...items] : items;

  return (
    <nav aria-label="Breadcrumb" style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap", ...style }}>
      {allItems.map((item, i) => {
        const isLast = i === allItems.length - 1;
        const Icon = item.icon;

        return (
          <React.Fragment key={i}>
            {i > 0 && (
              <ChevronRight size={12} style={{ color: TEXT_MUTED, flexShrink: 0 }} aria-hidden="true" />
            )}

            {isLast || !item.to ? (
              <span
                style={{
                  display: "inline-flex", alignItems: "center", gap: 4,
                  fontSize,
                  fontWeight: isLast ? 600 : 400,
                  color: isLast ? TEXT_PRIMARY : TEXT_MUTED,
                }}
                aria-current={isLast ? "page" : undefined}
              >
                {Icon && <Icon size={12} aria-hidden="true" />}
                {item.label}
              </span>
            ) : (
              <BreadcrumbLink to={item.to} fontSize={fontSize} Icon={Icon}>
                {item.label}
              </BreadcrumbLink>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}

function BreadcrumbLink({ to, fontSize, Icon, children }) {
  const [hov, setHov] = React.useState(false);

  return (
    <Link
      to={to}
      style={{
        display: "inline-flex", alignItems: "center", gap: 4,
        fontSize,
        fontWeight: 400,
        color: hov ? NAVY : TEXT_MUTED,
        textDecoration: "none",
        transition: "color 100ms",
      }}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
    >
      {Icon && <Icon size={12} aria-hidden="true" />}
      {children}
    </Link>
  );
}

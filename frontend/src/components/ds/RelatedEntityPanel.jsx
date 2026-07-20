import React from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { BRD, BRDX, WHITE, TEXT_PRIMARY, TEXT_MUTED, NAVY_06 } from "@/lib/tokens";

/**
 * RelatedEntityPanel — compact card exposing related-entity counts with
 * one-click navigation, so opening an object immediately shows what it's
 * connected to.
 *
 * Props:
 *   title   string   optional section heading
 *   items   [{ label, icon, count, to }]
 *   cols    number   grid columns (default 3)
 */
export function RelatedEntityPanel({ title = "Related", items = [], cols = 3 }) {
  if (items.length === 0) return null;

  return (
    <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 6, overflow: "hidden" }}>
      {title && (
        <div style={{ padding: "12px 16px", borderBottom: `1px solid ${BRD}` }}>
          <span style={{
            fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em",
            textTransform: "uppercase", color: TEXT_MUTED,
          }}>
            {title}
          </span>
        </div>
      )}
      <div style={{
        display: "grid",
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
      }}>
        {items.map((item, i) => {
          const Icon = item.icon;
          const inner = (
            <div
              style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "14px 16px",
                borderRight: (i + 1) % cols !== 0 ? `1px solid ${BRDX}` : "none",
                borderBottom: i < items.length - cols ? `1px solid ${BRDX}` : "none",
                cursor: item.to ? "pointer" : "default",
                transition: "background 100ms",
              }}
              onMouseEnter={item.to ? (e) => (e.currentTarget.style.background = NAVY_06) : undefined}
              onMouseLeave={item.to ? (e) => (e.currentTarget.style.background = "transparent") : undefined}
            >
              {Icon && (
                <div style={{
                  width: 30, height: 30, borderRadius: 6, background: NAVY_06,
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                }}>
                  <Icon size={13} strokeWidth={1.75} style={{ color: TEXT_MUTED }} />
                </div>
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: "1rem", fontWeight: 700, color: TEXT_PRIMARY, margin: 0, lineHeight: 1.2 }}>
                  {item.count ?? "—"}
                </p>
                <p style={{ fontSize: "0.72rem", color: TEXT_MUTED, margin: 0 }}>{item.label}</p>
              </div>
              {item.to && <ChevronRight size={13} style={{ color: TEXT_MUTED, flexShrink: 0 }} />}
            </div>
          );
          return item.to ? (
            <Link key={item.label} to={item.to} style={{ textDecoration: "none", color: "inherit" }}>
              {inner}
            </Link>
          ) : (
            <div key={item.label}>{inner}</div>
          );
        })}
      </div>
    </div>
  );
}

export default RelatedEntityPanel;

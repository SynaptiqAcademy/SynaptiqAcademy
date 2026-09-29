import React from "react";
import {
  LayoutGrid, FlaskConical, GraduationCap, Award, Globe2, BarChart3,
} from "lucide-react";
import { NAVY, TEXT_SECONDARY, BRD } from "@/lib/tokens";

export const TABS = [
  { id: "overview",   label: "Overview",   icon: LayoutGrid },
  { id: "research",   label: "Research",   icon: FlaskConical },
  { id: "teaching",   label: "Teaching",   icon: GraduationCap },
  { id: "reputation", label: "Reputation", icon: Award },
  { id: "portfolio",  label: "Portfolio",  icon: Globe2 },
  { id: "analytics",  label: "Analytics",  icon: BarChart3 },
];

/**
 * PassportNav — P1 Phase 7C4.1: replaces the old fixed 200px vertical
 * sidebar (a "sidebar inside sidebar" next to the app's own global left
 * nav) with a compact horizontal strip beneath the credential header.
 * Scrolls horizontally on narrow viewports instead of stacking a dropdown,
 * keeping every section one tap away at any width. Settings moved out of
 * this list — it's general account settings, not Passport content, so it
 * no longer needs a seat among six Passport sections.
 */
export function PassportNav({ activeTab, onTabChange }) {
  return (
    <div
      role="tablist"
      aria-label="Academic Passport sections"
      style={{
        display: "flex", gap: 4, borderBottom: `1px solid ${BRD}`,
        overflowX: "auto", WebkitOverflowScrolling: "touch", scrollbarWidth: "none",
      }}
    >
      {TABS.map(({ id, label, icon: Icon }) => {
        const active = activeTab === id;
        return (
          <button
            key={id}
            role="tab"
            aria-selected={active}
            onClick={() => onTabChange(id)}
            style={{
              display: "flex", alignItems: "center", gap: 7, padding: "10px 14px", flexShrink: 0,
              border: "none", borderBottom: active ? `2px solid ${NAVY}` : "2px solid transparent",
              background: "transparent", cursor: "pointer", whiteSpace: "nowrap",
              color: active ? NAVY : TEXT_SECONDARY, fontWeight: active ? 700 : 500, fontSize: 13.5,
              transition: "color 120ms ease, border-color 120ms ease", marginBottom: -1,
            }}
          >
            <Icon size={15} style={{ flexShrink: 0 }} />
            {label}
          </button>
        );
      })}
    </div>
  );
}

export default PassportNav;

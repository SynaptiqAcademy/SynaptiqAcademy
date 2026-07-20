import React from "react";
import { Link } from "react-router-dom";
import {
  LayoutGrid, FlaskConical, GraduationCap, Award, Globe2, BarChart3,
  Settings as SettingsIcon,
} from "lucide-react";
import { NAVY, TEXT_SECONDARY, WHITE, BRD } from "@/lib/tokens";

export const TABS = [
  { id: "overview",   label: "Overview",   icon: LayoutGrid },
  { id: "research",   label: "Research",   icon: FlaskConical },
  { id: "teaching",   label: "Teaching",   icon: GraduationCap },
  { id: "reputation", label: "Reputation", icon: Award },
  { id: "portfolio",  label: "Portfolio",  icon: Globe2 },
  { id: "analytics",  label: "Analytics",  icon: BarChart3 },
];

/**
 * PassportNav — six primary sections, replacing the previous ~30-item
 * anchor-link menu. Every one of those items still exists — they're now
 * grouped as premium cards inside their section's tab panel (see
 * AcademicPassport.jsx / components/passport/tabs/*) instead of being
 * separate nav entries. Coexists with the main app sidebar.
 */
export function PassportNav({ activeTab, onTabChange }) {
  return (
    <div className="w-full lg:w-[200px] lg:sticky lg:top-6" style={{ flexShrink: 0, alignSelf: "flex-start" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {TABS.map(({ id, label, icon: Icon }) => {
          const active = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              style={{
                display: "flex", alignItems: "center", gap: 10, width: "100%", padding: "9px 12px",
                border: "none", borderRadius: 9, cursor: "pointer", textAlign: "left",
                background: active ? NAVY : "transparent", color: active ? WHITE : TEXT_SECONDARY,
                fontWeight: active ? 600 : 500, fontSize: 13.5, transition: "background 120ms ease",
              }}
              onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "#F1F5F9"; }}
              onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}
            >
              <Icon size={16} style={{ flexShrink: 0 }} />
              {label}
            </button>
          );
        })}
      </div>

      <div style={{ marginTop: 16, paddingTop: 12, borderTop: `1px solid ${BRD}` }}>
        <Link
          to="/settings"
          style={{ display: "flex", alignItems: "center", gap: 10, width: "100%", padding: "9px 12px", borderRadius: 9, textDecoration: "none", color: TEXT_SECONDARY, fontSize: 13.5, fontWeight: 500 }}
        >
          <SettingsIcon size={16} /> Settings
        </Link>
      </div>
    </div>
  );
}

export default PassportNav;

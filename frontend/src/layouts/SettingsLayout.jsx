/* eslint-disable */
import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { PageLayout } from "@/components/ds/PageLayout";
import { SETTINGS_NAV_ITEMS } from "@/lib/navItems";
import { NAVY, TEXT_MUTED, NAVY_08, NAVY_04 } from "@/lib/tokens";
import { Settings } from "lucide-react";

function SettingsNav({ active }) {
  const navigate = useNavigate();
  return (
    <nav style={{ padding: "16px 8px" }}>
      {SETTINGS_NAV_ITEMS.map((group) => (
        <div key={group.group} style={{ marginBottom: 14 }}>
          <div style={{
            fontSize: 10.5, fontWeight: 700, color: TEXT_MUTED, letterSpacing: "0.06em",
            textTransform: "uppercase", padding: "0 10px", marginBottom: 4,
          }}>
            {group.group}
          </div>
          {group.items.map((item) => {
            const path = item.id.split("#")[0].split("?")[0];
            const isActive = active === path || active.startsWith(path + "/");
            return (
              <button
                key={item.id}
                onClick={() => navigate(item.id)}
                style={{
                  display: "flex", alignItems: "center", gap: 8,
                  width: "100%", padding: "7px 10px", borderRadius: 6,
                  border: "none", cursor: "pointer", textAlign: "left",
                  background: isActive ? NAVY_08 : "transparent",
                  color: isActive ? NAVY : TEXT_MUTED,
                  fontSize: "0.82rem", fontWeight: isActive ? 600 : 400,
                  marginBottom: 2, transition: "background 100ms",
                }}
                onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = NAVY_04; }}
                onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = "transparent"; }}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      ))}
    </nav>
  );
}

/** SettingsLayout — settings pages with left section nav. */
export function SettingsLayout({ title = "Settings", subtitle, actions, children, activePath }) {
  const location = useLocation();
  const active = activePath ?? location.pathname;

  return (
    <PageLayout
      title={title}
      subtitle={subtitle}
      icon={<Settings size={15} style={{ color: NAVY }} />}
      actions={actions}
      aside={<SettingsNav active={active} />}
      asideWidth={200}
      asideLeft
    >
      {children}
    </PageLayout>
  );
}

export default SettingsLayout;

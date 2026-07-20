import React from "react";
import { Palette, Droplet, LayoutGrid, PanelLeft, Zap, Type } from "lucide-react";
import { SettingsGrid } from "./SettingsGrid";
import { Tag } from "@/components/ds/Tag";
import { PreferenceCard } from "./PreferenceCard";
import { PreferenceRow } from "./PreferenceRow";
import { NAVY, EMERALD, AMBER, ACCENT } from "@/lib/tokens";

const SIDEBAR_LS_KEY = "sq_sidebar_collapsed";

const ACCENTS = [
  { value: "navy", label: "Navy", color: NAVY },
  { value: "emerald", label: "Emerald", color: EMERALD },
  { value: "amber", label: "Amber", color: AMBER },
  { value: "crimson", label: "Crimson", color: ACCENT },
];

export function AppearanceSection({ prefs, setPref }) {
  const setSidebarCollapsed = (collapsed) => {
    setPref("sidebarCollapsed", collapsed, "Sidebar Behaviour");
    try { localStorage.setItem(SIDEBAR_LS_KEY, String(collapsed)); } catch {}
    window.dispatchEvent(new CustomEvent("sq:sidebar-collapsed-changed", { detail: collapsed }));
  };

  return (
    <SettingsGrid>
      <PreferenceCard icon={Palette} title="Theme" description="Light is available now; Dark and System follow soon">
        <div style={{ display: "flex", gap: 8 }}>
          {["light", "dark", "system"].map((t) => (
            <Tag
              key={t}
              variant={prefs.theme === t ? "active" : "default"}
              onClick={() => setPref("theme", t, "Theme")}
              style={{ opacity: t === "light" ? 1 : 0.55, textTransform: "capitalize" }}
            >
              {t}{t !== "light" ? " · soon" : ""}
            </Tag>
          ))}
        </div>
      </PreferenceCard>

      <PreferenceCard icon={Droplet} title="Accent Color" description="Previewed on this Settings page today">
        <div style={{ display: "flex", gap: 10 }}>
          {ACCENTS.map((a) => (
            <button
              key={a.value}
              onClick={() => setPref("accentColor", a.value, "Accent Color")}
              title={a.label}
              aria-label={a.label}
              aria-pressed={prefs.accentColor === a.value}
              style={{
                width: 26, height: 26, borderRadius: "50%", background: a.color, cursor: "pointer",
                border: prefs.accentColor === a.value ? "2px solid #0f172a" : "2px solid transparent",
                boxShadow: prefs.accentColor === a.value ? "0 0 0 2px white inset" : "none",
              }}
            />
          ))}
        </div>
      </PreferenceCard>

      <PreferenceCard icon={LayoutGrid} title="Density" description="Compact tightens spacing across cards and lists">
        <PreferenceRow
          label="Compact Mode"
          control="select"
          value={prefs.density}
          options={[{ value: "comfortable", label: "Comfortable" }, { value: "compact", label: "Compact" }]}
          onChange={(v) => setPref("density", v, "Density")}
        />
        <PreferenceRow
          label="Card Style"
          control="select"
          value={prefs.cardStyle}
          options={[{ value: "bordered", label: "Bordered" }, { value: "elevated", label: "Elevated" }]}
          onChange={(v) => setPref("cardStyle", v, "Card Style")}
        />
      </PreferenceCard>

      <PreferenceCard icon={PanelLeft} title="Sidebar Behaviour" description="Controls the real left sidebar right now">
        <PreferenceRow
          label="Collapse Sidebar"
          hint="Same as clicking Collapse in the sidebar footer"
          value={prefs.sidebarCollapsed}
          onChange={setSidebarCollapsed}
        />
      </PreferenceCard>

      <PreferenceCard icon={Zap} title="Animations" description="Reduces or removes motion across the interface">
        <PreferenceRow
          label="Enable Animations"
          value={prefs.animationsEnabled}
          onChange={(v) => setPref("animationsEnabled", v, "Enable Animations")}
        />
        <PreferenceRow
          label="Reduced Motion"
          hint="Shortens all transitions and animations app-wide"
          value={prefs.reducedMotion}
          onChange={(v) => setPref("reducedMotion", v, "Reduced Motion")}
        />
      </PreferenceCard>

      <PreferenceCard icon={Type} title="Font Size" description="Applies a real base text-size across Synaptiq">
        <PreferenceRow
          label="Text Size"
          control="select"
          value={prefs.fontSize}
          options={[{ value: "small", label: "Small" }, { value: "medium", label: "Medium" }, { value: "large", label: "Large" }]}
          onChange={(v) => setPref("fontSize", v, "Font Size")}
        />
      </PreferenceCard>
    </SettingsGrid>
  );
}

export default AppearanceSection;

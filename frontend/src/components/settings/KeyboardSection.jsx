import React from "react";
import { Keyboard, Command, Zap } from "lucide-react";
import { SettingsGrid } from "./SettingsGrid";
import { PreferenceCard } from "./PreferenceCard";
import { PreferenceRow } from "./PreferenceRow";
import { QUICK_ACTIONS } from "@/config/navigation";
import { BRD, TEXT_MUTED, TEXT_PRIMARY } from "@/lib/tokens";

function Kbd({ children }) {
  return (
    <kbd style={{
      display: "inline-flex", alignItems: "center", justifyContent: "center", minWidth: 20, height: 20,
      padding: "0 6px", fontSize: 11, fontFamily: "monospace", fontWeight: 600, color: TEXT_PRIMARY,
      background: "#F1F5F9", border: `1px solid ${BRD}`, borderRadius: 4,
    }}>
      {children}
    </kbd>
  );
}

const NAV_SHORTCUTS = [
  { keys: ["G", "H"], label: "Go to Home" },
  { keys: ["G", "I"], label: "Go to Inbox" },
  { keys: ["G", "M"], label: "Go to Messages" },
  { keys: ["G", "E"], label: "Go to Meetings" },
];

const GLOBAL_SHORTCUTS = [
  { keys: ["⌘", "K"], label: "Open Command Palette" },
  { keys: ["/"], label: "Open Command Palette" },
  { keys: ["Esc"], label: "Close modal / dialog" },
];

export function KeyboardSection({ prefs, setPref }) {
  return (
    <SettingsGrid>
      <PreferenceCard icon={Keyboard} title="Navigation Shortcuts" description="Press G, then the letter, in quick succession">
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {NAV_SHORTCUTS.map((s) => (
            <div key={s.label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12, color: TEXT_MUTED }}>{s.label}</span>
              <span style={{ display: "flex", gap: 4 }}>{s.keys.map((k) => <Kbd key={k}>{k}</Kbd>)}</span>
            </div>
          ))}
        </div>
        <PreferenceRow
          label="Enable G-key Navigation Shortcuts"
          value={prefs.gKeyShortcutsEnabled}
          onChange={(v) => setPref("gKeyShortcutsEnabled", v, "G-key Navigation Shortcuts")}
        />
      </PreferenceCard>

      <PreferenceCard icon={Command} title="Global Shortcuts">
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {GLOBAL_SHORTCUTS.map((s) => (
            <div key={s.keys.join("+")} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12, color: TEXT_MUTED }}>{s.label}</span>
              <span style={{ display: "flex", gap: 4 }}>{s.keys.map((k) => <Kbd key={k}>{k}</Kbd>)}</span>
            </div>
          ))}
        </div>
      </PreferenceCard>

      <PreferenceCard icon={Zap} title="Quick Actions" description="Available from the Command Palette" style={{ gridColumn: "1 / -1" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8 }}>
          {QUICK_ACTIONS.slice(0, 8).map((a) => (
            <div key={a.label} style={{ fontSize: 12, color: TEXT_PRIMARY, padding: "6px 10px", border: `1px solid ${BRD}`, borderRadius: 6 }}>
              {a.label}
            </div>
          ))}
        </div>
      </PreferenceCard>
    </SettingsGrid>
  );
}

export default KeyboardSection;

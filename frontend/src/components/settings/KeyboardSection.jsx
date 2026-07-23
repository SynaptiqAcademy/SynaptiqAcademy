import React from "react";
import { Keyboard, Command, Zap } from "lucide-react";
import { SettingsGrid } from "./SettingsGrid";
import { PreferenceCard } from "./PreferenceCard";
import { PreferenceRow } from "./PreferenceRow";
import { Tag } from "@/components/ds/Tag";
import { List, ListItem } from "@/components/ds/List";
import { QUICK_ACTIONS } from "@/config/navigation";
import { BRD, TEXT_PRIMARY } from "@/lib/tokens";

// Kbd renders a native <kbd> element styled as a physical key — this is a
// semantic HTML element (not a status/label pill), so it's kept hand-rolled
// rather than forced into Tag/Badge, which represent something different.
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
        <List border={false} radius={0} style={{ background: "transparent" }}>
          {NAV_SHORTCUTS.map((s) => (
            <ListItem
              key={s.label}
              compact
              title={s.label}
              trailing={<span style={{ display: "flex", gap: 4 }}>{s.keys.map((k) => <Kbd key={k}>{k}</Kbd>)}</span>}
              style={{ padding: "6px 0" }}
            />
          ))}
        </List>
        <PreferenceRow
          label="Enable G-key Navigation Shortcuts"
          value={prefs.gKeyShortcutsEnabled}
          onChange={(v) => setPref("gKeyShortcutsEnabled", v, "G-key Navigation Shortcuts")}
        />
      </PreferenceCard>

      <PreferenceCard icon={Command} title="Global Shortcuts">
        <List border={false} radius={0} style={{ background: "transparent" }}>
          {GLOBAL_SHORTCUTS.map((s) => (
            <ListItem
              key={s.keys.join("+")}
              compact
              title={s.label}
              trailing={<span style={{ display: "flex", gap: 4 }}>{s.keys.map((k) => <Kbd key={k}>{k}</Kbd>)}</span>}
              style={{ padding: "6px 0" }}
            />
          ))}
        </List>
      </PreferenceCard>

      <PreferenceCard icon={Zap} title="Quick Actions" description="Available from the Command Palette" style={{ gridColumn: "1 / -1" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8 }}>
          {QUICK_ACTIONS.slice(0, 8).map((a) => (
            <Tag key={a.label} style={{ justifyContent: "flex-start", width: "100%" }}>
              {a.label}
            </Tag>
          ))}
        </div>
      </PreferenceCard>
    </SettingsGrid>
  );
}

export default KeyboardSection;

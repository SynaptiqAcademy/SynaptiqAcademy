import React from "react";
import { Eye, Move, Volume2 } from "lucide-react";
import { SettingsGrid } from "./SettingsGrid";
import { PreferenceCard } from "./PreferenceCard";
import { PreferenceRow } from "./PreferenceRow";

export function AccessibilitySection({ prefs, setPref }) {
  return (
    <SettingsGrid>
      <PreferenceCard icon={Eye} title="Visual" description="High Contrast applies immediately">
        <PreferenceRow
          label="High Contrast"
          value={prefs.highContrast}
          onChange={(v) => setPref("highContrast", v, "High Contrast")}
        />
        <PreferenceRow
          label="Focus Indicators"
          hint="Always show a visible outline around the focused element"
          value={prefs.focusIndicators}
          onChange={(v) => setPref("focusIndicators", v, "Focus Indicators")}
        />
        <PreferenceRow
          label="Large Cursor"
          caption="Stored for a future release — no visual change yet"
          value={prefs.largeCursor}
          onChange={(v) => setPref("largeCursor", v, "Large Cursor")}
        />
      </PreferenceCard>

      <PreferenceCard icon={Move} title="Motion & Navigation">
        <PreferenceRow
          label="Reduced Motion"
          hint="Same preference as Appearance — shortens transitions app-wide"
          value={prefs.reducedMotion}
          onChange={(v) => setPref("reducedMotion", v, "Reduced Motion")}
        />
        <PreferenceRow
          label="Keyboard Navigation"
          hint="Optimize tab order and focus handling"
          value={prefs.keyboardNavigation}
          onChange={(v) => setPref("keyboardNavigation", v, "Keyboard Navigation")}
        />
      </PreferenceCard>

      <PreferenceCard icon={Volume2} title="Screen Reader" style={{ gridColumn: "1 / -1" }}>
        <PreferenceRow
          label="Screen Reader Mode"
          hint="Increases ARIA label verbosity where already implemented"
          caption="Not a full screen-reader overhaul — most of the app already uses semantic HTML and ARIA roles"
          value={prefs.screenReaderMode}
          onChange={(v) => setPref("screenReaderMode", v, "Screen Reader Mode")}
        />
      </PreferenceCard>
    </SettingsGrid>
  );
}

export default AccessibilitySection;

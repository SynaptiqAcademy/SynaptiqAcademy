import React from "react";

/**
 * SettingsGrid — 2-column card grid that actually collapses to 1 column on
 * mobile. The shared ds/Grid's cols=2 mode uses inline `gridTemplateColumns`,
 * which never collapses (only cols 3/4 get a responsive Tailwind path there),
 * causing horizontal overflow on narrow viewports. This is scoped to
 * Settings only, so it doesn't risk changing ds/Grid's behavior app-wide.
 */
export function SettingsGrid({ children }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {children}
    </div>
  );
}

export default SettingsGrid;

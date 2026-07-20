import React, { useState, useEffect, useRef } from "react";
import { Card } from "@/components/ds/Card";
import { TYPE, TEXT_MUTED, TEXT_PRIMARY, BRD } from "@/lib/tokens";

const STORAGE_KEY = "synaptiq.meetings.quickNotes";

/**
 * QuickNotes — lightweight per-user scratch pad for the Meetings page.
 * Persisted to localStorage: this is personal scratch text, not tied to any
 * specific meeting, so there is no backend collection for it.
 */
export function QuickNotes() {
  const [value, setValue] = useState("");
  const saveTimer = useRef(null);

  useEffect(() => {
    setValue(localStorage.getItem(STORAGE_KEY) || "");
  }, []);

  const handleChange = (e) => {
    const next = e.target.value;
    setValue(next);
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => localStorage.setItem(STORAGE_KEY, next), 300);
  };

  return (
    <Card padding="lg">
      <div style={{ ...TYPE.section, marginBottom: 10 }}>Quick Notes</div>
      <textarea
        value={value}
        onChange={handleChange}
        placeholder="Jot down a quick note…"
        rows={4}
        style={{
          width: "100%", border: `1px solid ${BRD}`, borderRadius: 6,
          padding: "8px 10px", fontSize: 12.5, fontFamily: "inherit",
          resize: "vertical", outline: "none", color: TEXT_PRIMARY,
        }}
      />
      <div style={{ fontSize: 10.5, color: TEXT_MUTED, marginTop: 6 }}>Saved on this device only</div>
    </Card>
  );
}

export default QuickNotes;

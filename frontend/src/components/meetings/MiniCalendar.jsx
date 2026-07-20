import React, { useState, useMemo } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { TYPE, NAVY, TEXT_MUTED, TEXT_PRIMARY, BRD } from "@/lib/tokens";

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];

/**
 * MiniCalendar — small month widget with meeting-day dots.
 * highlightDates: Set/array of "YYYY-MM-DD" strings that have meetings.
 */
export function MiniCalendar({ highlightDates = [], onSelectDate }) {
  const [cursor, setCursor] = useState(() => new Date());
  const highlightSet = useMemo(() => new Set(highlightDates), [highlightDates]);

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const startOffset = firstDay.getDay();
  const todayKey = new Date().toDateString();

  const cells = [];
  for (let i = 0; i < startOffset; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const keyFor = (d) => {
    const dt = new Date(year, month, d);
    return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
  };

  return (
    <Card padding="lg">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <span style={{ fontSize: 12.5, fontWeight: 700, color: TEXT_PRIMARY }}>
          {cursor.toLocaleDateString("en-US", { month: "long", year: "numeric" })}
        </span>
        <div style={{ display: "flex", gap: 2 }}>
          <button onClick={() => setCursor(new Date(year, month - 1, 1))} style={btnStyle}><ChevronLeft size={13} /></button>
          <button onClick={() => setCursor(new Date(year, month + 1, 1))} style={btnStyle}><ChevronRight size={13} /></button>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 2 }}>
        {WEEKDAYS.map((w, i) => (
          <div key={i} style={{ fontSize: 9.5, fontWeight: 700, color: TEXT_MUTED, textAlign: "center", padding: "2px 0" }}>{w}</div>
        ))}
        {cells.map((d, i) => {
          if (d == null) return <div key={i} />;
          const dt = new Date(year, month, d);
          const isToday = dt.toDateString() === todayKey;
          const hasMeeting = highlightSet.has(keyFor(d));
          return (
            <button
              key={i}
              onClick={() => onSelectDate?.(dt)}
              style={{
                position: "relative",
                height: 26, borderRadius: 6, border: "none", cursor: "pointer",
                background: isToday ? NAVY : "transparent",
                color: isToday ? "#fff" : TEXT_PRIMARY,
                fontSize: 11.5, fontWeight: isToday ? 700 : 400,
              }}
            >
              {d}
              {hasMeeting && !isToday && (
                <span style={{ position: "absolute", bottom: 2, left: "50%", transform: "translateX(-50%)", width: 3, height: 3, borderRadius: "50%", background: NAVY }} />
              )}
            </button>
          );
        })}
      </div>
    </Card>
  );
}

const btnStyle = {
  width: 22, height: 22, display: "flex", alignItems: "center", justifyContent: "center",
  border: `1px solid ${BRD}`, borderRadius: 6, background: "#fff", cursor: "pointer", color: TEXT_MUTED,
};

export default MiniCalendar;

import React, { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ds/Button";
import { EmptyState } from "@/components/ds/EmptyState";
import { CalendarDays } from "lucide-react";
import { NAVY, ACCENT, EMERALD, AMBER, TEXT_MUTED, TEXT_PRIMARY, BRD, WHITE } from "@/lib/tokens";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const TYPE_COLOR = {
  "Research Meeting": NAVY,
  "PhD Supervision": ACCENT,
  "Project Meeting": EMERALD,
  "Grant Meeting": AMBER,
  "Peer Review Meeting": "#3B82F6",
  "Institution Meeting": "#7C3AED",
  "Conference Preparation": "#DB2777",
  "Journal Submission Meeting": "#0891B2",
};

/**
 * MeetingCalendar — Month grid + Agenda list toggle.
 * No drag-and-drop: click a meeting to open it, click a day to quick-create.
 */
export function MeetingCalendar({ meetings = [], onDayClick, month, onMonthChange }) {
  const navigate = useNavigate();
  const [view, setView] = useState("month");
  const cursor = month || new Date();

  const byDay = useMemo(() => {
    const map = new Map();
    for (const m of meetings) {
      const key = new Date(m.start_at).toDateString();
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(m);
    }
    return map;
  }, [meetings]);

  const year = cursor.getFullYear();
  const mon = cursor.getMonth();
  const firstDay = new Date(year, mon, 1);
  const daysInMonth = new Date(year, mon + 1, 0).getDate();
  const startOffset = firstDay.getDay();
  const cells = [];
  for (let i = 0; i < startOffset; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  const changeMonth = (delta) => onMonthChange?.(new Date(year, mon + delta, 1));

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Button size="sm" variant="ghost" onClick={() => onMonthChange?.(new Date())}>Today</Button>
          <Button size="sm" variant="ghost" onClick={() => changeMonth(-1)}><ChevronLeft size={13} /></Button>
          <Button size="sm" variant="ghost" onClick={() => changeMonth(1)}><ChevronRight size={13} /></Button>
          <span style={{ fontSize: 14, fontWeight: 700, color: TEXT_PRIMARY, marginLeft: 4 }}>
            {cursor.toLocaleDateString("en-US", { month: "long", year: "numeric" })}
          </span>
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          <Button size="sm" variant={view === "month" ? "primary" : "ghost"} onClick={() => setView("month")}>Month</Button>
          <Button size="sm" variant={view === "agenda" ? "primary" : "ghost"} onClick={() => setView("agenda")}>Agenda</Button>
        </div>
      </div>

      {view === "month" ? (
        <div style={{ border: `1px solid ${BRD}`, borderRadius: 8, overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", background: "#F8FAFC" }}>
            {WEEKDAYS.map((w) => (
              <div key={w} style={{ padding: "8px 10px", fontSize: 10.5, fontWeight: 700, color: TEXT_MUTED, textTransform: "uppercase", letterSpacing: "0.06em" }}>{w}</div>
            ))}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)" }}>
            {cells.map((d, i) => {
              if (d == null) return <div key={i} style={{ minHeight: 92, background: "#FAFBFC", borderTop: `1px solid ${BRD}`, borderLeft: i % 7 !== 0 ? `1px solid ${BRD}` : "none" }} />;
              const dt = new Date(year, mon, d);
              const dayMeetings = byDay.get(dt.toDateString()) || [];
              const isToday = dt.toDateString() === new Date().toDateString();
              return (
                <div
                  key={i}
                  role="button"
                  tabIndex={0}
                  aria-label={`Add meeting on ${dt.toDateString()}`}
                  onClick={() => onDayClick?.(dt)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onDayClick?.(dt); } }}
                  style={{
                    minHeight: 92, padding: 6, cursor: "pointer",
                    borderTop: `1px solid ${BRD}`, borderLeft: i % 7 !== 0 ? `1px solid ${BRD}` : "none",
                    background: WHITE,
                  }}
                >
                  <span style={{
                    display: "inline-flex", alignItems: "center", justifyContent: "center",
                    width: 20, height: 20, borderRadius: "50%", fontSize: 11, fontWeight: isToday ? 700 : 500,
                    background: isToday ? NAVY : "transparent", color: isToday ? "#fff" : TEXT_PRIMARY,
                  }}>
                    {d}
                  </span>
                  <div style={{ marginTop: 4, display: "flex", flexDirection: "column", gap: 2 }}>
                    {dayMeetings.slice(0, 3).map((m) => (
                      <div
                        key={m.id}
                        onClick={(e) => { e.stopPropagation(); navigate(`/meetings/${m.id}`); }}
                        title={m.title}
                        style={{
                          fontSize: 10, padding: "1px 5px", borderRadius: 4, color: "#fff",
                          background: TYPE_COLOR[m.meeting_type] || NAVY,
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                        }}
                      >
                        {m.title}
                      </div>
                    ))}
                    {dayMeetings.length > 3 && (
                      <span style={{ fontSize: 9.5, color: TEXT_MUTED }}>+{dayMeetings.length - 3} more</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <AgendaList meetings={meetings} onOpen={(id) => navigate(`/meetings/${id}`)} />
      )}
    </div>
  );
}

function AgendaList({ meetings, onOpen }) {
  if (!meetings.length) {
    return <EmptyState icon={<CalendarDays />} title="No meetings this month" />;
  }
  const sorted = [...meetings].sort((a, b) => new Date(a.start_at) - new Date(b.start_at));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {sorted.map((m) => (
        <div
          key={m.id}
          role="button"
          tabIndex={0}
          onClick={() => onOpen(m.id)}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(m.id); } }}
          style={{
            display: "flex", alignItems: "center", gap: 10, padding: "8px 12px",
            border: `1px solid ${BRD}`, borderRadius: 6, cursor: "pointer", background: WHITE,
          }}
        >
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: TYPE_COLOR[m.meeting_type] || NAVY, flexShrink: 0 }} />
          <span style={{ fontSize: 11.5, color: TEXT_MUTED, width: 130, flexShrink: 0 }}>
            {new Date(m.start_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}
          </span>
          <span style={{ fontSize: 13, fontWeight: 500, color: TEXT_PRIMARY }}>{m.title}</span>
        </div>
      ))}
    </div>
  );
}

export default MeetingCalendar;

import React from "react";
import { useNavigate } from "react-router-dom";
import { Clock } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { TYPE, BRD, TEXT_MUTED, TEXT_PRIMARY, NAVY } from "@/lib/tokens";

function formatTime(iso) {
  try { return new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }); }
  catch { return ""; }
}

/**
 * TodayAgenda — compact list of today's meetings, for the right rail.
 */
export function TodayAgenda({ meetings = [] }) {
  const navigate = useNavigate();
  const today = meetings.filter((m) => new Date(m.start_at).toDateString() === new Date().toDateString());

  return (
    <Card padding="lg">
      <div style={{ ...TYPE.section, marginBottom: 12 }}>Today's Agenda</div>
      {today.length === 0 ? (
        <p style={{ fontSize: 12.5, color: TEXT_MUTED, margin: 0 }}>No meetings scheduled today.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {today.map((m) => (
            <div
              key={m.id}
              role="button"
              tabIndex={0}
              onClick={() => navigate(`/meetings/${m.id}`)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); navigate(`/meetings/${m.id}`); } }}
              style={{ display: "flex", gap: 10, cursor: "pointer", paddingBottom: 10, borderBottom: `1px solid ${BRD}` }}
            >
              <Clock size={13} style={{ color: NAVY, marginTop: 2, flexShrink: 0 }} />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: TEXT_PRIMARY }}>{m.title}</div>
                <div style={{ fontSize: 11, color: TEXT_MUTED }}>{formatTime(m.start_at)} · {m.meeting_type}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default TodayAgenda;

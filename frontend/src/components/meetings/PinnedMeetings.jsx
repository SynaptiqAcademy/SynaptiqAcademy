import React from "react";
import { useNavigate } from "react-router-dom";
import { Pin } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { TYPE, TEXT_MUTED, TEXT_PRIMARY, BRD } from "@/lib/tokens";

/**
 * PinnedMeetings — right-rail list of meetings the user has pinned.
 */
export function PinnedMeetings({ meetings = [] }) {
  const navigate = useNavigate();
  const pinned = meetings.filter((m) => m.pinned);

  if (pinned.length === 0) return null;

  return (
    <Card padding="lg">
      <div style={{ ...TYPE.section, marginBottom: 10 }}>Pinned Meetings</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {pinned.map((m) => (
          <div
            key={m.id}
            role="button"
            tabIndex={0}
            onClick={() => navigate(`/meetings/${m.id}`)}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); navigate(`/meetings/${m.id}`); } }}
            style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}
          >
            <Pin size={12} style={{ color: TEXT_MUTED, flexShrink: 0 }} />
            <span style={{ fontSize: 12.5, color: TEXT_PRIMARY, fontWeight: 500 }}>{m.title}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default PinnedMeetings;

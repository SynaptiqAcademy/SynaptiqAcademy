import React, { useMemo } from "react";
import { CalendarDays } from "lucide-react";
import { EmptyState } from "@/components/ds/EmptyState";
import { Button } from "@/components/ds/Button";
import { TEXT_MUTED, BRD } from "@/lib/tokens";
import { MeetingCard } from "./MeetingCard";

function dateLabel(iso) {
  const d = new Date(iso);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  const sameDay = (a, b) => a.toDateString() === b.toDateString();
  if (sameDay(d, today)) return "Today";
  if (sameDay(d, tomorrow)) return "Tomorrow";
  return d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
}

/**
 * MeetingTimeline — date-separated groups of MeetingCards.
 */
export function MeetingTimeline({ meetings = [], onEdit, onCreate }) {
  const groups = useMemo(() => {
    const map = new Map();
    for (const m of meetings) {
      const key = new Date(m.start_at).toDateString();
      if (!map.has(key)) map.set(key, { label: dateLabel(m.start_at), items: [] });
      map.get(key).items.push(m);
    }
    return Array.from(map.values());
  }, [meetings]);

  if (!meetings.length) {
    return (
      <EmptyState
        icon={<CalendarDays />}
        title="No upcoming meetings"
        description="Schedule your first research meeting, supervision session, or grant review to see it here."
        action={<Button onClick={onCreate}>+ New Meeting</Button>}
      />
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {groups.map((group) => (
        <div key={group.label}>
          <div style={{
            fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase",
            color: TEXT_MUTED, marginBottom: 10, paddingBottom: 8, borderBottom: `1px solid ${BRD}`,
          }}>
            {group.label}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {group.items.map((m) => (
              <MeetingCard key={m.id} meeting={m} onEdit={onEdit} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default MeetingTimeline;

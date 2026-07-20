import React from "react";
import { Plus } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { TEXT_PRIMARY, TEXT_MUTED, NAVY } from "@/lib/tokens";

function formatNext(iso) {
  if (!iso) return "No upcoming occurrence";
  const d = new Date(iso);
  return `Next: ${d.toLocaleDateString("en-US", { month: "short", day: "numeric" })} · ${d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}`;
}

/**
 * MeetingCategoryCard — one of the 8 meeting-type category cards.
 */
export function MeetingCategoryCard({ category, onQuickCreate }) {
  const next = category.next_occurrence;
  return (
    <Card padding="lg" style={{ display: "flex", flexDirection: "column", gap: 10, height: "100%" }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: TEXT_PRIMARY, letterSpacing: "-0.01em" }}>
        {category.meeting_type}
      </div>
      <div style={{ fontFamily: "Georgia, serif", fontSize: 26, fontWeight: 700, color: NAVY }}>
        {category.scheduled_count}
        <span style={{ fontSize: 11, fontWeight: 400, color: TEXT_MUTED, marginLeft: 6 }}>scheduled</span>
      </div>
      <div style={{ fontSize: 11.5, color: TEXT_MUTED, flex: 1 }}>
        {next ? formatNext(next.start_at) : "No upcoming occurrence"}
      </div>
      <Button size="sm" variant="ghost" onClick={() => onQuickCreate?.(category.meeting_type)}>
        <Plus size={12} /> Quick create
      </Button>
    </Card>
  );
}

export default MeetingCategoryCard;

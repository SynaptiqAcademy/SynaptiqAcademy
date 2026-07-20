import React from "react";
import { Link } from "react-router-dom";
import {
  Activity, ArrowRight, BookOpen, ClipboardCheck, GraduationCap, Users2, UserCircle2,
} from "lucide-react";
import { Card } from "@/components/ds/Card";
import { TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, NAVY, EMERALD, BRD } from "@/lib/tokens";

const CATEGORY_ICON = {
  publication:   BookOpen,
  reviewer:      ClipboardCheck,
  teaching:      GraduationCap,
  collaboration: Users2,
  profile:       UserCircle2,
};

function timeAgo(iso) {
  if (!iso) return "";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

/** RecentActivityCard — real recent reputation events (GET /reputation/events/me), icon per real event category. */
export function RecentActivityCard({ events = [] }) {
  return (
    <Card padding="lg">
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
        <Activity size={14} style={{ color: NAVY }} />
        <div style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY }}>Recent Activity</div>
      </div>
      {events.length === 0 ? (
        <p style={{ fontSize: 12, color: TEXT_MUTED, margin: 0 }}>No recent activity yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {events.slice(0, 5).map((e, i) => {
            const Icon = CATEGORY_ICON[e.category] || Activity;
            return (
              <div key={e.id || i} style={{ display: "flex", alignItems: "center", gap: 9, padding: "6px 0", borderBottom: i < Math.min(events.length, 5) - 1 ? `1px solid ${BRD}` : "none" }}>
                <span style={{ width: 24, height: 24, borderRadius: 7, background: "rgba(15,40,71,0.06)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Icon size={12} style={{ color: NAVY }} />
                </span>
                <span style={{ fontSize: 12, color: TEXT_SECONDARY, flex: 1, minWidth: 0 }}>{e.description}</span>
                {e.points > 0 && <span style={{ fontSize: 10.5, fontWeight: 700, color: EMERALD, flexShrink: 0 }}>+{e.points}</span>}
                <span style={{ fontSize: 10.5, color: TEXT_MUTED, flexShrink: 0 }}>{timeAgo(e.created_at)}</span>
              </div>
            );
          })}
        </div>
      )}
      <Link to="/trust/history" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600, color: NAVY, textDecoration: "none", marginTop: 12 }}>
        View all activity <ArrowRight size={11} />
      </Link>
    </Card>
  );
}

export default RecentActivityCard;

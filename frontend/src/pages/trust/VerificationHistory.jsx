/* eslint-disable */
import React, { useEffect, useState } from "react";
import { History, BarChart2, Award } from "lucide-react";
import { NAVY, EMERALD, ACCENT, TEXT_SECONDARY } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, FormSelect, List, ListItem, Badge, EmptyState, LoadingOverlay } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = "/api/trust";

const EVENT_LABELS = {
  verification_run:    "Verification Run",
  request_submitted:   "Request Submitted",
  request_approved:    "Request Approved",
  request_rejected:    "Request Rejected",
  request_appealed:    "Appeal Filed",
  badge_awarded:       "Badge Awarded",
  admin_override:      "Admin Override",
  fraud_flag:          "Integrity Flag",
};

const EVENT_COLORS = {
  verification_run:    NAVY,
  request_submitted:   "#D97706",
  request_approved:    EMERALD,
  request_rejected:    ACCENT,
  badge_awarded:       "#7C3AED",
  admin_override:      "#0369A1",
  fraud_flag:          ACCENT,
};

export default function VerificationHistory() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(50);

  useEffect(() => {
    fetchApi(API + `/audit?limit=${limit}`, { credentials: "include" })
      .then(r => r.json())
      .then(d => { setEvents(d || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, [limit]);

  const eventCounts = events.reduce((acc, e) => {
    acc[e.event] = (acc[e.event] || 0) + 1;
    return acc;
  }, {});
  const badgesAwarded = events
    .filter(e => e.event === "badge_awarded" && e.data?.badge)
    .map(e => e.data.badge);

  return (
    <ResearchLayout
      title="Verification History"
      subtitle="Immutable audit trail of all trust events"
      stats={events.length > 0 ? [
        { label: "Total Events",       value: events.length },
        { label: "Verification Runs",  value: eventCounts.verification_run || 0 },
        { label: "Requests Approved",  value: eventCounts.request_approved || 0 },
        { label: "Badges Awarded",     value: eventCounts.badge_awarded || 0 },
      ] : undefined}
      sidebar={events.length > 0 ? (
        <VerificationHistorySidebar eventCounts={eventCounts} badgesAwarded={badgesAwarded} />
      ) : undefined}
      actions={
        <FormSelect value={limit} onChange={e => setLimit(Number(e.target.value))}>
          <option value={25}>Last 25</option>
          <option value={50}>Last 50</option>
          <option value={100}>Last 100</option>
          <option value={200}>Last 200</option>
        </FormSelect>
      }
    >
      <div style={{ maxWidth: 780, margin: "0 auto" }}>

        {loading ? (
          <LoadingOverlay text="Loading…" />
        ) : events.length === 0 ? (
          <EmptyState icon={<History />} title="No audit events yet." />
        ) : (
          <List>
            {events.map((e, i) => {
              const color = EVENT_COLORS[e.event] || NAVY;
              return (
                <ListItem
                  key={e._id || i}
                  leading={<div style={{ width: 8, height: 8, borderRadius: 4, background: color }} />}
                  trailing={
                    <div style={{ fontSize: 11, color: TEXT_SECONDARY, whiteSpace: "nowrap" }}>
                      {e.created_at ? new Date(e.created_at).toLocaleString() : "—"}
                    </div>
                  }
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: NAVY }}>
                      {EVENT_LABELS[e.event] || e.event?.replace(/_/g, " ")}
                    </span>
                    {e.data?.type && (
                      <Badge color={color}>
                        {e.data.type.replace(/_/g, " ")}
                      </Badge>
                    )}
                    {e.data?.badge && (
                      <Badge color="#7C3AED">
                        {e.data.badge.replace(/_/g, " ")}
                      </Badge>
                    )}
                  </div>
                  {e.data?.status && (
                    <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 2 }}>
                      Status: {e.data.status}
                    </div>
                  )}
                </ListItem>
              );
            })}
          </List>
        )}
      </div>
    </ResearchLayout>
  );
}

// ── Right rail — real data already loaded by this page, never fabricated ──────
function VerificationHistorySidebar({ eventCounts, badgesAwarded }) {
  const typeEntries = Object.entries(eventCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);
  const uniqueBadges = [...new Set(badgesAwarded)];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <BarChart2 size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Event Types</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {typeEntries.map(([event, count]) => (
            <div key={event} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12, color: "#374151", textTransform: "capitalize" }}>
                {event.replace(/_/g, " ")}
              </span>
              <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>{count}</span>
            </div>
          ))}
        </div>
      </Card>

      {uniqueBadges.length > 0 && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Award size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Badges Awarded</div>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {uniqueBadges.map(b => (
              <Badge key={b} color="#7C3AED">{b.replace(/_/g, " ")}</Badge>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

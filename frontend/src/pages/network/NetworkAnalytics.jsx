import React, { useState, useEffect } from "react";
import axios from "axios";
import { Users, Handshake, Layers, MessageSquare, Calendar, Award } from "lucide-react";
import { NAVY, WARM, ACCENT, EMERALD, WHITE, TEXT_SECONDARY } from "@/lib/tokens";
import { AnalyticsLayout } from "@/layouts";
import { Card, LoadingOverlay } from "@/components/ds";

// Hand-rolled rather than ds/StatCard: StatCard hardcodes icon-badge/value colors
// (WARM+TEXT_TERTIARY, or NAVY when highlighted) with no per-instance color prop,
// so it can't reproduce the per-metric brand-color coding (purple/orange/emerald/…)
// this page relies on to visually separate metric categories at a glance.
function MetricCard({ label, value, sub, icon: Icon, color }) {
  return (
    <Card padding="md" style={{ flex: 1, minWidth: 120 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <div style={{ width: 32, height: 32, borderRadius: 8, background: `${color}15`, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Icon size={16} color={color} />
        </div>
        <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>{label}</span>
      </div>
      <div style={{ fontSize: 28, fontWeight: 800, color }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 2 }}>{sub}</div>}
    </Card>
  );
}

// Hand-rolled rather than ds/ProgressRing: ProgressRing only offers NAVY (fixed) or
// an auto 4-step value-based color scale (colorByValue) — no custom-color override —
// so it can't render this page's fixed ACCENT-branded ring regardless of score value.
function ScoreRing({ score, color = ACCENT }) {
  const r = 42;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(100, Math.max(0, score));
  const dash = (pct / 100) * circ;
  return (
    <div style={{ position: "relative", width: 110, height: 110, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <svg width="110" height="110" style={{ position: "absolute" }}>
        <circle cx="55" cy="55" r={r} fill="none" stroke={`${color}15`} strokeWidth="10" />
        <circle cx="55" cy="55" r={r} fill="none" stroke={color} strokeWidth="10"
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
          transform="rotate(-90 55 55)" />
      </svg>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 22, fontWeight: 900, color }}>{pct}</div>
        <div style={{ fontSize: 10, color: TEXT_SECONDARY }}>/ 100</div>
      </div>
    </div>
  );
}

export default function NetworkAnalytics() {
  const [overview, setOverview] = useState(null);
  const [platform, setPlatform] = useState(null);
  const [collabAnalytics, setCollabAnalytics] = useState(null);
  const [groupAnalytics, setGroupAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      axios.get("/api/network/analytics/overview"),
      axios.get("/api/network/analytics/platform"),
      axios.get("/api/network/analytics/collaborations"),
      axios.get("/api/network/analytics/groups"),
    ]).then(([o, p, c, g]) => {
      setOverview(o.data);
      setPlatform(p.data);
      setCollabAnalytics(c.data);
      setGroupAnalytics(g.data);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingOverlay text="Loading analytics…" />;

  return (
    <AnalyticsLayout title="Network Analytics">

      {/* Network Score */}
      {overview && (
        <div style={{ background: `linear-gradient(135deg, ${NAVY} 0%, #3730a3 100%)`, borderRadius: 16, padding: "28px 32px", color: WHITE, marginBottom: 24, display: "flex", alignItems: "center", gap: 32 }}>
          <ScoreRing score={overview.network_score || 0} color={ACCENT} />
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, marginBottom: 4 }}>Your Network Score</div>
            <div style={{ opacity: 0.75, fontSize: 13, marginBottom: 12 }}>Based on groups, communities, collaborations, mentorship, and events.</div>
            <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
              {[
                ["Groups", overview.groups], ["Communities", overview.communities],
                ["Collaborations", overview.collaborations_created + overview.collaborations_applied],
                ["Events", overview.events_attended],
              ].map(([label, val]) => (
                <div key={label} style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 20, fontWeight: 800, color: ACCENT }}>{val || 0}</div>
                  <div style={{ fontSize: 11, opacity: 0.75 }}>{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Personal metrics */}
      {overview && (
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 24 }}>
          <MetricCard label="Groups" value={overview.groups} icon={Layers} color="#8b5cf6" />
          <MetricCard label="Communities" value={overview.communities} icon={MessageSquare} color="#f97316" />
          <MetricCard label="Collaborations Posted" value={overview.collaborations_created} icon={Handshake} color={EMERALD} />
          <MetricCard label="Applications Sent" value={overview.collaborations_applied} icon={Users} color={ACCENT} />
          <MetricCard label="Events Attended" value={overview.events_attended} icon={Calendar} color="#06b6d4" />
          <MetricCard label="Mentorship Links" value={overview.mentorship_connections} icon={Award} color="#ec4899" />
        </div>
      )}

      {/* Collaboration analytics */}
      {collabAnalytics && (
        <Card padding="lg" style={{ marginBottom: 16 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 14, fontWeight: 700, color: NAVY }}>Collaboration Analytics</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 10 }}>
            {[
              { label: "Posted (Open)", value: collabAnalytics.posted_open },
              { label: "Posted (Closed)", value: collabAnalytics.posted_closed },
              { label: "Applications Received", value: collabAnalytics.received_applications },
              { label: "Collaborators Accepted", value: collabAnalytics.accepted_collaborators },
              { label: "Applications Sent", value: collabAnalytics.sent_applications },
              { label: "Accepted as Collaborator", value: collabAnalytics.accepted_as_collaborator },
            ].map(({ label, value }) => (
              <div key={label} style={{ textAlign: "center", padding: "12px 8px", background: WARM, borderRadius: 10 }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: NAVY }}>{value || 0}</div>
                <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>{label}</div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 16, marginTop: 14, fontSize: 13 }}>
            <span style={{ color: TEXT_SECONDARY }}>Acceptance rate (as owner): <b style={{ color: NAVY }}>{collabAnalytics.acceptance_rate_as_owner || 0}%</b></span>
            <span style={{ color: TEXT_SECONDARY }}>Success rate (as applicant): <b style={{ color: NAVY }}>{collabAnalytics.acceptance_rate_as_applicant || 0}%</b></span>
          </div>
        </Card>
      )}

      {/* Platform-wide stats */}
      {platform && (
        <Card padding="lg">
          <h3 style={{ margin: "0 0 16px", fontSize: 14, fontWeight: 700, color: NAVY }}>Platform Network Overview</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 10 }}>
            {[
              { label: "Total Researchers", value: platform.total_researchers?.toLocaleString(), color: ACCENT },
              { label: "Research Groups", value: platform.total_groups, color: "#8b5cf6" },
              { label: "Communities", value: platform.total_communities, color: "#f97316" },
              { label: "Open Collaborations", value: platform.open_collaborations, color: EMERALD },
              { label: "Upcoming Events", value: platform.upcoming_events, color: "#06b6d4" },
              { label: "Active Mentors", value: platform.active_mentors, color: "#ec4899" },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ textAlign: "center", padding: "12px 8px", background: WARM, borderRadius: 10 }}>
                <div style={{ fontSize: 22, fontWeight: 800, color }}>{value || 0}</div>
                <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>{label}</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </AnalyticsLayout>
  );
}

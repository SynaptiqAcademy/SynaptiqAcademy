/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck, BadgeCheck, FileSearch, Fingerprint,
  Award, ChevronRight, Clock,
} from "lucide-react";
import { NAVY, BRD, EMERALD, ACCENT, TEXT_SECONDARY } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, LoadingOverlay } from "@/components/ds";

const API = "/api/trust";

// Kept hand-rolled: a custom 128px ring with a 4-tier (80/60/40) EMERALD /
// #0369A1 / #D97706 / ACCENT color scale. ds/Progress.jsx's ProgressRing
// only offers fixed sm/md/lg (48/64/96px) sizes and a different built-in
// colorByValue threshold set (80/50/30, EMERALD/NAVY/AMBER/CRIMSON), so
// reusing it would change both the size and the score-to-color mapping.
function TrustScoreRing({ score = 0 }) {
  const r = 54;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  const color = score >= 80 ? EMERALD : score >= 60 ? "#0369A1" : score >= 40 ? "#D97706" : ACCENT;
  return (
    <svg width={128} height={128} viewBox="0 0 128 128">
      <circle cx={64} cy={64} r={r} fill="none" stroke={BRD} strokeWidth={10} />
      <circle
        cx={64} cy={64} r={r} fill="none"
        stroke={color} strokeWidth={10}
        strokeDasharray={`${filled} ${circ - filled}`}
        strokeLinecap="round"
        transform="rotate(-90 64 64)"
        style={{ transition: "stroke-dasharray 0.8s ease" }}
      />
      <text x="50%" y="50%" textAnchor="middle" dy="0.35em"
        style={{ fontSize: 28, fontWeight: 700, fill: NAVY }}>
        {Math.round(score)}
      </text>
    </svg>
  );
}

function OverviewCard({ to, icon: Icon, label, value, color }) {
  return (
    <Card to={to} padding="md" style={{ display: "flex", alignItems: "center", gap: 14 }}>
      <span style={{ width: 38, height: 38, borderRadius: 9, background: color + "18",
        display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Icon size={18} color={color} />
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 1 }}>{label}</div>
        <div style={{ fontSize: 18, fontWeight: 700, color: NAVY }}>{value}</div>
      </div>
      <ChevronRight size={16} color={TEXT_SECONDARY} />
    </Card>
  );
}

export default function TrustOverview() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(API + "/overview", { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return (
    <ResearchLayout
      title="Trust & Verification"
      subtitle="Your verified academic identity — measurable, shareable, and trusted."
      icon={<ShieldCheck size={24} color={NAVY} />}
    >
      {loading ? (
          <LoadingOverlay text="Loading…" />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            {/* Trust Score Panel */}
            <Card padding="xl" style={{
              gridColumn: "1 / -1",
              display: "flex", alignItems: "center", gap: 32,
            }}>
              <TrustScoreRing score={data?.trust_score || 0} />
              <div>
                <div style={{ fontSize: 13, color: TEXT_SECONDARY, marginBottom: 4 }}>Trust Score</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: NAVY, marginBottom: 6 }}>
                  {data?.trust_level || "Unverified"}
                </div>
                <p style={{ fontSize: 13, color: TEXT_SECONDARY, margin: "0 0 14px" }}>
                  {data?.trust_advice || "Complete your profile and start verifying your academic identity."}
                </p>
                <Link to="/trust/score"
                  style={{ fontSize: 13, color: NAVY, fontWeight: 600,
                    textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 4 }}>
                  View full breakdown <ChevronRight size={14} />
                </Link>
              </div>
            </Card>

            <OverviewCard
              to="/trust/my-verifications"
              icon={BadgeCheck}
              label="Verifications"
              value={`${data?.verifications_verified || 0} / ${data?.verifications_total || 0}`}
              color={EMERALD}
            />
            <OverviewCard
              to="/trust/requests"
              icon={FileSearch}
              label="Pending Requests"
              value={data?.requests_pending || 0}
              color="#D97706"
            />
            <OverviewCard
              to="/academic-passport"
              icon={Fingerprint}
              label="Academic Passport"
              value="View Passport"
              color={NAVY}
            />
            <OverviewCard
              to="/trust/integrity"
              icon={Award}
              label="Integrity Report"
              value="View Report"
              color={ACCENT}
            />

            {/* Badges */}
            {data?.badges?.length > 0 && (
              <Card padding="lg" style={{ gridColumn: "1 / -1" }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 12 }}>
                  Your Badges ({data.badge_count})
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                  {data.badges.map(b => (
                    <Badge key={b.badge_key} color={b.color || NAVY}>
                      {b.label}
                    </Badge>
                  ))}
                </div>
              </Card>
            )}

            {/* Recent Activity */}
            {data?.recent_activity?.length > 0 && (
              <Card padding="lg" style={{ gridColumn: "1 / -1" }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 12,
                  display: "flex", alignItems: "center", gap: 6 }}>
                  <Clock size={14} /> Recent Activity
                </div>
                {data.recent_activity.map((e, i) => (
                  <div key={i} style={{
                    display: "flex", justifyContent: "space-between",
                    padding: "8px 0", borderBottom: i < data.recent_activity.length - 1 ? `1px solid ${BRD}` : "none",
                    fontSize: 13,
                  }}>
                    <span style={{ color: NAVY }}>{e.event?.replace(/_/g, " ")}</span>
                    <span style={{ color: TEXT_SECONDARY }}>
                      {e.created_at ? new Date(e.created_at).toLocaleDateString() : ""}
                    </span>
                  </div>
                ))}
              </Card>
            )}
          </div>
        )}
    </ResearchLayout>
  );
}

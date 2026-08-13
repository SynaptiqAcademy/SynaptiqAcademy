/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck, BadgeCheck, Fingerprint,
  Award, ChevronRight, Clock,
} from "lucide-react";
import { NAVY, BRD, EMERALD, ACCENT, TEXT_SECONDARY } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, LoadingOverlay } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = "/api/trust";

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
    fetchApi(API + "/overview", { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const trustScore = data?.trust_score || 0;
  const ringColor = trustScore >= 80 ? EMERALD : trustScore >= 60 ? "#0369A1" : trustScore >= 40 ? "#D97706" : ACCENT;

  return (
    <ResearchLayout
      title="Trust & Verification"
      subtitle="Your verified academic identity — measurable, shareable, and trusted."
      icon={<ShieldCheck size={15} strokeWidth={1.5} color={NAVY} />}
      ring={data ? { value: trustScore, max: 100, label: data.trust_level || "Unverified", color: ringColor } : undefined}
      stats={data ? [
        { label: "Verifications",    value: `${data.verifications_verified || 0}/${data.verifications_total || 0}` },
        { label: "Pending Requests", value: data.requests_pending || 0 },
        { label: "Badges",           value: data.badge_count || 0 },
        { label: "Recent Events",    value: data.recent_activity?.length || 0 },
      ] : undefined}
      sidebar={data ? <TrustOverviewSidebar data={data} /> : undefined}
    >
      {loading ? (
          <LoadingOverlay text="Loading…" />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            {/* Trust Score Panel */}
            <Card padding="xl" style={{ gridColumn: "1 / -1" }}>
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
            </Card>

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
          </div>
        )}
    </ResearchLayout>
  );
}

// ── Right rail — real data already loaded by this page, never fabricated ──────
function TrustOverviewSidebar({ data }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <BadgeCheck size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Your Badges</div>
        </div>
        {data.badges?.length > 0 ? (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {data.badges.map(b => (
              <Badge key={b.badge_key} color={b.color || NAVY}>
                {b.label}
              </Badge>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>
            Complete verifications to start earning badges.
          </p>
        )}
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Clock size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Recent Activity</div>
        </div>
        {data.recent_activity?.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {data.recent_activity.slice(0, 6).map((e, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span style={{ fontSize: 12, color: "#374151", textTransform: "capitalize" }}>
                  {e.event?.replace(/_/g, " ")}
                </span>
                <span style={{ fontSize: 11, color: "#94A3B8", whiteSpace: "nowrap" }}>
                  {e.created_at ? new Date(e.created_at).toLocaleDateString() : ""}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>
            No trust events recorded yet.
          </p>
        )}
      </Card>
    </div>
  );
}

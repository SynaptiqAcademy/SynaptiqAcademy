import React from "react";
import { Edit3, Building2, CheckCircle2, Award } from "lucide-react";
import { Avatar } from "@/components/ds/Avatar";
import OrcidBadge from "@/components/orcid/OrcidBadge";
import { NAVY, NAVY2, WHITE, EMERALD } from "@/lib/tokens";

function extractOrcidId(orcid) {
  if (!orcid) return null;
  if (typeof orcid === "object") return orcid.orcid_id || null;
  if (typeof orcid === "string") return orcid;
  return null;
}

function TrustRing({ value, level }) {
  const dim = 84, stroke = 6;
  const r = (dim - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(100, Math.max(0, value));
  const offset = circ - (pct / 100) * circ;
  return (
    <div style={{ textAlign: "center", flexShrink: 0 }}>
      <div style={{ position: "relative", width: dim, height: dim }}>
        <svg width={dim} height={dim} viewBox={`0 0 ${dim} ${dim}`} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth={stroke} />
          <circle
            cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke="#38BDF8" strokeWidth={stroke}
            strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 800ms ease-out" }}
          />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontFamily: "Georgia, serif", fontSize: 22, fontWeight: 700, color: WHITE, lineHeight: 1 }}>{Math.round(value)}</span>
          <span style={{ fontSize: 9.5, color: "rgba(255,255,255,0.5)" }}>/100</span>
        </div>
      </div>
      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.55)", marginTop: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>Trust Score</div>
      {level && <div style={{ fontSize: 12, fontWeight: 700, color: WHITE, marginTop: 2 }}>{level}</div>}
    </div>
  );
}

function Pill({ children }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11.5, fontWeight: 600,
      padding: "5px 11px", borderRadius: 100, background: "rgba(255,255,255,0.1)",
      border: "1px solid rgba(255,255,255,0.16)", color: WHITE,
    }}>
      {children}
    </span>
  );
}

/**
 * PassportHero — flagship identity header. Every badge/stat is conditional
 * on real data — nothing here is shown unless the backing field is present.
 */
export function PassportHero({ profile, passport, reputation, verification, researchRank, teachingStats, projectsTotal, grantsTotal, pubsTotal, achievementsTotal, onEdit }) {
  const orcidId = extractOrcidId(profile?.orcid);
  const trustScore = passport?.trust_score ?? 0;
  const trustLevel = passport?.trust_level;
  const isVerifiedResearcher = !!(verification?.researcher_verified || passport?.verified_orcid);
  const isTop5Percent = (researchRank?.percentile_global ?? 0) >= 95;

  return (
    <div style={{
      borderRadius: 16, padding: "32px 32px 0", width: "100%", maxWidth: "100%", boxSizing: "border-box",
      background: `linear-gradient(135deg, ${NAVY} 0%, ${NAVY2} 100%)`, color: WHITE, overflow: "hidden",
    }}>
      <div style={{ display: "flex", gap: 24, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{ position: "relative", flexShrink: 0 }}>
          <div style={{ width: 88, height: 88, borderRadius: "50%", border: "3px solid rgba(255,255,255,0.2)", overflow: "hidden" }}>
            <Avatar url={profile?.avatar_url} name={profile?.full_name} size={88} />
          </div>
          <button
            onClick={onEdit}
            aria-label="Edit Academic Identity"
            style={{
              position: "absolute", bottom: -2, right: -2, width: 26, height: 26, borderRadius: "50%",
              background: EMERALD, border: `2px solid ${NAVY}`, display: "flex", alignItems: "center",
              justifyContent: "center", cursor: "pointer",
            }}
          >
            <Edit3 size={11} style={{ color: WHITE }} />
          </button>
        </div>

        <div style={{ flex: "1 1 260px", minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <h1 style={{
              fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.4rem, 2.6vw, 1.8rem)",
              fontWeight: 700, letterSpacing: "-0.02em", margin: 0, color: WHITE,
            }}>
              {profile?.full_name || "—"}
            </h1>
            {isVerifiedResearcher && <CheckCircle2 size={18} style={{ color: "#38BDF8" }} />}
          </div>

          {profile?.academic_role && (
            <div style={{ fontSize: 13.5, color: "rgba(255,255,255,0.65)", marginTop: 4 }}>{profile.academic_role}</div>
          )}

          {(profile?.institution || profile?.department) && (
            <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12.5, color: "rgba(255,255,255,0.5)", marginTop: 4 }}>
              <Building2 size={12} />
              {[profile.institution, profile.department].filter(Boolean).join(" · ")}
            </div>
          )}

          <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
            {orcidId && (
              <Pill><OrcidBadge orcidId={orcidId} size="sm" testId="passport-orcid-badge" /> {orcidId}</Pill>
            )}
            {isVerifiedResearcher && (
              <Pill><CheckCircle2 size={12} /> Verified Researcher</Pill>
            )}
            {isTop5Percent && (
              <Pill><Award size={12} /> Top 5% Researcher</Pill>
            )}
          </div>
        </div>

        <TrustRing value={trustScore} level={trustLevel} />
      </div>

      {/* Real stats ribbon — Courses/Students dropped (no such concept exists
          in this platform's data model); Workspaces/AI Sessions used instead. */}
      <div
        className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-7 divide-x divide-y lg:divide-y-0 divide-white/10"
        style={{ marginTop: 28, background: "rgba(0,0,0,0.18)", borderTop: "1px solid rgba(255,255,255,0.1)" }}
      >
        {[
          { label: "Publications", value: pubsTotal ?? 0 },
          { label: "Citations", value: reputation?.publication?.external_citations ?? 0 },
          { label: "Projects", value: projectsTotal ?? 0 },
          { label: "Grants", value: grantsTotal ?? 0 },
          { label: "Achievements", value: achievementsTotal ?? 0 },
          { label: "Workspaces", value: teachingStats?.totals?.workspaces ?? 0 },
          { label: "AI Sessions", value: teachingStats?.totals?.ai_sessions ?? 0 },
        ].map((s) => (
          <div key={s.label} style={{ padding: "14px 8px", textAlign: "center", minWidth: 0 }}>
            <div style={{ fontFamily: "Georgia, serif", fontSize: 19, fontWeight: 700 }}>{s.value}</div>
            <div style={{ fontSize: 9.5, color: "rgba(255,255,255,0.55)", textTransform: "uppercase", letterSpacing: "0.05em", marginTop: 3 }}>{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default PassportHero;

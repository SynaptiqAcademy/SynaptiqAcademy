import React, { useState } from "react";
import { Link } from "react-router-dom";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import {
  BookOpen, GraduationCap, Users2, ClipboardCheck, UserCircle2,
  Award, ChevronDown, ChevronUp, ArrowRight, RefreshCw, Trophy,
} from "lucide-react";
import { SectionShell, MiniStat } from "./PassportUI";
import { Button } from "@/components/ds/Button";
import { ProgressBar } from "@/components/ds/Progress";
import { TYPE, NAVY, EMERALD, BRD, WARM, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY } from "@/lib/tokens";

const CATEGORY_DEFS = [
  { key: "publication_score",   label: "Research",      icon: BookOpen,       suggestion: { label: "Add a manuscript", to: "/manuscripts" } },
  { key: "teaching_score",      label: "Teaching",      icon: GraduationCap,  suggestion: { label: "Start a teaching workspace", to: "/teaching" } },
  { key: "collaboration_score", label: "Collaboration", icon: Users2,         suggestion: { label: "Join a collaboration", to: "/collaborations" } },
  { key: "reviewer_score",      label: "Reviewer",      icon: ClipboardCheck, suggestion: { label: "Complete a peer review", to: "/reviews" } },
  { key: "profile_score",       label: "Community",     icon: UserCircle2,    suggestion: { label: "Complete your academic identity", editIdentity: true } },
];

const RARITY_COLOR = {
  common:   { color: TEXT_SECONDARY, bg: WARM },
  uncommon: { color: EMERALD, bg: "#ECFDF5" },
  rare:     { color: NAVY, bg: "rgba(15,40,71,0.06)" },
  special:  { color: "#D97706", bg: "#FFFBEB" },
};

function monthLabel(m) {
  const names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const idx = parseInt(m.month, 10) - 1;
  return `${names[idx] ?? m.month} '${m.year.slice(2)}`;
}

/**
 * AcademicReputationSection — replaces the plain ReputationGrid on the
 * caller's own passport with a premium dashboard, powered by the points-based
 * reputation system (GET /reputation/analytics/me + /reputation/research/me)
 * rather than the older activity-score system. Every trend shown is real:
 * monthly_history is an actual aggregate points-earned time series — there is
 * no per-category history in the backend, so per-category cards show a real
 * static point/percentage breakdown rather than a fabricated per-category
 * sparkline.
 */
export function AcademicReputationSection({ analytics, researchRank, onSyncOpenAlex, syncing, onEditIdentity }) {
  const [badgesOpen, setBadgesOpen] = useState(true);

  if (!analytics && !researchRank) return null;

  const overall = Math.round(analytics?.overall_score ?? researchRank?.overall_score ?? 0);
  const levelLabel = analytics?.reputation_label ?? researchRank?.reputation_label ?? "Research Explorer";
  const progress = researchRank?.progress_to_next ?? 0;
  const nextLabel = researchRank?.next_level_label;
  const breakdown = analytics?.category_breakdown || {};
  const monthly = analytics?.monthly_history || [];
  const badges = researchRank?.badges || [];
  const percentile = researchRank?.percentile_global;

  const totalPts = CATEGORY_DEFS.reduce((sum, c) => sum + (breakdown[c.key]?.points || 0), 0);
  const weakest = CATEGORY_DEFS.reduce((min, c) => {
    const pts = breakdown[c.key]?.points ?? 0;
    return pts < (breakdown[min.key]?.points ?? Infinity) ? c : min;
  }, CATEGORY_DEFS[0]);

  return (
    <SectionShell
      title="Academic Reputation"
      subtitle="Computed from real platform activity — publications, reviews, collaborations, teaching, and grants"
    >
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 24, marginBottom: 20 }}>
        <div>
          <div style={{ fontFamily: "Georgia, serif", fontSize: 40, fontWeight: 700, color: TEXT_PRIMARY, lineHeight: 1 }}>{overall}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
            <span style={{
              fontSize: 11, fontWeight: 700, padding: "3px 9px", borderRadius: 100,
              background: "rgba(15,40,71,0.08)", color: NAVY,
            }}>{levelLabel}</span>
            {nextLabel && <span style={{ ...TYPE.caption }}>{researchRank.next_level_min - overall} pts to {nextLabel}</span>}
          </div>
        </div>
        {nextLabel && (
          <div style={{ flex: "1 1 220px", minWidth: 180, maxWidth: 320 }}>
            <ProgressBar value={progress} max={100} showValue={false} />
          </div>
        )}
        {percentile > 0 && <MiniStat label="Global Percentile" value={`Top ${Math.max(1, Math.round(100 - percentile))}%`} color={EMERALD} />}
        {researchRank?.rank_global && <MiniStat label="Global Rank" value={`#${researchRank.rank_global}`} />}
      </div>

      {monthly.length > 1 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ ...TYPE.label, marginBottom: 8 }}>Reputation Growth (points earned per month)</div>
          <div style={{ width: "100%", height: 100 }}>
            <ResponsiveContainer>
              <AreaChart data={monthly.map((m) => ({ label: monthLabel(m), points: m.points_earned }))}>
                <defs>
                  <linearGradient id="repGrowth" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={NAVY} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={NAVY} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: `1px solid ${BRD}` }} />
                <Area type="monotone" dataKey="points" stroke={NAVY} strokeWidth={2} fill="url(#repGrowth)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="grid sm:grid-cols-2 lg:grid-cols-5" style={{ gap: 12, marginBottom: 20 }}>
        {CATEGORY_DEFS.map(({ key, label, icon: Icon }) => {
          const pts = breakdown[key]?.points ?? 0;
          const pct = breakdown[key]?.percentage ?? 0;
          return (
            <div key={key} style={{ border: `1px solid ${BRD}`, borderRadius: 12, padding: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                <Icon size={14} style={{ color: NAVY }} />
                <span style={{ fontSize: 12, fontWeight: 700, color: TEXT_PRIMARY }}>{label}</span>
              </div>
              <div style={{ fontFamily: "Georgia, serif", fontSize: 22, fontWeight: 700, marginTop: 8 }}>{Math.round(pts)}</div>
              <div style={{ ...TYPE.caption, marginTop: 2 }}>{pct}% of total{totalPts ? "" : ""}</div>
            </div>
          );
        })}
      </div>

      {badges.length > 0 && (
        <div style={{ borderTop: `1px solid ${BRD}`, paddingTop: 16, marginBottom: 16 }}>
          <button
            onClick={() => setBadgesOpen((o) => !o)}
            style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", background: "none", border: "none", cursor: "pointer", padding: 0 }}
          >
            <span style={{ ...TYPE.label, display: "flex", alignItems: "center", gap: 6 }}>
              <Award size={12} style={{ color: NAVY }} /> Reputation Badges ({badges.length})
            </span>
            {badgesOpen ? <ChevronUp size={14} style={{ color: TEXT_MUTED }} /> : <ChevronDown size={14} style={{ color: TEXT_MUTED }} />}
          </button>
          {badgesOpen && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
              {badges.map((b) => {
                const tone = RARITY_COLOR[b.rarity] || RARITY_COLOR.common;
                return (
                  <span key={b.code} title={b.description} style={{
                    display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11.5, fontWeight: 600,
                    padding: "6px 11px", borderRadius: 100, background: tone.bg, color: tone.color,
                  }}>
                    <Trophy size={11} /> {b.label}
                  </span>
                );
              })}
            </div>
          )}
        </div>
      )}

      <div style={{ borderTop: `1px solid ${BRD}`, paddingTop: 16, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={TYPE.label}>Suggested next step</div>
          <div style={{ fontSize: 13, color: TEXT_SECONDARY, marginTop: 4 }}>
            Strengthen your <strong style={{ color: TEXT_PRIMARY }}>{weakest.label}</strong> dimension
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {weakest.suggestion.editIdentity ? (
            <Button size="sm" variant="outline" onClick={onEditIdentity}>
              {weakest.suggestion.label} <ArrowRight size={12} />
            </Button>
          ) : (
            <Link to={weakest.suggestion.to}>
              <Button as="span" size="sm" variant="outline">
                {weakest.suggestion.label} <ArrowRight size={12} />
              </Button>
            </Link>
          )}
          <Button size="sm" variant="ghost" onClick={onSyncOpenAlex} loading={syncing}>
            {!syncing && <RefreshCw size={12} />} Sync OpenAlex citations
          </Button>
        </div>
      </div>
    </SectionShell>
  );
}

export default AcademicReputationSection;

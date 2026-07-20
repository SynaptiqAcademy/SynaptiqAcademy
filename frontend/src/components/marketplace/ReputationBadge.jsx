/**
 * ReputationBadge — compact display of a user's overall reputation score with
 * an optional popover-style breakdown. Designed to embed inside MatchCard,
 * ProfileHeader, and Author cards.
 *
 * Supports both legacy 5-sub-score format and new 4-dimension format from
 * the Phase 7 scorer. Backward compatible — will render whichever data is present.
 */
import React, { useState } from "react";
import { NAVY } from "@/lib/tokens";
import { TrendingUp, Star, Award, Users, Coins, Activity, BookOpen,
         UserCheck, BarChart2, GraduationCap } from "lucide-react";

// ── 4-dimension view (Phase 7 scorer output) ─────────────────────────────────
const DIMENSIONS = [
  { key: "research_score",  label: "Research",  icon: BarChart2,     tone: "text-[#0F2847]" },
  { key: "teaching_score",  label: "Teaching",  icon: GraduationCap, tone: "text-emerald-700" },
  { key: "community_score", label: "Community", icon: Users,         tone: "text-slate-700" },
];

// ── Legacy 5-sub-score view (kept for backward compat) ───────────────────────
const SUB = [
  { key: "collaboration", label: "Collaboration", icon: Users,     tone: "text-[#0F2847]" },
  { key: "publication",   label: "Publication",   icon: BookOpen,  tone: "text-purple-700" },
  { key: "reviewer",      label: "Reviewer",      icon: UserCheck, tone: "text-amber-700" },
  { key: "funding",       label: "Funding",       icon: Coins,     tone: "text-emerald-700" },
  { key: "activity",      label: "Activity",      icon: Activity,  tone: "text-slate-700" },
];

export function tier(overall) {
  if (overall >= 80) return { label: "Distinguished", short: "Distinguished", tone: "border-amber-400 bg-amber-50 text-amber-800" };
  if (overall >= 60) return { label: "Established",  short: "Established",   tone: "border-[#0F2847]/40 bg-[#0F2847]/5 text-[#0F2847]" };
  if (overall >= 40) return { label: "Active",       short: "Active",        tone: "border-emerald-400 bg-emerald-50 text-emerald-800" };
  if (overall >= 20) return { label: "Contributor",  short: "Contributor",   tone: "border-slate-300 bg-slate-50 text-slate-700" };
  return { label: "New Member", short: "New", tone: "border-slate-200 bg-slate-50 text-slate-500" };
}

export default function ReputationBadge({ reputation, compact = false, testId }) {
  const [open, setOpen] = useState(false);
  if (!reputation) return null;

  const overall = Math.round(reputation.overall || 0);
  const t = tier(overall);

  // Detect which format we have
  const has4Dims = reputation.research_score != null || reputation.teaching_score != null;

  if (compact) {
    return (
      <span
        data-testid={testId || "rep-badge-compact"}
        className={`overline border ${t.tone} px-1.5 py-0.5 inline-flex items-center gap-1`}
      >
        <Star size={9} strokeWidth={1.5} />
        {overall}
      </span>
    );
  }

  return (
    <div className="relative">
      <button
        data-testid={testId || "rep-badge"}
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-2 border border-slate-200 bg-white px-3 py-1.5 hover:border-[#0F2847]"
      >
        <Award size={12} strokeWidth={1.5} className="text-[#0F2847]" />
        <span className="font-serif text-base">{overall}</span>
        <span className={`overline border ${t.tone} px-1.5 py-0.5`}>{t.label}</span>
      </button>

      {open && (
        <div
          data-testid="rep-breakdown"
          className="absolute right-0 top-full mt-1 z-20 w-72 bg-white border border-slate-200 shadow-xl p-4"
          onMouseLeave={() => setOpen(false)}
        >
          <div className="overline mb-2 flex items-center gap-2">
            <TrendingUp size={11} strokeWidth={1.5} className="text-[#0F2847]" />
            Reputation breakdown
          </div>

          <div className="space-y-2">
            {(has4Dims ? DIMENSIONS : SUB).map(({ key, label, icon: Icon, tone }) => {
              const raw = has4Dims ? reputation[key] : reputation[key]?.score;
              const score = Math.round(raw ?? 0);
              return (
                <div key={key}>
                  <div className="flex items-center justify-between text-xs">
                    <span className="inline-flex items-center gap-1.5">
                      <Icon size={10} strokeWidth={1.5} className={tone} />
                      <span className="text-slate-900">{label}</span>
                    </span>
                    <span className="font-mono text-slate-500">{score}</span>
                  </div>
                  <div className="h-1 bg-slate-100 mt-0.5 relative overflow-hidden">
                    <div className="absolute inset-y-0 left-0 bg-[#0F2847]" style={{ width: `${Math.min(100, score)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Top badges (if available) */}
          {(reputation.badges || []).length > 0 && (
            <div className="mt-3 border-t border-slate-100 pt-2">
              <div className="text-[10px] font-mono text-slate-400 mb-1.5">Top badges</div>
              <div className="flex flex-wrap gap-1.5">
                {(reputation.badges || []).slice(0, 4).map((b) => (
                  <span key={b.code} className="text-[10px] border border-slate-200 bg-slate-50 text-slate-700 px-1.5 py-0.5">
                    {b.label}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="text-[10px] font-mono text-slate-400 mt-3 leading-relaxed">
            Computed from real platform activity + OpenAlex citations (when ORCID is linked).
          </div>
        </div>
      )}
    </div>
  );
}

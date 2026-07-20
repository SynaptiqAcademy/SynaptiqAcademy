/**
 * ReputationCard — full reputation overview for the Profile page.
 *
 * Shows:
 * - Overall score + level + progress bar to next level
 * - 3 named dimensions: Research, Teaching, Community (each with bar)
 * - Earned badges grouped by category
 * - "How to improve" suggestions (adaptive by weakest dimension)
 * - Transparency note: computed from real platform activity
 */
import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  Award, BookOpen, GraduationCap, Users, TrendingUp, Star, Flame, Rocket,
  FileText, ClipboardCheck, MessageSquare, Heart, Network, Activity,
  ShieldCheck, Trophy, DollarSign, PenLine, CheckCircle2, BookCopy,
  ChevronDown, ChevronUp, ArrowRight, RefreshCw,
} from "lucide-react";
import { getLevel, getNextLevel, getProgressToNextLevel } from "../../hooks/useReputation";
import { NAVY } from "@/lib/tokens";

// Icon map for badge codes → Lucide icons
const BADGE_ICONS = {
  published_author:     BookOpen,
  active_researcher:    PenLine,
  collaboration_leader: Users,
  top_reviewer:         CheckCircle2,
  grant_contributor:    DollarSign,
  research_mentor:      GraduationCap,
  lesson_designer:      FileText,
  assessment_creator:   ClipboardCheck,
  teaching_contributor: MessageSquare,
  educational_mentor:   Heart,
  curriculum_builder:   BookCopy,
  network_builder:      Network,
  community_contributor: Activity,
  collaboration_champion: Trophy,
  trusted_member:       ShieldCheck,
  early_adopter:        Star,
  founding_member:      Flame,
  platform_pioneer:     Rocket,
};

const RARITY_TONE = {
  common:   "border-slate-200 bg-slate-50 text-slate-700",
  uncommon: "border-emerald-200 bg-emerald-50 text-emerald-800",
  rare:     "border-[#0F2847]/30 bg-[#0F2847]/5 text-[#0F2847]",
  special:  "border-amber-300 bg-amber-50 text-amber-800",
};

const CATEGORY_ORDER = ["research", "teaching", "community", "special"];
const CATEGORY_LABEL = {
  research:  "Research",
  teaching:  "Teaching",
  community: "Community",
  special:   "Special",
};

// Improvement suggestions per weakest dimension
const IMPROVE_SUGGESTIONS = {
  research: [
    { label: "Add a manuscript",         to: "/manuscripts" },
    { label: "Complete a peer review",   to: "/reviews" },
    { label: "Link your ORCID",          to: "/academic-passport" },
    { label: "Sync OpenAlex citations",  to: "/academic-passport" },
  ],
  teaching: [
    { label: "Create a lesson plan",     to: "/teaching/lesson-planner" },
    { label: "Build an assessment",      to: "/teaching/assessment-builder" },
    { label: "Start a teaching workspace", to: "/teaching/workspaces" },
    { label: "Add portfolio items",      to: "/teaching/portfolio" },
  ],
  community: [
    { label: "Join a collaboration",     to: "/collaborations" },
    { label: "Complete your profile",    to: "/academic-passport" },
    { label: "Connect with researchers", to: "/network" },
    { label: "Invite a collaborator",    to: "/marketplace" },
  ],
};

function DimensionBar({ label, score, tone }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-slate-700 font-medium">{label}</span>
        <span className="font-mono text-slate-500">{Math.round(score)}</span>
      </div>
      <div className="h-1.5 bg-slate-100 relative overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 transition-all duration-700 ${tone}`}
          style={{ width: `${Math.min(100, score)}%` }}
        />
      </div>
    </div>
  );
}

function BadgeChip({ badge }) {
  const Icon = BADGE_ICONS[badge.code] || Award;
  const tone = RARITY_TONE[badge.rarity] || RARITY_TONE.common;
  return (
    <div
      title={badge.description}
      className={`inline-flex items-center gap-1.5 border px-2.5 py-1.5 ${tone}`}
    >
      <Icon size={11} strokeWidth={1.5} className="shrink-0" />
      <span className="text-[11px] font-medium">{badge.label}</span>
    </div>
  );
}

export default function ReputationCard({ reputation, isMe = false, onSyncOpenAlex, syncing = false }) {
  const [badgesOpen, setBadgesOpen] = useState(true);
  const [improvOpen, setImprovOpen] = useState(false);

  if (!reputation) return null;

  const overall  = Math.round(reputation.overall || 0);
  const level    = getLevel(overall);
  const next     = getNextLevel(overall);
  const progress = getProgressToNextLevel(overall);

  const research  = Math.round(reputation.research_score  || 0);
  const teaching  = Math.round(reputation.teaching_score  || 0);
  const community = Math.round(reputation.community_score || 0);

  const badges = reputation.badges || [];
  const badgesByCategory: { [key: string]: any[] } = {};
  for (const b of badges) {
    if (!badgesByCategory[b.category]) badgesByCategory[b.category] = [];
    badgesByCategory[b.category].push(b);
  }

  // Weakest dimension → improvement suggestions
  const weakest = research <= teaching && research <= community
    ? "research"
    : teaching <= community
    ? "teaching"
    : "community";

  const computedAt = reputation.computed_at
    ? new Date(reputation.computed_at).toLocaleDateString("en-GB", {
        day: "numeric", month: "short", year: "numeric",
      })
    : null;

  return (
    <div className="border border-slate-200 bg-white p-6 space-y-6">
      {/* ── Header ── */}
      <div>
        <div className="overline mb-2">Reputation</div>
        <div className="flex items-center gap-4">
          <div className="font-serif text-5xl text-slate-900">{overall}</div>
          <div>
            <span className={`overline border px-2 py-0.5 ${level.tone}`}>
              {level.label}
            </span>
            {next && (
              <div className="text-[10px] font-mono text-slate-400 mt-1">
                {next.min - overall} pts to {next.short}
              </div>
            )}
          </div>
        </div>
        {/* Progress bar to next level */}
        <div className="mt-3 h-1.5 bg-slate-100 relative overflow-hidden">
          <div
            className="absolute inset-y-0 left-0 bg-[#0F2847] transition-all duration-700"
            style={{ width: `${progress}%` }}
          />
        </div>
        {next && (
          <div className="flex justify-between text-[10px] font-mono text-slate-400 mt-0.5">
            <span>{level.label}</span>
            <span>{next.short}</span>
          </div>
        )}
      </div>

      {/* ── 3 dimensions ── */}
      <div className="space-y-3 border-t border-slate-100 pt-5">
        <DimensionBar label="Research"  score={research}  tone="bg-[#0F2847]" />
        <DimensionBar label="Teaching"  score={teaching}  tone="bg-emerald-600" />
        <DimensionBar label="Community" score={community} tone="bg-slate-500" />
      </div>

      {/* ── Badges ── */}
      {badges.length > 0 && (
        <div className="border-t border-slate-100 pt-5">
          <button
            onClick={() => setBadgesOpen((o) => !o)}
            className="w-full flex items-center justify-between text-left"
          >
            <div className="overline flex items-center gap-1.5">
              <Award size={11} strokeWidth={1.5} className="text-[#0F2847]" />
              Badges ({badges.length})
            </div>
            {badgesOpen ? <ChevronUp size={13} strokeWidth={1.5} className="text-slate-400" />
                        : <ChevronDown size={13} strokeWidth={1.5} className="text-slate-400" />}
          </button>
          {badgesOpen && (
            <div className="mt-3 space-y-4">
              {CATEGORY_ORDER.map((cat) => {
                const catBadges = badgesByCategory[cat];
                if (!catBadges?.length) return null;
                return (
                  <div key={cat}>
                    <div className="text-[10px] uppercase tracking-widest text-slate-400 font-medium mb-2">
                      {CATEGORY_LABEL[cat]}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {catBadges.map((b) => <BadgeChip key={b.code} badge={b} />)}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Improvement suggestions (own profile only) ── */}
      {isMe && (
        <div className="border-t border-slate-100 pt-5">
          <button
            onClick={() => setImprovOpen((o) => !o)}
            className="w-full flex items-center justify-between text-left"
          >
            <div className="overline">Improve your reputation</div>
            {improvOpen ? <ChevronUp size={13} strokeWidth={1.5} className="text-slate-400" />
                        : <ChevronDown size={13} strokeWidth={1.5} className="text-slate-400" />}
          </button>
          {improvOpen && (
            <div className="mt-3 space-y-2">
              <div className="text-[10px] font-mono text-slate-400 mb-2">
                Suggested: strengthen your {weakest} dimension
              </div>
              {(IMPROVE_SUGGESTIONS[weakest] || []).map((s) => (
                <Link
                  key={s.to}
                  to={s.to}
                  className="flex items-center justify-between text-sm text-slate-700 hover:text-[#0F2847] group py-1"
                >
                  <span>{s.label}</span>
                  <ArrowRight size={11} strokeWidth={1.5} className="text-slate-300 group-hover:text-[#0F2847]" />
                </Link>
              ))}
              {isMe && (
                <button
                  onClick={onSyncOpenAlex}
                  disabled={syncing}
                  className="mt-2 w-full inline-flex items-center justify-center gap-2 border border-slate-300 text-xs text-slate-600 px-3 py-2 hover:border-[#0F2847] hover:text-[#0F2847] disabled:opacity-50 transition-colors"
                >
                  <RefreshCw size={11} strokeWidth={1.5} className={syncing ? "animate-spin" : ""} />
                  {syncing ? "Syncing OpenAlex…" : "Sync OpenAlex citations"}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Transparency note ── */}
      <div className="text-[10px] font-mono text-slate-400 border-t border-slate-100 pt-4 leading-relaxed">
        Computed from real platform activity: manuscripts, reviews, collaborations,
        teaching, grants, and OpenAlex citations (when ORCID is linked).
        {computedAt && <span className="ml-1">Last updated {computedAt}.</span>}
      </div>
    </div>
  );
}

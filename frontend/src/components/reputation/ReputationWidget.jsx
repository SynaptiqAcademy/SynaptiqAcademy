/**
 * ReputationWidget — compact dashboard sidebar widget.
 *
 * Shows: current level, overall score, progress bar, top 3 earned badges,
 * and context-aware suggested actions to improve reputation.
 *
 * Used in: Discover.jsx research/hybrid sidebar
 */
import React from "react";
import { Link } from "react-router-dom";
import { Award, ArrowRight, Star, Flame, Rocket, BookOpen, PenLine,
         Users, CheckCircle2, DollarSign, GraduationCap, FileText,
         ClipboardCheck, MessageSquare, Heart, Network, Activity,
         ShieldCheck, Trophy, BookCopy } from "lucide-react";
import { useReputation, getLevel, getNextLevel, getProgressToNextLevel } from "../../hooks/useReputation";
import { getDashboardMode } from "../../lib/dashboardConfig";
import { useAuth } from "../../contexts/AuthContext";
import { NAVY } from "@/lib/tokens";

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
  common:   "text-slate-600",
  uncommon: "text-emerald-700",
  rare:     "text-[#0F2847]",
  special:  "text-amber-700",
};

const SUGGESTIONS_RESEARCH = [
  { label: "Add a manuscript",         to: "/manuscripts" },
  { label: "Complete a peer review",   to: "/reviews" },
  { label: "Join a collaboration",     to: "/collaborations" },
];
const SUGGESTIONS_TEACHING = [
  { label: "Create a lesson plan",     to: "/teaching/lesson-planner" },
  { label: "Start a teaching workspace", to: "/teaching/workspaces" },
  { label: "Add portfolio items",      to: "/teaching/portfolio" },
];
const SUGGESTIONS_HYBRID = [
  { label: "Add a manuscript",         to: "/manuscripts" },
  { label: "Create a lesson plan",     to: "/teaching/lesson-planner" },
  { label: "Join a collaboration",     to: "/collaborations" },
];

export default function ReputationWidget() {
  const { user } = useAuth();
  const { data: rep, loading } = useReputation("me");
  const mode = getDashboardMode(user);

  if (loading || !rep) return null;

  const overall  = Math.round(rep.overall || 0);
  const level    = getLevel(overall);
  const next     = getNextLevel(overall);
  const progress = getProgressToNextLevel(overall);

  const badges = (rep.badges || []).slice(0, 3);
  const suggestions = mode === "teaching" ? SUGGESTIONS_TEACHING
                    : mode === "hybrid"   ? SUGGESTIONS_HYBRID
                    :                       SUGGESTIONS_RESEARCH;

  return (
    <div>
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <Award size={14} strokeWidth={1.5} className="text-[#0F2847]" />
          <h3 className="overline">Your Reputation</h3>
        </div>
        <Link to="/academic-passport" className="text-xs text-[#0F2847] hover:underline">
          Full view
        </Link>
      </div>

      {/* Score + level */}
      <div className="flex items-center gap-3 mb-3">
        <span className="font-serif text-3xl text-slate-900">{overall}</span>
        <span className={`overline border px-1.5 py-0.5 text-[10px] ${level.tone}`}>
          {level.short}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-slate-100 relative overflow-hidden mb-1">
        <div className="absolute inset-y-0 left-0 bg-[#0F2847]" style={{ width: `${progress}%` }} />
      </div>
      {next && (
        <div className="text-[10px] font-mono text-slate-400 mb-4">
          {next.min - overall} pts to {next.label}
        </div>
      )}

      {/* Top badges */}
      {badges.length > 0 && (
        <div className="mb-4 space-y-1.5">
          {badges.map((b) => {
            const Icon = BADGE_ICONS[b.code] || Award;
            const tone = RARITY_TONE[b.rarity] || RARITY_TONE.common;
            return (
              <div key={b.code} className="flex items-center gap-2">
                <Icon size={11} strokeWidth={1.5} className={`shrink-0 ${tone}`} />
                <span className={`text-[11px] font-medium ${tone}`}>{b.label}</span>
              </div>
            );
          })}
          {(rep.badges || []).length > 3 && (
            <Link to="/academic-passport" className="text-[10px] font-mono text-slate-400 hover:text-[#0F2847]">
              +{(rep.badges || []).length - 3} more badges →
            </Link>
          )}
        </div>
      )}

      {/* Suggestions */}
      <div className="border-t border-slate-100 pt-3">
        <div className="overline text-slate-400 mb-2">Earn more</div>
        {suggestions.map((s) => (
          <Link
            key={s.to}
            to={s.to}
            className="flex items-center justify-between text-sm text-slate-600 hover:text-[#0F2847] group py-1"
          >
            <span>{s.label}</span>
            <ArrowRight size={10} strokeWidth={1.5} className="text-slate-300 group-hover:text-[#0F2847]" />
          </Link>
        ))}
      </div>
    </div>
  );
}

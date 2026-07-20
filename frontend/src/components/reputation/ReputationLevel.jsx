/**
 * ReputationLevel — minimal inline reputation indicator for user cards.
 *
 * Variants:
 *   chip      — level badge only (default): "Active ·  42"
 *   score     — just the numeric score
 *   full      — level + top 2 badge icons
 *
 * Used in: Network.jsx user cards, Discover.jsx researcher list
 */
import React from "react";
import { Award, Star, Flame, Rocket, BookOpen, PenLine, Users,
         CheckCircle2, DollarSign, GraduationCap, FileText, ClipboardCheck,
         MessageSquare, Heart, Network, Activity, ShieldCheck, Trophy, BookCopy } from "lucide-react";
import { getLevel } from "../../hooks/useReputation";

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

export default function ReputationLevel({ reputation, variant = "chip", className = "" }) {
  if (!reputation) return null;

  const overall = Math.round(reputation.overall || 0);
  const level   = getLevel(overall);
  const badges  = (reputation.badges || []).slice(0, 2);

  if (variant === "score") {
    return (
      <span className={`inline-flex items-center gap-1 overline border ${level.tone} px-1.5 py-0.5 ${className}`}>
        <Award size={9} strokeWidth={1.5} />
        {overall}
      </span>
    );
  }

  if (variant === "full") {
    return (
      <div className={`inline-flex items-center gap-2 flex-wrap ${className}`}>
        <span className={`overline border px-1.5 py-0.5 inline-flex items-center gap-1 ${level.tone}`}>
          <Award size={9} strokeWidth={1.5} />
          {overall} · {level.short}
        </span>
        {badges.map((b) => {
          const Icon = BADGE_ICONS[b.code] || Award;
          return (
            <span key={b.code} title={b.label} className="text-slate-400">
              <Icon size={11} strokeWidth={1.5} />
            </span>
          );
        })}
      </div>
    );
  }

  // Default: chip
  return (
    <span className={`overline border px-1.5 py-0.5 inline-flex items-center gap-1 ${level.tone} ${className}`}>
      <Award size={9} strokeWidth={1.5} />
      {level.short} · {overall}
    </span>
  );
}

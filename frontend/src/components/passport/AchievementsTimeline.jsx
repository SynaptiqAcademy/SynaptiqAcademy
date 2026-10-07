import React from "react";
import {
  Shield, PenLine, BookOpen, FlaskConical, Tag, Users2, CheckCircle2,
  GraduationCap, Microscope, Users, Link2, Code2, Award,
  ShieldCheck, Building2, ClipboardCheck, BadgeDollarSign, Mic2,
  FolderOpen, Lock,
} from "lucide-react";
import { SectionShell } from "./PassportUI";
import { TYPE, BRD, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, SHADOW_CARD_HOVER } from "@/lib/tokens";
import { EmptyState } from "@/components/ds/EmptyState";
import { getAuthenticatedOrcidId } from "@/lib/orcid";

/**
 * computeProfileMilestones — NOT achievements. These are purely client-side,
 * non-persisted profile-completeness indicators (has a bio? has research
 * areas? etc.) with no award criteria, no timestamp, and nothing Synaptiq
 * verified or granted. Renamed from computeClientBadges (P1 Phase 7 C1.5):
 * the old name/UI implied these were earned achievements on equal footing
 * with real backend-issued badges (GET /trust/badges), and their counts were
 * summed together — exactly the "no fake achievements" problem the Phase 7
 * audit flagged. Keep this list purely as completion guidance; never count
 * it alongside, or label it as, a genuine achievement.
 */
export function computeProfileMilestones(profile, pubCount) {
  const orcidId = getAuthenticatedOrcidId(profile.orcid);
  return [
    orcidId && { icon: Shield, label: "ORCID Connected", color: "#059669", bg: "#F0FDF4" },
    profile.biography?.trim() && { icon: PenLine, label: "Researcher Profile", color: "#0F2847", bg: "#eef2f8" },
    pubCount > 0 && { icon: BookOpen, label: "Publications Imported", color: "#0F2847", bg: "#eef2f8" },
    (profile.research_areas || []).length > 0 && { icon: FlaskConical, label: "Research Areas Defined", color: "#0F2847", bg: "#eef2f8" },
    (profile.research_keywords || []).length > 0 && { icon: Tag, label: "Keywords Set", color: "#D97706", bg: "#FFFBEB" },
    profile.available_for_collaboration && { icon: Users2, label: "Open to Collaboration", color: "#059669", bg: "#F0FDF4" },
    profile.available_for_reviewing && { icon: CheckCircle2, label: "Open Reviewer", color: "#0F2847", bg: "#eef2f8" },
    (profile.teaching_areas || []).length > 0 && { icon: GraduationCap, label: "Teaching Profile", color: "#D97706", bg: "#FFFBEB" },
    (profile.methods || []).length >= 3 && { icon: Microscope, label: "Methods Expert", color: "#0F2847", bg: "#eef2f8" },
    (profile.connections_count ?? 0) > 0 && { icon: Users, label: "Network Builder", color: "#0F2847", bg: "#eef2f8" },
    (profile.google_scholar || profile.researchgate || profile.scopus_id) && { icon: Link2, label: "Academic IDs Linked", color: "#059669", bg: "#F0FDF4" },
    (profile.software_skills || []).length > 0 && { icon: Code2, label: "Software Skills", color: "#0F2847", bg: "#eef2f8" },
  ].filter(Boolean);
}

const BADGE_ICON_MAP = {
  "shield-check": ShieldCheck,
  "building-2": Building2,
  "clipboard-check": ClipboardCheck,
  "book-open": BookOpen,
  "badge-dollar-sign": BadgeDollarSign,
  "mic-2": Mic2,
  "pen-line": PenLine,
  "graduation-cap": GraduationCap,
  "award": Award,
  "flask-conical": FlaskConical,
  "folder-open": FolderOpen,
  "users-2": Users2,
};

function AchievementTile({ icon: Icon, label, color, bg, description, earned = true }) {
  return (
    <div
      title={description}
      style={{
        padding: 14, background: earned ? bg : "#F8FAFC", border: `1px solid ${earned ? color + "25" : BRD}`,
        borderRadius: 8, display: "flex", flexDirection: "column", gap: 10,
        opacity: earned ? 1 : 0.65, transition: "box-shadow 150ms ease, transform 120ms ease",
      }}
      onMouseEnter={(e) => { if (earned) { e.currentTarget.style.boxShadow = SHADOW_CARD_HOVER; e.currentTarget.style.transform = "translateY(-1px)"; } }}
      onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "none"; }}
    >
      <div style={{
        width: 32, height: 32, borderRadius: 9, flexShrink: 0,
        background: earned ? color + "20" : "#E2E8F0", display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {earned ? <Icon size={15} style={{ color }} /> : <Lock size={13} style={{ color: TEXT_MUTED }} />}
      </div>
      <div style={{ fontSize: 11.5, fontWeight: 700, color: earned ? TEXT_PRIMARY : TEXT_SECONDARY, lineHeight: 1.35 }}>{label}</div>
    </div>
  );
}

/**
 * AchievementsPanel — two DELIBERATELY separate, honestly-labeled galleries
 * (P1 Phase 7 C1.5 — see computeProfileMilestones' comment for why these
 * must never be merged):
 *  - "Achievements": ONLY the real trust badge catalogue (GET /trust/badges
 *    + /trust/badges/catalogue) — genuinely earned vs. genuinely
 *    not-yet-earned, each with its real award criterion as the tile's
 *    tooltip. Nothing here is invented; locked tiles show the actual
 *    requirement. The section's earned-count is scoped to this gallery only.
 *  - "Profile Milestones": client-computed profile-completeness indicators.
 *    Explicitly NOT called achievements, NOT counted into the Achievements
 *    total, and never implies Synaptiq awarded or verified anything.
 */
export function AchievementsPanel({ profile, pubCount = 0, catalogue = [], earnedBadges = [] }) {
  const milestones = computeProfileMilestones(profile || {}, pubCount);
  const earnedKeys = new Set(earnedBadges.map((b) => b.badge_key));

  const verifiedTiles = catalogue.map((def) => {
    const earned = earnedKeys.has(def.id);
    return {
      id: def.id,
      icon: BADGE_ICON_MAP[def.icon] || Award,
      label: def.label,
      description: def.description,
      color: def.color || "#0F2847",
      bg: (def.color || "#0F2847") + "18",
      earned,
    };
  });

  const totalEarned = verifiedTiles.filter((t) => t.earned).length;

  return (
    <SectionShell
      title="Achievements"
      subtitle={`${totalEarned} of ${verifiedTiles.length} verified credentials earned`}
    >
      {verifiedTiles.length === 0 && milestones.length === 0 ? (
        <EmptyState icon={<Award />} title="No achievements yet" description="Badges appear as you build your academic identity." />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          {verifiedTiles.length > 0 && (
            <div>
              <div style={{ ...TYPE.label, marginBottom: 10 }}>Verified Achievements</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 10 }}>
                {verifiedTiles.map((t) => <AchievementTile key={t.id} {...t} />)}
              </div>
            </div>
          )}
          {milestones.length > 0 && (
            <div>
              <div style={{ ...TYPE.label, marginBottom: 10 }}>Profile Milestones</div>
              <div style={{ fontSize: 11, color: TEXT_MUTED, marginBottom: 10, marginTop: -4 }}>
                Completion indicators, not verified achievements.
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 10 }}>
                {milestones.map((b) => <AchievementTile key={b.label} {...b} earned />)}
              </div>
            </div>
          )}
        </div>
      )}
    </SectionShell>
  );
}

export default AchievementsPanel;

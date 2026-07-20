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

function extractOrcidId(orcid) {
  if (!orcid) return null;
  if (typeof orcid === "object") return orcid.orcid_id || null;
  if (typeof orcid === "string") return orcid;
  return null;
}

export function computeClientBadges(profile, pubCount) {
  const orcidId = extractOrcidId(profile.orcid);
  return [
    orcidId && { icon: Shield, label: "ORCID Connected", color: "#059669", bg: "#F0FDF4" },
    profile.biography?.trim() && { icon: PenLine, label: "Researcher Profile", color: "#0891B2", bg: "#F0F9FF" },
    pubCount > 0 && { icon: BookOpen, label: "Publications Imported", color: "#0F2847", bg: "#EFF6FF" },
    (profile.research_areas || []).length > 0 && { icon: FlaskConical, label: "Research Areas Defined", color: "#7C3AED", bg: "#FAF5FF" },
    (profile.research_keywords || []).length > 0 && { icon: Tag, label: "Keywords Set", color: "#D97706", bg: "#FFFBEB" },
    profile.available_for_collaboration && { icon: Users2, label: "Open to Collaboration", color: "#059669", bg: "#F0FDF4" },
    profile.available_for_reviewing && { icon: CheckCircle2, label: "Open Reviewer", color: "#0891B2", bg: "#F0F9FF" },
    (profile.teaching_areas || []).length > 0 && { icon: GraduationCap, label: "Teaching Profile", color: "#D97706", bg: "#FFFBEB" },
    (profile.methods || []).length >= 3 && { icon: Microscope, label: "Methods Expert", color: "#7C3AED", bg: "#FAF5FF" },
    (profile.connections_count ?? 0) > 0 && { icon: Users, label: "Network Builder", color: "#0F2847", bg: "#EFF6FF" },
    (profile.google_scholar || profile.researchgate || profile.scopus_id) && { icon: Link2, label: "Academic IDs Linked", color: "#059669", bg: "#F0FDF4" },
    (profile.software_skills || []).length > 0 && { icon: Code2, label: "Software Skills", color: "#0891B2", bg: "#F0F9FF" },
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
        borderRadius: 12, display: "flex", flexDirection: "column", gap: 10,
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
 * AchievementsPanel — two real, distinct galleries:
 *  - "Verified Achievements": the trust badge catalogue (GET /trust/badges +
 *    /trust/badges/catalogue) — genuinely earned vs. genuinely not-yet-earned,
 *    each with its real award criterion as the tile's tooltip. Nothing here is
 *    invented; locked tiles show the actual requirement.
 *  - "Platform Achievements": lightweight client-computed milestones based on
 *    real profile completeness (unchanged logic from before, just restyled).
 */
export function AchievementsPanel({ profile, pubCount = 0, catalogue = [], earnedBadges = [] }) {
  const clientBadges = computeClientBadges(profile || {}, pubCount);
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

  const totalEarned = verifiedTiles.filter((t) => t.earned).length + clientBadges.length;

  return (
    <SectionShell
      title="Achievements"
      subtitle={`${totalEarned} earned across verified credentials and platform milestones`}
    >
      {verifiedTiles.length === 0 && clientBadges.length === 0 ? (
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
          {clientBadges.length > 0 && (
            <div>
              <div style={{ ...TYPE.label, marginBottom: 10 }}>Platform Achievements</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 10 }}>
                {clientBadges.map((b) => <AchievementTile key={b.label} {...b} earned />)}
              </div>
            </div>
          )}
        </div>
      )}
    </SectionShell>
  );
}

// Kept for compatibility with any other importer expecting the old combined name.
export const AchievementsTimeline = AchievementsPanel;
export default AchievementsPanel;

import React from "react";
import { AcademicReputationSection } from "@/components/passport/AcademicReputationSection";
import { AchievementsPanel } from "@/components/passport/AchievementsTimeline";
import { TrustHealthMini } from "@/components/passport/PassportUI";
import { TEXT_SECONDARY } from "@/lib/tokens";

/**
 * ReputationTab — P1 Phase 7C4.1 §15: deliberately does NOT include
 * verification content anymore (that's now Overview's Identity &
 * Verification section, "what Synaptiq can verify"). This tab is only
 * "what your academic activity demonstrates" — reputation/impact analytics,
 * the separate detail Trust Score, and earned achievements. UI separation
 * only; no backend systems were merged.
 */
export function ReputationTab({
  repAnalytics, researchRank, onSyncOpenAlex, syncing, onEditIdentity,
  profile, pubCount, trustBadges, badgeCatalogue, passport,
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <p style={{ fontSize: 12.5, color: TEXT_SECONDARY, margin: 0 }}>
        What your academic activity demonstrates — distinct from Overview's verification coverage.
      </p>

      <AcademicReputationSection
        analytics={repAnalytics}
        researchRank={researchRank}
        onSyncOpenAlex={onSyncOpenAlex}
        syncing={syncing}
        onEditIdentity={onEditIdentity}
      />

      <TrustHealthMini passport={passport} />

      <AchievementsPanel
        profile={profile}
        pubCount={pubCount}
        earnedBadges={trustBadges}
        catalogue={badgeCatalogue}
      />
    </div>
  );
}

export default ReputationTab;

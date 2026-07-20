import React from "react";
import { TrustVerificationSection } from "@/components/passport/TrustVerificationSection";
import { AcademicReputationSection } from "@/components/passport/AcademicReputationSection";
import { AchievementsPanel } from "@/components/passport/AchievementsTimeline";

/**
 * ReputationTab — Trust & Verification, Academic (Research/Teaching/
 * Collaboration/Reviewer) Reputation, and Achievements/Badges, all grouped in
 * one place as the spec requests. ORCID/OpenAlex connection cards live on the
 * Research tab (Research Integrations) — not duplicated here, since they're
 * the same live components and would double their API calls if rendered
 * twice.
 */
export function ReputationTab({
  profile, verification, passport, onEditIdentity,
  repAnalytics, researchRank, onSyncOpenAlex, syncing,
  pubCount, trustBadges, badgeCatalogue,
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <TrustVerificationSection
        verification={verification}
        profile={profile}
        passport={passport}
        onEditIdentity={onEditIdentity}
      />

      <AcademicReputationSection
        analytics={repAnalytics}
        researchRank={researchRank}
        onSyncOpenAlex={onSyncOpenAlex}
        syncing={syncing}
        onEditIdentity={onEditIdentity}
      />

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

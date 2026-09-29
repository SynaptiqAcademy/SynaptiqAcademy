import React from "react";
import { ArrowRight, BookOpen } from "lucide-react";
import { IdentityCard } from "@/components/passport/IdentityCard";
import { PassportCollaborationProfile } from "@/components/passport/PassportCollaborationProfile";
import { PassportCompletion } from "@/components/passport/PassportCompletion";
import { PassportNextBestAction } from "@/components/passport/PassportNextBestAction";
import { TrustVerificationSection } from "@/components/passport/TrustVerificationSection";
import { RecentActivityCard } from "@/components/passport/RecentActivityCard";
import { Card } from "@/components/ds/Card";
import { EmptyState } from "@/components/ds/EmptyState";
import { NAVY, TEXT_PRIMARY, TEXT_SECONDARY } from "@/lib/tokens";

/**
 * OverviewTab — P1 Phase 7C4.1: THE Passport, not a random card collection.
 * Tells the identity story top to bottom: completion + next step,
 * verification, academic focus, a Research Record teaser, collaboration
 * identity, then recent activity. Completion/Verification/Recent Activity
 * used to live permanently in a separate right rail on every tab — now
 * they appear once, in their natural place in this narrative, and the
 * other five tabs get their content-width back.
 */
export function OverviewTab({ profile, verification, completion, pubsTotal, recentEvents, onEdit, onGoToTab }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <PassportNextBestAction completion={completion} />

      <PassportCompletion completion={completion} />

      <TrustVerificationSection verification={verification} profile={profile} onEditIdentity={onEdit} />

      <IdentityCard profile={profile} />

      {pubsTotal > 0 ? (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ width: 34, height: 34, borderRadius: 9, background: "rgba(15,40,71,0.06)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <BookOpen size={16} style={{ color: NAVY }} />
              </span>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: TEXT_PRIMARY }}>Research Record</div>
                <div style={{ fontSize: 12.5, color: TEXT_SECONDARY, marginTop: 2 }}>{pubsTotal} publication{pubsTotal === 1 ? "" : "s"} on record</div>
              </div>
            </div>
            <button
              onClick={() => onGoToTab?.("research")}
              style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12.5, fontWeight: 600, color: NAVY, background: "none", border: "none", cursor: "pointer", padding: 0, flexShrink: 0 }}>
              View Research Record <ArrowRight size={12} />
            </button>
          </div>
        </Card>
      ) : (
        <Card padding="lg">
          <EmptyState
            icon={<BookOpen />}
            size="sm"
            title="Build your Research Record"
            description="Import verified works through ORCID or add a DOI to strengthen your academic evidence."
          />
        </Card>
      )}

      <PassportCollaborationProfile profile={profile} />

      <RecentActivityCard events={recentEvents} />
    </div>
  );
}

export default OverviewTab;

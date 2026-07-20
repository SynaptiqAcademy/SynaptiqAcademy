import React from "react";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { IdentityCard } from "@/components/passport/IdentityCard";
import { QuickActionsRail } from "@/components/passport/QuickActionsBar";
import { SectionShell, MiniStat } from "@/components/passport/PassportUI";
import { Button } from "@/components/ds/Button";
import { TYPE, NAVY } from "@/lib/tokens";

/**
 * OverviewTab — personal identity: biography, research interests, quick
 * actions, and a compact trust summary. Profile Completion / Trust Score /
 * Recent Activity are intentionally not duplicated here — they're always
 * visible in the persistent right rail (PassportRightRail), which is shown
 * on every tab including this one.
 */
export function OverviewTab({ profile, verification, passport, onGoToTab, onEdit }) {
  const verifiedCount = verification ? Object.values(verification).filter(Boolean).length : 0;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_260px]" style={{ gap: 20 }}>
      <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: 20 }}>
        <IdentityCard profile={profile} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <SectionShell title="Trust Summary">
          <div style={{ display: "flex", gap: 24, marginBottom: 14 }}>
            <MiniStat label="Trust Score" value={Math.round(passport?.trust_score ?? 0)} />
            <MiniStat label="Verified" value={`${verifiedCount} / 5`} />
          </div>
          <Button size="sm" variant="ghost" onClick={() => onGoToTab("reputation")} style={{ width: "100%" }}>
            <ShieldCheck size={13} /> View Trust &amp; Verification <ArrowRight size={12} />
          </Button>
        </SectionShell>

        <QuickActionsRail profile={profile} passport={passport} verification={verification} onEdit={onEdit} />
      </div>
    </div>
  );
}

export default OverviewTab;

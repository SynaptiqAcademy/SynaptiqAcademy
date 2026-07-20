import React from "react";
import {
  ProfileCompletionMini, TrustHealthMini, NextStepsMini, PlatformTipsMini,
} from "./PassportUI";
import { VerificationStatusCard } from "./VerificationStatusCard";
import { AIInsightsPanel } from "./AIInsightsPanel";
import { RecentActivityCard } from "./RecentActivityCard";

/**
 * PassportRightRail — the persistent contextual panel, visible across every
 * tab (Overview/Research/Teaching/Reputation/Portfolio/Analytics). Every
 * widget reuses data already fetched by AcademicPassport.jsx — nothing here
 * issues its own new request except AIInsightsPanel, which was already
 * self-contained before this refactor.
 */
export function PassportRightRail({ completion, passport, verification, recentEvents }) {
  return (
    <div className="w-full lg:w-[280px]" style={{ flexShrink: 0, display: "flex", flexDirection: "column", gap: 16 }}>
      <ProfileCompletionMini completion={completion} />
      <TrustHealthMini passport={passport} />
      <VerificationStatusCard verification={verification} />
      <NextStepsMini completion={completion} />
      <AIInsightsPanel />
      <RecentActivityCard events={recentEvents} />
      <PlatformTipsMini />
    </div>
  );
}

export default PassportRightRail;

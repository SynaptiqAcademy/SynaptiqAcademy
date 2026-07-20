import React from "react";
import { TYPE } from "@/lib/tokens";
import OrcidSettings from "@/components/orcid/OrcidSettings";
import OpenAlexSettings from "@/components/citations/OpenAlexSettings";

/**
 * ResearchIntegrationsCard — relocated from the old Settings.jsx "orcid" and
 * "integrations" sections. OrcidSettings/OpenAlexSettings are unchanged,
 * self-contained, individually-carded components — this renders them inside
 * the Trust & Verification section (which already provides its own Card
 * shell), so no extra outer card here — just a small heading to group them.
 */
export function ResearchIntegrationsCard() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={TYPE.label}>Research Platform Sync</div>
      <OrcidSettings />
      <OpenAlexSettings />
    </div>
  );
}

export default ResearchIntegrationsCard;

import React from "react";
import { Card } from "@/components/ds/Card";
import { Tag } from "@/components/ds/Tag";
import { NAVY, TEXT_MUTED, TEXT_PRIMARY } from "@/lib/tokens";

// P1 Phase 7C4.3 §13: this previously linked to "/academic-passport" — the
// page the user is already on — so "Edit Identity" silently did nothing.
// Opens the real in-place editor instead.
export function ResearchAreasCard({ profile, onEdit }) {
  const areas = profile?.research_areas || [];
  const visible = areas.slice(0, 4);
  const rest = areas.length - visible.length;

  return (
    <Card padding="lg" style={{ height: "100%" }}>
      <div style={{ fontSize: 13.5, fontWeight: 700, color: TEXT_PRIMARY, marginBottom: 10 }}>Research Areas</div>
      {areas.length === 0 ? (
        <p style={{ fontSize: 12, color: TEXT_MUTED, margin: 0 }}>
          Add research areas in{" "}
          <button onClick={onEdit} style={{ color: NAVY, background: "none", border: "none", padding: 0, font: "inherit", cursor: "pointer", textDecoration: "underline" }}>Edit Identity</button> to populate this.
        </p>
      ) : (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {visible.map((a) => <Tag key={a}>{a}</Tag>)}
          {rest > 0 && <Tag>+{rest} more</Tag>}
        </div>
      )}
    </Card>
  );
}

export default ResearchAreasCard;

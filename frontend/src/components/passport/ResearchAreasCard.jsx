import React from "react";
import { Link } from "react-router-dom";
import { Card } from "@/components/ds/Card";
import { Tag } from "@/components/ds/Tag";
import { NAVY, TEXT_MUTED, TEXT_PRIMARY } from "@/lib/tokens";

export function ResearchAreasCard({ profile }) {
  const areas = profile?.research_areas || [];
  const visible = areas.slice(0, 4);
  const rest = areas.length - visible.length;

  return (
    <Card padding="lg" style={{ height: "100%" }}>
      <div style={{ fontSize: 13.5, fontWeight: 700, color: TEXT_PRIMARY, marginBottom: 10 }}>Research Areas</div>
      {areas.length === 0 ? (
        <p style={{ fontSize: 12, color: TEXT_MUTED, margin: 0 }}>
          Add research areas in{" "}
          <Link to="/academic-passport" style={{ color: NAVY }}>Edit Identity</Link> to populate this.
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

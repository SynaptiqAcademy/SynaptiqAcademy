import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { Avatar } from "@/components/ds/Avatar";
import { TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, BRD, NAVY } from "@/lib/tokens";

export function CollaborationsCard({ collaborations = [] }) {
  return (
    <Card padding="lg" style={{ height: "100%" }}>
      <div style={{ fontSize: 13.5, fontWeight: 700, color: TEXT_PRIMARY, marginBottom: 10 }}>Collaborations</div>
      {collaborations.length === 0 ? (
        <p style={{ fontSize: 12, color: TEXT_MUTED, margin: 0 }}>No active collaborations yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column" }}>
          {collaborations.slice(0, 3).map((c, i) => (
            <div
              key={c.id || i}
              style={{
                display: "flex", alignItems: "center", gap: 8, padding: "8px 0",
                borderTop: i > 0 ? `1px solid ${BRD}` : "none",
              }}
            >
              <Avatar url={c.avatar_url} name={c.full_name || c.name} size={26} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: TEXT_PRIMARY, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {c.full_name || c.name || c.title}
                </div>
                {c.institution && <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 1 }}>{c.institution}</div>}
              </div>
              {c.project_count != null && (
                <span style={{ fontSize: 11, color: NAVY, fontWeight: 700, flexShrink: 0 }}>{c.project_count}</span>
              )}
            </div>
          ))}
        </div>
      )}
      <Link to="/collaborations" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600, color: NAVY, textDecoration: "none", marginTop: 10 }}>
        View all collaborations <ArrowRight size={11} />
      </Link>
    </Card>
  );
}

export default CollaborationsCard;

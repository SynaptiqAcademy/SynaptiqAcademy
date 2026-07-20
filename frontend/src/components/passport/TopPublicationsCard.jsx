import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, BRD } from "@/lib/tokens";

export function TopPublicationsCard({ pubs, loading }) {
  const results = [...(pubs?.results || [])]
    .sort((a, b) => (b.citations || 0) - (a.citations || 0))
    .slice(0, 3);

  return (
    <Card padding="lg" style={{ height: "100%" }}>
      <div style={{ fontSize: 13.5, fontWeight: 700, color: TEXT_PRIMARY, marginBottom: 10 }}>Top Publications</div>
      {loading ? (
        <p style={{ fontSize: 12, color: TEXT_MUTED, margin: 0 }}>Loading…</p>
      ) : results.length === 0 ? (
        <p style={{ fontSize: 12, color: TEXT_MUTED, margin: 0 }}>No publications on record yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column" }}>
          {results.map((p, i) => (
            <div
              key={p.id || i}
              style={{
                display: "flex", alignItems: "flex-start", gap: 8, padding: "8px 0",
                borderTop: i > 0 ? `1px solid ${BRD}` : "none",
              }}
            >
              <span style={{ fontSize: 12, color: TEXT_MUTED, fontWeight: 600, flexShrink: 0 }}>{i + 1}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: TEXT_PRIMARY, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {p.title}
                </div>
                <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 1 }}>
                  {p.year} {p.citations != null ? `· ${p.citations} citations` : ""}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      <Link to="/academic-passport#publications_panel" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600, color: "#0F2847", textDecoration: "none", marginTop: 10 }}>
        View all publications <ArrowRight size={11} />
      </Link>
    </Card>
  );
}

export default TopPublicationsCard;

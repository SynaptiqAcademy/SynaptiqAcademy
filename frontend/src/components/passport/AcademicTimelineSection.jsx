import React from "react";
import { NAVY, EMERALD, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, BRD } from "@/lib/tokens";
import { Card } from "@/components/ds/Card";

/**
 * AcademicTimelineSection — horizontal career timeline built from real
 * ORCID-sourced employment/education history (users.orcid_employments /
 * orcid_educations, synced by backend/services/orcid/sync.py), plus a real
 * publication-activity marker derived from the user's own publication years
 * (GET /users/:id/publications). No fabricated entries — project/grant dates
 * aren't reliably modeled in the backend, so they're deliberately left out
 * rather than guessed; renders an honest empty state if nothing is available.
 */
export function AcademicTimelineSection({ employments = [], educations = [], pubs = null }) {
  const records = [
    ...employments.map((e) => ({ ...e, kind: "Employment" })),
    ...educations.map((e) => ({ ...e, kind: "Education" })),
  ];

  const pubYears = (pubs?.results || []).map((p) => p.year).filter((y) => typeof y === "number" && y > 1900);
  if (pubYears.length > 0) {
    const minYear = Math.min(...pubYears);
    const maxYear = Math.max(...pubYears);
    records.push({
      kind: "Publications",
      role: `${pubYears.length} Publication${pubYears.length === 1 ? "" : "s"}`,
      institution: "Research output",
      start_year: minYear,
      end_year: maxYear,
      accent: EMERALD,
    });
  }

  records.sort((a, b) => (a.start_year || 0) - (b.start_year || 0));

  return (
    <Card padding="xl">
      <div style={{ fontSize: 15, fontWeight: 700, color: TEXT_PRIMARY, letterSpacing: "-0.01em", marginBottom: records.length ? 24 : 4 }}>
        Academic Timeline
      </div>

      {records.length === 0 ? (
        <p style={{ fontSize: 12.5, color: TEXT_MUTED, margin: 0 }}>
          Connect ORCID to import your employment and education history, or add publications to build a timeline.
        </p>
      ) : (
        <div style={{ display: "flex", overflowX: "auto", paddingBottom: 4 }}>
          {records.map((r, i) => {
            const isLast = i === records.length - 1;
            const accent = r.accent || NAVY;
            return (
              <div key={i} style={{ flex: "1 1 160px", minWidth: 150, maxWidth: isLast ? 200 : undefined }}>
                <div style={{ display: "flex", alignItems: "center" }}>
                  <div style={{
                    width: 12, height: 12, borderRadius: "50%", flexShrink: 0,
                    background: isLast ? accent : "#fff", border: `2px solid ${accent}`,
                  }} />
                  {!isLast && <div style={{ height: 2, background: BRD, flex: 1 }} />}
                </div>
                <div style={{ marginTop: 12, paddingRight: 12 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 700, color: TEXT_PRIMARY }}>{r.role || r.kind}</div>
                  <div style={{ fontSize: 11.5, color: TEXT_SECONDARY, marginTop: 2 }}>{r.institution}</div>
                  <div style={{ fontSize: 11, color: TEXT_MUTED, marginTop: 1 }}>
                    {r.start_year ? `${r.start_year} – ${r.end_year || "Present"}` : ""}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

export default AcademicTimelineSection;

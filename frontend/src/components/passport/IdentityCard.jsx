import React, { useState } from "react";
import { ExternalLink, Link2, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { Section } from "@/components/ds/Section";
import { TYPE, TEXT_MUTED, TEXT_SECONDARY, BRD, NAVY, WARM, EMERALD } from "@/lib/tokens";
import { ProvenanceTag, MATCHING_INPUT_FIELDS } from "@/components/passport/ProvenanceTag";

const IDENTIFIER_DEFS = [
  { key: "orcid_url",       label: "ORCID" },
  { key: "google_scholar",  label: "Google Scholar", href: (v) => `https://scholar.google.com/citations?user=${v}` },
  { key: "researchgate",    label: "ResearchGate",   href: (v) => `https://www.researchgate.net/profile/${v}` },
  { key: "scopus_id",       label: "Scopus",         href: (v) => `https://www.scopus.com/authid/detail.uri?authorId=${v}` },
  { key: "linkedin",        label: "LinkedIn",       href: (v) => `https://www.linkedin.com/in/${v}` },
  { key: "website",         label: "Website",        href: (v) => v },
];

function extractOrcidId(orcid) {
  if (!orcid) return null;
  if (typeof orcid === "object") return orcid.orcid_id || null;
  if (typeof orcid === "string") return orcid;
  return null;
}

const CHIP_COLLAPSE_THRESHOLD = 10;

/**
 * ExpertiseGroup — P1 Phase 7C4.1 §12: instead of a repeated "Used for
 * matching" pill beside every heading (the old pattern), a matching-input
 * group gets one small, subtle sparkle mark next to its heading — the
 * *meaning* of that mark is explained once, at the top of the whole
 * section (see the sectionSubtitle below), not re-explained per group.
 */
function ExpertiseGroup({ label, items = [], color = NAVY, bg, fieldKey }) {
  const [expanded, setExpanded] = useState(false);
  if (!items.length) return null;
  const usedForMatching = fieldKey && MATCHING_INPUT_FIELDS.has(fieldKey);
  const isLong = items.length > CHIP_COLLAPSE_THRESHOLD;
  const visible = isLong && !expanded ? items.slice(0, CHIP_COLLAPSE_THRESHOLD) : items;
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 8 }}>
        <div style={{ fontSize: 10.5, fontWeight: 700, color: TEXT_MUTED, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          {label}
        </div>
        {usedForMatching && (
          <Sparkles size={10} style={{ color: NAVY, opacity: 0.55 }} title="Used for collaboration matching" />
        )}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
        {visible.map((item) => (
          <span key={item} style={{
            fontSize: 12, padding: "4px 10px", fontWeight: 500,
            background: bg || (color + "12"), color, border: `1px solid ${color}35`,
          }}>
            {item}
          </span>
        ))}
        {isLong && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            style={{
              display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11.5, fontWeight: 600,
              color: TEXT_MUTED, background: "none", border: "none", cursor: "pointer", padding: "4px 2px",
            }}
          >
            {expanded ? <>Show less <ChevronUp size={12} /></> : <>+{items.length - CHIP_COLLAPSE_THRESHOLD} more <ChevronDown size={12} /></>}
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * IdentityCard — P1 Phase 7C4.1 §12: restructured from a flat wall of
 * chip-list cards into scannable expertise groups (Research Focus,
 * Specialisations, Methods, Tools, Skills, Teaching), each an honest
 * relabeling of the real stored fields — no invented categories. One
 * matching explanation at the top instead of a badge repeated on every
 * heading. Collaboration preferences (Open To / Can Contribute / Looking
 * For) moved to PassportCollaborationProfile — a distinct Passport concept
 * per the redesign brief, not part of "expertise."
 */
export function IdentityCard({ profile }) {
  if (!profile) return null;
  const orcidId = extractOrcidId(profile.orcid);

  const orcidIsAuthenticated = profile.orcid && typeof profile.orcid === "object" && !!profile.orcid.orcid_id;
  const identifiers = IDENTIFIER_DEFS
    .map((d) => {
      if (d.key === "orcid_url") {
        return orcidId
          ? { label: "ORCID", value: orcidId, href: `https://orcid.org/${orcidId}`,
              provenance: orcidIsAuthenticated ? "authenticated" : "self_declared" }
          : null;
      }
      const value = profile[d.key];
      return value ? { label: d.label, value, href: d.href(value) } : null;
    })
    .filter(Boolean);

  const allMethods = [...(profile.methods || []), ...(profile.methodological_expertise || [])]
    .filter((v, i, a) => a.indexOf(v) === i);
  const allSkills = [...(profile.skills || []), ...(profile.professional_expertise || [])]
    .filter((v, i, a) => a.indexOf(v) === i);

  const anyMatchingFieldPresent = ["research_areas", "research_interests", "research_keywords", "software_skills"]
    .some((k) => (profile[k] || []).length > 0);

  return (
    <Card padding="xl">
      <Section title="Academic Identity" gap="lg">
        {profile.biography ? (
          <p style={{ ...TYPE.body, lineHeight: 1.75, padding: "16px 18px", background: WARM, borderLeft: `3px solid ${NAVY}`, margin: 0 }}>
            {profile.biography}
          </p>
        ) : (
          <p style={{ fontSize: 13, color: TEXT_MUTED, fontStyle: "italic", margin: 0 }}>No biography yet — add one from Edit Identity.</p>
        )}

        {anyMatchingFieldPresent && (
          // P1 Phase 7C4.1: a `display:flex` paragraph containing mixed
          // text + a mid-sentence inline icon broke natural text wrapping
          // at narrow widths (each text/icon fragment wrapped as its own
          // flex item instead of flowing together) — caught live during
          // mobile visual QA. Plain inline flow avoids that entirely.
          <p style={{ fontSize: 11.5, color: TEXT_MUTED, margin: 0, lineHeight: 1.5 }}>
            <Sparkles size={11} style={{ color: NAVY, opacity: 0.55, verticalAlign: "-1px", marginRight: 5 }} />
            Synaptiq uses selected research fields, keywords, methods and tools (marked with a small sparkle icon) to improve collaborator recommendations.
          </p>
        )}

        <div className="grid sm:grid-cols-2" style={{ gap: 20 }}>
          <ExpertiseGroup label="Research Focus" items={profile.research_areas} color="#0891B2" fieldKey="research_areas" />
          <ExpertiseGroup label="Specialisations" items={profile.research_keywords} color={NAVY} fieldKey="research_keywords" />
        </div>

        {(profile.research_interests || []).length > 0 && (
          <ExpertiseGroup label="Research Interests" items={profile.research_interests} color={TEXT_SECONDARY} bg="#F8FAFC" fieldKey="research_interests" />
        )}

        <div className="grid sm:grid-cols-2" style={{ gap: 20, borderTop: `1px solid ${BRD}`, paddingTop: 18 }}>
          <ExpertiseGroup label="Methods" items={allMethods} color="#0891B2" />
          <ExpertiseGroup label="Tools" items={profile.software_skills} color="#D97706" fieldKey="software_skills" />
        </div>

        <div className="grid sm:grid-cols-2" style={{ gap: 20 }}>
          <ExpertiseGroup label="Skills" items={allSkills} color={EMERALD} />
          <ExpertiseGroup label="Teaching" items={profile.teaching_areas} color="#7C3AED" />
        </div>

        {identifiers.length > 0 && (
          <div style={{ borderTop: `1px solid ${BRD}`, paddingTop: 16 }}>
            <div style={{ fontSize: 10.5, fontWeight: 700, color: TEXT_MUTED, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>
              Academic Identifiers
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(210px, 1fr))", gap: 8 }}>
              {identifiers.map(({ label, value, href, provenance }) => (
                <a key={label} href={href} target="_blank" rel="noreferrer" style={{
                  display: "flex", alignItems: "center", gap: 8, padding: "10px 12px",
                  border: `1px solid ${BRD}`, borderRadius: 8, textDecoration: "none", color: "inherit",
                }}>
                  <Link2 size={12} style={{ color: NAVY, flexShrink: 0 }} />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontSize: 9.5, fontWeight: 700, color: TEXT_MUTED, textTransform: "uppercase" }}>{label}</div>
                    <div style={{ fontSize: 11.5, color: TEXT_SECONDARY, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{value}</div>
                    {provenance && (
                      <div style={{ marginTop: 2 }}>
                        <ProvenanceTag kind={provenance} size="sm" />
                      </div>
                    )}
                  </div>
                  <ExternalLink size={11} style={{ color: TEXT_MUTED, flexShrink: 0 }} />
                </a>
              ))}
            </div>
          </div>
        )}
      </Section>
    </Card>
  );
}

export default IdentityCard;

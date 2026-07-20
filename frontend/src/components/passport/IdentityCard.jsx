import React from "react";
import { ExternalLink, Link2 } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { Section } from "@/components/ds/Section";
import { Tag } from "@/components/ds/Tag";
import { Badge } from "@/components/ds/Badge";
import { TYPE, TEXT_MUTED, TEXT_SECONDARY, BRD, NAVY, WARM, EMERALD } from "@/lib/tokens";

const AREA_PALETTE = ["#0891B2", "#7C3AED", EMERALD, "#D97706", "#EA580C", "#8A1538", "#374151", NAVY];

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

function ChipGroup({ label, items = [], color = NAVY, bg }) {
  if (!items.length) return null;
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ ...TYPE.label, marginBottom: 8 }}>{label}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {items.map((item, i) => (
          <span key={item} style={{
            fontSize: 12, padding: "4px 10px", fontWeight: 500,
            background: bg || (color + "12"), color, border: `1px solid ${color}35`,
          }}>
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * IdentityCard — biography, research profile, availability, skills & identifiers.
 * Merges Profile.jsx's AboutSection + SkillsSection + IdentifiersSection.
 */
export function IdentityCard({ profile }) {
  if (!profile) return null;
  const orcidId = extractOrcidId(profile.orcid);
  const allMethods = [...(profile.methods || []), ...(profile.methodological_expertise || [])]
    .filter((v, i, a) => a.indexOf(v) === i);

  const identifiers = IDENTIFIER_DEFS
    .map((d) => {
      if (d.key === "orcid_url") {
        return orcidId ? { label: "ORCID", value: orcidId, href: `https://orcid.org/${orcidId}` } : null;
      }
      const value = profile[d.key];
      return value ? { label: d.label, value, href: d.href(value) } : null;
    })
    .filter(Boolean);

  const openTo = [
    profile.available_for_collaboration && "Collaboration",
    profile.available_for_supervision && "Supervision",
    profile.available_for_reviewing && "Peer Review",
    profile.available_for_consulting && "Consulting",
  ].filter(Boolean);

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

        {profile.availability && (
          <div>
            <Badge variant={profile.availability === "Available" ? "success" : "warning"} dot>
              {profile.availability}
            </Badge>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          <div>
            <ChipGroup label="Research Areas" items={profile.research_areas} color={AREA_PALETTE[0]} />
            <ChipGroup label="Research Keywords" items={profile.research_keywords} color={NAVY} />
            <ChipGroup label="Research Interests" items={profile.research_interests} color={TEXT_SECONDARY} bg="#F8FAFC" />
          </div>
          <div>
            <ChipGroup label="Open To" items={openTo} color={EMERALD} bg="#F0FDF4" />
            <ChipGroup label="Can Contribute" items={profile.can_contribute} color={NAVY} bg="#EFF6FF" />
            <ChipGroup label="Looking For" items={profile.looking_for} color="#92400E" bg="#FFFBEB" />
          </div>
        </div>

        <div style={{ borderTop: `1px solid ${BRD}`, paddingTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          <div>
            <ChipGroup label="Research Methods" items={allMethods} color="#0891B2" />
            <ChipGroup label="Software & Tools" items={profile.software_skills} color="#D97706" />
            <ChipGroup label="Academic Skills" items={profile.skills} color={EMERALD} />
          </div>
          <div>
            <ChipGroup label="Professional Expertise" items={profile.professional_expertise} color="#7C3AED" />
            <ChipGroup label="Teaching Areas" items={profile.teaching_areas} color={NAVY} />
          </div>
        </div>

        {identifiers.length > 0 && (
          <div style={{ borderTop: `1px solid ${BRD}`, paddingTop: 16 }}>
            <div style={{ ...TYPE.label, marginBottom: 10 }}>Academic Identifiers</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8 }}>
              {identifiers.map(({ label, value, href }) => (
                <a key={label} href={href} target="_blank" rel="noreferrer" style={{
                  display: "flex", alignItems: "center", gap: 8, padding: "10px 12px",
                  border: `1px solid ${BRD}`, textDecoration: "none", color: "inherit",
                }}>
                  <Link2 size={12} style={{ color: NAVY, flexShrink: 0 }} />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontSize: 9.5, fontWeight: 700, color: TEXT_MUTED, textTransform: "uppercase" }}>{label}</div>
                    <div style={{ fontSize: 11.5, color: TEXT_SECONDARY, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{value}</div>
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

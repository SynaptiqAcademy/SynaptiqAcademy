import React from "react";
import { Link } from "react-router-dom";
import {
  UserCircle2, Building2, Mail, ArrowRight,
  GraduationCap, Link2,
} from "lucide-react";
import { SectionShell, StatusCard, MiniStat } from "./PassportUI";
import { TYPE, NAVY, BRD, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY } from "@/lib/tokens";

// Maps 1:1 to real booleans on GET /api/verification/me. "Expertise" is
// deliberately labeled by what it actually measures (publication count) —
// there is no separate expert-review verification flow in the backend.
const ITEMS = [
  { key: "identity_verified",    icon: UserCircle2,   title: "Identity Verification" },
  { key: "institution_verified", icon: Building2,     title: "Institution Verification" },
  { key: "email_verified",       icon: Mail,          title: "Email Verification" },
  { key: "orcid_verified",       icon: Link2,         title: "ORCID Connection" },
  { key: "expert_verified",      icon: GraduationCap, title: "Expertise (Publication Count)" },
];

// Real profile fields, presented honestly as "linked / not linked" — there is
// no backend sync/verification pipeline for these, unlike ORCID/OpenAlex, so
// we never fabricate a completion % or "last synced" date for them.
const OTHER_PLATFORMS = [
  { key: "google_scholar", label: "Google Scholar", href: (v) => `https://scholar.google.com/citations?user=${v}` },
  { key: "researchgate",   label: "ResearchGate",    href: (v) => `https://www.researchgate.net/profile/${v}` },
  { key: "scopus_id",      label: "Scopus",          href: (v) => `https://www.scopus.com/authid/detail.uri?authorId=${v}` },
  { key: "linkedin",       label: "LinkedIn",        href: (v) => `https://www.linkedin.com/in/${v}` },
];

export function TrustVerificationSection({ verification, profile, passport, onEditIdentity, orcidSlot }) {
  if (!verification) return null;

  const verifiedCount = ITEMS.filter((i) => !!verification[i.key]).length;

  return (
    <SectionShell
      title="Trust &amp; Verification"
      subtitle="Your verified academic identity, at a glance"
      action={
        <Link to="/trust" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12.5, fontWeight: 600, color: NAVY, textDecoration: "none" }}>
          View full trust report <ArrowRight size={12} />
        </Link>
      }
    >
      <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 18, flexWrap: "wrap" }}>
        <MiniStat label="Verifications Complete" value={`${verifiedCount} / ${ITEMS.length}`} />
        {passport?.trust_score != null && <MiniStat label="Trust Score" value={Math.round(passport.trust_score)} />}
        {passport?.trust_level && <MiniStat label="Trust Level" value={passport.trust_level} color={NAVY} />}
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5" style={{ gap: 12 }}>
        {ITEMS.map(({ key, icon, title }) => (
          <StatusCard
            key={key}
            icon={icon}
            title={title}
            status={verification[key] ? "verified" : "pending"}
          />
        ))}
      </div>

      {orcidSlot && (
        <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 16 }}>
          {orcidSlot}
        </div>
      )}

      <div style={{ marginTop: 20, paddingTop: 18, borderTop: `1px solid ${BRD}` }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
          <div style={TYPE.label}>Other Research Platforms</div>
          <button
            onClick={onEditIdentity}
            style={{ fontSize: 11.5, fontWeight: 600, color: NAVY, background: "none", border: "none", cursor: "pointer", padding: 0 }}
          >
            Edit Academic Identity
          </button>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4" style={{ gap: 10 }}>
          {OTHER_PLATFORMS.map(({ key, label, href }) => {
            const value = profile?.[key];
            return value ? (
              <a
                key={key}
                href={href(value)}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8,
                  padding: "10px 12px", border: `1px solid ${BRD}`, borderRadius: 9, textDecoration: "none",
                }}
              >
                <span style={{ fontSize: 12.5, color: TEXT_PRIMARY, fontWeight: 600 }}>{label}</span>
                <span style={{ fontSize: 10.5, fontWeight: 700, color: "#059669" }}>Linked</span>
              </a>
            ) : (
              <div
                key={key}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8,
                  padding: "10px 12px", border: `1px dashed ${BRD}`, borderRadius: 9,
                }}
              >
                <span style={{ fontSize: 12.5, color: TEXT_SECONDARY }}>{label}</span>
                <span style={{ fontSize: 10.5, fontWeight: 700, color: TEXT_MUTED }}>Not linked</span>
              </div>
            );
          })}
        </div>
      </div>
    </SectionShell>
  );
}

export default TrustVerificationSection;

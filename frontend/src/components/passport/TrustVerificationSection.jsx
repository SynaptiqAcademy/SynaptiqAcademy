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
//
// This is the ONE canonical set of "verification dimensions" shown in the
// Passport verification summary — exported so every component that needs a
// "X / 5 verified" count (e.g. OverviewTab's Trust Summary mini-stat) reads
// this exact list instead of re-deriving its own. Counting
// Object.values(verification).filter(Boolean) directly is what previously
// produced the "11 / 5 Verified" bug: that response object also carries
// verification_score, verification_level, user_id, and several other
// verified_* booleans (researcher_verified, reviewer_verified, etc.) beyond
// these 5 — none of which belong in this specific summary.
// metaVerified/metaPending: honest, literally-true provenance/next-step
// text (P1 Phase 7 C2). Never claim more than the backend can prove — e.g.
// ORCID authentication is never described as legal identity verification.
export const VERIFICATION_ITEMS = [
  { key: "identity_verified",    icon: UserCircle2,   title: "Identity Verification",
    metaVerified: "System-derived from verified email + institution or ORCID",
    metaPending:  "Requires a verified email plus institution or ORCID connection" },
  { key: "institution_verified", icon: Building2,     title: "Institution Verification",
    metaVerified: "Source: institution verification request",
    metaPending:  "Self-declared — request verification below" },
  { key: "email_verified",       icon: Mail,          title: "Email Verification",
    metaVerified: "Source: account signup",
    metaPending:  "Verify your email address" },
  { key: "orcid_verified",       icon: Link2,         title: "ORCID Connection",
    metaVerified: "Source: ORCID OAuth — authenticated connection",
    metaPending:  "Connect your ORCID account" },
  { key: "expert_verified",      icon: GraduationCap, title: "Expertise (Publication Count)",
    metaVerified: "System-derived from your Research Record",
    metaPending:  "Requires 5+ publications in your Research Record" },
];

export function countVerifiedDimensions(verification) {
  if (!verification) return 0;
  return VERIFICATION_ITEMS.filter((i) => !!verification[i.key]).length;
}

const ITEMS = VERIFICATION_ITEMS;

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
        {/* Trust Score is a separate, secondary detail score (see
            TrustHealthMini) — only shown here once it's actually been
            calculated, so it can never read "0 / Unverified" next to
            verification items that are genuinely verified (P1 Phase 7 C1.1/C2). */}
        {passport?.trust_score_computed && (
          <>
            <MiniStat label="Trust Score" value={Math.round(passport.trust_score)} />
            {passport?.trust_level && <MiniStat label="Trust Level" value={passport.trust_level} color={NAVY} />}
          </>
        )}
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5" style={{ gap: 12 }}>
        {ITEMS.map(({ key, icon, title, metaVerified, metaPending }) => (
          <StatusCard
            key={key}
            icon={icon}
            title={title}
            status={verification[key] ? "verified" : "pending"}
            meta={verification[key] ? metaVerified : metaPending}
            action={
              key === "institution_verified" && !verification[key] ? (
                <Link to="/trust/institution" style={{ fontSize: 11.5, fontWeight: 600, color: NAVY, textDecoration: "none" }}>
                  Request institution verification →
                </Link>
              ) : undefined
            }
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

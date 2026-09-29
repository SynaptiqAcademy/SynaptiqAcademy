import React from "react";
import { Link } from "react-router-dom";
import {
  UserCircle2, Building2, Mail, ArrowRight, CheckCircle2, Clock,
  GraduationCap, Link2, ChevronRight,
} from "lucide-react";
import { SectionShell } from "./PassportUI";
import { EMERALD, AMBER, TYPE, NAVY, BRD, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY } from "@/lib/tokens";

// Maps 1:1 to real booleans on GET /api/verification/me. "Expertise" is
// deliberately labeled by what it actually measures (publication count) —
// there is no separate expert-review verification flow in the backend.
//
// This is the ONE canonical set of "verification dimensions" shown across
// the Passport (the hero's verification-coverage count, this section, and
// the old VerificationStatusCard — now retired, its content absorbed here
// to remove that duplicate item list). Counting
// Object.values(verification).filter(Boolean) directly is what previously
// produced the "11 / 5 Verified" bug: that response object also carries
// verification_score, verification_level, user_id, and several other
// verified_* booleans beyond these 5 — none of which belong here.
//
// metaVerified/metaPending: honest, literally-true provenance/next-step
// text (P1 Phase 7 C2). Never claim more than the backend can prove — e.g.
// ORCID authentication is never described as legal identity verification.
export const VERIFICATION_ITEMS = [
  { key: "email_verified",       icon: Mail,          title: "Email",
    metaVerified: "Source: account signup",
    metaPending:  "Verify your email address" },
  { key: "orcid_verified",       icon: Link2,         title: "ORCID",
    metaVerified: "Source: ORCID OAuth — authenticated connection",
    metaPending:  "Connect your ORCID account" },
  { key: "institution_verified", icon: Building2,     title: "Institution",
    metaVerified: "Source: institution verification request",
    metaPending:  "Self-declared" },
  { key: "identity_verified",    icon: UserCircle2,   title: "Academic Identity",
    metaVerified: "System-derived from verified email + institution or ORCID",
    metaPending:  "Requires verified email plus institution or ORCID connection" },
  { key: "expert_verified",      icon: GraduationCap, title: "Research Expertise",
    metaVerified: "System-derived from your Research Record",
    metaPending:  "Requires 5+ publications in your Research Record" },
];

export function countVerifiedDimensions(verification) {
  if (!verification) return 0;
  return VERIFICATION_ITEMS.filter((i) => !!verification[i.key]).length;
}

// Real profile fields, presented honestly as "linked / not linked" — there is
// no backend sync/verification pipeline for these, unlike ORCID/OpenAlex, so
// we never fabricate a completion % or "last synced" date for them.
const OTHER_PLATFORMS = [
  { key: "google_scholar", label: "Google Scholar", href: (v) => `https://scholar.google.com/citations?user=${v}` },
  { key: "researchgate",   label: "ResearchGate",    href: (v) => `https://www.researchgate.net/profile/${v}` },
  { key: "scopus_id",      label: "Scopus",          href: (v) => `https://www.scopus.com/authid/detail.uri?authorId=${v}` },
  { key: "linkedin",       label: "LinkedIn",        href: (v) => `https://www.linkedin.com/in/${v}` },
];

/**
 * VerificationRow — one full-width, readable row per dimension. Replaces
 * the old 5-column StatusCard grid, whose narrow columns caused labels
 * like "Expertise (Publication Count)" and provenance text to wrap
 * awkwardly (P1 Phase 7C4.1 §11/§E). Status is never color-only — every
 * row carries an icon + text label alongside the color.
 */
function VerificationRow({ icon: Icon, title, verified, meta, action }) {
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 12, padding: "14px 0",
      borderBottom: `1px solid ${BRD}`,
    }}>
      <span style={{
        width: 34, height: 34, borderRadius: 9, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
        background: verified ? `${EMERALD}18` : `${AMBER}18`,
      }}>
        <Icon size={16} style={{ color: verified ? EMERALD : AMBER }} />
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 13.5, fontWeight: 700, color: TEXT_PRIMARY }}>{title}</span>
          {verified ? (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11, fontWeight: 700, color: EMERALD }}>
              <CheckCircle2 size={12} /> Verified
            </span>
          ) : (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11, fontWeight: 700, color: AMBER }}>
              <Clock size={11} /> Pending
            </span>
          )}
        </div>
        {meta && <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 3, lineHeight: 1.5 }}>{meta}</div>}
        {action && <div style={{ marginTop: 6 }}>{action}</div>}
      </div>
    </div>
  );
}

export function TrustVerificationSection({ verification, profile, onEditIdentity }) {
  if (!verification) return null;

  return (
    <SectionShell
      title="Identity &amp; Verification"
      subtitle="What Synaptiq can verify about your academic identity"
      action={
        <Link to="/trust" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12.5, fontWeight: 600, color: NAVY, textDecoration: "none" }}>
          View full trust report <ArrowRight size={12} />
        </Link>
      }
    >
      <div>
        {VERIFICATION_ITEMS.map(({ key, icon, title, metaVerified, metaPending }) => (
          <VerificationRow
            key={key}
            icon={icon}
            title={title}
            verified={!!verification[key]}
            meta={verification[key] ? metaVerified : metaPending}
            action={
              key === "institution_verified" && !verification[key] ? (
                <Link to="/trust/institution" style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11.5, fontWeight: 600, color: NAVY, textDecoration: "none" }}>
                  Request institution verification <ChevronRight size={11} />
                </Link>
              ) : undefined
            }
          />
        ))}
      </div>

      <div style={{ marginTop: 20, paddingTop: 18, borderTop: `1px solid ${BRD}` }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10, flexWrap: "wrap", gap: 8 }}>
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

import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  UserCircle2, Building2, Mail, ArrowRight, CheckCircle2, Clock,
  BookOpen, Link2, ChevronRight, AlertTriangle,
} from "lucide-react";
import { SectionShell } from "./PassportUI";
import { EMERALD, AMBER, CRIMSON, TYPE, NAVY, BRD, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY } from "@/lib/tokens";
import api from "@/lib/api";

// Maps 1:1 to real booleans on GET /api/verification/me. Kept as the ONE
// canonical set of "verification dimensions" shown across the Passport (the
// header's coverage count and this section both read from here) — counting
// Object.values(verification).filter(Boolean) directly is what previously
// produced the "11 / 5 Verified" bug (P1 Phase 7 C1). Only the `title`/copy
// changed in P1 Phase 7C4.4 (Identity & Verification → Academic
// Verification rewrite) — the keys and what each one measures are
// unchanged, per that phase's "preserve backend semantics" constraint.
export const VERIFICATION_ITEMS = [
  { key: "email_verified",       icon: Mail,          title: "Email" },
  { key: "orcid_verified",       icon: Link2,         title: "ORCID" },
  { key: "institution_verified", icon: Building2,     title: "Institution" },
  { key: "identity_verified",    icon: UserCircle2,   title: "Academic Identity" },
  { key: "expert_verified",      icon: BookOpen,      title: "Research Record" },
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

const VERIFIED_VIA_LABELS = {
  institutional_email: "institutional email",
  email_domain: "institutional email domain",
  admin_approval: "admin review",
  creator: "institution registration",
};

/**
 * VerificationRow — one full-width, readable row per dimension. `status`
 * drives both the icon color and the status pill text/tone (verified /
 * pending / attention), so a row is never reduced to a plain boolean the
 * way "Pending" used to cover every non-verified state (P1 Phase 7C4.4 §E —
 * "Not verified" / "Verification in progress" / "Verified" / "Action
 * required" are visibly different, not all the same amber dot).
 */
function VerificationRow({ icon: Icon, title, status, statusLabel, meta, action }) {
  const tone = status === "verified" ? EMERALD : status === "attention" ? CRIMSON : AMBER;
  const StatusIcon = status === "verified" ? CheckCircle2 : status === "attention" ? AlertTriangle : Clock;
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 12, padding: "14px 0",
      borderBottom: `1px solid ${BRD}`,
    }}>
      <span style={{
        width: 34, height: 34, borderRadius: 9, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
        background: `${tone}18`,
      }}>
        <Icon size={16} style={{ color: tone }} />
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 13.5, fontWeight: 700, color: TEXT_PRIMARY }}>{title}</span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11, fontWeight: 700, color: tone }}>
            <StatusIcon size={11} /> {statusLabel}
          </span>
        </div>
        {meta && <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 3, lineHeight: 1.5 }}>{meta}</div>}
        {action && <div style={{ marginTop: 6 }}>{action}</div>}
      </div>
    </div>
  );
}

function ActionLink({ onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11.5, fontWeight: 600, color: NAVY, background: "none", border: "none", padding: 0, cursor: "pointer" }}
    >
      {children} <ChevronRight size={11} />
    </button>
  );
}

/**
 * TrustVerificationSection — "Academic Verification" (P1 Phase 7C4.4 §A: was
 * "Identity & Verification", explained in implementation-rule language like
 * "Requires verified email plus institution or ORCID connection"). Every row
 * now answers plain-language what/current-state/next-action instead of
 * exposing the backend's boolean requirements.
 */
export function TrustVerificationSection({
  verification, profile, onEditIdentity, onConnectOrcid, orcidConfigured = true,
  institutionStatus, onVerifyInstitution, pubsTotal = 0, onGoToResearch,
}) {
  const [resending, setResending] = useState(false);
  if (!verification) return null;

  const resendEmailVerification = async () => {
    if (!profile?.email || resending) return;
    setResending(true);
    try {
      await api.post("/auth/resend-verification", { email: profile.email });
      toast.success("Confirmation email sent — check your inbox");
    } catch {
      toast.error("Could not send confirmation email");
    } finally {
      setResending(false);
    }
  };

  const instState = institutionStatus?.state || (verification.institution_verified ? "verified" : "not_verified");
  const instName = institutionStatus?.institution_name || profile?.institution;

  return (
    <SectionShell
      title="Academic Verification"
      subtitle="Build a trusted Academic Passport by verifying your information and research record."
      action={
        <Link to="/trust" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12.5, fontWeight: 600, color: NAVY, textDecoration: "none" }}>
          View full trust report <ArrowRight size={12} />
        </Link>
      }
    >
      <div style={{ fontSize: 11.5, color: TEXT_MUTED, marginBottom: 4 }}>
        Academic verification · {countVerifiedDimensions(verification)} of {VERIFICATION_ITEMS.length} complete
      </div>

      <div>
        {/* Email */}
        {verification.email_verified ? (
          <VerificationRow icon={Mail} title="Email" status="verified" statusLabel="Verified"
            meta="Your email address has been confirmed." />
        ) : (
          <VerificationRow icon={Mail} title="Email" status="pending" statusLabel="Not yet verified"
            meta="Confirm your email address to activate full verification."
            action={<ActionLink onClick={resendEmailVerification}>{resending ? "Sending…" : "Resend confirmation email"}</ActionLink>}
          />
        )}

        {/* ORCID */}
        {verification.orcid_verified ? (
          <VerificationRow icon={Link2} title="ORCID" status="verified" statusLabel="Connected"
            meta="Your ORCID account is authenticated and confirms your researcher identity." />
        ) : (
          <VerificationRow icon={Link2} title="ORCID" status="pending" statusLabel="Not connected"
            meta="Connect your ORCID account to confirm your researcher identity."
            action={
              orcidConfigured
                ? <ActionLink onClick={onConnectOrcid}>Connect ORCID</ActionLink>
                : <span style={{ fontSize: 11, color: TEXT_MUTED, fontStyle: "italic" }}>ORCID connect is pending admin setup</span>
            }
          />
        )}

        {/* Institution */}
        {instState === "verified" ? (
          <VerificationRow icon={Building2} title="Institution" status="verified" statusLabel="Verified"
            meta={
              <>
                {instName}
                {institutionStatus?.verified_via && (
                  <> · Verified via {VERIFIED_VIA_LABELS[institutionStatus.verified_via] || institutionStatus.verified_via}</>
                )}
              </>
            }
          />
        ) : instState === "in_progress" ? (
          <VerificationRow icon={Building2} title="Institution" status="pending" statusLabel="Verification in progress"
            meta={`We're reviewing your affiliation with ${instName || "your institution"}.`} />
        ) : instState === "rejected" ? (
          <VerificationRow icon={Building2} title="Institution" status="attention" statusLabel="Action required"
            meta="Your submitted evidence didn't confirm your affiliation. You can try again with more evidence."
            action={<ActionLink onClick={onVerifyInstitution}>Try again</ActionLink>}
          />
        ) : (
          <VerificationRow icon={Building2} title="Institution" status="pending" statusLabel="Not verified"
            meta={instName ? `Verify your affiliation with ${instName}.` : "Add your institution to your profile, then verify your affiliation."}
            action={<ActionLink onClick={onVerifyInstitution}>Verify institution</ActionLink>}
          />
        )}

        {/* Academic Identity */}
        {verification.identity_verified ? (
          <VerificationRow icon={UserCircle2} title="Academic Identity" status="verified" statusLabel="Verified"
            meta="Confirmed from your verified email plus institution or ORCID connection." />
        ) : (
          <VerificationRow icon={UserCircle2} title="Academic Identity" status="pending" statusLabel="Not yet verified"
            meta={
              verification.email_verified
                ? "Connect ORCID or verify your institutional affiliation to strengthen your academic identity."
                : "Confirm your email, then connect ORCID or verify your institutional affiliation, to strengthen your academic identity."
            }
          />
        )}

        {/* Research Record */}
        {verification.expert_verified ? (
          <VerificationRow icon={BookOpen} title="Research Record" status="verified" statusLabel="Verified"
            meta="Confirmed from your Research Record." />
        ) : (
          <VerificationRow icon={BookOpen} title="Research Record" status="pending" statusLabel={`${Math.min(pubsTotal, 5)} of 5 publications recorded`}
            meta="Add or import publications to strengthen your verified research record."
            action={<ActionLink onClick={onGoToResearch}>Add or import publications</ActionLink>}
          />
        )}
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

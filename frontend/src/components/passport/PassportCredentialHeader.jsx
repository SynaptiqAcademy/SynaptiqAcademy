import React from "react";
import { Edit3, Building2, CheckCircle2, Share2, Download, Copy } from "lucide-react";
import { toast } from "sonner";
import { Avatar } from "@/components/ds/Avatar";
import OrcidBadge from "@/components/orcid/OrcidBadge";
import { NAVY, NAVY2, WHITE } from "@/lib/tokens";
import { getAuthenticatedOrcidId } from "@/lib/orcid";
import { VERIFICATION_ITEMS, countVerifiedDimensions } from "@/components/passport/TrustVerificationSection";

/**
 * PassportCredentialHeader — P1 Phase 7C4.1. Replaces the old PassportHero,
 * which repeated a 7-counter analytics ribbon (Publications/Citations/
 * Projects/Grants/Achievements/Workspaces/AI Sessions) inside the primary
 * identity credential — exactly what the redesign brief calls out as
 * wrong ("do NOT display seven analytics counters in the primary credential
 * header... AI sessions especially are not a core academic identity
 * credential"). Those numbers aren't lost — Research/Teaching/Reputation
 * already show them in context; repeating them here just diluted the
 * identity/verification/completion signal.
 *
 * Deliberately holds ONLY high-value identity information: photo, name,
 * role, institution, authenticated ORCID, verification coverage, the
 * Academic Fingerprint, Passport completeness, and primary actions.
 */
function Pill({ tone = "neutral", children }) {
  const bg = tone === "positive" ? "rgba(56,189,248,0.16)" : "rgba(255,255,255,0.1)";
  const border = tone === "positive" ? "rgba(56,189,248,0.35)" : "rgba(255,255,255,0.16)";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12, fontWeight: 600,
      padding: "5px 12px", borderRadius: 100, background: bg,
      border: `1px solid ${border}`, color: WHITE, lineHeight: 1.2,
    }}>
      {children}
    </span>
  );
}

function ActionButton({ icon: Icon, label, onClick, primary }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12.5, fontWeight: 600,
        padding: "8px 14px", borderRadius: 8, cursor: "pointer",
        background: primary ? WHITE : "rgba(255,255,255,0.08)",
        color: primary ? NAVY : WHITE,
        border: primary ? "none" : "1px solid rgba(255,255,255,0.2)",
      }}
    >
      <Icon size={13} /> {label}
    </button>
  );
}

export function PassportCredentialHeader({ profile, passport, verification, completion, onEdit, onShare, onExport }) {
  const orcidId = getAuthenticatedOrcidId(profile?.orcid);
  const verifiedCount = countVerifiedDimensions(verification);
  const totalVerification = VERIFICATION_ITEMS.length;
  const institutionPending = !!(profile?.institution && verification && !verification.institution_verified);
  const fingerprint = passport?.academic_fingerprint?.display;
  const completionPct = completion?.percentage;

  const copyFingerprint = () => {
    if (!fingerprint) return;
    navigator.clipboard?.writeText(fingerprint).then(() => toast.success("Passport ID copied"));
  };

  return (
    <div style={{
      borderRadius: 16, padding: "28px 28px 24px", width: "100%", boxSizing: "border-box",
      background: `linear-gradient(135deg, ${NAVY} 0%, ${NAVY2} 100%)`, color: WHITE,
    }}>
      <div style={{ display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{ width: 76, height: 76, borderRadius: "50%", border: "3px solid rgba(255,255,255,0.2)", overflow: "hidden", flexShrink: 0 }}>
          <Avatar url={profile?.avatar_url} name={profile?.full_name} size={76} />
        </div>

        <div style={{ flex: "1 1 320px", minWidth: 0 }}>
          <h1 style={{
            fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.35rem, 2.4vw, 1.65rem)",
            fontWeight: 700, letterSpacing: "-0.02em", margin: 0, color: WHITE, lineHeight: 1.2,
          }}>
            {profile?.full_name || "—"}
          </h1>

          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.7)", marginTop: 5, lineHeight: 1.5 }}>
            {[profile?.academic_role, profile?.professional_role].filter(Boolean).join(" · ")}
            {(profile?.institution || profile?.department) && (
              <div style={{ display: "flex", alignItems: "center", gap: 5, color: "rgba(255,255,255,0.55)", fontSize: 12.5, marginTop: 3 }}>
                <Building2 size={11} style={{ flexShrink: 0 }} />
                <span style={{ wordBreak: "break-word" }}>{[profile.institution, profile.department].filter(Boolean).join(" · ")}</span>
              </div>
            )}
          </div>

          <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
            {orcidId ? (
              <Pill tone="positive"><OrcidBadge orcidId={orcidId} size="sm" verified testId="passport-orcid-badge" /> ORCID authenticated</Pill>
            ) : (
              <Pill>ORCID not connected</Pill>
            )}
            {profile?.institution && (
              institutionPending
                ? <Pill>Institution verification pending</Pill>
                : verification?.institution_verified && <Pill tone="positive"><CheckCircle2 size={12} /> Institution verified</Pill>
            )}
            {completionPct != null && (
              <Pill>{completionPct}% Passport complete</Pill>
            )}
          </div>
        </div>

        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Academic Passport
          </div>
          {fingerprint && (
            <button
              onClick={copyFingerprint}
              title="Copy Passport ID"
              style={{
                display: "inline-flex", alignItems: "center", gap: 6, marginTop: 4, background: "none", border: "none",
                cursor: "pointer", color: "rgba(255,255,255,0.75)", fontFamily: "monospace", fontSize: 12.5, padding: 0,
              }}
            >
              {fingerprint} <Copy size={11} />
            </button>
          )}
          <div style={{ fontSize: 11.5, color: "rgba(255,255,255,0.5)", marginTop: 8 }}>
            Academic verification · {verifiedCount} of {totalVerification} complete
          </div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 20, flexWrap: "wrap", borderTop: "1px solid rgba(255,255,255,0.12)", paddingTop: 16 }}>
        <ActionButton icon={Edit3} label="Edit Passport" onClick={onEdit} primary />
        <ActionButton icon={Share2} label="Share" onClick={onShare} />
        <ActionButton icon={Download} label="Export Passport" onClick={onExport} />
      </div>
    </div>
  );
}

export default PassportCredentialHeader;

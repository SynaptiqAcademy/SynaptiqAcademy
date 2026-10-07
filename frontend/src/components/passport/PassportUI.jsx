import React from "react";
import { CheckCircle2, Clock, XCircle, ShieldCheck } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { ProgressRing } from "@/components/ds/Progress";
import { TYPE, NAVY, BRD, EMERALD, AMBER, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, SHADOW_CARD_HOVER } from "@/lib/tokens";

/**
 * Shared premium building blocks reused across every "bottom half" Academic
 * Passport section (Trust & Verification, Academic Reputation, Achievements,
 * etc.) so the whole page reads as one continuous design language instead of
 * a patchwork of one-off card styles.
 */

// ── Status vocabulary — consistent colors across every verification tile ──────
export const STATUS = {
  verified:  { label: "Verified",        color: EMERALD, bg: "#ECFDF5", Icon: CheckCircle2 },
  pending:   { label: "Pending",         color: AMBER,   bg: "#FFFBEB", Icon: Clock },
  attention: { label: "Needs Attention", color: "#DC2626", bg: "#FEF2F2", Icon: XCircle },
  none:      { label: "Not Connected",   color: TEXT_MUTED, bg: "#F1F5F9", Icon: XCircle },
};

export function StatusPill({ status = "pending" }) {
  const s = STATUS[status] || STATUS.pending;
  const { Icon } = s;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 700,
      padding: "3px 9px", borderRadius: 100, background: s.bg, color: s.color,
    }}>
      <Icon size={11} /> {s.label}
    </span>
  );
}

/**
 * StatusCard — the executive-dashboard tile used across Trust & Verification.
 * icon, title, status pill, optional % complete, optional meta line, optional
 * action, optional expandable detail — every field is optional so tiles never
 * fabricate data that isn't real.
 */
export function StatusCard({ icon: Icon, title, status = "pending", meta, action, children, expanded, onToggle }) {
  const s = STATUS[status] || STATUS.pending;
  const clickable = !!onToggle;
  return (
    <div
      onClick={onToggle}
      style={{
        background: "#fff", border: `1px solid ${BRD}`, borderRadius: 8, padding: 16,
        cursor: clickable ? "pointer" : "default", transition: "box-shadow 150ms ease, border-color 150ms ease",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.boxShadow = SHADOW_CARD_HOVER; e.currentTarget.style.borderColor = "rgba(15,23,42,0.14)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.borderColor = BRD; }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <div style={{
          width: 34, height: 34, borderRadius: 9, flexShrink: 0,
          background: s.bg, display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Icon size={16} style={{ color: s.color }} />
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY, lineHeight: 1.3 }}>{title}</div>
          <div style={{ marginTop: 6 }}><StatusPill status={status} /></div>
        </div>
      </div>
      {meta && <div style={{ ...TYPE.caption, marginTop: 10 }}>{meta}</div>}
      {action && <div style={{ marginTop: 10 }}>{action}</div>}
      {expanded && children && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${BRD}` }}>
          {children}
        </div>
      )}
    </div>
  );
}

/** SectionShell — consistent header (title + subtitle + right action) used by every bottom-half section. */
export function SectionShell({ title, subtitle, action, children }) {
  return (
    <Card padding="xl">
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, marginBottom: 18, flexWrap: "wrap" }}>
        <div>
          <h2 style={{ ...TYPE.h2, margin: 0 }}>{title}</h2>
          {subtitle && <p style={{ ...TYPE.bodySm, margin: "4px 0 0" }}>{subtitle}</p>}
        </div>
        {action && <div style={{ flexShrink: 0 }}>{action}</div>}
      </div>
      {children}
    </Card>
  );
}

/** MiniStat — small label/value pair used in "at a glance" rails. */
export function MiniStat({ label, value, color }) {
  return (
    <div>
      <div style={{ fontFamily: "'Newsreader Variable', Newsreader, Georgia, serif", fontSize: 20, fontWeight: 700, color: color || TEXT_PRIMARY, lineHeight: 1 }}>{value}</div>
      <div style={{ ...TYPE.meta, marginTop: 4 }}>{label}</div>
    </div>
  );
}

/** RailCard — compact card shell for the persistent right rail (smaller than SectionShell, which is for full-width main content). */
export function RailCard({ title, icon: Icon, action, children }) {
  return (
    <Card padding="lg">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {Icon && <Icon size={13} style={{ color: NAVY }} />}
          <span style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY }}>{title}</span>
        </div>
        {action}
      </div>
      {children}
    </Card>
  );
}

/**
 * TrustHealthMini — secondary-detail trust score widget (Passport V2: this
 * score is intentionally NOT the primary identity/verification signal —
 * see VerificationStatusCard / TrustVerificationSection for that, both
 * driven by verification_profiles). trust_score/trust_level come from the
 * separate trust_scores collection, which is only computed when a user
 * visits /trust/score or /trust/overview — never by viewing the Passport
 * (Passport load stays read-only). Most accounts have never triggered that
 * computation, so a bare "0 / Unverified" here does NOT mean the account
 * is actually unverified — passport.trust_score_computed distinguishes
 * "never calculated" from a genuinely low real score.
 */
export function TrustHealthMini({ passport }) {
  if (!passport) return null;
  if (!passport.trust_score_computed) {
    return (
      <RailCard title="Trust Health" icon={ShieldCheck}>
        <div style={{ fontSize: 12.5, color: TEXT_MUTED, lineHeight: 1.5 }}>
          Not yet calculated. This is a separate detail score from your verification status above —
          it has no bearing on whether your identity, email, or ORCID are verified.
        </div>
      </RailCard>
    );
  }
  const score = Math.round(passport.trust_score ?? 0);
  const color = score >= 70 ? EMERALD : score >= 40 ? AMBER : TEXT_MUTED;
  return (
    <RailCard title="Trust Health" icon={ShieldCheck}>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <ProgressRing value={score} max={100} size="sm" colorByValue />
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY }}>{passport.trust_level || "Unverified"}</div>
          <div style={{ ...TYPE.caption, marginTop: 2 }}>Trust score {score}/100</div>
        </div>
      </div>
    </RailCard>
  );
}

export default StatusCard;

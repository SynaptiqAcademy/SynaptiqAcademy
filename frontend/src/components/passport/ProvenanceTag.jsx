import React from "react";
import { Link2, ShieldCheck, Building2, Sparkles, Info } from "lucide-react";
import { TEXT_MUTED, EMERALD, NAVY, AMBER } from "@/lib/tokens";

/**
 * ProvenanceTag — Passport V2 (P1 Phase 7 C2). Human-readable labels for the
 * seven provenance categories from the Phase 7 audit (AUTHENTICATED,
 * EXTERNALLY_VERIFIED, INSTITUTION_VERIFIED, SYSTEM_VERIFIED, SELF_DECLARED,
 * DERIVED, UNKNOWN). The raw enum names are never shown to users — only
 * this UI copy. Every label here must be literally true for the data it's
 * attached to; never attach a stronger claim than the system can prove.
 *
 * IMPORTANT: "authenticated" here means an authenticated OAuth connection
 * (e.g. ORCID) — never "identity verified" or "legal identity verified".
 * See lib/orcid.js and services/verification/profile_service.py for what
 * "authenticated"/"verified" actually mean in this codebase.
 */
const KINDS = {
  authenticated: { icon: Link2, color: EMERALD, label: "Authenticated connection" },
  externally_verified: { icon: ShieldCheck, color: EMERALD, label: "Externally verified" },
  institution_verified: { icon: Building2, color: EMERALD, label: "Institution verified" },
  system_verified: { icon: ShieldCheck, color: NAVY, label: "System-derived" },
  self_declared: { icon: Info, color: TEXT_MUTED, label: "Self-declared" },
  derived: { icon: Sparkles, color: NAVY, label: "System-derived" },
  pending: { icon: Info, color: AMBER, label: "Verification pending" },
};

export function ProvenanceTag({ kind, source, size = "sm" }) {
  const def = KINDS[kind];
  if (!def) return null;
  const { icon: Icon, color, label } = def;
  const fontSize = size === "sm" ? 10.5 : 12;
  return (
    <span
      style={{
        display: "inline-flex", alignItems: "center", gap: 4, fontSize, fontWeight: 600,
        color, whiteSpace: "nowrap",
      }}
      title={source ? `Source: ${source}` : undefined}
    >
      <Icon size={fontSize + 1} />
      {label}
      {source && <span style={{ color: TEXT_MUTED, fontWeight: 500 }}>· {source}</span>}
    </span>
  );
}

/**
 * MatchingInputBadge — subtle "Used for collaboration matching" indicator
 * for Academic Identity fields (P1 Phase 7 C2/§8). Only render this next to
 * a field that is ACTUALLY consumed by services/collab_intelligence/
 * matching_engine.py — see MATCHING_INPUT_FIELDS below, the audited source
 * of truth. Never attach it to a field just because it looks related.
 */
export function MatchingInputBadge() {
  return (
    <span
      title="Synaptiq uses this information to find academically relevant collaborators."
      style={{
        display: "inline-flex", alignItems: "center", gap: 3, fontSize: 9.5, fontWeight: 700,
        color: NAVY, textTransform: "uppercase", letterSpacing: "0.04em",
        padding: "2px 6px", borderRadius: 100, background: "rgba(15,40,71,0.07)",
      }}
    >
      <Sparkles size={9} /> Used for matching
    </span>
  );
}

// Source of truth: services/collab_intelligence/researcher_profiler.py +
// matching_engine.py (P1 Phase 6 audit). CORE = research_similarity/
// complementarity/methodological_compatibility inputs (weights 0.25/0.20/
// 0.15). SECONDARY = smaller-weight dimensions (institution/career-stage/
// availability/reputation compatibility, weights <=0.07). research_interests
// is only a fallback used when research_areas is empty — still a genuine
// matching input, so it's included. Do NOT add skills,
// methodological_expertise, primary_domain, department, or bio here — the
// Phase 6/7 audits confirmed the canonical matcher does not consume them.
export const MATCHING_INPUT_FIELDS = new Set([
  "research_areas",
  "research_interests",
  "research_keywords",
  "methods",
  "software_skills",
  "institution",
  "academic_role",
  "user_type",
]);

export default ProvenanceTag;

import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { NAVY, EMERALD, TEXT_PRIMARY, TEXT_SECONDARY } from "@/lib/tokens";
import { pickNextBestAction } from "@/lib/passportCompletion";

// Honest, deterministic "why this helps" copy for each real canonical
// completion item (services/profile_completion.py) — concise, no
// overpromising (P1 Phase 7C4.1 §23). No AI, no credits, no invented
// recommendations — purely the highest-point unearned item from the one
// canonical completion source.
const BENEFIT_COPY = {
  avatar: "A profile photo makes your Passport recognizable to collaborators.",
  biography: "A short biography helps other researchers understand your focus.",
  institution: "Your institution strengthens your academic affiliation evidence.",
  keywords: "Research keywords improve how accurately Synaptiq finds relevant collaborators for you.",
  methods: "Listing your research methods makes matching more relevant.",
  social: "Linking an academic profile adds another point of reference to your identity.",
  availability: "Setting your availability tells collaborators whether you're open to new work.",
  orcid_connected: "An authenticated ORCID connection strengthens your research provenance.",
  publications: "Importing your publications builds your Research Record.",
  employment: "Employment history adds career context to your Passport.",
  education: "Education history completes your academic background.",
};

export function PassportNextBestAction({ completion }) {
  const navigate = useNavigate();
  if (!completion) return null;

  const next = pickNextBestAction(completion);
  if (!next) return null;

  return (
    <Card padding="lg" style={{ border: `1px solid ${NAVY}25`, background: "linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%)" }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <span style={{ width: 30, height: 30, borderRadius: 9, background: `${EMERALD}18`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <Sparkles size={14} style={{ color: EMERALD }} />
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 10.5, fontWeight: 700, color: TEXT_SECONDARY, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Recommended next step
          </div>
          <div style={{ fontSize: 14.5, fontWeight: 700, color: TEXT_PRIMARY, marginTop: 3 }}>{next.action_label || next.label}</div>
          {BENEFIT_COPY[next.key] && (
            <p style={{ fontSize: 12.5, color: TEXT_SECONDARY, margin: "4px 0 0", lineHeight: 1.5 }}>{BENEFIT_COPY[next.key]}</p>
          )}
        </div>
        {next.action && (
          <button
            onClick={() => navigate(next.action)}
            style={{
              display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12.5, fontWeight: 700,
              padding: "8px 14px", borderRadius: 8, background: NAVY, color: "#fff", border: "none",
              cursor: "pointer", flexShrink: 0,
            }}
          >
            {next.action_label || "Continue"} <ArrowRight size={12} />
          </button>
        )}
      </div>
    </Card>
  );
}

export default PassportNextBestAction;

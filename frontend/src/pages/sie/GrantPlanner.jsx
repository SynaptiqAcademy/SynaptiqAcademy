import React from "react";
import { useNavigate } from "react-router-dom";
import { Trophy, ArrowRight } from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Button, Callout, H4 } from "@/components/ds";

const STEPS = [
  { title: "Discover Grant Opportunities", desc: "Use Grant Hub to find open calls aligned with your research profile.", url: "/grant-hub", color: "#ec4899" },
  { title: "Build Your Consortium", desc: "Use Grant Collaboration Hub to find and onboard partner institutions.", url: "/grant-hub", color: "#8b5cf6" },
  { title: "Write the Proposal", desc: "Structure your narrative, work plan, budget, and deliverables.", url: "/grant-hub", color: ACCENT },
  { title: "Check Research Alignment", desc: "Use Research Gap Finder to validate the proposal's novelty.", url: "/research-gap-finder", color: "#0ea5e9" },
  { title: "Review & Submit", desc: "Apply Synaptiq AI tools to review the proposal before submission.", url: "/grant-hub", color: EMERALD },
];

const TIPS = [
  { title: "Success rate increases 40% with consortium applications", level: "success" },
  { title: "Start at least 8 weeks before the deadline", level: "warning" },
  { title: "Align your narrative with the funder's strategic priorities", level: "info" },
  { title: "Include preliminary data to reduce perceived risk", level: "info" },
];

export default function GrantPlanner() {
  const navigate = useNavigate();
  return (
    <AIWorkspaceLayout
      title="Grant Planner"
      subtitle="Plan and track your grant applications and funding strategy."
      navItems={SIE_NAV_ITEMS}
    >

      <Card padding="lg" style={{ marginBottom: 20 }}>
        <H4 style={{ marginBottom: 14 }}>5-Stage Grant Strategy</H4>
        {STEPS.map((step, i) => (
          <div key={i} style={{ display: "flex", gap: 12, marginBottom: 8, alignItems: "center" }}>
            {/* Numbered step avatar: no ds/ primitive for a per-item colored
                numbered circle, left hand-rolled */}
            <div style={{ width: 28, height: 28, borderRadius: "50%", background: `${step.color}20`, color: step.color, fontWeight: 800, fontSize: 12, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{i + 1}</div>
            {/* Step row: kept hand-rolled rather than nesting a second Card —
                Card enforces a white background so it can't reproduce this
                WARM-tinted row without doubling the border inside the outer Card */}
            <div style={{ flex: 1, background: WARM, border: `1px solid ${BRD}`, borderRadius: 10, padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: NAVY }}>{step.title}</div>
                <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{step.desc}</div>
              </div>
              <Button onClick={() => navigate(step.url)} size="sm" style={{ background: step.color, flexShrink: 0 }}>
                Open <ArrowRight size={11} />
              </Button>
            </div>
          </div>
        ))}
      </Card>

      <Card padding="lg">
        <H4 style={{ marginBottom: 12 }}>Grant Success Tips</H4>
        {TIPS.map((tip, i) => (
          <Callout key={i} variant={tip.level} style={{ marginBottom: 8, padding: "8px 12px" }}>
            <span style={{ fontSize: 13 }}>{tip.title}</span>
          </Callout>
        ))}
        <Button onClick={() => navigate("/sie/goals")} style={{ marginTop: 14 }}>
          Set a Grant Goal <ArrowRight size={13} />
        </Button>
      </Card>
    </AIWorkspaceLayout>
  );
}

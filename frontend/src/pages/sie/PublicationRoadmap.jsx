import React from "react";
import { useNavigate } from "react-router-dom";
import { FileText, ArrowRight } from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Button, H4, Body } from "@/components/ds";

const STEPS = [
  { icon: "1", title: "Research Gap Finder", desc: "Identify an unexplored angle in your field.", url: "/research-gap-finder", color: "#8b5cf6" },
  { icon: "2", title: "Literature Review", desc: "Map the state of knowledge in your area.", url: "/literature-review", color: "#0ea5e9" },
  { icon: "3", title: "Research Roadmap", desc: "Generate a full 18-stage research plan.", url: "/sie/planning", color: ACCENT },
  { icon: "4", title: "Manuscript Review", desc: "AI feedback on your draft before submission.", url: "/manuscript-review", color: "#f59e0b" },
  { icon: "5", title: "Statistical Review", desc: "Verify your statistical methodology.", url: "/statistical-review", color: "#14b8a6" },
  { icon: "6", title: "Publishing Intelligence", desc: "Match your paper to the best target journal.", url: "/publishing-intelligence", color: "#ec4899" },
];

export default function PublicationRoadmap() {
  const navigate = useNavigate();
  return (
    <AIWorkspaceLayout
      title="Publication Roadmap"
      subtitle="AI-guided publication strategy and submission tracking."
      navItems={SIE_NAV_ITEMS}
    >

      <Card padding="lg" style={{ marginBottom: 20 }}>
        <H4 style={{ marginBottom: 14 }}>6-Stage Publication Pipeline</H4>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {STEPS.map((step, i) => (
            <div key={i} style={{ display: "flex", gap: 12, alignItems: "center" }}>
              {/* Numbered step avatar: no ds/ primitive for a per-item colored
                  numbered circle, left hand-rolled */}
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: `${step.color}20`, color: step.color, fontWeight: 800, fontSize: 13, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                {step.icon}
              </div>
              {/* Step connector row: kept hand-rolled rather than nesting a
                  second Card — Card enforces a white background so it can't
                  reproduce this WARM-tinted pipeline-step row without
                  doubling the border inside the outer Card */}
              <div style={{ flex: 1, background: WARM, border: `1px solid ${BRD}`, borderRadius: 10, padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: NAVY }}>{step.title}</div>
                  <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{step.desc}</div>
                </div>
                <Button
                  onClick={() => navigate(step.url)}
                  size="sm"
                  style={{ background: step.color, flexShrink: 0 }}
                >
                  Open <ArrowRight size={11} />
                </Button>
              </div>
              {i < STEPS.length - 1 && (
                <div style={{ fontSize: 18, color: TEXT_SECONDARY }}>↓</div>
              )}
            </div>
          ))}
        </div>
      </Card>

      <Card padding="lg">
        <H4 style={{ marginBottom: 12 }}>Create Your Personal Roadmap</H4>
        <Body style={{ marginBottom: 14, fontSize: 13, color: "#334155" }}>
          Generate a personalised 18-stage research roadmap with writing schedule, journal selection, and review workflow.
        </Body>
        <Button onClick={() => navigate("/sie/planning")}>
          Generate Research Roadmap <ArrowRight size={14} />
        </Button>
      </Card>
    </AIWorkspaceLayout>
  );
}

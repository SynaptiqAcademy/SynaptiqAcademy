import React from "react";
import { useNavigate } from "react-router-dom";
import { Trophy, ArrowRight, Users } from "lucide-react";
import { NAVY, WARM, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import { Card, Button } from "@/components/ds";

const STEPS = [
  { title: "Find Grant Partners", desc: "Use Open Collaborations to post or discover grant partner opportunities.", url: "/network/collaborations", color: ACCENT },
  { title: "Discover Institutions", desc: "Find partner institutions with aligned research focus for consortium applications.", url: "/network/institutions", color: "#0ea5e9" },
  { title: "Browse Research Groups", desc: "Existing groups may already be forming grant teams — join or propose a team.", url: "/network/groups", color: "#8b5cf6" },
  { title: "Build Grant Strategy", desc: "Use the SIE Grant Planner and Grant Hub to structure the proposal.", url: "/sie/grants", color: EMERALD },
  { title: "Track Your Team", desc: "Use the Grant Collaboration Hub to manage consortium members and deliverables.", url: "/grant-hub", color: "#f97316" },
];

export default function GrantTeams() {
  const navigate = useNavigate();
  return (
    <DiscoveryLayout
      title="Grant Teams"
      subtitle="Assemble high-quality research consortia. Find co-applicants, partner institutions and specialist collaborators for competitive grants."
    >

      <Card padding="lg" style={{ marginBottom: 16 }}>
        <h3 style={{ margin: "0 0 16px", fontSize: 14, fontWeight: 700, color: NAVY }}>Grant Team Assembly Pathway</h3>
        {STEPS.map((step, i) => (
          <div key={i} style={{ display: "flex", gap: 12, marginBottom: 10, alignItems: "center" }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", background: `${step.color}20`, color: step.color, fontWeight: 800, fontSize: 13, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{i + 1}</div>
            <Card padding="sm" style={{ flex: 1, background: WARM, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: NAVY }}>{step.title}</div>
                <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{step.desc}</div>
              </div>
              <Button
                size="sm"
                onClick={() => navigate(step.url)}
                style={{ background: step.color, flexShrink: 0 }}
              >
                Open <ArrowRight size={11} />
              </Button>
            </Card>
          </div>
        ))}
      </Card>

      <Card padding="lg" style={{ background: `${ACCENT}06`, borderColor: `${ACCENT}20` }}>
        <div style={{ fontWeight: 700, fontSize: 13, color: NAVY, marginBottom: 8 }}>Grant Team Success Tips</div>
        {[
          "Consortium applications have significantly higher success rates than solo applications.",
          "Include institutions from different countries to strengthen international collaboration impact.",
          "Assign clear roles before submission — principal investigator, co-investigators, scientific coordinator.",
          "Start assembling 12+ weeks before the deadline to allow time for consortium agreements.",
        ].map((tip, i) => (
          <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, fontSize: 13, color: TEXT_SECONDARY, alignItems: "flex-start" }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: ACCENT, flexShrink: 0, marginTop: 6 }} />
            {tip}
          </div>
        ))}
      </Card>
    </DiscoveryLayout>
  );
}

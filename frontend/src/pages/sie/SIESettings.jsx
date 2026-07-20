import React from "react";
import { useNavigate } from "react-router-dom";
import { Settings, Brain, ArrowRight, Zap, Target } from "lucide-react";
import { ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, H4, BodySmall } from "@/components/ds";

const SETTINGS_SECTIONS = [
  { title: "AI Memory", desc: "Configure research interests, preferred journals, methodologies, and career goals.", url: "/sie/memory", icon: Brain, color: ACCENT },
  { title: "Automation Center", desc: "Manage automated monitoring, weekly reports, and deadline reminders.", url: "/sie/automations", icon: Zap, color: "#f97316" },
  { title: "Research Goals", desc: "Define and manage long-term academic goals.", url: "/sie/goals", icon: Target, color: "#8b5cf6" },
  { title: "Career Profile", desc: "Set your current position, target position, and promotion timeline.", url: "/sie/career", icon: Settings, color: EMERALD },
];

export default function SIESettings() {
  const navigate = useNavigate();
  return (
    <AIWorkspaceLayout
      title="SIE Settings"
      subtitle="Configure your Synaptiq Intelligence Engine preferences."
      navItems={SIE_NAV_ITEMS}
    >

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {SETTINGS_SECTIONS.map(({ title, desc, url, icon: Icon, color }) => (
          <Card key={url} onClick={() => navigate(url)} padding="md" style={{ display: "flex", gap: 14, alignItems: "center", textAlign: "left" }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: `${color}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Icon size={20} color={color} />
            </div>
            <div style={{ flex: 1 }}>
              <H4>{title}</H4>
              <BodySmall color={TEXT_SECONDARY}>{desc}</BodySmall>
            </div>
            <ArrowRight size={16} color={TEXT_SECONDARY} />
          </Card>
        ))}
      </div>

      <Card padding="lg" style={{ marginTop: 20 }}>
        <H4 style={{ marginBottom: 8 }}>About Synaptiq Intelligence Engine</H4>
        <BodySmall color={TEXT_SECONDARY} style={{ lineHeight: 1.6 }}>
          The SIE is the orchestration layer of Synaptiq. It coordinates all platform modules —
          Literature Review, Research Gap Finder, Publishing Intelligence, Grant Hub, Collaboration Intelligence,
          Trust Center, Integrity Engine, Institution Intelligence — into one unified academic operating system.
          It does not duplicate any functionality; it intelligently connects them.
        </BodySmall>
      </Card>
    </AIWorkspaceLayout>
  );
}

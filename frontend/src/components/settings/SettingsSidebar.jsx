import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Lightbulb, Command, Sparkles, HelpCircle, ArrowRight } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { Badge } from "@/components/ds/Badge";
import { List, ListItem } from "@/components/ds/List";
import { BodySmall } from "@/components/ds/Typography";
import { TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, NAVY, WHITE, BRD } from "@/lib/tokens";

const TIPS = {
  general: "These preferences are saved to this browser; they don't yet change app behaviour.",
  appearance: "Reduced Motion and Font Size apply immediately across the whole app.",
  languageRegion: "Timezone defaults to your system clock — override it if you travel often.",
  ai: "Smart Context lets AI features see your active project without re-explaining it.",
  workspace: "Defaults here are saved to this browser; they don't yet pre-fill meetings, documents or repository items.",
  editor: "Citation Style here becomes your default the moment manuscript editing adopts it.",
  keyboard: "Press G then H/I/M/E to jump between Home, Inbox, Messages and Meetings.",
  accessibility: "Focus Indicators help when navigating entirely by keyboard.",
  labs: "Labs features may change or be removed without notice.",
  privacy: "Analytics only run in your browser after you enable them here.",
};

// Only real, currently-wired shortcuts — no fabricated key combos.
const QUICK_SHORTCUTS = [
  { label: "Command Menu", keys: ["⌘", "K"] },
  { label: "Go to Home", keys: ["G", "H"] },
  { label: "Go to Inbox", keys: ["G", "I"] },
  { label: "Go to Messages", keys: ["G", "M"] },
  { label: "Go to Meetings", keys: ["G", "E"] },
];

function Kbd({ children }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      minWidth: 20, height: 20, padding: "0 5px", borderRadius: 4,
      border: `1px solid ${BRD}`, background: "#F8FAFC",
      fontSize: 10.5, fontFamily: "monospace", color: TEXT_SECONDARY,
    }}>
      {children}
    </span>
  );
}

function SidebarCardHeading({ icon: Icon, children }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 10 }}>
      <Icon size={14} style={{ color: NAVY }} />
      <div style={{ fontSize: 12.5, fontWeight: 700, color: TEXT_PRIMARY, letterSpacing: "-0.01em" }}>{children}</div>
    </div>
  );
}

function FooterLink({ to, children }) {
  return (
    <Link to={to} style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600, color: NAVY, textDecoration: "none", marginTop: 10 }}>
      {children} <ArrowRight size={11} />
    </Link>
  );
}

export function SettingsSidebar({ activeCategory }) {
  const [tipDismissed, setTipDismissed] = useState(false);

  useEffect(() => { setTipDismissed(false); }, [activeCategory]);

  return (
    <div className="w-full lg:w-[260px]" style={{ flexShrink: 0, display: "flex", flexDirection: "column", gap: 16 }}>
      {!tipDismissed && (
        <Card padding="lg" style={{ background: NAVY, border: "none" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 10 }}>
            <Lightbulb size={14} style={{ color: WHITE }} />
            <div style={{ fontSize: 12.5, fontWeight: 700, color: WHITE, letterSpacing: "-0.01em" }}>Contextual Tip</div>
          </div>
          <BodySmall as="p" style={{ color: "rgba(255,255,255,0.82)", lineHeight: 1.6, margin: "0 0 12px" }}>
            {TIPS[activeCategory]}
          </BodySmall>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setTipDismissed(true)}
            style={{ color: WHITE, background: "rgba(255,255,255,0.12)", border: "1px solid rgba(255,255,255,0.2)" }}
          >
            Got it
          </Button>
        </Card>
      )}

      <Card padding="lg">
        <SidebarCardHeading icon={Command}>Quick Shortcuts</SidebarCardHeading>
        <List border={false} radius={0} style={{ background: "transparent" }}>
          {QUICK_SHORTCUTS.map((s) => (
            <ListItem
              key={s.label}
              compact
              title={s.label}
              trailing={<span style={{ display: "flex", gap: 3 }}>{s.keys.map((k, i) => <Kbd key={i}>{k}</Kbd>)}</span>}
              style={{ borderBottom: "none", padding: "5px 0" }}
            />
          ))}
        </List>
        <FooterLink to="/settings?section=keyboard">View all shortcuts</FooterLink>
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
          <SidebarCardHeading icon={Sparkles}>Release Notes</SidebarCardHeading>
          <Badge variant="default" size="sm" style={{ marginLeft: -2, marginBottom: 8 }}>NEW</Badge>
        </div>
        <div style={{ fontSize: 12.5, fontWeight: 600, color: TEXT_PRIMARY, marginTop: -4, marginBottom: 4 }}>
          Application Preferences
        </div>
        <BodySmall as="p" color={TEXT_MUTED} style={{ margin: 0, lineHeight: 1.6 }}>
          Launched today. More categories arrive as new Synaptiq features ship.
        </BodySmall>
        <FooterLink to="/help-center">View release notes</FooterLink>
      </Card>

      <Card padding="lg">
        <SidebarCardHeading icon={HelpCircle}>Need Help?</SidebarCardHeading>
        <BodySmall as="p" style={{ lineHeight: 1.6, margin: 0 }}>
          Visit our Help Center for guides, tutorials and best practices.
        </BodySmall>
        <FooterLink to="/help-center">Open Help Center</FooterLink>
      </Card>
    </div>
  );
}

export default SettingsSidebar;

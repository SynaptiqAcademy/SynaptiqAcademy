import React from "react";
import { Card } from "@/components/ds/Card";
import { Section } from "@/components/ds/Section";
import { Badge } from "@/components/ds/Badge";
import { TEXT_MUTED, NAVY, EMERALD } from "@/lib/tokens";

/**
 * PassportCollaborationProfile — P1 Phase 7C4.1 §5/§16: Open To / Can
 * Contribute / Looking For, pulled out of IdentityCard into their own
 * Passport concept ("what I can contribute" / "what I'm looking for" are
 * collaboration signals, not academic expertise). These are display
 * preferences only — NOT canonical matching inputs (services/
 * collab_intelligence/matching_engine.py doesn't consume them), so unlike
 * IdentityCard's expertise groups, nothing here ever gets a "used for
 * matching" mark.
 */
function ChipRow({ label, items = [], color = NAVY, bg }) {
  if (!items.length) return null;
  return (
    <div>
      <div style={{ fontSize: 10.5, fontWeight: 700, color: TEXT_MUTED, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {items.map((item) => (
          <span key={item} style={{
            fontSize: 12, padding: "4px 10px", fontWeight: 500,
            background: bg || (color + "12"), color, border: `1px solid ${color}35`,
          }}>
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

export function PassportCollaborationProfile({ profile, onEdit }) {
  if (!profile) return null;

  const openTo = [
    profile.available_for_collaboration && "Collaboration",
    profile.available_for_supervision && "Supervision",
    profile.available_for_reviewing && "Peer Review",
    profile.available_for_consulting && "Consulting",
  ].filter(Boolean);
  const canContribute = profile.can_contribute || [];
  const lookingFor = profile.looking_for || [];

  const hasAnything = openTo.length || canContribute.length || lookingFor.length || profile.availability;
  if (!hasAnything) return null;

  // These fields (availability, open-to checkboxes, can-contribute /
  // looking-for chips) are all edited in EditIdentityModal's "Collaboration
  // & Availability" section, but this card previously had no edit action of
  // its own — the only way to find that editor was via an unrelated section
  // elsewhere on the page (P1 Phase 7C4.3 §11).
  const editAction = onEdit ? (
    <button onClick={onEdit} style={{ fontSize: 11.5, fontWeight: 600, color: NAVY, background: "none", border: "none", cursor: "pointer", padding: 0 }}>
      Edit
    </button>
  ) : undefined;

  return (
    <Card padding="xl">
      <Section title="Collaboration Profile" subtitle="Preferences you've set — not used by the matching engine" action={editAction} gap="lg">
        {profile.availability && (
          <Badge variant={profile.availability === "Available" ? "success" : "warning"} dot>
            {profile.availability}
          </Badge>
        )}
        <div className="grid sm:grid-cols-3" style={{ gap: 20 }}>
          <ChipRow label="Open To" items={openTo} color={EMERALD} bg="#F0FDF4" />
          <ChipRow label="Can Contribute" items={canContribute} color={NAVY} bg="#EFF6FF" />
          <ChipRow label="Looking For" items={lookingFor} color="#92400E" bg="#FFFBEB" />
        </div>
      </Section>
    </Card>
  );
}

export default PassportCollaborationProfile;

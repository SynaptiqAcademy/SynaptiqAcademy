import React from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Circle } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { ProgressBar } from "@/components/ds/Progress";
import { TYPE, TEXT_SECONDARY, TEXT_MUTED, NAVY, EMERALD } from "@/lib/tokens";

/**
 * CompletionWidget — profile completion % + suggested improvements checklist.
 *
 * The backend still returns action: "/settings" for ORCID-related items
 * (GET /users/me/profile-completion) since ORCID connect/sync now lives on
 * Academic Passport, not Settings — remapped here, no backend change.
 */
function resolveAction(action) {
  return action === "/settings" ? "/academic-passport" : action;
}

export function CompletionWidget({ completion }) {
  if (!completion) return null;
  return (
    <Card padding="lg">
      <div style={{ ...TYPE.section, marginBottom: 10 }}>Profile Completion</div>
      <ProgressBar value={completion.percentage} colorByValue />
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 14 }}>
        {(completion.items || []).map((item) => (
          <div key={item.key} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {item.earned
              ? <CheckCircle2 size={13} style={{ color: EMERALD, flexShrink: 0 }} />
              : <Circle size={13} style={{ color: "#CBD5E1", flexShrink: 0 }} />}
            <span style={{ flex: 1, fontSize: 12, color: item.earned ? TEXT_SECONDARY : TEXT_MUTED }}>{item.label}</span>
            {item.earned
              ? <span style={{ fontSize: 10.5, color: EMERALD, fontWeight: 600 }}>+{item.points}</span>
              : <Link to={resolveAction(item.action)} style={{ fontSize: 10.5, color: NAVY, textDecoration: "none" }}>{item.action_label}</Link>}
          </div>
        ))}
      </div>
    </Card>
  );
}

export default CompletionWidget;

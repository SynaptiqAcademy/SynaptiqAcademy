import React from "react";
import { BRD, WHITE } from "@/lib/tokens";
import { Button } from "./Button";

/**
 * SmartActionsBar — horizontal row of contextual actions for an entity page,
 * so common operations never require leaving the page.
 *
 * Props:
 *   actions  [{ label, icon, onClick, variant, disabled, loading }]
 */
export function SmartActionsBar({ actions = [] }) {
  if (actions.length === 0) return null;

  return (
    <div style={{
      display: "flex", flexWrap: "wrap", gap: 8,
      background: WHITE, border: `1px solid ${BRD}`, borderRadius: 6,
      padding: 12, marginBottom: 20,
    }}>
      {actions.map((a, i) => {
        const Icon = a.icon;
        return (
          <Button
            key={a.label || i}
            variant={a.variant || "ghost"}
            size="sm"
            onClick={a.onClick}
            disabled={a.disabled}
            loading={a.loading}
          >
            {Icon && <Icon size={13} strokeWidth={1.75} />}
            {a.label}
          </Button>
        );
      })}
    </div>
  );
}

export default SmartActionsBar;

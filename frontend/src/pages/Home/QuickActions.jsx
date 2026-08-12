/* eslint-disable */
import React from "react";
import { useNavigate } from "react-router-dom";
import { LayoutGrid } from "lucide-react";
import { QUICK_ACTIONS } from "@/config/navigation";
import { rankActions } from "@/hooks/useUserMemory";
import { TEXT_PRIMARY, TEXT_MUTED, NAVY, BRD, WHITE, TYPE } from "@/lib/tokens";
import { transition, transform } from "@/lib/motion";

const CAT_COLOR = {
  Research: "#0F2847",
  AI:       "#7C3AED",
  Teaching: "#047857",
  Funding:  "#B45309",
  Planning: "#1D4ED8",
};

function ActionTile({ action, onClick }) {
  const [hov, setHov] = React.useState(false);
  const Icon = action.icon;
  const color = CAT_COLOR[action.category] || NAVY;

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "flex", alignItems: "center", gap: 12,
        padding: "14px 16px",
        background: WHITE,
        border: `1px solid ${hov ? "rgba(15,40,71,0.16)" : BRD}`,
        borderRadius: 12,
        cursor: "pointer",
        textAlign: "left",
        transform: hov ? transform.liftSm : transform.none,
        transition: transition.hoverCard,
        boxShadow: hov ? "0 8px 20px -12px rgba(15,23,42,0.18)" : "none",
      }}
    >
      <div
        style={{
          width: 34, height: 34, borderRadius: 9, flexShrink: 0,
          background: color + "14",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
      >
        <Icon size={15} strokeWidth={1.75} style={{ color }} />
      </div>
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ ...TYPE.h4, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {action.label}
        </div>
      </div>
    </button>
  );
}

/**
 * QuickActions — one-click entry points to the app's core workflows.
 *
 * Shows the user's top-ranked actions (via useUserMemory's rankActions,
 * driven by real navigation history — not fabricated) directly on the
 * dashboard. "More workflows" opens the full WorkflowLauncher modal for
 * the complete categorized list — reusing that existing component instead
 * of building a second quick-actions surface.
 */
export default function QuickActions({ onOpenLauncher }) {
  const navigate = useNavigate();
  const top = React.useMemo(() => rankActions(QUICK_ACTIONS).slice(0, 6), []);

  return (
    <section aria-label="Quick Actions">
      <div className="flex items-baseline justify-between mb-4">
        <h2
          style={{
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: "1.35rem", fontWeight: 700, letterSpacing: "-0.02em",
            color: TEXT_PRIMARY, margin: 0,
          }}
        >
          Quick actions
        </h2>
        <button
          onClick={onOpenLauncher}
          style={{
            display: "inline-flex", alignItems: "center", gap: 5,
            ...TYPE.caption, color: TEXT_MUTED, background: "none", border: "none",
            cursor: "pointer", padding: 0, transition: transition.colorFast,
          }}
          onMouseEnter={e => (e.currentTarget.style.color = NAVY)}
          onMouseLeave={e => (e.currentTarget.style.color = TEXT_MUTED)}
        >
          <LayoutGrid size={11} strokeWidth={1.75} />
          All workflows →
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {top.map(action => (
          <ActionTile key={action.to} action={action} onClick={() => navigate(action.to)} />
        ))}
      </div>
    </section>
  );
}

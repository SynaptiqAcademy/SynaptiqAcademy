/* eslint-disable */
import React from "react";
import { useNavigate } from "react-router-dom";
import { LayoutGrid } from "lucide-react";
import { QUICK_ACTIONS } from "@/config/navigation";
import { rankActions } from "@/hooks/useUserMemory";

function ActionRow({ action, onClick }) {
  const Icon = action.icon;
  return (
    <button type="button" onClick={onClick} className="hm-action">
      <Icon size={15} strokeWidth={1.6} aria-hidden="true" />
      <span>{action.label}</span>
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
  // The four workflows this person uses most (ranked from real navigation
  // history); everything else is one click away in "All workflows".
  const top = React.useMemo(() => rankActions(QUICK_ACTIONS).slice(0, 4), []);

  return (
    <section aria-label="Quick actions" className="hm-block">
      <div className="hm-block-head">
        <h2 className="hm-h2">Quick actions</h2>
        <button type="button" onClick={onOpenLauncher} className="hm-link">
          <LayoutGrid size={12} strokeWidth={1.75} aria-hidden="true" /> All workflows
        </button>
      </div>
      <div className="hm-actions">
        {top.map((action) => (
          <ActionRow key={action.to} action={action} onClick={() => navigate(action.to)} />
        ))}
      </div>
    </section>
  );
}

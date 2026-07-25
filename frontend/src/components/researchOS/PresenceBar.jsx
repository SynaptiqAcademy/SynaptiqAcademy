import React from "react";
import { Avatar } from "@/components/ds/Avatar";
import { EMERALD, TEXT_MUTED, WHITE } from "@/lib/tokens";

const VIEW_LABELS = {
  overview: "Overview", tasks: "Tasks", gantt: "Timeline", wiki: "Wiki",
  team: "Team", coauthors: "Co-Authors", pipeline: "Pipeline", reviews: "Reviews",
  collaboration: "Collaboration", ai: "AI Enhancement", activity: "Activity",
  documents: "Documents", analytics: "Analytics",
};

function describePeer(p) {
  const where = VIEW_LABELS[p.view] || p.view || "the workspace";
  const suffix = p.typing ? " — typing…" : "";
  return `${p.full_name} — viewing ${where}${suffix}`;
}

/**
 * PresenceBar — live "who's here" avatar stack (Workspace redesign Phase 9).
 * Backed by useWorkspacePresence; shows each connected member with a real
 * active/idle status dot and a tooltip naming their current tab.
 */
export default function PresenceBar({ peers, max = 5 }) {
  if (!peers.length) return null;
  const visible = peers.slice(0, max);
  const overflow = peers.length - visible.length;

  return (
    <div
      style={{ display: "inline-flex", alignItems: "center" }}
      aria-label={`${peers.length} other member${peers.length === 1 ? "" : "s"} currently viewing this workspace`}
    >
      {visible.map((p, i) => (
        <div
          key={p.user_id}
          title={describePeer(p)}
          style={{ marginLeft: i === 0 ? 0 : -8, position: "relative", zIndex: visible.length - i }}
        >
          <Avatar url={p.avatar_url} name={p.full_name} size={26} border />
          <span
            aria-hidden="true"
            style={{
              position: "absolute", right: -1, bottom: -1, width: 8, height: 8, borderRadius: "50%",
              background: p.status === "active" ? EMERALD : TEXT_MUTED, border: `1.5px solid ${WHITE}`,
            }}
          />
        </div>
      ))}
      {overflow > 0 && (
        <span style={{ marginLeft: 6, fontSize: 11, color: TEXT_MUTED, fontWeight: 600 }}>+{overflow}</span>
      )}
    </div>
  );
}

/**
 * AssistantLauncher — pill button that opens the AssistantPanel drawer.
 * Drop into Workspace/Project/Manuscript detail pages.
 */
import React, { useState } from "react";
import AssistantPanel from "./AssistantPanel";
import { Sparkles } from "lucide-react";
import { NAVY } from "@/lib/tokens";

export default function AssistantLauncher({ entityKind, entityId, entityTitle, variant = "pill" }) {
  const [open, setOpen] = useState(false);

  if (variant === "fixed") {
    return (
      <>
        <button
          data-testid="assistant-launcher-fixed"
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 bg-[#0F2847] text-white px-4 py-2.5 shadow-lg hover:bg-slate-800 transition-colors"
        >
          <Sparkles size={14} strokeWidth={1.5} />
          <span className="text-sm">Research Copilot</span>
        </button>
        <AssistantPanel
          open={open}
          onClose={() => setOpen(false)}
          entityKind={entityKind}
          entityId={entityId}
          entityTitle={entityTitle}
        />
      </>
    );
  }

  return (
    <>
      <button
        data-testid="assistant-launcher"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 text-xs bg-gradient-to-r from-[#0F2847] to-[#1E3A5F] text-white px-3 py-1.5 hover:from-[#0a1f3a] hover:to-[#0F2847] transition-colors"
        title="Open Research Copilot"
      >
        <Sparkles size={12} strokeWidth={1.5} />
        Research Copilot
      </button>
      <AssistantPanel
        open={open}
        onClose={() => setOpen(false)}
        entityKind={entityKind}
        entityId={entityId}
        entityTitle={entityTitle}
      />
    </>
  );
}

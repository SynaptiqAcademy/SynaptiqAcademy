import React, { useEffect, useRef, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { X } from "lucide-react";
import { QUICK_ACTIONS } from "../../config/navigation";
import { rankActions } from "../../hooks/useUserMemory";

// Per-category accent color (background tint for the icon tile)
const CAT_COLOR = {
  Research: "#0F2847",
  AI:       "#7C3AED",
  Teaching: "#047857",
  Funding:  "#B45309",
  Planning: "#1D4ED8",
};

// Stable category order
const CAT_ORDER = ["Research", "AI", "Teaching", "Funding", "Planning"];

export default function WorkflowLauncher({ open, onClose }) {
  const navigate = useNavigate();
  const panelRef = useRef(null);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Focus panel on open
  useEffect(() => {
    if (open) panelRef.current?.focus();
  }, [open]);

  if (!open) return null;

  // Rank actions by the user's behavior, then group by category in stable order
  const ranked = rankActions(QUICK_ACTIONS);
  const grouped = {};
  CAT_ORDER.forEach((cat) => { grouped[cat] = []; });
  ranked.forEach((a) => {
    if (!grouped[a.category]) grouped[a.category] = [];
    grouped[a.category].push(a);
  });

  const handleSelect = (action) => {
    onClose();
    navigate(action.to);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={onClose}
      aria-modal="true"
      role="dialog"
      aria-label="Start a workflow"
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-[1px]" />

      {/* Panel */}
      <div
        ref={panelRef}
        tabIndex={-1}
        className="relative bg-white border border-slate-200 shadow-2xl w-full max-w-2xl mx-4 flex flex-col outline-none"
        style={{ maxHeight: "82vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 pt-5 pb-4 border-b border-slate-100 shrink-0">
          <div>
            <h2 className="text-[15px] font-semibold text-slate-900 tracking-tight">
              What do you want to do?
            </h2>
            <p className="text-[12px] text-slate-400 mt-0.5">
              Choose a workflow — we'll take you straight there
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 transition-colors p-1 -mr-1 -mt-0.5 shrink-0"
            aria-label="Close"
          >
            <X size={15} strokeWidth={1.5} />
          </button>
        </div>

        {/* Workflow grid */}
        <div className="overflow-y-auto flex-1 px-6 py-4 space-y-5">
          {CAT_ORDER.filter((cat) => grouped[cat].length > 0).map((cat) => {
            const color = CAT_COLOR[cat] || "#0F2847";
            return (
              <div key={cat}>
                <div
                  className="text-[9px] font-bold tracking-[0.12em] uppercase pb-2 mb-2 border-b border-slate-100"
                  style={{ color }}
                >
                  {cat}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {grouped[cat].map((action) => {
                    const Icon = action.icon;
                    return (
                      <button
                        key={action.to}
                        onClick={() => handleSelect(action)}
                        className="group text-left flex items-start gap-3 p-3 border border-slate-200 hover:border-slate-300 hover:shadow-sm transition-all duration-100"
                      >
                        {/* Icon tile */}
                        <div
                          className="w-8 h-8 flex items-center justify-center shrink-0 mt-0.5 transition-opacity"
                          style={{ background: color + "12" }}
                        >
                          <Icon size={14} strokeWidth={1.5} style={{ color }} />
                        </div>

                        {/* Text */}
                        <div className="min-w-0">
                          <div className="text-[13px] font-medium text-slate-800 group-hover:text-slate-900 truncate">
                            {action.label}
                          </div>
                          <div className="text-[11px] text-slate-400 mt-0.5 leading-snug line-clamp-2">
                            {action.description}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-100 text-[11px] text-slate-400 shrink-0 flex items-center justify-between">
          <span>
            <kbd className="border border-slate-200 px-1 py-px bg-slate-50 font-mono text-[10px]">
              Esc
            </kbd>
            {" "}dismiss
          </span>
          <span className="text-slate-300">Or use ⌘K to search any feature</span>
        </div>
      </div>
    </div>
  );
}

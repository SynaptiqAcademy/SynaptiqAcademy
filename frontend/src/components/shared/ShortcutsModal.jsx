import React, { useEffect, useRef } from "react";
import { Button } from "@/components/ds";
import { X } from "lucide-react";
import { WHITE, TEXT_PRIMARY, TEXT_SECONDARY, RADIUS_LG, SHADOW_CARD_HOVER, BRDX, SURF2 } from "@/lib/tokens";

/**
 * ShortcutsModal — keyboard-shortcuts help dialog.
 * Shared by Messages and Inbox (Notifications) — previously two near-identical
 * copies with different `rows`. `rows` is an array of [key, description] pairs.
 */
export function ShortcutsModal({ onClose, rows, title = "Keyboard shortcuts" }) {
  const panelRef = useRef(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement;
    panelRef.current?.focus();
    const onKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(15,23,42,0.4)" }}
      onClick={onClose}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        style={{ background: WHITE, borderRadius: RADIUS_LG, boxShadow: SHADOW_CARD_HOVER, width: 320, padding: 24, outline: "none" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 style={{ fontSize: "0.95rem", fontWeight: 650, color: TEXT_PRIMARY, margin: 0 }}>{title}</h3>
          <Button
            size="icon"
            variant="ghost"
            onClick={onClose}
            aria-label="Close"
            style={{
              color: TEXT_SECONDARY
            }}>
            <X size={16} />
          </Button>
        </div>
        <div className="flex flex-col gap-2.5">
          {rows.map(([key, desc]) => (
            <div key={key} className="flex items-center justify-between">
              <span style={{ fontSize: "0.8rem", color: TEXT_SECONDARY }}>{desc}</span>
              <kbd
                style={{
                  fontSize: "0.72rem", fontWeight: 600, color: TEXT_PRIMARY, background: SURF2,
                  border: `1px solid ${BRDX}`, borderRadius: 5, padding: "2px 7px", fontFamily: "monospace",
                }}
              >
                {key}
              </kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ShortcutsModal;

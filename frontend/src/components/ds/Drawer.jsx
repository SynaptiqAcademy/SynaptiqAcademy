import React, { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { BRD, WHITE, SURF2, SHADOW_XL, TEXT_PRIMARY, TEXT_MUTED, RADIUS_MD, Z } from "@/lib/tokens";

/**
 * Drawer — right-anchored slide-over panel for quick-preview / detail-without-navigation.
 *
 * Props:
 *   open      bool
 *   onClose   fn
 *   title     string
 *   width     string|number   default 440px
 *   footer    ReactNode (optional)
 *   children
 */
export function Drawer({ open, onClose, title, width = 440, footer, children }) {
  const panelRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement;
    panelRef.current?.focus();
    return () => prev?.focus?.();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === "Escape") onClose?.(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
      return () => { document.body.style.overflow = ""; };
    }
  }, [open]);

  if (!open) return null;

  const w = typeof width === "number" ? `${width}px` : width;

  return createPortal(
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: Z.modal,
        background: "rgba(15,23,42,0.4)",
        display: "flex", justifyContent: "flex-end",
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? "drawer-title" : undefined}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "relative",
          width: w,
          maxWidth: "calc(100vw - 32px)",
          height: "100vh",
          background: WHITE,
          boxShadow: SHADOW_XL,
          display: "flex",
          flexDirection: "column",
          outline: "none",
          animation: "sq-drawer-in 200ms cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      >
        <style>{`
          @keyframes sq-drawer-in {
            from { transform: translateX(24px); opacity: 0; }
            to   { transform: translateX(0);     opacity: 1; }
          }
        `}</style>

        <div style={{
          display: "flex", alignItems: "flex-start", justifyContent: "space-between",
          padding: "18px 20px", borderBottom: `1px solid ${BRD}`, flexShrink: 0,
        }}>
          {title && (
            <h2 id="drawer-title" style={{
              fontSize: "1rem", fontWeight: 600, color: TEXT_PRIMARY,
              letterSpacing: "-0.01em", margin: 0,
            }}>
              {title}
            </h2>
          )}
          <button
            onClick={onClose}
            aria-label="Close panel"
            style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              width: 30, height: 30, borderRadius: RADIUS_MD, border: `1px solid ${BRD}`,
              background: "transparent", cursor: "pointer", color: TEXT_MUTED,
              flexShrink: 0, marginLeft: 16, transition: "background 100ms",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = SURF2)}
            onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          >
            <X size={14} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "18px 20px" }}>
          {children}
        </div>

        {footer && (
          <div style={{
            padding: "14px 20px", borderTop: `1px solid ${BRD}`,
            display: "flex", justifyContent: "flex-end", gap: 8, flexShrink: 0,
          }}>
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}

export default Drawer;

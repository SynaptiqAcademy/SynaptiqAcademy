import React, { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import {
  NAVY, BRD, SHADOW_MODAL, WHITE, SURF2, CRIMSON, DANGER_BG, NAVY_06,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, RADIUS_MD, RADIUS_LG, Z,
} from "@/lib/tokens";
import { Button } from "./Button";

/**
 * Modal — full-featured overlay for complex interactions.
 *
 * Sizes: sm (400px) | md (640px, default) | lg (896px) | fullscreen
 *
 * Props:
 *   open        bool
 *   onClose     fn
 *   title       string
 *   description string (optional)
 *   size        "sm" | "md" | "lg" | "fullscreen"
 *   footer      ReactNode (optional)
 *   closeOnOverlay bool (default false)
 *   children
 */
export function Modal({
  open,
  onClose,
  title,
  description,
  size = "md",
  footer,
  closeOnOverlay = false,
  className = "",
  children,
}) {
  const overlayRef = useRef(null);
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

  const widths = { sm: 400, md: 640, lg: 896, fullscreen: "100vw" }[size] || 640;
  const heights = size === "fullscreen" ? "100vh" : "auto";

  const panelStyle = {
    position: "relative",
    background: WHITE,
    borderRadius: size === "fullscreen" ? 0 : RADIUS_MD,
    boxShadow: SHADOW_MODAL,
    width: widths,
    maxWidth: size === "fullscreen" ? "100vw" : "calc(100vw - 32px)",
    maxHeight: size === "fullscreen" ? "100vh" : "calc(100vh - 48px)",
    height: heights,
    display: "flex",
    flexDirection: "column",
    outline: "none",
  };

  return createPortal(
    <div
      ref={overlayRef}
      onClick={closeOnOverlay ? onClose : undefined}
      style={{
        position: "fixed", inset: 0, zIndex: Z.modal,
        background: "rgba(15,23,42,0.4)",
        backdropFilter: "blur(2px)",
        display: "flex",
        alignItems: size === "fullscreen" ? "stretch" : "center",
        justifyContent: "center",
        padding: size === "fullscreen" ? 0 : 16,
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? "modal-title" : undefined}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        className={className}
        style={panelStyle}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "flex-start", justifyContent: "space-between",
          padding: "20px 24px 16px", borderBottom: `1px solid ${BRD}`, flexShrink: 0,
        }}>
          <div>
            {title && (
              <h2 id="modal-title" style={{
                fontSize: "1.05rem", fontWeight: 600, color: TEXT_PRIMARY,
                letterSpacing: "-0.01em", margin: 0,
              }}>
                {title}
              </h2>
            )}
            {description && (
              <p style={{ fontSize: "0.8rem", color: TEXT_TERTIARY, margin: "4px 0 0", lineHeight: 1.5 }}>
                {description}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              width: 32, height: 32, borderRadius: RADIUS_MD, border: `1px solid ${BRD}`,
              background: "transparent", cursor: "pointer", color: TEXT_TERTIARY,
              flexShrink: 0, marginLeft: 16,
              transition: "background 100ms",
            }}
            onMouseEnter={e => (e.currentTarget.style.background = SURF2)}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          >
            <X size={14} />
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div style={{
            padding: "14px 24px", borderTop: `1px solid ${BRD}`,
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

/**
 * Dialog — lightweight confirmation overlay (simpler than Modal).
 *
 * Variants: confirm | destructive | info
 */
export function Dialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "confirm",
  loading = false,
}) {
  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === "Escape") onClose?.(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const iconColor = variant === "destructive" ? CRIMSON : NAVY;
  const iconBg = variant === "destructive" ? DANGER_BG : NAVY_06;

  return createPortal(
    <div
      style={{
        position: "fixed", inset: 0, zIndex: Z.modal + 50, // stacks above a plain Modal for nested confirm dialogs
        background: "rgba(15,23,42,0.4)",
        display: "flex", alignItems: "center", justifyContent: "center", padding: 16,
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      <div style={{
        background: WHITE, borderRadius: RADIUS_MD, boxShadow: SHADOW_MODAL,
        width: 400, maxWidth: "calc(100vw - 32px)", padding: 24,
        display: "flex", flexDirection: "column", gap: 16,
      }}>
        {/* Icon */}
        <div style={{
          width: 40, height: 40, borderRadius: RADIUS_LG,
          background: iconBg, display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          {variant === "destructive" ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={iconColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 6h18M19 6l-1 14H6L5 6M10 11v6M14 11v6M9 6V4h6v2" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={iconColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" />
            </svg>
          )}
        </div>

        {/* Text */}
        <div>
          <h3 id="dialog-title" style={{ fontSize: "0.95rem", fontWeight: 600, color: TEXT_PRIMARY, margin: "0 0 6px" }}>
            {title}
          </h3>
          {description && (
            <p style={{ fontSize: "0.8rem", color: TEXT_SECONDARY, margin: 0, lineHeight: 1.6 }}>
              {description}
            </p>
          )}
        </div>

        {/* Actions */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            variant={variant === "destructive" ? "danger" : "primary"}
            size="sm"
            onClick={onConfirm}
            loading={loading}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

export default Modal;

/* eslint-disable */
import React from "react";
import { CheckCircle, AlertTriangle, XCircle, Info, X } from "lucide-react";
import {
  EMERALD, AMBER, CRIMSON, INFO, BRD, SURF2, TEXT_STRONG, TEXT_TERTIARY,
  SUCCESS_BG, SUCCESS_TEXT, SUCCESS_BORDER,
  WARNING_BG, WARNING_TEXT, WARNING_BORDER,
  DANGER_BG, DANGER_TEXT, DANGER_BORDER,
  INFO_BG, INFO_TEXT, INFO_BORDER,
  RADIUS_LG, RADIUS_MD,
} from "@/lib/tokens";

// ── Config map ─────────────────────────────────────────────────────────────────
// Every value here is a named token (@/lib/tokens) — the same success/warning/
// danger/info palette Badge, Toast-replacement (sonner), and every other
// status-bearing component draws from.
const C = {
  success: { bg: SUCCESS_BG, border: SUCCESS_BORDER, text: SUCCESS_TEXT, accent: EMERALD, icon: CheckCircle   },
  warning: { bg: WARNING_BG, border: WARNING_BORDER, text: WARNING_TEXT, accent: AMBER,   icon: AlertTriangle },
  error:   { bg: DANGER_BG,  border: DANGER_BORDER,  text: DANGER_TEXT,  accent: CRIMSON, icon: XCircle       },
  info:    { bg: INFO_BG,    border: INFO_BORDER,    text: INFO_TEXT,    accent: INFO,    icon: Info          },
  neutral: { bg: SURF2,      border: BRD,            text: TEXT_STRONG,  accent: TEXT_TERTIARY, icon: Info    },
};

// ── Alert ─────────────────────────────────────────────────────────────────────
/**
 * Alert — inline contextual message.
 *
 * Props:
 *   variant    "success"|"warning"|"error"|"info"|"neutral"
 *   title      string
 *   children   content (description)
 *   onDismiss  fn   shows × button
 *   icon       ReactComponent  override icon
 */
export function Alert({ variant = "info", title, children, onDismiss, icon: CustomIcon, style }) {
  const c = C[variant] ?? C.info;
  const Icon = CustomIcon ?? c.icon;

  return (
    <div
      role="alert"
      style={{
        display: "flex", gap: 12, padding: "12px 16px",
        background: c.bg, border: `1px solid ${c.border}`,
        borderRadius: RADIUS_LG, ...style,
      }}
    >
      <Icon size={16} style={{ color: c.accent, flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
      <div style={{ flex: 1, minWidth: 0 }}>
        {title && (
          <p style={{ margin: "0 0 3px", fontSize: "0.875rem", fontWeight: 600, color: c.text, lineHeight: 1.4 }}>
            {title}
          </p>
        )}
        {children && (
          <div style={{ fontSize: "0.8125rem", color: c.text, lineHeight: 1.55 }}>
            {children}
          </div>
        )}
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{ background: "none", border: "none", cursor: "pointer", color: c.text, padding: 0, flexShrink: 0, opacity: 0.6, lineHeight: 0, marginTop: 2 }}
          aria-label="Dismiss"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}

// ── Banner ────────────────────────────────────────────────────────────────────
/**
 * Banner — full-width site-level notification. Place inside PageLayout's banner prop.
 */
export function Banner({ variant = "info", children, onDismiss, action, style }) {
  const c = C[variant] ?? C.info;
  const Icon = c.icon;

  return (
    <div
      role="status"
      style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "9px 16px",
        background: c.bg, borderBottom: `1px solid ${c.border}`,
        ...style,
      }}
    >
      <Icon size={14} style={{ color: c.accent, flexShrink: 0 }} aria-hidden="true" />
      <span style={{ flex: 1, fontSize: "0.8125rem", fontWeight: 500, color: c.text }}>{children}</span>
      {action && <div style={{ flexShrink: 0 }}>{action}</div>}
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{ background: "none", border: "none", cursor: "pointer", color: c.text, padding: 0, opacity: 0.6, lineHeight: 0, flexShrink: 0 }}
          aria-label="Dismiss"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}

// ── Callout ───────────────────────────────────────────────────────────────────
/**
 * Callout — left-bordered block quote / note. Good for documentation-style content.
 */
export function Callout({ variant = "info", title, children, style }) {
  const c = C[variant] ?? C.info;

  return (
    <div style={{
      padding: "12px 16px",
      background: c.bg,
      borderLeft: `3px solid ${c.accent}`,
      borderRadius: `0 ${RADIUS_MD} ${RADIUS_MD} 0`,
      ...style,
    }}>
      {title && (
        <p style={{ margin: "0 0 4px", fontSize: "0.875rem", fontWeight: 700, color: c.text }}>{title}</p>
      )}
      <div style={{ fontSize: "0.8125rem", color: c.text, lineHeight: 1.55 }}>{children}</div>
    </div>
  );
}

// ── InlineError ───────────────────────────────────────────────────────────────
/**
 * InlineError — compact single-line error. Use inside forms above submit buttons.
 */
export function InlineError({ children, style }) {
  if (!children) return null;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, ...style }}>
      <XCircle size={13} style={{ color: CRIMSON, flexShrink: 0 }} aria-hidden="true" />
      <span style={{ fontSize: "0.8125rem", color: CRIMSON, lineHeight: 1.4 }}>{children}</span>
    </div>
  );
}

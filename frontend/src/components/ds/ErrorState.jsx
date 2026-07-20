import React from "react";
import { AlertCircle, RefreshCw, WifiOff, Lock, ServerCrash } from "lucide-react";
import {
  NAVY, BRD, BRDX, NAVY_06, CRIMSON, AMBER, SURF2,
  DANGER_BG, DANGER_BORDER, WARNING_BG, WARNING_BORDER,
  TEXT_PRIMARY, TEXT_TERTIARY, RADIUS_MD,
} from "@/lib/tokens";

/**
 * ErrorState — standardized error display.
 *
 * type:
 *   "generic"   — generic error (default)
 *   "network"   — connectivity / timeout
 *   "auth"      — 401/403 / not authorized
 *   "server"    — 5xx / server-side failure
 *   "not_found" — 404 / resource missing
 *
 * Props:
 *   message     string   — main error message
 *   detail      string   — secondary detail line
 *   type        string   — error variant
 *   onRetry     function — show retry button if provided
 *   size        "sm" | "md" | "lg"
 *   className   string
 */

const TYPE_MAP = {
  generic:   { Icon: AlertCircle,  label: "Something went wrong",      bg: DANGER_BG,  border: DANGER_BORDER,  iconColor: CRIMSON },
  network:   { Icon: WifiOff,      label: "Connection problem",        bg: "#FFF7ED", border: "#FED7AA", iconColor: "#EA580C" },
  auth:      { Icon: Lock,         label: "Access denied",             bg: WARNING_BG, border: WARNING_BORDER, iconColor: AMBER },
  server:    { Icon: ServerCrash,  label: "Server error",              bg: DANGER_BG,  border: DANGER_BORDER,  iconColor: CRIMSON },
  not_found: { Icon: AlertCircle,  label: "Not found",                 bg: SURF2,      border: BRDX,           iconColor: TEXT_TERTIARY },
};

export function ErrorState({
  message,
  detail,
  type = "generic",
  onRetry,
  size = "md",
  className = "",
}) {
  const { Icon, label, bg, border, iconColor } = TYPE_MAP[type] || TYPE_MAP.generic;
  const displayMessage = message || label;

  const iconSizes = { sm: 16, md: 20, lg: 24 };
  const paddings  = { sm: "12px 16px", md: "20px 24px", lg: "28px 32px" };
  const titleSize = { sm: "0.82rem", md: "0.875rem", lg: "1rem" };
  const detailSize = { sm: "0.73rem", md: "0.78rem", lg: "0.82rem" };

  return (
    <div
      className={className}
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        background: bg,
        border: `1px solid ${border}`,
        borderRadius: RADIUS_MD,
        padding: paddings[size] || paddings.md,
      }}
    >
      <Icon
        size={iconSizes[size] || 20}
        style={{ color: iconColor, flexShrink: 0, marginTop: 1 }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontSize: titleSize[size] || titleSize.md,
            fontWeight: 600,
            color: TEXT_PRIMARY,
            margin: 0,
          }}
        >
          {displayMessage}
        </p>
        {detail && (
          <p
            style={{
              fontSize: detailSize[size] || detailSize.md,
              color: TEXT_TERTIARY,
              margin: "4px 0 0",
            }}
          >
            {detail}
          </p>
        )}
        {onRetry && (
          <button
            onClick={onRetry}
            style={{
              marginTop: 10,
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              fontSize: "0.75rem",
              fontWeight: 600,
              color: NAVY,
              background: "transparent",
              border: `1px solid ${BRD}`,
              borderRadius: RADIUS_MD,
              padding: "4px 10px",
              cursor: "pointer",
              transition: "background 150ms",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = NAVY_06; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
          >
            <RefreshCw size={11} />
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

export default ErrorState;

import React from "react";

/**
 * Badge — status and label indicators.
 * Variants: default | success | warning | danger | neutral | info | purple | outline
 * Sizes:    sm | md (default)
 *
 * color: an escape hatch for arbitrary per-entity/brand colors that don't map
 * onto the 8 fixed semantic variants (e.g. a conference/journal brand color).
 * Pass a hex string — Badge derives a soft tinted background and border from
 * it. Takes precedence over `variant` when present.
 */

// Every variant reads from the shared semantic-color group (index.css →
// tailwind.config.js: success/warning/danger/info/navy/crimson/violet) so a
// "success" badge always matches a "success" alert/callout exactly.
const VARIANTS = {
  default:  "bg-navy-wash        text-navy-700   border-navy-wash-border",
  success:  "bg-success-bg       text-success-text border-success-border",
  warning:  "bg-warning-bg       text-warning-text border-warning-border",
  danger:   "bg-danger-bg        text-danger-text  border-danger-border",
  neutral:  "bg-slate-100        text-slate-600  border-slate-200",
  info:     "bg-info-bg          text-info-text    border-info-border",
  purple:   "bg-violet-bg        text-violet-text  border-violet-200",
  outline:  "bg-transparent      text-slate-600  border-slate-300",
};

const DOT = {
  default: "bg-navy-700",
  success: "bg-emerald-600",
  warning: "bg-amber-600",
  danger:  "bg-crimson-600",
  neutral: "bg-slate-400",
  info:    "bg-blue-500",
  purple:  "bg-violet",
  outline: "bg-slate-400",
};

const SIZES = {
  sm: "text-[10px] px-1.5 py-0.5 gap-1",
  md: "text-[11px] px-2   py-0.5 gap-1.5",
};

export function Badge({ variant = "neutral", size = "md", dot = false, color, className = "", style, children }) {
  const base = [
    "inline-flex items-center font-medium border rounded-badge",
    color ? "" : (VARIANTS[variant] ?? VARIANTS.neutral),
    SIZES[size] ?? SIZES.md,
    className,
  ].filter(Boolean).join(" ");

  const colorStyle = color
    ? { background: `${color}18`, color, borderColor: `${color}33` }
    : undefined;

  return (
    <span className={base} style={{ ...colorStyle, ...style }}>
      {dot && (
        <span
          className={color ? "w-1.5 h-1.5 rounded-full shrink-0" : `w-1.5 h-1.5 rounded-full shrink-0 ${DOT[variant] ?? DOT.neutral}`}
          style={color ? { background: color } : undefined}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}

export default Badge;

import React from "react";

/**
 * Button — the one button system, shared with the public site and the
 * Sign In screens (same navy, same 4px shape, same deep-navy hover).
 *
 * Variants:
 *   primary   brand navy — the page's main action (one per view)
 *   secondary neutral surface with a hairline border
 *   ghost     = secondary (kept for existing callers)
 *   outline   = secondary (kept for existing callers)
 *   hero      = secondary. Page headers are light now; header actions read
 *             as secondary unless a page passes variant="primary".
 *   subtle    quiet filled neutral, for tertiary actions in dense UI
 *   link      text action
 *   danger    semantic red, destructive actions only (danger-outline: quiet version)
 * Sizes: sm | md (default) | lg | icon
 */

const BASE =
  "inline-flex items-center justify-center gap-2 font-semibold rounded-btn transition-colors duration-150 cursor-pointer select-none whitespace-nowrap " +
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy " +
  "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none";

// Every value is a named step on the shared navy/crimson scale
// (tailwind.config.js → index.css's --sq-* vars), so the family repaints
// from one place.
const SECONDARY = "border border-hairline-strong bg-white text-[color:var(--sq-text-primary)] hover:border-[color:var(--sq-text-primary)] active:bg-[color:var(--sq-surface-2)]";
const VARIANTS = {
  primary:   "border border-navy-700 bg-navy-700 text-white hover:bg-navy-800 hover:border-navy-800 active:bg-navy-900",
  secondary: SECONDARY,
  ghost:     SECONDARY,
  outline:   SECONDARY,
  hero:      SECONDARY,
  danger:    "border border-crimson-600 bg-crimson-600 text-white hover:bg-crimson-700 hover:border-crimson-700",
  // Destructive action that isn't the point of the view (e.g. Delete in a
  // page header): red text, quiet surface; the confirm dialog carries the weight.
  "danger-outline": "border border-crimson-200 bg-white text-crimson-600 hover:border-crimson-600",
  subtle:    "bg-[color:var(--sq-surface-2)] text-[color:var(--sq-text-secondary)] hover:text-[color:var(--sq-text-primary)] hover:bg-[#EEECE6]",
  link:      "bg-transparent text-navy-700 underline underline-offset-[3px] decoration-1 hover:decoration-2 p-0 h-auto",
};

const SIZES = {
  sm:   "h-8  px-3   text-xs   gap-1.5",
  md:   "h-9  px-4   text-[13px]",
  lg:   "h-11 px-5   text-sm",
  icon: "h-9  w-9    p-0 text-[13px]",
};

function Spinner({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="animate-spin" aria-hidden="true">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Button({
  variant  = "primary",
  size     = "md",
  loading  = false,
  disabled = false,
  as: Tag  = "button",
  className = "",
  children,
  ...props
}) {
  const isDisabled = disabled || loading;
  return (
    <Tag
      {...props}
      disabled={Tag === "button" ? isDisabled : undefined}
      aria-disabled={isDisabled || undefined}
      className={[BASE, VARIANTS[variant] ?? VARIANTS.primary, variant === "link" ? (size === "sm" ? "text-xs" : size === "lg" ? "text-sm" : "text-[13px]") : (SIZES[size] ?? SIZES.md), className]
        .filter(Boolean).join(" ")}
    >
      {loading && <Spinner size={size === "sm" ? 12 : 14} />}
      {children}
    </Tag>
  );
}

export default Button;

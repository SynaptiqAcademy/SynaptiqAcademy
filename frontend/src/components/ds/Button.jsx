import React from "react";

/**
 * Button — unified design system button.
 *
 * Variants: primary | ghost | danger | outline | subtle
 * Sizes:    sm | md (default) | lg | icon
 *
 * Replaces local BTN_PRIMARY / BTN_GHOST constants.
 */

const BASE =
  "inline-flex items-center justify-center gap-2 font-medium rounded-btn transition-all duration-150 cursor-pointer select-none " +
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy " +
  "active:scale-[0.98] " +
  "disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none disabled:active:scale-100";

// Every value here is a named step on the shared navy/crimson scale
// (tailwind.config.js → index.css's --sq-navy-*/--sq-crimson-* vars) —
// no arbitrary hex, so the whole button family repaints from one place.
const VARIANTS = {
  primary:
    "bg-navy-700 text-white hover:bg-navy-600 active:bg-navy-800 shadow-sq-xs hover:shadow-sq-sm",
  ghost:
    "border border-slate-200 bg-transparent text-slate-700 hover:border-slate-300 hover:bg-slate-50 active:bg-slate-100",
  danger:
    "bg-crimson-600 text-white hover:bg-crimson-700 active:bg-crimson-700 shadow-sq-xs",
  outline:
    "border border-navy-700 text-navy-700 bg-transparent hover:bg-navy-700 hover:text-white",
  subtle:
    "bg-slate-100 text-slate-700 hover:bg-slate-200 active:bg-slate-300",
  link:
    "bg-transparent text-navy-700 underline-offset-2 hover:underline p-0 h-auto font-medium",
};

const SIZES = {
  sm:   "h-7  px-2.5 text-xs   gap-1.5",
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
      className={[BASE, VARIANTS[variant] ?? VARIANTS.primary, SIZES[size] ?? SIZES.md, className]
        .filter(Boolean).join(" ")}
    >
      {loading && <Spinner size={size === "sm" ? 12 : 14} />}
      {children}
    </Tag>
  );
}

export default Button;

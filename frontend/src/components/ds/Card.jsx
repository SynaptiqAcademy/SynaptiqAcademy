/* eslint-disable */
import React from "react";
import { Link } from "react-router-dom";

/**
 * Card — the single visual container for all card-shaped content.
 *
 * Replaces: ds/Card.jsx (Tailwind), ui/card.jsx (shadcn), EntityCards CardShell (inline),
 *           PremiumCards Shell (inline), and all ad-hoc card divs across feature pages.
 *
 * Variants:
 *   default     — base card
 *   interactive — hover lift + border brighten (auto-applied when onClick or to is present)
 *   elevated    — stronger shadow, larger padding
 *   flush       — no padding
 *   ghost       — no border, no shadow
 *
 * Padding sizes: none | sm (12px) | md (16px) | lg (20px) | xl (24px)
 *   Defaults: flush→none, elevated→xl, others→md
 *
 * Link support: pass `to` to render as <Link>. Keyboard accessible.
 * onClick: auto-applies interactive variant unless explicitly overridden.
 *
 * accent: a token color (e.g. accent={EMERALD}) — renders a 3px colored left
 * border. Replaces the hand-rolled `style={{borderLeft: ...}}` pattern used
 * for "highlighted"/status cards across the app (e.g. PremiumCards.jsx's
 * ResearchCard `highlight` case).
 */

const BASE   = "bg-white border border-hairline rounded-card transition-all duration-150";
const INTER  = "hover:shadow-sq-card-hover hover:-translate-y-px cursor-pointer focus-visible:outline-none focus-visible:shadow-sq-focus";

const VARIANTS = {
  default:     "shadow-sq-card",
  interactive: `shadow-sq-card hover:border-hairline-strong ${INTER}`,
  elevated:    "shadow-sq-md",
  flush:       "shadow-sq-card",
  ghost:       "border-transparent shadow-none",
};

const PAD_SIZE = { none: "", sm: "p-3", md: "p-4", lg: "p-5", xl: "p-6" };

const VARIANT_DEFAULT_PAD = {
  default: "md", interactive: "md", elevated: "xl", flush: "none", ghost: "md",
};

export function Card({
  variant,
  className = "",
  padding,
  as: Tag = "div",
  to,
  onClick,
  href,
  style,
  accent,
  children,
  ...props
}) {
  // Auto-apply interactive when clickable, unless variant is explicit
  const isClickable = !!(to || onClick || href);
  const effectiveVariant = variant ?? (isClickable ? "interactive" : "default");
  const padKey  = padding ?? VARIANT_DEFAULT_PAD[effectiveVariant] ?? "md";
  const padCls  = PAD_SIZE[padKey] ?? "";
  const cls     = [BASE, VARIANTS[effectiveVariant], padCls, className].filter(Boolean).join(" ");
  const accentStyle = accent ? { borderLeft: `3px solid ${accent}` } : undefined;
  style = { ...accentStyle, ...style };

  // Link mode
  if (to) {
    return (
      <Link
        to={to}
        className={cls}
        style={{ textDecoration: "none", display: "block", ...style }}
        onClick={onClick}
        {...props}
      >
        {children}
      </Link>
    );
  }

  // External href mode
  if (href) {
    return (
      <a
        href={href}
        className={cls}
        style={{ textDecoration: "none", display: "block", ...style }}
        onClick={onClick}
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      >
        {children}
      </a>
    );
  }

  // Button / div mode
  return (
    <Tag
      className={cls}
      onClick={onClick}
      style={style}
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? "button" : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(e); } } : undefined}
      {...props}
    >
      {children}
    </Tag>
  );
}

Card.Header = function CardHeader({ className = "", children, ...props }) {
  return (
    <div className={`border-b border-hairline-soft pb-4 mb-4 ${className}`} {...props}>
      {children}
    </div>
  );
};

Card.Footer = function CardFooter({ className = "", children, ...props }) {
  return (
    <div className={`border-t border-hairline-soft pt-4 mt-4 ${className}`} {...props}>
      {children}
    </div>
  );
};

Card.Body = function CardBody({ className = "", children, ...props }) {
  return <div className={className} {...props}>{children}</div>;
};

export default Card;

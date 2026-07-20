import React from "react";
import { NAVY, BRDH, WHITE, RADIUS_FULL, TEXT_PRIMARY, TEXT_TERTIARY, MOTION } from "@/lib/tokens";

/**
 * Toggle — binary switch for immediate-effect settings.
 * NOT a substitute for Checkbox in forms — toggles apply instantly.
 * Shares its track/thumb visual language 1:1 with Form.jsx's `Switch`
 * (the form-embedded counterpart) — same tokens, same size scale, only the
 * label API differs (description/loading here vs hint/ariaLabel there).
 *
 * Sizes: sm | md (default)
 */
export function Toggle({
  checked,
  onChange,
  disabled = false,
  loading = false,
  label,
  description,
  size = "md",
  className = "",
  ...props
}) {
  const sizes = {
    sm: { track: [30, 16], thumb: 12, offset: 2, travel: 14 },
    md: { track: [40, 22], thumb: 18, offset: 2, travel: 18 },
  }[size] || { track: [40, 22], thumb: 18, offset: 2, travel: 18 };

  const [tw, th] = sizes.track;

  const trackStyle = {
    position: "relative",
    display: "inline-block",
    width: tw,
    height: th,
    borderRadius: RADIUS_FULL,
    background: checked ? NAVY : BRDH,
    cursor: disabled || loading ? "not-allowed" : "pointer",
    transition: `background ${MOTION.base} ${MOTION.ease}`,
    opacity: disabled ? 0.4 : 1,
    flexShrink: 0,
  };

  const thumbStyle = {
    position: "absolute",
    top: sizes.offset,
    left: sizes.offset,
    width: sizes.thumb,
    height: sizes.thumb,
    borderRadius: "50%",
    background: WHITE,
    boxShadow: "0 1px 3px rgba(15,23,42,0.25)",
    transform: `translateX(${checked ? sizes.travel : 0}px)`,
    transition: `transform ${MOTION.base} ${MOTION.ease}`,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };

  const handleClick = () => {
    if (!disabled && !loading) onChange?.(!checked);
  };

  const handleKey = (e) => {
    if (e.key === " " || e.key === "Enter") { e.preventDefault(); handleClick(); }
  };

  return (
    <div className={className} style={{ display: "flex", alignItems: label ? "flex-start" : "center", gap: 10 }}>
      <div
        role="switch"
        aria-checked={checked}
        aria-disabled={disabled}
        tabIndex={disabled ? -1 : 0}
        onClick={handleClick}
        onKeyDown={handleKey}
        style={trackStyle}
        {...props}
      >
        <div style={thumbStyle}>
          {loading && (
            <svg width={sizes.thumb - 4} height={sizes.thumb - 4} viewBox="0 0 24 24" fill="none" className="animate-spin">
              <circle cx="12" cy="12" r="10" stroke={NAVY} strokeWidth="3" strokeOpacity="0.25" />
              <path d="M12 2a10 10 0 0 1 10 10" stroke={NAVY} strokeWidth="3" strokeLinecap="round" />
            </svg>
          )}
        </div>
      </div>
      {(label || description) && (
        <div style={{ minWidth: 0 }}>
          {label && (
            <div style={{ fontSize: "0.825rem", fontWeight: 500, color: TEXT_PRIMARY, lineHeight: 1.4, cursor: disabled ? "not-allowed" : "pointer" }}
              onClick={handleClick}>
              {label}
            </div>
          )}
          {description && (
            <div style={{ fontSize: "0.75rem", color: TEXT_TERTIARY, marginTop: 2, lineHeight: 1.5 }}>
              {description}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Toggle;

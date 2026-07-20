/* eslint-disable */
import React from "react";
import { NAVY, BRD, BRDH, RADIUS_FULL, MOTION, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, CRIMSON, WHITE, WARM } from "@/lib/tokens";

// ── FormField ─────────────────────────────────────────────────────────────────
/**
 * FormField — wraps any input with label, hint, and error.
 *
 * Props:
 *   label     string
 *   hint      string   shown below input when no error
 *   error     string   replaces hint when set; turns input red
 *   required  bool     shows * on label
 *   id        string   forwarded to label htmlFor
 *   style     object
 */
export function FormField({ label, hint, error, required, id, children, style }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5, ...style }}>
      {label && (
        <label htmlFor={id} style={{ fontSize: "0.8125rem", fontWeight: 600, color: TEXT_PRIMARY, lineHeight: 1.4 }}>
          {label}
          {required && <span style={{ color: CRIMSON, marginLeft: 3 }} aria-hidden="true">*</span>}
        </label>
      )}
      {children}
      {error ? (
        <span role="alert" style={{ fontSize: "0.75rem", color: CRIMSON, lineHeight: 1.4 }}>{error}</span>
      ) : hint ? (
        <span style={{ fontSize: "0.75rem", color: TEXT_MUTED, lineHeight: 1.4 }}>{hint}</span>
      ) : null}
    </div>
  );
}

// ── FormGroup ─────────────────────────────────────────────────────────────────
/**
 * FormGroup — groups related FormFields with optional title/description.
 */
export function FormGroup({ title, description, children, divided = false, style }) {
  return (
    <div style={{
      paddingTop: divided ? 24 : 0,
      borderTop: divided ? `1px solid ${BRD}` : "none",
      ...style,
    }}>
      {(title || description) && (
        <div style={{ marginBottom: 16 }}>
          {title && (
            <h3 style={{ margin: "0 0 4px", fontSize: "0.9375rem", fontWeight: 600, color: TEXT_PRIMARY, letterSpacing: "-0.01em" }}>
              {title}
            </h3>
          )}
          {description && (
            <p style={{ margin: 0, fontSize: "0.8125rem", color: TEXT_MUTED, lineHeight: 1.55 }}>
              {description}
            </p>
          )}
        </div>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {children}
      </div>
    </div>
  );
}

// ── FormRow ───────────────────────────────────────────────────────────────────
/**
 * FormRow — horizontal grid of FormFields.
 */
export function FormRow({ cols = 2, gap = 16, children, style }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: `repeat(${cols}, 1fr)`, gap, ...style }}>
      {children}
    </div>
  );
}

// ── Checkbox ──────────────────────────────────────────────────────────────────
/**
 * Checkbox — accessible styled checkbox.
 *
 * Props:
 *   checked       bool
 *   onChange      fn(e)
 *   label         string
 *   hint          string   helper text under label
 *   indeterminate bool     shows dash instead of check
 *   disabled      bool
 */
export function Checkbox({ label, hint, checked, onChange, disabled, indeterminate, id, name, value, style }) {
  const inputRef = React.useRef(null);

  React.useEffect(() => {
    if (inputRef.current) inputRef.current.indeterminate = !!indeterminate;
  }, [indeterminate]);

  return (
    <label style={{ display: "flex", alignItems: "flex-start", gap: 9, cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1, ...style }}>
      <div style={{ position: "relative", flexShrink: 0, marginTop: 2 }}>
        <input
          ref={inputRef}
          type="checkbox"
          id={id}
          name={name}
          value={value}
          checked={!!checked}
          onChange={onChange}
          disabled={disabled}
          style={{ position: "absolute", opacity: 0, width: 16, height: 16, cursor: "inherit", margin: 0, zIndex: 1 }}
        />
        <div style={{
          width: 16, height: 16, borderRadius: 4, flexShrink: 0,
          border: `1.5px solid ${(checked || indeterminate) ? NAVY : "rgba(15,23,42,0.22)"}`,
          background: (checked || indeterminate) ? NAVY : WHITE,
          display: "flex", alignItems: "center", justifyContent: "center",
          transition: "all 100ms ease",
          pointerEvents: "none",
        }}>
          {checked && !indeterminate && (
            <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
              <path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
          {indeterminate && (
            <div style={{ width: 8, height: 1.5, background: "white", borderRadius: 1 }} />
          )}
        </div>
      </div>
      {(label || hint) && (
        <div style={{ flex: 1, minWidth: 0, marginTop: 1 }}>
          {label && <span style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, color: TEXT_PRIMARY, lineHeight: 1.5 }}>{label}</span>}
          {hint && <span style={{ display: "block", fontSize: "0.75rem", color: TEXT_MUTED, lineHeight: 1.4, marginTop: 2 }}>{hint}</span>}
        </div>
      )}
    </label>
  );
}

// ── Radio ─────────────────────────────────────────────────────────────────────

export function Radio({ label, hint, checked, onChange, disabled, id, name, value, style }) {
  return (
    <label style={{ display: "flex", alignItems: "flex-start", gap: 9, cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1, ...style }}>
      <div style={{ position: "relative", flexShrink: 0, marginTop: 2 }}>
        <input
          type="radio"
          id={id}
          name={name}
          value={value}
          checked={!!checked}
          onChange={onChange}
          disabled={disabled}
          style={{ position: "absolute", opacity: 0, width: 16, height: 16, cursor: "inherit", margin: 0, zIndex: 1 }}
        />
        <div style={{
          width: 16, height: 16, borderRadius: "50%", flexShrink: 0,
          border: `1.5px solid ${checked ? NAVY : "rgba(15,23,42,0.22)"}`,
          background: WHITE,
          display: "flex", alignItems: "center", justifyContent: "center",
          transition: "border-color 100ms ease",
          pointerEvents: "none",
        }}>
          {checked && (
            <div style={{ width: 7, height: 7, borderRadius: "50%", background: NAVY, transition: "transform 100ms ease", transform: checked ? "scale(1)" : "scale(0)" }} />
          )}
        </div>
      </div>
      {(label || hint) && (
        <div style={{ flex: 1, minWidth: 0, marginTop: 1 }}>
          {label && <span style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, color: TEXT_PRIMARY, lineHeight: 1.5 }}>{label}</span>}
          {hint && <span style={{ display: "block", fontSize: "0.75rem", color: TEXT_MUTED, lineHeight: 1.4, marginTop: 2 }}>{hint}</span>}
        </div>
      )}
    </label>
  );
}

// ── Switch ────────────────────────────────────────────────────────────────────

export function Switch({ checked, onChange, disabled, label, hint, ariaLabel, size = "md", style }) {
  // Shares its track/thumb visual language 1:1 with ds/Toggle.jsx (the
  // standalone instant-effect counterpart) — same tokens, same size scale,
  // only the label API differs (hint/ariaLabel here vs description/loading there).
  const sizes = {
    sm: { w: 30, h: 16, thumb: 12, offset: 2, travel: 14 },
    md: { w: 40, h: 22, thumb: 18, offset: 2, travel: 18 },
  };
  const s = sizes[size] ?? sizes.md;

  return (
    <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1, ...style }}>
      <button
        type="button"
        role="switch"
        aria-checked={!!checked}
        aria-label={ariaLabel || (typeof label === "string" ? label : undefined)}
        onClick={() => !disabled && onChange?.(!checked)}
        style={{
          width: s.w, height: s.h, borderRadius: RADIUS_FULL,
          border: "none", padding: 0, flexShrink: 0,
          background: checked ? NAVY : BRDH,
          position: "relative", cursor: "inherit",
          transition: `background ${MOTION.base} ${MOTION.ease}`,
        }}
      >
        <span style={{
          position: "absolute",
          top: s.offset, left: s.offset,
          width: s.thumb, height: s.thumb,
          borderRadius: "50%", background: WHITE,
          boxShadow: "0 1px 3px rgba(15,23,42,0.25)",
          transform: `translateX(${checked ? s.travel : 0}px)`,
          transition: `transform ${MOTION.base} ${MOTION.ease}`,
          display: "block",
        }} />
      </button>
      {(label || hint) && (
        <div style={{ flex: 1, minWidth: 0 }}>
          {label && <span style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, color: TEXT_PRIMARY, lineHeight: 1.5 }}>{label}</span>}
          {hint && <span style={{ display: "block", fontSize: "0.75rem", color: TEXT_MUTED, lineHeight: 1.4, marginTop: 1 }}>{hint}</span>}
        </div>
      )}
    </label>
  );
}

// ── RadioGroup ────────────────────────────────────────────────────────────────
/**
 * RadioGroup — renders a list of Radio options.
 *
 * Props:
 *   options  [{ value, label, hint?, disabled? }]
 *   value    string   currently selected value
 *   onChange fn(value)
 *   name     string
 */
export function RadioGroup({ options = [], value, onChange, name, disabled, gap = 8, style }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap, ...style }}>
      {options.map(opt => (
        <Radio
          key={opt.value}
          name={name}
          value={opt.value}
          label={opt.label}
          hint={opt.hint}
          checked={value === opt.value}
          onChange={() => onChange?.(opt.value)}
          disabled={disabled || opt.disabled}
        />
      ))}
    </div>
  );
}

// ── CheckboxGroup ─────────────────────────────────────────────────────────────
/**
 * CheckboxGroup — renders a list of Checkbox options for multi-select.
 *
 * Props:
 *   options  [{ value, label, hint?, disabled? }]
 *   value    string[]  currently checked values
 *   onChange fn(string[])
 */
export function CheckboxGroup({ options = [], value = [], onChange, disabled, gap = 8, style }) {
  const toggle = (v) => {
    const next = value.includes(v) ? value.filter(x => x !== v) : [...value, v];
    onChange?.(next);
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap, ...style }}>
      {options.map(opt => (
        <Checkbox
          key={opt.value}
          label={opt.label}
          hint={opt.hint}
          checked={value.includes(opt.value)}
          onChange={() => toggle(opt.value)}
          disabled={disabled || opt.disabled}
        />
      ))}
    </div>
  );
}

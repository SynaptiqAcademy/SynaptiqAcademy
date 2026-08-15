import React from "react";

/**
 * Textarea — canonical multiline input.
 * Replaces local TEXTAREA string constants.
 *
 * Forwards its ref to the underlying <textarea> (e.g. for auto-grow logic
 * driven by direct DOM measurement, or imperative `.focus()`).
 */
export const Textarea = React.forwardRef(function Textarea({
  label,
  hint,
  error,
  rows = 3,
  resize = true,
  className = "",
  wrapperClassName = "",
  id,
  ...props
}, ref) {
  // label may be a JSX node (e.g. a title + secondary hint span), not just a
  // string — only derive a slug from it when it actually is one.
  const inputId = id || (typeof label === "string" ? `ta-${label.toLowerCase().replace(/\s+/g, "-")}` : undefined);
  const errorId = error && inputId ? `${inputId}-error` : undefined;
  const hintId = hint && !error && inputId ? `${inputId}-hint` : undefined;

  const classes = [
    "w-full px-3 py-2.5 border rounded-input bg-white text-[13px] text-slate-900 placeholder:text-slate-400",
    "transition-colors duration-150",
    "focus:outline-none focus:ring-2 focus:ring-[rgba(15,40,71,0.15)] focus:border-[rgba(15,40,71,0.6)]",
    error
      ? "border-[#8A1538]/60 focus:ring-[rgba(138,21,56,0.15)]"
      : "border-slate-200 hover:border-slate-300",
    resize ? "resize-y" : "resize-none",
    "disabled:opacity-50 disabled:bg-slate-50 disabled:cursor-not-allowed",
    className,
  ].filter(Boolean).join(" ");

  return (
    <div className={`sq-form-group ${wrapperClassName}`}>
      {label && <label htmlFor={inputId} className="sq-form-label">{label}</label>}
      <textarea
        ref={ref}
        id={inputId}
        rows={rows}
        className={classes}
        aria-invalid={error ? true : undefined}
        aria-describedby={errorId || hintId || undefined}
        {...props}
      />
      {error   && <p id={errorId} className="sq-form-error" role="alert">{error}</p>}
      {hint && !error && <p id={hintId} className="sq-form-hint">{hint}</p>}
    </div>
  );
});

export default Textarea;

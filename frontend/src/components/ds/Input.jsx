import React from "react";

/**
 * Input — canonical text input.
 * Replaces local INPUT string constants across page files.
 *
 * Forwards its ref to the underlying <input> element, so callers needing
 * imperative access (e.g. `.focus()` on mount, after a clear action, or
 * `.scrollIntoView()`) can pass a ref directly instead of falling back to a
 * hand-rolled input.
 */
export const Input = React.forwardRef(function Input({
  label,
  hint,
  error,
  size = "md",
  prefix,
  suffix,
  className = "",
  wrapperClassName = "",
  id,
  ...props
}, ref) {
  // label may be a JSX node, not just a string — only derive a slug from it
  // when it actually is one.
  const inputId = id || (typeof label === "string" ? `input-${label.toLowerCase().replace(/\s+/g, "-")}` : undefined);
  const errorId = error && inputId ? `${inputId}-error` : undefined;
  const hintId = hint && !error && inputId ? `${inputId}-hint` : undefined;
  const heightClass = size === "sm" ? "h-7 text-[12px] px-2.5" : "h-9 text-[13px] px-3";
  const paddingLeft  = prefix ? (size === "sm" ? "pl-7"  : "pl-9")  : "";
  const paddingRight = suffix ? (size === "sm" ? "pr-7"  : "pr-9")  : "";

  const classes = [
    "w-full border rounded-input bg-white text-slate-900 placeholder:text-slate-400",
    "transition-colors duration-150",
    "focus:outline-none focus:ring-2 focus:ring-[rgba(15,40,71,0.15)] focus:border-[rgba(15,40,71,0.6)]",
    error
      ? "border-[#8A1538]/60 focus:ring-[rgba(138,21,56,0.15)]"
      : "border-slate-200 hover:border-slate-300",
    "disabled:opacity-50 disabled:bg-slate-50 disabled:cursor-not-allowed",
    heightClass, paddingLeft, paddingRight,
    className,
  ].filter(Boolean).join(" ");

  return (
    <div className={`sq-form-group ${wrapperClassName}`}>
      {label && <label htmlFor={inputId} className="sq-form-label">{label}</label>}
      <div className="relative flex items-center">
        {prefix && (
          <div className="absolute left-0 pl-2.5 pointer-events-none text-slate-400">{prefix}</div>
        )}
        <input
          ref={ref}
          id={inputId}
          className={classes}
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId || hintId || undefined}
          {...props}
        />
        {suffix && (
          <div className="absolute right-0 pr-2.5 pointer-events-none text-slate-400">{suffix}</div>
        )}
      </div>
      {error   && <p id={errorId} className="sq-form-error" role="alert">{error}</p>}
      {hint && !error && <p id={hintId} className="sq-form-hint">{hint}</p>}
    </div>
  );
});

export default Input;

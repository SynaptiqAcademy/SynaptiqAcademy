import React from "react";

/**
 * Textarea — canonical multiline input.
 * Replaces local TEXTAREA string constants.
 */
export function Textarea({
  label,
  hint,
  error,
  rows = 3,
  resize = true,
  className = "",
  wrapperClassName = "",
  id,
  ...props
}) {
  const inputId = id || (label ? `ta-${label.toLowerCase().replace(/\s+/g, "-")}` : undefined);

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
      <textarea id={inputId} rows={rows} className={classes} {...props} />
      {error   && <p className="sq-form-error">{error}</p>}
      {hint && !error && <p className="sq-form-hint">{hint}</p>}
    </div>
  );
}

export default Textarea;

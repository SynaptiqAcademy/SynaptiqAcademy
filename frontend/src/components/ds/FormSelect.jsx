import React from "react";
import { ChevronDown } from "lucide-react";

/**
 * FormSelect — simple HTML select wrapper.
 * Named FormSelect to avoid collision with shadcn's radix-based Select in /ui.
 * Replaces local SELECT string constants in forms.
 */
export function FormSelect({
  label,
  hint,
  error,
  size = "md",
  className = "",
  wrapperClassName = "",
  id,
  children,
  ...props
}) {
  const inputId = id || (label ? `sel-${label.toLowerCase().replace(/\s+/g, "-")}` : undefined);
  const heightClass = size === "sm" ? "h-7 text-[12px]" : "h-9 text-[13px]";

  const classes = [
    "w-full pl-3 pr-8 appearance-none border rounded-input bg-white text-slate-900",
    "transition-colors duration-150",
    "focus:outline-none focus:ring-2 focus:ring-[rgba(15,40,71,0.15)] focus:border-[rgba(15,40,71,0.6)]",
    error
      ? "border-[#8A1538]/60"
      : "border-slate-200 hover:border-slate-300",
    "disabled:opacity-50 disabled:bg-slate-50 disabled:cursor-not-allowed",
    heightClass,
    className,
  ].filter(Boolean).join(" ");

  return (
    <div className={`sq-form-group ${wrapperClassName}`}>
      {label && <label htmlFor={inputId} className="sq-form-label">{label}</label>}
      <div className="relative">
        <select id={inputId} className={classes} {...props}>
          {children}
        </select>
        <ChevronDown
          size={13}
          strokeWidth={1.5}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
        />
      </div>
      {error   && <p className="sq-form-error">{error}</p>}
      {hint && !error && <p className="sq-form-hint">{hint}</p>}
    </div>
  );
}

export default FormSelect;

import React from "react";
import { FormSelect } from "@/components/ds/FormSelect";
import { Switch } from "@/components/ds/Form";
import { TEXT_PRIMARY, TEXT_MUTED } from "@/lib/tokens";

/**
 * PreferenceRow — one labeled control inside a PreferenceCard.
 * `control` is "switch" | "select"; `caption` is shown for preferences that
 * are stored but not yet wired to a real app-wide effect (honesty label —
 * never claim a preference does something it doesn't).
 */
export function PreferenceRow({ label, hint, caption, control = "switch", value, onChange, options }) {
  const labelBlock = (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: TEXT_PRIMARY }}>{label}</div>
      {hint && <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 2 }}>{hint}</div>}
      {caption && <div style={{ fontSize: 10.5, color: TEXT_MUTED, marginTop: 3, fontStyle: "italic" }}>{caption}</div>}
    </div>
  );

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
      {labelBlock}
      <div style={{ flexShrink: 0, minWidth: control === "select" ? 140 : undefined, maxWidth: control === "select" ? 165 : undefined }}>
        {control === "switch" ? (
          <Switch checked={!!value} onChange={onChange} ariaLabel={label} size="sm" />
        ) : (
          <FormSelect value={value} onChange={(e) => onChange(e.target.value)} aria-label={label} size="sm" style={{ width: "100%" }}>
            {options.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </FormSelect>
        )}
      </div>
    </div>
  );
}

export default PreferenceRow;

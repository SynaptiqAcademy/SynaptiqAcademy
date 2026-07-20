import React from "react";
import { Card } from "@/components/ds/Card";
import { TEXT_MUTED, TEXT_PRIMARY, BRD, NAVY, NAVY_08 } from "@/lib/tokens";

/**
 * PreferenceCard — modular card wrapper for a small group of related
 * preferences. Settings is built as a grid of these (never one long
 * stacked form). `icon` renders in a small circular badge beside the title.
 */
export function PreferenceCard({ title, description, icon: Icon, children, style }) {
  return (
    <Card padding="md" style={{ display: "flex", flexDirection: "column", gap: 4, height: "100%", ...style }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 4 }}>
        {Icon && (
          <div style={{
            width: 38, height: 38, borderRadius: "50%", background: NAVY_08,
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <Icon size={16} strokeWidth={1.75} style={{ color: NAVY }} />
          </div>
        )}
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: TEXT_PRIMARY, letterSpacing: "-0.01em" }}>{title}</div>
          {description && <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 2, lineHeight: 1.5 }}>{description}</div>}
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, borderTop: `1px solid ${BRD}`, paddingTop: 16, marginTop: 8 }}>
        {children}
      </div>
    </Card>
  );
}

export default PreferenceCard;

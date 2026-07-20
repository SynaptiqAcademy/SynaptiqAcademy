/* eslint-disable */
import React from "react";
import { PageLayout } from "@/components/ds/PageLayout";
import { ADMIN_BG } from "@/lib/tokens";

/** AdministrationLayout — admin panel pages. Uses ADMIN_BG to distinguish from user-facing areas. */
export function AdministrationLayout({ title, subtitle, icon, actions, nav, toolbar, summaryRow, children }) {
  return (
    <div style={{ background: ADMIN_BG, flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
      <PageLayout
        title={title}
        subtitle={subtitle}
        icon={icon}
        actions={actions}
        nav={nav}
        toolbar={toolbar}
      >
        {summaryRow && <div style={{ marginBottom: 24 }}>{summaryRow}</div>}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>{children}</div>
      </PageLayout>
    </div>
  );
}

export default AdministrationLayout;

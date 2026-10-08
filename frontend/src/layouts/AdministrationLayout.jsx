/* eslint-disable */
import React from "react";
import { PageLayout } from "@/components/ds/PageLayout";

/** AdministrationLayout — admin panel pages. Same surface as every other page; the title says it is an admin page. */
export function AdministrationLayout({ title, subtitle, icon, actions, stats, ring, nav, toolbar, summaryRow, sidebar, children }) {
  return (
    <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
      <PageLayout
        title={title}
        subtitle={subtitle}
        icon={icon}
        actions={actions}
        stats={stats}
        ring={ring}
        nav={nav}
        toolbar={toolbar}
        aside={sidebar}
        asideWidth={360}
      >
        {summaryRow && <div style={{ marginBottom: 24 }}>{summaryRow}</div>}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>{children}</div>
      </PageLayout>
    </div>
  );
}

export default AdministrationLayout;

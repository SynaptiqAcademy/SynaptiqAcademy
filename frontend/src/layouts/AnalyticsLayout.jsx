/* eslint-disable */
import React from "react";
import { PageLayout } from "@/components/ds/PageLayout";

/** AnalyticsLayout — data/metrics/reporting pages. Thin wrapper around PageLayout. */
export function AnalyticsLayout({ title, subtitle, icon, actions, stats, ring, nav, toolbar, summaryRow, sidebar, children }) {
  return (
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
  );
}

export default AnalyticsLayout;

/* eslint-disable */
import React from "react";
import { PageLayout } from "@/components/ds/PageLayout";

/** AnalyticsLayout — data/metrics/reporting pages. Thin wrapper around PageLayout. */
export function AnalyticsLayout({ title, subtitle, icon, actions, nav, toolbar, summaryRow, children }) {
  return (
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
  );
}

export default AnalyticsLayout;

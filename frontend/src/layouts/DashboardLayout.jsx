/* eslint-disable */
import React from "react";
import { PageLayout } from "@/components/ds/PageLayout";

/**
 * DashboardLayout — thin wrapper around PageLayout.
 * Used by: Home, Today, ImpactDashboard, ReputationAnalytics, etc.
 */
export function DashboardLayout({
  greeting,     // maps to title slot
  actions,
  banner,
  widgets,      // renders above children
  primary,      // main column content
  secondary,    // right aside content (320px)
  children,
}) {
  const hasColumns = primary != null;

  const mainContent = (
    <>
      {widgets && <div style={{ marginBottom: 24 }}>{widgets}</div>}
      {hasColumns ? (
        <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 24 }}>
            {primary}
          </div>
          {secondary && (
            <aside style={{ width: 320, flexShrink: 0, display: "flex", flexDirection: "column", gap: 16 }}>
              {secondary}
            </aside>
          )}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>{children}</div>
      )}
    </>
  );

  return (
    <PageLayout
      title={typeof greeting === "string" ? greeting : undefined}
      actions={actions}
      banner={banner}
    >
      {mainContent}
    </PageLayout>
  );
}

export default DashboardLayout;

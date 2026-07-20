/* eslint-disable */
import React from "react";
import { PageLayout } from "@/components/ds/PageLayout";

/** ResearchLayout — research workspace pages. Thin wrapper around PageLayout. */
export function ResearchLayout({ title, subtitle, icon, actions, nav, toolbar, sidebar, children }) {
  return (
    <PageLayout
      title={title}
      subtitle={subtitle}
      icon={icon}
      actions={actions}
      nav={nav}
      toolbar={toolbar}
      aside={sidebar}
      asideWidth={360}
    >
      {children}
    </PageLayout>
  );
}

export default ResearchLayout;

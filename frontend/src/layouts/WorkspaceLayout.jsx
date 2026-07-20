/* eslint-disable */
import React from "react";
import { PageLayout } from "@/components/ds/PageLayout";

/**
 * WorkspaceLayout — split-pane shell for editor/composer pages.
 * Used by: manuscript editor, statistical workspaces, grant workspaces, etc.
 */
export function WorkspaceLayout({
  title,
  subtitle,
  icon,
  actions,
  toolbar,
  editor,       // main editing pane
  panel,        // right assistant/review panel
  panelWidth = 360,
  children,
}) {
  const hasSplit = editor != null;

  return (
    <PageLayout
      title={title}
      subtitle={subtitle}
      icon={icon}
      actions={actions}
      toolbar={toolbar}
      aside={hasSplit ? panel : undefined}
      asideWidth={panelWidth}
      split={hasSplit}
      noPad={hasSplit}
    >
      {hasSplit ? editor : children}
    </PageLayout>
  );
}

export default WorkspaceLayout;

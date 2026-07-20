import React from "react";

/**
 * PageContent — semantic main content wrapper.
 *
 * Pass into WorkspaceLayout's children slot.
 * Stack PageSection(s) inside for consistent visual rhythm.
 *
 * Usage:
 *   <WorkspaceLayout ...>
 *     <PageContent>
 *       <PageSection title="Active">...</PageSection>
 *       <PageSection title="Drafts">...</PageSection>
 *     </PageContent>
 *   </WorkspaceLayout>
 *
 * Or pass children directly to WorkspaceLayout (PageContent is optional):
 *   <WorkspaceLayout ...>
 *     <PageSection title="Active">...</PageSection>
 *   </WorkspaceLayout>
 */
export function PageContent({ children, gap = 28, style }) {
  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        gap,
        ...style,
      }}
    >
      {children}
    </main>
  );
}

export default PageContent;

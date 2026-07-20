/* eslint-disable */
import React from "react";
import { PageLayout } from "@/components/ds/PageLayout";

/** ArtifactLayout — detail/viewer pages with a custom full-width hero section. */
export function ArtifactLayout({ header, actions, nav, main, aside, children }) {
  const customHeroContent = (header || actions || nav) ? (
    <div style={{ padding: "24px 24px 0" }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: nav ? 16 : 0 }}>
        <div style={{ flex: 1, minWidth: 0 }}>{header}</div>
        {actions && (
          <div style={{ display: "flex", gap: 8, flexShrink: 0, marginLeft: 16 }}>{actions}</div>
        )}
      </div>
      {nav}
    </div>
  ) : undefined;

  return (
    <PageLayout
      customHero={customHeroContent}
      aside={aside}
      asideWidth={300}
    >
      {main ?? children}
    </PageLayout>
  );
}

export default ArtifactLayout;

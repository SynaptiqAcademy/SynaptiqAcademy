/* eslint-disable */
import React from "react";
import { PageLayout } from "@/components/ds/PageLayout";
import { NAVY, NAVY2, WHITE } from "@/lib/tokens";

/** ArtifactLayout — detail/viewer pages with a custom full-width hero section, painted
 * navy to match the platform-wide hero standard (see PageLayout.jsx). `header`/`actions`/
 * `nav` are caller-supplied — style their text/buttons for a dark background (white text,
 * Button variant="hero"/"subtle") since PageLayout's outer customHero wrapper stays white. */
export function ArtifactLayout({ header, actions, nav, main, aside, children }) {
  const customHeroContent = (header || actions || nav) ? (
    <div style={{
      margin: "4px 24px 20px",
      padding: "26px 28px 22px",
      borderRadius: 16,
      background: `linear-gradient(135deg, ${NAVY} 0%, ${NAVY2} 100%)`,
      color: WHITE,
    }}>
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

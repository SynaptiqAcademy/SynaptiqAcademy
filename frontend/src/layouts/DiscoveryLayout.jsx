/* eslint-disable */
import React from "react";
import { PageLayout } from "@/components/ds/PageLayout";

/** DiscoveryLayout — browse/search/catalogue pages. Left sidebar optional. */
export function DiscoveryLayout({ title, subtitle, icon, actions, searchBar, filters, sidebar, nav, customHero, noPad, children }) {
  const toolbar = (searchBar || filters)
    ? <>{searchBar}{filters}</>
    : undefined;

  return (
    <PageLayout
      title={title}
      subtitle={subtitle}
      icon={icon}
      actions={actions}
      nav={nav}
      toolbar={toolbar}
      aside={sidebar}
      asideWidth={240}
      asideLeft={!!sidebar}
      customHero={customHero}
      noPad={noPad}
    >
      {children}
    </PageLayout>
  );
}

export default DiscoveryLayout;

/* eslint-disable */
import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { PageLayout } from "@/components/ds/PageLayout";
import { NavTabs } from "@/components/ds/NavTabs";
import { NAVY } from "@/lib/tokens";
import { Sparkles } from "lucide-react";

/**
 * ResearchLayout — the single canonical layout for every page under Academic
 * Network, Research, Teaching, Publishing, Funding, and AI Workspace. Thin
 * wrapper around PageLayout; asideWidth/asideLeft are fixed (not
 * configurable per-page) so every page in these 6 sections renders an
 * identical shell.
 *
 * `navItems` is optional: when given, auto-builds a NavTabs row from it
 * (same behavior the retired AIWorkspaceLayout had for AI tool pages) and
 * defaults the hero icon to Sparkles/NAVY unless an explicit `icon` is
 * passed. Pages that need a search/filter toolbar (previously DiscoveryLayout)
 * just compose it themselves and pass it via `toolbar`.
 */
export function ResearchLayout({
  title, subtitle, icon, actions, nav, toolbar, sidebar,
  navItems, activePath, customHero, noPad, children,
}) {
  const location = useLocation();
  const navigate = useNavigate();

  let resolvedNav = nav;
  let resolvedIcon = icon;
  if (navItems && !nav) {
    const active = activePath ?? location.pathname;
    const items = navItems.map((i) => ({ id: i.id, label: i.label }));
    resolvedNav = (
      <NavTabs items={items} active={active} onChange={(id) => navigate(id)} variant="underline" size="sm" />
    );
    resolvedIcon = icon ?? <Sparkles size={15} style={{ color: NAVY }} />;
  }

  return (
    <PageLayout
      title={title}
      subtitle={subtitle}
      icon={resolvedIcon}
      actions={actions}
      nav={resolvedNav}
      toolbar={toolbar}
      aside={sidebar}
      asideWidth={360}
      asideLeft={false}
      customHero={customHero}
      noPad={noPad}
    >
      {children}
    </PageLayout>
  );
}

export default ResearchLayout;

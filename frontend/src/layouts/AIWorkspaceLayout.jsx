/* eslint-disable */
import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { PageLayout } from "@/components/ds/PageLayout";
import { NavTabs } from "@/components/ds/NavTabs";
import { AI_NAV_ITEMS } from "@/lib/navItems";
import { NAVY } from "@/lib/tokens";
import { Sparkles } from "lucide-react";

/** AIWorkspaceLayout — AI tool pages with auto-driven nav from AI_NAV_ITEMS. */
export function AIWorkspaceLayout({ title, subtitle, actions, toolbar, sidebar, children, activePath, navItems }) {
  const location = useLocation();
  const navigate = useNavigate();
  const active = activePath ?? location.pathname;
  const items = (navItems ?? AI_NAV_ITEMS).map(i => ({ id: i.id, label: i.label }));

  return (
    <PageLayout
      title={title}
      subtitle={subtitle}
      icon={<Sparkles size={15} style={{ color: NAVY }} />}
      actions={actions}
      nav={
        <NavTabs
          items={items}
          active={active}
          onChange={id => navigate(id)}
          variant="underline"
          size="sm"
        />
      }
      toolbar={toolbar}
      aside={sidebar}
      asideWidth={360}
    >
      {children}
    </PageLayout>
  );
}

export default AIWorkspaceLayout;

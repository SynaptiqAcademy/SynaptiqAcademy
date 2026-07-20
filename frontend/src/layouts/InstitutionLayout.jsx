/* eslint-disable */
import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { PageLayout } from "@/components/ds/PageLayout";
import { NavTabs } from "@/components/ds/NavTabs";
import { INSTITUTION_NAV_ITEMS } from "@/lib/navItems";
import { NAVY } from "@/lib/tokens";
import { Building2 } from "lucide-react";

/** InstitutionLayout — institution_platform/* pages with auto-driven nav. */
export function InstitutionLayout({ title, subtitle, actions, toolbar, sidebar, children, activePath }) {
  const location = useLocation();
  const navigate = useNavigate();
  const active = activePath ?? location.pathname;

  return (
    <PageLayout
      title={title}
      subtitle={subtitle}
      icon={<Building2 size={15} style={{ color: NAVY }} />}
      actions={actions}
      nav={
        <NavTabs
          items={INSTITUTION_NAV_ITEMS.map(i => ({ id: i.id, label: i.label }))}
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

export default InstitutionLayout;

/* eslint-disable */
import React from "react";
import { PageLayout } from "@/components/ds/PageLayout";
import { Avatar } from "@/components/ds/Avatar";
import { BRD, NAVY, WHITE, TEXT_PRIMARY, TEXT_SECONDARY } from "@/lib/tokens";

/** ProfileLayout — researcher profile pages. Custom identity hero via PageLayout's customHero. */
export function ProfileLayout({
  name,
  title: jobTitle,
  institution,
  avatar,
  verified,
  stats,
  actions,
  nav,
  sidebar,
  children,
}) {
  const heroContent = (
    <div style={{ padding: "24px 24px 0" }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 16, marginBottom: 16 }}>
        <Avatar src={avatar} name={name} size="xl" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h1 style={{ fontSize: "1.25rem", fontWeight: 700, color: TEXT_PRIMARY, margin: 0, letterSpacing: "-0.01em" }}>
              {name}
            </h1>
            {verified && (
              <span style={{
                fontSize: "0.7rem", fontWeight: 600, color: WHITE,
                background: NAVY, padding: "2px 7px", borderRadius: 100,
              }}>
                ✓ Verified
              </span>
            )}
          </div>
          {(jobTitle || institution) && (
            <p style={{ fontSize: "0.82rem", color: TEXT_SECONDARY, margin: "4px 0 0" }}>
              {[jobTitle, institution].filter(Boolean).join(" · ")}
            </p>
          )}
          {stats && (
            <div style={{ display: "flex", gap: 20, marginTop: 10, flexWrap: "wrap" }}>{stats}</div>
          )}
        </div>
        {actions && (
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>{actions}</div>
        )}
      </div>
      {nav}
    </div>
  );

  return (
    <PageLayout
      customHero={heroContent}
      aside={sidebar}
      asideWidth={300}
    >
      {children}
    </PageLayout>
  );
}

export default ProfileLayout;

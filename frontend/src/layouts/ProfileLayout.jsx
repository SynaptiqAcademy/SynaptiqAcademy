/* eslint-disable */
import React from "react";
import { CheckCircle2 } from "lucide-react";
import { PageLayout } from "@/components/ds/PageLayout";
import { Avatar } from "@/components/ds/Avatar";
import { NAVY, NAVY2, WHITE } from "@/lib/tokens";

/** ProfileLayout — researcher profile pages. Custom identity hero via PageLayout's
 * customHero — painted navy (matching Academic Passport's PassportHero) since
 * PageLayout's outer customHero wrapper stays a plain white bleed band. */
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
    <div style={{
      margin: "4px 24px 20px",
      padding: "26px 28px 22px",
      borderRadius: 16,
      background: `linear-gradient(135deg, ${NAVY} 0%, ${NAVY2} 100%)`,
      color: WHITE,
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 16, marginBottom: nav ? 16 : 0 }}>
        <div style={{ borderRadius: "50%", border: "3px solid rgba(255,255,255,0.2)", overflow: "hidden", flexShrink: 0 }}>
          <Avatar src={avatar} name={name} size="xl" />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <h1 style={{ fontSize: "1.25rem", fontWeight: 700, color: WHITE, margin: 0, letterSpacing: "-0.01em" }}>
              {name}
            </h1>
            {verified && (
              <span style={{
                display: "inline-flex", alignItems: "center", gap: 4,
                fontSize: "0.7rem", fontWeight: 600, color: WHITE,
                background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.16)",
                padding: "3px 8px", borderRadius: 100,
              }}>
                <CheckCircle2 size={11} style={{ color: "#38BDF8" }} /> Verified
              </span>
            )}
          </div>
          {(jobTitle || institution) && (
            <p style={{ fontSize: "0.82rem", color: "rgba(255,255,255,0.65)", margin: "4px 0 0" }}>
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

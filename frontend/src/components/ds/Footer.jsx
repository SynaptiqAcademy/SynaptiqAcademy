import React from "react";
import { Link } from "react-router-dom";
import { BRD, TEXT_MUTED, WARM, ADMIN_BG } from "@/lib/tokens";

/**
 * Footer — the one shell footer, rendered once per page inside ds/ContentFrame.
 * Minimal by design (not a marketing footer): a copyright line and a small set
 * of links to pages that actually exist.
 *
 * Props:
 *   variant   "app" | "admin"   background matches the surrounding shell
 */
export function Footer({ variant = "app" }) {
  const year = new Date().getFullYear();

  return (
    <footer
      style={{
        marginTop: 32,
        padding: "16px 0",
        borderTop: `1px solid ${BRD}`,
        background: variant === "admin" ? ADMIN_BG : WARM,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
        flexWrap: "wrap",
        fontSize: "0.75rem",
        color: TEXT_MUTED,
      }}
    >
      <span>© {year} Synaptiq</span>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <FooterLink to="/help-center">Help Center</FooterLink>
        <FooterLink to="/settings">Settings</FooterLink>
      </div>
    </footer>
  );
}

function FooterLink({ to, children }) {
  const [hov, setHov] = React.useState(false);
  return (
    <Link
      to={to}
      style={{ color: hov ? "inherit" : TEXT_MUTED, textDecoration: "none", transition: "color 100ms" }}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
    >
      {children}
    </Link>
  );
}

export default Footer;

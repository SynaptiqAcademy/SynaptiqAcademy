import React from "react";
import { useLocation } from "react-router-dom";
import { Breadcrumb } from "./Breadcrumb";
import { Footer } from "./Footer";
import { getBreadcrumbTrail } from "@/lib/breadcrumbTrail";
import { CONTAINER_MAX } from "@/lib/tokens";

// Full-bleed, immersive-viewport pages (chat, live editors) manage their own
// exact-viewport height math and don't want the shell's Footer competing for
// vertical space below the fold. Same convention as breadcrumbTrail's HIDDEN
// set — an explicit, small allowlist rather than per-page opt-out plumbing.
const FLUSH_ROUTES = new Set(["/messages", "/notifications"]);

/**
 * ContentFrame — the one place that owns breadcrumb + page container + footer,
 * used inside both AppShell and AdminShell. Sidebar/TopNav render around this;
 * this renders around whatever the current route provides (children or
 * <Outlet/>), so container width, spacing, breadcrumb, and footer can never
 * drift between the two shells again.
 *
 * Breadcrumb note: the admin variant already renders its own breadcrumb
 * inside AdminTopNavBody (sourced from the admin nav config, same as
 * Sidebar's admin variant reads ADMIN_SECTIONS instead of NAV_SECTIONS) — so
 * ContentFrame only owns the breadcrumb row for the app variant, to avoid
 * rendering it twice. Both ultimately render through the one ds/Breadcrumb.
 *
 * Props:
 *   variant   "app" | "admin"
 *   children  the routed page content
 */
export function ContentFrame({ variant = "app", children }) {
  const { pathname } = useLocation();
  const flush = FLUSH_ROUTES.has(pathname);
  const trail = variant === "app" && !flush ? getBreadcrumbTrail(pathname) : null;

  return (
    <div
      style={{
        maxWidth: CONTAINER_MAX,
        margin: "0 auto",
        width: "100%",
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        flex: 1,
        minHeight: 0,
      }}
    >
      {trail && (
        <div style={{ marginBottom: 20 }}>
          <Breadcrumb items={trail} />
        </div>
      )}

      <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        {children}
      </div>

      {!flush && <Footer variant={variant} />}
    </div>
  );
}

export default ContentFrame;

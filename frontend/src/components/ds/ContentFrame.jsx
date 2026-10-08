import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
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
// The last path segment when it looks like a record id (not a word like
// "new" or "settings"): ids here are 24-char hex, UUIDs or other long tokens.
function routeRecordId(pathname) {
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length < 2) return null;
  const last = parts[parts.length - 1];
  return /^[A-Za-z0-9_-]{8,}$/.test(last) && /\d/.test(last) ? last : null;
}

function NotAvailable({ status, pathname }) {
  const parent = "/" + pathname.split("/").filter(Boolean).slice(0, -1).join("/");
  const forbidden = status === 403;
  return (
    <div style={{ maxWidth: 560, padding: "24px 0" }} role="status">
      <h1 className="pl-hero-title" style={{ fontSize: "1.6rem" }}>
        {forbidden ? "You don't have access to this." : "This isn't available."}
      </h1>
      <p className="pl-sub" style={{ marginTop: 8 }}>
        {forbidden
          ? "It belongs to a team, project or institution you're not part of. Nothing in your account has changed."
          : "It may have been removed, or the link is out of date. Nothing in your account has changed."}
      </p>
      <div style={{ marginTop: 16 }}>
        <Link to={parent || "/discover"} className="inline-flex items-center h-9 px-4 text-[13px] font-semibold rounded-btn border border-hairline-strong bg-white text-[color:var(--sq-text-primary)] no-underline hover:border-[color:var(--sq-text-primary)]">
          Go back
        </Link>
      </div>
    </div>
  );
}

export function ContentFrame({ variant = "app", children }) {
  const { pathname } = useLocation();
  const [missing, setMissing] = useState(null);
  useEffect(() => {
    setMissing(null);
    const id = routeRecordId(pathname);
    if (!id) return undefined;
    const onMissing = (e) => {
      const path = String(e.detail?.url || "").split("?")[0].replace(/\/+$/, "");
      if (path.endsWith("/" + id)) setMissing(e.detail.status);
    };
    window.addEventListener("synaptiq:record-missing", onMissing);
    return () => window.removeEventListener("synaptiq:record-missing", onMissing);
  }, [pathname]);
  const flush = FLUSH_ROUTES.has(pathname);
  const trail = variant === "app" && !flush ? getBreadcrumbTrail(pathname) : null;

  return (
    <div
      className="sq-frame"
      style={{
        maxWidth: CONTAINER_MAX,
        margin: "0 auto",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        flex: 1,
        minHeight: 0,
      }}
    >
      {trail && (
        <div style={{ marginBottom: 14 }}>
          <Breadcrumb items={trail} />
        </div>
      )}

      <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        {missing ? <NotAvailable status={missing} pathname={pathname} /> : children}
      </div>

      {!flush && <Footer variant={variant} />}
    </div>
  );
}

export default ContentFrame;

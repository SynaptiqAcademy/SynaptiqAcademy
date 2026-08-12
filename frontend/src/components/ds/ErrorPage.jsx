import React from "react";
import { Link } from "react-router-dom";
import { Button } from "./Button";
import { NAVY, WARM, BRD, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, FONT_SERIF } from "@/lib/tokens";
import { ArrowLeft, Home } from "lucide-react";

/**
 * ErrorPage — the one full-page error template (404, 500, offline, generic
 * failure). Replaces hand-rolled full-page error markup (e.g. the old
 * NotFound.jsx layout) — every page-level error state should render this
 * instead of its own `min-h-screen` wrapper.
 *
 * Props:
 *   code          string    — large display code, e.g. "404" or "500" (optional)
 *   title         string    — headline (required)
 *   description   ReactNode — supporting text/detail (can include a <code> path)
 *   primaryAction { label, to?, onClick?, icon? }  — defaults to "Back to dashboard" → "/"
 *   secondaryAction { label, to?, onClick?, icon? } — e.g. "Go back" → history.back()
 *   quickLinks    [{ to, label, icon }]  — optional link grid below the actions
 */
export function ErrorPage({
  code,
  title,
  description,
  primaryAction = { label: "Back to dashboard", to: "/", icon: Home },
  secondaryAction = { label: "Go back", onClick: () => window.history.back(), icon: ArrowLeft },
  quickLinks,
}) {
  return (
    <div style={{ minHeight: "100vh", background: WARM, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "96px 24px" }}>
      <div style={{ width: "100%", maxWidth: 480 }}>
        <div style={{ fontSize: 10, fontFamily: "monospace", letterSpacing: "0.2em", textTransform: "uppercase", color: TEXT_MUTED, marginBottom: 32 }}>
          Synaptiq
        </div>

        {code && (
          <div style={{ fontFamily: FONT_SERIF, fontSize: "5rem", lineHeight: 1, color: NAVY, marginBottom: 16 }} aria-hidden="true">
            {code}
          </div>
        )}

        <h1 style={{ fontSize: 20, fontWeight: 500, color: TEXT_PRIMARY, margin: "0 0 8px" }}>{title}</h1>
        {description && <div style={{ fontSize: 13, color: TEXT_SECONDARY, marginBottom: 32, lineHeight: 1.6 }}>{description}</div>}

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 40 }}>
          {primaryAction && <ActionButton {...primaryAction} variant="primary" />}
          {secondaryAction && <ActionButton {...secondaryAction} variant="outline" />}
        </div>

        {quickLinks?.length > 0 && (
          <div style={{ borderTop: `1px solid ${BRD}`, paddingTop: 32 }}>
            <div style={{ fontSize: 10, fontFamily: "monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: TEXT_MUTED, marginBottom: 16 }}>
              Quick links
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {quickLinks.map(({ to, label, icon: Icon }) => (
                <Link key={to} to={to} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: TEXT_SECONDARY, textDecoration: "none", padding: "6px 0" }}>
                  {Icon && <Icon size={13} strokeWidth={1.5} style={{ color: TEXT_MUTED, flexShrink: 0 }} />}
                  {label}
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ActionButton({ label, to, onClick, icon: Icon, variant }) {
  const content = (
    <>
      {Icon && <Icon size={14} strokeWidth={1.5} />}
      {label}
    </>
  );
  return to
    ? <Button as={Link} to={to} variant={variant}>{content}</Button>
    : <Button onClick={onClick} variant={variant}>{content}</Button>;
}

export default ErrorPage;

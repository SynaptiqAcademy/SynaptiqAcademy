import React from "react";
import { Link } from "react-router-dom";
import { Button } from "./Button";
import { WARM, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, SUCCESS, SUCCESS_BG, RADIUS_FULL } from "@/lib/tokens";
import { CheckCircle2 } from "lucide-react";

/**
 * SuccessPage — the one full-page confirmation/success template (email
 * verified, payment complete, submission received, account created).
 * Replaces one-off hand-rolled "you're done" pages.
 *
 * Props:
 *   icon          ReactNode — defaults to a check-circle
 *   title         string    — headline (required)
 *   description   ReactNode — supporting text
 *   primaryAction { label, to?, onClick?, icon? }
 *   secondaryAction { label, to?, onClick?, icon? }
 *   children      ReactNode — optional extra content below the actions
 *                             (e.g. a summary card, a receipt, next steps)
 */
export function SuccessPage({
  icon,
  title,
  description,
  primaryAction,
  secondaryAction,
  children,
}) {
  return (
    <div style={{ minHeight: "100vh", background: WARM, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "96px 24px" }}>
      <div style={{ width: "100%", maxWidth: 480, textAlign: "center" }}>
        <div style={{
          width: 56, height: 56, borderRadius: RADIUS_FULL, background: SUCCESS_BG,
          display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px",
        }}>
          {icon
            ? React.cloneElement(icon, { size: 28, style: { color: SUCCESS } })
            : <CheckCircle2 size={28} style={{ color: SUCCESS }} />}
        </div>

        <h1 style={{ fontSize: 20, fontWeight: 500, color: TEXT_PRIMARY, margin: "0 0 8px" }}>{title}</h1>
        {description && <div style={{ fontSize: 13, color: TEXT_SECONDARY, marginBottom: 32, lineHeight: 1.6 }}>{description}</div>}

        {(primaryAction || secondaryAction) && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, marginBottom: children ? 32 : 0 }}>
            {primaryAction && <ActionButton {...primaryAction} variant="primary" />}
            {secondaryAction && <ActionButton {...secondaryAction} variant="outline" />}
          </div>
        )}

        {children}
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

export default SuccessPage;

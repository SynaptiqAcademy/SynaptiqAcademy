/* eslint-disable */
import React from "react";
import { Link } from "react-router-dom";
import { Bell, Settings, Zap } from "lucide-react";
import { WHITE, RADIUS_FULL } from "@/lib/tokens";
import { Avatar } from "@/components/ds/Avatar";
import { transition } from "@/lib/motion";

function getGreeting() {
  const h = new Date().getHours();
  if (h < 5)  return "Good night";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function formatDate() {
  return new Date().toLocaleDateString("en-GB", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });
}

const GLASS_BTN = {
  width: 32, height: 32, borderRadius: "50%",
  border: "1px solid rgba(255,255,255,0.14)",
  background: "rgba(255,255,255,0.06)",
  display: "flex", alignItems: "center", justifyContent: "center",
  cursor: "pointer", flexShrink: 0, textDecoration: "none",
  transition: transition.hover,
};

function IconBtn({ onClick, children, to, "aria-label": ariaLabel }) {
  const props = {
    style: GLASS_BTN,
    "aria-label": ariaLabel,
    onMouseEnter: e => { e.currentTarget.style.background = "rgba(255,255,255,0.12)"; },
    onMouseLeave: e => { e.currentTarget.style.background = "rgba(255,255,255,0.06)"; },
  };
  if (to) return <Link to={to} {...props}>{children}</Link>;
  return <button onClick={onClick} {...props}>{children}</button>;
}

export default function WelcomeHeader({ user, billing, notifCount, navigate }) {
  const firstName = user?.first_name || user?.full_name?.split(" ")[0] || "Researcher";
  const fullName  = user?.full_name || firstName;
  const credits   = billing?.credits;
  const planName  = billing?.plan?.name || null;
  const balance   = credits?.monthly_balance ?? credits?.balance ?? null;

  return (
    <div className="flex flex-col gap-8">

      {/* ── Utility row — identity + system controls, sits above the fold ── */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Avatar url={user?.avatar_url} name={fullName} size={30} />
          <span
            style={{
              fontSize: "0.72rem", fontWeight: 600, letterSpacing: "0.02em",
              color: "rgba(255,255,255,0.55)",
            }}
          >
            {formatDate()}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {planName && (
            <Link
              to="/settings/billing"
              style={{
                fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.03em",
                color: WHITE, background: "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.14)",
                borderRadius: RADIUS_FULL, padding: "4px 11px",
                textDecoration: "none", textTransform: "uppercase",
              }}
            >
              {planName}
            </Link>
          )}

          {balance != null && (
            <Link
              to="/ai-credits"
              style={{
                display: "inline-flex", alignItems: "center", gap: 5,
                padding: "4px 11px", borderRadius: RADIUS_FULL,
                background: "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.14)",
                textDecoration: "none", fontSize: "0.68rem", fontWeight: 700,
                color: "#A7F3D0", letterSpacing: "0.01em",
                transition: transition.hover,
              }}
              onMouseEnter={e => { e.currentTarget.style.background = "rgba(255,255,255,0.14)"; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.08)"; }}
            >
              <Zap size={10} strokeWidth={2.5} />
              {balance.toLocaleString()}
            </Link>
          )}

          <div style={{ position: "relative" }}>
            <IconBtn to="/notifications" aria-label="Notifications">
              <Bell size={13} strokeWidth={1.75} style={{ color: "rgba(255,255,255,0.75)" }} />
            </IconBtn>
            {notifCount > 0 && (
              <span
                style={{
                  position: "absolute", top: -2, right: -2,
                  minWidth: 13, height: 13, borderRadius: RADIUS_FULL,
                  background: "#F87171", color: WHITE,
                  fontSize: "0.48rem", fontWeight: 700,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  padding: "0 3px", border: "1.5px solid #0F2847",
                }}
              >
                {notifCount > 9 ? "9+" : notifCount}
              </span>
            )}
          </div>

          <IconBtn to="/settings" aria-label="Settings">
            <Settings size={12} strokeWidth={1.75} style={{ color: "rgba(255,255,255,0.75)" }} />
          </IconBtn>
        </div>
      </div>

      {/* ── The headline — the one thing every visit starts with ── */}
      <div className="sq-fade-up">
        <h1
          style={{
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: "clamp(1.9rem, 4vw, 2.75rem)",
            fontWeight: 700,
            letterSpacing: "-0.03em",
            lineHeight: 1.08,
            color: WHITE,
            margin: 0,
          }}
        >
          {getGreeting()}, {firstName}.
        </h1>
        <p
          style={{
            fontSize: "0.92rem",
            color: "rgba(255,255,255,0.55)",
            marginTop: 8,
          }}
        >
          What are we working on today?
        </p>
      </div>
    </div>
  );
}

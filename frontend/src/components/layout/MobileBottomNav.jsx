/* eslint-disable */
/**
 * MobileBottomNav — mirrors the desktop top nav's four primary destinations.
 *
 * Home · Inbox · Messages · Meetings · More
 *
 * "More" opens the full navigation drawer (all research sections).
 */
import React, { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { House, Inbox, MessageSquare, CalendarDays, LayoutGrid } from "lucide-react";
import { useUnread } from "../../contexts/UnreadContext";
import { NAVY } from "@/lib/tokens";

// ─── Individual tab ───────────────────────────────────────────────────────────

function BottomTab({ to, label, icon: Icon, badge, badgeColor, exact }) {
  const { pathname } = useLocation();
  const isActive = exact
    ? pathname === to
    : pathname === to || pathname.startsWith(to + "/");

  return (
    <NavLink
      to={to}
      aria-label={label}
      aria-current={isActive ? "page" : undefined}
      className={() => `flex flex-col items-center justify-center gap-0.5 flex-1 py-2 transition-colors relative ${
        isActive ? "text-[#0F2847]" : "text-slate-400 hover:text-slate-600"
      }`}
    >
      {/* Active top bar */}
      {isActive && (
        <span
          className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-[#0F2847]"
          aria-hidden="true"
        />
      )}

      {/* Icon + badge */}
      <div className="relative">
        <Icon size={18} strokeWidth={1.5} />
        {badge != null && badge > 0 && (
          <span
            style={{
              position: "absolute",
              top: -6,
              right: -8,
              minWidth: 14,
              height: 14,
              background: badgeColor || NAVY,
              color: "white",
              fontSize: 8,
              fontFamily: "monospace",
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "0 2px",
              lineHeight: 1,
              borderRadius: 100,
            }}
            aria-hidden="true"
          >
            {badge > 99 ? "99+" : badge}
          </span>
        )}
      </div>

      <span className="text-[10px] font-medium tracking-wide">{label}</span>
    </NavLink>
  );
}

// ─── More / Tools tab ─────────────────────────────────────────────────────────

function MoreTab({ onOpen }) {
  const { pathname } = useLocation();

  // "More" is active when on any route not covered by the four primary tabs
  const primaryRoutes = ["/discover", "/notifications", "/messages", "/meetings"];
  const isActive = !primaryRoutes.some(
    (r) => pathname === r || pathname.startsWith(r + "/")
  );

  return (
    <button
      onClick={onOpen}
      aria-label="Open navigation menu"
      aria-haspopup="dialog"
      className={`flex flex-col items-center justify-center gap-0.5 flex-1 py-2 transition-colors relative ${
        isActive ? "text-[#0F2847]" : "text-slate-400 hover:text-slate-600"
      }`}
    >
      {isActive && (
        <span
          className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-[#0F2847]"
          aria-hidden="true"
        />
      )}
      <LayoutGrid size={18} strokeWidth={1.5} />
      <span className="text-[10px] font-medium tracking-wide">More</span>
    </button>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function MobileBottomNav({ onOpenDrawer }) {
  const { total: msgUnread } = useUnread();
  const [notifCount, setNotifCount] = useState(0);
  const { pathname } = useLocation();

  // Increment Inbox badge on incoming WebSocket notifications
  useEffect(() => {
    const handler = () => setNotifCount((n) => n + 1);
    window.addEventListener("synaptiq:notification", handler);
    return () => window.removeEventListener("synaptiq:notification", handler);
  }, []);

  // Clear Inbox badge when user visits /notifications
  useEffect(() => {
    if (pathname === "/notifications") setNotifCount(0);
  }, [pathname]);

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 h-16 z-40 md:hidden bg-white border-t border-[rgba(15,23,42,0.08)] flex items-stretch"
      aria-label="Primary navigation"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <BottomTab
        to="/discover"
        label="Home"
        icon={House}
        exact
      />
      <BottomTab
        to="/notifications"
        label="Inbox"
        icon={Inbox}
        exact
        badge={notifCount}
        badgeColor="#8A1538"
      />
      <BottomTab
        to="/messages"
        label="Messages"
        icon={MessageSquare}
        badge={msgUnread}
        badgeColor={NAVY}
      />
      <BottomTab
        to="/meetings"
        label="Meetings"
        icon={CalendarDays}
      />
      <MoreTab onOpen={onOpenDrawer} />
    </nav>
  );
}

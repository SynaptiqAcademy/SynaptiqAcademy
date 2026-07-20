/* eslint-disable */
/**
 * TopNav — the one canonical top navigation bar in the product.
 *
 * variant="app"   (default) — Home/Inbox/Messages/Meetings with G+key chord
 *                  shortcuts, search trigger, Credits balance, + Create
 *                  dropdown, Avatar dropdown.
 * variant="admin" — the simpler Admin OS top bar: breadcrumbs, search
 *                  trigger, live-connection badge.
 *
 * Both variants are desktop-only (hidden below `lg`) — MobileTopBar is the
 * distinct small-viewport counterpart for the app shell, same as
 * MobileDrawer is the mobile counterpart of the Sidebar.
 */
import React, { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  House, Inbox, MessageSquare, CalendarDays,
  Search, Plus, Sparkles, ChevronDown,
  FileText, FolderOpen, BookMarked, BadgeDollarSign, Archive,
  BrainCircuit, LayoutGrid, Bot,
  Settings, CreditCard, LogOut,
  Keyboard, HelpCircle, ExternalLink, BookOpen,
  Fingerprint, ShieldCheck, Radio,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useUnread } from "@/contexts/UnreadContext";
import api from "@/lib/api";
import { loadPrefs } from "@/hooks/usePreferences";
import {
  NAVY, BRD, NAVY_06, NAVY_08, NAVY_04,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, TEXT_MUTED, ACCENT,
  HEADER_H,
} from "@/lib/tokens";
import { Breadcrumb } from "./Breadcrumb";
import { Badge } from "./Badge";
import { findAdminNavEntry } from "@/config/adminNavigation";
import { useAdminRealtime } from "@/contexts/AdminRealtimeContext";

export function TopNav({ variant = "app", onOpenPalette, onOpenSearch }) {
  if (variant === "admin") return <AdminTopNavBody onOpenSearch={onOpenSearch} />;
  return <AppTopNavBody onOpenPalette={onOpenPalette} />;
}

export default TopNav;

// ═══════════════════════════════════════════════════════════════════════════
// APP VARIANT — full research/teaching-OS top bar
// ═══════════════════════════════════════════════════════════════════════════

const BAR_H      = HEADER_H;
const ITEM_PAD   = "6px 11px";
const ITEM_R     = 7;
const ITEM_SZ    = 13;
const ICON_SZ    = 14;
const BADGE_H    = 15;
const BADGE_PAD  = "0 5px";

const BADGE_COLOR = {
  notif:    "#8A1538",
  messages: NAVY,
  meetings: "#047857",
};

const PRIMARY_NAV = [
  { to: "/discover",      label: "Home",     icon: House,         exact: true,  badgeKey: null,        shortcut: "G H" },
  { to: "/notifications", label: "Inbox",    icon: Inbox,         exact: true,  badgeKey: "notif",     shortcut: "G I" },
  { to: "/messages",      label: "Messages", icon: MessageSquare, exact: false, badgeKey: "messages",  shortcut: "G M" },
  { to: "/meetings",      label: "Meetings", icon: CalendarDays,  exact: false, badgeKey: "meetings",  shortcut: "G E" },
];

const CREATE_ITEMS = [
  {
    group: "Research",
    items: [
      { label: "New Research Project", icon: FolderOpen,      to: "/projects" },
      { label: "New Workspace",        icon: LayoutGrid,      to: "/workspaces" },
      { label: "New Manuscript",       icon: FileText,        to: "/manuscripts" },
      { label: "Literature Review",    icon: BookMarked,      to: "/literature-review" },
      { label: "Grant Application",    icon: BadgeDollarSign, to: "/grants" },
      { label: "Import to Repository", icon: Archive,         to: "/repository" },
    ],
  },
  {
    group: "Collaborate",
    items: [
      { label: "New Conversation", icon: MessageSquare, to: "/messages" },
      { label: "Schedule Meeting", icon: CalendarDays,  to: "/meetings" },
    ],
  },
  {
    group: "AI",
    items: [
      { label: "AI Session",       icon: BrainCircuit, to: "/ai" },
      { label: "Agent Workforce",  icon: Bot,          to: "/agent-workforce" },
    ],
  },
];

// Notifications lives ONLY as the top-nav bell (see PRIMARY_NAV) — not
// duplicated here, to keep exactly one entry point per feature.
const AVATAR_SECTIONS = [
  {
    id: "identity",
    items: [
      { label: "Academic Passport",   icon: Fingerprint, to: "/academic-passport" },
    ],
  },
  {
    id: "menu",
    items: [
      { label: "Account Settings",       icon: Settings,    to: "/settings" },
      { label: "Billing & Subscription", icon: CreditCard,  to: "/settings/billing" },
      { label: "Security & Privacy",     icon: ShieldCheck, to: "/settings/security" },
      { label: "Keyboard Shortcuts",     icon: Keyboard,    to: "/settings?section=keyboard" },
      { label: "Help Center",            icon: BookOpen,    to: "/help-center" },
    ],
  },
];

function useClickOutside(ref, onClose) {
  useEffect(() => {
    if (!onClose) return;
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [ref, onClose]);
}

function NavItem({ to, label, icon: Icon, exact, badge, badgeKey, shortcut, pathname }) {
  const [hov, setHov] = useState(false);
  const isActive = exact
    ? pathname === to
    : pathname === to || pathname.startsWith(to + "/");

  const bg   = isActive ? NAVY_08 : hov ? NAVY_04 : "transparent";
  const clr  = isActive ? NAVY : TEXT_TERTIARY;
  const fw   = isActive ? "600" : "500";
  const bClr = BADGE_COLOR[badgeKey] || NAVY;

  return (
    <Link
      to={to}
      title={`${label} · ${shortcut}`}
      aria-current={isActive ? "page" : undefined}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: ITEM_PAD,
        borderRadius: ITEM_R,
        fontSize: ITEM_SZ,
        fontWeight: fw,
        color: clr,
        background: bg,
        textDecoration: "none",
        whiteSpace: "nowrap",
        position: "relative",
        transition: "background 0.12s ease, color 0.12s ease",
        letterSpacing: "-0.01em",
      }}
    >
      <Icon size={ICON_SZ} strokeWidth={1.5} style={{ flexShrink: 0 }} />
      {label}
      {badge != null && badge > 0 && (
        <span
          aria-label={`${badge} unread`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            minWidth: BADGE_H,
            height: BADGE_H,
            padding: BADGE_PAD,
            borderRadius: 100,
            background: bClr,
            color: "white",
            fontSize: 9,
            fontFamily: "monospace",
            fontWeight: 700,
            letterSpacing: "0",
            lineHeight: 1,
            flexShrink: 0,
          }}
        >
          {badge > 99 ? "99+" : badge}
        </span>
      )}
    </Link>
  );
}

function VDivider() {
  return (
    <div
      aria-hidden="true"
      style={{ width: 1, height: 18, background: "rgba(15,23,42,0.10)", flexShrink: 0 }}
    />
  );
}

function TopNavDropdown({ children, style }) {
  return (
    <div
      style={{
        position: "absolute",
        top: "calc(100% + 6px)",
        right: 0,
        background: "white",
        border: "1px solid rgba(15,23,42,0.10)",
        borderRadius: 10,
        boxShadow: "0 8px 24px rgba(15,23,42,0.12), 0 2px 6px rgba(15,23,42,0.06)",
        zIndex: 300,
        overflow: "hidden",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function CreateDropdown({ onClose }) {
  const navigate = useNavigate();

  const go = (to) => {
    onClose();
    navigate(to);
  };

  return (
    <TopNavDropdown style={{ width: 240, padding: "8px 0" }}>
      {CREATE_ITEMS.map((section) => (
        <div key={section.group}>
          <div style={{
            padding: "6px 14px 3px",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: TEXT_MUTED,
          }}>
            {section.group}
          </div>
          {section.items.map((item) => (
            <CreateMenuItem key={item.label} item={item} onSelect={() => go(item.to)} />
          ))}
        </div>
      ))}
    </TopNavDropdown>
  );
}

function CreateMenuItem({ item, onSelect }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onSelect}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        width: "100%",
        padding: "7px 14px",
        border: "none",
        background: hov ? "rgba(15,23,42,0.04)" : "transparent",
        cursor: "pointer",
        textAlign: "left",
        transition: "background 0.1s",
      }}
    >
      <span style={{
        width: 26,
        height: 26,
        borderRadius: 6,
        background: "rgba(15,23,42,0.05)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
      }}>
        <item.icon size={13} strokeWidth={1.5} style={{ color: NAVY }} />
      </span>
      <span style={{ fontSize: 12.5, fontWeight: 500, color: TEXT_PRIMARY, letterSpacing: "-0.01em" }}>
        {item.label}
      </span>
    </button>
  );
}

function AvatarDropdown({ user, onClose, onSignOut }) {
  const navigate = useNavigate();

  const handleItem = (item) => {
    onClose();
    if (item.external) {
      window.open(item.to, "_blank", "noopener");
      return;
    }
    navigate(item.to);
  };

  const initials = (user?.full_name || "U")
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <TopNavDropdown style={{ width: 240, padding: "0 0 6px" }}>
      <div style={{
        padding: "14px 14px 12px",
        borderBottom: "1px solid rgba(15,23,42,0.07)",
        marginBottom: 4,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "rgba(15,23,42,0.07)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
            flexShrink: 0,
          }}>
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            ) : (
              <span style={{ fontSize: 11, fontWeight: 700, color: NAVY }}>{initials}</span>
            )}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: TEXT_PRIMARY, letterSpacing: "-0.01em", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {user?.full_name || "Researcher"}
            </div>
            <div style={{ fontSize: 11, color: TEXT_MUTED, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {user?.email || ""}
            </div>
          </div>
        </div>
      </div>

      {AVATAR_SECTIONS.map((section, si) => (
        <div key={section.id}>
          {section.heading && (
            <div style={{
              padding: "6px 14px 2px",
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: TEXT_MUTED,
            }}>
              {section.heading}
            </div>
          )}
          {section.items.map((item) => (
            <AvatarMenuItem key={item.label} item={item} onSelect={() => handleItem(item)} />
          ))}
          {si < AVATAR_SECTIONS.length - 1 && (
            <div style={{ height: 1, background: "rgba(15,23,42,0.06)", margin: "4px 0" }} />
          )}
        </div>
      ))}

      <div style={{ height: 1, background: "rgba(15,23,42,0.06)", margin: "4px 0" }} />
      <AvatarMenuItem
        item={{ label: "Sign Out", icon: LogOut }}
        onSelect={() => { onClose(); onSignOut(); }}
        danger
      />
    </TopNavDropdown>
  );
}

function AvatarMenuItem({ item, onSelect, danger }) {
  const [hov, setHov] = useState(false);
  const Icon = item.icon;
  const clr = danger
    ? (hov ? "#991B1B" : "#DC2626")
    : (hov ? NAVY : TEXT_SECONDARY);

  return (
    <button
      onClick={onSelect}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 9,
        width: "100%",
        padding: "7px 14px",
        border: "none",
        background: hov ? (danger ? "rgba(220,38,38,0.05)" : "rgba(15,23,42,0.04)") : "transparent",
        cursor: "pointer",
        textAlign: "left",
        transition: "background 0.1s",
      }}
    >
      <Icon size={13} strokeWidth={1.5} style={{ color: clr, flexShrink: 0 }} />
      <span style={{ fontSize: 12.5, fontWeight: 500, color: clr, letterSpacing: "-0.01em" }}>
        {item.label}
      </span>
      {item.hint && (
        <span style={{ marginLeft: "auto", fontSize: 10, color: TEXT_MUTED }}>{item.hint}</span>
      )}
      {item.external && (
        <ExternalLink size={9} strokeWidth={1.5} style={{ marginLeft: "auto", color: TEXT_MUTED, flexShrink: 0 }} />
      )}
    </button>
  );
}

function SearchTrigger({ onOpen }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onOpen}
      aria-label="Open command palette (⌘K)"
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        border: `1px solid ${hov ? "rgba(15,23,42,0.18)" : "rgba(15,23,42,0.10)"}`,
        background: hov ? "white" : "#F8FAFC",
        borderRadius: 7,
        padding: "0 10px",
        height: 32,
        maxWidth: 340,
        width: "100%",
        color: TEXT_MUTED,
        cursor: "pointer",
        transition: "border-color 0.12s, background 0.12s, box-shadow 0.12s",
        boxShadow: hov ? "0 1px 4px rgba(15,23,42,0.06)" : "none",
        flexShrink: 1,
        minWidth: 120,
      }}
    >
      <Search size={12} strokeWidth={1.5} style={{ flexShrink: 0 }} />
      <span style={{
        fontSize: 12.5,
        flex: 1,
        textAlign: "left",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
        color: TEXT_MUTED,
      }}>
        Search or jump to…
      </span>
      <kbd style={{
        fontSize: 10,
        fontFamily: "monospace",
        border: "1px solid #E2E8F0",
        color: TEXT_MUTED,
        padding: "1px 5px",
        borderRadius: 4,
        background: "white",
        lineHeight: 1.5,
        flexShrink: 0,
      }}>
        ⌘K
      </kbd>
    </button>
  );
}

function AppTopNavBody({ onOpenPalette }) {
  const { user, logout }       = useAuth();
  const { total: unreadMsg }   = useUnread();
  const { pathname }           = useLocation();
  const navigate               = useNavigate();

  const [credits,       setCredits]       = useState(null);
  const [notifCount,    setNotifCount]    = useState(0);
  const [createOpen,    setCreateOpen]    = useState(false);
  const [avatarOpen,    setAvatarOpen]    = useState(false);
  const [createHov,     setCreateHov]     = useState(false);
  const [avatarHov,     setAvatarHov]     = useState(false);

  const createRef = useRef(null);
  const avatarRef = useRef(null);

  useClickOutside(createRef, createOpen ? () => setCreateOpen(false) : null);
  useClickOutside(avatarRef, avatarOpen ? () => setAvatarOpen(false) : null);

  useEffect(() => {
    api.get("/credits/balance")
      .then((r) => setCredits(r.data.balance))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const handler = () => setNotifCount((n) => n + 1);
    window.addEventListener("synaptiq:notification", handler);
    return () => window.removeEventListener("synaptiq:notification", handler);
  }, []);

  useEffect(() => {
    if (pathname === "/notifications") setNotifCount(0);
  }, [pathname]);

  const gRef      = useRef(false);
  const gTimerRef = useRef(null);

  useEffect(() => {
    const SHORTCUTS = { h: "/discover", i: "/notifications", m: "/messages", e: "/meetings" };
    const handler = (e) => {
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA" ||
        document.activeElement?.isContentEditable
      ) return;
      if (loadPrefs().gKeyShortcutsEnabled === false) return;
      const key = e.key.toLowerCase();
      if (key === "g") {
        gRef.current = true;
        clearTimeout(gTimerRef.current);
        gTimerRef.current = setTimeout(() => { gRef.current = false; }, 800);
        return;
      }
      if (gRef.current && SHORTCUTS[key]) {
        e.preventDefault();
        gRef.current = false;
        clearTimeout(gTimerRef.current);
        navigate(SHORTCUTS[key]);
      }
    };
    window.addEventListener("keydown", handler);
    return () => {
      window.removeEventListener("keydown", handler);
      clearTimeout(gTimerRef.current);
    };
  }, [navigate]);

  const badges = {
    notif:    notifCount,
    messages: unreadMsg || 0,
    meetings: 0,
  };

  const initials = (user?.full_name || "U")
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const handleSignOut = () => {
    if (logout) logout();
  };

  return (
    <header
      className="hidden lg:flex items-center shrink-0 sticky top-0 z-20 bg-white"
      style={{
        height: BAR_H,
        borderBottom: `1px solid ${BRD}`,
        padding: "0 16px",
        gap: 8,
      }}
      role="banner"
    >
      <nav
        role="navigation"
        aria-label="Primary navigation"
        style={{ display: "flex", alignItems: "center", gap: 2, flexShrink: 0 }}
      >
        {PRIMARY_NAV.map((item) => (
          <NavItem
            key={item.to}
            {...item}
            badge={item.badgeKey ? badges[item.badgeKey] : null}
            pathname={pathname}
          />
        ))}
      </nav>

      <div style={{ flex: 1 }} />

      <SearchTrigger onOpen={onOpenPalette} />

      {credits !== null && (
        <Link
          to="/ai-credits"
          title="AI Credits remaining"
          className="flex items-center gap-1.5 text-[11.5px] font-mono text-slate-500 hover:text-[#0F2847] transition-colors px-1.5 py-1 hover:bg-slate-50 shrink-0"
          style={{ borderRadius: 4 }}
        >
          <Sparkles size={11} strokeWidth={1.5} className="text-[#0F2847]" />
          {credits.toLocaleString()} cr
        </Link>
      )}

      <VDivider />

      <div ref={createRef} style={{ position: "relative", flexShrink: 0 }}>
        <button
          onClick={() => { setCreateOpen((o) => !o); setAvatarOpen(false); }}
          onMouseEnter={() => setCreateHov(true)}
          onMouseLeave={() => setCreateHov(false)}
          aria-haspopup="menu"
          aria-expanded={createOpen}
          aria-label="Create new item"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            height: 30,
            padding: "0 10px 0 9px",
            borderRadius: 6,
            border: `1px solid ${createOpen || createHov ? "rgba(15,23,42,0.25)" : "rgba(15,23,42,0.15)"}`,
            background: createOpen ? NAVY : createHov ? "rgba(15,23,42,0.05)" : "white",
            cursor: "pointer",
            transition: "all 0.12s",
          }}
        >
          <Plus
            size={12}
            strokeWidth={2.5}
            style={{ color: createOpen ? "white" : NAVY, flexShrink: 0 }}
          />
          <span style={{
            fontSize: 12.5,
            fontWeight: 600,
            color: createOpen ? "white" : NAVY,
            letterSpacing: "-0.01em",
          }}>
            Create
          </span>
          <ChevronDown
            size={11}
            strokeWidth={2}
            style={{
              color: createOpen ? "rgba(255,255,255,0.7)" : TEXT_MUTED,
              transform: createOpen ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.15s",
              flexShrink: 0,
            }}
          />
        </button>

        {createOpen && (
          <CreateDropdown onClose={() => setCreateOpen(false)} />
        )}
      </div>

      <div ref={avatarRef} style={{ position: "relative", flexShrink: 0 }}>
        <button
          onClick={() => { setAvatarOpen((o) => !o); setCreateOpen(false); }}
          onMouseEnter={() => setAvatarHov(true)}
          onMouseLeave={() => setAvatarHov(false)}
          aria-haspopup="menu"
          aria-expanded={avatarOpen}
          aria-label={`Account menu for ${user?.full_name || "user"}`}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            padding: 0,
            border: "none",
            background: "transparent",
            cursor: "pointer",
          }}
        >
          <div style={{
            width: 30,
            height: 30,
            borderRadius: "50%",
            background: avatarHov || avatarOpen ? "rgba(15,23,42,0.12)" : "rgba(15,23,42,0.07)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
            transition: "background 0.12s",
            outline: avatarOpen ? `2px solid ${NAVY}` : "none",
            outlineOffset: 1,
          }}>
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            ) : (
              <span style={{ fontSize: 10.5, fontWeight: 700, lineHeight: 1, color: NAVY }}>{initials}</span>
            )}
          </div>
        </button>

        {avatarOpen && (
          <AvatarDropdown
            user={user}
            onClose={() => setAvatarOpen(false)}
            onSignOut={handleSignOut}
          />
        )}
      </div>
    </header>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ADMIN VARIANT — simpler Admin OS top bar
// ═══════════════════════════════════════════════════════════════════════════

function useAdminBreadcrumbs() {
  const { pathname } = useLocation();
  const entry = findAdminNavEntry(pathname);
  if (!entry) return [{ label: "Admin OS" }];
  const { section, item } = entry;
  if (item.end) return [{ label: item.label }];
  return [{ label: section.label }, { label: item.label }];
}

const ADMIN_STATUS_META = {
  connected:  { variant: "success", label: "Live" },
  connecting: { variant: "warning", label: "Connecting…" },
  offline:    { variant: "neutral", label: "Offline" },
};

function AdminTopNavBody({ onOpenSearch }) {
  const crumbs = useAdminBreadcrumbs();
  const { status } = useAdminRealtime();
  const meta = ADMIN_STATUS_META[status] || ADMIN_STATUS_META.offline;

  return (
    <header
      style={{ height: HEADER_H }}
      className="flex items-center justify-between px-4 border-b border-slate-200 bg-white flex-shrink-0"
    >
      <Breadcrumb items={crumbs} />
      <div className="flex items-center gap-2">
        <button
          onClick={onOpenSearch}
          className="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-500 border border-slate-200 rounded-md hover:bg-slate-50 hover:text-slate-700 transition-colors"
        >
          <Search size={13} />
          Search
          <kbd className="ml-1 px-1.5 py-0.5 text-[10px] font-mono bg-slate-100 border border-slate-200 rounded">⌘K</kbd>
        </button>
        <Badge variant={meta.variant} dot>
          <Radio size={10} />
          {meta.label}
        </Badge>
      </div>
    </header>
  );
}

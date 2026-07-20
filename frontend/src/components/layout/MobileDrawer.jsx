import React, { useEffect, useRef, useState, useCallback } from "react";
import { NavLink, Link, useNavigate, useLocation } from "react-router-dom";
import {
  X, Sparkles, User, LogOut, BrainCircuit, ChevronRight,
  BarChart3, HeartPulse, DollarSign, Mail as MailIcon,
  Users as UsersIcon, ShieldAlert, FileText as FileTextIcon, Activity, GraduationCap,
  Compass,
} from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useUnread } from "../../contexts/UnreadContext";
import { getDashboardMode } from "../../lib/dashboardConfig";
import api from "../../lib/api";
import { NAVY } from "@/lib/tokens";
import {
  getOrderedSections,
  findSectionForPath,
  findSubGroupForPath,
} from "../../config/navigation";

// ─── DrawerNavItem ────────────────────────────────────────────────────────────

function DrawerNavItem({ to, label, icon: Icon, badge, onClick, exact }) {
  return (
    <NavLink
      to={to}
      end={exact}
      onClick={onClick}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-2.5 text-[13px] font-medium transition-colors border-l-2 ${
          isActive
            ? "text-[#0F2847] bg-slate-100 border-[#0F2847]"
            : "text-slate-600 hover:text-slate-900 hover:bg-slate-50 border-transparent"
        }`
      }
    >
      {({ isActive }) => (
        <>
          <Icon size={14} strokeWidth={1.5} className="shrink-0" />
          <span className="flex-1 truncate">{label}</span>
          {badge != null && badge > 0 && (
            <span className="text-[9px] bg-[#0F2847] text-white px-1.5 py-0.5 font-mono min-w-[18px] text-center leading-none">
              {badge > 99 ? "99+" : badge}
            </span>
          )}
          {isActive && <span className="sr-only">(current)</span>}
        </>
      )}
    </NavLink>
  );
}

// ─── DrawerSubItem (third-level) ─────────────────────────────────────────────

function DrawerSubItem({ to, label, icon: Icon, badge, onClick, exact }) {
  return (
    <NavLink
      to={to}
      end={exact}
      onClick={onClick}
      className={({ isActive }) =>
        `flex items-center gap-2.5 pl-6 pr-4 py-2 text-[12px] transition-colors border-l-2 ${
          isActive
            ? "text-[#0F2847] font-semibold bg-slate-50 border-[#0F2847]"
            : "text-slate-500 hover:text-slate-800 hover:bg-slate-50 border-transparent"
        }`
      }
    >
      {({ isActive }) => (
        <>
          <Icon size={12} strokeWidth={1.5} className="shrink-0" />
          <span className="flex-1 truncate">{label}</span>
          {badge != null && badge > 0 && (
            <span className="text-[9px] bg-[#0F2847] text-white px-1.5 py-0.5 font-mono min-w-[16px] text-center leading-none">
              {badge > 99 ? "99+" : badge}
            </span>
          )}
        </>
      )}
    </NavLink>
  );
}

// ─── DrawerSection (accordion section) ───────────────────────────────────────

function DrawerSection({ section, isOpen, onOpen, openSubGroup, onSubGroupToggle, onClose, unreadTotal, pathname }) {
  const SectionIcon = section.icon;
  const isSectionActive = section.routes.some(
    (r) => pathname === r || pathname.startsWith(r + "/")
  );

  return (
    <div>
      {/* Section header */}
      <button
        onClick={onOpen}
        aria-expanded={isOpen}
        className={`
          w-full flex items-center justify-between px-4 py-3 text-left
          transition-colors duration-150 hover:bg-slate-50 group
          ${isSectionActive ? "text-[#0F2847]" : "text-slate-500 hover:text-slate-800"}
        `}
      >
        <div className="flex items-center gap-2.5">
          <SectionIcon size={14} strokeWidth={1.5} className="shrink-0" />
          <span className="text-[11px] font-semibold uppercase tracking-[0.08em]">
            {section.label}
          </span>
        </div>
        <ChevronRight
          size={11}
          strokeWidth={2}
          style={{
            transition: "transform 180ms cubic-bezier(0.16,1,0.3,1)",
            transform: isOpen ? "rotate(90deg)" : "rotate(0deg)",
            flexShrink: 0,
          }}
        />
      </button>

      {/* Section body */}
      <div
        style={{
          display: "grid",
          gridTemplateRows: isOpen ? "1fr" : "0fr",
          transition: "grid-template-rows 180ms cubic-bezier(0.16,1,0.3,1)",
        }}
      >
        <div style={{ overflow: "hidden" }}>
          <div className="pb-1">
            {section.items.filter((item) => !item.sidebarHidden).map((item) =>
              item._type === "subgroup" ? (
                <DrawerSubGroup
                  key={item.id}
                  subGroup={item}
                  isOpen={Boolean(openSubGroup[item.id])}
                  onToggle={() => onSubGroupToggle(item.id)}
                  onClose={onClose}
                  pathname={pathname}
                />
              ) : (
                <DrawerNavItem
                  key={item.to}
                  to={item.to}
                  label={item.label}
                  icon={item.icon}
                  exact={item.exact}
                  badge={item.badge ? unreadTotal : undefined}
                  onClick={onClose}
                />
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── DrawerSubGroup ───────────────────────────────────────────────────────────

function DrawerSubGroup({ subGroup, isOpen, onToggle, onClose, pathname }) {
  const SubIcon = subGroup.icon;
  const isActive = subGroup.items.some(
    (i) => pathname === i.to || pathname.startsWith(i.to + "/")
  );

  return (
    <div>
      <button
        onClick={onToggle}
        aria-expanded={isOpen}
        className={`
          w-full flex items-center justify-between px-4 py-2 text-left
          transition-colors duration-150 hover:bg-slate-50
          ${isActive ? "text-[#0F2847]" : "text-slate-500 hover:text-slate-800"}
        `}
      >
        <div className="flex items-center gap-2.5">
          <SubIcon size={13} strokeWidth={1.5} className="shrink-0" />
          <span className="text-[12px] font-medium">{subGroup.label}</span>
        </div>
        <ChevronRight
          size={10}
          strokeWidth={2}
          style={{
            transition: "transform 160ms cubic-bezier(0.16,1,0.3,1)",
            transform: isOpen ? "rotate(90deg)" : "rotate(0deg)",
            flexShrink: 0,
          }}
        />
      </button>

      <div
        style={{
          display: "grid",
          gridTemplateRows: isOpen ? "1fr" : "0fr",
          transition: "grid-template-rows 160ms cubic-bezier(0.16,1,0.3,1)",
        }}
      >
        <div style={{ overflow: "hidden" }}>
          {subGroup.items.map((item) => (
            <DrawerSubItem
              key={item.to}
              to={item.to}
              label={item.label}
              icon={item.icon}
              exact={item.exact}
              onClick={onClose}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Credits Widget ───────────────────────────────────────────────────────────

function CreditsWidget({ onClose }) {
  const [state, setState] = useState(null);
  useEffect(() => {
    let mounted = true;
    api.get("/credits/balance")
      .then((r) => { if (mounted) setState(r.data); })
      .catch(() => {});
    return () => { mounted = false; };
  }, []);
  if (!state) return null;
  const pct = state.monthly_allowance > 0
    ? Math.min(100, Math.round((state.balance / state.monthly_allowance) * 100))
    : 0;
  return (
    <Link
      to="/settings"
      onClick={onClose}
      className="block mx-4 px-3 py-3 border border-slate-200 hover:border-[#0F2847] transition-colors"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Sparkles size={11} strokeWidth={1.5} className="text-[#0F2847]" />
          <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-400">Credits</span>
        </div>
        <span className="text-xs font-mono text-slate-500 capitalize">{state.plan_code}</span>
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="font-serif text-xl text-slate-900">{state.balance}</span>
        <span className="text-xs text-slate-500">/ {state.monthly_allowance}</span>
      </div>
      <div className="mt-2 h-1 bg-slate-100 relative">
        <div className="absolute inset-y-0 left-0 bg-[#0F2847]" style={{ width: `${pct}%` }} />
      </div>
    </Link>
  );
}

// ─── Main Drawer ──────────────────────────────────────────────────────────────

export default function MobileDrawer({ open, onClose }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { total: msgUnread } = useUnread();
  const panelRef = useRef(null);

  const dashboardMode   = getDashboardMode(user);
  const showInstitution = Boolean(user?.institution_id);
  const showAdmin       = Boolean(user?.is_super_admin);

  const sections = getOrderedSections(dashboardMode, showInstitution);

  // ── Single open section (same accordion behavior as desktop) ─────────────
  const [openSection, setOpenSection] = useState(() => {
    try {
      const saved = localStorage.getItem("sq_nav_v2_section");
      if (saved) return saved;
    } catch {}
    return findSectionForPath(window.location.pathname) || "home";
  });

  const handleSectionOpen = useCallback((id) => {
    setOpenSection((prev) => (prev === id ? null : id));
  }, []);

  // ── Sub-group open state ─────────────────────────────────────────────────
  const [openSubGroup, setOpenSubGroup] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("sq_nav_v2_subgroup") || "{}");
    } catch { return {}; }
  });

  const handleSubGroupToggle = useCallback((id) => {
    setOpenSubGroup((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  // ── Sync open section with current route on open ──────────────────────────
  useEffect(() => {
    if (!open) return;
    const sectionId = findSectionForPath(location.pathname);
    if (sectionId) {
      setOpenSection(sectionId);
      const subGroupId = findSubGroupForPath(sectionId, location.pathname);
      if (subGroupId) setOpenSubGroup((prev) => ({ ...prev, [subGroupId]: true }));
    }
  }, [open, location.pathname]);

  // ── Close on Escape ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // ── Focus trap ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (open) panelRef.current?.focus();
  }, [open]);

  // ── Body scroll lock ─────────────────────────────────────────────────────
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  const handleLogout = async () => {
    onClose();
    await logout();
    navigate("/login");
  };

  return (
    <div
      id="mobile-drawer"
      className={`fixed inset-0 z-50 lg:hidden ${open ? "pointer-events-auto" : "pointer-events-none"}`}
      role="dialog"
      aria-modal="true"
      aria-label="Navigation menu"
    >
      {/* Backdrop */}
      <div
        className={`absolute inset-0 bg-slate-900/60 transition-opacity duration-200 ${open ? "opacity-100" : "opacity-0"}`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-over panel */}
      <div
        ref={panelRef}
        tabIndex={-1}
        className={`absolute top-0 left-0 bottom-0 w-72 bg-white flex flex-col shadow-xl transition-transform duration-200 outline-none ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 h-14 border-b border-slate-200 shrink-0">
          <Link to="/discover" onClick={onClose} className="flex items-center gap-2">
            <div className="w-6 h-6 bg-[#0F2847] rounded-sm flex items-center justify-center">
              <BrainCircuit size={12} strokeWidth={2} className="text-white" />
            </div>
            <span className="text-[13px] font-bold tracking-[0.07em] text-[#0F2847]">SYNAPTIQ</span>
          </Link>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
            aria-label="Close navigation menu"
          >
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>

        {/* Scrollable navigation */}
        <nav className="flex-1 overflow-y-auto overscroll-contain pb-4" aria-label="Main navigation">
          {sections.map((section) => (
            <DrawerSection
              key={section.id}
              section={section}
              isOpen={openSection === section.id}
              onOpen={() => handleSectionOpen(section.id)}
              openSubGroup={openSubGroup}
              onSubGroupToggle={handleSubGroupToggle}
              onClose={onClose}
              unreadTotal={msgUnread}
              pathname={location.pathname}
            />
          ))}

          {/* Admin section (super_admin only — not part of V2 user sections) */}
          {showAdmin && (
            <div>
              <div className="flex items-center gap-2.5 px-4 py-3 text-slate-400">
                <ShieldAlert size={14} strokeWidth={1.5} />
                <span className="text-[11px] font-semibold uppercase tracking-[0.08em]">Admin</span>
              </div>
              <DrawerNavItem to="/admin"                    label="Dashboard"          icon={Compass}           onClick={onClose} exact />
              <DrawerNavItem to="/admin/users"              label="Users"              icon={UsersIcon}         onClick={onClose} />
              <DrawerNavItem to="/admin/security"           label="Security"           icon={ShieldAlert}       onClick={onClose} />
              <DrawerNavItem to="/admin/audit"              label="Audit Log"          icon={FileTextIcon}      onClick={onClose} />
              <DrawerNavItem to="/admin/revenue"            label="Revenue"            icon={DollarSign}        onClick={onClose} />
              <DrawerNavItem to="/admin/analytics"          label="Analytics"          icon={BarChart3}         onClick={onClose} />
              <DrawerNavItem to="/admin/email"              label="Email Center"       icon={MailIcon}          onClick={onClose} />
              <DrawerNavItem to="/admin/reputation"         label="Reputation"         icon={Activity}          onClick={onClose} />
              <DrawerNavItem to="/admin/teaching-analytics" label="Teaching Analytics" icon={GraduationCap}     onClick={onClose} />
              <DrawerNavItem to="/admin/health"             label="Health"             icon={HeartPulse}        onClick={onClose} />
            </div>
          )}
        </nav>

        {/* Bottom strip */}
        <div className="border-t border-slate-200 pt-3 pb-4 shrink-0">
          <CreditsWidget onClose={onClose} />

          <div className="flex items-center gap-3 px-4 py-3">
            <div className="w-8 h-8 bg-slate-200 flex items-center justify-center overflow-hidden shrink-0">
              {user?.avatar_url
                ? <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
                : <User size={14} strokeWidth={1.5} className="text-slate-500" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-slate-900 truncate">{user?.full_name || "Profile"}</div>
              <div className="text-xs text-slate-500 truncate">{user?.institution || ""}</div>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-600 hover:text-[#8A1538] hover:bg-slate-50 transition-colors"
          >
            <LogOut size={14} strokeWidth={1.5} />
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}

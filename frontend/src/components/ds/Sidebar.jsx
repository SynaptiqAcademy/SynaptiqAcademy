import React, {
  useState, useEffect, useRef,
  useCallback, useMemo, memo,
} from "react";
import { NavLink, Link, useNavigate, useLocation } from "react-router-dom";
import {
  BrainCircuit, ChevronRight, ChevronDown, LogOut,
  PanelLeftClose, PanelLeftOpen, Sparkles,
  Search, Star, X, Cpu, ExternalLink, LayoutDashboard,
  Users, ShieldCheck, Lock, Mail,
  BarChart3, Activity, Award,
  GraduationCap, CreditCard, BookOpen, FlaskConical, Database,
  AlertTriangle, Megaphone, Gift,
  TrendingUp, Flag, Clock, Radio, HardDrive, Building2, Shield,
  GitBranch, Headphones, Map,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useUnread } from "@/contexts/UnreadContext";
import { TID } from "@/lib/testIds";
import { getDashboardMode } from "@/lib/dashboardConfig";
import api from "@/lib/api";
import { getOrderedSections, findSectionForPath, findSubGroupForPath } from "@/config/navigation";
import { ADMIN_SECTIONS } from "@/config/adminNavigation";
import { SIDEBAR_W, SIDEBAR_W_COLLAPSED, HEADER_H } from "@/lib/tokens";

/**
 * Sidebar — the one canonical navigation sidebar in the product.
 *
 * variant="app"   (default) — the full research/teaching-OS sidebar: collapse,
 *                  in-sidebar search, accordion sections with sub-groups,
 *                  pinned favorites, Expert Mode, Credits widget.
 * variant="admin" — the simpler Admin OS sidebar: dark theme, every section
 *                  always expanded, no collapse/search/favorites.
 *
 * Both variants are fully self-contained (read auth/nav config internally),
 * matching how the two previous separate components (components/layout/
 * Sidebar.jsx and components/admin/AdminSidebar.jsx) were always invoked
 * with zero props.
 */
export function Sidebar({ variant = "app" }) {
  if (variant === "admin") return <AdminSidebarBody />;
  return <AppSidebarBody />;
}

export default Sidebar;

// ═══════════════════════════════════════════════════════════════════════════
// APP VARIANT — full research/teaching-OS sidebar
// ═══════════════════════════════════════════════════════════════════════════

const LS = {
  COLLAPSED: "sq_sidebar_collapsed",
  SECTION:   "sq_nav_v2_section",
  SUBGROUP:  "sq_nav_v2_subgroup",
  FAVORITES: "sq_nav_favorites",
  EXPERT:    "sq_expert_mode",
};

function getSectionRouteItems(section) {
  const out = [];
  section.items.forEach((item) => {
    if (item._type === "subgroup") {
      item.items.forEach((sub) => out.push(sub));
    } else if (item.to) {
      out.push(item);
    }
  });
  return out;
}

function resolveRouteItems(section, paths) {
  const all = getSectionRouteItems(section);
  return paths.map((p) => all.find((i) => i.to === p)).filter(Boolean);
}

function HighlightText({ text, query }) {
  if (!query) return <>{text}</>;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return <>{text}</>;
  return (
    <>
      {text.slice(0, idx)}
      <span className="text-[#0F2847] font-semibold">
        {text.slice(idx, idx + query.length)}
      </span>
      {text.slice(idx + query.length)}
    </>
  );
}

function useNavMemory() {
  const [favorites, setFavorites] = useState(() => {
    try { return JSON.parse(localStorage.getItem(LS.FAVORITES) || "{}"); }
    catch { return {}; }
  });

  const toggleFavorite = useCallback((sectionId, itemTo) => {
    setFavorites((prev) => {
      const existing = prev[sectionId] || [];
      const isFav    = existing.includes(itemTo);
      const updated  = isFav
        ? existing.filter((r) => r !== itemTo)
        : [itemTo, ...existing].slice(0, 5);
      const next = { ...prev, [sectionId]: updated };
      try { localStorage.setItem(LS.FAVORITES, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  return { favorites, toggleFavorite };
}

function AppSidebarBody() {
  const { user, logout } = useAuth();
  const navigate         = useNavigate();
  const location         = useLocation();
  const { total: unreadTotal } = useUnread();

  const dashboardMode   = getDashboardMode(user);
  const showInstitution = Boolean(user?.institution_id);

  const sections = useMemo(
    () => getOrderedSections(dashboardMode, showInstitution),
    [dashboardMode, showInstitution]
  );

  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(LS.COLLAPSED) === "true"; }
    catch { return false; }
  });

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try { localStorage.setItem(LS.COLLAPSED, String(next)); } catch {}
      window.dispatchEvent(new CustomEvent("sq:sidebar-collapsed-changed", { detail: next }));
      return next;
    });
  }, []);

  useEffect(() => {
    const handler = (e) => setCollapsed(!!e.detail);
    window.addEventListener("sq:sidebar-collapsed-changed", handler);
    return () => window.removeEventListener("sq:sidebar-collapsed-changed", handler);
  }, []);

  const [openSection, setOpenSection] = useState(() => {
    try {
      const saved = localStorage.getItem(LS.SECTION);
      if (saved) return saved;
    } catch {}
    return findSectionForPath(window.location.pathname) || "research";
  });

  const handleSectionToggle = useCallback((id) => {
    setOpenSection((prev) => {
      const next = prev === id ? null : id;
      try { localStorage.setItem(LS.SECTION, next || ""); } catch {}
      return next;
    });
  }, []);

  const [openSubGroup, setOpenSubGroup] = useState(() => {
    try { return JSON.parse(localStorage.getItem(LS.SUBGROUP) || "{}"); }
    catch { return {}; }
  });

  const handleSubGroupToggle = useCallback((id) => {
    setOpenSubGroup((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      try { localStorage.setItem(LS.SUBGROUP, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  const [searchQuery, setSearchQuery] = useState("");
  const searchRef = useRef(null);

  const [expertMode, setExpertMode] = useState(() => {
    try { return localStorage.getItem(LS.EXPERT) === "true"; }
    catch { return false; }
  });

  const toggleExpertMode = useCallback(() => {
    setExpertMode((prev) => {
      const next = !prev;
      try { localStorage.setItem(LS.EXPERT, String(next)); } catch {}
      return next;
    });
  }, []);

  const { favorites, toggleFavorite } = useNavMemory();

  useEffect(() => {
    const sectionId = findSectionForPath(location.pathname);
    if (!sectionId) return;

    setOpenSection((prev) => {
      if (prev === sectionId) return prev;
      try { localStorage.setItem(LS.SECTION, sectionId); } catch {}
      return sectionId;
    });

    const subGroupId = findSubGroupForPath(sectionId, location.pathname);
    if (subGroupId) {
      setOpenSubGroup((prev) => {
        if (prev[subGroupId]) return prev;
        const next = { ...prev, [subGroupId]: true };
        try { localStorage.setItem(LS.SUBGROUP, JSON.stringify(next)); } catch {}
        return next;
      });
    }
  }, [location.pathname]);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === "Escape" && searchQuery) {
        setSearchQuery("");
        e.stopPropagation();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [searchQuery]);

  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return null;
    const out = [];
    sections.forEach((section) => {
      const expertOnlyPaths = expertMode ? new Set() : new Set(
        section.items
          .filter((item) => item._type === "subgroup" && item.expertOnly)
          .flatMap((sg) => sg.items.map((sub) => sub.to))
      );
      const matches = getSectionRouteItems(section).filter(
        (i) => !expertOnlyPaths.has(i.to) && i.label.toLowerCase().includes(q)
      );
      if (matches.length > 0) out.push({ section, items: matches });
    });
    return out;
  }, [searchQuery, sections, expertMode]);

  const handleExpandAndOpen = useCallback((sectionId) => {
    if (collapsed) {
      setCollapsed(false);
      try { localStorage.setItem(LS.COLLAPSED, "false"); } catch {}
    }
    setOpenSection(sectionId);
    try { localStorage.setItem(LS.SECTION, sectionId); } catch {}
  }, [collapsed]);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const initials = (user?.full_name || "U")
    .split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

  const subtitle =
    dashboardMode === "hybrid"   ? "Research & Education OS" :
    dashboardMode === "teaching" ? "Education OS" :
    "Research OS";

  return (
    <aside
      data-testid={TID.sidebar}
      aria-label="Main navigation"
      style={{
        width: collapsed ? SIDEBAR_W_COLLAPSED : SIDEBAR_W,
        transition: "width 220ms cubic-bezier(0.16,1,0.3,1)",
        willChange: "width",
      }}
      className="hidden lg:flex flex-col border-r border-[rgba(15,23,42,0.07)] bg-white h-screen sticky top-0 overflow-hidden shrink-0"
    >
      {/* ── Wordmark ─────────────────────────────────────────────────────── */}
      <div
        className="flex items-center border-b border-[rgba(15,23,42,0.06)] shrink-0"
        style={{
          height: HEADER_H,
          padding: collapsed ? "0" : "0 16px",
          justifyContent: collapsed ? "center" : "flex-start",
        }}
      >
        <NavLink
          to="/discover"
          className="flex items-center gap-2.5 min-w-0"
          title={collapsed ? "SYNAPTIQ" : undefined}
        >
          <div className="w-6 h-6 bg-[#0F2847] rounded-sm flex items-center justify-center shrink-0">
            <BrainCircuit size={12} strokeWidth={2} className="text-white" />
          </div>
          <div
            style={{
              overflow: "hidden",
              maxWidth: collapsed ? 0 : 200,
              opacity: collapsed ? 0 : 1,
              transition: "max-width 200ms ease, opacity 150ms ease",
            }}
          >
            <div className="text-[12px] font-bold tracking-[0.07em] text-[#0F2847] whitespace-nowrap">
              SYNAPTIQ
            </div>
            <div className="text-[9px] font-medium tracking-[0.08em] uppercase text-slate-400 whitespace-nowrap">
              {subtitle}
            </div>
          </div>
        </NavLink>
      </div>

      {/* ── Navigation search (expanded only) ────────────────────────────── */}
      {!collapsed && (
        <div className="px-3 py-2 border-b border-[rgba(15,23,42,0.05)] shrink-0">
          <label className="flex items-center gap-2 px-2.5 py-[5px] bg-slate-50 border border-slate-200 rounded-md focus-within:border-[#0F2847]/30 focus-within:bg-white transition-colors cursor-text">
            <Search size={11} strokeWidth={1.5} className="text-slate-400 shrink-0" />
            <input
              ref={searchRef}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && searchResults?.length > 0) {
                  const first = searchResults[0].items[0];
                  setSearchQuery("");
                  navigate(first.to);
                }
              }}
              placeholder="Filter navigation…"
              aria-label="Filter sidebar navigation"
              className="flex-1 text-[12px] bg-transparent text-slate-700 placeholder:text-slate-400 outline-none min-w-0"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="text-slate-400 hover:text-slate-600 transition-colors"
                aria-label="Clear search"
                tabIndex={-1}
              >
                <X size={10} strokeWidth={1.5} />
              </button>
            )}
          </label>
        </div>
      )}

      {/* ── Navigation ───────────────────────────────────────────────────── */}
      <nav
        className="flex-1 overflow-y-auto overflow-x-hidden py-1"
        role="navigation"
        aria-label="Application sections"
      >
        {searchResults !== null ? (
          searchResults.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <p className="text-[12px] text-slate-400">
                No results for "{searchQuery}"
              </p>
            </div>
          ) : (
            searchResults.map(({ section, items }) => (
              <SearchResultGroup
                key={section.id}
                section={section}
                items={items}
                query={searchQuery.trim()}
                onNavigate={() => setSearchQuery("")}
              />
            ))
          )
        ) : (
          sections.map((section) => (
            <SidebarSection
              key={section.id}
              section={section}
              collapsed={collapsed}
              isOpen={openSection === section.id}
              onToggle={() => handleSectionToggle(section.id)}
              onExpand={() => handleExpandAndOpen(section.id)}
              openSubGroup={openSubGroup}
              onSubGroupToggle={handleSubGroupToggle}
              unreadTotal={unreadTotal}
              pathname={location.pathname}
              sectionFavorites={favorites[section.id] || []}
              onToggleFavorite={(itemTo) => toggleFavorite(section.id, itemTo)}
              expertMode={expertMode}
            />
          ))
        )}
        <div style={{ height: 8 }} />
      </nav>

      {/* ── Bottom strip ─────────────────────────────────────────────────── */}
      <div className="border-t border-[rgba(15,23,42,0.06)] py-1.5 shrink-0">
        <CreditsWidget collapsed={collapsed} />

        <div
          data-testid={TID.navProfile}
          title={collapsed ? (user?.full_name || "Profile") : undefined}
          className="flex items-center gap-2.5"
          style={{
            padding: collapsed ? "7px 0" : "7px 14px",
            justifyContent: collapsed ? "center" : "flex-start",
          }}
        >
          <div
            className="bg-[#0F2847]/[0.08] flex items-center justify-center overflow-hidden shrink-0 text-[#0F2847]"
            style={{ width: 26, height: 26, borderRadius: "50%" }}
          >
            {user?.avatar_url
              ? <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
              : <span className="text-[10px] font-semibold leading-none">{initials}</span>}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <div className="truncate text-[12px] font-medium text-slate-800">
                {user?.full_name || "Profile"}
              </div>
              <div className="truncate text-[10px] text-slate-400">{user?.institution || ""}</div>
            </div>
          )}
        </div>

        <button
          onClick={toggleExpertMode}
          title={expertMode ? "Expert Mode: ON — click to show essential navigation only" : "Expert Mode: OFF — click to show advanced tools"}
          aria-pressed={expertMode}
          className={`w-full flex items-center gap-2.5 text-[12px] transition-colors duration-100 ${
            expertMode
              ? "text-[#0F2847] hover:bg-slate-50"
              : "text-slate-400 hover:text-slate-700 hover:bg-slate-50"
          }`}
          style={{
            padding: collapsed ? "5px 0" : "5px 14px",
            justifyContent: collapsed ? "center" : "flex-start",
          }}
        >
          <Cpu size={13} strokeWidth={1.5} />
          {!collapsed && (
            <span className="flex-1 text-left">Expert Mode</span>
          )}
          {!collapsed && (
            <span className={`text-[10px] font-mono px-1 rounded ${
              expertMode ? "bg-[#0F2847] text-white" : "bg-slate-100 text-slate-400"
            }`}>
              {expertMode ? "ON" : "OFF"}
            </span>
          )}
        </button>

        <button
          onClick={handleLogout}
          data-testid={TID.logoutBtn}
          title={collapsed ? "Sign out" : undefined}
          className="w-full flex items-center gap-2.5 text-[12px] text-slate-500 hover:text-[#8A1538] hover:bg-slate-50 transition-colors duration-100 text-left"
          style={{
            padding: collapsed ? "5px 0" : "5px 14px",
            justifyContent: collapsed ? "center" : "flex-start",
          }}
        >
          <LogOut size={13} strokeWidth={1.5} />
          {!collapsed && <span>Sign out</span>}
        </button>

        <div className="pt-1 mt-1 border-t border-slate-100">
          <button
            onClick={toggleCollapsed}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="w-full flex items-center gap-2 text-[11px] text-slate-400 hover:text-slate-700 hover:bg-slate-50 transition-colors duration-100"
            style={{
              padding: collapsed ? "5px 0" : "5px 14px",
              justifyContent: collapsed ? "center" : "flex-start",
            }}
          >
            {collapsed
              ? <PanelLeftOpen  size={13} strokeWidth={1.5} />
              : <PanelLeftClose size={13} strokeWidth={1.5} />}
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </div>
    </aside>
  );
}

const SearchResultGroup = memo(function SearchResultGroup({ section, items, query, onNavigate }) {
  const SectionIcon = section.icon;
  return (
    <div>
      <div className="flex items-center gap-1.5 px-3.5 pt-3 pb-1">
        <SectionIcon size={9} strokeWidth={1.5} className="text-slate-300" />
        <span className="text-[9px] font-semibold uppercase tracking-[0.1em] text-slate-300">
          {section.label}
        </span>
      </div>
      {items.map((item) => (
        <SearchResultItem key={item.to} item={item} query={query} onNavigate={onNavigate} />
      ))}
    </div>
  );
});

const SearchResultItem = memo(function SearchResultItem({ item, query, onNavigate }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.exact ?? false}
      onClick={onNavigate}
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-3.5 py-[5px] text-[12px] transition-colors border-l-2 ${
          isActive
            ? "text-[#0F2847] border-[#0F2847] bg-[#0F2847]/[0.06]"
            : "text-slate-600 border-transparent hover:text-slate-900 hover:bg-slate-50"
        }`
      }
    >
      <Icon size={12} strokeWidth={1.5} className="shrink-0 text-slate-400" />
      <span className="flex-1 truncate">
        <HighlightText text={item.label} query={query} />
      </span>
    </NavLink>
  );
});

const SidebarSection = memo(function SidebarSection({
  section, collapsed, isOpen, onToggle, onExpand,
  openSubGroup, onSubGroupToggle,
  unreadTotal, pathname,
  sectionFavorites,
  onToggleFavorite,
  expertMode,
}) {
  const SectionIcon     = section.icon;
  const sectionBodyRef  = useRef(null);
  const isSectionActive = section.routes.some(
    (r) => pathname === r || pathname.startsWith(r + "/")
  );

  const firstRouteItem = useMemo(
    () => section.items.find((i) => !i._type && i.to),
    [section.items]
  );

  const favoriteItems = useMemo(
    () => resolveRouteItems(section, sectionFavorites),
    [section, sectionFavorites]
  );

  useEffect(() => {
    if (isOpen && !collapsed && sectionBodyRef.current) {
      const t = setTimeout(() => {
        sectionBodyRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }, 80);
      return () => clearTimeout(t);
    }
  }, [isOpen, collapsed]);

  const colorClass = isSectionActive
    ? "text-[#0F2847]"
    : "text-slate-400 hover:text-slate-700";

  return (
    <div>
      {collapsed ? (
        <button
          onClick={onExpand}
          title={section.label}
          aria-label={`Open ${section.label}`}
          className={`w-full flex items-center justify-center py-2.5 transition-colors duration-150 hover:bg-slate-50 ${colorClass}`}
        >
          <SectionIcon size={15} strokeWidth={1.5} />
        </button>
      ) : (
        <div className="flex items-center">
          {firstRouteItem ? (
            <NavLink
              to={firstRouteItem.to}
              end={firstRouteItem.exact ?? false}
              onClick={() => { if (!isOpen) onToggle(); }}
              className={`flex-1 flex items-center gap-2 px-3.5 py-2.5 hover:bg-slate-50 transition-colors ${colorClass}`}
              title={`Open ${section.label}`}
            >
              <SectionIcon size={12} strokeWidth={1.5} className="shrink-0" />
              <span className="text-[10px] font-semibold uppercase tracking-[0.08em]">
                {section.label}
              </span>
            </NavLink>
          ) : (
            <button
              onClick={onToggle}
              className={`flex-1 flex items-center gap-2 px-3.5 py-2.5 hover:bg-slate-50 transition-colors ${colorClass}`}
            >
              <SectionIcon size={12} strokeWidth={1.5} className="shrink-0" />
              <span className="text-[10px] font-semibold uppercase tracking-[0.08em]">
                {section.label}
              </span>
            </button>
          )}
          <button
            onClick={onToggle}
            aria-expanded={isOpen}
            aria-label={`${isOpen ? "Collapse" : "Expand"} ${section.label}`}
            className="px-2 py-2.5 hover:bg-slate-50 transition-colors text-slate-300 hover:text-slate-500"
          >
            <ChevronRight
              size={10}
              strokeWidth={2}
              style={{
                transition: "transform 180ms cubic-bezier(0.16,1,0.3,1)",
                transform: isOpen ? "rotate(90deg)" : "rotate(0deg)",
                flexShrink: 0,
              }}
            />
          </button>
        </div>
      )}

      {!collapsed && (
        <div
          ref={sectionBodyRef}
          role="region"
          aria-label={`${section.label} navigation`}
          style={{
            display: "grid",
            gridTemplateRows: isOpen ? "1fr" : "0fr",
            transition: "grid-template-rows 180ms cubic-bezier(0.16,1,0.3,1)",
          }}
        >
          <div style={{ overflow: "hidden" }}>
            <div className="pb-1">
              {favoriteItems.length > 0 && (
                <>
                  <MiniLabel icon={<Star size={8} strokeWidth={2} />} text="Pinned" />
                  {favoriteItems.map((item) => (
                    <SidebarNavItem
                      key={`pin-${item.to}`}
                      item={item}
                      badge={item.badge ? unreadTotal : undefined}
                      isFavorited
                      onToggleFavorite={() => onToggleFavorite(item.to)}
                    />
                  ))}
                  <MiniDivider />
                </>
              )}

              {section.items
                .filter((item) => (!item.expertOnly || expertMode) && !item.sidebarHidden)
                .map((item) =>
                  item._type === "subgroup" ? (
                    <SubGroup
                      key={item.id}
                      subGroup={item}
                      isOpen={Boolean(openSubGroup[item.id])}
                      onToggle={() => onSubGroupToggle(item.id)}
                      pathname={pathname}
                    />
                  ) : (
                    <SidebarNavItem
                      key={item.to}
                      item={item}
                      badge={item.badge ? unreadTotal : undefined}
                      isFavorited={sectionFavorites.includes(item.to)}
                      onToggleFavorite={() => onToggleFavorite(item.to)}
                    />
                  )
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

function MiniLabel({ icon, text }) {
  return (
    <div className="flex items-center gap-1.5 px-3.5 pt-2 pb-0.5 text-slate-300">
      {icon}
      <span className="text-[9px] font-semibold uppercase tracking-[0.1em]">{text}</span>
    </div>
  );
}

function MiniDivider() {
  return <div className="mx-3.5 my-1.5 border-t border-slate-100" />;
}

const SubGroup = memo(function SubGroup({ subGroup, isOpen, onToggle, pathname }) {
  const SubIcon          = subGroup.icon;
  const isSubGroupActive = subGroup.items.some(
    (i) => pathname === i.to || pathname.startsWith(i.to + "/")
  );

  return (
    <div>
      <button
        onClick={onToggle}
        data-testid={subGroup.testid}
        aria-expanded={isOpen}
        aria-label={`${isOpen ? "Collapse" : "Expand"} ${subGroup.label}`}
        className={`
          w-full flex items-center justify-between px-3.5 py-[5px]
          text-[12px] font-medium transition-colors duration-150 hover:bg-slate-50
          ${isSubGroupActive ? "text-[#0F2847]" : "text-slate-500 hover:text-slate-800"}
        `}
      >
        <div className="flex items-center gap-2">
          <SubIcon size={13} strokeWidth={1.5} className="shrink-0" />
          <span>{subGroup.label}</span>
        </div>
        <ChevronRight
          size={9}
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
          <div className="ml-3.5 pl-3 border-l border-slate-100 mb-0.5 mt-0.5">
            {subGroup.items.map((item) => (
              <SubGroupItem key={item.to} item={item} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
});

const SidebarNavItem = memo(function SidebarNavItem({
  item, badge, isFavorited, onToggleFavorite,
}) {
  const Icon = item.icon;
  return (
    <div className="group relative">
      <NavLink
        to={item.to}
        end={item.exact ?? false}
        data-testid={item.testid}
        className={({ isActive }) =>
          `flex items-center gap-2.5 border-l-2 text-[12.5px] font-medium transition-colors duration-100 ${
            isActive
              ? "bg-[#0F2847]/[0.08] text-[#0F2847] border-[#0F2847]"
              : `${item.accent ? "text-[#0F2847]" : "text-slate-600"} hover:text-slate-900 hover:bg-slate-50 border-transparent`
          }`
        }
        style={{ padding: "6px 28px 6px 12px" }}
      >
        <Icon size={14} strokeWidth={1.5} className="shrink-0" />
        <span className="flex-1 truncate">{item.label}</span>
        {badge > 0 && (
          <span
            data-testid="nav-unread-badge"
            className="text-[10px] bg-[#0F2847] text-white px-1.5 font-mono min-w-[18px] text-center leading-tight"
            style={{ borderRadius: 3 }}
          >
            {badge > 99 ? "99+" : badge}
          </span>
        )}
      </NavLink>

      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggleFavorite(); }}
        title={isFavorited ? "Unpin" : "Pin to top"}
        aria-label={isFavorited ? `Unpin ${item.label}` : `Pin ${item.label} to top`}
        className={`
          absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded
          transition-all duration-100
          ${isFavorited
            ? "opacity-100 text-[#0F2847]"
            : "opacity-0 group-hover:opacity-100 text-slate-300 hover:text-[#0F2847]"
          }
        `}
      >
        <Star size={10} strokeWidth={1.5} fill={isFavorited ? "currentColor" : "none"} />
      </button>
    </div>
  );
});

const SubGroupItem = memo(function SubGroupItem({ item }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.exact ?? false}
      data-testid={item.testid}
      className={({ isActive }) =>
        `flex items-center gap-2 px-2 py-[5px] rounded-sm text-[12px] transition-colors duration-100 ${
          isActive
            ? "text-[#0F2847] font-semibold bg-[#0F2847]/[0.05]"
            : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
        }`
      }
    >
      <Icon size={11} strokeWidth={1.5} className="shrink-0" />
      <span className="truncate">{item.label}</span>
    </NavLink>
  );
});

function CreditsWidget({ collapsed }) {
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

  if (collapsed) {
    return (
      <Link
        to="/settings"
        data-testid={TID.creditsWidget}
        title={`${state.balance.toLocaleString()} credits`}
        className="flex items-center justify-center py-2 hover:bg-slate-50 transition-colors duration-100"
      >
        <Sparkles size={13} strokeWidth={1.5} className="text-[#0F2847]" />
      </Link>
    );
  }

  return (
    <Link
      to="/settings"
      data-testid={TID.creditsWidget}
      className="block px-3 py-2 mx-2.5 mb-1 border border-[rgba(15,23,42,0.07)] rounded-md hover:border-[#0F2847]/30 transition-colors duration-150"
    >
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <Sparkles size={10} strokeWidth={1.5} className="text-[#0F2847]" />
          <span className="text-[10px] font-semibold uppercase tracking-[0.06em] text-slate-400">
            Credits
          </span>
        </div>
        <span className="text-[9px] font-mono text-slate-400 capitalize">{state.plan_code}</span>
      </div>
      <div className="flex items-baseline gap-1 mb-1.5">
        <span className="text-base font-bold text-slate-900 tracking-tight">
          {state.balance.toLocaleString()}
        </span>
        <span className="text-[10px] text-slate-400">
          / {state.monthly_allowance.toLocaleString()}
        </span>
      </div>
      <div className="h-px bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-[#0F2847] rounded-full transition-[width] duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </Link>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ADMIN VARIANT — simpler Admin OS sidebar (dark theme, always-open sections)
// ═══════════════════════════════════════════════════════════════════════════

// Icons are kept here (not in the shared config) so config/adminNavigation.js
// stays framework/icon-agnostic and reusable by the command palette/breadcrumbs.
const ADMIN_ICON_BY_PATH = {
  "/admin": LayoutDashboard,
  "/admin/analytics": BarChart3,
  "/admin/revenue": TrendingUp,
  "/admin/copilot": Cpu,
  "/admin/users": Users,
  "/admin/subscriptions": CreditCard,
  "/admin/promotions": Gift,
  "/admin/institution-center": Building2,
  "/admin/teaching-analytics": GraduationCap,
  "/admin/research": FlaskConical,
  "/admin/research-integrity": Shield,
  "/admin/content": BookOpen,
  "/admin/reputation": Award,
  "/admin/grant-hub": GitBranch,
  "/admin/reviewer-hub": Star,
  "/admin/health": Activity,
  "/admin/command-map": Map,
  "/admin/errors": AlertTriangle,
  "/admin/platform-auditor": Star,
  "/admin/database": Database,
  "/admin/storage": HardDrive,
  "/admin/jobs": Clock,
  "/admin/api-monitor": Radio,
  "/admin/feature-flags-center": Flag,
  "/admin/releases": GitBranch,
  "/admin/data-quality": Shield,
  "/admin/search": Search,
  "/admin/reputation-center": Award,
  "/admin/recommendation-center": Star,
  "/admin/impact-center": TrendingUp,
  "/admin/ai-center": BrainCircuit,
  "/admin/profiles": Users,
  "/admin/verification": ShieldCheck,
  "/admin/integrity-center": Shield,
  "/admin/account-security": ShieldCheck,
  "/admin/mfa": Shield,
  "/admin/security-hardening": ShieldCheck,
  "/admin/security": Lock,
  "/admin/trust-center": ShieldCheck,
  "/admin/audit": ShieldCheck,
  "/admin/email": Mail,
  "/admin/communications": Megaphone,
  "/admin/support": Headphones,
};

const ADMIN_UI_SECTIONS = ADMIN_SECTIONS.map((section) => ({
  ...section,
  items: section.items.map((item) => ({ ...item, icon: ADMIN_ICON_BY_PATH[item.path] || LayoutDashboard })),
}));

function AdminSection({ section }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="mb-1">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500 hover:text-slate-300 transition-colors"
      >
        {section.label}
        {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
      </button>
      {open && (
        <div className="space-y-0.5">
          {section.items.map(({ label, icon: Icon, path, end }) => (
            <NavLink
              key={path}
              to={path}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-[#0F2847] text-white border-l-2 border-blue-400"
                    : "text-slate-400 hover:text-white hover:bg-[#0F2847]/60 border-l-2 border-transparent"
                }`
              }
            >
              <Icon size={14} className="flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

function AdminSidebarBody() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const initials = (user?.full_name || user?.email || "A")
    .split(" ").slice(0, 2).map((w) => w[0]?.toUpperCase() || "").join("");

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <aside
      style={{ width: SIDEBAR_W }}
      className="min-h-screen bg-[#0B1C35] flex flex-col flex-shrink-0 border-r border-[#1a3050]"
    >
      <div className="px-5 py-5 border-b border-[#1a3050]">
        <div className="font-serif text-white text-lg tracking-wide">SYNAPTIQ</div>
        <div className="text-xs text-slate-400 mt-0.5 tracking-widest uppercase">Admin OS</div>
      </div>

      <nav className="flex-1 py-3 px-1 overflow-y-auto space-y-1">
        {ADMIN_UI_SECTIONS.map((section) => (
          <AdminSection key={section.label} section={section} />
        ))}

        <div className="border-t border-[#1a3050] mx-2 my-2" />

        <a
          href="/discover"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-3 px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-[#0F2847]/60 border-l-2 border-transparent transition-colors"
        >
          <ExternalLink size={14} className="flex-shrink-0" />
          View Platform
        </a>
      </nav>

      <div className="border-t border-[#1a3050] p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 bg-[#0F2847] border border-slate-600 flex items-center justify-center text-xs text-white font-medium flex-shrink-0">
            {initials}
          </div>
          <div className="min-w-0">
            <div className="text-xs text-white truncate">{user?.full_name || "Admin"}</div>
            <div className="text-xs text-slate-400 truncate">{user?.email}</div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <LogOut size={13} />
          Sign out
        </button>
      </div>
    </aside>
  );
}

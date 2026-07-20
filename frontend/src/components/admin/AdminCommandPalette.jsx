import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search, X, ChevronRight, Clock, Zap, LayoutGrid,
} from "lucide-react";
import api from "@/lib/api";
import { getAllAdminPages, ADMIN_QUICK_ACTIONS } from "@/config/adminNavigation";
import { getRecentAdminPages } from "@/hooks/useAdminRecentPages";
import { rankActions } from "@/hooks/useUserMemory";

const ALL_ADMIN_PAGES = getAllAdminPages();

/** Turn a live /api/admin/search result set into command-palette sections. */
function buildLiveSearchSections(liveResults) {
  if (!liveResults) return [];
  const LABELS = {
    users: "Users", projects: "Projects", workspaces: "Workspaces",
    institutions: "Institutions", publications: "Publications", support_tickets: "Support Tickets",
  };
  const NAV_BY_COLLECTION = {
    users: "/admin/users", projects: "/admin/content", workspaces: "/admin/content",
    institutions: "/admin/institution-center", publications: "/admin/content", support_tickets: "/admin/support",
  };
  const sections = [];
  for (const [coll, docs] of Object.entries(liveResults)) {
    if (!docs || docs.length === 0) continue;
    sections.push({
      id: `live-${coll}`,
      label: LABELS[coll] || coll,
      icon: Search,
      items: docs.map((d) => ({
        label: d.full_name || d.title || d.name || d.subject || d.email || d.id,
        description: d.email || d.status || d.country || d.year ? String(d.email || d.status || d.country || d.year) : undefined,
        to: NAV_BY_COLLECTION[coll] || "/admin",
      })),
    });
  }
  return sections;
}

export default function AdminCommandPalette({ open, onClose }) {
  const [query, setQuery] = useState("");
  const [recent, setRecent] = useState([]);
  const [liveResults, setLiveResults] = useState(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const debounceRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (open) {
      setQuery("");
      setLiveResults(null);
      setActiveIndex(0);
      setRecent(getRecentAdminPages().slice(0, 5));
      const t = setTimeout(() => inputRef.current?.focus(), 40);
      return () => clearTimeout(t);
    }
  }, [open]);

  const RANKED_ACTIONS = rankActions(ADMIN_QUICK_ACTIONS);

  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const trimmed = query.trim().toLowerCase();

  // Debounced live search against the backend for 2+ character queries.
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (trimmed.length < 2) { setLiveResults(null); return; }
    debounceRef.current = setTimeout(() => {
      api.get("/admin/search", { params: { q: trimmed, limit_per_collection: 4 } })
        .then((r) => setLiveResults(r.data.results))
        .catch(() => setLiveResults(null));
    }, 250);
    return () => clearTimeout(debounceRef.current);
  }, [trimmed]);

  const sections = buildSections(trimmed, recent, RANKED_ACTIONS, liveResults);
  const flatItems = sections.flatMap((s) => s.items);

  useEffect(() => {
    if (!listRef.current) return;
    const active = listRef.current.querySelector("[data-active='true']");
    active?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  const handleSelect = useCallback((item) => {
    onClose();
    navigate(item.to);
  }, [onClose, navigate]);

  const handleKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, flatItems.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = flatItems[activeIndex];
      if (item) handleSelect(item);
    }
  };

  if (!open) return null;

  let flatIdx = 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center"
      style={{ paddingTop: "12vh" }}
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-slate-900/25 backdrop-blur-[1px]" />

      <div
        className="relative w-full max-w-xl bg-white border border-slate-200 shadow-2xl mx-4 flex flex-col"
        style={{ maxHeight: "72vh" }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Admin command palette"
      >
        <div className="flex items-center gap-3 px-4 border-b border-slate-100 shrink-0" style={{ height: 52 }}>
          <Search size={15} strokeWidth={1.5} className="text-slate-400 shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActiveIndex(0); }}
            onKeyDown={handleKeyDown}
            placeholder="Search admin pages, users, projects…"
            className="flex-1 text-[14px] text-slate-900 placeholder:text-slate-400 bg-transparent outline-none"
            aria-label="Admin command search"
            autoComplete="off"
            spellCheck={false}
          />
          {query ? (
            <button
              onClick={() => { setQuery(""); setActiveIndex(0); inputRef.current?.focus(); }}
              className="text-slate-400 hover:text-slate-700 transition-colors p-0.5 shrink-0"
              aria-label="Clear search"
            >
              <X size={13} strokeWidth={1.5} />
            </button>
          ) : (
            <kbd className="text-[10px] font-mono border border-slate-200 text-slate-300 px-1.5 py-0.5 rounded leading-none bg-white shrink-0">
              ⌘K
            </kbd>
          )}
        </div>

        <div ref={listRef} className="overflow-y-auto flex-1">
          {flatItems.length === 0 && trimmed && (
            <div className="px-5 py-12 text-center">
              <Search size={28} strokeWidth={1} className="text-slate-200 mx-auto mb-3" />
              <p className="text-[13px] text-slate-500">
                No results for <span className="font-medium text-slate-700">"{query}"</span>
              </p>
            </div>
          )}

          {sections.map((section) => {
            const SectionIcon = section.icon;
            return (
              <div key={section.id} className="border-b border-slate-50 last:border-0 py-1.5">
                <div className="flex items-center gap-1.5 px-4 pt-1.5 pb-1">
                  {SectionIcon && (
                    <SectionIcon size={9} strokeWidth={1.5} className="text-slate-300 shrink-0" />
                  )}
                  <span className="text-[9px] font-semibold uppercase tracking-[0.12em] text-slate-300">
                    {section.label}
                  </span>
                </div>

                {section.items.map((item, i) => {
                  const isActive = flatIdx === activeIndex;
                  const thisIdx = flatIdx++;
                  const Icon = item.icon;
                  return (
                    <button
                      key={`${section.id}-${item.to}-${i}`}
                      data-active={isActive}
                      onClick={() => handleSelect(item)}
                      onMouseEnter={() => setActiveIndex(thisIdx)}
                      className={`
                        w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors duration-75
                        ${isActive ? "bg-[#0F2847]/[0.07]" : "hover:bg-slate-50"}
                      `}
                    >
                      <div
                        className={`w-7 h-7 flex items-center justify-center shrink-0 ${
                          isActive ? "bg-[#0F2847]/[0.08]" : "bg-slate-100"
                        }`}
                      >
                        {Icon
                          ? <Icon size={13} strokeWidth={1.5} className={isActive ? "text-[#0F2847]" : "text-slate-400"} />
                          : <LayoutGrid size={13} strokeWidth={1.5} className="text-slate-300" />
                        }
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className={`text-[13px] font-medium truncate ${isActive ? "text-[#0F2847]" : "text-slate-700"}`}>
                          {item.label}
                        </div>
                        {item.description && (
                          <div className="text-[11px] text-slate-400 truncate mt-0.5 leading-snug">
                            {item.description}
                          </div>
                        )}
                        {!item.description && item.group && !trimmed && (
                          <div className="text-[11px] text-slate-300 mt-0.5">{item.group}</div>
                        )}
                      </div>

                      <ChevronRight
                        size={11}
                        strokeWidth={2}
                        className={`shrink-0 transition-colors ${isActive ? "text-[#0F2847]" : "text-slate-200"}`}
                      />
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>

        <div className="px-4 py-2.5 border-t border-slate-100 flex items-center gap-4 text-[10px] font-mono text-slate-400 shrink-0">
          <span><kbd className="border border-slate-200 px-1 py-px bg-slate-50">↑↓</kbd> navigate</span>
          <span><kbd className="border border-slate-200 px-1 py-px bg-slate-50">↵</kbd> open</span>
          <span><kbd className="border border-slate-200 px-1 py-px bg-slate-50">Esc</kbd> close</span>
          <span className="ml-auto text-slate-300">⌘K</span>
        </div>
      </div>
    </div>
  );
}

function buildSections(trimmed, recent, rankedActions, liveResults) {
  if (!trimmed) return buildDefaultSections(recent, rankedActions);
  return buildSearchSections(trimmed, rankedActions, liveResults);
}

function buildDefaultSections(recent, rankedActions) {
  const sections = [];
  sections.push({ id: "actions", label: "Quick Actions", icon: Zap, items: rankedActions.slice(0, 6) });
  if (recent.length > 0) {
    sections.push({ id: "recent", label: "Recent", icon: Clock, items: recent });
  }
  sections.push({ id: "pages", label: "Admin Pages", icon: LayoutGrid, items: ALL_ADMIN_PAGES.slice(0, 8) });
  return sections;
}

function buildSearchSections(trimmed, rankedActions, liveResults) {
  const sections = [];

  const matchActions = rankedActions.filter(
    (a) => a.label.toLowerCase().includes(trimmed) || a.description?.toLowerCase().includes(trimmed)
  );
  if (matchActions.length > 0) {
    sections.push({ id: "actions", label: "Actions", icon: Zap, items: matchActions });
  }

  const matchPages = ALL_ADMIN_PAGES.filter((p) => p.label.toLowerCase().includes(trimmed));
  if (matchPages.length > 0) {
    sections.push({ id: "pages", label: "Admin Pages", icon: LayoutGrid, items: matchPages });
  }

  sections.push(...buildLiveSearchSections(liveResults));

  return sections;
}

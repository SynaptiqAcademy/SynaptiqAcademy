import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search, X, ChevronRight, Clock, Zap, LayoutGrid, Compass,
} from "lucide-react";
import { getAllPages, QUICK_ACTIONS } from "../../config/navigation";
import { getRecentPages } from "../../hooks/useRecentPages";
import { rankActions } from "../../hooks/useUserMemory";
import { intentSearch } from "../../config/intentSearch";

const ALL_PAGES = getAllPages();

// Groups shown in the "no query" default state
const DEFAULT_GROUPS = new Set(["Platform", "Research", "AI Workspace"]);

export default function CommandPalette({ open, onClose }) {
  const [query, setQuery]           = useState("");
  const [recent, setRecent]         = useState([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef(null);
  const listRef  = useRef(null);
  const navigate = useNavigate();

  // Reset + load recents each time palette opens; rank actions by behavior
  useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIndex(0);
      setRecent(getRecentPages().slice(0, 5));
      const t = setTimeout(() => inputRef.current?.focus(), 40);
      return () => clearTimeout(t);
    }
  }, [open]);

  // Personalized quick actions (ranked by usage)
  const RANKED_ACTIONS = rankActions(QUICK_ACTIONS);

  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const trimmed = query.trim().toLowerCase();

  // ── Build result sections ────────────────────────────────────────────────
  const sections = buildSections(trimmed, recent, RANKED_ACTIONS);
  const flatItems = sections.flatMap((s) => s.items);

  // Scroll active item into view
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
        aria-label="Command palette"
      >
        {/* ── Search input ─────────────────────────────────────────────────── */}
        <div
          className="flex items-center gap-3 px-4 border-b border-slate-100 shrink-0"
          style={{ height: 52 }}
        >
          <Search size={15} strokeWidth={1.5} className="text-slate-400 shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActiveIndex(0); }}
            onKeyDown={handleKeyDown}
            placeholder="Search pages, start a workflow, or ask AI…"
            className="flex-1 text-[14px] text-slate-900 placeholder:text-slate-400 bg-transparent outline-none"
            aria-label="Command search"
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

        {/* ── Results ──────────────────────────────────────────────────────── */}
        <div ref={listRef} className="overflow-y-auto flex-1">
          {flatItems.length === 0 && trimmed && (
            <div className="px-5 py-12 text-center">
              <Search size={28} strokeWidth={1} className="text-slate-200 mx-auto mb-3" />
              <p className="text-[13px] text-slate-500">
                No results for <span className="font-medium text-slate-700">"{query}"</span>
              </p>
              <p className="text-[12px] text-slate-400 mt-1">
                Try searching for a feature name, workflow, or page title
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

                {section.items.map((item) => {
                  const isActive = flatIdx === activeIndex;
                  const thisIdx  = flatIdx++;
                  const Icon = item.icon;
                  return (
                    <button
                      key={`${section.id}-${item.to}`}
                      data-active={isActive}
                      onClick={() => handleSelect(item)}
                      onMouseEnter={() => setActiveIndex(thisIdx)}
                      className={`
                        w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors duration-75
                        ${isActive ? "bg-[#0F2847]/[0.07]" : "hover:bg-slate-50"}
                      `}
                    >
                      {/* Icon */}
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

                      {/* Label + description */}
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

        {/* ── Footer ───────────────────────────────────────────────────────── */}
        <div className="px-4 py-2.5 border-t border-slate-100 flex items-center gap-4 text-[10px] font-mono text-slate-400 shrink-0">
          <span><kbd className="border border-slate-200 px-1 py-px bg-slate-50">↑↓</kbd> navigate</span>
          <span><kbd className="border border-slate-200 px-1 py-px bg-slate-50">↵</kbd> open</span>
          <span><kbd className="border border-slate-200 px-1 py-px bg-slate-50">Esc</kbd> close</span>
          <span className="ml-auto text-slate-300">⌘K or /</span>
        </div>
      </div>
    </div>
  );
}

// ─── Result builder ────────────────────────────────────────────────────────────

function buildSections(trimmed, recent, rankedActions) {
  if (!trimmed) {
    return buildDefaultSections(recent, rankedActions);
  }
  return buildSearchSections(trimmed, rankedActions);
}

function buildDefaultSections(recent, rankedActions) {
  const sections = [];

  // Quick Start — top 6 workflow launchers, ranked by usage
  sections.push({
    id: "actions",
    label: "Quick Start",
    icon: Zap,
    items: rankedActions.slice(0, 6),
  });

  // Recent — last visited pages
  if (recent.length > 0) {
    sections.push({
      id: "recent",
      label: "Recent",
      icon: Clock,
      items: recent,
    });
  }

  // Platform defaults
  const defaults = ALL_PAGES.filter((p) => DEFAULT_GROUPS.has(p.group)).slice(0, 8);
  if (defaults.length > 0) {
    sections.push({
      id: "platform",
      label: "Platform",
      icon: LayoutGrid,
      items: defaults,
    });
  }

  return sections;
}

function buildSearchSections(trimmed, rankedActions) {
  const sections = [];

  // Intent-based results (goal-oriented, e.g. "submit paper")
  const intentResults = intentSearch(trimmed, ALL_PAGES);
  if (intentResults.length > 0) {
    sections.push({
      id: "intent",
      label: "Suggested for your goal",
      icon: Compass,
      items: intentResults.slice(0, 5),
    });
  }

  // Matching workflow actions
  const matchActions = rankedActions.filter(
    (a) =>
      a.label.toLowerCase().includes(trimmed) ||
      a.description?.toLowerCase().includes(trimmed) ||
      a.category?.toLowerCase().includes(trimmed)
  );
  if (matchActions.length > 0) {
    sections.push({ id: "actions", label: "Actions", icon: Zap, items: matchActions });
  }

  // Matching pages by label, grouped by section — deduplicate with intent results
  const intentPaths = new Set(intentResults.map(p => p.to));
  const matchPages = ALL_PAGES.filter(
    (p) => p.label.toLowerCase().includes(trimmed) && !intentPaths.has(p.to)
  );
  const byGroup = {};
  matchPages.forEach((p) => {
    if (!byGroup[p.group]) byGroup[p.group] = [];
    byGroup[p.group].push(p);
  });
  Object.entries(byGroup).forEach(([group, items]) => {
    sections.push({ id: `pages-${group}`, label: group, icon: null, items });
  });

  return sections;
}

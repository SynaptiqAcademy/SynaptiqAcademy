import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Search, X, Users, Layers, BookOpen, CalendarDays } from "lucide-react";
import api from "../../lib/api";
import { NAVY } from "@/lib/tokens";

function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

function ResultSection({ icon: Icon, label, items, renderItem }) {
  if (!items.length) return null;
  return (
    <div className="mb-4">
      <div className="flex items-center gap-1.5 px-4 py-2 border-b border-slate-100">
        <Icon size={11} strokeWidth={1.5} className="text-slate-400" />
        <span className="overline text-slate-400">{label}</span>
      </div>
      {items.map(renderItem)}
    </div>
  );
}

export default function MobileSearch({ open, onClose }) {
  const inputRef = useRef(null);
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, 280);

  const [people, setPeople]     = useState([]);
  const [collabs, setCollabs]   = useState([]);
  const [journals, setJournals] = useState([]);
  const [loading, setLoading]   = useState(false);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery("");
      setPeople([]);
      setCollabs([]);
      setJournals([]);
      setTimeout(() => inputRef.current?.focus(), 60);
    }
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Search when query changes
  const search = useCallback(async (q) => {
    if (!q.trim()) {
      setPeople([]); setCollabs([]); setJournals([]);
      return;
    }
    setLoading(true);
    try {
      const [pRes, cRes, jRes] = await Promise.allSettled([
        api.get("/users", { params: { q, limit: 4 } }),
        api.get("/collaborations", { params: { q, limit: 4 } }),
        api.get("/journals", { params: { q: q, limit: 3 } }),
      ]);
      const pData = pRes.status === "fulfilled" ? pRes.value.data : {};
      const cData = cRes.status === "fulfilled" ? cRes.value.data : [];
      const jData = jRes.status === "fulfilled" ? jRes.value.data : {};
      setPeople(Array.isArray(pData) ? pData : (pData.items || []));
      setCollabs(Array.isArray(cData) ? cData : (cData.items || []));
      setJournals(Array.isArray(jData) ? jData : (jData.items || []));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { search(debouncedQuery); }, [debouncedQuery, search]);

  const hasResults = people.length + collabs.length + journals.length > 0;
  const showEmpty  = debouncedQuery.trim() && !loading && !hasResults;

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] lg:hidden flex flex-col"
      role="dialog"
      aria-modal="true"
      aria-label="Search"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/60"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative bg-white flex flex-col" style={{ maxHeight: "85vh" }}>
        {/* Input row */}
        <div className="flex items-center gap-2 px-4 h-14 border-b border-slate-200">
          <Search size={15} strokeWidth={1.5} className="text-slate-400 shrink-0" />
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search people, collaborations, journals…"
            className="flex-1 text-sm text-slate-900 placeholder-slate-400 outline-none bg-transparent"
            aria-label="Search query"
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="text-slate-400 hover:text-slate-700"
              aria-label="Clear search"
            >
              <X size={14} strokeWidth={1.5} />
            </button>
          )}
          <button
            onClick={onClose}
            className="ml-1 text-sm text-slate-500 hover:text-slate-900 border-l border-slate-200 pl-3"
            aria-label="Close search"
          >
            Cancel
          </button>
        </div>

        {/* Results */}
        <div className="overflow-y-auto overscroll-contain flex-1">
          {loading && (
            <div className="px-4 py-8 text-center text-xs text-slate-400 font-mono">Searching…</div>
          )}

          {!loading && !debouncedQuery.trim() && (
            <div className="px-4 pt-6 pb-4">
              <p className="overline text-slate-400 mb-3">Quick links</p>
              {[
                { to: "/discover",       label: "Dashboard" },
                { to: "/collaborations", label: "Browse Collaborations" },
                { to: "/network",        label: "Research Network" },
                { to: "/journals",       label: "Journal Discovery" },
                { to: "/manuscripts",    label: "Manuscripts" },
              ].map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={onClose}
                  className="flex items-center gap-3 px-3 py-2.5 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          )}

          {showEmpty && (
            <div className="px-4 py-10 text-center text-sm text-slate-400">
              No results for <span className="text-slate-600">"{debouncedQuery}"</span>
            </div>
          )}

          {hasResults && !loading && (
            <div className="pt-2 pb-6">
              <ResultSection
                icon={Users}
                label="People"
                items={people}
                renderItem={(p) => (
                  <Link
                    key={p.id}
                    to={`/profile/${p.id}`}
                    onClick={onClose}
                    className="flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 transition-colors"
                  >
                    <div className="w-7 h-7 bg-slate-200 flex items-center justify-center shrink-0 text-[10px] text-slate-500 font-medium">
                      {p.full_name?.[0] || "?"}
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-slate-900 truncate">{p.full_name}</div>
                      <div className="text-xs text-slate-500 truncate">{p.institution || p.academic_role || ""}</div>
                    </div>
                  </Link>
                )}
              />

              <ResultSection
                icon={Layers}
                label="Collaborations"
                items={collabs}
                renderItem={(c) => (
                  <Link
                    key={c.id}
                    to={`/collaborations/${c.id}`}
                    onClick={onClose}
                    className="flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 transition-colors"
                  >
                    <div className="w-1 h-8 bg-[#0F2847]/20 shrink-0" />
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-slate-900 truncate">{c.title}</div>
                      <div className="text-xs text-slate-500 truncate">{c.collab_type}</div>
                    </div>
                  </Link>
                )}
              />

              <ResultSection
                icon={BookOpen}
                label="Journals"
                items={journals}
                renderItem={(j) => (
                  <Link
                    key={j.id}
                    to={`/journals/${j.id}`}
                    onClick={onClose}
                    className="flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 transition-colors"
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-slate-900 truncate">{j.name}</div>
                      <div className="text-xs text-slate-500 truncate">{j.publisher || j.issn || ""}</div>
                    </div>
                  </Link>
                )}
              />

              <div className="px-4 pt-3 border-t border-slate-100 mt-2 flex flex-wrap gap-x-4 gap-y-1">
                <Link to={`/network?q=${encodeURIComponent(debouncedQuery)}`} onClick={onClose} className="text-xs text-[#0F2847] hover:underline">
                  All people →
                </Link>
                <Link to={`/collaborations?q=${encodeURIComponent(debouncedQuery)}`} onClick={onClose} className="text-xs text-[#0F2847] hover:underline">
                  All collaborations →
                </Link>
                <Link to={`/journals?q=${encodeURIComponent(debouncedQuery)}`} onClick={onClose} className="text-xs text-[#0F2847] hover:underline">
                  All journals →
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

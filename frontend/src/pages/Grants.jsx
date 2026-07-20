import React, { useState, useEffect, useCallback, useRef } from "react";
import { DiscoveryLayout } from "@/layouts";
import { Link, NavLink } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { ACCENT, EMERALD, NAVY, WARM } from "@/lib/tokens";
import {
  Search, X, ChevronDown, ChevronLeft, ChevronRight, ArrowRight,
  Bookmark, BookmarkCheck, BadgeDollarSign, Coins, Globe, Calendar,
  Clock, Building2, BarChart2, TrendingUp, Sparkles, Lightbulb,
  Users, ExternalLink, FileText, Target, LayoutGrid, List,
  AlertCircle, Timer, PenLine, Filter, Award, Trophy,
  CheckCircle, Zap, Plus,
} from "lucide-react";

// ── Design tokens ─────────────────────────────────────────────────────────────
const BORDER  = "#E4E8EF";

// ── Data helpers ──────────────────────────────────────────────────────────────
function fmtAmount(fa) {
  if (!fa?.amount) return null;
  const { amount: a, currency: cur = "EUR" } = fa;
  if (a >= 1_000_000) return `${(a / 1_000_000).toFixed(1)}M ${cur}`;
  if (a >= 1_000)     return `${Math.round(a / 1_000)}K ${cur}`;
  return `${a} ${cur}`;
}

function daysUntil(dl) {
  if (!dl) return null;
  return Math.round((new Date(dl) - new Date()) / 86_400_000);
}

function urgencyLabel(dl) {
  const d = daysUntil(dl);
  if (d === null)  return null;
  if (d < 0)       return { text: "Closed",     color: "#94A3B8", bg: "#F1F5F9", urgent: false, closed: true };
  if (d === 0)     return { text: "Due today",  color: ACCENT,   bg: "#FFF1F2", urgent: true,  closed: false };
  if (d <= 7)      return { text: `${d}d left`, color: ACCENT,   bg: "#FFF1F2", urgent: true,  closed: false };
  if (d <= 30)     return { text: `${d}d left`, color: "#B45309",bg: "#FFFBEB", urgent: false, closed: false };
  if (d <= 90)     return { text: `${d}d left`, color: "#0369A1",bg: "#F0F9FF", urgent: false, closed: false };
  return {
    text: new Date(dl).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }),
    color: "#64748B", bg: "#F8FAFC", urgent: false, closed: false,
  };
}

const TYPE_STYLE = {
  "Research Grant":          { bg: "#EFF6FF", border: "#93C5FD", text: "#1D4ED8" },
  "Fellowship":              { bg: "#F5F3FF", border: "#C4B5FD", text: "#6D28D9" },
  "Doctoral Funding":        { bg: "#F5F3FF", border: "#C4B5FD", text: "#6D28D9" },
  "Postdoctoral Fellowship": { bg: "#F5F3FF", border: "#C4B5FD", text: "#6D28D9" },
  "Innovation Grant":        { bg: "#ECFDF5", border: "#6EE7B7", text: "#065F46" },
  "Travel Grant":            { bg: "#FFFBEB", border: "#FCD34D", text: "#92400E" },
  "Conference Grant":        { bg: "#FFFBEB", border: "#FCD34D", text: "#92400E" },
  "Scholarship":             { bg: "#FDF4FF", border: "#E879F9", text: "#86198F" },
  "Seed Funding":            { bg: "#FFF7ED", border: "#FDBA74", text: "#9A3412" },
  "Institutional Call":      { bg: "#F0FDF4", border: "#86EFAC", text: "#166534" },
};

function typeStyle(t) {
  return TYPE_STYLE[t] || { bg: "#F8FAFC", border: "#CBD5E1", text: "#475569" };
}

function scoreColor(s) {
  if (s >= 80) return EMERALD;
  if (s >= 60) return "#3B82F6";
  if (s >= 40) return "#F59E0B";
  return "#94A3B8";
}

// ── Constants ─────────────────────────────────────────────────────────────────
const PAGE_SIZE = 24;

const SORT_OPTIONS = [
  { value: "deadline_asc", label: "Soonest deadline" },
  { value: "amount",       label: "Largest funding" },
  { value: "recent",       label: "Recently added" },
  { value: "relevance",    label: "Most relevant" },
];

const CAREER_STAGES = [
  { value: "early_career", label: "Early Career / PhD" },
  { value: "mid_career",   label: "Mid-Career" },
  { value: "senior",       label: "Senior / PI" },
  { value: "industry",     label: "Industry" },
];

const TABS = [
  { to: "/journals",    label: "Journals",         testid: TID.discoveryTabJournals },
  { to: "/conferences", label: "Conferences",       testid: TID.discoveryTabConferences },
  { to: "/grants",      label: "Grants & Funding",  testid: TID.discoveryTabGrants },
];

// ── Main component ────────────────────────────────────────────────────────────
export default function Grants() {
  const { user } = useAuth();
  const explorerRef = useRef(null);

  // Search + filter state
  const [q,          setQ]          = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [filters,    setFilters]    = useState({});
  const [sort,       setSort]       = useState("deadline_asc");
  const [openOnly,   setOpenOnly]   = useState(false);
  const [page,       setPage]       = useState(1);
  const [view,       setView]       = useState("grid");

  // Data
  const [items,   setItems]   = useState([]);
  const [total,   setTotal]   = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [facets,  setFacets]  = useState({});
  const [gated,   setGated]   = useState(false);
  const [quota,   setQuota]   = useState(null);

  // Saved state: Map<id, boolean> for optimistic updates
  const [savedMap, setSavedMap] = useState(new Map());

  // Matches (profile-based)
  const [matches,        setMatches]        = useState(null);
  const [matchesLoading, setMatchesLoading] = useState(true);

  // Compare
  const [compareList, setCompareList] = useState([]);

  // ── Debounce q ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 400);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => { setPage(1); }, [debouncedQ, filters, sort, openOnly]);

  // ── Boot: quota, matches, facets ───────────────────────────────────────────
  useEffect(() => {
    api.get("/discovery/quota").then((r) => setQuota(r.data)).catch(() => {});
    api.get("/grants/matches?limit=10")
      .then((r) => setMatches(Array.isArray(r.data) ? r.data : []))
      .catch(() => setMatches([]))
      .finally(() => setMatchesLoading(false));
    api.get("/grants/facets").then((r) => setFacets(r.data)).catch(() => {});
  }, []);

  // ── Fetch grants ───────────────────────────────────────────────────────────
  const filtersKey = JSON.stringify(filters);
  const fetchGrants = useCallback(async () => {
    setLoading(true);
    setGated(false);
    try {
      const params = {
        page,
        page_size: PAGE_SIZE,
        sort,
        ...(debouncedQ            && { q: debouncedQ }),
        ...(openOnly              && { open_only: true }),
        ...(filters.research_area && { research_area: filters.research_area }),
        ...(filters.country       && { country: filters.country }),
        ...(filters.funding_type  && { funding_type: filters.funding_type }),
        ...(filters.sponsor       && { sponsor: filters.sponsor }),
        ...(filters.career_stage  && { career_stage: filters.career_stage }),
      };
      const { data } = await api.get("/grants", { params });
      setItems(data.items || []);
      setTotal(data.total || 0);
      setHasMore(data.has_more || false);
    } catch (err) {
      if (err?.response?.status === 402 || err?.response?.status === 429) setGated(true);
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, sort, debouncedQ, openOnly, filtersKey]);

  useEffect(() => { fetchGrants(); }, [fetchGrants]);

  // Update facets when query changes
  useEffect(() => {
    const params = debouncedQ ? { q: debouncedQ } : {};
    api.get("/grants/facets", { params }).then((r) => setFacets(r.data)).catch(() => {});
  }, [debouncedQ]);

  // ── Save / unsave ───────────────────────────────────────────────────────────
  const isSaved = (g) =>
    savedMap.has(g.id) ? savedMap.get(g.id) : g.is_saved;

  const toggleSave = async (g, e) => {
    e.preventDefault();
    e.stopPropagation();
    const was = isSaved(g);
    setSavedMap((prev) => new Map([...prev, [g.id, !was]]));
    try {
      if (was) {
        await api.post(`/grants/${g.id}/unsave`);
        toast.success("Removed from saved grants");
      } else {
        await api.post(`/grants/${g.id}/save`);
        toast.success("Grant saved");
      }
    } catch {
      setSavedMap((prev) => new Map([...prev, [g.id, was]]));
      toast.error("Could not update saved status");
    }
  };

  // ── Compare ────────────────────────────────────────────────────────────────
  const toggleCompare = (g, e) => {
    e.preventDefault();
    e.stopPropagation();
    setCompareList((prev) => {
      if (prev.find((x) => x.id === g.id)) return prev.filter((x) => x.id !== g.id);
      if (prev.length >= 3) { toast.error("Compare up to 3 grants at once"); return prev; }
      return [...prev, g];
    });
  };

  // ── Filters ────────────────────────────────────────────────────────────────
  const setFilter = (key, val) => {
    setFilters((prev) => {
      if (!val) { const { [key]: _, ...rest } = prev; return rest; }
      return { ...prev, [key]: val };
    });
  };

  const activeFilterCount = Object.values(filters).filter(Boolean).length + (openOnly ? 1 : 0);
  const hasFilters = activeFilterCount > 0 || !!debouncedQ;

  // Upcoming deadlines from the current page
  const upcoming = items
    .filter((g) => { const d = daysUntil(g.deadline); return d !== null && d >= 0 && d <= 60; })
    .sort((a, b) => daysUntil(a.deadline) - daysUntil(b.deadline))
    .slice(0, 8);

  return (
    <DiscoveryLayout>
      {/* Skeleton pulse animation */}
      <style>{`
        @keyframes sq-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.45; }
        }
        .sq-pulse { animation: sq-pulse 1.8s ease-in-out infinite; }
      `}</style>

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <HeroHeader
        user={user}
        onFindGrants={() => explorerRef.current?.scrollIntoView({ behavior: "smooth" })}
      />

      {/* ── Tabs ──────────────────────────────────────────────────────────── */}
      <div
        style={{
          margin: "0 -24px",
          borderBottom: `1px solid ${BORDER}`,
          background: "white",
          display: "flex",
          paddingLeft: 24,
        }}
      >
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            data-testid={tab.testid}
            style={({ isActive }) => ({
              padding: "10px 20px",
              fontSize: 13,
              fontWeight: isActive ? 700 : 500,
              color: isActive ? NAVY : "#64748B",
              borderBottom: `2px solid ${isActive ? NAVY : "transparent"}`,
              textDecoration: "none",
              whiteSpace: "nowrap",
              transition: "color 150ms, border-color 150ms",
            })}
          >
            {tab.label}
          </NavLink>
        ))}
      </div>

      {/* ── AI Match panel ────────────────────────────────────────────────── */}
      {(matchesLoading || (matches && matches.length > 0)) && (
        <MatchesPanel
          matches={matches}
          loading={matchesLoading}
          isSaved={isSaved}
          toggleSave={toggleSave}
          compareList={compareList}
          toggleCompare={toggleCompare}
          user={user}
        />
      )}

      {/* ── Deadline ticker ───────────────────────────────────────────────── */}
      {upcoming.length > 0 && <DeadlineTicker items={upcoming} />}

      {/* ── Grant Explorer ────────────────────────────────────────────────── */}
      <div ref={explorerRef} style={{ marginTop: 32, display: "flex", gap: 24, alignItems: "flex-start" }}>

        {/* ── Facet sidebar ─────────────────────────────────────────────── */}
        <aside
          style={{
            width: 248,
            flexShrink: 0,
            position: "sticky",
            top: 24,
            maxHeight: "calc(100vh - 80px)",
            overflowY: "auto",
          }}
        >
          <FacetPanel
            facets={facets}
            filters={filters}
            setFilter={setFilter}
            openOnly={openOnly}
            setOpenOnly={setOpenOnly}
          />
        </aside>

        {/* ── Main content ──────────────────────────────────────────────── */}
        <div style={{ flex: 1, minWidth: 0 }}>

          {/* Search + sort + view toggle */}
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12 }}>
            <div style={{ flex: 1, position: "relative" }}>
              <Search
                size={14} strokeWidth={1.5}
                style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94A3B8", pointerEvents: "none" }}
              />
              <input
                data-testid={TID.discoverySearch}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search grants, fellowships, programmes, sponsors…"
                style={{
                  width: "100%",
                  padding: "9px 36px 9px 36px",
                  border: `1px solid ${BORDER}`,
                  background: "white",
                  fontSize: 13,
                  color: "#1E293B",
                  outline: "none",
                  boxSizing: "border-box",
                  transition: "border-color 150ms",
                }}
                onFocus={(e) => { e.target.style.borderColor = NAVY; }}
                onBlur={(e) => { e.target.style.borderColor = BORDER; }}
              />
              {q && (
                <button
                  onClick={() => setQ("")}
                  style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", color: "#94A3B8", cursor: "pointer", display: "flex", alignItems: "center" }}
                >
                  <X size={13} strokeWidth={1.5} />
                </button>
              )}
            </div>

            <select
              data-testid={TID.discoverySortSelect}
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              style={{
                padding: "9px 12px",
                border: `1px solid ${BORDER}`,
                background: "white",
                fontSize: 13,
                color: "#374151",
                cursor: "pointer",
                flexShrink: 0,
                outline: "none",
              }}
            >
              {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>

            {/* View toggle */}
            <div style={{ display: "flex", border: `1px solid ${BORDER}`, overflow: "hidden", flexShrink: 0 }}>
              {[
                { k: "grid",     Icon: LayoutGrid },
                { k: "timeline", Icon: List       },
              ].map(({ k, Icon }) => (
                <button
                  key={k}
                  onClick={() => setView(k)}
                  title={k === "grid" ? "Grid view" : "Timeline view"}
                  style={{
                    padding: "8px 10px",
                    background: view === k ? NAVY : "white",
                    color: view === k ? "white" : "#64748B",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    borderLeft: k === "timeline" ? `1px solid ${BORDER}` : "none",
                    border: "none",
                    outline: "none",
                  }}
                >
                  <Icon size={14} strokeWidth={1.5} />
                </button>
              ))}
            </div>
          </div>

          {/* Filter chips */}
          {activeFilterCount > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
              {Object.entries(filters).map(([k, v]) => v && (
                <FilterChip key={k} label={`${k.replace(/_/g, " ")}: ${v}`} onRemove={() => setFilter(k, "")} />
              ))}
              {openOnly && <FilterChip label="Open calls only" onRemove={() => setOpenOnly(false)} />}
              <button
                onClick={() => { setFilters({}); setOpenOnly(false); setQ(""); }}
                style={{ fontSize: 11, color: "#94A3B8", cursor: "pointer", padding: "3px 8px", background: "none", border: "none", textDecoration: "underline" }}
              >
                Clear all
              </button>
            </div>
          )}

          {/* Results count */}
          {!loading && !gated && (
            <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 16, fontFamily: "monospace" }}>
              {total.toLocaleString()} {hasFilters ? "matching" : "total"} funding opportunities
            </div>
          )}

          {/* Content */}
          <div data-testid={TID.grantsList}>
            {gated ? (
              <GatedState />
            ) : view === "timeline" ? (
              <TimelineView
                items={items}
                loading={loading}
                isSaved={isSaved}
                toggleSave={toggleSave}
                compareList={compareList}
                toggleCompare={toggleCompare}
              />
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(270px, 1fr))", gap: 14 }}>
                {loading
                  ? Array.from({ length: 9 }).map((_, i) => <GrantSkeleton key={i} />)
                  : items.map((g) => (
                      <GrantCard
                        key={g.id}
                        g={g}
                        isSaved={isSaved(g)}
                        onSave={toggleSave}
                        isCompared={compareList.some((c) => c.id === g.id)}
                        onCompare={toggleCompare}
                      />
                    ))
                }
              </div>
            )}
          </div>

          {!loading && !gated && items.length === 0 && (
            <GrantsEmptyState hasFilters={hasFilters} />
          )}

          {/* Pagination */}
          {!loading && !gated && total > PAGE_SIZE && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 24, paddingTop: 16, borderTop: `1px solid ${BORDER}` }}>
              <button
                data-testid={TID.discoveryPagePrev}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "7px 16px", fontSize: 13,
                  border: `1px solid ${BORDER}`,
                  background: page === 1 ? "#F8FAFC" : "white",
                  color: page === 1 ? "#CBD5E1" : NAVY,
                  cursor: page === 1 ? "not-allowed" : "pointer",
                  outline: "none",
                }}
              >
                <ChevronLeft size={14} strokeWidth={1.5} /> Previous
              </button>
              <span style={{ fontSize: 12, color: "#94A3B8", fontFamily: "monospace" }}>
                Page {page} of {Math.ceil(total / PAGE_SIZE)}
              </span>
              <button
                data-testid={TID.discoveryPageNext}
                onClick={() => setPage((p) => p + 1)}
                disabled={!hasMore}
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "7px 16px", fontSize: 13,
                  border: `1px solid ${BORDER}`,
                  background: !hasMore ? "#F8FAFC" : "white",
                  color: !hasMore ? "#CBD5E1" : NAVY,
                  cursor: !hasMore ? "not-allowed" : "pointer",
                  outline: "none",
                }}
              >
                Next <ChevronRight size={14} strokeWidth={1.5} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Application prep strip ───────────────────────────────────────── */}
      <ApplicationPrepStrip />

      {/* ── Compare panel ────────────────────────────────────────────────── */}
      {compareList.length >= 2 && (
        <ComparePanel
          grants={compareList}
          onRemove={(id) => setCompareList((p) => p.filter((x) => x.id !== id))}
          onClose={() => setCompareList([])}
        />
      )}
    </DiscoveryLayout>
  );
}

// ── Hero header ───────────────────────────────────────────────────────────────
function HeroHeader({ user, onFindGrants }) {
  const userField = (user?.research_areas || []).slice(0, 2).join(", ") || "your research field";
  const institution = user?.institution || "your institution";

  return (
    <div
      style={{
        margin: "-24px -24px 0",
        background: `linear-gradient(145deg, ${NAVY} 0%, #163355 55%, ${NAVY} 100%)`,
        padding: "48px 56px 0",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Grid overlay */}
      <div style={{
        position: "absolute", inset: 0, opacity: 0.035,
        backgroundImage: "linear-gradient(rgba(255,255,255,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.3) 1px, transparent 1px)",
        backgroundSize: "40px 40px",
      }} />

      <div style={{ position: "relative" }}>
        {/* Kicker */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#34D399" }} />
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.45)" }}>
            Funding Intelligence Platform
          </span>
        </div>

        {/* Title */}
        <h1 style={{ fontFamily: "Georgia, serif", fontSize: 46, fontWeight: 400, color: "white", lineHeight: 1.1, marginBottom: 16, maxWidth: 560 }}>
          Research Funding<br />
          <span style={{ color: "rgba(255,255,255,0.65)", fontSize: 38 }}>Discovery &amp; Intelligence</span>
        </h1>

        <p style={{ fontSize: 14, color: "rgba(255,255,255,0.5)", lineHeight: 1.65, maxWidth: 500, marginBottom: 28 }}>
          Profile-matched grants, fellowships, scholarships and calls aggregated from OpenAIRE,
          NIH, NSF, ERC, Horizon Europe and 40+ international agencies.
          Personalized for <strong style={{ color: "rgba(255,255,255,0.75)" }}>{userField}</strong> at&nbsp;
          <strong style={{ color: "rgba(255,255,255,0.75)" }}>{institution}</strong>.
        </p>

        {/* CTAs */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 36 }}>
          <button
            onClick={onFindGrants}
            style={{
              padding: "10px 22px",
              background: "white",
              color: NAVY,
              fontSize: 13,
              fontWeight: 700,
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
              outline: "none",
            }}
          >
            <BadgeDollarSign size={14} strokeWidth={2} />
            Find Matching Grants
          </button>
          <Link
            to="/ai"
            style={{
              padding: "10px 22px",
              background: "transparent",
              color: "rgba(255,255,255,0.8)",
              fontSize: 13,
              fontWeight: 600,
              border: "1px solid rgba(255,255,255,0.2)",
              display: "flex",
              alignItems: "center",
              gap: 8,
              textDecoration: "none",
            }}
          >
            <PenLine size={14} strokeWidth={1.5} />
            Prepare Application
          </Link>
        </div>

        {/* Stats strip */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 0,
            borderTop: "1px solid rgba(255,255,255,0.08)",
            paddingTop: 20,
          }}
        >
          {[
            { icon: BadgeDollarSign, label: "Opportunities", val: "7,900+" },
            { icon: Globe,           label: "Agencies",      val: "40+" },
            { icon: Clock,           label: "Updated",       val: "Daily" },
            { icon: Sparkles,        label: "AI Matched",    val: "Free" },
          ].map(({ icon: Icon, label, val }) => (
            <div key={label} style={{ padding: "12px 16px 12px 0", borderRight: "1px solid rgba(255,255,255,0.06)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 3 }}>
                <Icon size={10} strokeWidth={1.5} style={{ color: "rgba(255,255,255,0.35)" }} />
                <span style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 600 }}>{label}</span>
              </div>
              <div style={{ fontSize: 20, fontWeight: 800, color: "white", fontFamily: "monospace" }}>{val}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Matches panel ─────────────────────────────────────────────────────────────
function MatchesPanel({ matches, loading, isSaved, toggleSave, compareList, toggleCompare, user }) {
  const [expanded, setExpanded] = useState(true);
  const hasProfile = !!(user?.research_areas?.length || user?.research_interests?.length);

  return (
    <div style={{ background: `${NAVY}05`, borderBottom: `1px solid ${BORDER}`, padding: "18px 0 20px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: expanded ? 16 : 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <Sparkles size={13} strokeWidth={1.5} style={{ color: NAVY }} />
          <span style={{ fontSize: 12, fontWeight: 700, color: NAVY, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Recommended for You
          </span>
          <span style={{ fontSize: 11, color: "#94A3B8" }}>Profile-matched · No credits consumed</span>
          {!hasProfile && (
            <span style={{ fontSize: 11, color: "#D97706", display: "flex", alignItems: "center", gap: 3 }}>
              <AlertCircle size={11} strokeWidth={1.5} />
              Add research areas to improve matching
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Link
            to="/academic-passport"
            style={{ fontSize: 11, color: "#64748B", textDecoration: "none", display: "flex", alignItems: "center", gap: 3 }}
          >
            Update profile <ArrowRight size={10} strokeWidth={1.5} />
          </Link>
          <button
            onClick={() => setExpanded((v) => !v)}
            style={{ color: "#94A3B8", cursor: "pointer", display: "flex", alignItems: "center", background: "none", border: "none", outline: "none" }}
          >
            <ChevronDown
              size={13} strokeWidth={1.5}
              style={{ transform: expanded ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 200ms ease-out" }}
            />
          </button>
        </div>
      </div>

      {expanded && (
        <div style={{ display: "flex", gap: 14, overflowX: "auto", paddingBottom: 4 }}>
          {loading
            ? Array.from({ length: 4 }).map((_, i) => <MatchSkeleton key={i} />)
            : (matches || []).slice(0, 7).map((g) => (
                <MatchCard
                  key={g.id}
                  g={g}
                  isSaved={isSaved(g)}
                  onSave={toggleSave}
                  isCompared={compareList.some((c) => c.id === g.id)}
                  onCompare={toggleCompare}
                />
              ))
          }
        </div>
      )}
    </div>
  );
}

function MatchCard({ g, isSaved, onSave, isCompared, onCompare }) {
  const amount   = fmtAmount(g.funding_amount);
  const deadline = urgencyLabel(g.deadline);
  const ts       = typeStyle(g.funding_type);
  const score    = g.match_score || 0;
  const color    = scoreColor(score);

  return (
    <Link
      to={`/grants/${g.id}`}
      data-testid={TID.discoveryItem(g.id)}
      style={{
        display: "block",
        minWidth: 240,
        maxWidth: 280,
        flexShrink: 0,
        border: `1px solid ${BORDER}`,
        background: "white",
        padding: 16,
        textDecoration: "none",
        position: "relative",
        transition: "border-color 150ms, box-shadow 150ms",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY; e.currentTarget.style.boxShadow = "0 4px 14px rgba(15,40,71,0.08)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.boxShadow = "none"; }}
    >
      {/* Score + save */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 10, gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 38, height: 38, borderRadius: "50%", background: color + "18", border: `1.5px solid ${color}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <span style={{ fontSize: 11, fontWeight: 800, color, fontFamily: "monospace" }}>{score}</span>
          </div>
          <div>
            <div style={{ fontSize: 9, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 600 }}>Match</div>
            <div style={{ fontSize: 9, fontWeight: 700, color: g.eligibility_estimate === "high" ? EMERALD : "#D97706" }}>
              {g.eligibility_estimate === "high" ? "High eligibility" : "Check eligibility"}
            </div>
          </div>
        </div>
        <button
          onClick={(e) => onSave(g, e)}
          style={{ color: isSaved ? ACCENT : "#CBD5E1", cursor: "pointer", padding: 2, display: "flex", alignItems: "center", background: "none", border: "none", outline: "none", transition: "color 150ms", flexShrink: 0 }}
          title={isSaved ? "Remove from saved" : "Save grant"}
        >
          {isSaved ? <BookmarkCheck size={14} strokeWidth={1.5} /> : <Bookmark size={14} strokeWidth={1.5} />}
        </button>
      </div>

      {/* Type */}
      {g.funding_type && (
        <div style={{ marginBottom: 7 }}>
          <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", padding: "2px 6px", background: ts.bg, border: `1px solid ${ts.border}`, color: ts.text }}>
            {g.funding_type}
          </span>
        </div>
      )}

      {/* Title */}
      <div style={{ fontFamily: "Georgia, serif", fontSize: 13, color: "#0F172A", lineHeight: 1.4, marginBottom: 6, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
        {g.title}
      </div>

      {/* Sponsor */}
      <div style={{ fontSize: 11, color: "#64748B", marginBottom: 8, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
        {g.sponsor}
      </div>

      {/* Match reason */}
      {g.match_reason && (
        <div style={{ fontSize: 10, color: "#94A3B8", fontStyle: "italic", marginBottom: 8, lineHeight: 1.4 }}>
          {g.match_reason}
        </div>
      )}

      {/* Score bar */}
      <div style={{ height: 2, background: "#F1F5F9", marginBottom: 8, borderRadius: 1 }}>
        <div style={{ height: "100%", width: `${Math.min(100, score)}%`, background: color, borderRadius: 1, transition: "width 700ms ease-out" }} />
      </div>

      {/* Meta */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        {amount && <span style={{ fontSize: 10, color: EMERALD, fontWeight: 700 }}>{amount}</span>}
        {deadline && !deadline.closed && (
          <span style={{ fontSize: 10, color: deadline.color, fontWeight: 600 }}>{deadline.text}</span>
        )}
      </div>
    </Link>
  );
}

function MatchSkeleton() {
  return (
    <div style={{ minWidth: 240, maxWidth: 280, flexShrink: 0, border: `1px solid ${BORDER}`, background: "white", padding: 16 }}>
      <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
        <div className="sq-pulse" style={{ width: 38, height: 38, borderRadius: "50%", background: "#F1F5F9" }} />
        <div style={{ flex: 1 }}>
          <div className="sq-pulse" style={{ height: 10, background: "#F1F5F9", marginBottom: 6, width: "60%" }} />
          <div className="sq-pulse" style={{ height: 8, background: "#F1F5F9", width: "40%" }} />
        </div>
      </div>
      <div className="sq-pulse" style={{ height: 36, background: "#F1F5F9", marginBottom: 8 }} />
      <div className="sq-pulse" style={{ height: 10, width: "70%", background: "#F1F5F9", marginBottom: 10 }} />
      <div className="sq-pulse" style={{ height: 2, background: "#F1F5F9", marginBottom: 8 }} />
      <div className="sq-pulse" style={{ height: 10, width: "45%", background: "#F1F5F9" }} />
    </div>
  );
}

// ── Deadline ticker ───────────────────────────────────────────────────────────
function DeadlineTicker({ items }) {
  const urgentCount = items.filter((g) => { const d = daysUntil(g.deadline); return d !== null && d <= 30; }).length;

  return (
    <div style={{ background: "#FFFBEB", borderBottom: "1px solid #FCD34D", padding: "7px 0", margin: "0 -24px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, paddingLeft: 24, overflowX: "auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 5, flexShrink: 0 }}>
          <Timer size={11} strokeWidth={1.5} style={{ color: "#B45309" }} />
          <span style={{ fontSize: 11, fontWeight: 700, color: "#B45309", whiteSpace: "nowrap" }}>
            {urgentCount > 0 ? `${urgentCount} closing soon` : "Upcoming deadlines"}
          </span>
        </div>
        {items.map((g) => {
          const ul = urgencyLabel(g.deadline);
          return ul ? (
            <Link
              key={g.id}
              to={`/grants/${g.id}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "3px 10px",
                background: ul.bg,
                textDecoration: "none",
                flexShrink: 0,
                border: `1px solid ${ul.color}22`,
              }}
            >
              <span style={{ fontSize: 10, fontWeight: 700, color: ul.color, whiteSpace: "nowrap" }}>{ul.text}</span>
              <span style={{ fontSize: 10, color: "#94A3B8" }}>·</span>
              <span style={{ fontSize: 10, color: "#374151", maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{g.title}</span>
            </Link>
          ) : null;
        })}
      </div>
    </div>
  );
}

// ── Facet panel ───────────────────────────────────────────────────────────────
function FacetPanel({ facets, filters, setFilter, openOnly, setOpenOnly }) {
  const [openSections, setOpenSections] = useState({
    research_areas: true,
    funding_types: true,
    countries: false,
    sponsors: false,
  });

  const toggle = (k) => setOpenSections((p) => ({ ...p, [k]: !p[k] }));

  function FGroup({ title, sk, fk, items }) {
    const isOpen = openSections[sk];
    const active = filters[fk];
    return (
      <div style={{ borderBottom: `1px solid ${BORDER}`, paddingBottom: 10, marginBottom: 10 }}>
        <button
          onClick={() => toggle(sk)}
          style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: isOpen ? 8 : 0, cursor: "pointer", background: "none", border: "none", outline: "none", padding: 0 }}
        >
          <span style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.1em" }}>{title}</span>
          <ChevronDown
            size={11} strokeWidth={1.5}
            style={{ color: "#94A3B8", transform: isOpen ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 150ms ease-out" }}
          />
        </button>
        {isOpen && (items || []).slice(0, 12).map((f) => (
          <button
            key={f._id}
            data-testid={TID.discoveryFacet(fk, f._id)}
            onClick={() => setFilter(fk, active === f._id ? "" : f._id)}
            style={{
              width: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "4px 0",
              cursor: "pointer",
              background: "none",
              border: "none",
              outline: "none",
              textAlign: "left",
            }}
          >
            <span style={{ fontSize: 12, color: active === f._id ? NAVY : "#64748B", fontWeight: active === f._id ? 700 : 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 160 }}>
              {active === f._id && "✓ "}{f._id}
            </span>
            <span style={{ fontSize: 10, color: "#94A3B8", fontFamily: "monospace", flexShrink: 0, marginLeft: 4 }}>{f.count}</span>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div style={{ padding: "4px 0" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 14 }}>Filters</div>

      {/* Open calls toggle */}
      <div style={{ marginBottom: 12, paddingBottom: 12, borderBottom: `1px solid ${BORDER}` }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={openOnly}
            onChange={(e) => setOpenOnly(e.target.checked)}
            style={{ accentColor: NAVY, width: 13, height: 13, cursor: "pointer" }}
          />
          <span style={{ fontSize: 12, fontWeight: 600, color: NAVY }}>Open calls only</span>
        </label>
      </div>

      {/* Career stage */}
      <div style={{ borderBottom: `1px solid ${BORDER}`, paddingBottom: 10, marginBottom: 10 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Career Stage</div>
        {CAREER_STAGES.map((cs) => {
          const isActive = filters.career_stage === cs.value;
          return (
            <button
              key={cs.value}
              data-testid={TID.grantsTab(cs.value)}
              onClick={() => setFilter("career_stage", isActive ? "" : cs.value)}
              style={{ width: "100%", display: "flex", alignItems: "center", gap: 7, padding: "4px 0", cursor: "pointer", background: "none", border: "none", outline: "none", textAlign: "left" }}
            >
              <div style={{ width: 13, height: 13, border: `1.5px solid ${isActive ? NAVY : "#CBD5E1"}`, background: isActive ? NAVY : "transparent", borderRadius: 2, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                {isActive && <div style={{ width: 7, height: 7, background: "white", borderRadius: 1 }} />}
              </div>
              <span style={{ fontSize: 12, color: isActive ? NAVY : "#64748B", fontWeight: isActive ? 700 : 400 }}>{cs.label}</span>
            </button>
          );
        })}
      </div>

      <FGroup title="Research Area" sk="research_areas" fk="research_area" items={facets.research_areas} />
      <FGroup title="Funding Type"  sk="funding_types"  fk="funding_type"  items={facets.funding_types} />
      <FGroup title="Country"       sk="countries"      fk="country"       items={facets.countries} />
      <FGroup title="Sponsor"       sk="sponsors"       fk="sponsor"       items={facets.sponsors} />
    </div>
  );
}

// ── Grant card (grid) ─────────────────────────────────────────────────────────
function GrantCard({ g, isSaved, onSave, isCompared, onCompare }) {
  const amount   = fmtAmount(g.funding_amount);
  const deadline = urgencyLabel(g.deadline);
  const ts       = typeStyle(g.funding_type);
  const d        = daysUntil(g.deadline);

  return (
    <Link
      to={`/grants/${g.id}`}
      data-testid={TID.discoveryItem(g.id)}
      style={{
        display: "flex",
        flexDirection: "column",
        border: `1px solid ${BORDER}`,
        background: "white",
        textDecoration: "none",
        transition: "border-color 150ms, box-shadow 150ms, transform 150ms",
        position: "relative",
        overflow: "hidden",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = NAVY;
        e.currentTarget.style.boxShadow = "0 4px 16px rgba(15,40,71,0.09)";
        e.currentTarget.style.transform = "translateY(-1px)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = BORDER;
        e.currentTarget.style.boxShadow = "none";
        e.currentTarget.style.transform = "translateY(0)";
      }}
    >
      {/* Urgency strip */}
      {deadline && !deadline.closed && d !== null && d <= 30 && (
        <div style={{ height: 2, background: deadline.color }} />
      )}

      <div style={{ padding: "14px 16px", flex: 1, display: "flex", flexDirection: "column", gap: 0 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8, marginBottom: 8 }}>
          <div style={{ display: "flex", gap: 5, flexWrap: "wrap", flex: 1 }}>
            {g.funding_type && (
              <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", padding: "2px 5px", background: ts.bg, border: `1px solid ${ts.border}`, color: ts.text, flexShrink: 0 }}>
                {g.funding_type}
              </span>
            )}
            {deadline && (
              <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 5px", background: deadline.bg, color: deadline.color, flexShrink: 0 }}>
                {deadline.text}
              </span>
            )}
          </div>
          <button
            onClick={(e) => onSave(g, e)}
            style={{ color: isSaved ? ACCENT : "#CBD5E1", cursor: "pointer", padding: 2, display: "flex", alignItems: "center", flexShrink: 0, background: "none", border: "none", outline: "none", transition: "color 150ms" }}
            title={isSaved ? "Remove from saved" : "Save grant"}
          >
            {isSaved ? <BookmarkCheck size={15} strokeWidth={1.5} /> : <Bookmark size={15} strokeWidth={1.5} />}
          </button>
        </div>

        {/* Title */}
        <h3
          style={{
            fontFamily: "Georgia, serif",
            fontSize: 14,
            color: "#0F172A",
            lineHeight: 1.4,
            marginBottom: 6,
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {g.title}
        </h3>

        {/* Sponsor */}
        <div style={{ fontSize: 11, color: "#64748B", marginBottom: 10, display: "flex", alignItems: "center", gap: 4, overflow: "hidden" }}>
          <Building2 size={10} strokeWidth={1.5} style={{ flexShrink: 0 }} />
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{g.sponsor || "—"}</span>
        </div>

        {/* Research areas */}
        {(g.research_areas || []).length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
            {g.research_areas.slice(0, 3).map((a, i) => (
              <span key={i} style={{ fontSize: 9, color: "#64748B", background: "#F8FAFC", border: `1px solid ${BORDER}`, padding: "2px 5px" }}>{a}</span>
            ))}
            {g.research_areas.length > 3 && (
              <span style={{ fontSize: 9, color: "#94A3B8" }}>+{g.research_areas.length - 3}</span>
            )}
          </div>
        )}

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Amount + Country */}
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 10 }}>
          {amount && (
            <span style={{ fontSize: 11, fontWeight: 700, color: EMERALD, display: "flex", alignItems: "center", gap: 3 }}>
              <Coins size={10} strokeWidth={1.5} /> {amount}
            </span>
          )}
          {g.country && (
            <span style={{ fontSize: 10, color: "#64748B", display: "flex", alignItems: "center", gap: 3 }}>
              <Globe size={9} strokeWidth={1.5} /> {g.country}
            </span>
          )}
          {g.duration && (
            <span style={{ fontSize: 10, color: "#64748B" }}>{g.duration}</span>
          )}
        </div>
      </div>

      {/* Card footer */}
      <div
        style={{
          borderTop: `1px solid ${BORDER}`,
          padding: "7px 16px",
          display: "flex",
          gap: 10,
          background: "#FAFBFC",
          alignItems: "center",
        }}
        onClick={(e) => e.preventDefault()}
      >
        <button
          onClick={(e) => onCompare(g, e)}
          style={{
            fontSize: 10,
            fontWeight: 600,
            color: isCompared ? NAVY : "#94A3B8",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 3,
            background: "none",
            border: "none",
            outline: "none",
            textDecoration: isCompared ? "underline" : "none",
            padding: 0,
          }}
        >
          <BarChart2 size={10} strokeWidth={1.5} /> {isCompared ? "Comparing" : "Compare"}
        </button>
        <span style={{ color: "#E2E8F0", fontSize: 12 }}>|</span>
        <Link
          to="/ai"
          onClick={(e) => e.stopPropagation()}
          style={{ fontSize: 10, fontWeight: 600, color: "#94A3B8", display: "flex", alignItems: "center", gap: 3, textDecoration: "none" }}
        >
          <Sparkles size={10} strokeWidth={1.5} /> Prepare
        </Link>
        <span style={{ color: "#E2E8F0", fontSize: 12 }}>|</span>
        <Link
          to="/grant-applications"
          onClick={(e) => e.stopPropagation()}
          style={{ fontSize: 10, fontWeight: 600, color: "#94A3B8", display: "flex", alignItems: "center", gap: 3, textDecoration: "none" }}
        >
          <Plus size={10} strokeWidth={1.5} /> Apply
        </Link>
      </div>
    </Link>
  );
}

function GrantSkeleton() {
  return (
    <div style={{ border: `1px solid ${BORDER}`, background: "white" }}>
      <div style={{ padding: "14px 16px" }}>
        <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
          <div className="sq-pulse" style={{ height: 16, width: 80, background: "#F1F5F9" }} />
          <div className="sq-pulse" style={{ height: 16, width: 60, background: "#F1F5F9" }} />
        </div>
        <div className="sq-pulse" style={{ height: 38, background: "#F1F5F9", marginBottom: 8 }} />
        <div className="sq-pulse" style={{ height: 11, width: "65%", background: "#F1F5F9", marginBottom: 12 }} />
        <div style={{ display: "flex", gap: 5, marginBottom: 12 }}>
          {[50, 45, 60].map((w, i) => (
            <div key={i} className="sq-pulse" style={{ height: 17, width: w, background: "#F1F5F9" }} />
          ))}
        </div>
        <div className="sq-pulse" style={{ height: 11, width: "40%", background: "#F1F5F9" }} />
      </div>
      <div style={{ borderTop: `1px solid ${BORDER}`, padding: "7px 16px", background: "#FAFBFC" }}>
        <div className="sq-pulse" style={{ height: 10, width: "50%", background: "#F1F5F9" }} />
      </div>
    </div>
  );
}

// ── Filter chip ───────────────────────────────────────────────────────────────
function FilterChip({ label, onRemove }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "3px 8px", background: `${NAVY}0D`, border: `1px solid ${NAVY}20`, fontSize: 11, color: NAVY, fontWeight: 600 }}>
      {label}
      <button
        onClick={onRemove}
        style={{ display: "flex", alignItems: "center", color: "#94A3B8", cursor: "pointer", marginLeft: 2, background: "none", border: "none", outline: "none" }}
      >
        <X size={10} strokeWidth={2} />
      </button>
    </div>
  );
}

// ── Timeline view ─────────────────────────────────────────────────────────────
function TimelineView({ items, loading, isSaved, toggleSave, compareList, toggleCompare }) {
  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {Array.from({ length: 6 }).map((_, i) => <TimelineSkeleton key={i} />)}
      </div>
    );
  }

  if (!items.length) return null;

  // Group by month
  const groups = {};
  items.forEach((g) => {
    const key = g.deadline
      ? new Date(g.deadline).toLocaleDateString("en-GB", { month: "long", year: "numeric" })
      : "No deadline";
    if (!groups[key]) groups[key] = [];
    groups[key].push(g);
  });

  return (
    <div>
      {Object.entries(groups).map(([month, grants]) => (
        <div key={month} style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.1em", whiteSpace: "nowrap" }}>{month}</div>
            <div style={{ flex: 1, height: 1, background: BORDER }} />
            <span style={{ fontSize: 10, color: "#94A3B8", fontFamily: "monospace" }}>{grants.length}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {grants.map((g) => (
              <TimelineCard
                key={g.id}
                g={g}
                isSaved={isSaved(g)}
                onSave={toggleSave}
                isCompared={compareList.some((c) => c.id === g.id)}
                onCompare={toggleCompare}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function TimelineCard({ g, isSaved, onSave, isCompared, onCompare }) {
  const amount   = fmtAmount(g.funding_amount);
  const deadline = urgencyLabel(g.deadline);
  const ts       = typeStyle(g.funding_type);

  return (
    <Link
      to={`/grants/${g.id}`}
      data-testid={TID.discoveryItem(g.id)}
      style={{
        display: "flex",
        border: `1px solid ${BORDER}`,
        background: "white",
        textDecoration: "none",
        transition: "border-color 150ms",
        overflow: "hidden",
      }}
      onMouseEnter={(e) => e.currentTarget.style.borderColor = NAVY}
      onMouseLeave={(e) => e.currentTarget.style.borderColor = BORDER}
    >
      {/* Deadline column */}
      <div style={{
        width: 84,
        flexShrink: 0,
        background: deadline?.bg || "#F8FAFC",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "12px 8px",
        borderRight: `1px solid ${BORDER}`,
      }}>
        {g.deadline ? (
          <>
            <div style={{ fontSize: 20, fontWeight: 800, color: deadline?.color || "#64748B", fontFamily: "monospace", lineHeight: 1 }}>
              {new Date(g.deadline).getDate()}
            </div>
            <div style={{ fontSize: 10, color: deadline?.color || "#94A3B8", fontWeight: 600, marginTop: 2 }}>
              {new Date(g.deadline).toLocaleDateString("en-GB", { month: "short" })}
            </div>
            {deadline && !deadline.closed && (
              <div style={{ fontSize: 9, color: deadline.color, marginTop: 4, fontWeight: 700 }}>{deadline.text}</div>
            )}
          </>
        ) : (
          <div style={{ fontSize: 9, color: "#94A3B8", textAlign: "center" }}>Rolling</div>
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, padding: "12px 16px", minWidth: 0 }}>
        <div style={{ display: "flex", gap: 6, marginBottom: 5, flexWrap: "wrap" }}>
          {g.funding_type && (
            <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", padding: "1px 5px", background: ts.bg, border: `1px solid ${ts.border}`, color: ts.text }}>
              {g.funding_type}
            </span>
          )}
          {amount && (
            <span style={{ fontSize: 9, fontWeight: 700, color: EMERALD, display: "flex", alignItems: "center", gap: 2 }}>
              <Coins size={9} strokeWidth={1.5} /> {amount}
            </span>
          )}
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 14, color: "#0F172A", lineHeight: 1.35, marginBottom: 3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{g.title}</div>
        <div style={{ fontSize: 11, color: "#64748B" }}>{g.sponsor}{g.country ? ` · ${g.country}` : ""}</div>
      </div>

      {/* Actions */}
      <div
        style={{ width: 76, flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10, padding: 10, borderLeft: `1px solid ${BORDER}` }}
        onClick={(e) => e.preventDefault()}
      >
        <button onClick={(e) => onSave(g, e)} style={{ color: isSaved ? ACCENT : "#CBD5E1", cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: 2, background: "none", border: "none", outline: "none" }}>
          {isSaved ? <BookmarkCheck size={14} strokeWidth={1.5} /> : <Bookmark size={14} strokeWidth={1.5} />}
          <span style={{ fontSize: 9, color: "#94A3B8" }}>{isSaved ? "Saved" : "Save"}</span>
        </button>
        <button onClick={(e) => onCompare(g, e)} style={{ color: isCompared ? NAVY : "#CBD5E1", cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: 2, background: "none", border: "none", outline: "none" }}>
          <BarChart2 size={14} strokeWidth={1.5} />
          <span style={{ fontSize: 9, color: "#94A3B8" }}>Compare</span>
        </button>
      </div>
    </Link>
  );
}

function TimelineSkeleton() {
  return (
    <div style={{ display: "flex", border: `1px solid ${BORDER}`, background: "white", overflow: "hidden" }}>
      <div className="sq-pulse" style={{ width: 84, background: "#F1F5F9", minHeight: 68 }} />
      <div style={{ flex: 1, padding: "12px 16px" }}>
        <div style={{ display: "flex", gap: 5, marginBottom: 8 }}>
          <div className="sq-pulse" style={{ height: 14, width: 70, background: "#F1F5F9" }} />
          <div className="sq-pulse" style={{ height: 14, width: 50, background: "#F1F5F9" }} />
        </div>
        <div className="sq-pulse" style={{ height: 16, width: "75%", background: "#F1F5F9", marginBottom: 6 }} />
        <div className="sq-pulse" style={{ height: 11, width: "45%", background: "#F1F5F9" }} />
      </div>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────
function GrantsEmptyState({ hasFilters }) {
  return (
    <div style={{ textAlign: "center", padding: "60px 24px", border: `1px dashed ${BORDER}` }}>
      <BadgeDollarSign size={44} strokeWidth={1} style={{ color: "#E2E8F0", margin: "0 auto 20px", display: "block" }} />
      <h3 style={{ fontFamily: "Georgia, serif", fontSize: 22, color: "#1E293B", marginBottom: 8, fontWeight: 400 }}>
        {hasFilters ? "No funding opportunities match your search" : "No grants indexed yet"}
      </h3>
      <p style={{ fontSize: 13, color: "#64748B", maxWidth: 420, margin: "0 auto 24px", lineHeight: 1.65 }}>
        {hasFilters
          ? "Try broadening your search or removing some filters. Synaptiq aggregates 7,900+ opportunities from OpenAIRE, NIH, NSF, and Horizon Europe."
          : "Funding opportunities from 40+ international agencies are indexed daily. Check back soon."}
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 300, margin: "0 auto", textAlign: "left" }}>
        {[
          { icon: Lightbulb, text: "Update your research profile for AI matching" },
          { icon: Globe,     text: "Remove country filter for broader results" },
          { icon: Calendar,  text: "Uncheck \"Open calls only\" to see all calls" },
          { icon: Target,    text: "Try searching by sponsor name, e.g. \"ERC\" or \"NIH\"" },
        ].map(({ icon: Icon, text }) => (
          <div key={text} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 12, color: "#64748B" }}>
            <Icon size={12} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0, marginTop: 2 }} />
            {text}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Gated state ───────────────────────────────────────────────────────────────
function GatedState() {
  return (
    <div style={{ textAlign: "center", padding: "60px 24px", border: `1px dashed ${BORDER}` }}>
      <Coins size={44} strokeWidth={1} style={{ color: "#E2E8F0", margin: "0 auto 20px", display: "block" }} />
      <h3 style={{ fontFamily: "Georgia, serif", fontSize: 22, color: "#1E293B", marginBottom: 8, fontWeight: 400 }}>
        Grant discovery limit reached
      </h3>
      <p style={{ fontSize: 13, color: "#64748B", maxWidth: 360, margin: "0 auto 24px", lineHeight: 1.65 }}>
        You've reached your monthly grant discovery quota. Upgrade to access the full funding database of 7,900+ opportunities.
      </p>
      <Link
        to="/settings/billing"
        style={{ padding: "9px 22px", background: NAVY, color: "white", fontSize: 13, fontWeight: 700, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 6 }}
      >
        View plans <ArrowRight size={13} strokeWidth={1.5} />
      </Link>
    </div>
  );
}

// ── Application prep strip ────────────────────────────────────────────────────
function ApplicationPrepStrip() {
  const TOOLS = [
    { label: "Proposal Outline",   desc: "AI-generated structure for any call", to: "/ai",                     icon: FileText },
    { label: "Impact Statement",   desc: "Articulate your research impact",      to: "/ai",                     icon: TrendingUp },
    { label: "Literature Review",  desc: "Situate your work in the field",       to: "/literature-review",      icon: Award },
    { label: "Methodology Review", desc: "Strengthen your approach",             to: "/manuscript-review",      icon: Target },
    { label: "Gap Analysis",       desc: "Identify and frame research gaps",      to: "/research-gap-finder",    icon: Lightbulb },
    { label: "Team Builder",       desc: "Find qualified co-applicants",          to: "/collaboration-intelligence", icon: Users },
  ];

  return (
    <div
      style={{
        margin: "48px -24px 0",
        background: WARM,
        borderTop: `1px solid ${BORDER}`,
        padding: "36px 56px",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 6 }}>Application Preparation</div>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: 26, color: NAVY, fontWeight: 400 }}>Prepare a Competitive Application</h2>
          <p style={{ fontSize: 13, color: "#64748B", marginTop: 6, maxWidth: 480, lineHeight: 1.6 }}>
            Synaptiq AI supports every stage of your funding application — from proposal structure to risk assessment.
          </p>
        </div>
        <Link
          to="/ai"
          style={{ fontSize: 13, fontWeight: 700, color: NAVY, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 6, padding: "9px 18px", border: `1.5px solid ${NAVY}`, alignSelf: "flex-start", whiteSpace: "nowrap" }}
        >
          Open Synaptiq AI <ArrowRight size={13} strokeWidth={2} />
        </Link>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(168px, 1fr))", gap: 12 }}>
        {TOOLS.map(({ label, desc, to, icon: Icon }) => (
          <Link
            key={label}
            to={to}
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 8,
              padding: 16,
              background: "white",
              border: `1px solid ${BORDER}`,
              textDecoration: "none",
              transition: "border-color 150ms, box-shadow 150ms",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY; e.currentTarget.style.boxShadow = "0 2px 8px rgba(15,40,71,0.07)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.boxShadow = "none"; }}
          >
            <Icon size={18} strokeWidth={1.5} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: NAVY, lineHeight: 1.3 }}>{label}</div>
            <div style={{ fontSize: 11, color: "#64748B", lineHeight: 1.5 }}>{desc}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}

// ── Compare panel ─────────────────────────────────────────────────────────────
function ComparePanel({ grants, onRemove, onClose }) {
  const METRICS = [
    { label: "Sponsor",        fn: (g) => g.sponsor || "—" },
    { label: "Funding Type",   fn: (g) => g.funding_type || "—" },
    { label: "Amount",         fn: (g) => fmtAmount(g.funding_amount) || "—" },
    { label: "Country",        fn: (g) => g.country || "International" },
    { label: "Deadline",       fn: (g) => g.deadline ? new Date(g.deadline).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "No deadline" },
    { label: "Duration",       fn: (g) => g.duration || "—" },
    { label: "Research Areas", fn: (g) => (g.research_areas || []).slice(0, 2).join(", ") || "—" },
    { label: "Career Stage",   fn: (g) => g.career_stage?.replace(/_/g, " ") || "—" },
  ];

  return (
    <div
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        background: NAVY,
        color: "white",
        padding: "14px 24px",
        zIndex: 200,
        boxShadow: "0 -8px 32px rgba(0,0,0,0.35)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <BarChart2 size={13} strokeWidth={1.5} style={{ color: "rgba(255,255,255,0.5)" }} />
          <span style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>
            Comparing {grants.length} grants
          </span>
          {grants.length < 3 && (
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.35)" }}>
              (add up to {3 - grants.length} more)
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          style={{ color: "rgba(255,255,255,0.45)", cursor: "pointer", display: "flex", alignItems: "center", gap: 4, fontSize: 12, background: "none", border: "none", outline: "none" }}
        >
          <X size={13} strokeWidth={1.5} /> Close
        </button>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 400 }}>
          <thead>
            <tr>
              <th style={{ width: 110, padding: "4px 12px 4px 0", textAlign: "left", fontSize: 9, color: "rgba(255,255,255,0.35)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", borderBottom: "1px solid rgba(255,255,255,0.1)" }} />
              {grants.map((g) => (
                <th key={g.id} style={{ padding: "4px 14px", textAlign: "left", borderBottom: "1px solid rgba(255,255,255,0.1)", minWidth: 180, verticalAlign: "bottom" }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "white", lineHeight: 1.3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 240 }}>{g.title}</div>
                  <button
                    onClick={() => onRemove(g.id)}
                    style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", cursor: "pointer", marginTop: 3, display: "inline-flex", alignItems: "center", gap: 2, background: "none", border: "none", outline: "none", padding: 0 }}
                  >
                    <X size={8} strokeWidth={1.5} /> Remove
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRICS.map(({ label, fn }) => (
              <tr key={label}>
                <td style={{ padding: "4px 12px 4px 0", fontSize: 9, color: "rgba(255,255,255,0.4)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", whiteSpace: "nowrap", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{label}</td>
                {grants.map((g) => (
                  <td key={g.id} style={{ padding: "4px 14px", fontSize: 11, color: "rgba(255,255,255,0.8)", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{fn(g)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

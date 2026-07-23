import React, { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "@/components/ds";
import { DiscoveryLayout } from "@/layouts";
import { Link, NavLink } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { useAuth } from "../contexts/AuthContext";
import { ACCENT, EMERALD, NAVY, WARM } from "@/lib/tokens";
import {
  Search, X, ChevronDown, ChevronLeft, ChevronRight, ArrowRight,
  CalendarDays, MapPin, Monitor, Wifi, Globe, Clock, Timer,
  Sparkles, AlertCircle, BarChart2, FileText, Award, Target,
  LayoutGrid, List, Building2, TrendingUp, Users, Lightbulb,
  CheckCircle, Zap,
} from "lucide-react";

// ── Design tokens ─────────────────────────────────────────────────────────────
const BORDER  = "#E4E8EF";

// ── Data helpers ──────────────────────────────────────────────────────────────
function daysUntil(dl) {
  if (!dl) return null;
  return Math.round((new Date(dl) - new Date()) / 86_400_000);
}

function urgencyLabel(dl) {
  const d = daysUntil(dl);
  if (d === null)  return null;
  if (d < 0)       return { text: "Closed",     color: "#94A3B8", bg: "#F1F5F9", closed: true };
  if (d === 0)     return { text: "Today",      color: ACCENT,   bg: "#FFF1F2", closed: false };
  if (d <= 7)      return { text: `${d}d left`, color: ACCENT,   bg: "#FFF1F2", closed: false };
  if (d <= 30)     return { text: `${d}d left`, color: "#B45309",bg: "#FFFBEB", closed: false };
  if (d <= 90)     return { text: `${d}d left`, color: "#0369A1",bg: "#F0F9FF", closed: false };
  return {
    text: new Date(dl).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }),
    color: "#64748B", bg: "#F8FAFC", closed: false,
  };
}

function fmtDate(s) {
  if (!s) return null;
  return new Date(s).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function fmtMonth(s) {
  if (!s) return "No deadline";
  return new Date(s).toLocaleDateString("en-GB", { month: "long", year: "numeric" });
}

// CORE Rank styles
const RANK_STYLE = {
  "A*": { bg: "#ECFDF5", border: "#34D399", text: "#065F46" },
  "A":  { bg: "#EFF6FF", border: "#60A5FA", text: "#1E3A8A" },
  "B":  { bg: "#FFFBEB", border: "#FCD34D", text: "#92400E" },
  "C":  { bg: "#F8FAFC", border: "#CBD5E1", text: "#475569" },
};

function rankStyle(r) {
  return r ? (RANK_STYLE[r] || { bg: "#F8FAFC", border: "#CBD5E1", text: "#475569" }) : null;
}

// Format info
const FORMAT_INFO = {
  "in-person": { Icon: MapPin,   label: "In-person", color: "#64748B" },
  "virtual":   { Icon: Monitor,  label: "Virtual",   color: "#3B82F6" },
  "hybrid":    { Icon: Wifi,     label: "Hybrid",    color: "#7C3AED" },
};

function formatInfo(f) {
  return f ? FORMAT_INFO[f] : null;
}

// Deadline state display
const STATE_DISPLAY = {
  open:          { label: "Open",          color: EMERALD,  bg: "#ECFDF5" },
  closing_soon:  { label: "Closing soon",  color: "#B45309", bg: "#FFFBEB" },
  closed:        { label: "Closed",        color: "#94A3B8", bg: "#F1F5F9" },
  unknown:       { label: "No deadline",   color: "#94A3B8", bg: "#F8FAFC" },
};

// ── Constants ─────────────────────────────────────────────────────────────────
const PAGE_SIZE = 24;

const SORT_OPTIONS = [
  { value: "deadline_asc",  label: "Soonest deadline" },
  { value: "deadline_desc", label: "Furthest deadline" },
  { value: "recent",        label: "Recently added" },
  { value: "relevance",     label: "Most relevant" },
];

const FORMAT_OPTIONS = [
  { value: "",           label: "All formats" },
  { value: "in-person",  label: "In-person" },
  { value: "virtual",    label: "Virtual" },
  { value: "hybrid",     label: "Hybrid" },
];

const DEADLINE_STATES = [
  { value: "closing_soon", label: "Closing soon (≤30d)" },
  { value: "open",         label: "Open (>30d)" },
  { value: "closed",       label: "Closed" },
];

const TABS = [
  { to: "/journals",    label: "Journals",         testid: TID.discoveryTabJournals },
  { to: "/conferences", label: "Conferences",       testid: TID.discoveryTabConferences },
  { to: "/grants",      label: "Grants & Funding",  testid: TID.discoveryTabGrants },
];

// ── Main component ────────────────────────────────────────────────────────────
export default function Conferences() {
  const { user } = useAuth();
  const explorerRef = useRef(null);

  // Search / filter state
  const [q,          setQ]          = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [filters,    setFilters]    = useState({});
  const [sort,       setSort]       = useState("deadline_asc");
  const [format,     setFormat]     = useState("");
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

  // Recommendations
  const [recs,        setRecs]        = useState(null);
  const [recsLoading, setRecsLoading] = useState(true);

  // Compare (client-side only — no save API)
  const [compareList, setCompareList] = useState([]);

  // ── Debounce q ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 400);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => { setPage(1); }, [debouncedQ, filters, sort, format]);

  // ── Boot ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    api.get("/discovery/quota").then((r) => setQuota(r.data)).catch(() => {});
    api.get("/conferences/facets").then((r) => setFacets(r.data)).catch(() => {});
    api.get("/recommendations/conferences?limit=8&deadline_state=open")
      .then((r) => {
        const raw = r.data;
        const list = Array.isArray(raw) ? raw : (raw?.results || []);
        setRecs(list.length > 0 ? list : null);
      })
      .catch(() => setRecs(null))
      .finally(() => setRecsLoading(false));
  }, []);

  // ── Fetch conferences ──────────────────────────────────────────────────────
  const filtersKey = JSON.stringify(filters);
  const fetchConferences = useCallback(async () => {
    setLoading(true);
    setGated(false);
    try {
      const params = {
        page,
        page_size: PAGE_SIZE,
        sort,
        ...(debouncedQ            && { q: debouncedQ }),
        ...(format                && { format }),
        ...(filters.research_area && { research_area: filters.research_area }),
        ...(filters.rank          && { rank: filters.rank }),
        ...(filters.country       && { country: filters.country }),
        ...(filters.deadline_state && { deadline_state: filters.deadline_state }),
      };
      const { data } = await api.get("/conferences", { params });
      setItems(data.items || []);
      setTotal(data.total || 0);
      setHasMore(data.has_more || false);
    } catch (err) {
      if (err?.response?.status === 402 || err?.response?.status === 429) setGated(true);
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, sort, debouncedQ, format, filtersKey]);

  useEffect(() => { fetchConferences(); }, [fetchConferences]);

  // Update facets on query change
  useEffect(() => {
    const params = debouncedQ ? { q: debouncedQ } : {};
    api.get("/conferences/facets", { params }).then((r) => setFacets(r.data)).catch(() => {});
  }, [debouncedQ]);

  // ── Compare ────────────────────────────────────────────────────────────────
  const toggleCompare = (c, e) => {
    e.preventDefault();
    e.stopPropagation();
    setCompareList((prev) => {
      if (prev.find((x) => x.id === c.id)) return prev.filter((x) => x.id !== c.id);
      if (prev.length >= 3) return prev; // silently cap
      return [...prev, c];
    });
  };

  // ── Filters ────────────────────────────────────────────────────────────────
  const setFilter = (key, val) => {
    setFilters((prev) => {
      if (!val) { const { [key]: _, ...rest } = prev; return rest; }
      return { ...prev, [key]: val };
    });
  };

  const activeFilterCount = Object.values(filters).filter(Boolean).length + (format ? 1 : 0);
  const hasFilters = activeFilterCount > 0 || !!debouncedQ;

  // Upcoming from current page
  const upcoming = items
    .filter((c) => { const d = daysUntil(c.submission_deadline); return d !== null && d >= 0 && d <= 60; })
    .sort((a, b) => daysUntil(a.submission_deadline) - daysUntil(b.submission_deadline))
    .slice(0, 8);

  return (
    <DiscoveryLayout>
      <style>{`
        @keyframes sq-pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.45; }
        }
        .sq-pulse { animation: sq-pulse 1.8s ease-in-out infinite; }
      `}</style>
      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <HeroHeader
        user={user}
        onExplore={() => explorerRef.current?.scrollIntoView({ behavior: "smooth" })}
      />
      {/* ── Tabs ──────────────────────────────────────────────────────────── */}
      <div style={{ margin: "0 -24px", borderBottom: `1px solid ${BORDER}`, background: "white", display: "flex", paddingLeft: 24 }}>
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
      {/* ── Recommendations ───────────────────────────────────────────────── */}
      {(recsLoading || recs) && (
        <RecsPanel
          recs={recs}
          loading={recsLoading}
          compareList={compareList}
          toggleCompare={toggleCompare}
          user={user}
        />
      )}
      {/* ── Deadline ticker ───────────────────────────────────────────────── */}
      {upcoming.length > 0 && <DeadlineTicker items={upcoming} />}
      {/* ── Explorer ──────────────────────────────────────────────────────── */}
      <div ref={explorerRef} style={{ marginTop: 32, display: "flex", gap: 24, alignItems: "flex-start" }}>

        {/* Facets */}
        <aside style={{ width: 248, flexShrink: 0, position: "sticky", top: 24, maxHeight: "calc(100vh - 80px)", overflowY: "auto" }}>
          <FacetPanel
            facets={facets}
            filters={filters}
            setFilter={setFilter}
            format={format}
            setFormat={setFormat}
          />
        </aside>

        {/* Main */}
        <div style={{ flex: 1, minWidth: 0 }}>

          {/* Search + sort + view */}
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12 }}>
            <div style={{ flex: 1, position: "relative" }}>
              <Search size={14} strokeWidth={1.5} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94A3B8", pointerEvents: "none" }} />
              <input
                data-testid={TID.discoverySearch}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search conferences, acronyms, topics, organizers…"
                style={{ width: "100%", padding: "9px 36px 9px 36px", border: `1px solid ${BORDER}`, background: "white", fontSize: 13, color: "#1E293B", outline: "none", boxSizing: "border-box", transition: "border-color 150ms" }}
                onFocus={(e) => { e.target.style.borderColor = NAVY; }}
                onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
              />
              {q && (
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setQ("")}
                  style={{
                    position: "absolute",
                    right: 10,
                    top: "50%",
                    transform: "translateY(-50%)",
                    color: "#94A3B8",
                    display: "flex",
                    alignItems: "center"
                  }}>
                  <X size={13} strokeWidth={1.5} />
                </Button>
              )}
            </div>

            <select
              data-testid={TID.discoverySortSelect}
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              style={{ padding: "9px 12px", border: `1px solid ${BORDER}`, background: "white", fontSize: 13, color: "#374151", cursor: "pointer", flexShrink: 0, outline: "none" }}
            >
              {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>

            {/* View toggle */}
            <div style={{ display: "flex", border: `1px solid ${BORDER}`, overflow: "hidden", flexShrink: 0 }}>
              {[{ k: "grid", Icon: LayoutGrid }, { k: "timeline", Icon: List }].map(({ k, Icon }) => (
                <button
                  key={k}
                  onClick={() => setView(k)}
                  title={k === "grid" ? "Grid view" : "Timeline view"}
                  style={{ padding: "8px 10px", background: view === k ? NAVY : "white", color: view === k ? "white" : "#64748B", cursor: "pointer", display: "flex", alignItems: "center", borderLeft: k === "timeline" ? `1px solid ${BORDER}` : "none", border: "none", outline: "none" }}
                >
                  <Icon size={14} strokeWidth={1.5} />
                </button>
              ))}
            </div>
          </div>

          {/* Filter chips */}
          {activeFilterCount > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
              {format && <FilterChip label={`Format: ${format}`} onRemove={() => setFormat("")} />}
              {Object.entries(filters).map(([k, v]) => v && (
                <FilterChip key={k} label={`${k.replace(/_/g, " ")}: ${v}`} onRemove={() => setFilter(k, "")} />
              ))}
              <button onClick={() => { setFilters({}); setFormat(""); setQ(""); }} style={{ fontSize: 11, color: "#94A3B8", cursor: "pointer", padding: "3px 8px", background: "none", border: "none", outline: "none", textDecoration: "underline" }}>
                Clear all
              </button>
            </div>
          )}

          {/* Count */}
          {!loading && !gated && (
            <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 16, fontFamily: "monospace" }}>
              {total.toLocaleString()} {hasFilters ? "matching" : "indexed"} conferences
            </div>
          )}

          {/* Content */}
          {gated ? (
            <GatedState />
          ) : view === "timeline" ? (
            <TimelineView items={items} loading={loading} compareList={compareList} toggleCompare={toggleCompare} />
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(270px, 1fr))", gap: 14 }}>
              {loading
                ? Array.from({ length: 9 }).map((_, i) => <ConferenceSkeleton key={i} />)
                : items.map((c) => (
                    <ConferenceCard
                      key={c.id}
                      c={c}
                      isCompared={compareList.some((x) => x.id === c.id)}
                      onCompare={toggleCompare}
                    />
                  ))
              }
            </div>
          )}

          {!loading && !gated && items.length === 0 && <ConferencesEmptyState hasFilters={hasFilters} />}

          {/* Pagination */}
          {!loading && !gated && total > PAGE_SIZE && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 24, paddingTop: 16, borderTop: `1px solid ${BORDER}` }}>
              <button
                data-testid={TID.discoveryPagePrev}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 16px", fontSize: 13, border: `1px solid ${BORDER}`, background: page === 1 ? "#F8FAFC" : "white", color: page === 1 ? "#CBD5E1" : NAVY, cursor: page === 1 ? "not-allowed" : "pointer", outline: "none" }}
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
                style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 16px", fontSize: 13, border: `1px solid ${BORDER}`, background: !hasMore ? "#F8FAFC" : "white", color: !hasMore ? "#CBD5E1" : NAVY, cursor: !hasMore ? "not-allowed" : "pointer", outline: "none" }}
              >
                Next <ChevronRight size={14} strokeWidth={1.5} />
              </button>
            </div>
          )}
        </div>
      </div>
      {/* ── Submission prep strip ────────────────────────────────────────── */}
      <SubmissionPrepStrip />
      {/* ── Compare panel ────────────────────────────────────────────────── */}
      {compareList.length >= 2 && (
        <ComparePanel
          conferences={compareList}
          onRemove={(id) => setCompareList((p) => p.filter((x) => x.id !== id))}
          onClose={() => setCompareList([])}
        />
      )}
    </DiscoveryLayout>
  );
}

// ── Hero ──────────────────────────────────────────────────────────────────────
function HeroHeader({ user, onExplore }) {
  const userField = (user?.research_areas || []).slice(0, 2).join(", ") || "your research";
  const institution = user?.institution || "your institution";

  return (
    <div
      style={{
        margin: "-24px -24px 0",
        background: `linear-gradient(145deg, #0B1E38 0%, ${NAVY} 50%, #163355 100%)`,
        padding: "48px 56px 0",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Grid overlay */}
      <div style={{ position: "absolute", inset: 0, opacity: 0.04, backgroundImage: "linear-gradient(rgba(255,255,255,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.3) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />

      <div style={{ position: "relative" }}>
        {/* Kicker */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#818CF8" }} />
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.45)" }}>
            Academic Conference Intelligence
          </span>
        </div>

        {/* Title */}
        <h1 style={{ fontFamily: "Georgia, serif", fontSize: 46, fontWeight: 400, color: "white", lineHeight: 1.1, marginBottom: 16, maxWidth: 560 }}>
          Discover Academic<br />
          <span style={{ color: "rgba(255,255,255,0.65)", fontSize: 38 }}>Conferences &amp; CFPs</span>
        </h1>

        <p style={{ fontSize: 14, color: "rgba(255,255,255,0.5)", lineHeight: 1.65, maxWidth: 500, marginBottom: 28 }}>
          Track submission windows, acceptance notifications and conference dates worldwide.
          Aggregated from WikiCFP and curated with CORE rankings.
          Matched to <strong style={{ color: "rgba(255,255,255,0.75)" }}>{userField}</strong> at{" "}
          <strong style={{ color: "rgba(255,255,255,0.75)" }}>{institution}</strong>.
        </p>

        {/* CTAs */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 36 }}>
          <button
            onClick={onExplore}
            style={{ padding: "10px 22px", background: "white", color: NAVY, fontSize: 13, fontWeight: 700, border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: 8, outline: "none" }}
          >
            <CalendarDays size={14} strokeWidth={2} />
            Find Best Conference
          </button>
          <Link
            to="/manuscript-review"
            style={{ padding: "10px 22px", background: "transparent", color: "rgba(255,255,255,0.8)", fontSize: 13, fontWeight: 600, border: "1px solid rgba(255,255,255,0.2)", display: "flex", alignItems: "center", gap: 8, textDecoration: "none" }}
          >
            <FileText size={14} strokeWidth={1.5} />
            Prepare Submission
          </Link>
        </div>

        {/* Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 0, borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 20 }}>
          {[
            { Icon: CalendarDays, label: "Active CFPs",     val: "800+" },
            { Icon: Globe,        label: "Countries",       val: "60+" },
            { Icon: Award,        label: "CORE Ranked",     val: "Yes" },
            { Icon: Sparkles,     label: "AI Matched",      val: "Free" },
          ].map(({ Icon, label, val }) => (
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

// ── Recommendations panel ─────────────────────────────────────────────────────
function RecsPanel({ recs, loading, compareList, toggleCompare, user }) {
  const [expanded, setExpanded] = useState(true);
  const hasProfile = !!(user?.research_areas?.length || user?.research_interests?.length);

  return (
    <div style={{ background: `${NAVY}05`, borderBottom: `1px solid ${BORDER}`, padding: "18px 0 20px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: expanded ? 16 : 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <Sparkles size={13} strokeWidth={1.5} style={{ color: NAVY }} />
          <span style={{ fontSize: 12, fontWeight: 700, color: NAVY, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Recommended Conferences
          </span>
          <span style={{ fontSize: 11, color: "#94A3B8" }}>Matched to your research profile</span>
          {!hasProfile && (
            <span style={{ fontSize: 11, color: "#D97706", display: "flex", alignItems: "center", gap: 3 }}>
              <AlertCircle size={11} strokeWidth={1.5} />
              Update profile for better matching
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Link to="/academic-passport" style={{ fontSize: 11, color: "#64748B", textDecoration: "none", display: "flex", alignItems: "center", gap: 3 }}>
            Update profile <ArrowRight size={10} strokeWidth={1.5} />
          </Link>
          <Button
            size="icon"
            variant="ghost"
            onClick={() => setExpanded((v) => !v)}
            style={{
              color: "#94A3B8",
              display: "flex",
              alignItems: "center"
            }}>
            <ChevronDown size={13} strokeWidth={1.5} style={{ transform: expanded ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 200ms ease-out" }} />
          </Button>
        </div>
      </div>
      {expanded && (
        <div style={{ display: "flex", gap: 14, overflowX: "auto", paddingBottom: 4 }}>
          {loading
            ? Array.from({ length: 4 }).map((_, i) => <RecSkeleton key={i} />)
            : (recs || []).slice(0, 7).map((c, i) => (
                <RecCard
                  key={c.id || c._id || i}
                  c={c}
                  isCompared={compareList.some((x) => x.id === (c.id || c._id))}
                  onCompare={toggleCompare}
                />
              ))
          }
        </div>
      )}
    </div>
  );
}

function RecCard({ c, isCompared, onCompare }) {
  const deadline = urgencyLabel(c.submission_deadline);
  const rs = rankStyle(c.rank);
  const fi = formatInfo(c.format);
  const score = c.score;
  const id = c.id || c._id;

  return (
    <Link
      to={`/conferences/${id}`}
      data-testid={TID.discoveryItem(id)}
      style={{ display: "block", minWidth: 240, maxWidth: 280, flexShrink: 0, border: `1px solid ${BORDER}`, background: "white", padding: 16, textDecoration: "none", transition: "border-color 150ms, box-shadow 150ms" }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY; e.currentTarget.style.boxShadow = "0 4px 14px rgba(15,40,71,0.08)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.boxShadow = "none"; }}
    >
      {/* Score + rank row */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        {score != null && (
          <div style={{ width: 34, height: 34, borderRadius: "50%", background: "#EFF6FF", border: "1.5px solid #60A5FA", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <span style={{ fontSize: 10, fontWeight: 800, color: "#1D4ED8", fontFamily: "monospace" }}>{Math.round(score)}</span>
          </div>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          {rs && (
            <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", padding: "2px 5px", background: rs.bg, border: `1px solid ${rs.border}`, color: rs.text }}>
              CORE {c.rank}
            </span>
          )}
        </div>
      </div>

      {/* Acronym + year */}
      {(c.acronym || c.year) && (
        <div style={{ fontSize: 12, fontWeight: 800, color: NAVY, letterSpacing: "0.04em", marginBottom: 4, fontFamily: "monospace" }}>
          {c.acronym} {c.year}
        </div>
      )}

      {/* Name */}
      <div style={{ fontFamily: "Georgia, serif", fontSize: 12, color: "#0F172A", lineHeight: 1.4, marginBottom: 6, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
        {c.name}
      </div>

      {/* Explanation */}
      {c.explanation && (
        <div style={{ fontSize: 10, color: "#94A3B8", fontStyle: "italic", lineHeight: 1.4, marginBottom: 8 }}>
          {c.explanation}
        </div>
      )}

      {/* Meta */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        {deadline && (
          <span style={{ fontSize: 10, fontWeight: 700, color: deadline.color, background: deadline.bg, padding: "1px 5px" }}>
            {deadline.text}
          </span>
        )}
        {fi && (
          <span style={{ fontSize: 10, color: fi.color, display: "flex", alignItems: "center", gap: 2 }}>
            <fi.Icon size={9} strokeWidth={1.5} /> {fi.label}
          </span>
        )}
      </div>
    </Link>
  );
}

function RecSkeleton() {
  return (
    <div style={{ minWidth: 240, maxWidth: 280, flexShrink: 0, border: `1px solid ${BORDER}`, background: "white", padding: 16 }}>
      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        <div className="sq-pulse" style={{ width: 34, height: 34, borderRadius: "50%", background: "#F1F5F9" }} />
        <div className="sq-pulse" style={{ height: 16, width: 60, background: "#F1F5F9", alignSelf: "center" }} />
      </div>
      <div className="sq-pulse" style={{ height: 14, width: "40%", background: "#F1F5F9", marginBottom: 6 }} />
      <div className="sq-pulse" style={{ height: 32, background: "#F1F5F9", marginBottom: 8 }} />
      <div className="sq-pulse" style={{ height: 10, width: "60%", background: "#F1F5F9" }} />
    </div>
  );
}

// ── Deadline ticker ───────────────────────────────────────────────────────────
function DeadlineTicker({ items }) {
  const urgentCount = items.filter((c) => { const d = daysUntil(c.submission_deadline); return d !== null && d <= 30; }).length;

  return (
    <div style={{ background: "#FFFBEB", borderBottom: "1px solid #FCD34D", padding: "7px 0", margin: "0 -24px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, paddingLeft: 24, overflowX: "auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 5, flexShrink: 0 }}>
          <Timer size={11} strokeWidth={1.5} style={{ color: "#B45309" }} />
          <span style={{ fontSize: 11, fontWeight: 700, color: "#B45309", whiteSpace: "nowrap" }}>
            {urgentCount > 0 ? `${urgentCount} deadlines closing soon` : "Upcoming deadlines"}
          </span>
        </div>
        {items.map((c) => {
          const ul = urgencyLabel(c.submission_deadline);
          return ul ? (
            <Link
              key={c.id}
              to={`/conferences/${c.id}`}
              style={{ display: "flex", alignItems: "center", gap: 6, padding: "3px 10px", background: ul.bg, textDecoration: "none", flexShrink: 0, border: `1px solid ${ul.color}22` }}
            >
              <span style={{ fontSize: 10, fontWeight: 700, color: ul.color, whiteSpace: "nowrap" }}>{ul.text}</span>
              <span style={{ fontSize: 10, color: "#94A3B8" }}>·</span>
              {(c.acronym || c.year) && (
                <span style={{ fontSize: 10, color: NAVY, fontWeight: 700, whiteSpace: "nowrap", fontFamily: "monospace" }}>{c.acronym} {c.year}</span>
              )}
              <span style={{ fontSize: 10, color: "#374151", maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {!c.acronym && c.name}
              </span>
            </Link>
          ) : null;
        })}
      </div>
    </div>
  );
}

// ── Facet panel ───────────────────────────────────────────────────────────────
function FacetPanel({ facets, filters, setFilter, format, setFormat }) {
  const [open, setOpen] = useState({ research_areas: true, rank: true, deadline_state: false, countries: false });
  const toggle = (k) => setOpen((p) => ({ ...p, [k]: !p[k] }));

  function FGroup({ title, sk, fk, items, fmtLabel }) {
    const isOpen = open[sk];
    const active = filters[fk];
    return (
      <div style={{ borderBottom: `1px solid ${BORDER}`, paddingBottom: 10, marginBottom: 10 }}>
        <button onClick={() => toggle(sk)} style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: isOpen ? 8 : 0, cursor: "pointer", background: "none", border: "none", outline: "none", padding: 0 }}>
          <span style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.1em" }}>{title}</span>
          <ChevronDown size={11} strokeWidth={1.5} style={{ color: "#94A3B8", transform: isOpen ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 150ms" }} />
        </button>
        {isOpen && (items || []).slice(0, 12).map((f) => (
          <button
            key={f._id}
            data-testid={TID.discoveryFacet(fk, f._id)}
            onClick={() => setFilter(fk, active === f._id ? "" : f._id)}
            style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "4px 0", cursor: "pointer", background: "none", border: "none", outline: "none", textAlign: "left" }}
          >
            <span style={{ fontSize: 12, color: active === f._id ? NAVY : "#64748B", fontWeight: active === f._id ? 700 : 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 160 }}>
              {active === f._id && "✓ "}{fmtLabel ? fmtLabel(f._id) : f._id}
            </span>
            <span style={{ fontSize: 10, color: "#94A3B8", fontFamily: "monospace", flexShrink: 0, marginLeft: 4 }}>{f.count}</span>
          </button>
        ))}
      </div>
    );
  }

  const DEADLINE_LABEL = { open: "Open (>30d)", closing_soon: "Closing soon (≤30d)", closed: "Closed", unknown: "No deadline" };

  return (
    <div style={{ padding: "4px 0" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 14 }}>Filters</div>

      {/* Format */}
      <div style={{ borderBottom: `1px solid ${BORDER}`, paddingBottom: 12, marginBottom: 12 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Format</div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {FORMAT_OPTIONS.map((fo) => (
            <button
              key={fo.value}
              onClick={() => setFormat(fo.value === format ? "" : fo.value)}
              style={{
                fontSize: 11,
                fontWeight: 600,
                padding: "4px 10px",
                border: `1px solid ${fo.value === format ? NAVY : BORDER}`,
                background: fo.value === format ? NAVY : "white",
                color: fo.value === format ? "white" : "#64748B",
                cursor: "pointer",
                outline: "none",
              }}
            >
              {fo.label}
            </button>
          ))}
        </div>
      </div>

      <FGroup title="Research Area"   sk="research_areas"  fk="research_area"   items={facets.research_areas} />
      <FGroup title="CORE Rank"       sk="rank"            fk="rank"            items={facets.rank} />
      <FGroup title="Deadline Status" sk="deadline_state"  fk="deadline_state"  items={facets.deadline_state} fmtLabel={(v) => DEADLINE_LABEL[v] || v} />
      <FGroup title="Country"         sk="countries"       fk="country"         items={facets.countries} />
    </div>
  );
}

// ── Conference card ───────────────────────────────────────────────────────────
function ConferenceCard({ c, isCompared, onCompare }) {
  const deadline = urgencyLabel(c.submission_deadline);
  const rs = rankStyle(c.rank);
  const fi = formatInfo(c.format);
  const stateDisplay = STATE_DISPLAY[c.deadline_state || "unknown"];
  const d = daysUntil(c.submission_deadline);

  return (
    <Link
      to={`/conferences/${c.id}`}
      data-testid={TID.discoveryItem(c.id)}
      style={{
        display: "flex",
        flexDirection: "column",
        border: `1px solid ${BORDER}`,
        background: "white",
        textDecoration: "none",
        transition: "border-color 150ms, box-shadow 150ms, transform 150ms",
        overflow: "hidden",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY; e.currentTarget.style.boxShadow = "0 4px 16px rgba(15,40,71,0.09)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "translateY(0)"; }}
    >
      {/* Urgency strip */}
      {deadline && !deadline.closed && d !== null && d <= 30 && (
        <div style={{ height: 2, background: deadline.color }} />
      )}

      <div style={{ padding: "14px 16px", flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Header row */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8, marginBottom: 8 }}>
          <div style={{ display: "flex", gap: 5, flexWrap: "wrap", flex: 1 }}>
            {/* Deadline state badge */}
            {stateDisplay && (
              <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: stateDisplay.bg, color: stateDisplay.color, flexShrink: 0 }}>
                {stateDisplay.label}
              </span>
            )}
            {/* CORE rank */}
            {rs && (
              <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", padding: "2px 5px", background: rs.bg, border: `1px solid ${rs.border}`, color: rs.text, flexShrink: 0 }}>
                CORE {c.rank}
              </span>
            )}
          </div>
          {/* Format badge */}
          {fi && (
            <span style={{ fontSize: 9, color: fi.color, display: "flex", alignItems: "center", gap: 2, flexShrink: 0 }}>
              <fi.Icon size={9} strokeWidth={1.5} /> {fi.label}
            </span>
          )}
        </div>

        {/* Acronym + year */}
        {(c.acronym || c.year) && (
          <div style={{ fontSize: 14, fontWeight: 800, color: NAVY, letterSpacing: "0.03em", marginBottom: 3, fontFamily: "monospace" }}>
            {c.acronym} {c.year}
          </div>
        )}

        {/* Full name */}
        <h3 style={{ fontFamily: "Georgia, serif", fontSize: 13, color: "#0F172A", lineHeight: 1.4, marginBottom: 8, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {c.name}
        </h3>

        {/* Submission deadline */}
        {c.submission_deadline && (
          <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 5 }}>
            <Clock size={10} strokeWidth={1.5} style={{ color: deadline?.color || "#94A3B8", flexShrink: 0 }} />
            <span style={{ fontSize: 11, color: "#374151" }}>
              Submit by <strong style={{ color: deadline?.color || "#1E293B" }}>{fmtDate(c.submission_deadline)}</strong>
            </span>
          </div>
        )}

        {/* Location */}
        {c.location && (
          <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 5 }}>
            <MapPin size={10} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0 }} />
            <span style={{ fontSize: 11, color: "#64748B", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.location}</span>
          </div>
        )}

        {/* Conference dates */}
        {c.start_date && (
          <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 8 }}>
            <CalendarDays size={10} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0 }} />
            <span style={{ fontSize: 11, color: "#64748B" }}>
              {fmtDate(c.start_date)}{c.end_date ? ` → ${fmtDate(c.end_date)}` : ""}
            </span>
          </div>
        )}

        {/* Topics */}
        {(c.topics || []).length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
            {c.topics.slice(0, 4).map((t, i) => (
              <span key={i} style={{ fontSize: 9, color: "#64748B", background: "#F8FAFC", border: `1px solid ${BORDER}`, padding: "2px 5px" }}>{t}</span>
            ))}
            {c.topics.length > 4 && <span style={{ fontSize: 9, color: "#94A3B8" }}>+{c.topics.length - 4}</span>}
          </div>
        )}

        <div style={{ flex: 1 }} />
      </div>

      {/* Card footer */}
      <div
        style={{ borderTop: `1px solid ${BORDER}`, padding: "7px 16px", display: "flex", gap: 10, background: "#FAFBFC", alignItems: "center" }}
        onClick={(e) => e.preventDefault()}
      >
        <button
          onClick={(e) => onCompare(c, e)}
          style={{ fontSize: 10, fontWeight: 600, color: isCompared ? NAVY : "#94A3B8", cursor: "pointer", display: "flex", alignItems: "center", gap: 3, background: "none", border: "none", outline: "none", textDecoration: isCompared ? "underline" : "none", padding: 0 }}
        >
          <BarChart2 size={10} strokeWidth={1.5} /> {isCompared ? "Comparing" : "Compare"}
        </button>
        <span style={{ color: "#E2E8F0" }}>|</span>
        <Link to="/ai/abstract" onClick={(e) => e.stopPropagation()} style={{ fontSize: 10, fontWeight: 600, color: "#94A3B8", display: "flex", alignItems: "center", gap: 3, textDecoration: "none" }}>
          <Sparkles size={10} strokeWidth={1.5} /> Abstract
        </Link>
        <span style={{ color: "#E2E8F0" }}>|</span>
        <Link to="/manuscript-review" onClick={(e) => e.stopPropagation()} style={{ fontSize: 10, fontWeight: 600, color: "#94A3B8", display: "flex", alignItems: "center", gap: 3, textDecoration: "none" }}>
          <FileText size={10} strokeWidth={1.5} /> Review
        </Link>
      </div>
    </Link>
  );
}

function ConferenceSkeleton() {
  return (
    <div style={{ border: `1px solid ${BORDER}`, background: "white" }}>
      <div style={{ padding: "14px 16px" }}>
        <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
          <div className="sq-pulse" style={{ height: 16, width: 70, background: "#F1F5F9" }} />
          <div className="sq-pulse" style={{ height: 16, width: 55, background: "#F1F5F9" }} />
        </div>
        <div className="sq-pulse" style={{ height: 16, width: "40%", background: "#F1F5F9", marginBottom: 6 }} />
        <div className="sq-pulse" style={{ height: 32, background: "#F1F5F9", marginBottom: 10 }} />
        <div className="sq-pulse" style={{ height: 11, width: "70%", background: "#F1F5F9", marginBottom: 6 }} />
        <div className="sq-pulse" style={{ height: 11, width: "55%", background: "#F1F5F9", marginBottom: 6 }} />
        <div className="sq-pulse" style={{ height: 11, width: "60%", background: "#F1F5F9", marginBottom: 12 }} />
        <div style={{ display: "flex", gap: 4 }}>
          {[50, 45, 60].map((w, i) => <div key={i} className="sq-pulse" style={{ height: 17, width: w, background: "#F1F5F9" }} />)}
        </div>
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
      <button onClick={onRemove} style={{ display: "flex", alignItems: "center", color: "#94A3B8", cursor: "pointer", marginLeft: 2, background: "none", border: "none", outline: "none" }}>
        <X size={10} strokeWidth={2} />
      </button>
    </div>
  );
}

// ── Timeline view ─────────────────────────────────────────────────────────────
function TimelineView({ items, loading, compareList, toggleCompare }) {
  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {Array.from({ length: 6 }).map((_, i) => <TimelineSkeleton key={i} />)}
      </div>
    );
  }
  if (!items.length) return null;

  // Group by submission deadline month
  const groups = {};
  items.forEach((c) => {
    const key = fmtMonth(c.submission_deadline);
    if (!groups[key]) groups[key] = [];
    groups[key].push(c);
  });

  return (
    <div>
      {Object.entries(groups).map(([month, confs]) => (
        <div key={month} style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.1em", whiteSpace: "nowrap" }}>
              Submit by {month}
            </div>
            <div style={{ flex: 1, height: 1, background: BORDER }} />
            <span style={{ fontSize: 10, color: "#94A3B8", fontFamily: "monospace" }}>{confs.length}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {confs.map((c) => (
              <TimelineCard
                key={c.id}
                c={c}
                isCompared={compareList.some((x) => x.id === c.id)}
                onCompare={toggleCompare}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function TimelineCard({ c, isCompared, onCompare }) {
  const deadline = urgencyLabel(c.submission_deadline);
  const rs = rankStyle(c.rank);
  const fi = formatInfo(c.format);

  return (
    <Link
      to={`/conferences/${c.id}`}
      data-testid={TID.discoveryItem(c.id)}
      style={{ display: "flex", border: `1px solid ${BORDER}`, background: "white", textDecoration: "none", transition: "border-color 150ms", overflow: "hidden" }}
      onMouseEnter={(e) => e.currentTarget.style.borderColor = NAVY}
      onMouseLeave={(e) => e.currentTarget.style.borderColor = BORDER}
    >
      {/* Date column */}
      <div style={{ width: 84, flexShrink: 0, background: deadline?.bg || "#F8FAFC", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "12px 8px", borderRight: `1px solid ${BORDER}` }}>
        {c.submission_deadline ? (
          <>
            <div style={{ fontSize: 20, fontWeight: 800, color: deadline?.color || "#64748B", fontFamily: "monospace", lineHeight: 1 }}>
              {new Date(c.submission_deadline).getDate()}
            </div>
            <div style={{ fontSize: 10, color: deadline?.color || "#94A3B8", fontWeight: 600, marginTop: 2 }}>
              {new Date(c.submission_deadline).toLocaleDateString("en-GB", { month: "short" })}
            </div>
            {deadline && !deadline.closed && (
              <div style={{ fontSize: 9, color: deadline.color, marginTop: 4, fontWeight: 700 }}>{deadline.text}</div>
            )}
          </>
        ) : (
          <div style={{ fontSize: 9, color: "#94A3B8", textAlign: "center", lineHeight: 1.4 }}>No deadline</div>
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, padding: "12px 16px", minWidth: 0 }}>
        <div style={{ display: "flex", gap: 5, marginBottom: 5, flexWrap: "wrap", alignItems: "center" }}>
          {(c.acronym || c.year) && (
            <span style={{ fontSize: 12, fontWeight: 800, color: NAVY, fontFamily: "monospace" }}>{c.acronym} {c.year}</span>
          )}
          {rs && <span style={{ fontSize: 9, fontWeight: 700, padding: "1px 5px", background: rs.bg, border: `1px solid ${rs.border}`, color: rs.text }}>CORE {c.rank}</span>}
          {fi && <span style={{ fontSize: 9, color: fi.color, display: "flex", alignItems: "center", gap: 2 }}><fi.Icon size={9} strokeWidth={1.5} />{fi.label}</span>}
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 13, color: "#0F172A", lineHeight: 1.35, marginBottom: 3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.name}</div>
        <div style={{ fontSize: 11, color: "#64748B" }}>
          {c.location && <span>{c.location}</span>}
          {c.start_date && <span style={{ marginLeft: c.location ? 8 : 0 }}>{fmtDate(c.start_date)}{c.end_date ? ` – ${fmtDate(c.end_date)}` : ""}</span>}
        </div>
      </div>

      {/* Actions */}
      <div style={{ width: 76, flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10, padding: 10, borderLeft: `1px solid ${BORDER}` }} onClick={(e) => e.preventDefault()}>
        <button
          onClick={(e) => onCompare(c, e)}
          style={{ color: isCompared ? NAVY : "#CBD5E1", cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: 2, background: "none", border: "none", outline: "none" }}
        >
          <BarChart2 size={14} strokeWidth={1.5} />
          <span style={{ fontSize: 9, color: "#94A3B8" }}>Compare</span>
        </button>
        <Link
          to="/ai"
          onClick={(e) => e.stopPropagation()}
          style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2, color: "#CBD5E1", textDecoration: "none" }}
        >
          <Sparkles size={14} strokeWidth={1.5} />
          <span style={{ fontSize: 9, color: "#94A3B8" }}>Prepare</span>
        </Link>
      </div>
    </Link>
  );
}

function TimelineSkeleton() {
  return (
    <div style={{ display: "flex", border: `1px solid ${BORDER}`, background: "white", overflow: "hidden" }}>
      <div className="sq-pulse" style={{ width: 84, background: "#F1F5F9", minHeight: 72 }} />
      <div style={{ flex: 1, padding: "12px 16px" }}>
        <div style={{ display: "flex", gap: 5, marginBottom: 8 }}>
          <div className="sq-pulse" style={{ height: 14, width: 60, background: "#F1F5F9" }} />
          <div className="sq-pulse" style={{ height: 14, width: 50, background: "#F1F5F9" }} />
        </div>
        <div className="sq-pulse" style={{ height: 16, width: "70%", background: "#F1F5F9", marginBottom: 6 }} />
        <div className="sq-pulse" style={{ height: 11, width: "40%", background: "#F1F5F9" }} />
      </div>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────
function ConferencesEmptyState({ hasFilters }) {
  return (
    <div style={{ textAlign: "center", padding: "60px 24px", border: `1px dashed ${BORDER}` }}>
      <CalendarDays size={44} strokeWidth={1} style={{ color: "#E2E8F0", margin: "0 auto 20px", display: "block" }} />
      <h3 style={{ fontFamily: "Georgia, serif", fontSize: 22, color: "#1E293B", marginBottom: 8, fontWeight: 400 }}>
        {hasFilters ? "No conferences match your search" : "No conferences indexed yet"}
      </h3>
      <p style={{ fontSize: 13, color: "#64748B", maxWidth: 420, margin: "0 auto 24px", lineHeight: 1.65 }}>
        {hasFilters
          ? "Try removing a filter or broadening your search. The index covers 800+ active calls for papers across all disciplines, aggregated from WikiCFP."
          : "Conference calls for papers are indexed continuously. Check back soon or update your profile for personalized recommendations."}
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 320, margin: "0 auto", textAlign: "left" }}>
        {[
          { Icon: Target,    text: "Remove the deadline status filter to see all conferences" },
          { Icon: Globe,     text: "Remove country filter for global results" },
          { Icon: Lightbulb, text: "Update your research profile for AI-matched recommendations" },
          { Icon: FileText,  text: "Try searching by acronym, e.g. \"ICML\", \"NeurIPS\", \"AAAI\"" },
        ].map(({ Icon, text }) => (
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
      <CalendarDays size={44} strokeWidth={1} style={{ color: "#E2E8F0", margin: "0 auto 20px", display: "block" }} />
      <h3 style={{ fontFamily: "Georgia, serif", fontSize: 22, color: "#1E293B", marginBottom: 8, fontWeight: 400 }}>Conference discovery limit reached</h3>
      <p style={{ fontSize: 13, color: "#64748B", maxWidth: 360, margin: "0 auto 24px", lineHeight: 1.65 }}>
        You've reached your monthly conference discovery quota. Upgrade to access the full index of 800+ active calls for papers.
      </p>
      <Link to="/settings/billing" style={{ padding: "9px 22px", background: NAVY, color: "white", fontSize: 13, fontWeight: 700, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 6 }}>
        View plans <ArrowRight size={13} strokeWidth={1.5} />
      </Link>
    </div>
  );
}

// ── Submission prep strip ─────────────────────────────────────────────────────
function SubmissionPrepStrip() {
  const TOOLS = [
    { label: "Abstract Generator",  desc: "Draft a conference-ready abstract",      to: "/ai/abstract",       icon: Sparkles },
    { label: "Manuscript Review",   desc: "AI review before submission",            to: "/manuscript-review", icon: FileText },
    { label: "Rewriting",           desc: "Sharpen your academic writing",          to: "/ai/rewrite",        icon: Zap },
    { label: "Literature Review",   desc: "Situate your contribution",              to: "/literature-review", icon: Award },
    { label: "Collab Intelligence", desc: "Find co-authors and collaborators",      to: "/collaboration-intelligence", icon: Users },
    { label: "Research Gaps",       desc: "Identify novelty and originality",       to: "/research-gap-finder", icon: Target },
  ];

  return (
    <div style={{ margin: "48px -24px 0", background: WARM, borderTop: `1px solid ${BORDER}`, padding: "36px 56px" }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 6 }}>Submission Preparation</div>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: 26, color: NAVY, fontWeight: 400 }}>Prepare a Competitive Submission</h2>
          <p style={{ fontSize: 13, color: "#64748B", marginTop: 6, maxWidth: 480, lineHeight: 1.6 }}>
            Synaptiq AI supports every stage of your conference submission — abstract to reviewer response.
          </p>
        </div>
        <Link to="/ai" style={{ fontSize: 13, fontWeight: 700, color: NAVY, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 6, padding: "9px 18px", border: `1.5px solid ${NAVY}`, alignSelf: "flex-start", whiteSpace: "nowrap" }}>
          Open Synaptiq AI <ArrowRight size={13} strokeWidth={2} />
        </Link>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(168px, 1fr))", gap: 12 }}>
        {TOOLS.map(({ label, desc, to, icon: Icon }) => (
          <Link
            key={label}
            to={to}
            style={{ display: "flex", flexDirection: "column", gap: 8, padding: 16, background: "white", border: `1px solid ${BORDER}`, textDecoration: "none", transition: "border-color 150ms, box-shadow 150ms" }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY; e.currentTarget.style.boxShadow = "0 2px 8px rgba(15,40,71,0.07)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.boxShadow = "none"; }}
          >
            <Icon size={18} strokeWidth={1.5} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: NAVY }}>{label}</div>
            <div style={{ fontSize: 11, color: "#64748B", lineHeight: 1.5 }}>{desc}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}

// ── Compare panel ─────────────────────────────────────────────────────────────
function ComparePanel({ conferences, onRemove, onClose }) {
  const METRICS = [
    { label: "Acronym",      fn: (c) => `${c.acronym || "—"} ${c.year || ""}`.trim() },
    { label: "CORE Rank",    fn: (c) => c.rank ? `CORE ${c.rank}` : "—" },
    { label: "Format",       fn: (c) => c.format || "—" },
    { label: "Location",     fn: (c) => c.location || "—" },
    { label: "Country",      fn: (c) => c.country || "—" },
    { label: "Submit by",    fn: (c) => fmtDate(c.submission_deadline) || "No deadline" },
    { label: "Conf. dates",  fn: (c) => c.start_date ? `${fmtDate(c.start_date)}${c.end_date ? ` – ${fmtDate(c.end_date)}` : ""}` : "—" },
    { label: "Status",       fn: (c) => STATE_DISPLAY[c.deadline_state || "unknown"]?.label || "—" },
    { label: "Research",     fn: (c) => (c.research_areas || []).slice(0, 2).join(", ") || "—" },
  ];

  return (
    <div style={{ position: "fixed", bottom: 0, left: 0, right: 0, background: NAVY, color: "white", padding: "14px 24px", zIndex: 200, boxShadow: "0 -8px 32px rgba(0,0,0,0.35)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <BarChart2 size={13} strokeWidth={1.5} style={{ color: "rgba(255,255,255,0.5)" }} />
          <span style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>
            Comparing {conferences.length} conferences
          </span>
        </div>
        <button onClick={onClose} style={{ color: "rgba(255,255,255,0.45)", cursor: "pointer", display: "flex", alignItems: "center", gap: 4, fontSize: 12, background: "none", border: "none", outline: "none" }}>
          <X size={13} strokeWidth={1.5} /> Close
        </button>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 400 }}>
          <thead>
            <tr>
              <th style={{ width: 90, padding: "4px 12px 4px 0", textAlign: "left", fontSize: 9, color: "rgba(255,255,255,0.35)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", borderBottom: "1px solid rgba(255,255,255,0.1)" }} />
              {conferences.map((c) => (
                <th key={c.id} style={{ padding: "4px 14px", textAlign: "left", borderBottom: "1px solid rgba(255,255,255,0.1)", minWidth: 180 }}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: "white", fontFamily: "monospace" }}>{c.acronym} {c.year}</div>
                  <button onClick={() => onRemove(c.id)} style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 2, background: "none", border: "none", outline: "none", padding: 0, marginTop: 2 }}>
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
                {conferences.map((c) => (
                  <td key={c.id} style={{ padding: "4px 14px", fontSize: 11, color: "rgba(255,255,255,0.8)", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{fn(c)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

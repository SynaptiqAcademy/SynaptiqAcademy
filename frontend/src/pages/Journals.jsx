import React, { useEffect, useMemo, useState, useRef } from "react";
import { DiscoveryLayout } from "@/layouts";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import SavedSearchControls from "../components/discovery/SavedSearchControls";
import { NAVY, WARM } from "@/lib/tokens";
import {
  Search, X, ChevronLeft, ChevronRight, Lock,
  BookOpen, Globe, ExternalLink, Scale, ArrowRight,
  ChevronDown, ChevronUp, Clock, CheckCircle2,
  Zap, Award, Target, Eye, Gauge, Sparkles, TrendingUp,
} from "lucide-react";

// ─── Brand tokens ─────────────────────────────────────────────────────────────
const BORDER = "#E4E8EF";

// ─── Static data ──────────────────────────────────────────────────────────────
const SORT_OPTIONS = [
  { value: "popularity", label: "Most popular" },
  { value: "works",      label: "Most published" },
  { value: "citations",  label: "Most cited" },
  { value: "recent",     label: "Recently updated" },
  { value: "relevance",  label: "Relevance" },
];

const FILTER_DEFS = [
  { key: "subject",     facetKey: "subjects",    label: "Research field" },
  { key: "quartile",    facetKey: "quartile",    label: "Quartile" },
  { key: "publisher",   facetKey: "publishers",  label: "Publisher" },
  { key: "country",     facetKey: "countries",   label: "Country" },
  { key: "open_access", facetKey: "open_access", label: "Open Access", fmt: (v) => (v ? "Open Access" : "Subscription") },
];

const Q_STYLE = {
  Q1: { bg: "#ECFDF5", border: "#34D399", text: "#065F46" },
  Q2: { bg: "#EFF6FF", border: "#60A5FA", text: "#1E3A8A" },
  Q3: { bg: "#FFFBEB", border: "#FCD34D", text: "#92400E" },
  Q4: { bg: "#F8FAFC", border: "#94A3B8", text: "#475569" },
};

const SRC_LABEL = { openalex: "OpenAlex", doaj: "DOAJ", crossref: "Crossref", seed: "Curated" };

const CATEGORY_COLORS = [
  { bg: "#EFF6FF", text: "#1E3A8A" },
  { bg: "#F0FDF4", text: "#14532D" },
  { bg: "#FFF7ED", text: "#7C2D12" },
  { bg: "#FDF4FF", text: "#581C87" },
  { bg: "#ECFDF5", text: "#064E3B" },
  { bg: "#FFFBEB", text: "#78350F" },
  { bg: "#FFF1F2", text: "#881337" },
  { bg: "#F0F9FF", text: "#0C4A6E" },
  { bg: "#F7F8FA", text: "#374151" },
  { bg: "#FEF9C3", text: "#713F12" },
];

const COMPARE_ROWS = [
  { label: "Publisher",        fmt: (j) => j.publisher || "—" },
  { label: "Quartile",         fmt: (j) => j.quartile || "—" },
  { label: "Open Access",      fmt: (j) => j.open_access ? "Yes" : "No" },
  { label: "Works published",  fmt: (j) => (j.works_count || 0).toLocaleString() },
  { label: "Total citations",  fmt: (j) => (j.cited_by_count || 0).toLocaleString() },
  { label: "h-index",          fmt: (j) => j.h_index || "—" },
  { label: "APC (USD)",        fmt: (j) => j.apc_usd ? `$${j.apc_usd.toLocaleString()}` : "—" },
  { label: "Review time",      fmt: (j) => j.review_time_weeks ? `${j.review_time_weeks} weeks` : "—" },
  { label: "Acceptance rate",  fmt: (j) => j.acceptance_rate ? `${j.acceptance_rate}%` : "—" },
  { label: "Country",          fmt: (j) => j.country || "—" },
];

// ─── Main Component ───────────────────────────────────────────────────────────
export default function Journals() {
  const searchRef = useRef(null);

  const [q, setQ]             = useState("");
  const [filters, setFilters] = useState({});
  const [sort, setSort]       = useState("popularity");
  const [page, setPage]       = useState(1);
  const [items, setItems]     = useState([]);
  const [total, setTotal]     = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [facets, setFacets]   = useState({});
  const [gated, setGated]     = useState(false);
  const [quota, setQuota]     = useState(null);
  const [compareList, setCompareList] = useState([]);
  const [showCompare, setShowCompare] = useState(false);
  const [recs, setRecs]               = useState(null);
  const [recsLoading, setRecsLoading] = useState(true);

  const params = useMemo(() => {
    const p = { q: q || undefined, sort, page, page_size: 24, ...filters };
    Object.keys(p).forEach((k) => { if (p[k] === undefined || p[k] === null || p[k] === "") delete p[k]; });
    return p;
  }, [q, sort, page, filters]);

  useEffect(() => {
    api.get("/discovery/quota")
      .then(({ data }) => {
        const qk = data?.quota?.journal;
        if (qk && qk.limit !== null) setQuota(qk);
      })
      .catch(() => {});

    setRecsLoading(true);
    api.get("/recommendations/journals", { params: { limit: 5 } })
      .then(({ data }) => {
        const results = data?.results || [];
        setRecs(results.length > 0 ? results : null);
      })
      .catch(() => setRecs(null))
      .finally(() => setRecsLoading(false));
  }, []);

  useEffect(() => {
    let abort = false;
    setLoading(true);
    api.get("/journals", { params })
      .then(({ data }) => {
        if (abort) return;
        setItems(data.items || []); setTotal(data.total || 0); setHasMore(!!data.has_more);
      })
      .catch((err) => {
        if (abort) return;
        if (err?.response?.status === 402) setGated(true);
        else { setItems([]); setTotal(0); }
      })
      .finally(() => { if (!abort) setLoading(false); });
    return () => { abort = true; };
  }, [params]);

  useEffect(() => {
    if (gated) return;
    api.get("/journals/facets", { params: { q: q || undefined } })
      .then(({ data }) => setFacets(data || {}))
      .catch(() => setFacets({}));
  }, [q, gated]);

  const setFilter = (key, value) => {
    setFilters((f) => { const nx = { ...f }; if (value == null) delete nx[key]; else nx[key] = value; return nx; });
    setPage(1);
  };
  const clearAll = () => { setFilters({}); setQ(""); setPage(1); };
  const activeCount = Object.keys(filters).length + (q ? 1 : 0);

  const toggleCompare = (j) => {
    setCompareList((prev) => {
      if (prev.some((c) => c.id === j.id)) return prev.filter((c) => c.id !== j.id);
      if (prev.length >= 3) return prev;
      return [...prev, j];
    });
    setShowCompare(true);
  };

  const focusSearch = () => {
    searchRef.current?.focus();
    searchRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const tabLinks = [
    { to: "/journals",    label: "Journals",    testid: TID.discoveryTabJournals,    active: true },
    { to: "/conferences", label: "Conferences", testid: TID.discoveryTabConferences, active: false },
    { to: "/grants",      label: "Grants",      testid: TID.discoveryTabGrants,      active: false },
  ];

  if (gated) return <GatedState tabLinks={tabLinks} />;

  return (
    <DiscoveryLayout>
      <style>{`@keyframes jpulse{0%,100%{opacity:1}50%{opacity:.4}}`}</style>

      {/* ── HERO HEADER (full-bleed navy) ─────────────────────────────── */}
      <div style={{ margin: "-24px -24px 0", background: NAVY }}>
        {/* Tab navigation row */}
        <div style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", padding: "0 24px" }}>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.22)", marginRight: "auto" }}>
            Discovery Suite
          </span>
          {tabLinks.map(({ to, label, testid, active }) => (
            <Link
              key={to}
              to={to}
              data-testid={testid}
              style={{
                display: "block", padding: "14px 20px",
                fontSize: 13, fontWeight: active ? 600 : 400,
                color: active ? "white" : "rgba(255,255,255,0.45)",
                textDecoration: "none",
                borderBottom: `2px solid ${active ? "white" : "transparent"}`,
                transition: "color 0.12s",
              }}
            >
              {label}
            </Link>
          ))}
        </div>

        {/* Hero content */}
        <div style={{ padding: "30px 24px 26px", display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 20, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.3)", marginBottom: 8 }}>
              Academic Publishing Intelligence
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 700, color: "white", margin: 0, letterSpacing: "-0.025em", lineHeight: 1.2 }}>
              Discover Academic Journals
            </h1>
            <p style={{ color: "rgba(255,255,255,0.48)", fontSize: 13, margin: "8px 0 0", maxWidth: 520, lineHeight: 1.65 }}>
              9,000+ journals indexed from OpenAlex, Crossref, and DOAJ — with quartile rankings,
              open access status, impact metrics, and subject coverage.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
            <button
              onClick={focusSearch}
              style={{ background: "white", color: NAVY, padding: "9px 18px", fontSize: 12, fontWeight: 700, border: "none", cursor: "pointer" }}
            >
              Find Best Journal
            </button>
            <button
              onClick={() => setShowCompare((s) => !s)}
              style={{
                background: compareList.length > 0 ? "rgba(255,255,255,0.18)" : "rgba(255,255,255,0.08)",
                color: "white", padding: "9px 16px", fontSize: 12, fontWeight: 500,
                border: "1px solid rgba(255,255,255,0.2)", cursor: "pointer",
              }}
            >
              <Scale size={12} strokeWidth={1.5} style={{ display: "inline", marginRight: 5, verticalAlign: "middle" }} />
              Compare{compareList.length > 0 ? ` (${compareList.length})` : ""}
            </button>
          </div>
        </div>
      </div>

      {/* ── STICKY SEARCH + SORT BAR ───────────────────────────────────── */}
      <div style={{
        margin: "0 -24px",
        padding: "12px 24px",
        background: "white",
        borderBottom: `1px solid ${BORDER}`,
        position: "sticky", top: 0, zIndex: 20,
        boxShadow: "0 2px 10px rgba(0,0,0,0.055)",
      }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {/* Search */}
          <div style={{ flex: 1, position: "relative" }}>
            <Search size={14} strokeWidth={1.5} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "#94A3B8", pointerEvents: "none" }} />
            <input
              ref={searchRef}
              data-testid={TID.discoverySearch}
              value={q}
              onChange={(e) => { setQ(e.target.value); setPage(1); }}
              placeholder="Search by journal name, publisher, field, or ISSN…"
              style={{ width: "100%", padding: "9px 12px 9px 34px", border: `1px solid ${BORDER}`, fontSize: 13, outline: "none", boxSizing: "border-box", transition: "border-color 0.12s" }}
              onFocus={(e) => e.currentTarget.style.borderColor = NAVY + "50"}
              onBlur={(e) => e.currentTarget.style.borderColor = BORDER}
            />
          </div>

          {/* Sort */}
          <select
            data-testid={TID.discoverySortSelect}
            value={sort}
            onChange={(e) => { setSort(e.target.value); setPage(1); }}
            style={{ padding: "8px 10px", border: `1px solid ${BORDER}`, fontSize: 12, color: "#374151", background: "white", cursor: "pointer", flexShrink: 0 }}
          >
            {SORT_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>

          {/* Saved search controls */}
          <SavedSearchControls kind="journal" query={q} filters={filters} />
        </div>

        {/* Active filter chips */}
        {activeCount > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 9, alignItems: "center" }}>
            {q && <FilterChip label={`"${q}"`} onRemove={() => setQ("")} />}
            {Object.entries(filters).map(([k, v]) => (
              <FilterChip key={k} label={`${k}: ${String(v)}`} onRemove={() => setFilter(k, null)} />
            ))}
            <button onClick={clearAll} style={{ fontSize: 11, color: "#94A3B8", background: "none", border: "none", cursor: "pointer", padding: "2px 4px" }}>
              Clear all
            </button>
          </div>
        )}
      </div>

      {/* ── AI RECOMMENDATIONS PANEL ──────────────────────────────────── */}
      {(recsLoading || recs) && (
        <div style={{ marginTop: 24, padding: "16px 18px", background: NAVY + "06", border: `1px solid ${NAVY}14` }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Sparkles size={13} strokeWidth={1.5} style={{ color: NAVY }} />
              <span style={{ fontSize: 12, fontWeight: 700, color: NAVY, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Recommended for You
              </span>
              <span style={{ fontSize: 11, color: "#94A3B8" }}>Based on your research profile</span>
            </div>
            <Link to="/academic-passport" style={{ fontSize: 11, color: "#64748B", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3 }}>
              Update profile <ArrowRight size={10} strokeWidth={1.5} />
            </Link>
          </div>

          {recsLoading ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} style={{ height: 120, background: "#E2E8F0", animation: "jpulse 1.6s ease-in-out infinite" }} />
              ))}
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(recs.length, 4)}, 1fr)`, gap: 10 }}>
              {recs.slice(0, 4).map((rec, i) => (
                <RecommendationCard key={rec.journal_id} rec={rec} rank={i + 1} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── TWO-COLUMN CONTENT AREA ────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 0, marginTop: 24, alignItems: "flex-start" }}>

        {/* LEFT FACET RAIL ─────────────────────────────────────────────── */}
        <aside style={{ width: 228, flexShrink: 0, position: "sticky", top: 57, alignSelf: "flex-start", maxHeight: "calc(100vh - 64px)", overflowY: "auto", paddingRight: 20, paddingBottom: 40 }}>

          {/* Quota banner */}
          {quota && (
            <div style={{
              marginBottom: 14, padding: "9px 11px", fontSize: 11,
              background: quota.used >= quota.limit ? "#FEF2F2" : quota.used >= quota.limit * 0.8 ? "#FFFBEB" : WARM,
              border: `1px solid ${quota.used >= quota.limit ? "#FECACA" : quota.used >= quota.limit * 0.8 ? "#FCD34D" : BORDER}`,
              display: "flex", alignItems: "center", gap: 6,
              color: quota.used >= quota.limit ? "#991B1B" : "#64748B",
            }}>
              <Gauge size={11} strokeWidth={1.5} style={{ flexShrink: 0 }} />
              <span style={{ flex: 1 }}>
                <strong>{quota.used}</strong> / {quota.limit} searches used
                {quota.used >= quota.limit && " — limit reached"}
                {quota.used >= quota.limit * 0.8 && quota.used < quota.limit && " — nearly full"}
              </span>
              {quota.used >= quota.limit * 0.8 && (
                <Link to="/pricing" style={{ fontSize: 10, color: NAVY, textDecoration: "none", fontWeight: 700 }}>↑</Link>
              )}
            </div>
          )}

          {/* Facet filter groups */}
          {FILTER_DEFS.map(({ key, facetKey, label, fmt }) => (
            <FacetGroup
              key={key}
              label={label}
              values={facets[facetKey] || []}
              activeValue={filters[key]}
              onChange={(v) => setFilter(key, v)}
              fmt={fmt}
            />
          ))}

          {/* Publishing quick-filters */}
          <div style={{ marginTop: 14, padding: "14px 12px", background: NAVY + "07", border: `1px solid ${NAVY}12` }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: NAVY + "CC", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 10 }}>
              Quick Filters
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {[
                { label: "Open Access only",  action: () => setFilter("open_access", true), icon: CheckCircle2, color: "#059669" },
                { label: "Q1 journals",       action: () => setFilter("quartile", "Q1"),    icon: Award,        color: "#1E3A8A" },
                { label: "Q2 journals",       action: () => setFilter("quartile", "Q2"),    icon: Award,        color: "#0369A1" },
              ].map(({ label, action, icon: Icon, color }) => (
                <button
                  key={label}
                  onClick={action}
                  style={{ display: "flex", alignItems: "center", gap: 7, background: "none", border: "none", cursor: "pointer", textAlign: "left", padding: "4px 2px" }}
                >
                  <Icon size={11} strokeWidth={1.5} style={{ color, flexShrink: 0 }} />
                  <span style={{ fontSize: 11, color: "#374151" }}>{label}</span>
                  <ArrowRight size={9} strokeWidth={1.5} style={{ color: "#CBD5E1", marginLeft: "auto" }} />
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* RIGHT CONTENT AREA ──────────────────────────────────────────── */}
        <div style={{ flex: 1, minWidth: 0, paddingLeft: 24 }}>

          {/* Subject category bar (shown only when no active search/filters) */}
          {!q && Object.keys(filters).length === 0 && (facets.subjects || []).length > 0 && (
            <CategoryBar subjects={facets.subjects} onSelect={(s) => setFilter("subject", s)} />
          )}

          {/* Result count */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <span style={{ fontSize: 12, color: "#64748B", fontFamily: "monospace" }}>
              {loading ? "Searching…" : `${total.toLocaleString()} ${total === 1 ? "journal" : "journals"}`}
            </span>
            {page > 1 && !loading && (
              <span style={{ fontSize: 11, color: "#94A3B8", fontFamily: "monospace" }}>Page {page}</span>
            )}
          </div>

          {/* Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
            {loading
              ? Array.from({ length: 6 }).map((_, i) => <JournalSkeleton key={i} />)
              : items.length === 0
                ? (
                  <div style={{ gridColumn: "span 2" }}>
                    <JournalsEmptyState q={q} filters={filters} onClear={clearAll} onSearch={focusSearch} />
                  </div>
                )
                : items.map((j) => (
                  <JournalCard
                    key={j.id}
                    j={j}
                    inCompare={compareList.some((c) => c.id === j.id)}
                    canAddToCompare={compareList.length < 3}
                    onCompare={() => toggleCompare(j)}
                  />
                ))
            }
          </div>

          {/* Pagination */}
          {(page > 1 || hasMore) && !loading && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 24, paddingTop: 20, borderTop: `1px solid ${BORDER}` }}>
              <button
                data-testid={TID.discoveryPagePrev}
                disabled={page === 1}
                onClick={() => { setPage((p) => Math.max(1, p - 1)); window.scrollTo({ top: 200, behavior: "smooth" }); }}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "8px 16px", border: `1px solid ${BORDER}`, fontSize: 12, background: "white", cursor: page === 1 ? "not-allowed" : "pointer", opacity: page === 1 ? 0.4 : 1 }}
              >
                <ChevronLeft size={12} strokeWidth={1.5} /> Previous
              </button>
              <span style={{ fontSize: 11, color: "#94A3B8", fontFamily: "monospace" }}>Page {page}</span>
              <button
                data-testid={TID.discoveryPageNext}
                disabled={!hasMore}
                onClick={() => { setPage((p) => p + 1); window.scrollTo({ top: 200, behavior: "smooth" }); }}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "8px 16px", border: `1px solid ${BORDER}`, fontSize: 12, background: "white", cursor: !hasMore ? "not-allowed" : "pointer", opacity: !hasMore ? 0.4 : 1 }}
              >
                Next <ChevronRight size={12} strokeWidth={1.5} />
              </button>
            </div>
          )}

          {/* ── Publishing Insights (shown when not loading, below results) */}
          {!loading && items.length > 0 && (
            <PublishingInsights />
          )}

          {/* Bottom padding to clear compare panel */}
          {showCompare && compareList.length > 0 && <div style={{ height: 280 }} />}
        </div>
      </div>

      {/* ── COMPARE PANEL (fixed at bottom) ───────────────────────────── */}
      {showCompare && compareList.length > 0 && (
        <ComparePanel
          journals={compareList}
          onRemove={(id) => setCompareList((prev) => prev.filter((j) => j.id !== id))}
          onClose={() => setShowCompare(false)}
          onClearAll={() => { setCompareList([]); setShowCompare(false); }}
        />
      )}
    </DiscoveryLayout>
  );
}

// ─── Journal Card ─────────────────────────────────────────────────────────────
function JournalCard({ j, inCompare, canAddToCompare, onCompare }) {
  const [hovered, setHovered] = useState(false);
  const qStyle = Q_STYLE[j.quartile] || null;

  return (
    <div
      style={{
        position: "relative",
        border: `1px solid ${inCompare ? NAVY : hovered ? "#94A3B8" : BORDER}`,
        background: "white",
        transition: "border-color 0.12s, box-shadow 0.12s",
        boxShadow: hovered ? "0 4px 18px rgba(15,40,71,0.09)" : "none",
        display: "flex", flexDirection: "column",
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Compare indicator bar */}
      {inCompare && (
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: NAVY }} />
      )}

      <Link
        to={`/journals/${j.id}`}
        data-testid={TID.discoveryItem(j.id)}
        style={{ display: "block", padding: "16px 16px 12px", textDecoration: "none", color: "inherit", flex: 1 }}
      >
        {/* Badge row */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
          <div style={{ display: "flex", gap: 5 }}>
            {j.quartile && qStyle && (
              <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 7px", background: qStyle.bg, border: `1px solid ${qStyle.border}`, color: qStyle.text, letterSpacing: "0.07em" }}>
                {j.quartile}
              </span>
            )}
            {j.open_access && (
              <span style={{ fontSize: 9, fontWeight: 600, padding: "2px 7px", background: "#ECFDF5", border: "1px solid #6EE7B7", color: "#065F46", letterSpacing: "0.05em" }}>
                OA
              </span>
            )}
          </div>
          <span style={{ fontSize: 10, color: "#CBD5E1", fontFamily: "monospace" }}>
            {SRC_LABEL[j.source] || ""}
          </span>
        </div>

        {/* Journal title */}
        <h3 style={{
          fontSize: 14, fontWeight: 700, color: "#0f172a", lineHeight: 1.35, marginBottom: 4,
          display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
        }}>
          {j.title}
        </h3>

        {/* Publisher · Country */}
        <div style={{ fontSize: 11, color: "#94A3B8", marginBottom: 10, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {j.publisher || "Publisher unknown"}
          {j.country && ` · ${j.country}`}
        </div>

        {/* Subject chips */}
        {j.subjects && j.subjects.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
            {j.subjects.slice(0, 3).map((s, i) => (
              <span key={i} style={{ fontSize: 10, padding: "2px 6px", background: WARM, border: `1px solid ${BORDER}`, color: "#64748B" }}>
                {s}
              </span>
            ))}
            {j.subjects.length > 3 && (
              <span style={{ fontSize: 10, color: "#94A3B8" }}>+{j.subjects.length - 3}</span>
            )}
          </div>
        )}

        {/* Impact metrics */}
        <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6 }}>
          <MetricCell label="Works"     value={(j.works_count || 0).toLocaleString()} />
          <MetricCell
            label="Citations"
            value={j.cited_by_count >= 1000 ? `${((j.cited_by_count || 0) / 1000).toFixed(0)}K` : (j.cited_by_count || 0).toLocaleString()}
          />
          <MetricCell label="h-index"   value={j.h_index || "—"} />
        </div>

        {/* Optional detail metrics (only real data) */}
        {(j.apc_usd || j.review_time_weeks || j.acceptance_rate) && (
          <div style={{ display: "flex", gap: 10, marginTop: 9, flexWrap: "wrap" }}>
            {j.apc_usd && (
              <span style={{ fontSize: 10, color: "#64748B" }}>
                <span style={{ color: "#CBD5E1", fontSize: 9 }}>APC </span>${j.apc_usd.toLocaleString()}
              </span>
            )}
            {j.review_time_weeks && (
              <span style={{ fontSize: 10, color: "#64748B", display: "inline-flex", alignItems: "center", gap: 3 }}>
                <Clock size={9} strokeWidth={1.5} style={{ color: "#94A3B8" }} />
                {j.review_time_weeks}w review
              </span>
            )}
            {j.acceptance_rate && (
              <span style={{ fontSize: 10, color: "#64748B" }}>
                {j.acceptance_rate}% accepted
              </span>
            )}
          </div>
        )}
      </Link>

      {/* Hover action bar */}
      <div style={{
        padding: "7px 12px",
        borderTop: hovered ? `1px solid ${BORDER}` : "1px solid transparent",
        background: hovered ? WARM : "transparent",
        display: "flex", gap: 5, alignItems: "center",
        minHeight: 34,
        transition: "background 0.1s, border-color 0.1s",
      }}>
        {hovered && (
          <>
            <button
              onClick={(e) => { e.preventDefault(); onCompare(); }}
              disabled={!canAddToCompare && !inCompare}
              style={{
                fontSize: 10, fontWeight: 500, padding: "3px 10px",
                border: `1px solid ${inCompare ? NAVY : BORDER}`,
                background: inCompare ? NAVY : "white",
                color: inCompare ? "white" : "#374151",
                cursor: (!canAddToCompare && !inCompare) ? "not-allowed" : "pointer",
                opacity: (!canAddToCompare && !inCompare) ? 0.4 : 1,
              }}
              title={!canAddToCompare && !inCompare ? "Maximum 3 journals in comparison" : undefined}
            >
              {inCompare ? "✓ Comparing" : "Compare"}
            </button>
            {j.homepage_url && (
              <a
                href={j.homepage_url}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                style={{ fontSize: 10, padding: "3px 9px", border: `1px solid ${BORDER}`, background: "white", color: "#374151", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3 }}
              >
                <Globe size={9} strokeWidth={1.5} /> Website
              </a>
            )}
            {j.submission_url && (
              <a
                href={j.submission_url}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                style={{ fontSize: 10, padding: "3px 9px", border: `1px solid ${BORDER}`, background: "white", color: "#374151", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 3 }}
              >
                <ExternalLink size={9} strokeWidth={1.5} /> Submit
              </a>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ─── Recommendation card ──────────────────────────────────────────────────────
function RecommendationCard({ rec, rank }) {
  const qStyle = Q_STYLE[rec.quartile] || null;
  const scorePct = Math.min(100, Math.round(rec.score));
  const scoreColor = scorePct >= 70 ? "#059669" : scorePct >= 45 ? "#D97706" : "#94A3B8";

  return (
    <Link
      to={`/journals/${rec.journal_id}`}
      style={{ display: "block", textDecoration: "none", background: "white", border: `1px solid ${BORDER}`, padding: "14px 14px 12px", transition: "box-shadow 0.12s" }}
      onMouseEnter={(e) => e.currentTarget.style.boxShadow = "0 4px 14px rgba(15,40,71,0.09)"}
      onMouseLeave={(e) => e.currentTarget.style.boxShadow = "none"}
    >
      {/* Rank + badges */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: "#CBD5E1", fontFamily: "monospace" }}>#{rank}</span>
        <div style={{ display: "flex", gap: 4 }}>
          {rec.quartile && qStyle && (
            <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: qStyle.bg, border: `1px solid ${qStyle.border}`, color: qStyle.text, letterSpacing: "0.06em" }}>
              {rec.quartile}
            </span>
          )}
          {rec.open_access && (
            <span style={{ fontSize: 9, fontWeight: 600, padding: "2px 6px", background: "#ECFDF5", border: "1px solid #6EE7B7", color: "#065F46" }}>OA</span>
          )}
        </div>
      </div>

      {/* Title */}
      <div style={{ fontSize: 12, fontWeight: 700, color: "#0f172a", lineHeight: 1.3, marginBottom: 4, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
        {rec.title}
      </div>

      {/* Publisher */}
      <div style={{ fontSize: 10, color: "#94A3B8", marginBottom: 8, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {rec.publisher || "—"}
      </div>

      {/* Match score bar */}
      <div style={{ marginBottom: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
          <span style={{ fontSize: 9, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.07em" }}>Match</span>
          <span style={{ fontSize: 10, fontFamily: "monospace", fontWeight: 700, color: scoreColor }}>{scorePct}%</span>
        </div>
        <div style={{ height: 3, background: "#E2E8F0" }}>
          <div style={{ height: "100%", background: scoreColor, width: `${scorePct}%`, transition: "width 0.5s" }} />
        </div>
      </div>

      {/* Explanation */}
      {rec.explanation && (
        <div style={{ fontSize: 10, color: "#64748B", lineHeight: 1.5, marginBottom: 6, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {rec.explanation}
        </div>
      )}

      {/* Review time + acceptance */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {rec.review_time_estimate && (
          <span style={{ fontSize: 9, color: "#94A3B8", display: "inline-flex", alignItems: "center", gap: 3 }}>
            <Clock size={8} strokeWidth={1.5} /> {rec.review_time_estimate}
          </span>
        )}
        {rec.acceptance_probability && (
          <span style={{ fontSize: 9, color: "#94A3B8" }}>
            Acceptance: {rec.acceptance_probability}
          </span>
        )}
      </div>
    </Link>
  );
}

// ─── Publishing Insights panel ────────────────────────────────────────────────
const INSIGHTS = [
  {
    icon: BookOpen,
    title: "Open Access Publishing",
    color: "#059669",
    bg: "#F0FDF4",
    border: "#A7F3D0",
    points: [
      "Diamond OA — free for authors and readers",
      "Gold OA — author pays APC, reader reads freely",
      "Hybrid OA — subscribe or pay per article",
      "Green OA — post preprint to repository",
    ],
  },
  {
    icon: Clock,
    title: "Peer Review Models",
    color: "#0369A1",
    bg: "#F0F9FF",
    border: "#BAE6FD",
    points: [
      "Single-blind — authors unknown, reviewers known",
      "Double-blind — both parties anonymous",
      "Open review — identities disclosed post-acceptance",
      "Post-publication — community review after publishing",
    ],
  },
  {
    icon: TrendingUp,
    title: "Impact & Rankings",
    color: "#7C3AED",
    bg: "#FDF4FF",
    border: "#DDD6FE",
    points: [
      "Q1 = top 25% by citation impact in subject area",
      "h-index measures sustained citation productivity",
      "JIF (Journal Impact Factor) — 2-year citation average",
      "CiteScore (Scopus) uses 4-year citation window",
    ],
  },
];

function PublishingInsights() {
  return (
    <div style={{ marginTop: 28, paddingTop: 24, borderTop: `1px solid ${BORDER}` }}>
      <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "#94A3B8", marginBottom: 14 }}>
        Publishing Intelligence
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        {INSIGHTS.map(({ icon: Icon, title, color, bg, border, points }) => (
          <div key={title} style={{ background: bg, border: `1px solid ${border}`, padding: "14px 14px 12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 10 }}>
              <Icon size={13} strokeWidth={1.5} style={{ color }} />
              <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>{title}</span>
            </div>
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 5 }}>
              {points.map((p) => (
                <li key={p} style={{ fontSize: 11, color: "#374151", display: "flex", alignItems: "flex-start", gap: 6, lineHeight: 1.45 }}>
                  <span style={{ width: 4, height: 4, background: color, borderRadius: "50%", flexShrink: 0, marginTop: 5 }} />
                  {p}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Metric cell ──────────────────────────────────────────────────────────────
function MetricCell({ label, value }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", fontFamily: "monospace", lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 9, color: "#94A3B8", letterSpacing: "0.05em", textTransform: "uppercase", marginTop: 3 }}>{label}</div>
    </div>
  );
}

// ─── Facet filter group ───────────────────────────────────────────────────────
function FacetGroup({ label, values, activeValue, onChange, fmt }) {
  const [open, setOpen] = useState(true);
  if (!values || values.length === 0) return null;
  return (
    <div style={{ borderBottom: `1px solid ${BORDER}`, paddingBottom: 12, marginBottom: 12 }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%", background: "none", border: "none", cursor: "pointer", padding: "0 0 6px" }}
      >
        <span style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          {label}
        </span>
        {open
          ? <ChevronUp size={11} strokeWidth={1.5} style={{ color: "#CBD5E1" }} />
          : <ChevronDown size={11} strokeWidth={1.5} style={{ color: "#CBD5E1" }} />
        }
      </button>
      {open && (
        <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {values.slice(0, 12).map((f) => {
            const id = f._id;
            const disp = fmt ? fmt(id) : String(id);
            const active = activeValue === id || activeValue === String(id);
            return (
              <li key={String(id)}>
                <button
                  onClick={() => onChange(active ? null : id)}
                  style={{
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    width: "100%", textAlign: "left", padding: "5px 6px",
                    border: "none",
                    background: active ? NAVY + "0c" : "transparent",
                    borderLeft: `2px solid ${active ? NAVY : "transparent"}`,
                    cursor: "pointer",
                  }}
                >
                  <span style={{ fontSize: 11, color: active ? NAVY : "#64748B", fontWeight: active ? 600 : 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 148 }}>
                    {disp}
                  </span>
                  <span style={{ fontSize: 10, color: "#94A3B8", fontFamily: "monospace", flexShrink: 0, marginLeft: 4 }}>{f.count}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ─── Category bar ─────────────────────────────────────────────────────────────
function CategoryBar({ subjects, onSelect }) {
  const top = subjects.slice(0, 10);
  return (
    <div style={{ marginBottom: 18, padding: "14px 16px", background: WARM, border: `1px solid ${BORDER}` }}>
      <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#94A3B8", marginBottom: 10 }}>
        Browse by research field
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {top.map((f, i) => {
          const col = CATEGORY_COLORS[i % CATEGORY_COLORS.length];
          return (
            <button
              key={f._id}
              onClick={() => onSelect(f._id)}
              style={{
                background: col.bg, color: col.text,
                fontSize: 11, fontWeight: 500,
                padding: "5px 12px", border: "none", cursor: "pointer",
                display: "inline-flex", alignItems: "center", gap: 5,
              }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = "0.75"}
              onMouseLeave={(e) => e.currentTarget.style.opacity = "1"}
            >
              {f._id}
              <span style={{ fontSize: 9, fontFamily: "monospace", opacity: 0.55 }}>{f.count.toLocaleString()}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Compare panel (fixed bottom) ────────────────────────────────────────────
function ComparePanel({ journals, onRemove, onClose, onClearAll }) {
  return (
    <div style={{
      position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 50,
      background: "white", borderTop: `2px solid ${NAVY}`,
      boxShadow: "0 -8px 32px rgba(15,40,71,0.15)",
      maxHeight: "48vh", overflowY: "auto",
    }}>
      {/* Panel header */}
      <div style={{ padding: "10px 20px", background: NAVY, display: "flex", alignItems: "center", gap: 10, position: "sticky", top: 0, zIndex: 1 }}>
        <Scale size={13} strokeWidth={1.5} style={{ color: "rgba(255,255,255,0.7)" }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: "white" }}>Journal Comparison</span>
        <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)" }}>Up to 3 journals</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}>
          <button onClick={onClearAll} style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", background: "none", border: "none", cursor: "pointer" }}>
            Clear all
          </button>
          <button onClick={onClose} style={{ color: "rgba(255,255,255,0.5)", background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", padding: 2 }}>
            <X size={14} strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {/* Comparison table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ background: WARM }}>
              <th style={{ padding: "10px 16px", textAlign: "left", fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.07em", width: 150, borderRight: `1px solid ${BORDER}` }}>
                Metric
              </th>
              {journals.map((j) => (
                <th key={j.id} style={{ padding: "10px 16px", textAlign: "left", borderRight: `1px solid ${BORDER}`, minWidth: 190, verticalAlign: "top" }}>
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: "#0f172a", lineHeight: 1.3 }}>{j.title}</div>
                      {j.quartile && (
                        <span style={{ fontSize: 9, fontWeight: 700, padding: "1px 5px", background: Q_STYLE[j.quartile]?.bg, color: Q_STYLE[j.quartile]?.text, border: `1px solid ${Q_STYLE[j.quartile]?.border}`, display: "inline-block", marginTop: 4, letterSpacing: "0.06em" }}>
                          {j.quartile}
                        </span>
                      )}
                    </div>
                    <button onClick={() => onRemove(j.id)} style={{ color: "#CBD5E1", background: "none", border: "none", cursor: "pointer", flexShrink: 0, padding: 2 }}>
                      <X size={11} strokeWidth={1.5} />
                    </button>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {COMPARE_ROWS.map(({ label, fmt }, ri) => (
              <tr key={label} style={{ background: ri % 2 === 0 ? "white" : WARM }}>
                <td style={{ padding: "8px 16px", fontSize: 11, color: "#64748B", fontWeight: 500, borderRight: `1px solid ${BORDER}`, whiteSpace: "nowrap" }}>
                  {label}
                </td>
                {journals.map((j) => (
                  <td key={j.id} style={{ padding: "8px 16px", fontFamily: "monospace", fontSize: 12, color: "#374151", borderRight: `1px solid ${BORDER}` }}>
                    {fmt(j)}
                  </td>
                ))}
              </tr>
            ))}
            {/* Action row */}
            <tr>
              <td style={{ padding: "10px 16px", borderRight: `1px solid ${BORDER}` }} />
              {journals.map((j) => (
                <td key={j.id} style={{ padding: "10px 16px", borderRight: `1px solid ${BORDER}` }}>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <Link
                      to={`/journals/${j.id}`}
                      style={{ display: "inline-flex", alignItems: "center", gap: 5, background: NAVY, color: "white", padding: "5px 12px", fontSize: 11, fontWeight: 600, textDecoration: "none" }}
                    >
                      <Eye size={10} strokeWidth={1.5} /> View
                    </Link>
                    {j.submission_url && (
                      <a
                        href={j.submission_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ display: "inline-flex", alignItems: "center", gap: 4, border: `1px solid ${BORDER}`, color: "#374151", padding: "5px 10px", fontSize: 11, textDecoration: "none" }}
                      >
                        Submit <ExternalLink size={9} strokeWidth={1.5} />
                      </a>
                    )}
                  </div>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────
function JournalSkeleton() {
  return (
    <div style={{ border: `1px solid ${BORDER}`, background: "white", padding: 16 }}>
      <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
        <div style={{ height: 17, width: 28, background: "#E2E8F0", animation: "jpulse 1.6s ease-in-out infinite" }} />
        <div style={{ height: 17, width: 22, background: "#E2E8F0", animation: "jpulse 1.6s ease-in-out infinite" }} />
      </div>
      <div style={{ height: 17, background: "#E2E8F0", marginBottom: 7, animation: "jpulse 1.6s ease-in-out infinite" }} />
      <div style={{ height: 13, background: "#E2E8F0", width: "60%", marginBottom: 12, animation: "jpulse 1.6s ease-in-out infinite" }} />
      <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
        {[55, 75, 50].map((w, i) => (
          <div key={i} style={{ height: 19, width: w, background: "#E2E8F0", animation: "jpulse 1.6s ease-in-out infinite" }} />
        ))}
      </div>
      <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6 }}>
        {[1, 2, 3].map((i) => (
          <div key={i} style={{ height: 30, background: "#E2E8F0", animation: "jpulse 1.6s ease-in-out infinite" }} />
        ))}
      </div>
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────
function JournalsEmptyState({ q, filters, onClear, onSearch }) {
  const hasActive = q || Object.keys(filters).length > 0;
  return (
    <div style={{ padding: "52px 32px", background: "white", border: `1px solid ${BORDER}`, textAlign: "center" }}>
      <div style={{ width: 54, height: 54, background: WARM, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px" }}>
        <BookOpen size={22} strokeWidth={1} style={{ color: NAVY + "50" }} />
      </div>
      {hasActive ? (
        <>
          <h3 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", margin: "0 0 8px", letterSpacing: "-0.01em" }}>
            No journals match your search
          </h3>
          <p style={{ fontSize: 13, color: "#64748B", maxWidth: 380, margin: "0 auto 20px", lineHeight: 1.65 }}>
            Try a broader keyword, remove a filter, or search by publisher or subject area.
            The index covers 9,000+ venues from OpenAlex, Crossref, and DOAJ.
          </p>
          <button onClick={onClear} style={{ background: NAVY, color: "white", padding: "9px 20px", fontSize: 12, fontWeight: 600, border: "none", cursor: "pointer" }}>
            Clear filters
          </button>
        </>
      ) : (
        <>
          <h3 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", margin: "0 0 8px", letterSpacing: "-0.01em" }}>
            Search Academic Journals
          </h3>
          <p style={{ fontSize: 13, color: "#64748B", maxWidth: 400, margin: "0 auto 20px", lineHeight: 1.65 }}>
            Search by journal name, publisher, or research field. Use the filters on the left
            to narrow by quartile, open access status, or country of publication.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "center", maxWidth: 340, margin: "0 auto 20px" }}>
            {[
              "Find Q1 journals in your research field",
              "Compare impact metrics across venues",
              "Filter by open access and APC range",
            ].map((tip) => (
              <div key={tip} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#64748B" }}>
                <Target size={10} strokeWidth={1.5} style={{ color: "#CBD5E1", flexShrink: 0 }} /> {tip}
              </div>
            ))}
          </div>
          <button
            onClick={onSearch}
            style={{ background: NAVY, color: "white", padding: "9px 20px", fontSize: 12, fontWeight: 600, border: "none", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}
          >
            <Search size={12} strokeWidth={1.5} /> Start searching
          </button>
        </>
      )}
    </div>
  );
}

// ─── Active filter chip ───────────────────────────────────────────────────────
function FilterChip({ label, onRemove }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, background: NAVY + "0f", color: NAVY, padding: "3px 8px 3px 10px", border: `1px solid ${NAVY}22` }}>
      {label}
      <button onClick={onRemove} style={{ background: "none", border: "none", cursor: "pointer", color: NAVY + "70", display: "flex", alignItems: "center", padding: 0 }}>
        <X size={10} strokeWidth={1.5} />
      </button>
    </span>
  );
}

// ─── Gated state (402 → upgrade required) ────────────────────────────────────
function GatedState({ tabLinks }) {
  return (
    <div>
      <div style={{ margin: "-24px -24px 0", background: NAVY }}>
        <div style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", padding: "0 24px" }}>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.22)", marginRight: "auto" }}>Discovery Suite</span>
          {tabLinks.map(({ to, label, testid, active }) => (
            <Link key={to} to={to} data-testid={testid} style={{ display: "block", padding: "14px 20px", fontSize: 13, fontWeight: active ? 600 : 400, color: active ? "white" : "rgba(255,255,255,0.45)", textDecoration: "none", borderBottom: `2px solid ${active ? "white" : "transparent"}` }}>
              {label}
            </Link>
          ))}
        </div>
        <div style={{ padding: "30px 24px 26px" }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, color: "white", margin: 0, letterSpacing: "-0.025em" }}>Discover Academic Journals</h1>
        </div>
      </div>
      <div style={{ maxWidth: 480, margin: "48px auto", padding: "44px 36px", background: "white", border: `1px solid ${BORDER}`, textAlign: "center" }}>
        <div style={{ width: 52, height: 52, background: WARM, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px" }}>
          <Lock size={20} strokeWidth={1.5} style={{ color: "#94A3B8" }} />
        </div>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: NAVY, marginBottom: 8 }}>
          Researcher Plan Required
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "#0f172a", margin: "0 0 10px", letterSpacing: "-0.01em" }}>
          Full journal access is a paid feature
        </h2>
        <p style={{ fontSize: 13, color: "#64748B", lineHeight: 1.7, margin: "0 0 24px" }}>
          Upgrade to unlock unlimited journal discovery, faceted filters, quartile rankings, open access data, and AI venue matching across 9,000+ academic journals.
        </p>
        <Link to="/pricing" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", padding: "10px 22px", fontSize: 13, fontWeight: 600, textDecoration: "none" }}>
          <Zap size={13} strokeWidth={1.5} /> View Plans
        </Link>
      </div>
    </div>
  );
}

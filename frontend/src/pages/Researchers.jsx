import React, { useState, useEffect, useCallback, useRef } from "react";
import { DiscoveryLayout } from "@/layouts";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { ACCENT, EMERALD, NAVY, WARM } from "@/lib/tokens";
import {
  Search, X, ChevronDown, ChevronLeft, ChevronRight, ArrowRight,
  Users, Globe, Building2, MapPin, BookOpen, Award, TrendingUp,
  Bookmark, BookmarkCheck, Sparkles, BarChart2, UserPlus, GraduationCap,
  FlaskConical, Lightbulb, CheckCircle, AlertCircle, Star, Clock,
  ExternalLink, RefreshCw, Activity,
} from "lucide-react";

// ── Design tokens ─────────────────────────────────────────────────────────────
const BORDER  = "#E4E8EF";

// ── Helpers ───────────────────────────────────────────────────────────────────
function computeSlug(fullName) {
  let s = (fullName || "").toLowerCase().trim();
  s = s.replace(/[^a-z0-9\s-]/g, "");
  s = s.replace(/\s+/g, "-");
  s = s.replace(/-+/g, "-").replace(/^-|-$/g, "");
  return s || "researcher";
}

function profileUrl(r) {
  const slug = r.slug || computeSlug(r.full_name);
  return `/researcher/${slug}`;
}

function initials(name) {
  return (name || "?")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join("");
}

function hasOrcid(r) {
  return !!(r.orcid?.orcid_id || (typeof r.orcid === "string" && r.orcid));
}

// ── Section definitions ───────────────────────────────────────────────────────
const SECTION_TABS = [
  { key: "recommended",             label: "For You",            icon: Sparkles,       desc: "Matched to your research profile" },
  { key: "top_scholars",            label: "Top Scholars",        icon: Award,          desc: "Leading researchers by academic impact" },
  { key: "available_collaborators", label: "Open to Collaborate", icon: UserPlus,       desc: "Actively seeking research partners" },
  { key: "methodology_experts",     label: "Methodology Experts", icon: FlaskConical,   desc: "Share your research methods" },
  { key: "institutional_matches",   label: "Your Institution",    icon: Building2,      desc: "Colleagues at your institution" },
  { key: "international_matches",   label: "International",       icon: Globe,          desc: "Global collaborators in your field" },
  { key: "available_reviewers",     label: "Reviewers",           icon: CheckCircle,    desc: "Available for peer review" },
  { key: "recently_active",         label: "Recently Active",     icon: Activity,       desc: "Updated their profile recently" },
];

const PAGE_SIZE = 24;

// ── Main component ────────────────────────────────────────────────────────────
export default function Researchers() {
  const { user } = useAuth();
  const explorerRef = useRef(null);

  // Discovery sections (from /researchers/discover/sections)
  const [sections,        setSections]        = useState(null);
  const [sectionsLoading, setSectionsLoading] = useState(true);
  const [activeSection,   setActiveSection]   = useState("recommended");

  // AI recommendations (from /recommendations/researchers)
  const [aiRecs,        setAiRecs]        = useState(null);
  const [aiRecsLoading, setAiRecsLoading] = useState(true);

  // Recently viewed
  const [recentlyViewed, setRecentlyViewed] = useState([]);

  // Saved
  const [savedIds, setSavedIds] = useState(new Set());
  const [savedMap, setSavedMap] = useState(new Map());

  // Explorer (search + filter)
  const [q,          setQ]          = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [filters,    setFilters]    = useState({});
  const [items,      setItems]      = useState([]);
  const [cursor,     setCursor]     = useState(null);
  const [hasMore,    setHasMore]    = useState(false);
  const [loading,    setLoading]    = useState(false);
  const [searched,   setSearched]   = useState(false);

  // Compare (client-side)
  const [compareList, setCompareList] = useState([]);

  // ── Debounce q ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 400);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    setCursor(null);
    setItems([]);
  }, [debouncedQ, filters]);

  // ── Boot ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    api.get("/researchers/discover/sections")
      .then((r) => setSections(r.data))
      .catch(() => setSections({}))
      .finally(() => setSectionsLoading(false));

    api.get("/researchers/saved/ids")
      .then((r) => setSavedIds(new Set(r.data?.ids || [])))
      .catch(() => {});

    api.get("/researchers/recently-viewed?limit=8")
      .then((r) => setRecentlyViewed(Array.isArray(r.data) ? r.data : []))
      .catch(() => {});

    api.get("/recommendations/researchers?limit=8")
      .then((r) => {
        const raw = r.data;
        const list = Array.isArray(raw) ? raw : (raw?.results || []);
        setAiRecs(list.length > 0 ? list : null);
      })
      .catch(() => setAiRecs(null))
      .finally(() => setAiRecsLoading(false));
  }, []);

  // ── Explorer search ────────────────────────────────────────────────────────
  const filtersKey = JSON.stringify(filters);
  const fetchResearchers = useCallback(async (reset = false) => {
    const thisQ = debouncedQ;
    if (!thisQ && !Object.values(filters).some(Boolean)) {
      setItems([]);
      setSearched(false);
      return;
    }
    setLoading(true);
    setSearched(true);
    try {
      const params = {
        limit: PAGE_SIZE,
        ...(thisQ                                   && { q: thisQ }),
        ...(filters.research_area                   && { research_area: filters.research_area }),
        ...(filters.country                         && { country: filters.country }),
        ...(filters.available_for_collaboration     && { available_for_collaboration: true }),
        ...(filters.available_for_reviewing         && { available_for_reviewing: true }),
        ...(filters.available_for_supervision       && { available_for_supervision: true }),
        ...(filters.has_orcid                       && { has_orcid: true }),
        ...(filters.min_h_index && parseInt(filters.min_h_index) > 0 && { min_h_index: parseInt(filters.min_h_index) }),
        ...(filters.institution                     && { institution: filters.institution }),
        ...(!reset && cursor                        && { cursor }),
      };
      const { data } = await api.get("/users", { params });
      const newItems = Array.isArray(data) ? data : (data?.items || []);
      const nextCursor = Array.isArray(data) ? null : (data?.next_cursor || null);
      setItems((prev) => reset ? newItems : [...prev, ...newItems]);
      setCursor(nextCursor);
      setHasMore(!!nextCursor);
    } catch {
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQ, filtersKey, cursor]);

  useEffect(() => {
    if (debouncedQ || Object.values(filters).some(Boolean)) {
      fetchResearchers(true);
    } else {
      setItems([]);
      setSearched(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQ, filtersKey]);

  // ── Save/unsave ────────────────────────────────────────────────────────────
  const isSaved = (r) => savedMap.has(r.id) ? savedMap.get(r.id) : (savedIds.has(r.id) || !!r.is_saved);

  const toggleSave = async (r, e) => {
    e.preventDefault();
    e.stopPropagation();
    const was = isSaved(r);
    setSavedMap((prev) => new Map([...prev, [r.id, !was]]));
    try {
      if (was) {
        await api.delete(`/researchers/saved/${r.id}`);
        setSavedIds((prev) => { const next = new Set(prev); next.delete(r.id); return next; });
        toast.success("Researcher removed from saved");
      } else {
        await api.post(`/researchers/saved/${r.id}`);
        setSavedIds((prev) => new Set([...prev, r.id]));
        toast.success("Researcher saved");
      }
    } catch {
      setSavedMap((prev) => new Map([...prev, [r.id, was]]));
      toast.error("Could not update");
    }
  };

  // ── Compare ────────────────────────────────────────────────────────────────
  const toggleCompare = (r, e) => {
    e.preventDefault();
    e.stopPropagation();
    setCompareList((prev) => {
      if (prev.find((x) => x.id === r.id)) return prev.filter((x) => x.id !== r.id);
      if (prev.length >= 3) { toast.error("Compare up to 3 researchers at once"); return prev; }
      return [...prev, r];
    });
  };

  // ── Filters ────────────────────────────────────────────────────────────────
  const setFilter = (key, val) => {
    setFilters((prev) => {
      if (!val && val !== true) { const { [key]: _, ...rest } = prev; return rest; }
      return { ...prev, [key]: val };
    });
  };

  const clearSearch = () => { setQ(""); setFilters({}); setItems([]); setSearched(false); };

  const activeTabData = sections?.[activeSection] || [];
  const hasSearch = !!debouncedQ || Object.values(filters).some(Boolean);

  // ── Total researchers count across sections ────────────────────────────────
  const totalInPlatform = sections
    ? Object.values(sections).reduce((acc, arr) => {
        const ids = new Set(acc.ids);
        (arr || []).forEach((r) => ids.add(r.id));
        return { count: ids.size, ids };
      }, { count: 0, ids: new Set() }).count
    : null;

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
      <HeroSection user={user} total={totalInPlatform} onExplore={() => explorerRef.current?.scrollIntoView({ behavior: "smooth" })} />

      {/* ── Recently Viewed ───────────────────────────────────────────────── */}
      {recentlyViewed.length > 0 && (
        <RecentlyViewedStrip researchers={recentlyViewed} isSaved={isSaved} toggleSave={toggleSave} />
      )}

      {/* ── AI Recommendations ────────────────────────────────────────────── */}
      {(aiRecsLoading || aiRecs) && (
        <AiRecsPanel recs={aiRecs} loading={aiRecsLoading} isSaved={isSaved} toggleSave={toggleSave} compareList={compareList} toggleCompare={toggleCompare} />
      )}

      {/* ── Discovery Sections ────────────────────────────────────────────── */}
      <DiscoverySections
        sections={sections}
        loading={sectionsLoading}
        activeSection={activeSection}
        setActiveSection={setActiveSection}
        isSaved={isSaved}
        toggleSave={toggleSave}
        compareList={compareList}
        toggleCompare={toggleCompare}
        user={user}
      />

      {/* ── Explorer ──────────────────────────────────────────────────────── */}
      <div ref={explorerRef} style={{ marginTop: 48 }}>
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 6 }}>
            Researcher Explorer
          </div>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: 28, color: NAVY, fontWeight: 400 }}>
            Search the Global Research Community
          </h2>
          <p style={{ fontSize: 13, color: "#64748B", marginTop: 6, lineHeight: 1.6 }}>
            Search by name, institution, country, research area, methods, ORCID — or apply filters.
          </p>
        </div>

        <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          {/* Filter sidebar */}
          <aside style={{ width: 220, flexShrink: 0, position: "sticky", top: 24 }}>
            <FilterPanel filters={filters} setFilter={setFilter} clearAll={clearSearch} />
          </aside>

          {/* Results */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Search input */}
            <div style={{ position: "relative", marginBottom: 12 }}>
              <Search size={14} strokeWidth={1.5} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94A3B8", pointerEvents: "none" }} />
              <input
                data-testid={TID.discoverySearch}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search name, institution, research area, ORCID, keywords…"
                style={{ width: "100%", padding: "10px 36px 10px 38px", border: `1px solid ${BORDER}`, background: "white", fontSize: 13, color: "#1E293B", outline: "none", boxSizing: "border-box" }}
                onFocus={(e) => { e.target.style.borderColor = NAVY; }}
                onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
              />
              {q && (
                <button onClick={() => setQ("")} style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", color: "#94A3B8", cursor: "pointer", display: "flex", alignItems: "center", background: "none", border: "none", outline: "none" }}>
                  <X size={13} strokeWidth={1.5} />
                </button>
              )}
            </div>

            {/* Results */}
            {!searched && !hasSearch && (
              <ExplorerPlaceholder onExplore={() => setFilter("available_for_collaboration", true)} />
            )}

            {loading && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 12 }}>
                {Array.from({ length: 9 }).map((_, i) => <ResearcherSkeleton key={i} />)}
              </div>
            )}

            {!loading && searched && items.length === 0 && (
              <SearchEmptyState q={debouncedQ} />
            )}

            {!loading && items.length > 0 && (
              <>
                <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 12, fontFamily: "monospace" }}>
                  {items.length} researcher{items.length !== 1 ? "s" : ""} found
                  {hasMore ? " (showing first batch)" : ""}
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 12 }}>
                  {items.map((r) => (
                    <ResearcherCard
                      key={r.id}
                      r={r}
                      isSaved={isSaved(r)}
                      onSave={toggleSave}
                      isCompared={compareList.some((x) => x.id === r.id)}
                      onCompare={toggleCompare}
                    />
                  ))}
                </div>
                {hasMore && (
                  <div style={{ textAlign: "center", marginTop: 24 }}>
                    <button
                      onClick={() => fetchResearchers(false)}
                      disabled={loading}
                      style={{ padding: "9px 24px", border: `1px solid ${BORDER}`, background: "white", fontSize: 13, fontWeight: 600, color: NAVY, cursor: "pointer", outline: "none" }}
                    >
                      Load more researchers
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── CTA strip ─────────────────────────────────────────────────────── */}
      <CollaborationStrip />

      {/* ── Compare panel ─────────────────────────────────────────────────── */}
      {compareList.length >= 2 && (
        <ComparePanel
          researchers={compareList}
          onRemove={(id) => setCompareList((p) => p.filter((x) => x.id !== id))}
          onClose={() => setCompareList([])}
        />
      )}
    </DiscoveryLayout>
  );
}

// ── Hero ──────────────────────────────────────────────────────────────────────
function HeroSection({ user, total, onExplore }) {
  const areas = (user?.research_areas || []).slice(0, 2).join(", ") || "your research";
  const institution = user?.institution || "your institution";

  return (
    <div
      style={{
        margin: "-24px -24px 0",
        background: `linear-gradient(145deg, #0B1E38 0%, ${NAVY} 55%, #163355 100%)`,
        padding: "48px 56px 0",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {/* Grid pattern */}
      <div style={{ position: "absolute", inset: 0, opacity: 0.035, backgroundImage: "linear-gradient(rgba(255,255,255,0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.4) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />
      {/* Radial glow */}
      <div style={{ position: "absolute", top: -120, right: 80, width: 400, height: 400, background: "radial-gradient(circle, rgba(138,21,56,0.15) 0%, transparent 70%)", pointerEvents: "none" }} />

      <div style={{ position: "relative" }}>
        {/* Kicker */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
          <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#818CF8" }} />
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>
            Academic Researcher Discovery
          </span>
        </div>

        {/* Headline */}
        <h1 style={{ fontFamily: "Georgia, serif", fontSize: 48, fontWeight: 400, color: "white", lineHeight: 1.07, marginBottom: 14, maxWidth: 580 }}>
          Discover Your<br />
          <span style={{ color: "rgba(255,255,255,0.6)", fontSize: 40 }}>Research Community</span>
        </h1>

        <p style={{ fontSize: 14, color: "rgba(255,255,255,0.48)", lineHeight: 1.7, maxWidth: 480, marginBottom: 30 }}>
          AI-powered matching for <strong style={{ color: "rgba(255,255,255,0.75)" }}>{areas}</strong> at{" "}
          <strong style={{ color: "rgba(255,255,255,0.75)" }}>{institution}</strong>.
          Find collaborators, mentors, reviewers and research partners worldwide.
        </p>

        {/* CTAs */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 36 }}>
          <button
            onClick={onExplore}
            style={{ padding: "10px 22px", background: "white", color: NAVY, fontSize: 13, fontWeight: 700, border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: 8, outline: "none" }}
          >
            <Search size={13} strokeWidth={2} /> Find Researchers
          </button>
          <Link
            to="/collaboration-requests"
            style={{ padding: "10px 22px", background: "transparent", color: "rgba(255,255,255,0.8)", fontSize: 13, fontWeight: 600, border: "1px solid rgba(255,255,255,0.2)", display: "flex", alignItems: "center", gap: 8, textDecoration: "none" }}
          >
            <UserPlus size={13} strokeWidth={1.5} /> Invite Collaborator
          </Link>
        </div>

        {/* Stats bar */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 0, borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: 20 }}>
          {[
            { Icon: Users,         label: "Researchers",       val: total != null ? `${total}+` : "—" },
            { Icon: Globe,         label: "Countries",         val: "50+" },
            { Icon: Building2,     label: "Institutions",      val: "100+" },
            { Icon: Sparkles,      label: "AI Matched",        val: "Always" },
          ].map(({ Icon, label, val }) => (
            <div key={label} style={{ padding: "12px 16px 12px 0" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 3 }}>
                <Icon size={9} strokeWidth={1.5} style={{ color: "rgba(255,255,255,0.3)" }} />
                <span style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 600 }}>{label}</span>
              </div>
              <div style={{ fontSize: 22, fontWeight: 800, color: "white", fontFamily: "monospace" }}>{val}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Recently Viewed strip ─────────────────────────────────────────────────────
function RecentlyViewedStrip({ researchers, isSaved, toggleSave }) {
  return (
    <div style={{ margin: "20px 0 0", padding: "14px 0 16px", borderBottom: `1px solid ${BORDER}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <Clock size={11} strokeWidth={1.5} style={{ color: "#94A3B8" }} />
        <span style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em" }}>Recently Viewed</span>
      </div>
      <div style={{ display: "flex", gap: 10, overflowX: "auto", paddingBottom: 4 }}>
        {researchers.map((r) => (
          <Link
            key={r.id}
            to={profileUrl(r)}
            style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 12px", border: `1px solid ${BORDER}`, background: "white", textDecoration: "none", flexShrink: 0, transition: "border-color 150ms" }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = NAVY}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = BORDER}
          >
            <AvatarCircle r={r} size={28} />
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: NAVY, whiteSpace: "nowrap" }}>{r.full_name}</div>
              <div style={{ fontSize: 10, color: "#94A3B8", whiteSpace: "nowrap" }}>{r.institution || r.country || "Researcher"}</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

// ── AI Recommendations panel ──────────────────────────────────────────────────
function AiRecsPanel({ recs, loading, isSaved, toggleSave, compareList, toggleCompare }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div style={{ background: `${NAVY}05`, borderBottom: `1px solid ${BORDER}`, padding: "18px 0 20px", marginTop: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: expanded ? 14 : 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Sparkles size={13} strokeWidth={1.5} style={{ color: NAVY }} />
          <span style={{ fontSize: 12, fontWeight: 700, color: NAVY, textTransform: "uppercase", letterSpacing: "0.08em" }}>AI Recommendations</span>
          <span style={{ fontSize: 11, color: "#94A3B8" }}>Powered by your research profile</span>
        </div>
        <button onClick={() => setExpanded((v) => !v)} style={{ color: "#94A3B8", cursor: "pointer", display: "flex", alignItems: "center", background: "none", border: "none", outline: "none" }}>
          <ChevronDown size={13} strokeWidth={1.5} style={{ transform: expanded ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 200ms" }} />
        </button>
      </div>

      {expanded && (
        <div style={{ display: "flex", gap: 12, overflowX: "auto", paddingBottom: 4 }}>
          {loading
            ? Array.from({ length: 4 }).map((_, i) => <ResearcherCardCompact key={i} loading />)
            : (recs || []).slice(0, 7).map((r, i) => (
                <ResearcherCardCompact
                  key={r.id || i}
                  r={r}
                  isSaved={isSaved(r)}
                  onSave={toggleSave}
                  isCompared={compareList.some((x) => x.id === r.id)}
                  onCompare={toggleCompare}
                  showExplanation
                />
              ))
          }
        </div>
      )}
    </div>
  );
}

// ── Discovery Sections ────────────────────────────────────────────────────────
function DiscoverySections({ sections, loading, activeSection, setActiveSection, isSaved, toggleSave, compareList, toggleCompare, user }) {
  const activeSectionData = sections?.[activeSection] || [];
  const hasData = activeSectionData.length > 0;

  return (
    <div style={{ marginTop: 32 }}>
      {/* Section title */}
      <div style={{ marginBottom: 16, display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 5 }}>Research Network</div>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: 28, color: NAVY, fontWeight: 400 }}>Curated for You</h2>
        </div>
        {!loading && sections && (
          <span style={{ fontSize: 12, color: "#94A3B8" }}>
            {SECTION_TABS.find((t) => t.key === activeSection)?.desc}
          </span>
        )}
      </div>

      {/* Tab strip */}
      <div style={{ display: "flex", gap: 0, overflowX: "auto", borderBottom: `1px solid ${BORDER}`, marginBottom: 20 }}>
        {SECTION_TABS.map((tab) => {
          const count = sections?.[tab.key]?.length || 0;
          const isActive = tab.key === activeSection;
          const hidden = !loading && sections && count === 0 && tab.key !== "recommended";
          if (hidden) return null;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveSection(tab.key)}
              style={{ display: "flex", alignItems: "center", gap: 5, padding: "8px 14px", fontSize: 12, fontWeight: isActive ? 700 : 500, color: isActive ? NAVY : "#64748B", borderBottom: `2px solid ${isActive ? NAVY : "transparent"}`, cursor: "pointer", background: "none", border: "none", borderBottomStyle: "solid", borderBottomWidth: 2, borderBottomColor: isActive ? NAVY : "transparent", whiteSpace: "nowrap", outline: "none", transition: "color 150ms" }}
            >
              <tab.icon size={11} strokeWidth={1.5} />
              {tab.label}
              {count > 0 && <span style={{ fontSize: 9, color: "#94A3B8", fontFamily: "monospace" }}>({count})</span>}
            </button>
          );
        })}
      </div>

      {/* Cards */}
      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 12 }}>
          {Array.from({ length: 8 }).map((_, i) => <ResearcherSkeleton key={i} />)}
        </div>
      ) : !hasData ? (
        <SectionEmptyState activeSection={activeSection} user={user} />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 12 }}>
          {activeSectionData.map((r) => (
            <ResearcherCard
              key={r.id}
              r={r}
              isSaved={isSaved(r)}
              onSave={toggleSave}
              isCompared={compareList.some((x) => x.id === r.id)}
              onCompare={toggleCompare}
              showMatchScore={activeSection === "recommended" && r.match_score > 0}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Avatar circle ─────────────────────────────────────────────────────────────
function AvatarCircle({ r, size = 44 }) {
  const [imgError, setImgError] = useState(false);
  const bg = NAVY;

  if (r?.avatar_url && !imgError) {
    return (
      <img
        src={r.avatar_url}
        alt={r.full_name || ""}
        onError={() => setImgError(true)}
        style={{ width: size, height: size, borderRadius: "50%", objectFit: "cover", flexShrink: 0, border: "1.5px solid #E4E8EF" }}
      />
    );
  }

  return (
    <div style={{
      width: size,
      height: size,
      borderRadius: "50%",
      background: bg,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flexShrink: 0,
      fontSize: Math.round(size * 0.34),
      fontWeight: 700,
      color: "white",
      letterSpacing: "0.02em",
    }}>
      {initials(r?.full_name)}
    </div>
  );
}

// ── Researcher Card (full) ─────────────────────────────────────────────────────
function ResearcherCard({ r, isSaved, onSave, isCompared, onCompare, showMatchScore }) {
  const orcidPresent = hasOrcid(r);
  const areas = (r.research_areas || []).slice(0, 3);
  const saved = isSaved;

  return (
    <Link
      to={profileUrl(r)}
      data-testid={TID.discoverResearcherCard(r.id)}
      style={{ display: "flex", flexDirection: "column", border: `1px solid ${BORDER}`, background: "white", textDecoration: "none", transition: "border-color 150ms, box-shadow 150ms, transform 150ms", overflow: "hidden" }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY; e.currentTarget.style.boxShadow = "0 4px 16px rgba(15,40,71,0.08)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "translateY(0)"; }}
    >
      {/* Card body */}
      <div style={{ padding: "16px 16px 12px", flex: 1 }}>
        {/* Header row */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
          {/* Avatar with optional score ring */}
          <div style={{ position: "relative", flexShrink: 0 }}>
            <AvatarCircle r={r} size={44} />
            {showMatchScore && r.match_score > 0 && (
              <div style={{
                position: "absolute",
                bottom: -4,
                right: -4,
                width: 20,
                height: 20,
                borderRadius: "50%",
                background: NAVY,
                border: "2px solid white",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 7,
                fontWeight: 800,
                color: "white",
                fontFamily: "monospace",
              }}>
                {Math.min(r.match_score, 99)}
              </div>
            )}
          </div>

          {/* Name + role */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 4, flexWrap: "wrap" }}>
              <h3 style={{ fontFamily: "Georgia, serif", fontSize: 14, color: "#0F172A", lineHeight: 1.25, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "100%" }}>
                {r.full_name || "Researcher"}
              </h3>
              {orcidPresent && (
                <span style={{ fontSize: 8, fontWeight: 700, color: "#15803D", background: "#DCFCE7", padding: "1px 4px", borderRadius: 2, flexShrink: 0, marginTop: 2 }}>ORCID</span>
              )}
            </div>
            {r.academic_role && (
              <div style={{ fontSize: 11, color: "#64748B", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.academic_role}</div>
            )}
          </div>

          {/* Save button */}
          <button
            onClick={(e) => onSave(r, e)}
            title={saved ? "Remove from saved" : "Save researcher"}
            style={{ flexShrink: 0, color: saved ? NAVY : "#CBD5E1", cursor: "pointer", display: "flex", alignItems: "center", background: "none", border: "none", outline: "none", padding: 2 }}
          >
            {saved ? <BookmarkCheck size={14} strokeWidth={1.5} /> : <Bookmark size={14} strokeWidth={1.5} />}
          </button>
        </div>

        {/* Institution / Location */}
        <div style={{ marginBottom: 8 }}>
          {r.institution && (
            <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 2 }}>
              <Building2 size={10} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0 }} />
              <span style={{ fontSize: 11, color: "#374151", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.institution}</span>
            </div>
          )}
          {(r.country || r.city) && (
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <MapPin size={10} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0 }} />
              <span style={{ fontSize: 11, color: "#64748B" }}>{[r.city, r.country].filter(Boolean).join(", ")}</span>
            </div>
          )}
        </div>

        {/* Research areas */}
        {areas.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 }}>
            {areas.map((a, i) => (
              <span key={i} style={{ fontSize: 9, color: "#374151", background: WARM, border: `1px solid ${BORDER}`, padding: "2px 6px" }}>{a}</span>
            ))}
            {(r.research_areas || []).length > 3 && (
              <span style={{ fontSize: 9, color: "#94A3B8" }}>+{r.research_areas.length - 3}</span>
            )}
          </div>
        )}

        {/* Metrics row */}
        {(r.h_index > 0 || r.publications_count > 0) && (
          <div style={{ display: "flex", gap: 12, marginBottom: 8 }}>
            {r.h_index > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 3 }}>
                <TrendingUp size={9} strokeWidth={1.5} style={{ color: "#94A3B8" }} />
                <span style={{ fontSize: 10, color: "#64748B" }}>h={r.h_index}</span>
              </div>
            )}
            {r.publications_count > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 3 }}>
                <BookOpen size={9} strokeWidth={1.5} style={{ color: "#94A3B8" }} />
                <span style={{ fontSize: 10, color: "#64748B" }}>{r.publications_count} pub{r.publications_count !== 1 ? "s" : ""}</span>
              </div>
            )}
          </div>
        )}

        {/* Availability badges */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
          {r.available_for_collaboration && (
            <span style={{ fontSize: 9, fontWeight: 600, color: EMERALD, background: "#ECFDF5", border: "1px solid #A7F3D0", padding: "2px 6px" }}>Open to collaborate</span>
          )}
          {r.available_for_reviewing && (
            <span style={{ fontSize: 9, fontWeight: 600, color: "#7C3AED", background: "#F5F3FF", border: "1px solid #DDD6FE", padding: "2px 6px" }}>Peer reviewer</span>
          )}
          {r.available_for_supervision && (
            <span style={{ fontSize: 9, fontWeight: 600, color: "#0369A1", background: "#F0F9FF", border: "1px solid #BAE6FD", padding: "2px 6px" }}>Supervisor</span>
          )}
        </div>
      </div>

      {/* Card footer */}
      <div
        style={{ borderTop: `1px solid ${BORDER}`, padding: "7px 16px", display: "flex", gap: 10, background: "#FAFBFC", alignItems: "center" }}
        onClick={(e) => e.preventDefault()}
      >
        <Link
          to={profileUrl(r)}
          onClick={(e) => e.stopPropagation()}
          style={{ fontSize: 10, fontWeight: 700, color: NAVY, display: "flex", alignItems: "center", gap: 3, textDecoration: "none" }}
        >
          View Profile <ArrowRight size={9} strokeWidth={2} />
        </Link>
        <span style={{ color: "#E2E8F0" }}>|</span>
        <button
          onClick={(e) => onCompare(r, e)}
          style={{ fontSize: 10, fontWeight: 600, color: isCompared ? NAVY : "#94A3B8", cursor: "pointer", display: "flex", alignItems: "center", gap: 3, background: "none", border: "none", outline: "none", padding: 0, textDecoration: isCompared ? "underline" : "none" }}
        >
          <BarChart2 size={10} strokeWidth={1.5} /> Compare
        </button>
        <span style={{ color: "#E2E8F0" }}>|</span>
        <Link
          to="/collaboration-requests"
          onClick={(e) => e.stopPropagation()}
          state={{ preselected_user_id: r.id }}
          style={{ fontSize: 10, fontWeight: 600, color: "#94A3B8", display: "flex", alignItems: "center", gap: 3, textDecoration: "none" }}
        >
          <UserPlus size={10} strokeWidth={1.5} /> Collab
        </Link>
      </div>
    </Link>
  );
}

// ── Compact card (for recommendations / recently viewed panels) ───────────────
function ResearcherCardCompact({ r, isSaved, onSave, isCompared, onCompare, showExplanation, loading: cardLoading }) {
  if (cardLoading) {
    return (
      <div style={{ minWidth: 220, maxWidth: 260, flexShrink: 0, border: `1px solid ${BORDER}`, background: "white", padding: 14 }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "center" }}>
          <div className="sq-pulse" style={{ width: 36, height: 36, borderRadius: "50%", background: "#F1F5F9", flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div className="sq-pulse" style={{ height: 13, width: "80%", background: "#F1F5F9", marginBottom: 5 }} />
            <div className="sq-pulse" style={{ height: 10, width: "55%", background: "#F1F5F9" }} />
          </div>
        </div>
        <div className="sq-pulse" style={{ height: 10, width: "70%", background: "#F1F5F9", marginBottom: 6 }} />
        <div className="sq-pulse" style={{ height: 24, background: "#F1F5F9" }} />
      </div>
    );
  }

  const score = r?.match_score || r?.score;

  return (
    <Link
      to={profileUrl(r)}
      style={{ display: "block", minWidth: 220, maxWidth: 260, flexShrink: 0, border: `1px solid ${BORDER}`, background: "white", padding: 14, textDecoration: "none", transition: "border-color 150ms" }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; }}
    >
      <div style={{ display: "flex", gap: 8, alignItems: "flex-start", marginBottom: 8 }}>
        {score != null && score > 0 ? (
          <div style={{ position: "relative", flexShrink: 0 }}>
            <AvatarCircle r={r} size={36} />
            <div style={{ position: "absolute", bottom: -3, right: -3, width: 16, height: 16, borderRadius: "50%", background: NAVY, border: "2px solid white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 6, fontWeight: 800, color: "white", fontFamily: "monospace" }}>
              {Math.min(Math.round(score), 99)}
            </div>
          </div>
        ) : (
          <AvatarCircle r={r} size={36} />
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: NAVY, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontFamily: "Georgia, serif" }}>{r?.full_name}</div>
          <div style={{ fontSize: 10, color: "#64748B", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r?.institution || r?.country || ""}</div>
        </div>
        <button onClick={(e) => onSave && onSave(r, e)} style={{ color: isSaved ? NAVY : "#CBD5E1", cursor: "pointer", flexShrink: 0, background: "none", border: "none", outline: "none" }}>
          {isSaved ? <BookmarkCheck size={12} strokeWidth={1.5} /> : <Bookmark size={12} strokeWidth={1.5} />}
        </button>
      </div>

      {(r?.research_areas || []).slice(0, 2).length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 3, marginBottom: 6 }}>
          {(r.research_areas || []).slice(0, 2).map((a, i) => (
            <span key={i} style={{ fontSize: 8, color: "#374151", background: WARM, border: `1px solid ${BORDER}`, padding: "1px 5px" }}>{a}</span>
          ))}
        </div>
      )}

      {showExplanation && r?.explanation && (
        <div style={{ fontSize: 10, color: "#94A3B8", fontStyle: "italic", lineHeight: 1.4 }}>{r.explanation}</div>
      )}
    </Link>
  );
}

// ── Researcher skeleton ───────────────────────────────────────────────────────
function ResearcherSkeleton() {
  return (
    <div style={{ border: `1px solid ${BORDER}`, background: "white" }}>
      <div style={{ padding: "16px 16px 12px" }}>
        <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
          <div className="sq-pulse" style={{ width: 44, height: 44, borderRadius: "50%", background: "#F1F5F9", flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div className="sq-pulse" style={{ height: 14, width: "75%", background: "#F1F5F9", marginBottom: 6 }} />
            <div className="sq-pulse" style={{ height: 11, width: "55%", background: "#F1F5F9" }} />
          </div>
        </div>
        <div className="sq-pulse" style={{ height: 11, width: "70%", background: "#F1F5F9", marginBottom: 5 }} />
        <div className="sq-pulse" style={{ height: 11, width: "50%", background: "#F1F5F9", marginBottom: 10 }} />
        <div style={{ display: "flex", gap: 4 }}>
          {[45, 60, 50].map((w, i) => <div key={i} className="sq-pulse" style={{ height: 16, width: w, background: "#F1F5F9" }} />)}
        </div>
      </div>
      <div style={{ borderTop: `1px solid ${BORDER}`, padding: "7px 16px", background: "#FAFBFC" }}>
        <div className="sq-pulse" style={{ height: 10, width: "45%", background: "#F1F5F9" }} />
      </div>
    </div>
  );
}

// ── Filter panel ──────────────────────────────────────────────────────────────
function FilterPanel({ filters, setFilter, clearAll }) {
  return (
    <div style={{ background: "white", border: `1px solid ${BORDER}`, padding: "16px 14px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.1em" }}>Filters</span>
        {Object.values(filters).some(Boolean) && (
          <button onClick={clearAll} style={{ fontSize: 10, color: "#94A3B8", cursor: "pointer", background: "none", border: "none", outline: "none", textDecoration: "underline" }}>Clear</button>
        )}
      </div>

      {/* Availability */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Availability</div>
        {[
          { key: "available_for_collaboration", label: "Open to collaborate" },
          { key: "available_for_reviewing",     label: "Peer reviewer" },
          { key: "available_for_supervision",   label: "Supervisor / mentor" },
        ].map(({ key, label }) => (
          <label key={key} style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 7, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={!!filters[key]}
              onChange={(e) => setFilter(key, e.target.checked || "")}
              style={{ accentColor: NAVY, width: 13, height: 13, flexShrink: 0 }}
            />
            <span style={{ fontSize: 12, color: "#374151" }}>{label}</span>
          </label>
        ))}
      </div>

      {/* Identifiers */}
      <div style={{ marginBottom: 14, borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Identifiers</div>
        <label style={{ display: "flex", alignItems: "center", gap: 7, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={!!filters.has_orcid}
            onChange={(e) => setFilter("has_orcid", e.target.checked || "")}
            style={{ accentColor: NAVY, width: 13, height: 13, flexShrink: 0 }}
          />
          <span style={{ fontSize: 12, color: "#374151" }}>Has ORCID</span>
        </label>
      </div>

      {/* Country */}
      <div style={{ marginBottom: 14, borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Country</div>
        <input
          value={filters.country || ""}
          onChange={(e) => setFilter("country", e.target.value)}
          placeholder="e.g. Romania"
          style={{ width: "100%", padding: "6px 8px", border: `1px solid ${BORDER}`, fontSize: 12, color: "#374151", outline: "none", boxSizing: "border-box" }}
          onFocus={(e) => { e.target.style.borderColor = NAVY; }}
          onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
        />
      </div>

      {/* Institution */}
      <div style={{ marginBottom: 14, borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Institution</div>
        <input
          value={filters.institution || ""}
          onChange={(e) => setFilter("institution", e.target.value)}
          placeholder="e.g. MIT"
          style={{ width: "100%", padding: "6px 8px", border: `1px solid ${BORDER}`, fontSize: 12, color: "#374151", outline: "none", boxSizing: "border-box" }}
          onFocus={(e) => { e.target.style.borderColor = NAVY; }}
          onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
        />
      </div>

      {/* Research area */}
      <div style={{ marginBottom: 14, borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Research Area</div>
        <input
          value={filters.research_area || ""}
          onChange={(e) => setFilter("research_area", e.target.value)}
          placeholder="e.g. Machine Learning"
          style={{ width: "100%", padding: "6px 8px", border: `1px solid ${BORDER}`, fontSize: 12, color: "#374151", outline: "none", boxSizing: "border-box" }}
          onFocus={(e) => { e.target.style.borderColor = NAVY; }}
          onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
        />
      </div>

      {/* Min H-index */}
      <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Min H-Index</div>
        <input
          type="number"
          min={0}
          value={filters.min_h_index || ""}
          onChange={(e) => setFilter("min_h_index", e.target.value)}
          placeholder="e.g. 5"
          style={{ width: "100%", padding: "6px 8px", border: `1px solid ${BORDER}`, fontSize: 12, color: "#374151", outline: "none", boxSizing: "border-box" }}
          onFocus={(e) => { e.target.style.borderColor = NAVY; }}
          onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
        />
      </div>
    </div>
  );
}

// ── Section empty state ───────────────────────────────────────────────────────
function SectionEmptyState({ activeSection, user }) {
  const HINTS = {
    recommended:             ["Complete your research profile", "Add research interests and keywords", "Connect your ORCID account"],
    institutional_matches:   ["Add your institution to your profile", "Other researchers from your institution will appear here"],
    methodology_experts:     ["Add your methods and techniques to your profile", "Researchers using your methods will appear here"],
    international_matches:   ["Add research areas to find international collaborators", "Expand your research profile for better global matching"],
    available_reviewers:     ["No researchers have indicated they're available for reviewing", "Try the 'Open to Collaborate' tab instead"],
    recently_active:         ["No recently active researchers found", "Check back soon"],
    top_scholars:            ["No scholars with h-index data found", "This section updates as profiles are connected to OpenAlex"],
    available_collaborators: ["No researchers have indicated availability for collaboration", "Try searching manually below"],
  };
  const hints = HINTS[activeSection] || ["No researchers found for this section"];

  return (
    <div style={{ textAlign: "center", padding: "48px 24px", border: `1px dashed ${BORDER}` }}>
      <Users size={40} strokeWidth={1} style={{ color: "#E2E8F0", margin: "0 auto 16px", display: "block" }} />
      <h3 style={{ fontFamily: "Georgia, serif", fontSize: 20, color: "#1E293B", marginBottom: 6, fontWeight: 400 }}>
        No researchers in this section yet
      </h3>
      <p style={{ fontSize: 13, color: "#64748B", marginBottom: 20, lineHeight: 1.6 }}>
        {activeSection === "recommended" ? "AI matching needs more profile data to make recommendations." : "This section is populated as researchers join and complete their profiles."}
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 7, maxWidth: 360, margin: "0 auto" }}>
        {hints.map((h) => (
          <div key={h} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 12, color: "#64748B", textAlign: "left" }}>
            <Lightbulb size={12} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0, marginTop: 2 }} />
            {h}
          </div>
        ))}
      </div>
      {activeSection === "recommended" && (
        <Link to="/academic-passport" style={{ display: "inline-flex", alignItems: "center", gap: 5, marginTop: 20, padding: "8px 18px", background: NAVY, color: "white", fontSize: 12, fontWeight: 700, textDecoration: "none" }}>
          Complete Profile <ArrowRight size={11} strokeWidth={2} />
        </Link>
      )}
    </div>
  );
}

// ── Explorer placeholder ──────────────────────────────────────────────────────
function ExplorerPlaceholder({ onExplore }) {
  const TIPS = [
    { Icon: Search,     text: 'Search by name — e.g. "Sarah Johnson"' },
    { Icon: Building2,  text: 'Filter by institution or department' },
    { Icon: Globe,      text: 'Find researchers in a specific country' },
    { Icon: FlaskConical, text: 'Discover methodology experts' },
    { Icon: CheckCircle, text: 'Filter by open-to-collaborate' },
    { Icon: Award,      text: 'Filter by minimum h-index' },
  ];

  return (
    <div style={{ border: `1px dashed ${BORDER}`, padding: "40px 32px", textAlign: "center" }}>
      <Search size={40} strokeWidth={1} style={{ color: "#E2E8F0", margin: "0 auto 16px", display: "block" }} />
      <h3 style={{ fontFamily: "Georgia, serif", fontSize: 20, color: "#1E293B", marginBottom: 6, fontWeight: 400 }}>
        Search the Research Community
      </h3>
      <p style={{ fontSize: 13, color: "#64748B", maxWidth: 420, margin: "0 auto 24px", lineHeight: 1.65 }}>
        Use the search bar to find researchers by name, institution, keywords, or research area.
        Use the filters for more specific discovery.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8, maxWidth: 500, margin: "0 auto 24px" }}>
        {TIPS.map(({ Icon, text }) => (
          <div key={text} style={{ display: "flex", alignItems: "flex-start", gap: 7, fontSize: 12, color: "#64748B", textAlign: "left", padding: "6px 8px", background: WARM, border: `1px solid ${BORDER}` }}>
            <Icon size={12} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0, marginTop: 2 }} />
            {text}
          </div>
        ))}
      </div>
      <button
        onClick={onExplore}
        style={{ padding: "8px 18px", background: NAVY, color: "white", fontSize: 12, fontWeight: 700, border: "none", cursor: "pointer", outline: "none", display: "inline-flex", alignItems: "center", gap: 6 }}
      >
        <UserPlus size={12} strokeWidth={2} /> Show Available Collaborators
      </button>
    </div>
  );
}

// ── Search empty state ────────────────────────────────────────────────────────
function SearchEmptyState({ q }) {
  return (
    <div style={{ textAlign: "center", padding: "48px 24px", border: `1px dashed ${BORDER}` }}>
      <Users size={40} strokeWidth={1} style={{ color: "#E2E8F0", margin: "0 auto 16px", display: "block" }} />
      <h3 style={{ fontFamily: "Georgia, serif", fontSize: 20, color: "#1E293B", marginBottom: 6, fontWeight: 400 }}>
        No researchers match "{q}"
      </h3>
      <p style={{ fontSize: 13, color: "#64748B", maxWidth: 360, margin: "0 auto", lineHeight: 1.65 }}>
        Try searching by a different term — institution name, research area, city, or keywords.
        Profiles are public only when researchers opt in.
      </p>
    </div>
  );
}

// ── Collaboration CTA strip ───────────────────────────────────────────────────
function CollaborationStrip() {
  const ACTIONS = [
    { label: "Send Collaboration Request", desc: "Propose a joint research project", to: "/collaboration-requests", icon: UserPlus },
    { label: "Collab Intelligence",        desc: "AI-powered team matching",         to: "/collaboration-intelligence", icon: Sparkles },
    { label: "Reviewer Marketplace",       desc: "Find peer reviewers for your work",to: "/reviewer-marketplace",      icon: CheckCircle },
    { label: "Grant Collaboration Hub",    desc: "Build research consortia",         to: "/grant-collaboration-hub",   icon: Award },
    { label: "Research Network",           desc: "Visualise your connections",       to: "/network",                   icon: Activity },
    { label: "Invite to Workspace",        desc: "Collaborate in a shared space",    to: "/workspaces",                icon: Users },
  ];

  return (
    <div style={{ margin: "48px -24px 0", background: WARM, borderTop: `1px solid ${BORDER}`, padding: "36px 56px" }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 6 }}>Collaboration Tools</div>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: 26, color: NAVY, fontWeight: 400 }}>Start Collaborating</h2>
          <p style={{ fontSize: 13, color: "#64748B", marginTop: 6, maxWidth: 480, lineHeight: 1.6 }}>
            Synaptiq supports every stage of academic collaboration — from discovering partners to running joint projects.
          </p>
        </div>
        <Link to="/network" style={{ fontSize: 13, fontWeight: 700, color: NAVY, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 6, padding: "9px 18px", border: `1.5px solid ${NAVY}`, alignSelf: "flex-start", whiteSpace: "nowrap" }}>
          My Research Network <ArrowRight size={13} strokeWidth={2} />
        </Link>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(168px, 1fr))", gap: 12 }}>
        {ACTIONS.map(({ label, desc, to, icon: Icon }) => (
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
function ComparePanel({ researchers, onRemove, onClose }) {
  const METRICS = [
    { label: "Role",           fn: (r) => r.academic_role || "—" },
    { label: "Institution",    fn: (r) => r.institution || "—" },
    { label: "Country",        fn: (r) => r.country || "—" },
    { label: "H-Index",        fn: (r) => r.h_index > 0 ? r.h_index : "—" },
    { label: "Publications",   fn: (r) => r.publications_count > 0 ? r.publications_count : "—" },
    { label: "Research areas", fn: (r) => (r.research_areas || []).slice(0, 2).join(", ") || "—" },
    { label: "Collab open",    fn: (r) => r.available_for_collaboration ? "Yes" : "No" },
    { label: "Reviewer",       fn: (r) => r.available_for_reviewing ? "Yes" : "No" },
    { label: "Supervisor",     fn: (r) => r.available_for_supervision ? "Yes" : "No" },
    { label: "ORCID",          fn: (r) => hasOrcid(r) ? "Verified" : "—" },
  ];

  return (
    <div style={{ position: "fixed", bottom: 0, left: 0, right: 0, background: NAVY, color: "white", padding: "14px 24px", zIndex: 200, boxShadow: "0 -8px 32px rgba(0,0,0,0.35)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <BarChart2 size={13} strokeWidth={1.5} style={{ color: "rgba(255,255,255,0.5)" }} />
          <span style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>
            Comparing {researchers.length} researchers
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
              <th style={{ width: 90, padding: "4px 12px 4px 0", textAlign: "left", fontSize: 9, color: "rgba(255,255,255,0.3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", borderBottom: "1px solid rgba(255,255,255,0.08)" }} />
              {researchers.map((r) => (
                <th key={r.id} style={{ padding: "4px 14px", textAlign: "left", borderBottom: "1px solid rgba(255,255,255,0.08)", minWidth: 160 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                    <AvatarCircle r={r} size={22} />
                    <span style={{ fontSize: 12, fontWeight: 700, color: "white", fontFamily: "Georgia, serif" }}>{r.full_name}</span>
                  </div>
                  <button onClick={() => onRemove(r.id)} style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 2, background: "none", border: "none", outline: "none", padding: 0, marginTop: 2 }}>
                    <X size={7} strokeWidth={1.5} /> Remove
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRICS.map(({ label, fn }) => (
              <tr key={label}>
                <td style={{ padding: "3px 12px 3px 0", fontSize: 9, color: "rgba(255,255,255,0.4)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", whiteSpace: "nowrap", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{label}</td>
                {researchers.map((r) => (
                  <td key={r.id} style={{ padding: "3px 14px", fontSize: 11, color: "rgba(255,255,255,0.8)", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{fn(r)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

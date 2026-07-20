import React, { useState, useEffect, useCallback, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { ACCENT, EMERALD, NAVY, WARM } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import {
  Search, X, ChevronDown, ChevronLeft, ChevronRight, ArrowRight,
  CheckCircle, Award, Shield, Globe, Building2, MapPin, BookOpen,
  Users, Sparkles, BarChart2, FileText, FlaskConical, Star, Clock,
  UserCheck, TrendingUp, Plus, GraduationCap, Lightbulb, AlertCircle,
  Microscope, ClipboardCheck,
} from "lucide-react";

// ── Design tokens ─────────────────────────────────────────────────────────────
const BORDER  = "#E4E8EF";

// ── Helpers ───────────────────────────────────────────────────────────────────
function cap(s) {
  if (!s) return "";
  return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ");
}

function computeSlug(name) {
  let s = (name || "").toLowerCase().trim();
  s = s.replace(/[^a-z0-9\s-]/g, "");
  s = s.replace(/\s+/g, "-");
  s = s.replace(/-+/g, "-").replace(/^-|-$/g, "");
  return s || "reviewer";
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

function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

// ── Reviewer level labels ──────────────────────────────────────────────────────
const LEVEL_LABEL = {
  1: "New Reviewer",
  2: "Junior Reviewer",
  3: "Experienced Reviewer",
  4: "Senior Reviewer",
  5: "Expert Reviewer",
};
const LEVEL_STYLE = {
  1: { color: "#64748B", bg: "#F8FAFC" },
  2: { color: "#0369A1", bg: "#F0F9FF" },
  3: { color: "#0F2847", bg: "#EFF6FF" },
  4: { color: "#065F46", bg: "#ECFDF5" },
  5: { color: "#92400E", bg: "#FFFBEB" },
};

// ── Availability config ────────────────────────────────────────────────────────
const AVAIL_CONFIG = {
  available:   { dot: EMERALD,  text: "Available",   bg: "#ECFDF5", border: "#A7F3D0" },
  busy:        { dot: "#D97706", text: "Busy",        bg: "#FFFBEB", border: "#FCD34D" },
  unavailable: { dot: "#94A3B8", text: "Unavailable", bg: "#F8FAFC", border: "#CBD5E1" },
};

// ── Review type config ─────────────────────────────────────────────────────────
const REVIEW_TYPES_LIST = [
  { value: "manuscript",   label: "Journal Manuscript",    icon: FileText },
  { value: "conference",   label: "Conference Paper",      icon: Users },
  { value: "grant",        label: "Grant Proposal",        icon: Award },
  { value: "thesis",       label: "Doctoral Thesis",       icon: GraduationCap },
  { value: "dissertation", label: "Master's Dissertation", icon: BookOpen },
  { value: "methodology",  label: "Methodology Review",    icon: FlaskConical },
  { value: "statistical",  label: "Statistical Review",    icon: BarChart2 },
  { value: "custom",       label: "Custom Review",         icon: ClipboardCheck },
];

const PAGE_SIZE = 20;

// ── Main component ────────────────────────────────────────────────────────────
export default function ReviewerMarketplace() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const explorerRef = useRef(null);

  // Reviewer list
  const [items,   setItems]   = useState([]);
  const [total,   setTotal]   = useState(0);
  const [pages,   setPages]   = useState(1);
  const [page,    setPage]    = useState(1);
  const [loading, setLoading] = useState(false);
  const [gated,   setGated]   = useState(false);

  // Search & filters
  const [q,          setQ]          = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [filters,    setFilters]    = useState({});

  // AI recommendations
  const [recs,        setRecs]        = useState(null);
  const [recsLoading, setRecsLoading] = useState(true);

  // Open requests
  const [openRequests, setOpenRequests] = useState([]);

  // My reviewer profile
  const [myProfile, setMyProfile] = useState(null);

  // Create request modal
  const [showCreate, setShowCreate] = useState(false);

  // Compare panel (client-side)
  const [compareList, setCompareList] = useState([]);

  // ── Debounce q ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 400);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => { setPage(1); }, [debouncedQ, filters]);

  // ── Boot ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    api.get("/recommendations/reviewers?limit=8")
      .then((r) => {
        const raw = r.data;
        const list = Array.isArray(raw) ? raw : (raw?.results || []);
        setRecs(list.length > 0 ? list : null);
      })
      .catch(() => setRecs(null))
      .finally(() => setRecsLoading(false));

    api.get("/reviewer-marketplace/requests?visibility=public&status=open&limit=6")
      .then((r) => setOpenRequests(r.data?.items || []))
      .catch(() => {});

    api.get("/reviewer-marketplace/profile/me")
      .then((r) => setMyProfile(r.data))
      .catch(() => {});
  }, []);

  // ── Fetch reviewers ────────────────────────────────────────────────────────
  const filtersKey = JSON.stringify(filters);
  const fetchReviewers = useCallback(async () => {
    setLoading(true);
    setGated(false);
    try {
      const params = {
        page,
        limit: PAGE_SIZE,
        ...(filters.research_area      && { research_area: filters.research_area }),
        ...(filters.country            && { country: filters.country }),
        ...(filters.methods_expertise  && { methods_expertise: filters.methods_expertise }),
        ...(filters.availability_status && { availability_status: filters.availability_status }),
        ...(filters.verified_reviewer  && { verified_reviewer: true }),
        ...(filters.reviewer_level     && { reviewer_level: parseInt(filters.reviewer_level) }),
      };
      const { data } = await api.get("/reviewer-marketplace/reviewers", { params });
      setItems(data.items || []);
      setTotal(data.total || 0);
      setPages(data.pages || 1);
    } catch (err) {
      if (err?.response?.status === 402 || err?.response?.status === 429) setGated(true);
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, filtersKey, debouncedQ]);

  useEffect(() => { fetchReviewers(); }, [fetchReviewers]);

  // ── Compare ────────────────────────────────────────────────────────────────
  const toggleCompare = (r, e) => {
    e.preventDefault();
    e.stopPropagation();
    setCompareList((prev) => {
      if (prev.find((x) => x.user_id === r.user_id)) return prev.filter((x) => x.user_id !== r.user_id);
      if (prev.length >= 3) { toast.error("Compare up to 3 reviewers at once"); return prev; }
      return [...prev, r];
    });
  };

  // ── Filter helpers ─────────────────────────────────────────────────────────
  const setFilter = (key, val) => {
    setFilters((prev) => {
      if (!val) { const { [key]: _, ...rest } = prev; return rest; }
      return { ...prev, [key]: val };
    });
  };

  const availableCount = items.filter((r) => r.availability_status === "available").length;

  return (
    <DiscoveryLayout title="Reviewer Marketplace" subtitle="Expert peer review matching for academic research">
      <style>{`
        @keyframes sq-pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.45; }
        }
        .sq-pulse { animation: sq-pulse 1.8s ease-in-out infinite; }
      `}</style>

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <HeroSection
        user={user}
        total={total}
        availableCount={availableCount}
        myProfile={myProfile}
        onFindReviewer={() => explorerRef.current?.scrollIntoView({ behavior: "smooth" })}
        onBecomeReviewer={() => {
          api.get("/reviewer-marketplace/profile/me")
            .then((r) => { setMyProfile(r.data); toast.success("Your reviewer profile is active."); })
            .catch(() => toast.error("Could not activate reviewer profile."));
        }}
        onPostRequest={() => setShowCreate(true)}
      />

      {/* ── AI Recommendations ───────────────────────────────────────────── */}
      {(recsLoading || recs) && (
        <AiRecsPanel
          recs={recs}
          loading={recsLoading}
          compareList={compareList}
          toggleCompare={toggleCompare}
        />
      )}

      {/* ── Open Review Requests strip ────────────────────────────────────── */}
      {openRequests.length > 0 && (
        <OpenRequestsStrip requests={openRequests} onPost={() => setShowCreate(true)} />
      )}

      {/* ── Reviewer Explorer ─────────────────────────────────────────────── */}
      <div ref={explorerRef} style={{ marginTop: 36, display: "flex", gap: 24, alignItems: "flex-start" }}>

        {/* Filter sidebar */}
        <aside style={{ width: 228, flexShrink: 0, position: "sticky", top: 24, maxHeight: "calc(100vh - 80px)", overflowY: "auto" }}>
          <FilterPanel filters={filters} setFilter={setFilter} onClear={() => setFilters({})} />
        </aside>

        {/* Main panel */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Search + sort bar */}
          <div style={{ display: "flex", gap: 10, marginBottom: 14, alignItems: "center" }}>
            <div style={{ flex: 1, position: "relative" }}>
              <Search size={14} strokeWidth={1.5} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94A3B8", pointerEvents: "none" }} />
              <input
                data-testid={TID.discoverySearch}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search reviewers by name, institution, research area, method…"
                style={{ width: "100%", padding: "9px 36px 9px 38px", border: `1px solid ${BORDER}`, background: "white", fontSize: 13, color: "#1E293B", outline: "none", boxSizing: "border-box" }}
                onFocus={(e) => { e.target.style.borderColor = NAVY; }}
                onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
              />
              {q && (
                <button onClick={() => setQ("")} style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", color: "#94A3B8", cursor: "pointer", display: "flex", alignItems: "center", background: "none", border: "none", outline: "none" }}>
                  <X size={13} strokeWidth={1.5} />
                </button>
              )}
            </div>
            <button
              onClick={() => setShowCreate(true)}
              style={{ padding: "9px 16px", background: NAVY, color: "white", fontSize: 13, fontWeight: 700, border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, flexShrink: 0, outline: "none" }}
            >
              <Plus size={13} strokeWidth={2} /> Post Request
            </button>
          </div>

          {/* Count */}
          {!loading && !gated && (
            <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 14, fontFamily: "monospace" }}>
              {total.toLocaleString()} reviewers in marketplace
            </div>
          )}

          {/* Cards */}
          {gated ? (
            <GatedState />
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(256px, 1fr))", gap: 14 }}>
              {loading
                ? Array.from({ length: 8 }).map((_, i) => <ReviewerSkeleton key={i} />)
                : items.map((r) => (
                    <ReviewerCard
                      key={r.user_id || r._id}
                      r={r}
                      isCompared={compareList.some((x) => x.user_id === r.user_id)}
                      onCompare={toggleCompare}
                      onInvite={() => setShowCreate(true)}
                    />
                  ))
              }
            </div>
          )}

          {!loading && !gated && items.length === 0 && <EmptyState />}

          {/* Pagination */}
          {!loading && !gated && pages > 1 && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 24, paddingTop: 16, borderTop: `1px solid ${BORDER}` }}>
              <button
                data-testid={TID.discoveryPagePrev}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 16px", fontSize: 13, border: `1px solid ${BORDER}`, background: page === 1 ? "#F8FAFC" : "white", color: page === 1 ? "#CBD5E1" : NAVY, cursor: page === 1 ? "not-allowed" : "pointer", outline: "none" }}
              >
                <ChevronLeft size={14} strokeWidth={1.5} /> Previous
              </button>
              <span style={{ fontSize: 12, color: "#94A3B8", fontFamily: "monospace" }}>Page {page} of {pages}</span>
              <button
                data-testid={TID.discoveryPageNext}
                onClick={() => setPage((p) => Math.min(pages, p + 1))}
                disabled={page === pages}
                style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 16px", fontSize: 13, border: `1px solid ${BORDER}`, background: page === pages ? "#F8FAFC" : "white", color: page === pages ? "#CBD5E1" : NAVY, cursor: page === pages ? "not-allowed" : "pointer", outline: "none" }}
              >
                Next <ChevronRight size={14} strokeWidth={1.5} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Review Services strip ─────────────────────────────────────────── */}
      <ReviewServicesStrip onPost={() => setShowCreate(true)} />

      {/* ── Academic Integrity note ───────────────────────────────────────── */}
      <IntegrityNote />

      {/* ── Compare panel ─────────────────────────────────────────────────── */}
      {compareList.length >= 2 && (
        <ComparePanel
          reviewers={compareList}
          onRemove={(uid) => setCompareList((p) => p.filter((x) => x.user_id !== uid))}
          onClose={() => setCompareList([])}
        />
      )}

      {/* ── Create Request Modal ──────────────────────────────────────────── */}
      {showCreate && (
        <CreateRequestModal
          onClose={() => setShowCreate(false)}
          onCreated={(req) => {
            setShowCreate(false);
            if (req._id || req.id) navigate(`/review-workspace/${req._id || req.id}`);
          }}
        />
      )}
    </DiscoveryLayout>
  );
}

// ── Hero ──────────────────────────────────────────────────────────────────────
function HeroSection({ user, total, availableCount, myProfile, onFindReviewer, onBecomeReviewer, onPostRequest }) {
  const userField = (user?.research_areas || []).slice(0, 2).join(", ") || "your research";
  const isReviewer = myProfile?.reviewer_status === "active";

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
      {/* Grid overlay */}
      <div style={{ position: "absolute", inset: 0, opacity: 0.035, backgroundImage: "linear-gradient(rgba(255,255,255,0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.4) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />
      <div style={{ position: "absolute", top: -100, right: 60, width: 360, height: 360, background: "radial-gradient(circle, rgba(138,21,56,0.13) 0%, transparent 70%)", pointerEvents: "none" }} />

      <div style={{ position: "relative" }}>
        {/* Kicker */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
          <div style={{ width: 5, height: 5, borderRadius: "50%", background: EMERALD }} />
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>
            Academic Peer Review Marketplace
          </span>
        </div>

        {/* Headline */}
        <h1 style={{ fontFamily: "Georgia, serif", fontSize: 46, fontWeight: 400, color: "white", lineHeight: 1.08, marginBottom: 14, maxWidth: 560 }}>
          Find the Right<br />
          <span style={{ color: "rgba(255,255,255,0.58)", fontSize: 38 }}>Academic Reviewer</span>
        </h1>

        <p style={{ fontSize: 14, color: "rgba(255,255,255,0.46)", lineHeight: 1.7, maxWidth: 490, marginBottom: 30 }}>
          Connect with verified academic reviewers matched to{" "}
          <strong style={{ color: "rgba(255,255,255,0.73)" }}>{userField}</strong>.
          Expert reviewers for manuscripts, grants, theses and conference papers.
        </p>

        {/* CTAs */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 36 }}>
          <button
            onClick={onFindReviewer}
            style={{ padding: "10px 22px", background: "white", color: NAVY, fontSize: 13, fontWeight: 700, border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: 8, outline: "none" }}
          >
            <Search size={13} strokeWidth={2} /> Find Reviewer
          </button>
          {isReviewer ? (
            <span style={{ padding: "10px 16px", background: "rgba(5,150,105,0.15)", color: "#34D399", fontSize: 12, fontWeight: 600, border: "1px solid rgba(52,211,153,0.25)", display: "flex", alignItems: "center", gap: 6 }}>
              <CheckCircle size={12} strokeWidth={2} /> You are a reviewer
            </span>
          ) : (
            <button
              onClick={onBecomeReviewer}
              style={{ padding: "10px 22px", background: "transparent", color: "rgba(255,255,255,0.8)", fontSize: 13, fontWeight: 600, border: "1px solid rgba(255,255,255,0.2)", cursor: "pointer", display: "flex", alignItems: "center", gap: 8, outline: "none" }}
            >
              <UserCheck size={13} strokeWidth={1.5} /> Become a Reviewer
            </button>
          )}
          <button
            onClick={onPostRequest}
            style={{ padding: "10px 22px", background: "transparent", color: "rgba(255,255,255,0.6)", fontSize: 13, fontWeight: 600, border: "1px solid rgba(255,255,255,0.12)", cursor: "pointer", display: "flex", alignItems: "center", gap: 8, outline: "none" }}
          >
            <Plus size={13} strokeWidth={1.5} /> Post Review Request
          </button>
        </div>

        {/* Stats bar */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 0, borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: 20 }}>
          {[
            { Icon: Users,        label: "Reviewers",     val: total > 0 ? `${total}+` : "—" },
            { Icon: CheckCircle,  label: "Available now", val: availableCount > 0 ? `${availableCount}` : "—" },
            { Icon: Globe,        label: "Countries",     val: "Global" },
            { Icon: Shield,       label: "Integrity",     val: "Guaranteed" },
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

// ── AI Recommendations panel ──────────────────────────────────────────────────
function AiRecsPanel({ recs, loading, compareList, toggleCompare }) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div style={{ background: `${NAVY}05`, borderBottom: `1px solid ${BORDER}`, padding: "16px 0 20px", marginTop: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: expanded ? 14 : 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Sparkles size={13} strokeWidth={1.5} style={{ color: NAVY }} />
          <span style={{ fontSize: 12, fontWeight: 700, color: NAVY, textTransform: "uppercase", letterSpacing: "0.08em" }}>AI Reviewer Matches</span>
          <span style={{ fontSize: 11, color: "#94A3B8" }}>Matched to your expertise and current work</span>
        </div>
        <button onClick={() => setExpanded((v) => !v)} style={{ color: "#94A3B8", cursor: "pointer", display: "flex", alignItems: "center", background: "none", border: "none", outline: "none" }}>
          <ChevronDown size={13} strokeWidth={1.5} style={{ transform: expanded ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 200ms" }} />
        </button>
      </div>

      {expanded && (
        <div style={{ display: "flex", gap: 12, overflowX: "auto", paddingBottom: 4 }}>
          {loading
            ? Array.from({ length: 4 }).map((_, i) => <ReviewerCardCompact key={i} loading />)
            : (recs || []).slice(0, 7).map((r, i) => (
                <ReviewerCardCompact
                  key={r.user_id || r._id || i}
                  r={r}
                  isCompared={compareList.some((x) => x.user_id === r.user_id)}
                  onCompare={toggleCompare}
                />
              ))
          }
        </div>
      )}
    </div>
  );
}

// ── Open Requests strip ───────────────────────────────────────────────────────
function OpenRequestsStrip({ requests, onPost }) {
  const TYPE_COLOR = {
    manuscript:   NAVY,
    conference:   "#1D4ED8",
    grant:        EMERALD,
    thesis:       "#7C3AED",
    dissertation: "#9333EA",
    methodology:  "#0369A1",
    statistical:  "#92400E",
    custom:       "#64748B",
  };

  return (
    <div style={{ marginTop: 20, padding: "14px 0 16px", borderBottom: `1px solid ${BORDER}` }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <ClipboardCheck size={11} strokeWidth={1.5} style={{ color: "#94A3B8" }} />
          <span style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em" }}>Open Review Requests</span>
          <span style={{ fontSize: 10, color: "#CBD5E1" }}>Seeking reviewers now</span>
        </div>
        <button onClick={onPost} style={{ fontSize: 11, fontWeight: 600, color: NAVY, cursor: "pointer", display: "flex", alignItems: "center", gap: 3, background: "none", border: "none", outline: "none", textDecoration: "underline" }}>
          Post yours <ArrowRight size={10} strokeWidth={2} />
        </button>
      </div>
      <div style={{ display: "flex", gap: 10, overflowX: "auto", paddingBottom: 4 }}>
        {requests.map((req) => (
          <Link
            key={req._id}
            to={`/review-workspace/${req._id}`}
            style={{ display: "flex", flexDirection: "column", gap: 5, minWidth: 180, maxWidth: 220, flexShrink: 0, padding: "10px 12px", border: `1px solid ${BORDER}`, background: "white", textDecoration: "none", transition: "border-color 150ms" }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = NAVY}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = BORDER}
          >
            <span style={{ fontSize: 9, fontWeight: 700, color: TYPE_COLOR[req.review_type] || "#64748B", textTransform: "uppercase", letterSpacing: "0.07em" }}>
              {cap(req.review_type)}
            </span>
            <div style={{ fontSize: 12, fontWeight: 600, color: NAVY, lineHeight: 1.3, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
              {req.title}
            </div>
            {req.research_area && (
              <span style={{ fontSize: 10, color: "#64748B", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{req.research_area}</span>
            )}
            {req.deadline && (
              <span style={{ fontSize: 9, color: "#94A3B8" }}>Due {fmtDate(req.deadline)}</span>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}

// ── Avatar circle ─────────────────────────────────────────────────────────────
function AvatarCircle({ r, size = 44 }) {
  const [imgError, setImgError] = useState(false);
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
    <div style={{ width: size, height: size, borderRadius: "50%", background: NAVY, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: Math.round(size * 0.33), fontWeight: 700, color: "white" }}>
      {initials(r?.full_name)}
    </div>
  );
}

// ── Reviewer card (full grid) ─────────────────────────────────────────────────
function ReviewerCard({ r, isCompared, onCompare, onInvite }) {
  const avail = AVAIL_CONFIG[r.availability_status] || AVAIL_CONFIG.unavailable;
  const lvlStyle = LEVEL_STYLE[r.reviewer_level] || LEVEL_STYLE[1];
  const lvlLabel = LEVEL_LABEL[r.reviewer_level] || "Reviewer";
  const areas = (r.research_areas || []).slice(0, 3);
  const methods = (r.methods_expertise || []).slice(0, 2);
  const hasRatingData = r.reviews_completed > 0;
  const showScore = r.reviewer_score > 0;

  return (
    <Link
      to={profileUrl(r)}
      data-testid={TID.discoverResearcherCard(r.user_id || r._id)}
      style={{ display: "flex", flexDirection: "column", border: `1px solid ${BORDER}`, background: "white", textDecoration: "none", transition: "border-color 150ms, box-shadow 150ms, transform 150ms", overflow: "hidden" }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY; e.currentTarget.style.boxShadow = "0 4px 16px rgba(15,40,71,0.09)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "translateY(0)"; }}
    >
      {/* Availability top strip */}
      <div style={{ height: 2, background: avail.dot }} />

      <div style={{ padding: "14px 16px 12px", flex: 1 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
          <div style={{ position: "relative", flexShrink: 0 }}>
            <AvatarCircle r={r} size={44} />
            {/* Availability dot */}
            <div style={{ position: "absolute", bottom: 1, right: 1, width: 10, height: 10, borderRadius: "50%", background: avail.dot, border: "2px solid white" }} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 4 }}>
              <h3 style={{ fontFamily: "Georgia, serif", fontSize: 14, color: "#0F172A", lineHeight: 1.25, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {r.full_name || "Reviewer"}
              </h3>
              {r.verified_reviewer && (
                <Shield size={13} strokeWidth={1.5} style={{ color: EMERALD, flexShrink: 0, marginTop: 1 }} title="Verified reviewer" />
              )}
            </div>
            {/* Level */}
            <span style={{ fontSize: 9, fontWeight: 700, color: lvlStyle.color, background: lvlStyle.bg, padding: "2px 6px", display: "inline-block", marginTop: 2 }}>
              {lvlLabel}
            </span>
          </div>
        </div>

        {/* Institution + Location */}
        <div style={{ marginBottom: 9 }}>
          {r.institution && (
            <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 2 }}>
              <Building2 size={9} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0 }} />
              <span style={{ fontSize: 11, color: "#374151", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.institution}</span>
            </div>
          )}
          {r.country && (
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <Globe size={9} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0 }} />
              <span style={{ fontSize: 11, color: "#64748B" }}>{r.country}</span>
            </div>
          )}
        </div>

        {/* Research areas */}
        {areas.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 6 }}>
            {areas.map((a, i) => (
              <span key={i} style={{ fontSize: 9, color: "#374151", background: WARM, border: `1px solid ${BORDER}`, padding: "2px 6px" }}>{a}</span>
            ))}
            {(r.research_areas || []).length > 3 && <span style={{ fontSize: 9, color: "#94A3B8" }}>+{r.research_areas.length - 3}</span>}
          </div>
        )}

        {/* Methods */}
        {methods.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 }}>
            {methods.map((m, i) => (
              <span key={i} style={{ fontSize: 9, color: "#7C3AED", background: "#F5F3FF", border: "1px solid #DDD6FE", padding: "2px 6px" }}>{m}</span>
            ))}
          </div>
        )}

        {/* Reviewer score */}
        {showScore && (
          <div style={{ marginBottom: 8 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 3 }}>
              <span style={{ fontSize: 9, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600 }}>Reviewer Score</span>
              <span style={{ fontSize: 10, fontWeight: 800, color: NAVY, fontFamily: "monospace" }}>{Math.round(r.reviewer_score)}</span>
            </div>
            <div style={{ height: 3, background: "#F1F5F9", overflow: "hidden" }}>
              <div style={{ height: "100%", background: NAVY, width: `${Math.min(100, r.reviewer_score)}%`, transition: "width 600ms ease" }} />
            </div>
          </div>
        )}

        {/* Rating + reviews (only if real data exists) */}
        {hasRatingData && (
          <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 6 }}>
            {r.average_rating > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 3 }}>
                <Star size={10} strokeWidth={0} style={{ fill: "#F59E0B", color: "#F59E0B" }} />
                <span style={{ fontSize: 11, fontWeight: 700, color: "#374151", fontFamily: "monospace" }}>{r.average_rating.toFixed(1)}</span>
              </div>
            )}
            <div style={{ display: "flex", alignItems: "center", gap: 3 }}>
              <ClipboardCheck size={9} strokeWidth={1.5} style={{ color: "#94A3B8" }} />
              <span style={{ fontSize: 10, color: "#64748B" }}>{r.reviews_completed} review{r.reviews_completed !== 1 ? "s" : ""}</span>
            </div>
          </div>
        )}

        {/* Availability */}
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <div style={{ width: 7, height: 7, borderRadius: "50%", background: avail.dot, flexShrink: 0 }} />
          <span style={{ fontSize: 10, fontWeight: 600, color: avail.dot }}>{avail.text}</span>
        </div>
      </div>

      {/* Footer */}
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
        <button
          onClick={(e) => { e.stopPropagation(); onInvite(); }}
          style={{ fontSize: 10, fontWeight: 600, color: "#94A3B8", cursor: "pointer", display: "flex", alignItems: "center", gap: 3, background: "none", border: "none", outline: "none", padding: 0 }}
        >
          <ClipboardCheck size={10} strokeWidth={1.5} /> Invite
        </button>
      </div>
    </Link>
  );
}

// ── Compact card (recommendations panel) ──────────────────────────────────────
function ReviewerCardCompact({ r, isCompared, onCompare, loading: cardLoading }) {
  if (cardLoading) {
    return (
      <div style={{ minWidth: 220, maxWidth: 260, flexShrink: 0, border: `1px solid ${BORDER}`, background: "white", padding: 14 }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <div className="sq-pulse" style={{ width: 36, height: 36, borderRadius: "50%", background: "#F1F5F9", flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div className="sq-pulse" style={{ height: 13, width: "80%", background: "#F1F5F9", marginBottom: 5 }} />
            <div className="sq-pulse" style={{ height: 9, width: "55%", background: "#F1F5F9" }} />
          </div>
        </div>
        <div className="sq-pulse" style={{ height: 9, width: "70%", background: "#F1F5F9", marginBottom: 6 }} />
        <div className="sq-pulse" style={{ height: 24, background: "#F1F5F9" }} />
      </div>
    );
  }

  const avail = AVAIL_CONFIG[r?.availability_status] || AVAIL_CONFIG.unavailable;

  return (
    <Link
      to={profileUrl(r)}
      style={{ display: "block", minWidth: 220, maxWidth: 260, flexShrink: 0, border: `1px solid ${BORDER}`, background: "white", padding: 14, textDecoration: "none", transition: "border-color 150ms" }}
      onMouseEnter={(e) => e.currentTarget.style.borderColor = NAVY}
      onMouseLeave={(e) => e.currentTarget.style.borderColor = BORDER}
    >
      <div style={{ display: "flex", gap: 8, alignItems: "flex-start", marginBottom: 8 }}>
        <div style={{ position: "relative", flexShrink: 0 }}>
          <AvatarCircle r={r} size={36} />
          <div style={{ position: "absolute", bottom: 0, right: 0, width: 9, height: 9, borderRadius: "50%", background: avail.dot, border: "1.5px solid white" }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: NAVY, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontFamily: "Georgia, serif" }}>{r?.full_name}</div>
          <div style={{ fontSize: 10, color: "#64748B", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r?.institution || r?.country || ""}</div>
        </div>
        {r?.verified_reviewer && (
          <Shield size={11} strokeWidth={1.5} style={{ color: EMERALD, flexShrink: 0 }} />
        )}
      </div>

      {(r?.research_areas || []).slice(0, 2).length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 3, marginBottom: 6 }}>
          {(r.research_areas || []).slice(0, 2).map((a, i) => (
            <span key={i} style={{ fontSize: 8, color: "#374151", background: WARM, border: `1px solid ${BORDER}`, padding: "1px 5px" }}>{a}</span>
          ))}
        </div>
      )}

      {r?.explanation && (
        <div style={{ fontSize: 10, color: "#94A3B8", fontStyle: "italic", lineHeight: 1.4 }}>{r.explanation}</div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 6 }}>
        <div style={{ width: 6, height: 6, borderRadius: "50%", background: avail.dot }} />
        <span style={{ fontSize: 9, color: avail.dot, fontWeight: 600 }}>{avail.text}</span>
      </div>
    </Link>
  );
}

// ── Reviewer skeleton ──────────────────────────────────────────────────────────
function ReviewerSkeleton() {
  return (
    <div style={{ border: `1px solid ${BORDER}`, background: "white" }}>
      <div style={{ height: 2, background: "#F1F5F9" }} />
      <div style={{ padding: "14px 16px 12px" }}>
        <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
          <div className="sq-pulse" style={{ width: 44, height: 44, borderRadius: "50%", background: "#F1F5F9", flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div className="sq-pulse" style={{ height: 14, width: "70%", background: "#F1F5F9", marginBottom: 6 }} />
            <div className="sq-pulse" style={{ height: 9, width: "45%", background: "#F1F5F9" }} />
          </div>
        </div>
        <div className="sq-pulse" style={{ height: 11, width: "70%", background: "#F1F5F9", marginBottom: 5 }} />
        <div className="sq-pulse" style={{ height: 11, width: "50%", background: "#F1F5F9", marginBottom: 10 }} />
        <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
          {[44, 56, 48].map((w, i) => <div key={i} className="sq-pulse" style={{ height: 16, width: w, background: "#F1F5F9" }} />)}
        </div>
        <div className="sq-pulse" style={{ height: 3, background: "#F1F5F9", marginBottom: 8 }} />
        <div className="sq-pulse" style={{ height: 11, width: "35%", background: "#F1F5F9" }} />
      </div>
      <div style={{ borderTop: `1px solid ${BORDER}`, padding: "7px 16px", background: "#FAFBFC" }}>
        <div className="sq-pulse" style={{ height: 10, width: "55%", background: "#F1F5F9" }} />
      </div>
    </div>
  );
}

// ── Filter panel ──────────────────────────────────────────────────────────────
function FilterPanel({ filters, setFilter, onClear }) {
  const AVAIL_OPTIONS = [
    { value: "available",   label: "Available" },
    { value: "busy",        label: "Busy" },
    { value: "unavailable", label: "Unavailable" },
  ];
  const LEVEL_OPTIONS = [
    { value: "1", label: "New Reviewer (L1)" },
    { value: "2", label: "Junior Reviewer (L2)" },
    { value: "3", label: "Experienced (L3)" },
    { value: "4", label: "Senior Reviewer (L4)" },
    { value: "5", label: "Expert Reviewer (L5)" },
  ];

  return (
    <div style={{ background: "white", border: `1px solid ${BORDER}`, padding: "16px 14px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.1em" }}>Filters</span>
        {Object.values(filters).some(Boolean) && (
          <button onClick={onClear} style={{ fontSize: 10, color: "#94A3B8", cursor: "pointer", background: "none", border: "none", outline: "none", textDecoration: "underline" }}>Clear</button>
        )}
      </div>

      {/* Availability */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Availability</div>
        {AVAIL_OPTIONS.map((o) => {
          const cfg = AVAIL_CONFIG[o.value];
          return (
            <label key={o.value} style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 7, cursor: "pointer" }}>
              <input
                type="radio"
                name="availability_status"
                checked={filters.availability_status === o.value}
                onChange={() => setFilter("availability_status", filters.availability_status === o.value ? "" : o.value)}
                style={{ accentColor: NAVY, width: 12, height: 12, flexShrink: 0 }}
              />
              <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: cfg.dot, flexShrink: 0 }} />
                <span style={{ fontSize: 12, color: "#374151" }}>{o.label}</span>
              </div>
            </label>
          );
        })}
      </div>

      {/* Verified only */}
      <div style={{ marginBottom: 14, borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 7, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={!!filters.verified_reviewer}
            onChange={(e) => setFilter("verified_reviewer", e.target.checked || "")}
            style={{ accentColor: NAVY, width: 13, height: 13, flexShrink: 0 }}
          />
          <span style={{ fontSize: 12, color: "#374151", display: "flex", alignItems: "center", gap: 4 }}>
            <Shield size={11} strokeWidth={1.5} style={{ color: EMERALD }} /> Verified reviewers only
          </span>
        </label>
      </div>

      {/* Level */}
      <div style={{ marginBottom: 14, borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Reviewer Level</div>
        <select
          data-testid={TID.discoverySortSelect}
          value={filters.reviewer_level || ""}
          onChange={(e) => setFilter("reviewer_level", e.target.value)}
          style={{ width: "100%", padding: "6px 8px", border: `1px solid ${BORDER}`, fontSize: 12, color: "#374151", background: "white", outline: "none", boxSizing: "border-box" }}
        >
          <option value="">All levels</option>
          {LEVEL_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {/* Research Area */}
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

      {/* Methodology */}
      <div style={{ marginBottom: 14, borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Methodology</div>
        <input
          value={filters.methods_expertise || ""}
          onChange={(e) => setFilter("methods_expertise", e.target.value)}
          placeholder="e.g. Systematic Review"
          style={{ width: "100%", padding: "6px 8px", border: `1px solid ${BORDER}`, fontSize: 12, color: "#374151", outline: "none", boxSizing: "border-box" }}
          onFocus={(e) => { e.target.style.borderColor = NAVY; }}
          onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
        />
      </div>

      {/* Country */}
      <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Country</div>
        <input
          value={filters.country || ""}
          onChange={(e) => setFilter("country", e.target.value)}
          placeholder="e.g. United Kingdom"
          style={{ width: "100%", padding: "6px 8px", border: `1px solid ${BORDER}`, fontSize: 12, color: "#374151", outline: "none", boxSizing: "border-box" }}
          onFocus={(e) => { e.target.style.borderColor = NAVY; }}
          onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
        />
      </div>
    </div>
  );
}

// ── Review Services strip ─────────────────────────────────────────────────────
function ReviewServicesStrip({ onPost }) {
  return (
    <div style={{ margin: "48px -24px 0", background: WARM, borderTop: `1px solid ${BORDER}`, padding: "36px 56px" }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 6 }}>Peer Review Services</div>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: 26, color: NAVY, fontWeight: 400 }}>Supported Review Types</h2>
          <p style={{ fontSize: 13, color: "#64748B", marginTop: 6, maxWidth: 480, lineHeight: 1.6 }}>
            Post a review request and let AI match you with the most qualified reviewer for your work.
          </p>
        </div>
        <button
          onClick={onPost}
          style={{ fontSize: 13, fontWeight: 700, color: NAVY, display: "inline-flex", alignItems: "center", gap: 6, padding: "9px 18px", border: `1.5px solid ${NAVY}`, cursor: "pointer", alignSelf: "flex-start", background: "white", outline: "none", whiteSpace: "nowrap" }}
        >
          <Plus size={13} strokeWidth={2} /> Post Review Request
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(168px, 1fr))", gap: 12 }}>
        {REVIEW_TYPES_LIST.map(({ value, label, icon: Icon }) => (
          <div
            key={value}
            style={{ display: "flex", flexDirection: "column", gap: 8, padding: 16, background: "white", border: `1px solid ${BORDER}` }}
          >
            <Icon size={18} strokeWidth={1.5} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: NAVY }}>{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Academic Integrity note ───────────────────────────────────────────────────
function IntegrityNote() {
  return (
    <div style={{ margin: "0 -24px", background: `${NAVY}04`, borderTop: `1px solid ${BORDER}`, padding: "20px 56px" }}>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start", maxWidth: 760 }}>
        <Shield size={16} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0, marginTop: 2 }} />
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#374151", marginBottom: 4 }}>Academic Integrity & Ethics</div>
          <p style={{ fontSize: 12, color: "#64748B", lineHeight: 1.6 }}>
            Synaptiq Reviewer Marketplace facilitates connections between researchers and peer reviewers.
            All review invitations include conflict-of-interest checks. Reviewers are selected for
            academic expertise — not to guarantee specific outcomes. Synaptiq does not endorse
            or guarantee journal acceptance. Reviews are conducted with full confidentiality
            as agreed between parties.
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Empty state ────────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <div style={{ textAlign: "center", padding: "60px 24px", border: `1px dashed ${BORDER}` }}>
      <Users size={44} strokeWidth={1} style={{ color: "#E2E8F0", margin: "0 auto 20px", display: "block" }} />
      <h3 style={{ fontFamily: "Georgia, serif", fontSize: 22, color: "#1E293B", marginBottom: 8, fontWeight: 400 }}>
        No reviewers match your filters
      </h3>
      <p style={{ fontSize: 13, color: "#64748B", maxWidth: 380, margin: "0 auto 24px", lineHeight: 1.65 }}>
        Try removing a filter or broadening your search. Reviewers are listed from the Synaptiq community
        who have indicated availability for peer review.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 7, maxWidth: 360, margin: "0 auto" }}>
        {[
          { Icon: CheckCircle, text: "Remove the availability filter to see all reviewers" },
          { Icon: Globe,       text: "Remove the country filter for global results" },
          { Icon: Lightbulb,   text: "Become a reviewer yourself and expand the community" },
        ].map(({ Icon, text }) => (
          <div key={text} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 12, color: "#64748B", textAlign: "left" }}>
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
      <Shield size={44} strokeWidth={1} style={{ color: "#E2E8F0", margin: "0 auto 20px", display: "block" }} />
      <h3 style={{ fontFamily: "Georgia, serif", fontSize: 22, color: "#1E293B", marginBottom: 8, fontWeight: 400 }}>
        Reviewer access limit reached
      </h3>
      <p style={{ fontSize: 13, color: "#64748B", maxWidth: 360, margin: "0 auto 24px", lineHeight: 1.65 }}>
        Upgrade your plan to access the full reviewer marketplace and invite unlimited reviewers.
      </p>
      <Link to="/settings/billing" style={{ padding: "9px 22px", background: NAVY, color: "white", fontSize: 13, fontWeight: 700, textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 6 }}>
        View plans <ArrowRight size={13} strokeWidth={1.5} />
      </Link>
    </div>
  );
}

// ── Compare panel ─────────────────────────────────────────────────────────────
function ComparePanel({ reviewers, onRemove, onClose }) {
  const METRICS = [
    { label: "Level",          fn: (r) => LEVEL_LABEL[r.reviewer_level] || "—" },
    { label: "Institution",    fn: (r) => r.institution || "—" },
    { label: "Country",        fn: (r) => r.country || "—" },
    { label: "Availability",   fn: (r) => AVAIL_CONFIG[r.availability_status]?.text || "—" },
    { label: "Score",          fn: (r) => r.reviewer_score > 0 ? `${Math.round(r.reviewer_score)}/100` : "—" },
    { label: "Reviews done",   fn: (r) => r.reviews_completed > 0 ? r.reviews_completed : "—" },
    { label: "Avg rating",     fn: (r) => r.reviews_completed > 0 && r.average_rating > 0 ? `${r.average_rating.toFixed(1)}/5` : "—" },
    { label: "Verified",       fn: (r) => r.verified_reviewer ? "Yes" : "No" },
    { label: "Research areas", fn: (r) => (r.research_areas || []).slice(0, 2).join(", ") || "—" },
    { label: "Methodology",    fn: (r) => (r.methods_expertise || []).slice(0, 2).join(", ") || "—" },
  ];

  return (
    <div style={{ position: "fixed", bottom: 0, left: 0, right: 0, background: NAVY, color: "white", padding: "14px 24px", zIndex: 200, boxShadow: "0 -8px 32px rgba(0,0,0,0.35)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <BarChart2 size={13} strokeWidth={1.5} style={{ color: "rgba(255,255,255,0.5)" }} />
          <span style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>
            Comparing {reviewers.length} reviewers
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
              {reviewers.map((r) => (
                <th key={r.user_id} style={{ padding: "4px 14px", textAlign: "left", borderBottom: "1px solid rgba(255,255,255,0.08)", minWidth: 160 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "white", fontFamily: "Georgia, serif", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 160 }}>{r.full_name}</div>
                  <button onClick={() => onRemove(r.user_id)} style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 2, background: "none", border: "none", outline: "none", padding: 0, marginTop: 2 }}>
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
                {reviewers.map((r) => (
                  <td key={r.user_id} style={{ padding: "3px 14px", fontSize: 11, color: "rgba(255,255,255,0.8)", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{fn(r)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Create Request Modal ──────────────────────────────────────────────────────
const REVIEW_TYPE_VALUES = ["manuscript", "conference", "grant", "thesis", "dissertation", "methodology", "statistical", "custom"];
const CONFIDENTIALITY_OPTS = [
  { value: "anonymous",    label: "Anonymous — reviewers are anonymous to authors" },
  { value: "double-blind", label: "Double-blind — both parties anonymous" },
  { value: "single-blind", label: "Single-blind — reviewer knows author" },
  { value: "public",       label: "Public — all identities disclosed" },
];

function CreateRequestModal({ onClose, onCreated }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: "", description: "", review_type: "manuscript",
    research_area: "", required_expertise: "", keywords: "",
    deadline: "", confidentiality: "anonymous", visibility: "public",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) { setError("Title is required."); return; }
    setSubmitting(true);
    setError("");
    try {
      const payload = {
        title: form.title,
        description: form.description,
        review_type: form.review_type,
        research_area: form.research_area,
        required_expertise: form.required_expertise.split(",").map((s) => s.trim()).filter(Boolean),
        keywords: form.keywords.split(",").map((s) => s.trim()).filter(Boolean),
        deadline: form.deadline || null,
        confidentiality: form.confidentiality,
        visibility: form.visibility,
      };
      const { data } = await api.post("/reviewer-marketplace/requests", payload);
      onCreated(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create request. Please try again.");
      setSubmitting(false);
    }
  };

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 300, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ background: "white", width: "100%", maxWidth: 580, maxHeight: "90vh", overflowY: "auto", boxShadow: "0 24px 64px rgba(0,0,0,0.28)" }}>
        {/* Modal header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 24px", borderBottom: `1px solid ${BORDER}` }}>
          <div>
            <h2 style={{ fontFamily: "Georgia, serif", fontSize: 18, color: NAVY, fontWeight: 400 }}>Post Review Request</h2>
            <p style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>Describe what you need reviewed and let AI match you with qualified reviewers.</p>
          </div>
          <button onClick={onClose} style={{ color: "#94A3B8", cursor: "pointer", display: "flex", background: "none", border: "none", outline: "none" }}>
            <X size={18} strokeWidth={1.5} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ padding: 24 }}>
          {error && (
            <div style={{ padding: "10px 14px", background: "#FFF1F2", border: "1px solid #FECDD3", color: ACCENT, fontSize: 12, marginBottom: 16 }}>{error}</div>
          )}

          {/* Title */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#374151", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Title <span style={{ color: ACCENT }}>*</span>
            </label>
            <input
              value={form.title}
              onChange={(e) => set("title", e.target.value)}
              placeholder="e.g. Review of AI Ethics manuscript for IJHCS submission"
              style={{ width: "100%", padding: "9px 12px", border: `1px solid ${BORDER}`, fontSize: 13, color: "#1E293B", outline: "none", boxSizing: "border-box" }}
              onFocus={(e) => { e.target.style.borderColor = NAVY; }}
              onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
            />
          </div>

          {/* Description */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#374151", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>Description</label>
            <textarea
              rows={4}
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
              placeholder="Describe what you need reviewed, context, scope, specific feedback areas…"
              style={{ width: "100%", padding: "9px 12px", border: `1px solid ${BORDER}`, fontSize: 13, color: "#1E293B", outline: "none", resize: "vertical", boxSizing: "border-box" }}
              onFocus={(e) => { e.target.style.borderColor = NAVY; }}
              onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
            />
          </div>

          {/* Review type + Confidentiality */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#374151", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>Review Type</label>
              <select
                value={form.review_type}
                onChange={(e) => set("review_type", e.target.value)}
                style={{ width: "100%", padding: "9px 10px", border: `1px solid ${BORDER}`, fontSize: 13, color: "#374151", background: "white", outline: "none", boxSizing: "border-box" }}
              >
                {REVIEW_TYPE_VALUES.map((t) => <option key={t} value={t}>{cap(t)}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#374151", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>Confidentiality</label>
              <select
                value={form.confidentiality}
                onChange={(e) => set("confidentiality", e.target.value)}
                style={{ width: "100%", padding: "9px 10px", border: `1px solid ${BORDER}`, fontSize: 13, color: "#374151", background: "white", outline: "none", boxSizing: "border-box" }}
              >
                {CONFIDENTIALITY_OPTS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>

          {/* Research area + Deadline */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#374151", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>Research Area</label>
              <input
                value={form.research_area}
                onChange={(e) => set("research_area", e.target.value)}
                placeholder="e.g. Machine Learning"
                style={{ width: "100%", padding: "9px 12px", border: `1px solid ${BORDER}`, fontSize: 13, color: "#1E293B", outline: "none", boxSizing: "border-box" }}
                onFocus={(e) => { e.target.style.borderColor = NAVY; }}
                onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#374151", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>Deadline</label>
              <input
                type="date"
                value={form.deadline}
                onChange={(e) => set("deadline", e.target.value)}
                style={{ width: "100%", padding: "9px 12px", border: `1px solid ${BORDER}`, fontSize: 13, color: "#1E293B", outline: "none", boxSizing: "border-box" }}
                onFocus={(e) => { e.target.style.borderColor = NAVY; }}
                onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
              />
            </div>
          </div>

          {/* Required expertise */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#374151", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>Required Expertise</label>
            <input
              value={form.required_expertise}
              onChange={(e) => set("required_expertise", e.target.value)}
              placeholder="e.g. NLP, ethics, qualitative analysis (comma-separated)"
              style={{ width: "100%", padding: "9px 12px", border: `1px solid ${BORDER}`, fontSize: 13, color: "#1E293B", outline: "none", boxSizing: "border-box" }}
              onFocus={(e) => { e.target.style.borderColor = NAVY; }}
              onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
            />
          </div>

          {/* Visibility */}
          <div style={{ marginBottom: 24 }}>
            <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#374151", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>Visibility</label>
            <div style={{ display: "flex", gap: 12 }}>
              {["public", "private"].map((v) => (
                <label key={v} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                  <input
                    type="radio"
                    name="visibility"
                    value={v}
                    checked={form.visibility === v}
                    onChange={() => set("visibility", v)}
                    style={{ accentColor: NAVY }}
                  />
                  <span style={{ fontSize: 13, color: "#374151" }}>{cap(v)}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Submit */}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button type="button" onClick={onClose} style={{ padding: "9px 20px", border: `1px solid ${BORDER}`, background: "white", fontSize: 13, fontWeight: 600, color: "#64748B", cursor: "pointer", outline: "none" }}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              style={{ padding: "9px 22px", background: submitting ? "#94A3B8" : NAVY, color: "white", fontSize: 13, fontWeight: 700, border: "none", cursor: submitting ? "not-allowed" : "pointer", outline: "none", display: "flex", alignItems: "center", gap: 8 }}
            >
              {submitting ? "Posting…" : "Post & Find Reviewers"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

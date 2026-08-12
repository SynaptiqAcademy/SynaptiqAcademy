import React, { useState, useEffect, useCallback, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { EMERALD, NAVY, WARM } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import {
  Avatar, Button, Card, Badge, Tag, Input, Textarea, FormSelect,
  SearchBar, Modal, EmptyState as DsEmptyState, Alert, Checkbox, Radio,
} from "@/components/ds";
import { Pagination } from "@/components/ds/DataTable";
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
    <ResearchLayout
      title="Reviewer Marketplace"
      subtitle="Expert peer review matching for academic research"
      actions={
        <>
          <Button onClick={() => explorerRef.current?.scrollIntoView({ behavior: "smooth" })} size="sm">
            <Search size={13} strokeWidth={2} /> Find Reviewer
          </Button>
          {myProfile?.reviewer_status === "active" ? (
            <Badge size="sm" variant="success">
              <CheckCircle size={12} strokeWidth={2} /> You are a reviewer
            </Badge>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                api.get("/reviewer-marketplace/profile/me")
                  .then((r) => { setMyProfile(r.data); toast.success("Your reviewer profile is active."); })
                  .catch(() => toast.error("Could not activate reviewer profile."));
              }}
            >
              <UserCheck size={13} strokeWidth={1.5} /> Become a Reviewer
            </Button>
          )}
        </>
      }
    >
      <style>{`
        @keyframes sq-pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.45; }
        }
        .sq-pulse { animation: sq-pulse 1.8s ease-in-out infinite; }
      `}</style>
      {/* ── Stats strip ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 max-w-lg mb-8">
        {[
          { label: "Reviewers",     value: total > 0 ? `${total}+` : "—" },
          { label: "Available now", value: availableCount > 0 ? `${availableCount}` : "—" },
          { label: "Countries",     value: "Global" },
          { label: "Integrity",     value: "Guaranteed" },
        ].map(({ label, value }) => (
          <div key={label} className="text-center">
            <div className="font-serif text-3xl text-slate-900">{value}</div>
            <div className="overline mt-1 text-xs">{label}</div>
          </div>
        ))}
      </div>
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
            <div style={{ flex: 1 }}>
              <SearchBar
                data-testid={TID.discoverySearch}
                value={q}
                onChange={setQ}
                placeholder="Search reviewers by name, institution, research area, method…"
                onClear={() => setQ("")}
              />
            </div>
            <Button onClick={() => setShowCreate(true)} className="shrink-0">
              <Plus size={13} strokeWidth={2} /> Post Request
            </Button>
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
            <div style={{ marginTop: 24, paddingTop: 16, borderTop: `1px solid ${BORDER}` }}>
              <Pagination page={page} totalPages={pages} onPage={setPage} />
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
    </ResearchLayout>
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
        <Button
          size="icon"
          variant="ghost"
          onClick={() => setExpanded((v) => !v)}
          aria-label={expanded ? "Collapse recommendations" : "Expand recommendations"}
          style={{
            color: "#94A3B8",
            display: "flex",
            alignItems: "center"
          }}>
          <ChevronDown size={13} strokeWidth={1.5} style={{ transform: expanded ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 200ms" }} />
        </Button>
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
        <Button variant="link" size="sm" onClick={onPost}>
          Post yours <ArrowRight size={10} strokeWidth={2} />
        </Button>
      </div>
      <div style={{ display: "flex", gap: 10, overflowX: "auto", paddingBottom: 4 }}>
        {requests.map((req) => (
          <Card
            key={req._id}
            to={`/review-workspace/${req._id}`}
            padding="sm"
            style={{ display: "flex", flexDirection: "column", gap: 5, minWidth: 180, maxWidth: 220, flexShrink: 0 }}
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
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Avatar circle ─────────────────────────────────────────────────────────────
function AvatarCircle({ r, size = 44 }) {
  return <Avatar url={r?.avatar_url} name={r?.full_name} size={size} border />;
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
    <Card
      to={profileUrl(r)}
      data-testid={TID.discoverResearcherCard(r.user_id || r._id)}
      padding="none"
      style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}
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
            <Badge color={lvlStyle.color} size="sm" style={{ marginTop: 2 }}>
              {lvlLabel}
            </Badge>
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
              <Tag key={i} size="sm">{a}</Tag>
            ))}
            {(r.research_areas || []).length > 3 && <span style={{ fontSize: 9, color: "#94A3B8" }}>+{r.research_areas.length - 3}</span>}
          </div>
        )}

        {/* Methods */}
        {methods.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 }}>
            {methods.map((m, i) => (
              <Badge key={i} variant="purple" size="sm">{m}</Badge>
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
        <Button as={Link} to={profileUrl(r)} onClick={(e) => e.stopPropagation()} variant="link" size="sm" style={{ color: NAVY }}>
          View Profile <ArrowRight size={9} strokeWidth={2} />
        </Button>
        <span style={{ color: "#E2E8F0" }}>|</span>
        <Button
          variant="link"
          size="sm"
          onClick={(e) => onCompare(r, e)}
          style={{ color: isCompared ? NAVY : "#94A3B8", textDecoration: isCompared ? "underline" : "none" }}
        >
          <BarChart2 size={10} strokeWidth={1.5} /> Compare
        </Button>
        <span style={{ color: "#E2E8F0" }}>|</span>
        <Button
          variant="link"
          size="sm"
          onClick={(e) => { e.stopPropagation(); onInvite(); }}
          style={{ color: "#94A3B8" }}
        >
          <ClipboardCheck size={10} strokeWidth={1.5} /> Invite
        </Button>
      </div>
    </Card>
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
    <Card
      to={profileUrl(r)}
      padding="md"
      style={{ minWidth: 220, maxWidth: 260, flexShrink: 0 }}
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
            <Tag key={i} size="sm">{a}</Tag>
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
    </Card>
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
    <Card padding="md">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.1em" }}>Filters</span>
        {Object.values(filters).some(Boolean) && (
          <Button variant="link" size="sm" onClick={onClear}>Clear</Button>
        )}
      </div>

      {/* Availability */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Availability</div>
        {AVAIL_OPTIONS.map((o) => {
          const cfg = AVAIL_CONFIG[o.value];
          return (
            <Radio
              key={o.value}
              name="availability_status"
              checked={filters.availability_status === o.value}
              onChange={() => setFilter("availability_status", filters.availability_status === o.value ? "" : o.value)}
              style={{ marginBottom: 7 }}
              label={
                <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: cfg.dot, flexShrink: 0, display: "inline-block" }} />
                  <span style={{ fontSize: 12, color: "#374151" }}>{o.label}</span>
                </span>
              }
            />
          );
        })}
      </div>

      {/* Verified only */}
      <div style={{ marginBottom: 14, borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <Checkbox
          checked={!!filters.verified_reviewer}
          onChange={(e) => setFilter("verified_reviewer", e.target.checked || "")}
          label={
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <Shield size={11} strokeWidth={1.5} style={{ color: EMERALD }} /> Verified reviewers only
            </span>
          }
        />
      </div>

      {/* Level */}
      <div style={{ marginBottom: 14, borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Reviewer Level</div>
        <FormSelect
          data-testid={TID.discoverySortSelect}
          size="sm"
          value={filters.reviewer_level || ""}
          onChange={(e) => setFilter("reviewer_level", e.target.value)}
        >
          <option value="">All levels</option>
          {LEVEL_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </FormSelect>
      </div>

      {/* Research Area */}
      <div style={{ marginBottom: 14, borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Research Area</div>
        <Input
          size="sm"
          value={filters.research_area || ""}
          onChange={(e) => setFilter("research_area", e.target.value)}
          placeholder="e.g. Machine Learning"
        />
      </div>

      {/* Methodology */}
      <div style={{ marginBottom: 14, borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Methodology</div>
        <Input
          size="sm"
          value={filters.methods_expertise || ""}
          onChange={(e) => setFilter("methods_expertise", e.target.value)}
          placeholder="e.g. Systematic Review"
        />
      </div>

      {/* Country */}
      <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Country</div>
        <Input
          size="sm"
          value={filters.country || ""}
          onChange={(e) => setFilter("country", e.target.value)}
          placeholder="e.g. United Kingdom"
        />
      </div>
    </Card>
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
        <Button variant="outline" onClick={onPost} className="self-start whitespace-nowrap">
          <Plus size={13} strokeWidth={2} /> Post Review Request
        </Button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(168px, 1fr))", gap: 12 }}>
        {REVIEW_TYPES_LIST.map(({ value, label, icon: Icon }) => (
          <Card
            key={value}
            padding="md"
            style={{ display: "flex", flexDirection: "column", gap: 8 }}
          >
            <Icon size={18} strokeWidth={1.5} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: NAVY }}>{label}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Academic Integrity note ───────────────────────────────────────────────────
function IntegrityNote() {
  return (
    <div style={{ margin: "0 -24px", background: `${NAVY}04`, borderTop: `1px solid ${BORDER}`, padding: "20px 56px" }}>
      <Alert
        variant="neutral"
        icon={Shield}
        title="Academic Integrity & Ethics"
        style={{ maxWidth: 760, background: "transparent", border: "none", padding: 0 }}
      >
        Synaptiq Reviewer Marketplace facilitates connections between researchers and peer reviewers.
        All review invitations include conflict-of-interest checks. Reviewers are selected for
        academic expertise — not to guarantee specific outcomes. Synaptiq does not endorse
        or guarantee journal acceptance. Reviews are conducted with full confidentiality
        as agreed between parties.
      </Alert>
    </div>
  );
}

// ── Empty state ────────────────────────────────────────────────────────────────
function EmptyState() {
  return (
    <DsEmptyState
      icon={<Users strokeWidth={1} />}
      title="No reviewers match your filters"
      description="Try removing a filter or broadening your search. Reviewers are listed from the Synaptiq community who have indicated availability for peer review."
      size="lg"
      action={
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
      }
    />
  );
}

// ── Gated state ───────────────────────────────────────────────────────────────
function GatedState() {
  return (
    <DsEmptyState
      icon={<Shield strokeWidth={1} />}
      title="Reviewer access limit reached"
      description="Upgrade your plan to access the full reviewer marketplace and invite unlimited reviewers."
      size="lg"
      action={
        <Button as={Link} to="/settings/billing">
          View plans <ArrowRight size={13} strokeWidth={1.5} />
        </Button>
      }
    />
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
        <Button variant="link" size="sm" onClick={onClose} style={{ color: "rgba(255,255,255,0.45)" }}>
          <X size={13} strokeWidth={1.5} /> Close
        </Button>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 400 }}>
          <thead>
            <tr>
              <th style={{ width: 90, padding: "4px 12px 4px 0", textAlign: "left", fontSize: 9, color: "rgba(255,255,255,0.3)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", borderBottom: "1px solid rgba(255,255,255,0.08)" }} />
              {reviewers.map((r) => (
                <th key={r.user_id} style={{ padding: "4px 14px", textAlign: "left", borderBottom: "1px solid rgba(255,255,255,0.08)", minWidth: 160 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "white", fontFamily: "Georgia, serif", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 160 }}>{r.full_name}</div>
                  <Button variant="link" size="sm" onClick={() => onRemove(r.user_id)} style={{ color: "rgba(255,255,255,0.3)", marginTop: 2, fontSize: 9 }}>
                    <X size={7} strokeWidth={1.5} /> Remove
                  </Button>
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
    <Modal
      open
      onClose={onClose}
      title="Post Review Request"
      description="Describe what you need reviewed and let AI match you with qualified reviewers."
      size="md"
      footer={
        <>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" form="create-request-form" disabled={submitting} loading={submitting}>
            Post & Find Reviewers
          </Button>
        </>
      }
    >
      <form id="create-request-form" onSubmit={handleSubmit}>
        {error && (
          <Alert variant="error" style={{ marginBottom: 16 }}>{error}</Alert>
        )}

        {/* Title */}
        <div style={{ marginBottom: 16 }}>
          <Input
            label="Title *"
            value={form.title}
            onChange={(e) => set("title", e.target.value)}
            placeholder="e.g. Review of AI Ethics manuscript for IJHCS submission"
          />
        </div>

        {/* Description */}
        <div style={{ marginBottom: 16 }}>
          <Textarea
            label="Description"
            rows={4}
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
            placeholder="Describe what you need reviewed, context, scope, specific feedback areas…"
          />
        </div>

        {/* Review type + Confidentiality */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 16 }}>
          <FormSelect
            label="Review Type"
            value={form.review_type}
            onChange={(e) => set("review_type", e.target.value)}
          >
            {REVIEW_TYPE_VALUES.map((t) => <option key={t} value={t}>{cap(t)}</option>)}
          </FormSelect>
          <FormSelect
            label="Confidentiality"
            value={form.confidentiality}
            onChange={(e) => set("confidentiality", e.target.value)}
          >
            {CONFIDENTIALITY_OPTS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </FormSelect>
        </div>

        {/* Research area + Deadline */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 16 }}>
          <Input
            label="Research Area"
            value={form.research_area}
            onChange={(e) => set("research_area", e.target.value)}
            placeholder="e.g. Machine Learning"
          />
          <Input
            label="Deadline"
            type="date"
            value={form.deadline}
            onChange={(e) => set("deadline", e.target.value)}
          />
        </div>

        {/* Required expertise */}
        <div style={{ marginBottom: 16 }}>
          <Input
            label="Required Expertise"
            value={form.required_expertise}
            onChange={(e) => set("required_expertise", e.target.value)}
            placeholder="e.g. NLP, ethics, qualitative analysis (comma-separated)"
          />
        </div>

        {/* Visibility */}
        <div style={{ marginBottom: 8 }}>
          <div style={{ display: "block", fontSize: 11, fontWeight: 700, color: "#374151", marginBottom: 5, textTransform: "uppercase", letterSpacing: "0.06em" }}>Visibility</div>
          <div style={{ display: "flex", gap: 12 }}>
            {["public", "private"].map((v) => (
              <Radio
                key={v}
                name="visibility"
                checked={form.visibility === v}
                onChange={() => set("visibility", v)}
                label={cap(v)}
              />
            ))}
          </div>
        </div>
      </form>
    </Modal>
  );
}

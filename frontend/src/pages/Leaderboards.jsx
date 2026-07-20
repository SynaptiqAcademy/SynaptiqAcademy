import React, { useState, useEffect, useCallback, useRef } from "react";
import { DiscoveryLayout } from "@/layouts";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { ACCENT, EMERALD, NAVY, WARM } from "@/lib/tokens";
import {
  Award, Shield, Globe, Building2, BookOpen, ClipboardCheck, Users,
  GraduationCap, BarChart2, Star, TrendingUp, ArrowRight, ChevronLeft,
  ChevronRight, X, Search, Sparkles, Clock, CheckCircle, Lightbulb,
  Activity, Zap, ChevronDown, ChevronUp, RefreshCw, UserCheck,
} from "lucide-react";

// ── Design tokens ─────────────────────────────────────────────────────────────
const BORDER  = "#E4E8EF";

// ── Research levels (must match backend REPUTATION_LEVELS exactly) ─────────────
const RESEARCH_LEVELS = [
  { level: 1, label: "Research Explorer",      min: 0,    max: 99,      color: "#64748B", bg: "#F8FAFC", border: "#CBD5E1" },
  { level: 2, label: "Emerging Researcher",    min: 100,  max: 249,     color: "#059669", bg: "#ECFDF5", border: "#6EE7B7" },
  { level: 3, label: "Active Researcher",      min: 250,  max: 499,     color: "#1D4ED8", bg: "#EFF6FF", border: "#93C5FD" },
  { level: 4, label: "Established Researcher", min: 500,  max: 999,     color: "#4338CA", bg: "#EEF2FF", border: "#A5B4FC" },
  { level: 5, label: "Advanced Researcher",    min: 1000, max: 1999,    color: "#7C3AED", bg: "#F5F3FF", border: "#C4B5FD" },
  { level: 6, label: "Research Leader",        min: 2000, max: 4999,    color: "#B45309", bg: "#FFFBEB", border: "#FCD34D" },
  { level: 7, label: "Distinguished Scholar",  min: 5000, max: 9999999, color: "#92400E", bg: "#FEF3C7", border: "#F59E0B" },
];

// ── Leaderboard categories ─────────────────────────────────────────────────────
const CATEGORIES = [
  { key: "top_researchers",   label: "Overall Researchers",   Icon: Award,          isUserList: true,  desc: "Ranked by total reputation score across all categories" },
  { key: "top_collaborators", label: "Research Collaborators",Icon: Users,          isUserList: true,  desc: "Ranked by collaboration activity and partnerships" },
  { key: "top_reviewers",     label: "Peer Reviewers",        Icon: ClipboardCheck, isUserList: true,  desc: "Ranked by peer review completions and quality" },
  { key: "top_mentors",       label: "Mentors",               Icon: GraduationCap,  isUserList: true,  desc: "Ranked by mentoring sessions and academic guidance" },
  { key: "top_teachers",      label: "Teaching Excellence",   Icon: BookOpen,       isUserList: true,  desc: "Ranked by teaching contributions and published lessons" },
  { key: "top_institutions",  label: "Institutions",          Icon: Building2,      isUserList: false, desc: "Institutions ranked by the aggregate reputation of their Synaptiq members" },
  { key: "top_countries",     label: "Countries",             Icon: Globe,          isUserList: false, desc: "Countries ranked by the aggregate reputation of their Synaptiq researchers" },
];

// ── Badge rarity styles ────────────────────────────────────────────────────────
const RARITY = {
  common:    { bg: "#F8FAFC", border: "#CBD5E1", color: "#64748B", label: "Common" },
  rare:      { bg: "#EFF6FF", border: "#93C5FD", color: "#1D4ED8", label: "Rare" },
  epic:      { bg: "#F5F3FF", border: "#C4B5FD", color: "#7C3AED", label: "Epic" },
  legendary: { bg: "#FEF3C7", border: "#F59E0B", color: "#92400E", label: "Legendary" },
};

// ── Score sub-categories ───────────────────────────────────────────────────────
const SCORE_CATEGORIES = [
  { key: "publication_score",   label: "Research Activity",  color: NAVY,    Icon: BarChart2 },
  { key: "collaboration_score", label: "Collaboration",      color: "#1D4ED8", Icon: Users },
  { key: "reviewer_score",      label: "Peer Review",        color: EMERALD,  Icon: ClipboardCheck },
  { key: "teaching_score",      label: "Teaching",           color: "#7C3AED", Icon: BookOpen },
  { key: "profile_score",       label: "Profile Quality",    color: "#B45309", Icon: Shield },
];

// ── Event category styles ──────────────────────────────────────────────────────
const EVENT_CATEGORY_COLOR = {
  research:      { bg: "#EFF6FF", color: "#1D4ED8" },
  collaboration: { bg: "#ECFDF5", color: "#059669" },
  reviewer:      { bg: "#F5F3FF", color: "#7C3AED" },
  teaching:      { bg: "#FFFBEB", color: "#B45309" },
  profile:       { bg: "#F0F9FF", color: "#0369A1" },
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function getLevelInfo(level) {
  return RESEARCH_LEVELS.find((l) => l.level === level) || RESEARCH_LEVELS[0];
}

function getLevelByScore(score) {
  const s = Math.round(score || 0);
  return RESEARCH_LEVELS.slice().reverse().find((l) => s >= l.min) || RESEARCH_LEVELS[0];
}

function getProgressPct(score, levelInfo) {
  const next = RESEARCH_LEVELS.find((l) => l.level === levelInfo.level + 1);
  if (!next) return 100;
  const range  = next.min - levelInfo.min;
  const within = Math.round(score) - levelInfo.min;
  return Math.min(100, Math.max(0, Math.round((within / range) * 100)));
}

function initials(name) {
  return (name || "?").split(" ").filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
}

function fmtPts(n) {
  if (!n && n !== 0) return "—";
  return Number(n).toLocaleString();
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function computeSlug(name) {
  let s = (name || "").toLowerCase().trim();
  s = s.replace(/[^a-z0-9\s-]/g, "");
  s = s.replace(/\s+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
  return s || "researcher";
}

function profileUrl(item) {
  return `/researcher/${item.slug || computeSlug(item.full_name)}`;
}

const PAGE_LIMIT = 18;

// ── Main component ────────────────────────────────────────────────────────────
export default function Leaderboards() {
  const { user } = useAuth();

  // Own reputation
  const [myRep,        setMyRep]        = useState(null);
  const [myRepLoading, setMyRepLoading] = useState(true);
  const [myEvents,     setMyEvents]     = useState([]);

  // Leaderboard
  const [activeCat, setActiveCat] = useState(CATEGORIES[0]);
  const [page,      setPage]      = useState(1);
  const [country,   setCountry]   = useState("");
  const [institution, setInstitution] = useState("");
  const [items,     setItems]     = useState([]);
  const [loading,   setLoading]   = useState(false);
  const [isLastPage, setIsLastPage] = useState(false);

  // Compare
  const [compareList, setCompareList] = useState([]);

  const intervalRef = useRef(null);
  const mainRef     = useRef(null);

  // ── Boot: my reputation + events ──────────────────────────────────────────
  useEffect(() => {
    Promise.all([
      api.get("/reputation/research/me"),
      api.get("/reputation/events/me", { params: { limit: 10 } }),
    ])
      .then(([repRes, evRes]) => {
        setMyRep(repRes.data);
        setMyEvents(Array.isArray(evRes.data) ? evRes.data : []);
      })
      .catch(() => {})
      .finally(() => setMyRepLoading(false));
  }, []);

  // ── Leaderboard fetch ──────────────────────────────────────────────────────
  const fetchLeaderboard = useCallback(async () => {
    setLoading(true);
    try {
      const params = { category: activeCat.key, page, limit: PAGE_LIMIT };
      if (country)     params.country     = country;
      if (institution) params.institution = institution;
      const { data } = await api.get("/reputation/leaderboard", { params });
      const results = Array.isArray(data?.results) ? data.results : [];
      setItems(results);
      setIsLastPage(results.length < PAGE_LIMIT);
    } catch {
      setItems([]);
      setIsLastPage(true);
    } finally {
      setLoading(false);
    }
  }, [activeCat.key, page, country, institution]);

  useEffect(() => { fetchLeaderboard(); }, [fetchLeaderboard]);

  // Auto-refresh
  useEffect(() => {
    clearInterval(intervalRef.current);
    intervalRef.current = setInterval(fetchLeaderboard, 60_000);
    return () => clearInterval(intervalRef.current);
  }, [fetchLeaderboard]);

  // Reset page on category/filter change
  useEffect(() => { setPage(1); }, [activeCat.key, country, institution]);

  // ── Compare helpers ────────────────────────────────────────────────────────
  const toggleCompare = (item, e) => {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    setCompareList((prev) => {
      if (prev.find((x) => x.user_id === item.user_id)) return prev.filter((x) => x.user_id !== item.user_id);
      if (prev.length >= 3) { toast.error("Compare up to 3 researchers at once"); return prev; }
      return [...prev, item];
    });
  };

  const isCompared = (item) => compareList.some((x) => x.user_id === item.user_id);

  const scrollToMain = () => mainRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <DiscoveryLayout>
      <style>{`
        @keyframes sq-pulse { 0%,100%{opacity:1} 50%{opacity:.42} }
        .sq-pulse { animation: sq-pulse 1.8s ease-in-out infinite; }
        @keyframes slide-up { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
        .slide-up { animation: slide-up 350ms ease both; }
      `}</style>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <HeroSection myRep={myRep} loading={myRepLoading} user={user} onExplore={scrollToMain} />

      {/* ── My Academic Standing ────────────────────────────────────────── */}
      {(myRepLoading || myRep) && (
        <MyStandingPanel myRep={myRep} events={myEvents} loading={myRepLoading} />
      )}

      {/* ── Leaderboard explorer ─────────────────────────────────────────── */}
      <div ref={mainRef} style={{ marginTop: 40, display: "flex", gap: 24, alignItems: "flex-start" }}>

        {/* Category sidebar */}
        <aside style={{ width: 220, flexShrink: 0, position: "sticky", top: 24, maxHeight: "calc(100vh - 80px)", overflowY: "auto" }}>
          <CategorySidebar
            categories={CATEGORIES}
            active={activeCat}
            onSelect={(c) => setActiveCat(c)}
            country={country}
            setCountry={setCountry}
            institution={institution}
            setInstitution={setInstitution}
          />
        </aside>

        {/* Main panel */}
        <div style={{ flex: 1, minWidth: 0 }}>

          {/* Category header */}
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 14 }}>
            <div>
              <h2 style={{ fontFamily: "Georgia, serif", fontSize: 22, color: NAVY, fontWeight: 400 }}>
                {activeCat.label}
              </h2>
              <p style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>{activeCat.desc}</p>
            </div>
            <button
              onClick={fetchLeaderboard}
              style={{ display: "flex", alignItems: "center", gap: 5, padding: "7px 12px", fontSize: 11, fontWeight: 600, color: "#64748B", border: `1px solid ${BORDER}`, background: "white", cursor: "pointer", outline: "none" }}
              title="Refresh"
            >
              <RefreshCw size={12} strokeWidth={1.5} /> Refresh
            </button>
          </div>

          {/* Researcher cards */}
          {activeCat.isUserList ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(272px, 1fr))", gap: 12 }}>
              {loading
                ? Array.from({ length: 6 }).map((_, i) => <ResearcherCardSkeleton key={i} />)
                : items.map((item) => (
                    <ResearcherCard
                      key={item.user_id}
                      item={item}
                      compared={isCompared(item)}
                      onCompare={toggleCompare}
                    />
                  ))
              }
            </div>
          ) : (
            <AggregateList items={items} loading={loading} catKey={activeCat.key} />
          )}

          {/* Empty state */}
          {!loading && items.length === 0 && (
            <EmptyLeaderboardState cat={activeCat} />
          )}

          {/* Pagination */}
          {!loading && items.length > 0 && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 24, paddingTop: 16, borderTop: `1px solid ${BORDER}` }}>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                style={{ display: "flex", alignItems: "center", gap: 5, padding: "7px 16px", fontSize: 12, border: `1px solid ${BORDER}`, background: page === 1 ? WARM : "white", color: page === 1 ? "#CBD5E1" : NAVY, cursor: page === 1 ? "not-allowed" : "pointer", outline: "none" }}
              >
                <ChevronLeft size={13} strokeWidth={1.5} /> Previous
              </button>
              <span style={{ fontSize: 11, color: "#94A3B8", fontFamily: "monospace" }}>Page {page}</span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={isLastPage}
                style={{ display: "flex", alignItems: "center", gap: 5, padding: "7px 16px", fontSize: 12, border: `1px solid ${BORDER}`, background: isLastPage ? WARM : "white", color: isLastPage ? "#CBD5E1" : NAVY, cursor: isLastPage ? "not-allowed" : "pointer", outline: "none" }}
              >
                Next <ChevronRight size={13} strokeWidth={1.5} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── My Achievements ────────────────────────────────────────────────── */}
      {myRep?.badges?.length > 0 && (
        <BadgesSection badges={myRep.badges} />
      )}

      {/* ── Transparency ────────────────────────────────────────────────────── */}
      <TransparencySection />

      {/* ── Compare panel ────────────────────────────────────────────────────── */}
      {compareList.length >= 2 && (
        <ComparePanel
          researchers={compareList}
          onRemove={(uid) => setCompareList((p) => p.filter((x) => x.user_id !== uid))}
          onClose={() => setCompareList([])}
        />
      )}
    </DiscoveryLayout>
  );
}

// ── Hero section ──────────────────────────────────────────────────────────────
function HeroSection({ myRep, loading, user, onExplore }) {
  const score    = myRep?.overall_score || 0;
  const level    = myRep?.reputation_level || 1;
  const label    = myRep?.reputation_label || "Research Explorer";
  const rankGlobal  = myRep?.rank_global;
  const percentile  = myRep?.percentile_global;
  const lvlInfo  = getLevelInfo(level);
  const progress = getProgressPct(score, lvlInfo);
  const nextMin  = myRep?.next_level_min;
  const nextLabel = myRep?.next_level_label;

  return (
    <div
      style={{
        margin: "-24px -24px 0",
        background: `linear-gradient(145deg, #091D35 0%, ${NAVY} 55%, #163355 100%)`,
        padding: "48px 56px 40px",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {/* Subtle grid */}
      <div style={{ position: "absolute", inset: 0, opacity: 0.03, backgroundImage: "linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)", backgroundSize: "48px 48px" }} />
      {/* Glow */}
      <div style={{ position: "absolute", top: -120, right: 100, width: 400, height: 400, background: "radial-gradient(circle, rgba(138,21,56,0.1) 0%, transparent 65%)", pointerEvents: "none" }} />

      <div style={{ position: "relative", display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 48 }}>

        {/* Left: headline */}
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
            <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#FCD34D" }} />
            <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase", color: "rgba(255,255,255,0.35)" }}>
              Academic Excellence Center
            </span>
          </div>

          <h1 style={{ fontFamily: "Georgia, serif", fontSize: 44, fontWeight: 400, color: "white", lineHeight: 1.08, marginBottom: 14, maxWidth: 560 }}>
            Academic<br />
            <span style={{ color: "rgba(255,255,255,0.5)", fontSize: 36 }}>Recognition Rankings</span>
          </h1>

          <p style={{ fontSize: 13, color: "rgba(255,255,255,0.42)", lineHeight: 1.75, maxWidth: 440, marginBottom: 28 }}>
            Transparent, evidence-based rankings that celebrate genuine academic contributions —
            research activity, collaboration, peer review, mentoring and teaching.
          </p>

          <div style={{ display: "flex", gap: 10 }}>
            <Link
              to="/settings#profile"
              style={{ padding: "9px 20px", background: "white", color: NAVY, fontSize: 12, fontWeight: 700, textDecoration: "none", display: "flex", alignItems: "center", gap: 6 }}
            >
              <UserCheck size={12} strokeWidth={2} /> Improve My Profile
            </Link>
            <button
              onClick={onExplore}
              style={{ padding: "9px 20px", background: "transparent", color: "rgba(255,255,255,0.75)", fontSize: 12, fontWeight: 600, border: "1px solid rgba(255,255,255,0.18)", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, outline: "none" }}
            >
              <Award size={12} strokeWidth={1.5} /> Explore Rankings
            </button>
          </div>
        </div>

        {/* Right: personal standing card */}
        <div style={{ flexShrink: 0, width: 260, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", padding: 24 }}>
          {loading ? (
            <HeroStandingSkeleton />
          ) : (
            <>
              <div style={{ fontSize: 9, fontWeight: 700, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 14 }}>
                Your Standing
              </div>

              {/* Level badge */}
              <div style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 10px", background: "rgba(255,255,255,0.09)", border: "1px solid rgba(255,255,255,0.13)", marginBottom: 12 }}>
                <div style={{ width: 5, height: 5, borderRadius: "50%", background: lvlInfo.color }} />
                <span style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.85)" }}>Level {level} · {label}</span>
              </div>

              {/* Score */}
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 36, fontWeight: 800, color: "white", fontFamily: "monospace", lineHeight: 1 }}>
                  {fmtPts(score)}
                </div>
                <div style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", marginTop: 3, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Reputation Points
                </div>
              </div>

              {/* Progress bar */}
              {level < 7 && nextMin && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                    <span style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", fontWeight: 600 }}>Progress to {nextLabel}</span>
                    <span style={{ fontSize: 9, color: "rgba(255,255,255,0.4)", fontFamily: "monospace" }}>{progress}%</span>
                  </div>
                  <div style={{ height: 3, background: "rgba(255,255,255,0.1)", overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${progress}%`, background: lvlInfo.color, transition: "width 800ms ease" }} />
                  </div>
                  <div style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", marginTop: 3, fontFamily: "monospace" }}>
                    {fmtPts(nextMin - score)} pts to next level
                  </div>
                </div>
              )}
              {level === 7 && (
                <div style={{ marginBottom: 16, fontSize: 10, color: "#FCD34D", fontWeight: 600 }}>
                  ✦ Distinguished Scholar — highest level
                </div>
              )}

              {/* Rank / percentile */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <div>
                  <div style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em" }}>Global Rank</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: "white", fontFamily: "monospace", marginTop: 2 }}>
                    {rankGlobal ? `#${rankGlobal}` : "—"}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em" }}>Percentile</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: "white", fontFamily: "monospace", marginTop: 2 }}>
                    {percentile > 0 ? `${percentile.toFixed(1)}%` : "—"}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function HeroStandingSkeleton() {
  return (
    <div>
      <div className="sq-pulse" style={{ height: 10, width: "60%", background: "rgba(255,255,255,0.12)", marginBottom: 18 }} />
      <div className="sq-pulse" style={{ height: 18, width: "80%", background: "rgba(255,255,255,0.1)", marginBottom: 10 }} />
      <div className="sq-pulse" style={{ height: 36, width: "60%", background: "rgba(255,255,255,0.1)", marginBottom: 14 }} />
      <div className="sq-pulse" style={{ height: 3, background: "rgba(255,255,255,0.08)", marginBottom: 16 }} />
    </div>
  );
}

// ── My Academic Standing panel ─────────────────────────────────────────────────
function MyStandingPanel({ myRep, events, loading }) {
  const [collapsed, setCollapsed] = useState(false);

  const totalSub = SCORE_CATEGORIES.reduce((sum, c) => sum + (myRep?.[c.key] || 0), 0) || 1;

  return (
    <div style={{ marginTop: 24, background: "white", border: `1px solid ${BORDER}`, overflow: "hidden" }}>
      {/* Panel header */}
      <div
        style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", cursor: "pointer", userSelect: "none" }}
        onClick={() => setCollapsed((v) => !v)}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Sparkles size={13} strokeWidth={1.5} style={{ color: NAVY }} />
          <span style={{ fontSize: 12, fontWeight: 700, color: NAVY, textTransform: "uppercase", letterSpacing: "0.08em" }}>My Academic Standing</span>
          <span style={{ fontSize: 11, color: "#94A3B8" }}>Your contribution breakdown</span>
        </div>
        {collapsed
          ? <ChevronDown size={14} strokeWidth={1.5} style={{ color: "#94A3B8" }} />
          : <ChevronUp size={14} strokeWidth={1.5} style={{ color: "#94A3B8" }} />
        }
      </div>

      {!collapsed && (
        <div style={{ borderTop: `1px solid ${BORDER}`, padding: "20px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28 }}>

          {/* Score breakdown */}
          <div>
            <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 14 }}>
              Score Breakdown
            </div>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} style={{ marginBottom: 12 }}>
                  <div className="sq-pulse" style={{ height: 11, width: "50%", background: "#F1F5F9", marginBottom: 5 }} />
                  <div className="sq-pulse" style={{ height: 4, background: "#F1F5F9" }} />
                </div>
              ))
            ) : (
              SCORE_CATEGORIES.map(({ key, label, color, Icon }) => {
                const pts = myRep?.[key] || 0;
                const pct = Math.round((pts / totalSub) * 100);
                return (
                  <div key={key} style={{ marginBottom: 11 }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                        <Icon size={10} strokeWidth={1.5} style={{ color }} />
                        <span style={{ fontSize: 11, color: "#374151" }}>{label}</span>
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 700, color: NAVY, fontFamily: "monospace" }}>{fmtPts(pts)} pts</span>
                    </div>
                    <div style={{ height: 4, background: "#F1F5F9", overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${pct}%`, background: color, transition: "width 700ms ease" }} />
                    </div>
                  </div>
                );
              })
            )}

            {!loading && !myRep && (
              <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.6, padding: "8px 0" }}>
                Complete your profile and participate in research activities to begin building your reputation score.
              </div>
            )}
          </div>

          {/* Recent events */}
          <div>
            <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 14 }}>
              Recent Activity
            </div>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                  <div className="sq-pulse" style={{ width: 24, height: 24, borderRadius: "50%", background: "#F1F5F9", flexShrink: 0 }} />
                  <div style={{ flex: 1 }}>
                    <div className="sq-pulse" style={{ height: 11, width: "70%", background: "#F1F5F9", marginBottom: 4 }} />
                    <div className="sq-pulse" style={{ height: 9, width: "40%", background: "#F1F5F9" }} />
                  </div>
                </div>
              ))
            ) : events.length > 0 ? (
              events.map((ev, i) => {
                const cat = ev.category || "research";
                const catStyle = EVENT_CATEGORY_COLOR[cat] || EVENT_CATEGORY_COLOR.research;
                return (
                  <div key={i} style={{ display: "flex", gap: 10, marginBottom: 9, alignItems: "flex-start" }}>
                    <div style={{ width: 28, height: 28, borderRadius: "50%", background: catStyle.bg, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <span style={{ fontSize: 9, fontWeight: 800, color: catStyle.color }}>+{ev.points}</span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, color: "#1E293B", lineHeight: 1.3 }}>{ev.description || ev.event_type?.replace(/_/g, " ")}</div>
                      <div style={{ fontSize: 9, color: "#94A3B8", marginTop: 2 }}>{fmtDate(ev.created_at)}</div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ padding: "12px 0", fontSize: 12, color: "#94A3B8", lineHeight: 1.6 }}>
                No activity yet. Start collaborating, reviewing, and contributing to earn reputation points.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Category sidebar ───────────────────────────────────────────────────────────
function CategorySidebar({ categories, active, onSelect, country, setCountry, institution, setInstitution }) {
  const hasFilters = country || institution;
  return (
    <div>
      {/* Category nav */}
      <div style={{ background: "white", border: `1px solid ${BORDER}`, padding: "10px 8px", marginBottom: 12 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", padding: "6px 8px 10px" }}>
          Categories
        </div>
        <nav>
          {categories.map((cat) => {
            const isActive = active.key === cat.key;
            return (
              <button
                key={cat.key}
                onClick={() => onSelect(cat)}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 10px",
                  marginBottom: 2,
                  fontSize: 12,
                  fontWeight: isActive ? 700 : 500,
                  color: isActive ? "white" : "#374151",
                  background: isActive ? NAVY : "transparent",
                  border: "none",
                  cursor: "pointer",
                  textAlign: "left",
                  outline: "none",
                  transition: "background 150ms, color 150ms",
                }}
                onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = WARM; }}
                onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = "transparent"; }}
              >
                <cat.Icon size={12} strokeWidth={1.5} style={{ flexShrink: 0, opacity: isActive ? 1 : 0.6 }} />
                <span style={{ lineHeight: 1.3 }}>{cat.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Filters */}
      <div style={{ background: "white", border: `1px solid ${BORDER}`, padding: "14px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <span style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em" }}>Filters</span>
          {hasFilters && (
            <button onClick={() => { setCountry(""); setInstitution(""); }} style={{ fontSize: 9, color: "#94A3B8", cursor: "pointer", background: "none", border: "none", outline: "none", textDecoration: "underline" }}>Clear</button>
          )}
        </div>
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 9, fontWeight: 600, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 5 }}>Country</div>
          <input
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            placeholder="e.g. Germany"
            style={{ width: "100%", padding: "7px 9px", border: `1px solid ${BORDER}`, fontSize: 12, color: "#374151", outline: "none", boxSizing: "border-box" }}
            onFocus={(e) => { e.target.style.borderColor = NAVY; }}
            onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
          />
        </div>
        <div>
          <div style={{ fontSize: 9, fontWeight: 600, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 5 }}>Institution</div>
          <input
            value={institution}
            onChange={(e) => setInstitution(e.target.value)}
            placeholder="e.g. MIT"
            style={{ width: "100%", padding: "7px 9px", border: `1px solid ${BORDER}`, fontSize: 12, color: "#374151", outline: "none", boxSizing: "border-box" }}
            onFocus={(e) => { e.target.style.borderColor = NAVY; }}
            onBlur={(e)  => { e.target.style.borderColor = BORDER; }}
          />
        </div>
      </div>
    </div>
  );
}

// ── Avatar ────────────────────────────────────────────────────────────────────
function AvatarCircle({ item, size = 48 }) {
  const [err, setErr] = useState(false);
  if (item?.avatar_url && !err) {
    return (
      <img
        src={item.avatar_url}
        alt={item.full_name || ""}
        onError={() => setErr(true)}
        style={{ width: size, height: size, borderRadius: "50%", objectFit: "cover", flexShrink: 0, border: `1.5px solid ${BORDER}` }}
      />
    );
  }
  return (
    <div style={{ width: size, height: size, borderRadius: "50%", background: NAVY, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: Math.round(size * 0.3), fontWeight: 700, color: "white" }}>
      {initials(item?.full_name)}
    </div>
  );
}

// ── Rank medal / number ────────────────────────────────────────────────────────
function RankDisplay({ rank }) {
  if (rank === 1) return (
    <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#FFFBEB", border: "1.5px solid #FCD34D", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0 }}>
      🥇
    </div>
  );
  if (rank === 2) return (
    <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#F8FAFC", border: "1.5px solid #CBD5E1", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0 }}>
      🥈
    </div>
  );
  if (rank === 3) return (
    <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#FFF7ED", border: "1.5px solid #FED7AA", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0 }}>
      🥉
    </div>
  );
  return (
    <div style={{ width: 28, textAlign: "center", fontSize: 11, fontWeight: 700, color: "#94A3B8", fontFamily: "monospace", flexShrink: 0 }}>
      #{rank}
    </div>
  );
}

// ── Researcher card ───────────────────────────────────────────────────────────
function ResearcherCard({ item, compared, onCompare }) {
  const level    = item.reputation_level || 1;
  const lvlInfo  = getLevelInfo(level);
  const label    = item.reputation_label || "Research Explorer";
  const score    = item.overall_score || 0;

  return (
    <Link
      to={profileUrl(item)}
      className="slide-up"
      style={{ display: "flex", flexDirection: "column", border: `1px solid ${compared ? NAVY : BORDER}`, background: compared ? `${NAVY}03` : "white", textDecoration: "none", transition: "border-color 150ms, box-shadow 150ms, transform 150ms", overflow: "hidden" }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY; e.currentTarget.style.boxShadow = "0 4px 16px rgba(15,40,71,0.08)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = compared ? NAVY : BORDER; e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "translateY(0)"; }}
    >
      {/* Top rank accent */}
      {item.rank <= 3 && (
        <div style={{ height: 2, background: item.rank === 1 ? "#FCD34D" : item.rank === 2 ? "#CBD5E1" : "#FED7AA" }} />
      )}

      <div style={{ padding: "14px 16px 12px", flex: 1 }}>
        {/* Header row */}
        <div style={{ display: "flex", gap: 10, alignItems: "flex-start", marginBottom: 10 }}>
          <AvatarCircle item={item} size={44} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 4 }}>
              <h3 style={{ fontFamily: "Georgia, serif", fontSize: 14, color: "#0F172A", lineHeight: 1.25, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {item.full_name || "Researcher"}
              </h3>
              <RankDisplay rank={item.rank} />
            </div>
            {item.academic_role && (
              <div style={{ fontSize: 10, color: "#64748B", marginTop: 2 }}>{item.academic_role}</div>
            )}
          </div>
        </div>

        {/* Institution + Country */}
        <div style={{ marginBottom: 10 }}>
          {item.institution && (
            <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 2 }}>
              <Building2 size={9} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0 }} />
              <span style={{ fontSize: 11, color: "#374151", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.institution}</span>
            </div>
          )}
          {item.country && (
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <Globe size={9} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0 }} />
              <span style={{ fontSize: 11, color: "#64748B" }}>{item.country}</span>
            </div>
          )}
        </div>

        {/* Level badge */}
        <div style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "3px 8px", background: lvlInfo.bg, border: `1px solid ${lvlInfo.border}`, marginBottom: 10 }}>
          <div style={{ width: 5, height: 5, borderRadius: "50%", background: lvlInfo.color, flexShrink: 0 }} />
          <span style={{ fontSize: 9, fontWeight: 700, color: lvlInfo.color, textTransform: "uppercase", letterSpacing: "0.07em" }}>
            Lv {level} · {label}
          </span>
        </div>

        {/* Score + badges + percentile */}
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 9, color: "#94A3B8", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em" }}>Score</div>
            <div style={{ fontSize: 16, fontWeight: 800, color: NAVY, fontFamily: "monospace" }}>{fmtPts(score)}</div>
          </div>
          {item.badges_count > 0 && (
            <div>
              <div style={{ fontSize: 9, color: "#94A3B8", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em" }}>Badges</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#374151" }}>{item.badges_count}</div>
            </div>
          )}
          {item.percentile_global > 0 && (
            <div>
              <div style={{ fontSize: 9, color: "#94A3B8", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em" }}>Percentile</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: EMERALD }}>{item.percentile_global.toFixed(1)}%</div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div
        style={{ borderTop: `1px solid ${BORDER}`, padding: "7px 16px", background: "#FAFBFC", display: "flex", gap: 10, alignItems: "center" }}
        onClick={(e) => e.preventDefault()}
      >
        <Link
          to={profileUrl(item)}
          onClick={(e) => e.stopPropagation()}
          style={{ fontSize: 10, fontWeight: 700, color: NAVY, display: "flex", alignItems: "center", gap: 3, textDecoration: "none" }}
        >
          View Profile <ArrowRight size={9} strokeWidth={2} />
        </Link>
        <span style={{ color: "#E2E8F0" }}>|</span>
        <button
          onClick={(e) => onCompare(item, e)}
          style={{ fontSize: 10, fontWeight: 600, color: compared ? NAVY : "#94A3B8", cursor: "pointer", display: "flex", alignItems: "center", gap: 3, background: "none", border: "none", outline: "none", padding: 0, textDecoration: compared ? "underline" : "none" }}
        >
          <BarChart2 size={10} strokeWidth={1.5} /> {compared ? "Remove" : "Compare"}
        </button>
      </div>
    </Link>
  );
}

// ── Researcher card skeleton ───────────────────────────────────────────────────
function ResearcherCardSkeleton() {
  return (
    <div style={{ border: `1px solid ${BORDER}`, background: "white" }}>
      <div style={{ padding: "14px 16px 12px" }}>
        <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
          <div className="sq-pulse" style={{ width: 44, height: 44, borderRadius: "50%", background: "#F1F5F9", flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div className="sq-pulse" style={{ height: 14, width: "65%", background: "#F1F5F9", marginBottom: 5 }} />
            <div className="sq-pulse" style={{ height: 10, width: "45%", background: "#F1F5F9" }} />
          </div>
        </div>
        <div className="sq-pulse" style={{ height: 11, width: "60%", background: "#F1F5F9", marginBottom: 5 }} />
        <div className="sq-pulse" style={{ height: 11, width: "40%", background: "#F1F5F9", marginBottom: 10 }} />
        <div className="sq-pulse" style={{ height: 20, width: "70%", background: "#F1F5F9", marginBottom: 10 }} />
        <div style={{ display: "flex", gap: 14 }}>
          <div className="sq-pulse" style={{ width: 48, height: 28, background: "#F1F5F9" }} />
          <div className="sq-pulse" style={{ width: 36, height: 28, background: "#F1F5F9" }} />
        </div>
      </div>
      <div style={{ borderTop: `1px solid ${BORDER}`, padding: "7px 16px", background: "#FAFBFC" }}>
        <div className="sq-pulse" style={{ height: 10, width: "50%", background: "#F1F5F9" }} />
      </div>
    </div>
  );
}

// ── Aggregate list (institutions / countries) ─────────────────────────────────
function AggregateList({ items, loading, catKey }) {
  const isInstitution = catKey === "top_institutions";

  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} style={{ display: "flex", gap: 14, alignItems: "center", padding: "14px 18px", border: `1px solid ${BORDER}`, background: "white" }}>
            <div className="sq-pulse" style={{ width: 32, height: 32, background: "#F1F5F9", flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <div className="sq-pulse" style={{ height: 14, width: "40%", background: "#F1F5F9", marginBottom: 5 }} />
              <div className="sq-pulse" style={{ height: 10, width: "25%", background: "#F1F5F9" }} />
            </div>
            <div className="sq-pulse" style={{ width: 64, height: 24, background: "#F1F5F9" }} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {items.map((item) => {
        const name   = isInstitution ? item.institution : item.country;
        const score  = item.total_score || 0;
        const count  = item.member_count || item.members_count || 0;
        const country = isInstitution ? item.country : null;
        return (
          <div
            key={name || item.rank}
            style={{ display: "flex", gap: 14, alignItems: "center", padding: "14px 18px", border: `1px solid ${BORDER}`, background: "white", transition: "border-color 150ms" }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = NAVY}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = BORDER}
          >
            <RankDisplay rank={item.rank} />

            {isInstitution
              ? <Building2 size={22} strokeWidth={1} style={{ color: "#94A3B8", flexShrink: 0 }} />
              : <Globe size={22} strokeWidth={1} style={{ color: "#94A3B8", flexShrink: 0 }} />
            }

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: "Georgia, serif", fontSize: 15, color: NAVY, fontWeight: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {name || "—"}
              </div>
              {country && (
                <div style={{ fontSize: 11, color: "#64748B", marginTop: 1 }}>{country}</div>
              )}
            </div>

            <div style={{ textAlign: "right", flexShrink: 0 }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: NAVY, fontFamily: "monospace" }}>{fmtPts(score)}</div>
              <div style={{ fontSize: 10, color: "#94A3B8", marginTop: 1 }}>{count} member{count !== 1 ? "s" : ""}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Badges section ─────────────────────────────────────────────────────────────
function BadgesSection({ badges }) {
  return (
    <div style={{ marginTop: 48, background: WARM, borderTop: `1px solid ${BORDER}`, padding: "32px 0 36px" }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 20 }}>
        <Award size={14} strokeWidth={1.5} style={{ color: NAVY }} />
        <h2 style={{ fontFamily: "Georgia, serif", fontSize: 22, color: NAVY, fontWeight: 400 }}>My Achievements</h2>
        <span style={{ fontSize: 11, color: "#94A3B8" }}>{badges.length} earned</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 10 }}>
        {badges.map((b) => {
          const r = RARITY[b.rarity] || RARITY.common;
          return (
            <div
              key={b.code}
              style={{ padding: "12px 14px", background: r.bg, border: `1px solid ${r.border}` }}
              title={b.description}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 5 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: r.color }}>{b.label}</span>
                <span style={{ fontSize: 8, fontWeight: 700, color: r.color, textTransform: "uppercase", letterSpacing: "0.1em", opacity: 0.7 }}>{r.label}</span>
              </div>
              <p style={{ fontSize: 10, color: "#64748B", lineHeight: 1.4, margin: 0 }}>{b.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Transparency section ───────────────────────────────────────────────────────
function TransparencySection() {
  const FACTORS = [
    {
      Icon: BarChart2,
      title: "Research Activity",
      color: NAVY,
      items: [
        "Creating and completing research projects (+5 to +20 pts)",
        "Submitting manuscripts (+15 pts) and publishing them (+50 pts)",
        "Submitting grant applications (+20 pts) and receiving awards (+100 pts)",
        "Conference participation (+10 pts)",
        "Citation milestones (+5 pts)",
      ],
    },
    {
      Icon: Users,
      title: "Collaboration",
      color: "#1D4ED8",
      items: [
        "Creating research collaborations (+5 pts)",
        "Accepting collaboration invitations (+10 pts)",
        "Contributing to shared workspaces (+3 pts per contribution)",
      ],
    },
    {
      Icon: ClipboardCheck,
      title: "Peer Review",
      color: EMERALD,
      items: [
        "Completing peer reviews for other researchers (+15 pts)",
      ],
    },
    {
      Icon: GraduationCap,
      title: "Mentoring & Teaching",
      color: "#7C3AED",
      items: [
        "Completing mentor sessions (+15 pts)",
        "Publishing teaching lessons (+10 pts)",
      ],
    },
    {
      Icon: Shield,
      title: "Profile & Verification",
      color: "#B45309",
      items: [
        "Completing your academic profile (+20 pts)",
        "Connecting your ORCID account (+25 pts)",
      ],
    },
  ];

  return (
    <div style={{ margin: "48px -24px 0", background: "#0B1E38", padding: "40px 56px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <Shield size={13} strokeWidth={1.5} style={{ color: "rgba(255,255,255,0.35)" }} />
        <span style={{ fontSize: 10, fontWeight: 700, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.12em" }}>
          How Rankings Work
        </span>
      </div>
      <h2 style={{ fontFamily: "Georgia, serif", fontSize: 26, color: "white", fontWeight: 400, marginBottom: 10 }}>
        Transparent, Evidence-Based Rankings
      </h2>
      <p style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", maxWidth: 580, lineHeight: 1.7, marginBottom: 32 }}>
        Every ranking on Synaptiq is computed from real platform activity — no hidden algorithms, no purchased rankings, no popularity metrics.
        The factors below are the only inputs to your reputation score.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>
        {FACTORS.map(({ Icon, title, color, items }) => (
          <div key={title} style={{ padding: "16px 18px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 12 }}>
              <Icon size={14} strokeWidth={1.5} style={{ color }} />
              <span style={{ fontSize: 12, fontWeight: 700, color: "rgba(255,255,255,0.8)" }}>{title}</span>
            </div>
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {items.map((item, i) => (
                <li key={i} style={{ display: "flex", gap: 6, fontSize: 10, color: "rgba(255,255,255,0.38)", lineHeight: 1.6, marginBottom: 4 }}>
                  <span style={{ color, flexShrink: 0, marginTop: 2 }}>·</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 28, padding: "14px 20px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)", maxWidth: 640 }}>
        <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
          <Lightbulb size={13} strokeWidth={1.5} style={{ color: "#FCD34D", flexShrink: 0, marginTop: 1 }} />
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "rgba(255,255,255,0.7)", marginBottom: 4 }}>Institution & Country Rankings</div>
            <p style={{ fontSize: 10, color: "rgba(255,255,255,0.35)", lineHeight: 1.65, margin: 0 }}>
              Institutions and countries are ranked by the aggregate reputation scores of their Synaptiq members, not by external metrics, journal rankings, or third-party sources.
              These rankings reflect community activity on Synaptiq only.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Empty leaderboard state ────────────────────────────────────────────────────
function EmptyLeaderboardState({ cat }) {
  const isUserList = cat.isUserList;
  return (
    <div style={{ textAlign: "center", padding: "60px 24px", border: `1px dashed ${BORDER}` }}>
      <cat.Icon size={44} strokeWidth={1} style={{ color: "#E2E8F0", margin: "0 auto 20px", display: "block" }} />
      <h3 style={{ fontFamily: "Georgia, serif", fontSize: 22, color: "#1E293B", marginBottom: 8, fontWeight: 400 }}>
        No {cat.label} yet
      </h3>
      <p style={{ fontSize: 13, color: "#64748B", maxWidth: 440, margin: "0 auto 24px", lineHeight: 1.65 }}>
        {isUserList
          ? `Rankings for "${cat.label}" appear once researchers in this category have earned reputation points. Be the first.`
          : `Rankings will appear once enough ${cat.key === "top_institutions" ? "institutions" : "countries"} have members with reputation scores.`
        }
      </p>
      {isUserList && (
        <div style={{ display: "flex", flexDirection: "column", gap: 7, maxWidth: 380, margin: "0 auto" }}>
          {[
            { Icon: CheckCircle, text: "Complete your academic profile (+20 pts)" },
            { Icon: Shield,      text: "Connect your ORCID account (+25 pts)" },
            { Icon: Users,       text: "Start a collaboration or join one (+5–10 pts)" },
            { Icon: ClipboardCheck, text: "Complete a peer review (+15 pts)" },
          ].map(({ Icon, text }) => (
            <div key={text} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 12, color: "#64748B", textAlign: "left" }}>
              <Icon size={12} strokeWidth={1.5} style={{ color: EMERALD, flexShrink: 0, marginTop: 2 }} />
              {text}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Compare panel ──────────────────────────────────────────────────────────────
function ComparePanel({ researchers, onRemove, onClose }) {
  const ROWS = [
    { label: "Level",       fn: (r) => `${r.reputation_level || 1} · ${r.reputation_label || "—"}` },
    { label: "Institution", fn: (r) => r.institution || "—" },
    { label: "Country",     fn: (r) => r.country || "—" },
    { label: "Role",        fn: (r) => r.academic_role || "—" },
    { label: "Score",       fn: (r) => fmtPts(r.overall_score) },
    { label: "Badges",      fn: (r) => r.badges_count > 0 ? r.badges_count : "—" },
    { label: "Percentile",  fn: (r) => r.percentile_global > 0 ? `${r.percentile_global.toFixed(1)}%` : "—" },
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
              <th style={{ width: 80, padding: "3px 10px 3px 0", textAlign: "left", fontSize: 9, color: "rgba(255,255,255,0.28)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", borderBottom: "1px solid rgba(255,255,255,0.07)" }} />
              {researchers.map((r) => (
                <th key={r.user_id} style={{ padding: "3px 14px", textAlign: "left", borderBottom: "1px solid rgba(255,255,255,0.07)", minWidth: 160 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "white", fontFamily: "Georgia, serif", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 160 }}>{r.full_name}</div>
                  <button onClick={() => onRemove(r.user_id)} style={{ fontSize: 9, color: "rgba(255,255,255,0.28)", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 2, background: "none", border: "none", outline: "none", padding: 0, marginTop: 2 }}>
                    <X size={7} strokeWidth={1.5} /> Remove
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map(({ label, fn }) => (
              <tr key={label}>
                <td style={{ padding: "3px 10px 3px 0", fontSize: 9, color: "rgba(255,255,255,0.35)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", whiteSpace: "nowrap", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{label}</td>
                {researchers.map((r) => (
                  <td key={r.user_id} style={{ padding: "3px 14px", fontSize: 11, color: "rgba(255,255,255,0.75)", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>{fn(r)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

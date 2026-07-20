import React, { useState } from "react";
import { Link } from "react-router-dom";
import { AnalyticsLayout } from "@/layouts";
import {
  useResearchReputation,
  useReputationEvents,
  useReputationAnalytics,
  RESEARCH_LEVELS,
  getResearchLevel,
  getResearchNextLevel,
  getResearchProgress,
} from "@/hooks/useReputation";
import { useAuth } from "@/contexts/AuthContext";
import { WARM } from "@/lib/tokens";
import {
  TrendingUp, Award, BarChart2, Users, BookOpen, Star,
  ArrowRight, ChevronRight, Target,
} from "lucide-react";

// ── Research Intelligence Nav ─────────────────────────────────────────────────

const INTEL_NAV = [
  { to: "/analytics",           label: "Analytics"    },
  { to: "/research-impact",     label: "Impact"       },
  { to: "/impact-dashboard",    label: "Dashboard"    },
  { to: "/citations",           label: "Citations"    },
  { to: "/citation-monitoring", label: "Monitoring"   },
  { to: "/reputation",          label: "Reputation"   },
  { to: "/verification",        label: "Verification" },
];

function IntelNav({ current }) {
  const ChevSmall = () => (
    <svg width={10} height={10} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: "#CBD5E1", flexShrink: 0 }}>
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
      {INTEL_NAV.map((s, i) => {
        const isCur = s.to === current;
        return (
          <React.Fragment key={s.to}>
            {i > 0 && <ChevSmall />}
            <Link to={s.to} style={{ fontSize: 11, fontWeight: isCur ? 700 : 400, color: isCur ? "#0F2847" : "#94A3B8", padding: "3px 7px", background: isCur ? "rgba(15,40,71,0.07)" : "transparent", borderRadius: 3, textDecoration: "none", whiteSpace: "nowrap" }}>
              {s.label}
            </Link>
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ── Primitives ────────────────────────────────────────────────────────────────

function Stat({ label, value, sub, highlight }) {
  return (
    <div className={`border bg-white p-6 ${highlight ? "border-[#0F2847]" : "border-slate-200"}`}>
      <div className="overline">{label}</div>
      <div className={`font-serif text-5xl mt-3 tracking-tight ${highlight ? "text-[#0F2847]" : "text-slate-900"}`}>
        {value ?? "—"}
      </div>
      {sub && <div className="text-xs text-slate-400 mt-1 font-mono">{sub}</div>}
    </div>
  );
}

function SectionHeader({ label, action }) {
  return (
    <div className="flex items-center justify-between mb-5">
      <h2 className="overline">{label}</h2>
      {action}
    </div>
  );
}

function ScoreBar({ label, value, sub }) {
  const pct = Math.min(100, Math.max(0, Number(value) || 0));
  return (
    <div className="border border-slate-200 bg-white p-5">
      <div className="flex items-baseline justify-between mb-1">
        <div className="overline text-slate-500">{label}</div>
        <div className="font-serif text-2xl text-slate-900">{pct}</div>
      </div>
      <div className="h-1.5 bg-slate-100 relative mt-2">
        <div className="absolute inset-y-0 left-0 bg-[#0F2847] transition-all duration-700" style={{ width: `${pct}%` }} />
      </div>
      {sub && <div className="text-xs text-slate-400 mt-1.5 font-mono">{sub}</div>}
    </div>
  );
}

function ProgressBar({ value }) {
  const v = Math.min(100, Math.max(0, value || 0));
  return (
    <div className="h-1.5 bg-slate-100 w-full overflow-hidden">
      <div className="h-full bg-[#0F2847] transition-all duration-700" style={{ width: `${v}%` }} />
    </div>
  );
}

// ── Icon helpers ──────────────────────────────────────────────────────────────

const RARITY_COLORS = {
  common:    "border-slate-200 bg-slate-50 text-slate-600",
  uncommon:  "border-emerald-200 bg-emerald-50 text-emerald-700",
  rare:      "border-blue-200 bg-blue-50 text-blue-700",
  epic:      "border-purple-200 bg-purple-50 text-purple-700",
  legendary: "border-amber-300 bg-amber-50 text-amber-800",
};

const EVENT_ICONS = {
  project_created:      "📁",
  project_published:    "🚀",
  publication_added:    "📄",
  collaboration_joined: "🤝",
  review_submitted:     "✅",
  teaching_session:     "🎓",
  badge_earned:         "🏅",
  profile_updated:      "👤",
  default:              "⭐",
};

function eventIcon(type) {
  return EVENT_ICONS[type] || EVENT_ICONS.default;
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

// ── Skeletons ─────────────────────────────────────────────────────────────────

function SkeletonCard({ rows = 3 }) {
  return (
    <div className="border border-slate-200 bg-white p-5 animate-pulse space-y-3">
      <div className="h-3 w-1/3 bg-slate-200" />
      <div className="h-8 w-1/2 bg-slate-200" />
      {Array.from({ length: rows - 2 }).map((_, i) => (
        <div key={i} className="h-3 w-full bg-slate-200" />
      ))}
    </div>
  );
}

// ── Badge card ────────────────────────────────────────────────────────────────

function BadgeCard({ badge, locked = false }) {
  const rarityClass = RARITY_COLORS[badge.rarity] || RARITY_COLORS.common;
  return (
    <div className={`border p-4 flex flex-col items-center gap-2 text-center ${locked ? "opacity-40 grayscale" : ""} ${rarityClass}`}>
      <span className="text-2xl">{badge.icon || "🏅"}</span>
      <div className="text-xs font-semibold text-slate-700 leading-tight">{badge.label}</div>
      <div className="text-[10px] text-slate-400 capitalize font-mono">{badge.rarity}</div>
      {!locked && badge.awarded_at && (
        <div className="text-[10px] text-slate-400">{formatDate(badge.awarded_at)}</div>
      )}
      {locked && <div className="text-[10px] text-slate-400 italic">Not yet earned</div>}
    </div>
  );
}

// ── Monthly bar chart ─────────────────────────────────────────────────────────

function MonthlyBarChart({ months }) {
  if (!months || months.length === 0) {
    return <p className="text-slate-400 text-sm text-center py-8">No monthly data yet.</p>;
  }
  const maxPoints = Math.max(...months.map((m) => m.points || 0), 1);
  return (
    <div className="flex items-end gap-1.5 h-36 mt-2">
      {months.map((m) => {
        const pct = ((m.points || 0) / maxPoints) * 100;
        const barH = Math.max(4, Math.round((pct / 100) * 110));
        return (
          <div key={m.month} className="flex flex-col items-center gap-1 flex-1 min-w-0">
            <span className="text-[10px] text-slate-500 font-mono">{m.points}</span>
            <div
              title={`${m.month}: ${m.points} pts (${m.count} events)`}
              className="w-full bg-[#0F2847] transition-all duration-500"
              style={{ height: `${barH}px` }}
            />
            <span className="text-[10px] text-slate-400 truncate w-full text-center">{m.month?.slice(5)}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Category breakdown ────────────────────────────────────────────────────────

const CATEGORY_LABELS = {
  publication_score:   "Publications",
  collaboration_score: "Collaborations",
  reviewer_score:      "Peer Reviews",
  teaching_score:      "Teaching",
  profile_score:       "Profile",
  research_score:      "Research Activity",
};

function CategoryBreakdown({ breakdown, totalScore }) {
  if (!breakdown) return null;
  const entries = Object.entries(breakdown).filter(([k]) => k !== "overall_score");
  const total = totalScore || entries.reduce((a, [, v]) => a + (v || 0), 0) || 1;
  return (
    <div className="space-y-4">
      {entries.map(([key, val]) => {
        const pct = Math.min(100, Math.round(((val || 0) / total) * 100));
        return (
          <div key={key}>
            <div className="flex justify-between mb-1">
              <span className="text-xs font-medium text-slate-700">{CATEGORY_LABELS[key] || key}</span>
              <span className="text-xs text-slate-500 font-mono">{val} pts ({pct}%)</span>
            </div>
            <div className="h-1.5 bg-slate-100 w-full overflow-hidden">
              <div className="h-full bg-[#0F2847] transition-all duration-700" style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Percentile bar ────────────────────────────────────────────────────────────

function PercentileDisplay({ percentile }) {
  const pct = Math.min(100, Math.max(0, percentile || 0));
  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between">
        <span className="text-xs text-slate-500">0th</span>
        <div className="text-center">
          <div className="font-serif text-4xl text-[#0F2847] tracking-tight">{pct.toFixed(1)}</div>
          <div className="text-xs text-slate-400 font-mono">th percentile</div>
        </div>
        <span className="text-xs text-slate-500">100th</span>
      </div>
      <div className="h-2 bg-slate-100 relative overflow-hidden">
        <div className="absolute inset-y-0 left-0 bg-[#0F2847] transition-all duration-1000" style={{ width: `${pct}%` }} />
        <div className="absolute inset-y-0 w-px bg-white" style={{ left: `${pct}%` }} />
      </div>
      <p className="text-xs text-slate-500 text-center">
        You score higher than {pct.toFixed(1)}% of all researchers on the platform.
      </p>
    </div>
  );
}

// ── Quick actions ─────────────────────────────────────────────────────────────

function QuickActions() {
  const actions = [
    { to: "/analytics",          label: "Research Analytics",    icon: BarChart2 },
    { to: "/research-impact",    label: "Impact Dashboard",      icon: TrendingUp },
    { to: "/verification",       label: "Verification Center",   icon: Award },
    { to: "/leaderboards",       label: "Global Leaderboards",   icon: Star },
    { to: "/collaboration-intelligence", label: "Find Collaborators", icon: Users },
  ];
  return (
    <section>
      <SectionHeader label="Continue in Research Intelligence" />
      <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {actions.map(({ to, label, icon: Icon }) => (
          <Link key={to} to={to} className="border border-slate-200 bg-white p-4 hover:border-[#0F2847] transition-colors group block">
            <Icon size={14} strokeWidth={1.5} className="text-slate-300 group-hover:text-[#0F2847] mb-2 transition-colors" />
            <div className="text-xs font-medium text-slate-700 group-hover:text-[#0F2847] transition-colors">{label}</div>
          </Link>
        ))}
      </div>
    </section>
  );
}

// ── TABS ──────────────────────────────────────────────────────────────────────

const TABS = ["Overview", "Activity", "Rankings", "Badges"];

// ── Main component ────────────────────────────────────────────────────────────

export default function ReputationAnalytics() {
  const { user } = useAuth();
  const { data: rep, loading: repLoading, error: repError } = useResearchReputation();
  const { data: events, loading: evLoading }               = useReputationEvents(20);
  const { data: analytics, loading: analyticsLoading }     = useReputationAnalytics();
  const [activeTab, setActiveTab] = useState("Overview");

  // ── Header ────────────────────────────────────────────────────────────────

  const renderHeader = () => {
    if (repLoading) {
      return (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {[1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)}
        </div>
      );
    }
    if (repError) {
      return (
        <div className="border border-red-200 bg-red-50 p-6 text-sm text-red-700">
          Failed to load reputation data. Please refresh.
        </div>
      );
    }
    if (!rep) return null;

    const level     = getResearchLevel(rep.overall_score);
    const nextLevel = getResearchNextLevel(rep.overall_score);
    const progress  = getResearchProgress(rep.overall_score);

    return (
      <div className="space-y-5">
        {/* Score + level strip */}
        <div className="border border-[#0F2847] bg-white p-6">
          <div className="flex flex-col md:flex-row md:items-center gap-6">
            <div className="flex-shrink-0">
              <div className="overline text-[#0F2847] mb-1">Reputation Score</div>
              <div className="font-serif text-7xl text-[#0F2847] tracking-tight leading-none">{rep.overall_score}</div>
              <div className="text-xs text-slate-400 mt-1 font-mono">pts</div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2 mb-3">
                <span className={`inline-flex items-center gap-1 px-3 py-1 border text-sm font-semibold ${level.tone || "border-slate-200 bg-slate-50 text-slate-600"}`}>
                  Level {level.level} · {level.label}
                </span>
              </div>
              <p className="text-xs text-slate-500 mb-3">
                {nextLevel
                  ? `${nextLevel.min - rep.overall_score} pts to reach ${nextLevel.label}`
                  : "Maximum level reached — Distinguished Scholar"}
              </p>
              <ProgressBar value={progress} />
              <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
                <span>Level {level.level}</span>
                {nextLevel && <span>{progress}% · Level {nextLevel.level}</span>}
              </div>
            </div>
            {/* Rank pills */}
            <div className="flex gap-3 md:flex-col md:items-end">
              {[
                { label: "Global",      value: rep.rank_global },
                { label: "Country",     value: rep.rank_country },
                { label: "Institution", value: rep.rank_institution },
              ].map(({ label, value }) => (
                <div key={label} className="border border-slate-200 bg-white p-3 text-center min-w-[72px]">
                  <div className="font-serif text-2xl text-[#0F2847]">{value ? `#${value}` : "—"}</div>
                  <div className="overline text-slate-400 mt-0.5">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Score breakdown grid */}
        <div className="grid sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {[
            ["Research",       rep.research_score],
            ["Publications",   rep.publication_score],
            ["Collaborations", rep.collaboration_score],
            ["Peer Reviews",   rep.reviewer_score],
            ["Teaching",       rep.teaching_score],
            ["Profile",        rep.profile_score],
          ].map(([label, val]) => (
            <div key={label} className="border border-slate-200 bg-white p-4 text-center">
              <div className="font-serif text-3xl text-[#0F2847]">{val ?? 0}</div>
              <div className="overline text-slate-400 mt-1">{label}</div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // ── Tab: Overview ─────────────────────────────────────────────────────────

  const renderOverview = () => {
    if (repLoading) return (
      <div className="space-y-5">
        {[1, 2, 3].map((i) => <SkeletonCard key={i} rows={4} />)}
      </div>
    );
    if (!rep) return null;

    return (
      <div className="space-y-8">
        {/* Activity counts */}
        <section>
          <SectionHeader label="Research Activity" />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <Stat label="Projects"      value={rep.research_projects_count ?? 0} />
            <Stat label="Publications"  value={rep.research_publications_count ?? 0} />
            <Stat label="Reviews"       value={rep.research_reviews_count ?? 0} />
            <Stat label="Collaborations" value={rep.research_collaborations_count ?? 0} />
          </div>
        </section>

        {/* Score breakdown */}
        <section>
          <SectionHeader label="Score Breakdown" />
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              ["Research Activity",  rep.research_score],
              ["Publications",       rep.publication_score],
              ["Collaborations",     rep.collaboration_score],
              ["Peer Reviews",       rep.reviewer_score],
              ["Teaching",           rep.teaching_score],
              ["Profile",            rep.profile_score],
            ].map(([label, val]) => (
              <ScoreBar key={label} label={label} value={val} />
            ))}
          </div>
        </section>

        {/* Badge showcase */}
        {rep.badges && rep.badges.length > 0 && (
          <section>
            <SectionHeader
              label={`Earned Badges (${rep.badges.length})`}
              action={
                <button onClick={() => setActiveTab("Badges")} className="text-xs text-[#0F2847] hover:underline flex items-center gap-1">
                  View all <ArrowRight size={10} />
                </button>
              }
            />
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
              {rep.badges.slice(0, 6).map((b) => (
                <BadgeCard key={b.code} badge={b} />
              ))}
            </div>
          </section>
        )}

        {/* Rank pills */}
        <section>
          <SectionHeader
            label="Rankings"
            action={
              <button onClick={() => setActiveTab("Rankings")} className="text-xs text-[#0F2847] hover:underline flex items-center gap-1">
                Full rankings <ArrowRight size={10} />
              </button>
            }
          />
          <div className="grid sm:grid-cols-3 gap-5">
            <Stat label="Global Rank"      value={rep.rank_global ? `#${rep.rank_global}` : "—"} sub={`Top ${rep.percentile_global ? (100 - rep.percentile_global).toFixed(1) : "?"}%`} />
            <Stat label="Country Rank"     value={rep.rank_country ? `#${rep.rank_country}` : "—"} />
            <Stat label="Institution Rank" value={rep.rank_institution ? `#${rep.rank_institution}` : "—"} />
          </div>
        </section>
      </div>
    );
  };

  // ── Tab: Activity ─────────────────────────────────────────────────────────

  const renderActivity = () => {
    const loading = analyticsLoading || evLoading;
    if (loading) return (
      <div className="space-y-5">
        {[1, 2, 3].map((i) => <SkeletonCard key={i} rows={5} />)}
      </div>
    );

    return (
      <div className="space-y-8">
        {/* Monthly chart */}
        <section>
          <SectionHeader label="Reputation Points by Month" />
          <div className="border border-slate-200 bg-white p-5">
            <p className="text-xs text-slate-500 mb-4">Reputation points earned each calendar month</p>
            <MonthlyBarChart months={analytics?.events_by_month || []} />
          </div>
        </section>

        {/* Category breakdown */}
        <section>
          <SectionHeader label="Score by Category" />
          <div className="border border-slate-200 bg-white p-5">
            <CategoryBreakdown
              breakdown={analytics?.category_breakdown}
              totalScore={rep?.overall_score}
            />
          </div>
        </section>

        {/* Recent events */}
        <section>
          <SectionHeader
            label="Recent Activity"
            action={analytics?.total_events != null && (
              <span className="text-xs text-slate-400 font-mono">{analytics.total_events} total events</span>
            )}
          />
          <div className="border border-slate-200 bg-white p-5">
            {!events || events.length === 0 ? (
              <div className="py-8 text-center text-slate-400 text-sm">
                No events recorded yet. Publish research, collaborate, and engage to earn reputation points.
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {events.map((ev) => (
                  <div key={ev.event_id} className="flex items-start gap-3 py-3">
                    <span className="text-lg mt-0.5 flex-shrink-0">{eventIcon(ev.event_type)}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-800">{ev.description}</p>
                      <p className="text-xs text-slate-400 mt-0.5 font-mono">{formatDate(ev.created_at)}</p>
                    </div>
                    <span className={`text-sm font-semibold flex-shrink-0 font-mono ${ev.points >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                      {ev.points >= 0 ? "+" : ""}{ev.points} pts
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    );
  };

  // ── Tab: Rankings ─────────────────────────────────────────────────────────

  const renderRankings = () => {
    if (repLoading) return (
      <div className="space-y-5">
        {[1, 2].map((i) => <SkeletonCard key={i} rows={4} />)}
      </div>
    );
    if (!rep) return null;

    return (
      <div className="space-y-8">
        {/* Percentile */}
        <section>
          <SectionHeader label="Global Percentile" />
          <div className="border border-slate-200 bg-white p-6">
            <PercentileDisplay percentile={rep.percentile_global} />
          </div>
        </section>

        {/* Rank breakdown */}
        <section>
          <SectionHeader label="Your Rankings" />
          <div className="grid sm:grid-cols-3 gap-5">
            {[
              { label: "Global Rank",      value: rep.rank_global,      desc: "Across all researchers on the platform" },
              { label: "Country Rank",     value: rep.rank_country,     desc: "Among researchers in your country" },
              { label: "Institution Rank", value: rep.rank_institution, desc: "Among researchers at your institution" },
            ].map(({ label, value, desc }) => (
              <div key={label} className="border border-slate-200 bg-white p-6 text-center">
                <div className="font-serif text-5xl text-[#0F2847] tracking-tight">{value ? `#${value}` : "—"}</div>
                <div className="overline mt-2">{label}</div>
                <div className="text-xs text-slate-400 mt-1">{desc}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Level progression */}
        <section>
          <SectionHeader label="Level Progression" />
          <div className="border border-slate-200 bg-white p-5 space-y-3">
            {RESEARCH_LEVELS.map((lvl) => {
              const isCurrentLevel = rep.reputation_level === lvl.level;
              const isPast = (rep.reputation_level || 1) > lvl.level;
              return (
                <div
                  key={lvl.level}
                  className={`flex items-center gap-3 p-3 border transition-all ${
                    isCurrentLevel ? "border-[#0F2847] bg-[#0F2847]/4" :
                    isPast ? "border-emerald-200 bg-emerald-50" : "border-slate-100 bg-slate-50 opacity-60"
                  }`}
                >
                  <span className={`text-sm font-mono w-6 text-center flex-shrink-0 ${isPast || isCurrentLevel ? "text-[#0F2847]" : "text-slate-300"}`}>
                    {isPast ? "✓" : isCurrentLevel ? "▶" : lvl.level}
                  </span>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-slate-800">{lvl.label}</div>
                    <div className="text-xs text-slate-400 font-mono">{lvl.min} – {lvl.max === 9999999 ? "∞" : lvl.max} pts</div>
                  </div>
                  {isCurrentLevel && (
                    <span className="text-xs font-medium px-2 py-0.5 bg-[#0F2847] text-white">Current</span>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        <div className="text-center">
          <Link to="/leaderboards" className="inline-flex items-center gap-2 text-sm text-[#0F2847] hover:underline font-medium">
            View Global Leaderboards <ChevronRight size={14} />
          </Link>
        </div>
      </div>
    );
  };

  // ── Tab: Badges ───────────────────────────────────────────────────────────

  const BADGE_CATEGORIES = [
    { key: "research",       label: "Research" },
    { key: "publication",    label: "Publications" },
    { key: "collaboration",  label: "Collaboration" },
    { key: "teaching",       label: "Teaching" },
    { key: "community",      label: "Community" },
    { key: "ranking",        label: "Rankings" },
    { key: "profile",        label: "Profile" },
  ];

  const renderBadges = () => {
    if (repLoading) return (
      <div className="grid sm:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="border border-slate-200 bg-white p-4 animate-pulse h-28" />
        ))}
      </div>
    );
    if (!rep) return null;

    const earnedCodes = new Set((rep.badges || []).map((b) => b.code));
    const badgesByCategory = {};
    (rep.badges || []).forEach((b) => {
      const cat = b.category || "other";
      if (!badgesByCategory[cat]) badgesByCategory[cat] = [];
      badgesByCategory[cat].push(b);
    });

    const allCategories = BADGE_CATEGORIES.filter((c) => badgesByCategory[c.key]?.length > 0);

    if (Object.keys(badgesByCategory).length === 0) {
      return (
        <div className="border border-dashed border-slate-200 bg-white p-12 text-center">
          <span className="text-5xl mb-4 block">🏅</span>
          <div className="overline text-slate-500 mb-2">No badges yet</div>
          <p className="text-sm text-slate-500 max-w-sm mx-auto">
            Complete research activities — publish papers, collaborate with peers, submit reviews, and engage with the community to earn your first badge.
          </p>
        </div>
      );
    }

    return (
      <div className="space-y-8">
        {allCategories.map(({ key, label }) => {
          const badges = badgesByCategory[key] || [];
          if (badges.length === 0) return null;
          return (
            <section key={key}>
              <SectionHeader label={`${label} (${badges.length})`} />
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
                {badges.map((b) => (
                  <BadgeCard key={b.code} badge={b} locked={!earnedCodes.has(b.code)} />
                ))}
              </div>
            </section>
          );
        })}
      </div>
    );
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <AnalyticsLayout
      title="Reputation"
      subtitle="Your academic reputation score, earned badges, and relative rankings — all computed from real platform activity."
      nav={<IntelNav current="/reputation" />}
      actions={
        <Link to="/leaderboards" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none", padding: "8px 14px", border: "1px solid rgba(15,23,42,0.08)", background: "#fff" }}>
          <Star size={12} strokeWidth={1.5} /> Leaderboards
        </Link>
      }
    >
      <div className="space-y-10">

        {/* Reputation header */}
        {renderHeader()}

        {/* Tab bar */}
        <div className="border-b border-slate-200">
          <div className="flex gap-0">
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition -mb-px ${
                  activeTab === tab
                    ? "border-[#0F2847] text-[#0F2847]"
                    : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        <div>
          {activeTab === "Overview"  && renderOverview()}
          {activeTab === "Activity"  && renderActivity()}
          {activeTab === "Rankings"  && renderRankings()}
          {activeTab === "Badges"    && renderBadges()}
        </div>

        {/* Quick actions */}
        <QuickActions />

      </div>
    </AnalyticsLayout>
  );
}

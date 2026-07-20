import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { NAVY, WARM } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import {
  Search, Globe, Building2, Users, BookOpen, ShieldCheck,
  ChevronLeft, ChevronRight, AlertCircle, BarChart2, Trophy,
  TrendingUp,
} from "lucide-react";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(val, fallback = "—") {
  if (val == null || val === "") return fallback;
  return val;
}

function fmtNum(val) {
  if (val == null) return "—";
  return Number(val).toLocaleString();
}

function pct(val, max) {
  if (!max) return 0;
  return Math.min(100, Math.round((val / max) * 100));
}

function iisColor(score) {
  if (score >= 7500) return "#D97706";
  if (score >= 5000) return "#7C3AED";
  if (score >= 2500) return "#0891B2";
  return "#94A3B8";
}

function iisLabel(score) {
  if (score >= 7500) return "Distinguished";
  if (score >= 5000) return "Premier";
  if (score >= 2500) return "Established";
  return "Emerging";
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton({ h = "h-4", w = "w-full", className = "" }) {
  return <div className={`${h} ${w} bg-slate-200 animate-pulse ${className}`} />;
}

function CardSkeleton() {
  return (
    <div className="border border-slate-200 bg-white p-5 animate-pulse space-y-3">
      <Skeleton h="h-3" w="w-1/3" />
      <Skeleton h="h-5" w="w-2/3" />
      <Skeleton h="h-3" />
      <Skeleton h="h-3" w="w-1/2" />
    </div>
  );
}

// ── Error card ────────────────────────────────────────────────────────────────

function ErrorCard({ message, onRetry }) {
  return (
    <div className="border border-red-200 bg-red-50 p-6 text-center col-span-full">
      <AlertCircle size={22} strokeWidth={1.5} className="text-red-400 mx-auto mb-2" />
      <p className="text-red-700 text-sm mb-3">{message || "Failed to load data."}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs border border-red-300 text-red-700 px-3 py-1.5 hover:bg-red-100 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ icon: Icon = Building2, message, sub }) {
  return (
    <div className="border border-dashed border-slate-300 bg-slate-50 p-10 text-center col-span-full">
      <Icon size={28} strokeWidth={1.5} className="text-slate-300 mx-auto mb-3" />
      <p className="text-slate-600 text-sm font-medium">{message}</p>
      {sub && <p className="text-slate-400 text-xs mt-1 max-w-sm mx-auto">{sub}</p>}
    </div>
  );
}

// ── Type badge ────────────────────────────────────────────────────────────────

function TypeBadge({ type }) {
  const map = {
    university: "bg-blue-50 text-blue-700 border-blue-200",
    research_center: "bg-purple-50 text-purple-700 border-purple-200",
    laboratory: "bg-emerald-50 text-emerald-700 border-emerald-200",
    hospital: "bg-rose-50 text-rose-700 border-rose-200",
    government: "bg-amber-50 text-amber-700 border-amber-200",
    ngo: "bg-teal-50 text-teal-700 border-teal-200",
  };
  const cls = map[type] || "bg-slate-100 text-slate-600 border-slate-200";
  const label = type ? type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Unknown";
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 text-xs border ${cls}`}>
      {label}
    </span>
  );
}

// ── Institution card ──────────────────────────────────────────────────────────

function InstitutionCard({ inst }) {
  return (
    <div className="border border-slate-200 bg-white p-5 flex flex-col gap-3 hover:border-[#0F2847] transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-slate-900 truncate">{fmt(inst.name)}</h3>
          <div className="flex items-center gap-1 mt-0.5 text-xs text-slate-500">
            <Globe size={11} strokeWidth={1.5} />
            <span>{fmt(inst.country)}</span>
          </div>
        </div>
        {inst.verification_level >= 2 && (
          <ShieldCheck size={16} strokeWidth={1.5} className="text-emerald-600 flex-shrink-0 mt-0.5" />
        )}
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <TypeBadge type={inst.type} />
      </div>

      <div className="flex items-center gap-4 text-xs text-slate-500 border-t border-slate-100 pt-3">
        <div className="flex items-center gap-1">
          <Users size={11} strokeWidth={1.5} />
          <span>{fmtNum(inst.member_count)} members</span>
        </div>
        {inst.total_publications != null && (
          <div className="flex items-center gap-1">
            <BookOpen size={11} strokeWidth={1.5} />
            <span>{fmtNum(inst.total_publications)} pubs</span>
          </div>
        )}
      </div>

      <Link
        to={`/institution-hub/${inst._id || inst.institution_id}`}
        className="mt-auto text-xs font-medium text-[#0F2847] underline-offset-2 hover:underline"
      >
        View Profile
      </Link>
    </div>
  );
}

// ── Leaderboard rank row ──────────────────────────────────────────────────────

function RankRow({ rank, name, sub, score, scoreLabel, max = 10000, color }) {
  const pctVal = pct(score || 0, max);
  return (
    <div className="py-3 border-b border-slate-100 last:border-0">
      <div className="flex items-center gap-3">
        <div className="w-7 text-center">
          <span className="font-mono text-xs text-slate-400 font-semibold">{rank}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-slate-900 truncate">{name}</div>
          {sub && <div className="text-xs text-slate-500 truncate">{sub}</div>}
        </div>
        <div className="text-right">
          <div className="font-mono text-sm font-semibold" style={{ color: color || iisColor(score) }}>
            {fmtNum(score)}
          </div>
          {scoreLabel && <div className="text-[10px] text-slate-400">{scoreLabel}</div>}
        </div>
      </div>
      <div className="ml-10 mt-2 h-1.5 bg-slate-100 overflow-hidden">
        <div
          className="h-full transition-all duration-700"
          style={{ width: `${pctVal}%`, backgroundColor: color || iisColor(score) }}
        />
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

const INSTITUTION_TYPES = [
  { value: "", label: "All Types" },
  { value: "university", label: "University" },
  { value: "research_center", label: "Research Center" },
  { value: "laboratory", label: "Laboratory" },
  { value: "hospital", label: "Hospital" },
  { value: "government", label: "Government" },
  { value: "ngo", label: "NGO" },
];

export default function InstitutionHub() {
  const { user } = useAuth();

  const [activeTab, setActiveTab] = useState("discover");
  const [institutions, setInstitutions] = useState([]);
  const [total, setTotal] = useState(0);
  const [leaderboard, setLeaderboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lbLoading, setLbLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lbError, setLbError] = useState(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [countryFilter, setCountryFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [page, setPage] = useState(1);

  const LIMIT = 20;

  const fetchDirectory = useCallback(async (opts = {}) => {
    const q = opts.search ?? searchQuery;
    const c = opts.country ?? countryFilter;
    const t = opts.type ?? typeFilter;
    const p = opts.page ?? page;

    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page: p, limit: LIMIT });
      if (q) params.set("search", q);
      if (c) params.set("country", c);
      if (t) params.set("type", t);
      const res = await api.get(`/institution-hub/directory?${params}`);
      setInstitutions(res.data.institutions || res.data.data || []);
      setTotal(res.data.total || 0);
    } catch (e) {
      setError(e?.response?.data?.message || "Failed to load institutions.");
    } finally {
      setLoading(false);
    }
  }, [searchQuery, countryFilter, typeFilter, page]);

  const fetchLeaderboard = useCallback(async () => {
    setLbLoading(true);
    setLbError(null);
    try {
      const res = await api.get("/institution-hub/leaderboards");
      setLeaderboard(res.data);
    } catch (e) {
      setLbError(e?.response?.data?.message || "Failed to load leaderboards.");
    } finally {
      setLbLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDirectory();
    fetchLeaderboard();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = () => {
    setPage(1);
    fetchDirectory({ page: 1 });
  };

  const handleFilterChange = (key, val) => {
    setPage(1);
    if (key === "country") {
      setCountryFilter(val);
      fetchDirectory({ country: val, page: 1 });
    } else if (key === "type") {
      setTypeFilter(val);
      fetchDirectory({ type: val, page: 1 });
    }
  };

  const goPage = (p) => {
    setPage(p);
    fetchDirectory({ page: p });
  };

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <InstitutionLayout
      title="Institution Hub"
      subtitle="Discover universities, research centers, and laboratories"
    >
      {/* Tab bar */}
      <div className="border-b border-slate-200 bg-white sticky top-0 z-10">
          <nav className="flex gap-0">
            {[
              { key: "discover", label: "Discover", icon: Search },
              { key: "leaderboards", label: "Leaderboards", icon: Trophy },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === key
                    ? "border-[#0F2847] text-[#0F2847]"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                <Icon size={14} strokeWidth={1.5} />
                {label}
              </button>
            ))}
          </nav>
      </div>

        {/* ── Discover tab ── */}
        {activeTab === "discover" && (
          <div>
            {/* Filter row */}
            <div className="flex flex-wrap items-center gap-3 mb-6">
              <div className="relative flex-1 min-w-52">
                <Search size={14} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search institutions..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  className="w-full pl-9 pr-3 py-2 border border-slate-200 bg-white text-sm focus:outline-none focus:border-[#0F2847]"
                />
              </div>
              <input
                type="text"
                placeholder="Country..."
                value={countryFilter}
                onChange={(e) => handleFilterChange("country", e.target.value)}
                className="px-3 py-2 border border-slate-200 bg-white text-sm focus:outline-none focus:border-[#0F2847] w-36"
              />
              <select
                value={typeFilter}
                onChange={(e) => handleFilterChange("type", e.target.value)}
                className="px-3 py-2 border border-slate-200 bg-white text-sm focus:outline-none focus:border-[#0F2847]"
              >
                {INSTITUTION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
              <button
                onClick={handleSearch}
                className="px-4 py-2 bg-[#0F2847] text-white text-sm font-medium hover:bg-[#0a1f38] transition-colors"
              >
                Search
              </button>
            </div>

            {/* Results count */}
            {!loading && !error && (
              <p className="text-xs text-slate-500 mb-4">
                {fmtNum(total)} institution{total !== 1 ? "s" : ""} found
              </p>
            )}

            {/* Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {loading ? (
                Array.from({ length: 9 }).map((_, i) => <CardSkeleton key={i} />)
              ) : error ? (
                <ErrorCard message={error} onRetry={() => fetchDirectory()} />
              ) : institutions.length === 0 ? (
                <EmptyState
                  message="No institutions found"
                  sub="Try adjusting your search filters or clearing the country field."
                />
              ) : (
                institutions.map((inst) => (
                  <InstitutionCard key={inst._id || inst.institution_id} inst={inst} />
                ))
              )}
            </div>

            {/* Pagination */}
            {!loading && !error && totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                <button
                  onClick={() => goPage(page - 1)}
                  disabled={page <= 1}
                  className="p-2 border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft size={14} strokeWidth={1.5} />
                </button>
                <span className="text-sm text-slate-600 px-2">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => goPage(page + 1)}
                  disabled={page >= totalPages}
                  className="p-2 border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight size={14} strokeWidth={1.5} />
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── Leaderboards tab ── */}
        {activeTab === "leaderboards" && (
          <div>
            {lbLoading ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {[0, 1].map((i) => (
                  <div key={i} className="border border-slate-200 bg-white p-5 animate-pulse space-y-3">
                    <Skeleton h="h-4" w="w-1/2" />
                    {Array.from({ length: 8 }).map((_, j) => (
                      <Skeleton key={j} h="h-10" />
                    ))}
                  </div>
                ))}
              </div>
            ) : lbError ? (
              <ErrorCard message={lbError} onRetry={fetchLeaderboard} />
            ) : !leaderboard ? (
              <EmptyState message="No leaderboard data available." />
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Institution leaderboard */}
                <div className="border border-slate-200 bg-white p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <Building2 size={14} strokeWidth={1.5} className="text-slate-400" />
                    <h2 className="text-sm font-semibold text-slate-900">Top Institutions by Impact Score</h2>
                  </div>
                  {(leaderboard.institutions || []).length === 0 ? (
                    <EmptyState message="No institutions ranked yet." />
                  ) : (
                    <div>
                      {(leaderboard.institutions || []).map((inst, idx) => (
                        <RankRow
                          key={inst._id || idx}
                          rank={idx + 1}
                          name={inst.name}
                          sub={inst.country}
                          score={inst.iis_score || inst.impact_score}
                          scoreLabel={iisLabel(inst.iis_score || inst.impact_score)}
                          max={10000}
                        />
                      ))}
                    </div>
                  )}
                </div>

                {/* Researcher leaderboard */}
                <div className="border border-slate-200 bg-white p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <TrendingUp size={14} strokeWidth={1.5} className="text-slate-400" />
                    <h2 className="text-sm font-semibold text-slate-900">Top Researchers Globally</h2>
                  </div>
                  {(leaderboard.researchers || []).length === 0 ? (
                    <EmptyState message="No researcher rankings available." />
                  ) : (
                    <div>
                      {(leaderboard.researchers || []).map((r, idx) => (
                        <RankRow
                          key={r._id || idx}
                          rank={idx + 1}
                          name={r.name || r.display_name}
                          sub={r.institution_name || r.institution}
                          score={r.sis_score || r.impact_score}
                          scoreLabel="SIS"
                          max={10000}
                          color="#7C3AED"
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
    </InstitutionLayout>
  );
}

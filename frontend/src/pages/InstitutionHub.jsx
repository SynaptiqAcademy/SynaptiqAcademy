import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { NAVY, WARM } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import {
  Search, Globe, Building2, Users, BookOpen, ShieldCheck,
  Trophy, TrendingUp,
} from "lucide-react";
import {
  Card, NavTabs, Input, FormSelect, Button, Badge, ErrorState, EmptyState,
  SkeletonCard, Pagination,
} from "@/components/ds";

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

// ── Type badge ────────────────────────────────────────────────────────────────

const TYPE_COLOR = {
  university: "#1D4ED8",
  research_center: "#7C3AED",
  laboratory: "#047857",
  hospital: "#BE123C",
  government: "#B45309",
  ngo: "#0F766E",
};

function TypeBadge({ type }) {
  const color = TYPE_COLOR[type];
  const label = type ? type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Unknown";
  return (
    <Badge size="sm" variant="neutral" color={color}>
      {label}
    </Badge>
  );
}

// ── Institution card ──────────────────────────────────────────────────────────

function InstitutionCard({ inst }) {
  return (
    <Card padding="lg" className="flex flex-col gap-3">
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
    </Card>
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
      <div className="bg-white sticky top-0 z-10 mb-6">
        <NavTabs
          variant="underline"
          active={activeTab}
          onChange={setActiveTab}
          tabs={[
            { id: "discover", label: "Discover", icon: Search },
            { id: "leaderboards", label: "Leaderboards", icon: Trophy },
          ]}
        />
      </div>

        {/* ── Discover tab ── */}
        {activeTab === "discover" && (
          <div>
            {/* Filter row */}
            <div className="flex flex-wrap items-center gap-3 mb-6">
              <Input
                type="text"
                placeholder="Search institutions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                prefix={<Search size={14} strokeWidth={1.5} />}
                wrapperClassName="flex-1 min-w-52"
              />
              <Input
                type="text"
                placeholder="Country..."
                value={countryFilter}
                onChange={(e) => handleFilterChange("country", e.target.value)}
                wrapperClassName="w-36"
              />
              <FormSelect
                value={typeFilter}
                onChange={(e) => handleFilterChange("type", e.target.value)}
                wrapperClassName="w-auto"
              >
                {INSTITUTION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </FormSelect>
              <Button onClick={handleSearch}>Search</Button>
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
                Array.from({ length: 9 }).map((_, i) => <SkeletonCard key={i} rows={3} />)
              ) : error ? (
                <div className="col-span-full"><ErrorState message={error} onRetry={() => fetchDirectory()} /></div>
              ) : institutions.length === 0 ? (
                <div className="col-span-full">
                  <EmptyState
                    icon={<Building2 />}
                    title="No institutions found"
                    description="Try adjusting your search filters or clearing the country field."
                  />
                </div>
              ) : (
                institutions.map((inst) => (
                  <InstitutionCard key={inst._id || inst.institution_id} inst={inst} />
                ))
              )}
            </div>

            {/* Pagination */}
            {!loading && !error && totalPages > 1 && (
              <div className="mt-8">
                <Pagination page={page} totalPages={totalPages} onPage={goPage} />
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
                  <SkeletonCard key={i} rows={8} />
                ))}
              </div>
            ) : lbError ? (
              <ErrorState message={lbError} onRetry={fetchLeaderboard} />
            ) : !leaderboard ? (
              <EmptyState title="No leaderboard data available." />
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Institution leaderboard */}
                <Card padding="lg">
                  <div className="flex items-center gap-2 mb-4">
                    <Building2 size={14} strokeWidth={1.5} className="text-slate-400" />
                    <h2 className="text-sm font-semibold text-slate-900">Top Institutions by Impact Score</h2>
                  </div>
                  {(leaderboard.institutions || []).length === 0 ? (
                    <EmptyState title="No institutions ranked yet." />
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
                </Card>

                {/* Researcher leaderboard */}
                <Card padding="lg">
                  <div className="flex items-center gap-2 mb-4">
                    <TrendingUp size={14} strokeWidth={1.5} className="text-slate-400" />
                    <h2 className="text-sm font-semibold text-slate-900">Top Researchers Globally</h2>
                  </div>
                  {(leaderboard.researchers || []).length === 0 ? (
                    <EmptyState title="No researcher rankings available." />
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
                </Card>
              </div>
            )}
          </div>
        )}
    </InstitutionLayout>
  );
}

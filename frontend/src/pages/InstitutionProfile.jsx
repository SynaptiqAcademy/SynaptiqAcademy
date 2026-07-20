/* eslint-disable */
import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { EMERALD, NAVY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import {
  Globe, Users, BookOpen, ShieldCheck, Building2, AlertCircle,
  DollarSign, BarChart2, Clock, TrendingUp, FileText, Activity,
  CheckCircle2, ChevronDown, ChevronUp, Search, Calendar, Award,
  Lock,
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

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function relativeTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return formatDate(iso);
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

// ── Error card ────────────────────────────────────────────────────────────────

function ErrorCard({ message, onRetry }) {
  return (
    <div className="border border-red-200 bg-red-50 p-6 text-center">
      <AlertCircle size={20} strokeWidth={1.5} className="text-red-400 mx-auto mb-2" />
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

function EmptyState({ icon: Icon = AlertCircle, message, sub }) {
  return (
    <div className="border border-dashed border-slate-300 bg-slate-50 p-10 text-center">
      <Icon size={28} strokeWidth={1.5} className="text-slate-300 mx-auto mb-3" />
      <p className="text-slate-600 text-sm font-medium">{message}</p>
      {sub && <p className="text-slate-400 text-xs mt-1 max-w-sm mx-auto">{sub}</p>}
    </div>
  );
}

// ── IIS Ring (SVG) ────────────────────────────────────────────────────────────

function IisRing({ score = 0, size = 120, stroke = 10 }) {
  const max = 10000;
  const r = (size - stroke) / 2;
  const ci = 2 * Math.PI * r;
  const off = ci - (Math.min(max, score) / max) * ci;
  const color = iisColor(score);

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90 absolute inset-0">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={color} strokeWidth={stroke}
          strokeDasharray={ci} strokeDashoffset={off}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <div className="text-center z-10">
        <div className="font-mono text-xl font-bold" style={{ color }}>{fmtNum(score)}</div>
        <div className="text-[10px] text-slate-500 font-medium">IIS</div>
      </div>
    </div>
  );
}

// ── Progress bar ──────────────────────────────────────────────────────────────

function ProgressBar({ label, value = 0, max = 1000, color = "#0F2847" }) {
  const p = pct(value, max);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-700 capitalize">{String(label).replace(/_/g, " ")}</span>
        <span className="text-xs text-slate-500 font-mono">{fmtNum(value)}</span>
      </div>
      <div className="h-2 bg-slate-100 w-full overflow-hidden">
        <div
          className="h-full transition-all duration-700"
          style={{ width: `${p}%`, backgroundColor: color }}
        />
      </div>
      <div className="text-[10px] text-slate-400 mt-0.5">{p}% of max</div>
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
  };
  const cls = map[type] || "bg-slate-100 text-slate-600 border-slate-200";
  const label = type ? type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Unknown";
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 text-xs border ${cls}`}>{label}</span>
  );
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ label, color = "slate" }) {
  const palette = {
    green: "bg-emerald-50 text-emerald-700 border-emerald-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200",
    amber: "bg-amber-50 text-amber-700 border-amber-200",
    red: "bg-red-50 text-red-700 border-red-200",
    slate: "bg-slate-100 text-slate-600 border-slate-200",
  };
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 text-xs border ${palette[color] || palette.slate}`}>
      {label}
    </span>
  );
}

// ── Grant status color ────────────────────────────────────────────────────────

function grantStatusColor(status) {
  const m = {
    approved: "green",
    pending: "amber",
    rejected: "red",
    under_review: "blue",
  };
  return m[status] || "slate";
}

// ── VBar chart ────────────────────────────────────────────────────────────────

function VBarChart({ items = [], valueKey = "count", labelKey = "year", color = "#0891B2", height = 100 }) {
  const max = Math.max(...items.map((i) => i[valueKey] || 0), 1);
  return (
    <div className="flex items-end gap-1" style={{ height }}>
      {items.map((item, idx) => {
        const h = Math.max(4, pct(item[valueKey] || 0, max));
        return (
          <div key={idx} className="flex-1 flex flex-col items-center gap-1">
            <div
              className="w-full transition-all duration-700 min-h-[4px]"
              style={{ height: `${h}%`, backgroundColor: color }}
              title={`${item[labelKey]}: ${item[valueKey]}`}
            />
            <div className="text-[9px] text-slate-400 truncate w-full text-center">{item[labelKey]}</div>
          </div>
        );
      })}
    </div>
  );
}

// ── Timeline event ────────────────────────────────────────────────────────────

const EVENT_CONFIG = {
  member_joined: { icon: Users, color: "#059669", label: "Member Joined" },
  publication_added: { icon: BookOpen, color: "#0891B2", label: "Publication Added" },
  grant_applied: { icon: DollarSign, color: "#D97706", label: "Grant Applied" },
  grant_funded: { icon: CheckCircle2, color: "#059669", label: "Grant Funded" },
  verification_upgraded: { icon: ShieldCheck, color: "#7C3AED", label: "Verification Upgraded" },
  unit_created: { icon: Building2, color: "#0F2847", label: "Unit Created" },
  default: { icon: Activity, color: "#64748B", label: "Activity" },
};

function TimelineEvent({ event }) {
  const cfg = EVENT_CONFIG[event.event_type] || EVENT_CONFIG.default;
  const Icon = cfg.icon;
  return (
    <div className="flex gap-3 py-3 border-b border-slate-100 last:border-0">
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
        style={{ backgroundColor: `${cfg.color}18` }}
      >
        <Icon size={13} strokeWidth={1.5} style={{ color: cfg.color }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-slate-900">{event.title || cfg.label}</span>
          <span className="text-[10px] text-slate-400 flex-shrink-0">{relativeTime(event.created_at)}</span>
        </div>
        {event.description && (
          <p className="text-xs text-slate-500 mt-0.5 truncate">{event.description}</p>
        )}
      </div>
    </div>
  );
}

// ── TABS definition ───────────────────────────────────────────────────────────

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "publications", label: "Publications" },
  { key: "grants", label: "Grants" },
  { key: "researchers", label: "Researchers" },
  { key: "impact", label: "Impact" },
  { key: "units", label: "Units" },
  { key: "timeline", label: "Timeline" },
  { key: "recommendations", label: "Recommendations" },
];

const COMPONENT_COLORS = [
  "#0F2847", "#0891B2", "#7C3AED", "#059669",
  "#D97706", "#DC2626", "#DB2777", "#64748B",
];

// ── Main component ────────────────────────────────────────────────────────────

export default function InstitutionProfile() {
  const { id } = useParams();
  const { user } = useAuth();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [profileError, setProfileError] = useState(null);

  const [activeTab, setActiveTab] = useState("overview");
  const [tabData, setTabData] = useState({});
  const [tabLoading, setTabLoading] = useState({});
  const [tabError, setTabError] = useState({});
  const loadedTabs = useRef(new Set());

  // Grant filter
  const [grantStatusFilter, setGrantStatusFilter] = useState("all");
  // Publication search
  const [pubSearch, setPubSearch] = useState("");

  const fetchTabData = useCallback(
    async (tab) => {
      setTabLoading((prev) => ({ ...prev, [tab]: true }));
      setTabError((prev) => ({ ...prev, [tab]: null }));
      try {
        let data = {};
        if (tab === "overview") {
          const impRes = await api.get(`/institution-hub/${id}/impact`);
          data = impRes.data;
        } else if (tab === "publications") {
          const res = await api.get(`/institution-hub/${id}/publications?page=1&limit=20`);
          data = res.data;
        } else if (tab === "grants") {
          const res = await api.get(`/institution-hub/${id}/grants?page=1&limit=20`);
          data = res.data;
        } else if (tab === "researchers") {
          const res = await api.get(`/institution-hub/${id}/research-directory`);
          data = res.data;
        } else if (tab === "impact") {
          const res = await api.get(`/institution-hub/${id}/impact`);
          data = res.data;
        } else if (tab === "units") {
          const res = await api.get(`/institution-hub/${id}/unit-rankings`);
          data = res.data;
        } else if (tab === "timeline") {
          const res = await api.get(`/institution-hub/${id}/timeline`);
          data = res.data;
        } else if (tab === "recommendations") {
          if (!user) {
            data = { auth_required: true };
          } else {
            try {
              const res = await api.get(`/institution-hub/${id}/recommendations`);
              data = res.data;
            } catch (e) {
              if (e?.response?.status === 401 || e?.response?.status === 403) {
                data = { auth_required: true };
              } else {
                throw e;
              }
            }
          }
        }
        setTabData((prev) => ({ ...prev, [tab]: data }));
      } catch (e) {
        setTabError((prev) => ({
          ...prev,
          [tab]: e?.response?.data?.message || `Failed to load ${tab} data.`,
        }));
      } finally {
        setTabLoading((prev) => ({ ...prev, [tab]: false }));
      }
    },
    [id, user]
  );

  const handleTabChange = useCallback(
    (tab) => {
      setActiveTab(tab);
      if (!loadedTabs.current.has(tab)) {
        loadedTabs.current.add(tab);
        fetchTabData(tab);
      }
    },
    [fetchTabData]
  );

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      setProfileError(null);
      try {
        const res = await api.get(`/institution-hub/${id}/public-profile`);
        setProfile(res.data);
      } catch (e) {
        setProfileError(e?.response?.data?.message || "Failed to load institution profile.");
      } finally {
        setLoading(false);
      }
    };
    init();
    loadedTabs.current.add("overview");
    fetchTabData("overview");
  }, [id, fetchTabData]);

  // ── Loading state ──────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-10 animate-pulse space-y-4">
        <div className="h-8 bg-slate-200 w-1/3" />
        <div className="h-4 bg-slate-200 w-1/2" />
        <div className="h-32 bg-slate-200 w-full mt-6" />
      </div>
    );
  }

  if (profileError) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-10">
        <ErrorCard message={profileError} onRetry={() => window.location.reload()} />
      </div>
    );
  }

  if (!profile) return null;

  const iisScore = profile.iis_score || 0;

  // ── Render helpers ─────────────────────────────────────────────────────────

  const td = tabData[activeTab] || {};
  const tl = tabLoading[activeTab];
  const te = tabError[activeTab];

  // ── Overview tab content ───────────────────────────────────────────────────

  function OverviewContent() {
    const impactData = tabData["overview"] || {};
    const components = impactData.components || {};
    const componentKeys = Object.keys(components);
    const topResearchers = profile.top_researchers || impactData.top_researchers || [];

    return (
      <div className="space-y-6">
        {/* Key stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: "Members", value: fmtNum(profile.member_count), icon: Users },
            { label: "Publications", value: fmtNum(profile.total_publications || impactData.total_publications), icon: BookOpen },
            { label: "Citations", value: fmtNum(profile.total_citations || impactData.total_citations), icon: TrendingUp },
            { label: "Grants", value: fmtNum(profile.total_grants || impactData.total_grants), icon: DollarSign },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="border border-slate-200 bg-white p-4">
              <div className="flex items-center gap-1.5 mb-2">
                <Icon size={12} strokeWidth={1.5} className="text-slate-400" />
                <span className="text-xs text-slate-500">{label}</span>
              </div>
              <div className="font-serif text-2xl text-slate-900">{value}</div>
            </div>
          ))}
        </div>

        {/* IIS components */}
        {componentKeys.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">IIS Score Breakdown</h3>
            <div className="space-y-4">
              {componentKeys.map((key, idx) => {
                const comp = components[key];
                const val = typeof comp === "object" ? comp.score || comp.value || 0 : comp || 0;
                const maxVal = typeof comp === "object" ? comp.max_score || comp.max || 1000 : 1000;
                return (
                  <ProgressBar
                    key={key}
                    label={key}
                    value={val}
                    max={maxVal}
                    color={COMPONENT_COLORS[idx % COMPONENT_COLORS.length]}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* Top researchers */}
        {topResearchers.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Top Researchers</h3>
            <div className="space-y-3">
              {topResearchers.slice(0, 5).map((r, idx) => (
                <div key={r._id || idx} className="flex items-center gap-3">
                  <span className="font-mono text-xs text-slate-400 w-5 text-center">{idx + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-900 truncate">
                      {r.name || r.display_name}
                    </div>
                    {r.sis_score != null && (
                      <div className="text-xs text-slate-500">SIS {fmtNum(r.sis_score)}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── Publications tab ───────────────────────────────────────────────────────

  function PublicationsContent() {
    const data = tabData["publications"] || {};
    const pubs = data.publications || data.data || [];
    const stats = data.stats || {};
    const trends = data.trends || data.citation_trends || [];

    const filtered = pubSearch
      ? pubs.filter((p) =>
          (p.title || "").toLowerCase().includes(pubSearch.toLowerCase())
        )
      : pubs;

    return (
      <div className="space-y-5">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Total Publications", value: fmtNum(stats.total_publications || pubs.length) },
            { label: "Total Citations", value: fmtNum(stats.total_citations) },
            { label: "Avg Citations", value: fmt(stats.avg_citations != null ? stats.avg_citations.toFixed(1) : null) },
          ].map(({ label, value }) => (
            <div key={label} className="border border-slate-200 bg-white p-4">
              <div className="text-xs text-slate-500 mb-1">{label}</div>
              <div className="font-serif text-2xl text-slate-900">{value}</div>
            </div>
          ))}
        </div>

        {/* Citation trend chart */}
        {trends.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Citation Trends</h3>
            <VBarChart items={trends} valueKey="count" labelKey="year" color="#0891B2" height={100} />
          </div>
        )}

        {/* Search + table */}
        <div className="border border-slate-200 bg-white">
          <div className="p-4 border-b border-slate-100">
            <div className="relative">
              <Search size={13} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search publications..."
                value={pubSearch}
                onChange={(e) => setPubSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-2 border border-slate-200 text-sm focus:outline-none focus:border-[#0F2847]"
              />
            </div>
          </div>
          {filtered.length === 0 ? (
            <div className="p-8">
              <EmptyState icon={BookOpen} message="No publications found." />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Title</th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Year</th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Journal</th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Citations</th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Researcher</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((pub, idx) => (
                    <tr key={pub._id || idx} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-2.5 max-w-xs">
                        <div className="text-sm text-slate-900 truncate" title={pub.title}>{fmt(pub.title)}</div>
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-500 whitespace-nowrap">{fmt(pub.year)}</td>
                      <td className="px-4 py-2.5 text-xs text-slate-500 whitespace-nowrap">{fmt(pub.journal || pub.venue)}</td>
                      <td className="px-4 py-2.5 text-xs font-mono text-slate-700">{fmtNum(pub.citations)}</td>
                      <td className="px-4 py-2.5 text-xs text-slate-500">{fmt(pub.researcher_name || pub.author)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Grants tab ─────────────────────────────────────────────────────────────

  function GrantsContent() {
    const data = tabData["grants"] || {};
    const grants = data.grants || data.data || [];
    const stats = data.stats || {};

    const filtered =
      grantStatusFilter === "all"
        ? grants
        : grants.filter((g) => g.status === grantStatusFilter);

    return (
      <div className="space-y-5">
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Total Applications", value: fmtNum(stats.total_applications || grants.length) },
            { label: "Success Rate", value: stats.success_rate != null ? `${stats.success_rate.toFixed(1)}%` : "—" },
            { label: "Total Awarded", value: stats.total_awarded != null ? `$${fmtNum(stats.total_awarded)}` : "—" },
          ].map(({ label, value }) => (
            <div key={label} className="border border-slate-200 bg-white p-4">
              <div className="text-xs text-slate-500 mb-1">{label}</div>
              <div className="font-serif text-2xl text-slate-900">{value}</div>
            </div>
          ))}
        </div>

        <div className="border border-slate-200 bg-white">
          <div className="p-4 border-b border-slate-100 flex gap-2 flex-wrap">
            {["all", "pending", "approved", "rejected"].map((s) => (
              <button
                key={s}
                onClick={() => setGrantStatusFilter(s)}
                className={`px-3 py-1 text-xs font-medium transition-colors ${
                  grantStatusFilter === s
                    ? "bg-[#0F2847] text-white"
                    : "border border-slate-200 text-slate-600 hover:bg-slate-50"
                }`}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
          {filtered.length === 0 ? (
            <div className="p-8">
              <EmptyState icon={DollarSign} message="No grants found." />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Grant Title</th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Applicant</th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Status</th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Amount</th>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Submitted</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((g, idx) => (
                    <tr key={g._id || idx} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-2.5 max-w-xs">
                        <div className="text-sm text-slate-900 truncate" title={g.title}>{fmt(g.title)}</div>
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-500">{fmt(g.applicant_name || g.applicant)}</td>
                      <td className="px-4 py-2.5">
                        <StatusBadge label={g.status || "unknown"} color={grantStatusColor(g.status)} />
                      </td>
                      <td className="px-4 py-2.5 text-xs font-mono text-slate-700">
                        {g.amount != null ? `$${fmtNum(g.amount)}` : "—"}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-slate-500 whitespace-nowrap">
                        {formatDate(g.submitted_at || g.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Researchers tab ────────────────────────────────────────────────────────

  function ResearchersContent() {
    const data = tabData["researchers"] || {};
    const top = data.top_researchers || data.researchers || [];
    const members = data.members || [];
    const maxSis = Math.max(...top.map((r) => r.sis_score || 0), 1);

    return (
      <div className="space-y-5">
        {top.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Top Researchers by SIS Score</h3>
            <div className="space-y-4">
              {top.map((r, idx) => {
                const p = pct(r.sis_score || 0, maxSis);
                return (
                  <div key={r._id || idx}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-slate-400 w-5 text-center">{idx + 1}</span>
                        <span className="text-sm text-slate-900">{r.name || r.display_name}</span>
                      </div>
                      <span className="font-mono text-xs text-slate-600">{fmtNum(r.sis_score)}</span>
                    </div>
                    <div className="ml-7 h-1.5 bg-slate-100 overflow-hidden">
                      <div
                        className="h-full transition-all duration-700 bg-[#7C3AED]"
                        style={{ width: `${p}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {members.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">All Members</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {members.map((m, idx) => (
                <div key={m._id || idx} className="flex items-center gap-3 p-3 border border-slate-100">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-900 truncate">{m.name || m.display_name}</div>
                    <div className="text-xs text-slate-500">{m.role || m.user_type || "Member"}</div>
                  </div>
                  {m.sis_score != null && (
                    <span className="text-xs font-mono text-slate-500">SIS {fmtNum(m.sis_score)}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {top.length === 0 && members.length === 0 && (
          <EmptyState icon={Users} message="No researchers listed." />
        )}
      </div>
    );
  }

  // ── Impact tab ─────────────────────────────────────────────────────────────

  function ImpactContent() {
    const data = tabData["impact"] || {};
    const components = data.components || {};
    const avg = data.platform_average || {};
    const componentKeys = Object.keys(components);

    return (
      <div className="space-y-5">
        <div className="border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-4 mb-6">
            <IisRing score={data.iis_score || iisScore} size={100} stroke={8} />
            <div>
              <div className="text-xs text-slate-500 mb-1">Institution Impact Score</div>
              <div className="font-serif text-3xl text-slate-900">{fmtNum(data.iis_score || iisScore)}</div>
              <div className="text-xs font-medium mt-0.5" style={{ color: iisColor(data.iis_score || iisScore) }}>
                {iisLabel(data.iis_score || iisScore)}
              </div>
            </div>
          </div>

          {componentKeys.length > 0 && (
            <div className="space-y-5">
              {componentKeys.map((key, idx) => {
                const comp = components[key];
                const val = typeof comp === "object" ? comp.score || comp.value || 0 : comp || 0;
                const maxVal = typeof comp === "object" ? comp.max_score || comp.max || 1000 : 1000;
                const platformVal = avg[key] || 0;
                const isAbove = val >= platformVal;

                return (
                  <div key={key} className="border border-slate-100 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-900 capitalize">
                        {key.replace(/_/g, " ")}
                      </span>
                      <StatusBadge
                        label={isAbove ? "Above Average" : "Below Average"}
                        color={isAbove ? "green" : "amber"}
                      />
                    </div>
                    <ProgressBar label="" value={val} max={maxVal} color={COMPONENT_COLORS[idx % COMPONENT_COLORS.length]} />
                    {platformVal > 0 && (
                      <div className="text-xs text-slate-400 mt-1">
                        Platform avg: {fmtNum(platformVal)} — Your score: {fmtNum(val)}
                      </div>
                    )}
                    {typeof comp === "object" && comp.description && (
                      <p className="text-xs text-slate-500 mt-2">{comp.description}</p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Units tab ──────────────────────────────────────────────────────────────

  function UnitsContent() {
    const data = tabData["units"] || {};
    const units = data.units || data.rankings || data.data || [];

    if (units.length === 0) {
      return <EmptyState icon={Building2} message="No units listed." sub="Units will appear here once added by the institution admin." />;
    }

    return (
      <div className="border border-slate-200 bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Rank</th>
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Unit Name</th>
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Members</th>
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-600">Publications</th>
            </tr>
          </thead>
          <tbody>
            {units.map((u, idx) => (
              <tr key={u._id || idx} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-4 py-2.5 font-mono text-xs text-slate-400">{idx + 1}</td>
                <td className="px-4 py-2.5 text-sm font-medium text-slate-900">{fmt(u.name)}</td>
                <td className="px-4 py-2.5 text-xs text-slate-600">{fmtNum(u.member_count || u.members)}</td>
                <td className="px-4 py-2.5 text-xs text-slate-600">{fmtNum(u.publication_count || u.publications)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // ── Timeline tab ───────────────────────────────────────────────────────────

  function TimelineContent() {
    const data = tabData["timeline"] || {};
    const events = data.events || data.timeline || data.data || [];
    const sorted = [...events].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    if (sorted.length === 0) {
      return <EmptyState icon={Clock} message="No timeline events yet." />;
    }

    return (
      <div className="border border-slate-200 bg-white p-5">
        {sorted.map((ev, idx) => (
          <TimelineEvent key={ev._id || idx} event={ev} />
        ))}
      </div>
    );
  }

  // ── Recommendations tab ────────────────────────────────────────────────────

  function RecommendationsContent() {
    const data = tabData["recommendations"] || {};

    if (data.auth_required) {
      return (
        <div className="border border-slate-200 bg-white p-10 text-center">
          <Lock size={28} strokeWidth={1.5} className="text-slate-300 mx-auto mb-3" />
          <p className="text-slate-600 text-sm font-medium">Sign in to view recommendations</p>
          <p className="text-slate-400 text-xs mt-1">
            Log in to see personalized collaboration and funding recommendations.
          </p>
          <Link
            to="/login"
            className="inline-block mt-4 px-4 py-2 bg-[#0F2847] text-white text-sm font-medium hover:bg-[#0a1f38] transition-colors"
          >
            Sign In
          </Link>
        </div>
      );
    }

    const collab = data.collaborating_institutions || [];
    const funding = data.funding_opportunities || [];
    const recruit = data.researchers_to_recruit || [];

    if (collab.length === 0 && funding.length === 0 && recruit.length === 0) {
      return <EmptyState message="No recommendations available at this time." />;
    }

    return (
      <div className="space-y-6">
        {collab.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Collaborating Institutions</h3>
            <div className="space-y-3">
              {collab.map((inst, idx) => (
                <div key={inst._id || idx} className="p-3 border border-slate-100 flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-900 truncate">{inst.name}</div>
                    <div className="text-xs text-slate-500">{inst.country}</div>
                  </div>
                  {inst.match_score != null && (
                    <span className="text-xs font-mono text-[#0F2847]">{Math.round(inst.match_score)}% match</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {funding.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Funding Opportunities</h3>
            <div className="space-y-3">
              {funding.map((f, idx) => (
                <div key={f._id || idx} className="p-3 border border-slate-100">
                  <div className="text-sm font-medium text-slate-900">{fmt(f.title || f.name)}</div>
                  {f.description && <p className="text-xs text-slate-500 mt-1">{f.description}</p>}
                  {f.deadline && <div className="text-xs text-slate-400 mt-1">Deadline: {formatDate(f.deadline)}</div>}
                </div>
              ))}
            </div>
          </div>
        )}

        {recruit.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Researchers to Recruit</h3>
            <div className="space-y-3">
              {recruit.map((r, idx) => (
                <div key={r._id || idx} className="p-3 border border-slate-100 flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-900">{r.name || r.display_name}</div>
                    <div className="text-xs text-slate-500">{r.expertise || r.field}</div>
                  </div>
                  {r.sis_score != null && (
                    <span className="text-xs font-mono text-slate-500">SIS {fmtNum(r.sis_score)}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── Tab content dispatcher ─────────────────────────────────────────────────

  function TabContent() {
    if (tl) {
      return (
        <div className="space-y-3 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 bg-slate-200" />
          ))}
        </div>
      );
    }
    if (te) {
      return <ErrorCard message={te} />;
    }

    switch (activeTab) {
      case "overview":        return <OverviewContent />;
      case "publications":    return <PublicationsContent />;
      case "grants":          return <GrantsContent />;
      case "researchers":     return <ResearchersContent />;
      case "impact":          return <ImpactContent />;
      case "units":           return <UnitsContent />;
      case "timeline":        return <TimelineContent />;
      case "recommendations": return <RecommendationsContent />;
      default:                return null;
    }
  }

  return (
    <InstitutionLayout
      title={fmt(profile.name)}
      subtitle={profile.country ? `${profile.country}${profile.member_count != null ? ` · ${fmtNum(profile.member_count)} members` : ""}` : undefined}
    >
      {/* Tab bar */}
      <div className="border-b border-slate-200 bg-white sticky top-0 z-10 overflow-x-auto">
          <nav className="flex gap-0 min-w-max">
            {TABS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => handleTabChange(key)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === key
                    ? "border-[#0F2847] text-[#0F2847]"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
      </div>

        <TabContent />
    </InstitutionLayout>
  );
}

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { AnalyticsLayout } from "@/layouts";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { EMERALD } from "@/lib/tokens";
import {
  RefreshCw, Download, Save, Award, BookOpen, Users, BarChart2,
  TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp,
  AlertCircle, CheckCircle2, Clock, Globe, FileText,
  GraduationCap, DollarSign, Activity, Target, Calendar,
  Star, Zap, ArrowUpRight, Info, Camera, ChevronRight,
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
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
      {INTEL_NAV.map((s, i) => {
        const isCur = s.to === current;
        return (
          <React.Fragment key={s.to}>
            {i > 0 && <ChevronRight size={10} strokeWidth={1.5} style={{ color: "#CBD5E1", flexShrink: 0 }} />}
            <Link to={s.to} style={{ fontSize: 11, fontWeight: isCur ? 700 : 400, color: isCur ? "#0F2847" : "#94A3B8", padding: "3px 7px", background: isCur ? "rgba(15,40,71,0.07)" : "transparent", borderRadius: 3, textDecoration: "none", whiteSpace: "nowrap" }}>
              {s.label}
            </Link>
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(val, fallback = "—") {
  if (val == null || val === "") return fallback;
  return val;
}

function fmtNum(val) {
  if (val == null) return "—";
  return Number(val).toLocaleString();
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function pct(val, max) {
  if (!max) return 0;
  return Math.min(100, Math.round((val / max) * 100));
}

// ── SIS ring color ────────────────────────────────────────────────────────────

function sisColor(score) {
  if (score >= 7500) return "#D97706"; // gold
  if (score >= 5000) return "#7C3AED"; // purple
  if (score >= 2500) return "#0891B2"; // blue
  return "#94A3B8";                    // grey
}

function sisLabel(score) {
  if (score >= 7500) return "Distinguished";
  if (score >= 5000) return "Senior Scholar";
  if (score >= 2500) return "Established";
  return "Emerging";
}

// ── Component color palette for 8 SIS components ─────────────────────────────

const COMPONENT_COLORS = [
  "#0F2847", "#0891B2", "#7C3AED", "#059669",
  "#D97706", "#DC2626", "#DB2777", "#64748B",
];

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton({ h = "h-4", w = "w-full", className = "" }) {
  return <div className={`${h} ${w} bg-slate-200 animate-pulse rounded-sm ${className}`} />;
}

function SkeletonCard({ rows = 3 }) {
  return (
    <div className="border border-slate-200 bg-white p-5 animate-pulse space-y-3">
      <Skeleton h="h-3" w="w-1/3" />
      <Skeleton h="h-8" w="w-1/2" />
      {Array.from({ length: rows - 2 }).map((_, i) => (
        <Skeleton key={i} h="h-3" />
      ))}
    </div>
  );
}

// ── Error card ────────────────────────────────────────────────────────────────

function ErrorCard({ message, onRetry }) {
  return (
    <div className="border border-red-200 bg-red-50 p-6 text-center">
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

function EmptyState({ icon: Icon = AlertCircle, message, sub }) {
  return (
    <div className="border border-dashed border-slate-300 bg-slate-50 p-10 text-center">
      <Icon size={28} strokeWidth={1.5} className="text-slate-300 mx-auto mb-3" />
      <p className="text-slate-600 text-sm font-medium">{message}</p>
      {sub && <p className="text-slate-400 text-xs mt-1 max-w-sm mx-auto">{sub}</p>}
    </div>
  );
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ message, type = "success", onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);

  const colors =
    type === "success"
      ? "bg-emerald-50 border-emerald-200 text-emerald-800"
      : "bg-red-50 border-red-200 text-red-800";

  return (
    <div className={`fixed bottom-6 right-6 z-50 border px-4 py-3 text-sm shadow-lg max-w-xs ${colors}`}>
      <div className="flex items-center gap-2">
        {type === "success" ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
        <span>{message}</span>
        <button onClick={onClose} className="ml-auto opacity-60 hover:opacity-100 text-lg leading-none">&times;</button>
      </div>
    </div>
  );
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, highlight, loading, ringColor, ringPct, icon: Icon }) {
  if (loading) return <SkeletonCard rows={3} />;

  return (
    <div className={`border bg-white p-5 ${highlight ? "border-[#0F2847]" : "border-slate-200"}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">{label}</div>
        {Icon && <Icon size={14} strokeWidth={1.5} className="text-slate-400" />}
      </div>
      {ringColor ? (
        <div className="flex items-center gap-4">
          <SisRing score={typeof value === "number" ? value : 0} size={56} stroke={5} />
          <div>
            <div className="font-serif text-3xl text-slate-900">{fmtNum(value)}</div>
            <div className="text-xs text-slate-500">{sub}</div>
          </div>
        </div>
      ) : (
        <>
          <div className={`font-serif text-4xl mt-1 tracking-tight ${highlight ? "text-[#0F2847]" : "text-slate-900"}`}>
            {value ?? "—"}
          </div>
          {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
        </>
      )}
    </div>
  );
}

// ── SIS Ring (SVG) ────────────────────────────────────────────────────────────

function SisRing({ score = 0, size = 80, stroke = 6 }) {
  const max = 10000;
  const r = (size - stroke) / 2;
  const ci = 2 * Math.PI * r;
  const off = ci - (Math.min(max, score) / max) * ci;
  const color = sisColor(score);

  return (
    <svg width={size} height={size} className="-rotate-90" style={{ flexShrink: 0 }}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
      <circle
        cx={size / 2} cy={size / 2} r={r} fill="none"
        stroke={color} strokeWidth={stroke}
        strokeDasharray={ci} strokeDashoffset={off}
        strokeLinecap="round"
        className="transition-all duration-700"
      />
    </svg>
  );
}

// ── Progress bar ──────────────────────────────────────────────────────────────

function ProgressBar({ value = 0, max = 100, color = "#0F2847", height = "h-2", label, showPct = false }) {
  const p = pct(value, max);
  return (
    <div>
      {label && (
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-slate-700">{label}</span>
          <span className="text-xs text-slate-500">{showPct ? `${p}%` : `${fmtNum(value)} / ${fmtNum(max)}`}</span>
        </div>
      )}
      <div className={`${height} bg-slate-100 w-full overflow-hidden`}>
        <div
          className="h-full transition-all duration-700"
          style={{ width: `${p}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

// ── Status Badge ──────────────────────────────────────────────────────────────

function StatusBadge({ label, color = "slate" }) {
  const palette = {
    green:  "bg-emerald-50 text-emerald-700 border-emerald-200",
    blue:   "bg-blue-50 text-blue-700 border-blue-200",
    amber:  "bg-amber-50 text-amber-700 border-amber-200",
    red:    "bg-red-50 text-red-700 border-red-200",
    slate:  "bg-slate-100 text-slate-600 border-slate-200",
    purple: "bg-purple-50 text-purple-700 border-purple-200",
  };
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 text-xs border ${palette[color] || palette.slate}`}>
      {label}
    </span>
  );
}

// ── Div Bar Chart (horizontal) ────────────────────────────────────────────────

function HBarChart({ items = [], valueKey = "value", labelKey = "label", color = "#0F2847", maxVal }) {
  const max = maxVal || Math.max(...items.map((i) => i[valueKey] || 0), 1);
  return (
    <div className="space-y-2">
      {items.map((item, idx) => (
        <div key={idx}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-slate-700 truncate max-w-[60%]">{item[labelKey]}</span>
            <span className="text-xs text-slate-500">{fmtNum(item[valueKey])}</span>
          </div>
          <div className="h-2 bg-slate-100 w-full overflow-hidden">
            <div
              className="h-full transition-all duration-700"
              style={{ width: `${pct(item[valueKey] || 0, max)}%`, backgroundColor: color }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Vertical Bar Chart (div-based) ────────────────────────────────────────────

function VBarChart({ items = [], valueKey = "value", labelKey = "label", color = "#0891B2", height = 120 }) {
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

// ── Expandable SIS Component Card ─────────────────────────────────────────────

function SisComponentCard({ name, score, max_score, details = [], color, idx }) {
  const [open, setOpen] = useState(false);
  const p = pct(score || 0, max_score || 1000);

  return (
    <div className="border border-slate-200 bg-white">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full p-4 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-900">
            {idx + 1}. {name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          </span>
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold" style={{ color }}>
              {fmtNum(score)} / {fmtNum(max_score)}
            </span>
            {open ? <ChevronUp size={14} className="text-slate-400" /> : <ChevronDown size={14} className="text-slate-400" />}
          </div>
        </div>
        <div className="h-2 bg-slate-100 w-full overflow-hidden">
          <div className="h-full transition-all duration-700" style={{ width: `${p}%`, backgroundColor: color }} />
        </div>
        <div className="text-[10px] text-slate-400 mt-1">{p}% of maximum</div>
      </button>
      {open && details.length > 0 && (
        <div className="border-t border-slate-100 px-4 pb-4 pt-3 bg-slate-50">
          <div className="text-xs font-medium text-slate-600 mb-2">Score breakdown:</div>
          <ul className="space-y-1">
            {details.map((d, i) => (
              <li key={i} className="text-xs text-slate-600 flex items-start gap-1.5">
                <span className="text-slate-400 flex-shrink-0 mt-0.5">•</span>
                {d}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Timeline Event ────────────────────────────────────────────────────────────

const EVENT_CONFIG = {
  manuscript_published:  { icon: BookOpen,      color: "#059669", label: "Manuscript Published" },
  manuscript_submitted:  { icon: FileText,       color: "#0891B2", label: "Manuscript Submitted" },
  collaboration_started: { icon: Users,          color: "#7C3AED", label: "Collaboration Started" },
  badge_earned:          { icon: Award,          color: "#D97706", label: "Badge Earned" },
  grant_applied:         { icon: DollarSign,     color: "#DC2626", label: "Grant Applied" },
  grant_funded:          { icon: CheckCircle2,   color: "#059669", label: "Grant Funded" },
  course_published:      { icon: GraduationCap,  color: "#0891B2", label: "Course Published" },
  project_created:       { icon: Target,         color: "#7C3AED", label: "Project Created" },
  default:               { icon: Activity,       color: "#64748B", label: "Activity" },
};

function TimelineEvent({ event }) {
  const cfg = EVENT_CONFIG[event.event_type] || EVENT_CONFIG.default;
  const Icon = cfg.icon;

  return (
    <div className="flex gap-3 py-3">
      <div className="flex flex-col items-center">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: `${cfg.color}18` }}
        >
          <Icon size={14} strokeWidth={1.5} style={{ color: cfg.color }} />
        </div>
        <div className="w-px bg-slate-200 flex-1 mt-2" />
      </div>
      <div className="flex-1 pb-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-slate-900">{cfg.label}</span>
          <span className="text-xs text-slate-400 flex-shrink-0">{formatDate(event.date)}</span>
        </div>
        {event.description && (
          <p className="text-xs text-slate-600 mt-0.5 line-clamp-2">{event.description}</p>
        )}
        {event.title && event.title !== event.description && (
          <p className="text-xs text-slate-500 mt-0.5 italic">"{event.title}"</p>
        )}
      </div>
    </div>
  );
}

// ── Forecast Card ─────────────────────────────────────────────────────────────

function ForecastCard({ metric }) {
  const { name, current, forecast, confidence_low, confidence_high, trend, history = [] } = metric;
  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const trendColor = trend === "up" ? "text-emerald-600" : trend === "down" ? "text-red-500" : "text-slate-500";
  const trendLabel = trend === "up" ? "Increasing" : trend === "down" ? "Declining" : "Stable";
  const delta = forecast != null && current != null ? forecast - current : null;

  return (
    <div className="border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm font-semibold text-slate-900">{name}</div>
        <div className={`flex items-center gap-1 text-xs font-medium ${trendColor}`}>
          <TrendIcon size={13} strokeWidth={2} />
          {trendLabel}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Current</div>
          <div className="font-serif text-2xl text-slate-900">{fmtNum(current)}</div>
        </div>
        <div>
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">6-Month Forecast</div>
          <div className="font-serif text-2xl text-slate-900">{fmtNum(forecast)}</div>
          {delta != null && (
            <div className={`text-xs mt-0.5 ${delta >= 0 ? "text-emerald-600" : "text-red-500"}`}>
              {delta >= 0 ? "+" : ""}{fmtNum(delta)}
            </div>
          )}
        </div>
      </div>
      {(confidence_low != null || confidence_high != null) && (
        <div className="text-xs text-slate-500 mb-3">
          Range: {fmtNum(confidence_low)} – {fmtNum(confidence_high)}
        </div>
      )}
      {history.length > 1 && (
        <VBarChart items={history.map((h) => ({ label: h.label || "", value: h.value || 0 }))} height={60} />
      )}
    </div>
  );
}

// ── TABS CONFIG ───────────────────────────────────────────────────────────────

const TABS = [
  { id: "overview",        label: "Overview",       icon: BarChart2 },
  { id: "publications",    label: "Publications",   icon: BookOpen },
  { id: "citations",       label: "Citations",      icon: TrendingUp },
  { id: "impact_score",    label: "Impact Score",   icon: Award },
  { id: "collaborations",  label: "Collaborations", icon: Users },
  { id: "grants",          label: "Grants",         icon: DollarSign },
  { id: "teaching",        label: "Teaching",       icon: GraduationCap },
  { id: "benchmarks",      label: "Benchmarks",     icon: Target },
  { id: "timeline",        label: "Timeline",       icon: Calendar },
  { id: "forecasts",       label: "Forecasts",      icon: Zap },
];

// ─────────────────────────────────────────────────────────────────────────────
// ── MAIN PAGE ─────────────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────

export default function ImpactDashboard() {
  const { user } = useAuth();

  // Core state
  const [activeTab, setActiveTab] = useState("overview");
  const [mainData, setMainData]   = useState(null);
  const [mainLoading, setMainLoading] = useState(true);
  const [mainError, setMainError]   = useState(null);

  // Tab-specific data (fetched lazily on first activation)
  const [tabData, setTabData]       = useState({});
  const [tabLoading, setTabLoading] = useState({});
  const [tabError, setTabError]     = useState({});
  const fetched = useRef(new Set());

  // UI state
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState(null);
  const [savingSnapshot, setSavingSnapshot] = useState(false);
  const [snapshotName, setSnapshotName] = useState("");
  const [showSnapshotInput, setShowSnapshotInput] = useState(false);

  // ── Fetch main data ──────────────────────────────────────────────────────

  const fetchMain = useCallback(async (forceRefresh = false) => {
    setMainLoading(true);
    setMainError(null);
    try {
      const res = await api.get("/impact/me", { params: forceRefresh ? { force_refresh: true } : {} });
      setMainData(res.data);
    } catch (e) {
      setMainError(e?.response?.data?.detail || "Failed to load impact data.");
    } finally {
      setMainLoading(false);
    }
  }, []);

  useEffect(() => { fetchMain(); }, [fetchMain]);

  // ── Fetch tab-specific detail data ───────────────────────────────────────

  const fetchTab = useCallback(async (tabId) => {
    if (fetched.current.has(tabId)) return;
    fetched.current.add(tabId);

    const endpointMap = {
      impact_score:   "/impact/score",
      publications:   "/impact/publication-metrics",
      citations:      "/impact/history",
      benchmarks:     "/impact/benchmarks",
      timeline:       "/impact/timeline",
      forecasts:      "/impact/forecasts",
    };

    const endpoint = endpointMap[tabId];
    if (!endpoint) return;

    setTabLoading((prev) => ({ ...prev, [tabId]: true }));
    setTabError((prev) => ({ ...prev, [tabId]: null }));
    try {
      const res = await api.get(endpoint);
      setTabData((prev) => ({ ...prev, [tabId]: res.data }));
    } catch (e) {
      fetched.current.delete(tabId); // allow retry
      setTabError((prev) => ({
        ...prev,
        [tabId]: e?.response?.data?.detail || "Failed to load.",
      }));
    } finally {
      setTabLoading((prev) => ({ ...prev, [tabId]: false }));
    }
  }, []);

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    fetchTab(tabId);
  };

  useEffect(() => {
    // Trigger tab-specific fetch on initial load for the default tab
    fetchTab("overview");
  }, [fetchTab]);

  // ── Actions ───────────────────────────────────────────────────────────────

  const handleRefresh = async () => {
    setRefreshing(true);
    fetched.current.clear();
    await fetchMain(true);
    await fetchTab(activeTab);
    setRefreshing(false);
    showToast("Data refreshed successfully.", "success");
  };

  const handleExport = async (format) => {
    try {
      const res = await api.get(`/impact/export/${format}`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `impact-export.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast(`${format.toUpperCase()} exported successfully.`, "success");
    } catch {
      showToast("Export failed. Please try again.", "error");
    }
  };

  const handleSaveSnapshot = async () => {
    if (!snapshotName.trim()) {
      showToast("Please enter a snapshot name.", "error");
      return;
    }
    setSavingSnapshot(true);
    try {
      await api.post("/impact/snapshot", { name: snapshotName.trim() });
      setSnapshotName("");
      setShowSnapshotInput(false);
      showToast("Snapshot saved successfully.", "success");
    } catch {
      showToast("Failed to save snapshot.", "error");
    } finally {
      setSavingSnapshot(false);
    }
  };

  const showToast = (message, type) => {
    setToast({ message, type, id: Date.now() });
  };

  // ── Derived data ──────────────────────────────────────────────────────────

  const d = mainData || {};
  const sisScore = d.sis_score || {};
  const pubMetrics = d.publication_metrics || {};
  const collab = d.collaboration || {};
  const teaching = d.teaching || {};
  const grants = d.grants || {};
  const publications = d.publications || [];
  const reputation = d.research_reputation || {};

  const scoreData = tabData["impact_score"] || {};
  const historyData = tabData["citations"] || {};
  const benchmarkData = tabData["benchmarks"] || {};
  const timelineData = tabData["timeline"] || {};
  const forecastData = tabData["forecasts"] || {};

  const components = scoreData.components || sisScore.components || [];
  const historyList = Array.isArray(historyData.snapshots) ? historyData.snapshots :
                      Array.isArray(historyData) ? historyData : [];
  const benchmarks = Array.isArray(benchmarkData.benchmarks) ? benchmarkData.benchmarks :
                     Array.isArray(benchmarkData) ? benchmarkData : [];
  const timelineEvents = Array.isArray(timelineData.events) ? timelineData.events :
                         Array.isArray(timelineData) ? timelineData : [];
  const forecasts = Array.isArray(forecastData.forecasts) ? forecastData.forecasts :
                    Array.isArray(forecastData) ? forecastData : [];

  // Group timeline events by year
  const timelineByYear = timelineEvents.reduce((acc, ev) => {
    const year = ev.date ? new Date(ev.date).getFullYear() : "Unknown";
    if (!acc[year]) acc[year] = [];
    acc[year].push(ev);
    return acc;
  }, {});
  const timelineYears = Object.keys(timelineByYear).sort((a, b) => b - a);

  // Citation monthly bars from history
  const citationMonthly = historyList.slice(-12).map((s) => ({
    label: s.month || s.date?.slice(0, 7) || "",
    value: s.citations || s.total_citations || 0,
  }));

  // Publication type distribution
  const pubTypes = publications.reduce((acc, p) => {
    const t = p.type || p.pub_type || "Other";
    acc[t] = (acc[t] || 0) + 1;
    return acc;
  }, {});
  const pubTypeItems = Object.entries(pubTypes).map(([label, value]) => ({ label, value }));

  // ── Render ────────────────────────────────────────────────────────────────

  const tabBar = (
    <div className="flex items-end gap-0 overflow-x-auto">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const active = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
              active
                ? "border-[#0F2847] text-[#0F2847]"
                : "border-transparent text-slate-600 hover:text-[#0F2847] hover:border-slate-300"
            }`}
          >
            <Icon size={12} strokeWidth={1.5} />
            {tab.label}
          </button>
        );
      })}
    </div>
  );

  return (
    <AnalyticsLayout
      title="Impact Dashboard"
      subtitle="Synaptiq Impact Score, publications, citations, benchmarks & forecasts"
      nav={<><IntelNav current="/impact-dashboard" />{tabBar}</>}
      actions={
        <>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 border border-slate-300 bg-white px-3 py-2 text-xs text-slate-700 hover:border-[#0F2847] hover:text-[#0F2847] disabled:opacity-40 transition-colors"
          >
            <RefreshCw size={12} strokeWidth={1.5} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
          <button
            onClick={() => handleExport("csv")}
            className="inline-flex items-center gap-1.5 border border-slate-300 bg-white px-3 py-2 text-xs text-slate-700 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
          >
            <Download size={12} strokeWidth={1.5} />
            Export CSV
          </button>
          <button
            onClick={() => handleExport("json")}
            className="inline-flex items-center gap-1.5 border border-slate-300 bg-white px-3 py-2 text-xs text-slate-700 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
          >
            <Download size={12} strokeWidth={1.5} />
            Export JSON
          </button>
          {!showSnapshotInput ? (
            <button
              onClick={() => setShowSnapshotInput(true)}
              className="inline-flex items-center gap-1.5 bg-[#0F2847] text-white px-3 py-2 text-xs hover:opacity-90 transition-opacity"
            >
              <Camera size={12} strokeWidth={1.5} />
              Save Snapshot
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={snapshotName}
                onChange={(e) => setSnapshotName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSaveSnapshot()}
                placeholder="Snapshot name…"
                className="border border-slate-300 px-2 py-1.5 text-xs focus:outline-none focus:border-[#0F2847] w-36"
                autoFocus
              />
              <button
                onClick={handleSaveSnapshot}
                disabled={savingSnapshot}
                className="bg-[#0F2847] text-white px-3 py-1.5 text-xs hover:opacity-90 disabled:opacity-50"
              >
                {savingSnapshot ? "Saving…" : "Save"}
              </button>
              <button
                onClick={() => { setShowSnapshotInput(false); setSnapshotName(""); }}
                className="text-slate-400 hover:text-slate-600 text-xs px-1"
              >
                &times;
              </button>
            </div>
          )}
        </>
      }
    >

        {mainError && activeTab === "overview" && (
          <ErrorCard message={mainError} onRetry={() => fetchMain()} />
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 1: OVERVIEW
        ══════════════════════════════════════════════════════════════ */}
        {activeTab === "overview" && (
          <div className="space-y-8">

            {/* KPI Cards */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {/* SIS Score */}
              <div className={`border bg-white p-5 lg:col-span-1 ${!mainLoading && sisScore.total >= 7500 ? "border-amber-300" : "border-[#0F2847]"}`}>
                <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-2">Synaptiq Impact Score</div>
                {mainLoading ? (
                  <Skeleton h="h-16" />
                ) : (
                  <div className="flex items-center gap-3">
                    <div className="relative flex-shrink-0">
                      <SisRing score={sisScore.total || 0} size={64} stroke={5} />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="font-serif text-lg" style={{ color: sisColor(sisScore.total || 0) }}>
                          {Math.round((sisScore.total || 0) / 100)}
                        </span>
                      </div>
                    </div>
                    <div>
                      <div className="font-serif text-2xl text-slate-900">{fmtNum(sisScore.total)}</div>
                      <div className="text-[10px] text-slate-500">/ 10,000</div>
                      <StatusBadge label={sisLabel(sisScore.total || 0)} color="blue" />
                    </div>
                  </div>
                )}
              </div>

              <KpiCard label="H-Index" value={mainLoading ? null : fmt(pubMetrics.h_index)} icon={Award}
                sub="Hirsch index" loading={mainLoading} />
              <KpiCard label="i10-Index" value={mainLoading ? null : fmt(pubMetrics.i10_index)} icon={Star}
                sub="Papers with ≥10 citations" loading={mainLoading} />
              <KpiCard label="Total Publications" value={mainLoading ? null : fmtNum(pubMetrics.total || publications.length)} icon={BookOpen}
                sub={pubMetrics.published ? `${pubMetrics.published} published` : undefined}
                loading={mainLoading} />
              <KpiCard label="Total Citations" value={mainLoading ? null : fmtNum(pubMetrics.total_citations)} icon={ArrowUpRight}
                highlight loading={mainLoading}
                sub={pubMetrics.citations_last_year ? `+${pubMetrics.citations_last_year} last year` : undefined} />
            </div>

            {/* Impact Score Composition */}
            {!mainLoading && components.length > 0 && (
              <div className="border border-slate-200 bg-white p-6">
                <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-4">Impact Score Composition</div>
                <div className="relative h-6 bg-slate-100 w-full overflow-hidden flex">
                  {components.map((comp, idx) => {
                    const total = components.reduce((s, c) => s + (c.score || 0), 0) || 1;
                    const w = pct(comp.score || 0, total);
                    return (
                      <div
                        key={idx}
                        className="h-full transition-all duration-700 relative group"
                        style={{ width: `${w}%`, backgroundColor: COMPONENT_COLORS[idx % COMPONENT_COLORS.length], minWidth: w > 0 ? "2px" : 0 }}
                        title={`${comp.name}: ${comp.score}`}
                      />
                    );
                  })}
                </div>
                <div className="flex flex-wrap gap-3 mt-3">
                  {components.map((comp, idx) => (
                    <div key={idx} className="flex items-center gap-1.5 text-xs text-slate-600">
                      <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: COMPONENT_COLORS[idx % COMPONENT_COLORS.length] }} />
                      <span>{comp.name?.replace(/_/g, " ")?.replace(/\b\w/g, (c) => c.toUpperCase())}: {fmtNum(comp.score)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 3-column summary cards */}
            <div className="grid lg:grid-cols-3 gap-5">
              {/* Research Output */}
              <div className="border border-slate-200 bg-white p-5">
                <div className="flex items-center gap-2 mb-4">
                  <BookOpen size={14} strokeWidth={1.5} className="text-slate-500" />
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Research Output</div>
                </div>
                {mainLoading ? (
                  <div className="space-y-2"><Skeleton /><Skeleton /><Skeleton /></div>
                ) : (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between"><span className="text-slate-600">Published</span><span className="font-medium">{fmtNum(pubMetrics.published)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-600">Submitted</span><span className="font-medium">{fmtNum(pubMetrics.submitted)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-600">Drafted</span><span className="font-medium">{fmtNum(pubMetrics.drafted)}</span></div>
                    <div className="flex justify-between border-t border-slate-100 pt-2 mt-2"><span className="text-slate-700 font-medium">Total</span><span className="font-semibold">{fmtNum(pubMetrics.total || publications.length)}</span></div>
                  </div>
                )}
              </div>

              {/* Collaboration */}
              <div className="border border-slate-200 bg-white p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Users size={14} strokeWidth={1.5} className="text-slate-500" />
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Collaboration</div>
                </div>
                {mainLoading ? (
                  <div className="space-y-2"><Skeleton /><Skeleton /><Skeleton /></div>
                ) : (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between"><span className="text-slate-600">Active Collaborations</span><span className="font-medium">{fmtNum(collab.active)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-600">Projects</span><span className="font-medium">{fmtNum(collab.projects)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-600">International</span><span className="font-medium">{fmtNum(collab.international)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-600">Cross-institutional</span><span className="font-medium">{fmtNum(collab.cross_institutional)}</span></div>
                  </div>
                )}
              </div>

              {/* Platform Reputation */}
              <div className="border border-slate-200 bg-white p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Star size={14} strokeWidth={1.5} className="text-slate-500" />
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Platform Reputation</div>
                </div>
                {mainLoading ? (
                  <div className="space-y-2"><Skeleton /><Skeleton /><Skeleton /></div>
                ) : (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between"><span className="text-slate-600">Reputation Level</span><span className="font-medium">{fmt(reputation.level)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-600">Overall Score</span><span className="font-medium">{fmtNum(reputation.total_score)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-600">Badges Earned</span><span className="font-medium">{fmtNum(reputation.badge_count)}</span></div>
                    <div className="flex justify-between"><span className="text-slate-600">Rank</span><span className="font-medium">{fmt(reputation.rank)}</span></div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 2: PUBLICATIONS
        ══════════════════════════════════════════════════════════════ */}
        {activeTab === "publications" && (
          <div className="space-y-6">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Your Publications</div>

            {mainLoading ? (
              <div className="space-y-3">{Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} rows={3} />)}</div>
            ) : mainError ? (
              <ErrorCard message={mainError} onRetry={() => fetchMain()} />
            ) : publications.length === 0 ? (
              <EmptyState
                icon={BookOpen}
                message="No publications found"
                sub="Sync your ORCID to import publications and track your academic output."
              />
            ) : (
              <div className="border border-slate-200 bg-white overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50">
                        <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Title</th>
                        <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Status</th>
                        <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Year</th>
                        <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Type</th>
                        <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Citations</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {publications.map((pub, idx) => {
                        const status = pub.status || pub.pub_status || "unknown";
                        const statusColor = status === "published" ? "green" : status === "submitted" ? "blue" : "slate";
                        return (
                          <tr key={pub.id || idx} className="hover:bg-slate-50 transition-colors">
                            <td className="px-4 py-3 max-w-xs">
                              <p className="font-medium text-slate-900 line-clamp-2">{fmt(pub.title)}</p>
                              {pub.venue && <p className="text-xs text-slate-400 mt-0.5">{pub.venue}</p>}
                            </td>
                            <td className="px-4 py-3">
                              <StatusBadge label={status} color={statusColor} />
                            </td>
                            <td className="px-4 py-3 text-slate-600">{fmt(pub.year)}</td>
                            <td className="px-4 py-3 text-slate-600 capitalize">{fmt(pub.type || pub.pub_type)}</td>
                            <td className="px-4 py-3 font-medium text-slate-900">{fmtNum(pub.citations)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Publication type distribution */}
            {pubTypeItems.length > 0 && (
              <div className="border border-slate-200 bg-white p-5">
                <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-4">Publication Type Distribution</div>
                <HBarChart items={pubTypeItems} />
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 3: CITATIONS
        ══════════════════════════════════════════════════════════════ */}
        {activeTab === "citations" && (
          <div className="space-y-6">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Citation Analytics</div>

            {tabLoading["citations"] ? (
              <div className="space-y-4">
                <SkeletonCard rows={5} />
                <SkeletonCard rows={4} />
              </div>
            ) : tabError["citations"] ? (
              <ErrorCard message={tabError["citations"]} onRetry={() => { fetched.current.delete("citations"); fetchTab("citations"); }} />
            ) : citationMonthly.length === 0 ? (
              <EmptyState
                icon={TrendingUp}
                message="No citation history available"
                sub="Citation data appears here once your publications are synced and citations begin accumulating."
              />
            ) : (
              <>
                {/* Monthly bar chart */}
                <div className="border border-slate-200 bg-white p-5">
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-4">
                    Citations Over Time (Last 12 Months)
                  </div>
                  <VBarChart items={citationMonthly} height={160} color="#0891B2" />
                </div>

                {/* Key metrics */}
                <div className="grid sm:grid-cols-3 gap-4">
                  {[
                    {
                      label: "Avg Citations / Publication",
                      value: publications.length
                        ? Math.round((pubMetrics.total_citations || 0) / publications.length * 10) / 10
                        : "—",
                    },
                    {
                      label: "Citations Last 12 Months",
                      value: fmtNum(pubMetrics.citations_last_year),
                    },
                    {
                      label: "Citation Growth Rate",
                      value: historyList.length >= 2
                        ? (() => {
                            const latest = historyList[historyList.length - 1];
                            const prev = historyList[historyList.length - 2];
                            const latestV = latest?.citations || latest?.total_citations || 0;
                            const prevV = prev?.citations || prev?.total_citations || 1;
                            return `${latestV > prevV ? "+" : ""}${Math.round(((latestV - prevV) / prevV) * 100)}%`;
                          })()
                        : "—",
                    },
                  ].map(({ label, value }) => (
                    <div key={label} className="border border-slate-200 bg-white p-5">
                      <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">{label}</div>
                      <div className="font-serif text-3xl text-slate-900">{value}</div>
                    </div>
                  ))}
                </div>

                {/* Citation distribution by publication */}
                {publications.length > 0 && (
                  <div className="border border-slate-200 bg-white p-5">
                    <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-4">
                      Citations by Publication
                    </div>
                    <HBarChart
                      items={publications
                        .filter((p) => p.citations > 0)
                        .sort((a, b) => (b.citations || 0) - (a.citations || 0))
                        .slice(0, 10)
                        .map((p) => ({ label: p.title?.slice(0, 50) + (p.title?.length > 50 ? "…" : "") || "Untitled", value: p.citations || 0 }))}
                    />
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 4: IMPACT SCORE
        ══════════════════════════════════════════════════════════════ */}
        {activeTab === "impact_score" && (
          <div className="space-y-6">

            {/* Total score header */}
            <div className="border border-[#0F2847] bg-white p-6">
              <div className="flex items-center gap-6">
                <div className="relative flex-shrink-0">
                  <SisRing score={sisScore.total || 0} size={100} stroke={8} />
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="font-serif text-2xl text-slate-900">{fmtNum(sisScore.total)}</span>
                    <span className="text-[9px] text-slate-400">/ 10,000</span>
                  </div>
                </div>
                <div>
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Total Synaptiq Impact Score</div>
                  <div className="font-serif text-4xl text-slate-900 mt-1">{fmtNum(sisScore.total)}</div>
                  <StatusBadge label={sisLabel(sisScore.total || 0)} color="blue" />
                  {sisScore.label && <div className="text-xs text-slate-500 mt-1">{sisScore.label}</div>}
                </div>
              </div>
            </div>

            {tabLoading["impact_score"] ? (
              <div className="space-y-3">{Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}</div>
            ) : tabError["impact_score"] ? (
              <ErrorCard
                message={tabError["impact_score"]}
                onRetry={() => { fetched.current.delete("impact_score"); fetchTab("impact_score"); }}
              />
            ) : components.length === 0 ? (
              <EmptyState
                icon={Award}
                message="No score breakdown available"
                sub="Your impact score components will appear here once data is available."
              />
            ) : (
              <div className="space-y-3">
                <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Score Components</div>
                {components.map((comp, idx) => (
                  <SisComponentCard
                    key={comp.name || idx}
                    name={comp.name || `Component ${idx + 1}`}
                    score={comp.score}
                    max_score={comp.max_score || 1000}
                    details={comp.details || comp.breakdown || []}
                    color={COMPONENT_COLORS[idx % COMPONENT_COLORS.length]}
                    idx={idx}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 5: COLLABORATIONS
        ══════════════════════════════════════════════════════════════ */}
        {activeTab === "collaborations" && (
          <div className="space-y-6">
            <div className="grid sm:grid-cols-4 gap-4">
              {[
                { label: "Total Collaborations", value: fmtNum(collab.total || collab.active) },
                { label: "Active Projects", value: fmtNum(collab.projects) },
                { label: "International", value: fmtNum(collab.international) },
                { label: "Cross-institutional", value: fmtNum(collab.cross_institutional) },
              ].map(({ label, value }) => (
                <div key={label} className="border border-slate-200 bg-white p-5">
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">{label}</div>
                  <div className="font-serif text-3xl text-slate-900">{mainLoading ? "—" : value}</div>
                </div>
              ))}
            </div>

            {mainLoading ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
              </div>
            ) : (collab.list || []).length === 0 ? (
              <EmptyState
                icon={Users}
                message="No collaborations yet"
                sub="Start collaborating with other researchers to track your collaboration network."
              />
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {(collab.list || []).map((c, idx) => (
                  <div key={c.id || idx} className="border border-slate-200 bg-white p-5">
                    <div className="font-medium text-slate-900 mb-1 line-clamp-1">{fmt(c.title)}</div>
                    <div className="flex items-center gap-2 flex-wrap mb-2">
                      {c.type && <StatusBadge label={c.type} color="blue" />}
                      {c.status && <StatusBadge label={c.status} color={c.status === "active" ? "green" : "slate"} />}
                    </div>
                    <div className="text-xs text-slate-500 space-y-0.5">
                      {c.member_count != null && <div>{c.member_count} members</div>}
                      {c.research_area && <div>{c.research_area}</div>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 6: GRANTS
        ══════════════════════════════════════════════════════════════ */}
        {activeTab === "grants" && (
          <div className="space-y-6">
            <div className="grid sm:grid-cols-3 gap-4">
              {[
                { label: "Applications Submitted", value: fmtNum(grants.submitted) },
                { label: "Funded", value: fmtNum(grants.funded) },
                { label: "Success Rate", value: grants.success_rate != null ? `${grants.success_rate}%` : "—" },
              ].map(({ label, value }) => (
                <div key={label} className="border border-slate-200 bg-white p-5">
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">{label}</div>
                  <div className="font-serif text-3xl text-slate-900">{mainLoading ? "—" : value}</div>
                </div>
              ))}
            </div>

            {mainLoading ? (
              <SkeletonCard rows={5} />
            ) : (grants.applications || []).length === 0 ? (
              <EmptyState
                icon={DollarSign}
                message="No grant applications yet"
                sub="Apply for grants to track your funding activity and success rate."
              />
            ) : (
              <div className="border border-slate-200 bg-white overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50">
                        <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Grant</th>
                        <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Status</th>
                        <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Amount</th>
                        <th className="text-left px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">Applied</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {(grants.applications || []).map((g, idx) => {
                        const status = g.status || "pending";
                        const sc = status === "funded" || status === "approved" ? "green" :
                                   status === "rejected" ? "red" : "amber";
                        return (
                          <tr key={g.id || idx} className="hover:bg-slate-50 transition-colors">
                            <td className="px-4 py-3">
                              <p className="font-medium text-slate-900 line-clamp-1">{fmt(g.title)}</p>
                              {g.funder && <p className="text-xs text-slate-400 mt-0.5">{g.funder}</p>}
                            </td>
                            <td className="px-4 py-3"><StatusBadge label={status} color={sc} /></td>
                            <td className="px-4 py-3 text-slate-600">{g.amount ? `€${fmtNum(g.amount)}` : "—"}</td>
                            <td className="px-4 py-3 text-slate-500">{formatDate(g.applied_at || g.created_at)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 7: TEACHING
        ══════════════════════════════════════════════════════════════ */}
        {activeTab === "teaching" && (
          <div className="space-y-6">
            <div className="grid sm:grid-cols-4 gap-4">
              {[
                { label: "Lessons Published", value: fmtNum(teaching.lessons_published) },
                { label: "Courses", value: fmtNum(teaching.courses) },
                { label: "Total Students", value: fmtNum(teaching.students) },
                { label: "Teaching Score", value: fmtNum(teaching.contribution_score) },
              ].map(({ label, value }) => (
                <div key={label} className="border border-slate-200 bg-white p-5">
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">{label}</div>
                  <div className="font-serif text-3xl text-slate-900">{mainLoading ? "—" : value}</div>
                </div>
              ))}
            </div>

            {mainLoading ? (
              <SkeletonCard rows={4} />
            ) : !teaching.lessons_published && !teaching.courses ? (
              <EmptyState
                icon={GraduationCap}
                message="No teaching content yet"
                sub="Publish teaching content to track your teaching impact and reach more students."
              />
            ) : (
              <div className="border border-slate-200 bg-white p-5">
                <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-4">Teaching Contribution</div>
                <div className="space-y-3">
                  <ProgressBar label="Lessons Published" value={teaching.lessons_published || 0} max={50} color="#7C3AED" />
                  <ProgressBar label="Courses" value={teaching.courses || 0} max={10} color="#0891B2" />
                  <ProgressBar label="Teaching Score" value={teaching.contribution_score || 0} max={1000} color="#059669" />
                </div>
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 8: BENCHMARKS
        ══════════════════════════════════════════════════════════════ */}
        {activeTab === "benchmarks" && (
          <div className="space-y-6">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Peer Comparison</div>

            {tabLoading["benchmarks"] ? (
              <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} rows={4} />)}</div>
            ) : tabError["benchmarks"] ? (
              <ErrorCard
                message={tabError["benchmarks"]}
                onRetry={() => { fetched.current.delete("benchmarks"); fetchTab("benchmarks"); }}
              />
            ) : benchmarks.length === 0 ? (
              <EmptyState
                icon={Target}
                message="No benchmark data available yet"
                sub="Peer comparison data will appear as more researchers join your field on the platform."
              />
            ) : (
              <div className="space-y-5">
                {benchmarks.map((bm, idx) => {
                  const myScore = bm.your_score || bm.user_score || sisScore.total || 0;
                  const groupAvg = bm.group_average || bm.avg_score || 0;
                  const groupSize = bm.group_size || bm.count || 0;
                  const percentile = bm.percentile || bm.your_percentile || null;
                  const rank = bm.rank || bm.your_rank || null;
                  const groupMax = Math.max(myScore, groupAvg, 1);

                  return (
                    <div key={idx} className="border border-slate-200 bg-white p-5">
                      <div className="flex items-start justify-between gap-4 mb-4">
                        <div>
                          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{bm.peer_group || bm.group_type}</div>
                          <div className="font-medium text-slate-900 mt-0.5">{bm.group_label || bm.description || ""}</div>
                          {groupSize > 0 && <div className="text-xs text-slate-500 mt-0.5">Group size: {fmtNum(groupSize)} researchers</div>}
                        </div>
                        {percentile != null && (
                          <div className="text-right flex-shrink-0">
                            <div className="font-serif text-2xl text-[#0F2847]">{percentile}<span className="text-sm">th</span></div>
                            <div className="text-xs text-slate-500">percentile</div>
                          </div>
                        )}
                      </div>

                      <div className="grid sm:grid-cols-2 gap-4 mb-4">
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Your SIS</div>
                          <div className="font-serif text-xl text-[#0F2847]">{fmtNum(myScore)}</div>
                          <ProgressBar value={myScore} max={groupMax * 1.2} color="#0F2847" height="h-1.5" />
                        </div>
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Group Average</div>
                          <div className="font-serif text-xl text-slate-700">{fmtNum(groupAvg)}</div>
                          <ProgressBar value={groupAvg} max={groupMax * 1.2} color="#94A3B8" height="h-1.5" />
                        </div>
                      </div>

                      {percentile != null && (
                        <div className="mb-3">
                          <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                            <span>Percentile</span>
                            {rank && groupSize ? <span>Rank #{rank} of {fmtNum(groupSize)}</span> : null}
                          </div>
                          <div className="h-2.5 bg-slate-100 w-full overflow-hidden">
                            <div
                              className="h-full transition-all duration-700"
                              style={{ width: `${percentile}%`, backgroundColor: percentile >= 75 ? "#059669" : percentile >= 50 ? "#0891B2" : percentile >= 25 ? "#D97706" : "#DC2626" }}
                            />
                          </div>
                          <div className="text-[10px] text-slate-400 mt-1">{percentile}th percentile</div>
                        </div>
                      )}

                      {/* Improvement opportunities */}
                      {(bm.opportunities || bm.suggestions || []).length > 0 && (
                        <div className="border-t border-slate-100 pt-3 mt-3">
                          <div className="text-xs font-medium text-slate-600 mb-2">Improvement Opportunities</div>
                          <ul className="space-y-1">
                            {(bm.opportunities || bm.suggestions || []).map((opp, i) => (
                              <li key={i} className="text-xs text-slate-600 flex items-start gap-1.5">
                                <span className="text-[#0F2847] flex-shrink-0 mt-0.5">•</span>
                                {opp}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 9: TIMELINE
        ══════════════════════════════════════════════════════════════ */}
        {activeTab === "timeline" && (
          <div className="space-y-4">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Academic Event Timeline</div>

            {tabLoading["timeline"] ? (
              <div className="space-y-3">{Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} rows={3} />)}</div>
            ) : tabError["timeline"] ? (
              <ErrorCard
                message={tabError["timeline"]}
                onRetry={() => { fetched.current.delete("timeline"); fetchTab("timeline"); }}
              />
            ) : timelineEvents.length === 0 ? (
              <EmptyState
                icon={Calendar}
                message="Your academic journey will appear here"
                sub="Complete activities on the platform — publish manuscripts, start collaborations, earn badges — to build your timeline."
              />
            ) : (
              <div className="border border-slate-200 bg-white p-5">
                {timelineYears.map((year) => (
                  <div key={year}>
                    <div className="text-xs font-bold text-slate-400 uppercase tracking-widest py-2 mb-1 border-b border-slate-100">
                      {year}
                    </div>
                    {timelineByYear[year].map((ev, idx) => (
                      <TimelineEvent key={ev.id || idx} event={ev} />
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 10: FORECASTS
        ══════════════════════════════════════════════════════════════ */}
        {activeTab === "forecasts" && (
          <div className="space-y-6">
            <div className="flex items-start gap-2 border border-amber-100 bg-amber-50 p-3 text-xs text-amber-800">
              <Info size={12} className="shrink-0 mt-0.5 text-amber-600" />
              <span>
                Forecasts are based on your historical activity patterns. Add more data points for improved accuracy.
              </span>
            </div>

            {tabLoading["forecasts"] ? (
              <div className="grid sm:grid-cols-3 gap-4">
                {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} rows={4} />)}
              </div>
            ) : tabError["forecasts"] ? (
              <ErrorCard
                message={tabError["forecasts"]}
                onRetry={() => { fetched.current.delete("forecasts"); fetchTab("forecasts"); }}
              />
            ) : forecasts.length === 0 ? (
              <EmptyState
                icon={Zap}
                message="Insufficient data for forecasts"
                sub="Continue using the platform to generate trend forecasts. At least 2 historical data points are needed."
              />
            ) : (
              <>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {forecasts.map((metric, idx) => (
                    <ForecastCard key={metric.name || idx} metric={metric} />
                  ))}
                </div>
                {forecastData.generated_at && (
                  <div className="text-xs text-slate-400 text-right">
                    Forecast generated: {formatDate(forecastData.generated_at)}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Research Intelligence Quick Links ── */}
        <section className="px-6 pb-8">
          <h2 className="overline mb-5">Continue in Research Intelligence</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {[
              { to: "/analytics",           label: "Analytics Overview"   },
              { to: "/citations",           label: "Citation Tracker"     },
              { to: "/citation-monitoring", label: "Citation Monitoring"  },
              { to: "/reputation",          label: "Reputation Score"     },
              { to: "/verification",        label: "Verification Center"  },
            ].map(({ to, label }) => (
              <Link key={to} to={to} className="border border-slate-200 bg-white p-4 hover:border-[#0F2847] transition-colors group block">
                <div className="text-xs font-medium text-slate-700 group-hover:text-[#0F2847] transition-colors flex items-center justify-between">
                  {label} <ChevronRight size={12} className="text-slate-300 group-hover:text-[#0F2847]" />
                </div>
              </Link>
            ))}
          </div>
        </section>

      {/* ── Toast ─────────────────────────────────────────────────────── */}
      {toast && (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </AnalyticsLayout>
  );
}

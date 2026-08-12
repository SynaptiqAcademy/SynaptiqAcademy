import React, { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { ResearchLayout } from "@/layouts";
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
import { toast } from "sonner";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { StatCard } from "@/components/ds/StatCard";
import { Input } from "@/components/ds/Input";
import { ErrorState } from "@/components/ds/ErrorState";
import { EmptyState as DsEmptyState } from "@/components/ds/EmptyState";
import { SkeletonCard as DsSkeletonCard } from "@/components/ds/LoadingState";
import { ProgressBar as DsProgressBar } from "@/components/ds/Progress";
import { BarChart as DsBarChart } from "@/components/ds/Chart";
import { NavTabs } from "@/components/ds/NavTabs";
import { DataTable } from "@/components/ds/DataTable";
import { Callout } from "@/components/ds/Alert";

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
  return <DsSkeletonCard rows={rows} />;
}

// ── Error card ────────────────────────────────────────────────────────────────

function ErrorCard({ message, onRetry }) {
  return (
    <Card padding="xl" className="text-center">
      <ErrorState message={message || "Failed to load data."} onRetry={onRetry} />
    </Card>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ icon: Icon = AlertCircle, message, sub }) {
  return (
    <DsEmptyState
      icon={<Icon />}
      title={message}
      description={sub}
      size="lg"
      dashed
    />
  );
}

// ── Toast ─────────────────────────────────────────────────────────────────────
// Toast notifications use sonner's `toast` directly (see showToast() below) —
// there is deliberately no local toast component; ds/ removed its own for the
// same reason (a second, unmounted toast system is pure dead code).

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, highlight, loading, ringColor, ringPct, icon: Icon }) {
  if (loading) return <SkeletonCard rows={3} />;

  if (ringColor) {
    return (
      <Card padding="lg" style={highlight ? { borderColor: "#0F2847" } : undefined}>
        <div className="flex items-center justify-between mb-2">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">{label}</div>
          {Icon && <Icon size={14} strokeWidth={1.5} className="text-slate-400" />}
        </div>
        <div className="flex items-center gap-4">
          <SisRing score={typeof value === "number" ? value : 0} size={56} stroke={5} />
          <div>
            <div className="font-serif text-3xl text-slate-900">{fmtNum(value)}</div>
            <div className="text-xs text-slate-500">{sub}</div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <StatCard
      label={label}
      value={value ?? "—"}
      sub={sub}
      highlight={highlight}
      icon={Icon ? <Icon size={14} strokeWidth={1.5} /> : undefined}
    />
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
  const variants = {
    green:  "success",
    blue:   "info",
    amber:  "warning",
    red:    "danger",
    slate:  "neutral",
    purple: "purple",
  };
  return (
    <Badge variant={variants[color] || "neutral"} size="sm">
      {label}
    </Badge>
  );
}

// ── Div Bar Chart (horizontal) ────────────────────────────────────────────────

function HBarChart({ items = [], valueKey = "value", labelKey = "label", color = "#0F2847", maxVal }) {
  const max = maxVal || Math.max(...items.map((i) => i[valueKey] || 0), 1);
  return (
    <div className="space-y-2">
      {items.map((item, idx) => (
        <DsProgressBar
          key={idx}
          label={item[labelKey]}
          value={item[valueKey] || 0}
          max={max}
          valueLabel={fmtNum(item[valueKey])}
          size="sm"
        />
      ))}
    </div>
  );
}

// ── Vertical Bar Chart (div-based) ────────────────────────────────────────────

function VBarChart({ items = [], valueKey = "value", labelKey = "label", color = "#0891B2", height = 120 }) {
  return (
    <DsBarChart
      data={items.map((i) => ({ label: i[labelKey], value: i[valueKey] || 0 }))}
      height={height}
      color={color}
      showLabels
    />
  );
}

// ── Expandable SIS Component Card ─────────────────────────────────────────────

function SisComponentCard({ name, score, max_score, details = [], color, idx }) {
  const [open, setOpen] = useState(false);
  const p = pct(score || 0, max_score || 1000);

  return (
    <Card padding="none">
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
        {/* ds ProgressBar has no per-instance color override (only auto colorByValue),
            but each SIS component needs its own distinct hue from COMPONENT_COLORS, so
            this stays hand-rolled. */}
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
    </Card>
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
    <Card padding="lg">
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
    </Card>
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
    if (type === "error") toast.error(message);
    else toast.success(message);
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
    <div className="overflow-x-auto">
      <NavTabs
        variant="underline"
        size="sm"
        active={activeTab}
        onChange={handleTabChange}
        tabs={TABS}
      />
    </div>
  );

  return (
    <ResearchLayout
      title="Impact Dashboard"
      subtitle="Synaptiq Impact Score, publications, citations, benchmarks & forecasts"
      nav={<><IntelNav current="/impact-dashboard" />{tabBar}</>}
      actions={
        <>
          <Button onClick={handleRefresh} disabled={refreshing} variant="outline" size="sm">
            <RefreshCw size={12} strokeWidth={1.5} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Refreshing…" : "Refresh"}
          </Button>
          <Button onClick={() => handleExport("csv")} variant="outline" size="sm">
            <Download size={12} strokeWidth={1.5} />
            Export CSV
          </Button>
          <Button onClick={() => handleExport("json")} variant="outline" size="sm">
            <Download size={12} strokeWidth={1.5} />
            Export JSON
          </Button>
          {!showSnapshotInput ? (
            <Button onClick={() => setShowSnapshotInput(true)} variant="primary" size="sm">
              <Camera size={12} strokeWidth={1.5} />
              Save Snapshot
            </Button>
          ) : (
            <div className="flex items-center gap-2">
              <Input
                type="text"
                value={snapshotName}
                onChange={(e) => setSnapshotName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSaveSnapshot()}
                placeholder="Snapshot name…"
                size="sm"
                wrapperClassName="w-36"
                autoFocus
              />
              <Button onClick={handleSaveSnapshot} disabled={savingSnapshot} loading={savingSnapshot} variant="primary" size="sm">
                {savingSnapshot ? "Saving…" : "Save"}
              </Button>
              <Button
                onClick={() => { setShowSnapshotInput(false); setSnapshotName(""); }}
                variant="ghost"
                size="sm"
              >
                &times;
              </Button>
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
              <Card padding="lg" className="lg:col-span-1" style={{ borderColor: !mainLoading && sisScore.total >= 7500 ? "#FCD34D" : "#0F2847" }}>
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
              </Card>

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
              <Card padding="xl">
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
              </Card>
            )}

            {/* 3-column summary cards */}
            <div className="grid lg:grid-cols-3 gap-5">
              {/* Research Output */}
              <Card padding="lg">
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
              </Card>

              {/* Collaboration */}
              <Card padding="lg">
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
              </Card>

              {/* Platform Reputation */}
              <Card padding="lg">
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
              </Card>
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
              <DataTable
                columns={[
                  { key: "title",     label: "Title" },
                  { key: "status",    label: "Status" },
                  { key: "year",      label: "Year" },
                  { key: "type",      label: "Type" },
                  { key: "citations", label: "Citations" },
                ]}
                rows={publications.map((pub, idx) => {
                  const status = pub.status || pub.pub_status || "unknown";
                  const statusColor = status === "published" ? "green" : status === "submitted" ? "blue" : "slate";
                  return {
                    id: pub.id || idx,
                    title: (
                      <div className="max-w-xs">
                        <p className="font-medium text-slate-900 line-clamp-2">{fmt(pub.title)}</p>
                        {pub.venue && <p className="text-xs text-slate-400 mt-0.5">{pub.venue}</p>}
                      </div>
                    ),
                    status: <StatusBadge label={status} color={statusColor} />,
                    year: fmt(pub.year),
                    type: <span className="capitalize">{fmt(pub.type || pub.pub_type)}</span>,
                    citations: <span className="font-medium text-slate-900">{fmtNum(pub.citations)}</span>,
                  };
                })}
              />
            )}

            {/* Publication type distribution */}
            {pubTypeItems.length > 0 && (
              <Card padding="lg">
                <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-4">Publication Type Distribution</div>
                <HBarChart items={pubTypeItems} />
              </Card>
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
                <Card padding="lg">
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-4">
                    Citations Over Time (Last 12 Months)
                  </div>
                  <VBarChart items={citationMonthly} height={160} color="#0891B2" />
                </Card>

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
                    <Card key={label} padding="lg">
                      <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">{label}</div>
                      <div className="font-serif text-3xl text-slate-900">{value}</div>
                    </Card>
                  ))}
                </div>

                {/* Citation distribution by publication */}
                {publications.length > 0 && (
                  <Card padding="lg">
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
                  </Card>
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
            <Card padding="xl" style={{ borderColor: "#0F2847" }}>
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
            </Card>

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
                <Card key={label} padding="lg">
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">{label}</div>
                  <div className="font-serif text-3xl text-slate-900">{mainLoading ? "—" : value}</div>
                </Card>
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
                  <Card key={c.id || idx} padding="lg">
                    <div className="font-medium text-slate-900 mb-1 line-clamp-1">{fmt(c.title)}</div>
                    <div className="flex items-center gap-2 flex-wrap mb-2">
                      {c.type && <StatusBadge label={c.type} color="blue" />}
                      {c.status && <StatusBadge label={c.status} color={c.status === "active" ? "green" : "slate"} />}
                    </div>
                    <div className="text-xs text-slate-500 space-y-0.5">
                      {c.member_count != null && <div>{c.member_count} members</div>}
                      {c.research_area && <div>{c.research_area}</div>}
                    </div>
                  </Card>
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
                <Card key={label} padding="lg">
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">{label}</div>
                  <div className="font-serif text-3xl text-slate-900">{mainLoading ? "—" : value}</div>
                </Card>
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
              <DataTable
                columns={[
                  { key: "grant",   label: "Grant" },
                  { key: "status",  label: "Status" },
                  { key: "amount",  label: "Amount" },
                  { key: "applied", label: "Applied" },
                ]}
                rows={(grants.applications || []).map((g, idx) => {
                  const status = g.status || "pending";
                  const sc = status === "funded" || status === "approved" ? "green" :
                             status === "rejected" ? "red" : "amber";
                  return {
                    id: g.id || idx,
                    grant: (
                      <div>
                        <p className="font-medium text-slate-900 line-clamp-1">{fmt(g.title)}</p>
                        {g.funder && <p className="text-xs text-slate-400 mt-0.5">{g.funder}</p>}
                      </div>
                    ),
                    status: <StatusBadge label={status} color={sc} />,
                    amount: g.amount ? `€${fmtNum(g.amount)}` : "—",
                    applied: formatDate(g.applied_at || g.created_at),
                  };
                })}
              />
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
                <Card key={label} padding="lg">
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-1">{label}</div>
                  <div className="font-serif text-3xl text-slate-900">{mainLoading ? "—" : value}</div>
                </Card>
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
              <Card padding="lg">
                <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-4">Teaching Contribution</div>
                <div className="space-y-3">
                  <ProgressBar label="Lessons Published" value={teaching.lessons_published || 0} max={50} color="#7C3AED" />
                  <ProgressBar label="Courses" value={teaching.courses || 0} max={10} color="#0891B2" />
                  <ProgressBar label="Teaching Score" value={teaching.contribution_score || 0} max={1000} color="#059669" />
                </div>
              </Card>
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
                    <Card key={idx} padding="lg">
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
                    </Card>
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
              <Card padding="lg">
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
              </Card>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 10: FORECASTS
        ══════════════════════════════════════════════════════════════ */}
        {activeTab === "forecasts" && (
          <div className="space-y-6">
            <Callout variant="warning">
              Forecasts are based on your historical activity patterns. Add more data points for improved accuracy.
            </Callout>

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
              <Card key={to} to={to} padding="md" className="group">
                <div className="text-xs font-medium text-slate-700 group-hover:text-[#0F2847] transition-colors flex items-center justify-between">
                  {label} <ChevronRight size={12} className="text-slate-300 group-hover:text-[#0F2847]" />
                </div>
              </Card>
            ))}
          </div>
        </section>

    </ResearchLayout>
  );
}

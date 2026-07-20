import React, { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { AnalyticsLayout } from "@/layouts";
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import {
  Lock, Download, TrendingUp, Award, BookOpen, Zap, RefreshCw,
  ExternalLink, ChevronRight, Bell, BarChart2, Target, Sparkles,
  ArrowUpRight, Info, Users, FolderOpen, FileText, CheckCircle2,
  AlertCircle, Layers, Activity,
} from "lucide-react";
import { TID } from "../lib/testIds";
import { NAVY, WARM } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";
import {
  useResearchImpactDashboard,
  useImpactCitationChart,
  useSaveGoals,
} from "../hooks/useResearchImpact";

// ─────────────────────────── research intelligence nav ───────────────────────

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

const ImpactHero = ({ kpi, onExport }) => (
  <div style={{ background: "#F4F6FA", margin: "-24px -24px 0", padding: "28px 32px 24px", borderBottom: "1px solid rgba(15,23,42,0.08)", marginBottom: 40 }}>
    <IntelNav current="/research-impact" />
    <div style={{ marginTop: 16, display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 20, flexWrap: "wrap" }}>
      <div>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 6 }}>Research Intelligence</div>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "#0F172A", margin: "0 0 6px", letterSpacing: "-0.02em", fontFamily: "Georgia, serif" }}>Research Impact</h1>
        <p style={{ fontSize: 13, color: "#64748B", margin: 0, maxWidth: 520, lineHeight: 1.6 }}>
          Publication output, citation growth, collaboration network, and research score in one view.
          {kpi?.last_synced && <span style={{ color: "#94A3B8", marginLeft: 6 }}>Last synced: {new Date(kpi.last_synced).toLocaleDateString()}</span>}
        </p>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={onExport} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", padding: "8px 14px", border: "1px solid rgba(15,23,42,0.08)", background: "#fff", cursor: "pointer" }}>
          <Download size={12} strokeWidth={1.5} /> Export CSV
        </button>
        <button onClick={() => window.print()} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#fff", padding: "8px 14px", background: "#0F2847", border: "none", cursor: "pointer" }}>
          <FileText size={12} strokeWidth={1.5} /> Print / PDF
        </button>
      </div>
    </div>
  </div>
);

// ─────────────────────────── primitives ──────────────────────────────────────

function Stat({ label, value, sub, highlight, icon: Icon }) {
  return (
    <div className={`border bg-white p-6 ${highlight ? "border-[#0F2847]" : "border-slate-200"}`}>
      <div className="flex items-center justify-between mb-1">
        <div className="overline">{label}</div>
        {Icon && <Icon size={14} strokeWidth={1.5} className="text-slate-400" />}
      </div>
      <div className={`font-serif text-5xl mt-2 tracking-tight ${highlight ? "text-[#0F2847]" : "text-slate-900"}`}>
        {value ?? "—"}
      </div>
      {sub && <div className="text-xs text-slate-500 mt-2">{sub}</div>}
    </div>
  );
}

function SectionHeader({ label, icon: Icon, action, sub }) {
  return (
    <div className="flex items-start justify-between mb-5">
      <div>
        <div className="flex items-center gap-2">
          {Icon && <Icon size={14} strokeWidth={1.5} className="text-slate-500" />}
          <h2 className="overline">{label}</h2>
        </div>
        {sub && <p className="text-sm text-slate-500 mt-1">{sub}</p>}
      </div>
      {action}
    </div>
  );
}

function DataNote({ children }) {
  return (
    <div className="flex items-start gap-2 border border-amber-100 bg-amber-50 p-3 text-xs text-amber-800">
      <Info size={12} className="shrink-0 mt-0.5 text-amber-600" />
      <span>{children}</span>
    </div>
  );
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="border border-slate-200 bg-white shadow-sm px-3 py-2 text-xs">
      <div className="font-medium text-slate-900 mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2 text-slate-600">
          <span style={{ color: p.color }}>■</span>
          <span>{p.name}: {p.value?.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

function Badge({ children, color = "slate" }) {
  const colors = {
    slate:  "bg-slate-100 text-slate-700",
    cyan:   "bg-cyan-50 text-cyan-800 border border-cyan-200",
    green:  "bg-green-50 text-green-800 border border-green-200",
    amber:  "bg-amber-50 text-amber-800 border border-amber-200",
    red:    "bg-red-50 text-red-800 border border-red-200",
    navy:   "bg-[#0F2847] text-white",
  };
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 ${colors[color] || colors.slate}`}>
      {children}
    </span>
  );
}

function ScoreBar({ label, value, color = "#0F2847", formula, reasoning }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-slate-700">{label}</span>
        <span className="font-serif text-sm font-medium text-slate-900">{value ?? 0}<span className="text-slate-400 text-xs">/100</span></span>
      </div>
      <div className="h-2 bg-slate-100 w-full overflow-hidden">
        <div className="h-full transition-all duration-700" style={{ width: `${value ?? 0}%`, backgroundColor: color }} />
      </div>
      {(formula || reasoning) && (
        <button
          onClick={() => setOpen((o) => !o)}
          className="text-[10px] text-slate-400 hover:text-slate-600 mt-1 flex items-center gap-1"
        >
          <Info size={9} /> {open ? "Hide formula" : "How is this calculated?"}
        </button>
      )}
      {open && (
        <div className="mt-2 border border-slate-100 bg-slate-50 p-3 text-xs text-slate-600 space-y-1">
          {formula   && <p><span className="font-medium">Formula:</span> <code className="font-mono text-[10px]">{formula}</code></p>}
          {reasoning && <p><span className="font-medium">Your data:</span> {reasoning}</p>}
        </div>
      )}
    </div>
  );
}

function ProgressRing({ pct = 0, size = 80, stroke = 6, color = "#0F2847" }) {
  const r  = (size - stroke) / 2;
  const ci = 2 * Math.PI * r;
  const off = ci - (Math.min(100, pct) / 100) * ci;
  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color}
        strokeWidth={stroke} strokeDasharray={ci} strokeDashoffset={off}
        strokeLinecap="round" className="transition-all duration-700" />
    </svg>
  );
}

function GoalRow({ label, current, target, pct }) {
  if (!target) return null;
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-700">{label}</span>
        <span className="text-xs text-slate-500">{current?.toLocaleString()} / {target?.toLocaleString()}</span>
      </div>
      <div className="h-1.5 bg-slate-100 w-full">
        <div
          className="h-full bg-[#0F2847] transition-all duration-700"
          style={{ width: `${Math.min(100, pct ?? 0)}%` }}
        />
      </div>
      {pct !== null && pct !== undefined && (
        <div className="text-[10px] text-slate-400 mt-0.5">{pct}% complete</div>
      )}
    </div>
  );
}

const TREND_BADGE = {
  rising:   { label: "Rising",    color: "green" },
  emerging: { label: "Emerging",  color: "cyan" },
  growing:  { label: "Growing",   color: "green" },
  stable:   { label: "Stable",    color: "slate" },
  declining:{ label: "Declining", color: "amber" },
};

const INSIGHT_ICONS = {
  "trending-up": TrendingUp,
  "award":       Award,
  "zap":         Zap,
  "users":       Users,
  "bar-chart":   BarChart2,
  "target":      Target,
  "folder":      FolderOpen,
  "refresh":     RefreshCw,
};

const PERIOD_OPTIONS = ["30d", "90d", "365d", "all"];
const PERIOD_LABELS  = { "30d": "30 days", "90d": "90 days", "365d": "1 year", "all": "All time" };

// ─────────────────────────── gated wall ──────────────────────────────────────

function UpgradeWall() {
  return (
    <div className="space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <div className="overline">Pro Researcher</div>
        <h1 className="font-serif text-5xl text-slate-900 mt-2">Research Impact Dashboard</h1>
      </header>
      <div className="border border-slate-200 bg-white p-16 flex flex-col items-center text-center gap-6">
        <Lock size={28} strokeWidth={1} className="text-slate-300" />
        <div>
          <div className="overline text-[#0F2847] mb-2">Pro Researcher plan required</div>
          <h2 className="font-serif text-3xl text-slate-900">Your central research intelligence hub</h2>
          <p className="text-slate-500 text-sm mt-3 max-w-lg mx-auto">
            The Research Impact Dashboard combines all SYNAPTIQ modules into a single executive view:
            citation growth, research scorecard, AI insights, goal tracking, and export — all from real data.
          </p>
        </div>
        <div className="grid sm:grid-cols-3 gap-4 w-full max-w-xl text-left text-xs text-slate-600">
          {[
            ["Research Scorecard", "Transparent 5-component score with formulas"],
            ["Citation Growth Charts", "Interactive timeline of your citation history"],
            ["AI Research Insights", "Rule-based patterns from your actual data"],
            ["Research Area Breakdown", "Which topics generate the most citations"],
            ["Goals & Progress",   "Set publication and citation milestones"],
            ["CSV Export",         "Download complete publication impact table"],
          ].map(([t, d]) => (
            <div key={t} className="border border-slate-100 bg-slate-50 p-3">
              <CheckCircle2 size={12} className="text-[#0F2847] mb-1" />
              <div className="font-medium text-slate-800">{t}</div>
              <div className="text-slate-500 mt-0.5">{d}</div>
            </div>
          ))}
        </div>
        <Link
          to="/pricing"
          className="inline-block bg-[#0F2847] text-white text-sm px-8 py-3 hover:opacity-90 transition-opacity"
        >
          Upgrade to Pro Researcher
        </Link>
      </div>
    </div>
  );
}

// ─────────────────────────── citation chart section ───────────────────────────

function CitationGrowthSection() {
  const [period, setPeriod] = useState("365d");
  const { data, loading }   = useImpactCitationChart(period);

  return (
    <section data-testid={TID.impactCitationChart}>
      <SectionHeader
        label="Citation Growth"
        icon={TrendingUp}
        sub="Citation accumulation over time from OpenAlex snapshots"
        action={
          <div className="flex gap-1">
            {PERIOD_OPTIONS.map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`text-xs px-3 py-1 border transition-colors ${
                  period === p
                    ? "bg-[#0F2847] text-white border-[#0F2847]"
                    : "border-slate-200 text-slate-600 hover:border-slate-400"
                }`}
              >
                {PERIOD_LABELS[p]}
              </button>
            ))}
          </div>
        }
      />

      {loading && <div className="py-8 flex justify-center"><Spinner size={16} /></div>}

      {!loading && data?.series?.length > 0 && (
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-4">Cumulative Citations</div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={data.series}>
                <defs>
                  <linearGradient id="citFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#0F2847" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#0F2847" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} width={35} />
                <Tooltip content={<ChartTooltip />} />
                <Area dataKey="cumulative" name="Cumulative" stroke="#0F2847" fill="url(#citFill)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-4">New Citations per Month</div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={data.series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} width={35} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="new_citations" name="New Citations" fill="#0891b2" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {!loading && data?.distribution?.length > 0 && (
        <div className="mt-5 border border-slate-200 bg-white p-5">
          <div className="overline mb-4">Publication Citation Distribution</div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={data.distribution} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="label" tick={{ fontSize: 10 }} width={90} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="count" name="Publications" fill="#0F2847" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-slate-500 mt-2">
            Avg monthly velocity: <span className="font-medium text-slate-800">{data.avg_monthly_velocity} citations/month</span>
          </p>
        </div>
      )}

      {!loading && (!data?.series?.length) && (
        <div className="border border-dashed border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
          No citation history yet. Sync your publications via Citation Tracker to start tracking.
          <div className="mt-3">
            <Link to="/citations" className="text-[#0F2847] underline underline-offset-2 text-xs">
              Go to Citation Tracker →
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}

// ─────────────────────────── goals editor ────────────────────────────────────

function GoalsSection({ goals: initialGoals, progress }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm]       = useState({
    target_publications:   initialGoals?.target_publications   ?? "",
    target_citations:      initialGoals?.target_citations      ?? "",
    target_collaborations: initialGoals?.target_collaborations ?? "",
    target_projects:       initialGoals?.target_projects       ?? "",
    target_h_index:        initialGoals?.target_h_index        ?? "",
    deadline:              initialGoals?.deadline              ?? "",
  });
  const { save, saving, error } = useSaveGoals();

  const handleSave = useCallback(async () => {
    const payload = {};
    for (const [k, v] of Object.entries(form)) {
      if (v !== "" && v !== null) {
        payload[k] = k === "deadline" ? v : Number(v);
      }
    }
    await save(payload);
    setEditing(false);
  }, [form, save]);

  const fields = [
    { key: "target_publications",   label: "Target Publications" },
    { key: "target_citations",      label: "Target Citations" },
    { key: "target_collaborations", label: "Target Collaborations" },
    { key: "target_projects",       label: "Target Projects" },
    { key: "target_h_index",        label: "Target h-index" },
  ];

  return (
    <section data-testid={TID.impactGoals}>
      <SectionHeader
        label="Goals & Progress"
        icon={Target}
        sub="Set personal research milestones and track your progress"
        action={
          !editing ? (
            <button
              onClick={() => setEditing(true)}
              className="text-xs border border-slate-200 px-3 py-1.5 hover:border-slate-400 transition-colors"
            >
              {initialGoals ? "Edit goals" : "Set goals"}
            </button>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={() => setEditing(false)}
                className="text-xs border border-slate-200 px-3 py-1.5 hover:border-slate-400"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="text-xs bg-[#0F2847] text-white px-3 py-1.5 hover:opacity-90 disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          )
        }
      />

      {error && (
        <div className="flex items-center gap-2 text-xs text-red-700 border border-red-100 bg-red-50 p-3 mb-4">
          <AlertCircle size={12} /> {error}
        </div>
      )}

      {editing ? (
        <div className="border border-slate-200 bg-white p-6">
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {fields.map(({ key, label }) => (
              <div key={key}>
                <label className="text-xs font-medium text-slate-700 block mb-1">{label}</label>
                <input
                  type="number"
                  min={0}
                  value={form[key]}
                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                  className="w-full border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847]"
                  placeholder="e.g. 50"
                />
              </div>
            ))}
            <div>
              <label className="text-xs font-medium text-slate-700 block mb-1">Target Deadline</label>
              <input
                type="date"
                value={form.deadline ? form.deadline.slice(0, 10) : ""}
                onChange={(e) => setForm((f) => ({ ...f, deadline: e.target.value }))}
                className="w-full border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847]"
              />
            </div>
          </div>
        </div>
      ) : progress ? (
        <div className="border border-slate-200 bg-white p-6 space-y-5">
          {initialGoals?.deadline && (
            <p className="text-xs text-slate-500">Deadline: <span className="font-medium text-slate-700">{initialGoals.deadline.slice(0, 10)}</span></p>
          )}
          <GoalRow label="Publications" current={progress.publications?.current} target={progress.publications?.target} pct={progress.publications?.pct} />
          <GoalRow label="Citations"    current={progress.citations?.current}    target={progress.citations?.target}    pct={progress.citations?.pct} />
          <GoalRow label="Collaborations" current={progress.collaborations?.current} target={progress.collaborations?.target} pct={progress.collaborations?.pct} />
          <GoalRow label="Projects"    current={progress.projects?.current}    target={progress.projects?.target}    pct={progress.projects?.pct} />
          <GoalRow label="h-index"     current={progress.h_index?.current}     target={progress.h_index?.target}     pct={progress.h_index?.pct} />
        </div>
      ) : (
        <div className="border border-dashed border-slate-200 p-10 text-center">
          <Target size={24} strokeWidth={1} className="text-slate-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500">No goals set yet.</p>
          <p className="text-xs text-slate-400 mt-1">Click "Set goals" to add publication, citation, and collaboration targets.</p>
        </div>
      )}
    </section>
  );
}

// ─────────────────────────── main page ───────────────────────────────────────

export default function ResearchImpact() {
  const { data, loading, error, refetch } = useResearchImpactDashboard();
  const [scorecardOpen, setScorecardOpen] = useState(false);

  // Handle gate
  if (!loading && error && (error?.includes?.("402") || error === "Forbidden" || error?.toString().includes("402") || error?.toString().includes("pro"))) {
    return <UpgradeWall />;
  }

  if (loading) {
    return (
      <AnalyticsLayout title="Research Impact" subtitle="Publication output, citation growth, collaboration network, and research score in one view.">
        <div className="py-16 flex justify-center"><Spinner size={20} /></div>
      </AnalyticsLayout>
    );
  }

  if (error) {
    return (
      <AnalyticsLayout title="Research Impact" subtitle="Publication output, citation growth, collaboration network, and research score in one view.">
        <div className="border border-red-100 bg-red-50 p-6 text-sm text-red-700 flex items-center gap-3">
          <AlertCircle size={16} />
          <span>Failed to load dashboard: {error}</span>
          <button onClick={refetch} className="ml-auto text-xs underline">Retry</button>
        </div>
      </AnalyticsLayout>
    );
  }

  if (!data) return null;

  const { kpi, pub_spotlight, areas, collabs, projects, opportunities, scorecard, goals, insights } = data;
  const allAreas   = areas?.areas     || [];
  const classified = areas?.classified || {};

  const handleExport = () => {
    window.open("/api/research-impact/export", "_blank");
  };

  return (
    <AnalyticsLayout
      title="Research Impact"
      subtitle={
        <>
          Publication output, citation growth, collaboration network, and research score in one view.
          {kpi?.last_synced && <span style={{ color: "#94A3B8", marginLeft: 6 }}>Last synced: {new Date(kpi.last_synced).toLocaleDateString()}</span>}
        </>
      }
      actions={
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={handleExport} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", padding: "8px 14px", border: "1px solid rgba(15,23,42,0.08)", background: "#fff", cursor: "pointer" }}>
            <Download size={12} strokeWidth={1.5} /> Export CSV
          </button>
          <button onClick={() => window.print()} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#fff", padding: "8px 14px", background: "#0F2847", border: "none", cursor: "pointer" }}>
            <FileText size={12} strokeWidth={1.5} /> Print / PDF
          </button>
        </div>
      }
    >
    <div data-testid={TID.researchImpactPage}>

      {kpi?.has_citations_data === false && (
        <div style={{ marginBottom: 24, fontSize: 12, color: "#92400E", background: "#FFFBEB", border: "1px solid #FDE68A", padding: "10px 16px" }}>
          No citation data yet. Import publications via ORCID then sync via Citation Tracker to populate this dashboard.
        </div>
      )}

      <div className="space-y-14">

      {/* ── Section 1: KPIs ── */}
      <section data-testid={TID.impactKPIs}>
        <SectionHeader label="Research Output" icon={BarChart2} />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <Stat label="Publications" value={kpi?.publications?.toLocaleString()} icon={BookOpen}
            sub={kpi?.enriched_pubs ? `${kpi.enriched_pubs} enriched via OpenAlex` : undefined} />
          <Stat label="Total Citations" value={kpi?.citations?.toLocaleString()} icon={Activity} highlight
            sub={kpi?.cit_delta_30d > 0 ? `+${kpi.cit_delta_30d} in last 30 days` : undefined} />
          <Stat label="h-index" value={kpi?.h_index || "—"} icon={Award}
            sub={kpi?.i10_index ? `i10-index: ${kpi.i10_index}` : undefined} />
          <Stat label="Active Collaborations" value={kpi?.active_collabs?.toLocaleString()} icon={Users}
            sub={kpi?.total_projects ? `${kpi.total_projects} projects` : undefined} />
        </div>
      </section>

      {/* ── Section 2: Publication Spotlight ── */}
      {pub_spotlight && (
        <section data-testid={TID.impactPubSpotlight}>
          <SectionHeader label="Publication Impact" icon={BookOpen}
            sub="Top publications by citations, velocity, and recent growth" />
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {pub_spotlight.most_cited && (
              <div className="border border-[#0F2847] bg-white p-5">
                <div className="overline text-[#0F2847] mb-2">Most Cited</div>
                <p className="text-sm font-medium text-slate-900 line-clamp-2">{pub_spotlight.most_cited.title}</p>
                <div className="flex items-center gap-3 mt-3 text-xs text-slate-500">
                  <span>{pub_spotlight.most_cited.year}</span>
                  <span>·</span>
                  <span className="font-medium text-slate-800">{pub_spotlight.most_cited.citations?.toLocaleString()} citations</span>
                </div>
                {pub_spotlight.most_cited.topics?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {pub_spotlight.most_cited.topics.map((t) => <Badge key={t} color="slate">{t}</Badge>)}
                  </div>
                )}
                <Link to={`/citations/${pub_spotlight.most_cited.id}`}
                  className="mt-4 flex items-center gap-1 text-xs text-[#0F2847] hover:underline">
                  View details <ChevronRight size={12} />
                </Link>
              </div>
            )}

            {pub_spotlight.fastest_growing && (
              <div className="border border-slate-200 bg-white p-5">
                <div className="overline mb-2">Fastest Growing</div>
                <p className="text-sm font-medium text-slate-900 line-clamp-2">{pub_spotlight.fastest_growing.title}</p>
                <div className="flex items-center gap-3 mt-3 text-xs text-slate-500">
                  <span>{pub_spotlight.fastest_growing.year}</span>
                  <span>·</span>
                  <span className="text-green-700 font-medium">+{pub_spotlight.fastest_growing.recent_delta} citations</span>
                  <span className="text-green-600">({pub_spotlight.fastest_growing.growth_pct}%)</span>
                </div>
                <Link to={`/citations/${pub_spotlight.fastest_growing.id}`}
                  className="mt-4 flex items-center gap-1 text-xs text-[#0F2847] hover:underline">
                  View details <ChevronRight size={12} />
                </Link>
              </div>
            )}

            {pub_spotlight.highest_velocity && (
              <div className="border border-slate-200 bg-white p-5">
                <div className="overline mb-2">Highest Velocity</div>
                <p className="text-sm font-medium text-slate-900 line-clamp-2">{pub_spotlight.highest_velocity.title}</p>
                <div className="flex items-center gap-3 mt-3 text-xs text-slate-500">
                  <span>{pub_spotlight.highest_velocity.year}</span>
                  <span>·</span>
                  <span className="font-medium text-slate-800">{pub_spotlight.highest_velocity.velocity} cit/yr</span>
                </div>
                <Link to={`/citations/${pub_spotlight.highest_velocity.id}`}
                  className="mt-4 flex items-center gap-1 text-xs text-[#0F2847] hover:underline">
                  View details <ChevronRight size={12} />
                </Link>
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── Section 3: Citation Growth Chart ── */}
      <CitationGrowthSection />

      {/* ── Section 4: Research Areas ── */}
      {allAreas.length > 0 && (
        <section data-testid={TID.impactResearchAreas}>
          <SectionHeader label="Research Areas Impact" icon={Layers}
            sub="Citation performance broken down by your research topics" />
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {allAreas.slice(0, 9).map((a) => {
              const t = TREND_BADGE[a.trend] || TREND_BADGE.stable;
              return (
                <div key={a.area} className="border border-slate-200 bg-white p-4">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="text-sm font-medium text-slate-900 line-clamp-1">{a.area}</span>
                    <Badge color={t.color}>{t.label}</Badge>
                  </div>
                  <div className="flex gap-4 text-xs text-slate-500">
                    <span><span className="font-medium text-slate-800">{(a.total_citations || 0).toLocaleString()}</span> citations</span>
                    <span><span className="font-medium text-slate-800">{a.publication_count}</span> pubs</span>
                  </div>
                  {a.growth_rate > 0 && (
                    <div className="text-xs text-green-700 mt-1">+{a.growth_rate}% growth</div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* ── Section 5: Collaboration Impact ── */}
      <section data-testid={TID.impactCollabs}>
        <SectionHeader label="Collaboration Impact" icon={Users}
          sub="Collaboration network and outcomes" />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-6">
          <Stat label="Sent Requests"     value={collabs?.sent_total ?? "—"} />
          <Stat label="Received Requests" value={collabs?.received_total ?? "—"} />
          <Stat label="Accepted"          value={collabs?.accepted ?? "—"} highlight />
          <Stat label="Success Rate"      value={collabs?.success_rate != null ? `${collabs.success_rate}%` : "—"} />
        </div>
        {collabs?.top_collaborators?.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-4">Active Collaborators</div>
            <div className="divide-y divide-slate-100">
              {collabs.top_collaborators.map((c) => (
                <div key={c.id} className="flex items-center gap-3 py-2.5">
                  {c.avatar_url
                    ? <img src={c.avatar_url} alt="" className="w-8 h-8 rounded-full object-cover" />
                    : <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-xs font-medium text-slate-600">{c.full_name?.[0]}</div>
                  }
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">{c.full_name}</p>
                    <p className="text-xs text-slate-500 truncate">{c.institution || c.role}</p>
                  </div>
                  <Link to={`/discover/${c.id}`} className="text-xs text-[#0F2847] hover:underline flex items-center gap-0.5">
                    View <ChevronRight size={10} />
                  </Link>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* ── Section 6: Project Impact ── */}
      <section data-testid={TID.impactProjects}>
        <SectionHeader label="Project Impact" icon={FolderOpen}
          sub="Research projects and their origins" />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-6">
          <Stat label="Total Projects"      value={projects?.total ?? "—"} />
          <Stat label="With Team"           value={projects?.with_team ?? "—"} />
          <Stat label="From Gap Analysis"   value={projects?.from_gap ?? "—"} highlight />
          <Stat label="Collab-Sourced"      value={projects?.from_collab ?? "—"} />
        </div>
        {projects?.project_cards?.length > 0 && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.project_cards.slice(0, 6).map((p) => (
              <div key={p.id} className="border border-slate-200 bg-white p-4">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <p className="text-sm font-medium text-slate-900 line-clamp-1">{p.title}</p>
                  <Badge color={p.visibility === "public" ? "green" : "slate"}>
                    {p.visibility}
                  </Badge>
                </div>
                <p className="text-xs text-slate-500 line-clamp-2 mt-1">{p.description}</p>
                <div className="flex items-center gap-3 text-xs text-slate-400 mt-2">
                  <span>{p.team_size} member{p.team_size !== 1 ? "s" : ""}</span>
                  {p.source && <span>· From {p.source.replace(/_/g, " ")}</span>}
                </div>
                <Link to={`/projects/${p.id}`} className="mt-3 text-xs text-[#0F2847] hover:underline flex items-center gap-0.5">
                  View project <ChevronRight size={10} />
                </Link>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Section 7: Research Opportunities ── */}
      {(opportunities?.gap_opportunities?.length > 0 || opportunities?.citation_opps?.length > 0) && (
        <section data-testid={TID.impactOpportunities}>
          <SectionHeader label="Research Opportunities" icon={Target}
            sub="High-potential areas identified from gap analyses and citation patterns" />
          <div className="grid lg:grid-cols-2 gap-6">
            {opportunities.gap_opportunities.length > 0 && (
              <div className="space-y-3">
                <div className="overline mb-3">From Gap Analyses</div>
                {opportunities.gap_opportunities.map((o, i) => (
                  <div key={i} className="border border-slate-200 bg-white p-4">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium text-slate-900">{o.area}</p>
                      <Badge color={o.opportunity_level === "high" ? "navy" : o.opportunity_level === "medium" ? "cyan" : "slate"}>
                        {o.opportunity_level}
                      </Badge>
                    </div>
                    {o.explanation && <p className="text-xs text-slate-500 mt-1">{o.explanation}</p>}
                    {o.why && <p className="text-xs text-slate-400 mt-1 italic">{o.why}</p>}
                    <div className="mt-2 text-xs text-slate-400">Topic: {o.topic}</div>
                  </div>
                ))}
                <Link to="/research-gap-finder" className="text-xs text-[#0F2847] hover:underline flex items-center gap-0.5">
                  Run new gap analysis <ChevronRight size={10} />
                </Link>
              </div>
            )}

            {opportunities.citation_opps.length > 0 && (
              <div className="space-y-3">
                <div className="overline mb-3">From Citation Patterns</div>
                {opportunities.citation_opps.map((o, i) => (
                  <div key={i} className="border border-slate-200 bg-white p-4">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium text-slate-900">{o.area}</p>
                      <Badge color={o.priority === "high" ? "green" : "slate"}>
                        {o.trend}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">{o.why}</p>
                    <div className="flex gap-3 text-xs text-slate-400 mt-2">
                      <span>{(o.citations || 0).toLocaleString()} citations</span>
                      {o.growth_rate > 0 && <span>+{o.growth_rate}% growth</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── Section 8: Research Scorecard ── */}
      {scorecard && (
        <section data-testid={TID.impactScorecard}>
          <SectionHeader
            label="Academic Performance Scorecard"
            icon={Award}
            sub="Transparent 5-component research impact score with open formulas"
            action={
              <button
                onClick={() => setScorecardOpen((o) => !o)}
                className="text-xs border border-slate-200 px-3 py-1.5 hover:border-slate-400 transition-colors"
              >
                {scorecardOpen ? "Collapse" : "Show formulas"}
              </button>
            }
          />

          <div className="border border-[#0F2847] bg-white p-6">
            <div className="flex items-center gap-6 mb-8">
              <div className="relative flex-shrink-0">
                <ProgressRing pct={scorecard.overall} size={100} stroke={8} />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="font-serif text-3xl text-slate-900">{scorecard.overall}</span>
                  <span className="text-[10px] text-slate-400">/100</span>
                </div>
              </div>
              <div>
                <div className="overline mb-1">Overall Impact Score</div>
                <p className="text-sm text-slate-600 max-w-xs">
                  Weighted across 5 research dimensions — all numbers are calculated transparently from your real data.
                </p>
                <code className="text-[10px] text-slate-400 mt-2 block">{scorecard.formula}</code>
              </div>
            </div>

            <div className="space-y-6">
              {Object.entries(scorecard.components || {}).map(([key, c]) => (
                <ScoreBar
                  key={key}
                  label={`${c.label} (${Math.round((c.weight || 0) * 100)}% weight · ${c.contribution} pts)`}
                  value={c.score}
                  color={key === "citation" ? "#0891b2" : key === "publication" ? "#0F2847" : key === "collaboration" ? "#7c3aed" : key === "project" ? "#059669" : "#d97706"}
                  formula={scorecardOpen ? c.formula : undefined}
                  reasoning={scorecardOpen ? c.reasoning : undefined}
                />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Section 9: AI Insights ── */}
      {insights?.length > 0 && (
        <section data-testid={TID.impactInsights}>
          <SectionHeader label="AI Research Insights" icon={Sparkles}
            sub="Rule-based patterns derived from your real data — no AI hallucinations" />
          <div className="grid sm:grid-cols-2 gap-4">
            {insights.map((ins, i) => {
              const Icon = INSIGHT_ICONS[ins.icon] || Sparkles;
              const pColor = ins.priority === "high" ? "border-l-[#0F2847]" :
                             ins.priority === "medium" ? "border-l-[#0891b2]" : "border-l-slate-300";
              return (
                <div key={i} className={`border border-slate-200 border-l-4 ${pColor} bg-white p-4 flex gap-3`}>
                  <Icon size={16} strokeWidth={1.5} className="text-slate-400 shrink-0 mt-0.5" />
                  <p className="text-sm text-slate-700">{ins.text}</p>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* ── Section 10: Goals ── */}
      <GoalsSection goals={goals?.goals} progress={goals?.progress} />

      {/* ── Section 11: Export ── */}
      <section data-testid={TID.impactExport}>
        <SectionHeader label="Export & Reports" icon={Download} />
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="border border-slate-200 bg-white p-6">
            <div className="overline mb-2">CSV Export</div>
            <p className="text-xs text-slate-500 mb-4">Download all publications with citation counts, topics, co-authors, and enrichment status.</p>
            <button
              onClick={handleExport}
              className="flex items-center gap-2 text-xs bg-[#0F2847] text-white px-4 py-2 hover:opacity-90 transition-opacity"
            >
              <Download size={12} /> Download CSV
            </button>
          </div>
          <div className="border border-slate-200 bg-white p-6">
            <div className="overline mb-2">PDF / Print</div>
            <p className="text-xs text-slate-500 mb-4">Print this page or save it as a PDF — includes all charts, scorecard, and insights.</p>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-2 text-xs border border-slate-200 px-4 py-2 hover:border-slate-400 transition-colors"
            >
              <FileText size={12} /> Print / Save PDF
            </button>
          </div>
        </div>
      </section>

      {/* ── Section 12: Institutional compatibility note ── */}
      <section className="border border-dashed border-slate-200 bg-slate-50 p-6">
        <div className="flex items-start gap-3">
          <Info size={14} strokeWidth={1.5} className="text-slate-400 mt-0.5 shrink-0" />
          <div>
            <div className="overline mb-1">Institutional Compatibility</div>
            <p className="text-xs text-slate-600">
              This dashboard is designed to align with future institutional analytics in SYNAPTIQ.
              Department heads and institutional admins will be able to aggregate impact scores across
              their research groups. Your individual data feeds directly into those institutional views.
            </p>
          </div>
        </div>
      </section>

      {/* ── Research Intelligence Quick Links ── */}
      <section>
        <h2 className="overline mb-5">Continue in Research Intelligence</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {[
            { to: "/analytics",           label: "Analytics Overview"   },
            { to: "/citations",           label: "Citation Tracker"     },
            { to: "/citation-monitoring", label: "Citation Monitoring"  },
            { to: "/reputation",          label: "Reputation Score"     },
            { to: "/impact-dashboard",    label: "Impact Dashboard"     },
          ].map(({ to, label }) => (
            <Link key={to} to={to} className="border border-slate-200 bg-white p-4 hover:border-[#0F2847] transition-colors group block">
              <div className="text-xs font-medium text-slate-700 group-hover:text-[#0F2847] transition-colors flex items-center justify-between">
                {label} <ChevronRight size={12} className="text-slate-300 group-hover:text-[#0F2847]" />
              </div>
            </Link>
          ))}
        </div>
      </section>

    </div>
    </div>
    </AnalyticsLayout>
  );
}

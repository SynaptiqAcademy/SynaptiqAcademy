import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { AnalyticsLayout } from "@/layouts";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import {
  Lock, Users, Target, FolderPlus, Send, Clock, Sparkles,
  ArrowRight, Bell, TrendingUp, BookOpen, Zap, Award,
  Download, FileText, DollarSign, FileEdit, Network,
  CheckCircle, XCircle, AlertCircle, RefreshCw, ChevronRight,
} from "lucide-react";
import { useCitationDashboard } from "../hooks/useCitations";
import { WARM } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";

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

// ─────────────────────────── primitive stat card ─────────────────────────────

function Stat({ label, value, sub, icon: Icon, highlight }) {
  return (
    <div className={`border bg-white p-6 ${highlight ? "border-[#0F2847]" : "border-slate-200"}`}>
      <div className="flex items-center justify-between">
        <div className="overline">{label}</div>
        {Icon && <Icon size={13} strokeWidth={1.5} className={highlight ? "text-[#0F2847]" : "text-slate-300"} />}
      </div>
      <div className={`font-serif text-5xl mt-3 tracking-tight ${highlight ? "text-[#0F2847]" : "text-slate-900"}`}>
        {value ?? "—"}
      </div>
      {sub && <div className="text-xs text-slate-400 mt-1 font-mono">{sub}</div>}
    </div>
  );
}

function Score({ label, value }) {
  const pct = Math.min(100, Math.max(0, Number(value) || 0));
  return (
    <div className="border border-slate-200 bg-white p-6">
      <div className="flex items-baseline justify-between">
        <div className="overline">{label}</div>
        <div className="font-serif text-3xl text-slate-900">{pct}</div>
      </div>
      <div className="mt-3 h-1 bg-slate-100 relative">
        <div className="absolute inset-y-0 left-0 bg-[#0F2847] transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function SectionHeader({ label, sub, action }) {
  return (
    <div className="flex items-start justify-between mb-5">
      <div>
        <h2 className="overline">{label}</h2>
        {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
      </div>
      {action}
    </div>
  );
}

function EmptyState({ text, link, linkLabel }) {
  return (
    <div className="border border-dashed border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
      {text}
      {link && (
        <div className="mt-3">
          <Link to={link} className="text-[#0F2847] text-xs underline underline-offset-2">
            {linkLabel || "Go →"}
          </Link>
        </div>
      )}
    </div>
  );
}

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 px-3 py-2 text-xs shadow">
      <div className="font-medium text-slate-700 mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.color }}>
          {p.name}: <span className="font-mono font-medium">{p.value?.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
};

// ─────────────────────────── hooks ───────────────────────────────────────────

function useAnalytics(path) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(() => {
    setLoading(true);
    api.get(path)
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [path]);

  useEffect(() => { fetch(); }, [fetch]);
  return { data, loading, refetch: fetch };
}

// ─────────────────────────── gated wall ──────────────────────────────────────

function UpgradeWall() {
  return (
    <div className="space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <div className="overline">Dashboard</div>
        <h1 className="font-serif text-5xl text-slate-900 mt-2">Analytics</h1>
      </header>
      <div className="border border-slate-200 bg-white p-16 flex flex-col items-center text-center gap-5">
        <Lock size={28} strokeWidth={1} className="text-slate-300" />
        <div>
          <div className="overline text-[#0F2847] mb-2">Researcher plan required</div>
          <h2 className="font-serif text-2xl text-slate-900">Advanced Analytics is a paid feature</h2>
          <p className="text-slate-500 text-sm mt-3 max-w-sm mx-auto">
            Upgrade to Researcher to unlock real research metrics, grant analytics, manuscript pipeline,
            career timeline, and productivity scores.
          </p>
        </div>
        <Link
          to="/pricing"
          className="inline-block bg-[#0F2847] text-white text-sm px-6 py-2.5 hover:opacity-90 transition-opacity"
        >
          View Plans
        </Link>
      </div>
    </div>
  );
}

// ─────────────────────────── career timeline ─────────────────────────────────

function CareerTimeline() {
  const { data, loading } = useAnalytics("/analytics/career-timeline");

  if (loading) return <div className="py-6 flex justify-center"><Spinner size={16} /></div>;
  if (!data?.timeline?.length) {
    return (
      <EmptyState
        text="No career timeline yet. Publications and projects will appear here once added."
        link="/citations"
        linkLabel="Import publications →"
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="border border-slate-200 bg-white p-5">
        <div className="overline mb-4">Publications &amp; Citations Per Year</div>
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={data.timeline}>
            <defs>
              <linearGradient id="pubFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#0F2847" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#0F2847" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="year" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} width={28} />
            <Tooltip content={<ChartTooltip />} />
            <Area dataKey="publications" name="Publications" stroke="#0F2847" fill="url(#pubFill)" strokeWidth={2} dot={false} />
            <Area dataKey="grants_awarded" name="Grants awarded" stroke="#0891b2" fill="none" strokeWidth={1.5} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {data.first_publication_year && (
        <div className="grid sm:grid-cols-3 gap-4">
          <div className="border border-slate-200 bg-white p-4">
            <div className="overline text-slate-500">First Publication</div>
            <div className="font-serif text-3xl text-slate-900 mt-2">{data.first_publication_year}</div>
          </div>
          <div className="border border-slate-200 bg-white p-4">
            <div className="overline text-slate-500">Total Publications</div>
            <div className="font-serif text-3xl text-slate-900 mt-2">{data.total_publications}</div>
          </div>
          <div className="border border-slate-200 bg-white p-4">
            <div className="overline text-slate-500">Active Years</div>
            <div className="font-serif text-3xl text-slate-900 mt-2">{data.years_active}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────── grant analytics ─────────────────────────────────

const GRANT_STATUS_COLORS = {
  awarded:        "#16a34a",
  submitted:      "#0891b2",
  in_preparation: "#64748b",
  rejected:       "#dc2626",
  closed:         "#94a3b8",
};

function GrantAnalytics() {
  const { data, loading } = useAnalytics("/analytics/grants");

  if (loading) return <div className="py-6 flex justify-center"><Spinner size={16} /></div>;
  if (!data || data.total_grants === 0) {
    return (
      <EmptyState
        text="No grant data yet. Link your ORCID or create grant applications to see analytics."
        link="/grants"
        linkLabel="Manage grants →"
      />
    );
  }

  const pieData = (data.by_status || [])
    .filter((s) => s.count > 0)
    .map((s) => ({ name: s.status, value: s.count, fill: GRANT_STATUS_COLORS[s.status] || "#94a3b8" }));

  return (
    <div className="space-y-5">
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Total Grants"     value={data.total_grants}    icon={DollarSign} />
        <Stat label="Awarded"          value={data.awarded}          icon={CheckCircle} highlight />
        <Stat label="Success Rate"     value={`${data.success_rate}%`} icon={Target} />
        <Stat
          label="Funding (USD)"
          value={data.total_funding_usd > 0 ? `$${(data.total_funding_usd / 1000).toFixed(0)}k` : "—"}
          icon={Award}
        />
      </div>

      <div className="grid sm:grid-cols-2 gap-5">
        {pieData.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-4">By Status</div>
            <div className="flex items-center gap-6">
              <ResponsiveContainer width="50%" height={120}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={30} outerRadius={50}>
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1.5 text-xs">
                {pieData.map((s) => (
                  <div key={s.name} className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ background: s.fill }} />
                    <span className="text-slate-600 capitalize">{s.name.replace(/_/g, " ")}</span>
                    <span className="font-mono font-medium text-slate-800 ml-auto">{s.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {data.by_year?.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-4">Grant Applications by Year</div>
            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={data.by_year}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="year" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} width={20} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="count" name="Grants" fill="#0F2847" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {data.by_funder?.length > 0 && (
        <div className="border border-slate-200 bg-white p-5">
          <div className="overline mb-3">Top Funders</div>
          <div className="space-y-2">
            {data.by_funder.slice(0, 5).map((f) => (
              <div key={f.funder} className="flex items-center gap-3 text-sm">
                <span className="text-slate-700 truncate flex-1">{f.funder}</span>
                <span className="font-mono text-xs text-slate-500 shrink-0">{f.count} grant{f.count !== 1 ? "s" : ""}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────── manuscript analytics ────────────────────────────

const STAGE_COLORS = {
  accepted:           "#16a34a",
  published:          "#0d9488",
  under_review:       "#0891b2",
  revision_requested: "#d97706",
  submitted:          "#64748b",
  rejected:           "#dc2626",
  withdrawn:          "#94a3b8",
};

function ManuscriptAnalytics() {
  const { data, loading } = useAnalytics("/analytics/manuscripts");

  if (loading) return <div className="py-6 flex justify-center"><Spinner size={16} /></div>;
  if (!data || data.total_manuscripts === 0) {
    return (
      <EmptyState
        text="No manuscripts yet. Track your submission pipeline in the Publication Hub."
        link="/publication-hub"
        linkLabel="Open Publication Hub →"
      />
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Manuscripts"    value={data.total_manuscripts} icon={FileEdit} />
        <Stat label="Active"         value={data.active}            icon={RefreshCw} />
        <Stat label="Accepted / Published" value={data.accepted}   icon={CheckCircle} highlight />
        <Stat label="Acceptance Rate" value={`${data.acceptance_rate}%`} icon={Target} />
      </div>

      <div className="grid sm:grid-cols-2 gap-5">
        {data.stage_counts?.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-3">Submission Pipeline</div>
            <div className="space-y-2">
              {data.stage_counts.slice(0, 8).map((s) => (
                <div key={s.stage} className="flex items-center gap-3">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: STAGE_COLORS[s.stage] || "#94a3b8" }}
                  />
                  <span className="text-xs text-slate-600 capitalize flex-1">
                    {s.stage.replace(/_/g, " ")}
                  </span>
                  <span className="font-mono text-xs font-medium text-slate-800">{s.count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="border border-slate-200 bg-white p-5 space-y-4">
          <div>
            <div className="overline text-slate-500 text-[10px]">Avg Revision Cycles</div>
            <div className="font-serif text-4xl text-slate-900 mt-1">{data.avg_revision_cycles}</div>
          </div>
          <div>
            <div className="overline text-slate-500 text-[10px]">Total Submissions</div>
            <div className="font-serif text-4xl text-slate-900 mt-1">{data.total_submissions}</div>
          </div>
          {data.rejected > 0 && (
            <div className="text-xs text-slate-500">
              {data.rejected} rejection{data.rejected !== 1 ? "s" : ""},&nbsp;
              {data.withdrawn} withdrawal{data.withdrawn !== 1 ? "s" : ""}
            </div>
          )}
        </div>
      </div>

      {data.top_venues?.length > 0 && (
        <div className="border border-slate-200 bg-white p-5">
          <div className="overline mb-3">Venues Submitted To</div>
          <div className="space-y-2">
            {data.top_venues.slice(0, 5).map((v) => (
              <div key={v.venue} className="flex items-center gap-3 text-sm">
                <span className="text-slate-700 truncate flex-1">{v.venue}</span>
                <span className="font-mono text-xs text-slate-500 shrink-0">{v.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────── productivity score ───────────────────────────────

function ProductivityScore() {
  const { data, loading } = useAnalytics("/analytics/productivity");

  if (loading) return <div className="py-6 flex justify-center"><Spinner size={16} /></div>;
  if (!data) return null;

  return (
    <div className="space-y-5">
      <div className="border border-[#0F2847] bg-white p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="overline text-[#0F2847]">Research Productivity Score</div>
            <div className="font-serif text-6xl text-[#0F2847] mt-2 tracking-tight">{data.score}</div>
            <div className="text-xs text-slate-400 mt-1 font-mono">/ 100</div>
          </div>
          <div className="text-right text-xs text-slate-400 max-w-xs">
            {data.reputation_blended && (
              <div className="text-green-700 font-medium mb-1">✓ Reputation score blended</div>
            )}
            <div className="font-mono">{data.data_sources}</div>
          </div>
        </div>
        <div className="mt-4 h-1 bg-slate-100">
          <div className="h-1 bg-[#0F2847]" style={{ width: `${Math.min(100, data.score)}%` }} />
        </div>
      </div>

      <div className="border border-slate-200 bg-white p-5">
        <div className="overline mb-4">Score Components</div>
        <div className="space-y-3">
          {(data.components || []).map((c) => (
            <div key={c.key}>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-slate-700 font-medium">{c.label}</span>
                <div className="flex items-center gap-3 text-slate-400">
                  <span className="font-mono">
                    value: {c.value?.toLocaleString?.() ?? c.value}
                  </span>
                  <span className="font-mono text-slate-600 font-medium">{c.score} / 100</span>
                  <span className="text-slate-300">{Math.round(c.weight * 100)}% weight</span>
                </div>
              </div>
              <div className="h-1.5 bg-slate-100 rounded">
                <div
                  className="h-1.5 bg-[#0F2847] rounded transition-all"
                  style={{ width: `${Math.min(100, c.score)}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5 font-mono">{c.formula}</div>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-slate-400 mt-4 font-mono border-t border-slate-100 pt-3">
          {data.formula}
        </p>
      </div>
    </div>
  );
}

// ─────────────────────────── collaboration network ────────────────────────────

function CollaborationNetwork() {
  const { data, loading } = useAnalytics("/analytics/network");

  if (loading) return <div className="py-6 flex justify-center"><Spinner size={16} /></div>;
  if (!data || (data.total_unique_coauthors === 0 && data.total_partners === 0)) {
    return (
      <EmptyState
        text="No co-author data yet. Import publications via ORCID to populate your network."
        link="/citations"
        linkLabel="Citation Tracker →"
      />
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid sm:grid-cols-3 gap-4">
        <Stat label="Unique Co-authors"    value={data.total_unique_coauthors} icon={Users} />
        <Stat label="Collaboration Partners" value={data.total_partners}       icon={Network} />
        <Stat label="International"        value={data.international_partners} icon={Award} />
      </div>

      <div className="grid sm:grid-cols-2 gap-5">
        {data.top_coauthors?.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-3">Top Co-authors</div>
            <div className="space-y-2">
              {data.top_coauthors.slice(0, 8).map((c) => (
                <div key={c.name} className="flex items-center justify-between text-sm">
                  <span className="text-slate-700 truncate flex-1">{c.name}</span>
                  <span className="font-mono text-xs text-slate-500 shrink-0">
                    {c.count} pub{c.count !== 1 ? "s" : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.top_institutions?.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-3">Partner Institutions</div>
            <div className="space-y-2">
              {data.top_institutions.slice(0, 8).map((i) => (
                <div key={i.institution} className="flex items-center justify-between text-sm">
                  <span className="text-slate-700 truncate flex-1">{i.institution}</span>
                  <span className="font-mono text-xs text-slate-500 shrink-0">{i.count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {data.country_distribution?.length > 0 && (
        <div className="border border-slate-200 bg-white p-5">
          <div className="overline mb-3">Country Distribution</div>
          <div className="flex flex-wrap gap-2">
            {data.country_distribution.map((c) => (
              <div
                key={c.country}
                className="border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700"
              >
                {c.country}
                <span className="font-mono ml-1.5 text-slate-400">{c.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────── citation widgets ─────────────────────────────────

const ALERT_COLORS = {
  new_citation:   "#2563eb",
  milestone:      "#16a34a",
  highly_cited:   "#7c3aed",
  velocity:       "#d97706",
  rapid_growth:   "#dc2626",
  emerging_topic: "#0891b2",
  top_performer:  "#16a34a",
  high_velocity:  "#d97706",
};

function CitationWidgets() {
  const { data, loading } = useCitationDashboard();
  if (loading || !data) return null;

  const total        = data.total_citations  ?? 0;
  const newThisMonth = data.new_this_month   ?? 0;
  const topPub       = (data.publications    || [])[0];
  const alerts       = (data.alerts          || []).slice(0, 5);
  const impactScore  = data.impact_score?.score ?? null;
  const areas        = data.research_areas || [];
  const fastestArea  = areas.find((a) => a.trend === "rising" || a.trend === "growing") || areas[0];

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="overline">Citation Intelligence</h2>
        <Link to="/citations" className="text-xs text-[#0F2847] hover:underline flex items-center gap-1">
          Full tracker <ArrowRight size={10} />
        </Link>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="border border-slate-200 bg-white p-6">
          <div className="flex items-center justify-between">
            <div className="overline">Total Citations</div>
            <BookOpen size={13} strokeWidth={1.5} className="text-slate-300" />
          </div>
          <div className="font-serif text-5xl text-slate-900 mt-3 tracking-tight">{total.toLocaleString()}</div>
        </div>

        <div className="border border-slate-200 bg-white p-6">
          <div className="flex items-center justify-between">
            <div className="overline">New This Month</div>
            <TrendingUp size={13} strokeWidth={1.5} className={newThisMonth > 0 ? "text-green-500" : "text-slate-300"} />
          </div>
          <div className={`font-serif text-5xl mt-3 tracking-tight ${newThisMonth > 0 ? "text-green-600" : "text-slate-900"}`}>
            {newThisMonth > 0 ? `+${newThisMonth}` : "0"}
          </div>
        </div>

        {impactScore != null ? (
          <div className="border border-[#0F2847] bg-white p-6">
            <div className="flex items-center justify-between">
              <div className="overline">Research Impact</div>
              <Zap size={13} strokeWidth={1.5} className="text-[#0F2847]" />
            </div>
            <div className="font-serif text-5xl text-[#0F2847] mt-3 tracking-tight">{impactScore}</div>
            <div className="text-xs text-slate-400 mt-1 font-mono">/ 100</div>
          </div>
        ) : (
          <div className="border border-slate-200 bg-white p-6">
            <div className="overline mb-3">Research Impact</div>
            <div className="text-sm text-slate-400">Sync publications to compute.</div>
          </div>
        )}

        {fastestArea ? (
          <div className="border border-slate-200 bg-white p-6">
            <div className="overline mb-3">Fastest Growing Area</div>
            <div className="text-base font-medium text-slate-900 line-clamp-2">{fastestArea.area}</div>
            <div className="text-xs text-slate-500 mt-1.5 font-mono">
              {fastestArea.total_citations} cit · {fastestArea.growth_rate > 0 ? "+" : ""}{fastestArea.growth_rate}%
            </div>
          </div>
        ) : (
          <div className="border border-slate-200 bg-white p-6">
            <div className="overline mb-3">Fastest Growing Area</div>
            <div className="text-sm text-slate-400">No area data yet.</div>
          </div>
        )}
      </div>

      <div className="grid sm:grid-cols-2 gap-5">
        {topPub && (
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline text-slate-500 mb-3">Most Cited Publication</div>
            <Link
              to={`/citations/${topPub.id}`}
              className="font-medium text-slate-900 text-sm line-clamp-2 hover:text-[#0F2847] transition-colors block mb-2"
            >
              {topPub.title}
            </Link>
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span className="font-mono">{(topPub.citations || 0).toLocaleString()} citations</span>
              {topPub.year && <span>{topPub.year}</span>}
              {topPub.journal && <span className="truncate italic">{topPub.journal}</span>}
            </div>
            <Link to={`/citations/${topPub.id}`} className="mt-3 flex items-center gap-1 text-xs text-[#0F2847] hover:underline">
              View detail <ArrowRight size={10} />
            </Link>
          </div>
        )}

        <div className="border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 overline text-slate-500">
              <Bell size={12} strokeWidth={1.5} />
              Recent Alerts
            </div>
            <Link to="/citations" className="text-xs text-[#0F2847] hover:underline">View all</Link>
          </div>
          {alerts.length > 0 ? (
            <div className="space-y-2">
              {alerts.map((a) => (
                <div key={a.id} className="flex items-start gap-2 py-2 border-b border-slate-100 last:border-0">
                  <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
                    style={{ background: ALERT_COLORS[a.alert_type] || "#64748b" }} />
                  <div className="min-w-0">
                    <div className="text-xs text-slate-700 line-clamp-1">{a.message}</div>
                    <div className="text-xs text-slate-400 mt-0.5 font-mono">
                      {new Date(a.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-slate-400">No recent citation alerts.</div>
          )}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────── research workflow ────────────────────────────────

function WorkflowStat({ icon: Icon, label, value, link, urgent }) {
  return (
    <Link
      to={link}
      className={`border bg-white p-6 hover:border-[#0F2847] transition-colors block ${urgent ? "border-[#0F2847]" : "border-slate-200"}`}
    >
      <div className="flex items-center justify-between">
        <div className="overline">{label}</div>
        <Icon size={14} strokeWidth={1.5} className={urgent ? "text-[#0F2847]" : "text-slate-300"} />
      </div>
      <div className={`font-serif text-5xl mt-3 tracking-tight ${urgent ? "text-[#0F2847]" : "text-slate-900"}`}>
        {value ?? 0}
      </div>
    </Link>
  );
}

function ResearchWorkflowWidgets() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/collaboration-requests/metrics")
      .then((r) => setMetrics(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading || !metrics) return null;

  return (
    <section className="space-y-6">
      <h2 className="overline mb-4">Research Workflow</h2>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <WorkflowStat icon={Send}    label="Pending Requests"      value={metrics.pending_received}         link="/collaboration-requests" urgent={metrics.pending_received > 0} />
        <WorkflowStat icon={Users}   label="Accepted Collaborations" value={metrics.requests_accepted}      link="/collaboration-requests" />
        <WorkflowStat icon={Target}  label="Gap Analyses"          value={metrics.gap_analyses}             link="/research-gap-finder" />
        <WorkflowStat icon={Sparkles} label="AI Recommendations"   value={metrics.total_recommendations}   link="/collaboration-intelligence" />
      </div>

      {(metrics.projects_from_gap > 0 || metrics.projects_from_collab > 0) && (
        <div className="grid sm:grid-cols-2 gap-5">
          <WorkflowStat icon={FolderPlus} label="Projects from Gap Finder"  value={metrics.projects_from_gap}   link="/projects" />
          <WorkflowStat icon={FolderPlus} label="Projects from Collab AI"   value={metrics.projects_from_collab} link="/projects" />
        </div>
      )}

      {(metrics.recent_gap_analyses || []).length > 0 && (
        <div className="border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="overline text-slate-500 flex items-center gap-2">
              <Clock size={12} strokeWidth={1.5} />
              Recent Gap Analyses
            </div>
            <Link to="/research-gap-finder" className="text-xs text-[#0F2847] hover:underline flex items-center gap-1">
              View all <ArrowRight size={10} strokeWidth={1.5} />
            </Link>
          </div>
          <div className="space-y-3">
            {(metrics.recent_gap_analyses || []).map((g) => (
              <div key={g.id} className="flex items-start justify-between gap-4 py-2.5 border-b border-slate-100 last:border-0">
                <div className="min-w-0">
                  <div className="text-sm text-slate-900 font-medium truncate">{g.topic}</div>
                  {(g.keywords || []).length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {(g.keywords || []).slice(0, 3).map((k) => (
                        <span key={k} className="text-xs border border-slate-200 text-slate-500 px-1.5 py-0.5">{k}</span>
                      ))}
                    </div>
                  )}
                </div>
                {g.publication_score > 0 && (
                  <span className="text-xs font-mono text-slate-500 shrink-0">
                    Score: <span className="font-medium text-slate-700">{g.publication_score}</span>
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="border border-slate-200 bg-slate-50 p-5">
        <div className="overline text-slate-500 mb-3">Research Opportunities</div>
        <div className="grid sm:grid-cols-3 gap-3">
          <Link to="/research-gap-finder" className="flex items-center gap-2 border border-slate-200 bg-white px-4 py-3 hover:border-[#0F2847] transition-colors group">
            <Target size={14} strokeWidth={1.5} className="text-slate-400 group-hover:text-[#0F2847]" />
            <span className="text-sm text-slate-700 group-hover:text-[#0F2847]">Find Research Gap</span>
          </Link>
          <Link to="/collaboration-intelligence" className="flex items-center gap-2 border border-slate-200 bg-white px-4 py-3 hover:border-[#0F2847] transition-colors group">
            <Users size={14} strokeWidth={1.5} className="text-slate-400 group-hover:text-[#0F2847]" />
            <span className="text-sm text-slate-700 group-hover:text-[#0F2847]">Find Collaborators</span>
          </Link>
          <Link to="/collaboration-requests" className="flex items-center gap-2 border border-slate-200 bg-white px-4 py-3 hover:border-[#0F2847] transition-colors group">
            <Send size={14} strokeWidth={1.5} className="text-slate-400 group-hover:text-[#0F2847]" />
            <span className="text-sm text-slate-700 group-hover:text-[#0F2847]">
              View Requests
              {metrics.pending_received > 0 && (
                <span className="ml-2 text-[10px] bg-[#0F2847] text-white px-1.5 py-0.5 font-mono">
                  {metrics.pending_received}
                </span>
              )}
            </span>
          </Link>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────── export button ───────────────────────────────────

function ExportMenu() {
  const [open, setOpen] = useState(false);
  const options = [
    { label: "Publications CSV",  report: "publications" },
    { label: "Grants CSV",        report: "grants" },
    { label: "Manuscripts CSV",   report: "manuscripts" },
    { label: "Network CSV",       report: "network" },
    { label: "Summary CSV",       report: "summary" },
  ];
  const download = (report) => {
    setOpen(false);
    window.open(`/api/analytics/export?report=${report}`, "_blank");
  };
  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs border border-slate-200 px-3 py-1.5 hover:border-slate-400 transition-colors"
      >
        <Download size={12} /> Export
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 z-20 bg-white border border-slate-200 shadow-lg min-w-[160px]">
          {options.map((o) => (
            <button
              key={o.report}
              onClick={() => download(o.report)}
              className="block w-full text-left px-4 py-2 text-xs text-slate-700 hover:bg-slate-50"
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────── main page ───────────────────────────────────────

export default function Analytics() {
  const [stats, setStats]   = useState(null);
  const [gated, setGated]   = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/analytics/me")
      .then((r) => setStats(r.data))
      .catch((err) => { if (err?.response?.status === 402) setGated(true); })
      .finally(() => setLoading(false));
  }, []);

  if (gated) return <UpgradeWall />;
  if (loading) return <div className="py-12 flex justify-center"><Spinner size={20} /></div>;
  if (!stats)  return null;

  return (
    <AnalyticsLayout
      data-testid={TID.analyticsDashboard}
      title="Analytics"
      subtitle={
        <>
          Your research activity and impact across Synaptiq — all metrics from real platform data.
          {!stats.has_openalex_data && <span style={{ marginLeft: 8, color: "#B45309", fontFamily: "monospace", fontSize: 11 }}>⚠ Sync ORCID for h-index</span>}
        </>
      }
      nav={<IntelNav current="/analytics" />}
      actions={
        <>
          <ExportMenu />
          <Link to="/research-impact" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none", padding: "8px 14px", border: "1px solid rgba(15,23,42,0.08)", background: "#fff" }}>
            <FileText size={12} strokeWidth={1.5} /> Full Impact
          </Link>
        </>
      }
    >
      <div className="space-y-14">

      {/* ── Research Output ── */}
      <section>
        <SectionHeader
          label="Research Output"
          sub="Publication and citation metrics from live platform data"
          action={
            <Link to="/citations" className="text-xs text-[#0F2847] hover:underline flex items-center gap-1">
              Citation tracker <ArrowRight size={10} />
            </Link>
          }
        />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <Stat label="Publications"  value={stats.publications}  icon={BookOpen}
            sub={stats.has_openalex_data ? "enriched via OpenAlex" : "from platform"} />
          <Stat label="Total Citations" value={(stats.citations || 0).toLocaleString()} icon={TrendingUp} highlight
            sub={stats.has_openalex_data ? "from OpenAlex" : "sum from publications"} />
          <Stat label="h-index"  value={stats.h_index  || "—"} icon={Award}
            sub={stats.i10_index ? `i10-index: ${stats.i10_index}` : undefined} />
          <Stat label="Active Collaborations" value={stats.active_collaborations} icon={Users}
            sub={`${stats.active_projects} projects`} />
        </div>
      </section>

      {/* ── Reputation Scores ── */}
      <section>
        <SectionHeader
          label="Reputation Scores"
          sub={stats.has_reputation_data ? "Computed by SYNAPTIQ reputation engine" : "Sync activity to compute reputation scores"}
          action={
            <Link to="/reputation" className="text-xs text-[#0F2847] hover:underline flex items-center gap-1">
              View badges <ArrowRight size={10} />
            </Link>
          }
        />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <Score label="Collaboration" value={stats.collaboration_score} />
          <Score label="Publication"   value={stats.publication_score} />
          <Score label="Expertise"     value={stats.expertise_score} />
          <Score label="Community"     value={stats.community_score} />
        </div>
        {!stats.has_reputation_data && (
          <p className="text-xs text-slate-400 mt-3 font-mono">
            Scores show 0 until the reputation engine computes them. Publish, collaborate, and engage to generate scores.
          </p>
        )}
      </section>

      {/* ── Career Timeline ── */}
      <section>
        <SectionHeader
          label="Career Timeline"
          sub="Publications, citations, and grants over the years"
        />
        <CareerTimeline />
      </section>

      {/* ── Research Productivity Score ── */}
      <section>
        <SectionHeader
          label="Research Productivity"
          sub="Transparent 7-component score — formula exposed, all inputs from real data"
          action={
            <Link to="/research-impact" className="text-xs text-[#0F2847] hover:underline flex items-center gap-1">
              Full scorecard <ArrowRight size={10} />
            </Link>
          }
        />
        <ProductivityScore />
      </section>

      {/* ── Grant Analytics ── */}
      <section>
        <SectionHeader
          label="Grant Analytics"
          sub="Real grant data from ORCID links and platform applications"
          action={
            <Link to="/grants" className="text-xs text-[#0F2847] hover:underline flex items-center gap-1">
              Manage grants <ArrowRight size={10} />
            </Link>
          }
        />
        <GrantAnalytics />
      </section>

      {/* ── Manuscript Analytics ── */}
      <section>
        <SectionHeader
          label="Manuscript Analytics"
          sub="Submission pipeline — acceptance rates, review cycles, venue distribution"
          action={
            <Link to="/publication-hub" className="text-xs text-[#0F2847] hover:underline flex items-center gap-1">
              Publication Hub <ArrowRight size={10} />
            </Link>
          }
        />
        <ManuscriptAnalytics />
      </section>

      {/* ── Collaboration Network ── */}
      <section>
        <SectionHeader
          label="Collaboration Network"
          sub="Co-author network from publications and accepted collaboration requests"
          action={
            <Link to="/collaboration-requests" className="text-xs text-[#0F2847] hover:underline flex items-center gap-1">
              View requests <ArrowRight size={10} />
            </Link>
          }
        />
        <CollaborationNetwork />
      </section>

      {/* ── Citation Intelligence (existing widgets) ── */}
      <CitationWidgets />

      {/* ── Research Workflow (existing widgets) ── */}
      <ResearchWorkflowWidgets />

      {/* ── Research Intelligence Quick Links ── */}
      <section>
        <h2 className="overline mb-5">Continue in Research Intelligence</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {[
            { to: "/citations",           label: "Citation Tracker"      },
            { to: "/citation-monitoring", label: "Citation Monitoring"   },
            { to: "/research-impact",     label: "Research Impact"       },
            { to: "/reputation",          label: "Reputation Score"      },
            { to: "/verification",        label: "Verification Center"   },
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
    </AnalyticsLayout>
  );
}

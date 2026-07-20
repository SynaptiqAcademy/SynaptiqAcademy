import React, { useState, useEffect } from "react";
import { AnalyticsLayout } from "@/layouts";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  TrendingUp, Users, BookOpen, DollarSign, Award, Target,
  GitBranch, BarChart2, Layers, Activity, AlertCircle,
  GraduationCap, Briefcase, Download, Clock, AlertTriangle,
} from "lucide-react";
import api from "@/lib/api";
import { userTypeLabel } from "@/lib/userTypes";
import { NAVY } from "@/lib/tokens";

const TABS = [
  { id: "executive",       label: "Executive" },
  { id: "research",        label: "Research" },
  { id: "funding",         label: "Funding" },
  { id: "collaboration",   label: "Collaboration" },
  { id: "research-office", label: "Research Office" },
  { id: "doctoral",        label: "Doctoral School" },
];

const PIE_COLORS = ["#0F2847", "#1E4080", "#2A5CB0", "#3B7DD8", "#6FA3E8", "#A0C4F5", "#C8DFFB"];

function fmt(n, decimals = 0) {
  if (n == null) return "—";
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return n >= 10_000 ? `${(n / 1_000).toFixed(0)}k` : `${(n / 1_000).toFixed(1)}k`;
  return n.toLocaleString(undefined, { maximumFractionDigits: decimals });
}

function fmtUSD(n) {
  if (n == null) return "—";
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

function KPI({ label, value, sub, icon: Icon, highlight }) {
  return (
    <div className={`bg-white border p-5 ${highlight ? "border-[#0F2847]" : "border-slate-200"}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">{label}</span>
        {Icon && <Icon size={14} className="text-slate-300" strokeWidth={1.5} />}
      </div>
      <div className={`font-serif text-4xl tracking-tight ${highlight ? "text-[#0F2847]" : "text-slate-900"}`}>
        {value ?? "—"}
      </div>
      {sub && <div className="text-xs text-slate-500 mt-1.5">{sub}</div>}
    </div>
  );
}

function Card({ title, children, className = "" }) {
  return (
    <div className={`bg-white border border-slate-200 ${className}`}>
      {title && (
        <div className="px-5 py-3.5 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

function Skeleton({ rows = 4, height = "h-10" }) {
  return (
    <div className="space-y-2 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className={`${height} animate-pulse bg-slate-100`} />
      ))}
    </div>
  );
}

function GatedBanner() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <AlertCircle size={36} className="text-slate-300 mb-4" strokeWidth={1.5} />
      <h2 className="font-serif text-2xl text-slate-700 mb-2">Institutional Plan Required</h2>
      <p className="text-sm text-slate-500 max-w-sm">
        Institutional Analytics is available on Institution, Institution Pro, and Institution Enterprise plans.
        Contact your administrator to upgrade.
      </p>
    </div>
  );
}

function NoAffiliation() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <Users size={36} className="text-slate-300 mb-4" strokeWidth={1.5} />
      <h2 className="font-serif text-2xl text-slate-700 mb-2">No Institutional Affiliation</h2>
      <p className="text-sm text-slate-500 max-w-sm">
        You must be an approved member of an institution to access Institutional Analytics.
      </p>
    </div>
  );
}

function ScoreGauge({ score }) {
  const color = score >= 70 ? "#16a34a" : score >= 40 ? "#ca8a04" : "#dc2626";
  const data = [{ value: score }, { value: 100 - score }];
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-32 h-32">
        <PieChart width={128} height={128}>
          <Pie
            data={data}
            cx={60}
            cy={60}
            startAngle={90}
            endAngle={-270}
            innerRadius={44}
            outerRadius={60}
            dataKey="value"
            strokeWidth={0}
          >
            <Cell fill={color} />
            <Cell fill="#f1f5f9" />
          </Pie>
        </PieChart>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-serif text-2xl text-slate-900">{score}</span>
          <span className="text-xs text-slate-400">/100</span>
        </div>
      </div>
      <span className="text-sm font-medium mt-1" style={{ color }}>
        {score >= 70 ? "Strong" : score >= 40 ? "Developing" : "Early Stage"}
      </span>
    </div>
  );
}

// ─── Executive Dashboard ──────────────────────────────────────────────────────

function ExecutiveTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/institutional/analytics/executive")
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton rows={6} height="h-16" />;
  if (error?.includes("affiliation")) return <NoAffiliation />;
  if (error?.includes("plan") || error?.includes("402")) return <GatedBanner />;
  if (error) return <div className="p-6 text-sm text-red-700 bg-red-50 border border-red-200">{error}</div>;
  if (!data) return null;

  const { overview, publication_trend, research_areas, department_comparison,
    impact_score, institutional_h_index, grant_success_rate, top_researchers } = data;

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPI label="Researchers" value={fmt(overview?.researchers)} icon={Users} highlight />
        <KPI label="Publications" value={fmt(overview?.publications?.total)} icon={BookOpen} />
        <KPI label="Total Citations" value={fmt(overview?.citations_total)} icon={TrendingUp} />
        <KPI label="Institutional h-index" value={institutional_h_index} icon={Award} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPI label="Total Funding" value={fmtUSD(overview?.grants?.awarded_usd)} icon={DollarSign} />
        <KPI label="Active Grants" value={fmt(overview?.grants?.awarded)} icon={Target} />
        <KPI label="Grant Success Rate" value={`${grant_success_rate}%`} icon={BarChart2} />
        <KPI label="Avg Reputation" value={overview?.reputation?.average?.toFixed(1)} icon={Activity} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Publication trend */}
        <Card title="Publication Output by Year" className="lg:col-span-2">
          {publication_trend?.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={publication_trend} margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="pubGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0F2847" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#0F2847" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Area type="monotone" dataKey="n" name="Publications" stroke="#0F2847" fill="url(#pubGrad)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">No publication data yet</p>
          )}
        </Card>

        {/* Impact score gauge */}
        <Card title="Research Health Score">
          <div className="flex flex-col items-center">
            <ScoreGauge score={impact_score?.score ?? 0} />
            <div className="mt-4 w-full space-y-2">
              {[
                { label: "Publications", val: impact_score?.publications_component },
                { label: "Grants", val: impact_score?.grants_component },
                { label: "Funding", val: impact_score?.funding_usd_component },
                { label: "Reputation", val: impact_score?.reputation_component },
              ].map(({ label, val }) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 w-24 flex-shrink-0">{label}</span>
                  <div className="flex-1 h-1.5 bg-slate-100">
                    <div className="h-1.5 bg-[#0F2847]" style={{ width: `${Math.min(100, val ?? 0)}%` }} />
                  </div>
                  <span className="text-xs text-slate-400 w-8 text-right">{(val ?? 0).toFixed(0)}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Research areas */}
        <Card title="Research Area Distribution">
          {research_areas?.length > 0 ? (
            <div className="flex gap-4">
              <div className="flex-1">
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie data={research_areas.slice(0, 7)} dataKey="n" nameKey="area" cx="50%" cy="50%" outerRadius={70} strokeWidth={0}>
                      {research_areas.slice(0, 7).map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                    </Pie>
                    <Tooltip formatter={(v, n) => [v, n]} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-col justify-center gap-1.5 min-w-0">
                {research_areas.slice(0, 7).map((a, i) => (
                  <div key={a.area} className="flex items-center gap-1.5 text-xs">
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                    <span className="text-slate-600 truncate">{a.area}</span>
                    <span className="text-slate-400 ml-auto pl-2">{a.n}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">No research area data yet</p>
          )}
        </Card>

        {/* Department comparison */}
        <Card title="Department Output Comparison">
          {department_comparison?.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={department_comparison.slice(0, 8)} layout="vertical" margin={{ left: 0, right: 16 }}>
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={100} />
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <Tooltip />
                <Bar dataKey="n" name="Publications" fill="#0F2847" radius={[0, 2, 2, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">No department data yet</p>
          )}
        </Card>
      </div>

      {/* Top researchers */}
      {top_researchers?.length > 0 && (
        <Card title="Top Researchers by Reputation">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                {["Researcher", "Role", "Overall", "Publications", "Funding"].map((h) => (
                  <th key={h} className="text-left pb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {top_researchers.map((r, i) => (
                <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-2.5 font-medium text-slate-900">{r.user?.full_name || "—"}</td>
                  <td className="py-2.5 text-slate-500 text-xs">{userTypeLabel(r.user) || "—"}</td>
                  <td className="py-2.5 text-[#0F2847] font-semibold">{r.overall?.toFixed(1) ?? "—"}</td>
                  <td className="py-2.5 text-slate-600">{r.publication?.toFixed(1) ?? "—"}</td>
                  <td className="py-2.5 text-slate-600">{r.funding?.toFixed(1) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

// ─── Research Dashboard ───────────────────────────────────────────────────────

function ResearchTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/institutional/analytics/research")
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton rows={6} height="h-16" />;
  if (error?.includes("affiliation")) return <NoAffiliation />;
  if (error?.includes("plan") || error?.includes("402")) return <GatedBanner />;
  if (error) return <div className="p-6 text-sm text-red-700 bg-red-50 border border-red-200">{error}</div>;
  if (!data) return null;

  const { publication_trend, research_areas, citation_trend, faculty_productivity, top_publications, by_unit } = data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Publication trend */}
        <Card title="Publication Trend by Year">
          {publication_trend?.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={publication_trend}>
                <defs>
                  <linearGradient id="pubGrad2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0F2847" stopOpacity={0.12} />
                    <stop offset="95%" stopColor="#0F2847" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Area type="monotone" dataKey="n" name="Publications" stroke="#0F2847" fill="url(#pubGrad2)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">No data yet</p>
          )}
        </Card>

        {/* Citation growth */}
        <Card title="Citation Growth">
          {citation_trend?.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={citation_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="citations" name="Citations" stroke="#1E4080" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">No citation data yet</p>
          )}
        </Card>
      </div>

      {/* Research area distribution */}
      {research_areas?.length > 0 && (
        <Card title="Research Area Distribution">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={research_areas.slice(0, 12)} margin={{ left: 0, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="area" tick={{ fontSize: 10 }} angle={-25} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="n" name="Researchers" fill="#0F2847" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Faculty productivity */}
      {faculty_productivity?.length > 0 && (
        <Card title="Faculty Productivity">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                {["Researcher", "Role", "Publications", "Citations", "h-index"].map((h) => (
                  <th key={h} className="text-left pb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {faculty_productivity.map((f, i) => (
                <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-2.5 font-medium text-slate-900">{f.name || "—"}</td>
                  <td className="py-2.5 text-slate-500 text-xs">{f.role || "—"}</td>
                  <td className="py-2.5 text-[#0F2847] font-semibold">{f.publications}</td>
                  <td className="py-2.5 text-slate-700">{fmt(f.citations)}</td>
                  <td className="py-2.5 text-slate-700">{f.h_index}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Top publications */}
      {top_publications?.length > 0 && (
        <Card title="Top Publications by Citations">
          <div className="space-y-3">
            {top_publications.map((p, i) => (
              <div key={p.id || i} className="flex items-start gap-3 py-2 border-b border-slate-50 last:border-0">
                <span className="text-xs font-mono text-slate-300 w-5 flex-shrink-0 pt-0.5">{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-800 font-medium truncate">{p.title || "Untitled"}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{p.journal || ""}{p.published_at ? ` · ${p.published_at.slice(0, 4)}` : ""}</p>
                </div>
                <span className="text-sm font-semibold text-[#0F2847] flex-shrink-0">{fmt(p.citations)} <span className="text-xs font-normal text-slate-400">cit.</span></span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ─── Funding Dashboard ────────────────────────────────────────────────────────

function FundingTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/institutional/analytics/funding")
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton rows={5} height="h-16" />;
  if (error?.includes("affiliation")) return <NoAffiliation />;
  if (error?.includes("plan") || error?.includes("402")) return <GatedBanner />;
  if (error) return <div className="p-6 text-sm text-red-700 bg-red-50 border border-red-200">{error}</div>;
  if (!data) return null;

  const { summary, by_status, by_department, trend } = data;

  const statusColors = { awarded: "#16a34a", pending: "#ca8a04", rejected: "#dc2626", submitted: "#2563eb" };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPI label="Total Awarded" value={fmtUSD(summary?.total_usd)} icon={DollarSign} highlight />
        <KPI label="Awarded Grants" value={fmt(summary?.awarded_grants)} icon={Award} />
        <KPI label="Total Applications" value={fmt(summary?.total_grants)} icon={BookOpen} />
        <KPI label="Success Rate" value={`${summary?.grant_success_rate ?? 0}%`} icon={Target} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Funding trend */}
        <Card title="Funding Awarded by Year">
          {trend?.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={trend}>
                <defs>
                  <linearGradient id="fundGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#16a34a" stopOpacity={0.12} />
                    <stop offset="95%" stopColor="#16a34a" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => fmtUSD(v)} tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v) => [fmtUSD(v), "Awarded"]} />
                <Area type="monotone" dataKey="total_usd" name="Awarded" stroke="#16a34a" fill="url(#fundGrad)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">No funding trend data yet</p>
          )}
        </Card>

        {/* Grant status breakdown */}
        <Card title="Grant Applications by Status">
          {by_status?.length > 0 ? (
            <div className="space-y-3 py-2">
              {by_status.map((s) => (
                <div key={s.status} className="flex items-center gap-3">
                  <span
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ background: statusColors[s.status] || "#94a3b8" }}
                  />
                  <span className="text-sm text-slate-700 capitalize flex-1">{s.status}</span>
                  <span className="text-sm font-semibold text-slate-900">{s.n}</span>
                  <span className="text-xs text-slate-400 w-20 text-right">{fmtUSD(s.usd)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">No grant data yet</p>
          )}
        </Card>
      </div>

      {/* Department funding */}
      {by_department?.length > 0 && (
        <Card title="Funding by Department">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={by_department.slice(0, 10)} layout="vertical" margin={{ left: 0, right: 60 }}>
              <XAxis type="number" tickFormatter={(v) => fmtUSD(v)} tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={120} />
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <Tooltip formatter={(v) => [fmtUSD(v), "Awarded"]} />
              <Bar dataKey="awarded_usd" name="Awarded" fill="#0F2847" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}

// ─── Collaboration Dashboard ──────────────────────────────────────────────────

function CollaborationTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/institutional/analytics/collaboration")
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton rows={5} height="h-16" />;
  if (error?.includes("affiliation")) return <NoAffiliation />;
  if (error?.includes("plan") || error?.includes("402")) return <GatedBanner />;
  if (error) return <div className="p-6 text-sm text-red-700 bg-red-50 border border-red-200">{error}</div>;
  if (!data) return null;

  const { summary, network, trend, top_collaborators } = data;

  const internalRatio = summary?.total
    ? Math.round((summary.internal_collaborations / summary.total) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <KPI label="Total Collaborations" value={fmt(summary?.total)} icon={GitBranch} highlight />
        <KPI label="Internal" value={fmt(summary?.internal_collaborations)} sub={`${internalRatio}% of total`} icon={Users} />
        <KPI label="External" value={fmt(summary?.external_collaborations)} sub={`${100 - internalRatio}% of total`} icon={Layers} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Collaboration trend */}
        <Card title="Collaboration Trend (Manuscripts)">
          {trend?.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="n" name="Manuscripts" stroke="#0F2847" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">No trend data yet</p>
          )}
        </Card>

        {/* Internal vs external donut */}
        <Card title="Internal vs External">
          {summary?.total > 0 ? (
            <div className="flex items-center gap-6">
              <PieChart width={160} height={160}>
                <Pie
                  data={[
                    { name: "Internal", value: summary.internal_collaborations },
                    { name: "External", value: summary.external_collaborations },
                  ]}
                  cx={76}
                  cy={76}
                  innerRadius={48}
                  outerRadius={70}
                  dataKey="value"
                  strokeWidth={0}
                >
                  <Cell fill="#0F2847" />
                  <Cell fill="#A0C4F5" />
                </Pie>
                <Tooltip />
              </PieChart>
              <div className="space-y-3">
                {[
                  { label: "Internal", n: summary.internal_collaborations, color: "#0F2847" },
                  { label: "External", n: summary.external_collaborations, color: "#A0C4F5" },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: item.color }} />
                    <span className="text-sm text-slate-600">{item.label}</span>
                    <span className="text-sm font-semibold text-slate-900 ml-2">{item.n}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">No collaboration data yet</p>
          )}
        </Card>
      </div>

      {/* Top collaborators */}
      {top_collaborators?.length > 0 && (
        <Card title="Most Active Collaborators">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                {["Researcher", "Co-authored Publications"].map((h) => (
                  <th key={h} className="text-left pb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {top_collaborators.map((f, i) => (
                <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-2.5 font-medium text-slate-900">{f.name || "—"}</td>
                  <td className="py-2.5 text-[#0F2847] font-semibold">{f.publications}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Network sample */}
      {network?.length > 0 && (
        <Card title="Collaboration Network (top co-author pairs)">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                {["Researcher A", "Researcher B", "Joint Papers"].map((h) => (
                  <th key={h} className="text-left pb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {network.slice(0, 15).map((edge, i) => (
                <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-2.5 text-slate-700">{edge.source_name || edge.source}</td>
                  <td className="py-2.5 text-slate-700">{edge.target_name || edge.target}</td>
                  <td className="py-2.5 text-[#0F2847] font-semibold">{edge.weight}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

// ─── Research Office Tab ──────────────────────────────────────────────────────

const APP_STATUS_COLORS = {
  draft: "#94a3b8", in_preparation: "#6366f1", internal_review: "#8b5cf6",
  ready_for_submission: "#f59e0b", submitted: "#3b82f6", eligible: "#06b6d4",
  under_evaluation: "#0ea5e9", funded: "#16a34a", rejected: "#dc2626",
  closed: "#9ca3af", withdrawn: "#d1d5db",
};

function ResearchOfficeTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/institutional/analytics/research-office")
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton rows={5} height="h-16" />;
  if (error?.includes("affiliation")) return <NoAffiliation />;
  if (error?.includes("plan") || error?.includes("402")) return <GatedBanner />;
  if (error) return <div className="p-6 text-sm text-red-700 bg-red-50 border border-red-200">{error}</div>;
  if (!data) return null;

  const { summary, pipeline, upcoming_deadlines, top_pis, overloaded_pis } = data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <KPI label="Total Applications" value={fmt(summary?.total_applications)} icon={Target} highlight />
        <KPI label="Active PIs" value={fmt(summary?.active_pis)} icon={Users} />
        <KPI label="Committed Budget" value={fmtUSD(summary?.committed_budget_usd)} icon={DollarSign} />
        <KPI label="Funded Budget" value={fmtUSD(summary?.funded_budget_usd)} icon={Award} />
        <KPI label="Success Rate" value={`${summary?.success_rate ?? 0}%`} icon={TrendingUp} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Application pipeline */}
        <Card title="Application Pipeline by Status">
          {pipeline?.length > 0 ? (
            <div className="space-y-2">
              {pipeline.map((p) => (
                <div key={p.status} className="flex items-center gap-3">
                  <span className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ background: APP_STATUS_COLORS[p.status] || "#94a3b8" }} />
                  <span className="text-sm text-slate-700 flex-1 capitalize">
                    {p.status.replace(/_/g, " ")}
                  </span>
                  <span className="text-sm font-semibold text-slate-900 w-8 text-right">{p.n}</span>
                  <span className="text-xs text-slate-400 w-20 text-right">{fmtUSD(p.budget_usd)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">No grant applications yet</p>
          )}
        </Card>

        {/* Upcoming deadlines */}
        <Card title="Upcoming Grant Deadlines">
          {upcoming_deadlines?.length > 0 ? (
            <div className="space-y-3">
              {upcoming_deadlines.map((d, i) => {
                const daysLeft = d.deadline
                  ? Math.ceil((new Date(d.deadline) - new Date()) / 86400000)
                  : null;
                const urgent = daysLeft != null && daysLeft <= 14;
                return (
                  <div key={i} className="flex items-start gap-3 py-2 border-b border-slate-50 last:border-0">
                    {urgent
                      ? <AlertTriangle size={14} className="text-amber-500 flex-shrink-0 mt-0.5" strokeWidth={1.5} />
                      : <Clock size={14} className="text-slate-300 flex-shrink-0 mt-0.5" strokeWidth={1.5} />
                    }
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-800 font-medium truncate">{d.title || "Grant"}</p>
                      <p className="text-xs text-slate-400">{d.sponsor}</p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className={`text-xs font-mono ${urgent ? "text-amber-600" : "text-slate-500"}`}>
                        {d.deadline}
                      </div>
                      {daysLeft != null && (
                        <div className={`text-xs ${urgent ? "text-amber-500 font-semibold" : "text-slate-400"}`}>
                          {daysLeft}d left
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">No upcoming deadlines</p>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top funded PIs */}
        {top_pis?.length > 0 && (
          <Card title="Top PIs by Funded Amount">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {["Principal Investigator", "Funded (USD)"].map((h) => (
                    <th key={h} className="text-left pb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {top_pis.map((pi, i) => (
                  <tr key={i} className="border-b border-slate-50">
                    <td className="py-2.5 font-medium text-slate-900">{pi.name || pi.pi_id}</td>
                    <td className="py-2.5 text-[#0F2847] font-semibold">{fmtUSD(pi.funded_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}

        {/* Overloaded PIs */}
        {overloaded_pis?.length > 0 && (
          <Card title="High-Load PIs (3+ active applications)">
            <div className="space-y-2">
              {overloaded_pis.map((pi, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 border-b border-slate-50 last:border-0">
                  <span className="text-sm text-slate-700 font-mono">{pi.pi_id.slice(-8)}</span>
                  <span className="text-sm font-semibold text-amber-600">{pi.active_apps} apps</span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}


// ─── Doctoral School Tab ──────────────────────────────────────────────────────

function DoctoralTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/institutional/analytics/doctoral")
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton rows={5} height="h-16" />;
  if (error?.includes("affiliation")) return <NoAffiliation />;
  if (error?.includes("plan") || error?.includes("402")) return <GatedBanner />;
  if (error) return <div className="p-6 text-sm text-red-700 bg-red-50 border border-red-200">{error}</div>;
  if (!data) return null;

  const { total_phd_students, total_supervisors, manuscripts_active, manuscripts_completed,
          completion_rate, supervision_coverage, by_department, student_profiles } = data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <KPI label="PhD Students" value={fmt(total_phd_students)} icon={GraduationCap} highlight />
        <KPI label="Supervisors" value={fmt(total_supervisors)} icon={Users} />
        <KPI label="Supervision Coverage" value={`${supervision_coverage ?? 0}%`} icon={Briefcase} />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <KPI label="Active Theses" value={fmt(manuscripts_active)} icon={BookOpen}
             sub="Manuscripts in progress" />
        <KPI label="Completed Works" value={fmt(manuscripts_completed)} icon={Award}
             sub="Published manuscripts" />
        <KPI label="Completion Rate" value={`${completion_rate ?? 0}%`} icon={TrendingUp}
             sub="Published / Total" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* PhD by department */}
        {by_department?.length > 0 && (
          <Card title="PhD Students by Department">
            <div className="space-y-2">
              {by_department.slice(0, 10).map((d, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-xs text-slate-400 w-4 flex-shrink-0">{i + 1}</span>
                  <span className="text-sm text-slate-700 flex-1 truncate">{d.department}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-1.5 bg-slate-100">
                      <div className="h-1.5 bg-[#0F2847]"
                           style={{ width: `${(d.phd_students / (by_department[0]?.phd_students || 1)) * 100}%` }} />
                    </div>
                    <span className="text-sm font-semibold text-slate-900 w-6">{d.phd_students}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Thesis progress gauge */}
        <Card title="Thesis Progress Overview">
          {(manuscripts_active + manuscripts_completed) > 0 ? (
            <div className="space-y-4">
              <div className="flex items-center justify-center">
                <PieChart width={160} height={160}>
                  <Pie
                    data={[
                      { name: "Active", value: manuscripts_active },
                      { name: "Completed", value: manuscripts_completed },
                    ]}
                    cx={76} cy={76} innerRadius={44} outerRadius={68}
                    dataKey="value" strokeWidth={0}
                  >
                    <Cell fill="#3b82f6" />
                    <Cell fill="#16a34a" />
                  </Pie>
                  <Tooltip />
                </PieChart>
              </div>
              <div className="flex justify-center gap-8">
                {[
                  { label: "Active", n: manuscripts_active, color: "#3b82f6" },
                  { label: "Completed", n: manuscripts_completed, color: "#16a34a" },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ background: item.color }} />
                    <span className="text-sm text-slate-600">{item.label}</span>
                    <span className="text-sm font-semibold text-slate-900">{item.n}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400 text-center py-8">No manuscript data yet</p>
          )}
        </Card>
      </div>

      {/* Student profiles */}
      {student_profiles?.length > 0 && (
        <Card title="PhD Student Profiles">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                {["Student", "Research Areas", "Active Work", "Published", "Supervisors"].map((h) => (
                  <th key={h} className="text-left pb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {student_profiles.map((s, i) => (
                <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-2.5 font-medium text-slate-900">{s.name || "—"}</td>
                  <td className="py-2.5 text-slate-500 text-xs">
                    {(s.research_areas || []).slice(0, 2).join(", ") || "—"}
                  </td>
                  <td className="py-2.5 text-[#0F2847] font-semibold">{s.manuscripts_active}</td>
                  <td className="py-2.5 text-slate-600">{s.manuscripts_published}</td>
                  <td className="py-2.5 text-slate-500 text-xs">
                    {(s.supervisor_names || []).join(", ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {total_phd_students === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <GraduationCap size={36} className="text-slate-200 mb-4" strokeWidth={1.5} />
          <h3 className="font-serif text-xl text-slate-600 mb-2">No Doctoral Students Found</h3>
          <p className="text-sm text-slate-400 max-w-sm">
            PhD students are identified by their academic role. Ensure institution members have
            set their role to "PhD Student" or "Doctoral Researcher" in their profile.
          </p>
        </div>
      )}
    </div>
  );
}


// ─── Main page ────────────────────────────────────────────────────────────────

const EXPORT_OPTIONS = [
  { value: "researchers", label: "Researchers Report" },
  { value: "publications", label: "Publications Report" },
  { value: "funding", label: "Funding Report" },
  { value: "departments", label: "Departments Ranking" },
];

function ExportButton() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const doExport = async (type) => {
    setLoading(true);
    setOpen(false);
    try {
      const resp = await api.get(`/institutional/analytics/export?report_type=${type}`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(new Blob([resp.data], { type: "text/csv" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `synaptiq_${type}_report.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Export failed — please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={loading}
        className="inline-flex items-center gap-2 text-xs border border-slate-300 text-slate-600 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors disabled:opacity-50"
      >
        <Download size={12} strokeWidth={1.5} />
        {loading ? "Exporting…" : "Export CSV"}
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-slate-200 shadow-lg z-10">
          {EXPORT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => doExport(opt.value)}
              className="w-full text-left px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
            >
              <BookOpen size={12} strokeWidth={1.5} className="text-slate-400" />
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function InstitutionAnalytics() {
  const [activeTab, setActiveTab] = useState("executive");

  const tabBar = (
    <div className="flex border-b border-slate-200 overflow-x-auto">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id)}
          className={`px-5 py-3 text-sm font-medium transition-colors whitespace-nowrap ${
            activeTab === tab.id
              ? "border-b-2 border-[#0F2847] text-[#0F2847]"
              : "text-slate-500 hover:text-slate-800"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );

  return (
    <AnalyticsLayout
      title="Institutional Analytics"
      subtitle="Executive-level research performance and impact insights for your institution."
      icon={<BarChart2 size={18} strokeWidth={1.5} />}
      actions={<ExportButton />}
      nav={tabBar}
    >
      {activeTab === "executive"       && <ExecutiveTab />}
      {activeTab === "research"        && <ResearchTab />}
      {activeTab === "funding"         && <FundingTab />}
      {activeTab === "collaboration"   && <CollaborationTab />}
      {activeTab === "research-office" && <ResearchOfficeTab />}
      {activeTab === "doctoral"        && <DoctoralTab />}
    </AnalyticsLayout>
  );
}

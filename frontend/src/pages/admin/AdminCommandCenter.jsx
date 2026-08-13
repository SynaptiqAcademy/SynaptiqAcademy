/* eslint-disable */
import React, { useState, useEffect, useCallback, useMemo } from "react";
import { toast } from "sonner";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  Users, TrendingUp, DollarSign, Activity, UserCheck, Link2, BookOpen,
  FlaskConical, RefreshCw, Download, AlertCircle, AlertTriangle,
  Sparkles, LifeBuoy, Network, HeartPulse, Zap, Gauge, CheckCircle2,
} from "lucide-react";
import api from "@/lib/api";
import { INFO, EMERALD, AMBER, CRIMSON, VIOLET, TEXT_MUTED, BRD, BRD_SOFT, WHITE } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { useAdminRealtime } from "@/contexts/AdminRealtimeContext";
import {
  Button, Card, StatCard, Badge, MiniBar, FormSelect, Input, Alert,
  Dropdown, DropdownItem,
} from "@/components/ds";

function useAOS(path, params = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const query = new URLSearchParams(params).toString();
  const fetch = useCallback(() => {
    setLoading(true);
    api.get(`/admin/aos/${path}${query ? "?" + query : ""}`)
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [path, query]);
  useEffect(() => { fetch(); }, [fetch]);
  return { data, loading, refetch: fetch };
}

/** Fetch a plain /admin/* endpoint outside the /admin/aos/* prefix. */
function useAdminEndpoint(path) {
  const [data, setData] = useState(null);
  const fetch = useCallback(() => {
    api.get(path).then((r) => setData(r.data)).catch(() => setData(null));
  }, [path]);
  useEffect(() => { fetch(); }, [fetch]);
  return { data, refetch: fetch };
}

const KPI_COLORS = { blue: INFO, green: EMERALD, yellow: AMBER, red: CRIMSON, purple: VIOLET };

function KpiCard({ icon: Icon, label, value, sub, color = "blue" }) {
  const c = KPI_COLORS[color] || KPI_COLORS.blue;
  return (
    <StatCard
      label={label}
      value={value ?? "—"}
      sub={sub}
      icon={Icon ? <Icon style={{ color: c }} /> : undefined}
    />
  );
}

/** Command Center section — a focused, titled zone of the control room. */
function MCSection({ icon: Icon, title, action, children }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-slate-500">
          {Icon && <Icon size={12} />} {title}
        </h2>
        {action}
      </div>
      {children}
    </div>
  );
}

const STATUS_VARIANT = { healthy: "success", degraded: "warning", unhealthy: "danger" };
const COMPONENT_LABEL = {
  mongodb: "Database", redis: "Cache (Redis)", worker_queue: "Worker Queue",
  scheduler: "Scheduler", workers: "Background Workers", event_bus: "Event Bus",
  ai_gateway: "AI Gateway", llm_providers: "LLM Providers", knowledge_graph: "Knowledge Graph",
  digital_twin: "Digital Twin", storage: "File Storage", api: "API",
};

function StatusPill({ status }) {
  return <Badge variant={STATUS_VARIANT[status] || "neutral"}>{status || "unknown"}</Badge>;
}

const CHART_BLUE = INFO;
const CHART_GREEN = EMERALD;
const CHART_PURPLE = VIOLET;
const CHART_RED = CRIMSON;

const SEVERITY_ALERT_VARIANT = { high: "error", medium: "warning", low: "info" };

export default function AdminCommandCenter() {
  const [days, setDays] = useState(30);
  const [country, setCountry] = useState("");
  const [academicRole, setAcademicRole] = useState("");

  const params = { days };
  if (country) params.country = country;
  if (academicRole) params.academic_role = academicRole;

  const { data, loading, refetch } = useAOS("dashboard", params);
  const { data: ts, loading: tsLoading } = useAOS("timeseries", { days: Math.min(days, 90) });
  const { data: health } = useAOS("health/infrastructure");
  const { data: errorStats } = useAOS("errors/stats");
  const { data: revenue } = useAOS("revenue/metrics");
  const { data: research } = useAOS("research/overview");
  const { data: community } = useAOS("community/stats");
  const [impact, setImpact] = useState(null);
  useEffect(() => { api.get("/admin/impact/stats").then((r) => setImpact(r.data)).catch(() => setImpact(null)); }, []);

  const { data: aiStats } = useAdminEndpoint("/admin/ai/stats");
  const { data: securityEvents } = useAdminEndpoint("/admin/security/events");
  const { data: failedLogins } = useAdminEndpoint("/admin/security/failed-logins");
  const { data: supportStats } = useAdminEndpoint("/admin/x/support/stats");
  const { data: opsHealth, refetch: refetchHealth } = useAdminEndpoint("/ops/health");

  // Real traffic & performance — from the api_stats collection populated by
  // the request-logging middleware (backend/middleware/api_monitor.py).
  // This is the only genuine "what do users actually use" / "how fast is it"
  // signal in the platform today — page-view/session tracking is not wired
  // up anywhere, so we don't fabricate a "traffic" number from nothing.
  const apiDays = Math.min(days, 90);
  const { data: apiMonitor, refetch: refetchApiMonitor } = useAdminEndpoint(`/admin/x/api-monitor/overview?days=${apiDays}`);
  const { data: apiAlerts, refetch: refetchApiAlerts } = useAdminEndpoint("/admin/x/api-monitor/alerts");

  // Live updates: refetch the dashboard/timeseries whenever a curated domain
  // event arrives on the Admin OS WebSocket channel, instead of relying on
  // manual refresh or a poll interval.
  const { lastEvent } = useAdminRealtime();
  useEffect(() => {
    if (!lastEvent) return;
    refetch();
    const label = {
      user_registered: "New user registered",
      payment_received: "Payment received",
      security_event: `Security event: ${lastEvent.event_type || ""}`,
      job_failed: `Background job failed (${lastEvent.scope || "unknown"})`,
      domain_event: `${lastEvent.event_type || "Event"}`,
    }[lastEvent.type] || lastEvent.type;
    toast.info(label, { duration: 4000 });
  }, [lastEvent, refetch]);

  const u = data?.users || {};
  const a = data?.activity || {};
  const f = data?.financial || {};

  const handleExport = (report) => {
    window.open(`/api/admin/aos/export?report=${report}`, "_blank");
  };

  const handleRefreshAll = () => {
    refetch();
    refetchHealth();
    refetchApiMonitor();
    refetchApiAlerts();
  };

  // ── "Needs Attention" — every real signal that something needs a human,
  // merged into one ranked list instead of scattered across five sections.
  // Nothing here is invented: unhealthy components come straight from
  // /ops/health's real checks, alerts from the api_stats anomaly detector,
  // errors from error_logs, security from real audit_log queries.
  const attentionItems = useMemo(() => {
    const items = [];
    const components = opsHealth?.components || {};
    Object.entries(components).forEach(([name, c]) => {
      if (c.status === "unhealthy") {
        items.push({ severity: "high", title: COMPONENT_LABEL[name] || name, message: c.message || "Unhealthy" });
      } else if (c.status === "degraded") {
        items.push({ severity: "medium", title: COMPONENT_LABEL[name] || name, message: c.message || "Degraded" });
      }
    });
    (apiAlerts?.alerts || []).forEach((al) => {
      items.push({ severity: al.severity === "high" ? "high" : "medium", title: "Traffic / API", message: al.message });
    });
    if (errorStats?.critical > 0) {
      items.push({ severity: "high", title: "Critical errors", message: `${errorStats.critical} unresolved critical error${errorStats.critical !== 1 ? "s" : ""} logged` });
    }
    if ((failedLogins?.items?.length || 0) > 0) {
      const top = failedLogins.items[0];
      items.push({ severity: "medium", title: "Failed logins", message: `${failedLogins.items.length} distinct IPs with failed attempts in the last 24h (top: ${top?.count ?? "?"} attempts)` });
    }
    if ((securityEvents?.items?.length || 0) > 0) {
      items.push({ severity: "low", title: "Security events", message: `${securityEvents.items.length} security event${securityEvents.items.length !== 1 ? "s" : ""} recorded recently — review the Security page` });
    }
    if ((supportStats?.open || 0) > 0 && supportStats?.avg_resolution_hours > 48) {
      items.push({ severity: "low", title: "Support backlog", message: `${supportStats.open} open tickets, averaging ${supportStats.avg_resolution_hours}h to resolve` });
    }
    const order = { high: 0, medium: 1, low: 2 };
    return items.sort((x, y) => order[x.severity] - order[y.severity]);
  }, [opsHealth, apiAlerts, errorStats, failedLogins, securityEvents, supportStats]);

  const componentEntries = Object.entries(opsHealth?.components || {});

  return (
    <AdministrationLayout
      title="Mission Control"
      subtitle="The single place to operate Synaptiq — what needs attention, real traffic, real performance."
      stats={[
        { label: "Total Users",  value: u.total?.toLocaleString() ?? "—" },
        { label: "Online Now",   value: u.online_now?.toLocaleString() ?? "—" },
        { label: "Requests / period", value: apiMonitor?.total_requests?.toLocaleString() ?? "—" },
        { label: "Errors (24h)", value: health?.errors_24h ?? "—" },
      ]}
      ring={apiMonitor ? {
        value: apiMonitor.health_score ?? 0,
        label: "API Health",
        color: (apiMonitor.health_score ?? 0) >= 80 ? EMERALD : (apiMonitor.health_score ?? 0) >= 50 ? AMBER : CRIMSON,
      } : undefined}
      actions={
        <div className="flex items-center gap-2">
          <FormSelect
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            size="sm"
            wrapperClassName="w-32"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </FormSelect>
          <Input
            type="text"
            placeholder="Country filter"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            size="sm"
            wrapperClassName="w-28"
          />
          <Button variant="hero" size="icon" onClick={handleRefreshAll} aria-label="Refresh">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </Button>
          <Dropdown
            align="right"
            trigger={
              <Button variant="hero" size="sm">
                <Download size={12} />
                Export
              </Button>
            }
          >
            {["users", "activity", "financial"].map((r) => (
              <DropdownItem key={r} onClick={() => handleExport(r)}>
                <span className="capitalize">{r} CSV</span>
              </DropdownItem>
            ))}
          </Dropdown>
        </div>
      }
    >

      {/* ═══════════════════════ NEEDS ATTENTION ═══════════════════════ */}
      <MCSection icon={AlertTriangle} title="Needs Attention">
        {attentionItems.length === 0 ? (
          <Alert variant="success" title="Everything looks healthy">
            No unhealthy components, critical errors, or traffic anomalies right now.
          </Alert>
        ) : (
          <div className="space-y-2">
            {attentionItems.slice(0, 8).map((item, i) => (
              <Alert key={i} variant={SEVERITY_ALERT_VARIANT[item.severity]} title={item.title}>
                {item.message}
              </Alert>
            ))}
          </div>
        )}
      </MCSection>

      {/* ═══════════════════════ TRAFFIC & PERFORMANCE ═══════════════════════ */}
      <MCSection icon={Gauge} title="Traffic & Performance">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={Zap} label="Requests" value={apiMonitor?.total_requests?.toLocaleString() ?? "—"} sub={`over ${apiDays}d`} color="blue" />
          <KpiCard icon={CheckCircle2} label="Success Rate" value={apiMonitor ? `${apiMonitor.success_rate_pct}%` : "—"} color="green" />
          <KpiCard icon={Activity} label="Avg Response" value={apiMonitor ? `${apiMonitor.avg_response_ms}ms` : "—"} color={apiMonitor?.avg_response_ms > 500 ? "yellow" : "blue"} />
          <KpiCard icon={AlertCircle} label="Error Rate" value={apiMonitor ? `${apiMonitor.error_rate_pct}%` : "—"} color={apiMonitor?.error_rate_pct > 2 ? "red" : "green"} />
        </div>

        <Card padding="lg">
          <div className="text-sm font-semibold text-slate-800 mb-3">Requests &amp; Errors (daily)</div>
          {!apiMonitor ? (
            <div className="h-48 flex items-center justify-center text-slate-400 text-sm">Loading...</div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={apiMonitor.daily_trend || []}>
                <defs>
                  <linearGradient id="reqGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={CHART_BLUE} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={CHART_BLUE} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={BRD_SOFT} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: TEXT_MUTED }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fontSize: 10, fill: TEXT_MUTED }} />
                <Tooltip contentStyle={{ backgroundColor: WHITE, border: `1px solid ${BRD}`, fontSize: 12 }} />
                <Area type="monotone" dataKey="requests" name="Requests" stroke={CHART_BLUE} fill="url(#reqGrad)" strokeWidth={2} />
                <Area type="monotone" dataKey="errors" name="Errors" stroke={CHART_RED} fillOpacity={0} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card padding="lg">
            <div className="text-sm font-semibold text-slate-800 mb-3">Most Used (by request volume)</div>
            {(apiMonitor?.top_endpoints || []).length === 0 ? (
              <div className="text-sm text-slate-400">No traffic recorded yet for this period.</div>
            ) : (
              <div className="space-y-1.5">
                {apiMonitor.top_endpoints.slice(0, 8).map((ep, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 text-xs py-1 border-b border-slate-100 last:border-0">
                    <span className="font-mono text-slate-700 truncate" title={ep.endpoint}>
                      <span className="text-slate-400 mr-1">{ep.method}</span>{ep.endpoint}
                    </span>
                    <span className="flex items-center gap-2 shrink-0">
                      <span className="text-slate-500">{ep.requests.toLocaleString()} req</span>
                      {ep.error_rate > 5 && <Badge variant="danger" size="sm">{ep.error_rate}% err</Badge>}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card padding="lg">
            <div className="text-sm font-semibold text-slate-800 mb-3">Slowest Endpoints</div>
            {(apiMonitor?.slowest_endpoints || []).length === 0 ? (
              <div className="text-sm text-slate-400">No latency data yet for this period.</div>
            ) : (
              <div className="space-y-1.5">
                {apiMonitor.slowest_endpoints.slice(0, 8).map((ep, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 text-xs py-1 border-b border-slate-100 last:border-0">
                    <span className="font-mono text-slate-700 truncate" title={ep.endpoint}>
                      <span className="text-slate-400 mr-1">{ep.method}</span>{ep.endpoint}
                    </span>
                    <span className="text-slate-500 shrink-0">{ep.avg_ms}ms avg</span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </MCSection>

      {/* ═══════════════════════ COMPONENT HEALTH ═══════════════════════ */}
      <MCSection icon={HeartPulse} title="Component Health" action={<StatusPill status={opsHealth?.status} />}>
        {componentEntries.length === 0 ? (
          <div className="text-sm text-slate-400">Loading health checks...</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {componentEntries.map(([name, c]) => (
              <Card key={name} padding="md" className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-slate-800 truncate">{COMPONENT_LABEL[name] || name}</div>
                  <div className="text-[11px] text-slate-400 truncate">{c.message || "—"}</div>
                </div>
                <StatusPill status={c.status} />
              </Card>
            ))}
          </div>
        )}
      </MCSection>

      {/* ═══════════════════════ USERS ═══════════════════════ */}
      <MCSection icon={Users} title="Users">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={Users}     label="Total Users"        value={u.total?.toLocaleString()}     color="blue" />
          <KpiCard icon={UserCheck} label="New This Period"    value={u.new_period?.toLocaleString()} sub={`${u.new_today ?? 0} today`} color="blue" />
          <KpiCard icon={Users}     label="Premium Users"     value={u.premium?.toLocaleString()}    color="yellow" />
          <KpiCard icon={AlertCircle} label="Suspended/Banned" value={((u.suspended ?? 0) + (u.banned ?? 0)).toLocaleString()} color="red" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={UserCheck} label="Email Verified"    value={u.email_verified?.toLocaleString()} color="green" />
          <KpiCard icon={UserCheck} label="Verified Researchers" value={u.verified_researchers?.toLocaleString()} color="purple" />
          <KpiCard icon={Link2}     label="ORCID Linked"      value={u.orcid_linked?.toLocaleString()} color="purple" />
          <KpiCard icon={Activity}  label="Onboarded"          value={u.onboarded?.toLocaleString()}      color="purple" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card padding="lg">
            <div className="text-sm font-semibold text-slate-800 mb-3">User Registrations</div>
            {tsLoading ? (
              <div className="h-48 flex items-center justify-center text-slate-400 text-sm">Loading...</div>
            ) : (
              <ResponsiveContainer width="100%" height={180}>
                <AreaChart data={ts?.series || []}>
                  <defs>
                    <linearGradient id="regGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_BLUE} stopOpacity={0.25} />
                      <stop offset="95%" stopColor={CHART_BLUE} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={BRD_SOFT} />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: TEXT_MUTED }} tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 10, fill: TEXT_MUTED }} />
                  <Tooltip contentStyle={{ backgroundColor: WHITE, border: `1px solid ${BRD}`, fontSize: 12 }} />
                  <Area type="monotone" dataKey="registrations" stroke={CHART_BLUE} fill="url(#regGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </Card>

          <Card padding="lg">
            <div className="text-sm font-semibold text-slate-800 mb-3">Plan Distribution</div>
            {!loading && (
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: "Free",            value: u.free,           pct: u.total ? Math.round(u.free / u.total * 100) : 0,           color: TEXT_MUTED },
                  { label: "Researcher",      value: u.researcher,     pct: u.total ? Math.round(u.researcher / u.total * 100) : 0,     color: INFO },
                  { label: "Pro Researcher",  value: u.pro_researcher, pct: u.total ? Math.round(u.pro_researcher / u.total * 100) : 0, color: VIOLET },
                  { label: "Institution",     value: u.institution,    pct: u.total ? Math.round(u.institution / u.total * 100) : 0,    color: EMERALD },
                ].map(({ label, value, pct, color }) => (
                  <div key={label}>
                    <div className="flex justify-between text-xs text-slate-400 mb-1">
                      <span>{label}</span>
                      <span>{pct}%</span>
                    </div>
                    <MiniBar value={pct} max={100} height={6} color={color} />
                    <div className="text-xs text-slate-800 mt-1">{value?.toLocaleString() ?? 0}</div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </MCSection>

      {/* ═══════════════════════ PLATFORM ACTIVITY ═══════════════════════ */}
      <MCSection icon={FlaskConical} title="Platform Activity">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card padding="lg">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 mb-3">
              <BookOpen size={14} /> Research
            </div>
            <div className="space-y-1.5 text-xs">
              {[
                ["New publications", a.new_publications],
                ["New projects", a.new_projects],
                ["New collaborations", a.new_collaborations],
                ["Active manuscripts", research?.manuscripts?.active],
                ["Total projects", research?.projects?.total],
                ["Total citations", impact?.total_citations?.toLocaleString?.()],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between border-b border-slate-100 py-1 last:border-0">
                  <span className="text-slate-500">{label}</span>
                  <span className="text-slate-800 font-medium">{value ?? "—"}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card padding="lg">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 mb-3">
              <Network size={14} /> Community
            </div>
            <div className="space-y-1.5 text-xs">
              {[
                ["Researchers", community?.total_researchers?.toLocaleString?.()],
                ["Groups", community?.total_groups?.toLocaleString?.()],
                ["Communities", community?.total_communities?.toLocaleString?.()],
                ["Open collaborations", community?.open_collaborations?.toLocaleString?.()],
                ["Upcoming events", community?.upcoming_events?.toLocaleString?.()],
                ["Active mentors", community?.active_mentors?.toLocaleString?.()],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between border-b border-slate-100 py-1 last:border-0">
                  <span className="text-slate-500">{label}</span>
                  <span className="text-slate-800 font-medium">{value ?? "—"}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card padding="lg">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 mb-3">
              <Sparkles size={14} /> AI Usage
            </div>
            <div className="space-y-1.5 text-xs">
              {[
                ["Conversations", aiStats?.total_conversations?.toLocaleString?.()],
                ["AI requests", a.ai_requests?.toLocaleString?.()],
                ["Active AI users", aiStats?.active_users?.toLocaleString?.()],
                ["Avg msgs / user", aiStats?.avg_messages_per_user],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between border-b border-slate-100 py-1 last:border-0">
                  <span className="text-slate-500">{label}</span>
                  <span className="text-slate-800 font-medium">{value ?? "—"}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <Card padding="lg">
          <div className="text-sm font-semibold text-slate-800 mb-3">Daily Logins &amp; AI Requests</div>
          {tsLoading ? (
            <div className="h-48 flex items-center justify-center text-slate-400 text-sm">Loading...</div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={ts?.series || []}>
                <CartesianGrid strokeDasharray="3 3" stroke={BRD_SOFT} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: TEXT_MUTED }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fontSize: 10, fill: TEXT_MUTED }} />
                <Tooltip contentStyle={{ backgroundColor: WHITE, border: `1px solid ${BRD}`, fontSize: 12 }} />
                <Bar dataKey="logins"      name="Logins"      fill={CHART_GREEN}  radius={[2, 2, 0, 0]} />
                <Bar dataKey="ai_requests" name="AI Requests" fill={CHART_PURPLE} radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </MCSection>

      {/* ═══════════════════════ BUSINESS & REVENUE ═══════════════════════ */}
      <MCSection icon={DollarSign} title="Business & Revenue">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={DollarSign} label="MRR (EUR)"          value={`€${f.mrr_eur?.toLocaleString()}`}  color="green" />
          <KpiCard icon={TrendingUp} label="ARR (EUR)"          value={`€${f.arr_eur?.toLocaleString()}`}  color="green" />
          <KpiCard icon={TrendingUp} label="Conversion Rate"    value={`${f.conversion_rate_pct ?? 0}%`}  sub={`${f.conversions ?? 0} conversions`} color="green" />
          <KpiCard icon={AlertCircle} label="Churn Rate"        value={`${f.churn_rate_pct ?? 0}%`}        sub={`${f.churned_period ?? 0} churned`} color="red" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={DollarSign} label="ARPU (EUR)"         value={`€${f.arpu_eur}`}                   color="blue" />
          <KpiCard icon={DollarSign} label="LTV (EUR)" value={revenue?.ltv_eur != null ? `€${revenue.ltv_eur.toLocaleString()}` : "—"} color="green" />
          <KpiCard icon={TrendingUp} label="Retention Rate" value={revenue?.retention_rate_pct != null ? `${revenue.retention_rate_pct}%` : "—"} color="purple" />
          <KpiCard icon={Users}      label="Active Subscribers" value={f.active_subscribers?.toLocaleString()} color="blue" />
        </div>
      </MCSection>

      {/* ═══════════════════════ SUPPORT ═══════════════════════ */}
      <MCSection icon={LifeBuoy} title="Support">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={LifeBuoy} label="Open Tickets" value={supportStats?.open?.toLocaleString?.() ?? "—"} color={supportStats?.open ? "yellow" : "green"} />
          <KpiCard icon={UserCheck} label="Resolved" value={supportStats?.resolved?.toLocaleString?.() ?? "—"} color="green" />
          <KpiCard icon={TrendingUp} label="Resolution Rate" value={supportStats?.resolution_rate_pct != null ? `${supportStats.resolution_rate_pct}%` : "—"} color="blue" />
          <KpiCard icon={Activity} label="Avg Resolution (h)" value={supportStats?.avg_resolution_hours ?? "—"} color="purple" />
        </div>
      </MCSection>
    </AdministrationLayout>
  );
}

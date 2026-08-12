/* eslint-disable */
import React, { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  Users, TrendingUp, DollarSign, Activity, UserCheck, Link2, BookOpen,
  FlaskConical, RefreshCw, Download, AlertCircle, Server, ShieldAlert, Award, Globe2,
  Sparkles, LifeBuoy, Network, HeartPulse,
} from "lucide-react";
import api from "@/lib/api";
import { INFO, EMERALD, AMBER, CRIMSON, VIOLET, TEXT_MUTED, BRD, BRD_SOFT, WHITE } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { useAdminRealtime } from "@/contexts/AdminRealtimeContext";
import {
  Button, Card, StatCard, Badge, MiniBar, FormSelect, Input,
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

/** Mission Control section — one of the 10 named areas of the control room. */
function MCSection({ icon: Icon, title, children }) {
  return (
    <div className="space-y-3">
      <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-slate-500">
        {Icon && <Icon size={12} />} {title}
      </h2>
      {children}
    </div>
  );
}

const STATUS_VARIANT = { healthy: "success", degraded: "warning", unhealthy: "danger" };

function StatusPill({ status }) {
  return <Badge variant={STATUS_VARIANT[status] || "neutral"}>{status || "unknown"}</Badge>;
}

const CHART_BLUE = INFO;
const CHART_GREEN = EMERALD;
const CHART_PURPLE = VIOLET;

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
  const { data: opsHealth } = useAdminEndpoint("/ops/health");

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

  return (
    <AdministrationLayout
      title="Mission Control"
      subtitle="The single place to operate Synaptiq"
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
          <Button variant="ghost" size="icon" onClick={refetch} aria-label="Refresh">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </Button>
          <Dropdown
            align="right"
            trigger={
              <Button variant="primary" size="sm">
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

      {/* ═══════════════════════ 1. PLATFORM OVERVIEW ═══════════════════════ */}
      <MCSection icon={Users} title="Platform Overview">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={Users}     label="Total Users"        value={u.total?.toLocaleString()}     color="blue" />
          <KpiCard icon={Activity}  label="Online Now"         value={u.online_now?.toLocaleString()} color="green" />
          <KpiCard icon={UserCheck} label="New This Period"    value={u.new_period?.toLocaleString()} sub={`${u.new_today ?? 0} today`} color="blue" />
          <KpiCard icon={Link2}     label="ORCID Linked"      value={u.orcid_linked?.toLocaleString()} color="purple" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={Users}     label="Premium Users"     value={u.premium?.toLocaleString()}    color="yellow" />
          <KpiCard icon={UserCheck} label="Email Verified"    value={u.email_verified?.toLocaleString()} color="green" />
          <KpiCard icon={UserCheck} label="Verified Researchers" value={u.verified_researchers?.toLocaleString()} color="purple" />
          <KpiCard icon={AlertCircle} label="Suspended/Banned" value={((u.suspended ?? 0) + (u.banned ?? 0)).toLocaleString()} color="red" />
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

      {/* ═══════════════════════ 2. BUSINESS ═══════════════════════ */}
      <MCSection icon={TrendingUp} title="Business">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={TrendingUp} label="Conversion Rate"    value={`${f.conversion_rate_pct ?? 0}%`}  sub={`${f.conversions ?? 0} conversions`} color="green" />
          <KpiCard icon={Users}      label="Active Subscribers" value={f.active_subscribers?.toLocaleString()} color="blue" />
          <KpiCard icon={AlertCircle} label="Churn Rate"        value={`${f.churn_rate_pct ?? 0}%`}        sub={`${f.churned_period ?? 0} churned`} color="red" />
          <KpiCard icon={Activity}   label="Onboarded"          value={u.onboarded?.toLocaleString()}      color="purple" />
        </div>
      </MCSection>

      {/* ═══════════════════════ 3. RESEARCH ═══════════════════════ */}
      <MCSection icon={FlaskConical} title="Research">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={BookOpen}    label="New Publications"   value={a.new_publications?.toLocaleString()} color="blue" />
          <KpiCard icon={FlaskConical} label="New Projects"      value={a.new_projects?.toLocaleString()}     color="purple" />
          <KpiCard icon={Users}       label="New Collaborations" value={a.new_collaborations?.toLocaleString()} color="green" />
          <KpiCard icon={Award}       label="Active Manuscripts" value={research?.manuscripts?.active?.toLocaleString?.() ?? "—"} color="yellow" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={Award} label="Researchers Scored" value={impact?.total_researchers_scored?.toLocaleString?.() ?? "—"} color="purple" />
          <KpiCard icon={TrendingUp} label="Avg SIS" value={impact?.avg_sis ?? "—"} color="blue" />
          <KpiCard icon={BookOpen} label="Total Publications" value={impact?.total_publications?.toLocaleString?.() ?? "—"} color="green" />
          <KpiCard icon={Globe2} label="Total Citations" value={impact?.total_citations?.toLocaleString?.() ?? "—"} color="yellow" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={FlaskConical} label="Total Projects" value={research?.projects?.total?.toLocaleString?.() ?? "—"} color="blue" />
          <KpiCard icon={Users} label="Total Workspaces" value={research?.workspaces?.total?.toLocaleString?.() ?? "—"} color="purple" />
          <KpiCard icon={Users} label="Total Collaborations" value={research?.collaborations?.total?.toLocaleString?.() ?? "—"} color="green" />
          <KpiCard icon={Award} label="Grants (links + apps)" value={research?.grants?.total?.toLocaleString?.() ?? "—"} color="yellow" />
        </div>
      </MCSection>

      {/* ═══════════════════════ 4. COMMUNITY ═══════════════════════ */}
      <MCSection icon={Network} title="Community">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={Users} label="Researchers" value={community?.total_researchers?.toLocaleString?.() ?? "—"} color="blue" />
          <KpiCard icon={Network} label="Groups" value={community?.total_groups?.toLocaleString?.() ?? "—"} color="purple" />
          <KpiCard icon={Network} label="Communities" value={community?.total_communities?.toLocaleString?.() ?? "—"} color="green" />
          <KpiCard icon={Users} label="Open Collaborations" value={community?.open_collaborations?.toLocaleString?.() ?? "—"} color="yellow" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={Activity} label="Upcoming Events" value={community?.upcoming_events?.toLocaleString?.() ?? "—"} color="blue" />
          <KpiCard icon={UserCheck} label="Active Mentors" value={community?.active_mentors?.toLocaleString?.() ?? "—"} color="green" />
        </div>
      </MCSection>

      {/* ═══════════════════════ 5. AI ═══════════════════════ */}
      <MCSection icon={Sparkles} title="AI">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={Sparkles} label="Conversations" value={aiStats?.total_conversations?.toLocaleString?.() ?? "—"} color="purple" />
          <KpiCard icon={Activity} label="AI Requests" value={a.ai_requests?.toLocaleString?.() ?? "—"} color="yellow" />
          <KpiCard icon={Users} label="Active AI Users" value={aiStats?.active_users?.toLocaleString?.() ?? "—"} color="blue" />
          <KpiCard icon={TrendingUp} label="Avg Msgs / User" value={aiStats?.avg_messages_per_user ?? "—"} color="green" />
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

      {/* ═══════════════════════ 6. SECURITY ═══════════════════════ */}
      <MCSection icon={ShieldAlert} title="Security">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={ShieldAlert} label="Recent Security Events" value={securityEvents?.items?.length ?? "—"} color={securityEvents?.items?.length ? "yellow" : "green"} />
          <KpiCard icon={AlertCircle} label="Distinct Failing IPs (24h)" value={failedLogins?.items?.length ?? "—"} color={failedLogins?.items?.length ? "red" : "green"} />
          <KpiCard icon={AlertCircle} label="Top Failing IP Attempts" value={failedLogins?.items?.[0]?.count ?? "—"} color="red" />
          <KpiCard icon={Users} label="Suspended/Banned" value={((u.suspended ?? 0) + (u.banned ?? 0)).toLocaleString()} color="red" />
        </div>
      </MCSection>

      {/* ═══════════════════════ 7. INFRASTRUCTURE ═══════════════════════ */}
      <MCSection icon={Server} title="Infrastructure">
        <Card padding="lg" className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <Server size={14} /> Overall Platform Status
          </div>
          <StatusPill status={opsHealth?.status} />
        </Card>
        <div className="grid grid-cols-2 gap-3">
          <KpiCard icon={Server} label="App Uptime (h)" value={health?.app_uptime_hours ?? "—"} color="blue" />
          <KpiCard icon={AlertCircle} label="Errors (24h)" value={health?.errors_24h ?? "—"} color={health?.errors_24h ? "red" : "green"} />
          <KpiCard icon={Activity} label="DB Status" value={health?.database?.ok ? "OK" : "—"} color={health?.database?.ok ? "green" : "red"} />
          <KpiCard icon={Users} label="Collections" value={health?.database?.collections ?? "—"} color="purple" />
        </div>
      </MCSection>

      {/* ═══════════════════════ 8. SUPPORT ═══════════════════════ */}
      <MCSection icon={LifeBuoy} title="Support">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={LifeBuoy} label="Open Tickets" value={supportStats?.open?.toLocaleString?.() ?? "—"} color={supportStats?.open ? "yellow" : "green"} />
          <KpiCard icon={UserCheck} label="Resolved" value={supportStats?.resolved?.toLocaleString?.() ?? "—"} color="green" />
          <KpiCard icon={TrendingUp} label="Resolution Rate" value={supportStats?.resolution_rate_pct != null ? `${supportStats.resolution_rate_pct}%` : "—"} color="blue" />
          <KpiCard icon={Activity} label="Avg Resolution (h)" value={supportStats?.avg_resolution_hours ?? "—"} color="purple" />
        </div>
      </MCSection>

      {/* ═══════════════════════ 9. FINANCE ═══════════════════════ */}
      <MCSection icon={DollarSign} title="Finance">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={DollarSign} label="MRR (EUR)"          value={`€${f.mrr_eur?.toLocaleString()}`}  color="green" />
          <KpiCard icon={TrendingUp} label="ARR (EUR)"          value={`€${f.arr_eur?.toLocaleString()}`}  color="green" />
          <KpiCard icon={DollarSign} label="ARPU (EUR)"         value={`€${f.arpu_eur}`}                   color="blue" />
          <KpiCard icon={DollarSign} label="LTV (EUR)" value={revenue?.ltv_eur != null ? `€${revenue.ltv_eur.toLocaleString()}` : "—"} color="green" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={TrendingUp} label="Retention Rate" value={revenue?.retention_rate_pct != null ? `${revenue.retention_rate_pct}%` : "—"} color="purple" />
          <KpiCard icon={DollarSign} label="CAC (EUR)" value={revenue?.cac_eur != null ? `€${revenue.cac_eur.toLocaleString()}` : "—"} color="yellow" />
          <KpiCard icon={Users} label="Active Subscribers" value={revenue?.active_subscribers?.toLocaleString?.() ?? "—"} color="blue" />
          <KpiCard icon={Activity} label="Free Users" value={u.free?.toLocaleString()} color="yellow" />
        </div>
      </MCSection>

      {/* ═══════════════════════ 10. SYSTEM HEALTH ═══════════════════════ */}
      <MCSection icon={HeartPulse} title="System Health">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card padding="lg">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 mb-3">
              <ShieldAlert size={14} /> Errors &amp; Incidents
            </div>
            <div className="grid grid-cols-2 gap-3">
              <KpiCard icon={AlertCircle} label="Unresolved" value={errorStats?.unresolved ?? "—"} color={errorStats?.unresolved ? "yellow" : "green"} />
              <KpiCard icon={AlertCircle} label="Critical" value={errorStats?.critical ?? "—"} color={errorStats?.critical ? "red" : "green"} />
              <KpiCard icon={AlertCircle} label="New (24h)" value={errorStats?.new_24h ?? "—"} color="blue" />
              <KpiCard icon={Activity} label="Top Category" value={errorStats?.by_category?.[0]?.category ?? "—"} color="purple" />
            </div>
          </Card>

          <Card padding="lg">
            <div className="flex items-center gap-2 justify-between mb-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                <HeartPulse size={14} /> Component Health
              </div>
              <StatusPill status={opsHealth?.status} />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <KpiCard icon={Activity} label="Healthy" value={opsHealth?.summary?.healthy ?? "—"} color="green" />
              <KpiCard icon={AlertCircle} label="Degraded" value={opsHealth?.summary?.degraded ?? "—"} color="yellow" />
              <KpiCard icon={AlertCircle} label="Unhealthy" value={opsHealth?.summary?.unhealthy ?? "—"} color="red" />
            </div>
          </Card>
        </div>
      </MCSection>
    </AdministrationLayout>
  );
}

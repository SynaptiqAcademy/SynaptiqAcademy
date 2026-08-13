import React, { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { EMERALD, CRIMSON, TEAL, TEXT_MUTED } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  RefreshCw,
  MessageSquare,
  Users,
  Zap,
  Cpu,
  ChevronDown,
  ChevronUp,
  DollarSign,
  Activity,
} from "lucide-react";
import {
  Button, Card, StatCard, StatGrid, MiniBar, DataTable, Badge,
  EmptyState, ErrorState, Skeleton, SkeletonCard,
} from "@/components/ds";

// ── Constants ────────────────────────────────────────────────────────────────

const AGENT_COLORS_ADMIN = {
  research:      { bar: "#7C3AED", label: "Research" },
  publication:   { bar: "#3B82F6", label: "Publication" },
  journal:       { bar: "#0891B2", label: "Journal" },
  grant:         { bar: "#059669", label: "Grant" },
  collaboration: { bar: "#EA580C", label: "Collaboration" },
  teaching:      { bar: "#D97706", label: "Teaching" },
  analytics:     { bar: "#06B6D4", label: "Analytics" },
  profile:       { bar: "#E11D48", label: "Profile" },
  general:       { bar: "#64748B", label: "General" },
  auto:          { bar: "#8B5CF6", label: "Auto" },
};

const ACTION_VARIANT = {
  create:  "success",
  update:  "info",
  delete:  "danger",
  export:  "warning",
  analyze: "purple",
};

const MEMORY_TYPE_COLORS = {
  preference: "#3B82F6",
  goal:       "#7C3AED",
  fact:       "#059669",
  context:    "#D97706",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtNum(val) {
  if (val == null) return "—";
  return Number(val).toLocaleString();
}

function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function fmtCost(tokens) {
  // claude-sonnet-4-6: $3/M input, $15/M output — approximate at blended $9/M
  if (tokens == null) return "—";
  const cost = (tokens / 1_000_000) * 9;
  return `$${cost.toFixed(2)}`;
}

function pct(val, max) {
  if (!max) return 0;
  return Math.min(100, Math.round((val / max) * 100));
}

// ── Hook ─────────────────────────────────────────────────────────────────────

function useAdminAI(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/admin/ai/${path}`);
      setData(res.data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, refetch: load };
}

// ── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, icon: Icon, loading, highlight }) {
  return (
    <StatCard
      label={label}
      value={loading ? <Skeleton height="h-7" width="w-16" /> : (value ?? "—")}
      sub={loading ? undefined : sub}
      icon={Icon ? <Icon /> : undefined}
      highlight={highlight}
    />
  );
}

// ── Section wrapper ───────────────────────────────────────────────────────────

function Section({ title, children, action, collapsible = false }) {
  const [open, setOpen] = useState(true);
  return (
    <Card padding="none">
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          {title}
        </h2>
        <div className="flex items-center gap-2">
          {action}
          {collapsible && (
            <button
              onClick={() => setOpen((v) => !v)}
              aria-label={open ? `Collapse ${title}` : `Expand ${title}`}
              className="text-slate-400 hover:text-slate-600 transition-colors"
            >
              {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          )}
        </div>
      </div>
      {(!collapsible || open) && <div className="p-5">{children}</div>}
    </Card>
  );
}

// ── Horizontal bar chart — chrome converted to ds/, bar itself uses MiniBar ───

function HBarChart({ items, maxVal }) {
  if (!items || items.length === 0) {
    return <EmptyState title="No data." size="inline" />;
  }
  const top = maxVal || Math.max(...items.map((i) => i.value || 0), 1);

  return (
    <div className="space-y-3">
      {items.map((item, idx) => {
        const color = item.color || AGENT_COLORS_ADMIN[item.key]?.bar || TEXT_MUTED;
        return (
          <div key={idx} className="flex items-center gap-3">
            <div className="w-20 text-[10px] text-slate-500 text-right flex-shrink-0 truncate" title={item.label}>
              {item.label}
            </div>
            <MiniBar value={item.value || 0} max={top} height={14} color={color} style={{ flex: 1 }} />
            <div className="w-14 text-[10px] text-slate-500 text-right flex-shrink-0">
              {typeof item.value === "number" ? fmtNum(item.value) : item.value}
              {item.pct != null ? ` (${item.pct}%)` : ""}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Vertical bar chart (div-based) — kept hand-rolled: this renders 30+ dense
// daily bars with 45°-rotated labels and a horizontal scroll container, which
// ds/Chart's BarChart can't do (no label rotation, no per-bar min-width
// scroll). Only its colors are restyled for the light theme. ─────────────────

function VBarChart({ data, height = 100 }) {
  if (!data || data.length === 0) {
    return <EmptyState title="No data." size="inline" />;
  }
  const maxVal = Math.max(...data.map((d) => d.value || 0), 1);

  return (
    <div className="flex items-end gap-0.5 overflow-x-auto" style={{ height: height + 24 }}>
      {data.map((item, idx) => {
        const h = Math.max(2, Math.round((item.value / maxVal) * height));
        return (
          <div
            key={idx}
            className="flex flex-col items-center flex-shrink-0"
            style={{ minWidth: 16 }}
            title={`${item.label}: ${fmtNum(item.value)}`}
          >
            <div
              className="w-full rounded-t-sm transition-colors"
              style={{ height: h, backgroundColor: TEAL }}
            />
            <div
              className="text-[8px] text-slate-400 mt-1 rotate-45 origin-left"
              style={{ whiteSpace: "nowrap" }}
            >
              {item.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Main ─────────────────────────────────────────────────────────────────────

export default function AdminAICenter() {
  const { data: stats, loading: statsL, error: statsE, refetch: refStats } = useAdminAI("stats");
  const { data: topUsers, loading: topL, error: topE, refetch: refTop } = useAdminAI("top-users");
  const { data: actionsLog, loading: actL, error: actE, refetch: refAct } = useAdminAI("actions-log");
  const { data: costData, loading: costL, error: costE, refetch: refCost } = useAdminAI("cost-analytics");
  const { data: memStats, loading: memL, error: memE, refetch: refMem } = useAdminAI("memory-stats");

  function refetchAll() {
    refStats(); refTop(); refAct(); refCost(); refMem();
  }

  // ── Agent usage from stats ─────────────────────────────────────────────────
  const agentUsage = (() => {
    if (!stats?.agent_usage) return [];
    const total = Object.values(stats.agent_usage).reduce((s, v) => s + (v || 0), 0) || 1;
    return Object.entries(stats.agent_usage).map(([key, value]) => ({
      key,
      label: AGENT_COLORS_ADMIN[key]?.label || key,
      value,
      pct: Math.round((value / total) * 100),
      color: AGENT_COLORS_ADMIN[key]?.bar,
    })).sort((a, b) => b.value - a.value);
  })();

  // ── Daily activity ─────────────────────────────────────────────────────────
  const dailyActivity = (() => {
    if (!stats?.daily_activity) return [];
    return stats.daily_activity.map((d) => ({
      label: new Date(d.date).toLocaleDateString("en-US", { month: "numeric", day: "numeric" }),
      value: d.messages || d.count || 0,
    }));
  })();

  // ── Cost by agent ──────────────────────────────────────────────────────────
  const costByAgent = (() => {
    if (!costData?.by_agent) return [];
    return Object.entries(costData.by_agent).map(([key, tokens]) => ({
      key,
      label: AGENT_COLORS_ADMIN[key]?.label || key,
      value: Math.round(((tokens || 0) / 1_000_000) * 9 * 100) / 100,
      color: AGENT_COLORS_ADMIN[key]?.bar,
    })).sort((a, b) => b.value - a.value);
  })();

  // ── Memory by type ─────────────────────────────────────────────────────────
  const memByType = (() => {
    if (!memStats?.by_type) return [];
    const total = Object.values(memStats.by_type).reduce((s, v) => s + (v || 0), 0) || 1;
    return Object.entries(memStats.by_type).map(([key, value]) => ({
      key,
      label: key.charAt(0).toUpperCase() + key.slice(1),
      value,
      pct: Math.round((value / total) * 100),
      color: MEMORY_TYPE_COLORS[key] || "#64748B",
    })).sort((a, b) => b.value - a.value);
  })();

  const kpis = [
    {
      label: "Total Conversations",
      value: fmtNum(stats?.total_conversations),
      icon: MessageSquare,
    },
    {
      label: "Total Messages",
      value: fmtNum(stats?.total_messages),
      icon: Activity,
      highlight: true,
    },
    {
      label: "Active Users (30d)",
      value: fmtNum(stats?.active_users_30d),
      icon: Users,
    },
    {
      label: "Actions Executed",
      value: fmtNum(stats?.total_actions),
      icon: Zap,
    },
    {
      label: "Total Tokens Used",
      value: stats?.total_tokens != null ? fmtNum(stats.total_tokens) : "—",
      sub: stats?.total_tokens != null ? `≈ ${fmtCost(stats.total_tokens)} est.` : null,
      icon: Cpu,
    },
  ];

  const topUsersList = (Array.isArray(topUsers) ? topUsers : topUsers?.users || []);
  const topUsersRows = topUsersList.slice(0, 50).map((u, idx) => ({
    ...u, id: u.user_id ?? idx, _rank: idx + 1,
  }));
  const topUsersColumns = [
    { key: "_rank", label: "#", width: 32, render: (v) => <span className="font-mono text-slate-400">{v}</span> },
    { key: "name", label: "Name", render: (_v, row) => row.full_name || row.name || row.email || "—" },
    { key: "institution", label: "Institution", maxWidth: 160, render: (v) => v || "—" },
    { key: "message_count", label: "Messages", render: (v) => <span className="font-mono text-slate-800">{fmtNum(v)}</span> },
    { key: "tokens_used", label: "Tokens", render: (v) => <span className="font-mono">{fmtNum(v)}</span> },
    { key: "actions_count", label: "Actions", render: (v) => <span className="font-mono">{fmtNum(v)}</span> },
  ];

  const actionsList = (Array.isArray(actionsLog) ? actionsLog : actionsLog?.actions || []);
  const actionsRows = actionsList.slice(0, 100).map((a, idx) => ({ ...a, id: a.id ?? idx }));
  const actionsColumns = [
    { key: "user", label: "User", render: (_v, row) => row.user_email || row.user_id || "—" },
    {
      key: "action_type", label: "Action Type",
      render: (v) => {
        const key = (v || "").split("_")[0].toLowerCase();
        return key === "search"
          ? <Badge size="sm" color={TEAL}>{v || "—"}</Badge>
          : <Badge size="sm" variant={ACTION_VARIANT[key] || "neutral"}>{v || "—"}</Badge>;
      },
    },
    {
      key: "status", label: "Status",
      render: (v) => (
        <span
          className="text-[10px] font-mono"
          style={{ color: (v === "success" || v === "completed") ? EMERALD : (v === "failed" || v === "error") ? CRIMSON : TEXT_MUTED }}
        >
          {v || "—"}
        </span>
      ),
    },
    {
      key: "params", label: "Params", maxWidth: 200,
      render: (v) => (
        <span className="font-mono text-[10px] text-slate-400">
          {v ? (typeof v === "string" ? v.slice(0, 60) : JSON.stringify(v).slice(0, 60)) : "—"}
        </span>
      ),
    },
    { key: "created_at", label: "Date", render: (_v, row) => fmtDateTime(row.created_at || row.timestamp) },
  ];

  return (
    <AdministrationLayout
      title="AI Operating System Center"
      subtitle="Usage analytics, cost tracking, and operational intelligence for Synaptiq AI OS"
      actions={
        <Button variant="hero" size="sm" onClick={refetchAll}>
          <RefreshCw size={12} />
          Refresh All
        </Button>
      }
    >

      {/* Section 1: KPI Cards */}
      <StatGrid cols={5}>
        {kpis.map((kpi, idx) => (
          <KpiCard
            key={idx}
            label={kpi.label}
            value={kpi.value}
            sub={kpi.sub}
            icon={kpi.icon}
            loading={statsL}
            highlight={kpi.highlight}
          />
        ))}
      </StatGrid>

      {/* Section 2: Agent Usage Distribution */}
      <Section title="Agent Usage Distribution">
        {statsE ? (
          <ErrorState message={statsE} onRetry={refStats} />
        ) : statsL ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} height="h-4" />
            ))}
          </div>
        ) : agentUsage.length === 0 ? (
          <EmptyState title="No agent usage data available." size="inline" />
        ) : (
          <HBarChart items={agentUsage} />
        )}
      </Section>

      {/* Section 3: Daily Activity */}
      <Section title="Daily Message Activity (last 30 days)">
        {statsE ? (
          <ErrorState message={statsE} onRetry={refStats} />
        ) : statsL ? (
          <Skeleton height="h-32" />
        ) : dailyActivity.length === 0 ? (
          <EmptyState title="No daily activity data available." size="inline" />
        ) : (
          <div className="overflow-x-auto">
            <VBarChart data={dailyActivity} height={120} />
          </div>
        )}
      </Section>

      {/* Section 4: Top Users Table */}
      <Section title="Top Users by Activity" collapsible>
        {topE ? (
          <ErrorState message={topE} onRetry={refTop} />
        ) : topL ? (
          <SkeletonCard rows={5} />
        ) : topUsersList.length === 0 ? (
          <EmptyState title="No user data available." size="inline" />
        ) : (
          <DataTable columns={topUsersColumns} rows={topUsersRows} />
        )}
      </Section>

      {/* Section 5: Actions Log */}
      <Section title="Actions Log" collapsible>
        {actE ? (
          <ErrorState message={actE} onRetry={refAct} />
        ) : actL ? (
          <SkeletonCard rows={5} />
        ) : actionsList.length === 0 ? (
          <EmptyState title="No actions logged yet." size="inline" />
        ) : (
          <DataTable columns={actionsColumns} rows={actionsRows} />
        )}
      </Section>

      {/* Section 6: Cost Analytics */}
      <Section
        title="Cost Analytics"
        action={
          <span className="text-[10px] text-slate-400 italic">
            claude-sonnet-4-6: $3/M input · $15/M output
          </span>
        }
        collapsible
      >
        {costE ? (
          <ErrorState message={costE} onRetry={refCost} />
        ) : costL ? (
          <div className="grid grid-cols-2 gap-4">
            <Skeleton height="h-24" />
            <Skeleton height="h-24" />
          </div>
        ) : !costData ? (
          <EmptyState title="No cost data available." size="inline" />
        ) : (
          <div className="space-y-6">
            {/* Summary cards */}
            <StatGrid cols={3}>
              <StatCard
                label="Total Input Tokens"
                value={fmtNum(costData.total_input_tokens)}
                sub={`≈ $${((costData.total_input_tokens || 0) / 1_000_000 * 3).toFixed(2)}`}
              />
              <StatCard
                label="Total Output Tokens"
                value={fmtNum(costData.total_output_tokens)}
                sub={`≈ $${((costData.total_output_tokens || 0) / 1_000_000 * 15).toFixed(2)}`}
              />
              <StatCard
                label="Estimated Total Cost"
                value={
                  costData.estimated_cost_usd != null
                    ? `$${Number(costData.estimated_cost_usd).toFixed(2)}`
                    : fmtCost((costData.total_input_tokens || 0) + (costData.total_output_tokens || 0))
                }
                sub="blended avg rate applied"
                icon={<DollarSign />}
                highlight
              />
            </StatGrid>

            {/* Cost by agent */}
            {costByAgent.length > 0 && (
              <div>
                <div className="text-xs uppercase tracking-widest text-slate-500 mb-3">
                  Cost by Agent ($USD est.)
                </div>
                <HBarChart
                  items={costByAgent.map((i) => ({ ...i, value: i.value }))}
                  maxVal={costByAgent[0]?.value || 1}
                />
              </div>
            )}

            {/* Daily cost */}
            {costData.daily_cost && costData.daily_cost.length > 0 && (
              <div>
                <div className="text-xs uppercase tracking-widest text-slate-500 mb-3">
                  Daily Cost Trend ($USD)
                </div>
                <VBarChart
                  data={costData.daily_cost.map((d) => ({
                    label: new Date(d.date).toLocaleDateString("en-US", { month: "numeric", day: "numeric" }),
                    value: d.cost || d.estimated_cost || 0,
                  }))}
                  height={100}
                />
              </div>
            )}
          </div>
        )}
      </Section>

      {/* Section 7: Memory Stats */}
      <Section title="Memory Analytics" collapsible>
        {memE ? (
          <ErrorState message={memE} onRetry={refMem} />
        ) : memL ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <Skeleton key={i} height="h-5" />)}
          </div>
        ) : !memStats ? (
          <EmptyState title="No memory stats available." size="inline" />
        ) : (
          <div className="space-y-5">
            <StatGrid cols={3}>
              <StatCard label="Total Memory Items" value={fmtNum(memStats.total_count || memStats.total)} />
              <StatCard label="Users with Memory" value={fmtNum(memStats.users_with_memory)} />
              <StatCard
                label="Avg per User"
                value={memStats.avg_per_user != null ? Number(memStats.avg_per_user).toFixed(1) : "—"}
              />
            </StatGrid>

            {memByType.length > 0 && (
              <div>
                <div className="text-xs uppercase tracking-widest text-slate-500 mb-3">
                  Distribution by Memory Type
                </div>
                <HBarChart items={memByType} />
              </div>
            )}
          </div>
        )}
      </Section>

      {/* Footer note */}
      <div className="text-center text-[10px] text-slate-400 pb-4">
        Cost estimates based on claude-sonnet-4-6 pricing ($3/M input tokens · $15/M output tokens).
        Actual billing may vary.
      </div>
    </AdministrationLayout>
  );
}

import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { EMERALD } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  RefreshCw,
  MessageSquare,
  Users,
  Zap,
  Cpu,
  TrendingUp,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  DollarSign,
  Brain,
  BarChart2,
  Activity,
} from "lucide-react";

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

const ACTION_COLORS = {
  create:   "text-emerald-400 border-emerald-700 bg-emerald-950/30",
  update:   "text-blue-400 border-blue-700 bg-blue-950/30",
  delete:   "text-red-400 border-red-700 bg-red-950/30",
  export:   "text-amber-400 border-amber-700 bg-amber-950/30",
  analyze:  "text-violet-400 border-violet-700 bg-violet-950/30",
  search:   "text-cyan-400 border-cyan-700 bg-cyan-950/30",
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

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
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

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Sk({ h = "h-4", w = "w-full" }) {
  return <div className={`${h} ${w} bg-[#1a3050] animate-pulse rounded-sm`} />;
}

function SkCard() {
  return (
    <div className="border border-[#1a3050] bg-[#0B1C35] p-5 space-y-3 animate-pulse">
      <Sk h="h-3" w="w-1/3" />
      <Sk h="h-8" w="w-1/2" />
      <Sk h="h-3" />
    </div>
  );
}

// ── Error ─────────────────────────────────────────────────────────────────────

function Err({ message, onRetry }) {
  return (
    <div className="border border-red-800 bg-red-950/30 p-4 text-center">
      <AlertCircle size={18} strokeWidth={1.5} className="text-red-400 mx-auto mb-2" />
      <p className="text-red-400 text-xs mb-2">{message || "Failed to load."}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-[10px] border border-red-700 text-red-400 px-3 py-1 hover:bg-red-950 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}

// ── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, icon: Icon, loading, highlight }) {
  return (
    <div className={`border bg-[#0B1C35] p-5 ${highlight ? "border-[#0891B2]" : "border-[#1a3050]"}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">
          {label}
        </div>
        {Icon && <Icon size={12} strokeWidth={1.5} className="text-slate-600" />}
      </div>
      {loading ? (
        <Sk h="h-8" w="w-2/3" />
      ) : (
        <>
          <div className={`font-serif text-3xl ${highlight ? "text-[#0891B2]" : "text-white"}`}>
            {value ?? "—"}
          </div>
          {sub && <div className="text-[10px] text-slate-500 mt-1">{sub}</div>}
        </>
      )}
    </div>
  );
}

// ── Section wrapper ───────────────────────────────────────────────────────────

function Section({ title, children, action, collapsible = false }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="border border-[#1a3050] bg-[#080f1f]">
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#1a3050]">
        <h2 className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">
          {title}
        </h2>
        <div className="flex items-center gap-2">
          {action}
          {collapsible && (
            <button
              onClick={() => setOpen((v) => !v)}
              className="text-slate-500 hover:text-slate-300 transition-colors"
            >
              {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          )}
        </div>
      </div>
      {(!collapsible || open) && <div className="p-5">{children}</div>}
    </div>
  );
}

// ── Horizontal bar chart (div-based) ─────────────────────────────────────────

function HBarChart({ items, maxVal, colorKey = "bar" }) {
  if (!items || items.length === 0) {
    return <p className="text-xs text-slate-500 italic">No data.</p>;
  }
  const top = maxVal || Math.max(...items.map((i) => i.value || 0), 1);

  return (
    <div className="space-y-3">
      {items.map((item, idx) => {
        const color = item.color || AGENT_COLORS_ADMIN[item.key]?.bar || "#64748B";
        const w = pct(item.value, top);
        return (
          <div key={idx} className="flex items-center gap-3">
            <div className="w-20 text-[10px] text-slate-400 text-right flex-shrink-0 truncate" title={item.label}>
              {item.label}
            </div>
            <div className="flex-1 h-4 bg-[#1a3050] rounded-sm overflow-hidden">
              <div
                className="h-full rounded-sm transition-all duration-500"
                style={{ width: `${w}%`, backgroundColor: color }}
              />
            </div>
            <div className="w-14 text-[10px] text-slate-400 text-right flex-shrink-0">
              {typeof item.value === "number" ? fmtNum(item.value) : item.value}
              {item.pct != null ? ` (${item.pct}%)` : ""}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Vertical bar chart (div-based) ────────────────────────────────────────────

function VBarChart({ data, height = 100 }) {
  if (!data || data.length === 0) {
    return <p className="text-xs text-slate-500 italic">No data.</p>;
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
              className="w-full rounded-t-sm bg-[#0891B2] hover:bg-[#06B6D4] transition-colors"
              style={{ height: h }}
            />
            <div
              className="text-[8px] text-slate-600 mt-1 rotate-45 origin-left"
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

  return (
    <AdministrationLayout
      title="AI Operating System Center"
      subtitle="Usage analytics, cost tracking, and operational intelligence for Synaptiq AI OS"
      actions={
        <button
          onClick={refetchAll}
          className="flex items-center gap-2 px-3 py-1.5 text-xs border border-[#1a3050] text-slate-400 hover:text-white hover:border-[#0891B2] transition-colors"
        >
          <RefreshCw size={12} />
          Refresh All
        </button>
      }
    >

      {/* Section 1: KPI Cards */}
      <div className="grid grid-cols-5 gap-3">
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
      </div>

      {/* Section 2: Agent Usage Distribution */}
      <Section title="Agent Usage Distribution">
        {statsE ? (
          <Err message={statsE} onRetry={refStats} />
        ) : statsL ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Sk key={i} h="h-4" />
            ))}
          </div>
        ) : agentUsage.length === 0 ? (
          <p className="text-xs text-slate-500 italic">No agent usage data available.</p>
        ) : (
          <HBarChart items={agentUsage} />
        )}
      </Section>

      {/* Section 3: Daily Activity */}
      <Section title="Daily Message Activity (last 30 days)">
        {statsE ? (
          <Err message={statsE} onRetry={refStats} />
        ) : statsL ? (
          <Sk h="h-32" />
        ) : dailyActivity.length === 0 ? (
          <p className="text-xs text-slate-500 italic">No daily activity data available.</p>
        ) : (
          <div className="overflow-x-auto">
            <VBarChart data={dailyActivity} height={120} />
          </div>
        )}
      </Section>

      {/* Section 4: Top Users Table */}
      <Section title="Top Users by Activity" collapsible>
        {topE ? (
          <Err message={topE} onRetry={refTop} />
        ) : topL ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => <Sk key={i} h="h-8" />)}
          </div>
        ) : !topUsers || (Array.isArray(topUsers) ? topUsers : topUsers.users || []).length === 0 ? (
          <p className="text-xs text-slate-500 italic">No user data available.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[#1a3050]">
                  {["#", "Name", "Institution", "Messages", "Tokens", "Actions"].map((col) => (
                    <th
                      key={col}
                      className="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-widest text-slate-500"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(Array.isArray(topUsers) ? topUsers : topUsers.users || [])
                  .slice(0, 50)
                  .map((u, idx) => (
                    <tr
                      key={u.user_id || idx}
                      className="border-t border-[#1a3050] hover:bg-[#1a3050]/30 transition-colors"
                    >
                      <td className="px-3 py-2 text-slate-500 font-mono">{idx + 1}</td>
                      <td className="px-3 py-2 text-slate-200">
                        {u.full_name || u.name || u.email || "—"}
                      </td>
                      <td className="px-3 py-2 text-slate-400 truncate max-w-[160px]">
                        {u.institution || "—"}
                      </td>
                      <td className="px-3 py-2 text-white font-mono">{fmtNum(u.message_count)}</td>
                      <td className="px-3 py-2 text-slate-300 font-mono">{fmtNum(u.tokens_used)}</td>
                      <td className="px-3 py-2 text-slate-300 font-mono">{fmtNum(u.actions_count)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {/* Section 5: Actions Log */}
      <Section title="Actions Log" collapsible>
        {actE ? (
          <Err message={actE} onRetry={refAct} />
        ) : actL ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => <Sk key={i} h="h-8" />)}
          </div>
        ) : !actionsLog || (Array.isArray(actionsLog) ? actionsLog : actionsLog.actions || []).length === 0 ? (
          <p className="text-xs text-slate-500 italic">No actions logged yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[#1a3050]">
                  {["User", "Action Type", "Status", "Params", "Date"].map((col) => (
                    <th
                      key={col}
                      className="px-3 py-2 text-left text-[9px] font-semibold uppercase tracking-widest text-slate-500"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(Array.isArray(actionsLog) ? actionsLog : actionsLog.actions || [])
                  .slice(0, 100)
                  .map((a, idx) => {
                    const actionKey = (a.action_type || "").split("_")[0].toLowerCase();
                    const cls = ACTION_COLORS[actionKey] || "text-slate-400 border-slate-700 bg-slate-900/30";
                    return (
                      <tr
                        key={a.id || idx}
                        className="border-t border-[#1a3050] hover:bg-[#1a3050]/30 transition-colors"
                      >
                        <td className="px-3 py-2 text-slate-300">
                          {a.user_email || a.user_id || "—"}
                        </td>
                        <td className="px-3 py-2">
                          <span className={`text-[10px] px-2 py-0.5 border rounded-full ${cls}`}>
                            {a.action_type || "—"}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={`text-[10px] font-mono ${
                              a.status === "success" || a.status === "completed"
                                ? "text-emerald-400"
                                : a.status === "failed" || a.status === "error"
                                ? "text-red-400"
                                : "text-slate-400"
                            }`}
                          >
                            {a.status || "—"}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-slate-500 font-mono text-[10px] max-w-[200px] truncate">
                          {a.params
                            ? typeof a.params === "string"
                              ? a.params.slice(0, 60)
                              : JSON.stringify(a.params).slice(0, 60)
                            : "—"}
                        </td>
                        <td className="px-3 py-2 text-slate-500">
                          {fmtDateTime(a.created_at || a.timestamp)}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {/* Section 6: Cost Analytics */}
      <Section
        title="Cost Analytics"
        action={
          <span className="text-[9px] text-slate-600 italic">
            claude-sonnet-4-6: $3/M input · $15/M output
          </span>
        }
        collapsible
      >
        {costE ? (
          <Err message={costE} onRetry={refCost} />
        ) : costL ? (
          <div className="grid grid-cols-2 gap-4">
            <Sk h="h-24" />
            <Sk h="h-24" />
          </div>
        ) : !costData ? (
          <p className="text-xs text-slate-500 italic">No cost data available.</p>
        ) : (
          <div className="space-y-6">
            {/* Summary cards */}
            <div className="grid grid-cols-3 gap-4">
              <div className="border border-[#1a3050] bg-[#0B1C35] p-4">
                <div className="text-[9px] uppercase tracking-widest text-slate-500 mb-2">
                  Total Input Tokens
                </div>
                <div className="text-2xl text-white font-serif">
                  {fmtNum(costData.total_input_tokens)}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">
                  ≈ ${((costData.total_input_tokens || 0) / 1_000_000 * 3).toFixed(2)}
                </div>
              </div>
              <div className="border border-[#1a3050] bg-[#0B1C35] p-4">
                <div className="text-[9px] uppercase tracking-widest text-slate-500 mb-2">
                  Total Output Tokens
                </div>
                <div className="text-2xl text-white font-serif">
                  {fmtNum(costData.total_output_tokens)}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">
                  ≈ ${((costData.total_output_tokens || 0) / 1_000_000 * 15).toFixed(2)}
                </div>
              </div>
              <div className="border border-[#0891B2] bg-[#0B1C35] p-4">
                <div className="text-[9px] uppercase tracking-widest text-slate-500 mb-2 flex items-center gap-1">
                  <DollarSign size={10} />
                  Estimated Total Cost
                </div>
                <div className="text-2xl text-[#0891B2] font-serif">
                  {costData.estimated_cost_usd != null
                    ? `$${Number(costData.estimated_cost_usd).toFixed(2)}`
                    : fmtCost((costData.total_input_tokens || 0) + (costData.total_output_tokens || 0))}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">
                  blended avg rate applied
                </div>
              </div>
            </div>

            {/* Cost by agent */}
            {costByAgent.length > 0 && (
              <div>
                <div className="text-[9px] uppercase tracking-widest text-slate-500 mb-3">
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
                <div className="text-[9px] uppercase tracking-widest text-slate-500 mb-3">
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
          <Err message={memE} onRetry={refMem} />
        ) : memL ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <Sk key={i} h="h-5" />)}
          </div>
        ) : !memStats ? (
          <p className="text-xs text-slate-500 italic">No memory stats available.</p>
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-3 gap-4">
              <div className="border border-[#1a3050] bg-[#0B1C35] p-4">
                <div className="text-[9px] uppercase tracking-widest text-slate-500 mb-2">
                  Total Memory Items
                </div>
                <div className="text-2xl text-white font-serif">
                  {fmtNum(memStats.total_count || memStats.total)}
                </div>
              </div>
              <div className="border border-[#1a3050] bg-[#0B1C35] p-4">
                <div className="text-[9px] uppercase tracking-widest text-slate-500 mb-2">
                  Users with Memory
                </div>
                <div className="text-2xl text-white font-serif">
                  {fmtNum(memStats.users_with_memory)}
                </div>
              </div>
              <div className="border border-[#1a3050] bg-[#0B1C35] p-4">
                <div className="text-[9px] uppercase tracking-widest text-slate-500 mb-2">
                  Avg per User
                </div>
                <div className="text-2xl text-white font-serif">
                  {memStats.avg_per_user != null
                    ? Number(memStats.avg_per_user).toFixed(1)
                    : "—"}
                </div>
              </div>
            </div>

            {memByType.length > 0 && (
              <div>
                <div className="text-[9px] uppercase tracking-widest text-slate-500 mb-3">
                  Distribution by Memory Type
                </div>
                <HBarChart items={memByType} />
              </div>
            )}
          </div>
        )}
      </Section>

      {/* Footer note */}
      <div className="text-center text-[9px] text-slate-600 pb-4">
        Cost estimates based on claude-sonnet-4-6 pricing ($3/M input tokens · $15/M output tokens).
        Actual billing may vary.
      </div>
    </AdministrationLayout>
  );
}

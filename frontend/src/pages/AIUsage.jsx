/**
 * AI Usage dashboard — premium analytics view consuming /api/ai/usage and
 * /api/matching/analytics. Personal scope for users; admin sees global stats
 * with top journals/conferences/grants + top users.
 */
import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { WARM } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";
import {
  Sparkles, TrendingUp, Activity, Coins, BarChart3, BookOpen,
  CalendarDays, UserCheck, MessageSquare, Users, Award, ExternalLink,
} from "lucide-react";
import { AIWorkspaceLayout } from "@/layouts";


const KIND_META = {
  journal_matching:    { label: "Journal Match",     icon: BookOpen,    tone: "text-[#0F2847]", endpoint: "/journals" },
  conference_matching: { label: "Conference Match",  icon: CalendarDays, tone: "text-purple-700", endpoint: "/conferences" },
  grant_matching:      { label: "Grant Match",       icon: Coins,       tone: "text-emerald-700", endpoint: "/grants" },
  reviewer_matching:   { label: "Reviewer Match",    icon: UserCheck,   tone: "text-amber-700", endpoint: "/reviews" },
  assistant_message:   { label: "Copilot Messages",  icon: MessageSquare, tone: "text-slate-700", endpoint: null },
};

function Kpi({ label, value, sub, icon: Icon }) {
  return (
    <div className="border border-slate-200 bg-white p-5">
      <div className="flex items-center gap-2 overline">
        {Icon && <Icon size={11} strokeWidth={1.5} className="text-[#0F2847]" />}
        <span>{label}</span>
      </div>
      <div className="font-serif text-3xl text-slate-900 mt-2">{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1 font-mono">{sub}</div>}
    </div>
  );
}

function SparklineBars({ data, max }) {
  if (!data || data.length === 0) return <div className="text-xs text-slate-400">No activity in the last 30 days.</div>;
  const m = max || Math.max(...data.map((d) => d.credits || 0), 1);
  // Build 30-day window, fill missing days with 0.
  const days = [];
  const today = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today); d.setDate(today.getDate() - i);
    const iso = d.toISOString().slice(0, 10);
    const found = data.find((x) => x._id === iso);
    days.push({ date: iso, credits: found?.credits || 0 });
  }
  return (
    <div className="flex items-end gap-[3px] h-24" data-testid="usage-sparkline">
      {days.map((d, i) => {
        const h = Math.max(2, (d.credits / m) * 96);
        return (
          <div
            key={i}
            title={`${d.date} · ${d.credits} credits`}
            className={`flex-1 ${d.credits > 0 ? "bg-[#0F2847]" : "bg-slate-100"} hover:bg-amber-500 transition-colors`}
            style={{ height: h }}
          />
        );
      })}
    </div>
  );
}

function HBar({ label, value, max, sub, accent }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-900 truncate pr-2">{label}</span>
        <span className="font-mono text-slate-500 shrink-0">{sub || `${value}`}</span>
      </div>
      <div className="h-1.5 bg-slate-100 mt-1.5 relative overflow-hidden">
        <div className={`absolute inset-y-0 left-0 ${accent || "bg-[#0F2847]"}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function AIUsage() {
  const { user } = useAuth();
  const [usage, setUsage] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    Promise.all([
      api.get("/ai/usage").catch(() => ({ data: null })),
      api.get("/matching/analytics").catch(() => ({ data: null })),
    ]).then(([u, a]) => {
      if (!mounted) return;
      setUsage(u.data);
      setAnalytics(a.data);
    }).finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, []);

  const isAdmin = user?.role === "admin" || usage?.scope === "global";

  const byKind = usage?.by_kind || [];
  const totals = usage?.totals || { calls: 0, credits: 0 };
  const maxKindCredits = Math.max(...byKind.map((k) => k.credits || 0), 1);

  // From matching analytics: per-kind counts (journal/conference/grant/reviewer/assistant)
  const matchingByKind = analytics?.by_kind || [];
  const topJournals = analytics?.top_journals || [];
  const topConferences = analytics?.top_conferences || [];
  const topGrants = analytics?.top_grants || [];
  const topUsers = analytics?.top_users || [];

  // Combine assistant sessions: prefer chat_sessions count from analytics, fallback to ai_requests calls.
  const assistantSessions = analytics?.assistant_sessions ?? (byKind.find((k) => k._id === "assistant_message")?.calls || 0);

  return (
    <AIWorkspaceLayout
      title="AI Usage"
      subtitle={isAdmin ? "Platform-wide intelligence consumption, popular venues, and top users." : "Your Research Credit consumption, AI feature usage, and trends."}
    >
    <div className="space-y-8">
      <div className="border-b border-slate-200 pb-6 flex items-start justify-between gap-6">
        <div>
          {isAdmin && <span className="overline border border-amber-300 bg-amber-50 text-amber-700 px-1.5 py-0.5">admin · global view</span>}
        </div>
        <Link to="/pricing" className="text-xs inline-flex items-center gap-1.5 border border-[#0F2847] text-[#0F2847] px-3 py-1.5 hover:bg-[#0F2847] hover:text-white">
          Upgrade plan <ExternalLink size={11} strokeWidth={1.5} />
        </Link>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-slate-500 text-sm">
          <Spinner size={14} /> Loading analytics…
        </div>
      )}

      {!loading && (
        <>
          {/* Top KPI row */}
          <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3" data-testid="ai-usage-kpis">
            <Kpi
              label="Credits remaining"
              value={(usage?.credits_balance ?? 0).toLocaleString()}
              sub={`${(usage?.plan_code || "free").toString().toUpperCase()} plan`}
              icon={Coins}
            />
            <Kpi
              label="Credits used"
              value={(totals.credits || 0).toLocaleString()}
              sub={`${(totals.calls || 0).toLocaleString()} total calls`}
              icon={TrendingUp}
            />
            <Kpi
              label="Assistant sessions"
              value={assistantSessions.toLocaleString()}
              sub="Conversations with Copilot"
              icon={MessageSquare}
            />
            <Kpi
              label={isAdmin ? "Platform cost (est.)" : "Estimated cost"}
              value={`$${(usage?.cost_usd_estimate ?? 0).toFixed(2)}`}
              sub="LLM inference estimate"
              icon={BarChart3}
            />
          </section>

          {/* 30-day trend */}
          <section className="border border-slate-200 bg-white p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="flex items-center gap-2">
                  <Activity size={13} strokeWidth={1.5} className="text-[#0F2847]" />
                  <div className="overline">Last 30 days · credit consumption</div>
                </div>
                <h3 className="font-serif text-xl text-slate-900 mt-1">Consumption trend</h3>
              </div>
              <div className="text-right">
                <div className="font-mono text-xs text-slate-500">Total in window</div>
                <div className="font-serif text-2xl text-slate-900">{(usage?.last_30d || []).reduce((s, d) => s + (d.credits || 0), 0)}</div>
              </div>
            </div>
            <SparklineBars data={usage?.last_30d} />
          </section>

          {/* Feature breakdown */}
          <section className="grid lg:grid-cols-2 gap-5">
            <div className="border border-slate-200 bg-white p-6">
              <div className="overline mb-4">Most used AI features</div>
              {byKind.length === 0 && <div className="text-sm text-slate-500">No AI activity yet.</div>}
              <div className="space-y-4" data-testid="ai-usage-by-kind">
                {byKind.map((k) => {
                  const meta = KIND_META[k._id] || { label: k._id, icon: Sparkles, tone: "text-slate-700" };
                  const Icon = meta.icon;
                  return (
                    <div key={k._id}>
                      <div className="flex items-center justify-between text-xs">
                        <span className="inline-flex items-center gap-1.5">
                          <Icon size={12} strokeWidth={1.5} className={meta.tone} />
                          <span className="text-slate-900">{meta.label}</span>
                        </span>
                        <span className="font-mono text-slate-500">
                          {k.calls} {k.calls === 1 ? "call" : "calls"} · {k.credits} credits · {Math.round((k.avg_latency || 0) / 1000)}s avg
                        </span>
                      </div>
                      <div className="h-2 bg-slate-100 mt-1.5 relative overflow-hidden">
                        <div className="absolute inset-y-0 left-0 bg-[#0F2847]" style={{ width: `${Math.round((k.credits / maxKindCredits) * 100)}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="border border-slate-200 bg-white p-6">
              <div className="overline mb-4">Matching breakdown</div>
              {matchingByKind.length === 0 && <div className="text-sm text-slate-500">No matching activity yet.</div>}
              <div className="grid grid-cols-2 gap-3" data-testid="matching-breakdown">
                {matchingByKind.map((k) => {
                  const meta = KIND_META[`${k._id}_matching`] || KIND_META[k._id] || { label: k._id, icon: Sparkles, tone: "text-slate-700" };
                  const Icon = meta.icon;
                  return (
                    <div key={k._id} className="border border-slate-200 p-3">
                      <div className="flex items-center gap-2">
                        <Icon size={13} strokeWidth={1.5} className={meta.tone} />
                        <span className="text-xs text-slate-600">{meta.label.replace(" Match", "")}</span>
                      </div>
                      <div className="font-serif text-2xl text-slate-900 mt-1">{k.n}</div>
                      <div className="text-[10px] font-mono text-slate-400">matches found</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>

          {/* Popular venues — visible to all but more meaningful for admins */}
          {(topJournals.length > 0 || topConferences.length > 0 || topGrants.length > 0) && (
            <section className="grid md:grid-cols-3 gap-5" data-testid="popular-venues">
              <PopularList
                title="Most popular journals"
                items={topJournals.slice(0, 8)}
                getKey={(x) => x._id}
                getName={(x) => x.title || x.name || "Untitled"}
                getValue={(x) => x.n}
                getLink={(x) => `/journals/${x._id}`}
                icon={BookOpen}
                accent="bg-[#0F2847]"
              />
              <PopularList
                title="Most popular conferences"
                items={topConferences.slice(0, 8)}
                getKey={(x) => x._id}
                getName={(x) => x.name || x.title || "Untitled"}
                getValue={(x) => x.n}
                getLink={(x) => `/conferences/${x._id}`}
                icon={CalendarDays}
                accent="bg-purple-600"
              />
              <PopularList
                title="Most popular grants"
                items={topGrants.slice(0, 8)}
                getKey={(x) => x._id}
                getName={(x) => x.title || "Untitled"}
                getValue={(x) => x.n}
                getLink={(x) => `/grants/${x._id}`}
                icon={Coins}
                accent="bg-emerald-600"
              />
            </section>
          )}

          {/* Admin: top users / top consumers */}
          {isAdmin && topUsers.length > 0 && (
            <section className="border border-slate-200 bg-white p-6" data-testid="admin-top-users">
              <div className="flex items-center gap-2 mb-4">
                <Users size={13} strokeWidth={1.5} className="text-[#0F2847]" />
                <div className="overline">Top credit consumers</div>
              </div>
              <div className="space-y-3">
                {topUsers.slice(0, 10).map((u, i) => (
                  <div key={u._id || i} className="flex items-center gap-3 text-sm">
                    <span className="font-mono text-xs text-slate-400 w-5">{i + 1}.</span>
                    <Link to={`/profile/${u._id}`} className="flex-1 text-slate-900 hover:text-[#0F2847] truncate">{u.full_name || u._id}</Link>
                    <span className="font-mono text-xs text-slate-500">{u.calls} calls</span>
                    <span className="font-mono text-xs text-[#0F2847]">{u.credits} credits</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Recent activity */}
          {(analytics?.recent || []).length > 0 && (
            <section className="border border-slate-200 bg-white p-6" data-testid="recent-ai-activity">
              <div className="overline mb-3">Recent AI activity</div>
              <div className="divide-y divide-slate-100">
                {(analytics.recent || []).slice(0, 12).map((r, i) => {
                  const meta = KIND_META[`${r.kind}_matching`] || KIND_META[r.kind] || { label: r.kind, icon: Sparkles, tone: "text-slate-700" };
                  const Icon = meta.icon;
                  const cc = typeof r.credits_consumed === "number"
                    ? r.credits_consumed
                    : (r.credits_consumed?.consumed ?? 0);
                  return (
                    <div key={i} className="py-2.5 flex items-center gap-3 text-sm">
                      <Icon size={12} strokeWidth={1.5} className={meta.tone} />
                      <div className="min-w-0 flex-1">
                        <div className="text-slate-900 truncate">{meta.label}</div>
                        {r.input_summary && <div className="text-xs text-slate-500 truncate">{r.input_summary}</div>}
                      </div>
                      <span className="font-mono text-[10px] text-slate-400 shrink-0">
                        {r.created_at ? new Date(r.created_at).toLocaleString() : ""}
                      </span>
                      <span className="font-mono text-xs text-[#0F2847] shrink-0">−{cc}</span>
                    </div>
                  );
                })}
              </div>
            </section>
          )}
        </>
      )}
    </div>
    </AIWorkspaceLayout>
  );
}

function PopularList({ title, items, getKey, getName, getValue, getLink, icon: Icon, accent }) {
  const max = Math.max(...items.map(getValue), 1);
  return (
    <div className="border border-slate-200 bg-white p-5">
      <div className="flex items-center gap-2 mb-3">
        <Icon size={13} strokeWidth={1.5} className="text-[#0F2847]" />
        <div className="overline">{title}</div>
      </div>
      {items.length === 0 && <div className="text-xs text-slate-500">No data yet.</div>}
      <div className="space-y-3">
        {items.map((it) => (
          <Link key={getKey(it)} to={getLink(it)}>
            <HBar
              label={getName(it)}
              value={getValue(it)}
              max={max}
              sub={`${getValue(it)} match${getValue(it) === 1 ? "" : "es"}`}
              accent={accent}
            />
          </Link>
        ))}
      </div>
    </div>
  );
}

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
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Button } from "@/components/ds/Button";
import { StatCard, StatGrid } from "@/components/ds/StatCard";
import { BarChart, MiniBar } from "@/components/ds/Chart";
import { List, ListItem } from "@/components/ds/List";
import {
  Sparkles, TrendingUp, Activity, Coins, BarChart3, BookOpen,
  CalendarDays, UserCheck, MessageSquare, Users, Award, ExternalLink,
} from "lucide-react";
import { ResearchLayout } from "@/layouts";
import { AI_NAV_ITEMS } from "@/lib/navItems";


const KIND_META = {
  journal_matching:    { label: "Journal Match",     icon: BookOpen,    tone: "text-[#0F2847]", endpoint: "/journals" },
  conference_matching: { label: "Conference Match",  icon: CalendarDays, tone: "text-purple-700", endpoint: "/conferences" },
  grant_matching:      { label: "Grant Match",       icon: Coins,       tone: "text-emerald-700", endpoint: "/grants" },
  reviewer_matching:   { label: "Reviewer Match",    icon: UserCheck,   tone: "text-amber-700", endpoint: "/reviews" },
  assistant_message:   { label: "Copilot Messages",  icon: MessageSquare, tone: "text-slate-700", endpoint: null },
};

function SparklineBars({ data, max }) {
  if (!data || data.length === 0) return <div className="text-xs text-slate-400">No activity in the last 30 days.</div>;
  // Build 30-day window, fill missing days with 0.
  const days = [];
  const today = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today); d.setDate(today.getDate() - i);
    const iso = d.toISOString().slice(0, 10);
    const found = data.find((x) => x._id === iso);
    days.push({ date: iso, credits: found?.credits || 0 });
  }
  const chartData = days.map((d) => ({
    label: d.date,
    value: d.credits,
    color: d.credits > 0 ? "#0F2847" : "#F1F5F9",
  }));
  return (
    <div data-testid="usage-sparkline">
      <BarChart data={chartData} height={96} gap={3} />
    </div>
  );
}

function HBar({ label, value, max, sub, accent }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-900 truncate pr-2">{label}</span>
        <span className="font-mono text-slate-500 shrink-0">{sub || `${value}`}</span>
      </div>
      <div className="mt-1.5">
        <MiniBar value={value} max={max} color={accent} height={6} />
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
    <ResearchLayout
      navItems={AI_NAV_ITEMS}
      title="AI Usage"
      subtitle={isAdmin ? "Platform-wide intelligence consumption, popular venues, and top users." : "Your Research Credit consumption, AI feature usage, and trends."}
    >
    <div className="space-y-8">
      <div className="border-b border-slate-200 pb-6 flex items-start justify-between gap-6">
        <div>
          {isAdmin && <Badge variant="warning">admin · global view</Badge>}
        </div>
        <Button as={Link} to="/pricing" variant="outline" size="sm">
          Upgrade plan <ExternalLink size={11} strokeWidth={1.5} />
        </Button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-slate-500 text-sm">
          <Spinner size={14} /> Loading analytics…
        </div>
      )}

      {!loading && (
        <>
          {/* Top KPI row */}
          <section data-testid="ai-usage-kpis">
            <StatGrid cols={4}>
              <StatCard
                label="Credits remaining"
                value={(usage?.credits_balance ?? 0).toLocaleString()}
                sub={`${(usage?.plan_code || "free").toString().toUpperCase()} plan`}
                icon={<Coins />}
              />
              <StatCard
                label="Credits used"
                value={(totals.credits || 0).toLocaleString()}
                sub={`${(totals.calls || 0).toLocaleString()} total calls`}
                icon={<TrendingUp />}
              />
              <StatCard
                label="Assistant sessions"
                value={assistantSessions.toLocaleString()}
                sub="Conversations with Copilot"
                icon={<MessageSquare />}
              />
              <StatCard
                label={isAdmin ? "Platform cost (est.)" : "Estimated cost"}
                value={`$${(usage?.cost_usd_estimate ?? 0).toFixed(2)}`}
                sub="LLM inference estimate"
                icon={<BarChart3 />}
              />
            </StatGrid>
          </section>

          {/* 30-day trend */}
          <Card as="section" padding="lg">
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
          </Card>

          {/* Feature breakdown */}
          <section className="grid lg:grid-cols-2 gap-5">
            <Card padding="lg">
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
                      <div className="mt-1.5">
                        <MiniBar value={k.credits} max={maxKindCredits} color="#0F2847" height={8} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            <Card padding="lg">
              <div className="overline mb-4">Matching breakdown</div>
              {matchingByKind.length === 0 && <div className="text-sm text-slate-500">No matching activity yet.</div>}
              <div className="grid grid-cols-2 gap-3" data-testid="matching-breakdown">
                {matchingByKind.map((k) => {
                  const meta = KIND_META[`${k._id}_matching`] || KIND_META[k._id] || { label: k._id, icon: Sparkles, tone: "text-slate-700" };
                  const Icon = meta.icon;
                  return (
                    <Card key={k._id} padding="sm">
                      <div className="flex items-center gap-2">
                        <Icon size={13} strokeWidth={1.5} className={meta.tone} />
                        <span className="text-xs text-slate-600">{meta.label.replace(" Match", "")}</span>
                      </div>
                      <div className="font-serif text-2xl text-slate-900 mt-1">{k.n}</div>
                      <div className="text-[10px] font-mono text-slate-400">matches found</div>
                    </Card>
                  );
                })}
              </div>
            </Card>
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
                accent="#0F2847"
              />
              <PopularList
                title="Most popular conferences"
                items={topConferences.slice(0, 8)}
                getKey={(x) => x._id}
                getName={(x) => x.name || x.title || "Untitled"}
                getValue={(x) => x.n}
                getLink={(x) => `/conferences/${x._id}`}
                icon={CalendarDays}
                accent="#9333EA"
              />
              <PopularList
                title="Most popular grants"
                items={topGrants.slice(0, 8)}
                getKey={(x) => x._id}
                getName={(x) => x.title || "Untitled"}
                getValue={(x) => x.n}
                getLink={(x) => `/grants/${x._id}`}
                icon={Coins}
                accent="#059669"
              />
            </section>
          )}

          {/* Admin: top users / top consumers */}
          {isAdmin && topUsers.length > 0 && (
            <Card as="section" padding="lg" data-testid="admin-top-users">
              <div className="flex items-center gap-2 mb-4">
                <Users size={13} strokeWidth={1.5} className="text-[#0F2847]" />
                <div className="overline">Top credit consumers</div>
              </div>
              <List border={false} divided>
                {topUsers.slice(0, 10).map((u, i) => (
                  <ListItem
                    key={u._id || i}
                    to={`/profile/${u._id}`}
                    leading={<span className="font-mono text-xs text-slate-400 w-5 inline-block">{i + 1}.</span>}
                    title={u.full_name || u._id}
                    trailing={
                      <span className="flex items-center gap-3">
                        <span className="font-mono text-xs text-slate-500">{u.calls} calls</span>
                        <span className="font-mono text-xs text-[#0F2847]">{u.credits} credits</span>
                      </span>
                    }
                  />
                ))}
              </List>
            </Card>
          )}

          {/* Recent activity */}
          {(analytics?.recent || []).length > 0 && (
            <Card as="section" padding="lg" data-testid="recent-ai-activity">
              <div className="overline mb-3">Recent AI activity</div>
              <List border={false} divided>
                {(analytics.recent || []).slice(0, 12).map((r, i) => {
                  const meta = KIND_META[`${r.kind}_matching`] || KIND_META[r.kind] || { label: r.kind, icon: Sparkles, tone: "text-slate-700" };
                  const Icon = meta.icon;
                  const cc = typeof r.credits_consumed === "number"
                    ? r.credits_consumed
                    : (r.credits_consumed?.consumed ?? 0);
                  return (
                    <ListItem
                      key={i}
                      compact
                      leading={<Icon size={12} strokeWidth={1.5} className={meta.tone} />}
                      title={meta.label}
                      subtitle={r.input_summary || undefined}
                      trailing={
                        <span className="flex items-center gap-3">
                          <span className="font-mono text-[10px] text-slate-400 shrink-0">
                            {r.created_at ? new Date(r.created_at).toLocaleString() : ""}
                          </span>
                          <span className="font-mono text-xs text-[#0F2847] shrink-0">−{cc}</span>
                        </span>
                      }
                    />
                  );
                })}
              </List>
            </Card>
          )}
        </>
      )}
    </div>
    </ResearchLayout>
  );
}

function PopularList({ title, items, getKey, getName, getValue, getLink, icon: Icon, accent }) {
  const max = Math.max(...items.map(getValue), 1);
  return (
    <Card padding="md">
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
    </Card>
  );
}

/* eslint-disable */
import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, Cell,
} from "recharts";
import {
  BookOpen, ClipboardCheck, FolderOpen, Award, Sparkles,
  Users, Activity, TrendingUp, BarChart2, Zap, Lightbulb,
  Brain, RefreshCw, CheckCircle,
} from "lucide-react";
import api from "../../lib/api";
import { toast } from "sonner";
import { getLevel } from "../../hooks/useReputation";
import { NAVY } from "@/lib/tokens";
import { SkeletonCard } from "@/components/ds/LoadingState";
import { ErrorState as DsErrorState } from "@/components/ds/ErrorState";
import { EmptyState } from "@/components/ds/EmptyState";
import { StatCard } from "@/components/ds/StatCard";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { NavTabs } from "@/components/ds/NavTabs";
import { List, ListItem } from "@/components/ds/List";
import { Alert, Callout } from "@/components/ds/Alert";
import { AnalyticsLayout } from "@/layouts";

// ── Period picker ──────────────────────────────────────────────────────────────
const PERIODS = [
  { value: "today", label: "Today" },
  { value: "7d",    label: "7 days" },
  { value: "30d",   label: "30 days" },
  { value: "90d",   label: "90 days" },
  { value: "all",   label: "All time" },
];

// ── Tab definitions ────────────────────────────────────────────────────────────
const TABS = [
  { id: "overview",      label: "Overview",       icon: BarChart2,      endpoint: "overview",      hasPeriod: true  },
  { id: "lessons",       label: "Lessons",        icon: BookOpen,       endpoint: "lessons",       hasPeriod: true  },
  { id: "assessments",   label: "Assessments",    icon: ClipboardCheck, endpoint: "assessments",   hasPeriod: true  },
  { id: "workspaces",    label: "Workspaces",     icon: FolderOpen,     endpoint: "workspaces",    hasPeriod: true  },
  { id: "collaboration", label: "Collaboration",  icon: Users,          endpoint: "collaboration",  hasPeriod: true  },
  { id: "ai-usage",      label: "AI Usage",       icon: Sparkles,       endpoint: "ai-usage",       hasPeriod: true  },
  { id: "portfolio",     label: "Portfolio",      icon: Award,          endpoint: "portfolio",      hasPeriod: true  },
  { id: "reputation",    label: "Reputation",     icon: TrendingUp,     endpoint: "reputation",     hasPeriod: false },
  { id: "productivity",  label: "Productivity",   icon: Zap,            endpoint: "productivity",   hasPeriod: false },
  { id: "insights",      label: "Insights",       icon: Lightbulb,      endpoint: "insights",       hasPeriod: false },
];

// ── Chart colours ──────────────────────────────────────────────────────────────
const PRIMARY   = "#0F2847";
const SECONDARY = "#94a3b8";
const ACCENT    = "#10b981";

// ── Shared sub-components ──────────────────────────────────────────────────────

function SectionTitle({ children }) {
  return <div className="overline mb-4">{children}</div>;
}

function TrendChart({ data, color = PRIMARY, height = 160 }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center bg-slate-50 border border-dashed border-slate-200" style={{ height }}>
        <span className="text-xs text-slate-400">No activity in this period</span>
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#94a3b8" }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 9, fill: "#94a3b8" }} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip
          contentStyle={{ border: "1px solid #e2e8f0", borderRadius: 0, padding: "6px 10px", fontSize: 12 }}
          labelStyle={{ color: "#475569", fontSize: 10 }}
        />
        <Line type="monotone" dataKey="count" stroke={color} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function DistBar({ data, color = PRIMARY, height = 180 }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center bg-slate-50 border border-dashed border-slate-200" style={{ height }}>
        <span className="text-xs text-slate-400">No data yet</span>
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 9, fill: "#94a3b8" }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 9, fill: "#94a3b8" }} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip contentStyle={{ border: "1px solid #e2e8f0", borderRadius: 0, padding: "6px 10px", fontSize: 12 }} />
        <Bar dataKey="count" fill={color} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function ScoreBar({ label, score, color = PRIMARY }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-700">{label}</span>
        <span className="font-mono font-medium text-slate-900">{score}</span>
      </div>
      <div className="h-2 bg-slate-100 relative">
        <div className="absolute inset-y-0 left-0 transition-all" style={{ width: `${score}%`, background: color }} />
      </div>
    </div>
  );
}

function Loading() {
  return <div className="p-6"><SkeletonCard rows={5} /></div>;
}

// ── Health badge ───────────────────────────────────────────────────────────────
// Maps cleanly onto the fixed Badge variants — no arbitrary color needed.
const HEALTH_BADGE_VARIANT = {
  Excellent:         "success",
  Healthy:           "info",
  "Needs Attention": "warning",
  Inactive:          "neutral",
};

function HealthBadge({ label }) {
  return (
    <Badge variant={HEALTH_BADGE_VARIANT[label] || "neutral"} size="sm">
      {label}
    </Badge>
  );
}

// ── Insight icon ───────────────────────────────────────────────────────────────
const INSIGHT_ICONS = {
  growth:     "📈",
  trend:      "🔥",
  suggestion: "💡",
  achievement: "🏆",
  strength:   "💪",
  gap:        "⚠️",
};

// ══════════════════════════════════════════════════════════════════════════════
// Main page
// ══════════════════════════════════════════════════════════════════════════════

export default function TeachingAnalytics() {
  const [tab, setTab]       = useState("overview");
  const [period, setPeriod] = useState("30d");
  const [data, setData]     = useState({});
  const [loading, setLoading] = useState({});
  const [errors, setErrors] = useState({});

  const cacheKey = useCallback((section) => {
    const t = TABS.find((x) => x.id === section);
    return t?.hasPeriod ? `${section}:${period}` : section;
  }, [period]);

  const fetchSection = useCallback(async (section) => {
    const key = cacheKey(section);
    if (data[key]) return;

    const t = TABS.find((x) => x.id === section);
    setLoading((p) => ({ ...p, [section]: true }));
    setErrors((p) => ({ ...p, [section]: false }));
    try {
      const params = t?.hasPeriod ? { period } : {};
      const { data: d } = await api.get(`/teaching-analytics/${t?.endpoint || section}`, { params });
      setData((p) => ({ ...p, [key]: d }));
    } catch (_) {
      setErrors((p) => ({ ...p, [section]: true }));
      toast.error("Failed to load analytics section");
    } finally {
      setLoading((p) => ({ ...p, [section]: false }));
    }
  }, [cacheKey, data, period]);

  // Fetch current tab on mount and whenever tab/period changes
  useEffect(() => {
    fetchSection(tab);
  }, [tab, period]); // eslint-disable-line react-hooks/exhaustive-deps

  const d   = data[cacheKey(tab)];
  const isL = loading[tab];
  const isE = errors[tab];

  const retry = () => {
    const key = cacheKey(tab);
    setData((p) => { const next = { ...p }; delete next[key]; return next; });
    fetchSection(tab);
  };

  return (
    <AnalyticsLayout
      title="Teaching Analytics"
      subtitle="Intelligence derived from your real platform activity"
      icon={BarChart2}
      toolbar={
        <NavTabs
          variant="segment"
          size="sm"
          tabs={PERIODS.map((p) => ({ id: p.value, label: p.label }))}
          active={period}
          onChange={setPeriod}
        />
      }
      nav={
        <NavTabs
          className="overflow-x-auto scrollbar-none"
          size="sm"
          tabs={TABS.map(({ id, label, icon }) => ({ id, label, icon }))}
          active={tab}
          onChange={setTab}
        />
      }
    >
      {/* ── Tab content ─────────────────────────────────────────────────────── */}
      <div className="pt-6">
        {isL && <Loading />}
        {isE && <DsErrorState message="Failed to load analytics" onRetry={retry} />}
        {!isL && !isE && d && (
          <>
            {/* ── 1. Overview ─────────────────────────────────────────────── */}
            {tab === "overview" && (
              <div className="space-y-8">
                <div>
                  <SectionTitle>All-time totals</SectionTitle>
                  <div className="grid sm:grid-cols-3 lg:grid-cols-4 gap-4">
                    <StatCard label="Lessons"        value={d.totals?.lessons}         icon={<BookOpen />}      />
                    <StatCard label="Assessments"    value={d.totals?.assessments}      icon={<ClipboardCheck />} />
                    <StatCard label="Workspaces"     value={d.totals?.workspaces}       icon={<FolderOpen />}    />
                    <StatCard label="Portfolio Items" value={d.totals?.portfolio_items} icon={<Award />}         />
                    <StatCard label="AI Sessions"    value={d.totals?.ai_sessions}      icon={<Sparkles />}      />
                    <StatCard label="Collaborations" value={d.totals?.collaborations}   icon={<Users />}         />
                    <StatCard label="Invitations Sent" value={d.totals?.invitations}   icon={<Activity />}      />
                  </div>
                </div>

                <div>
                  <SectionTitle>This period</SectionTitle>
                  <div className="grid sm:grid-cols-3 lg:grid-cols-4 gap-4">
                    <StatCard label="Lessons"         value={d.period_counts?.lessons}         highlight />
                    <StatCard label="Assessments"     value={d.period_counts?.assessments}     highlight />
                    <StatCard label="Workspaces"      value={d.period_counts?.workspaces}      highlight />
                    <StatCard label="Portfolio Items" value={d.period_counts?.portfolio_items} highlight />
                    <StatCard label="AI Sessions"     value={d.period_counts?.ai_sessions}     highlight />
                    <StatCard label="Collaborations"  value={d.period_counts?.collaborations}  highlight />
                    <StatCard label="Invitations"     value={d.period_counts?.invitations}     highlight />
                  </div>
                </div>

                <div className="grid sm:grid-cols-3 gap-4">
                  <Card padding="lg">
                    <div className="overline text-slate-500 mb-3">Teaching Reputation</div>
                    <div className="font-serif text-4xl text-[#0F2847]">{d.reputation?.teaching_score ?? 0}</div>
                    <div className="text-xs text-slate-500 mt-0.5">/ 100</div>
                  </Card>
                  <Card padding="lg">
                    <div className="overline text-slate-500 mb-3">Community Reputation</div>
                    <div className="font-serif text-4xl text-[#0F2847]">{d.reputation?.community_score ?? 0}</div>
                    <div className="text-xs text-slate-500 mt-0.5">/ 100</div>
                  </Card>
                  <Card padding="lg">
                    <div className="overline text-slate-500 mb-3">Overall Reputation</div>
                    <div className="font-serif text-4xl text-[#0F2847]">{d.reputation?.overall ?? 0}</div>
                    <div className="text-xs text-slate-500 mt-0.5">/ 100 · {getLevel(d.reputation?.overall || 0)}</div>
                  </Card>
                </div>
              </div>
            )}

            {/* ── 2. Lessons ──────────────────────────────────────────────── */}
            {tab === "lessons" && (
              <div className="space-y-8">
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <StatCard label="Created"            value={d.created}         icon={<BookOpen />} highlight />
                  <StatCard label="Updated"            value={d.updated}         icon={<Activity />}       />
                  <StatCard label="Collab Edited"      value={d.collab_edited}   icon={<Users />}          />
                  <StatCard label="Versions Saved"     value={d.versions_saved}  icon={<RefreshCw />}      />
                  <StatCard label="Restored"           value={d.restored}        icon={<RefreshCw />}      />
                </div>

                <div>
                  <SectionTitle>Lesson creation trend</SectionTitle>
                  <TrendChart data={d.trend} />
                </div>

                <div className="grid sm:grid-cols-2 gap-8">
                  <div>
                    <SectionTitle>By subject</SectionTitle>
                    <DistBar data={d.by_subject} />
                  </div>
                  <div>
                    <SectionTitle>By level</SectionTitle>
                    <DistBar data={d.by_level} color={ACCENT} />
                  </div>
                </div>

                <div>
                  <SectionTitle>By status</SectionTitle>
                  <DistBar data={d.by_status} color={SECONDARY} height={120} />
                </div>
              </div>
            )}

            {/* ── 3. Assessments ──────────────────────────────────────────── */}
            {tab === "assessments" && (
              <div className="space-y-8">
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <StatCard label="Created"          value={d.created}          icon={<ClipboardCheck />} highlight />
                  <StatCard label="Total Questions"  value={d.total_questions}  icon={<Brain />}          />
                  <StatCard label="Rubrics"          value={d.rubrics_created}  icon={<Award />}          />
                  <StatCard label="Versions Saved"   value={d.versions_saved}   icon={<RefreshCw />}      />
                  <StatCard label="Collab Edited"    value={d.collab_edited}    icon={<Users />}          />
                </div>

                <div>
                  <SectionTitle>Assessment creation trend</SectionTitle>
                  <TrendChart data={d.trend} />
                </div>

                <div className="grid sm:grid-cols-2 gap-8">
                  <div>
                    <SectionTitle>By assessment type</SectionTitle>
                    <DistBar data={d.by_type} />
                  </div>
                  <div>
                    <SectionTitle>By subject</SectionTitle>
                    <DistBar data={d.by_subject} color={ACCENT} />
                  </div>
                </div>
              </div>
            )}

            {/* ── 4. Workspaces ───────────────────────────────────────────── */}
            {tab === "workspaces" && (
              <div className="space-y-8">
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <StatCard label="Total Workspaces"  value={d.total_workspaces} icon={<FolderOpen />} />
                  <StatCard label="Created"           value={d.created}          highlight           />
                  <StatCard label="Invitations Sent"  value={d.invites_sent}     icon={<Activity />}  />
                  <StatCard label="Invites Accepted"  value={d.invites_accepted} icon={<CheckCircle />} highlight />
                  <StatCard label="Comments"          value={d.comments}         icon={<Activity />}  />
                  <StatCard label="Version Events"    value={d.version_events}   icon={<RefreshCw />} />
                </div>

                <div>
                  <SectionTitle>Workspace health</SectionTitle>
                  <List className="divide-y divide-slate-100">
                    {(d.workspace_health || []).length === 0 && (
                      <div className="px-6 py-8 text-sm text-slate-400 text-center italic">
                        No workspaces yet. <Link to="/teaching/workspaces" className="text-[#0F2847] hover:underline">Create one →</Link>
                      </div>
                    )}
                    {(d.workspace_health || []).map((ws) => (
                      <div key={ws.id} className="px-5 py-4 flex items-center gap-4">
                        <div className="flex-1 min-w-0">
                          <Link
                            to={`/teaching/workspaces/${ws.id}`}
                            className="font-medium text-sm text-slate-900 hover:text-[#0F2847] truncate block"
                          >
                            {ws.title}
                          </Link>
                          <div className="text-xs text-slate-500 mt-0.5">
                            {ws.member_count} member{ws.member_count !== 1 ? "s" : ""}
                            {" · "}{ws.activity_30d} activity events
                            {" · "}{ws.comments_30d} comments (30d)
                          </div>
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          <div className="text-right">
                            <div className="font-serif text-xl text-slate-900">{ws.health_score}</div>
                            <div className="text-[10px] text-slate-400">/ 100</div>
                          </div>
                          <HealthBadge label={ws.health_label} />
                        </div>
                      </div>
                    ))}
                  </List>
                </div>

                {(d.role_distribution || []).length > 0 && (
                  <div>
                    <SectionTitle>Member role distribution (your workspaces)</SectionTitle>
                    <DistBar
                      data={(d.role_distribution || []).map((r) => ({
                        label: r.role.replace(/_/g, " "),
                        count: r.count,
                      }))}
                      height={140}
                    />
                  </div>
                )}
              </div>
            )}

            {/* ── 5. Collaboration ────────────────────────────────────────── */}
            {tab === "collaboration" && (
              <div className="space-y-8">
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <StatCard label="Collaborations"    value={d.collaborations_total} icon={<Users />}        />
                  <StatCard label="This Period"       value={d.collaborations}       highlight               />
                  <StatCard label="Invites Sent"      value={d.invites_sent}         icon={<Activity />}     />
                  <StatCard label="Invites Accepted"  value={d.invites_accepted}     icon={<CheckCircle />} highlight />
                  <StatCard label="Invites Declined"  value={d.invites_declined}     icon={<Activity />}     />
                  <StatCard label="Acceptance Rate"   value={`${d.acceptance_rate}%`} icon={<TrendingUp />}   />
                </div>

                {(d.by_collab_type || []).length > 0 && (
                  <div>
                    <SectionTitle>Collaboration type distribution</SectionTitle>
                    <DistBar data={d.by_collab_type} height={140} />
                  </div>
                )}

                {(d.top_contributors || []).length > 0 && (
                  <div>
                    <SectionTitle>Top contributors to your workspaces</SectionTitle>
                    <List className="divide-y divide-slate-100">
                      {d.top_contributors.map((c, i) => (
                        <ListItem
                          key={i}
                          title={c.name}
                          trailing={<span className="text-sm font-mono text-slate-600">{c.contributions} events</span>}
                        />
                      ))}
                    </List>
                  </div>
                )}
              </div>
            )}

            {/* ── 6. AI Usage ─────────────────────────────────────────────── */}
            {tab === "ai-usage" && (
              <div className="space-y-8">
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <StatCard label="AI Sessions (all)"     value={d.total_messages}              icon={<Sparkles />}      />
                  <StatCard label="AI Sessions (period)"  value={d.period_messages}             icon={<Sparkles />} highlight />
                  <StatCard label="Credits Consumed"      value={d.credits_consumed}            icon={<Zap />}           />
                  <StatCard label="Lessons Generated"     value={d.lesson_plans_generated}      icon={<BookOpen />}      />
                  <StatCard label="Assessments Generated" value={d.assessments_generated}       icon={<ClipboardCheck />} />
                  <StatCard label="Total Lessons Gen."    value={d.lesson_plans_generated_total} icon={<BookOpen />}     />
                  <StatCard label="Total Assess. Gen."    value={d.assessments_generated_total}  icon={<ClipboardCheck />} />
                </div>

                <div>
                  <SectionTitle>AI usage trend</SectionTitle>
                  <TrendChart data={d.trend} color={ACCENT} />
                </div>

                {(d.by_workspace || []).length > 0 && (
                  <div>
                    <SectionTitle>Usage by workspace</SectionTitle>
                    <DistBar
                      data={(d.by_workspace || []).map((w) => ({
                        label: w.workspace,
                        count: w.messages,
                      }))}
                      color={PRIMARY}
                    />
                  </div>
                )}
              </div>
            )}

            {/* ── 7. Portfolio ─────────────────────────────────────────────── */}
            {tab === "portfolio" && (
              <div className="space-y-8">
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <StatCard label="Total Items"     value={d.total_items}       icon={<Award />}       />
                  <StatCard label="Added (period)"  value={d.period_items}      highlight             />
                  <StatCard label="Featured"        value={d.featured_items}    icon={<Award />}       />
                  <StatCard label="Completeness"    value={`${d.completeness_score}%`} icon={<CheckCircle />} highlight />
                </div>

                <div>
                  <SectionTitle>Completeness score</SectionTitle>
                  <Card padding="xl">
                    <div className="flex items-baseline gap-3 mb-4">
                      <span className="font-serif text-4xl text-slate-900">{d.completeness_score}%</span>
                      <span className="text-sm text-slate-500">portfolio completeness</span>
                    </div>
                    <div className="h-3 bg-slate-100 relative mb-4">
                      <div
                        className="absolute inset-y-0 left-0 transition-all"
                        style={{
                          width: `${d.completeness_score}%`,
                          background: d.completeness_score >= 80 ? ACCENT : PRIMARY,
                        }}
                      />
                    </div>
                    <p className="text-xs text-slate-500">
                      Based on presence of: lesson, course, assessment, achievement, reflection, publication items.
                    </p>
                  </Card>
                </div>

                <div>
                  <SectionTitle>Portfolio growth trend</SectionTitle>
                  <TrendChart data={d.trend} color={ACCENT} />
                </div>

                <div className="grid sm:grid-cols-2 gap-8">
                  <div>
                    <SectionTitle>By item type</SectionTitle>
                    <DistBar data={d.by_type} />
                  </div>
                  <div>
                    <SectionTitle>Professional timeline (recent)</SectionTitle>
                    <div className="space-y-2">
                      {(d.timeline || []).length === 0 && (
                        <div className="text-sm text-slate-400 italic text-center py-8">No portfolio items yet.</div>
                      )}
                      {(d.timeline || []).map((t, i) => (
                        <div key={i} className="flex items-start gap-3 py-2 border-b border-slate-100">
                          <div className="text-[10px] font-mono text-slate-400 mt-0.5 shrink-0 w-20">{t.date || "—"}</div>
                          <div className="min-w-0">
                            <div className="text-sm text-slate-900 truncate">{t.title}</div>
                            <div className="text-[10px] text-slate-500 capitalize">{t.type}</div>
                          </div>
                          {t.featured && (
                            <Badge variant="warning" size="sm" className="shrink-0">Featured</Badge>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ── 8. Reputation ────────────────────────────────────────────── */}
            {tab === "reputation" && (
              <div className="space-y-8">
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <StatCard label="Overall"          value={d.overall}          icon={<TrendingUp />} highlight />
                  <StatCard label="Teaching Score"   value={d.teaching_score}   icon={<BookOpen />}         />
                  <StatCard label="Community Score"  value={d.community_score}  icon={<Users />}            />
                  <StatCard label="Research Score"   value={d.research_score}   icon={<BarChart2 />}        />
                  <StatCard label="Total Badges"     value={d.badge_count}      icon={<Award />}            />
                  <StatCard label="Teaching Badges"  value={d.teaching_badge_count}  icon={<Award />}      />
                  <StatCard label="Community Badges" value={d.community_badge_count} icon={<Award />}      />
                </div>

                <Card padding="xl" className="space-y-5">
                  <SectionTitle>Score breakdown</SectionTitle>
                  <ScoreBar label="Teaching"   score={d.teaching_score  || 0} color={PRIMARY} />
                  <ScoreBar label="Community"  score={d.community_score || 0} color={ACCENT}  />
                  <ScoreBar label="Research"   score={d.research_score  || 0} color={SECONDARY} />
                  <ScoreBar label="Overall"    score={d.overall         || 0} color={PRIMARY} />
                </Card>

                {(d.computed_at) && (
                  <div className="text-xs text-slate-400">
                    Last computed: {new Date(d.computed_at).toLocaleString()}
                    {" · "}
                    <Link to="/academic-passport" className="text-[#0F2847] hover:underline">
                      View full reputation profile →
                    </Link>
                  </div>
                )}

                {(d.badges || []).length > 0 && (
                  <div>
                    <SectionTitle>Badges earned</SectionTitle>
                    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {(d.badges || []).map((b, i) => (
                        <Card key={i} padding="md" className="flex items-start gap-3">
                          <span className="text-2xl">{b.icon || "🏅"}</span>
                          <div>
                            <div className="text-sm font-medium text-slate-900">{b.name}</div>
                            <div className="text-xs text-slate-500 mt-0.5">{b.description || b.category}</div>
                          </div>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── 9. Productivity ──────────────────────────────────────────── */}
            {tab === "productivity" && (
              <div className="space-y-8">
                <div className="grid sm:grid-cols-3 gap-6">
                  <Card padding="xl" className="sm:col-span-1">
                    <div className="overline text-slate-500 mb-3">Productivity Score</div>
                    <div className="font-serif text-5xl text-[#0F2847]">{d.productivity_score}</div>
                    <div className="text-sm text-slate-500 mt-1">{d.score_label}</div>
                    <div className="mt-4 h-2 bg-slate-100 relative">
                      <div
                        className="absolute inset-y-0 left-0"
                        style={{
                          width: `${d.productivity_score}%`,
                          background: d.productivity_score >= 80 ? ACCENT : PRIMARY,
                        }}
                      />
                    </div>
                    <div className="text-xs text-slate-400 mt-2">Based on 30-day rolling activity</div>
                  </Card>

                  <Card padding="xl" className="sm:col-span-2 space-y-4">
                    <div className="overline text-slate-500">Components</div>
                    <div className="grid sm:grid-cols-2 gap-4 text-sm">
                      {[
                        { label: "Lessons (30d)",     value: d.components?.content_creation?.lessons },
                        { label: "Assessments (30d)", value: d.components?.content_creation?.assessments },
                        { label: "WS Activity (30d)", value: d.components?.collaboration?.workspace_activity },
                        { label: "Invitations (30d)", value: d.components?.collaboration?.invitations },
                        { label: "Versions (30d)",    value: d.components?.depth?.versions },
                        { label: "Comments (30d)",    value: d.components?.depth?.comments },
                        { label: "AI Sessions (30d)", value: d.components?.engagement?.ai_sessions },
                        { label: "Portfolio (30d)",   value: d.components?.engagement?.portfolio_items },
                      ].map(({ label, value }) => (
                        <div key={label} className="flex items-baseline justify-between border-b border-slate-100 pb-1">
                          <span className="text-slate-600 text-xs">{label}</span>
                          <span className="font-mono text-sm text-slate-900">{value ?? 0}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>

                <div className="grid sm:grid-cols-2 gap-6">
                  <StatCard label="This week (lessons + assessments)" value={d.this_week} icon={<Zap />} highlight />
                </div>

                {(d.suggestions || []).length > 0 && (
                  <div>
                    <SectionTitle>Improvement suggestions</SectionTitle>
                    <div className="space-y-3">
                      {d.suggestions.map((s, i) => (
                        <Alert key={i} variant="warning" icon={Lightbulb}>{s}</Alert>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── 10. Insights ─────────────────────────────────────────────── */}
            {tab === "insights" && (
              <div className="space-y-6">
                <div className="text-xs text-slate-400">
                  Auto-generated from your real teaching activity · updated every 5 minutes
                  {d.generated_at && ` · ${new Date(d.generated_at).toLocaleString()}`}
                </div>

                {(d.insights || []).length === 0 && (
                  <EmptyState
                    icon={<Lightbulb />}
                    title="No insights yet"
                    description="Start creating lessons and assessments to generate analytics."
                    action={
                      <Link to="/teaching/lesson-planner" className="text-sm text-[#0F2847] hover:underline">
                        Go to Lesson Planner →
                      </Link>
                    }
                  />
                )}

                <div className="grid sm:grid-cols-2 gap-4">
                  {(d.insights || []).map((ins, i) => (
                    <Card key={i} padding="lg">
                      <div className="flex items-start gap-3">
                        <span className="text-2xl mt-0.5">{INSIGHT_ICONS[ins.type] || "📌"}</span>
                        <div>
                          <div className={`text-[10px] uppercase tracking-widest font-semibold mb-1.5 ${
                            ins.type === "growth" || ins.type === "achievement" || ins.type === "strength"
                              ? "text-emerald-600"
                              : ins.type === "gap"
                              ? "text-red-500"
                              : "text-amber-600"
                          }`}>
                            {ins.type}
                          </div>
                          <p className="text-sm text-slate-700 leading-relaxed">{ins.text}</p>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>

                <Callout variant="neutral">
                  <strong className="text-slate-700">How insights are generated:</strong>{" "}
                  All insights compare your current 30-day activity against the prior 30-day window.
                  No AI generation — all signals derive from real collection counts.
                </Callout>
              </div>
            )}
          </>
        )}
      </div>
    </AnalyticsLayout>
  );
}

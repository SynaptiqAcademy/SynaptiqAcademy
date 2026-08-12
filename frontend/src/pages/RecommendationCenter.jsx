/**
 * RecommendationCenter — Full proactive recommendations page (Phase XXX).
 *
 * Route: /recommendation-center
 *
 * Shows: health score breakdown, opportunity score, all recommendations
 * filterable by category, weekly insights, and learning stats.
 */

import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { ResearchLayout } from "@/layouts";
import { AI_NAV_ITEMS } from "@/lib/navItems";
import {
  Sparkles, TrendingUp, Activity, BarChart2, Users, FileText,
  BadgeDollarSign, GraduationCap, Building2, Briefcase, Zap,
  BookMarked, RefreshCw, ChevronRight,
} from "lucide-react";
import {
  getRecommendations, getHealthScore, getOpportunityScore, getInsights, getBriefing,
} from "../services/proactiveEngine";
import RecommendationCard from "../components/proactive/RecommendationCard";
import { NAVY, ACCENT, WARM } from "@/lib/tokens";
import { Button } from "@/components/ds/Button";
import { Tag } from "@/components/ds/Tag";
import { EmptyState } from "@/components/ds/EmptyState";
import { SkeletonCard } from "@/components/ds/LoadingState";
import { MiniBar } from "@/components/ds/Chart";
import { List, ListItem } from "@/components/ds/List";

// ── Constants ──────────────────────────────────────────────────────────────────

const BORDER = "#E4E8EF";

const CATEGORIES = [
  { id: null,           label: "All",           icon: Sparkles },
  { id: "writing",      label: "Writing",        icon: FileText },
  { id: "publishing",   label: "Publishing",     icon: BookMarked },
  { id: "research",     label: "Research",       icon: BarChart2 },
  { id: "collaboration",label: "Collaboration",  icon: Users },
  { id: "funding",      label: "Funding",        icon: BadgeDollarSign },
  { id: "teaching",     label: "Teaching",       icon: GraduationCap },
  { id: "institution",  label: "Institution",    icon: Building2 },
  { id: "career",       label: "Career",         icon: Briefcase },
  { id: "productivity", label: "Productivity",   icon: Zap },
];

const HEALTH_COLOR = (score) =>
  score >= 80 ? "#047857" : score >= 60 ? "#B45309" : "#DC2626";

const INSIGHT_ICON_MAP = {
  "file-text": FileText,
  "dollar-sign": BadgeDollarSign,
  users: Users,
  brain: Sparkles,
  user: Briefcase,
  link: Activity,
  "trending-up": TrendingUp,
};

// ── Page ───────────────────────────────────────────────────────────────────────

export default function RecommendationCenter() {
  const [category,    setCategory]   = useState(null);
  const [recs,        setRecs]       = useState([]);
  const [total,       setTotal]      = useState(0);
  const [health,      setHealth]     = useState(null);
  const [opportunity, setOpportunity] = useState(null);
  const [insights,    setInsights]   = useState([]);
  const [briefing,    setBriefing]   = useState(null);
  const [loading,     setLoading]    = useState(true);
  const [refreshing,  setRefreshing] = useState(false);

  const load = useCallback(async (forceRefresh = false) => {
    setLoading(true);
    const [r, h, o, i, b] = await Promise.all([
      getRecommendations({ category: category || undefined }),
      getHealthScore(),
      getOpportunityScore(),
      getInsights(),
      getBriefing(forceRefresh),
    ]);
    setRecs(r?.recommendations || []);
    setTotal(r?.total || 0);
    setHealth(h);
    setOpportunity(o);
    setInsights(i?.insights || []);
    setBriefing(b);
    setLoading(false);
    setRefreshing(false);
  }, [category]);

  useEffect(() => { load(); }, [load]);

  const handleDismiss = useCallback((recId) => {
    setRecs(prev => prev.filter(r => r.id !== recId));
    setTotal(prev => Math.max(0, prev - 1));
  }, []);

  const refresh = async () => {
    setRefreshing(true);
    await load(true);
  };

  return (
    <ResearchLayout
      navItems={AI_NAV_ITEMS}
      title="AI Advisor"
      subtitle="Evidence-based recommendations from your verified platform data. Every suggestion includes its source and reasoning."
      actions={
        <Button onClick={refresh} disabled={refreshing} variant="ghost" size="sm">
          <RefreshCw size={11} strokeWidth={1.5} className={refreshing ? "animate-spin" : ""} />
          Refresh
        </Button>
      }
    >
      <div className="grid gap-7 items-start lg:grid-cols-[1fr_300px]">
        {/* ── Left column ──────────────────────────────────────────────── */}
        <div>
          {/* Greeting from briefing */}
          {briefing?.greeting && (
            <div className="text-[13px] text-slate-500 mb-5">
              {briefing.greeting} — {total} recommendation{total !== 1 ? "s" : ""} active.
            </div>
          )}

          {/* Category filter */}
          <div className="flex flex-wrap gap-1.5 mb-5">
            {CATEGORIES.map(({ id, label, icon: Icon }) => {
              const active = category === id;
              return (
                <Tag
                  key={String(id)}
                  onClick={() => setCategory(id)}
                  variant={active ? "active" : "default"}
                  color={active ? NAVY : undefined}
                >
                  <Icon size={10} strokeWidth={1.5} />
                  {label}
                </Tag>
              );
            })}
          </div>

          {/* Recommendations list */}
          {loading ? (
            <div className="flex flex-col gap-3">
              {[1, 2, 3].map(i => (
                <SkeletonCard key={i} rows={2} />
              ))}
            </div>
          ) : recs.length === 0 ? (
            <EmptyState
              icon={<Sparkles />}
              title={category ? `No ${category} recommendations right now` : "All caught up!"}
              description="Complete your profile and add manuscripts to unlock more recommendations."
              action={category && (
                <Button onClick={() => setCategory(null)} variant="link" size="sm">
                  Show all categories
                </Button>
              )}
            />
          ) : (
            <div className="flex flex-col gap-3">
              {recs.map(rec => (
                <RecommendationCard
                  key={rec.id}
                  rec={rec}
                  onDismiss={handleDismiss}
                  showWhy
                />
              ))}
            </div>
          )}
        </div>

        {/* ── Right panel ──────────────────────────────────────────────── */}
        <aside className="flex flex-col gap-6">

          {/* Platform Activity Score */}
          {health && (
            <div>
              <div className="flex items-center justify-between mb-3 pb-2" style={{ borderBottom: `1px solid ${BORDER}` }}>
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
                  Platform Activity
                </span>
                <Activity size={11} strokeWidth={1.5} style={{ color: NAVY }} />
              </div>
              <div className="flex items-center gap-3 mb-2">
                <div
                  className="text-[36px] font-bold leading-none"
                  style={{ color: HEALTH_COLOR(health.score) }}
                >
                  {health.score}
                </div>
                <div>
                  <div className="text-[13px] font-semibold text-slate-800">{health.label}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">Platform activity indicator</div>
                </div>
              </div>
              <p className="text-[10px] text-slate-400 mb-3 m-0 leading-relaxed">
                Reflects your Synaptiq profile and database activity only. Not a measure of research quality or academic standing.
              </p>
              <div className="flex flex-col gap-2">
                {Object.entries(health.subscores).map(([key, sub]) => (
                  <div key={key}>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
                      <span title={sub.basis}>{sub.label}</span>
                      <span className="font-mono">{sub.score}/{sub.max}</span>
                    </div>
                    <MiniBar
                      value={sub.score}
                      max={sub.max}
                      color={sub.score >= sub.max * 0.7 ? "#047857" : NAVY}
                      height={6}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Open Opportunities */}
          {opportunity && (
            <div>
              <div className="flex items-center justify-between mb-3 pb-2" style={{ borderBottom: `1px solid ${BORDER}` }}>
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
                  Open Opportunities
                </span>
                <TrendingUp size={11} strokeWidth={1.5} style={{ color: NAVY }} />
              </div>
              <div className="text-[28px] font-bold leading-none text-[#B45309] mb-1">
                {opportunity.total_open_items ?? opportunity.score ?? 0}
              </div>
              <div className="text-[11px] text-slate-500 mb-1">{opportunity.label}</div>
              <p className="text-[10px] text-slate-400 mb-3 m-0">Live counts from the platform database.</p>
              <div className="flex flex-col gap-1.5">
                {Object.entries(opportunity.counts || {}).filter(([, v]) => v > 0).map(([key, count]) => (
                  <div key={key} className="flex items-center justify-between text-[12px] text-slate-600">
                    <span className="capitalize">{key.replace(/_/g, " ")}</span>
                    <span className="font-mono font-semibold text-slate-800">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Weekly Insights */}
          {insights.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3 pb-2" style={{ borderBottom: `1px solid ${BORDER}` }}>
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
                  Your Insights
                </span>
                <Sparkles size={11} strokeWidth={1.5} style={{ color: NAVY }} />
              </div>
              <div className="flex flex-col gap-3">
                {insights.map(ins => {
                  const Icon = INSIGHT_ICON_MAP[ins.icon] || Sparkles;
                  return (
                    <div key={ins.id} className="flex items-start gap-2.5">
                      <Icon size={11} strokeWidth={1.5} style={{ color: NAVY, marginTop: 2, flexShrink: 0 }} />
                      <div>
                        <div className="text-[12px] font-medium text-slate-800">{ins.title}</div>
                        <div className="text-[11px] text-slate-400 mt-0.5">{ins.text}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Quick links */}
          <List border={false} divided>
            {[
              { label: "Manuscripts",        to: "/manuscripts",        icon: FileText },
              { label: "Grant Discovery",    to: "/grants",             icon: BadgeDollarSign },
              { label: "Collaboration AI",   to: "/collaboration-intelligence", icon: Users },
              { label: "Research Impact",    to: "/research-impact",    icon: TrendingUp },
              { label: "Citation Monitoring",to: "/citation-monitoring", icon: Activity },
            ].map(({ label, to, icon: Icon }) => (
              <ListItem
                key={to}
                to={to}
                compact
                leading={<Icon size={11} strokeWidth={1.5} style={{ color: NAVY }} />}
                title={label}
                trailing={<ChevronRight size={10} strokeWidth={2} className="text-slate-300" />}
              />
            ))}
          </List>
        </aside>
      </div>
    </ResearchLayout>
  );
}

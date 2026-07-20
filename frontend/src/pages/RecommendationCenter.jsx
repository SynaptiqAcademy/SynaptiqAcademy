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
import { AIWorkspaceLayout } from "@/layouts";
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
    <AIWorkspaceLayout
      title="AI Advisor"
      subtitle="Evidence-based recommendations from your verified platform data. Every suggestion includes its source and reasoning."
      actions={
        <button
          onClick={refresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 border border-slate-200 text-slate-500 hover:text-slate-800 hover:border-slate-300 transition-colors"
        >
          <RefreshCw size={11} strokeWidth={1.5} className={refreshing ? "animate-spin" : ""} />
          Refresh
        </button>
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
                <button
                  key={String(id)}
                  onClick={() => setCategory(id)}
                  className="flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1.5 border transition-all duration-100"
                  style={{
                    background:   active ? NAVY : "white",
                    color:        active ? "white" : "#475569",
                    borderColor:  active ? NAVY   : BORDER,
                  }}
                >
                  <Icon size={10} strokeWidth={1.5} />
                  {label}
                </button>
              );
            })}
          </div>

          {/* Recommendations list */}
          {loading ? (
            <div className="flex flex-col gap-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-28 bg-slate-100 animate-pulse" />
              ))}
            </div>
          ) : recs.length === 0 ? (
            <div className="text-center py-16 border border-dashed border-slate-200">
              <Sparkles size={28} strokeWidth={1} className="text-slate-200 mx-auto mb-3" />
              <p className="text-[14px] font-medium text-slate-500 m-0">
                {category ? `No ${category} recommendations right now` : "All caught up!"}
              </p>
              <p className="text-[12px] text-slate-400 mt-1 m-0">
                Complete your profile and add manuscripts to unlock more recommendations.
              </p>
              {category && (
                <button
                  onClick={() => setCategory(null)}
                  className="mt-3 text-[12px] font-medium text-slate-500 hover:text-slate-800 transition-colors underline"
                >
                  Show all categories
                </button>
              )}
            </div>
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
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.round((sub.score / sub.max) * 100)}%`,
                          background: sub.score >= sub.max * 0.7 ? "#047857" : NAVY,
                        }}
                      />
                    </div>
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
          <div>
            <div className="flex flex-col gap-1.5">
              {[
                { label: "Manuscripts",        to: "/manuscripts",        icon: FileText },
                { label: "Grant Discovery",    to: "/grants",             icon: BadgeDollarSign },
                { label: "Collaboration AI",   to: "/collaboration-intelligence", icon: Users },
                { label: "Research Impact",    to: "/research-impact",    icon: TrendingUp },
                { label: "Citation Monitoring",to: "/citation-monitoring", icon: Activity },
              ].map(({ label, to, icon: Icon }) => (
                <Link
                  key={to}
                  to={to}
                  className="flex items-center justify-between py-1.5 px-0 text-[12px] text-slate-500 hover:text-slate-900 no-underline transition-colors"
                  style={{ borderBottom: `1px solid ${BORDER}` }}
                >
                  <div className="flex items-center gap-2">
                    <Icon size={11} strokeWidth={1.5} style={{ color: NAVY }} />
                    {label}
                  </div>
                  <ChevronRight size={10} strokeWidth={2} className="text-slate-300" />
                </Link>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </AIWorkspaceLayout>
  );
}

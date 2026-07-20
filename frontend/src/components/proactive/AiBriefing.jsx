/**
 * AiBriefing — Personalized daily briefing widget (Phase XXX).
 *
 * Shows: greeting, summary items, profile completion, top recommendation.
 * Designed to be placed at the top of Today.jsx or Discover.jsx.
 *
 * Props:
 *   compact  boolean — compact single-line variant (default false)
 */

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, Sparkles, X, TrendingUp, FileText, Users, BadgeDollarSign, Folder } from "lucide-react";
import { getBriefing } from "../../services/proactiveEngine";
import { NAVY, ACCENT } from "@/lib/tokens";

const ITEM_ICON = {
  manuscripts:    FileText,
  grants:         BadgeDollarSign,
  collaborations: Users,
  projects:       Folder,
  citations:      TrendingUp,
};

export default function AiBriefing({ compact = false }) {
  const [briefing, setBriefing] = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [hidden,   setHidden]   = useState(false);

  useEffect(() => {
    getBriefing().then(data => {
      setBriefing(data);
      setLoading(false);
    });
  }, []);

  if (hidden || (!loading && !briefing)) return null;
  if (loading) return <BriefingSkeleton compact={compact} />;

  const { greeting, summary_items = [], profile_completion, top_recommendation } = briefing;

  if (compact) {
    return (
      <div
        className="flex items-center gap-3 px-4 py-2.5 border-b border-slate-100 text-[12px]"
        style={{ background: "#FAFAFA" }}
      >
        <Sparkles size={11} strokeWidth={1.5} style={{ color: NAVY, flexShrink: 0 }} />
        <span className="text-slate-600 flex-1 truncate">
          {greeting} — {summary_items.length > 0
            ? `${summary_items[0].count} ${summary_items[0].label}${summary_items.length > 1 ? ` · +${summary_items.length - 1} more` : ""}`
            : "Your research OS is ready."}
        </span>
        {top_recommendation && (
          <Link
            to={top_recommendation.action?.route || "/recommendation-center"}
            className="text-[11px] font-medium shrink-0 transition-colors hover:underline"
            style={{ color: NAVY }}
          >
            View →
          </Link>
        )}
      </div>
    );
  }

  return (
    <div
      className="mb-6 border border-slate-200"
      style={{ background: "white" }}
    >
      {/* Header */}
      <div
        className="flex items-start justify-between gap-4 px-5 py-4"
        style={{ background: NAVY }}
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Sparkles size={11} strokeWidth={1.5} className="text-white/40" />
            <span className="text-[9px] font-bold uppercase tracking-widest text-white/35">
              AI Briefing
            </span>
          </div>
          <h3 className="text-[15px] font-bold text-white m-0 leading-snug">
            {greeting}
          </h3>
        </div>
        <button
          onClick={() => setHidden(true)}
          className="text-white/30 hover:text-white/60 transition-colors p-0.5 shrink-0 mt-0.5"
          aria-label="Dismiss briefing"
        >
          <X size={13} strokeWidth={1.5} />
        </button>
      </div>

      {/* Summary items */}
      {summary_items.length > 0 && (
        <div className="flex flex-wrap gap-0 border-b border-slate-100">
          {summary_items.map((item, i) => {
            const Icon = ITEM_ICON[item.type] || Sparkles;
            return (
              <Link
                key={item.type}
                to={item.route || "/"}
                className="flex items-center gap-2 px-4 py-2.5 text-[12px] text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors no-underline"
                style={{ borderRight: i < summary_items.length - 1 ? "1px solid #F1F5F9" : "none" }}
              >
                <Icon size={11} strokeWidth={1.5} className="text-slate-400 shrink-0" />
                <span className="font-semibold text-slate-800">{item.count}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      )}

      {/* Top recommendation */}
      {top_recommendation && (
        <div className="px-5 py-3 flex items-start gap-3">
          <div className="flex-1 min-w-0">
            <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">
              Recommended next action
            </div>
            <div className="text-[13px] font-semibold text-slate-800">
              {top_recommendation.title}
            </div>
            {top_recommendation.description && (
              <p className="text-[12px] text-slate-500 m-0 mt-0.5 leading-relaxed">
                {top_recommendation.description}
              </p>
            )}
          </div>
          {top_recommendation.action && (
            <Link
              to={top_recommendation.action.route}
              className="flex items-center gap-1.5 text-[12px] font-semibold px-3 py-1.5 shrink-0 transition-colors no-underline"
              style={{ background: NAVY, color: "white" }}
              onMouseEnter={e => e.currentTarget.style.background = "#0a1d38"}
              onMouseLeave={e => e.currentTarget.style.background = NAVY}
            >
              {top_recommendation.action.label}
              <ChevronRight size={11} strokeWidth={2} />
            </Link>
          )}
        </div>
      )}

      {/* Profile completion hint */}
      {profile_completion != null && profile_completion < 85 && (
        <div className="px-5 py-2 border-t border-slate-100 flex items-center gap-2">
          <div className="flex-1 h-1 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${profile_completion}%`, background: NAVY }}
            />
          </div>
          <span className="text-[11px] text-slate-400 font-mono shrink-0">
            Profile {profile_completion}%
          </span>
          <Link
            to="/academic-passport"
            className="text-[11px] font-medium transition-colors no-underline hover:underline shrink-0"
            style={{ color: NAVY }}
          >
            Complete →
          </Link>
        </div>
      )}
    </div>
  );
}

function BriefingSkeleton({ compact }) {
  if (compact) return (
    <div className="h-10 bg-slate-50 border-b border-slate-100 animate-pulse" />
  );
  return (
    <div className="mb-6 border border-slate-200">
      <div className="h-16 bg-slate-200 animate-pulse" />
      <div className="flex gap-4 px-5 py-3">
        {[120, 140, 110].map(w => (
          <div key={w} className="h-4 bg-slate-100 animate-pulse rounded" style={{ width: w }} />
        ))}
      </div>
    </div>
  );
}

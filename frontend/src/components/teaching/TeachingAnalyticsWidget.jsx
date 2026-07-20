import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart2, Sparkles, BookOpen, ClipboardCheck, ArrowRight, Lightbulb } from "lucide-react";
import api from "../../lib/api";
import { NAVY } from "@/lib/tokens";

const INSIGHT_ICONS = {
  growth:      "📈",
  trend:       "🔥",
  suggestion:  "💡",
  achievement: "🏆",
  strength:    "💪",
  gap:         "⚠️",
};

export default function TeachingAnalyticsWidget() {
  const [overview, setOverview]       = useState(null);
  const [productivity, setProductivity] = useState(null);
  const [insights, setInsights]       = useState([]);
  const [loading, setLoading]         = useState(true);

  useEffect(() => {
    let mounted = true;
    Promise.allSettled([
      api.get("/teaching-analytics/overview", { params: { period: "30d" } }),
      api.get("/teaching-analytics/productivity"),
      api.get("/teaching-analytics/insights"),
    ]).then(([ovRes, prRes, inRes]) => {
      if (!mounted) return;
      if (ovRes.status === "fulfilled") setOverview(ovRes.value.data);
      if (prRes.status === "fulfilled") setProductivity(prRes.value.data);
      if (inRes.status === "fulfilled") setInsights(inRes.value.data.insights || []);
      setLoading(false);
    });
    return () => { mounted = false; };
  }, []);

  if (loading) {
    return (
      <div className="border border-slate-200 bg-white p-5 animate-pulse">
        <div className="h-4 bg-slate-100 w-32 mb-3" />
        <div className="h-8 bg-slate-100 w-16 mb-2" />
        <div className="h-3 bg-slate-100 w-full mb-1" />
        <div className="h-3 bg-slate-100 w-3/4" />
      </div>
    );
  }

  if (!overview && !productivity) return null;

  const topInsight = insights[0];
  const score = productivity?.productivity_score ?? 0;

  return (
    <div className="border border-slate-200 bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <BarChart2 size={13} strokeWidth={1.5} className="text-[#0F2847]" />
          <span className="overline">Teaching Analytics</span>
        </div>
        <Link to="/teaching/analytics" className="text-xs text-slate-500 hover:text-[#0F2847] flex items-center gap-1">
          View all <ArrowRight size={10} strokeWidth={1.5} />
        </Link>
      </div>

      <div className="p-5 space-y-5">
        {/* Productivity + reputation */}
        <div className="grid grid-cols-2 gap-3">
          <div className="border border-slate-100 bg-slate-50 p-3">
            <div className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold mb-1">Productivity</div>
            <div className="font-serif text-2xl text-[#0F2847]">{score}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">{productivity?.score_label || "—"}</div>
            <div className="mt-2 h-1.5 bg-slate-200 relative">
              <div
                className="absolute inset-y-0 left-0"
                style={{
                  width: `${score}%`,
                  background: score >= 60 ? "#10b981" : "#0F2847",
                }}
              />
            </div>
          </div>
          <div className="border border-slate-100 bg-slate-50 p-3">
            <div className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold mb-1">Teaching Rep.</div>
            <div className="font-serif text-2xl text-[#0F2847]">{overview?.reputation?.teaching_score ?? 0}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">/ 100</div>
          </div>
        </div>

        {/* Key stats (30d) */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { icon: BookOpen,      label: "Lessons",     value: overview?.period_counts?.lessons     ?? 0 },
            { icon: ClipboardCheck, label: "Assessments", value: overview?.period_counts?.assessments ?? 0 },
            { icon: Sparkles,      label: "AI sessions", value: overview?.period_counts?.ai_sessions  ?? 0 },
          ].map(({ icon: Icon, label, value }) => (
            <div key={label} className="text-center">
              <Icon size={13} strokeWidth={1.5} className="text-slate-400 mx-auto mb-1" />
              <div className="font-serif text-xl text-slate-900">{value}</div>
              <div className="text-[10px] text-slate-400">{label}</div>
            </div>
          ))}
        </div>

        {/* Top insight */}
        {topInsight && (
          <div className="border border-amber-100 bg-amber-50 px-3 py-2.5 flex items-start gap-2">
            <span className="text-base shrink-0">{INSIGHT_ICONS[topInsight.type] || "💡"}</span>
            <p className="text-xs text-amber-900 leading-relaxed">{topInsight.text}</p>
          </div>
        )}

        <Link
          to="/teaching/analytics"
          className="block text-center text-xs text-[#0F2847] border border-[#0F2847] py-2 hover:bg-[#0F2847] hover:text-white transition-colors"
        >
          Full Teaching Analytics →
        </Link>
      </div>
    </div>
  );
}

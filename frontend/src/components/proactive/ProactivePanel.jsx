/**
 * ProactivePanel — persistent floating AI advisor panel (Phase XXX).
 *
 * A floating button (bottom-right) that expands into a compact side panel.
 * Never a modal. Always accessible. Zero-distraction by default.
 *
 * Shows: health score, opportunity score, top 3 recommendations, briefing summary.
 * Wired into AppShell so it's always present when authenticated.
 */

import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Sparkles, X, ChevronRight, TrendingUp, AlertCircle,
  Activity, BarChart2, ArrowUpRight,
} from "lucide-react";
import {
  getBriefing, getRecommendations, getHealthScore, getOpportunityScore,
} from "../../services/proactiveEngine";
import RecommendationCard from "./RecommendationCard";
import { NAVY, ACCENT } from "@/lib/tokens";

export default function ProactivePanel() {
  const [open,        setOpen]        = useState(false);
  const [briefing,    setBriefing]    = useState(null);
  const [recs,        setRecs]        = useState([]);
  const [health,      setHealth]      = useState(null);
  const [opportunity, setOpportunity] = useState(null);
  const [loading,     setLoading]     = useState(false);
  const [loaded,      setLoaded]      = useState(false);

  const load = useCallback(async () => {
    if (loaded) return;
    setLoading(true);
    const [b, r, h, o] = await Promise.all([
      getBriefing(),
      getRecommendations({ limit: 3 }),
      getHealthScore(),
      getOpportunityScore(),
    ]);
    setBriefing(b);
    setRecs(r?.recommendations || []);
    setHealth(h);
    setOpportunity(o);
    setLoading(false);
    setLoaded(true);
  }, [loaded]);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  const handleDismiss = useCallback((recId) => {
    setRecs(prev => prev.filter(r => r.id !== recId));
  }, []);

  const healthColor = !health ? "#94A3B8"
    : health.score >= 80 ? "#047857"
    : health.score >= 60 ? "#B45309"
    : "#DC2626";

  return (
    <>
      {/* Floating trigger button */}
      <button
        onClick={() => setOpen(v => !v)}
        aria-label={open ? "Close AI Advisor" : "Open AI Advisor"}
        aria-expanded={open}
        className="fixed bottom-6 right-6 z-40 w-11 h-11 flex items-center justify-center shadow-lg transition-all duration-200 hover:scale-105 active:scale-95"
        style={{
          background: open ? "#0a1d38" : NAVY,
          borderRadius: "50%",
        }}
      >
        {open
          ? <X size={16} strokeWidth={1.5} className="text-white" />
          : <Sparkles size={16} strokeWidth={1.5} className="text-white" />
        }
        {/* Notification dot */}
        {!open && (
          <span
            className="absolute top-0.5 right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white"
            style={{ background: ACCENT }}
            aria-hidden="true"
          />
        )}
      </button>

      {/* Slide-in panel */}
      <div
        className="fixed bottom-20 right-6 z-40 bg-white border border-slate-200 shadow-2xl flex flex-col"
        style={{
          width: 320,
          maxHeight: "70vh",
          transform: open ? "translateY(0) scale(1)" : "translateY(16px) scale(0.96)",
          opacity: open ? 1 : 0,
          pointerEvents: open ? "auto" : "none",
          transition: "transform 0.2s ease, opacity 0.15s ease",
          transformOrigin: "bottom right",
        }}
        role="complementary"
        aria-label="AI Advisor panel"
      >
        {/* Panel header */}
        <div
          className="flex items-center justify-between px-4 py-3 shrink-0"
          style={{ background: NAVY }}
        >
          <div className="flex items-center gap-2">
            <Sparkles size={11} strokeWidth={1.5} className="text-white/50" />
            <span className="text-[11px] font-bold uppercase tracking-widest text-white/60">
              AI Advisor
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/recommendation-center"
              onClick={() => setOpen(false)}
              className="text-[10px] text-white/40 hover:text-white/70 transition-colors no-underline"
            >
              All recommendations →
            </Link>
          </div>
        </div>

        {loading && (
          <div className="flex flex-col gap-2 p-4">
            {[80, 120, 80].map(w => (
              <div key={w} className="h-3 bg-slate-100 animate-pulse rounded" style={{ width: w }} />
            ))}
          </div>
        )}

        {!loading && (
          <div className="overflow-y-auto flex-1">

            {/* Scores strip */}
            {(health || opportunity) && (
              <div className="flex border-b border-slate-100">
                {health && (
                  <div className="flex-1 flex flex-col items-center py-3 border-r border-slate-100">
                    <div className="text-[18px] font-bold" style={{ color: healthColor }}>
                      {health.score}
                    </div>
                    <div className="text-[9px] uppercase tracking-widest text-slate-400 font-bold mt-0.5">
                      Health
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">{health.label}</div>
                  </div>
                )}
                {opportunity && (
                  <div className="flex-1 flex flex-col items-center py-3">
                    <div className="text-[18px] font-bold text-[#B45309]">
                      {opportunity.score}
                    </div>
                    <div className="text-[9px] uppercase tracking-widest text-slate-400 font-bold mt-0.5">
                      Opportunities
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">{opportunity.label}</div>
                  </div>
                )}
              </div>
            )}

            {/* Briefing summary */}
            {briefing?.summary_items?.length > 0 && (
              <div className="px-4 py-3 border-b border-slate-100">
                <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                  Today
                </div>
                {briefing.summary_items.slice(0, 3).map(item => (
                  <Link
                    key={item.type}
                    to={item.route || "/"}
                    onClick={() => setOpen(false)}
                    className="flex items-center gap-2 py-1 text-[12px] text-slate-600 hover:text-slate-900 transition-colors no-underline"
                  >
                    <span className="font-semibold text-slate-800 w-6 text-right shrink-0">
                      {item.count}
                    </span>
                    <span className="truncate">{item.label}</span>
                    <ChevronRight size={9} strokeWidth={2} className="text-slate-300 shrink-0 ml-auto" />
                  </Link>
                ))}
              </div>
            )}

            {/* Top recommendations */}
            {recs.length > 0 && (
              <div className="px-4 py-3">
                <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                  Recommendations
                </div>
                <div className="flex flex-col gap-2">
                  {recs.map(rec => (
                    <RecommendationCard
                      key={rec.id}
                      rec={rec}
                      compact
                      showWhy={false}
                      onDismiss={handleDismiss}
                      onAccept={() => setOpen(false)}
                    />
                  ))}
                </div>
              </div>
            )}

            {!loading && recs.length === 0 && (
              <div className="px-4 py-6 text-center">
                <Sparkles size={20} strokeWidth={1} className="text-slate-200 mx-auto mb-2" />
                <p className="text-[12px] text-slate-400 m-0">
                  All recommendations dismissed.<br />
                  <Link to="/recommendation-center" className="text-[#0F2847]" onClick={() => setOpen(false)}>
                    View all
                  </Link>
                </p>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="px-4 py-2.5 border-t border-slate-100 flex items-center justify-between shrink-0">
          <Link
            to="/recommendation-center"
            onClick={() => setOpen(false)}
            className="text-[11px] text-slate-400 hover:text-slate-700 transition-colors no-underline flex items-center gap-1"
          >
            <ArrowUpRight size={10} strokeWidth={1.5} />
            Recommendation Center
          </Link>
          <span className="text-[10px] text-slate-300 font-mono">
            {recs.length} active
          </span>
        </div>
      </div>
    </>
  );
}

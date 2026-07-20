import React, { useState } from "react";
import { Info, ChevronDown, ChevronUp } from "lucide-react";
import { explainHealth } from "../../services/twinEngine";

const LEVEL_STYLE = {
  good:     { color: "#047857", bg: "#F0FDF4", bar: "#10B981", label: "Good" },
  moderate: { color: "#B45309", bg: "#FFFBEB", bar: "#F59E0B", label: "Moderate" },
  low:      { color: "#6B7280", bg: "#F9FAFB", bar: "#D1D5DB", label: "Low activity" },
};

function IndicatorCard({ indicator, onExplain }) {
  const [open, setOpen] = useState(false);
  const style = LEVEL_STYLE[indicator.level] || LEVEL_STYLE.low;

  const fillPct = indicator.unit === "%" ? indicator.value : Math.min(100,
    indicator.level === "good" ? 90 : indicator.level === "moderate" ? 55 : 20
  );

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[12px] font-semibold text-slate-700">{indicator.label}</span>
            <div className="flex items-center gap-2">
              <span
                className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                style={{ color: style.color, background: style.bg }}
              >
                {style.label}
              </span>
              <span className="text-[11px] font-bold text-slate-600">
                {indicator.value}{indicator.unit !== "items updated" && indicator.unit !== "projects" ? ` ${indicator.unit}` : ""}
              </span>
            </div>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5">
            <div
              className="h-1.5 rounded-full transition-all"
              style={{ width: `${fillPct}%`, background: style.bar }}
            />
          </div>
        </div>
        {open ? <ChevronUp size={13} className="text-slate-400 flex-shrink-0" /> : <ChevronDown size={13} className="text-slate-400 flex-shrink-0" />}
      </div>

      {open && (
        <div className="px-4 pb-3 pt-1 bg-slate-50/50 border-t border-slate-100">
          <p className="text-[11px] text-slate-600 mb-2">{indicator.description}</p>
          {indicator.missing_fields?.length > 0 && (
            <p className="text-[10px] text-amber-600 mb-2">
              Missing: {indicator.missing_fields.join(", ")}
            </p>
          )}
          <div className="flex items-center gap-2 mt-1">
            <p className="text-[10px] text-slate-400 flex-1">
              <span className="font-medium">Method: </span>{indicator.methodology}
            </p>
            <button
              onClick={e => { e.stopPropagation(); onExplain(indicator.id); }}
              className="flex items-center gap-1 text-[10px] text-blue-600 hover:text-blue-800 flex-shrink-0"
            >
              <Info size={10} /> Explain
            </button>
          </div>
          <p className="text-[10px] text-slate-400 mt-0.5">Source: {indicator.source}</p>
        </div>
      )}
    </div>
  );
}

export default function ResearchHealth({ health, loading }) {
  const [explanation, setExplanation] = useState(null);

  async function handleExplain(id) {
    try {
      const res = await explainHealth(id);
      setExplanation(res.data?.explanation || null);
    } catch {
      setExplanation(null);
    }
  }

  if (loading) {
    return <div className="text-center py-12 text-[11px] text-slate-400">Computing health indicators…</div>;
  }

  if (!health) {
    return <div className="text-center py-12 text-[11px] text-slate-400">No health data available. Sync your twin first.</div>;
  }

  const overall = health.overall || {};

  return (
    <div className="space-y-4">
      {/* Overall */}
      <div className="p-4 rounded-xl border border-slate-200 bg-gradient-to-r from-slate-50 to-white">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">Platform Activity Score</span>
          <span className="text-[11px] text-slate-500">{overall.score}</span>
        </div>
        <div className={`text-sm font-bold ${overall.level === "good" ? "text-emerald-700" : overall.level === "moderate" ? "text-amber-700" : "text-slate-600"}`}>
          {overall.level === "good" ? "Active" : overall.level === "moderate" ? "Moderate activity" : "Low activity"}
        </div>
        <p className="text-[10px] text-slate-400 mt-1">{health.policy_note}</p>
      </div>

      {/* Indicators */}
      <div className="space-y-2">
        {(health.indicators || []).map(ind => (
          <IndicatorCard key={ind.id} indicator={ind} onExplain={handleExplain} />
        ))}
      </div>

      {/* Explanation modal */}
      {explanation && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setExplanation(null)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-5" onClick={e => e.stopPropagation()}>
            <h3 className="font-bold text-slate-800 mb-2">{explanation.what}</h3>
            <p className="text-[12px] text-slate-600 mb-3">{explanation.why}</p>
            <div className="bg-slate-50 rounded-lg p-3 text-[11px] text-slate-500 space-y-1">
              <p><span className="font-medium">Method: </span>{explanation.methodology}</p>
              <p><span className="font-medium">Sources: </span>{explanation.data_sources?.join(", ")}</p>
              <p><span className="font-medium">Confidence: </span>{explanation.confidence}</p>
            </div>
            <p className="text-[10px] text-slate-400 mt-2 italic">{explanation.policy_note}</p>
            <button onClick={() => setExplanation(null)} className="mt-3 text-[11px] text-blue-600 hover:underline">Close</button>
          </div>
        </div>
      )}

      <p className="text-[10px] text-slate-400 text-center">{health.methodology}</p>
    </div>
  );
}

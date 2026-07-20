/**
 * RecommendationCard — reusable proactive recommendation display (Phase XXX).
 *
 * Props:
 *   rec        { id, category, priority, title, description, why, action, confidence, confidence_pct, meta }
 *   onDismiss  (recId) => void
 *   onAccept   (recId) => void  (optional, called on CTA click before navigation)
 *   compact    boolean — compact variant for panels/briefings
 *   showWhy    boolean — show explainability section (default true)
 */

import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  X, ChevronRight, Info, Lightbulb,
  FileText, BadgeDollarSign, Users, GraduationCap, Building2,
  Briefcase, Zap, BarChart2, BookMarked, Database,
} from "lucide-react";
import { dismissRec, acceptRec } from "../../services/proactiveEngine";

// ── Per-category styling ──────────────────────────────────────────────────────

const CAT_STYLE = {
  writing:       { color: "#1D4ED8", bg: "#EFF6FF", label: "Writing" },
  publishing:    { color: "#7C3AED", bg: "#F5F3FF", label: "Publishing" },
  research:      { color: "#0F2847", bg: "#F0F4FF", label: "Research" },
  collaboration: { color: "#047857", bg: "#F0FDF4", label: "Collaboration" },
  funding:       { color: "#B45309", bg: "#FFFBEB", label: "Funding" },
  teaching:      { color: "#0891B2", bg: "#ECFEFF", label: "Teaching" },
  institution:   { color: "#6D28D9", bg: "#F5F3FF", label: "Institution" },
  career:        { color: "#DC2626", bg: "#FEF2F2", label: "Career" },
  productivity:  { color: "#475569", bg: "#F8FAFC", label: "Productivity" },
};

const CAT_ICON = {
  writing:       FileText,
  publishing:    BookMarked,
  research:      BarChart2,
  collaboration: Users,
  funding:       BadgeDollarSign,
  teaching:      GraduationCap,
  institution:   Building2,
  career:        Briefcase,
  productivity:  Zap,
};

const CONF_STYLE = {
  high:           { color: "#047857", bg: "#F0FDF4", label: "Strong evidence" },
  medium:         { color: "#B45309", bg: "#FFFBEB", label: "Partial evidence" },
  low:            { color: "#6B7280", bg: "#F9FAFB", label: "Limited evidence" },
  not_applicable: { color: "#6B7280", bg: "#F9FAFB", label: "Insufficient data" },
};

// ── Component ──────────────────────────────────────────────────────────────────

export default function RecommendationCard({
  rec,
  onDismiss,
  onAccept,
  compact   = false,
  showWhy   = true,
}) {
  const [dismissed, setDismissed] = useState(false);
  const [expanded,  setExpanded]  = useState(false);

  if (!rec || dismissed) return null;

  const catStyle  = CAT_STYLE[rec.category]  || CAT_STYLE.research;
  const CatIcon   = CAT_ICON[rec.category]   || Lightbulb;
  const confStyle = CONF_STYLE[rec.confidence] || CONF_STYLE.medium;

  const handleDismiss = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDismissed(true);
    await dismissRec(rec.id);
    onDismiss?.(rec.id);
  };

  const handleAccept = async () => {
    await acceptRec(rec.id);
    onAccept?.(rec.id);
  };

  if (compact) {
    return (
      <div
        className="flex items-start gap-3 p-3 border border-slate-100 bg-white relative group"
        style={{ borderLeft: `3px solid ${catStyle.color}` }}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <span
              className="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5"
              style={{ color: catStyle.color, background: catStyle.bg }}
            >
              {catStyle.label}
            </span>
          </div>
          <div className="text-[13px] font-medium text-slate-800 leading-snug">{rec.title}</div>
          {rec.action && (
            <Link
              to={rec.action.route}
              onClick={handleAccept}
              className="inline-flex items-center gap-1 text-[11px] font-medium mt-1.5 transition-colors"
              style={{ color: catStyle.color }}
            >
              {rec.action.label}
              <ChevronRight size={9} strokeWidth={2} />
            </Link>
          )}
        </div>
        <button
          onClick={handleDismiss}
          className="text-slate-300 hover:text-slate-500 transition-colors p-0.5 shrink-0 opacity-0 group-hover:opacity-100"
          aria-label="Dismiss"
        >
          <X size={12} strokeWidth={1.5} />
        </button>
      </div>
    );
  }

  return (
    <div
      className="border border-slate-200 bg-white relative group"
      style={{ borderLeft: `3px solid ${catStyle.color}` }}
    >
      {/* Header */}
      <div className="flex items-start gap-3 p-4 pb-3">
        {/* Category icon */}
        <div
          className="w-8 h-8 flex items-center justify-center shrink-0 mt-0.5"
          style={{ background: catStyle.bg }}
        >
          <CatIcon size={13} strokeWidth={1.5} style={{ color: catStyle.color }} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span
              className="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5"
              style={{ color: catStyle.color, background: catStyle.bg }}
            >
              {catStyle.label}
            </span>
            <span
              className="text-[9px] font-semibold px-1.5 py-0.5"
              style={{ color: confStyle.color, background: confStyle.bg }}
            >
              {confStyle.label}
            </span>
            {rec.meta?.deadline_label && (
              <span className="text-[9px] font-semibold px-1.5 py-0.5 bg-red-50 text-red-600">
                ⏱ {rec.meta.deadline_label}
              </span>
            )}
          </div>
          <h4 className="text-[14px] font-semibold text-slate-900 leading-snug mb-1">
            {rec.title}
          </h4>
          <p className="text-[12px] text-slate-500 leading-relaxed m-0">{rec.description}</p>
        </div>

        {/* Dismiss */}
        <button
          onClick={handleDismiss}
          className="text-slate-300 hover:text-slate-500 transition-colors p-0.5 shrink-0 mt-0.5 opacity-0 group-hover:opacity-100"
          aria-label="Dismiss recommendation"
        >
          <X size={13} strokeWidth={1.5} />
        </button>
      </div>

      {/* Explainability (why) + evidence sources */}
      {showWhy && rec.why && (
        <div className="px-4 pb-3">
          <button
            onClick={() => setExpanded(v => !v)}
            className="flex items-center gap-1.5 text-[11px] text-slate-400 hover:text-slate-600 transition-colors"
          >
            <Info size={10} strokeWidth={1.5} />
            {expanded ? "Hide reasoning" : "Why this recommendation?"}
          </button>
          {expanded && (
            <div
              className="mt-2 px-3 py-2"
              style={{ background: catStyle.bg, borderLeft: `2px solid ${catStyle.color}40` }}
            >
              <p className="text-[12px] text-slate-600 leading-relaxed m-0">{rec.why}</p>
              {Array.isArray(rec.evidence) && rec.evidence.length > 0 && (
                <div className="mt-2 pt-2 border-t border-slate-100">
                  <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
                    <Database size={9} strokeWidth={1.5} />
                    Evidence sources
                  </div>
                  {rec.evidence.map((ev, i) => (
                    <div key={i} className="text-[11px] text-slate-500 mb-1 leading-snug">
                      <span className="font-medium text-slate-600">{ev.source}:</span>{" "}
                      {ev.detail}
                    </div>
                  ))}
                </div>
              )}
              {rec.confidence_basis && (
                <p className="text-[11px] text-slate-400 mt-2 pt-2 border-t border-slate-100 m-0 italic">
                  {rec.confidence_basis}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Action */}
      {rec.action && (
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-slate-50">
          <Link
            to={rec.action.route}
            onClick={handleAccept}
            className="inline-flex items-center gap-1.5 text-[12px] font-semibold transition-colors"
            style={{ color: catStyle.color }}
          >
            {rec.action.label}
            <ChevronRight size={10} strokeWidth={2.5} />
          </Link>
          <span className="text-[10px] font-mono text-slate-300">
            Priority {rec.priority}/10
          </span>
        </div>
      )}
    </div>
  );
}

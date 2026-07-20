/**
 * AgentCard — displays one agent's output with evidence, confidence, and expandable reasoning.
 *
 * Props:
 *   output   { agent, status, content, confidence, confidence_basis, evidence[], limitations[], structured_data }
 *   compact  boolean
 */
import React, { useState } from "react";
import {
  ChevronDown, ChevronRight, Database, AlertTriangle, CheckCircle,
  Clock, Info, BookOpen, BarChart2, FileText, Users, BadgeDollarSign,
  GraduationCap, Building2, Briefcase, Zap, BookMarked, Search, Shield,
} from "lucide-react";
import { NAVY } from "@/lib/tokens";

const AGENT_META = {
  literature:    { label: "Literature",    icon: Search,        color: "#1D4ED8", bg: "#EFF6FF" },
  gap:           { label: "Research Gap",  icon: BarChart2,     color: "#7C3AED", bg: "#F5F3FF" },
  study_design:  { label: "Study Design",  icon: BookOpen,      color: "#0F2847", bg: "#F0F4FF" },
  statistics:    { label: "Statistics",    icon: BarChart2,     color: "#047857", bg: "#F0FDF4" },
  writing:       { label: "Writing",       icon: FileText,      color: "#B45309", bg: "#FFFBEB" },
  journal:       { label: "Journal",       icon: BookMarked,    color: "#DB2777", bg: "#FDF2F8" },
  reviewer:      { label: "Peer Review",   icon: CheckCircle,   color: "#0891B2", bg: "#ECFEFF" },
  ethics:        { label: "Ethics",        icon: Shield,        color: "#DC2626", bg: "#FEF2F2" },
  citation:      { label: "Citations",     icon: BookOpen,      color: "#6D28D9", bg: "#F5F3FF" },
  funding:       { label: "Funding",       icon: BadgeDollarSign, color: "#D97706", bg: "#FFFBEB" },
  collaboration: { label: "Collaboration", icon: Users,         color: "#059669", bg: "#F0FDF4" },
  teaching:      { label: "Teaching",      icon: GraduationCap, color: "#0284C7", bg: "#EFF6FF" },
  institution:   { label: "Institution",   icon: Building2,     color: "#7C3AED", bg: "#F5F3FF" },
  career:        { label: "Career",        icon: Briefcase,     color: "#475569", bg: "#F8FAFC" },
};

const CONF_STYLE = {
  high:           { label: "Strong evidence",    color: "#047857" },
  medium:         { label: "Partial evidence",   color: "#B45309" },
  low:            { label: "Limited evidence",   color: "#6B7280" },
  not_applicable: { label: "Insufficient data",  color: "#9CA3AF" },
};

const STATUS_ICON = {
  success:          <CheckCircle size={11} className="text-emerald-500" />,
  partial:          <AlertTriangle size={11} className="text-amber-500" />,
  insufficient_data: <Info size={11} className="text-slate-400" />,
  error:            <AlertTriangle size={11} className="text-red-500" />,
  running:          <Clock size={11} className="text-blue-400 animate-pulse" />,
};

export default function AgentCard({ output, compact = false }) {
  const [expanded, setExpanded] = useState(false);

  if (!output) return null;

  const meta   = AGENT_META[output.agent] || { label: output.agent, icon: Zap, color: NAVY, bg: "#F8FAFC" };
  const Icon   = meta.icon;
  const conf   = CONF_STYLE[output.confidence] || CONF_STYLE.medium;
  const isRunning = output.status === "running";

  if (compact) {
    return (
      <div
        className="flex items-center gap-2 px-3 py-2 border border-slate-100 bg-white"
        style={{ borderLeft: `3px solid ${meta.color}` }}
      >
        <div className="w-5 h-5 flex items-center justify-center shrink-0" style={{ background: meta.bg }}>
          <Icon size={10} strokeWidth={1.5} style={{ color: meta.color }} />
        </div>
        <span className="text-[11px] font-semibold text-slate-700 flex-1">{meta.label}</span>
        {STATUS_ICON[output.status] || STATUS_ICON.running}
      </div>
    );
  }

  return (
    <div className="border border-slate-200 bg-white" style={{ borderLeft: `3px solid ${meta.color}` }}>
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="w-7 h-7 flex items-center justify-center shrink-0" style={{ background: meta.bg }}>
          <Icon size={12} strokeWidth={1.5} style={{ color: meta.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-bold uppercase tracking-widest" style={{ color: meta.color }}>
              {meta.label}
            </span>
            <span className="text-[10px] font-semibold px-1.5 py-0.5" style={{ color: conf.color, background: `${conf.color}14` }}>
              {conf.label}
            </span>
            {STATUS_ICON[output.status]}
          </div>
        </div>
        {output.content && !isRunning && (
          <button
            onClick={() => setExpanded(v => !v)}
            className="text-slate-400 hover:text-slate-600 transition-colors p-0.5 shrink-0"
          >
            {expanded ? <ChevronDown size={13} strokeWidth={1.5} /> : <ChevronRight size={13} strokeWidth={1.5} />}
          </button>
        )}
      </div>

      {/* Running state */}
      {isRunning && (
        <div className="px-4 pb-3">
          <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full bg-blue-300 animate-pulse rounded-full w-2/3" />
          </div>
        </div>
      )}

      {/* Content preview (always visible) */}
      {!isRunning && output.content && (
        <div className="px-4 pb-3">
          <p className="text-[12px] text-slate-600 leading-relaxed m-0 line-clamp-3">
            {output.content.replace(/^[⚠️\s]+/, "").slice(0, 200)}
            {output.content.length > 200 && "…"}
          </p>
        </div>
      )}

      {/* Expanded: full content + evidence */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-50">
          <div className="mt-3 text-[12px] text-slate-700 leading-relaxed whitespace-pre-wrap">
            {output.content}
          </div>

          {/* Evidence sources */}
          {Array.isArray(output.evidence) && output.evidence.length > 0 && (
            <div className="mt-4 pt-3 border-t border-slate-100">
              <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                <Database size={9} strokeWidth={1.5} />
                Evidence sources
              </div>
              {output.evidence.map((ev, i) => (
                <div key={i} className="text-[11px] text-slate-500 mb-1 leading-snug">
                  <span className="font-semibold text-slate-600">{ev.source}:</span>{" "}
                  {ev.detail}
                </div>
              ))}
            </div>
          )}

          {/* Confidence basis */}
          {output.confidence_basis && (
            <p className="text-[10px] text-slate-400 mt-2 m-0 italic leading-relaxed">
              {output.confidence_basis}
            </p>
          )}

          {/* Limitations */}
          {Array.isArray(output.limitations) && output.limitations.length > 0 && (
            <div className="mt-3 pt-2 border-t border-slate-100">
              <div className="text-[10px] font-bold uppercase tracking-widest text-slate-300 mb-1">Limitations</div>
              {output.limitations.map((lim, i) => (
                <div key={i} className="text-[10px] text-slate-400 mb-0.5">• {lim}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

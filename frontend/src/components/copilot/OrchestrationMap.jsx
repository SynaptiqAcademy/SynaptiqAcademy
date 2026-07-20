/**
 * OrchestrationMap — visual agent activation map.
 *
 * Shows workflow stages left-to-right with agents per stage.
 * Agents highlight as they activate. Status shown per agent.
 *
 * Props:
 *   plan      { workflow_label, stages: [[agentNames], ...] }
 *   statuses  { agentName: "waiting"|"running"|"success"|"partial"|"error"|"insufficient_data" }
 */
import React from "react";
import {
  Search, BarChart2, BookOpen, FileText, BookMarked,
  CheckCircle, Shield, BadgeDollarSign, Users,
  GraduationCap, Building2, Briefcase, Zap, ChevronRight,
} from "lucide-react";
import { NAVY } from "@/lib/tokens";

const AGENT_ICON = {
  literature:    Search,
  gap:           BarChart2,
  study_design:  BookOpen,
  statistics:    BarChart2,
  writing:       FileText,
  journal:       BookMarked,
  reviewer:      CheckCircle,
  ethics:        Shield,
  citation:      BookOpen,
  funding:       BadgeDollarSign,
  collaboration: Users,
  teaching:      GraduationCap,
  institution:   Building2,
  career:        Briefcase,
};

const AGENT_LABEL = {
  literature:    "Literature",
  gap:           "Gap",
  study_design:  "Design",
  statistics:    "Statistics",
  writing:       "Writing",
  journal:       "Journal",
  reviewer:      "Reviewer",
  ethics:        "Ethics",
  citation:      "Citations",
  funding:       "Funding",
  collaboration: "Collaboration",
  teaching:      "Teaching",
  institution:   "Institution",
  career:        "Career",
};

const STATUS_COLOR = {
  waiting:          { bg: "#F8FAFC", border: "#E4E8EF", text: "#94A3B8" },
  running:          { bg: "#EFF6FF", border: "#3B82F6", text: "#1D4ED8" },
  success:          { bg: "#F0FDF4", border: "#10B981", text: "#047857" },
  partial:          { bg: "#FFFBEB", border: "#F59E0B", text: "#B45309" },
  insufficient_data:{ bg: "#F9FAFB", border: "#CBD5E1", text: "#6B7280" },
  error:            { bg: "#FEF2F2", border: "#EF4444", text: "#DC2626" },
};

function AgentNode({ name, status = "waiting" }) {
  const Icon   = AGENT_ICON[name] || Zap;
  const label  = AGENT_LABEL[name] || name;
  const colors = STATUS_COLOR[status] || STATUS_COLOR.waiting;

  return (
    <div
      className="flex flex-col items-center gap-1 px-2 py-2 min-w-[64px] transition-all duration-300"
      style={{
        background:  colors.bg,
        border:      `1px solid ${colors.border}`,
        boxShadow:   status === "running" ? `0 0 0 2px ${colors.border}30` : "none",
      }}
    >
      <Icon size={14} strokeWidth={1.5} style={{ color: colors.text }} />
      <span className="text-[9px] font-semibold text-center leading-tight" style={{ color: colors.text }}>
        {label}
      </span>
      {status === "running" && (
        <div className="w-8 h-0.5 bg-blue-100 rounded overflow-hidden">
          <div className="h-full bg-blue-400 animate-pulse rounded w-1/2" />
        </div>
      )}
    </div>
  );
}

export default function OrchestrationMap({ plan, statuses = {} }) {
  if (!plan || !plan.stages) return null;

  return (
    <div className="py-3">
      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">
        {plan.workflow_label || "Orchestration plan"}
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        {plan.stages.map((stage, si) => (
          <React.Fragment key={si}>
            {si > 0 && (
              <ChevronRight size={12} strokeWidth={1.5} className="text-slate-300 shrink-0" />
            )}
            <div className="flex items-center gap-1.5 flex-wrap">
              {stage.map(agentName => (
                <AgentNode
                  key={agentName}
                  name={agentName}
                  status={statuses[agentName] || "waiting"}
                />
              ))}
            </div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

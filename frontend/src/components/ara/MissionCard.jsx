import React from "react";
import {
  Clock, CheckCircle, XCircle, Pause, AlertCircle,
  PlayCircle, Loader, Ban,
} from "lucide-react";

const STATUS_META = {
  draft:          { icon: Clock,        color: "text-slate-400", bg: "bg-slate-50",  label: "Draft" },
  planning:       { icon: Loader,       color: "text-blue-500",  bg: "bg-blue-50",   label: "Planning…" },
  plan_review:    { icon: AlertCircle,  color: "text-amber-500", bg: "bg-amber-50",  label: "Awaiting Your Review" },
  running:        { icon: PlayCircle,   color: "text-indigo-500",bg: "bg-indigo-50", label: "Running" },
  awaiting_human: { icon: AlertCircle,  color: "text-orange-500",bg: "bg-orange-50", label: "Needs Your Approval" },
  paused:         { icon: Pause,        color: "text-slate-500", bg: "bg-slate-50",  label: "Paused" },
  completed:      { icon: CheckCircle,  color: "text-green-500", bg: "bg-green-50",  label: "Completed" },
  failed:         { icon: XCircle,      color: "text-red-500",   bg: "bg-red-50",    label: "Failed" },
  cancelled:      { icon: Ban,          color: "text-slate-400", bg: "bg-slate-50",  label: "Cancelled" },
};

const AUTONOMY_LABELS = {
  0: "Manual",
  1: "Assist",
  2: "Semi-Autonomous",
  3: "Autonomous",
};

function ProgressBar({ total, done }) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  return (
    <div className="mt-2">
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>{done}/{total} steps</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function MissionCard({ mission, onClick }) {
  const meta   = STATUS_META[mission.status] || STATUS_META.draft;
  const Icon   = meta.icon;
  const isUrgent = ["plan_review", "awaiting_human"].includes(mission.status);

  return (
    <button
      onClick={() => onClick && onClick(mission)}
      className={`w-full text-left rounded-md border p-4 transition-all hover:shadow-sm
        ${isUrgent ? "border-amber-300 bg-amber-50/40" : "border-slate-200 bg-white"}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-medium text-sm text-slate-800 truncate">{mission.title}</p>
          <p className="text-xs text-slate-400 mt-0.5 capitalize">
            {AUTONOMY_LABELS[mission.autonomy_level] ?? "Assist"} · {mission.mission_type}
          </p>
        </div>
        <span className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${meta.bg} ${meta.color}`}>
          <Icon size={12} />
          {meta.label}
        </span>
      </div>

      {(mission.total_steps > 0) && (
        <ProgressBar total={mission.total_steps} done={mission.completed_steps ?? 0} />
      )}

      {mission.result_summary && mission.status === "completed" && (
        <p className="text-xs text-slate-500 mt-2 line-clamp-2">{mission.result_summary}</p>
      )}
      {mission.error && mission.status === "failed" && (
        <p className="text-xs text-red-500 mt-2 line-clamp-2">{mission.error}</p>
      )}

      <p className="text-xs text-slate-300 mt-2">
        {mission.created_at ? new Date(mission.created_at).toLocaleDateString() : ""}
      </p>
    </button>
  );
}

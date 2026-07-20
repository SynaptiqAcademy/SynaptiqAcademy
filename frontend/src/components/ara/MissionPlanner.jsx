import React, { useState } from "react";
import {
  CheckCircle, Circle, ChevronRight, Zap, ShieldAlert, Info,
  Clock, Play,
} from "lucide-react";
import { approvePlan, refinePlan } from "../../services/araEngine";

const STEP_TYPE_META = {
  safe:     { icon: CheckCircle, color: "text-green-500",  label: "Auto" },
  approval: { icon: ShieldAlert, color: "text-orange-500", label: "Needs Approval" },
  info:     { icon: Info,        color: "text-blue-400",   label: "Info" },
};

function StepRow({ step, index }) {
  const meta = STEP_TYPE_META[step.step_type] || STEP_TYPE_META.safe;
  const Icon = meta.icon;
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-slate-100 last:border-0">
      <div className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-100 text-xs text-slate-500 font-medium shrink-0 mt-0.5">
        {index + 1}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-slate-800">{step.name}</p>
          <span className={`flex items-center gap-0.5 text-xs ${meta.color}`}>
            <Icon size={11} />
            {meta.label}
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{step.description}</p>
        {step.estimated_duration_s > 0 && (
          <p className="text-xs text-slate-300 mt-0.5 flex items-center gap-1">
            <Clock size={10} />
            ~{Math.ceil(step.estimated_duration_s / 60)} min
          </p>
        )}
      </div>
    </div>
  );
}

export default function MissionPlanner({ mission, steps, onApproved, onCancelled }) {
  const [loading,  setLoading]  = useState(false);
  const [expanded, setExpanded] = useState(true);

  const needsApproval = steps.filter(s => s.step_type === "approval").length;
  const autoSteps     = steps.filter(s => s.step_type === "safe").length;
  const totalCredits  = mission?.estimated_credits ?? 0;

  async function handleApprove() {
    setLoading(true);
    try {
      await approvePlan(mission._id || mission.mission_id || mission.id);
      onApproved && onApproved();
    } catch (e) {
      alert("Could not start mission: " + (e?.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-md border border-slate-200 bg-white overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer bg-slate-50 hover:bg-slate-100 transition-colors"
        onClick={() => setExpanded(v => !v)}
      >
        <div>
          <p className="font-semibold text-sm text-slate-800">Execution Plan</p>
          <p className="text-xs text-slate-400 mt-0.5">
            {steps.length} steps · {autoSteps} auto · {needsApproval} need your approval
            {totalCredits > 0 && ` · ~${totalCredits} credits`}
          </p>
        </div>
        <ChevronRight
          size={16}
          className={`text-slate-400 transition-transform ${expanded ? "rotate-90" : ""}`}
        />
      </div>

      {expanded && (
        <div className="px-4 pb-2">
          {steps.map((step, i) => (
            <StepRow key={step.step_id || i} step={step} index={i} />
          ))}
        </div>
      )}

      {/* Safety policy */}
      <div className="mx-4 mb-3 px-3 py-2 rounded bg-amber-50 border border-amber-100">
        <p className="text-xs text-amber-700">
          <strong>Safety guarantee:</strong> Agents never submit, send emails, or apply for grants
          without your explicit approval — regardless of autonomy level.
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-2 px-4 pb-4">
        <button
          onClick={handleApprove}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50"
        >
          <Play size={14} />
          {loading ? "Starting…" : "Approve & Start"}
        </button>
        <button
          onClick={onCancelled}
          disabled={loading}
          className="px-3 py-2 text-sm text-slate-500 hover:text-slate-700 border border-slate-200 rounded"
        >
          Cancel Mission
        </button>
      </div>
    </div>
  );
}

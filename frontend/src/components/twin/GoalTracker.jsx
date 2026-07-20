import React, { useState } from "react";
import { Plus, Trash2, CheckCircle, Clock, PauseCircle, XCircle } from "lucide-react";
import { createGoal, updateGoal, deleteGoal } from "../../services/twinEngine";

const STATUS_ICON = {
  active:    { icon: Clock,        color: "#3B82F6" },
  completed: { icon: CheckCircle,  color: "#10B981" },
  paused:    { icon: PauseCircle,  color: "#F59E0B" },
  abandoned: { icon: XCircle,      color: "#6B7280" },
};

const CATEGORY_COLORS = {
  publication:   "#6366F1",
  grant:         "#F97316",
  collaboration: "#14B8A6",
  career:        "#8B5CF6",
  teaching:      "#EC4899",
  citation:      "#3B82F6",
  network:       "#10B981",
  other:         "#6B7280",
};

function GoalCard({ goal, onDelete, onUpdateStatus }) {
  const pct = goal.progress_pct ?? 0;
  const color = CATEGORY_COLORS[goal.category] || CATEGORY_COLORS.other;
  const si    = STATUS_ICON[goal.status] || STATUS_ICON.active;
  const StatusIcon = si.icon;

  return (
    <div className="border border-slate-200 rounded-lg p-4 hover:border-slate-300 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-start gap-2 flex-1 min-w-0">
          <StatusIcon size={14} color={si.color} className="flex-shrink-0 mt-0.5" />
          <div className="min-w-0">
            <p className="text-[13px] font-semibold text-slate-800 leading-snug">{goal.title}</p>
            <span
              className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wide text-white mt-0.5 inline-block"
              style={{ background: color }}
            >
              {goal.category}
            </span>
          </div>
        </div>
        <button onClick={() => onDelete(goal._id)} className="text-slate-300 hover:text-red-400 ml-2 flex-shrink-0">
          <Trash2 size={13} />
        </button>
      </div>

      {/* Progress bar */}
      <div className="mb-2">
        <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
          <span>{goal.current_value ?? 0} / {goal.target_value} {goal.unit}</span>
          <span>{pct}%</span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-2">
          <div
            className="h-2 rounded-full transition-all"
            style={{ width: `${pct}%`, background: pct >= 100 ? "#10B981" : color }}
          />
        </div>
      </div>

      {/* Evidence */}
      {goal.evidence?.length > 0 && (
        <p className="text-[10px] text-slate-400">
          {goal.evidence[0]?.detail}
        </p>
      )}
      {goal.urgency && goal.urgency !== "no_deadline" && (
        <p className={`text-[10px] mt-1 font-medium ${goal.urgency === "urgent" || goal.urgency === "overdue" ? "text-red-500" : "text-slate-400"}`}>
          {goal.urgency === "overdue" ? "Past deadline" : goal.urgency === "urgent" ? "Due within 30 days" : goal.urgency === "upcoming" ? "Due within 90 days" : ""}
        </p>
      )}

      {/* Status controls */}
      <div className="flex gap-1.5 mt-2">
        {["active", "paused", "completed", "abandoned"].map(s => (
          <button
            key={s}
            onClick={() => onUpdateStatus(goal._id, s)}
            className={`text-[9px] px-1.5 py-0.5 rounded capitalize transition-colors ${goal.status === s ? "bg-slate-700 text-white" : "bg-slate-100 text-slate-500 hover:bg-slate-200"}`}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function AddGoalForm({ onAdd, onCancel }) {
  const [form, setForm] = useState({
    title: "", category: "publication", target_value: 1, unit: "items", deadline: "",
  });

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.title.trim()) return;
    await onAdd(form);
  }

  return (
    <form onSubmit={handleSubmit} className="border border-blue-200 rounded-lg p-4 bg-blue-50/30 space-y-3">
      <input
        value={form.title}
        onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
        placeholder="Goal title (e.g., Publish 2 WoS papers)"
        className="w-full px-3 py-2 text-[12px] border border-slate-200 rounded-md focus:outline-none focus:border-blue-400"
        required
      />
      <div className="flex gap-2">
        <select
          value={form.category}
          onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
          className="flex-1 px-2 py-1.5 text-[11px] border border-slate-200 rounded-md focus:outline-none focus:border-blue-400 bg-white"
        >
          {["publication", "grant", "collaboration", "career", "teaching", "citation", "network", "other"].map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <input
          type="number"
          min="1"
          value={form.target_value}
          onChange={e => setForm(f => ({ ...f, target_value: parseInt(e.target.value) || 1 }))}
          className="w-20 px-2 py-1.5 text-[11px] border border-slate-200 rounded-md focus:outline-none focus:border-blue-400"
          placeholder="Target"
        />
        <input
          value={form.unit}
          onChange={e => setForm(f => ({ ...f, unit: e.target.value }))}
          placeholder="unit"
          className="w-20 px-2 py-1.5 text-[11px] border border-slate-200 rounded-md focus:outline-none focus:border-blue-400"
        />
      </div>
      <input
        type="date"
        value={form.deadline}
        onChange={e => setForm(f => ({ ...f, deadline: e.target.value }))}
        className="w-full px-2 py-1.5 text-[11px] border border-slate-200 rounded-md focus:outline-none focus:border-blue-400"
      />
      <div className="flex gap-2">
        <button type="submit" className="px-3 py-1.5 bg-blue-600 text-white text-[11px] font-medium rounded-md hover:bg-blue-700">
          Add Goal
        </button>
        <button type="button" onClick={onCancel} className="px-3 py-1.5 text-slate-500 text-[11px] hover:text-slate-700">
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function GoalTracker({ goals, loading, onRefresh }) {
  const [adding, setAdding] = useState(false);

  async function handleAdd(form) {
    try {
      await createGoal(form);
      setAdding(false);
      onRefresh?.();
    } catch { }
  }

  async function handleDelete(id) {
    try {
      await deleteGoal(id);
      onRefresh?.();
    } catch { }
  }

  async function handleStatus(id, status) {
    try {
      await updateGoal(id, { status });
      onRefresh?.();
    } catch { }
  }

  if (loading) {
    return <div className="text-center py-12 text-[11px] text-slate-400">Loading goals…</div>;
  }

  const allGoals = goals?.goals || [];
  const active   = allGoals.filter(g => g.status === "active");
  const done     = allGoals.filter(g => g.status === "completed");
  const paused   = allGoals.filter(g => ["paused", "abandoned"].includes(g.status));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex gap-3">
          {[
            { label: "Active", count: active.length, color: "text-blue-600" },
            { label: "Completed", count: done.length, color: "text-emerald-600" },
          ].map(s => (
            <div key={s.label}>
              <span className={`text-lg font-bold ${s.color}`}>{s.count}</span>
              <span className="text-[10px] text-slate-400 ml-1">{s.label}</span>
            </div>
          ))}
        </div>
        <button
          onClick={() => setAdding(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-[11px] font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={12} /> Add Goal
        </button>
      </div>

      {adding && <AddGoalForm onAdd={handleAdd} onCancel={() => setAdding(false)} />}

      {/* Active goals */}
      {active.length === 0 && !adding && (
        <div className="text-center py-8 text-[11px] text-slate-400">
          No active goals. Add one to start tracking your research progress.
        </div>
      )}
      <div className="space-y-2">
        {active.map(g => <GoalCard key={g._id} goal={g} onDelete={handleDelete} onUpdateStatus={handleStatus} />)}
      </div>

      {/* Completed */}
      {done.length > 0 && (
        <details>
          <summary className="text-[11px] font-medium text-slate-500 cursor-pointer hover:text-slate-700 select-none">
            {done.length} completed goal(s)
          </summary>
          <div className="mt-2 space-y-2">
            {done.map(g => <GoalCard key={g._id} goal={g} onDelete={handleDelete} onUpdateStatus={handleStatus} />)}
          </div>
        </details>
      )}

      {paused.length > 0 && (
        <details>
          <summary className="text-[11px] font-medium text-slate-500 cursor-pointer hover:text-slate-700 select-none">
            {paused.length} paused/abandoned goal(s)
          </summary>
          <div className="mt-2 space-y-2">
            {paused.map(g => <GoalCard key={g._id} goal={g} onDelete={handleDelete} onUpdateStatus={handleStatus} />)}
          </div>
        </details>
      )}

      <p className="text-[9px] text-slate-400 text-center">
        Auto-tracked goals (publication, grant, collaboration, teaching) update progress from platform data.
      </p>
    </div>
  );
}

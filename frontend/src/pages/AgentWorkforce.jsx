import React, { useState, useEffect, useCallback } from "react";
import { AIWorkspaceLayout } from "@/layouts";
import {
  Bot, Plus, RefreshCw, Play, Pause, CheckCircle, Clock,
  AlertCircle, XCircle, Calendar, Activity, ShieldCheck,
  ChevronRight, Loader, Bell, List,
} from "lucide-react";
import {
  listMissions, getMission, getMissionSteps, getMissionLogs,
  cancelMission, listAgents, getPendingApprovals,
  getMonitorAlerts, runMonitors, listSchedules,
  createMission,
} from "../services/araEngine";
import MissionCard from "../components/ara/MissionCard";
import MissionPlanner from "../components/ara/MissionPlanner";
import ApprovalGate from "../components/ara/ApprovalGate";

const TABS = [
  { id: "active",    label: "Active",           icon: Play },
  { id: "approvals", label: "Approvals",         icon: ShieldCheck },
  { id: "agents",    label: "Agent Roster",      icon: Bot },
  { id: "completed", label: "Completed",         icon: CheckCircle },
  { id: "scheduled", label: "Scheduled",         icon: Calendar },
  { id: "failed",    label: "Failed",            icon: XCircle },
  { id: "monitors",  label: "Monitors",          icon: Activity },
];

const AUTONOMY_LABELS = {
  0: "Manual",
  1: "Assist",
  2: "Semi-Auto",
  3: "Autonomous",
};

// ── New Mission Form ──────────────────────────────────────────────────────────

function NewMissionForm({ onCreated, onClose }) {
  const [form, setForm] = useState({
    title:          "",
    description:    "",
    mission_type:   "general",
    autonomy_level: 1,
  });
  const [loading, setLoading] = useState(false);

  function set(k, v) { setForm(f => ({ ...f, [k]: v })); }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.title.trim() || !form.description.trim()) return;
    setLoading(true);
    try {
      const res = await createMission(form);
      onCreated && onCreated(res.data);
    } catch (err) {
      alert("Failed to create mission: " + (err?.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }

  const missionTypes = [
    "manuscript", "literature", "funding", "review",
    "collaboration", "career", "teaching", "repository",
    "institution", "monitor", "general",
  ];

  return (
    <div className="rounded-md border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-800">New Research Mission</h3>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-sm">
          Cancel
        </button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Mission Title</label>
          <input
            className="w-full border border-slate-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-300"
            placeholder="e.g. Prepare manuscript for submission"
            value={form.title}
            onChange={e => set("title", e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Describe what you want the agents to do</label>
          <textarea
            className="w-full border border-slate-200 rounded px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-indigo-300"
            rows={3}
            placeholder="e.g. Review this manuscript for statistical issues, simulate peer review, find matching journals, and prepare a submission checklist."
            value={form.description}
            onChange={e => set("description", e.target.value)}
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Mission Type</label>
            <select
              className="w-full border border-slate-200 rounded px-3 py-2 text-sm focus:outline-none"
              value={form.mission_type}
              onChange={e => set("mission_type", e.target.value)}
            >
              {missionTypes.map(t => (
                <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Autonomy Level</label>
            <select
              className="w-full border border-slate-200 rounded px-3 py-2 text-sm focus:outline-none"
              value={form.autonomy_level}
              onChange={e => set("autonomy_level", parseInt(e.target.value))}
            >
              {Object.entries(AUTONOMY_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{k} — {v}</option>
              ))}
            </select>
          </div>
        </div>
        <p className="text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded">
          Agents never submit, send emails, or apply for grants without your explicit approval.
        </p>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Creating plan…" : "Create Mission"}
        </button>
      </form>
    </div>
  );
}


// ── Mission Detail ────────────────────────────────────────────────────────────

function MissionDetail({ missionId, onBack, onUpdated }) {
  const [mission,  setMission]  = useState(null);
  const [steps,    setSteps]    = useState([]);
  const [logs,     setLogs]     = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [tab,      setTab]      = useState("steps");

  const load = useCallback(async () => {
    try {
      const [m, s, l] = await Promise.all([
        getMission(missionId),
        getMissionSteps(missionId),
        getMissionLogs(missionId, 50),
      ]);
      setMission(m.data);
      setSteps(s.data);
      setLogs(l.data);
    } catch {}
    setLoading(false);
  }, [missionId]);

  useEffect(() => { load(); }, [load]);

  // Poll while running
  useEffect(() => {
    if (!mission) return;
    if (!["running", "planning", "awaiting_human"].includes(mission.status)) return;
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [mission, load]);

  if (loading) return <div className="p-6 text-slate-400 text-sm">Loading…</div>;
  if (!mission) return <div className="p-6 text-slate-500 text-sm">Mission not found.</div>;

  const pendingApprovals = steps.filter(s => s.status === "awaiting_approval");

  const StepStatusDot = ({ status }) => {
    const colors = {
      pending: "bg-slate-300", running: "bg-indigo-500 animate-pulse",
      completed: "bg-green-500", failed: "bg-red-500", skipped: "bg-slate-300",
      awaiting_approval: "bg-orange-500", approved: "bg-green-400", rejected: "bg-red-400",
    };
    return <span className={`inline-block w-2 h-2 rounded-full ${colors[status] || "bg-slate-300"}`} />;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-1">
        <button onClick={onBack} className="text-slate-400 hover:text-slate-600 text-sm">
          ← Back
        </button>
      </div>

      <div className="rounded-md border border-slate-200 bg-white p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold text-slate-800">{mission.title}</h2>
            <p className="text-xs text-slate-400 mt-0.5">{mission.description}</p>
          </div>
          <span className={`text-xs px-2 py-0.5 rounded-full capitalize font-medium
            ${mission.status === "completed" ? "bg-green-50 text-green-600" :
              mission.status === "failed"    ? "bg-red-50 text-red-500" :
              mission.status === "running"   ? "bg-indigo-50 text-indigo-600" :
              "bg-slate-50 text-slate-500"}`}>
            {mission.status.replace("_", " ")}
          </span>
        </div>
        {mission.total_steps > 0 && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-slate-400 mb-1">
              <span>{mission.completed_steps}/{mission.total_steps} steps</span>
            </div>
            <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all"
                style={{ width: `${mission.total_steps > 0 ? Math.round((mission.completed_steps/mission.total_steps)*100) : 0}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Plan review */}
      {mission.status === "plan_review" && steps.length > 0 && (
        <MissionPlanner
          mission={mission}
          steps={steps}
          onApproved={() => { onUpdated && onUpdated(); load(); }}
          onCancelled={async () => {
            await cancelMission(missionId);
            onBack();
          }}
        />
      )}

      {/* Pending approvals */}
      {pendingApprovals.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-orange-600 uppercase tracking-wide">Action Required</p>
          {pendingApprovals.map(step => (
            <ApprovalGate
              key={step.step_id}
              approval={{ _id: step.approval_id, ...step }}
              onResolved={() => load()}
            />
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-100">
        {[["steps","Steps"], ["logs","Logs"]].map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`px-3 py-2 text-xs font-medium transition-colors
              ${tab === id ? "text-indigo-600 border-b-2 border-indigo-500" : "text-slate-400 hover:text-slate-600"}`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "steps" && (
        <div className="space-y-2">
          {steps.map((step, i) => (
            <div key={step.step_id} className="rounded-md border border-slate-100 bg-white p-3">
              <div className="flex items-center gap-2">
                <StepStatusDot status={step.status} />
                <span className="text-xs text-slate-400">{i + 1}.</span>
                <span className="text-sm font-medium text-slate-700">{step.name}</span>
                <span className="ml-auto text-xs text-slate-400 capitalize">{step.status}</span>
              </div>
              {step.outputs?.summary && (
                <p className="text-xs text-slate-500 mt-2 ml-4 line-clamp-3">
                  {step.outputs.summary}
                </p>
              )}
              {step.outputs?.confidence && (
                <span className={`ml-4 mt-1 inline-block text-xs px-1.5 py-0.5 rounded
                  ${step.outputs.confidence === "high" ? "bg-green-50 text-green-600" :
                    step.outputs.confidence === "medium" ? "bg-amber-50 text-amber-600" :
                    "bg-slate-50 text-slate-400"}`}>
                  Confidence: {step.outputs.confidence}
                </span>
              )}
              {step.error && (
                <p className="text-xs text-red-500 mt-1 ml-4">{step.error}</p>
              )}
            </div>
          ))}
          {steps.length === 0 && (
            <p className="text-xs text-slate-400 text-center py-4">No steps yet.</p>
          )}
        </div>
      )}

      {tab === "logs" && (
        <div className="space-y-1 max-h-80 overflow-y-auto">
          {logs.map((log, i) => (
            <div key={i} className="flex gap-3 text-xs py-1.5 border-b border-slate-50">
              <span className="text-slate-300 shrink-0 font-mono">
                {log.created_at ? new Date(log.created_at).toLocaleTimeString() : ""}
              </span>
              <span className="text-indigo-500 shrink-0">[{log.agent}]</span>
              <span className="text-slate-600">{log.detail}</span>
            </div>
          ))}
          {logs.length === 0 && (
            <p className="text-xs text-slate-400 text-center py-4">No logs yet.</p>
          )}
        </div>
      )}

      {mission.result_summary && mission.status === "completed" && (
        <div className="rounded-md border border-green-100 bg-green-50 p-4">
          <p className="text-xs font-semibold text-green-700 mb-1">Mission Summary</p>
          <p className="text-sm text-green-800 whitespace-pre-line">{mission.result_summary}</p>
          {mission.validation && !mission.validation.passed && (
            <p className="text-xs text-amber-600 mt-2">
              Validation warnings: {mission.validation.warnings?.length ?? 0}
            </p>
          )}
        </div>
      )}
    </div>
  );
}


// ── Main Page ─────────────────────────────────────────────────────────────────

export default function AgentWorkforce() {
  const [tab,          setTab]          = useState("active");
  const [missions,     setMissions]     = useState([]);
  const [agents,       setAgents]       = useState([]);
  const [approvals,    setApprovals]    = useState([]);
  const [alerts,       setAlerts]       = useState([]);
  const [schedules,    setSchedules]    = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [showNew,      setShowNew]      = useState(false);
  const [selected,     setSelected]     = useState(null); // mission id for detail view
  const [newMission,   setNewMission]   = useState(null); // freshly created mission for plan review

  const loadTab = useCallback(async (t) => {
    setLoading(true);
    try {
      if (t === "active") {
        const statuses = ["running", "plan_review", "awaiting_human", "paused", "planning", "draft"];
        const all = await Promise.all(statuses.map(s => listMissions(s, 10)));
        setMissions(all.flatMap(r => r.data || []));
      } else if (t === "completed") {
        const r = await listMissions("completed", 20);
        setMissions(r.data || []);
      } else if (t === "failed") {
        const [f, c] = await Promise.all([listMissions("failed", 10), listMissions("cancelled", 10)]);
        setMissions([...(f.data||[]), ...(c.data||[])]);
      } else if (t === "agents") {
        const r = await listAgents();
        setAgents(r.data?.agents || []);
      } else if (t === "approvals") {
        const r = await getPendingApprovals();
        setApprovals(r.data || []);
      } else if (t === "monitors") {
        const [a, s] = await Promise.all([getMonitorAlerts(20), listSchedules()]);
        setAlerts(a.data || []);
        setSchedules(s.data || []);
      } else if (t === "scheduled") {
        const r = await listSchedules();
        setSchedules(r.data || []);
      }
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => {
    setSelected(null);
    loadTab(tab);
  }, [tab, loadTab]);

  function handleMissionCreated(data) {
    setShowNew(false);
    setNewMission(data);
    setTab("active");
    loadTab("active");
  }

  const pageActions = (
    <>
      <button
        onClick={() => loadTab(tab)}
        className="p-2 text-slate-400 hover:text-slate-600 border border-slate-200 rounded"
      >
        <RefreshCw size={15} />
      </button>
      <button
        onClick={() => setShowNew(v => !v)}
        className="flex items-center gap-2 px-3 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
      >
        <Plus size={15} />
        New Mission
      </button>
    </>
  );

  if (selected) {
    return (
      <AIWorkspaceLayout
        title="Agent Workforce"
        subtitle="Autonomous research agents that execute workflows while you stay in control"
        actions={pageActions}
      >
          <MissionDetail
            missionId={selected}
            onBack={() => { setSelected(null); loadTab(tab); }}
            onUpdated={() => loadTab(tab)}
          />
      </AIWorkspaceLayout>
    );
  }

  return (
    <AIWorkspaceLayout
      title="Agent Workforce"
      subtitle="Autonomous research agents that execute workflows while you stay in control"
      actions={pageActions}
    >

      {/* New mission form */}
      {showNew && (
        <div className="mb-6">
          <NewMissionForm
            onCreated={handleMissionCreated}
            onClose={() => setShowNew(false)}
          />
        </div>
      )}

      {/* Plan review for freshly-created mission */}
      {newMission && newMission.status === "plan_review" && (
        <div className="mb-6">
          <p className="text-sm font-medium text-slate-700 mb-2">
            Plan ready — review and approve:
          </p>
          <MissionPlanner
            mission={{ _id: newMission.mission_id, ...newMission }}
            steps={newMission.steps || []}
            onApproved={() => { setNewMission(null); loadTab("active"); }}
            onCancelled={async () => {
              try { await cancelMission(newMission.mission_id); } catch {}
              setNewMission(null);
            }}
          />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-0.5 border-b border-slate-100 mb-5 overflow-x-auto">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium whitespace-nowrap transition-colors
              ${tab === id
                ? "text-indigo-600 border-b-2 border-indigo-500"
                : "text-slate-400 hover:text-slate-600"}`}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {loading ? (
        <div className="flex items-center justify-center py-12 text-slate-400">
          <Loader size={20} className="animate-spin mr-2" />
          Loading…
        </div>
      ) : (
        <>
          {/* Active / Completed / Failed missions */}
          {["active","completed","failed"].includes(tab) && (
            missions.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-sm">
                No missions in this category.
                {tab === "active" && (
                  <p className="mt-2">
                    <button
                      onClick={() => setShowNew(true)}
                      className="text-indigo-500 hover:underline"
                    >
                      Create your first mission →
                    </button>
                  </p>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {missions.map(m => (
                  <MissionCard
                    key={m._id}
                    mission={m}
                    onClick={mission => setSelected(mission._id)}
                  />
                ))}
              </div>
            )
          )}

          {/* Pending approvals */}
          {tab === "approvals" && (
            approvals.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-sm">
                No pending approvals. Agents are running autonomously within their permitted actions.
              </div>
            ) : (
              <div className="space-y-3">
                {approvals.map(a => (
                  <div key={a._id} className="rounded-md border border-slate-200 bg-white p-4">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-sm font-medium text-slate-700">
                        Mission: <span className="text-indigo-600">{a.mission_id?.slice(-8)}</span>
                      </p>
                      <span className="text-xs text-slate-300">
                        {a.created_at ? new Date(a.created_at).toLocaleString() : ""}
                      </span>
                    </div>
                    <ApprovalGate
                      approval={a}
                      onResolved={() => loadTab("approvals")}
                    />
                  </div>
                ))}
              </div>
            )
          )}

          {/* Agent roster */}
          {tab === "agents" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {agents.map(agent => (
                <div key={agent.name} className="rounded-md border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-medium text-sm text-slate-800">{agent.label}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full
                      ${agent.health === "active" ? "bg-green-50 text-green-600" : "bg-slate-50 text-slate-400"}`}>
                      {agent.health}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 line-clamp-2 mb-2">{agent.mission}</p>
                  <div className="flex flex-wrap gap-1">
                    {(agent.safe_actions || []).slice(0, 3).map(a => (
                      <span key={a} className="text-xs bg-green-50 text-green-600 px-1.5 py-0.5 rounded">
                        {a.replace("_", " ")}
                      </span>
                    ))}
                    {(agent.approval_required_actions || []).slice(0, 2).map(a => (
                      <span key={a} className="text-xs bg-orange-50 text-orange-600 px-1.5 py-0.5 rounded">
                        {a.replace("_", " ")} ⚠
                      </span>
                    ))}
                  </div>
                  <p className="text-xs text-slate-300 mt-2">
                    ~{agent.cost_estimate_credits} credits · ~{Math.ceil(agent.estimated_duration_s / 60)} min
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Schedules */}
          {tab === "scheduled" && (
            schedules.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-sm">
                No scheduled missions. Use the API to set up recurring workflows.
              </div>
            ) : (
              <div className="space-y-2">
                {schedules.map(s => (
                  <div key={s._id} className="rounded-md border border-slate-200 bg-white p-4 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-700">{s.title}</p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {s.interval} · {s.mission_type}
                        {s.last_run && ` · Last: ${new Date(s.last_run).toLocaleDateString()}`}
                      </p>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${s.active ? "bg-green-50 text-green-600" : "bg-slate-50 text-slate-400"}`}>
                      {s.active ? "Active" : "Paused"}
                    </span>
                  </div>
                ))}
              </div>
            )
          )}

          {/* Monitors */}
          {tab === "monitors" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-600">
                  Background monitors watch publications, grants, and trends continuously.
                </p>
                <button
                  onClick={async () => {
                    try {
                      await runMonitors();
                      setTimeout(() => loadTab("monitors"), 3000);
                    } catch {}
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-200 rounded hover:bg-slate-50"
                >
                  <Play size={13} />
                  Run Now
                </button>
              </div>
              {alerts.length === 0 ? (
                <p className="text-center py-8 text-slate-400 text-sm">
                  No alerts yet. Click "Run Now" to check for updates.
                </p>
              ) : (
                <div className="space-y-2">
                  {alerts.map((a, i) => (
                    <div key={i} className="rounded-md border border-slate-100 bg-white p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-sm font-medium text-slate-700">{a.data?.title || a.detail}</p>
                          <p className="text-xs text-slate-400 mt-0.5">{a.data?.body || ""}</p>
                        </div>
                        <span className="text-xs text-slate-300 shrink-0">
                          {a.created_at ? new Date(a.created_at).toLocaleDateString() : ""}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </AIWorkspaceLayout>
  );
}

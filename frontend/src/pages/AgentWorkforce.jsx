import React, { useState, useEffect, useCallback } from "react";
import { ResearchLayout } from "@/layouts";
import { AI_NAV_ITEMS } from "@/lib/navItems";
import {
  Bot, Plus, RefreshCw, Play, Pause, CheckCircle, Clock,
  AlertCircle, XCircle, Calendar, Activity, ShieldCheck,
  ChevronRight, Bell, List,
} from "lucide-react";
import {
  listMissions, getMission, getMissionSteps, getMissionLogs,
  cancelMission, listAgents, getPendingApprovals,
  getMonitorAlerts, runMonitors, listSchedules,
  createMission,
} from "../services/araEngine";
import { toast } from "sonner";
import MissionCard from "../components/ara/MissionCard";
import MissionPlanner from "../components/ara/MissionPlanner";
import ApprovalGate from "../components/ara/ApprovalGate";
import { Card } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { Alert } from "@/components/ds/Alert";
import { Badge } from "@/components/ds/Badge";
import { NavTabs } from "@/components/ds/NavTabs";
import { EmptyState } from "@/components/ds/EmptyState";
import { Spinner } from "@/components/ds/LoadingState";
import { ProgressBar } from "@/components/ds/Progress";

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
      toast.error("Failed to create mission: " + (err?.response?.data?.detail || err.message));
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
    <Card padding="lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-800">New Research Mission</h3>
        <Button onClick={onClose} variant="link" size="sm">
          Cancel
        </Button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        <Input
          label="Mission Title"
          placeholder="e.g. Prepare manuscript for submission"
          value={form.title}
          onChange={e => set("title", e.target.value)}
          required
        />
        <Textarea
          label="Describe what you want the agents to do"
          rows={3}
          placeholder="e.g. Review this manuscript for statistical issues, simulate peer review, find matching journals, and prepare a submission checklist."
          value={form.description}
          onChange={e => set("description", e.target.value)}
          required
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FormSelect
            label="Mission Type"
            value={form.mission_type}
            onChange={e => set("mission_type", e.target.value)}
          >
            {missionTypes.map(t => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </FormSelect>
          <FormSelect
            label="Autonomy Level"
            value={form.autonomy_level}
            onChange={e => set("autonomy_level", parseInt(e.target.value))}
          >
            {Object.entries(AUTONOMY_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{k} — {v}</option>
            ))}
          </FormSelect>
        </div>
        <Alert variant="warning">
          Agents never submit, send emails, or apply for grants without your explicit approval.
        </Alert>
        <Button type="submit" disabled={loading} loading={loading} variant="primary" className="w-full">
          {loading ? "Creating plan…" : "Create Mission"}
        </Button>
      </form>
    </Card>
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

  if (loading) return (
    <div className="p-6 text-slate-400 text-sm flex items-center gap-2">
      <Spinner size={14} /> Loading…
    </div>
  );
  if (!mission) return <div className="p-6 text-slate-500 text-sm">Mission not found.</div>;

  const pendingApprovals = steps.filter(s => s.status === "awaiting_approval");

  const STATUS_DOT_COLOR = {
    pending: "#CBD5E1", running: "#6366F1",
    completed: "#22C55E", failed: "#EF4444", skipped: "#CBD5E1",
    awaiting_approval: "#F97316", approved: "#4ADE80", rejected: "#F87171",
  };

  const StepStatusDot = ({ status }) => (
    <span
      className={status === "running" ? "animate-pulse" : ""}
      style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: STATUS_DOT_COLOR[status] || "#CBD5E1" }}
    />
  );

  const MISSION_STATUS_BADGE = {
    completed: "success",
    failed: "danger",
    running: "info",
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-1">
        <Button onClick={onBack} variant="link" size="sm">
          ← Back
        </Button>
      </div>

      <Card padding="md">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold text-slate-800">{mission.title}</h2>
            <p className="text-xs text-slate-400 mt-0.5">{mission.description}</p>
          </div>
          <Badge variant={MISSION_STATUS_BADGE[mission.status] || "neutral"} className="capitalize">
            {mission.status.replace("_", " ")}
          </Badge>
        </div>
        {mission.total_steps > 0 && (
          <div className="mt-3">
            <ProgressBar
              value={mission.completed_steps}
              max={mission.total_steps}
              valueLabel={`${mission.completed_steps}/${mission.total_steps} steps`}
              size="sm"
            />
          </div>
        )}
      </Card>

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
      <NavTabs
        tabs={[{ id: "steps", label: "Steps" }, { id: "logs", label: "Logs" }]}
        active={tab}
        onChange={setTab}
        size="sm"
      />

      {tab === "steps" && (
        <div className="space-y-2">
          {steps.map((step, i) => (
            <Card key={step.step_id} padding="sm">
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
                <div className="ml-4 mt-1">
                  <Badge
                    size="sm"
                    variant={
                      step.outputs.confidence === "high" ? "success" :
                      step.outputs.confidence === "medium" ? "warning" : "neutral"
                    }
                  >
                    Confidence: {step.outputs.confidence}
                  </Badge>
                </div>
              )}
              {step.error && (
                <p className="text-xs text-red-500 mt-1 ml-4">{step.error}</p>
              )}
            </Card>
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
        <Alert variant="success" title="Mission Summary">
          <p className="whitespace-pre-line">{mission.result_summary}</p>
          {mission.validation && !mission.validation.passed && (
            <p className="text-xs text-amber-600 mt-2">
              Validation warnings: {mission.validation.warnings?.length ?? 0}
            </p>
          )}
        </Alert>
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
      <Button onClick={() => loadTab(tab)} variant="hero" size="icon" aria-label="Refresh">
        <RefreshCw size={15} />
      </Button>
      <Button onClick={() => setShowNew(v => !v)} variant="hero" size="sm">
        <Plus size={15} />
        New Mission
      </Button>
    </>
  );

  if (selected) {
    return (
      <ResearchLayout
        navItems={AI_NAV_ITEMS}
        title="Agent Workforce"
        subtitle="Autonomous research agents that execute workflows while you stay in control"
        actions={pageActions}
      >
          <MissionDetail
            missionId={selected}
            onBack={() => { setSelected(null); loadTab(tab); }}
            onUpdated={() => loadTab(tab)}
          />
      </ResearchLayout>
    );
  }

  return (
    <ResearchLayout
      navItems={AI_NAV_ITEMS}
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
      <div className="mb-5 overflow-x-auto">
        <NavTabs tabs={TABS} active={tab} onChange={setTab} />
      </div>

      {/* Tab content */}
      {loading ? (
        <div className="flex items-center justify-center py-12 text-slate-400">
          <Spinner size={20} className="mr-2" />
          Loading…
        </div>
      ) : (
        <>
          {/* Active / Completed / Failed missions */}
          {["active","completed","failed"].includes(tab) && (
            missions.length === 0 ? (
              <EmptyState
                title="No missions in this category."
                action={tab === "active" && (
                  <Button onClick={() => setShowNew(true)} variant="link" size="sm">
                    Create your first mission →
                  </Button>
                )}
              />
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
              <EmptyState title="No pending approvals. Agents are running autonomously within their permitted actions." />
            ) : (
              <div className="space-y-3">
                {approvals.map(a => (
                  <Card key={a._id} padding="md">
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
                  </Card>
                ))}
              </div>
            )
          )}

          {/* Agent roster */}
          {tab === "agents" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {agents.map(agent => (
                <Card key={agent.name} padding="md">
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-medium text-sm text-slate-800">{agent.label}</p>
                    <Badge variant={agent.health === "active" ? "success" : "neutral"}>
                      {agent.health}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500 line-clamp-2 mb-2">{agent.mission}</p>
                  <div className="flex flex-wrap gap-1">
                    {(agent.safe_actions || []).slice(0, 3).map(a => (
                      <Badge key={a} variant="success" size="sm">
                        {a.replace("_", " ")}
                      </Badge>
                    ))}
                    {(agent.approval_required_actions || []).slice(0, 2).map(a => (
                      <Badge key={a} variant="warning" size="sm">
                        {a.replace("_", " ")} ⚠
                      </Badge>
                    ))}
                  </div>
                  <p className="text-xs text-slate-300 mt-2">
                    ~{agent.cost_estimate_credits} credits · ~{Math.ceil(agent.estimated_duration_s / 60)} min
                  </p>
                </Card>
              ))}
            </div>
          )}

          {/* Schedules */}
          {tab === "scheduled" && (
            schedules.length === 0 ? (
              <EmptyState title="No scheduled missions. Use the API to set up recurring workflows." />
            ) : (
              <div className="space-y-2">
                {schedules.map(s => (
                  <Card key={s._id} padding="md" className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-700">{s.title}</p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {s.interval} · {s.mission_type}
                        {s.last_run && ` · Last: ${new Date(s.last_run).toLocaleDateString()}`}
                      </p>
                    </div>
                    <Badge variant={s.active ? "success" : "neutral"}>
                      {s.active ? "Active" : "Paused"}
                    </Badge>
                  </Card>
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
                <Button
                  onClick={async () => {
                    try {
                      await runMonitors();
                      setTimeout(() => loadTab("monitors"), 3000);
                    } catch {}
                  }}
                  variant="ghost"
                  size="sm"
                >
                  <Play size={13} />
                  Run Now
                </Button>
              </div>
              {alerts.length === 0 ? (
                <EmptyState size="sm" title="No alerts yet. Click &quot;Run Now&quot; to check for updates." />
              ) : (
                <div className="space-y-2">
                  {alerts.map((a, i) => (
                    <Card key={i} padding="sm">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="text-sm font-medium text-slate-700">{a.data?.title || a.detail}</p>
                          <p className="text-xs text-slate-400 mt-0.5">{a.data?.body || ""}</p>
                        </div>
                        <span className="text-xs text-slate-300 shrink-0">
                          {a.created_at ? new Date(a.created_at).toLocaleDateString() : ""}
                        </span>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </ResearchLayout>
  );
}

import React, { useState, useEffect, useCallback } from "react";
import { Target, Trash2, Pencil, ChevronDown, ChevronUp } from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Badge, Button, Modal, Input, FormSelect, NavTabs, EmptyState, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const GOAL_TYPES = ["publication", "grant", "career", "teaching", "collaboration", "citation", "degree", "trust", "reputation", "other"];
const RISK_COLOR = { low: EMERALD, medium: "#f59e0b", high: "#f97316", critical: "#dc2626" };
const STATUS_COLOR = { active: ACCENT, completed: EMERALD, paused: "#94a3b8" };

function GoalCard({ goal, onUpdate, onDelete }) {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [progress, setProgress] = useState(goal.progress || 0);
  const [saving, setSaving] = useState(false);

  const saveProgress = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/sie/goals/${goal.id}`, {
        method: "PUT",
        headers: { ...authH(), "Content-Type": "application/json" },
        body: JSON.stringify({ progress }),
      });
      if (r.ok) onUpdate(await r.json());
    } catch (_) {}
    setSaving(false);
    setEditing(false);
  };

  const riskColor = RISK_COLOR[goal.risk_level] || "#94a3b8";
  const statusColor = STATUS_COLOR[goal.status] || ACCENT;

  return (
    <Card padding="none" style={{ marginBottom: 10, overflow: "hidden" }}>
      <div style={{ padding: "14px 16px", display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ flex: 1, cursor: "pointer" }} onClick={() => setOpen(v => !v)}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ fontWeight: 700, fontSize: 14, color: NAVY }}>{goal.title}</span>
            <Badge color={statusColor} size="sm" style={{ textTransform: "uppercase" }}>{goal.status}</Badge>
            <Badge color={riskColor} size="sm">Risk: {goal.risk_level}</Badge>
          </div>
          {/* Progress fill: kept hand-rolled — ds/ProgressBar's fill color is
              either fixed navy or driven by its own colorByValue thresholds,
              with no way to pin it to this goal's constant ACCENT tone that
              pairs with the ACCENT percentage label beside it */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ flex: 1, height: 6, background: `${NAVY}15`, borderRadius: 3 }}>
              <div style={{ width: `${goal.progress || 0}%`, height: "100%", background: ACCENT, borderRadius: 3, transition: "width 0.3s" }} />
            </div>
            <span style={{ fontSize: 12, fontWeight: 700, color: ACCENT, minWidth: 36 }}>{goal.progress || 0}%</span>
          </div>
        </div>
        {/* Icon-only row controls: bare 14px icons — Button's smallest
            ("icon", 36px) size would visually overpower this compact header
            row, so they're left hand-rolled */}
        <div style={{ display: "flex", gap: 4 }}>
          <Button
            size="icon"
            variant="ghost"
            onClick={() => setEditing(v => !v)}
            style={{
              padding: 4,
              color: TEXT_SECONDARY
            }}>
            <Pencil size={14} />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            onClick={() => onDelete(goal.id)}
            style={{
              padding: 4,
              color: "#dc2626"
            }}>
            <Trash2 size={14} />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            onClick={() => setOpen(v => !v)}
            style={{
              padding: 4,
              color: TEXT_SECONDARY
            }}>
            {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </Button>
        </div>
      </div>
      {editing && (
        <div style={{ padding: "0 16px 12px", borderTop: `1px solid ${BRD}`, paddingTop: 12 }}>
          <label style={{ fontSize: 12, color: TEXT_SECONDARY, display: "block", marginBottom: 4 }}>Update Progress ({progress}%)</label>
          {/* Range slider: left as a native <input type="range"> — ds/Input's
              styling targets text-like fields and would override the native
              track/thumb rendering a range control needs */}
          <div style={{ display: "flex", gap: 8 }}>
            <input type="range" min={0} max={100} value={progress} onChange={e => setProgress(Number(e.target.value))} style={{ flex: 1 }} />
            <Button onClick={saveProgress} loading={saving} disabled={saving} size="sm" style={{ background: ACCENT }}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      )}
      {open && (
        <div style={{ padding: "10px 16px 14px", borderTop: `1px solid ${BRD}`, background: WARM }}>
          {goal.description && <p style={{ margin: "0 0 10px", fontSize: 13, color: "#334155" }}>{goal.description}</p>}
          <div style={{ display: "flex", gap: 16, marginBottom: 10, flexWrap: "wrap" }}>
            <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>Type: <strong style={{ color: NAVY }}>{goal.type}</strong></span>
            <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>Priority: <strong style={{ color: NAVY }}>{goal.priority}/5</strong></span>
            {goal.deadline && <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>Deadline: <strong style={{ color: NAVY }}>{goal.deadline?.slice(0, 10)}</strong></span>}
            {goal.estimated_completion && <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>Est. completion: <strong style={{ color: EMERALD }}>{goal.estimated_completion}</strong></span>}
          </div>
          {goal.ai_recommendations?.length > 0 && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: ACCENT, marginBottom: 6, letterSpacing: "0.05em" }}>AI RECOMMENDATIONS</div>
              {goal.ai_recommendations.map((rec, i) => (
                <div key={i} style={{ display: "flex", gap: 6, marginBottom: 4 }}>
                  <span style={{ color: ACCENT, fontSize: 12, flexShrink: 0 }}>→</span>
                  <span style={{ fontSize: 12, color: "#334155" }}>{rec}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function NewGoalModal({ onClose, onCreate }) {
  const [form, setForm] = useState({ title: "", description: "", type: "publication", priority: 3, deadline: "" });
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/sie/goals`, {
        method: "POST",
        headers: { ...authH(), "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (r.ok) { onCreate(await r.json()); onClose(); }
    } catch (_) {}
    setSaving(false);
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="New Research Goal"
      footer={
        <Button onClick={submit} loading={saving} disabled={saving || !form.title.trim()} className="w-full">
          {saving ? "Creating…" : "Create Goal"}
        </Button>
      }
    >
      {[
        { label: "Title", key: "title", type: "text", placeholder: "e.g. Publish 3 Q1 papers" },
        { label: "Description (optional)", key: "description", type: "text", placeholder: "Additional context…" },
        { label: "Deadline (optional)", key: "deadline", type: "date" },
      ].map(({ label, key, type, placeholder }) => (
        <div key={key} style={{ marginBottom: 14 }}>
          <Input
            label={label}
            type={type}
            placeholder={placeholder}
            value={form[key]}
            onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
          />
        </div>
      ))}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <FormSelect
          label="Type"
          value={form.type}
          onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
        >
          {GOAL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </FormSelect>
        <Input
          label="Priority (1-5)"
          type="number"
          min={1}
          max={5}
          value={form.priority}
          onChange={e => setForm(f => ({ ...f, priority: Number(e.target.value) }))}
        />
      </div>
    </Modal>
  );
}

export default function GoalManager() {
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [filter, setFilter] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/sie/goals`, { headers: authH() });
      if (r.ok) setGoals(await r.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this goal?")) return;
    await fetch(`${API}/api/sie/goals/${id}`, { method: "DELETE", headers: authH() });
    setGoals(g => g.filter(x => x.id !== id));
  };

  const displayed = filter === "all" ? goals : goals.filter(g => g.status === filter);
  const active = goals.filter(g => g.status === "active").length;
  const completed = goals.filter(g => g.status === "completed").length;

  return (
    <AIWorkspaceLayout
      title="Research Goals"
      subtitle="Set, track, and achieve your research goals with AI guidance."
      navItems={SIE_NAV_ITEMS}
    >

      <div style={{ marginBottom: 16 }}>
        <NavTabs
          variant="pill"
          tabs={["all", "active", "completed", "paused"].map(f => ({ id: f, label: f.charAt(0).toUpperCase() + f.slice(1) }))}
          active={filter}
          onChange={setFilter}
        />
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 40 }}><Spinner size={28} color={ACCENT} /></div>
      ) : displayed.length === 0 ? (
        <EmptyState
          icon={<Target />}
          title="No goals yet"
          description="Define your first research goal to unlock AI planning."
          action={<Button onClick={() => setShowNew(true)}>Create First Goal</Button>}
        />
      ) : (
        displayed.map(g => (
          <GoalCard key={g.id} goal={g}
            onUpdate={updated => setGoals(gs => gs.map(x => x.id === updated.id ? updated : x))}
            onDelete={handleDelete}
          />
        ))
      )}

      {showNew && <NewGoalModal onClose={() => setShowNew(false)} onCreate={g => { setGoals(gs => [g, ...gs]); }} />}
    </AIWorkspaceLayout>
  );
}

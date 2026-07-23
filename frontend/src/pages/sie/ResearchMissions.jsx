import React, { useState, useEffect, useCallback } from "react";
import { CheckSquare, Plus, Check, X, Pencil } from "lucide-react";
import { NAVY, BRD, ACCENT, EMERALD, WHITE, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Button, Modal, Input, FormSelect, NavTabs, EmptyState, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const STATUS_COLOR = { pending: "#94a3b8", in_progress: "#f59e0b", completed: EMERALD };
const MISSION_TYPES = ["literature_review","data_collection","writing","submission","revision","conference","grant_application","collaboration","analysis","presentation","teaching","admin","other"];

function MissionCard({ mission, onComplete, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [progress, setProgress] = useState(mission.completion || 0);
  const color = STATUS_COLOR[mission.status] || "#94a3b8";

  const save = async () => {
    const r = await fetch(`${API}/api/sie/missions/${mission.id}`, {
      method: "PUT", headers: { ...authH(), "Content-Type": "application/json" },
      body: JSON.stringify({ completion: progress }),
    });
    if (r.ok) { onUpdate(await r.json()); setEditing(false); }
  };

  return (
    <Card
      accent={color}
      padding="md"
      style={{
        background: mission.status === "completed" ? `${EMERALD}06` : undefined,
        opacity: mission.status === "completed" ? 0.75 : 1,
        marginBottom: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {/* Completion toggle: circular check control — no ds/ primitive for
            this shape, left hand-rolled */}
        <button onClick={() => onComplete(mission.id)} style={{
          width: 22, height: 22, borderRadius: "50%",
          background: mission.status === "completed" ? EMERALD : "transparent",
          border: `2px solid ${color}`, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}>
          {mission.status === "completed" && <Check size={12} color={WHITE} />}
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: NAVY, textDecoration: mission.status === "completed" ? "line-through" : "none" }}>
            {mission.title}
          </div>
          <div style={{ display: "flex", gap: 10, marginTop: 3 }}>
            <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>{mission.type?.replace(/_/g, " ")}</span>
            <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>~{mission.estimated_hours}h</span>
            <span style={{ fontSize: 11, fontWeight: 700, color }}>P{mission.priority}</span>
            {mission.due_date && <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>Due: {mission.due_date?.slice(0, 10)}</span>}
          </div>
        </div>
        {/* Edit control: bare 13px icon-only button — Button's smallest
            ("icon", 36px) size would visually overpower this compact row,
            so it's left hand-rolled */}
        <div style={{ display: "flex", gap: 4 }}>
          <Button
            size="icon"
            variant="ghost"
            onClick={() => setEditing(v => !v)}
            style={{
              padding: 3,
              color: TEXT_SECONDARY
            }}>
            <Pencil size={13} />
          </Button>
        </div>
      </div>
      {editing && (
        <div style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${BRD}` }}>
          {/* Range slider: left as a native <input type="range"> — ds/Input's
              styling targets text-like fields and would override the native
              track/thumb rendering a range control needs */}
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>Progress ({progress}%)</span>
            <input type="range" min={0} max={100} value={progress} onChange={e => setProgress(Number(e.target.value))} style={{ flex: 1 }} />
            <Button onClick={save} size="sm" style={{ background: ACCENT }}>Save</Button>
            <Button size="icon" variant="ghost" onClick={() => setEditing(false)}><X size={13} color={TEXT_SECONDARY} /></Button>
          </div>
        </div>
      )}
    </Card>
  );
}

function NewMissionModal({ onClose, onCreate }) {
  const [form, setForm] = useState({ title: "", type: "writing", priority: 3, difficulty: 3, estimated_hours: 4, description: "" });
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/sie/missions`, {
        method: "POST", headers: { ...authH(), "Content-Type": "application/json" },
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
      title="New Mission"
      footer={
        <Button onClick={submit} loading={saving} disabled={saving || !form.title.trim()} className="w-full" style={{ background: EMERALD }}>
          {saving ? "Creating…" : "Create Mission"}
        </Button>
      }
    >
      <div style={{ marginBottom: 14 }}>
        <Input
          label="Title"
          type="text"
          placeholder="e.g. Write introduction section"
          value={form.title}
          onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
        />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <FormSelect
          label="Type"
          value={form.type}
          onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
        >
          {MISSION_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </FormSelect>
        <Input
          label="Est. Hours"
          type="number"
          min={0.5}
          step={0.5}
          value={form.estimated_hours}
          onChange={e => setForm(f => ({ ...f, estimated_hours: Number(e.target.value) }))}
        />
        <Input
          label="Priority (1-5)"
          type="number"
          min={1}
          max={5}
          value={form.priority}
          onChange={e => setForm(f => ({ ...f, priority: Number(e.target.value) }))}
        />
        <Input
          label="Difficulty (1-5)"
          type="number"
          min={1}
          max={5}
          value={form.difficulty}
          onChange={e => setForm(f => ({ ...f, difficulty: Number(e.target.value) }))}
        />
      </div>
    </Modal>
  );
}

export default function ResearchMissions() {
  const [missions, setMissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [filter, setFilter] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/sie/missions`, { headers: authH() });
      if (r.ok) setMissions(await r.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleComplete = async (id) => {
    const r = await fetch(`${API}/api/sie/missions/${id}/complete`, { method: "POST", headers: authH() });
    if (r.ok) setMissions(ms => ms.map(m => m.id === id ? { ...m, status: "completed", completion: 100 } : m));
  };

  const displayed = filter === "all" ? missions : missions.filter(m => m.status === filter);
  const pending = missions.filter(m => m.status === "pending").length;
  const completed = missions.filter(m => m.status === "completed").length;

  return (
    <AIWorkspaceLayout
      title="Research Missions"
      subtitle={`${pending} pending · ${completed} completed`}
      navItems={SIE_NAV_ITEMS}
      actions={
        <Button onClick={() => setShowNew(true)} size="sm">
          <Plus size={13} /> New Mission
        </Button>
      }
    >

      <div style={{ marginBottom: 16 }}>
        <NavTabs
          variant="pill"
          tabs={["all", "pending", "in_progress", "completed"].map(f => ({
            id: f,
            label: f === "all" ? `All (${missions.length})` : f.replace("_", " "),
          }))}
          active={filter}
          onChange={setFilter}
        />
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 40 }}><Spinner size={28} color={ACCENT} /></div>
      ) : displayed.length === 0 ? (
        <EmptyState
          icon={<CheckSquare />}
          title="No missions in this view"
          description="Create a mission or generate missions from a goal."
          action={<Button onClick={() => setShowNew(true)} style={{ background: EMERALD }}>Create Mission</Button>}
        />
      ) : (
        displayed.map(m => (
          <MissionCard key={m.id} mission={m}
            onComplete={handleComplete}
            onUpdate={updated => setMissions(ms => ms.map(x => x.id === updated.id ? updated : x))}
          />
        ))
      )}

      {showNew && <NewMissionModal onClose={() => setShowNew(false)} onCreate={m => setMissions(ms => [m, ...ms])} />}
    </AIWorkspaceLayout>
  );
}

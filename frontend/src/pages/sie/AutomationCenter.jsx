import React, { useState, useEffect, useCallback } from "react";
import { Zap, Play, Trash2 } from "lucide-react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Tag, Button, Modal, Input, FormSelect, Alert, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const AUTOMATION_TYPES = [
  "monitor_journal","monitor_grant","monitor_citation","monitor_collaborator",
  "deadline_reminder","weekly_report","goal_check","recommendation_refresh",
];
const TYPE_COLOR = { deadline_reminder: "#f97316", goal_check: ACCENT, weekly_report: "#8b5cf6", recommendation_refresh: EMERALD, monitor_journal: "#0ea5e9", monitor_grant: "#ec4899", monitor_citation: "#f59e0b", monitor_collaborator: "#14b8a6" };

function AutomationCard({ auto, onToggle, onRun, onDelete }) {
  const color = TYPE_COLOR[auto.type] || ACCENT;
  const [running, setRunning] = useState(false);

  const run = async () => {
    setRunning(true);
    await onRun(auto.id);
    setRunning(false);
  };

  return (
    <Card padding="md" style={{ display: "flex", gap: 12, alignItems: "center" }}>
      <div style={{ width: 38, height: 38, borderRadius: 10, background: `${color}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <Zap size={18} color={color} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: NAVY }}>{auto.name}</div>
        <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{auto.description}</div>
        <div style={{ display: "flex", gap: 10, marginTop: 3 }}>
          <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>Schedule: <strong style={{ color: NAVY }}>{auto.schedule}</strong></span>
          <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>Runs: <strong style={{ color: NAVY }}>{auto.run_count}</strong></span>
          {auto.last_run && <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>Last: {auto.last_run?.slice(0, 10)}</span>}
        </div>
      </div>
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <Tag onClick={() => onToggle(auto.id, !auto.enabled)} color={auto.enabled ? EMERALD : ACCENT}>
          {auto.enabled ? "Enabled" : "Disabled"}
        </Tag>
        <Button onClick={run} loading={running} disabled={running || !auto.enabled} variant="primary" size="sm">
          {!running && <Play size={12} />}
        </Button>
        {/* Delete control: bare 14px icon-only button — Button's smallest
            ("icon", 36px) size would visually overpower this compact card
            row, so it's left hand-rolled */}
        <Button
          size="icon"
          variant="ghost"
          onClick={() => onDelete(auto.id)}
          style={{
            padding: 4,
            color: "#dc2626"
          }}>
          <Trash2 size={14} />
        </Button>
      </div>
    </Card>
  );
}

function NewAutoModal({ onClose, onCreate }) {
  const [form, setForm] = useState({ type: "deadline_reminder", schedule: "daily", name: "" });
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/sie/automations`, {
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
      title="New Automation"
      size="sm"
      footer={
        <Button onClick={submit} loading={saving} disabled={saving} className="w-full" style={{ background: ACCENT }}>
          {saving ? "Creating…" : "Create Automation"}
        </Button>
      }
    >
      <div style={{ marginBottom: 14 }}>
        <FormSelect
          label="Automation Type"
          value={form.type}
          onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
        >
          {AUTOMATION_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </FormSelect>
      </div>
      <div style={{ marginBottom: 14 }}>
        <Input
          label="Name (optional)"
          type="text"
          value={form.name}
          onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          placeholder="Custom automation name…"
        />
      </div>
      <div>
        <FormSelect
          label="Schedule"
          value={form.schedule}
          onChange={e => setForm(f => ({ ...f, schedule: e.target.value }))}
        >
          {["daily", "weekly", "monthly"].map(s => <option key={s} value={s}>{s}</option>)}
        </FormSelect>
      </div>
    </Modal>
  );
}

export default function AutomationCenter() {
  const [automations, setAutomations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [runResult, setRunResult] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/sie/automations`, { headers: authH() });
      if (r.ok) setAutomations(await r.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleToggle = async (id, enabled) => {
    const r = await fetch(`${API}/api/sie/automations/${id}`, {
      method: "PUT", headers: { ...authH(), "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    if (r.ok) setAutomations(as => as.map(a => a.id === id ? { ...a, enabled } : a));
  };

  const handleRun = async (id) => {
    const r = await fetch(`${API}/api/sie/automations/${id}/run`, { method: "POST", headers: authH() });
    if (r.ok) { setRunResult(await r.json()); load(); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this automation?")) return;
    await fetch(`${API}/api/sie/automations/${id}`, { method: "DELETE", headers: authH() });
    setAutomations(as => as.filter(a => a.id !== id));
  };

  const enabled = automations.filter(a => a.enabled).length;

  return (
    <AIWorkspaceLayout
      title="Automation Center"
      subtitle="Automate repetitive research tasks with AI workflows."
      navItems={SIE_NAV_ITEMS}
    >

      {runResult && (
        <Alert variant="success" title="Automation ran successfully" onDismiss={() => setRunResult(null)} style={{ marginBottom: 16 }}>
          {JSON.stringify(runResult.result)}
        </Alert>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: 40 }}><Spinner size={28} color={ACCENT} /></div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {automations.map(a => (
            <AutomationCard key={a.id} auto={a} onToggle={handleToggle} onRun={handleRun} onDelete={handleDelete} />
          ))}
        </div>
      )}

      {showNew && <NewAutoModal onClose={() => setShowNew(false)} onCreate={a => { setAutomations(as => [a, ...as]); }} />}
    </AIWorkspaceLayout>
  );
}

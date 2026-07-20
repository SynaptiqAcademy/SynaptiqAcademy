import React, { useState, useEffect, useCallback } from "react";
import { BookMarked, Plus, CheckCircle, Clock, X } from "lucide-react";
import { NAVY, WARM, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Tag, Button, Modal, Input, EmptyState, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const STATUS_COLOR = { pending: "#94a3b8", in_progress: "#f59e0b", completed: EMERALD };

function StageRow({ stage, onAdvance }) {
  const color = STATUS_COLOR[stage.status] || "#94a3b8";
  return (
    <Card
      padding="md"
      style={{
        display: "flex", gap: 12, marginBottom: 10,
        background: stage.status === "in_progress" ? `${ACCENT}06` : undefined,
        borderColor: stage.status === "in_progress" ? ACCENT : undefined,
      }}
    >
      {/* Status avatar: no ds/ primitive for a per-status icon circle, left hand-rolled */}
      <div style={{ width: 28, height: 28, borderRadius: "50%", background: `${color}20`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        {stage.status === "completed" ? <CheckCircle size={14} color={EMERALD} /> : <Clock size={14} color={color} />}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: NAVY, marginBottom: 2 }}>{stage.name}</div>
        <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 4 }}>{stage.description}</div>
        <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>
          {stage.start_date} → {stage.end_date} · {stage.estimated_days}d
        </div>
        {stage.tasks?.length > 0 && (
          <div style={{ marginTop: 6, display: "flex", gap: 4, flexWrap: "wrap" }}>
            {stage.tasks.map((t, i) => <Tag key={i} size="sm">{t}</Tag>)}
          </div>
        )}
      </div>
      <div style={{ flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color, textTransform: "uppercase" }}>{stage.status.replace("_", " ")}</span>
        <div style={{ display: "flex", gap: 4 }}>
          {stage.status !== "completed" && (
            <Button onClick={() => onAdvance(stage.key, 100)} size="sm" style={{ background: EMERALD }}>Complete</Button>
          )}
          {stage.status === "pending" && (
            <Button onClick={() => onAdvance(stage.key, 50)} size="sm" style={{ background: ACCENT }}>Start</Button>
          )}
        </div>
      </div>
    </Card>
  );
}

function RoadmapCard({ roadmap, onSelect }) {
  const pct = roadmap.overall_completion || 0;
  return (
    <Card onClick={() => onSelect(roadmap)} padding="md" style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 3 }}>{roadmap.title}</div>
          <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{roadmap.topic}</div>
        </div>
        <span style={{ fontSize: 13, fontWeight: 800, color: ACCENT }}>{pct}%</span>
      </div>
      {/* Progress fill: kept hand-rolled — ds/ProgressBar's fill color is
          fixed navy (or colorByValue's threshold palette), with no way to
          pin it to this roadmap's constant ACCENT tone */}
      <div style={{ height: 4, background: `${NAVY}15`, borderRadius: 2 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: ACCENT, borderRadius: 2, transition: "width 0.3s" }} />
      </div>
      <div style={{ marginTop: 6, fontSize: 11, color: TEXT_SECONDARY }}>
        Current: <strong style={{ color: NAVY }}>{roadmap.current_stage?.replace(/_/g, " ")}</strong> · Est. end: {roadmap.estimated_end_date}
      </div>
    </Card>
  );
}

function GenerateModal({ onClose, onCreate }) {
  const [form, setForm] = useState({ title: "", topic: "", research_questions: [""], target_journal: "" });
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      const payload = { ...form, research_questions: form.research_questions.filter(q => q.trim()) };
      const r = await fetch(`${API}/api/sie/roadmaps/generate`, {
        method: "POST", headers: { ...authH(), "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (r.ok) { onCreate(await r.json()); onClose(); }
    } catch (_) {}
    setSaving(false);
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Generate Research Roadmap"
      footer={
        <Button onClick={submit} loading={saving} disabled={saving || !form.title.trim()} className="w-full">
          {saving ? "Generating 18-stage roadmap…" : "Generate Roadmap"}
        </Button>
      }
    >
      {[
        { label: "Roadmap Title", key: "title", placeholder: "e.g. AI in Medical Diagnosis Paper" },
        { label: "Research Topic", key: "topic", placeholder: "e.g. Deep learning for early cancer detection" },
        { label: "Target Journal (optional)", key: "target_journal", placeholder: "e.g. Nature Medicine" },
      ].map(({ label, key, placeholder }) => (
        <div key={key} style={{ marginBottom: 14 }}>
          <Input
            label={label}
            type="text"
            placeholder={placeholder}
            value={form[key]}
            onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
          />
        </div>
      ))}
      <div>
        <label style={{ fontSize: 12, color: TEXT_SECONDARY, display: "block", marginBottom: 4 }}>Research Questions</label>
        {form.research_questions.map((q, i) => (
          <div key={i} style={{ display: "flex", gap: 6, marginBottom: 6 }}>
            <Input
              type="text"
              placeholder={`Question ${i + 1}…`}
              value={q}
              onChange={e => setForm(f => ({ ...f, research_questions: f.research_questions.map((x, j) => j === i ? e.target.value : x) }))}
              wrapperClassName="flex-1"
            />
            {i === form.research_questions.length - 1 && (
              <Button
                onClick={() => setForm(f => ({ ...f, research_questions: [...f.research_questions, ""] }))}
                style={{ background: ACCENT, fontSize: 18 }}
              >+</Button>
            )}
          </div>
        ))}
      </div>
    </Modal>
  );
}

export default function ResearchPlanning() {
  const [roadmaps, setRoadmaps] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/sie/roadmaps`, { headers: authH() });
      if (r.ok) setRoadmaps(await r.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const loadDetail = async (rm) => {
    const r = await fetch(`${API}/api/sie/roadmaps/${rm.id}`, { headers: authH() });
    if (r.ok) setSelected(await r.json());
  };

  const advance = async (stageKey, completion) => {
    if (!selected) return;
    const r = await fetch(`${API}/api/sie/roadmaps/${selected.id}/stage`, {
      method: "PUT", headers: { ...authH(), "Content-Type": "application/json" },
      body: JSON.stringify({ stage_key: stageKey, completion }),
    });
    if (r.ok) setSelected(await r.json());
  };

  return (
    <AIWorkspaceLayout
      title="Research Roadmaps"
      subtitle={`${roadmaps.length} roadmap${roadmaps.length !== 1 ? "s" : ""} · 18-stage AI-generated plans`}
      navItems={SIE_NAV_ITEMS}
      actions={
        <Button onClick={() => setShowNew(true)} size="sm">
          <Plus size={13} /> Generate Roadmap
        </Button>
      }
    >

      {loading ? <div style={{ textAlign: "center", padding: 40 }}><Spinner size={28} color={ACCENT} /></div> : (
        <div style={{ display: "grid", gridTemplateColumns: selected ? "320px 1fr" : "1fr", gap: 20 }}>
          <div>
            {roadmaps.length === 0 ? (
              <EmptyState
                icon={<BookMarked />}
                title="No roadmaps yet"
                description="Generate your first 18-stage research roadmap."
                action={<Button onClick={() => setShowNew(true)} style={{ background: "#8b5cf6" }}>Generate First Roadmap</Button>}
              />
            ) : roadmaps.map(rm => <RoadmapCard key={rm.id} roadmap={rm} onSelect={loadDetail} />)}
          </div>

          {selected && (
            <Card padding="none" style={{ overflow: "hidden" }}>
              <Card.Header style={{ margin: 0, padding: "14px 20px", background: WARM, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: NAVY }}>{selected.title}</div>
                  <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>Overall: {selected.overall_completion}% complete · Est. end: {selected.estimated_end_date}</div>
                </div>
                <button onClick={() => setSelected(null)} style={{ background: "none", border: "none", cursor: "pointer" }}><X size={16} color={TEXT_SECONDARY} /></button>
              </Card.Header>
              <div style={{ padding: 16, maxHeight: 600, overflowY: "auto" }}>
                {(selected.stages || []).map(s => <StageRow key={s.key} stage={s} onAdvance={advance} />)}
              </div>
            </Card>
          )}
        </div>
      )}

      {showNew && <GenerateModal onClose={() => setShowNew(false)} onCreate={rm => { setRoadmaps(rs => [rm, ...rs]); setSelected(rm); }} />}
    </AIWorkspaceLayout>
  );
}

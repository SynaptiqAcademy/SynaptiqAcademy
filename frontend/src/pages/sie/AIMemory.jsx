import React, { useState, useEffect, useCallback } from "react";
import { Save, RefreshCw, Plus } from "lucide-react";
import { ACCENT } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Tag, TagGroup, Input, FormSelect, Textarea, Button, Spinner, H4, Label } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

function TagEditor({ label, items, onChange }) {
  const [input, setInput] = useState("");
  return (
    <div style={{ marginBottom: 16 }}>
      <Label style={{ display: "block", marginBottom: 6 }}>{label}</Label>
      <TagGroup style={{ marginBottom: 6 }}>
        {items.map((item, i) => (
          <Tag key={i} variant="removable" onRemove={() => onChange(items.filter((_, j) => j !== i))}>
            {item}
          </Tag>
        ))}
      </TagGroup>
      <div style={{ display: "flex", gap: 6 }}>
        <Input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && input.trim()) { onChange([...items, input.trim()]); setInput(""); } }}
          placeholder={`Add ${label.toLowerCase()}…`}
          size="sm"
          wrapperClassName="flex-1"
        />
        <Button
          onClick={() => { if (input.trim()) { onChange([...items, input.trim()]); setInput(""); } }}
          size="sm"
          style={{ background: ACCENT }}
        >
          <Plus size={13} />
        </Button>
      </div>
    </div>
  );
}

export default function AIMemory() {
  const [memory, setMemory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/sie/memory`, { headers: authH() });
      if (r.ok) { const d = await r.json(); setMemory(d); setForm(d); }
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/sie/memory`, {
        method: "PUT", headers: { ...authH(), "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (r.ok) { setMemory(await r.json()); setSaved(true); setTimeout(() => setSaved(false), 2000); }
    } catch (_) {}
    setSaving(false);
  };

  const enrich = async () => {
    setEnriching(true);
    await fetch(`${API}/api/sie/memory/enrich`, { method: "POST", headers: authH() });
    setTimeout(() => { load(); setEnriching(false); }, 2000);
  };

  if (loading) return (
    <AIWorkspaceLayout title="AI Memory" navItems={SIE_NAV_ITEMS}>
      <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Spinner size={32} color={ACCENT} />
      </div>
    </AIWorkspaceLayout>
  );

  const actions = (
    <div style={{ display: "flex", gap: 8 }}>
      <Button onClick={enrich} loading={enriching} disabled={enriching} variant="ghost" size="sm">
        {!enriching && <RefreshCw size={13} />}
        Auto-enrich
      </Button>
      <Button onClick={save} loading={saving} disabled={saving} variant="primary" size="sm">
        {!saving && <Save size={13} />}
        {saved ? "Saved!" : "Save"}
      </Button>
    </div>
  );

  return (
    <AIWorkspaceLayout
      title="AI Memory"
      subtitle={`The AI learns from this profile to personalise all recommendations and plans. Last updated: ${memory?.last_updated?.slice(0, 10) || "never"}`}
      navItems={SIE_NAV_ITEMS}
      actions={actions}
    >

      <div style={{ maxWidth: 800, margin: "0 auto" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <Card padding="lg">
          <H4 style={{ marginBottom: 16 }}>Research Identity</H4>
          <TagEditor label="Research Interests" items={form.research_interests || []} onChange={v => setForm(f => ({ ...f, research_interests: v }))} />
          <TagEditor label="Preferred Methodologies" items={form.methodologies || []} onChange={v => setForm(f => ({ ...f, methodologies: v }))} />
          <TagEditor label="Statistical Methods" items={form.stats_methods || []} onChange={v => setForm(f => ({ ...f, stats_methods: v }))} />
          <FormSelect
            label="Writing Style"
            value={form.writing_style || "academic"}
            onChange={e => setForm(f => ({ ...f, writing_style: e.target.value }))}
          >
            {["academic", "technical", "interdisciplinary", "narrative", "data-driven"].map(s => <option key={s} value={s}>{s}</option>)}
          </FormSelect>
        </Card>

        <Card padding="lg">
          <H4 style={{ marginBottom: 16 }}>Publication & Funding</H4>
          <TagEditor label="Preferred Journals" items={form.preferred_journals || []} onChange={v => setForm(f => ({ ...f, preferred_journals: v }))} />
          <TagEditor label="Preferred Conferences" items={form.preferred_conferences || []} onChange={v => setForm(f => ({ ...f, preferred_conferences: v }))} />
          <TagEditor label="Grant Agencies" items={form.grant_agencies || []} onChange={v => setForm(f => ({ ...f, grant_agencies: v }))} />
        </Card>

        <Card padding="lg">
          <H4 style={{ marginBottom: 16 }}>Career & Teaching</H4>
          <TagEditor label="Career Goals" items={form.career_goals || []} onChange={v => setForm(f => ({ ...f, career_goals: v }))} />
          <TagEditor label="Teaching Interests" items={form.teaching_interests || []} onChange={v => setForm(f => ({ ...f, teaching_interests: v }))} />
          <TagEditor label="Target Positions" items={form.target_positions || []} onChange={v => setForm(f => ({ ...f, target_positions: v }))} />
        </Card>

        <Card padding="lg">
          <H4 style={{ marginBottom: 16 }}>AI Preferences & Notes</H4>
          <div style={{ marginBottom: 14 }}>
            <FormSelect
              label="AI Response Verbosity"
              value={form.ai_preferences?.verbosity || "medium"}
              onChange={e => setForm(f => ({ ...f, ai_preferences: { ...f.ai_preferences, verbosity: e.target.value } }))}
            >
              {["concise", "medium", "detailed"].map(s => <option key={s} value={s}>{s}</option>)}
            </FormSelect>
          </div>
          <Textarea
            label="Personal Notes"
            value={form.notes || ""}
            onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
            rows={5}
            placeholder="Any notes for the AI to remember…"
          />
        </Card>
      </div>
      </div>
    </AIWorkspaceLayout>
  );
}

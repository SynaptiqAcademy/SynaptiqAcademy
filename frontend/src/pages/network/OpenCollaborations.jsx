import React, { useState, useEffect } from "react";
import axios from "axios";
import { Plus, Search, Clock } from "lucide-react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import {
  Card, Badge, Tag, Button, Input, Textarea, FormSelect, FormRow, Checkbox, Modal,
  NavTabs, EmptyState, LoadingOverlay, InlineError,
} from "@/components/ds";

const TYPE_COLOR = {
  co_author: ACCENT, statistician: "#8b5cf6", ai_specialist: "#06b6d4",
  data_analyst: "#f97316", reviewer: EMERALD, translator: "#ec4899",
  supervisor: NAVY, institution_partner: "#0ea5e9", grant_partner: "#dc2626",
  educator: "#7c3aed", research_assistant: "#059669", industry_expert: "#92400e",
};

const TYPES = [
  "co_author","statistician","ai_specialist","data_analyst","reviewer",
  "translator","supervisor","institution_partner","grant_partner","educator",
  "research_assistant","industry_expert","software_engineer","field_researcher","clinical_specialist",
];

function CollabCard({ c, onApply }) {
  const color = TYPE_COLOR[c.type] || NAVY;
  return (
    <Card padding="md">
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: NAVY, marginBottom: 4 }}>{c.title}</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
            <Badge color={color} size="sm">{c.type?.replace(/_/g, " ")}</Badge>
            {c.discipline && <Badge variant="neutral" size="sm">{c.discipline}</Badge>}
            {c.remote && <Badge variant="success" size="sm">Remote OK</Badge>}
          </div>
          {c.description && <div style={{ fontSize: 12, color: TEXT_SECONDARY, lineHeight: 1.5 }}>{c.description.slice(0, 120)}{c.description.length > 120 ? "…" : ""}</div>}
          <div style={{ display: "flex", gap: 14, marginTop: 10, fontSize: 12, color: TEXT_SECONDARY }}>
            {c.owner_name && <span>{c.owner_name}{c.owner_institution ? `, ${c.owner_institution}` : ""}</span>}
            {c.deadline && <span style={{ display: "flex", alignItems: "center", gap: 4 }}><Clock size={11} />Deadline: {c.deadline.slice(0, 10)}</span>}
            <span>{c.applicant_count || 0} applicants</span>
          </div>
        </div>
        <Button variant="primary" size="sm" onClick={() => onApply(c)} style={{ flexShrink: 0 }}>
          Apply
        </Button>
      </div>
    </Card>
  );
}

function ApplyModal({ collab, onClose, onSuccess }) {
  const [form, setForm] = useState({ message: "", cv_summary: "", skills: [] });
  const [skillInput, setSkillInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const addSkill = () => { if (skillInput.trim()) { setForm(f => ({ ...f, skills: [...f.skills, skillInput.trim()] })); setSkillInput(""); } };
  const removeSkill = s => setForm(f => ({ ...f, skills: f.skills.filter(x => x !== s) }));

  const handleSubmit = async () => {
    setSaving(true); setError("");
    try {
      const r = await axios.post(`/api/network/collaborations/${collab.id}/apply`, form);
      if (r.data.error) { setError(r.data.error); setSaving(false); return; }
      onSuccess();
      onClose();
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to apply");
      setSaving(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={`Apply: ${collab.title}`}
      size="md"
      footer={
        <Button variant="primary" onClick={handleSubmit} disabled={saving} loading={saving} style={{ width: "100%" }}>
          {saving ? "Sending…" : "Send Application"}
        </Button>
      }
    >
      {error && <InlineError style={{ marginBottom: 12 }}>{error}</InlineError>}
      <Textarea
        label="Cover Message"
        value={form.message}
        onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
        rows={4}
        placeholder="Introduce yourself and explain your interest…"
      />
      <Textarea
        label="CV Summary"
        value={form.cv_summary}
        onChange={e => setForm(f => ({ ...f, cv_summary: e.target.value }))}
        rows={3}
        placeholder="Brief CV summary highlighting relevant experience…"
      />
      <div>
        <label style={{ fontSize: 12, fontWeight: 600, color: NAVY, display: "block", marginBottom: 4 }}>Key Skills</label>
        <div style={{ display: "flex", gap: 6, marginBottom: 6 }}>
          <Input
            value={skillInput}
            onChange={e => setSkillInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addSkill(); } }}
            placeholder="Add skill…"
            wrapperClassName="flex-1"
          />
          <Button variant="subtle" onClick={addSkill}>Add</Button>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {form.skills.map(s => (
            <Tag key={s} variant="removable" color={ACCENT} onRemove={() => removeSkill(s)}>
              {s}
            </Tag>
          ))}
        </div>
      </div>
    </Modal>
  );
}

function CreateCollabModal({ onClose, onCreate }) {
  const [form, setForm] = useState({ title: "", description: "", type: "co_author", discipline: "", remote: true, deadline: "", slots: 1, compensation: "unpaid" });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      await axios.post("/api/network/collaborations", form);
      onCreate(); onClose();
    } catch { setSaving(false); }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Post Collaboration"
      size="md"
      footer={
        <Button variant="primary" onClick={handleSubmit} disabled={saving} loading={saving} style={{ width: "100%" }}>
          {saving ? "Posting…" : "Post Opportunity"}
        </Button>
      }
    >
      <Input
        label="Title *"
        value={form.title}
        onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
      />
      <Input
        label="Discipline"
        value={form.discipline}
        onChange={e => setForm(f => ({ ...f, discipline: e.target.value }))}
      />
      <Textarea
        label="Description"
        value={form.description}
        onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
        rows={3}
      />
      <FormRow cols={2}>
        <FormSelect
          label="Type"
          value={form.type}
          onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
        >
          {TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </FormSelect>
        <Input
          label="Deadline"
          type="date"
          value={form.deadline}
          onChange={e => setForm(f => ({ ...f, deadline: e.target.value }))}
        />
      </FormRow>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <Checkbox
          label="Remote OK"
          checked={form.remote}
          onChange={e => setForm(f => ({ ...f, remote: e.target.checked }))}
        />
        <FormSelect
          value={form.compensation}
          onChange={e => setForm(f => ({ ...f, compensation: e.target.value }))}
        >
          <option value="unpaid">Unpaid</option>
          <option value="co-authorship">Co-authorship</option>
          <option value="grant_funded">Grant Funded</option>
          <option value="paid">Paid</option>
        </FormSelect>
      </div>
    </Modal>
  );
}

export default function OpenCollaborations() {
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [applyCollab, setApplyCollab] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [tab, setTab] = useState("discover");
  const [mine, setMine] = useState({ owned: [], applied: [] });

  const fetchCollabs = async () => {
    setLoading(true);
    try {
      const params = { limit: 30 };
      if (q) params.q = q;
      if (typeFilter) params.type = typeFilter;
      const r = await axios.get("/api/network/collaborations", { params });
      setResults(r.data.results || []);
      setTotal(r.data.total || 0);
    } catch { } finally { setLoading(false); }
  };

  const fetchMine = async () => {
    try {
      const r = await axios.get("/api/network/collaborations/mine");
      setMine(r.data || { owned: [], applied: [] });
    } catch { }
  };

  useEffect(() => { fetchCollabs(); fetchMine(); }, []);

  return (
    <DiscoveryLayout
      title="Open Collaborations"
      actions={<Button variant="primary" onClick={() => setShowCreate(true)}><Plus size={15} />Post</Button>}
    >

      <div style={{ marginBottom: 16 }}>
        <NavTabs
          variant="pill"
          tabs={[
            { id: "discover", label: "Discover" },
            { id: "mine", label: "My Collaborations" },
          ]}
          active={tab}
          onChange={setTab}
        />
      </div>

      {tab === "discover" && (
        <>
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
            <Input
              value={q}
              onChange={e => setQ(e.target.value)}
              onKeyDown={e => e.key === "Enter" && fetchCollabs()}
              placeholder="Search collaborations…"
              prefix={<Search size={14} />}
              style={{ minWidth: 200 }}
              wrapperClassName="flex-1"
            />
            <FormSelect value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
              <option value="">All types</option>
              {TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </FormSelect>
            <Button variant="primary" onClick={fetchCollabs}>Search</Button>
          </div>
          {loading ? <LoadingOverlay text="Loading…" /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {results.length === 0 ? (
                <EmptyState title="No open collaborations found." />
              ) : results.map((c, i) => <CollabCard key={c.id || i} c={c} onApply={setApplyCollab} />)}
            </div>
          )}
        </>
      )}

      {tab === "mine" && (
        <div>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 10 }}>Posted by me ({mine.owned.length})</h3>
          {mine.owned.length === 0 ? <div style={{ color: TEXT_SECONDARY, fontSize: 13, marginBottom: 20 }}>You haven't posted any collaborations yet.</div> : mine.owned.map((c, i) => (
            <Card key={i} padding="sm" style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: NAVY }}>{c.title}</div>
              <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{c.type?.replace(/_/g, " ")} · {c.applicant_count || 0} applicants · {c.status}</div>
            </Card>
          ))}
          <h3 style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 10, marginTop: 20 }}>My applications ({mine.applied.length})</h3>
          {mine.applied.length === 0 ? <div style={{ color: TEXT_SECONDARY, fontSize: 13 }}>You haven't applied to any collaborations yet.</div> : mine.applied.map((a, i) => (
            <Card key={i} padding="sm" style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: NAVY }}>Application</div>
              <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>Status: {a.status}</div>
            </Card>
          ))}
        </div>
      )}

      {applyCollab && <ApplyModal collab={applyCollab} onClose={() => setApplyCollab(null)} onSuccess={() => { fetchCollabs(); fetchMine(); }} />}
      {showCreate && <CreateCollabModal onClose={() => setShowCreate(false)} onCreate={() => { fetchCollabs(); fetchMine(); }} />}
    </DiscoveryLayout>
  );
}

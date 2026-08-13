/**
 * ExpertiseRequests — list + create open requests for specific expertise.
 *
 * Filters: kind, research area, free text.
 * Action: open detail page; create new (modal).
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { NAVY } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";
import { ResearchLayout } from "@/layouts";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Tag } from "@/components/ds/Tag";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { NavTabs } from "@/components/ds/NavTabs";
import { Modal } from "@/components/ds/Modal";
import { EmptyState } from "@/components/ds/EmptyState";
import { Plus, Briefcase, Building2 } from "lucide-react";

const KIND_LABEL = {
  co_author: "Co-author",
  statistician: "Statistician",
  methodology: "Methodology expert",
  reviewer: "Reviewer",
  ai_specialist: "AI specialist",
  data_scientist: "Data scientist",
  editor: "Editor",
  sme: "Subject matter expert",
};

const KIND_TONE = {
  co_author:      "border-[#0F2847]/30 bg-[#0F2847]/5 text-[#0F2847]",
  statistician:   "border-emerald-300 bg-emerald-50 text-emerald-800",
  methodology:    "border-purple-300 bg-purple-50 text-purple-800",
  reviewer:       "border-amber-300 bg-amber-50 text-amber-800",
  ai_specialist:  "border-fuchsia-300 bg-fuchsia-50 text-fuchsia-800",
  data_scientist: "border-cyan-300 bg-cyan-50 text-cyan-800",
  editor:         "border-rose-300 bg-rose-50 text-rose-800",
  sme:            "border-slate-300 bg-slate-50 text-slate-800",
};

export default function ExpertiseRequests() {
  const [items, setItems] = useState(null);
  const [facets, setFacets] = useState({});
  const [kind, setKind] = useState("");
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(false);
  const [tab, setTab] = useState("open");  // open | matching | mine

  const load = useCallback(async () => {
    setItems(null);
    try {
      if (tab === "matching") {
        const { data } = await api.get("/expertise/matching");
        setItems(data || []);
      } else if (tab === "mine") {
        const { data } = await api.get("/expertise/mine");
        setItems(data || []);
      } else {
        const params = new URLSearchParams();
        if (kind) params.set("kind", kind);
        if (q) params.set("q", q);
        const { data } = await api.get(`/expertise?${params.toString()}`);
        setItems(data.results || []);
        setFacets(data.facets || {});
      }
    } catch (e) {
      toast.error("Failed to load requests");
      setItems([]);
    }
  }, [kind, q, tab]);
  useEffect(() => { load(); }, [load]);

  return (
    <ResearchLayout
      title="Expertise Requests"
      subtitle="Researchers post specific needs — co-author, statistician, reviewer, AI specialist, methodologist — and you respond."
      actions={
        <Button data-testid="expertise-create-btn" onClick={() => setCreating(true)} variant="hero" size="sm">
          <Plus size={12} strokeWidth={1.5} /> Post request
        </Button>
      }
      nav={
        <NavTabs
          tabs={[
            { id: "open", label: "Open requests" },
            { id: "matching", label: "Matching me" },
            { id: "mine", label: "My requests" },
          ]}
          active={tab}
          onChange={setTab}
        />
      }
    >

      {/* Filter row (only on Open tab) */}
      {tab === "open" && (
        <div className="flex flex-wrap items-center gap-2">
          <FormSelect
            data-testid="expertise-kind-filter"
            size="sm"
            value={kind} onChange={(e) => setKind(e.target.value)}
            wrapperClassName="w-auto"
          >
            <option value="">All kinds</option>
            {Object.entries(KIND_LABEL).map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </FormSelect>
          <Input
            data-testid="expertise-search"
            size="sm"
            value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search title, description, areas, skills…"
            wrapperClassName="flex-1 min-w-[240px]"
          />
          {(facets.by_kind || []).length > 0 && (
            <div className="text-[10px] font-mono text-slate-400">
              {(facets.by_kind || []).slice(0, 5).map((f) => `${f._id}=${f.n}`).join("  ")}
            </div>
          )}
        </div>
      )}

      {/* List */}
      {items === null && <div className="py-4 flex justify-center"><Spinner size={16} /></div>}
      {items && items.length === 0 && (
        <div data-testid="expertise-empty">
          <EmptyState
            title={
              tab === "matching" ? "No requests match your profile yet. Update your expertise tags to surface more." :
              tab === "mine" ? "You haven't posted any requests yet. Click 'Post request' to begin." :
              "No open requests right now."
            }
            size="md"
            dashed={true}
          />
        </div>
      )}
      {items && items.length > 0 && (
        <div className="grid sm:grid-cols-2 gap-4" data-testid="expertise-list">
          {items.map((r) => <RequestCard key={r.id} r={r} />)}
        </div>
      )}

      {creating && <CreateModal onClose={() => setCreating(false)} onCreated={() => { setCreating(false); setTab("mine"); load(); }} />}
    </ResearchLayout>
  );
}

function RequestCard({ r }) {
  return (
    <Card to={`/expertise/${r.id}`} padding="md" className="group" data-testid={`expertise-card-${r.id}`}>
      <div className="flex items-start justify-between gap-2">
        <Badge variant="outline" size="sm" className={KIND_TONE[r.kind] || KIND_TONE.sme}>{KIND_LABEL[r.kind] || r.kind}</Badge>
        <Badge variant={r.status === "open" ? "success" : r.status === "filled" ? "default" : "neutral"} size="sm">
          {r.status}
        </Badge>
      </div>
      <h3 className="font-serif text-lg text-slate-900 mt-2 group-hover:text-[#0F2847]">{r.title}</h3>
      <p className="text-xs text-slate-600 mt-1 line-clamp-2">{r.description}</p>
      {(r.required_skills || []).length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {(r.required_skills || []).slice(0, 5).map((s, i) => (
            <Tag key={i} size="sm">{s}</Tag>
          ))}
        </div>
      )}
      <div className="flex items-center gap-3 mt-3 text-[10px] font-mono text-slate-500">
        {r.owner && (
          <span className="inline-flex items-center gap-1">
            <Briefcase size={9} strokeWidth={1.5} /> {r.owner.full_name}
          </span>
        )}
        {r.owner?.institution && (
          <span className="inline-flex items-center gap-1">
            <Building2 size={9} strokeWidth={1.5} /> {r.owner.institution}
          </span>
        )}
        {(r.applicants || []).length > 0 && (
          <span className="ml-auto">{(r.applicants || []).length} applicant{(r.applicants || []).length === 1 ? "" : "s"}</span>
        )}
      </div>
    </Card>
  );
}

function CreateModal({ onClose, onCreated }) {
  const [kind, setKind] = useState("co_author");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [skillsRaw, setSkillsRaw] = useState("");
  const [areasRaw, setAreasRaw] = useState("");
  const [entityKind, setEntityKind] = useState("");
  const [entityId, setEntityId] = useState("");
  const [duration, setDuration] = useState("");
  const [compensation, setCompensation] = useState("authorship");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (title.trim().length < 4 || description.trim().length < 10) {
      toast.error("Title (≥4 chars) and description (≥10 chars) required");
      return;
    }
    setBusy(true);
    try {
      const payload = {
        kind, title: title.trim(), description: description.trim(),
        required_skills: skillsRaw.split(",").map((s) => s.trim()).filter(Boolean),
        research_areas:  areasRaw.split(",").map((s) => s.trim()).filter(Boolean),
        duration: duration || null, compensation: compensation || null,
      };
      if (entityKind && entityId) {
        payload.entity_kind = entityKind;
        payload.entity_id = entityId;
      }
      await api.post("/expertise", payload);
      toast.success("Request posted");
      onCreated?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to create");
    } finally { setBusy(false); }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Post an expertise request"
      description="Marketplace"
      size="md"
      data-testid="expertise-create-modal"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button data-testid="create-submit" disabled={busy} loading={busy} onClick={submit}>
            Post request
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <FormSelect label="Kind of expertise needed" data-testid="create-kind" value={kind} onChange={(e) => setKind(e.target.value)}>
          {Object.entries(KIND_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </FormSelect>
        <Input label="Title" data-testid="create-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Need PLS-SEM expert for HR study" />
        <Textarea label="Description" data-testid="create-description" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Project context, scope, sample size, timeline." />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input label="Required skills (comma-sep)" data-testid="create-skills" value={skillsRaw} onChange={(e) => setSkillsRaw(e.target.value)} placeholder="pls-sem, sem, statistics" />
          <Input label="Research areas" data-testid="create-areas" value={areasRaw} onChange={(e) => setAreasRaw(e.target.value)} placeholder="management, hrm" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input label="Duration" data-testid="create-duration" value={duration} onChange={(e) => setDuration(e.target.value)} placeholder="e.g. 3 months" />
          <FormSelect label="Compensation" data-testid="create-compensation" value={compensation} onChange={(e) => setCompensation(e.target.value)}>
            <option value="authorship">Authorship</option>
            <option value="paid">Paid engagement</option>
            <option value="credit">Acknowledgment / credit</option>
            <option value="grant_split">Grant split</option>
          </FormSelect>
        </div>
        <div>
          <div className="overline mb-1">Link to (optional)</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <FormSelect data-testid="create-entity-kind" value={entityKind} onChange={(e) => setEntityKind(e.target.value)}>
              <option value="">No link</option>
              <option value="workspace">Workspace</option>
              <option value="project">Project</option>
              <option value="manuscript">Manuscript</option>
            </FormSelect>
            <Input data-testid="create-entity-id" value={entityId} onChange={(e) => setEntityId(e.target.value)} placeholder="ID" className="font-mono" disabled={!entityKind} />
          </div>
          <div className="text-[10px] text-slate-400 mt-1">Linking helps applicants understand context. You must own/be a member.</div>
        </div>
      </div>
    </Modal>
  );
}

/**
 * ExpertiseRequests — list + create open requests for specific expertise.
 *
 * Filters: kind, research area, free text.
 * Action: open detail page; create new (modal).
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { NAVY } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";
import { DiscoveryLayout } from "@/layouts";
import {
  Compass, Plus, X, Loader2, Filter, ArrowRight, Briefcase, MapPin,
  Building2, ChevronDown,
} from "lucide-react";

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

  const load = async () => {
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
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [kind, q, tab]);

  return (
    <DiscoveryLayout
      title="Expertise Requests"
      subtitle="Researchers post specific needs — co-author, statistician, reviewer, AI specialist, methodologist — and you respond."
      actions={
        <button
          data-testid="expertise-create-btn"
          onClick={() => setCreating(true)}
          className="inline-flex items-center gap-2 bg-[#0F2847] text-white text-sm px-4 py-2 hover:bg-slate-800"
        >
          <Plus size={12} strokeWidth={1.5} /> Post request
        </button>
      }
    >

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-200" data-testid="expertise-tabs">
        {[
          { v: "open", label: "Open requests" },
          { v: "matching", label: "Matching me" },
          { v: "mine", label: "My requests" },
        ].map((t) => (
          <button
            key={t.v}
            data-testid={`expertise-tab-${t.v}`}
            onClick={() => setTab(t.v)}
            className={`px-4 py-2 text-sm -mb-px border-b-2 transition-colors ${tab === t.v ? "border-[#0F2847] text-[#0F2847]" : "border-transparent text-slate-500 hover:text-slate-900"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Filter row (only on Open tab) */}
      {tab === "open" && (
        <div className="flex flex-wrap items-center gap-2">
          <select
            data-testid="expertise-kind-filter"
            value={kind} onChange={(e) => setKind(e.target.value)}
            className="text-xs px-3 py-2 border border-slate-300"
          >
            <option value="">All kinds</option>
            {Object.entries(KIND_LABEL).map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
          <input
            data-testid="expertise-search"
            value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search title, description, areas, skills…"
            className="flex-1 min-w-[240px] px-3 py-2 border border-slate-300 text-sm"
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
        <div className="text-center py-16 border border-dashed border-slate-300 text-sm text-slate-500" data-testid="expertise-empty">
          {tab === "matching" ? "No requests match your profile yet. Update your expertise tags to surface more." :
           tab === "mine" ? "You haven't posted any requests yet. Click 'Post request' to begin." :
           "No open requests right now."}
        </div>
      )}
      {items && items.length > 0 && (
        <div className="grid sm:grid-cols-2 gap-4" data-testid="expertise-list">
          {items.map((r) => <RequestCard key={r.id} r={r} />)}
        </div>
      )}

      {creating && <CreateModal onClose={() => setCreating(false)} onCreated={() => { setCreating(false); setTab("mine"); load(); }} />}
    </DiscoveryLayout>
  );
}

function RequestCard({ r }) {
  return (
    <Link to={`/expertise/${r.id}`} className="block border border-slate-200 bg-white p-4 hover:border-[#0F2847] group transition-colors" data-testid={`expertise-card-${r.id}`}>
      <div className="flex items-start justify-between gap-2">
        <span className={`overline border px-1.5 py-0.5 ${KIND_TONE[r.kind] || KIND_TONE.sme}`}>{KIND_LABEL[r.kind] || r.kind}</span>
        <span className={`overline px-1.5 py-0.5 ${r.status === "open" ? "border-emerald-300 bg-emerald-50 text-emerald-800" : r.status === "filled" ? "border-[#0F2847]/30 bg-[#0F2847]/5 text-[#0F2847]" : "border-slate-200 bg-slate-50 text-slate-500"}`}>
          {r.status}
        </span>
      </div>
      <h3 className="font-serif text-lg text-slate-900 mt-2 group-hover:text-[#0F2847]">{r.title}</h3>
      <p className="text-xs text-slate-600 mt-1 line-clamp-2">{r.description}</p>
      {(r.required_skills || []).length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {(r.required_skills || []).slice(0, 5).map((s, i) => (
            <span key={i} className="text-[10px] font-mono border border-slate-200 bg-slate-50 px-1.5 py-0.5">{s}</span>
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
    </Link>
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
    <div className="fixed inset-0 z-[100] bg-slate-900/50 flex items-center justify-center px-4 overflow-y-auto py-10" onClick={onClose} data-testid="expertise-create-modal">
      <div className="bg-white w-full max-w-xl border border-slate-200" onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <div>
            <div className="overline">Marketplace</div>
            <h3 className="font-serif text-xl text-slate-900">Post an expertise request</h3>
          </div>
          <button onClick={onClose}><X size={16} strokeWidth={1.5} className="text-slate-400 hover:text-slate-900" /></button>
        </div>
        <div className="p-5 space-y-3">
          <div>
            <div className="overline mb-1">Kind of expertise needed</div>
            <select data-testid="create-kind" value={kind} onChange={(e) => setKind(e.target.value)} className="w-full px-3 py-2 border border-slate-300 text-sm">
              {Object.entries(KIND_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div>
            <div className="overline mb-1">Title</div>
            <input data-testid="create-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Need PLS-SEM expert for HR study" className="w-full px-3 py-2 border border-slate-300 text-sm" />
          </div>
          <div>
            <div className="overline mb-1">Description</div>
            <textarea data-testid="create-description" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Project context, scope, sample size, timeline." className="w-full px-3 py-2 border border-slate-300 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="overline mb-1">Required skills (comma-sep)</div>
              <input data-testid="create-skills" value={skillsRaw} onChange={(e) => setSkillsRaw(e.target.value)} placeholder="pls-sem, sem, statistics" className="w-full px-3 py-2 border border-slate-300 text-sm" />
            </div>
            <div>
              <div className="overline mb-1">Research areas</div>
              <input data-testid="create-areas" value={areasRaw} onChange={(e) => setAreasRaw(e.target.value)} placeholder="management, hrm" className="w-full px-3 py-2 border border-slate-300 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="overline mb-1">Duration</div>
              <input data-testid="create-duration" value={duration} onChange={(e) => setDuration(e.target.value)} placeholder="e.g. 3 months" className="w-full px-3 py-2 border border-slate-300 text-sm" />
            </div>
            <div>
              <div className="overline mb-1">Compensation</div>
              <select data-testid="create-compensation" value={compensation} onChange={(e) => setCompensation(e.target.value)} className="w-full px-3 py-2 border border-slate-300 text-sm">
                <option value="authorship">Authorship</option>
                <option value="paid">Paid engagement</option>
                <option value="credit">Acknowledgment / credit</option>
                <option value="grant_split">Grant split</option>
              </select>
            </div>
          </div>
          <div>
            <div className="overline mb-1">Link to (optional)</div>
            <div className="grid grid-cols-2 gap-2">
              <select data-testid="create-entity-kind" value={entityKind} onChange={(e) => setEntityKind(e.target.value)} className="px-3 py-2 border border-slate-300 text-sm">
                <option value="">No link</option>
                <option value="workspace">Workspace</option>
                <option value="project">Project</option>
                <option value="manuscript">Manuscript</option>
              </select>
              <input data-testid="create-entity-id" value={entityId} onChange={(e) => setEntityId(e.target.value)} placeholder="ID" className="px-3 py-2 border border-slate-300 text-sm font-mono" disabled={!entityKind} />
            </div>
            <div className="text-[10px] text-slate-400 mt-1">Linking helps applicants understand context. You must own/be a member.</div>
          </div>
        </div>
        <div className="border-t border-slate-200 px-5 py-3 flex items-center justify-end gap-2">
          <button onClick={onClose} className="text-xs text-slate-600 px-3 py-2">Cancel</button>
          <button data-testid="create-submit" disabled={busy} onClick={submit} className="text-xs bg-[#0F2847] text-white px-4 py-2 hover:bg-slate-800 disabled:opacity-50 inline-flex items-center gap-1.5">
            {busy && <Loader2 size={11} className="animate-spin" />} Post request
          </button>
        </div>
      </div>
    </div>
  );
}

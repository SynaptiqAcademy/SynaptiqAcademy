import React, { useCallback, useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { Avatar } from "../components/ds/Avatar";
import { toast } from "sonner";
import { Plus, Check, MessageSquare, Award, AlertTriangle, Users, Search } from "lucide-react";
import { userTypeLabel } from "../lib/userTypes";
import AssistantLauncher from "../components/ai/AssistantLauncher";
import FilePanel from "../components/files/FilePanel";
import { SkeletonCard } from "../components/ds/LoadingState";
import { EmptyState } from "../components/ds/EmptyState";
import { Button } from "../components/ds/Button";
import { NavTabs } from "../components/ds/NavTabs";
import { Input } from "../components/ds/Input";
import { Textarea } from "../components/ds/Textarea";
import { FormSelect } from "../components/ds/FormSelect";
import { Card } from "../components/ds/Card";
import { Badge } from "../components/ds/Badge";
import { Checkbox } from "../components/ds/Form";
import { ResearchLayout } from "@/layouts";
import { NAVY } from "@/lib/tokens";

const TABS = [
  { key: "foundation", label: "Research Foundation" },
  { key: "design",     label: "Research Design"     },
  { key: "literature", label: "Literature"           },
  { key: "tasks",      label: "Tasks & Milestones"  },
  { key: "team",       label: "Team"                },
];


export default function ProjectDetail() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [tab, setTab] = useState("foundation");
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    const { data } = await api.get(`/projects/${id}`);
    setProject(data);
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const save = async (patch) => {
    setSaving(true);
    try {
      const { data } = await api.patch(`/projects/${id}`, patch);
      setProject({ ...project, ...data });
      toast.success("Saved");
    } catch { toast.error("Failed"); }
    finally { setSaving(false); }
  };

  if (!project) return <div className="p-6"><SkeletonCard rows={4} /></div>;

  return (
    <ResearchLayout>
    <div className="space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2 mb-1.5">
                <Badge variant="outline" className="capitalize">{project.visibility} project</Badge>
              </div>
              <h1 className="text-[1.4rem] font-semibold text-slate-900 tracking-tight leading-snug">
                {project.title}
              </h1>
              {project.description && (
                <p className="text-[13px] text-slate-500 mt-2 max-w-2xl leading-relaxed">{project.description}</p>
              )}
            </div>
            <div className="flex flex-col items-end gap-2 shrink-0">
              <Button
                data-testid={TID.openChatBtn}
                onClick={() => navigate("/messages", { state: { openContext: { type: "project", id } } })}
                variant="ghost"
              >
                <MessageSquare size={12} strokeWidth={1.5} /> Project chat
              </Button>
              <AssistantLauncher entityKind="project" entityId={id} entityTitle={project.title} />
            </div>
          </div>
          {(project.members_info || []).length > 0 && (
            <div className="flex items-center gap-3 mt-4">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Team</span>
              <div className="flex -space-x-2">
                {(project.members_info || []).map((m) => (
                  <Link to={`/profile/${m.id}`} key={m.id} title={m.full_name} className="ring-2 ring-white">
                    <Avatar url={m.avatar_url} name={m.full_name} size={28} />
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </header>

      <NavTabs
        tabs={TABS.map((t) => ({ id: t.key, label: t.label }))}
        active={tab}
        onChange={setTab}
      />

      {tab === "foundation" && <Foundation project={project} onSave={save} saving={saving} />}
      {tab === "design"     && <Design project={project} onSave={save} saving={saving} />}
      {tab === "literature" && <Literature projectId={id} />}
      {tab === "tasks"      && <Tasks projectId={id} members={project.members_info || []} />}
      {tab === "team"       && <Team members={project.members_info || []} projectId={id} />}

      <div className="mt-6">
        <FilePanel entityKind="project" entityId={id} />
      </div>
    </div>
    </ResearchLayout>
  );
}

// ─── Foundation ───────────────────────────────────────────────────────────────

function Foundation({ project, onSave, saving }) {
  const [f, setF] = useState({
    problem_statement:       project.problem_statement || "",
    research_gap:            project.research_gap || "",
    objectives:              (project.objectives || []).join("\n"),
    research_questions:      (project.research_questions || []).join("\n"),
    hypotheses:              (project.hypotheses || []).join("\n"),
    expected_contributions:  project.expected_contributions || "",
  });
  const save = () => onSave({
    problem_statement:      f.problem_statement,
    research_gap:           f.research_gap,
    objectives:             f.objectives.split("\n").filter(Boolean),
    research_questions:     f.research_questions.split("\n").filter(Boolean),
    hypotheses:             f.hypotheses.split("\n").filter(Boolean),
    expected_contributions: f.expected_contributions,
  });
  return (
    <div className="space-y-5 max-w-3xl">
      <TextBlock label="Problem statement"           value={f.problem_statement}      onChange={(v) => setF({ ...f, problem_statement: v })} />
      <TextBlock label="Research gap"                value={f.research_gap}           onChange={(v) => setF({ ...f, research_gap: v })} />
      <TextBlock label="Objectives (one per line)"   value={f.objectives}             onChange={(v) => setF({ ...f, objectives: v })} rows={4} />
      <TextBlock label="Research questions"          value={f.research_questions}     onChange={(v) => setF({ ...f, research_questions: v })} rows={4} />
      <TextBlock label="Hypotheses (one per line)"   value={f.hypotheses}             onChange={(v) => setF({ ...f, hypotheses: v })} rows={4} />
      <TextBlock label="Expected contributions"      value={f.expected_contributions} onChange={(v) => setF({ ...f, expected_contributions: v })} />
      <Button onClick={save} disabled={saving} loading={saving}>
        Save research foundation
      </Button>
    </div>
  );
}

// ─── Design ───────────────────────────────────────────────────────────────────

function Design({ project, onSave, saving }) {
  const [f, setF] = useState({
    methodology:      project.methodology || "",
    data_sources:     project.data_sources || "",
    sampling:         project.sampling || "",
    analysis_methods: project.analysis_methods || "",
    ethics:           project.ethics || "",
  });
  return (
    <div className="space-y-5 max-w-3xl">
      <SelectBlock
        label="Methodology"
        value={f.methodology}
        options={["", "Quantitative", "Qualitative", "Mixed Methods"]}
        onChange={(v) => setF({ ...f, methodology: v })}
      />
      <TextBlock label="Data sources"       value={f.data_sources}     onChange={(v) => setF({ ...f, data_sources: v })} />
      <TextBlock label="Sampling strategy"  value={f.sampling}         onChange={(v) => setF({ ...f, sampling: v })} />
      <TextBlock label="Analysis methods"   value={f.analysis_methods} onChange={(v) => setF({ ...f, analysis_methods: v })} />
      <TextBlock label="Ethical considerations" value={f.ethics}       onChange={(v) => setF({ ...f, ethics: v })} />
      <button onClick={() => onSave(f)} disabled={saving} className="inline-flex items-center gap-2 bg-[#0F2847] text-white px-4 h-9 text-xs font-medium hover:bg-[#1a3d65] disabled:opacity-40 transition-colors">
        {saving ? "Saving…" : "Save research design"}
      </button>
    </div>
  );
}

// ─── Literature ───────────────────────────────────────────────────────────────

function Literature({ projectId }) {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ title: "", authors: "", year: "", source_type: "Paper", notes: "", url: "" });
  const [adding, setAdding] = useState(false);
  const load = useCallback(async () => { const r = await api.get(`/projects/${projectId}/literature`); setItems(r.data); }, [projectId]);
  useEffect(() => { load(); }, [load]);
  const add = async () => {
    if (!form.title.trim()) return;
    setAdding(true);
    try {
      await api.post(`/projects/${projectId}/literature`, { ...form, year: form.year ? parseInt(form.year) : null });
      setForm({ title: "", authors: "", year: "", source_type: "Paper", notes: "", url: "" });
      load();
    } catch { toast.error("Failed"); }
    finally { setAdding(false); }
  };
  return (
    <div className="grid lg:grid-cols-12 gap-6">
      <div className="lg:col-span-7 space-y-2">
        {items.length === 0 && (
          <EmptyState title="No literature added yet." size="sm" dashed={true} />
        )}
        {items.map((l) => (
          <div key={l.id} className="border border-slate-200 bg-white p-4 hover:border-[#0F2847]/40 transition-colors">
            <div className="text-[11px] font-mono text-[#0F2847] mb-1.5">
              {l.source_type}{l.year ? ` · ${l.year}` : ""}
            </div>
            <div className="text-[13px] font-semibold text-slate-900 leading-snug">{l.title}</div>
            {l.authors && <div className="text-[11px] text-slate-500 mt-1">{l.authors}</div>}
            {l.notes && <div className="text-[13px] text-slate-700 mt-2 leading-relaxed">{l.notes}</div>}
            {l.url && (
              <a href={l.url} target="_blank" rel="noreferrer" className="text-[11px] text-[#0F2847] hover:underline mt-2 inline-block">
                View source ↗
              </a>
            )}
          </div>
        ))}
      </div>
      <div className="lg:col-span-5 border border-slate-200 bg-white p-5 h-fit">
        <div className="overline text-slate-500 mb-3">Add source</div>
        <div className="space-y-2">
          <input className="h-9 w-full px-3 border border-slate-200 bg-white text-[13px] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors" placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input className="h-9 w-full px-3 border border-slate-200 bg-white text-[13px] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors" placeholder="Authors" value={form.authors} onChange={(e) => setForm({ ...form, authors: e.target.value })} />
          <div className="grid grid-cols-2 gap-2">
            <input className="h-9 px-3 border border-slate-200 bg-white text-[13px] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors" placeholder="Year" value={form.year} onChange={(e) => setForm({ ...form, year: e.target.value })} />
            <select className="h-9 px-3 border border-slate-200 bg-white text-[13px] focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors" value={form.source_type} onChange={(e) => setForm({ ...form, source_type: e.target.value })}>
              <option>Paper</option><option>Book</option><option>Report</option>
            </select>
          </div>
          <input className="h-9 w-full px-3 border border-slate-200 bg-white text-[13px] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors" placeholder="URL (optional)" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
          <textarea rows={3} className="w-full px-3 py-2.5 border border-slate-200 bg-white text-[13px] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] resize-y transition-colors" placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          <button onClick={add} disabled={adding || !form.title.trim()} className="inline-flex items-center gap-2 bg-[#0F2847] text-white px-4 h-9 text-xs font-medium hover:bg-[#1a3d65] disabled:opacity-40 transition-colors">
            <Plus size={12} strokeWidth={1.5} /> Add to literature
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Tasks ────────────────────────────────────────────────────────────────────

function Tasks({ projectId, members }) {
  const [tasks, setTasks] = useState([]);
  const [milestones, setMilestones] = useState([]);
  const [tForm, setTForm] = useState({ title: "", assignee_id: "", due_date: "", priority: "medium" });
  const [mForm, setMForm] = useState({ title: "", due_date: "", description: "" });
  const load = useCallback(async () => {
    const [t, m] = await Promise.all([api.get(`/projects/${projectId}/tasks`), api.get(`/projects/${projectId}/milestones`)]);
    setTasks(t.data); setMilestones(m.data);
  }, [projectId]);
  useEffect(() => { load(); }, [load]);

  const addTask = async () => {
    if (!tForm.title.trim()) return;
    await api.post(`/projects/${projectId}/tasks`, tForm);
    setTForm({ title: "", assignee_id: "", due_date: "", priority: "medium" });
    load();
  };
  const toggleStatus = async (t) => {
    const next = t.status === "done" ? "todo" : "done";
    await api.patch(`/projects/tasks/${t.id}`, { status: next });
    load();
  };
  const addMilestone = async () => {
    if (!mForm.title.trim()) return;
    await api.post(`/projects/${projectId}/milestones`, mForm);
    setMForm({ title: "", due_date: "", description: "" });
    load();
  };

  const PRIORITY_DOT = { high: "bg-rose-500", medium: "bg-amber-500", low: "bg-slate-400" };

  return (
    <div className="grid lg:grid-cols-12 gap-6">
      <div className="lg:col-span-7">
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-200">
          <h2 className="overline text-slate-500">Tasks</h2>
          <span className="text-[11px] font-mono text-slate-400">{tasks.filter((t) => t.status === "done").length}/{tasks.length} done</span>
        </div>
        <div className="space-y-1.5">
          {tasks.length === 0 && (
            <EmptyState title="No tasks yet." size="sm" dashed={true} />
          )}
          {tasks.map((t) => {
            const assignee = members.find((m) => m.id === t.assignee_id);
            return (
              <div key={t.id} className="flex items-center gap-3 border border-slate-200 bg-white px-3 py-2.5 hover:border-slate-300 transition-colors">
                <button
                  onClick={() => toggleStatus(t)}
                  className={`w-4 h-4 border-2 flex items-center justify-center shrink-0 transition-colors ${
                    t.status === "done" ? "bg-[#0F2847] border-[#0F2847]" : "border-slate-300 hover:border-[#0F2847]"
                  }`}
                >
                  {t.status === "done" && <Check size={10} strokeWidth={2.5} className="text-white" />}
                </button>
                <div className="flex-1 min-w-0">
                  <div className={`text-[13px] ${t.status === "done" ? "line-through text-slate-400" : "text-slate-900"}`}>
                    {t.title}
                  </div>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${PRIORITY_DOT[t.priority] || "bg-slate-400"}`} />
                    {assignee && <span className="text-[11px] text-slate-500">{assignee.full_name}</span>}
                    {t.due_date && <span className="text-[11px] font-mono text-slate-400">Due {t.due_date}</span>}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-5 border border-slate-200 bg-white p-4">
          <div className="overline text-slate-500 mb-3">New task</div>
          <div className="grid sm:grid-cols-5 gap-2">
            <input placeholder="Title" value={tForm.title} onChange={(e) => setTForm({ ...tForm, title: e.target.value })}
              className="sm:col-span-2 h-9 px-3 border border-slate-200 bg-white text-[13px] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors" />
            <select value={tForm.assignee_id} onChange={(e) => setTForm({ ...tForm, assignee_id: e.target.value })}
              className="h-9 px-3 border border-slate-200 bg-white text-[13px] focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors">
              <option value="">Assignee</option>
              {members.map((m) => <option key={m.id} value={m.id}>{m.full_name}</option>)}
            </select>
            <input type="date" value={tForm.due_date} onChange={(e) => setTForm({ ...tForm, due_date: e.target.value })}
              className="h-9 px-3 border border-slate-200 bg-white text-[13px] focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors" />
            <select value={tForm.priority} onChange={(e) => setTForm({ ...tForm, priority: e.target.value })}
              className="h-9 px-3 border border-slate-200 bg-white text-[13px] focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors">
              <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
            </select>
          </div>
          <button onClick={addTask} disabled={!tForm.title.trim()} className="mt-3 inline-flex items-center gap-2 bg-[#0F2847] text-white px-4 h-8 text-xs font-medium hover:bg-[#1a3d65] disabled:opacity-40 transition-colors">
            Add task
          </button>
        </div>
      </div>

      <div className="lg:col-span-5">
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-200">
          <h2 className="overline text-slate-500">Milestones</h2>
        </div>
        <div className="space-y-2">
          {milestones.length === 0 && (
            <EmptyState title="No milestones yet." size="sm" dashed={true} />
          )}
          {milestones.map((m) => (
            <div key={m.id} className="border-l-2 border-[#0F2847] pl-3 py-2">
              <div className="text-[13px] font-semibold text-slate-900">{m.title}</div>
              {m.due_date && <div className="text-[11px] font-mono text-slate-400 mt-0.5">{m.due_date}</div>}
              {m.description && <div className="text-[13px] text-slate-600 mt-1 leading-relaxed">{m.description}</div>}
            </div>
          ))}
        </div>

        <div className="mt-5 border border-slate-200 bg-white p-4">
          <div className="overline text-slate-500 mb-3">New milestone</div>
          <div className="space-y-2">
            <input placeholder="Title" value={mForm.title} onChange={(e) => setMForm({ ...mForm, title: e.target.value })}
              className="h-9 w-full px-3 border border-slate-200 bg-white text-[13px] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors" />
            <input type="date" value={mForm.due_date} onChange={(e) => setMForm({ ...mForm, due_date: e.target.value })}
              className="h-9 w-full px-3 border border-slate-200 bg-white text-[13px] focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors" />
            <textarea rows={2} placeholder="Description" value={mForm.description} onChange={(e) => setMForm({ ...mForm, description: e.target.value })}
              className="w-full px-3 py-2.5 border border-slate-200 bg-white text-[13px] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] resize-y transition-colors" />
          </div>
          <button onClick={addMilestone} disabled={!mForm.title.trim()} className="mt-3 inline-flex items-center gap-2 bg-[#0F2847] text-white px-4 h-8 text-xs font-medium hover:bg-[#1a3d65] disabled:opacity-40 transition-colors">
            Add milestone
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Team ─────────────────────────────────────────────────────────────────────

function Team({ members, projectId }) {
  const [roles, setRoles] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loadingIntel, setLoadingIntel] = useState(false);
  const [intelLoaded, setIntelLoaded] = useState(false);

  const loadIntelligence = async () => {
    if (intelLoaded) return;
    setLoadingIntel(true);
    try {
      const [rolesRes, analysisRes] = await Promise.all([
        api.get(`/projects/${projectId}/role-recommendations`),
        api.get(`/projects/${projectId}/team-analysis`),
      ]);
      setRoles(rolesRes.data.roles || []);
      setAnalysis(analysisRes.data);
      setIntelLoaded(true);
    } catch {
      // Team intelligence optional
    } finally {
      setLoadingIntel(false);
    }
  };

  const rolesMap = {};
  (roles || []).forEach((r) => { rolesMap[r.id] = r.recommended_role; });

  const ROLE_COLORS = {
    "Principal Investigator": "border-[#0F2847] text-[#0F2847]",
    "Co-Investigator":        "border-blue-600 text-blue-700",
    "Methodology Lead":       "border-purple-600 text-purple-700",
    "Data Analysis Lead":     "border-green-700 text-green-700",
    "Literature Review Lead": "border-amber-700 text-amber-700",
    "Grant Writing Lead":     "border-rose-700 text-rose-700",
  };

  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {members.map((m) => (
          <Link
            to={`/profile/${m.id}`}
            key={m.id}
            className="group border border-slate-200 bg-white p-5 hover:border-[#0F2847]/40 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Avatar url={m.avatar_url} name={m.full_name} size={44} />
              <div className="min-w-0">
                <div className="text-[13px] font-semibold text-slate-900 truncate group-hover:text-[#0F2847] transition-colors">
                  {m.full_name}
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">{userTypeLabel(m)}</div>
                <div className="text-[11px] text-slate-400 truncate">{m.institution}</div>
              </div>
            </div>
            {rolesMap[m.id] && (
              <div className="mt-3 pt-3 border-t border-slate-100">
                <span className={`text-[10px] border px-2 py-0.5 font-mono ${ROLE_COLORS[rolesMap[m.id]] || "border-slate-300 text-slate-500"}`}>
                  {rolesMap[m.id]}
                </span>
              </div>
            )}
          </Link>
        ))}
      </div>

      {!intelLoaded ? (
        <button
          onClick={loadIntelligence}
          disabled={loadingIntel}
          className="flex items-center gap-2 text-[13px] text-slate-600 border border-slate-200 px-4 py-2 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors disabled:opacity-50"
        >
          <Award size={13} strokeWidth={1.5} />
          {loadingIntel ? "Analysing team…" : "Analyse Team Intelligence"}
        </button>
      ) : (
        <div className="space-y-5">
          {(roles || []).length > 0 && (
            <div className="border border-slate-200 bg-white p-5">
              <div className="flex items-center gap-2 mb-4">
                <Award size={13} strokeWidth={1.5} className="text-[#0F2847]" />
                <div className="overline text-[#0F2847]">Recommended Roles</div>
              </div>
              <div className="grid sm:grid-cols-2 gap-2">
                {(roles || []).map((r) => (
                  <div key={r.id} className="flex items-center gap-3 px-3 py-2.5 bg-slate-50 border border-slate-100">
                    <Avatar url={r.avatar_url} name={r.full_name} size={32} />
                    <div className="min-w-0 flex-1">
                      <div className="text-[13px] font-medium text-slate-900 truncate">{r.full_name}</div>
                      <div className={`text-[10px] border px-1.5 py-0.5 mt-0.5 inline-block font-mono ${ROLE_COLORS[r.recommended_role] || "border-slate-300 text-slate-500"}`}>
                        {r.recommended_role}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis && (
            <div className="border border-slate-200 bg-white p-5">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle size={13} strokeWidth={1.5} className="text-amber-600" />
                <div className="overline text-amber-700">Missing Expertise</div>
              </div>

              {(analysis.missing_expertise || []).length === 0 ? (
                <div className="flex items-center gap-2 text-[13px] text-green-700 bg-green-50 border border-green-200 px-4 py-3">
                  <Check size={13} strokeWidth={2} />
                  Great team coverage — no critical expertise gaps detected.
                </div>
              ) : (
                <div className="space-y-4">
                  {(analysis.covered_expertise || []).length > 0 && (
                    <div>
                      <div className="text-[11px] text-slate-500 mb-2 font-mono uppercase tracking-wider">Current Expertise</div>
                      <div className="flex flex-wrap gap-1.5">
                        {(analysis.covered_expertise || []).map((e) => (
                          <span key={e} className="text-[11px] border border-green-300 text-green-700 bg-green-50 px-2 py-0.5">✓ {e}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {(analysis.suggestions || []).map((s) => (
                    <div key={s.expertise} className="border border-amber-200 bg-amber-50 p-4 space-y-3">
                      <div className="flex items-center gap-2">
                        <AlertTriangle size={12} strokeWidth={1.5} className="text-amber-600 shrink-0" />
                        <span className="text-[13px] font-medium text-amber-900">Missing: {s.expertise}</span>
                      </div>
                      {(s.researchers || []).length > 0 && (
                        <div>
                          <div className="text-[11px] text-amber-700 mb-2 font-mono uppercase tracking-wider">Suggested researchers</div>
                          <div className="space-y-1.5">
                            {(s.researchers || []).map((r) => (
                              <Link
                                key={r.id}
                                to={`/profile/${r.id}`}
                                className="flex items-center gap-2.5 bg-white border border-amber-100 px-3 py-2 hover:border-[#0F2847]/40 transition-colors"
                              >
                                <Avatar url={r.avatar_url} name={r.full_name} size={28} />
                                <div className="min-w-0 flex-1">
                                  <div className="text-[13px] font-medium text-slate-900 truncate">{r.full_name}</div>
                                  <div className="text-[11px] text-slate-500">{r.institution}</div>
                                </div>
                                <Search size={11} strokeWidth={1.5} className="ml-auto text-slate-400 shrink-0" />
                              </Link>
                            ))}
                          </div>
                        </div>
                      )}
                      <Link
                        to="/collaboration-intelligence"
                        className="flex items-center gap-1.5 text-[11px] text-[#0F2847] hover:underline"
                      >
                        <Users size={11} strokeWidth={1.5} />
                        Find {s.expertise} expert via Collaboration Intelligence
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Form primitives ──────────────────────────────────────────────────────────

function TextBlock({ label, value, onChange, rows = 3 }) {
  return (
    <Textarea
      label={label}
      rows={rows}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function SelectBlock({ label, value, options, onChange }) {
  return (
    <FormSelect label={label} value={value} onChange={(e) => onChange(e.target.value)}>
      {options.map((o) => <option key={o} value={o}>{o || "Select…"}</option>)}
    </FormSelect>
  );
}

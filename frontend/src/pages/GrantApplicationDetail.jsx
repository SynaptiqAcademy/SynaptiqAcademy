import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { useAuth } from "../contexts/AuthContext";
import { NAVY } from "@/lib/tokens";
import { SkeletonCard } from "@/components/ds/LoadingState";
import {
  ChevronDown, Users, DollarSign, ClipboardList, Save,
  GitBranch, Trash2, Plus, Check, X, FileText, AlertTriangle,
  CheckCircle2, Calendar,
} from "lucide-react";

// ── constants ──────────────────────────────────────────────────────────────────

const STATUSES = [
  { value: "draft",                label: "Draft" },
  { value: "in_preparation",       label: "In preparation" },
  { value: "internal_review",      label: "Internal review" },
  { value: "ready_for_submission", label: "Ready to submit" },
  { value: "submitted",            label: "Submitted" },
  { value: "eligible",             label: "Eligible" },
  { value: "under_evaluation",     label: "Under evaluation" },
  { value: "funded",               label: "Funded" },
  { value: "rejected",             label: "Rejected" },
  { value: "withdrawn",            label: "Withdrawn" },
];

const STATUS_COLOR = {
  draft:                "bg-slate-100 text-slate-700",
  in_preparation:       "bg-sky-50 text-sky-700",
  internal_review:      "bg-amber-50 text-amber-700",
  ready_for_submission: "bg-violet-50 text-violet-700",
  submitted:            "bg-blue-50 text-blue-700",
  eligible:             "bg-teal-50 text-teal-700",
  under_evaluation:     "bg-amber-100 text-amber-800",
  funded:               "bg-emerald-100 text-emerald-800",
  rejected:             "bg-rose-50 text-rose-700",
  withdrawn:            "bg-slate-200 text-slate-600",
};

const TEAM_ROLES = [
  "Principal Investigator", "Co-Investigator", "Work Package Lead",
  "Researcher", "Statistician", "Advisor", "Industry Partner",
  "Postdoctoral Researcher", "PhD Student", "Research Engineer",
];

const BUDGET_CATEGORIES = [
  "Personnel", "Equipment", "Travel", "Software", "Consumables",
  "Dissemination", "Overheads", "Subcontracting", "Other",
];

const DELIVERABLE_TYPES = [
  "Milestone", "Report", "Publication", "Dataset", "Software",
  "Patent", "Workshop", "Deliverable", "Other",
];

const DELIVERABLE_STATUS = {
  pending:   "bg-slate-100 text-slate-700",
  in_progress: "bg-amber-50 text-amber-700",
  completed: "bg-emerald-50 text-emerald-700",
  submitted: "bg-blue-50 text-blue-700",
  delayed:   "bg-rose-50 text-rose-700",
};

const PROPOSAL_SECTIONS = [
  { key: "executive_summary",      label: "Executive Summary" },
  { key: "introduction",           label: "Introduction" },
  { key: "objectives",             label: "Objectives" },
  { key: "methodology",            label: "Methodology" },
  { key: "work_plan",              label: "Work Plan" },
  { key: "team_expertise",         label: "Team & Expertise" },
  { key: "budget_justification",   label: "Budget Justification" },
  { key: "impact",                 label: "Impact" },
  { key: "dissemination",          label: "Dissemination" },
  { key: "ethics",                 label: "Ethics" },
  { key: "references",             label: "References" },
];

const TABS = [
  { k: "overview",   label: "Overview" },
  { k: "proposal",   label: "Proposal" },
  { k: "budget",     label: "Budget" },
  { k: "team",       label: "Team" },
  { k: "deliverables", label: "Deliverables" },
  { k: "versions",   label: "History" },
];

const fmtBudget = (n, cur = "EUR") => {
  if (!n) return "—";
  const a = parseFloat(n);
  if (a >= 1_000_000) return `${(a / 1_000_000).toFixed(2)}M ${cur}`;
  if (a >= 1_000) return `${(a / 1_000).toFixed(1)}K ${cur}`;
  return `${a} ${cur}`;
};

// ── components ─────────────────────────────────────────────────────────────────

function ChecklistItem({ label, done }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {done ? <CheckCircle2 size={14} className="text-emerald-600 shrink-0" /> : <AlertTriangle size={14} className="text-amber-500 shrink-0" />}
      <span className={done ? "text-slate-700" : "text-slate-500"}>{label}</span>
    </div>
  );
}

// ── main component ─────────────────────────────────────────────────────────────

export default function GrantApplicationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [app, setApp] = useState(null);
  const [dash, setDash] = useState(null);
  const [tab, setTab] = useState("overview");
  const [saving, setSaving] = useState(false);

  // Proposal editor
  const [sectionKey, setSectionKey] = useState("executive_summary");
  const [draft, setDraft] = useState("");
  const [savedFlag, setSavedFlag] = useState("");

  // Budget
  const [budget, setBudget] = useState(null);
  const [budgetForm, setBudgetForm] = useState({ category: "Personnel", description: "", amount: "", justification: "" });
  const [addingBudget, setAddingBudget] = useState(false);

  // Team
  const [teamInviteEmail, setTeamInviteEmail] = useState("");
  const [teamInviteRole, setTeamInviteRole] = useState("Co-Investigator");
  const [addingMember, setAddingMember] = useState(false);

  // Deliverables
  const [deliverables, setDeliverables] = useState([]);
  const [delivForm, setDelivForm] = useState({ title: "", type: "Milestone", due_date: "", work_package: "", description: "" });
  const [addingDeliv, setAddingDeliv] = useState(false);

  // Versions
  const [versions, setVersions] = useState([]);

  const load = useCallback(async () => {
    try {
      const [a, d] = await Promise.all([
        api.get(`/grant-applications/${id}`),
        api.get(`/grant-applications/${id}/dashboard`).catch(() => ({ data: null })),
      ]);
      setApp(a.data);
      setDash(d.data);
      const secs = a.data.proposal_sections || {};
      setDraft(secs[sectionKey] || "");
    } catch {
      toast.error("Failed to load application");
    }
  }, [id, sectionKey]);

  useEffect(() => { load(); }, [id]);

  useEffect(() => {
    if (app) {
      setDraft((app.proposal_sections || {})[sectionKey] || "");
    }
  }, [sectionKey, app?.id]);

  const loadTab = useCallback(async (k) => {
    setTab(k);
    if (k === "budget") {
      const { data } = await api.get(`/grant-applications/${id}/budget`).catch(() => ({ data: null }));
      setBudget(data);
    } else if (k === "deliverables") {
      const { data } = await api.get(`/grant-applications/${id}/deliverables`).catch(() => ({ data: [] }));
      setDeliverables(data || []);
    } else if (k === "versions") {
      const { data } = await api.get(`/grant-applications/${id}/versions`).catch(() => ({ data: [] }));
      setVersions(data || []);
    }
  }, [id]);

  const saveSection = async () => {
    if (!app) return;
    setSaving(true);
    try {
      const sections = { ...(app.proposal_sections || {}), [sectionKey]: draft };
      const { data } = await api.patch(`/grant-applications/${id}`, { proposal_sections: sections });
      setApp(data);
      setSavedFlag(`Saved · ${new Date().toLocaleTimeString()}`);
      setTimeout(() => setSavedFlag(""), 2400);
      api.get(`/grant-applications/${id}/dashboard`).then((r) => setDash(r.data)).catch(() => {});
    } catch { toast.error("Failed to save"); }
    finally { setSaving(false); }
  };

  const changeStatus = async (status) => {
    try {
      const { data } = await api.patch(`/grant-applications/${id}`, { status });
      setApp(data);
      toast.success(`Status: ${STATUSES.find((s) => s.value === status)?.label || status}`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const addBudgetItem = async () => {
    try {
      await api.post(`/grant-applications/${id}/budget`, { ...budgetForm, amount: parseFloat(budgetForm.amount) || 0 });
      setBudgetForm({ category: "Personnel", description: "", amount: "", justification: "" });
      setAddingBudget(false);
      const { data } = await api.get(`/grant-applications/${id}/budget`);
      setBudget(data);
      toast.success("Budget item added");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const deleteBudgetItem = async (bid) => {
    try {
      await api.delete(`/grant-applications/${id}/budget/${bid}`);
      const { data } = await api.get(`/grant-applications/${id}/budget`);
      setBudget(data);
    } catch { toast.error("Failed"); }
  };

  const inviteTeamMember = async () => {
    if (!teamInviteEmail.trim()) return;
    try {
      // Find user by email
      const { data: found } = await api.get(`/users/search?q=${encodeURIComponent(teamInviteEmail)}`).catch(() => ({ data: [] }));
      const target = Array.isArray(found) ? found[0] : null;
      if (!target) { toast.error("User not found"); return; }
      await api.post(`/grant-applications/${id}/team`, { user_id: target.id, role: teamInviteRole });
      setTeamInviteEmail("");
      setAddingMember(false);
      toast.success("Team member invited");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const removeTeamMember = async (uid) => {
    try {
      await api.delete(`/grant-applications/${id}/team/${uid}`);
      load();
      toast.success("Member removed");
    } catch { toast.error("Failed"); }
  };

  const addDeliverable = async () => {
    if (!delivForm.title.trim()) return;
    try {
      await api.post(`/grant-applications/${id}/deliverables`, delivForm);
      setDelivForm({ title: "", type: "Milestone", due_date: "", work_package: "", description: "" });
      setAddingDeliv(false);
      const { data } = await api.get(`/grant-applications/${id}/deliverables`);
      setDeliverables(data || []);
      toast.success("Deliverable added");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const markDeliverable = async (did, status) => {
    try {
      await api.patch(`/grant-applications/${id}/deliverables/${did}`, { status });
      const { data } = await api.get(`/grant-applications/${id}/deliverables`);
      setDeliverables(data || []);
    } catch { toast.error("Failed"); }
  };

  const deleteDeliverable = async (did) => {
    try {
      await api.delete(`/grant-applications/${id}/deliverables/${did}`);
      const { data } = await api.get(`/grant-applications/${id}/deliverables`);
      setDeliverables(data || []);
    } catch { toast.error("Failed"); }
  };

  const snapshotVersion = async () => {
    const summary = window.prompt("Version summary (optional):") || "";
    try {
      await api.post(`/grant-applications/${id}/versions`, { summary });
      toast.success("Version snapshot created");
      const { data } = await api.get(`/grant-applications/${id}/versions`);
      setVersions(data || []);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const restoreVersion = async (v) => {
    if (!window.confirm(`Restore to version ${v}? Current state will be auto-snapshotted.`)) return;
    try {
      await api.post(`/grant-applications/${id}/versions/${v}/restore`);
      toast.success(`Restored to v${v}`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const deleteApplication = async () => {
    if (!window.confirm("Permanently delete this application? This cannot be undone.")) return;
    try {
      await api.delete(`/grant-applications/${id}`);
      toast.success("Application deleted");
      navigate("/grant-applications");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  if (!app) return <div className="p-6"><SkeletonCard rows={5} /></div>;

  const isPi = app.pi_id === user?.id;

  return (
    <div className="space-y-6">
      <Link to="/grant-applications" className="text-sm text-slate-500 hover:text-slate-900">← My Applications</Link>

      {/* Header */}
      <header className="border-b border-slate-200 pb-6">
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <span className={`text-xs px-2 py-0.5 rounded-sm ${STATUS_COLOR[app.status] || "bg-slate-100 text-slate-700"}`}>
            {STATUSES.find((s) => s.value === app.status)?.label || app.status}
          </span>
          {app.grant?.agency && (
            <span className="overline text-slate-500 border border-slate-200 bg-slate-50 px-2 py-0.5">
              {app.grant.agency}
            </span>
          )}
          {isPi && (
            <select
              value={app.status}
              onChange={(e) => changeStatus(e.target.value)}
              className="ml-auto text-xs border border-slate-300 bg-white px-2 py-1 focus:outline-none"
            >
              {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          )}
        </div>
        <h1 className="font-serif text-4xl text-slate-900 leading-tight mt-2">
          {app.grant?.title || app.grant_title || "Grant Application"}
        </h1>
        <div className="mt-2 flex items-center gap-4 text-sm text-slate-500 flex-wrap font-mono">
          {app.grant?.deadline && <span className="flex items-center gap-1"><Calendar size={12} /> Deadline {app.grant.deadline}</span>}
          {app.consortium_name && <span>{app.consortium_name}</span>}
          {app.institution && <span>{app.institution}</span>}
          {app.requested_budget > 0 && (
            <span className="text-emerald-700 font-medium">{fmtBudget(app.requested_budget, app.currency)}</span>
          )}
        </div>
      </header>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.k}
            onClick={() => loadTab(t.k)}
            className={`shrink-0 px-4 py-2.5 text-sm border-b-2 -mb-px ${tab === t.k ? "border-[#0F2847] text-slate-900 font-medium" : "border-transparent text-slate-500 hover:text-slate-900"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW ─────────────────────────────────────────────────── */}
      {tab === "overview" && (
        <div className="grid lg:grid-cols-12 gap-8">
          <div className="lg:col-span-8 space-y-6">
            {dash && (
              <>
                <div className="grid sm:grid-cols-3 gap-4">
                  {[
                    { label: "Proposal progress",  value: `${dash.progress_pct}%`, sub: `${dash.filled_sections}/${dash.total_sections} sections` },
                    { label: "Total budget",        value: fmtBudget(dash.total_budget, dash.currency), sub: `${dash.currency}` },
                    { label: "Deliverables",        value: dash.deliverable_count, sub: dash.overdue_count > 0 ? `${dash.overdue_count} overdue` : "on track" },
                  ].map((k) => (
                    <div key={k.label} className="border border-slate-200 bg-white p-4">
                      <div className="overline text-slate-500">{k.label}</div>
                      <div className="font-serif text-2xl text-slate-900 mt-1">{k.value || "—"}</div>
                      <div className="text-xs text-slate-500 font-mono mt-1">{k.sub}</div>
                    </div>
                  ))}
                </div>

                {/* Progress bar */}
                <div className="bg-slate-100 h-1.5">
                  <div className="bg-[#0F2847] h-full transition-all" style={{ width: `${dash.progress_pct}%` }} />
                </div>

                {/* Readiness checklist */}
                <div className="border border-slate-200 bg-white p-5">
                  <div className="overline mb-3">{dash.ready_to_submit ? "Ready to submit" : "Checklist"}</div>
                  <div className="space-y-2">
                    {(dash.checklist || []).map((c, i) => (
                      <ChecklistItem key={i} label={c.label} done={c.done} />
                    ))}
                  </div>
                </div>

                {/* Upcoming deliverables */}
                {(dash.upcoming_deliverables || []).length > 0 && (
                  <div className="border border-slate-200 bg-white p-5">
                    <div className="overline mb-3">Upcoming deliverables</div>
                    <div className="space-y-2">
                      {dash.upcoming_deliverables.map((d) => (
                        <div key={d.id} className="flex items-center justify-between text-sm">
                          <span>{d.title}</span>
                          <span className="font-mono text-slate-500">{d.due_date || "—"}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          <aside className="lg:col-span-4 space-y-4">
            <div className="border border-slate-200 bg-white p-5 space-y-2 text-sm">
              <div className="overline">Grant details</div>
              {app.grant?.deadline && <div className="flex justify-between"><span className="text-slate-500">Deadline</span><span className="font-mono text-slate-900">{app.grant.deadline}</span></div>}
              {app.grant?.funding_amount?.amount && <div className="flex justify-between"><span className="text-slate-500">Available budget</span><span className="text-slate-900">{fmtBudget(app.grant.funding_amount.amount, app.grant.funding_amount.currency)}</span></div>}
              <div className="flex justify-between"><span className="text-slate-500">Your request</span><span className="text-emerald-700">{fmtBudget(app.requested_budget, app.currency)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Team</span><span>{(app.team || []).length + 1} members</span></div>
            </div>
            {app.grant?.id && (
              <Link to={`/grants/${app.grant.id}`} className="block text-center text-sm text-[#0F2847] border border-[#0F2847] px-4 py-2 hover:bg-[#0F2847] hover:text-white transition-colors">
                View grant opportunity →
              </Link>
            )}
            {isPi && (
              <button onClick={deleteApplication} className="w-full text-center text-sm text-rose-600 border border-rose-200 px-4 py-2 hover:bg-rose-50 flex items-center justify-center gap-2">
                <Trash2 size={13} /> Delete application
              </button>
            )}
          </aside>
        </div>
      )}

      {/* ── PROPOSAL ─────────────────────────────────────────────────── */}
      {tab === "proposal" && (
        <div className="grid lg:grid-cols-12 gap-6">
          {/* Section navigator */}
          <aside className="lg:col-span-3">
            <div className="space-y-1">
              {PROPOSAL_SECTIONS.map((s) => {
                const filled = !!(app.proposal_sections || {})[s.key]?.trim();
                return (
                  <button
                    key={s.key}
                    onClick={() => setSectionKey(s.key)}
                    className={`w-full text-left px-3 py-2 text-sm flex items-center justify-between ${sectionKey === s.key ? "bg-[#0F2847] text-white" : "text-slate-700 hover:bg-slate-50"}`}
                  >
                    <span className="truncate">{s.label}</span>
                    {filled && <CheckCircle2 size={12} className={sectionKey === s.key ? "text-white/70" : "text-emerald-500"} />}
                  </button>
                );
              })}
            </div>
          </aside>

          {/* Editor */}
          <div className="lg:col-span-9 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-slate-900">
                {PROPOSAL_SECTIONS.find((s) => s.key === sectionKey)?.label || sectionKey}
              </h3>
              <div className="flex items-center gap-3">
                {savedFlag && <span className="text-xs text-emerald-600 font-mono">{savedFlag}</span>}
                <button
                  onClick={saveSection}
                  disabled={saving}
                  className="inline-flex items-center gap-1 bg-[#0F2847] text-white px-3 py-1.5 text-xs hover:bg-slate-800 disabled:opacity-50"
                >
                  <Save size={12} strokeWidth={1.5} /> {saving ? "Saving…" : "Save"}
                </button>
              </div>
            </div>
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={`Write the ${PROPOSAL_SECTIONS.find((s) => s.key === sectionKey)?.label || sectionKey} section…`}
              className="w-full border border-slate-300 px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847] leading-relaxed"
              rows={20}
            />
            <div className="text-xs text-slate-500 font-mono">{draft.length} chars</div>
          </div>
        </div>
      )}

      {/* ── BUDGET ───────────────────────────────────────────────────── */}
      {tab === "budget" && (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="overline">Budget plan</div>
              {budget && (
                <div className="text-2xl font-serif text-emerald-700 mt-1">
                  {fmtBudget(budget.total, budget.currency)}
                </div>
              )}
            </div>
            <button onClick={() => setAddingBudget(!addingBudget)} className="inline-flex items-center gap-1 bg-[#0F2847] text-white px-3 py-1.5 text-xs">
              <Plus size={12} /> Add item
            </button>
          </div>

          {/* Category breakdown */}
          {budget && (budget.by_category || []).length > 0 && (
            <div className="grid sm:grid-cols-3 gap-3">
              {budget.by_category.map((c) => (
                <div key={c.category} className="border border-slate-200 bg-white p-3">
                  <div className="overline text-slate-500">{c.category}</div>
                  <div className="font-serif text-lg text-slate-900">{fmtBudget(c.amount, budget.currency)}</div>
                </div>
              ))}
            </div>
          )}

          {addingBudget && (
            <div className="border border-slate-200 bg-white p-5 space-y-3">
              <div className="overline">New budget item</div>
              <div className="grid sm:grid-cols-2 gap-3">
                <select value={budgetForm.category} onChange={(e) => setBudgetForm({ ...budgetForm, category: e.target.value })} className="px-3 py-2 border border-slate-300 bg-white text-sm">
                  {BUDGET_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
                </select>
                <input
                  placeholder="Description"
                  value={budgetForm.description}
                  onChange={(e) => setBudgetForm({ ...budgetForm, description: e.target.value })}
                  className="px-3 py-2 border border-slate-300 text-sm"
                />
                <input
                  type="number"
                  placeholder="Amount"
                  value={budgetForm.amount}
                  onChange={(e) => setBudgetForm({ ...budgetForm, amount: e.target.value })}
                  className="px-3 py-2 border border-slate-300 text-sm"
                />
                <input
                  placeholder="Justification"
                  value={budgetForm.justification}
                  onChange={(e) => setBudgetForm({ ...budgetForm, justification: e.target.value })}
                  className="px-3 py-2 border border-slate-300 text-sm"
                />
              </div>
              <div className="flex gap-2">
                <button onClick={addBudgetItem} className="bg-[#0F2847] text-white px-4 py-1.5 text-sm">Add</button>
                <button onClick={() => setAddingBudget(false)} className="border border-slate-300 px-4 py-1.5 text-sm">Cancel</button>
              </div>
            </div>
          )}

          <div className="border border-slate-200 divide-y divide-slate-100">
            {(budget?.items || []).length === 0 && (
              <div className="p-6 text-center text-sm text-slate-500">No budget items yet.</div>
            )}
            {(budget?.items || []).map((b) => (
              <div key={b.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <span className="overline text-xs text-[#0F2847]">{b.category}</span>
                  <div className="text-sm text-slate-900 mt-0.5">{b.description}</div>
                  {b.justification && <div className="text-xs text-slate-500 font-mono mt-0.5">{b.justification}</div>}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-mono text-emerald-700">{fmtBudget(b.amount, budget?.currency)}</span>
                  {isPi && <button onClick={() => deleteBudgetItem(b.id)} className="text-slate-400 hover:text-rose-600"><Trash2 size={13} /></button>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── TEAM ─────────────────────────────────────────────────────── */}
      {tab === "team" && (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <div className="overline">Grant team</div>
            <button onClick={() => setAddingMember(!addingMember)} className="inline-flex items-center gap-1 bg-[#0F2847] text-white px-3 py-1.5 text-xs">
              <Plus size={12} /> Invite member
            </button>
          </div>

          {addingMember && (
            <div className="border border-slate-200 bg-white p-5 space-y-3">
              <div className="overline">Invite collaborator</div>
              <div className="grid sm:grid-cols-2 gap-3">
                <input
                  placeholder="Email or name"
                  value={teamInviteEmail}
                  onChange={(e) => setTeamInviteEmail(e.target.value)}
                  className="px-3 py-2 border border-slate-300 text-sm"
                />
                <select value={teamInviteRole} onChange={(e) => setTeamInviteRole(e.target.value)} className="px-3 py-2 border border-slate-300 bg-white text-sm">
                  {TEAM_ROLES.map((r) => <option key={r}>{r}</option>)}
                </select>
              </div>
              <div className="flex gap-2">
                <button onClick={inviteTeamMember} className="bg-[#0F2847] text-white px-4 py-1.5 text-sm">Send invitation</button>
                <button onClick={() => setAddingMember(false)} className="border border-slate-300 px-4 py-1.5 text-sm">Cancel</button>
              </div>
            </div>
          )}

          {/* PI card */}
          <div className="border border-[#0F2847]/20 bg-[#0F2847]/5 p-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-[#0F2847] flex items-center justify-center text-white text-xs font-medium">
                {(app.pi?.full_name || "PI").charAt(0).toUpperCase()}
              </div>
              <div>
                <div className="text-sm font-medium text-slate-900">{app.pi?.full_name || "Principal Investigator"}</div>
                <div className="text-xs text-slate-500">{app.pi?.institution}</div>
              </div>
              <span className="ml-auto overline text-[#0F2847] text-xs">Principal Investigator</span>
            </div>
          </div>

          {/* Team members */}
          {(app.team || []).map((m) => (
            <div key={m.id} className="border border-slate-200 bg-white p-4 flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 text-xs font-medium shrink-0">
                {(m.user?.full_name || "?").charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-900">{m.user?.full_name || m.user_id}</div>
                <div className="text-xs text-slate-500">{m.user?.institution}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className="overline text-xs text-slate-600">{m.role}</span>
                <span className={`text-xs px-1.5 py-0.5 ${m.status === "accepted" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{m.status}</span>
                {isPi && (
                  <button onClick={() => removeTeamMember(m.user_id)} className="text-slate-400 hover:text-rose-600 ml-2">
                    <X size={13} />
                  </button>
                )}
              </div>
            </div>
          ))}

          {(app.team || []).length === 0 && (
            <div className="text-center text-sm text-slate-500 py-8">No team members invited yet.</div>
          )}
        </div>
      )}

      {/* ── DELIVERABLES ─────────────────────────────────────────────── */}
      {tab === "deliverables" && (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <div className="overline">Deliverables & milestones</div>
            <button onClick={() => setAddingDeliv(!addingDeliv)} className="inline-flex items-center gap-1 bg-[#0F2847] text-white px-3 py-1.5 text-xs">
              <Plus size={12} /> Add deliverable
            </button>
          </div>

          {addingDeliv && (
            <div className="border border-slate-200 bg-white p-5 space-y-3">
              <div className="overline">New deliverable</div>
              <div className="grid sm:grid-cols-2 gap-3">
                <input
                  placeholder="Title"
                  value={delivForm.title}
                  onChange={(e) => setDelivForm({ ...delivForm, title: e.target.value })}
                  className="px-3 py-2 border border-slate-300 text-sm sm:col-span-2"
                />
                <select value={delivForm.type} onChange={(e) => setDelivForm({ ...delivForm, type: e.target.value })} className="px-3 py-2 border border-slate-300 bg-white text-sm">
                  {DELIVERABLE_TYPES.map((t) => <option key={t}>{t}</option>)}
                </select>
                <input
                  type="date"
                  value={delivForm.due_date}
                  onChange={(e) => setDelivForm({ ...delivForm, due_date: e.target.value })}
                  className="px-3 py-2 border border-slate-300 text-sm"
                />
                <input
                  placeholder="Work package (e.g. WP1)"
                  value={delivForm.work_package}
                  onChange={(e) => setDelivForm({ ...delivForm, work_package: e.target.value })}
                  className="px-3 py-2 border border-slate-300 text-sm"
                />
                <input
                  placeholder="Description"
                  value={delivForm.description}
                  onChange={(e) => setDelivForm({ ...delivForm, description: e.target.value })}
                  className="px-3 py-2 border border-slate-300 text-sm"
                />
              </div>
              <div className="flex gap-2">
                <button onClick={addDeliverable} className="bg-[#0F2847] text-white px-4 py-1.5 text-sm">Add</button>
                <button onClick={() => setAddingDeliv(false)} className="border border-slate-300 px-4 py-1.5 text-sm">Cancel</button>
              </div>
            </div>
          )}

          <div className="border border-slate-200 divide-y divide-slate-100">
            {deliverables.length === 0 && (
              <div className="p-6 text-center text-sm text-slate-500">No deliverables defined yet.</div>
            )}
            {deliverables.map((d) => (
              <div key={d.id} className="flex items-start justify-between px-4 py-3 gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs px-1.5 py-0.5 ${DELIVERABLE_STATUS[d.status] || "bg-slate-100 text-slate-700"}`}>{d.status}</span>
                    <span className="overline text-xs text-[#0F2847]">{d.type}</span>
                    {d.work_package && <span className="text-xs text-slate-500 font-mono">{d.work_package}</span>}
                  </div>
                  <div className="text-sm font-medium text-slate-900 mt-1">{d.title}</div>
                  {d.description && <div className="text-xs text-slate-500 mt-0.5">{d.description}</div>}
                  {d.due_date && (
                    <div className="text-xs font-mono text-slate-500 mt-1 flex items-center gap-1">
                      <Calendar size={10} /> Due {d.due_date}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {d.status !== "completed" && (
                    <button onClick={() => markDeliverable(d.id, "completed")} className="text-xs text-emerald-600 hover:underline flex items-center gap-1"><Check size={12} /> Done</button>
                  )}
                  <button onClick={() => deleteDeliverable(d.id)} className="text-slate-400 hover:text-rose-600"><Trash2 size={13} /></button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── VERSIONS ─────────────────────────────────────────────────── */}
      {tab === "versions" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="overline">Proposal version history</div>
            <button onClick={snapshotVersion} className="inline-flex items-center gap-1 bg-[#0F2847] text-white px-3 py-1.5 text-xs">
              <GitBranch size={12} /> Snapshot current version
            </button>
          </div>
          <div className="border border-slate-200 divide-y divide-slate-100">
            {versions.length === 0 && (
              <div className="p-6 text-center text-sm text-slate-500">No snapshots yet. Click "Snapshot" to create the first version.</div>
            )}
            {versions.map((v) => (
              <div key={v.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <div className="text-sm font-medium text-slate-900">v{v.version} — {v.summary || "No summary"}</div>
                  <div className="text-xs text-slate-500 font-mono mt-0.5">
                    {v.author_name} · {v.created_at ? new Date(v.created_at).toLocaleString() : "—"}
                  </div>
                </div>
                <button onClick={() => restoreVersion(v.version)} className="text-xs text-[#0F2847] hover:underline">Restore</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { useAuth } from "../contexts/AuthContext";
import { SkeletonCard } from "@/components/ds/LoadingState";
import {
  ChevronDown, Users, DollarSign, ClipboardList, Save,
  GitBranch, Trash2, Plus, Check, X, FileText, AlertTriangle,
  CheckCircle2, Calendar,
} from "lucide-react";
import { Badge } from "@/components/ds/Badge";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { NavTabs } from "@/components/ds/NavTabs";
import { StatCard, StatGrid } from "@/components/ds/StatCard";
import { ProgressBar } from "@/components/ds/Progress";
import { ResearchLayout } from "@/layouts";

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

// Hex equivalents for the ds Badge's `color` prop
const STATUS_HEX = {
  draft:                "#64748B",
  in_preparation:       "#0369A1",
  internal_review:      "#B45309",
  ready_for_submission: "#6D28D9",
  submitted:            "#1D4ED8",
  eligible:             "#0F766E",
  under_evaluation:     "#92400E",
  funded:               "#065F46",
  rejected:             "#BE123C",
  withdrawn:            "#475569",
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

// Hex equivalents for the ds Badge's `color` prop
const DELIVERABLE_STATUS_HEX = {
  pending:     "#64748B",
  in_progress: "#B45309",
  completed:   "#059669",
  submitted:   "#1D4ED8",
  delayed:     "#BE123C",
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

  useEffect(() => { load(); }, [id, load]);

  useEffect(() => {
    if (app) {
      setDraft((app.proposal_sections || {})[sectionKey] || "");
    }
  }, [sectionKey, app]);

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

  if (!app) return <ResearchLayout title="Grant Application"><SkeletonCard rows={5} /></ResearchLayout>;

  const isPi = app.pi_id === user?.id;

  const headerActions = isPi ? (
    <FormSelect
      value={app.status}
      onChange={(e) => changeStatus(e.target.value)}
      size="sm"
      style={{ width: 200 }}
    >
      {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
    </FormSelect>
  ) : null;

  return (
    <ResearchLayout
      title={app.grant?.title || app.grant_title || "Grant Application"}
      actions={headerActions}
      nav={
        <NavTabs
          tabs={TABS.map((t) => ({ id: t.k, label: t.label }))}
          active={tab}
          onChange={loadTab}
        />
      }
    >
    <div className="space-y-6">
      <Link to="/grant-applications" className="text-sm text-slate-500 hover:text-slate-900">← My Applications</Link>

      {/* Meta bar */}
      <div className="border-b border-slate-200 pb-6">
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <Badge color={STATUS_HEX[app.status] || "#64748B"}>
            {STATUSES.find((s) => s.value === app.status)?.label || app.status}
          </Badge>
          {app.grant?.agency && (
            <Badge variant="neutral">{app.grant.agency}</Badge>
          )}
        </div>
        <div className="flex items-center gap-4 text-sm text-slate-500 flex-wrap font-mono">
          {app.grant?.deadline && <span className="flex items-center gap-1"><Calendar size={12} /> Deadline {app.grant.deadline}</span>}
          {app.consortium_name && <span>{app.consortium_name}</span>}
          {app.institution && <span>{app.institution}</span>}
          {app.requested_budget > 0 && (
            <span className="text-emerald-700 font-medium">{fmtBudget(app.requested_budget, app.currency)}</span>
          )}
        </div>
      </div>

      {/* ── OVERVIEW ─────────────────────────────────────────────────── */}
      {tab === "overview" && (
        <div className="grid lg:grid-cols-12 gap-8">
          <div className="lg:col-span-8 space-y-6">
            {dash && (
              <>
                <StatGrid cols={3}>
                  <StatCard label="Proposal progress" value={`${dash.progress_pct}%`} sub={`${dash.filled_sections}/${dash.total_sections} sections`} />
                  <StatCard label="Total budget" value={fmtBudget(dash.total_budget, dash.currency)} sub={dash.currency} />
                  <StatCard label="Deliverables" value={dash.deliverable_count} sub={dash.overdue_count > 0 ? `${dash.overdue_count} overdue` : "on track"} />
                </StatGrid>

                {/* Progress bar */}
                <ProgressBar value={dash.progress_pct} max={100} size="sm" showValue={false} />

                {/* Readiness checklist */}
                <Card padding="lg">
                  <div className="overline mb-3">{dash.ready_to_submit ? "Ready to submit" : "Checklist"}</div>
                  <div className="space-y-2">
                    {(dash.checklist || []).map((c, i) => (
                      <ChecklistItem key={i} label={c.label} done={c.done} />
                    ))}
                  </div>
                </Card>

                {/* Upcoming deliverables */}
                {(dash.upcoming_deliverables || []).length > 0 && (
                  <Card padding="lg">
                    <div className="overline mb-3">Upcoming deliverables</div>
                    <div className="space-y-2">
                      {dash.upcoming_deliverables.map((d) => (
                        <div key={d.id} className="flex items-center justify-between text-sm">
                          <span>{d.title}</span>
                          <span className="font-mono text-slate-500">{d.due_date || "—"}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
              </>
            )}
          </div>

          <aside className="lg:col-span-4 space-y-4">
            <Card padding="lg" className="space-y-2 text-sm">
              <div className="overline">Grant details</div>
              {app.grant?.deadline && <div className="flex justify-between"><span className="text-slate-500">Deadline</span><span className="font-mono text-slate-900">{app.grant.deadline}</span></div>}
              {app.grant?.funding_amount?.amount && <div className="flex justify-between"><span className="text-slate-500">Available budget</span><span className="text-slate-900">{fmtBudget(app.grant.funding_amount.amount, app.grant.funding_amount.currency)}</span></div>}
              <div className="flex justify-between"><span className="text-slate-500">Your request</span><span className="text-emerald-700">{fmtBudget(app.requested_budget, app.currency)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Team</span><span>{(app.team || []).length + 1} members</span></div>
            </Card>
            {app.grant?.id && (
              <Button as={Link} to={`/grants/${app.grant.id}`} variant="outline" className="w-full">
                View grant opportunity →
              </Button>
            )}
            {isPi && (
              <Button onClick={deleteApplication} variant="danger" className="w-full !bg-transparent !text-rose-600 !border !border-rose-200 hover:!bg-rose-50">
                <Trash2 size={13} /> Delete application
              </Button>
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
                const active = sectionKey === s.key;
                return (
                  <Button
                    key={s.key}
                    onClick={() => setSectionKey(s.key)}
                    variant={active ? "primary" : "ghost"}
                    className={`!w-full !justify-between !border-none ${active ? "" : "!bg-transparent"}`}
                  >
                    <span className="truncate">{s.label}</span>
                    {filled && <CheckCircle2 size={12} className={active ? "text-white/70" : "text-emerald-500"} />}
                  </Button>
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
                <Button onClick={saveSection} loading={saving} size="sm">
                  <Save size={12} strokeWidth={1.5} /> {saving ? "Saving…" : "Save"}
                </Button>
              </div>
            </div>
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={`Write the ${PROPOSAL_SECTIONS.find((s) => s.key === sectionKey)?.label || sectionKey} section…`}
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
            <Button onClick={() => setAddingBudget(!addingBudget)} size="sm">
              <Plus size={12} /> Add item
            </Button>
          </div>

          {/* Category breakdown */}
          {budget && (budget.by_category || []).length > 0 && (
            <div className="grid sm:grid-cols-3 gap-3">
              {budget.by_category.map((c) => (
                <Card key={c.category} padding="sm">
                  <div className="overline text-slate-500">{c.category}</div>
                  <div className="font-serif text-lg text-slate-900">{fmtBudget(c.amount, budget.currency)}</div>
                </Card>
              ))}
            </div>
          )}

          {addingBudget && (
            <Card padding="lg" className="space-y-3">
              <div className="overline">New budget item</div>
              <div className="grid sm:grid-cols-2 gap-3">
                <FormSelect value={budgetForm.category} onChange={(e) => setBudgetForm({ ...budgetForm, category: e.target.value })}>
                  {BUDGET_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
                </FormSelect>
                <Input
                  placeholder="Description"
                  value={budgetForm.description}
                  onChange={(e) => setBudgetForm({ ...budgetForm, description: e.target.value })}
                />
                <Input
                  type="number"
                  placeholder="Amount"
                  value={budgetForm.amount}
                  onChange={(e) => setBudgetForm({ ...budgetForm, amount: e.target.value })}
                />
                <Input
                  placeholder="Justification"
                  value={budgetForm.justification}
                  onChange={(e) => setBudgetForm({ ...budgetForm, justification: e.target.value })}
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={addBudgetItem} size="sm">Add</Button>
                <Button onClick={() => setAddingBudget(false)} variant="ghost" size="sm">Cancel</Button>
              </div>
            </Card>
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
                  {isPi && <Button onClick={() => deleteBudgetItem(b.id)} variant="ghost" size="icon" aria-label="Delete budget item" className="!text-slate-400 hover:!text-rose-600"><Trash2 size={13} /></Button>}
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
            <Button onClick={() => setAddingMember(!addingMember)} size="sm">
              <Plus size={12} /> Invite member
            </Button>
          </div>

          {addingMember && (
            <Card padding="lg" className="space-y-3">
              <div className="overline">Invite collaborator</div>
              <div className="grid sm:grid-cols-2 gap-3">
                <Input
                  placeholder="Email or name"
                  value={teamInviteEmail}
                  onChange={(e) => setTeamInviteEmail(e.target.value)}
                />
                <FormSelect value={teamInviteRole} onChange={(e) => setTeamInviteRole(e.target.value)}>
                  {TEAM_ROLES.map((r) => <option key={r}>{r}</option>)}
                </FormSelect>
              </div>
              <div className="flex gap-2">
                <Button onClick={inviteTeamMember} size="sm">Send invitation</Button>
                <Button onClick={() => setAddingMember(false)} variant="ghost" size="sm">Cancel</Button>
              </div>
            </Card>
          )}

          {/* PI card */}
          <Card padding="md" className="border-[#0F2847]/20 bg-[#0F2847]/5">
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
          </Card>

          {/* Team members */}
          {(app.team || []).map((m) => (
            <Card key={m.id} padding="md" className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 text-xs font-medium shrink-0">
                {(m.user?.full_name || "?").charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-900">{m.user?.full_name || m.user_id}</div>
                <div className="text-xs text-slate-500">{m.user?.institution}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className="overline text-xs text-slate-600">{m.role}</span>
                <Badge color={m.status === "accepted" ? "#059669" : "#B45309"} size="sm">{m.status}</Badge>
                {isPi && (
                  <Button onClick={() => removeTeamMember(m.user_id)} variant="ghost" size="icon" aria-label="Remove team member" className="!text-slate-400 hover:!text-rose-600 ml-2">
                    <X size={13} />
                  </Button>
                )}
              </div>
            </Card>
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
            <Button onClick={() => setAddingDeliv(!addingDeliv)} size="sm">
              <Plus size={12} /> Add deliverable
            </Button>
          </div>

          {addingDeliv && (
            <Card padding="lg" className="space-y-3">
              <div className="overline">New deliverable</div>
              <div className="grid sm:grid-cols-2 gap-3">
                <Input
                  placeholder="Title"
                  value={delivForm.title}
                  onChange={(e) => setDelivForm({ ...delivForm, title: e.target.value })}
                  wrapperClassName="sm:col-span-2"
                />
                <FormSelect value={delivForm.type} onChange={(e) => setDelivForm({ ...delivForm, type: e.target.value })}>
                  {DELIVERABLE_TYPES.map((t) => <option key={t}>{t}</option>)}
                </FormSelect>
                <Input
                  type="date"
                  value={delivForm.due_date}
                  onChange={(e) => setDelivForm({ ...delivForm, due_date: e.target.value })}
                />
                <Input
                  placeholder="Work package (e.g. WP1)"
                  value={delivForm.work_package}
                  onChange={(e) => setDelivForm({ ...delivForm, work_package: e.target.value })}
                />
                <Input
                  placeholder="Description"
                  value={delivForm.description}
                  onChange={(e) => setDelivForm({ ...delivForm, description: e.target.value })}
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={addDeliverable} size="sm">Add</Button>
                <Button onClick={() => setAddingDeliv(false)} variant="ghost" size="sm">Cancel</Button>
              </div>
            </Card>
          )}

          <div className="border border-slate-200 divide-y divide-slate-100">
            {deliverables.length === 0 && (
              <div className="p-6 text-center text-sm text-slate-500">No deliverables defined yet.</div>
            )}
            {deliverables.map((d) => (
              <div key={d.id} className="flex items-start justify-between px-4 py-3 gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge color={DELIVERABLE_STATUS_HEX[d.status] || "#64748B"} size="sm">{d.status}</Badge>
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
                    <Button onClick={() => markDeliverable(d.id, "completed")} variant="link" size="sm" className="!text-emerald-600">
                      <Check size={12} /> Done
                    </Button>
                  )}
                  <Button onClick={() => deleteDeliverable(d.id)} variant="ghost" size="icon" aria-label="Delete deliverable" className="!text-slate-400 hover:!text-rose-600">
                    <Trash2 size={13} />
                  </Button>
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
            <Button onClick={snapshotVersion} size="sm">
              <GitBranch size={12} /> Snapshot current version
            </Button>
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
                <Button onClick={() => restoreVersion(v.version)} variant="link" size="sm">Restore</Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
    </ResearchLayout>
  );
}

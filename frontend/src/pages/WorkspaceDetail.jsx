import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { Avatar } from "@/components/ds/Avatar";
import { useAuth } from "../contexts/AuthContext";
import { userTypeLabel } from "../lib/userTypes";
import WorkspaceKanban from "../components/researchOS/WorkspaceKanban";
import WorkspaceGantt from "../components/researchOS/WorkspaceGantt";
import PresenceBar from "../components/researchOS/PresenceBar";
import { useWorkspacePresence } from "../hooks/useWorkspacePresence";
import WikiPanel from "../components/wiki/WikiPanel";
import DeadlinesWidget from "../components/ai/DeadlinesWidget";
import AssistantLauncher from "../components/ai/AssistantLauncher";
import FilePanel from "../components/files/FilePanel";
import { toast } from "sonner";
import { ResearchLayout } from "@/layouts";
import { NAVY } from "@/lib/tokens";
import { SkeletonCard } from "@/components/ds/LoadingState";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Tag } from "@/components/ds/Tag";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { NavTabs } from "@/components/ds/NavTabs";
import { Modal } from "@/components/ds/Modal";
import { Alert } from "@/components/ds/Alert";
import { BarChart, LineChart, DonutChart } from "@/components/ds/Chart";
import {
  Send, MessageSquare, UserPlus, Activity, Target, FileText,
  Beaker, Users2, ShieldCheck, Trash2, Search, ChevronRight,
  BarChart2, LogOut, ArrowRightLeft,
  BrainCircuit, BookMarked, Microscope, PenLine, AlignLeft, Sparkles,
  Coins, ArrowRight, Info, AlertTriangle, Clock, GitBranch, ListTodo,
} from "lucide-react";
import { confirmDialog } from "@/lib/confirm";

const TABS = [
  { key: "overview",      label: "Overview"      },
  { key: "tasks",         label: "Tasks"         },
  { key: "gantt",         label: "Timeline"      },
  { key: "wiki",          label: "Wiki"          },
  { key: "team",          label: "Team"          },
  { key: "coauthors",     label: "Co-Authors"    },
  { key: "pipeline",      label: "Pipeline"      },
  { key: "reviews",       label: "Reviews"       },
  { key: "collaboration", label: "Collaboration" },
  { key: "ai",            label: "AI Enhancement" },
  { key: "activity",      label: "Activity"      },
  { key: "documents",     label: "Documents"     },
  { key: "analytics",     label: "Analytics"     },
];

// ── Document lifecycle stages ──────────────────────────────────────────────────
const DOC_STAGES = [
  { key: "idea",              label: "Idea",              color: "#94A3B8" },
  { key: "outline",           label: "Outline",           color: "#64748B" },
  { key: "draft",             label: "Draft",             color: "#0891B2" },
  { key: "in_progress",       label: "In Progress",       color: "#2563EB" },
  { key: "internal_review",   label: "Internal Review",   color: "#7C3AED" },
  { key: "coauthor_review",   label: "Co-author Review",  color: "#8B5CF6" },
  { key: "revision",          label: "Revision",          color: "#D97706" },
  { key: "ready_submission",  label: "Ready to Submit",   color: "#F59E0B" },
  { key: "submitted",         label: "Submitted",         color: "#EA580C" },
  { key: "accepted",          label: "Accepted",          color: "#059669" },
  { key: "published",         label: "Published",         color: "#065F46" },
  { key: "archived",          label: "Archived",          color: "#374151" },
];

const PIPELINE_STAGES = [
  { key: "workspace",      label: "Workspace",         icon: "⬡" },
  { key: "writing",        label: "Writing",           icon: "✏" },
  { key: "review",         label: "Internal Review",   icon: "👁" },
  { key: "repository",     label: "Repository",        icon: "📦" },
  { key: "discovery",      label: "Venue Discovery",   icon: "🔍" },
  { key: "submission_pkg", label: "Submission Package",icon: "📋" },
  { key: "submitted",      label: "Submitted",         icon: "📤" },
  { key: "revision",       label: "Revision",          icon: "🔄" },
  { key: "accepted",       label: "Accepted",          icon: "✅" },
  { key: "published",      label: "Published",         icon: "📖" },
  { key: "impact",         label: "Impact & Citations",icon: "📈" },
];

const CONTRIBUTION_ROLES = [
  "Conceptualization", "Data Curation", "Formal Analysis", "Funding Acquisition",
  "Investigation", "Methodology", "Project Administration", "Resources",
  "Software", "Supervision", "Validation", "Visualization",
  "Writing – Original Draft", "Writing – Review & Editing",
];

const WS_ROLES = ["Owner", "Administrator", "Lead Researcher", "Co-Author", "Reviewer", "Research Assistant", "Statistician", "Observer"];
const WS_ADMIN_ROLES = new Set(["Owner", "Administrator"]);

function HealthGauge({ value }) {
  // Circular SVG gauge — Oxford Blue arc on slate track.
  const r = 36, c = 2 * Math.PI * r;
  const off = c - (Math.min(100, Math.max(0, value)) / 100) * c;
  return (
    <div data-testid={TID.workspaceHealth} className="relative h-24 w-24">
      <svg viewBox="0 0 80 80" className="-rotate-90 h-24 w-24">
        <circle cx="40" cy="40" r={r} stroke="#E2E8F0" strokeWidth="6" fill="none" />
        <circle cx="40" cy="40" r={r} stroke="#0F2847" strokeWidth="6" fill="none"
                strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-2xl font-bold text-slate-900">{value}</div>
        <div className="text-[10px] uppercase tracking-wider text-slate-500 font-mono">health</div>
      </div>
    </div>
  );
}

function Kpi({ label, value, sub }) {
  return (
    <Card padding="md">
      <div className="overline">{label}</div>
      <div className="text-2xl font-bold text-slate-900 mt-2">{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1 font-mono">{sub}</div>}
    </Card>
  );
}

function InviteModal({ wsId, onClose, onInvited, existingIds }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [role, setRole] = useState("Researcher");
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    const t = setTimeout(async () => {
      if (!q.trim()) { setResults([]); return; }
      try {
        const { data } = await api.get(`/users?q=${encodeURIComponent(q)}&limit=8`);
        setResults((data || []).filter((u) => !existingIds.has(u.id)));
      } catch { setResults([]); }
    }, 220);
    return () => clearTimeout(t);
  }, [q, existingIds]);

  const invite = async (uid) => {
    setBusy(uid);
    try {
      await api.post(`/workspaces/${wsId}/invitations`, { user_id: uid, role });
      toast.success("Invitation sent");
      onInvited?.();
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    } finally { setBusy(null); }
  };

  return (
    <Modal open onClose={onClose} title="Invite a researcher" description="Workspace" size="sm">
      <div className="space-y-4">
        <FormSelect
          label="Role"
          data-testid={TID.workspaceInviteRole}
          value={role} onChange={(e) => setRole(e.target.value)}
        >
          {WS_ROLES.filter((r) => r !== "Owner").map((r) => <option key={r} value={r}>{r}</option>)}
        </FormSelect>
        <Input
          label="Search the network"
          data-testid={TID.workspaceInviteSearch}
          prefix={<Search size={14} strokeWidth={1.5} />}
          autoFocus value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Name, institution, area, skill…"
        />
        <div className="max-h-80 overflow-auto -mx-1">
          {q.trim() && results.length === 0 && (
            <div className="text-sm text-slate-500 px-1 py-3">No matches.</div>
          )}
          {results.map((u) => (
            <button
              key={u.id}
              data-testid={TID.workspaceInviteUserPick(u.id)}
              disabled={busy === u.id}
              onClick={() => invite(u.id)}
              className="w-full flex items-center gap-3 px-1 py-2 hover:bg-slate-50 border-b border-slate-100 text-left"
            >
              <Avatar url={u.avatar_url} name={u.full_name} size={36} />
              <div className="min-w-0 flex-1">
                <div className="text-sm text-slate-900 truncate">{u.full_name}</div>
                <div className="text-xs text-slate-500 truncate">{userTypeLabel(u)} · {u.institution}</div>
              </div>
              <span className="text-xs text-[#0F2847] font-mono">{busy === u.id ? "…" : "Invite"}</span>
            </button>
          ))}
        </div>
      </div>
    </Modal>
  );
}

export default function WorkspaceDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [ws, setWs] = useState(null);
  const [dash, setDash] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [tab, setTab] = useState("overview");
  const [wikiTyping, setWikiTyping] = useState(false);
  const { peers: presencePeers } = useWorkspacePresence(id, tab, tab === "wiki" && wikiTyping);
  const [note, setNote] = useState("");
  const [showInvite, setShowInvite] = useState(false);
  const [showTransfer, setShowTransfer] = useState(false);
  const [transferTarget, setTransferTarget] = useState("");

  // ── Co-author state ──────────────────────────────────────────────────────────
  const [coauthorRoles, setCoauthorRoles] = useState({});   // { uid: [role strings] }
  const [coauthorOrder, setCoauthorOrder] = useState([]);   // ordered uid list
  const [correspondingAuthor, setCorrespondingAuthor] = useState(null);
  const [coauthorDirty, setCoauthorDirty] = useState(false);
  const [coauthorSaving, setCoauthorSaving] = useState(false);

  // ── Collaboration state ──────────────────────────────────────────────────────
  const [discussions, setDiscussions] = useState([]);
  const [collabNote, setCollabNote] = useState("");
  const [collabKind, setCollabKind] = useState("note");

  // ── Review state ─────────────────────────────────────────────────────────────
  const [reviews, setReviewsData] = useState([]);
  const [docStage, setDocStage] = useState("draft");
  const [stageChanging, setStageChanging] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      const [a, b] = await Promise.all([
        api.get(`/workspaces/${id}`),
        api.get(`/workspaces/${id}/dashboard`).catch(() => ({ data: null })),
      ]);
      setWs(a.data); setDash(b.data);
      // Co-author order/roles/corresponding-author: prefer whatever was
      // already saved on the workspace; only default-seed from member
      // order the very first time none has ever been saved.
      if (a.data?.members_info?.length && !coauthorOrder.length) {
        const memberIds = a.data.members_info.map((m) => m.id);
        const savedOrder = Array.isArray(a.data.coauthor_order) ? a.data.coauthor_order : null;
        setCoauthorOrder(
          savedOrder
            ? [...savedOrder.filter((id) => memberIds.includes(id)), ...memberIds.filter((id) => !savedOrder.includes(id))]
            : memberIds
        );
        setCoauthorRoles(a.data.coauthor_roles || {});
        setCorrespondingAuthor(a.data.corresponding_author_id || a.data.owner_id || null);
        if (a.data.doc_stage) setDocStage(a.data.doc_stage);
      }
    } catch {
      toast.error("Failed to load workspace");
    }
  }, [id, coauthorOrder.length]);

  const saveCoauthors = useCallback(async () => {
    setCoauthorSaving(true);
    try {
      await api.patch(`/workspaces/${id}`, {
        coauthor_order: coauthorOrder,
        coauthor_roles: coauthorRoles,
        corresponding_author_id: correspondingAuthor,
      });
      setCoauthorDirty(false);
      toast.success("Author order & roles saved");
    } catch {
      toast.error("Failed to save — you may need admin access to this workspace");
    } finally {
      setCoauthorSaving(false);
    }
  }, [id, coauthorOrder, coauthorRoles, correspondingAuthor]);

  const loadDiscussions = useCallback(async () => {
    try {
      const { data } = await api.get(`/workspaces/${id}/activity`, { params: { limit: 50 } });
      setDiscussions(Array.isArray(data) ? data : (data.items || []));
    } catch { setDiscussions([]); }
  }, [id]);

  const loadReviewsData = useCallback(async () => {
    try {
      const { data } = await api.get(`/workspaces/${id}/activity`, { params: { kind: "review", limit: 30 } });
      setReviewsData(Array.isArray(data) ? data : (data.items || []));
    } catch { setReviewsData([]); }
  }, [id]);

  const loadAnalytics = useCallback(async () => {
    if (analytics) return;
    try {
      const { data } = await api.get(`/workspaces/${id}/analytics`);
      setAnalytics(data);
    } catch { setAnalytics(null); }
  }, [id, analytics]);

  useEffect(() => { load(); }, [id, load]);
  useEffect(() => { if (tab === "analytics") loadAnalytics(); }, [tab, loadAnalytics]);
  useEffect(() => { if (tab === "collaboration") loadDiscussions(); }, [tab, loadDiscussions]);
  useEffect(() => { if (tab === "reviews") loadReviewsData(); }, [tab, loadReviewsData]);

  const myRole = dash?.your_role || (ws?.member_roles?.[user?.id]) || (ws?.owner_id === user?.id ? "Owner" : "Researcher");
  const isAdmin = WS_ADMIN_ROLES.has(myRole);
  const existingIds = useMemo(() => new Set([...(ws?.members || [])]), [ws]);

  const postNote = async () => {
    if (!note.trim()) return;
    try {
      await api.post(`/workspaces/${id}/activity`, { message: note, kind: "note" });
      setNote(""); load();
    } catch (e) { toast.error("Failed"); }
  };

  const changeRole = async (uid, role) => {
    try {
      await api.patch(`/workspaces/${id}/members/${uid}/role`, { role });
      toast.success("Role updated"); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const removeMember = async (uid) => {
    if (!(await confirmDialog({ title: "Remove this member from the workspace?", danger: true }))) return;
    try {
      await api.delete(`/workspaces/${id}/members/${uid}`);
      toast.success("Member removed"); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const leaveWorkspace = async () => {
    if (!(await confirmDialog({ title: "Leave this workspace? You'll lose access unless re-invited.", danger: true }))) return;
    try {
      await api.post(`/workspaces/${id}/leave`);
      toast.success("You left the workspace");
      navigate("/workspaces");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const transferOwnership = async () => {
    if (!transferTarget) { toast.error("Select a member"); return; }
    if (!(await confirmDialog({ title: `Transfer ownership to ${(ws?.members_info || []).find((m) => m.id === transferTarget)?.full_name}?`, danger: false }))) return;
    try {
      await api.post(`/workspaces/${id}/transfer`, { new_owner_id: transferTarget });
      toast.success("Ownership transferred"); setShowTransfer(false); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  if (!ws) return (
    <div className="p-6 space-y-4">
      <SkeletonCard rows={4} />
    </div>
  );

  const counts = dash?.counts || { members: 0, active_projects: 0, active_manuscripts: 0, tasks_total: 0, tasks_completed: 0, milestones_total: 0, milestones_completed: 0 };
  const health = dash?.research_health ?? 0;
  const upcoming = dash?.upcoming_milestones || [];
  const linkedManuscripts = dash?.manuscripts || [];

  return (
    <ResearchLayout
      eyebrow="Workspace"
      title={ws.name}
      subtitle={ws.description}
      ring={{ value: health, label: "Research Health" }}
      stats={[
        { label: "Members",             value: counts.members },
        { label: "Active Projects",     value: counts.active_projects },
        { label: "Active Manuscripts",  value: counts.active_manuscripts },
        { label: "Milestones",          value: `${counts.milestones_completed}/${counts.milestones_total}` },
      ]}
      actions={
        <>
          <AssistantLauncher entityKind="workspace" entityId={id} entityTitle={ws.name} />
          <Button
            data-testid={TID.openChatBtn}
            onClick={() => navigate("/messages", { state: { openContext: { type: "workspace", id } } })}
            variant="hero"
            size="sm"
          >
            <MessageSquare size={12} strokeWidth={1.5} /> Open chat
          </Button>
          {isAdmin && (
            <Button
              data-testid={TID.workspaceInviteBtn}
              onClick={() => setShowInvite(true)}
              variant="subtle"
              size="sm"
            >
              <UserPlus size={12} strokeWidth={1.5} /> Invite member
            </Button>
          )}
          {myRole === "Owner" && (
            <Button variant="hero" size="sm" onClick={() => setShowTransfer(!showTransfer)}>
              <ArrowRightLeft size={12} strokeWidth={1.5} /> Transfer ownership
            </Button>
          )}
          {myRole !== "Owner" && (
            <Button variant="danger" size="sm" onClick={leaveWorkspace}>
              <LogOut size={12} strokeWidth={1.5} /> Leave workspace
            </Button>
          )}
        </>
      }
    >
    <div className="space-y-8">
      <header className="pb-2">
        <div className="flex items-center gap-3 flex-wrap">
          <Badge variant="warning" size="sm">{ws.status || "active"}</Badge>
          <Badge variant="default" size="sm" data-testid={TID.workspaceYourRole}>
            <ShieldCheck size={11} strokeWidth={1.5} /> Your role: {myRole}
          </Badge>
          <PresenceBar peers={presencePeers} />
        </div>

        {/* Transfer ownership panel */}
        {showTransfer && (
          <Card variant="ghost" padding="md" className="mt-4 border border-amber-200 bg-amber-50 flex items-center gap-4">
            <div className="overline text-amber-700 shrink-0">Transfer to</div>
            <FormSelect
              wrapperClassName="flex-1"
              value={transferTarget}
              onChange={(e) => setTransferTarget(e.target.value)}
            >
              <option value="">Select a member…</option>
              {(ws.members_info || []).filter((m) => m.id !== user?.id).map((m) => (
                <option key={m.id} value={m.id}>{m.full_name} ({m.workspace_role})</option>
              ))}
            </FormSelect>
            <Button size="sm" onClick={transferOwnership} className="bg-amber-700 hover:bg-amber-800">Confirm</Button>
            <Button size="sm" variant="ghost" onClick={() => setShowTransfer(false)}>Cancel</Button>
          </Card>
        )}
      </header>

      <NavTabs
        tabs={TABS.map((t) => ({ id: t.key, label: t.label }))}
        active={tab}
        onChange={setTab}
      />

      {tab === "overview" && (
        <div className="grid lg:grid-cols-12 gap-8">
          <section className="lg:col-span-8 space-y-6">
            {/* Health + KPI grid */}
            <Card padding="lg">
              <div className="flex items-center gap-6">
                <HealthGauge value={health} />
                <div className="flex-1">
                  <div className="overline">Research health</div>
                  <p className="text-sm text-slate-700 mt-1 max-w-xl">A weighted score across task completion, milestone progress, and active project load. Improves as your team ships.</p>
                </div>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
                <Kpi label="Members" value={counts.members} sub={`${Object.keys(ws.member_roles || {}).length} role assignments`} />
                <Kpi label="Active projects" value={counts.active_projects} sub={`${(ws.project_ids || []).length} linked`} />
                <Kpi label="Active manuscripts" value={counts.active_manuscripts} sub={`${linkedManuscripts.length} total`} />
                <Kpi label="Milestones" value={`${counts.milestones_completed}/${counts.milestones_total}`} sub={`${counts.tasks_completed}/${counts.tasks_total} tasks done`} />
              </div>
            </Card>

            {/* Linked manuscripts */}
            <Card data-testid={TID.workspaceLinkedManuscripts} padding="lg">
              <div className="flex items-center gap-2 mb-3">
                <FileText size={14} strokeWidth={1.5} className="text-[#0F2847]" />
                <div className="overline">Linked manuscripts</div>
              </div>
              {linkedManuscripts.length === 0 ? (
                <div className="text-sm text-slate-500">No manuscripts linked to this workspace yet. Open a manuscript and assign this workspace from its metadata panel.</div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {linkedManuscripts.map((m) => (
                    <Link to={`/manuscripts/${m.id}`} key={m.id} className="flex items-center gap-3 py-3 hover:bg-slate-50 -mx-2 px-2">
                      <div className="min-w-0 flex-1">
                        <div className="text-[13px] font-semibold text-slate-900 truncate">{m.title}</div>
                        <div className="text-xs text-slate-500 font-mono mt-0.5">{m.status} · v{m.current_version || 0}</div>
                      </div>
                      <ChevronRight size={14} strokeWidth={1.5} className="text-slate-400" />
                    </Link>
                  ))}
                </div>
              )}
            </Card>

            {/* Linked projects */}
            <Card padding="lg">
              <div className="flex items-center gap-2 mb-3">
                <Beaker size={14} strokeWidth={1.5} className="text-[#0F2847]" />
                <div className="overline">Projects</div>
              </div>
              {(ws.projects || []).length === 0 ? (
                <div className="text-sm text-slate-500">No projects linked yet.</div>
              ) : (
                <div className="space-y-3">
                  {ws.projects.map((p) => (
                    <Link key={p.id} to={`/projects/${p.id}`} className="block border-l-2 border-[#0F2847] pl-3 py-1 hover:bg-slate-50">
                      <div className="text-[13px] font-semibold text-slate-900">{p.title}</div>
                      <div className="text-xs text-slate-500">{p.description}</div>
                    </Link>
                  ))}
                </div>
              )}
            </Card>
          </section>

          <aside className="lg:col-span-4 space-y-6">
            <DeadlinesWidget workspaceId={id} initialItems={dash?.upcoming_deadlines || null} />
            <Card data-testid={TID.workspaceUpcomingMilestones} padding="md">
              <div className="flex items-center gap-2 mb-3">
                <Target size={14} strokeWidth={1.5} className="text-[#0F2847]" />
                <div className="overline">Upcoming milestones</div>
              </div>
              {upcoming.length === 0 ? (
                <div className="text-sm text-slate-500">No upcoming milestones.</div>
              ) : (
                <ul className="space-y-3">
                  {upcoming.map((m) => (
                    <li key={m.id} className="border-l-2 border-amber-400 pl-3">
                      <div className="text-sm text-slate-900">{m.title}</div>
                      <div className="text-xs text-slate-500 font-mono mt-0.5">{m.target_date || "No date"}</div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card padding="md">
              <div className="flex items-center gap-2 mb-3">
                <Activity size={14} strokeWidth={1.5} className="text-[#0F2847]" />
                <div className="overline">Recent activity</div>
              </div>
              {(dash?.recent_activity || []).length === 0 ? (
                <div className="text-sm text-slate-500">Nothing yet.</div>
              ) : (
                <ul className="space-y-3">
                  {(dash?.recent_activity || []).slice(0, 6).map((a) => (
                    <li key={a.id} className="text-sm">
                      <span className="text-slate-900">{a.message}</span>
                      <div className="text-xs text-slate-500 font-mono mt-0.5">{a.actor_name} · {new Date(a.created_at).toLocaleDateString()}</div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </aside>
        </div>
      )}

      {tab === "tasks" && (
        <WorkspaceKanban wsId={id} canEdit={WS_ADMIN_ROLES.has(myRole) || myRole === "Co-Investigator" || myRole === "Researcher"} />
      )}

      {tab === "gantt" && (
        <WorkspaceGantt wsId={id} canEdit={WS_ADMIN_ROLES.has(myRole) || myRole === "Co-Investigator" || myRole === "Researcher"} />
      )}

      {tab === "wiki" && (
        <WikiPanel workspaceId={id} members={ws?.members_info || []} onTypingChange={setWikiTyping} />
      )}

      {tab === "team" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-600">{(ws.members_info || []).length} member{(ws.members_info || []).length === 1 ? "" : "s"} · Owner & PI can modify roles.</div>
            {isAdmin && (
              <Button variant="outline" size="sm" onClick={() => setShowInvite(true)}>
                <UserPlus size={12} strokeWidth={1.5} /> Invite
              </Button>
            )}
          </div>
          <Card padding="none" className="divide-y divide-slate-100">
            {(ws.members_info || []).map((m) => {
              const role = ws.member_roles?.[m.id] || (m.id === ws.owner_id ? "Owner" : "Researcher");
              const isOwner = m.id === ws.owner_id;
              return (
                <div key={m.id} className="flex items-center gap-4 px-5 py-3">
                  <Link to={`/profile/${m.id}`}><Avatar url={m.avatar_url} name={m.full_name} size={40} /></Link>
                  <div className="min-w-0 flex-1">
                    <Link to={`/profile/${m.id}`} className="text-sm text-slate-900 font-medium hover:underline">{m.full_name}</Link>
                    <div className="text-xs text-slate-500">{userTypeLabel(m)} · {m.institution}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isAdmin && !isOwner ? (
                      <FormSelect
                        data-testid={TID.workspaceMemberRole(m.id)}
                        size="sm"
                        value={role}
                        onChange={(e) => changeRole(m.id, e.target.value)}
                      >
                        {WS_ROLES.filter((r) => r !== "Owner").map((r) => <option key={r} value={r}>{r}</option>)}
                      </FormSelect>
                    ) : (
                      <Badge variant="default" size="sm">{role}</Badge>
                    )}
                    {isAdmin && !isOwner && (
                      <Button
                        variant="ghost"
                        size="icon"
                        data-testid={TID.workspaceMemberRemove(m.id)}
                        onClick={() => removeMember(m.id)}
                        className="text-slate-400 hover:text-red-600"
                        title="Remove member"
                      >
                        <Trash2 size={14} strokeWidth={1.5} />
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </Card>
        </div>
      )}

      {/* ══ AI ENHANCEMENT TAB ══════════════════════════════════════════════ */}
      {tab === "ai" && (
        <AIEnhancementTab workspace={ws} docStage={docStage} />
      )}

      {tab === "activity" && (
        <div className="max-w-3xl space-y-5">
          <Card padding="md" className="flex gap-3">
            <Input
              data-testid={TID.workspaceNoteInput}
              wrapperClassName="flex-1"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && postNote()}
              placeholder="Post a note to the team…"
            />
            <Button data-testid={TID.workspaceNoteSubmit} onClick={postNote}>
              <Send size={12} strokeWidth={1.5} /> Post
            </Button>
          </Card>
          <div className="space-y-3">
            {(ws.activity || []).length === 0 && <div className="text-sm text-slate-500">No activity yet.</div>}
            {(ws.activity || []).map((a) => (
              <div key={a.id} className="border-l-2 border-[#0F2847] pl-3">
                <div className="text-sm text-slate-900">{a.message}</div>
                <div className="text-xs text-slate-500 mt-0.5 font-mono">{a.actor_name} · {new Date(a.created_at).toLocaleString()}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "documents" && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {(ws.documents || []).length === 0 && (
            <div className="col-span-full text-sm text-slate-500 py-12 text-center border border-dashed border-slate-300">No documents yet. Add resources from the <Link to="/repository" className="text-[#0F2847] underline">Repository</Link>.</div>
          )}
          {(ws.documents || []).map((d) => (
            <Card key={d.id} padding="lg">
              <div className="overline text-[#0F2847]">{d.type}</div>
              <h3 className="text-[13px] font-semibold text-slate-900 mt-1">{d.title}</h3>
              <p className="text-sm text-slate-600 mt-2 line-clamp-3">{d.description}</p>
            </Card>
          ))}
        </div>
      )}

      {tab === "analytics" && (
        <div className="space-y-6">
          {!analytics ? (
            <div className="p-6">
              <SkeletonCard rows={3} />
            </div>
          ) : (
            <>
              <div className="grid sm:grid-cols-3 gap-4">
                <Card padding="lg">
                  <div className="overline">Total activity events</div>
                  <div className="text-2xl font-bold text-slate-900 mt-2">{analytics.activity_by_day.reduce((s, d) => s + d.count, 0)}</div>
                  <div className="text-xs text-slate-500 font-mono mt-1">last {analytics.period_days} days</div>
                </Card>
                <Card padding="lg">
                  <div className="overline">Active contributors</div>
                  <div className="text-2xl font-bold text-slate-900 mt-2">{analytics.top_contributors.length}</div>
                  <div className="text-xs text-slate-500 font-mono mt-1">unique actors</div>
                </Card>
                <Card padding="lg">
                  <div className="overline">Most active day</div>
                  <div className="text-2xl font-bold text-slate-900 mt-2 truncate">
                    {analytics.activity_by_day.length > 0
                      ? analytics.activity_by_day.reduce((a, b) => a.count > b.count ? a : b).date
                      : "—"}
                  </div>
                </Card>
              </div>

              <Card padding="lg">
                <div className="flex items-center gap-2 mb-4">
                  <BarChart2 size={14} strokeWidth={1.5} className="text-[#0F2847]" />
                  <div className="overline">Activity by type</div>
                </div>
                {analytics.activity_by_kind.length === 0 ? (
                  <div className="text-sm text-slate-500">No activity recorded.</div>
                ) : (
                  <div className="space-y-2">
                    {analytics.activity_by_kind.map(({ kind, count }) => {
                      const max = analytics.activity_by_kind[0].count;
                      return (
                        <div key={kind} className="flex items-center gap-3">
                          <div className="overline w-36 truncate">{kind || "note"}</div>
                          <div className="flex-1 bg-slate-100 h-2">
                            <div className="bg-[#0F2847] h-2" style={{ width: `${(count / max) * 100}%` }} />
                          </div>
                          <div className="text-xs text-slate-500 w-6 text-right font-mono">{count}</div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>

              <Card padding="lg">
                <div className="flex items-center gap-2 mb-4">
                  <Users2 size={14} strokeWidth={1.5} className="text-[#0F2847]" />
                  <div className="overline">Top contributors</div>
                </div>
                {analytics.top_contributors.length === 0 ? (
                  <div className="text-sm text-slate-500">No contributors yet.</div>
                ) : (
                  <div className="space-y-2">
                    {analytics.top_contributors.map((c, i) => (
                      <div key={c.user_id} className="flex items-center gap-3">
                        <div className="text-xs text-slate-400 w-4 font-mono">{i + 1}</div>
                        <div className="text-sm text-slate-900 flex-1">{c.name}</div>
                        <div className="text-xs text-slate-500 font-mono">{c.actions} actions</div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              {analytics.tasks && (
                <>
                  <div className="grid sm:grid-cols-4 gap-4">
                    <Card padding="lg">
                      <div className="overline mb-2">Completion rate</div>
                      <div className="flex items-center gap-3">
                        <DonutChart value={Math.round((analytics.tasks.completion_rate_overall || 0) * 100)} size={44} strokeWidth={5}>
                          <span className="text-[11px] font-bold text-slate-900">
                            {analytics.tasks.completion_rate_overall != null ? `${Math.round(analytics.tasks.completion_rate_overall * 100)}%` : "—"}
                          </span>
                        </DonutChart>
                        <div className="text-xs text-slate-500 font-mono">{analytics.tasks.tasks_completed_total} of {analytics.tasks.tasks_total} tasks</div>
                      </div>
                    </Card>
                    <Card padding="lg">
                      <div className="overline">Overdue</div>
                      <div className="text-2xl font-bold mt-2" style={{ color: analytics.tasks.overdue_count > 0 ? "#DC2626" : "#0f172a" }}>{analytics.tasks.overdue_count}</div>
                      <div className="text-xs text-slate-500 font-mono mt-1">open tasks past due date</div>
                    </Card>
                    <Card padding="lg">
                      <div className="overline">Blocked</div>
                      <div className="text-2xl font-bold text-slate-900 mt-2">{analytics.tasks.blocked_count}</div>
                      <div className="text-xs text-slate-500 font-mono mt-1">waiting on a dependency</div>
                    </Card>
                    <Card padding="lg">
                      <div className="overline">Work in progress</div>
                      <div className="text-2xl font-bold text-slate-900 mt-2">{analytics.tasks.wip_count}</div>
                      <div className="text-xs text-slate-500 font-mono mt-1">in progress + review</div>
                    </Card>
                  </div>

                  <div className="grid sm:grid-cols-2 gap-4">
                    <Card padding="lg">
                      <div className="flex items-center gap-2 mb-4">
                        <Clock size={14} strokeWidth={1.5} className="text-[#0F2847]" />
                        <div className="overline">Cycle time</div>
                      </div>
                      {analytics.tasks.cycle_time_days.sample_size === 0 ? (
                        <div className="text-sm text-slate-500">Not enough completed tasks with tracked status history yet.</div>
                      ) : (
                        <>
                          <div className="text-2xl font-bold text-slate-900">{analytics.tasks.cycle_time_days.avg}d <span className="text-sm font-normal text-slate-500">avg</span></div>
                          <div className="text-xs text-slate-500 font-mono mt-1">median {analytics.tasks.cycle_time_days.median}d · {analytics.tasks.cycle_time_days.sample_size} tasks · in-progress → completed</div>
                        </>
                      )}
                    </Card>
                    <Card padding="lg">
                      <div className="flex items-center gap-2 mb-4">
                        <Clock size={14} strokeWidth={1.5} className="text-[#0F2847]" />
                        <div className="overline">Lead time</div>
                      </div>
                      {analytics.tasks.lead_time_days.sample_size === 0 ? (
                        <div className="text-sm text-slate-500">Not enough completed tasks yet.</div>
                      ) : (
                        <>
                          <div className="text-2xl font-bold text-slate-900">{analytics.tasks.lead_time_days.avg}d <span className="text-sm font-normal text-slate-500">avg</span></div>
                          <div className="text-xs text-slate-500 font-mono mt-1">median {analytics.tasks.lead_time_days.median}d · {analytics.tasks.lead_time_days.sample_size} tasks · created → completed</div>
                        </>
                      )}
                    </Card>
                  </div>

                  <Card padding="lg">
                    <div className="flex items-center gap-2 mb-4">
                      <Activity size={14} strokeWidth={1.5} className="text-[#0F2847]" />
                      <div className="overline">Burndown — open tasks over time</div>
                    </div>
                    {analytics.tasks.tasks_total === 0 ? (
                      <div className="text-sm text-slate-500">No tasks yet.</div>
                    ) : (
                      <LineChart series={[{ label: "Open tasks", data: analytics.tasks.burndown.map((d) => d.open_count), color: "#0F2847" }]} height={140} />
                    )}
                  </Card>

                  <Card padding="lg">
                    <div className="flex items-center gap-2 mb-4">
                      <GitBranch size={14} strokeWidth={1.5} className="text-[#0F2847]" />
                      <div className="overline">Cumulative flow by status</div>
                    </div>
                    {analytics.tasks.tasks_total === 0 ? (
                      <div className="text-sm text-slate-500">No tasks yet.</div>
                    ) : (
                      <LineChart
                        height={140}
                        series={[
                          { label: "Backlog", data: analytics.tasks.cumulative_flow.map((d) => d.backlog), color: "#63707f" },
                          { label: "Planned", data: analytics.tasks.cumulative_flow.map((d) => d.planned), color: "#0284C7" },
                          { label: "In progress", data: analytics.tasks.cumulative_flow.map((d) => d.in_progress), color: "#D97706" },
                          { label: "Review", data: analytics.tasks.cumulative_flow.map((d) => d.review), color: "#7C3AED" },
                          { label: "Completed", data: analytics.tasks.cumulative_flow.map((d) => d.completed), color: "#059669" },
                        ]}
                      />
                    )}
                  </Card>

                  <div className="grid sm:grid-cols-2 gap-4">
                    <Card padding="lg">
                      <div className="flex items-center gap-2 mb-4">
                        <ListTodo size={14} strokeWidth={1.5} className="text-[#0F2847]" />
                        <div className="overline">Workload by assignee</div>
                      </div>
                      {analytics.tasks.workload_by_assignee.length === 0 ? (
                        <div className="text-sm text-slate-500">No open tasks assigned.</div>
                      ) : (
                        <BarChart
                          data={analytics.tasks.workload_by_assignee.map((w) => ({ label: w.name || "Unassigned", value: w.open_count }))}
                          showValues showLabels height={90}
                        />
                      )}
                    </Card>
                    <Card padding="lg">
                      <div className="flex items-center gap-2 mb-4">
                        <AlertTriangle size={14} strokeWidth={1.5} className="text-[#0F2847]" />
                        <div className="overline">Completed per week</div>
                      </div>
                      {analytics.tasks.completed_trend.length === 0 ? (
                        <div className="text-sm text-slate-500">No tasks completed in this period.</div>
                      ) : (
                        <BarChart
                          data={analytics.tasks.completed_trend.map((w) => ({ label: w.period_start.slice(5), value: w.count }))}
                          showValues showLabels height={90}
                        />
                      )}
                    </Card>
                  </div>

                  <Card padding="lg">
                    <div className="overline mb-3">Content activity (last {analytics.period_days} days)</div>
                    <div className="flex gap-8">
                      <div>
                        <div className="text-2xl font-bold text-slate-900">{(analytics.comments_by_day || []).reduce((s, d) => s + d.count, 0)}</div>
                        <div className="text-xs text-slate-500 font-mono mt-1">comments</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-slate-900">{(analytics.wiki_edits_by_day || []).reduce((s, d) => s + d.count, 0)}</div>
                        <div className="text-xs text-slate-500 font-mono mt-1">wiki edits</div>
                      </div>
                    </div>
                  </Card>
                </>
              )}
            </>
          )}
        </div>
      )}

      {/* ══ CO-AUTHORS TAB ══════════════════════════════════════════════════ */}
      {tab === "coauthors" && (
        <div className="max-w-4xl space-y-6">
          <Card padding="lg">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="overline">Author Order & Contributions</div>
                <p className="text-xs text-slate-500 mt-1">Drag to reorder. Order reflects authorship position. CRediT taxonomy roles.</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => setShowInvite(true)}>
                <UserPlus size={12} strokeWidth={1.5} /> Add Co-Author
              </Button>
            </div>

            <div className="divide-y divide-slate-100">
              {(ws?.members_info || []).length === 0 && (
                <div className="text-sm text-slate-500 py-8 text-center">No members yet. Invite co-authors first.</div>
              )}
              {(ws?.members_info || []).map((m, idx) => {
                const isCa = correspondingAuthor === m.id;
                const roles = coauthorRoles[m.id] || [];
                return (
                  <div key={m.id} className="flex items-start gap-4 py-4">
                    <div className="flex flex-col items-center gap-1 pt-1 shrink-0 w-8">
                      <span className="text-xl font-bold text-slate-900 leading-none">{idx + 1}</span>
                      <div className="flex flex-col gap-0.5">
                        {idx > 0 && (
                          <button
                            aria-label={`Move ${m.full_name} up in author order`}
                            onClick={() => { setCoauthorOrder((prev) => { const a = [...prev]; [a[idx - 1], a[idx]] = [a[idx], a[idx - 1]]; return a; }); setCoauthorDirty(true); }}
                            className="text-slate-400 hover:text-slate-900 text-xs leading-none"
                          >▲</button>
                        )}
                        {idx < (ws?.members_info || []).length - 1 && (
                          <button
                            aria-label={`Move ${m.full_name} down in author order`}
                            onClick={() => { setCoauthorOrder((prev) => { const a = [...prev]; [a[idx], a[idx + 1]] = [a[idx + 1], a[idx]]; return a; }); setCoauthorDirty(true); }}
                            className="text-slate-400 hover:text-slate-900 text-xs leading-none"
                          >▼</button>
                        )}
                      </div>
                    </div>
                    <Link to={`/profile/${m.id}`}><Avatar url={m.avatar_url} name={m.full_name} size={40} /></Link>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-slate-900">{m.full_name}</span>
                        {isCa && <Badge variant="default" size="sm">Corresponding</Badge>}
                        {m.orcid?.orcid_id && (
                          <a href={`https://orcid.org/${m.orcid.orcid_id}`} target="_blank" rel="noopener noreferrer" className="text-[10px] font-mono font-bold text-[#a6ce39] border border-[#a6ce3940] px-1.5 py-0.5">iD</a>
                        )}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">{m.institution}</div>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {CONTRIBUTION_ROLES.map((r) => {
                          const active = roles.includes(r);
                          return (
                            <Tag
                              key={r}
                              size="sm"
                              variant={active ? "active" : "default"}
                              onClick={() => {
                                setCoauthorRoles((prev) => {
                                  const cur = prev[m.id] || [];
                                  return { ...prev, [m.id]: active ? cur.filter((x) => x !== r) : [...cur, r] };
                                });
                                setCoauthorDirty(true);
                              }}
                            >
                              {r}
                            </Tag>
                          );
                        })}
                      </div>
                    </div>
                    <div className="shrink-0 flex flex-col gap-2">
                      <Button
                        variant={isCa ? "primary" : "ghost"}
                        size="sm"
                        onClick={() => { setCorrespondingAuthor(isCa ? null : m.id); setCoauthorDirty(true); }}
                      >
                        {isCa ? "★ Corresponding" : "Set Corresponding"}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>

            {(ws?.members_info || []).length > 0 && (
              <div className="flex items-center justify-end gap-3 mt-5 pt-4 border-t border-slate-100">
                {coauthorDirty && (
                  <span className="text-xs text-amber-700 font-medium">Unsaved changes</span>
                )}
                <Button
                  variant="primary"
                  size="sm"
                  onClick={saveCoauthors}
                  disabled={!coauthorDirty || coauthorSaving}
                  loading={coauthorSaving}
                >
                  {coauthorSaving ? "Saving…" : "Save changes"}
                </Button>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ══ PIPELINE TAB ════════════════════════════════════════════════════ */}
      {tab === "pipeline" && (
        <div className="space-y-8">
          {/* Document stage selector */}
          <Card padding="lg">
            <div className="overline mb-4">Document Lifecycle Stage</div>
            <div className="flex flex-wrap gap-2 mb-6">
              {DOC_STAGES.map((s, i) => {
                const active = docStage === s.key;
                const isPast = DOC_STAGES.findIndex((x) => x.key === docStage) > i;
                return (
                  <button
                    key={s.key}
                    onClick={async () => {
                      setDocStage(s.key);
                      setStageChanging(true);
                      try {
                        await api.patch(`/workspaces/${id}`, { status: s.key });
                        await api.post(`/workspaces/${id}/activity`, { message: `Stage changed to: ${s.label}`, kind: "stage_change" });
                        toast.success(`Stage → ${s.label}`);
                      } catch { toast.error("Failed to update stage"); }
                      finally { setStageChanging(false); }
                    }}
                    disabled={stageChanging}
                    style={{ borderColor: active ? s.color : undefined, background: active ? s.color : undefined }}
                    className={`text-xs px-3 py-1.5 border transition-all font-medium ${active ? "text-white" : isPast ? "text-slate-400 border-slate-200 line-through" : "text-slate-600 border-slate-200 hover:border-slate-400"}`}
                  >
                    {i + 1}. {s.label}
                  </button>
                );
              })}
            </div>
            <div className="border-l-2 pl-4" style={{ borderColor: DOC_STAGES.find((s) => s.key === docStage)?.color || "#94A3B8" }}>
              <div className="text-sm font-semibold text-slate-900">Current stage: {DOC_STAGES.find((s) => s.key === docStage)?.label}</div>
              <div className="text-xs text-slate-500 mt-0.5">Update stage as your document progresses through the research lifecycle.</div>
            </div>
          </Card>

          {/* Publication Pipeline visual */}
          <Card padding="lg">
            <div className="overline mb-6">Publication Pipeline</div>
            <div className="overflow-x-auto">
              <div className="flex items-center gap-0 min-w-max pb-2">
                {PIPELINE_STAGES.map((s, i) => {
                  const stageIdx = DOC_STAGES.findIndex((x) => x.key === docStage);
                  const pipelineMap = {
                    0: 0, 1: 0, 2: 1, 3: 4, 4: 2, 5: 5, 6: 6, 7: 3, 8: 7, 9: 8, 10: 9, 11: 10
                  };
                  const activePipeStage = pipelineMap[stageIdx] ?? 0;
                  const isPast = i < activePipeStage;
                  const isActive = i === activePipeStage;
                  return (
                    <React.Fragment key={s.key}>
                      <div className={`flex flex-col items-center gap-2 w-20 ${isActive ? "opacity-100" : isPast ? "opacity-60" : "opacity-30"}`}>
                        <div className={`w-10 h-10 rounded-none flex items-center justify-center text-base border-2 transition-all ${isActive ? "border-[#0F2847] bg-[#0F2847] text-white" : isPast ? "border-green-600 bg-green-50" : "border-slate-200 bg-white"}`}>
                          {isPast ? "✓" : s.icon}
                        </div>
                        <div className="text-[10px] text-center text-slate-600 leading-tight font-medium">{s.label}</div>
                      </div>
                      {i < PIPELINE_STAGES.length - 1 && (
                        <div className={`w-6 h-0.5 shrink-0 mb-6 ${i < activePipeStage ? "bg-green-500" : "bg-slate-200"}`} />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>
          </Card>

          {/* Linked manuscripts with status */}
          <Card padding="lg">
            <div className="overline mb-4">Linked Documents</div>
            {(dash?.manuscripts || []).length === 0 ? (
              <div className="text-sm text-slate-500">No manuscripts linked. Link from <Link to="/publications" className="text-[#0F2847] underline">Publications</Link>.</div>
            ) : (
              <div className="space-y-3">
                {(dash?.manuscripts || []).map((m) => {
                  const stage = DOC_STAGES.find((s) => s.key === m.status || s.label.toLowerCase() === m.status?.toLowerCase());
                  return (
                    <Link to={`/manuscripts/${m.id}`} key={m.id} className="flex items-center gap-4 py-3 border-b border-slate-100 hover:bg-slate-50 -mx-2 px-2">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-slate-900 truncate">{m.title}</div>
                        <div className="text-xs text-slate-500 font-mono mt-0.5">v{m.current_version || 0}</div>
                      </div>
                      {stage && (
                        <Badge color={stage.color} size="sm" className="shrink-0">
                          {stage.label}
                        </Badge>
                      )}
                      <ChevronRight size={14} strokeWidth={1.5} className="text-slate-400 shrink-0" />
                    </Link>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Quick links to pipeline services */}
          <Card padding="lg">
            <div className="overline mb-4">Pipeline Services</div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[
                { label: "Journal Discovery",    to: "/publishing-intelligence",  desc: "Find the right journal for your paper" },
                { label: "Conference Matching",  to: "/matching/conference",       desc: "Match to academic conferences" },
                { label: "Publication Hub",      to: "/publications",              desc: "Manage submissions & status" },
                { label: "Statistical Review",   to: "/statistical-review",        desc: "AI-powered statistical analysis" },
                { label: "Manuscript Review",    to: "/manuscript-review",         desc: "Pre-submission manuscript check" },
                { label: "Citation Monitoring",  to: "/citation-monitoring",       desc: "Track citations post-publication" },
              ].map(({ label, to, desc }) => (
                <Card key={to} to={to} padding="md">
                  <div className="text-sm font-semibold text-slate-900">{label}</div>
                  <div className="text-xs text-slate-500 mt-1">{desc}</div>
                </Card>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* ══ REVIEWS TAB ═════════════════════════════════════════════════════ */}
      {tab === "reviews" && (
        <div className="max-w-3xl space-y-6">
          {/* Request review */}
          <Card padding="md">
            <div className="overline mb-3">Request Review</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
              {[
                { type: "internal",  label: "Internal Review",     desc: "Team member reviews the work" },
                { type: "coauthor",  label: "Co-author Review",    desc: "Co-author approves before submission" },
                { type: "external",  label: "External Reviewer",   desc: "Independent peer review" },
                { type: "editorial", label: "Editorial Review",    desc: "Editor decision on submission" },
              ].map((r) => (
                <Card
                  key={r.type}
                  padding="sm"
                  onClick={() => {
                    api.post(`/workspaces/${id}/activity`, {
                      message: `Review requested: ${r.label}`,
                      kind: "review",
                      metadata: { review_type: r.type, status: "pending" },
                    }).then(() => { toast.success(`${r.label} requested`); loadReviewsData(); }).catch(() => toast.error("Failed"));
                  }}
                >
                  <div className="text-sm font-semibold text-slate-900">{r.label}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{r.desc}</div>
                </Card>
              ))}
            </div>
          </Card>

          {/* Review history */}
          <Card padding="md">
            <div className="overline mb-3">Review History</div>
            {reviews.length === 0 ? (
              <div className="text-sm text-slate-500 py-6 text-center border border-dashed border-slate-200">No reviews yet. Request a review above to start the workflow.</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {reviews.map((r) => (
                  <div key={r.id} className="flex items-start gap-3 py-3">
                    <div className={`w-2 h-2 rounded-full mt-2 shrink-0 ${r.metadata?.status === "approved" ? "bg-green-500" : r.metadata?.status === "rejected" ? "bg-red-500" : "bg-amber-400"}`} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-slate-900">{r.message}</div>
                      <div className="text-xs text-slate-500 font-mono mt-0.5">{r.actor_name} · {r.created_at ? new Date(r.created_at).toLocaleDateString() : ""}</div>
                      {r.metadata?.comment && <div className="text-xs text-slate-600 mt-1 border-l-2 border-slate-200 pl-2">{r.metadata.comment}</div>}
                    </div>
                    {r.metadata?.status === "pending" && isAdmin && (
                      <div className="flex gap-2 shrink-0">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-green-700 border-green-300 hover:bg-green-50"
                          onClick={() => api.patch(`/workspaces/${id}/activity/${r.id}`, { metadata: { ...r.metadata, status: "approved" } }).then(() => loadReviewsData()).catch(() => {})}
                        >Approve</Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-600 border-red-200 hover:bg-red-50"
                          onClick={() => api.patch(`/workspaces/${id}/activity/${r.id}`, { metadata: { ...r.metadata, status: "rejected" } }).then(() => loadReviewsData()).catch(() => {})}
                        >Reject</Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ══ COLLABORATION TAB ═══════════════════════════════════════════════ */}
      {tab === "collaboration" && (
        <div className="max-w-3xl space-y-6">
          {/* Post to collaboration center */}
          <Card padding="md">
            <div className="overline mb-3">Post to Collaboration Center</div>
            <div className="flex gap-2 mb-2">
              {[
                { value: "note",         label: "Note" },
                { value: "announcement", label: "Announcement" },
                { value: "decision",     label: "Decision" },
                { value: "meeting",      label: "Meeting Note" },
              ].map((k) => (
                <Tag
                  key={k.value}
                  variant={collabKind === k.value ? "active" : "default"}
                  onClick={() => setCollabKind(k.value)}
                >
                  {k.label}
                </Tag>
              ))}
            </div>
            <div className="flex gap-3 mt-3">
              <Textarea
                wrapperClassName="flex-1"
                value={collabNote}
                onChange={(e) => setCollabNote(e.target.value)}
                placeholder={
                  collabKind === "announcement" ? "Post an announcement to the team…" :
                  collabKind === "decision"     ? "Record a team decision…" :
                  collabKind === "meeting"      ? "Add meeting notes…" :
                  "Add a note or comment…"
                }
                rows={3}
              />
            </div>
            <div className="flex justify-end mt-2">
              <Button
                onClick={async () => {
                  if (!collabNote.trim()) return;
                  try {
                    await api.post(`/workspaces/${id}/activity`, { message: collabNote, kind: collabKind });
                    setCollabNote(""); await loadDiscussions();
                    toast.success("Posted");
                  } catch { toast.error("Failed"); }
                }}
              >
                <Send size={12} strokeWidth={1.5} /> Post
              </Button>
            </div>
          </Card>

          {/* Discussion feed */}
          <Card padding="md">
            <div className="overline mb-4">Discussion</div>
            {discussions.length === 0 ? (
              <div className="text-sm text-slate-500 py-8 text-center border border-dashed border-slate-200">No collaboration posts yet. Post a note, announcement or decision above.</div>
            ) : (
              <div className="space-y-4">
                {discussions.map((d) => {
                  const kindColors = {
                    announcement: { bg: "#FFFBEB", border: "#FDE68A", label: "Announcement" },
                    decision:     { bg: "#F0FDF4", border: "#A7F3D0", label: "Decision" },
                    meeting:      { bg: "#EFF6FF", border: "#BFDBFE", label: "Meeting Note" },
                    review:       { bg: "#FAF5FF", border: "#DDD6FE", label: "Review" },
                    note:         { bg: "white",   border: "#E2E8F0", label: "Note" },
                  };
                  const style = kindColors[d.kind] || kindColors.note;
                  return (
                    <div key={d.id} className="border-l-4 pl-4 py-2" style={{ borderColor: style.border, background: style.bg }}>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" size="sm" style={{ borderColor: style.border }}>
                          {style.label}
                        </Badge>
                        <span className="text-xs text-slate-500 font-mono">{d.actor_name}</span>
                        <span className="text-xs text-slate-400 font-mono ml-auto">{d.created_at ? new Date(d.created_at).toLocaleString() : ""}</span>
                      </div>
                      <div className="text-sm text-slate-900">{d.message}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Quick links */}
          <Card padding="md">
            <div className="overline mb-3">Collaboration Tools</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { label: "Open Chat",       to: "/messages",    desc: "Real-time team messaging" },
                { label: "Group Chat",      to: "/messages",    desc: "Workspace group channel" },
                { label: "Collaboration Requests", to: "/collaboration-requests", desc: "Manage open collaboration calls" },
                { label: "Collaboration AI", to: "/collaboration-intelligence", desc: "AI-powered team insights" },
              ].map(({ label, to, desc }) => (
                <Card key={label} to={to} padding="sm">
                  <div className="text-sm font-semibold text-slate-900">{label}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{desc}</div>
                </Card>
              ))}
            </div>
          </Card>
        </div>
      )}

      {showInvite && (
        <InviteModal
          wsId={id}
          existingIds={existingIds}
          onClose={() => setShowInvite(false)}
          onInvited={load}
        />
      )}
      <div className="mt-6">
        <FilePanel entityKind="workspace" entityId={id} />
      </div>
    </div>
    </ResearchLayout>
  );
}

/* ══ AI ENHANCEMENT TAB COMPONENT ══════════════════════════════════════════ */

// Contextual AI tool suggestions per document stage
const STAGE_AI_MAP = {
  idea:              ["literature-review", "research-gap-finder", "research-design-advisor"],
  outline:           ["literature-review", "research-gap-finder", "research-design-advisor"],
  draft:             ["ai-assistant", "ai-rewrite", "statistical-review"],
  in_progress:       ["ai-assistant", "ai-rewrite", "statistical-review"],
  internal_review:   ["manuscript-review", "statistical-review", "ai-rewrite"],
  coauthor_review:   ["manuscript-review", "ai-rewrite", "abstract-generator"],
  revision:          ["manuscript-review", "ai-rewrite", "statistical-review"],
  ready_submission:  ["abstract-generator", "manuscript-review", "ai-rewrite"],
  submitted:         ["abstract-generator"],
  accepted:          ["abstract-generator", "ai-rewrite"],
  published:         [],
  archived:          [],
};

const AI_TOOLS = {
  "literature-review":        { to: "/literature-review",       label: "Literature Review",    icon: BookMarked, cost: 20, unit: "per review",   desc: "Survey the field. Identify what's been done and what's missing." },
  "research-gap-finder":      { to: "/research-gap-finder",     label: "Research Gap Finder",  icon: Target,     cost: 10, unit: "per analysis",  desc: "Find novel angles and underexplored questions in your field." },
  "research-design-advisor":  { to: "/research-design-advisor", label: "Study Design Advisor", icon: Beaker,     cost: 10, unit: "per session",   desc: "Validate your methodology and study design before data collection." },
  "ai-assistant":             { to: "/ai",                      label: "AI Research Assistant",icon: BrainCircuit, cost: 2, unit: "per message", desc: "Expert guidance on any research question or writing challenge." },
  "ai-rewrite":               { to: "/ai/rewrite",              label: "Academic Rewriting",   icon: PenLine,    cost: 2,  unit: "per rewrite",   desc: "Elevate academic writing — clarity, tone, and register." },
  "statistical-review":       { to: "/statistical-review",      label: "Statistical Analysis", icon: BarChart2,  cost: 25, unit: "per analysis",  desc: "Review statistical methods, assumptions, and reporting." },
  "manuscript-review":        { to: "/manuscript-review",       label: "Manuscript Review",    icon: Microscope, cost: 20, unit: "per review",   desc: "Simulated peer review with structured feedback across all sections." },
  "abstract-generator":       { to: "/ai/abstract",             label: "Abstract Generator",   icon: AlignLeft,  cost: 5,  unit: "per abstract",  desc: "Generate a structured, publication-ready abstract from your text." },
};

function AIToolCard({ toolKey }) {
  const tool = AI_TOOLS[toolKey];
  if (!tool) return null;
  const Icon = tool.icon;
  return (
    <Card to={tool.to} padding="lg" className="group">
      <div className="flex items-start justify-between gap-2 mb-3">
        <Icon size={17} strokeWidth={1.5} className="text-[#0F2847] shrink-0" />
        <span className="text-[10px] font-mono text-slate-400 shrink-0">
          {tool.cost === 0 ? "Free" : `${tool.cost} credits ${tool.unit}`}
        </span>
      </div>
      <div className="font-serif text-sm text-slate-900 group-hover:text-[#0F2847] transition-colors mb-1.5">
        {tool.label}
      </div>
      <p className="text-xs text-slate-500 leading-relaxed">{tool.desc}</p>
      <div className="mt-3 flex items-center gap-1 text-xs text-[#0F2847] opacity-0 group-hover:opacity-100 transition-opacity">
        Launch <ArrowRight size={10} strokeWidth={1.5} />
      </div>
    </Card>
  );
}

function AIEnhancementTab({ workspace, docStage }) {
  const stage = docStage || workspace?.status || "draft";
  const suggestedKeys = STAGE_AI_MAP[stage] || STAGE_AI_MAP["draft"];
  const allToolKeys = Object.keys(AI_TOOLS).filter((k) => !suggestedKeys.includes(k));

  const STAGE_LABELS = {
    idea: "Idea", outline: "Outline", draft: "Draft", in_progress: "In Progress",
    internal_review: "Internal Review", coauthor_review: "Co-author Review",
    revision: "Revision", ready_submission: "Ready to Submit",
    submitted: "Submitted", accepted: "Accepted", published: "Published", archived: "Archived",
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Stage context banner */}
      <Alert variant="info" icon={Info}>
        <div className="flex items-start gap-3">
          <div>
            <div className="text-sm font-medium text-[#0F2847]">
              Stage: <span className="font-mono">{STAGE_LABELS[stage] || stage}</span>
            </div>
            <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
              AI tools are recommended based on your document's current lifecycle stage.
              Change the stage in the Pipeline tab to get updated recommendations.
            </p>
          </div>
          <Button as={Link} to="/ai-credits" variant="outline" size="sm" className="ml-auto shrink-0">
            <Coins size={10} strokeWidth={1.5} />
            Credits
          </Button>
        </div>
      </Alert>

      {/* Suggested for current stage */}
      {suggestedKeys.length > 0 && (
        <section>
          <div className="overline mb-3 flex items-center gap-2">
            <Sparkles size={12} strokeWidth={1.5} className="text-[#0F2847]" />
            Recommended for {STAGE_LABELS[stage] || stage} stage
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {suggestedKeys.map((key) => (
              <AIToolCard key={key} toolKey={key} />
            ))}
          </div>
        </section>
      )}

      {/* All available tools */}
      {allToolKeys.length > 0 && (
        <section>
          <div className="overline mb-3">All AI tools</div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {allToolKeys.map((key) => {
              const tool = AI_TOOLS[key];
              const Icon = tool.icon;
              return (
                <Card
                  key={key}
                  to={tool.to}
                  padding="md"
                  className="flex items-center gap-3 group"
                >
                  <Icon size={14} strokeWidth={1.5} className="text-[#0F2847] shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-slate-900 group-hover:text-[#0F2847] transition-colors truncate">{tool.label}</div>
                    <div className="text-[10px] font-mono text-slate-400">{tool.cost === 0 ? "Free" : `${tool.cost} credits`}</div>
                  </div>
                  <ChevronRight size={12} strokeWidth={1.5} className="text-slate-300 shrink-0" />
                </Card>
              );
            })}
          </div>
        </section>
      )}

      {/* AI Suite link */}
      <Card padding="md" className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-slate-900">Explore the full Research AI Suite</div>
          <div className="text-xs text-slate-500 mt-0.5">All AI tools organized by category with credit costs and usage guides.</div>
        </div>
        <Button as={Link} to="/ai-suite" size="sm" className="shrink-0">
          <BrainCircuit size={12} strokeWidth={1.5} />
          Open AI Suite
        </Button>
      </Card>
    </div>
  );
}

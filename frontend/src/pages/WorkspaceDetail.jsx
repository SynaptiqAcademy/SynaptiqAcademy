import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { Avatar } from "@/components/ds/Avatar";
import { useAuth } from "../contexts/AuthContext";
import { userTypeLabel } from "../lib/userTypes";
import WorkspaceKanban from "../components/researchOS/WorkspaceKanban";
import DeadlinesWidget from "../components/ai/DeadlinesWidget";
import AssistantLauncher from "../components/ai/AssistantLauncher";
import FilePanel from "../components/files/FilePanel";
import { toast } from "sonner";
import { ResearchLayout } from "@/layouts";
import { NAVY } from "@/lib/tokens";
import { SkeletonCard } from "@/components/ds/LoadingState";
import {
  Send, MessageSquare, UserPlus, Activity, Target, FileText,
  Beaker, Users2, ShieldCheck, Trash2, Search, ChevronRight,
  BarChart2, LogOut, ArrowRightLeft,
  BrainCircuit, BookMarked, Microscope, PenLine, AlignLeft, Sparkles,
  Coins, ArrowRight, Info,
} from "lucide-react";

const TABS = [
  { key: "overview",      label: "Overview"      },
  { key: "tasks",         label: "Tasks"         },
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
    <div className="border border-slate-200 bg-white p-4">
      <div className="overline">{label}</div>
      <div className="text-2xl font-bold text-slate-900 mt-2">{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1 font-mono">{sub}</div>}
    </div>
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
    <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center px-4" onClick={onClose}>
      <div className="bg-white w-full max-w-lg border border-slate-200" onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <div>
            <div className="overline">Workspace</div>
            <h3 className="text-base font-semibold text-slate-900">Invite a researcher</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-900 text-sm">Close</button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <div className="overline mb-2">Role</div>
            <select
              data-testid={TID.workspaceInviteRole}
              value={role} onChange={(e) => setRole(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 bg-white text-sm"
            >
              {WS_ROLES.filter((r) => r !== "Owner").map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <div className="overline mb-2">Search the network</div>
            <div className="relative">
              <Search size={14} strokeWidth={1.5} className="absolute left-3 top-2.5 text-slate-400" />
              <input
                data-testid={TID.workspaceInviteSearch}
                autoFocus value={q} onChange={(e) => setQ(e.target.value)}
                placeholder="Name, institution, area, skill…"
                className="w-full pl-9 pr-3 py-2 border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
              />
            </div>
          </div>
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
      </div>
    </div>
  );
}

export default function WorkspaceDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [ws, setWs] = useState(null);
  const [dash, setDash] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [tab, setTab] = useState("overview");
  const [note, setNote] = useState("");
  const [showInvite, setShowInvite] = useState(false);
  const [showTransfer, setShowTransfer] = useState(false);
  const [transferTarget, setTransferTarget] = useState("");

  // ── Co-author state ──────────────────────────────────────────────────────────
  const [coauthorRoles, setCoauthorRoles] = useState({});   // { uid: [role strings] }
  const [coauthorOrder, setCoauthorOrder] = useState([]);   // ordered uid list
  const [correspondingAuthor, setCorrespondingAuthor] = useState(null);

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
      // Seed co-author order from members
      if (a.data?.members_info?.length && !coauthorOrder.length) {
        setCoauthorOrder(a.data.members_info.map((m) => m.id));
        if (a.data.owner_id) setCorrespondingAuthor(a.data.owner_id);
        if (a.data.doc_stage) setDocStage(a.data.doc_stage);
      }
    } catch {
      toast.error("Failed to load workspace");
    }
  }, [id, coauthorOrder.length]);

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
    if (!confirm("Remove this member from the workspace?")) return;
    try {
      await api.delete(`/workspaces/${id}/members/${uid}`);
      toast.success("Member removed"); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const leaveWorkspace = async () => {
    if (!confirm("Leave this workspace? You'll lose access unless re-invited.")) return;
    try {
      await api.post(`/workspaces/${id}/leave`);
      toast.success("You left the workspace");
      navigate("/workspaces");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const transferOwnership = async () => {
    if (!transferTarget) { toast.error("Select a member"); return; }
    if (!confirm(`Transfer ownership to ${(ws?.members_info || []).find((m) => m.id === transferTarget)?.full_name}?`)) return;
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
    <ResearchLayout>
    <div className="space-y-8">
      <header className="border-b border-slate-200 pb-6">
        <div className="flex items-start justify-between gap-6">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <div className="overline">Workspace</div>
              <span className="overline text-amber-700 border border-amber-200 bg-amber-50 px-2 py-0.5">{ws.status || "active"}</span>
              <span className="inline-flex items-center gap-1 overline text-[#0F2847] border border-[#0F2847] px-2 py-0.5" data-testid={TID.workspaceYourRole}>
                <ShieldCheck size={11} strokeWidth={1.5} /> Your role: {myRole}
              </span>
            </div>
            <h1 className="text-[1.4rem] font-semibold text-slate-900 tracking-tight mt-2 leading-snug">{ws.name}</h1>
            {ws.description && <p className="text-[13px] text-slate-500 mt-2 max-w-3xl leading-relaxed">{ws.description}</p>}
          </div>
          <div className="flex flex-col items-end gap-2 shrink-0">
            <AssistantLauncher entityKind="workspace" entityId={id} entityTitle={ws.name} />
            <button
              data-testid={TID.openChatBtn}
              onClick={() => navigate("/messages", { state: { openContext: { type: "workspace", id } } })}
              className="inline-flex items-center gap-2 text-xs border border-[#0F2847] text-[#0F2847] px-3 py-1.5 hover:bg-[#0F2847] hover:text-white transition-colors"
            >
              <MessageSquare size={12} strokeWidth={1.5} /> Open chat
            </button>
            {isAdmin && (
              <button
                data-testid={TID.workspaceInviteBtn}
                onClick={() => setShowInvite(true)}
                className="inline-flex items-center gap-2 text-xs bg-[#0F2847] text-white px-3 py-1.5 hover:bg-slate-800"
              >
                <UserPlus size={12} strokeWidth={1.5} /> Invite member
              </button>
            )}
            {myRole === "Owner" && (
              <button onClick={() => setShowTransfer(!showTransfer)} className="inline-flex items-center gap-2 text-xs border border-slate-300 text-slate-600 px-3 py-1.5 hover:bg-slate-50">
                <ArrowRightLeft size={12} strokeWidth={1.5} /> Transfer ownership
              </button>
            )}
            {myRole !== "Owner" && (
              <button onClick={leaveWorkspace} className="inline-flex items-center gap-2 text-xs border border-red-200 text-red-600 px-3 py-1.5 hover:bg-red-50">
                <LogOut size={12} strokeWidth={1.5} /> Leave workspace
              </button>
            )}
          </div>
        </div>

        {/* Transfer ownership panel */}
        {showTransfer && (
          <div className="mt-4 border border-amber-200 bg-amber-50 p-4 flex items-center gap-4">
            <div className="overline text-amber-700 shrink-0">Transfer to</div>
            <select
              value={transferTarget}
              onChange={(e) => setTransferTarget(e.target.value)}
              className="flex-1 px-2 py-1 border border-amber-300 bg-white text-sm"
            >
              <option value="">Select a member…</option>
              {(ws.members_info || []).filter((m) => m.id !== user?.id).map((m) => (
                <option key={m.id} value={m.id}>{m.full_name} ({m.workspace_role})</option>
              ))}
            </select>
            <button onClick={transferOwnership} className="bg-amber-700 text-white px-3 py-1.5 text-xs hover:bg-amber-800">Confirm</button>
            <button onClick={() => setShowTransfer(false)} className="text-sm text-slate-500 hover:text-slate-900">Cancel</button>
          </div>
        )}
      </header>

      <nav className="flex border-b border-slate-200 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.key}
            data-testid={TID.workspaceTab(t.key)}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-[13px] font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${tab === t.key ? "border-[#0F2847] text-slate-900" : "border-transparent text-slate-500 hover:text-slate-900"}`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "overview" && (
        <div className="grid lg:grid-cols-12 gap-8">
          <section className="lg:col-span-8 space-y-6">
            {/* Health + KPI grid */}
            <div className="border border-slate-200 bg-white p-6">
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
            </div>

            {/* Linked manuscripts */}
            <div data-testid={TID.workspaceLinkedManuscripts} className="border border-slate-200 bg-white p-6">
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
            </div>

            {/* Linked projects */}
            <div className="border border-slate-200 bg-white p-6">
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
            </div>
          </section>

          <aside className="lg:col-span-4 space-y-6">
            <DeadlinesWidget workspaceId={id} initialItems={dash?.upcoming_deadlines || null} />
            <div data-testid={TID.workspaceUpcomingMilestones} className="border border-slate-200 bg-white p-5">
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
            </div>
            <div className="border border-slate-200 bg-white p-5">
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
            </div>
          </aside>
        </div>
      )}

      {tab === "tasks" && (
        <WorkspaceKanban wsId={id} canEdit={WS_ADMIN_ROLES.has(myRole) || myRole === "Co-Investigator" || myRole === "Researcher"} />
      )}

      {tab === "team" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-600">{(ws.members_info || []).length} member{(ws.members_info || []).length === 1 ? "" : "s"} · Owner & PI can modify roles.</div>
            {isAdmin && (
              <button onClick={() => setShowInvite(true)} className="inline-flex items-center gap-2 text-xs border border-[#0F2847] text-[#0F2847] px-3 py-1.5 hover:bg-[#0F2847] hover:text-white">
                <UserPlus size={12} strokeWidth={1.5} /> Invite
              </button>
            )}
          </div>
          <div className="border border-slate-200 bg-white divide-y divide-slate-100">
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
                      <select
                        data-testid={TID.workspaceMemberRole(m.id)}
                        value={role}
                        onChange={(e) => changeRole(m.id, e.target.value)}
                        className="px-2 py-1 border border-slate-300 bg-white text-xs"
                      >
                        {WS_ROLES.filter((r) => r !== "Owner").map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                    ) : (
                      <span className="overline text-[#0F2847] border border-[#0F2847] px-2 py-0.5">{role}</span>
                    )}
                    {isAdmin && !isOwner && (
                      <button data-testid={TID.workspaceMemberRemove(m.id)} onClick={() => removeMember(m.id)} className="text-slate-400 hover:text-red-600 p-1" title="Remove member">
                        <Trash2 size={14} strokeWidth={1.5} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ══ AI ENHANCEMENT TAB ══════════════════════════════════════════════ */}
      {tab === "ai" && (
        <AIEnhancementTab workspace={ws} docStage={docStage} />
      )}

      {tab === "activity" && (
        <div className="max-w-3xl space-y-5">
          <div className="border border-slate-200 bg-white p-4 flex gap-3">
            <input
              data-testid={TID.workspaceNoteInput}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && postNote()}
              placeholder="Post a note to the team…"
              className="flex-1 px-3 py-2 border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
            />
            <button
              data-testid={TID.workspaceNoteSubmit}
              onClick={postNote}
              className="bg-[#0F2847] text-white px-4 py-2 text-sm hover:bg-slate-800 inline-flex items-center gap-2"
            >
              <Send size={12} strokeWidth={1.5} /> Post
            </button>
          </div>
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
            <div key={d.id} className="border border-slate-200 bg-white p-5">
              <div className="overline text-[#0F2847]">{d.type}</div>
              <h3 className="text-[13px] font-semibold text-slate-900 mt-1">{d.title}</h3>
              <p className="text-sm text-slate-600 mt-2 line-clamp-3">{d.description}</p>
            </div>
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
                <div className="border border-slate-200 bg-white p-5">
                  <div className="overline">Total activity events</div>
                  <div className="text-2xl font-bold text-slate-900 mt-2">{analytics.activity_by_day.reduce((s, d) => s + d.count, 0)}</div>
                  <div className="text-xs text-slate-500 font-mono mt-1">last {analytics.period_days} days</div>
                </div>
                <div className="border border-slate-200 bg-white p-5">
                  <div className="overline">Active contributors</div>
                  <div className="text-2xl font-bold text-slate-900 mt-2">{analytics.top_contributors.length}</div>
                  <div className="text-xs text-slate-500 font-mono mt-1">unique actors</div>
                </div>
                <div className="border border-slate-200 bg-white p-5">
                  <div className="overline">Most active day</div>
                  <div className="text-2xl font-bold text-slate-900 mt-2 truncate">
                    {analytics.activity_by_day.length > 0
                      ? analytics.activity_by_day.reduce((a, b) => a.count > b.count ? a : b).date
                      : "—"}
                  </div>
                </div>
              </div>

              <div className="border border-slate-200 bg-white p-5">
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
              </div>

              <div className="border border-slate-200 bg-white p-5">
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
              </div>
            </>
          )}
        </div>
      )}

      {/* ══ CO-AUTHORS TAB ══════════════════════════════════════════════════ */}
      {tab === "coauthors" && (
        <div className="max-w-4xl space-y-6">
          <div className="border border-slate-200 bg-white p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="overline">Author Order & Contributions</div>
                <p className="text-xs text-slate-500 mt-1">Drag to reorder. Order reflects authorship position. CRediT taxonomy roles.</p>
              </div>
              <button onClick={() => setShowInvite(true)} className="inline-flex items-center gap-2 text-xs border border-[#0F2847] text-[#0F2847] px-3 py-1.5 hover:bg-[#0F2847] hover:text-white">
                <UserPlus size={12} strokeWidth={1.5} /> Add Co-Author
              </button>
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
                          <button onClick={() => setCoauthorOrder((prev) => { const a = [...prev]; [a[idx - 1], a[idx]] = [a[idx], a[idx - 1]]; return a; })} className="text-slate-400 hover:text-slate-900 text-xs leading-none">▲</button>
                        )}
                        {idx < (ws?.members_info || []).length - 1 && (
                          <button onClick={() => setCoauthorOrder((prev) => { const a = [...prev]; [a[idx], a[idx + 1]] = [a[idx + 1], a[idx]]; return a; })} className="text-slate-400 hover:text-slate-900 text-xs leading-none">▼</button>
                        )}
                      </div>
                    </div>
                    <Link to={`/profile/${m.id}`}><Avatar url={m.avatar_url} name={m.full_name} size={40} /></Link>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-slate-900">{m.full_name}</span>
                        {isCa && <span className="overline text-[#0F2847] border border-[#0F2847] px-1.5 py-0.5">Corresponding</span>}
                        {m.orcid?.orcid_id && (
                          <a href={`https://orcid.org/${m.orcid.orcid_id}`} target="_blank" rel="noopener noreferrer" className="text-[10px] font-mono font-bold text-[#a6ce39] border border-[#a6ce3940] px-1.5 py-0.5">iD</a>
                        )}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">{m.institution}</div>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {CONTRIBUTION_ROLES.map((r) => {
                          const active = roles.includes(r);
                          return (
                            <button
                              key={r}
                              onClick={() => setCoauthorRoles((prev) => {
                                const cur = prev[m.id] || [];
                                return { ...prev, [m.id]: active ? cur.filter((x) => x !== r) : [...cur, r] };
                              })}
                              className={`text-[10px] px-1.5 py-0.5 border transition-colors ${active ? "border-[#0F2847] bg-[#0F2847] text-white" : "border-slate-200 text-slate-500 hover:border-[#0F2847]"}`}
                            >
                              {r}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                    <div className="shrink-0 flex flex-col gap-2">
                      <button
                        onClick={() => setCorrespondingAuthor(isCa ? null : m.id)}
                        className={`text-xs px-2 py-1 border transition-colors ${isCa ? "border-[#0F2847] bg-[#0F2847] text-white" : "border-slate-200 text-slate-500 hover:border-[#0F2847]"}`}
                      >
                        {isCa ? "★ Corresponding" : "Set Corresponding"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ══ PIPELINE TAB ════════════════════════════════════════════════════ */}
      {tab === "pipeline" && (
        <div className="space-y-8">
          {/* Document stage selector */}
          <div className="border border-slate-200 bg-white p-6">
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
          </div>

          {/* Publication Pipeline visual */}
          <div className="border border-slate-200 bg-white p-6">
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
          </div>

          {/* Linked manuscripts with status */}
          <div className="border border-slate-200 bg-white p-6">
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
                        <span className="text-[10px] font-semibold px-2 py-0.5 shrink-0" style={{ color: stage.color, background: stage.color + "14", border: `1px solid ${stage.color}30` }}>
                          {stage.label}
                        </span>
                      )}
                      <ChevronRight size={14} strokeWidth={1.5} className="text-slate-400 shrink-0" />
                    </Link>
                  );
                })}
              </div>
            )}
          </div>

          {/* Quick links to pipeline services */}
          <div className="border border-slate-200 bg-white p-6">
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
                <Link key={to} to={to} className="border border-slate-200 p-4 hover:border-[#0F2847] hover:bg-slate-50 transition-colors">
                  <div className="text-sm font-semibold text-slate-900">{label}</div>
                  <div className="text-xs text-slate-500 mt-1">{desc}</div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ══ REVIEWS TAB ═════════════════════════════════════════════════════ */}
      {tab === "reviews" && (
        <div className="max-w-3xl space-y-6">
          {/* Request review */}
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-3">Request Review</div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              {[
                { type: "internal",  label: "Internal Review",     desc: "Team member reviews the work" },
                { type: "coauthor",  label: "Co-author Review",    desc: "Co-author approves before submission" },
                { type: "external",  label: "External Reviewer",   desc: "Independent peer review" },
                { type: "editorial", label: "Editorial Review",    desc: "Editor decision on submission" },
              ].map((r) => (
                <button
                  key={r.type}
                  onClick={() => {
                    api.post(`/workspaces/${id}/activity`, {
                      message: `Review requested: ${r.label}`,
                      kind: "review",
                      metadata: { review_type: r.type, status: "pending" },
                    }).then(() => { toast.success(`${r.label} requested`); loadReviewsData(); }).catch(() => toast.error("Failed"));
                  }}
                  className="text-left border border-slate-200 p-3 hover:border-[#0F2847] hover:bg-slate-50 transition-colors"
                >
                  <div className="text-sm font-semibold text-slate-900">{r.label}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{r.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Review history */}
          <div className="border border-slate-200 bg-white p-5">
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
                        <button
                          onClick={() => api.patch(`/workspaces/${id}/activity/${r.id}`, { metadata: { ...r.metadata, status: "approved" } }).then(() => loadReviewsData()).catch(() => {})}
                          className="text-xs text-green-700 border border-green-300 px-2 py-0.5 hover:bg-green-50"
                        >Approve</button>
                        <button
                          onClick={() => api.patch(`/workspaces/${id}/activity/${r.id}`, { metadata: { ...r.metadata, status: "rejected" } }).then(() => loadReviewsData()).catch(() => {})}
                          className="text-xs text-red-600 border border-red-200 px-2 py-0.5 hover:bg-red-50"
                        >Reject</button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ══ COLLABORATION TAB ═══════════════════════════════════════════════ */}
      {tab === "collaboration" && (
        <div className="max-w-3xl space-y-6">
          {/* Post to collaboration center */}
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-3">Post to Collaboration Center</div>
            <div className="flex gap-2 mb-2">
              {[
                { value: "note",         label: "Note" },
                { value: "announcement", label: "Announcement" },
                { value: "decision",     label: "Decision" },
                { value: "meeting",      label: "Meeting Note" },
              ].map((k) => (
                <button
                  key={k.value}
                  onClick={() => setCollabKind(k.value)}
                  className={`text-xs px-3 py-1.5 border transition-colors ${collabKind === k.value ? "border-[#0F2847] bg-[#0F2847] text-white" : "border-slate-200 text-slate-500 hover:border-[#0F2847]"}`}
                >
                  {k.label}
                </button>
              ))}
            </div>
            <div className="flex gap-3 mt-3">
              <textarea
                value={collabNote}
                onChange={(e) => setCollabNote(e.target.value)}
                placeholder={
                  collabKind === "announcement" ? "Post an announcement to the team…" :
                  collabKind === "decision"     ? "Record a team decision…" :
                  collabKind === "meeting"      ? "Add meeting notes…" :
                  "Add a note or comment…"
                }
                rows={3}
                className="flex-1 px-3 py-2 border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847] text-sm resize-none"
              />
            </div>
            <div className="flex justify-end mt-2">
              <button
                onClick={async () => {
                  if (!collabNote.trim()) return;
                  try {
                    await api.post(`/workspaces/${id}/activity`, { message: collabNote, kind: collabKind });
                    setCollabNote(""); await loadDiscussions();
                    toast.success("Posted");
                  } catch { toast.error("Failed"); }
                }}
                className="inline-flex items-center gap-2 bg-[#0F2847] text-white px-4 py-2 text-sm hover:bg-slate-800"
              >
                <Send size={12} strokeWidth={1.5} /> Post
              </button>
            </div>
          </div>

          {/* Discussion feed */}
          <div className="border border-slate-200 bg-white p-5">
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
                        <span className="text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 border" style={{ color: "#64748B", borderColor: style.border }}>
                          {style.label}
                        </span>
                        <span className="text-xs text-slate-500 font-mono">{d.actor_name}</span>
                        <span className="text-xs text-slate-400 font-mono ml-auto">{d.created_at ? new Date(d.created_at).toLocaleString() : ""}</span>
                      </div>
                      <div className="text-sm text-slate-900">{d.message}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Quick links */}
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-3">Collaboration Tools</div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Open Chat",       to: "/messages",    desc: "Real-time team messaging" },
                { label: "Group Chat",      to: "/messages",    desc: "Workspace group channel" },
                { label: "Collaboration Requests", to: "/collaboration-requests", desc: "Manage open collaboration calls" },
                { label: "Collaboration AI", to: "/collaboration-intelligence", desc: "AI-powered team insights" },
              ].map(({ label, to, desc }) => (
                <Link key={label} to={to} className="border border-slate-200 p-3 hover:border-[#0F2847] hover:bg-slate-50 transition-colors">
                  <div className="text-sm font-semibold text-slate-900">{label}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{desc}</div>
                </Link>
              ))}
            </div>
          </div>
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
    <Link
      to={tool.to}
      className="group block border border-slate-200 bg-white p-5 hover:border-[#0F2847] transition-colors"
    >
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
    </Link>
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
      <div className="border border-[#0F2847]/20 bg-[#0F2847]/5 p-4 flex items-start gap-3">
        <Info size={15} strokeWidth={1.5} className="text-[#0F2847] mt-0.5 shrink-0" />
        <div>
          <div className="text-sm font-medium text-[#0F2847]">
            Stage: <span className="font-mono">{STAGE_LABELS[stage] || stage}</span>
          </div>
          <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
            AI tools are recommended based on your document's current lifecycle stage.
            Change the stage in the Pipeline tab to get updated recommendations.
          </p>
        </div>
        <Link to="/ai-credits" className="ml-auto shrink-0 text-xs border border-[#0F2847] text-[#0F2847] px-2 py-1 hover:bg-[#0F2847] hover:text-white inline-flex items-center gap-1">
          <Coins size={10} strokeWidth={1.5} />
          Credits
        </Link>
      </div>

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
                <Link
                  key={key}
                  to={tool.to}
                  className="flex items-center gap-3 border border-slate-200 bg-white px-4 py-3 hover:border-[#0F2847] transition-colors group"
                >
                  <Icon size={14} strokeWidth={1.5} className="text-[#0F2847] shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-slate-900 group-hover:text-[#0F2847] transition-colors truncate">{tool.label}</div>
                    <div className="text-[10px] font-mono text-slate-400">{tool.cost === 0 ? "Free" : `${tool.cost} credits`}</div>
                  </div>
                  <ChevronRight size={12} strokeWidth={1.5} className="text-slate-300 shrink-0" />
                </Link>
              );
            })}
          </div>
        </section>
      )}

      {/* AI Suite link */}
      <div className="border border-slate-200 bg-white p-5 flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-slate-900">Explore the full Research AI Suite</div>
          <div className="text-xs text-slate-500 mt-0.5">All AI tools organized by category with credit costs and usage guides.</div>
        </div>
        <Link
          to="/ai-suite"
          className="shrink-0 text-xs bg-[#0F2847] text-white px-4 py-2 hover:bg-slate-800 inline-flex items-center gap-1.5"
        >
          <BrainCircuit size={12} strokeWidth={1.5} />
          Open AI Suite
        </Link>
      </div>
    </div>
  );
}

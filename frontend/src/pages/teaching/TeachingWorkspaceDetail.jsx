import React, { useEffect, useRef, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Send, Sparkles, BookOpen, ClipboardCheck, Settings, Trash2,
  Bot, Users, Activity, Plus, UserMinus, RefreshCw,
  MessageSquare, Shield, Eye, Search, X, CheckCircle,
} from "lucide-react";
import api from "../../lib/api";
import { toast } from "sonner";
import { useAuth } from "../../contexts/AuthContext";
import { NAVY } from "@/lib/tokens";
import { EmptyState } from "../../components/ds/EmptyState";
import { Spinner, SkeletonPage } from "../../components/ds/LoadingState";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Tag } from "@/components/ds/Tag";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { NavTabs } from "@/components/ds/NavTabs";
import { List, ListItem } from "@/components/ds/List";

// ─── Role display helpers ─────────────────────────────────────────────────────

const ROLE_LABELS = {
  workspace_owner:    "Owner",
  course_lead:        "Course Lead",
  co_instructor:      "Co-Instructor",
  teaching_assistant: "Teaching Assistant",
  reviewer:           "Reviewer",
  observer:           "Observer",
};

// Maps cleanly onto the 6 fixed Badge variants — no arbitrary color needed.
const ROLE_BADGE_VARIANT = {
  workspace_owner:    "default",
  course_lead:        "success",
  co_instructor:      "info",
  teaching_assistant: "warning",
  reviewer:           "neutral",
  observer:           "outline",
};

const ACTIVITY_ICONS = {
  workspace_created:   "🏗️",
  member_joined:       "👋",
  member_invited:      "✉️",
  member_removed:      "🚪",
  role_changed:        "🔄",
  lesson_created:      "📖",
  lesson_edited:       "✏️",
  lesson_restored:     "↩️",
  assessment_created:  "📋",
  assessment_edited:   "✏️",
  assessment_restored: "↩️",
  comment_added:       "💬",
  ai_session:          "🤖",
  settings_updated:    "⚙️",
};

const INVITE_ROLES = ["course_lead", "co_instructor", "teaching_assistant", "reviewer", "observer"];

function RoleBadge({ role }) {
  return (
    <Badge variant={ROLE_BADGE_VARIANT[role] || "outline"} size="sm" className="uppercase tracking-wide shrink-0">
      {ROLE_LABELS[role] || role}
    </Badge>
  );
}

// ─── Chat bubble ─────────────────────────────────────────────────────────────

function ChatBubble({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      {!isUser && (
        <div className="w-7 h-7 bg-[#0F2847] text-white flex items-center justify-center shrink-0 mr-2 mt-0.5">
          <Bot size={13} strokeWidth={1.5} />
        </div>
      )}
      <div className={`max-w-[82%] px-4 py-3 text-sm leading-relaxed whitespace-pre-line ${
        isUser ? "bg-[#0F2847] text-white" : "bg-white border border-slate-200 text-slate-800"
      }`}>
        {msg.content}
      </div>
    </div>
  );
}

// ─── Comment thread ───────────────────────────────────────────────────────────

function CommentThread({ comments, onPost, canComment, currentUserId, onDelete }) {
  const [text, setText]     = useState("");
  const [posting, setPosting] = useState(false);

  const handlePost = async () => {
    if (!text.trim() || posting) return;
    setPosting(true);
    try {
      await onPost(text.trim());
      setText("");
    } catch (_) {
      /* toast already fired inside onPost */
    } finally {
      setPosting(false);
    }
  };

  return (
    <div className="space-y-3">
      {comments.length === 0 && (
        <div className="text-sm text-slate-400 italic py-4 text-center">No comments yet.</div>
      )}
      {comments.map((c) => (
        <Card key={c.id} padding="md">
          <div className="flex items-start justify-between gap-2">
            <div className="font-medium text-sm text-slate-900">{c.author_name}</div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-slate-400 font-mono">
                {new Date(c.created_at).toLocaleDateString()}
              </span>
              {c.author_id === currentUserId && (
                <Button variant="ghost" size="icon" onClick={() => onDelete(c.id)} className="text-slate-300 hover:text-red-400">
                  <X size={11} strokeWidth={1.5} />
                </Button>
              )}
            </div>
          </div>
          <p className="text-sm text-slate-700 mt-1 leading-relaxed">{c.content}</p>
        </Card>
      ))}
      {canComment && (
        <div className="flex gap-2 mt-2">
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handlePost(); } }}
            placeholder="Add a comment…"
            wrapperClassName="flex-1"
          />
          <Button onClick={handlePost} disabled={!text.trim() || posting}>
            <Send size={13} strokeWidth={1.5} />
          </Button>
        </div>
      )}
    </div>
  );
}

// ─── Invite panel ─────────────────────────────────────────────────────────────

function InvitePanel({ workspaceId, onInvited }) {
  const [query, setQuery]     = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [role, setRole]       = useState("co_instructor");
  const [email, setEmail]     = useState("");
  const [inviting, setInviting] = useState(null);

  const search = useCallback(async (q) => {
    if (!q.trim()) { setResults([]); return; }
    setSearching(true);
    try {
      const { data } = await api.get("/users", { params: { q, limit: 10 } });
      setResults(Array.isArray(data) ? data : (data.items || []));
    } catch (_) {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => search(query), 350);
    return () => clearTimeout(t);
  }, [query, search]);

  const inviteUser = async (userId) => {
    setInviting(userId);
    try {
      await api.post(`/teaching/workspaces/${workspaceId}/members/invite`, { user_id: userId, role });
      toast.success("Invitation sent");
      onInvited();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to send invitation");
    } finally {
      setInviting(null);
    }
  };

  const inviteByEmail = async () => {
    if (!email.trim()) return;
    setInviting("email");
    try {
      await api.post(`/teaching/workspaces/${workspaceId}/members/invite`, { email: email.trim(), role });
      toast.success("Invitation sent");
      setEmail("");
      onInvited();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to send invitation");
    } finally {
      setInviting(null);
    }
  };

  return (
    <Card variant="flush" padding="lg" className="bg-slate-50 space-y-5">
      <div className="overline">Invite Member</div>

      <FormSelect
        label="Role for new member"
        value={role}
        onChange={(e) => setRole(e.target.value)}
      >
        {INVITE_ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
      </FormSelect>

      <div>
        <Input
          label="Search platform members"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Name, institution, research area…"
          prefix={<Search size={13} strokeWidth={1.5} />}
        />
        {searching && <div className="text-xs text-slate-400 mt-1">Searching…</div>}
        {results.length > 0 && (
          <List className="mt-2 max-h-56 overflow-y-auto">
            {results.map((u) => (
              <ListItem
                key={u.id}
                title={u.full_name || "—"}
                subtitle={u.institution || u.user_type || ""}
                trailing={
                  <Button size="sm" onClick={() => inviteUser(u.id)} disabled={inviting === u.id}>
                    {inviting === u.id ? "Sending…" : "Invite"}
                  </Button>
                }
              />
            ))}
          </List>
        )}
      </div>

      <div>
        <label className="sq-form-label block mb-1.5">Or invite by email</label>
        <div className="flex gap-2">
          <Input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            placeholder="colleague@university.edu"
            wrapperClassName="flex-1"
          />
          <Button onClick={inviteByEmail} disabled={!email.trim() || inviting === "email"}>
            {inviting === "email" ? "Sending…" : "Send"}
          </Button>
        </div>
      </div>
    </Card>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

const TABS = [
  { id: "overview",    label: "Overview",     icon: BookOpen },
  { id: "members",     label: "Members",      icon: Users },
  { id: "activity",    label: "Activity",     icon: Activity },
  { id: "lessons",     label: "Lessons",      icon: BookOpen },
  { id: "assessments", label: "Assessments",  icon: ClipboardCheck },
  { id: "assistant",   label: "AI Assistant", icon: Sparkles },
  { id: "settings",    label: "Settings",     icon: Settings },
];

export default function TeachingWorkspaceDetail() {
  const { workspaceId } = useParams();
  const navigate = useNavigate();
  const { user: me } = useAuth();
  const bottomRef = useRef(null);

  const [workspace, setWorkspace]     = useState(null);
  const [messages, setMessages]       = useState([]);
  const [loading, setLoading]         = useState(true);
  const [tab, setTab]                 = useState("overview");

  const [members, setMembers]         = useState([]);
  const [showInvite, setShowInvite]   = useState(false);

  const [activity, setActivity]       = useState([]);
  const [actLoaded, setActLoaded]     = useState(false);

  const [lessons, setLessons]         = useState([]);
  const [assessments, setAssessments] = useState([]);
  const [contentLoaded, setContentLoaded] = useState(false);

  const [wsComments, setWsComments]   = useState([]);
  const [cmtsLoaded, setCmtsLoaded]   = useState(false);

  const [settingsForm, setSettingsForm] = useState({});
  const [savingSettings, setSavingSettings] = useState(false);

  const [input, setInput]             = useState("");
  const [sending, setSending]         = useState(false);

  const myRole  = workspace?.my_role || "";
  const myId    = me?.id || me?._id || "";
  const canInvite   = ["workspace_owner", "course_lead"].includes(myRole);
  const canSettings = myRole === "workspace_owner";
  const canComment  = ["workspace_owner", "course_lead", "co_instructor", "teaching_assistant", "reviewer"].includes(myRole);
  const canAI       = ["workspace_owner", "course_lead", "co_instructor", "teaching_assistant"].includes(myRole);

  // ── Load workspace + initial chat ─────────────────────────────────────────
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const [wsRes, chatRes] = await Promise.all([
          api.get(`/teaching/workspaces/${workspaceId}`),
          api.get(`/teaching/workspaces/${workspaceId}/chat`),
        ]);
        if (!mounted) return;
        setWorkspace(wsRes.data);
        setSettingsForm({
          title:       wsRes.data.title,
          course_code: wsRes.data.course_code  || "",
          description: wsRes.data.description  || "",
          subject:     wsRes.data.subject      || "",
          level:       wsRes.data.level        || "undergraduate",
          semester:    wsRes.data.semester     || "",
          status:      wsRes.data.status       || "active",
        });
        setMessages(chatRes.data || []);
        setMembers(wsRes.data.members_info || []);
      } catch (_) {
        toast.error("Workspace not found");
        navigate("/teaching/workspaces");
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, [workspaceId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Auto-scroll chat ──────────────────────────────────────────────────────
  useEffect(() => {
    if (tab === "assistant") bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, tab]);

  // ── Lazy-load activity ────────────────────────────────────────────────────
  useEffect(() => {
    if (tab !== "activity" || actLoaded) return;
    api.get(`/teaching/workspaces/${workspaceId}/activity`)
      .then(({ data }) => { setActivity(data || []); setActLoaded(true); })
      .catch(() => toast.error("Failed to load activity"));
  }, [tab, actLoaded, workspaceId]);

  // ── Lazy-load lessons + assessments ───────────────────────────────────────
  useEffect(() => {
    if ((tab !== "lessons" && tab !== "assessments") || contentLoaded || !workspace) return;
    (async () => {
      try {
        const linkedL = new Set(workspace.linked_lesson_ids || []);
        const linkedA = new Set(workspace.linked_assessment_ids || []);
        const [lRes, aRes] = await Promise.all([
          api.get("/teaching/lessons"),
          api.get("/teaching/assessments"),
        ]);
        setLessons((lRes.data || []).filter((l) => linkedL.has(l.id)));
        setAssessments((aRes.data || []).filter((a) => linkedA.has(a.id)));
        setContentLoaded(true);
      } catch (_) {
        toast.error("Failed to load content");
      }
    })();
  }, [tab, contentLoaded, workspace]);

  // ── Lazy-load workspace comments ──────────────────────────────────────────
  useEffect(() => {
    if (tab !== "overview" || cmtsLoaded) return;
    api.get(`/teaching/workspaces/${workspaceId}/comments`)
      .then(({ data }) => { setWsComments(data || []); setCmtsLoaded(true); })
      .catch(() => {});
  }, [tab, cmtsLoaded, workspaceId]);

  // ── Send AI message ───────────────────────────────────────────────────────
  const sendMessage = async () => {
    const content = input.trim();
    if (!content || sending || !canAI) return;
    setInput("");
    setSending(true);
    const userMsg = { role: "user", content, id: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    try {
      const { data } = await api.post(`/teaching/workspaces/${workspaceId}/chat`, { content });
      setMessages((prev) => [...prev, { role: "assistant", content: data.content, id: Date.now() + 1 }]);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to send");
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
      setInput(content);
    } finally {
      setSending(false);
    }
  };

  // ── Change member role ────────────────────────────────────────────────────
  const changeMemberRole = async (memberId, newRole) => {
    try {
      await api.patch(`/teaching/workspaces/${workspaceId}/members/${memberId}/role`, { role: newRole });
      setMembers((prev) => prev.map((m) => m.id === memberId ? { ...m, role: newRole } : m));
      toast.success("Role updated");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to change role");
    }
  };

  // ── Remove member ─────────────────────────────────────────────────────────
  const removeMember = async (memberId, isLeave = false) => {
    const memberName = members.find((m) => m.id === memberId)?.full_name || "this member";
    const confirmMsg = isLeave
      ? "Leave this workspace? You will lose access unless re-invited."
      : `Remove ${memberName} from this workspace?`;
    if (!window.confirm(confirmMsg)) return;
    try {
      await api.delete(`/teaching/workspaces/${workspaceId}/members/${memberId}`);
      if (isLeave) {
        navigate("/teaching/workspaces");
        return;
      }
      setMembers((prev) => prev.filter((m) => m.id !== memberId));
      toast.success("Member removed");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    }
  };

  // ── Save settings ─────────────────────────────────────────────────────────
  const saveSettings = async () => {
    setSavingSettings(true);
    try {
      const { data } = await api.patch(`/teaching/workspaces/${workspaceId}`, settingsForm);
      setWorkspace((prev) => ({ ...prev, ...data }));
      toast.success("Settings saved");
    } catch (_) {
      toast.error("Failed to save settings");
    } finally {
      setSavingSettings(false);
    }
  };

  // ── Delete workspace ──────────────────────────────────────────────────────
  const handleDelete = async () => {
    if (!window.confirm("Delete this workspace and all its data? This cannot be undone.")) return;
    try {
      await api.delete(`/teaching/workspaces/${workspaceId}`);
      toast.success("Workspace deleted");
      navigate("/teaching/workspaces");
    } catch (_) {
      toast.error("Failed to delete workspace");
    }
  };

  // ── Post workspace comment ────────────────────────────────────────────────
  const postWsComment = async (content) => {
    const { data } = await api.post(`/teaching/workspaces/${workspaceId}/comments`, { content });
    setWsComments((prev) => [...prev, data]);
  };

  const deleteComment = async (commentId) => {
    try {
      await api.delete(`/teaching/comments/${commentId}`);
      setWsComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch (_) {
      toast.error("Failed to delete comment");
    }
  };

  // ── Guard ─────────────────────────────────────────────────────────────────
  if (loading) return <div className="p-6"><SkeletonPage cards={3} /></div>;
  if (!workspace) return null;

  const STARTER_PROMPTS = [
    "What teaching strategies work well for this course?",
    "Suggest active learning activities for my next class.",
    "How can I differentiate instruction for mixed-ability groups?",
    "Help me write learning objectives aligned to Bloom's Taxonomy.",
    "What formative assessment techniques would you recommend?",
  ];

  return (
    <div className="space-y-0">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <header className="border-b border-slate-200 pb-4">
        <Link to="/teaching/workspaces" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-[#0F2847] mb-3">
          <ArrowLeft size={12} strokeWidth={1.5} /> Teaching Workspaces
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="font-serif text-2xl text-slate-900">{workspace.title}</h1>
              <RoleBadge role={myRole} />
            </div>
            <div className="flex items-center gap-2 mt-1 text-xs text-slate-500 flex-wrap">
              {workspace.course_code && <span className="font-mono">{workspace.course_code}</span>}
              {workspace.subject && <><span className="text-slate-300">·</span><span>{workspace.subject}</span></>}
              {workspace.level && <><span className="text-slate-300">·</span><span>{workspace.level}</span></>}
              {workspace.semester && <><span className="text-slate-300">·</span><span>{workspace.semester}</span></>}
              <span className="text-slate-300">·</span>
              <span className="flex items-center gap-1">
                <Users size={10} strokeWidth={1.5} />{members.length} member{members.length !== 1 ? "s" : ""}
              </span>
            </div>
          </div>
          <Badge variant={workspace.status === "active" ? "success" : "neutral"} size="sm" className="shrink-0">
            {workspace.status}
          </Badge>
        </div>

        {/* Tab bar */}
        <NavTabs
          className="mt-5 overflow-x-auto scrollbar-none"
          tabs={TABS.filter(({ id }) => id !== "settings" || canSettings).map(({ id, label, icon }) => ({ id, label, icon }))}
          active={tab}
          onChange={setTab}
        />
      </header>

      {/* ── Overview tab ──────────────────────────────────────────────────── */}
      {tab === "overview" && (
        <div className="grid lg:grid-cols-3 gap-8 pt-6">
          <div className="lg:col-span-2 space-y-6">
            {workspace.description && (
              <div>
                <div className="overline mb-2">About</div>
                <p className="text-sm text-slate-700 leading-relaxed">{workspace.description}</p>
              </div>
            )}

            {(workspace.teaching_objectives || []).length > 0 && (
              <div>
                <div className="overline mb-2">Teaching Objectives</div>
                <ul className="space-y-1.5">
                  {workspace.teaching_objectives.map((o, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                      <CheckCircle size={13} strokeWidth={1.5} className="text-emerald-500 mt-0.5 shrink-0" />
                      {o}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="grid sm:grid-cols-3 gap-4">
              {[
                { label: "Lessons", value: (workspace.linked_lesson_ids || []).length, targetTab: "lessons" },
                { label: "Assessments", value: (workspace.linked_assessment_ids || []).length, targetTab: "assessments" },
                { label: "Members", value: members.length, targetTab: "members" },
              ].map(({ label, value, targetTab }) => (
                <Card key={label} padding="md" onClick={() => setTab(targetTab)} className="text-left">
                  <div className="overline text-slate-500 mb-1">{label}</div>
                  <div className="font-serif text-3xl text-slate-900">{value}</div>
                </Card>
              ))}
            </div>

            <div>
              <div className="overline mb-3">Workspace Discussion</div>
              <CommentThread
                comments={wsComments}
                onPost={postWsComment}
                canComment={canComment}
                currentUserId={myId}
                onDelete={deleteComment}
              />
            </div>
          </div>

          <aside className="space-y-6">
            <div>
              <div className="overline mb-3">Recent Activity</div>
              <div className="space-y-2">
                {actLoaded && activity.length === 0 && (
                  <div className="text-xs text-slate-400 italic">No activity yet.</div>
                )}
                {(actLoaded ? activity : []).slice(0, 5).map((a) => (
                  <div key={a.id} className="flex items-start gap-2 text-xs text-slate-600">
                    <span className="shrink-0 mt-0.5">{ACTIVITY_ICONS[a.kind] || "📌"}</span>
                    <div>
                      <span className="font-medium text-slate-700">{a.actor_name}</span>{" "}{a.message}
                    </div>
                  </div>
                ))}
                <Button variant="link" size="sm" onClick={() => setTab("activity")}>
                  View all activity →
                </Button>
              </div>
            </div>

            <div>
              <div className="overline mb-3">Team</div>
              <div className="space-y-2">
                {members.slice(0, 6).map((m) => (
                  <div key={m.id} className="flex items-center justify-between gap-2">
                    <div className="text-sm text-slate-900 truncate">{m.full_name || "—"}</div>
                    <RoleBadge role={m.role} />
                  </div>
                ))}
                {members.length > 6 && (
                  <Button variant="link" size="sm" onClick={() => setTab("members")}>
                    +{members.length - 6} more →
                  </Button>
                )}
              </div>
            </div>
          </aside>
        </div>
      )}

      {/* ── Members tab ───────────────────────────────────────────────────── */}
      {tab === "members" && (
        <div className="pt-6 space-y-6">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div className="overline">Workspace Members</div>
              <p className="text-sm text-slate-500 mt-0.5">{members.length} member{members.length !== 1 ? "s" : ""}</p>
            </div>
            {canInvite && (
              <Button
                variant={showInvite ? "primary" : "outline"}
                onClick={() => setShowInvite(!showInvite)}
              >
                <Plus size={14} strokeWidth={1.5} /> Invite member
              </Button>
            )}
          </div>

          {showInvite && (
            <InvitePanel
              workspaceId={workspaceId}
              onInvited={() => {
                setShowInvite(false);
                api.get(`/teaching/workspaces/${workspaceId}/members`)
                  .then(({ data }) => setMembers(data))
                  .catch(() => {});
              }}
            />
          )}

          <List className="divide-y divide-slate-100">
            {members.map((m) => {
              const isMe    = m.id === myId;
              const isOwner = m.role === "workspace_owner";
              return (
                <div key={m.id} className="px-5 py-4 flex items-center gap-4">
                  <div className="w-9 h-9 bg-slate-200 flex items-center justify-center shrink-0 text-sm font-medium text-slate-600">
                    {(m.full_name || "?").charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-900 truncate">
                      {m.full_name || "—"}
                      {isMe && <span className="text-slate-400 font-normal ml-1">(you)</span>}
                    </div>
                    <div className="text-xs text-slate-500 truncate">{m.institution || m.user_type || ""}</div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    {myRole === "workspace_owner" && !isOwner ? (
                      <FormSelect
                        size="sm"
                        value={m.role}
                        onChange={(e) => changeMemberRole(m.id, e.target.value)}
                        className="!w-auto"
                      >
                        {INVITE_ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                      </FormSelect>
                    ) : (
                      <RoleBadge role={m.role} />
                    )}
                    {canInvite && !isOwner && !isMe && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeMember(m.id)}
                        title="Remove member"
                        className="text-slate-300 hover:text-red-500"
                      >
                        <UserMinus size={14} strokeWidth={1.5} />
                      </Button>
                    )}
                    {isMe && !isOwner && (
                      <Button
                        variant="link"
                        size="sm"
                        onClick={() => removeMember(m.id, true)}
                        className="text-slate-400 hover:text-red-500"
                      >
                        Leave
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </List>

          {/* Role legend */}
          <Card variant="flush" padding="lg" className="bg-slate-50">
            <div className="overline mb-3">Permission Guide</div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                { role: "workspace_owner",    perms: "Full control · delete workspace · manage all roles" },
                { role: "course_lead",         perms: "Manage lessons, assessments, members (except owner)" },
                { role: "co_instructor",       perms: "Create and edit lessons and assessments · planning" },
                { role: "teaching_assistant",  perms: "Contribute materials · comment · use AI assistant" },
                { role: "reviewer",            perms: "Review content · comment only" },
                { role: "observer",            perms: "Read-only access to all content" },
              ].map(({ role, perms }) => (
                <div key={role} className="flex flex-col gap-1.5">
                  <RoleBadge role={role} />
                  <p className="text-[11px] text-slate-500 leading-relaxed">{perms}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* ── Activity tab ──────────────────────────────────────────────────── */}
      {tab === "activity" && (
        <div className="pt-6">
          <div className="flex items-center justify-between mb-5">
            <div className="overline">Activity Feed</div>
            <Button variant="link" size="sm" onClick={() => { setActLoaded(false); }}>
              <RefreshCw size={11} strokeWidth={1.5} /> Refresh
            </Button>
          </div>
          <List className="divide-y divide-slate-100">
            {activity.length === 0 && (
              <div className="px-6 py-10 text-sm text-slate-400 text-center italic">No activity yet.</div>
            )}
            {activity.map((a) => (
              <div key={a.id} className="px-5 py-4 flex items-start gap-3">
                <span className="text-base shrink-0 mt-0.5">{ACTIVITY_ICONS[a.kind] || "📌"}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-800">
                    <strong className="font-medium">{a.actor_name}</strong>{" "}{a.message}
                  </div>
                  {a.entity_type && (
                    <div className="text-xs text-slate-400 mt-0.5 capitalize">{a.entity_type}</div>
                  )}
                </div>
                <div className="text-[10px] text-slate-400 font-mono shrink-0 whitespace-nowrap">
                  {new Date(a.created_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
            ))}
          </List>
        </div>
      )}

      {/* ── Lessons tab ───────────────────────────────────────────────────── */}
      {tab === "lessons" && (
        <div className="pt-6 space-y-5">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="overline">Linked Lessons ({(workspace.linked_lesson_ids || []).length})</div>
            {["workspace_owner", "course_lead", "co_instructor"].includes(myRole) && (
              <Button as={Link} to="/teaching/lesson-planner" variant="outline">
                <Plus size={14} strokeWidth={1.5} /> New lesson
              </Button>
            )}
          </div>
          {!contentLoaded && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Spinner size={14} /> Loading…
            </div>
          )}
          {contentLoaded && lessons.length === 0 && (
            <EmptyState
              icon={<BookOpen />}
              title="No lessons linked yet"
              description="No lessons linked to this workspace yet."
              action={
                <Link to="/teaching/lesson-planner" className="text-sm text-[#0F2847] hover:underline">
                  Go to Lesson Planner →
                </Link>
              }
              size="sm"
            />
          )}
          {contentLoaded && lessons.length > 0 && (
            <div className="space-y-3">
              {lessons.map((l) => (
                <Card key={l.id} padding="lg" className="hover:border-[#0F2847]">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <Link to={`/teaching/lessons/${l.id}`} className="font-serif text-lg text-slate-900 hover:text-[#0F2847]">
                        {l.title}
                      </Link>
                      <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                        {l.subject && <span>{l.subject}</span>}
                        {l.level && <><span className="text-slate-300">·</span><span>{l.level}</span></>}
                        {l.duration_minutes && <><span className="text-slate-300">·</span><span>{l.duration_minutes} min</span></>}
                      </div>
                    </div>
                    <Badge variant={l.status === "published" ? "success" : "neutral"} size="sm" className="shrink-0">
                      {l.status}
                    </Badge>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Assessments tab ───────────────────────────────────────────────── */}
      {tab === "assessments" && (
        <div className="pt-6 space-y-5">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="overline">Linked Assessments ({(workspace.linked_assessment_ids || []).length})</div>
            {["workspace_owner", "course_lead", "co_instructor"].includes(myRole) && (
              <Button as={Link} to="/teaching/assessment-builder" variant="outline">
                <Plus size={14} strokeWidth={1.5} /> New assessment
              </Button>
            )}
          </div>
          {!contentLoaded && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Spinner size={14} /> Loading…
            </div>
          )}
          {contentLoaded && assessments.length === 0 && (
            <EmptyState
              icon={<ClipboardCheck />}
              title="No assessments linked yet"
              description="No assessments linked to this workspace yet."
              action={
                <Link to="/teaching/assessment-builder" className="text-sm text-[#0F2847] hover:underline">
                  Go to Assessment Builder →
                </Link>
              }
              size="sm"
            />
          )}
          {contentLoaded && assessments.length > 0 && (
            <div className="space-y-3">
              {assessments.map((a) => (
                <Card key={a.id} padding="lg" className="hover:border-[#0F2847]">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <Link to={`/teaching/assessments/${a.id}`} className="font-serif text-lg text-slate-900 hover:text-[#0F2847]">
                        {a.title}
                      </Link>
                      <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                        {a.subject && <span>{a.subject}</span>}
                        {a.assessment_type && <><span className="text-slate-300">·</span><span>{a.assessment_type}</span></>}
                        {a.total_marks && <><span className="text-slate-300">·</span><span>{a.total_marks} marks</span></>}
                      </div>
                    </div>
                    <Badge variant={a.status === "published" ? "success" : "neutral"} size="sm" className="shrink-0">
                      {a.status}
                    </Badge>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── AI Assistant tab ──────────────────────────────────────────────── */}
      {tab === "assistant" && (
        <div className="flex flex-col" style={{ height: "calc(100vh - 20rem)" }}>
          {!canAI ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Eye size={32} strokeWidth={1} className="text-slate-300 mx-auto mb-3" />
                <div className="text-sm text-slate-500">AI assistant requires Teaching Assistant role or above.</div>
              </div>
            </div>
          ) : (
            <>
              <div className="border-b border-slate-100 bg-slate-50 px-4 py-2 shrink-0">
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <Bot size={11} strokeWidth={1.5} className="text-[#0F2847]" />
                  <span>AI Teaching Assistant · workspace-aware · {members.length} team members · 2 credits/message</span>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto px-4 py-4">
                {messages.length === 0 && (
                  <div className="py-6 text-center">
                    <div className="w-10 h-10 bg-[#0F2847] text-white flex items-center justify-center mx-auto mb-4">
                      <Bot size={20} strokeWidth={1.5} />
                    </div>
                    <div className="font-serif text-lg text-slate-900 mb-1">AI Teaching Assistant</div>
                    <p className="text-sm text-slate-500 max-w-md mx-auto mb-6">
                      I know this course — {workspace.title}{workspace.subject ? ` (${workspace.subject})` : ""}
                      {members.length > 1 ? ` — and I know your ${members.length}-person team` : ""}. Ask me anything.
                    </p>
                    <div className="flex flex-wrap gap-2 justify-center">
                      {STARTER_PROMPTS.map((p) => (
                        <Tag key={p} onClick={() => setInput(p)}>
                          {p}
                        </Tag>
                      ))}
                    </div>
                  </div>
                )}
                {messages.map((msg, i) => <ChatBubble key={msg.id || i} msg={msg} />)}
                {sending && (
                  <div className="flex justify-start mb-3">
                    <div className="w-7 h-7 bg-[#0F2847] text-white flex items-center justify-center shrink-0 mr-2 mt-0.5">
                      <Bot size={13} strokeWidth={1.5} />
                    </div>
                    <div className="bg-white border border-slate-200 px-4 py-3">
                      <div className="flex gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>

              <div className="border-t border-slate-200 p-4 shrink-0 bg-white">
                <div className="flex gap-2">
                  <Textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                    placeholder="Ask about teaching strategies, activities, assessment design…"
                    rows={2}
                    resize={false}
                    wrapperClassName="flex-1"
                  />
                  <Button
                    onClick={sendMessage}
                    disabled={!input.trim() || sending}
                    size="icon"
                    className="self-stretch h-auto"
                  >
                    <Send size={15} strokeWidth={1.5} />
                  </Button>
                </div>
                <div className="text-[10px] text-slate-400 mt-1.5">Enter to send · Shift+Enter for newline</div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Settings tab ──────────────────────────────────────────────────── */}
      {tab === "settings" && canSettings && (
        <div className="pt-6 space-y-8 max-w-2xl">
          <section>
            <div className="overline mb-4">Workspace Settings</div>
            <div className="grid sm:grid-cols-2 gap-4">
              <Input
                label="Course title *"
                value={settingsForm.title || ""}
                onChange={(e) => setSettingsForm({ ...settingsForm, title: e.target.value })}
                wrapperClassName="sm:col-span-2"
              />
              <Input
                label="Course code"
                value={settingsForm.course_code || ""}
                onChange={(e) => setSettingsForm({ ...settingsForm, course_code: e.target.value })}
                placeholder="e.g. ECON 101"
              />
              <Input
                label="Semester / term"
                value={settingsForm.semester || ""}
                onChange={(e) => setSettingsForm({ ...settingsForm, semester: e.target.value })}
                placeholder="e.g. Fall 2025"
              />
              <Input
                label="Subject"
                value={settingsForm.subject || ""}
                onChange={(e) => setSettingsForm({ ...settingsForm, subject: e.target.value })}
              />
              <FormSelect
                label="Status"
                value={settingsForm.status || "active"}
                onChange={(e) => setSettingsForm({ ...settingsForm, status: e.target.value })}
              >
                <option value="active">Active</option>
                <option value="archived">Archived</option>
              </FormSelect>
              <Textarea
                label="Description"
                rows={3}
                value={settingsForm.description || ""}
                onChange={(e) => setSettingsForm({ ...settingsForm, description: e.target.value })}
                resize={false}
                wrapperClassName="sm:col-span-2"
              />
            </div>
            <div className="mt-4">
              <Button onClick={saveSettings} loading={savingSettings}>
                {savingSettings ? "Saving…" : "Save changes"}
              </Button>
            </div>
          </section>

          <Card variant="flush" padding="lg" className="border-red-200 bg-red-50">
            <div className="flex items-center gap-2 mb-2">
              <Shield size={14} strokeWidth={1.5} className="text-red-500" />
              <div className="overline text-red-700">Danger Zone</div>
            </div>
            <p className="text-xs text-red-600 mb-4">
              Deleting this workspace permanently removes all activity, comments, and invitations.
              Lessons and assessments remain in your Teaching Hub. This cannot be undone.
            </p>
            <Button variant="danger" onClick={handleDelete}>
              <Trash2 size={13} strokeWidth={1.5} />
              Delete workspace
            </Button>
          </Card>
        </div>
      )}
    </div>
  );
}

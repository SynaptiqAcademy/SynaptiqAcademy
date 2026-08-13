/* eslint-disable */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FolderOpen, Plus, BookOpen, ClipboardCheck, Users, Layers } from "lucide-react";
import api from "../../lib/api";
import { toast } from "sonner";
import { EmptyState } from "../../components/ds/EmptyState";
import { Spinner } from "../../components/ds/LoadingState";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { ResearchLayout } from "@/layouts";
import { NAVY } from "@/lib/tokens";

const SUBJECTS = ["Mathematics","Economics","Management","Computer Science","Medicine","Engineering","Psychology","Education","Sciences","Humanities","Law","Business","History","Literature","Physics","Chemistry","Biology","Other"];
const LEVELS   = ["secondary","undergraduate","graduate","professional","adult","other"];

export default function TeachingWorkspace() {
  const navigate = useNavigate();
  const [workspaces, setWorkspaces] = useState([]);
  const [loading, setLoading]       = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [pendingInvites, setPendingInvites] = useState([]);
  const [form, setForm]             = useState({
    title: "", course_code: "", description: "", subject: "", level: "undergraduate", semester: "",
  });
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [wsRes, invRes] = await Promise.all([
        api.get("/teaching/workspaces"),
        api.get("/teaching/workspace-invitations").catch(() => ({ data: [] })),
      ]);
      setWorkspaces(wsRes.data || []);
      setPendingInvites(invRes.data || []);
    } catch (_) {
      toast.error("Failed to load workspaces");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const acceptInvite = async (invId) => {
    try {
      await api.post(`/teaching/workspace-invitations/${invId}/accept`);
      toast.success("Joined workspace");
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to accept invitation");
    }
  };

  const declineInvite = async (invId) => {
    try {
      await api.post(`/teaching/workspace-invitations/${invId}/decline`);
      setPendingInvites((prev) => prev.filter((i) => i.id !== invId));
    } catch (_) {
      toast.error("Failed to decline invitation");
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.title) return;
    setCreating(true);
    try {
      const { data } = await api.post("/teaching/workspaces", form);
      toast.success("Workspace created");
      navigate(`/teaching/workspaces/${data.id}`);
    } catch (_) {
      toast.error("Failed to create workspace");
    } finally {
      setCreating(false);
    }
  };

  const activeCount    = workspaces.filter((ws) => ws.status === "active").length;
  const totalLessons   = workspaces.reduce((s, ws) => s + (ws.linked_lesson_ids || []).length, 0);
  const totalAssessments = workspaces.reduce((s, ws) => s + (ws.linked_assessment_ids || []).length, 0);

  return (
    <ResearchLayout
      title="Teaching Workspaces"
      subtitle="Course-level workspaces where you can organize lesson plans, assessments, and get support from the AI Teaching Assistant."
      icon={<FolderOpen size={15} strokeWidth={1.5} style={{ color: "#0F2847" }} />}
      stats={!loading ? [
        { label: "Workspaces",   value: workspaces.length },
        { label: "Active",       value: activeCount },
        { label: "Lessons",      value: totalLessons },
        { label: "Assessments",  value: totalAssessments },
      ] : undefined}
      sidebar={!loading && workspaces.length > 0 ? <TeachingWorkspaceSidebar workspaces={workspaces} /> : undefined}
      actions={
        <Button
          variant="hero"
          onClick={() => setShowCreate(!showCreate)}
        >
          <Plus size={14} strokeWidth={1.5} /> New workspace
        </Button>
      }
    >

      {/* Create form */}
      {showCreate && (
        <Card variant="flush" padding="lg">
          <div className="overline mb-4">New teaching workspace</div>
          <form onSubmit={handleCreate} className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Input
              label="Course title *"
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="e.g. Introduction to Microeconomics"
              wrapperClassName="sm:col-span-2"
            />
            <Input
              label="Course code"
              value={form.course_code}
              onChange={(e) => setForm({ ...form, course_code: e.target.value })}
              placeholder="e.g. ECON 101"
            />
            <FormSelect
              label="Subject"
              value={form.subject}
              onChange={(e) => setForm({ ...form, subject: e.target.value })}
            >
              <option value="">Not specified</option>
              {SUBJECTS.map((s) => <option key={s}>{s}</option>)}
            </FormSelect>
            <FormSelect
              label="Level"
              value={form.level}
              onChange={(e) => setForm({ ...form, level: e.target.value })}
            >
              {LEVELS.map((l) => <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>)}
            </FormSelect>
            <Input
              label="Semester / term"
              value={form.semester}
              onChange={(e) => setForm({ ...form, semester: e.target.value })}
              placeholder="e.g. Fall 2025"
            />
            <Textarea
              label="Description"
              rows={2}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Brief description of the course or module"
              wrapperClassName="lg:col-span-3"
            />
            <div className="lg:col-span-3 flex gap-3">
              <Button type="submit" loading={creating}>
                {creating ? "Creating…" : "Create workspace"}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}

      {/* Pending invitations */}
      {pendingInvites.length > 0 && (
        <div className="space-y-3">
          <div className="overline">Workspace Invitations ({pendingInvites.length})</div>
          {pendingInvites.map((inv) => (
            <Card key={inv.id} variant="flush" padding="md" className="border-[#0F2847]/20 bg-[#0F2847]/5 flex items-center justify-between gap-4 flex-wrap">
              <div>
                <div className="text-sm font-medium text-slate-900">{inv.workspace_title}</div>
                <div className="text-xs text-slate-500 mt-0.5">
                  Invited by {inv.inviter_name} · as{" "}
                  <span className="font-medium">{inv.role?.replace(/_/g, " ")}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Button size="sm" onClick={() => acceptInvite(inv.id)}>
                  Accept
                </Button>
                <Button size="sm" variant="ghost" onClick={() => declineInvite(inv.id)}>
                  Decline
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Workspace list */}
      {loading && (
        <div className="flex items-center gap-2 text-sm text-slate-400 py-8">
          <Spinner size={14} /> Loading…
        </div>
      )}

      {!loading && workspaces.length === 0 && (
        <EmptyState
          icon={<FolderOpen />}
          title="No teaching workspaces yet"
          description="Create a workspace for each course or teaching module. Link lesson plans and assessments, and get real-time support from the AI Teaching Assistant."
          action={
            <Button onClick={() => setShowCreate(true)}>
              Create first workspace
            </Button>
          }
        />
      )}

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {workspaces.map((ws) => (
          <Card key={ws.id} to={`/teaching/workspaces/${ws.id}`} padding="lg">
            <div className="flex items-start justify-between gap-2 mb-1">
              <h3 className="font-serif text-lg text-slate-900 leading-snug line-clamp-2">{ws.title}</h3>
              <Badge variant={ws.status === "active" ? "success" : "neutral"} size="sm" className="shrink-0">
                {ws.status}
              </Badge>
            </div>
            {ws.course_code && <div className="text-xs text-slate-400 font-mono mb-2">{ws.course_code}</div>}
            <div className="flex items-center gap-3 text-xs text-slate-500 mb-3">
              {ws.subject && <span>{ws.subject}</span>}
              {ws.level && <><span className="text-slate-300">·</span><span>{ws.level}</span></>}
              {ws.semester && <><span className="text-slate-300">·</span><span>{ws.semester}</span></>}
            </div>
            {ws.description && <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">{ws.description}</p>}
            <div className="mt-4 pt-4 border-t border-slate-100 flex items-center gap-4 text-xs text-slate-400 flex-wrap">
              <span className="flex items-center gap-1"><BookOpen size={10} strokeWidth={1.5} />{(ws.linked_lesson_ids || []).length} lessons</span>
              <span className="flex items-center gap-1"><ClipboardCheck size={10} strokeWidth={1.5} />{(ws.linked_assessment_ids || []).length} assessments</span>
              <span className="flex items-center gap-1"><Users size={10} strokeWidth={1.5} />{ws.member_count || 1} member{(ws.member_count || 1) !== 1 ? "s" : ""}</span>
              {ws.my_role && ws.my_role !== "workspace_owner" && (
                <Badge variant="neutral" size="sm" className="capitalize">
                  {ws.my_role.replace("_", " ")}
                </Badge>
              )}
            </div>
          </Card>
        ))}
      </div>
    </ResearchLayout>
  );
}

// ── Right rail — subject breakdown + average team size, real data already loaded above ──
function TeachingWorkspaceSidebar({ workspaces }) {
  const bySubject = new Map();
  workspaces.forEach((ws) => {
    if (!ws.subject) return;
    bySubject.set(ws.subject, (bySubject.get(ws.subject) || 0) + 1);
  });
  const topSubjects = Array.from(bySubject.entries()).sort((a, b) => b[1] - a[1]).slice(0, 4);

  const avgMembers = workspaces.length > 0
    ? Math.round((workspaces.reduce((s, ws) => s + (ws.member_count || 1), 0) / workspaces.length) * 10) / 10
    : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
          <Layers size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>By Subject</div>
        </div>
        {topSubjects.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {topSubjects.map(([subject, count]) => (
              <div key={subject} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <span style={{ fontSize: 12.5, color: "#374151", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{subject}</span>
                <span style={{ fontSize: 11, color: "#94A3B8", fontFamily: "monospace", flexShrink: 0 }}>{count}</span>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>
            Subjects will appear here as you add workspaces.
          </p>
        )}
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Users size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Average Team Size</div>
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 28, fontWeight: 700, color: "#0f172a" }}>
          {avgMembers}
        </div>
        <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0", lineHeight: 1.5 }}>
          Members per workspace, across {workspaces.length}.
        </p>
      </Card>
    </div>
  );
}

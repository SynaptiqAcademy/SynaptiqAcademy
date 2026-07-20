/**
 * MeetingDetail — full meeting view: overview, agenda, files, discussion,
 * action items, AI summary, recording, and activity timeline.
 */
import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft, Video, MapPin, Clock, Users, Pencil, Trash2, Pin, PinOff,
  Sparkles, Send, Plus, FileText, PlayCircle, ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ds/Button";
import { Badge } from "@/components/ds/Badge";
import { NavTabs } from "@/components/ds/NavTabs";
import { AvatarGroup } from "@/components/ds/AvatarGroup";
import { Textarea } from "@/components/ds/Textarea";
import { Dialog } from "@/components/ds/Modal";
import { SkeletonPage } from "@/components/ds/LoadingState";
import { ErrorState } from "@/components/ds/ErrorState";
import { EmptyState } from "@/components/ds/EmptyState";
import { AIResponsePanel } from "@/components/ds/AIComponents";
import { ResearchLayout } from "@/layouts";
import { WARM, TYPE, BRD, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, NAVY } from "@/lib/tokens";
import {
  useMeetingDetail, updateMeeting, deleteMeeting, addMeetingNote,
  addActionItem, updateActionItem, runMeetingAI,
} from "@/hooks/useMeetings";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "agenda", label: "Agenda" },
  { id: "files", label: "Files" },
  { id: "discussion", label: "Discussion" },
  { id: "tasks", label: "Tasks" },
  { id: "ai", label: "AI Summary" },
  { id: "recording", label: "Recording" },
  { id: "timeline", label: "Timeline" },
];

function fmt(iso) {
  try { return new Date(iso).toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); }
  catch { return iso; }
}

export default function MeetingDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tab, setTab] = useState("overview");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: meeting, loading, error, reload, setData } = useMeetingDetail(id);

  const togglePin = async () => {
    const next = !meeting.pinned;
    setData((m) => ({ ...m, pinned: next }));
    try { await updateMeeting(id, { pinned: next }); } catch { reload(); }
  };

  const handleDelete = async () => {
    try {
      await deleteMeeting(id);
      toast.success("Meeting deleted");
      navigate("/meetings");
    } catch {
      toast.error("Could not delete the meeting");
    }
  };

  if (loading) return <div style={{ background: WARM, minHeight: "100vh", padding: 24 }}><SkeletonPage cards={3} /></div>;
  if (error || !meeting) {
    return (
      <div style={{ background: WARM, minHeight: "100vh", padding: 24 }}>
        <ErrorState message="Could not load this meeting" onRetry={reload} />
      </div>
    );
  }

  const headerActions = (
    <div style={{ display: "flex", gap: 8 }}>
      <Button variant="ghost" size="sm" onClick={togglePin}>
        {meeting.pinned ? <PinOff size={13} /> : <Pin size={13} />} {meeting.pinned ? "Unpin" : "Pin"}
      </Button>
      {meeting.video_link && (
        <Button size="sm" onClick={() => window.open(meeting.video_link, "_blank", "noopener,noreferrer")}>
          <Video size={13} /> Join
        </Button>
      )}
      <Button variant="ghost" size="sm" onClick={() => setConfirmDelete(true)}>
        <Trash2 size={13} /> Delete
      </Button>
    </div>
  );

  return (
    <ResearchLayout
      title={
        <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
          {meeting.title}
          <Badge variant={meeting.status === "completed" ? "success" : meeting.status === "cancelled" ? "neutral" : "info"} dot>
            {meeting.status}
          </Badge>
        </span>
      }
      subtitle={meeting.meeting_type}
      actions={headerActions}
      nav={<NavTabs tabs={TABS} active={tab} onChange={setTab} />}
    >
        <Button variant="ghost" size="sm" onClick={() => navigate("/meetings")} className="mb-4">
          <ArrowLeft size={13} /> Back to Meetings
        </Button>

        {/* Meta strip */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 20, padding: "14px 18px", background: "#fff", border: `1px solid ${BRD}`, borderRadius: 8, marginBottom: 20, fontSize: 12.5, color: TEXT_SECONDARY }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <Clock size={13} /> {fmt(meeting.start_at)} — {fmt(meeting.end_at)} ({meeting.timezone})
          </span>
          {meeting.location && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><MapPin size={13} /> {meeting.location}</span>
          )}
          {meeting.workspace_name && <span>Workspace: {meeting.workspace_name}</span>}
          {meeting.project_title && <span>Project: {meeting.project_title}</span>}
        </div>

        {meeting.participants?.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
            <AvatarGroup users={meeting.participants.map((p) => ({ name: p.full_name, avatar: p.avatar_url }))} max={6} size="sm" />
            <span style={{ fontSize: 12, color: TEXT_MUTED }}>{meeting.participants.length} participants</span>
          </div>
        )}

        <div style={{ marginTop: 20 }}>
          {tab === "overview" && <OverviewTab meeting={meeting} />}
          {tab === "agenda" && <AgendaTab meeting={meeting} />}
          {tab === "files" && <FilesTab meeting={meeting} />}
          {tab === "discussion" && <DiscussionTab meeting={meeting} onNoteAdded={reload} />}
          {tab === "tasks" && <TasksTab meeting={meeting} onChanged={reload} />}
          {tab === "ai" && <AITab meeting={meeting} onGenerated={reload} />}
          {tab === "recording" && <RecordingTab meeting={meeting} />}
          {tab === "timeline" && <TimelineTab meeting={meeting} />}
        </div>

      <Dialog
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={handleDelete}
        title="Delete this meeting?"
        description="This permanently removes the meeting, its notes, action items and AI summary."
        variant="destructive"
        confirmLabel="Delete"
      />
    </ResearchLayout>
  );
}

function OverviewTab({ meeting }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <div style={{ ...TYPE.section, marginBottom: 8 }}>Description</div>
        <p style={{ ...TYPE.body, margin: 0, whiteSpace: "pre-wrap" }}>{meeting.description || "No description provided."}</p>
      </div>
      {meeting.tags?.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {meeting.tags.map((t) => <Badge key={t} variant="neutral" size="sm">{t}</Badge>)}
        </div>
      )}
    </div>
  );
}

function AgendaTab({ meeting }) {
  if (!meeting.agenda?.length) {
    return <EmptyState icon={<FileText />} title="No agenda set" description="This meeting doesn't have an agenda yet." />;
  }
  return (
    <ol style={{ margin: 0, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 8 }}>
      {meeting.agenda.map((item, i) => (
        <li key={i} style={{ ...TYPE.body }}>{item}</li>
      ))}
    </ol>
  );
}

function FilesTab({ meeting }) {
  const files = meeting.files || [];
  const links = meeting.attachment_links || [];
  if (!files.length && !links.length) {
    return <EmptyState icon={<FileText />} title="No files yet" description="Attachments and linked files for this meeting will appear here." />;
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {files.map((f) => (
        <a key={f.id} href={f.url} target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", border: `1px solid ${BRD}`, borderRadius: 6, textDecoration: "none", color: TEXT_PRIMARY, fontSize: 13 }}>
          <FileText size={14} /> {f.title}
        </a>
      ))}
      {links.map((url, i) => (
        <a key={i} href={url} target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", border: `1px solid ${BRD}`, borderRadius: 6, textDecoration: "none", color: TEXT_PRIMARY, fontSize: 13 }}>
          <ExternalLink size={14} /> {url}
        </a>
      ))}
    </div>
  );
}

function DiscussionTab({ meeting, onNoteAdded }) {
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const notes = (meeting.notes || []).filter((n) => n.kind === "note");

  const submit = async () => {
    if (!body.trim()) return;
    setSubmitting(true);
    try {
      await addMeetingNote(meeting.id, body.trim());
      setBody("");
      onNoteAdded?.();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", gap: 8 }}>
        <Textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder="Add a discussion note…" rows={2} style={{ flex: 1 }} />
        <Button onClick={submit} disabled={!body.trim()} loading={submitting}><Send size={13} /></Button>
      </div>
      {notes.length === 0 ? (
        <EmptyState title="No discussion yet" description="Notes added during or after the meeting will show up here." />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {notes.map((n) => (
            <div key={n.id} style={{ padding: "10px 14px", border: `1px solid ${BRD}`, borderRadius: 6, background: "#fff" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: TEXT_PRIMARY }}>{n.actor_name}</span>
                <span style={{ fontSize: 11, color: TEXT_MUTED }}>{fmt(n.created_at)}</span>
              </div>
              <p style={{ fontSize: 13, color: TEXT_SECONDARY, margin: 0, whiteSpace: "pre-wrap" }}>{n.body}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const PRIORITY_VARIANT = { high: "danger", medium: "warning", low: "neutral" };

function TasksTab({ meeting, onChanged }) {
  const [title, setTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const items = meeting.action_items || [];

  const submit = async () => {
    if (!title.trim()) return;
    setSubmitting(true);
    try {
      await addActionItem(meeting.id, { title: title.trim() });
      setTitle("");
      onChanged?.();
    } finally {
      setSubmitting(false);
    }
  };

  const toggle = async (item) => {
    await updateActionItem(item.id, { status: item.status === "done" ? "open" : "done" });
    onChanged?.();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="Add an action item…"
          style={{ flex: 1, height: 34, border: `1px solid ${BRD}`, borderRadius: 6, padding: "0 10px", fontSize: 13, outline: "none" }}
        />
        <Button onClick={submit} disabled={!title.trim()} loading={submitting}><Plus size={13} /></Button>
      </div>
      {items.length === 0 ? (
        <EmptyState title="No action items" description="Add items manually, or generate them from the AI Summary tab." />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {items.map((item) => (
            <div key={item.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", border: `1px solid ${BRD}`, borderRadius: 6, background: "#fff" }}>
              <input type="checkbox" checked={item.status === "done"} onChange={() => toggle(item)} />
              <span style={{ flex: 1, fontSize: 13, textDecoration: item.status === "done" ? "line-through" : "none", opacity: item.status === "done" ? 0.55 : 1 }}>{item.title}</span>
              <Badge variant={PRIORITY_VARIANT[item.priority] || "neutral"} size="sm">{item.priority}</Badge>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const AI_ACTIONS = [
  { kind: "summary", label: "Generate summary" },
  { kind: "agenda", label: "Generate agenda" },
  { kind: "actionItems", label: "Extract action items" },
  { kind: "decisions", label: "Extract decisions" },
  { kind: "followUpEmail", label: "Follow-up email" },
  { kind: "nextSteps", label: "Research next steps" },
];

function AITab({ meeting, onGenerated }) {
  const [running, setRunning] = useState(null);
  const [result, setResult] = useState(null);

  const run = async (kind) => {
    setRunning(kind);
    setResult(null);
    try {
      const res = await runMeetingAI(meeting.id, kind);
      setResult(res);
      if (kind === "summary") onGenerated?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "AI request failed");
    } finally {
      setRunning(null);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {meeting.ai_summary && (
        <div style={{ padding: "14px 16px", border: `1px solid ${BRD}`, borderRadius: 8, background: "#fff" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Sparkles size={13} style={{ color: NAVY }} />
            <span style={{ fontSize: 12, fontWeight: 700, color: TEXT_PRIMARY }}>Latest AI Summary</span>
          </div>
          <p style={{ fontSize: 13, color: TEXT_SECONDARY, whiteSpace: "pre-wrap", margin: 0 }}>{meeting.ai_summary.summary_text}</p>
        </div>
      )}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {AI_ACTIONS.map((a) => (
          <Button key={a.kind} size="sm" variant="ghost" onClick={() => run(a.kind)} loading={running === a.kind}>
            <Sparkles size={12} /> {a.label}
          </Button>
        ))}
      </div>

      {result && (
        <AIResponsePanel source="anthropic">
          <p style={{ fontSize: 13, color: TEXT_SECONDARY, whiteSpace: "pre-wrap", margin: 0 }}>{result.text}</p>
        </AIResponsePanel>
      )}
    </div>
  );
}

function RecordingTab({ meeting }) {
  return (
    <EmptyState
      icon={<PlayCircle />}
      title="No recording linked"
      description="Once a recording is uploaded or linked for this meeting, it will appear here for playback."
    />
  );
}

function TimelineTab({ meeting }) {
  const events = (meeting.notes || []).filter((n) => n.kind !== "note");
  if (!events.length) {
    return <EmptyState title="No activity yet" description="Updates to this meeting will be logged here." />;
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {events.map((e) => (
        <div key={e.id} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: NAVY, marginTop: 6, flexShrink: 0 }} />
          <div>
            <p style={{ fontSize: 13, color: TEXT_PRIMARY, margin: 0 }}>{e.body}</p>
            <span style={{ fontSize: 11, color: TEXT_MUTED }}>{fmt(e.created_at)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

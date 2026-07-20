import React, { useState, useEffect, useMemo } from "react";
import { Modal } from "@/components/ds/Modal";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { FormField, FormGroup, FormRow, Switch } from "@/components/ds/Form";
import { Avatar } from "@/components/ds/Avatar";
import { X } from "lucide-react";
import { TEXT_MUTED, BRD, NAVY } from "@/lib/tokens";
import api from "@/lib/api";
import { createMeeting } from "@/hooks/useMeetings";
import { toast } from "sonner";

const MEETING_TYPES = [
  "Research Meeting", "PhD Supervision", "Project Meeting", "Grant Meeting",
  "Peer Review Meeting", "Institution Meeting", "Conference Preparation",
  "Journal Submission Meeting",
];

const RECURRENCE_OPTIONS = [
  { value: "none", label: "Does not repeat" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "biweekly", label: "Every 2 weeks" },
  { value: "monthly", label: "Monthly" },
];

const TIMEZONES = Intl.supportedValuesOf ? Intl.supportedValuesOf("timeZone") : ["UTC"];

function toLocalInputValue(d) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/**
 * CreateMeetingModal — modern create/quick-create modal for a new meeting.
 */
export function CreateMeetingModal({ open, onClose, onCreated, defaultType, defaultWorkspaceId, defaultProjectId, defaultDate }) {
  const now = useMemo(() => {
    if (defaultDate) {
      const d = new Date(defaultDate);
      const withTime = new Date();
      d.setHours(withTime.getHours(), withTime.getMinutes(), 0, 0);
      return d;
    }
    return new Date();
  }, [open, defaultDate]);
  const inHour = useMemo(() => new Date(now.getTime() + 60 * 60 * 1000), [now]);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [meetingType, setMeetingType] = useState(defaultType || "Research Meeting");
  const [startAt, setStartAt] = useState(toLocalInputValue(now));
  const [endAt, setEndAt] = useState(toLocalInputValue(inHour));
  const [timezone, setTimezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC");
  const [location, setLocation] = useState("");
  const [videoLink, setVideoLink] = useState("");
  const [agenda, setAgenda] = useState("");
  const [attachmentLinks, setAttachmentLinks] = useState("");
  const [isRecurring, setIsRecurring] = useState(false);
  const [recurrenceRule, setRecurrenceRule] = useState("weekly");
  const [reminderMinutes, setReminderMinutes] = useState(15);
  const [aiSummaryEnabled, setAiSummaryEnabled] = useState(true);
  const [workspaceId, setWorkspaceId] = useState(defaultWorkspaceId || "");
  const [projectId, setProjectId] = useState(defaultProjectId || "");
  const [workspaces, setWorkspaces] = useState([]);
  const [projects, setProjects] = useState([]);

  const [participantQuery, setParticipantQuery] = useState("");
  const [participantResults, setParticipantResults] = useState([]);
  const [participants, setParticipants] = useState([]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setMeetingType(defaultType || "Research Meeting");
    setWorkspaceId(defaultWorkspaceId || "");
    setProjectId(defaultProjectId || "");
    setStartAt(toLocalInputValue(now));
    setEndAt(toLocalInputValue(inHour));
    api.get("/workspaces").then((r) => setWorkspaces(r.data || [])).catch(() => setWorkspaces([]));
    api.get("/projects").then((r) => setProjects(r.data || [])).catch(() => setProjects([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, defaultType, defaultWorkspaceId, defaultProjectId, defaultDate]);

  useEffect(() => {
    if (!participantQuery.trim()) { setParticipantResults([]); return; }
    const t = setTimeout(() => {
      api.get("/users", { params: { q: participantQuery, limit: 8 } })
        .then((r) => setParticipantResults(r.data || []))
        .catch(() => setParticipantResults([]));
    }, 250);
    return () => clearTimeout(t);
  }, [participantQuery]);

  if (!open) return null;

  const addParticipant = (u) => {
    if (!participants.some((p) => p.id === u.id)) setParticipants([...participants, u]);
    setParticipantQuery("");
    setParticipantResults([]);
  };
  const removeParticipant = (id) => setParticipants(participants.filter((p) => p.id !== id));

  const handleSubmit = async () => {
    setError("");
    if (!title.trim()) { setError("Title is required."); return; }
    if (new Date(endAt) <= new Date(startAt)) { setError("End time must be after start time."); return; }

    setSubmitting(true);
    try {
      const payload = {
        title: title.trim(),
        description,
        meeting_type: meetingType,
        start_at: new Date(startAt).toISOString(),
        end_at: new Date(endAt).toISOString(),
        timezone,
        participant_ids: participants.map((p) => p.id),
        workspace_id: workspaceId,
        project_id: projectId,
        location,
        video_link: videoLink,
        agenda: agenda.split("\n").map((l) => l.trim()).filter(Boolean),
        attachment_links: attachmentLinks.split("\n").map((l) => l.trim()).filter(Boolean),
        is_recurring: isRecurring,
        recurrence_rule: isRecurring ? recurrenceRule : "none",
        reminder_minutes: reminderMinutes,
        ai_summary_enabled: aiSummaryEnabled,
      };
      const created = await createMeeting(payload);
      toast.success("Meeting scheduled");
      onCreated?.(created);
      onClose?.();
    } catch (e) {
      setError(e?.response?.data?.detail?.message || e?.response?.data?.detail || "Could not create the meeting. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New Meeting"
      description="Schedule a research meeting, supervision session, or review."
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>Cancel</Button>
          <Button onClick={handleSubmit} loading={submitting}>Create meeting</Button>
        </>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {error && (
          <div style={{ fontSize: 12.5, color: "#DC2626", background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: 6, padding: "8px 12px" }}>
            {error}
          </div>
        )}

        <FormGroup>
          <FormField label="Title" required>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Weekly supervision check-in" autoFocus />
          </FormField>
          <FormField label="Description">
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} placeholder="What is this meeting about?" />
          </FormField>
          <FormRow cols={2}>
            <FormField label="Meeting type">
              <FormSelect value={meetingType} onChange={(e) => setMeetingType(e.target.value)}>
                {MEETING_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </FormSelect>
            </FormField>
            <FormField label="Timezone">
              <FormSelect value={timezone} onChange={(e) => setTimezone(e.target.value)}>
                {TIMEZONES.slice(0, 300).map((tz) => <option key={tz} value={tz}>{tz}</option>)}
              </FormSelect>
            </FormField>
          </FormRow>
        </FormGroup>

        <FormGroup title="When" divided>
          <FormRow cols={2}>
            <FormField label="Start" required>
              <Input type="datetime-local" value={startAt} onChange={(e) => setStartAt(e.target.value)} />
            </FormField>
            <FormField label="End" required>
              <Input type="datetime-local" value={endAt} onChange={(e) => setEndAt(e.target.value)} />
            </FormField>
          </FormRow>
          <Switch checked={isRecurring} onChange={setIsRecurring} label="Recurring meeting" hint="Creates up to 12 future occurrences" />
          {isRecurring && (
            <FormField label="Repeats">
              <FormSelect value={recurrenceRule} onChange={(e) => setRecurrenceRule(e.target.value)}>
                {RECURRENCE_OPTIONS.filter((o) => o.value !== "none").map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </FormSelect>
            </FormField>
          )}
          <FormField label="Reminder" hint="Minutes before the meeting starts">
            <FormSelect value={reminderMinutes} onChange={(e) => setReminderMinutes(Number(e.target.value))}>
              {[5, 10, 15, 30, 60].map((m) => <option key={m} value={m}>{m} minutes before</option>)}
            </FormSelect>
          </FormField>
        </FormGroup>

        <FormGroup title="Participants" divided>
          <div style={{ position: "relative" }}>
            <Input
              value={participantQuery}
              onChange={(e) => setParticipantQuery(e.target.value)}
              placeholder="Search researchers by name…"
            />
            {participantResults.length > 0 && (
              <div style={{
                position: "absolute", top: "100%", left: 0, right: 0, zIndex: 20,
                background: "#fff", border: `1px solid ${BRD}`, borderRadius: 6,
                boxShadow: "0 8px 24px rgba(15,23,42,0.12)", marginTop: 4, maxHeight: 220, overflowY: "auto",
              }}>
                {participantResults.map((u) => (
                  <div
                    key={u.id}
                    onClick={() => addParticipant(u)}
                    style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", cursor: "pointer" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "#F8FAFC")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <Avatar url={u.avatar_url} name={u.full_name} size={24} />
                    <div>
                      <div style={{ fontSize: 12.5, fontWeight: 600 }}>{u.full_name}</div>
                      <div style={{ fontSize: 11, color: TEXT_MUTED }}>{u.institution}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          {participants.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {participants.map((p) => (
                <span key={p.id} style={{
                  display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12,
                  background: "rgba(15,40,71,0.06)", border: `1px solid ${BRD}`, borderRadius: 999,
                  padding: "3px 6px 3px 10px",
                }}>
                  {p.full_name}
                  <button onClick={() => removeParticipant(p.id)} style={{ background: "none", border: "none", cursor: "pointer", display: "flex", color: TEXT_MUTED }}>
                    <X size={11} />
                  </button>
                </span>
              ))}
            </div>
          )}
        </FormGroup>

        <FormGroup title="Context" divided>
          <FormRow cols={2}>
            <FormField label="Workspace">
              <FormSelect value={workspaceId} onChange={(e) => setWorkspaceId(e.target.value)}>
                <option value="">None</option>
                {workspaces.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
              </FormSelect>
            </FormField>
            <FormField label="Project">
              <FormSelect value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                <option value="">None</option>
                {projects.map((p) => <option key={p.id} value={p.id}>{p.title || p.name}</option>)}
              </FormSelect>
            </FormField>
          </FormRow>
          <FormRow cols={2}>
            <FormField label="Location">
              <Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Room / building (optional)" />
            </FormField>
            <FormField label="Video link">
              <Input value={videoLink} onChange={(e) => setVideoLink(e.target.value)} placeholder="Google Meet / Zoom URL" />
            </FormField>
          </FormRow>
        </FormGroup>

        <FormGroup title="Agenda & attachments" divided>
          <FormField label="Agenda" hint="One item per line">
            <Textarea value={agenda} onChange={(e) => setAgenda(e.target.value)} rows={3} placeholder={"Review manuscript draft\nDiscuss next experiment\nPlan submission timeline"} />
          </FormField>
          <FormField label="Attachment links" hint="Paste one link per line">
            <Textarea value={attachmentLinks} onChange={(e) => setAttachmentLinks(e.target.value)} rows={2} placeholder="https://…" />
          </FormField>
          <Switch checked={aiSummaryEnabled} onChange={setAiSummaryEnabled} label="AI Summary" hint="Automatically offer to generate a summary and action items after this meeting" />
        </FormGroup>
      </div>
    </Modal>
  );
}

export default CreateMeetingModal;

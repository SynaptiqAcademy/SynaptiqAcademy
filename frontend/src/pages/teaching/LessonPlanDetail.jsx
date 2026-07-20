import React, { useEffect, useState, useRef } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Sparkles, Download, Edit2, Check, X, Trash2, Plus } from "lucide-react";
import api from "../../lib/api";
import { toast } from "sonner";
import { NAVY } from "@/lib/tokens";
import { SkeletonPage } from "../../components/ds/LoadingState";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { NavTabs } from "@/components/ds/NavTabs";
import { ResearchLayout } from "@/layouts";

const SUBJECTS = ["Mathematics","Economics","Management","Computer Science","Medicine","Engineering","Psychology","Education","Sciences","Humanities","Law","Business","History","Literature","Physics","Chemistry","Biology","Sociology","Political Science","Philosophy"];
const LEVELS   = ["secondary","undergraduate","graduate","professional","adult","other"];

function Section({ title, children }) {
  return (
    <div className="border-t border-slate-200 pt-6">
      <div className="overline mb-3">{title}</div>
      {children}
    </div>
  );
}

function PhaseRow({ phase, index, onChange, onDelete }) {
  return (
    <Card padding="md" className="space-y-2">
      <div className="grid sm:grid-cols-4 gap-2">
        <Input value={phase.phase} onChange={(e) => onChange(index, "phase", e.target.value)}
          placeholder="Phase name" />
        <Input type="number" min={1} max={240} value={phase.duration_minutes}
          onChange={(e) => onChange(index, "duration_minutes", parseInt(e.target.value) || 5)}
          placeholder="Min" />
        <div className="sm:col-span-2 flex gap-2">
          <Input value={phase.activity} onChange={(e) => onChange(index, "activity", e.target.value)}
            placeholder="Activity description"
            wrapperClassName="flex-1" />
          <Button type="button" variant="ghost" size="icon" onClick={() => onDelete(index)} className="text-slate-400 hover:text-red-500">
            <X size={14} strokeWidth={1.5} />
          </Button>
        </div>
      </div>
      {phase.notes && (
        <Textarea value={phase.notes} onChange={(e) => onChange(index, "notes", e.target.value)}
          rows={2} placeholder="Teacher notes for this phase" />
      )}
      {!phase.notes && (
        <Button type="button" variant="link" size="sm" onClick={() => onChange(index, "notes", " ")}>
          + Add notes
        </Button>
      )}
    </Card>
  );
}

export default function LessonPlanDetail() {
  const { lessonId } = useParams();
  const navigate     = useNavigate();
  const [lesson, setLesson]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft]     = useState(null);
  const [tab, setTab]         = useState("overview");

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await api.get(`/teaching/lessons/${lessonId}`);
        setLesson(data);
        setDraft(data);
      } catch (_) {
        toast.error("Lesson not found");
        navigate("/teaching/lesson-planner");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [lessonId]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    if (!draft) return;
    setSaving(true);
    try {
      const { data } = await api.patch(`/teaching/lessons/${lessonId}`, draft);
      setLesson(data);
      setDraft(data);
      setEditing(false);
      toast.success("Lesson saved");
    } catch (_) {
      toast.error("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Delete this lesson plan? This cannot be undone.")) return;
    try {
      await api.delete(`/teaching/lessons/${lessonId}`);
      toast.success("Lesson deleted");
      navigate("/teaching/lesson-planner");
    } catch (_) {
      toast.error("Failed to delete");
    }
  };

  const handlePhaseChange = (index, field, value) => {
    const outline = [...(draft.outline || [])];
    outline[index] = { ...outline[index], [field]: value };
    setDraft({ ...draft, outline });
  };

  const addPhase = () => {
    const outline = [...(draft.outline || []), { phase: "New Phase", duration_minutes: 10, activity: "", notes: "" }];
    setDraft({ ...draft, outline });
  };

  const deletePhase = (index) => {
    const outline = (draft.outline || []).filter((_, i) => i !== index);
    setDraft({ ...draft, outline });
  };

  const toggleListItem = (field, index, value) => {
    const arr = [...(draft[field] || [])];
    arr[index] = value;
    setDraft({ ...draft, [field]: arr });
  };

  const addListItem = (field) => {
    setDraft({ ...draft, [field]: [...(draft[field] || []), ""] });
  };

  const removeListItem = (field, index) => {
    const arr = (draft[field] || []).filter((_, i) => i !== index);
    setDraft({ ...draft, [field]: arr });
  };

  const exportAsText = () => {
    if (!lesson) return;
    const lines = [
      `LESSON PLAN: ${lesson.title}`,
      `${"=".repeat(60)}`,
      `Subject: ${lesson.subject}   Level: ${lesson.level || "N/A"}   Duration: ${lesson.duration_minutes} min`,
      `Audience: ${lesson.audience || "N/A"}`,
      "",
      "LEARNING OBJECTIVES",
      "-".repeat(40),
      ...(lesson.learning_objectives || []).map((o, i) => `${i + 1}. ${o}`),
      "",
      "MATERIALS",
      "-".repeat(40),
      ...(lesson.materials || []).map((m) => `• ${m}`),
      "",
      "LESSON OUTLINE",
      "-".repeat(40),
      ...(lesson.outline || []).map((p) =>
        `[${p.phase} — ${p.duration_minutes} min]\n${p.activity}${p.notes ? `\nNotes: ${p.notes}` : ""}`
      ),
      "",
      "ASSESSMENT STRATEGY",
      "-".repeat(40),
      lesson.assessment_strategy || "N/A",
      "",
      "DIFFERENTIATION STRATEGIES",
      "-".repeat(40),
      ...(lesson.differentiation_strategies || []).map((s) => `• ${s}`),
      "",
      "TEACHER NOTES",
      "-".repeat(40),
      lesson.teacher_notes || "N/A",
      "",
      `Generated by SYNAPTIQ Teaching Hub — ${new Date().toLocaleDateString()}`,
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `lesson-plan-${lesson.title.replace(/\s+/g, "-").toLowerCase()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <div className="p-6"><SkeletonPage cards={2} /></div>;
  if (!lesson) return null;

  const d = editing ? draft : lesson;
  const totalDuration = (d.outline || []).reduce((s, p) => s + (p.duration_minutes || 0), 0);

  return (
    <ResearchLayout>
    <div className="max-w-4xl space-y-8">
      {/* Header */}
      <header className="border-b border-slate-200 pb-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            {editing
              ? <input value={d.title} onChange={(e) => setDraft({ ...d, title: e.target.value })}
                  className="w-full font-serif text-3xl text-slate-900 border-b border-slate-300 focus:outline-none focus:border-[#0F2847] bg-transparent pb-1" />
              : <h1 className="font-serif text-3xl text-slate-900">{d.title}</h1>
            }
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              <span className="text-sm text-slate-500">{d.subject}</span>
              <span className="text-slate-300">·</span>
              <span className="text-sm text-slate-500">{d.duration_minutes} min</span>
              {d.level && <><span className="text-slate-300">·</span><span className="text-sm text-slate-500">{d.level}</span></>}
              {d.ai_generated && (
                <span className="inline-flex items-center gap-1 text-[10px] text-[#0F2847]/60">
                  <Sparkles size={9} strokeWidth={1.5} /> AI-generated
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {editing ? (
              <>
                <Button onClick={save} loading={saving}>
                  <Check size={14} strokeWidth={1.5} />{saving ? "Saving…" : "Save"}
                </Button>
                <Button variant="ghost" onClick={() => { setDraft(lesson); setEditing(false); }}>
                  Cancel
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" size="sm" onClick={exportAsText} title="Export as text">
                  <Download size={13} strokeWidth={1.5} /> Export
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
                  <Edit2 size={13} strokeWidth={1.5} /> Edit
                </Button>
                <Button variant="ghost" size="icon" onClick={handleDelete} title="Delete lesson" className="text-slate-400 hover:text-red-500">
                  <Trash2 size={15} strokeWidth={1.5} />
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Tabs */}
        <NavTabs
          className="mt-6 -mb-6"
          tabs={["overview", "outline", "assessment"].map((t) => ({ id: t, label: t.charAt(0).toUpperCase() + t.slice(1) }))}
          active={tab}
          onChange={setTab}
        />
      </header>

      {/* Overview tab */}
      {tab === "overview" && (
        <div className="space-y-6">
          {editing && (
            <div className="grid sm:grid-cols-3 gap-4">
              <FormSelect
                label="Subject"
                value={d.subject}
                onChange={(e) => setDraft({ ...d, subject: e.target.value })}
              >
                {SUBJECTS.map((s) => <option key={s}>{s}</option>)}
              </FormSelect>
              <FormSelect
                label="Level"
                value={d.level || ""}
                onChange={(e) => setDraft({ ...d, level: e.target.value })}
              >
                <option value="">Not specified</option>
                {LEVELS.map((l) => <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>)}
              </FormSelect>
              <Input
                label="Duration (minutes)"
                type="number"
                min={5}
                max={480}
                value={d.duration_minutes}
                onChange={(e) => setDraft({ ...d, duration_minutes: parseInt(e.target.value) || 60 })}
              />
              <Input
                label="Audience"
                value={d.audience || ""}
                onChange={(e) => setDraft({ ...d, audience: e.target.value })}
                placeholder="Who are the learners?"
                wrapperClassName="sm:col-span-2"
              />
              <FormSelect
                label="Status"
                value={d.status}
                onChange={(e) => setDraft({ ...d, status: e.target.value })}
              >
                <option value="draft">Draft</option>
                <option value="published">Published</option>
              </FormSelect>
            </div>
          )}

          <Section title="Learning objectives">
            <ol className="space-y-2">
              {(d.learning_objectives || []).map((obj, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="font-mono text-xs text-[#0F2847] mt-1 shrink-0">{String(i + 1).padStart(2, "0")}</span>
                  {editing
                    ? <Input value={obj} onChange={(e) => toggleListItem("learning_objectives", i, e.target.value)}
                        wrapperClassName="flex-1" />
                    : <span className="text-sm text-slate-700 leading-relaxed">{obj}</span>
                  }
                  {editing && (
                    <Button variant="ghost" size="icon" onClick={() => removeListItem("learning_objectives", i)} className="text-slate-300 hover:text-red-400 shrink-0">
                      <X size={12} strokeWidth={1.5} />
                    </Button>
                  )}
                </li>
              ))}
            </ol>
            {editing && (
              <Button variant="link" size="sm" onClick={() => addListItem("learning_objectives")} className="mt-3">
                <Plus size={11} strokeWidth={1.5} /> Add objective
              </Button>
            )}
            {!editing && (d.learning_objectives || []).length === 0 && (
              <p className="text-sm text-slate-400 italic">No learning objectives specified.</p>
            )}
          </Section>

          <Section title="Materials">
            <ul className="space-y-1.5">
              {(d.materials || []).map((m, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-[#0F2847] shrink-0" />
                  {editing
                    ? <Input value={m} onChange={(e) => toggleListItem("materials", i, e.target.value)}
                        wrapperClassName="flex-1" />
                    : <span className="text-sm text-slate-700">{m}</span>
                  }
                  {editing && (
                    <Button variant="ghost" size="icon" onClick={() => removeListItem("materials", i)} className="text-slate-300 hover:text-red-400 shrink-0">
                      <X size={12} strokeWidth={1.5} />
                    </Button>
                  )}
                </li>
              ))}
            </ul>
            {editing && (
              <Button variant="link" size="sm" onClick={() => addListItem("materials")} className="mt-3">
                <Plus size={11} strokeWidth={1.5} /> Add material
              </Button>
            )}
          </Section>

          <Section title="Differentiation strategies">
            <ul className="space-y-1.5">
              {(d.differentiation_strategies || []).map((s, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="w-1 h-1 rounded-full bg-[#0F2847] shrink-0 mt-2" />
                  {editing
                    ? <Input value={s} onChange={(e) => toggleListItem("differentiation_strategies", i, e.target.value)}
                        wrapperClassName="flex-1" />
                    : <span className="text-sm text-slate-700 leading-relaxed">{s}</span>
                  }
                  {editing && (
                    <Button variant="ghost" size="icon" onClick={() => removeListItem("differentiation_strategies", i)} className="text-slate-300 hover:text-red-400 shrink-0">
                      <X size={12} strokeWidth={1.5} />
                    </Button>
                  )}
                </li>
              ))}
            </ul>
            {editing && (
              <Button variant="link" size="sm" onClick={() => addListItem("differentiation_strategies")} className="mt-3">
                <Plus size={11} strokeWidth={1.5} /> Add strategy
              </Button>
            )}
          </Section>

          {(d.teacher_notes || editing) && (
            <Section title="Teacher notes">
              {editing
                ? <Textarea value={d.teacher_notes || ""} onChange={(e) => setDraft({ ...d, teacher_notes: e.target.value })}
                    rows={4} resize={false} />
                : <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">{d.teacher_notes}</p>
              }
            </Section>
          )}
        </div>
      )}

      {/* Outline tab */}
      {tab === "outline" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-500">
              Total time: <strong className={totalDuration !== d.duration_minutes ? "text-amber-600" : "text-emerald-600"}>{totalDuration} min</strong>
              {totalDuration !== d.duration_minutes && <span className="ml-1 text-amber-600">(target: {d.duration_minutes} min)</span>}
            </div>
            {editing && (
              <Button variant="outline" size="sm" onClick={addPhase}>
                <Plus size={11} strokeWidth={1.5} /> Add phase
              </Button>
            )}
          </div>
          {(d.outline || []).length === 0 && (
            <div className="text-sm text-slate-400 italic py-8 text-center">No lesson outline yet. {editing ? "Add phases above." : "Enable editing to add phases."}</div>
          )}
          <div className="space-y-3">
            {editing
              ? (d.outline || []).map((phase, i) => (
                  <PhaseRow key={i} phase={phase} index={i} onChange={handlePhaseChange} onDelete={deletePhase} />
                ))
              : (d.outline || []).map((phase, i) => (
                  <Card key={i} padding="md">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm text-slate-900">{phase.phase}</span>
                      <span className="text-xs text-slate-500 font-mono">{phase.duration_minutes} min</span>
                    </div>
                    <p className="text-sm text-slate-700 leading-relaxed">{phase.activity}</p>
                    {phase.notes && (
                      <p className="mt-2 text-xs text-slate-500 italic leading-relaxed">{phase.notes}</p>
                    )}
                  </Card>
                ))
            }
          </div>
        </div>
      )}

      {/* Assessment tab */}
      {tab === "assessment" && (
        <div className="space-y-6">
          <Section title="Assessment strategy">
            {editing
              ? <Textarea value={d.assessment_strategy || ""}
                  onChange={(e) => setDraft({ ...d, assessment_strategy: e.target.value })}
                  rows={5} placeholder="Describe how learning will be assessed — formative checks, exit tickets, summative tasks, rubrics…"
                  resize={false} />
              : <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
                  {d.assessment_strategy || <span className="text-slate-400 italic">No assessment strategy specified.</span>}
                </p>
            }
          </Section>
          <Card variant="flush" padding="lg" className="bg-slate-50">
            <div className="text-sm text-slate-600">
              Need a matching assessment? Go to the{" "}
              <Link to="/teaching/assessment-builder" className="text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
                Assessment Builder
              </Link>{" "}
              to generate a quiz, exam, or rubric aligned to this lesson's objectives.
            </div>
          </Card>
        </div>
      )}
    </div>
    </ResearchLayout>
  );
}

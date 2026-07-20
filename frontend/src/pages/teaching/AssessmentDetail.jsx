import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Sparkles, Download, Edit2, Check, X, Trash2, Plus, CheckCircle } from "lucide-react";
import api from "../../lib/api";
import { toast } from "sonner";
import { NAVY } from "@/lib/tokens";
import { SkeletonPage } from "../../components/ds/LoadingState";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Textarea } from "@/components/ds/Textarea";
import { NavTabs } from "@/components/ds/NavTabs";
import { ResearchLayout } from "@/layouts";

const TYPE_BADGE_VARIANT = {
  quiz: "info",
  exam: "danger",
  rubric: "purple",
  assignment: "warning",
  reflection: "success",
  presentation: "neutral",
};

const Q_TYPE_LABELS = {
  multiple_choice: "MC",
  short_answer:    "SA",
  essay:           "Essay",
  true_false:      "T/F",
};

function QuestionCard({ q, index, editing, onChange }) {
  const isMC = q.type === "multiple_choice";
  const isTF = q.type === "true_false";

  return (
    <Card padding="lg">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-slate-400">{String(index + 1).padStart(2, "0")}</span>
          <Badge variant={TYPE_BADGE_VARIANT[q.type] || "neutral"} size="sm">{Q_TYPE_LABELS[q.type] || q.type}</Badge>
        </div>
        <span className="text-xs text-slate-500 font-mono">{q.marks} marks</span>
      </div>
      {editing
        ? <Textarea value={q.question} onChange={(e) => onChange("question", e.target.value)}
            rows={2} className="mb-3" />
        : <p className="text-sm text-slate-900 font-medium mb-3 leading-snug">{q.question}</p>
      }

      {(isMC || isTF) && (
        <div className="space-y-1.5 mb-3">
          {(q.options || []).map((opt, oi) => {
            const letter = ["A","B","C","D"][oi] || String.fromCharCode(65 + oi);
            const isCorrect = q.correct_answer === letter || q.correct_answer === opt;
            return (
              <div key={oi} className={`flex items-center gap-2 text-sm px-3 py-1.5 border ${isCorrect ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-slate-100 text-slate-700"}`}>
                <span className="font-mono text-xs text-slate-400 w-4">{letter}.</span>
                <span>{opt}</span>
                {isCorrect && <CheckCircle size={12} strokeWidth={1.5} className="text-emerald-500 ml-auto" />}
              </div>
            );
          })}
        </div>
      )}

      {q.model_answer && (
        <div className="border-t border-slate-100 pt-3">
          <div className="text-[10px] overline mb-1">Model answer</div>
          <p className="text-xs text-slate-600 leading-relaxed">{q.model_answer}</p>
        </div>
      )}
      {q.rubric && (
        <div className="border-t border-slate-100 pt-3 mt-2">
          <div className="text-[10px] overline mb-1">Rubric</div>
          <p className="text-xs text-slate-600 leading-relaxed">{q.rubric}</p>
        </div>
      )}
    </Card>
  );
}

export default function AssessmentDetail() {
  const { assessmentId } = useParams();
  const navigate = useNavigate();
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading]       = useState(true);
  const [saving, setSaving]         = useState(false);
  const [editing, setEditing]       = useState(false);
  const [draft, setDraft]           = useState(null);
  const [tab, setTab]               = useState("questions");

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await api.get(`/teaching/assessments/${assessmentId}`);
        setAssessment(data);
        setDraft(data);
      } catch (_) {
        toast.error("Assessment not found");
        navigate("/teaching/assessment-builder");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [assessmentId]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.patch(`/teaching/assessments/${assessmentId}`, draft);
      setAssessment(data);
      setDraft(data);
      setEditing(false);
      toast.success("Assessment saved");
    } catch (_) {
      toast.error("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Delete this assessment? This cannot be undone.")) return;
    try {
      await api.delete(`/teaching/assessments/${assessmentId}`);
      toast.success("Assessment deleted");
      navigate("/teaching/assessment-builder");
    } catch (_) {
      toast.error("Failed to delete");
    }
  };

  const exportAsText = () => {
    if (!assessment) return;
    const lines = [
      `ASSESSMENT: ${assessment.title}`,
      `${"=".repeat(60)}`,
      `Type: ${assessment.assessment_type}   Subject: ${assessment.subject}   Total marks: ${assessment.total_marks}`,
      "",
      "INSTRUCTIONS",
      "-".repeat(40),
      assessment.instructions || "N/A",
      "",
      "LEARNING OBJECTIVES",
      "-".repeat(40),
      ...(assessment.learning_objectives || []).map((o, i) => `${i + 1}. ${o}`),
      "",
      "QUESTIONS",
      "-".repeat(40),
      ...(assessment.questions || []).map((q, i) => {
        const parts = [`Q${i + 1} [${Q_TYPE_LABELS[q.type] || q.type}] (${q.marks} marks)`, q.question];
        if (q.options) parts.push(...q.options.map((o, oi) => `  ${["A","B","C","D"][oi]}. ${o}`));
        if (q.correct_answer) parts.push(`  Answer: ${q.correct_answer}`);
        if (q.model_answer) parts.push(`  Model Answer: ${q.model_answer}`);
        return parts.join("\n");
      }),
      "",
      "RUBRIC",
      "-".repeat(40),
      ...(assessment.rubric_criteria || []).map((c) => [
        `${c.criterion} (${c.max_marks} marks)`,
        `  Excellent: ${c.descriptors?.excellent || ""}`,
        `  Good: ${c.descriptors?.good || ""}`,
        `  Satisfactory: ${c.descriptors?.satisfactory || ""}`,
        `  Needs improvement: ${c.descriptors?.needs_improvement || ""}`,
      ].join("\n")),
      "",
      `Generated by SYNAPTIQ Teaching Hub — ${new Date().toLocaleDateString()}`,
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `assessment-${assessment.title.replace(/\s+/g, "-").toLowerCase()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <div className="p-6"><SkeletonPage cards={2} /></div>;
  if (!assessment) return null;

  const d = editing ? draft : assessment;
  const totalQMarks = (d.questions || []).reduce((s, q) => s + (q.marks || 0), 0);

  return (
    <ResearchLayout>
    <div className="max-w-4xl space-y-8">
      <header className="border-b border-slate-200 pb-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            {editing
              ? <input value={d.title} onChange={(e) => setDraft({ ...d, title: e.target.value })}
                  className="w-full font-serif text-3xl text-slate-900 border-b border-slate-300 focus:outline-none focus:border-[#0F2847] bg-transparent pb-1" />
              : <h1 className="font-serif text-3xl text-slate-900">{d.title}</h1>
            }
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              <Badge variant={TYPE_BADGE_VARIANT[d.assessment_type] || "neutral"}>
                {d.assessment_type}
              </Badge>
              <span className="text-sm text-slate-500">{d.subject}</span>
              <span className="text-slate-300">·</span>
              <span className="text-sm text-slate-500">{d.total_marks} marks</span>
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
                <Button variant="ghost" onClick={() => { setDraft(assessment); setEditing(false); }}>
                  Cancel
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" size="sm" onClick={exportAsText}>
                  <Download size={13} strokeWidth={1.5} /> Export
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
                  <Edit2 size={13} strokeWidth={1.5} /> Edit
                </Button>
                <Button variant="ghost" size="icon" onClick={handleDelete} className="text-slate-400 hover:text-red-500">
                  <Trash2 size={15} strokeWidth={1.5} />
                </Button>
              </>
            )}
          </div>
        </div>

        <NavTabs
          className="mt-6 -mb-6"
          tabs={["questions", "rubric", "instructions"].map((t) => ({ id: t, label: t.charAt(0).toUpperCase() + t.slice(1) }))}
          active={tab}
          onChange={setTab}
        />
      </header>

      {/* Questions tab */}
      {tab === "questions" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-500">
              {(d.questions || []).length} questions ·{" "}
              <span className={totalQMarks !== d.total_marks && (d.questions || []).length > 0 ? "text-amber-600 font-medium" : ""}>
                {totalQMarks} / {d.total_marks} marks allocated
              </span>
            </div>
            {editing && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const q = { id: `q${(d.questions || []).length + 1}`, type: "short_answer", question: "", marks: 5, model_answer: "", rubric: "" };
                  setDraft({ ...d, questions: [...(d.questions || []), q] });
                }}
              >
                <Plus size={11} strokeWidth={1.5} /> Add question
              </Button>
            )}
          </div>
          {(d.questions || []).length === 0 && (
            <div className="text-sm text-slate-400 italic py-8 text-center">No questions yet. {editing ? "Add questions above." : "Enable editing to add questions."}</div>
          )}
          <div className="space-y-3">
            {(d.questions || []).map((q, i) => (
              <QuestionCard key={q.id || i} q={q} index={i} editing={editing}
                onChange={(field, val) => {
                  const questions = [...(d.questions || [])];
                  questions[i] = { ...questions[i], [field]: val };
                  setDraft({ ...d, questions });
                }} />
            ))}
          </div>
        </div>
      )}

      {/* Rubric tab */}
      {tab === "rubric" && (
        <div className="space-y-4">
          {(d.rubric_criteria || []).length === 0 && (
            <div className="text-sm text-slate-400 italic py-8 text-center">No rubric criteria. Generate an assessment with rubric type, or add criteria manually.</div>
          )}
          {(d.rubric_criteria || []).map((c, i) => (
            <Card key={i} variant="flush" padding="none">
              <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
                <span className="font-medium text-sm text-slate-900">{c.criterion}</span>
                <span className="text-xs text-slate-500 font-mono">{c.max_marks} marks</span>
              </div>
              <div className="grid sm:grid-cols-2 gap-0 divide-x divide-y divide-slate-100">
                {Object.entries(c.descriptors || {}).map(([level, desc]) => (
                  <div key={level} className="px-4 py-3">
                    <div className="text-[10px] overline mb-1 text-slate-500">{level.replace("_", " ")}</div>
                    <p className="text-xs text-slate-700 leading-relaxed">{desc}</p>
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Instructions tab */}
      {tab === "instructions" && (
        <div className="space-y-6">
          <div className="border-t border-slate-200 pt-6">
            <div className="overline mb-3">Instructions for students</div>
            {editing
              ? <Textarea value={d.instructions || ""}
                  onChange={(e) => setDraft({ ...d, instructions: e.target.value })}
                  rows={6} placeholder="What students need to know before taking this assessment…"
                  resize={false} />
              : <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
                  {d.instructions || <span className="text-slate-400 italic">No instructions written yet.</span>}
                </p>
            }
          </div>
          {(d.learning_objectives || []).length > 0 && (
            <div className="border-t border-slate-200 pt-6">
              <div className="overline mb-3">Learning objectives assessed</div>
              <ol className="space-y-2">
                {(d.learning_objectives || []).map((o, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                    <span className="font-mono text-xs text-[#0F2847] mt-0.5 shrink-0">{String(i + 1).padStart(2, "0")}</span>
                    {o}
                  </li>
                ))}
              </ol>
            </div>
          )}
          {d.teacher_notes && (
            <div className="border-t border-slate-200 pt-6">
              <div className="overline mb-3">Teacher notes</div>
              <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">{d.teacher_notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
    </ResearchLayout>
  );
}

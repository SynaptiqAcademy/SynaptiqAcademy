/* eslint-disable */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ClipboardCheck, Plus, Sparkles, FileText } from "lucide-react";
import api from "../../lib/api";
import { toast } from "sonner";
import { EmptyState } from "../../components/ds/EmptyState";
import { Spinner } from "../../components/ds/LoadingState";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Tag } from "@/components/ds/Tag";
import { Input } from "@/components/ds/Input";
import { FormSelect } from "@/components/ds/FormSelect";
import { NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";

const SUBJECTS      = ["Mathematics","Economics","Management","Computer Science","Medicine","Engineering","Psychology","Education","Sciences","Humanities","Law","Business","History","Literature","Physics","Chemistry","Biology","Sociology","Political Science","Philosophy"];
const LEVELS        = ["secondary","undergraduate","graduate","professional","adult","other"];
const TYPES         = ["quiz","exam","rubric","assignment","reflection","presentation"];
const QUESTION_TYPES = ["multiple_choice","short_answer","essay","true_false"];
const FILTER_TYPES  = ["", ...TYPES];

const TYPE_BADGE_VARIANT = {
  quiz: "info",
  exam: "danger",
  rubric: "purple",
  assignment: "warning",
  reflection: "success",
  presentation: "neutral",
};

export default function AssessmentBuilder() {
  const navigate = useNavigate();
  const [assessments, setAssessments]   = useState([]);
  const [loading, setLoading]           = useState(true);
  const [filterType, setFilterType]     = useState("");
  const [showCreate, setShowCreate]     = useState(false);
  const [showGenerate, setShowGenerate] = useState(false);

  const [createForm, setCreateForm] = useState({
    title: "", subject: "", assessment_type: "quiz", total_marks: 100,
  });
  const [creating, setCreating] = useState(false);

  const [genForm, setGenForm] = useState({
    title: "", subject: "", assessment_type: "quiz",
    learning_objectives: [""],
    level: "undergraduate", question_count: 10, question_types: ["multiple_choice"], total_marks: 100,
  });
  const [generating, setGenerating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/teaching/assessments", {
        params: filterType ? { assessment_type: filterType } : {},
      });
      setAssessments(data || []);
    } catch (_) {
      toast.error("Failed to load assessments");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterType]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!createForm.title || !createForm.subject) return;
    setCreating(true);
    try {
      const { data } = await api.post("/teaching/assessments", createForm);
      toast.success("Assessment created");
      navigate(`/teaching/assessments/${data.id}`);
    } catch (_) {
      toast.error("Failed to create assessment");
    } finally {
      setCreating(false);
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    const objectives = genForm.learning_objectives.filter((o) => o.trim());
    if (!genForm.title || !genForm.subject || objectives.length === 0) return;
    setGenerating(true);
    try {
      const { data } = await api.post("/teaching/assessments/generate", {
        ...genForm,
        learning_objectives: objectives,
      });
      toast.success("Assessment generated — 10 credits used");
      navigate(`/teaching/assessments/${data.id}`);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Generation failed";
      toast.error(msg);
    } finally {
      setGenerating(false);
    }
  };

  const toggleQType = (qt) => {
    const types = genForm.question_types.includes(qt)
      ? genForm.question_types.filter((t) => t !== qt)
      : [...genForm.question_types, qt];
    if (types.length > 0) setGenForm({ ...genForm, question_types: types });
  };

  const updateObjective = (i, v) => {
    const objs = [...genForm.learning_objectives];
    objs[i] = v;
    setGenForm({ ...genForm, learning_objectives: objs });
  };

  return (
    <ResearchLayout
      title="Assessment Builder"
      subtitle="Design quizzes, exams, rubrics, and assignments. Use AI to generate complete, aligned assessments in seconds."
      icon={ClipboardCheck}
      actions={
        <div className="flex gap-2">
          <Button
            variant={showGenerate ? "primary" : "outline"}
            onClick={() => { setShowGenerate(!showGenerate); setShowCreate(false); }}
          >
            <Sparkles size={14} strokeWidth={1.5} /> AI Generate
          </Button>
          <Button
            variant={showCreate ? "primary" : "ghost"}
            onClick={() => { setShowCreate(!showCreate); setShowGenerate(false); }}
          >
            <Plus size={14} strokeWidth={1.5} /> New assessment
          </Button>
        </div>
      }
    >

      {/* AI Generate panel */}
      {showGenerate && (
        <Card variant="flush" padding="lg" className="border-[#0F2847]/20 bg-slate-50">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={16} strokeWidth={1.5} className="text-[#0F2847]" />
            <div className="overline text-[#0F2847]">AI Assessment Generator — 10 credits</div>
          </div>
          <form onSubmit={handleGenerate} className="space-y-4">
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <Input
                label="Assessment title *"
                required
                value={genForm.title}
                onChange={(e) => setGenForm({ ...genForm, title: e.target.value })}
                placeholder="e.g. Midterm Exam: Cell Biology"
                wrapperClassName="sm:col-span-2"
              />
              <FormSelect
                label="Subject *"
                required
                value={genForm.subject}
                onChange={(e) => setGenForm({ ...genForm, subject: e.target.value })}
              >
                <option value="">Select subject</option>
                {SUBJECTS.map((s) => <option key={s}>{s}</option>)}
              </FormSelect>
              <FormSelect
                label="Assessment type"
                value={genForm.assessment_type}
                onChange={(e) => setGenForm({ ...genForm, assessment_type: e.target.value })}
              >
                {TYPES.map((t) => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
              </FormSelect>
              <FormSelect
                label="Level"
                value={genForm.level}
                onChange={(e) => setGenForm({ ...genForm, level: e.target.value })}
              >
                {LEVELS.map((l) => <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>)}
              </FormSelect>
              <Input
                label="Number of questions"
                type="number"
                min={3}
                max={40}
                value={genForm.question_count}
                onChange={(e) => setGenForm({ ...genForm, question_count: parseInt(e.target.value) || 10 })}
              />
              <Input
                label="Total marks"
                type="number"
                min={10}
                max={500}
                value={genForm.total_marks}
                onChange={(e) => setGenForm({ ...genForm, total_marks: parseInt(e.target.value) || 100 })}
              />
            </div>
            <div>
              <label className="sq-form-label block mb-1.5">Question types</label>
              <div className="flex flex-wrap gap-2">
                {QUESTION_TYPES.map((qt) => (
                  <Tag
                    key={qt}
                    variant={genForm.question_types.includes(qt) ? "active" : "default"}
                    onClick={() => toggleQType(qt)}
                  >
                    {qt.replace("_", " ")}
                  </Tag>
                ))}
              </div>
            </div>
            <div>
              <label className="sq-form-label block mb-1.5">Learning objectives *</label>
              <div className="space-y-2">
                {genForm.learning_objectives.map((obj, i) => (
                  <div key={i} className="flex gap-2">
                    <Input
                      value={obj}
                      onChange={(e) => updateObjective(i, e.target.value)}
                      placeholder={`Objective ${i + 1}`}
                      wrapperClassName="flex-1"
                    />
                    {genForm.learning_objectives.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setGenForm({ ...genForm, learning_objectives: genForm.learning_objectives.filter((_, j) => j !== i) })}
                      >
                        ✕
                      </Button>
                    )}
                  </div>
                ))}
                <Button
                  type="button"
                  variant="link"
                  size="sm"
                  onClick={() => setGenForm({ ...genForm, learning_objectives: [...genForm.learning_objectives, ""] })}
                >
                  <Plus size={11} strokeWidth={1.5} /> Add objective
                </Button>
              </div>
            </div>
            <div className="flex gap-3 items-center">
              <Button type="submit" loading={generating} disabled={!genForm.title || !genForm.subject}>
                {generating
                  ? "Generating…"
                  : (<><Sparkles size={14} strokeWidth={1.5} /> Generate assessment</>)}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setShowGenerate(false)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}

      {/* Manual create panel */}
      {showCreate && (
        <Card variant="flush" padding="lg">
          <div className="overline mb-4">New assessment (blank)</div>
          <form onSubmit={handleCreate} className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Input
              label="Title *"
              required
              value={createForm.title}
              onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
              placeholder="Assessment title"
              wrapperClassName="sm:col-span-2"
            />
            <FormSelect
              label="Subject *"
              required
              value={createForm.subject}
              onChange={(e) => setCreateForm({ ...createForm, subject: e.target.value })}
            >
              <option value="">Select subject</option>
              {SUBJECTS.map((s) => <option key={s}>{s}</option>)}
            </FormSelect>
            <FormSelect
              label="Type"
              value={createForm.assessment_type}
              onChange={(e) => setCreateForm({ ...createForm, assessment_type: e.target.value })}
            >
              {TYPES.map((t) => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
            </FormSelect>
            <Input
              label="Total marks"
              type="number"
              min={1}
              max={1000}
              value={createForm.total_marks}
              onChange={(e) => setCreateForm({ ...createForm, total_marks: parseInt(e.target.value) || 100 })}
            />
            <div className="sm:col-span-2 flex gap-3 items-end">
              <Button type="submit" loading={creating}>
                {creating ? "Creating…" : "Create assessment"}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}

      {/* Filter + list */}
      <div>
        <div className="flex items-center gap-4 mb-5">
          <div className="overline">Your assessments</div>
          <FormSelect
            size="sm"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="!w-auto"
          >
            {FILTER_TYPES.map((t) => <option key={t} value={t}>{t || "All types"}</option>)}
          </FormSelect>
        </div>

        {loading && (
          <div className="flex items-center gap-2 text-sm text-slate-400 py-8">
            <Spinner size={14} /> Loading…
          </div>
        )}

        {!loading && assessments.length === 0 && (
          <EmptyState
            icon={<ClipboardCheck />}
            title="No assessments yet"
            description="Generate a complete quiz, exam, or rubric with AI — questions, marks, and model answers included."
            action={
              <Button onClick={() => setShowGenerate(true)}>
                Generate with AI
              </Button>
            }
          />
        )}

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {assessments.map((a) => (
            <Card key={a.id} to={`/teaching/assessments/${a.id}`} padding="lg">
              <div className="flex items-start justify-between gap-2 mb-2">
                <h3 className="font-medium text-slate-900 leading-snug line-clamp-2">{a.title}</h3>
                <Badge variant={TYPE_BADGE_VARIANT[a.assessment_type] || "neutral"} size="sm" className="shrink-0">
                  {a.assessment_type}
                </Badge>
              </div>
              <div className="text-xs text-slate-500 mb-3">{a.subject}</div>
              <div className="flex items-center gap-4 text-xs text-slate-500">
                <span className="flex items-center gap-1"><FileText size={10} strokeWidth={1.5} />{a.total_marks} marks</span>
              </div>
              {a.ai_generated && (
                <div className="mt-3 flex items-center gap-1 text-[10px] text-[#0F2847]/60">
                  <Sparkles size={9} strokeWidth={1.5} /> AI-generated
                </div>
              )}
            </Card>
          ))}
        </div>
      </div>
    </ResearchLayout>
  );
}

/* eslint-disable */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookOpen, Plus, Sparkles, Clock, Users, Layers } from "lucide-react";
import api from "../../lib/api";
import { toast } from "sonner";
import { EmptyState } from "../../components/ds/EmptyState";
import { Spinner } from "../../components/ds/LoadingState";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Input } from "@/components/ds/Input";
import { FormSelect } from "@/components/ds/FormSelect";
import { ResearchLayout } from "@/layouts";
import { NAVY } from "@/lib/tokens";

const SUBJECTS = ["Mathematics","Economics","Management","Computer Science","Medicine","Engineering","Psychology","Education","Sciences","Humanities","Law","Business","History","Literature","Physics","Chemistry","Biology","Sociology","Political Science","Philosophy"];
const LEVELS   = ["secondary","undergraduate","graduate","professional","adult","other"];
const STATUSES = ["", "draft", "published"];

function LabelTag({ status }) {
  return (
    <Badge variant={status === "published" ? "success" : "neutral"} size="sm">
      {status}
    </Badge>
  );
}

export default function LessonPlanner() {
  const navigate   = useNavigate();
  const [lessons, setLessons]           = useState([]);
  const [loading, setLoading]           = useState(true);
  const [filterStatus, setFilterStatus] = useState("");
  const [showCreate, setShowCreate]     = useState(false);
  const [showGenerate, setShowGenerate] = useState(false);

  const [createForm, setCreateForm] = useState({
    title: "", subject: "", audience: "", level: "undergraduate", duration_minutes: 60,
  });
  const [creating, setCreating]   = useState(false);

  const [genForm, setGenForm] = useState({
    topic: "", subject: "", audience: "", level: "undergraduate",
    duration_minutes: 60, objectives_count: 4,
  });
  const [generating, setGenerating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/teaching/lessons", {
        params: filterStatus ? { status: filterStatus } : {},
      });
      setLessons(data || []);
    } catch (_) {
      toast.error("Failed to load lessons");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!createForm.title || !createForm.subject) return;
    setCreating(true);
    try {
      const { data } = await api.post("/teaching/lessons", createForm);
      toast.success("Lesson plan created");
      navigate(`/teaching/lessons/${data.id}`);
    } catch (_) {
      toast.error("Failed to create lesson");
    } finally {
      setCreating(false);
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!genForm.topic || !genForm.subject) return;
    setGenerating(true);
    try {
      const { data } = await api.post("/teaching/lessons/generate", genForm);
      toast.success("Lesson plan generated — 10 credits used");
      navigate(`/teaching/lessons/${data.id}`);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Generation failed";
      toast.error(msg);
    } finally {
      setGenerating(false);
    }
  };

  const publishedCount = lessons.filter((l) => l.status === "published").length;
  const draftCount     = lessons.filter((l) => l.status === "draft").length;
  const aiCount        = lessons.filter((l) => l.ai_generated).length;

  return (
    <ResearchLayout
      title="Lesson Planner"
      subtitle="Create structured lesson plans with AI assistance — objectives, activities, materials, and differentiation strategies."
      icon={<BookOpen size={15} strokeWidth={1.5} style={{ color: "#0F2847" }} />}
      stats={!loading ? [
        { label: "Lessons",      value: lessons.length },
        { label: "Published",    value: publishedCount },
        { label: "Drafts",       value: draftCount },
        { label: "AI-Generated", value: aiCount },
      ] : undefined}
      sidebar={!loading && lessons.length > 0 ? <LessonPlannerSidebar lessons={lessons} /> : undefined}
      actions={
        <div className="flex gap-2">
          <Button
            variant="hero"
            onClick={() => { setShowGenerate(!showGenerate); setShowCreate(false); }}
          >
            <Sparkles size={14} strokeWidth={1.5} /> AI Generate
          </Button>
          <Button
            variant="hero"
            onClick={() => { setShowCreate(!showCreate); setShowGenerate(false); }}
          >
            <Plus size={14} strokeWidth={1.5} /> New lesson
          </Button>
        </div>
      }
    >

      {/* AI Generate panel */}
      {showGenerate && (
        <Card variant="flush" padding="lg" className="border-[#0F2847]/20 bg-slate-50">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={16} strokeWidth={1.5} className="text-[#0F2847]" />
            <div className="overline text-[#0F2847]">AI Lesson Generator — 10 credits</div>
          </div>
          <form onSubmit={handleGenerate} className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Input
              label="Topic *"
              required
              value={genForm.topic}
              onChange={(e) => setGenForm({ ...genForm, topic: e.target.value })}
              placeholder="e.g. Introduction to Photosynthesis"
              wrapperClassName="lg:col-span-2"
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
            <Input
              label="Target audience"
              value={genForm.audience}
              onChange={(e) => setGenForm({ ...genForm, audience: e.target.value })}
              placeholder="e.g. Second-year biology students"
            />
            <FormSelect
              label="Level"
              value={genForm.level}
              onChange={(e) => setGenForm({ ...genForm, level: e.target.value })}
            >
              {LEVELS.map((l) => <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>)}
            </FormSelect>
            <Input
              label="Duration (minutes)"
              type="number"
              min={15}
              max={480}
              value={genForm.duration_minutes}
              onChange={(e) => setGenForm({ ...genForm, duration_minutes: parseInt(e.target.value) || 60 })}
            />
            <Input
              label="Learning objectives to generate"
              type="number"
              min={2}
              max={8}
              value={genForm.objectives_count}
              onChange={(e) => setGenForm({ ...genForm, objectives_count: parseInt(e.target.value) || 4 })}
            />
            <div className="lg:col-span-3 flex gap-3 items-center">
              <Button type="submit" loading={generating} disabled={!genForm.topic || !genForm.subject}>
                {generating
                  ? "Generating…"
                  : (<><Sparkles size={14} strokeWidth={1.5} /> Generate lesson plan</>)}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setShowGenerate(false)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}

      {/* Manual create panel */}
      {showCreate && (
        <Card variant="flush" padding="lg">
          <div className="overline mb-4">New lesson (blank)</div>
          <form onSubmit={handleCreate} className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Input
              label="Title *"
              required
              value={createForm.title}
              onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
              placeholder="Lesson title"
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
              label="Level"
              value={createForm.level}
              onChange={(e) => setCreateForm({ ...createForm, level: e.target.value })}
            >
              {LEVELS.map((l) => <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>)}
            </FormSelect>
            <Input
              label="Audience"
              value={createForm.audience}
              onChange={(e) => setCreateForm({ ...createForm, audience: e.target.value })}
              placeholder="Who are the learners?"
              wrapperClassName="sm:col-span-2"
            />
            <Input
              label="Duration (minutes)"
              type="number"
              min={5}
              max={480}
              value={createForm.duration_minutes}
              onChange={(e) => setCreateForm({ ...createForm, duration_minutes: parseInt(e.target.value) || 60 })}
            />
            <div className="sm:col-span-2 flex gap-3 items-end">
              <Button type="submit" loading={creating}>
                {creating ? "Creating…" : "Create lesson"}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}

      {/* Filter + list */}
      <div>
        <div className="flex items-center gap-4 mb-5">
          <div className="overline">Your lessons</div>
          <FormSelect
            size="sm"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="!w-auto"
          >
            {STATUSES.map((s) => <option key={s} value={s}>{s || "All statuses"}</option>)}
          </FormSelect>
        </div>

        {loading && (
          <div className="flex items-center gap-2 text-sm text-slate-400 py-8">
            <Spinner size={14} /> Loading…
          </div>
        )}

        {!loading && lessons.length === 0 && (
          <EmptyState
            icon={<BookOpen />}
            title="No lesson plans yet"
            description="Start by generating an AI lesson plan or creating a blank one. Each plan saves your objectives, activities, materials, and assessment strategy."
            action={
              <Button onClick={() => setShowGenerate(true)}>
                Generate with AI
              </Button>
            }
          />
        )}

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {lessons.map((l) => (
            <Card key={l.id} to={`/teaching/lessons/${l.id}`} padding="lg">
              <div className="flex items-start justify-between gap-2 mb-2">
                <h3 className="font-medium text-slate-900 leading-snug line-clamp-2">{l.title}</h3>
                <LabelTag status={l.status} />
              </div>
              <div className="text-xs text-slate-500 mb-3">{l.subject}</div>
              <div className="flex items-center gap-4 text-xs text-slate-500">
                <span className="flex items-center gap-1"><Clock size={10} strokeWidth={1.5} />{l.duration_minutes} min</span>
                {l.audience && <span className="flex items-center gap-1"><Users size={10} strokeWidth={1.5} />{l.audience}</span>}
              </div>
              {l.ai_generated && (
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

// ── Right rail — subject breakdown + average duration, real data already loaded above ──
function LessonPlannerSidebar({ lessons }) {
  const bySubject = new Map();
  lessons.forEach((l) => {
    if (!l.subject) return;
    bySubject.set(l.subject, (bySubject.get(l.subject) || 0) + 1);
  });
  const topSubjects = Array.from(bySubject.entries()).sort((a, b) => b[1] - a[1]).slice(0, 4);

  const avgDuration = lessons.length > 0
    ? Math.round(lessons.reduce((s, l) => s + (l.duration_minutes || 0), 0) / lessons.length)
    : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
          <Layers size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Top Subjects</div>
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
            Subjects will appear here as you add lessons.
          </p>
        )}
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Clock size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Average Duration</div>
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 28, fontWeight: 700, color: "#0f172a" }}>
          {avgDuration} <span style={{ fontSize: 13, fontWeight: 400, color: "#64748B" }}>min</span>
        </div>
        <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0", lineHeight: 1.5 }}>
          Across {lessons.length} lesson{lessons.length !== 1 ? "s" : ""}.
        </p>
      </Card>
    </div>
  );
}

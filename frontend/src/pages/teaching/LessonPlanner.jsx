/* eslint-disable */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookOpen, Plus, Sparkles, Clock, Users } from "lucide-react";
import api from "../../lib/api";
import { toast } from "sonner";
import { EmptyState } from "../../components/ds/EmptyState";
import { Spinner } from "../../components/ds/LoadingState";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Input } from "@/components/ds/Input";
import { FormSelect } from "@/components/ds/FormSelect";
import { NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";

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

  return (
    <ResearchLayout
      title="Lesson Planner"
      subtitle="Create structured lesson plans with AI assistance — objectives, activities, materials, and differentiation strategies."
      icon={BookOpen}
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

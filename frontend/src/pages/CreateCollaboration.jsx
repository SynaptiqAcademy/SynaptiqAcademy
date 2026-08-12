import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { toast } from "sonner";
import { NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { FormField } from "@/components/ds/Form";
import { Tag } from "@/components/ds/Tag";
import { Button } from "@/components/ds/Button";

const TYPES = [
  "Journal Article", "Conference Paper", "Research Project", "Book Chapter", "Book",
  "Grant Proposal", "Systematic Review", "Meta-analysis", "Dataset Development",
  "Teaching Collaboration", "Curriculum Design", "Course Development",
  "Mentorship", "Industry Partnership", "Grant Consortium", "Publication Project",
];
const AREAS = ["Artificial Intelligence", "Healthcare", "Management", "Economics", "Education", "Public Health", "Cybersecurity", "Engineering", "Psychology"];
const SKILLS = ["SPSS", "R", "Python", "PLS-SEM", "SEM", "Regression Analysis", "Systematic Literature Review", "Qualitative Research"];

export default function CreateCollaboration() {
  const [form, setForm] = useState({
    title: "", description: "", collab_type: "Journal Article",
    research_area: "Artificial Intelligence", skills_needed: [],
    team_size: 2, duration: "3 months", publication_goal: "", funding_status: "Not funded",
  });
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const toggleSkill = (s) => {
    const set = new Set(form.skills_needed);
    set.has(s) ? set.delete(s) : set.add(s);
    setForm({ ...form, skills_needed: Array.from(set) });
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await api.post("/collaborations", form);
      toast.success("Collaboration posted");
      navigate(`/collaborations/${data.id}`);
    } catch (e) {
      toast.error("Failed to post");
    } finally {
      setSaving(false);
    }
  };

  return (
    <ResearchLayout title="Create a collaboration" subtitle="Be specific. The clearer your ask, the better your applicants.">
      <form onSubmit={onSubmit} className="max-w-3xl">
      <div className="mt-10 space-y-6">
        <Input
          label="Title"
          data-testid={TID.collabCreateTitle}
          required
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          placeholder="e.g. Looking for a statistician for a healthcare paper"
        />
        <Textarea
          label="Description"
          data-testid={TID.collabCreateDescription}
          required
          rows={5}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          placeholder="What is the project about? Dataset? Target journal? Why now?"
        />
        <div className="grid sm:grid-cols-2 gap-6">
          <FormSelect
            label="Type"
            data-testid={TID.collabCreateType}
            value={form.collab_type}
            onChange={(e) => setForm({ ...form, collab_type: e.target.value })}
          >
            {TYPES.map((t) => <option key={t}>{t}</option>)}
          </FormSelect>
          <FormSelect
            label="Research area"
            data-testid={TID.collabCreateArea}
            value={form.research_area}
            onChange={(e) => setForm({ ...form, research_area: e.target.value })}
          >
            {AREAS.map((a) => <option key={a}>{a}</option>)}
          </FormSelect>
        </div>
        <FormField label="Skills needed">
          <div className="flex flex-wrap gap-2">
            {SKILLS.map((s) => (
              <Tag
                key={s}
                variant={form.skills_needed.includes(s) ? "active" : "default"}
                onClick={() => toggleSkill(s)}
              >
                {s}
              </Tag>
            ))}
          </div>
        </FormField>
        <div className="grid sm:grid-cols-3 gap-6">
          <Input
            label="Team size"
            type="number" min={2} max={20} value={form.team_size}
            onChange={(e) => setForm({ ...form, team_size: parseInt(e.target.value) || 2 })}
          />
          <Input
            label="Duration"
            value={form.duration}
            onChange={(e) => setForm({ ...form, duration: e.target.value })}
          />
          <FormSelect
            label="Funding status"
            value={form.funding_status}
            onChange={(e) => setForm({ ...form, funding_status: e.target.value })}
          >
            <option>Not funded</option>
            <option>Internal grant</option>
            <option>Pending application</option>
            <option>Funded</option>
          </FormSelect>
        </div>
        <Input
          label="Publication goal"
          value={form.publication_goal}
          onChange={(e) => setForm({ ...form, publication_goal: e.target.value })}
          placeholder="Target venue (e.g. Nature, Q1 healthcare journal)"
        />
      </div>

      <div className="mt-10 flex gap-4">
        <Button
          type="submit"
          data-testid={TID.collabCreateSubmit}
          disabled={saving}
          loading={saving}
        >
          Post collaboration
        </Button>
        <Button type="button" variant="ghost" onClick={() => navigate("/collaborations")}>
          Cancel
        </Button>
      </div>
      </form>
    </ResearchLayout>
  );
}

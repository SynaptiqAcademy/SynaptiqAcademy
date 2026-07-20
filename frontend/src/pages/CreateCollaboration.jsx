import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { toast } from "sonner";
import { NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";

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
        <div>
          <Label>Title</Label>
          <input
            data-testid={TID.collabCreateTitle}
            required
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="e.g. Looking for a statistician for a healthcare paper"
            className="w-full px-3 py-2 border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
          />
        </div>
        <div>
          <Label>Description</Label>
          <textarea
            data-testid={TID.collabCreateDescription}
            required
            rows={5}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="What is the project about? Dataset? Target journal? Why now?"
            className="w-full px-3 py-2 border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
          />
        </div>
        <div className="grid sm:grid-cols-2 gap-6">
          <div>
            <Label>Type</Label>
            <select
              data-testid={TID.collabCreateType}
              value={form.collab_type}
              onChange={(e) => setForm({ ...form, collab_type: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 bg-white"
            >
              {TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <Label>Research area</Label>
            <select
              data-testid={TID.collabCreateArea}
              value={form.research_area}
              onChange={(e) => setForm({ ...form, research_area: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 bg-white"
            >
              {AREAS.map((a) => <option key={a}>{a}</option>)}
            </select>
          </div>
        </div>
        <div>
          <Label>Skills needed</Label>
          <div className="flex flex-wrap gap-2">
            {SKILLS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => toggleSkill(s)}
                className={`px-3 py-1.5 text-xs border ${
                  form.skills_needed.includes(s)
                    ? "bg-[#0F2847] text-white border-[#0F2847]"
                    : "bg-white text-slate-700 border-slate-300 hover:border-slate-500"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
        <div className="grid sm:grid-cols-3 gap-6">
          <div>
            <Label>Team size</Label>
            <input type="number" min={2} max={20} value={form.team_size}
              onChange={(e) => setForm({ ...form, team_size: parseInt(e.target.value) || 2 })}
              className="w-full px-3 py-2 border border-slate-300" />
          </div>
          <div>
            <Label>Duration</Label>
            <input value={form.duration}
              onChange={(e) => setForm({ ...form, duration: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300" />
          </div>
          <div>
            <Label>Funding status</Label>
            <select value={form.funding_status}
              onChange={(e) => setForm({ ...form, funding_status: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 bg-white">
              <option>Not funded</option>
              <option>Internal grant</option>
              <option>Pending application</option>
              <option>Funded</option>
            </select>
          </div>
        </div>
        <div>
          <Label>Publication goal</Label>
          <input value={form.publication_goal}
            onChange={(e) => setForm({ ...form, publication_goal: e.target.value })}
            placeholder="Target venue (e.g. Nature, Q1 healthcare journal)"
            className="w-full px-3 py-2 border border-slate-300" />
        </div>
      </div>

      <div className="mt-10 flex gap-4">
        <button
          type="submit"
          data-testid={TID.collabCreateSubmit}
          disabled={saving}
          className="bg-[#0F2847] text-white px-6 py-3 text-sm hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? "Posting…" : "Post collaboration"}
        </button>
        <button type="button" onClick={() => navigate("/collaborations")} className="border border-slate-300 px-6 py-3 text-sm hover:bg-slate-50">
          Cancel
        </button>
      </div>
      </form>
    </ResearchLayout>
  );
}

function Label({ children }) {
  return <label className="block text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">{children}</label>;
}

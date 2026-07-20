import React, { useState } from "react";
import { toast } from "sonner";
import { X } from "lucide-react";
import { Modal } from "@/components/ds/Modal";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { FormField, FormGroup, FormRow, Checkbox } from "@/components/ds/Form";
import { Tag } from "@/components/ds/Tag";
import { NAVY } from "@/lib/tokens";
import { USER_TYPE_OPTIONS, PRIMARY_DOMAIN_OPTIONS } from "@/lib/userTypes";
import api from "@/lib/api";

const RESEARCH_AREAS = [
  "Artificial Intelligence", "Healthcare", "Management", "Economics", "Education",
  "Public Health", "Cybersecurity", "Engineering", "Psychology", "Sociology",
  "Political Science", "Environmental Science", "History", "Communication", "Law",
  "Philosophy", "Mathematics", "Physics", "Chemistry", "Biology", "Medicine",
  "Business", "Finance", "Accounting", "Marketing",
];
const TEACHING_AREAS_OPTS = ["Mathematics", "Economics", "Management", "Computer Science", "Medicine", "Engineering", "Psychology", "Education", "Sciences", "Humanities", "Law", "Business"];
const PROFESSIONAL_EXPERTISE_OPTS = ["Artificial Intelligence", "Cybersecurity", "Public Health", "Project Management", "Innovation", "Data Science", "Finance", "Strategy", "Operations", "R&D", "Product Development", "Sustainability"];
const METHODS_OPTS = ["Quantitative", "Qualitative", "Mixed Methods", "Systematic Review", "Meta-Analysis", "Case Study", "Survey", "Ethnography", "Grounded Theory", "Experimental"];
const SOFTWARE_OPTS = ["SPSS", "R", "Python", "Stata", "SAS", "MATLAB", "NVivo", "Atlas.ti", "Excel", "Tableau"];
const SKILLS_OPTS = ["Data Analysis", "Literature Review", "Grant Writing", "Statistics", "Methodology", "Writing", "Supervision", "Peer Review"];
const CONTRIBUTE_OPTS = ["Writing", "Statistics", "Methodology", "Data Analysis", "Literature Review", "Grant Writing", "Supervision", "Peer Review"];
const LOOKING_OPTS = ["Co-authors", "Statisticians", "AI Researchers", "Healthcare Experts", "Economists", "Engineers", "Supervisors", "Funding Partners"];
const CAREER_STAGES = [
  { value: "phd_student", label: "PhD Student" }, { value: "postdoc", label: "Postdoctoral Researcher" },
  { value: "early_career", label: "Early Career Researcher" }, { value: "mid_career", label: "Mid-Career Researcher" },
  { value: "senior", label: "Senior Researcher" }, { value: "professor", label: "Professor" },
  { value: "emeritus", label: "Professor Emeritus" }, { value: "industry", label: "Industry Researcher" },
];
const AVAILABILITY_OPTIONS = ["Available", "Limited Availability", "Not Currently Available"];

function ChipToggle({ label, options, selected, onToggle }) {
  return (
    <FormField label={label}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {options.map((o) => (
          <Tag key={o} variant={selected.includes(o) ? "active" : "default"} onClick={() => onToggle(o)}>{o}</Tag>
        ))}
      </div>
    </FormField>
  );
}

/**
 * EditIdentityModal — the full editable identity form, ported from
 * Profile.jsx's EditProfile into a ds Modal. Same PATCH /users/me save call.
 */
export function EditIdentityModal({ open, onClose, profile, onSaved }) {
  const [f, setF] = useState(() => ({
    full_name: profile?.full_name || "", institution: profile?.institution || "",
    department: profile?.department || "", country: profile?.country || "", city: profile?.city || "",
    career_stage: profile?.career_stage || "", user_type: profile?.user_type || "",
    primary_domain: profile?.primary_domain || "", academic_role: profile?.academic_role || "",
    biography: profile?.biography || "", google_scholar: profile?.google_scholar || "",
    researchgate: profile?.researchgate || "", scopus_id: profile?.scopus_id || "",
    linkedin: profile?.linkedin || "", website: profile?.website || "", avatar_url: profile?.avatar_url || "",
    research_areas: profile?.research_areas || [], research_interests: profile?.research_interests || [],
    research_keywords: profile?.research_keywords || [], methods: profile?.methods || [],
    software_skills: profile?.software_skills || [], teaching_areas: profile?.teaching_areas || [],
    professional_expertise: profile?.professional_expertise || [], skills: profile?.skills || [],
    can_contribute: profile?.can_contribute || [], looking_for: profile?.looking_for || [],
    availability: profile?.availability || "Available",
    available_for_collaboration: profile?.available_for_collaboration ?? true,
    available_for_supervision: profile?.available_for_supervision ?? false,
    available_for_reviewing: profile?.available_for_reviewing ?? false,
    available_for_consulting: profile?.available_for_consulting ?? false,
  }));
  const [keywordInput, setKeywordInput] = useState("");
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const update = (key, val) => setF((p) => ({ ...p, [key]: val }));
  const toggle = (key, v) => {
    const set = new Set(f[key]);
    set.has(v) ? set.delete(v) : set.add(v);
    update(key, Array.from(set));
  };
  const addKeyword = (e) => {
    if ((e.key === "Enter" || e.key === ",") && keywordInput.trim()) {
      e.preventDefault();
      const kw = keywordInput.trim().replace(/,$/, "");
      if (kw && !f.research_keywords.includes(kw)) update("research_keywords", [...f.research_keywords, kw]);
      setKeywordInput("");
    }
  };

  const save = async () => {
    if (f.avatar_url && !f.avatar_url.startsWith("http")) return toast.error("Avatar URL must start with http:// or https://");
    if (f.website && !f.website.startsWith("http")) return toast.error("Website URL must start with http:// or https://");
    setSaving(true);
    try {
      await api.patch("/users/me", f);
      toast.success("Identity saved");
      onSaved?.();
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Edit Academic Identity"
      size="lg"
      footer={<>
        <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
        <Button onClick={save} loading={saving}>Save changes</Button>
      </>}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <FormGroup title="Identity">
          <FormRow cols={2}>
            <FormField label="Full name"><Input value={f.full_name} onChange={(e) => update("full_name", e.target.value)} /></FormField>
            <FormField label="Job title"><Input value={f.academic_role} onChange={(e) => update("academic_role", e.target.value)} placeholder="e.g. Associate Professor" /></FormField>
            <FormField label="Institution"><Input value={f.institution} onChange={(e) => update("institution", e.target.value)} /></FormField>
            <FormField label="Department"><Input value={f.department} onChange={(e) => update("department", e.target.value)} /></FormField>
            <FormField label="City"><Input value={f.city} onChange={(e) => update("city", e.target.value)} /></FormField>
            <FormField label="Country"><Input value={f.country} onChange={(e) => update("country", e.target.value)} /></FormField>
            <FormField label="Career stage">
              <FormSelect value={f.career_stage} onChange={(e) => update("career_stage", e.target.value)}>
                <option value="">Select…</option>
                {CAREER_STAGES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </FormSelect>
            </FormField>
            <FormField label="Avatar URL"><Input value={f.avatar_url} onChange={(e) => update("avatar_url", e.target.value)} placeholder="https://" /></FormField>
          </FormRow>
          <FormField label="Biography">
            <Textarea rows={4} value={f.biography} onChange={(e) => update("biography", e.target.value)} placeholder="Describe your research background, interests, and goals…" />
          </FormField>
        </FormGroup>

        <FormGroup title="Academic Identifiers" divided>
          <FormRow cols={2}>
            <FormField label="Google Scholar ID"><Input value={f.google_scholar} onChange={(e) => update("google_scholar", e.target.value)} /></FormField>
            <FormField label="ResearchGate username"><Input value={f.researchgate} onChange={(e) => update("researchgate", e.target.value)} /></FormField>
            <FormField label="Scopus Author ID"><Input value={f.scopus_id} onChange={(e) => update("scopus_id", e.target.value)} /></FormField>
            <FormField label="LinkedIn username"><Input value={f.linkedin} onChange={(e) => update("linkedin", e.target.value)} /></FormField>
            <FormField label="Personal website"><Input value={f.website} onChange={(e) => update("website", e.target.value)} placeholder="https://" /></FormField>
          </FormRow>
        </FormGroup>

        <FormGroup title="Research Profile" divided>
          <FormField label="Research keywords" hint="Press Enter or comma to add">
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
              {f.research_keywords.map((kw) => (
                <span key={kw} style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, padding: "3px 8px", background: "rgba(15,40,71,0.06)", border: "1px solid rgba(15,40,71,0.2)", color: NAVY }}>
                  {kw}
                  <button onClick={() => update("research_keywords", f.research_keywords.filter((k) => k !== kw))} aria-label={`Remove keyword ${kw}`} style={{ background: "none", border: "none", cursor: "pointer", display: "flex" }}>
                    <X size={10} />
                  </button>
                </span>
              ))}
            </div>
            <Input value={keywordInput} onChange={(e) => setKeywordInput(e.target.value)} onKeyDown={addKeyword} placeholder="Type keyword and press Enter…" />
          </FormField>
          <ChipToggle label="Research areas" options={RESEARCH_AREAS} selected={f.research_areas} onToggle={(v) => toggle("research_areas", v)} />
          <ChipToggle label="Research methods" options={METHODS_OPTS} selected={f.methods} onToggle={(v) => toggle("methods", v)} />
          <ChipToggle label="Software & tools" options={SOFTWARE_OPTS} selected={f.software_skills} onToggle={(v) => toggle("software_skills", v)} />
          <ChipToggle label="Skills" options={SKILLS_OPTS} selected={f.skills} onToggle={(v) => toggle("skills", v)} />
          <ChipToggle label="Teaching areas" options={TEACHING_AREAS_OPTS} selected={f.teaching_areas} onToggle={(v) => toggle("teaching_areas", v)} />
          <ChipToggle label="Professional expertise" options={PROFESSIONAL_EXPERTISE_OPTS} selected={f.professional_expertise} onToggle={(v) => toggle("professional_expertise", v)} />
        </FormGroup>

        <FormGroup title="Collaboration & Availability" divided>
          <FormField label="Status">
            <FormSelect value={f.availability} onChange={(e) => update("availability", e.target.value)}>
              {AVAILABILITY_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
            </FormSelect>
          </FormField>
          <FormField label="Open to">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <Checkbox label="Collaboration" checked={f.available_for_collaboration} onChange={(e) => update("available_for_collaboration", e.target.checked)} />
              <Checkbox label="PhD / Masters Supervision" checked={f.available_for_supervision} onChange={(e) => update("available_for_supervision", e.target.checked)} />
              <Checkbox label="Peer Review" checked={f.available_for_reviewing} onChange={(e) => update("available_for_reviewing", e.target.checked)} />
              <Checkbox label="Consulting" checked={f.available_for_consulting} onChange={(e) => update("available_for_consulting", e.target.checked)} />
            </div>
          </FormField>
          <ChipToggle label="Can contribute" options={CONTRIBUTE_OPTS} selected={f.can_contribute} onToggle={(v) => toggle("can_contribute", v)} />
          <ChipToggle label="Looking for" options={LOOKING_OPTS} selected={f.looking_for} onToggle={(v) => toggle("looking_for", v)} />
        </FormGroup>
      </div>
    </Modal>
  );
}

export default EditIdentityModal;

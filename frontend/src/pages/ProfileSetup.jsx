/* eslint-disable */
/**
 * ProfileSetup — Mandatory Academic Profile Completion
 *
 * Renders after onboarding (onboarded=true) until the community unlock
 * threshold (COMMUNITY_UNLOCK_THRESHOLD %) is reached. No AppShell wraps
 * this route (community isn't unlocked yet, so the full nav shouldn't show)
 * — the page manually recreates the same background/container conventions
 * AppShell applies everywhere else, then uses the same ds/PageLayout hero
 * every other page gets from its shell, so it reads as part of the same
 * product rather than a separate flow.
 *
 * Uses only existing backend endpoints:
 *   PATCH /api/users/me        — profile update
 *   GET  /auth/me              — user refresh (via refreshMe)
 */
import React, { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";
import {
  computeProfileScore,
  getCompletionItems,
  COMMUNITY_UNLOCK_THRESHOLD,
} from "@/lib/profileCompletion";
import { toast } from "sonner";
import {
  CheckCircle2,
  Circle,
  ChevronRight,
  Lock,
  Unlock,
  Sparkles,
  Save,
  ArrowRight,
  User,
  BookOpen,
  FlaskConical,
  GraduationCap,
  Code2,
  Link2,
  FileText,
  Award,
  Handshake,
  Star,
} from "lucide-react";

import { Card } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { Tag, TagGroup } from "@/components/ds/Tag";
import { Toggle } from "@/components/ds/Toggle";
import { Badge } from "@/components/ds/Badge";
import { ProgressBar, ProgressRing } from "@/components/ds/Progress";
import { Alert, Banner } from "@/components/ds/Alert";
import { PageLayout } from "@/components/ds/PageLayout";
import {
  NAVY, NAVY_08, EMERALD, WHITE, BRD, SURF2,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED, TYPE,
} from "@/lib/tokens";

// ─── Constants ────────────────────────────────────────────────────────────────

const RESEARCH_AREA_OPTIONS = [
  "Artificial Intelligence", "Machine Learning", "Data Science", "Computer Science",
  "Software Engineering", "Cybersecurity", "Healthcare", "Medicine", "Public Health",
  "Biomedical Sciences", "Biology", "Chemistry", "Physics", "Mathematics", "Statistics",
  "Economics", "Finance", "Management", "Business Administration", "Marketing",
  "Psychology", "Sociology", "Anthropology", "Political Science", "Law",
  "Education", "Engineering", "Environmental Science", "Climate Science",
  "Sustainability", "Energy", "Architecture", "Urban Planning",
  "Philosophy", "History", "Linguistics", "Literature", "Arts",
  "Communications", "Media Studies", "Social Work", "Nursing",
];

const TEACHING_AREA_OPTIONS = [
  "Mathematics", "Statistics", "Computer Science", "Artificial Intelligence",
  "Data Science", "Physics", "Chemistry", "Biology", "Economics",
  "Finance", "Management", "Marketing", "Law", "Psychology",
  "Sociology", "Education", "Engineering", "Medicine", "Nursing",
  "Public Health", "Environmental Science", "History", "Philosophy",
  "Literature", "Linguistics", "Political Science", "Communications",
];

const METHOD_OPTIONS = [
  "Qualitative Research", "Quantitative Research", "Mixed Methods",
  "Systematic Review", "Meta-Analysis", "Literature Review",
  "Randomised Controlled Trial", "Cohort Study", "Case Study",
  "Ethnography", "Grounded Theory", "Content Analysis",
  "Statistical Analysis", "Regression Analysis", "Structural Equation Modelling",
  "Natural Language Processing", "Computer Vision", "Deep Learning",
  "Network Analysis", "Agent-Based Modelling", "Simulation",
  "Survey Research", "Experimental Design", "Action Research",
];

const PROGRAMMING_LANG_OPTIONS = [
  "Python", "R", "MATLAB", "Julia", "SQL", "Java", "JavaScript",
  "TypeScript", "C", "C++", "C#", "Go", "Rust", "Scala",
  "SAS", "Stata", "SPSS", "LaTeX",
];

const SOFTWARE_OPTIONS = [
  "Power BI", "Tableau", "Excel", "SPSS", "NVivo", "ATLAS.ti",
  "Gephi", "QGIS", "ArcGIS", "Mendeley", "Zotero", "EndNote",
  "RevMan", "STATA", "EViews", "EVIEWS", "MAXQDA",
  "TensorFlow", "PyTorch", "scikit-learn", "Pandas", "NumPy",
];

const SKILL_OPTIONS = [
  "Grant Writing", "Academic Writing", "Scientific Communication",
  "Project Management", "Team Leadership", "Data Visualization",
  "Statistical Analysis", "Machine Learning", "Deep Learning",
  "Qualitative Analysis", "Survey Design", "Systematic Reviews",
  "Literature Synthesis", "Peer Review", "Manuscript Editing",
  "Supervision", "Teaching", "Mentoring", "Industry Collaboration",
  "Policy Advising", "Science Communication", "Entrepreneurship",
];

const COLLAB_LOOKING_FOR = [
  "Co-author", "Collaborator", "Mentor", "Mentee", "Reviewer",
  "Editor", "Grant partner", "Postdoc position", "PhD student",
  "Industry partner", "Consultant", "Speaker", "Committee member",
];

const AVAILABILITY_OPTIONS = [
  "Available", "Limited availability", "Not available", "Open to short projects only",
];

const LANGUAGE_OPTIONS = [
  "English", "French", "Spanish", "Portuguese", "German", "Italian",
  "Dutch", "Polish", "Romanian", "Czech", "Hungarian", "Greek",
  "Turkish", "Arabic", "Mandarin Chinese", "Japanese", "Korean",
  "Hindi", "Russian", "Swedish", "Norwegian", "Danish", "Finnish",
];

const USER_TYPES = [
  { value: "undergraduate_student", label: "Undergraduate Student" },
  { value: "masters_student",       label: "Master's Student" },
  { value: "phd_candidate",         label: "PhD Candidate" },
  { value: "postdoctoral_researcher", label: "Postdoctoral Researcher" },
  { value: "researcher",            label: "Researcher" },
  { value: "educator",              label: "Educator" },
  { value: "university_faculty",    label: "University Faculty" },
  { value: "trainer",               label: "Trainer" },
  { value: "industry_professional", label: "Industry Professional" },
];

const PRIMARY_DOMAINS = [
  { value: "research", label: "Research" },
  { value: "teaching", label: "Teaching" },
  { value: "both",     label: "Research & Teaching" },
];

const CAREER_STAGES = [
  { value: "early_career", label: "Early Career" },
  { value: "mid_career",   label: "Mid Career" },
  { value: "senior",       label: "Senior Researcher" },
  { value: "professor",    label: "Professor" },
  { value: "industry",     label: "Industry Professional" },
];

// ─── Section definitions ──────────────────────────────────────────────────────

const SECTIONS = [
  { id: "personal",      label: "Personal Information", icon: User,        weight: 20 },
  { id: "academic",      label: "Academic Information", icon: BookOpen,    weight: 20 },
  { id: "biography",     label: "Biography",            icon: FileText,    weight: 10 },
  { id: "research",      label: "Research Interests",   icon: FlaskConical, weight: 20 },
  { id: "teaching",      label: "Teaching Interests",   icon: GraduationCap, weight: 10 },
  { id: "skills",        label: "Skills & Expertise",   icon: Star,        weight: 15 },
  { id: "tools",         label: "Tools & Languages",    icon: Code2,       weight: 10 },
  { id: "collaboration", label: "Collaboration",        icon: Handshake,   weight: 15 },
  { id: "links",         label: "Academic Links",       icon: Link2,       weight: 10 },
  { id: "awards",        label: "Awards & Memberships", icon: Award,       weight: 5  },
];

// ─── Small reusable components ────────────────────────────────────────────────

/** ChipSelector — multi-select chip group built on the shared Tag component. */
function ChipSelector({ label, hint, selected, options, onToggle, max }) {
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? options : options.slice(0, 18);
  return (
    <div className="sq-form-group">
      <label className="sq-form-label">
        {label}
        {max && <span style={{ marginLeft: 4, fontWeight: 400, color: TEXT_MUTED, textTransform: "none" }}>({selected.length}/{max})</span>}
      </label>
      <TagGroup gap={6}>
        {visible.map((opt) => (
          <Tag key={opt} variant={selected.includes(opt) ? "active" : "default"} onClick={() => onToggle(opt)}>
            {opt}
          </Tag>
        ))}
        {options.length > 18 && (
          <Tag variant="default" onClick={() => setShowAll((s) => !s)} style={{ borderStyle: "dashed", color: TEXT_MUTED }}>
            {showAll ? "Show less" : `+${options.length - 18} more`}
          </Tag>
        )}
      </TagGroup>
      {hint && !max && <p className="sq-form-hint">{hint}</p>}
    </div>
  );
}

/** KeywordInput — free-text tag entry (press Enter or comma to add). */
function KeywordInput({ values, onChange, placeholder }) {
  const [draft, setDraft] = useState("");
  const add = () => {
    const trimmed = draft.trim();
    if (trimmed && !values.includes(trimmed)) onChange([...values, trimmed]);
    setDraft("");
  };
  const handleKey = (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add();
    } else if (e.key === "Backspace" && !draft && values.length > 0) {
      onChange(values.slice(0, -1));
    }
  };
  return (
    <div
      style={{
        border: `1px solid ${BRD}`, borderRadius: 6, padding: 6, minHeight: 40,
        display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", background: WHITE,
      }}
    >
      {values.map((kw) => (
        <Tag key={kw} variant="active" onRemove={() => onChange(values.filter((v) => v !== kw))}>
          {kw}
        </Tag>
      ))}
      <input
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKey}
        onBlur={add}
        placeholder={values.length === 0 ? placeholder : ""}
        style={{ flex: 1, minWidth: 140, fontSize: 13, outline: "none", background: "transparent", border: "none", padding: "4px 2px" }}
      />
    </div>
  );
}

/** CompletionRow — one item in the completion checklist (right rail). */
function CompletionRow({ label, earned, hint }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "6px 0" }}>
      {earned
        ? <CheckCircle2 size={14} style={{ color: EMERALD, flexShrink: 0, marginTop: 1 }} />
        : <Circle size={14} style={{ color: TEXT_DISABLED, flexShrink: 0, marginTop: 1 }} />}
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 12.5, color: earned ? TEXT_PRIMARY : TEXT_SECONDARY, lineHeight: 1.4 }}>{label}</div>
        {!earned && hint && <div style={{ fontSize: 11, color: TEXT_MUTED, lineHeight: 1.4, marginTop: 1 }}>{hint}</div>}
      </div>
    </div>
  );
}

// ─── Section forms ────────────────────────────────────────────────────────────

function SectionPersonal({ form, onChange }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-4">
        <Input label="First Name" value={form.first_name} onChange={(e) => onChange("first_name", e.target.value)} placeholder="Jane" />
        <Input label="Last Name" value={form.last_name} onChange={(e) => onChange("last_name", e.target.value)} placeholder="Smith" />
      </div>
      <Input label="City" value={form.city} onChange={(e) => onChange("city", e.target.value)} placeholder="London" />
      <FormSelect label="Country" value={form.country} onChange={(e) => onChange("country", e.target.value)}>
        <option value="">Select country…</option>
        {COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
      </FormSelect>
      <FormSelect
        label="Languages Spoken"
        value=""
        onChange={(e) => {
          const v = e.target.value;
          if (v && !form.languages.includes(v)) onChange("languages", [...form.languages, v]);
        }}
      >
        <option value="">Add a language…</option>
        {LANGUAGE_OPTIONS.map((l) => <option key={l} value={l}>{l}</option>)}
      </FormSelect>
      {form.languages.length > 0 && (
        <TagGroup>
          {form.languages.map((lang) => (
            <Tag key={lang} variant="active" onRemove={() => onChange("languages", form.languages.filter((l) => l !== lang))}>
              {lang}
            </Tag>
          ))}
        </TagGroup>
      )}
    </div>
  );
}

function SectionAcademic({ form, onChange }) {
  return (
    <div className="flex flex-col gap-4">
      <FormSelect label="Role / User Type" value={form.user_type} onChange={(e) => onChange("user_type", e.target.value)}>
        <option value="">Select your role…</option>
        {USER_TYPES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </FormSelect>
      <FormSelect label="Primary Domain" value={form.primary_domain} onChange={(e) => onChange("primary_domain", e.target.value)}>
        <option value="">Research, Teaching, or Both…</option>
        {PRIMARY_DOMAINS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </FormSelect>
      <FormSelect label="Career Stage" value={form.career_stage} onChange={(e) => onChange("career_stage", e.target.value)}>
        <option value="">Select career stage…</option>
        {CAREER_STAGES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </FormSelect>
      <Input label="Academic Title / Job Title" value={form.academic_role} onChange={(e) => onChange("academic_role", e.target.value)} placeholder="Associate Professor, Research Fellow…" />
      <Input label="Institution" value={form.institution} onChange={(e) => onChange("institution", e.target.value)} placeholder="University of Oxford" />
      <Input label="Department / Faculty" value={form.department} onChange={(e) => onChange("department", e.target.value)} placeholder="Department of Computer Science" />
      <Input label="Scopus Author ID" value={form.scopus_id} onChange={(e) => onChange("scopus_id", e.target.value)} placeholder="57219…" hint="Optional — enables publication imports" />
    </div>
  );
}

function SectionBiography({ form, onChange }) {
  const len = (form.biography || "").trim().length;
  return (
    <div>
      <Textarea
        label="Academic Biography"
        value={form.biography}
        onChange={(e) => onChange("biography", e.target.value)}
        placeholder="Write a short academic biography — your research focus, expertise, achievements, and what you are looking to collaborate on…"
        rows={6}
      />
      <p style={{ fontSize: 12, marginTop: 4, color: len >= 20 ? EMERALD : TEXT_MUTED }}>
        {len} characters{len < 20 ? ` — write at least ${20 - len} more to complete` : " ✓"}
      </p>
    </div>
  );
}

function SectionResearch({ form, onChange }) {
  const toggle = (field, val) => {
    const arr = form[field] || [];
    onChange(field, arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val]);
  };
  return (
    <div className="flex flex-col gap-4">
      <ChipSelector label="Research Areas" selected={form.research_areas} options={RESEARCH_AREA_OPTIONS} onToggle={(v) => toggle("research_areas", v)} />
      <div className="sq-form-group">
        <label className="sq-form-label">Research Keywords <span style={{ fontWeight: 400, textTransform: "none", color: TEXT_MUTED }}>(press Enter to add)</span></label>
        <KeywordInput
          values={form.research_keywords}
          onChange={(v) => onChange("research_keywords", v)}
          placeholder="e.g. clinical NLP, EHR analysis, predictive modelling…"
        />
      </div>
      <ChipSelector label="Research Methods" selected={form.methods || []} options={METHOD_OPTIONS} onToggle={(v) => toggle("methods", v)} />
    </div>
  );
}

function SectionTeaching({ form, onChange }) {
  const toggle = (val) => {
    const arr = form.teaching_areas || [];
    onChange("teaching_areas", arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val]);
  };
  return (
    <div className="flex flex-col gap-4">
      <p style={{ ...TYPE.body, margin: 0 }}>
        Add the subjects and fields you teach or have taught. This makes you discoverable for teaching collaborations, co-teaching invitations, and mentorship.
      </p>
      <ChipSelector label="Teaching Fields" selected={form.teaching_areas || []} options={TEACHING_AREA_OPTIONS} onToggle={toggle} />
      <Toggle
        checked={!!form.available_for_supervision}
        onChange={(v) => onChange("available_for_supervision", v)}
        label="Available to supervise PhD students"
      />
    </div>
  );
}

function SectionSkills({ form, onChange }) {
  const toggle = (field, val) => {
    const arr = form[field] || [];
    onChange(field, arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val]);
  };
  return (
    <div className="flex flex-col gap-4">
      <ChipSelector label="Skills & Competencies" selected={form.skills || []} options={SKILL_OPTIONS} onToggle={(v) => toggle("skills", v)} />
      <ChipSelector label="What I Can Contribute" selected={form.can_contribute || []} options={COLLAB_LOOKING_FOR} onToggle={(v) => toggle("can_contribute", v)} />
      <ChipSelector label="What I Am Looking For" selected={form.looking_for || []} options={COLLAB_LOOKING_FOR} onToggle={(v) => toggle("looking_for", v)} />
    </div>
  );
}

function SectionTools({ form, onChange }) {
  const toggle = (field, val) => {
    const arr = form[field] || [];
    onChange(field, arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val]);
  };
  return (
    <div className="flex flex-col gap-4">
      <ChipSelector label="Programming Languages" selected={form.software_skills || []} options={PROGRAMMING_LANG_OPTIONS} onToggle={(v) => toggle("software_skills", v)} />
      <ChipSelector label="Software & Tools" selected={form.methodological_expertise || []} options={SOFTWARE_OPTIONS} onToggle={(v) => toggle("methodological_expertise", v)} />
    </div>
  );
}

function SectionCollaboration({ form, onChange }) {
  return (
    <div className="flex flex-col gap-4">
      <FormSelect label="Collaboration Availability" value={form.availability} onChange={(e) => onChange("availability", e.target.value)}>
        <option value="">Select availability…</option>
        {AVAILABILITY_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
      </FormSelect>
      <div className="flex flex-col gap-3">
        {[
          { field: "available_for_collaboration", label: "Open to new collaborations" },
          { field: "available_for_reviewing",     label: "Available for peer reviewing" },
          { field: "available_for_consulting",    label: "Available for consulting" },
        ].map(({ field, label }) => (
          <Toggle key={field} checked={!!form[field]} onChange={(v) => onChange(field, v)} label={label} />
        ))}
      </div>
      <Input
        label="Professional Expertise / Specialisations"
        value={(form.professional_expertise || []).join(", ")}
        onChange={(e) => onChange("professional_expertise", e.target.value.split(",").map((x) => x.trim()).filter(Boolean))}
        placeholder="Grant writing, Science communication…"
        hint="Comma-separated list"
      />
    </div>
  );
}

function SectionLinks({ form, onChange }) {
  return (
    <div className="flex flex-col gap-4">
      <Input label="ORCID iD" value={form.orcid_manual} onChange={(e) => onChange("orcid_manual", e.target.value)} placeholder="0000-0000-0000-0000" hint="Connect ORCID in Settings → ORCID for full integration" />
      <Input label="Google Scholar URL" value={form.google_scholar} onChange={(e) => onChange("google_scholar", e.target.value)} placeholder="https://scholar.google.com/citations?user=…" />
      <Input label="ResearchGate URL" value={form.researchgate} onChange={(e) => onChange("researchgate", e.target.value)} placeholder="https://www.researchgate.net/profile/…" />
      <Input label="LinkedIn URL" value={form.linkedin} onChange={(e) => onChange("linkedin", e.target.value)} placeholder="https://linkedin.com/in/…" />
      <Input label="Personal / Lab Website" value={form.website} onChange={(e) => onChange("website", e.target.value)} placeholder="https://yourlab.ac.uk" />
    </div>
  );
}

function SectionAwards({ form, onChange }) {
  return (
    <div className="flex flex-col gap-4">
      <Textarea
        label="Awards & Honours"
        hint="One per line"
        value={(form.awards || []).join("\n")}
        onChange={(e) => onChange("awards", e.target.value.split("\n").map((x) => x.trim()).filter(Boolean))}
        placeholder={"Best Paper Award — ICML 2023\nBritish Academy Fellowship 2022"}
        rows={4}
      />
      <Textarea
        label="Professional Memberships"
        value={(form.memberships || []).join("\n")}
        onChange={(e) => onChange("memberships", e.target.value.split("\n").map((x) => x.trim()).filter(Boolean))}
        placeholder={"IEEE Member\nACM Senior Member"}
        rows={3}
      />
    </div>
  );
}

// ─── Countries list (condensed) ───────────────────────────────────────────────

const COUNTRIES = [
  "Afghanistan", "Albania", "Algeria", "Argentina", "Australia", "Austria",
  "Azerbaijan", "Bangladesh", "Belarus", "Belgium", "Bolivia", "Bosnia and Herzegovina",
  "Brazil", "Bulgaria", "Cambodia", "Cameroon", "Canada", "Chile", "China",
  "Colombia", "Costa Rica", "Croatia", "Czech Republic", "Denmark", "Ecuador",
  "Egypt", "Estonia", "Ethiopia", "Finland", "France", "Georgia", "Germany",
  "Ghana", "Greece", "Guatemala", "Hungary", "India", "Indonesia", "Iran",
  "Iraq", "Ireland", "Israel", "Italy", "Japan", "Jordan", "Kazakhstan",
  "Kenya", "Kuwait", "Latvia", "Lebanon", "Lithuania", "Luxembourg", "Malaysia",
  "Mexico", "Moldova", "Morocco", "Netherlands", "New Zealand", "Nigeria",
  "North Macedonia", "Norway", "Pakistan", "Peru", "Philippines", "Poland",
  "Portugal", "Qatar", "Romania", "Russia", "Saudi Arabia", "Senegal", "Serbia",
  "Singapore", "Slovakia", "Slovenia", "South Africa", "South Korea", "Spain",
  "Sri Lanka", "Sweden", "Switzerland", "Taiwan", "Thailand", "Tunisia",
  "Turkey", "Ukraine", "United Arab Emirates", "United Kingdom", "United States",
  "Uruguay", "Uzbekistan", "Venezuela", "Vietnam", "Zimbabwe",
];

// ─── Left: section navigation (mirrors SettingsNav's active-state language) ───

function ProfileSectionNav({ sections, active, onSelect, sectionStatus }) {
  return (
    <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {sections.map((s) => {
        const Icon = s.icon;
        const done = sectionStatus[s.id];
        const isActive = s.id === active;
        return (
          <button
            key={s.id}
            type="button"
            onClick={() => onSelect(s.id)}
            style={{
              display: "flex", alignItems: "center", gap: 9, width: "100%", padding: "8px 10px",
              border: "none", borderRadius: 7, cursor: "pointer", textAlign: "left",
              background: isActive ? NAVY_08 : "transparent",
              color: isActive ? NAVY : TEXT_MUTED,
              fontWeight: isActive ? 600 : 400,
              transition: "background 100ms",
            }}
            onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = SURF2; }}
            onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = "transparent"; }}
          >
            <Icon size={14} style={{ flexShrink: 0, color: isActive ? NAVY : TEXT_MUTED }} />
            <span style={{ flex: 1, fontSize: 12.5 }}>{s.label}</span>
            {done
              ? <CheckCircle2 size={13} style={{ color: EMERALD, flexShrink: 0 }} />
              : <Circle size={13} style={{ color: TEXT_DISABLED, flexShrink: 0 }} />}
          </button>
        );
      })}
    </nav>
  );
}

// ─── Right: contextual profile guide ──────────────────────────────────────────

function ProfileGuide({ user, score }) {
  const items = getCompletionItems(user);
  const unlocked = score >= COMMUNITY_UNLOCK_THRESHOLD;
  const remaining = items.filter((i) => !i.earned);

  return (
    <Card padding="lg" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <ProgressRing value={score} size="sm" colorByValue />
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY }}>Profile Guide</div>
          <div style={{ fontSize: 11.5, color: TEXT_MUTED, marginTop: 1 }}>
            {unlocked ? "Community unlocked" : `${COMMUNITY_UNLOCK_THRESHOLD - score}% more to unlock`}
          </div>
        </div>
      </div>

      <div
        style={{
          display: "flex", alignItems: "center", gap: 8, padding: "9px 12px", borderRadius: 8,
          background: unlocked ? "#ECFDF5" : SURF2,
          border: `1px solid ${unlocked ? "#A7F3D0" : BRD}`,
        }}
      >
        {unlocked ? <Unlock size={14} style={{ color: EMERALD }} /> : <Lock size={14} style={{ color: TEXT_MUTED }} />}
        <span style={{ fontSize: 12.5, fontWeight: 600, color: unlocked ? "#065F46" : TEXT_SECONDARY }}>
          {unlocked ? "Community Unlocked" : "Community access locked"}
        </span>
      </div>

      <div>
        <div style={{ ...TYPE.label, marginBottom: 8 }}>Completion checklist</div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          {items.map((item) => (
            <CompletionRow key={item.key} label={item.label} earned={item.earned} hint={item.hint} />
          ))}
        </div>
      </div>

      {!unlocked && remaining.length > 0 && (
        <div style={{ borderTop: `1px solid ${BRD}`, paddingTop: 14 }}>
          <div style={{ ...TYPE.label, marginBottom: 8 }}>What you'll unlock</div>
          <p style={{ fontSize: 12.5, color: TEXT_SECONDARY, lineHeight: 1.55, margin: 0 }}>
            Researchers, teams, projects, workspaces, AI tools, and the full Synaptiq community.
          </p>
        </div>
      )}
    </Card>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ProfileSetup() {
  const { user, refreshMe } = useAuth();
  const navigate = useNavigate();

  // Compute orcid_id from user object
  const orcidId =
    user?.orcid && typeof user.orcid === "object"
      ? user.orcid.orcid_id || ""
      : user?.orcid || "";

  const [activeSection, setActiveSection] = useState("personal");
  const [saving, setSaving] = useState(false);
  const [justUnlocked, setJustUnlocked] = useState(false);
  const prevScore = useRef(computeProfileScore(user));

  const [form, setForm] = useState({
    first_name:              user?.first_name || "",
    last_name:               user?.last_name || "",
    city:                    user?.city || "",
    country:                 user?.country || "",
    languages:               user?.languages || [],
    user_type:               user?.user_type || "",
    primary_domain:          user?.primary_domain || "",
    career_stage:            user?.career_stage || "",
    academic_role:           user?.academic_role || "",
    institution:             user?.institution || "",
    department:              user?.department || "",
    scopus_id:               user?.scopus_id || "",
    biography:               user?.biography || "",
    research_areas:          user?.research_areas || [],
    research_keywords:       user?.research_keywords || [],
    methods:                 user?.methods || [],
    teaching_areas:          user?.teaching_areas || [],
    available_for_supervision: user?.available_for_supervision || false,
    skills:                  user?.skills || [],
    can_contribute:          user?.can_contribute || [],
    looking_for:             user?.looking_for || [],
    software_skills:         user?.software_skills || [],
    methodological_expertise: user?.methodological_expertise || [],
    availability:            user?.availability || "",
    available_for_collaboration: user?.available_for_collaboration || false,
    available_for_reviewing: user?.available_for_reviewing || false,
    available_for_consulting: user?.available_for_consulting || false,
    professional_expertise:  user?.professional_expertise || [],
    orcid_manual:            orcidId,
    google_scholar:          user?.google_scholar || "",
    researchgate:            user?.researchgate || "",
    linkedin:                user?.linkedin || "",
    website:                 user?.website || "",
    awards:                  user?.awards || [],
    memberships:             user?.memberships || [],
  });

  const onChange = useCallback((field, value) => {
    setForm((f) => ({ ...f, [field]: value }));
  }, []);

  // Compute live score from form (approximation without refreshing user)
  const liveUser = { ...user, ...form };
  const score = computeProfileScore(liveUser);
  const unlocked = score >= COMMUNITY_UNLOCK_THRESHOLD;

  // Detect unlock crossing
  useEffect(() => {
    if (score >= COMMUNITY_UNLOCK_THRESHOLD && prevScore.current < COMMUNITY_UNLOCK_THRESHOLD) {
      setJustUnlocked(true);
    }
    prevScore.current = score;
  }, [score]);

  // Section completion status (simple heuristics per section)
  const sectionStatus = {
    personal:      !!(form.first_name && form.last_name && form.country),
    academic:      !!(form.user_type && form.institution),
    biography:     form.biography.trim().length > 20,
    research:      form.research_areas.length >= 1 || form.research_keywords.length >= 2,
    teaching:      form.teaching_areas.length >= 1,
    skills:        form.skills.length >= 1 || form.looking_for.length >= 1,
    tools:         form.software_skills.length >= 1 || form.methodological_expertise.length >= 1,
    collaboration: !!form.availability,
    links:         !!(form.google_scholar || form.researchgate || form.linkedin || form.orcid_manual),
    awards:        form.awards.length >= 1 || form.memberships.length >= 1,
  };

  const handleSave = async (andNavigate = false) => {
    setSaving(true);
    try {
      const payload = {
        first_name:          form.first_name,
        last_name:           form.last_name,
        city:                form.city,
        country:             form.country,
        languages:           form.languages,
        user_type:           form.user_type || undefined,
        primary_domain:      form.primary_domain || undefined,
        career_stage:        form.career_stage || undefined,
        academic_role:       form.academic_role,
        institution:         form.institution,
        department:          form.department,
        scopus_id:           form.scopus_id,
        biography:           form.biography,
        research_areas:      form.research_areas,
        research_keywords:   form.research_keywords,
        methods:             form.methods,
        teaching_areas:      form.teaching_areas,
        available_for_supervision: form.available_for_supervision,
        skills:              form.skills,
        can_contribute:      form.can_contribute,
        looking_for:         form.looking_for,
        software_skills:     form.software_skills,
        methodological_expertise: form.methodological_expertise,
        availability:        form.availability || undefined,
        available_for_collaboration: form.available_for_collaboration,
        available_for_reviewing: form.available_for_reviewing,
        available_for_consulting: form.available_for_consulting,
        professional_expertise: form.professional_expertise,
        google_scholar:      form.google_scholar,
        researchgate:        form.researchgate,
        linkedin:            form.linkedin,
        website:             form.website,
        awards:              form.awards,
        memberships:         form.memberships,
      };
      // Remove null/undefined top-level keys
      Object.keys(payload).forEach((k) => {
        if (payload[k] === undefined) delete payload[k];
      });
      await api.patch("/users/me", payload);
      await refreshMe();
      toast.success("Profile saved");
      if (andNavigate) navigate("/discover");
    } catch (e) {
      toast.error("Could not save profile. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const renderSection = () => {
    switch (activeSection) {
      case "personal":      return <SectionPersonal form={form} onChange={onChange} />;
      case "academic":      return <SectionAcademic form={form} onChange={onChange} />;
      case "biography":     return <SectionBiography form={form} onChange={onChange} />;
      case "research":      return <SectionResearch form={form} onChange={onChange} />;
      case "teaching":      return <SectionTeaching form={form} onChange={onChange} />;
      case "skills":        return <SectionSkills form={form} onChange={onChange} />;
      case "tools":         return <SectionTools form={form} onChange={onChange} />;
      case "collaboration": return <SectionCollaboration form={form} onChange={onChange} />;
      case "links":         return <SectionLinks form={form} onChange={onChange} />;
      case "awards":        return <SectionAwards form={form} onChange={onChange} />;
      default:              return null;
    }
  };

  const currentSectionIndex = SECTIONS.findIndex((s) => s.id === activeSection);
  const nextSection = SECTIONS[currentSectionIndex + 1];
  const activeMeta = SECTIONS.find((s) => s.id === activeSection);
  const completedCount = Object.values(sectionStatus).filter(Boolean).length;

  return (
    <div className="min-h-screen" style={{ background: "#FAFAFA" }}>
      <div className="max-w-7xl mx-auto px-6 py-6">
        <PageLayout
          title="Academic Profile Setup"
          subtitle="Complete your profile to join the Synaptiq community"
          actions={
            <>
              <Button variant="ghost" size="md" onClick={() => handleSave(false)} disabled={saving}>
                <Save size={14} /> Save
              </Button>
              <Button
                variant={unlocked ? "primary" : "subtle"}
                size="md"
                onClick={() => handleSave(true)}
                disabled={saving || !unlocked}
                title={!unlocked ? `Complete ${COMMUNITY_UNLOCK_THRESHOLD - score}% more to unlock` : ""}
                style={unlocked ? { background: EMERALD } : undefined}
              >
                {unlocked ? <Unlock size={14} /> : <Lock size={14} />}
                {unlocked ? "Enter Community" : `${COMMUNITY_UNLOCK_THRESHOLD - score}% to unlock`}
                {unlocked && <ArrowRight size={14} />}
              </Button>
            </>
          }
        >
          <div style={{ position: "relative", width: "100%", maxWidth: 420 }}>
            <ProgressBar value={score} label="Profile Completion" colorByValue />
            <div
              aria-hidden="true"
              style={{
                position: "absolute", top: 20, left: `${COMMUNITY_UNLOCK_THRESHOLD}%`,
                width: 2, height: 8, background: NAVY, opacity: 0.35, borderRadius: 1,
              }}
            />
          </div>

          {/* Unlock banner */}
          {justUnlocked && (
            <Banner
              variant="success"
              action={
                <Button variant="ghost" size="sm" onClick={() => handleSave(true)} style={{ color: "#065F46" }}>
                  Enter Community <ArrowRight size={12} />
                </Button>
              }
            >
              <Sparkles size={13} style={{ display: "inline", marginRight: 4, verticalAlign: -2 }} />
              Community unlocked! You can now access researchers, teams, projects, and collaboration features.
            </Banner>
          )}

          <div className="grid gap-6 mt-6" style={{ gridTemplateColumns: "220px 1fr 280px" }}>
          {/* Left: section nav */}
          <aside>
            <Card padding="md" style={{ position: "sticky", top: 24 }}>
              <div style={{ ...TYPE.label, marginBottom: 10 }}>Sections</div>
              <ProfileSectionNav
                sections={SECTIONS}
                active={activeSection}
                onSelect={setActiveSection}
                sectionStatus={sectionStatus}
              />
              <div style={{ marginTop: 14, paddingTop: 14, borderTop: `1px solid ${BRD}`, fontSize: 12, color: TEXT_MUTED }}>
                <span style={{ color: EMERALD, fontWeight: 700 }}>{completedCount}</span> / {SECTIONS.length} sections complete
              </div>
            </Card>
          </aside>

          {/* Main: section form */}
          <main>
            <Card padding="xl">
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20, paddingBottom: 16, borderBottom: `1px solid ${BRD}` }}>
                {activeMeta && <activeMeta.icon size={18} style={{ color: NAVY }} />}
                <h2 style={{ fontSize: 15, fontWeight: 700, color: TEXT_PRIMARY, letterSpacing: "-0.01em", margin: 0 }}>
                  {activeMeta?.label}
                </h2>
                {sectionStatus[activeSection] && (
                  <Badge variant="success" className="ml-auto">Complete ✓</Badge>
                )}
              </div>

              {renderSection()}

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 20, marginTop: 20, borderTop: `1px solid ${BRD}` }}>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const prev = SECTIONS[currentSectionIndex - 1];
                    if (prev) setActiveSection(prev.id);
                  }}
                  disabled={currentSectionIndex === 0}
                  style={{ opacity: currentSectionIndex === 0 ? 0 : 1, border: "none" }}
                >
                  ← Previous
                </Button>
                <Button
                  variant="outline"
                  size="md"
                  onClick={() => {
                    handleSave(false);
                    if (nextSection) setActiveSection(nextSection.id);
                  }}
                >
                  {nextSection ? (
                    <>Save & Next: {nextSection.label} <ChevronRight size={14} /></>
                  ) : (
                    <>Save all changes <Save size={14} /></>
                  )}
                </Button>
              </div>
            </Card>

            {/* Community locked notice */}
            {!unlocked && (
              <Alert
                variant="warning"
                title="Community access is locked"
                icon={Lock}
                style={{ marginTop: 16 }}
              >
                You need <strong>{COMMUNITY_UNLOCK_THRESHOLD - score}% more</strong> to unlock researchers,
                teams, projects, workspaces, AI tools, and the full Synaptiq community.
              </Alert>
            )}
          </main>

          {/* Right: contextual profile guide */}
          <aside style={{ position: "sticky", top: 24 }}>
            <ProfileGuide user={liveUser} score={score} />
          </aside>
        </div>
        </PageLayout>
      </div>
    </div>
  );
}

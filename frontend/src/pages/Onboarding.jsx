import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { formatApiError, getErrorMessage } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { TID } from "../lib/testIds";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, Check } from "lucide-react";
import { ACCENT, NAVY } from "@/lib/tokens";

const RESEARCH_AREAS = ["Artificial Intelligence", "Healthcare", "Management", "Economics", "Education", "Public Health", "Cybersecurity", "Engineering", "Psychology"];

const TEACHING_AREAS = ["Mathematics", "Economics", "Management", "Computer Science", "Medicine", "Engineering", "Psychology", "Education", "Sciences", "Humanities", "Law", "Business"];

const PROFESSIONAL_EXPERTISE = ["Artificial Intelligence", "Cybersecurity", "Public Health", "Project Management", "Innovation", "Data Science", "Finance", "Strategy", "Operations", "R&D", "Product Development", "Sustainability"];

const USER_TYPES = [
  { value: "undergraduate_student",   label: "Undergraduate Student" },
  { value: "masters_student",         label: "Master's Student" },
  { value: "phd_candidate",           label: "PhD Candidate" },
  { value: "postdoctoral_researcher", label: "Postdoctoral Researcher" },
  { value: "researcher",              label: "Researcher" },
  { value: "educator",                label: "Educator" },
  { value: "university_faculty",      label: "University Faculty" },
  { value: "trainer",                 label: "Trainer" },
  { value: "industry_professional",   label: "Industry Professional" },
];

const PRIMARY_DOMAINS = [
  { value: "research", label: "Research" },
  { value: "teaching", label: "Teaching" },
  { value: "both",     label: "Research & Teaching" },
];

const STEPS = [
  { id: "personal",    label: "Personal" },
  { id: "academic",    label: "Academic" },
  { id: "focus",       label: "Focus" },
  { id: "profiles",    label: "Profiles" },
  { id: "experience",  label: "Experience" },
];

// Determine which focus fields to show based on primary_domain + user_type
function getFocusMode(primary_domain, user_type) {
  if (primary_domain === "teaching") return "teaching";
  if (primary_domain === "both")     return "hybrid";
  if (user_type === "industry_professional" || user_type === "trainer") return "industry";
  return "research";
}

export default function Onboarding() {
  const { user, refreshMe } = useAuth();
  const navigate = useNavigate();
  const [step, setStep]     = useState(0);
  const [err, setErr]       = useState("");
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    first_name:         user?.first_name || "",
    last_name:          user?.last_name || "",
    country:            user?.country || "",
    user_type:          user?.user_type || "",
    primary_domain:     user?.primary_domain || "",
    academic_role:      user?.academic_role || "",
    institution:        user?.institution || "",
    department:         user?.department || "",
    research_areas:     user?.research_areas || [],
    teaching_areas:     user?.teaching_areas || [],
    professional_expertise: user?.professional_expertise || [],
    research_interests: user?.research_interests || [],
    research_keywords:  user?.research_keywords || [],
    orcid:              user?.orcid || "",
    google_scholar:     user?.google_scholar || "",
    researchgate:       user?.researchgate || "",
    linkedin:           user?.linkedin || "",
    publications_count: user?.publications_count || 0,
    conferences_count:  user?.conferences_count || 0,
    _interests_text:    (user?.research_interests || []).join(", "),
    _keywords_text:     (user?.research_keywords || []).join(", "),
  });

  const set = (k, v) => setForm({ ...form, [k]: v });

  const toggleArea = (arr, v) => {
    const s = new Set(form[arr]);
    s.has(v) ? s.delete(v) : s.add(v);
    set(arr, Array.from(s));
  };

  const focusMode = getFocusMode(form.primary_domain, form.user_type);
  const showResearchFields  = focusMode === "research" || focusMode === "hybrid" || focusMode === "industry";
  const showTeachingFields  = focusMode === "teaching" || focusMode === "hybrid";
  const showIndustryFields  = focusMode === "industry";

  const validateStep = () => {
    if (step === 0) {
      if (!form.first_name.trim() || !form.last_name.trim() || !form.country.trim())
        return "First name, last name and country are required.";
    }
    if (step === 1) {
      if (!form.user_type) return "Please select what best describes you.";
      if (!form.primary_domain) return "Please select your primary focus.";
      if (!form.institution.trim() || !form.department.trim()) return "Institution and department are required.";
    }
    if (step === 2) {
      if (focusMode === "teaching") {
        if (form.teaching_areas.length === 0) return "Select at least one teaching area.";
      } else if (focusMode === "hybrid") {
        if (form.research_areas.length === 0) return "Select at least one research area.";
        if (form.teaching_areas.length === 0) return "Select at least one teaching area.";
      } else if (focusMode === "industry") {
        if (form.professional_expertise.length === 0 && form.research_areas.length === 0)
          return "Select at least one area of expertise.";
      } else {
        const interests = form._interests_text.split(",").map((s) => s.trim()).filter(Boolean);
        const keywords  = form._keywords_text.split(",").map((s) => s.trim()).filter(Boolean);
        if (form.research_areas.length === 0) return "Select at least one research area.";
        if (interests.length === 0) return "Add at least one research interest.";
        if (keywords.length === 0) return "Add at least one research keyword.";
      }
    }
    return "";
  };

  const next = () => {
    const e = validateStep();
    if (e) { setErr(e); return; }
    setErr("");
    setStep(Math.min(step + 1, STEPS.length - 1));
  };
  const back = () => { setErr(""); setStep(Math.max(0, step - 1)); };

  const submit = async () => {
    const e = validateStep();
    if (e) { setErr(e); return; }
    setSaving(true);
    setErr("");
    try {
      const interests = form._interests_text.split(",").map((s) => s.trim()).filter(Boolean);
      const keywords  = form._keywords_text.split(",").map((s) => s.trim()).filter(Boolean);
      const payload = {
        first_name:         form.first_name.trim(),
        last_name:          form.last_name.trim(),
        country:            form.country.trim(),
        user_type:          form.user_type,
        primary_domain:     form.primary_domain,
        academic_role:      form.academic_role.trim(),
        institution:        form.institution.trim(),
        department:         form.department.trim(),
        research_areas:     form.research_areas,
        teaching_areas:     form.teaching_areas.length > 0 ? form.teaching_areas : undefined,
        professional_expertise: form.professional_expertise.length > 0 ? form.professional_expertise : undefined,
        research_interests: interests,
        research_keywords:  keywords,
        orcid:              form.orcid.trim(),
        google_scholar:     form.google_scholar.trim(),
        researchgate:       form.researchgate.trim(),
        linkedin:           form.linkedin.trim(),
        publications_count: parseInt(form.publications_count) || 0,
        conferences_count:  parseInt(form.conferences_count) || 0,
      };
      await api.post("/users/me/onboarding", payload);
      await refreshMe();
      toast.success("Welcome to Synaptiq");
      navigate("/profile-setup", { replace: true });
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || getErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const step2Title =
    focusMode === "teaching"  ? "What you teach." :
    focusMode === "hybrid"    ? "Your research and teaching focus." :
    focusMode === "industry"  ? "Your expertise and focus." :
    "What you research.";

  const step2Sub =
    focusMode === "teaching"  ? "This drives network matching and helps educators and trainers find you." :
    focusMode === "hybrid"    ? "Select both your research areas and teaching areas. Both drive AI matching." :
    focusMode === "industry"  ? "Select your professional expertise and any research areas relevant to your work." :
    "This drives Discover and AI matching. Be specific — keywords help collaborators find you.";

  return (
    <div className="min-h-screen bg-[#FDFDFB] py-12 px-6">
      <div data-testid={TID.onboardingForm} className="max-w-3xl mx-auto bg-white border border-slate-200">
        {/* Progress */}
        <div className="px-10 pt-8">
          <div className="overline">Step {step + 1} of {STEPS.length} · {STEPS[step].label}</div>
          <div className="mt-3 flex gap-1">
            {STEPS.map((_, i) => (
              <div key={i} className={`flex-1 h-1 ${i <= step ? "bg-[#0F2847]" : "bg-slate-200"}`} />
            ))}
          </div>
        </div>

        <div className="px-10 py-8 space-y-6">
          {/* ── Step 0: Personal ────────────────────────── */}
          {step === 0 && (
            <>
              <h2 className="font-serif text-3xl text-slate-900">A little about you.</h2>
              <p className="text-slate-600 text-sm">We use this for your profile and to connect you with peers nearby.</p>
              <div className="grid sm:grid-cols-2 gap-5">
                <Field label="First name"  testid={TID.onbFirstName} value={form.first_name} onChange={(v) => set("first_name", v)} required />
                <Field label="Last name"   testid={TID.onbLastName}  value={form.last_name}  onChange={(v) => set("last_name", v)}  required />
                <Field label="Country"     testid={TID.onbCountry}   value={form.country}    onChange={(v) => set("country", v)}    placeholder="e.g. Switzerland" required />
              </div>
            </>
          )}

          {/* ── Step 1: Academic identity ────────────────── */}
          {step === 1 && (
            <>
              <h2 className="font-serif text-3xl text-slate-900">Your academic identity.</h2>
              <p className="text-slate-600 text-sm">Where you work, and what you do there.</p>
              <div className="grid sm:grid-cols-2 gap-5">
                <SelectField label="Which best describes you?" testid={TID.onbRole} value={form.user_type} onChange={(v) => set("user_type", v)} options={USER_TYPES} required />
                <SelectField label="What is your primary focus?" value={form.primary_domain} onChange={(v) => set("primary_domain", v)} options={PRIMARY_DOMAINS} required />
                <Field label="Institution" testid={TID.onbInstitution} value={form.institution} onChange={(v) => set("institution", v)} placeholder="ETH Zürich" required />
                <Field label="Department"  testid={TID.onbDepartment}  value={form.department}  onChange={(v) => set("department", v)}  placeholder="Computer Science" required />
                <Field
                  label="Job title"
                  value={form.academic_role}
                  onChange={(v) => set("academic_role", v)}
                  placeholder="e.g. Associate Professor of Management"
                  className="sm:col-span-2"
                />
              </div>
            </>
          )}

          {/* ── Step 2: Focus fields (adaptive) ─────────── */}
          {step === 2 && (
            <>
              <h2 className="font-serif text-3xl text-slate-900">{step2Title}</h2>
              <p className="text-slate-600 text-sm">{step2Sub}</p>

              {/* Research fields */}
              {showResearchFields && (
                <>
                  <ChipBlock
                    label="Research areas"
                    testidPrefix={TID.onbAreaChip}
                    options={RESEARCH_AREAS}
                    selected={form.research_areas}
                    onToggle={(v) => toggleArea("research_areas", v)}
                    required={focusMode === "research"}
                  />
                  {focusMode === "research" && (
                    <>
                      <Field label="Research interests (comma-separated)" testid={TID.onbInterests} value={form._interests_text} onChange={(v) => set("_interests_text", v)} placeholder="e.g. explainable ML, fairness, clinical NLP" />
                      <Field label="Research keywords (comma-separated)"  testid={TID.onbKeywords}  value={form._keywords_text}  onChange={(v) => set("_keywords_text", v)}  placeholder="e.g. SHAP, RCT, fMRI" />
                    </>
                  )}
                </>
              )}

              {/* Professional expertise (industry / hybrid-industry) */}
              {showIndustryFields && (
                <ChipBlock
                  label="Professional expertise"
                  options={PROFESSIONAL_EXPERTISE}
                  selected={form.professional_expertise}
                  onToggle={(v) => toggleArea("professional_expertise", v)}
                />
              )}

              {/* Teaching areas */}
              {showTeachingFields && (
                <ChipBlock
                  label="Teaching areas"
                  options={TEACHING_AREAS}
                  selected={form.teaching_areas}
                  onToggle={(v) => toggleArea("teaching_areas", v)}
                  required={focusMode === "teaching" || focusMode === "hybrid"}
                />
              )}

              {/* Hybrid: also show text fields for research interests/keywords */}
              {focusMode === "hybrid" && (
                <>
                  <Field label="Research interests (comma-separated)" testid={TID.onbInterests} value={form._interests_text} onChange={(v) => set("_interests_text", v)} placeholder="e.g. explainable ML, fairness, clinical NLP" />
                  <Field label="Research keywords (comma-separated)"  testid={TID.onbKeywords}  value={form._keywords_text}  onChange={(v) => set("_keywords_text", v)}  placeholder="e.g. SHAP, RCT, fMRI" />
                </>
              )}
            </>
          )}

          {/* ── Step 3: Scholarly profiles ───────────────── */}
          {step === 3 && (
            <>
              <h2 className="font-serif text-3xl text-slate-900">Link your scholarly identity.</h2>
              <p className="text-slate-600 text-sm">All optional, all editable later. Linking ORCID enables live publication sync and the ORCID Verified badge across the platform.</p>
              <div className="grid sm:grid-cols-2 gap-5">
                <Field label="ORCID"             testid={TID.onbOrcid}    value={form.orcid}         onChange={(v) => set("orcid", v)}         placeholder="0000-0002-1825-0097" />
                <Field label="Google Scholar ID"  testid={TID.onbScholar}  value={form.google_scholar} onChange={(v) => set("google_scholar", v)} />
                <Field label="ResearchGate URL"   testid={TID.onbRgate}    value={form.researchgate}   onChange={(v) => set("researchgate", v)} />
                <Field label="LinkedIn URL"        testid={TID.onbLinkedin} value={form.linkedin}       onChange={(v) => set("linkedin", v)} />
              </div>
            </>
          )}

          {/* ── Step 4: Track record ─────────────────────── */}
          {step === 4 && (
            <>
              <h2 className="font-serif text-3xl text-slate-900">A little track record.</h2>
              <p className="text-slate-600 text-sm">Approximate numbers — these feed your analytics dashboard and matching.</p>
              <div className="grid sm:grid-cols-2 gap-5">
                <Field label="Publications (approx.)"        type="number" testid={TID.onbPubs}  value={form.publications_count} onChange={(v) => set("publications_count", v)} />
                <Field label="Conferences attended (approx.)" type="number" testid={TID.onbConfs} value={form.conferences_count}  onChange={(v) => set("conferences_count", v)} />
              </div>
              <div className="mt-4 border-l-2 border-[#0F2847] pl-4 text-sm text-slate-600">
                You can refine your full profile at any time from Settings → Profile.
              </div>
            </>
          )}

          {err && <div data-testid={TID.onbError} className="text-sm text-[#8A1538] border-l-2 border-[#8A1538] pl-3 py-1">{err}</div>}
        </div>

        <div className="px-10 py-5 border-t border-slate-200 flex items-center justify-between">
          <button type="button" onClick={back} disabled={step === 0} className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 disabled:opacity-30">
            <ChevronLeft size={14} strokeWidth={1.5} /> Back
          </button>
          {step < STEPS.length - 1 ? (
            <button data-testid={TID.onbNext} type="button" onClick={next} className="inline-flex items-center gap-2 bg-[#0F2847] text-white px-5 py-2.5 text-sm hover:bg-slate-800">
              Continue <ChevronRight size={14} strokeWidth={1.5} />
            </button>
          ) : (
            <button data-testid={TID.onboardingSubmit} onClick={submit} disabled={saving} className="inline-flex items-center gap-2 bg-[#0F2847] text-white px-5 py-2.5 text-sm hover:bg-slate-800 disabled:opacity-50">
              <Check size={14} strokeWidth={1.5} /> {saving ? "Finalising…" : "Complete onboarding"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function Field({ label, value, onChange, placeholder, type = "text", required, testid, className }) {
  return (
    <div className={className}>
      <label className="overline block mb-2">{label}{required && <span className="text-[#8A1538] ml-1">*</span>}</label>
      <input data-testid={testid} type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} required={required} className="w-full px-3 py-2 border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847]" />
    </div>
  );
}

function SelectField({ label, value, onChange, options, required, testid }) {
  return (
    <div>
      <label className="overline block mb-2">{label}{required && <span className="text-[#8A1538] ml-1">*</span>}</label>
      <select data-testid={testid} value={value} onChange={(e) => onChange(e.target.value)} required={required} className="w-full px-3 py-2 border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-[#0F2847]">
        <option value="">Select…</option>
        {options.map((o) => <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>)}
      </select>
    </div>
  );
}

function ChipBlock({ label, options, selected, onToggle, testidPrefix, required }) {
  return (
    <div>
      <label className="overline block mb-3">{label}{required && <span className="text-[#8A1538] ml-1">*</span>}</label>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o}
            type="button"
            data-testid={testidPrefix ? `${testidPrefix}-${o.toLowerCase().replace(/\s/g, "-")}` : undefined}
            onClick={() => onToggle(o)}
            className={`px-3 py-1.5 text-xs border ${selected.includes(o) ? "bg-[#0F2847] text-white border-[#0F2847]" : "bg-white text-slate-700 border-slate-300 hover:border-slate-500"}`}
          >
            {o}
          </button>
        ))}
      </div>
    </div>
  );
}

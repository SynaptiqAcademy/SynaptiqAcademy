import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FlaskConical, Lock, RotateCcw, Clock, ChevronDown, ChevronUp,
  AlertTriangle, CheckCircle2, XCircle, Target, Layers,
  BarChart2, Users, Database, Shield, BookOpen, Lightbulb,
  ListChecks, ClipboardList, TrendingUp,
} from "lucide-react";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { NAVY, WARM } from "@/lib/tokens";
import { ErrorState } from "@/components/ds/ErrorState";
import { AIWorkspaceLayout } from "@/layouts";



// ─────────────────────── shared primitives ───────────────────────────────────

function SectionHeader({ icon: Icon, label, color = "#0F2847" }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon size={15} strokeWidth={1.5} style={{ color }} />
      <div className="overline" style={{ color }}>{label}</div>
    </div>
  );
}

function Tag({ children, className = "" }) {
  return (
    <span className={`inline-block border border-slate-200 text-slate-600 text-xs px-2 py-0.5 ${className}`}>
      {children}
    </span>
  );
}

function BulletList({ items }) {
  if (!items?.length) return null;
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2.5 text-sm text-slate-700 leading-relaxed">
          <span className="mt-2 w-1 h-1 rounded-full bg-slate-400 shrink-0" />
          <span>{typeof item === "string" ? item : JSON.stringify(item)}</span>
        </li>
      ))}
    </ul>
  );
}

function LabelValue({ label, value }) {
  if (!value && value !== 0) return null;
  return (
    <div>
      <div className="text-xs text-slate-500 overline mb-0.5">{label}</div>
      <div className="text-sm text-slate-700 leading-relaxed">{String(value)}</div>
    </div>
  );
}

function ExpandCard({ title, subtitle, badge, badgeColor, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const Chev = open ? ChevronUp : ChevronDown;
  return (
    <div className="border border-slate-200 bg-white">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-start justify-between gap-4 px-5 py-4 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="font-serif text-base text-slate-900 leading-snug">{title}</div>
          {subtitle && <div className="text-sm text-slate-500 mt-0.5 leading-snug">{subtitle}</div>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {badge && (
            <span
              className="text-xs px-2 py-0.5 border font-mono"
              style={badgeColor
                ? { borderColor: badgeColor, color: badgeColor }
                : { borderColor: "#e2e8f0", color: "#64748b" }
              }
            >
              {badge}
            </span>
          )}
          <Chev size={15} strokeWidth={1.5} className="text-slate-400" />
        </div>
      </button>
      {open && (
        <div className="border-t border-slate-100 px-5 pb-5 pt-4">
          {children}
        </div>
      )}
    </div>
  );
}

// ─────────────────────── score bar ───────────────────────────────────────────

function ScoreBar({ label, score }) {
  const color = score >= 8 ? "#16a34a" : score >= 6 ? "#d97706" : "#dc2626";
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-500">{label}</span>
        <span className="text-xs font-mono text-slate-600">{score}/10</span>
      </div>
      <div className="h-1.5 bg-slate-100">
        <div className="h-full transition-all" style={{ width: `${score * 10}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

// ─────────────────────── publication score ring ───────────────────────────────

function ScoreRing({ score }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score));
  const offset = circ * (1 - pct / 100);
  const color = pct >= 80 ? "#16a34a" : pct >= 60 ? "#d97706" : pct >= 40 ? "#ea580c" : "#dc2626";
  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={88} height={88} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={44} cy={44} r={r} fill="none" stroke="#e2e8f0" strokeWidth={6} />
        <circle cx={44} cy={44} r={r} fill="none" stroke={color} strokeWidth={6}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="butt" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-serif text-xl text-slate-900">{score}</span>
        <span className="text-[9px] text-slate-500 -mt-0.5">/ 100</span>
      </div>
    </div>
  );
}

// ─────────────────────── design type badge ───────────────────────────────────

function DesignBadge({ type }) {
  const map = {
    qualitative:   { color: "#7c3aed", label: "Qualitative" },
    quantitative:  { color: "#2563eb", label: "Quantitative" },
    mixed_methods: { color: "#0F2847", label: "Mixed Methods" },
  };
  const cfg = map[type?.toLowerCase()] || { color: "#64748b", label: type || "Unknown" };
  return (
    <span className="text-xs px-3 py-1 border font-mono"
      style={{ borderColor: cfg.color, color: cfg.color }}>
      {cfg.label}
    </span>
  );
}

function PriorityIcon({ level }) {
  if (level === "high") return <XCircle size={14} className="text-red-500 shrink-0 mt-0.5" />;
  if (level === "medium") return <AlertTriangle size={14} className="text-amber-500 shrink-0 mt-0.5" />;
  return <CheckCircle2 size={14} className="text-slate-400 shrink-0 mt-0.5" />;
}

// ─────────────────────── gate view ───────────────────────────────────────────

function GateView() {
  return (
    <div className="min-h-screen bg-[#F4F6FA]">
      <div style={{ background: "#F4F6FA", padding: "13px 32px", borderBottom: "1px solid rgba(15,23,42,0.08)" }}>
      </div>
      <div className="flex items-center justify-center p-8" style={{ minHeight: "calc(100vh - 50px)" }}>
      <div className="max-w-md w-full text-center space-y-6">
        <div className="w-14 h-14 border-2 border-slate-900 flex items-center justify-center mx-auto">
          <Lock size={22} strokeWidth={1.5} />
        </div>
        <div>
          <h1 className="font-serif text-2xl text-slate-900 mb-2">Pro Researcher Required</h1>
          <p className="text-slate-600 text-sm leading-relaxed">
            AI Research Design Advisor requires a Pro Researcher or Institution plan.
            Transform any research idea into a defensible, publishable study design.
          </p>
        </div>
        <div className="border border-slate-200 bg-white p-4 text-left space-y-2">
          <div className="text-xs overline text-slate-500 mb-3">Included in this advisory</div>
          {[
            "Methodology recommendation with justification",
            "Research framework & theoretical structure",
            "Hypothesis development (H1–H4)",
            "Full variables, sampling & data collection plan",
            "Threats to validity & ethical considerations",
            "Publication readiness score (0–100)",
            "Prioritised improvement plan",
          ].map((f) => (
            <div key={f} className="flex items-center gap-2 text-sm text-slate-700">
              <CheckCircle2 size={13} className="text-[#0F2847] shrink-0" />
              {f}
            </div>
          ))}
        </div>
        <Link
          to="/pricing"
          className="inline-block w-full bg-[#0F2847] text-white text-sm font-medium py-3 px-6 hover:bg-[#1a3a5c] transition-colors"
        >
          Upgrade to Pro Researcher
        </Link>
        <p className="text-xs text-slate-500">10 credits per advisory · Refunded if advisory fails</p>
      </div>
      </div>
    </div>
  );
}

// ─────────────────────── input form view ─────────────────────────────────────

function InputView({ onResult }) {
  const [topic, setTopic] = useState("");
  const [question, setQuestion] = useState("");
  const [objective, setObjective] = useState("");
  const [showOptional, setShowOptional] = useState(false);
  const [discipline, setDiscipline] = useState("");
  const [journalType, setJournalType] = useState("");
  const [methodology, setMethodology] = useState("");
  const [population, setPopulation] = useState("");
  const [sampleSize, setSampleSize] = useState("");
  const [dataSources, setDataSources] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const isGated = error?.status === 402;

  const submit = async (e) => {
    e.preventDefault();
    if (!topic.trim() || !question.trim() || !objective.trim()) {
      setError({ message: "Topic, research question, and research objective are required." });
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const body = {
        topic: topic.trim(),
        research_question: question.trim(),
        research_objective: objective.trim(),
        ...(discipline && { discipline }),
        ...(journalType && { target_journal_type: journalType }),
        ...(methodology && { preferred_methodology: methodology }),
        ...(population && { target_population: population }),
        ...(sampleSize && { expected_sample_size: sampleSize }),
        ...(dataSources && { available_data_sources: dataSources }),
      };
      const { data } = await api.post("/research-design-advisor", body, { timeout: 180000 });
      onResult(data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 402) {
        setError({ status: 402, message: detail?.message || "Plan upgrade required." });
      } else {
        setError({ message: detail?.message || detail || "Advisory failed. Please try again." });
      }
    } finally {
      setLoading(false);
    }
  };

  if (isGated) return <GateView />;

  return (
    <div className="min-h-screen bg-[#F4F6FA]">
      <div style={{ background: "#F4F6FA", padding: "13px 32px", borderBottom: "1px solid rgba(15,23,42,0.08)" }}>
      </div>
      <div className="max-w-2xl mx-auto py-12 px-6">
        {/* header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 border-2 border-[#0F2847] flex items-center justify-center">
              <FlaskConical size={18} strokeWidth={1.5} className="text-[#0F2847]" />
            </div>
            <div>
              <h1 className="font-serif text-2xl text-slate-900">AI Research Design Advisor</h1>
              <p className="text-xs text-slate-500 mt-0.5">Pro Researcher · 10 credits per advisory</p>
            </div>
          </div>
          <p className="text-slate-600 text-sm leading-relaxed">
            Transform your research idea into a methodologically defensible study design —
            including framework, hypotheses, sampling strategy, analysis plan, and a
            prioritised improvement roadmap.
          </p>
        </div>

        {/* form */}
        <form onSubmit={submit} data-testid={TID.researchDesignForm} className="space-y-5">
          {/* topic */}
          <div>
            <label className="overline block mb-1.5">Research Topic *</label>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Digital health interventions for Type 2 diabetes self-management"
              className="w-full border border-slate-300 px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
              maxLength={300}
              data-testid={TID.researchDesignTopic}
            />
          </div>

          {/* research question */}
          <div>
            <label className="overline block mb-1.5">Research Question *</label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. To what extent do smartphone-based self-monitoring apps improve glycaemic control in adults with Type 2 diabetes compared to standard care over 12 months?"
              rows={3}
              className="w-full border border-slate-300 px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors resize-none"
              maxLength={1000}
              data-testid={TID.researchDesignQuestion}
            />
          </div>

          {/* research objective */}
          <div>
            <label className="overline block mb-1.5">Research Objective *</label>
            <textarea
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="e.g. To evaluate the effectiveness of a smartphone-based self-monitoring intervention on HbA1c levels, medication adherence, and quality of life in adults with Type 2 diabetes over a 12-month period."
              rows={3}
              className="w-full border border-slate-300 px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors resize-none"
              maxLength={1000}
              data-testid={TID.researchDesignObjective}
            />
          </div>

          {/* optional section toggle */}
          <button
            type="button"
            onClick={() => setShowOptional((v) => !v)}
            className="flex items-center gap-2 text-sm text-slate-500 hover:text-[#0F2847] transition-colors"
          >
            {showOptional ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {showOptional ? "Hide" : "Show"} optional refinements
          </button>

          {showOptional && (
            <div className="border border-slate-200 bg-white p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="overline block mb-1.5">Discipline</label>
                  <input
                    value={discipline}
                    onChange={(e) => setDiscipline(e.target.value)}
                    placeholder="e.g. Public Health"
                    className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                    maxLength={100}
                  />
                </div>
                <div>
                  <label className="overline block mb-1.5">Target Journal Type</label>
                  <input
                    value={journalType}
                    onChange={(e) => setJournalType(e.target.value)}
                    placeholder="e.g. High-impact clinical"
                    className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                    maxLength={200}
                  />
                </div>
              </div>
              <div>
                <label className="overline block mb-1.5">Preferred Methodology</label>
                <input
                  value={methodology}
                  onChange={(e) => setMethodology(e.target.value)}
                  placeholder="e.g. RCT, mixed methods, systematic review"
                  className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                  maxLength={200}
                />
              </div>
              <div>
                <label className="overline block mb-1.5">Target Population</label>
                <input
                  value={population}
                  onChange={(e) => setPopulation(e.target.value)}
                  placeholder="e.g. Adults aged 40–70 with diagnosed Type 2 diabetes"
                  className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                  maxLength={300}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="overline block mb-1.5">Expected Sample Size</label>
                  <input
                    value={sampleSize}
                    onChange={(e) => setSampleSize(e.target.value)}
                    placeholder="e.g. 200 participants"
                    className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                    maxLength={100}
                  />
                </div>
                <div>
                  <label className="overline block mb-1.5">Available Data Sources</label>
                  <input
                    value={dataSources}
                    onChange={(e) => setDataSources(e.target.value)}
                    placeholder="e.g. Hospital EHR, patient surveys"
                    className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                    maxLength={500}
                  />
                </div>
              </div>
            </div>
          )}

          {error && !isGated && (
            <ErrorState message={error.message} type="generic" />
          )}

          <button
            type="submit"
            disabled={loading}
            data-testid={TID.researchDesignSubmitBtn}
            className="w-full bg-[#0F2847] text-white text-sm font-medium py-3 px-6 hover:bg-[#1a3a5c] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <RotateCcw size={14} className="animate-spin" />
                Designing your study… (up to 3 min)
              </span>
            ) : (
              "Design My Study — 10 Credits"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

// ─────────────────────── result view ─────────────────────────────────────────

function VariableTable({ items, columns }) {
  if (!items?.length) return <p className="text-sm text-slate-400">None identified.</p>;
  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div key={i} className="border border-slate-100 bg-slate-50 p-4 space-y-2">
          {columns.map(([key, label]) => item[key] ? (
            <LabelValue key={key} label={label} value={item[key]} />
          ) : null)}
        </div>
      ))}
    </div>
  );
}

function ValiditySection({ threats, label, color }) {
  if (!threats?.length) return null;
  return (
    <div>
      <div className="text-xs overline mb-2" style={{ color }}>{label}</div>
      <div className="space-y-3">
        {threats.map((t, i) => (
          <div key={i} className="border border-slate-100 bg-slate-50 p-4 space-y-2">
            <div className="font-medium text-sm text-slate-900">{t.threat}</div>
            <LabelValue label="Risk" value={t.description} />
            <LabelValue label="Mitigation" value={t.mitigation} />
          </div>
        ))}
      </div>
    </div>
  );
}

function ImprovementList({ items, level }) {
  const configs = {
    high:   { color: "#dc2626", bg: "bg-red-50",   border: "border-red-100",   label: "High Priority" },
    medium: { color: "#d97706", bg: "bg-amber-50", border: "border-amber-100", label: "Medium Priority" },
    low:    { color: "#64748b", bg: "bg-slate-50",  border: "border-slate-100", label: "Low Priority" },
  };
  const cfg = configs[level];
  if (!items?.length) return null;
  return (
    <div>
      <div className="text-xs overline mb-2" style={{ color: cfg.color }}>{cfg.label}</div>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className={`border ${cfg.border} ${cfg.bg} p-4 space-y-1.5`}>
            <div className="flex items-start gap-2">
              <PriorityIcon level={level} />
              <div className="font-medium text-sm text-slate-900">{item.action}</div>
            </div>
            {item.reason && (
              <p className="text-xs text-slate-500 leading-relaxed ml-5">{item.reason}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ResultView({ data, onReset }) {
  const r = data.review_json || {};
  const design = r.research_design_recommendation || {};
  const framework = r.research_framework || {};
  const objAssess = r.research_objectives_assessment || {};
  const hypoSection = r.hypothesis_development || {};
  const variables = r.variables || {};
  const sampling = r.sampling_strategy || {};
  const dataCol = r.data_collection_strategy || {};
  const analysis = r.data_analysis_plan || {};
  const validity = r.threats_to_validity || {};
  const ethics = r.ethical_considerations || {};
  const pubReady = r.publication_readiness || {};
  const improvement = r.improvement_plan || {};

  const potColor = (pubReady.score >= 80) ? "#16a34a" : (pubReady.score >= 60) ? "#d97706" : "#dc2626";

  return (
    <div className="min-h-screen bg-[#F4F6FA]" data-testid={TID.researchDesignResult}>
      <div style={{ background: "#F4F6FA", padding: "13px 32px", borderBottom: "1px solid rgba(15,23,42,0.08)" }}>
      </div>
      {/* sticky header */}
      <div className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h1 className="font-serif text-lg text-slate-900 truncate">{data.topic}</h1>
            <p className="text-xs text-slate-500 mt-0.5 truncate">{data.research_question}</p>
          </div>
          <button
            onClick={onReset}
            className="shrink-0 flex items-center gap-1.5 text-sm text-slate-600 border border-slate-300 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
          >
            <RotateCcw size={13} />
            New Advisory
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">

        {/* design recommendation + publication score */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2 border border-slate-200 bg-white p-6 space-y-4">
            <SectionHeader icon={Target} label="Research Design Recommendation" />
            <div className="flex flex-wrap gap-2">
              <DesignBadge type={design.recommended_design} />
              {design.design_type && (
                <span className="text-xs border border-slate-200 px-2 py-1 text-slate-600 font-mono">
                  {design.design_type}
                </span>
              )}
            </div>
            {design.justification && (
              <p className="text-sm text-slate-700 leading-relaxed">{design.justification}</p>
            )}
            {design.alternative_considered && (
              <div className="border border-slate-100 bg-slate-50 p-3">
                <div className="text-xs overline text-slate-500 mb-1">Alternative Considered</div>
                <p className="text-sm text-slate-600">{design.alternative_considered}</p>
              </div>
            )}
            {design.feasibility_note && (
              <div className="border border-amber-100 bg-amber-50 p-3">
                <div className="text-xs overline text-amber-700 mb-1">Feasibility Note</div>
                <p className="text-sm text-amber-800">{design.feasibility_note}</p>
              </div>
            )}
          </div>

          {/* publication readiness */}
          <div className="border border-slate-200 bg-white p-6 flex flex-col items-center justify-center text-center gap-3">
            <div className="overline text-slate-500">Publication Readiness</div>
            <ScoreRing score={pubReady.score || 0} />
            {pubReady.recommended_target_journals && (
              <p className="text-xs text-slate-500 leading-snug">{pubReady.recommended_target_journals}</p>
            )}
          </div>
        </div>

        {/* objectives assessment */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={ClipboardList} label="Research Objectives Assessment" color="#2563eb" />
          <div className="grid grid-cols-3 gap-4 mb-5">
            <ScoreBar label="Clarity" score={objAssess.clarity_score || 0} />
            <ScoreBar label="Measurability" score={objAssess.measurability_score || 0} />
            <ScoreBar label="Alignment" score={objAssess.alignment_score || 0} />
          </div>
          <div className="space-y-3">
            {objAssess.overall_assessment && (
              <p className="text-sm text-slate-700 leading-relaxed">{objAssess.overall_assessment}</p>
            )}
            {objAssess.refined_objective && (
              <div className="border border-[#0F2847] bg-slate-50 p-4">
                <div className="text-xs overline text-[#0F2847] mb-1">Refined Objective</div>
                <p className="text-sm text-slate-700 leading-relaxed italic">{objAssess.refined_objective}</p>
              </div>
            )}
          </div>
        </div>

        {/* research framework */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={Layers} label="Research Framework" color="#7c3aed" />
          <div className="space-y-4">
            <LabelValue label="Conceptual Model" value={framework.conceptual_model} />
            <LabelValue label="Theoretical Structure" value={framework.theoretical_structure} />
            {framework.framework_rationale && (
              <LabelValue label="Framework Rationale" value={framework.framework_rationale} />
            )}
            {framework.key_constructs?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Key Constructs</div>
                <div className="space-y-2">
                  {framework.key_constructs.map((c, i) => (
                    <div key={i} className="border border-slate-100 bg-slate-50 p-3 flex gap-3">
                      <span className="text-xs border border-slate-300 px-1.5 py-0.5 font-mono text-slate-500 shrink-0 h-fit capitalize">
                        {c.role}
                      </span>
                      <div>
                        <div className="text-sm font-medium text-slate-900">{c.construct}</div>
                        {c.definition && <div className="text-xs text-slate-500 mt-0.5">{c.definition}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* hypotheses */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={Lightbulb} label="Hypothesis Development" color="#16a34a" />
          {hypoSection.hypotheses_appropriate === false ? (
            <div className="border border-amber-100 bg-amber-50 p-4">
              <div className="text-xs overline text-amber-700 mb-1">Hypotheses Not Applicable</div>
              <p className="text-sm text-amber-800">{hypoSection.hypotheses_not_appropriate_reason}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {(hypoSection.hypotheses || []).map((h, i) => (
                <ExpandCard
                  key={i}
                  title={`${h.id}: ${h.statement}`}
                  badge={h.test_type}
                  defaultOpen={i === 0}
                >
                  <div className="space-y-3">
                    <LabelValue label="Null Hypothesis" value={h.null_hypothesis} />
                    <LabelValue label="Rationale" value={h.rationale} />
                    <LabelValue label="Statistical Test" value={h.test_type} />
                  </div>
                </ExpandCard>
              ))}
            </div>
          )}
        </div>

        {/* variables */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={Database} label="Variables" color="#0F2847" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="text-xs overline text-[#0F2847] mb-2">Independent Variables</div>
              <VariableTable items={variables.independent_variables}
                columns={[["variable","Variable"],["operationalisation","Operationalisation"],["measurement_level","Measurement Level"]]} />
            </div>
            <div>
              <div className="text-xs overline text-[#2563eb] mb-2">Dependent Variables</div>
              <VariableTable items={variables.dependent_variables}
                columns={[["variable","Variable"],["operationalisation","Operationalisation"],["measurement_level","Measurement Level"]]} />
            </div>
          </div>
          {(variables.moderators?.length > 0 || variables.mediators?.length > 0 || variables.control_variables?.length > 0) && (
            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
              {variables.moderators?.length > 0 && (
                <div>
                  <div className="text-xs overline text-slate-500 mb-2">Moderators</div>
                  <VariableTable items={variables.moderators}
                    columns={[["variable","Variable"],["rationale","Rationale"]]} />
                </div>
              )}
              {variables.mediators?.length > 0 && (
                <div>
                  <div className="text-xs overline text-slate-500 mb-2">Mediators</div>
                  <VariableTable items={variables.mediators}
                    columns={[["variable","Variable"],["rationale","Rationale"]]} />
                </div>
              )}
              {variables.control_variables?.length > 0 && (
                <div>
                  <div className="text-xs overline text-slate-500 mb-2">Control Variables</div>
                  <VariableTable items={variables.control_variables}
                    columns={[["variable","Variable"],["rationale","Rationale"]]} />
                </div>
              )}
            </div>
          )}
        </div>

        {/* sampling */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={Users} label="Sampling Strategy" color="#7c3aed" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <LabelValue label="Target Population" value={sampling.target_population} />
              <LabelValue label="Sampling Method" value={sampling.sampling_method} />
              <LabelValue label="Justification" value={sampling.sampling_method_justification} />
              <LabelValue label="Recommended Sample Size" value={sampling.recommended_sample_size} />
              <LabelValue label="Sample Size Rationale" value={sampling.sample_size_rationale} />
              <LabelValue label="Recruitment Strategy" value={sampling.recruitment_strategy} />
            </div>
            <div className="space-y-4">
              {sampling.inclusion_criteria?.length > 0 && (
                <div>
                  <div className="text-xs overline text-[#16a34a] mb-2">Inclusion Criteria</div>
                  <BulletList items={sampling.inclusion_criteria} />
                </div>
              )}
              {sampling.exclusion_criteria?.length > 0 && (
                <div>
                  <div className="text-xs overline text-[#dc2626] mb-2">Exclusion Criteria</div>
                  <BulletList items={sampling.exclusion_criteria} />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* data collection */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={ClipboardList} label="Data Collection Strategy" color="#2563eb" />
          <div className="space-y-4">
            <LabelValue label="Primary Method" value={dataCol.primary_method} />
            <LabelValue label="Justification" value={dataCol.primary_method_justification} />
            {dataCol.secondary_methods?.length > 0 && (
              <LabelValue label="Secondary Methods" value={dataCol.secondary_methods.join(", ")} />
            )}
            <LabelValue label="Estimated Timeline" value={dataCol.timeline_estimate} />
            {dataCol.instruments?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Instruments</div>
                <div className="space-y-3">
                  {dataCol.instruments.map((inst, i) => (
                    <div key={i} className="border border-slate-100 bg-slate-50 p-4 space-y-2">
                      <div className="font-medium text-sm text-slate-900">{inst.instrument}</div>
                      <LabelValue label="Purpose" value={inst.purpose} />
                      <LabelValue label="Validation" value={inst.validation_note} />
                      <LabelValue label="Duration" value={inst.estimated_duration} />
                    </div>
                  ))}
                </div>
              </div>
            )}
            {dataCol.data_quality_measures?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Data Quality Measures</div>
                <BulletList items={dataCol.data_quality_measures} />
              </div>
            )}
          </div>
        </div>

        {/* analysis plan */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={BarChart2} label="Data Analysis Plan" color="#0F2847" />
          <div className="space-y-4">
            <LabelValue label="Primary Analysis Method" value={analysis.primary_analysis_method} />
            <LabelValue label="Justification" value={analysis.primary_method_justification} />
            <LabelValue label="Software" value={analysis.software_recommendation} />
            <LabelValue label="Reporting Standards" value={analysis.reporting_standards} />
            {analysis.secondary_analyses?.length > 0 && (
              <LabelValue label="Secondary Analyses" value={analysis.secondary_analyses.join(", ")} />
            )}
            {analysis.analysis_steps?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Analysis Steps</div>
                <ol className="space-y-2">
                  {analysis.analysis_steps.map((step, i) => (
                    <li key={i} className="flex gap-3 text-sm text-slate-700">
                      <span className="font-mono text-[#0F2847] shrink-0 w-5">{step.step}.</span>
                      <span>{step.description}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
            {analysis.statistical_assumptions?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Statistical Assumptions</div>
                <BulletList items={analysis.statistical_assumptions} />
              </div>
            )}
          </div>
        </div>

        {/* validity threats */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={Shield} label="Threats to Validity" color="#dc2626" />
          <div className="space-y-6">
            <ValiditySection threats={validity.internal_validity} label="Internal Validity" color="#dc2626" />
            <ValiditySection threats={validity.external_validity} label="External Validity" color="#d97706" />
            <ValiditySection threats={validity.construct_validity} label="Construct Validity" color="#7c3aed" />
          </div>
        </div>

        {/* ethics */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={BookOpen} label="Ethical Considerations" color="#16a34a" />
          <div className="space-y-4">
            {ethics.irb_required != null && (
              <div className={`inline-flex items-center gap-2 text-xs border px-3 py-1 font-mono
                ${ethics.irb_required ? "border-red-200 text-red-700 bg-red-50" : "border-slate-200 text-slate-600"}`}>
                {ethics.irb_required ? <XCircle size={12} /> : <CheckCircle2 size={12} />}
                IRB / Ethics approval {ethics.irb_required ? "required" : "may not be required — verify locally"}
              </div>
            )}
            <LabelValue label="Consent Approach" value={ethics.consent_approach} />
            <LabelValue label="Data Privacy" value={ethics.data_privacy} />
            <LabelValue label="Vulnerable Populations" value={ethics.vulnerable_populations} />
            {ethics.key_ethical_risks?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Key Ethical Risks</div>
                <div className="space-y-2">
                  {ethics.key_ethical_risks.map((risk, i) => (
                    <div key={i} className="border border-slate-100 bg-slate-50 p-3 space-y-1">
                      <div className="text-sm font-medium text-slate-900">{risk.risk}</div>
                      {risk.mitigation && <p className="text-xs text-slate-500">{risk.mitigation}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {ethics.additional_considerations && (
              <LabelValue label="Additional Considerations" value={ethics.additional_considerations} />
            )}
          </div>
        </div>

        {/* publication readiness detail */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={TrendingUp} label="Publication Readiness Assessment" color={potColor} />
          <div className="space-y-4">
            {pubReady.assessment && (
              <p className="text-sm text-slate-700 leading-relaxed">{pubReady.assessment}</p>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {pubReady.strongest_elements?.length > 0 && (
                <div>
                  <div className="text-xs overline text-[#16a34a] mb-2">Strongest Elements</div>
                  <BulletList items={pubReady.strongest_elements} />
                </div>
              )}
              {pubReady.weakest_elements?.length > 0 && (
                <div>
                  <div className="text-xs overline text-[#dc2626] mb-2">Weakest Elements</div>
                  <BulletList items={pubReady.weakest_elements} />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* improvement plan */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={ListChecks} label="Research Design Improvement Plan" color="#0F2847" />
          <div className="space-y-6">
            <ImprovementList items={improvement.high_priority} level="high" />
            <ImprovementList items={improvement.medium_priority} level="medium" />
            <ImprovementList items={improvement.low_priority} level="low" />
          </div>
        </div>

        {/* footer */}
        <div className="border border-slate-100 bg-white px-6 py-4 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-3">
            <Clock size={11} />
            <span>Analysed {new Date(data.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}</span>
            {data.credits_used != null && <span>· {data.credits_used} credits used</span>}
          </div>
          <div className="flex items-center gap-1.5 text-amber-600">
            <AlertTriangle size={11} />
            <span>Consult your institution's IRB before commencing data collection</span>
          </div>
        </div>
      </div>
    </div>

  );
}

// ─────────────────────── history item ────────────────────────────────────────

function HistoryItem({ item, onSelect }) {
  return (
    <button
      onClick={() => onSelect(item.id)}
      data-testid={TID.researchDesignHistoryItem(item.id)}
      className="w-full text-left border border-slate-200 bg-white hover:border-[#0F2847] transition-colors p-4 space-y-2"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="font-serif text-sm text-slate-900 line-clamp-1">{item.topic}</div>
        {item.publication_score != null && (
          <span className="shrink-0 text-xs font-mono border border-slate-200 px-1.5 py-0.5 text-slate-500">
            {item.publication_score}/100
          </span>
        )}
      </div>
      <p className="text-xs text-slate-500 line-clamp-2">{item.research_question}</p>
      <div className="flex items-center gap-1.5 text-xs text-slate-400">
        <Clock size={10} />
        {new Date(item.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
      </div>
    </button>
  );
}

// ─────────────────────── main page ───────────────────────────────────────────

export default function ResearchDesignAdvisor() {
  const [view, setView] = useState("input");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    api.get("/research-design-advisor/history")
      .then((r) => setHistory(r.data))
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
  }, []);

  const handleResult = (data) => {
    setResult(data);
    setView("result");
    setHistory((h) => [{ ...data, review_json: undefined }, ...h]);
  };

  const handleHistorySelect = async (id) => {
    try {
      const { data } = await api.get(`/research-design-advisor/${id}`);
      setResult(data);
      setView("result");
    } catch {}
  };

  const handleReset = () => {
    setResult(null);
    setView("input");
  };

  if (view === "result" && result) {
    return (
      <div style={{ display: "flex", flex: 1, minHeight: 0, overflow: "hidden" }}>
        <div className="flex-1 overflow-y-auto">
          <ResultView data={result} onReset={handleReset} />
        </div>
        {history.length > 1 && (
          <aside className="hidden xl:flex flex-col w-72 border-l border-slate-200 bg-white overflow-y-auto">
            <div className="px-4 py-4 border-b border-slate-100">
              <div className="overline text-slate-500">Past Advisories</div>
            </div>
            <div className="p-3 space-y-2">
              {history.map((item) => (
                <HistoryItem key={item.id} item={item} onSelect={handleHistorySelect} />
              ))}
            </div>
          </aside>
        )}
      </div>
    );
  }

  return (
    <AIWorkspaceLayout
      title="Research Design Advisor"
      subtitle="AI-powered guidance on research methodology, design, and study planning."
    >
    <div style={{ display: "flex", flex: 1, minHeight: 0, overflow: "hidden" }}>
      <div className="flex-1 overflow-y-auto">
        <InputView onResult={handleResult} />
      </div>
      {!loadingHistory && history.length > 0 && (
        <aside className="hidden xl:flex flex-col w-72 border-l border-slate-200 bg-white overflow-y-auto">
          <div className="px-4 py-4 border-b border-slate-100">
            <div className="overline text-slate-500">Past Advisories</div>
          </div>
          <div className="p-3 space-y-2">
            {history.map((item) => (
              <HistoryItem key={item.id} item={item} onSelect={handleHistorySelect} />
            ))}
          </div>
        </aside>
      )}
    </div>
    </AIWorkspaceLayout>

  );
}

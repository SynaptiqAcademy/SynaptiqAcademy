import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  BarChart2, Lock, RotateCcw, Clock, ChevronDown, ChevronUp,
  AlertTriangle, CheckCircle2, XCircle, MinusCircle,
  TrendingUp, Shield, MessageSquare, ListChecks, Lightbulb,
  FileText, Upload, ClipboardList,
} from "lucide-react";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { WARM } from "@/lib/tokens";
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
            <span className="text-xs px-2 py-0.5 border font-mono"
              style={badgeColor
                ? { borderColor: badgeColor, color: badgeColor }
                : { borderColor: "#e2e8f0", color: "#64748b" }}>
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

// ─────────────────────── score ring ──────────────────────────────────────────

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

// ─────────────────────── verdict badge ───────────────────────────────────────

function VerdictBadge({ verdict }) {
  const map = {
    strong:       { color: "#16a34a" },
    adequate:     { color: "#2563eb" },
    weak:         { color: "#d97706" },
    insufficient: { color: "#dc2626" },
  };
  const cfg = map[verdict?.toLowerCase()] || { color: "#64748b" };
  return (
    <span className="text-xs px-2 py-0.5 border font-mono capitalize"
      style={{ borderColor: cfg.color, color: cfg.color }}>
      {verdict?.replace(/_/g, " ")}
    </span>
  );
}

function SeverityBadge({ severity }) {
  const map = {
    critical: "#dc2626", major: "#ea580c", moderate: "#d97706",
    minor: "#64748b", fatal: "#dc2626",
  };
  const color = map[severity?.toLowerCase()] || "#64748b";
  return (
    <span className="text-xs px-2 py-0.5 border font-mono capitalize"
      style={{ borderColor: color, color }}>
      {severity}
    </span>
  );
}

function HypothesisVerdictBadge({ verdict }) {
  const map = {
    supported:           { color: "#16a34a" },
    partially_supported: { color: "#d97706" },
    not_supported:       { color: "#dc2626" },
    cannot_determine:    { color: "#64748b" },
  };
  const cfg = map[verdict?.toLowerCase()] || { color: "#64748b" };
  const label = verdict?.replace(/_/g, " ");
  return (
    <span className="text-xs px-2 py-0.5 border font-mono capitalize"
      style={{ borderColor: cfg.color, color: cfg.color }}>
      {label}
    </span>
  );
}

function AssumptionStatusDot({ status }) {
  const map = {
    met:              { color: "#16a34a", label: "Met" },
    violated:         { color: "#dc2626", label: "Violated" },
    not_tested:       { color: "#d97706", label: "Not Tested" },
    cannot_determine: { color: "#64748b", label: "Cannot Determine" },
  };
  const cfg = map[status?.toLowerCase()] || { color: "#64748b", label: status };
  return (
    <span className="flex items-center gap-1.5 text-xs font-mono" style={{ color: cfg.color }}>
      <span className="w-2 h-2 rounded-full inline-block" style={{ background: cfg.color }} />
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
            AI Statistical Review requires a Pro Researcher or Institution plan.
            Get expert-level statistical critique before you submit to a journal.
          </p>
        </div>
        <div className="border border-slate-200 bg-white p-4 text-left space-y-2">
          <div className="text-xs overline text-slate-500 mb-3">Included in this review</div>
          {[
            "Analysis appropriateness assessment",
            "Assumption review (normality, multicollinearity, etc.)",
            "Academic-language results interpretation",
            "Hypothesis evaluation (Supported / Partially / Not Supported)",
            "Simulated peer reviewer criticisms",
            "Publication readiness score (0–100)",
            "Prioritised revision roadmap",
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
        <p className="text-xs text-slate-500">25 credits per review · Refunded if review fails</p>
      </div>
      </div>
    </div>
  );
}

// ─────────────────────── input mode tabs ─────────────────────────────────────

const INPUT_MODES = [
  { id: "text",        label: "Text / Paste",      icon: FileText,    placeholder: "Paste your statistical results, output tables, or any analysis text here…" },
  { id: "regression",  label: "Regression Output", icon: BarChart2,   placeholder: "Paste regression output (OLS, logistic, etc.) — e.g. coefficient table from SPSS, R lm(), Stata regress…" },
  { id: "sem",         label: "SEM / PLS-SEM",     icon: ClipboardList, placeholder: "Paste SEM output (AMOS, lavaan, SmartPLS) — path coefficients, fit indices (CFI, RMSEA, AVE, CR)…" },
  { id: "anova",       label: "ANOVA Output",      icon: BarChart2,   placeholder: "Paste ANOVA / ANCOVA / MANOVA output — F-values, p-values, effect sizes, post-hoc tests…" },
  { id: "csv",         label: "CSV / Table Data",  icon: Upload,      placeholder: "Paste CSV data or a descriptive statistics table (means, SDs, correlations)…" },
];

// ─────────────────────── input form view ─────────────────────────────────────

function InputView({ onResult }) {
  const [topic, setTopic] = useState("");
  const [question, setQuestion] = useState("");
  const [results, setResults] = useState("");
  const [inputMode, setInputMode] = useState("text");
  const [showOptional, setShowOptional] = useState(false);
  const [methodology, setMethodology] = useState("");
  const [sampleSize, setSampleSize] = useState("");
  const [variables, setVariables] = useState("");
  const [hypotheses, setHypotheses] = useState("");
  const [analysisType, setAnalysisType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const isGated = error?.status === 402;
  const currentMode = INPUT_MODES.find((m) => m.id === inputMode) || INPUT_MODES[0];

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setResults(ev.target?.result || "");
    reader.readAsText(file);
    e.target.value = "";
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!topic.trim() || !question.trim() || !results.trim()) {
      setError({ message: "Topic, research question, and statistical results are required." });
      return;
    }
    if (results.trim().length < 20) {
      setError({ message: "Statistical results must be at least 20 characters. Please provide your actual output." });
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const body = {
        topic: topic.trim(),
        research_question: question.trim(),
        statistical_results: results.trim(),
        ...(methodology && { methodology }),
        ...(sampleSize && { sample_size: sampleSize }),
        ...(variables && { variables }),
        ...(hypotheses && { hypotheses }),
        ...(analysisType && { analysis_technique: analysisType }),
      };
      const { data } = await api.post("/statistical-review", body, { timeout: 180000 });
      onResult(data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 402) {
        setError({ status: 402, message: detail?.message || "Plan upgrade required." });
      } else {
        setError({ message: detail?.message || detail || "Review failed. Please try again." });
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
              <BarChart2 size={18} strokeWidth={1.5} className="text-[#0F2847]" />
            </div>
            <div>
              <h1 className="font-serif text-2xl text-slate-900">AI Statistical Review</h1>
              <p className="text-xs text-slate-500 mt-0.5">Pro Researcher · 25 credits per review</p>
            </div>
          </div>
          <p className="text-slate-600 text-sm leading-relaxed">
            Submit your statistical output for an expert critique — assumptions, interpretation,
            validity threats, simulated reviewer feedback, and a prioritised revision roadmap
            before you submit to a journal.
          </p>
        </div>

        <form onSubmit={submit} data-testid={TID.statisticalReviewForm} className="space-y-5">
          {/* topic */}
          <div>
            <label className="overline block mb-1.5">Research Topic *</label>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Impact of digital literacy on academic performance in higher education"
              className="w-full border border-slate-300 px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
              maxLength={300}
              data-testid={TID.statisticalReviewTopic}
            />
          </div>

          {/* research question */}
          <div>
            <label className="overline block mb-1.5">Research Question *</label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Does digital literacy significantly predict academic performance when controlling for socioeconomic status and prior academic achievement?"
              rows={3}
              className="w-full border border-slate-300 px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors resize-none"
              maxLength={1000}
              data-testid={TID.statisticalReviewQuestion}
            />
          </div>

          {/* input mode selector */}
          <div>
            <label className="overline block mb-1.5">Statistical Output Type *</label>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {INPUT_MODES.map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  onClick={() => setInputMode(mode.id)}
                  className={`flex items-center gap-1.5 text-xs px-3 py-1.5 border transition-colors ${
                    inputMode === mode.id
                      ? "bg-[#0F2847] border-[#0F2847] text-white"
                      : "border-slate-300 text-slate-600 hover:border-[#0F2847] hover:text-[#0F2847]"
                  }`}
                >
                  <mode.icon size={11} strokeWidth={1.5} />
                  {mode.label}
                </button>
              ))}
            </div>

            <textarea
              value={results}
              onChange={(e) => setResults(e.target.value)}
              placeholder={currentMode.placeholder}
              rows={12}
              className="w-full border border-slate-300 px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors resize-y font-mono"
              maxLength={80000}
              data-testid={TID.statisticalReviewResults}
            />
            <div className="flex items-center justify-between mt-1">
              <p className="text-xs text-slate-400">
                Paste output directly or upload a text/CSV file
              </p>
              <label className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-[#0F2847] cursor-pointer transition-colors">
                <Upload size={11} />
                Upload file
                <input
                  type="file"
                  accept=".txt,.csv,.tsv,.out,.spo,.log"
                  className="hidden"
                  onChange={handleFile}
                />
              </label>
            </div>
          </div>

          {/* optional section toggle */}
          <button
            type="button"
            onClick={() => setShowOptional((v) => !v)}
            className="flex items-center gap-2 text-sm text-slate-500 hover:text-[#0F2847] transition-colors"
          >
            {showOptional ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {showOptional ? "Hide" : "Show"} optional context (improves review quality)
          </button>

          {showOptional && (
            <div className="border border-slate-200 bg-white p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="overline block mb-1.5">Methodology</label>
                  <input
                    value={methodology}
                    onChange={(e) => setMethodology(e.target.value)}
                    placeholder="e.g. Cross-sectional survey"
                    className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                    maxLength={300}
                  />
                </div>
                <div>
                  <label className="overline block mb-1.5">Sample Size</label>
                  <input
                    value={sampleSize}
                    onChange={(e) => setSampleSize(e.target.value)}
                    placeholder="e.g. 342 undergraduates"
                    className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                    maxLength={100}
                  />
                </div>
              </div>
              <div>
                <label className="overline block mb-1.5">Variables</label>
                <input
                  value={variables}
                  onChange={(e) => setVariables(e.target.value)}
                  placeholder="e.g. IV: digital literacy score; DV: GPA; Controls: SES, prior achievement"
                  className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                  maxLength={500}
                />
              </div>
              <div>
                <label className="overline block mb-1.5">Hypotheses</label>
                <textarea
                  value={hypotheses}
                  onChange={(e) => setHypotheses(e.target.value)}
                  placeholder="e.g. H1: Digital literacy positively predicts GPA (β > 0, p < .05)"
                  rows={3}
                  className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors resize-none"
                  maxLength={2000}
                />
              </div>
              <div>
                <label className="overline block mb-1.5">Analysis Technique</label>
                <input
                  value={analysisType}
                  onChange={(e) => setAnalysisType(e.target.value)}
                  placeholder="e.g. Hierarchical multiple regression, PLS-SEM, one-way ANOVA"
                  className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                  maxLength={200}
                />
              </div>
            </div>
          )}

          {error && !isGated && (
            <div className="border border-red-200 bg-red-50 p-3 flex gap-2.5">
              <AlertTriangle size={14} className="text-red-500 shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error.message}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            data-testid={TID.statisticalReviewSubmitBtn}
            className="w-full bg-[#0F2847] text-white text-sm font-medium py-3 px-6 hover:bg-[#1a3a5c] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <RotateCcw size={14} className="animate-spin" />
                Reviewing statistical output… (up to 3 min)
              </span>
            ) : (
              "Review Statistics — 25 Credits"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

// ─────────────────────── result view ─────────────────────────────────────────

function ValiditySection({ threats, label, color }) {
  if (!threats?.length) return null;
  return (
    <div>
      <div className="text-xs overline mb-2" style={{ color }}>{label}</div>
      <div className="space-y-3">
        {threats.map((t, i) => (
          <div key={i} className="border border-slate-100 bg-slate-50 p-4 space-y-2">
            <div className="font-medium text-sm text-slate-900">{t.threat}</div>
            <LabelValue label="Description" value={t.description} />
            <LabelValue label="Mitigation" value={t.mitigation} />
          </div>
        ))}
      </div>
    </div>
  );
}

function ImprovementList({ items, level }) {
  const cfg = {
    high:   { color: "#dc2626", bg: "bg-red-50",   border: "border-red-100" },
    medium: { color: "#d97706", bg: "bg-amber-50", border: "border-amber-100" },
    low:    { color: "#64748b", bg: "bg-slate-50",  border: "border-slate-100" },
  }[level];
  if (!items?.length) return null;
  return (
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
  );
}

function ResultView({ data, onReset }) {
  const r = data.review_json || {};
  const exec = r.executive_statistical_assessment || {};
  const appropriateness = r.analysis_appropriateness || {};
  const assumptions = r.assumption_review || {};
  const interpretation = r.results_interpretation || {};
  const hypotheses = r.hypothesis_evaluation || [];
  const weaknesses = r.statistical_weaknesses || [];
  const validity = r.threats_to_validity || {};
  const pubRisk = r.publication_risk_assessment || {};
  const additionalAnalyses = r.recommended_additional_analyses || [];
  const reviewer = r.reviewer_perspective || {};
  const pubReady = r.publication_readiness || {};
  const roadmap = r.revision_roadmap || {};

  const potColor = (pubReady.score >= 80) ? "#16a34a" : (pubReady.score >= 60) ? "#d97706" : "#dc2626";

  return (
    <div className="min-h-screen bg-[#F4F6FA]" data-testid={TID.statisticalReviewResult}>
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
            New Review
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">

        {/* executive assessment + score */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2 border border-slate-200 bg-white p-6 space-y-4">
            <SectionHeader icon={BarChart2} label="Executive Statistical Assessment" />
            <div className="flex flex-wrap gap-2">
              {exec.overall_verdict && <VerdictBadge verdict={exec.overall_verdict} />}
              {exec.output_completeness && (
                <span className="text-xs border border-slate-200 px-2 py-0.5 text-slate-500 font-mono">
                  {exec.output_completeness}
                </span>
              )}
            </div>
            {exec.summary && <p className="text-sm text-slate-700 leading-relaxed">{exec.summary}</p>}
            <div className="grid grid-cols-2 gap-4">
              {exec.key_strengths?.length > 0 && (
                <div>
                  <div className="text-xs overline text-[#16a34a] mb-2">Key Strengths</div>
                  <BulletList items={exec.key_strengths} />
                </div>
              )}
              {exec.critical_issues?.length > 0 && (
                <div>
                  <div className="text-xs overline text-[#dc2626] mb-2">Critical Issues</div>
                  <BulletList items={exec.critical_issues} />
                </div>
              )}
            </div>
          </div>

          {/* publication readiness ring */}
          <div className="border border-slate-200 bg-white p-6 flex flex-col items-center justify-center text-center gap-3">
            <div className="overline text-slate-500">Publication Readiness</div>
            <ScoreRing score={pubReady.score || 0} />
            {pubReady.most_critical_barrier && (
              <p className="text-xs text-slate-500 leading-snug">{pubReady.most_critical_barrier}</p>
            )}
          </div>
        </div>

        {/* analysis appropriateness */}
        <div className="border border-slate-200 bg-white p-6 space-y-4">
          <SectionHeader icon={CheckCircle2} label="Analysis Appropriateness" color="#2563eb" />
          <div className="flex flex-wrap gap-2">
            {appropriateness.method_used && (
              <span className="text-xs border border-[#0F2847] px-2 py-0.5 text-[#0F2847] font-mono">
                {appropriateness.method_used}
              </span>
            )}
            {appropriateness.is_appropriate != null && (
              <span className={`text-xs border px-2 py-0.5 font-mono ${
                appropriateness.is_appropriate
                  ? "border-green-300 text-green-700"
                  : "border-red-300 text-red-700"
              }`}>
                {appropriateness.is_appropriate ? "Appropriate" : "Questionable"}
              </span>
            )}
          </div>
          {appropriateness.appropriateness_rationale && (
            <p className="text-sm text-slate-700 leading-relaxed">{appropriateness.appropriateness_rationale}</p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {appropriateness.alternative_methods?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Alternatives Considered</div>
                <BulletList items={appropriateness.alternative_methods} />
              </div>
            )}
            {appropriateness.missing_reporting_elements?.length > 0 && (
              <div>
                <div className="text-xs overline text-[#dc2626] mb-2">Missing Reporting Elements</div>
                <BulletList items={appropriateness.missing_reporting_elements} />
              </div>
            )}
          </div>
          {appropriateness.reporting_standard_compliance && (
            <LabelValue label="Reporting Standard Compliance" value={appropriateness.reporting_standard_compliance} />
          )}
        </div>

        {/* assumption review */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={ClipboardList} label="Assumption Review" color="#7c3aed" />
          {assumptions.overall_assumption_verdict && (
            <div className="mb-4">
              <VerdictBadge verdict={assumptions.overall_assumption_verdict?.replace(/_/g, " ")} />
            </div>
          )}
          <div className="space-y-3">
            {(assumptions.assumptions_assessed || []).map((a, i) => (
              <ExpandCard
                key={i}
                title={a.assumption}
                subtitle={a.evidence || (a.applicable === false ? "Not applicable to this design" : undefined)}
                badge={a.status?.replace(/_/g, " ")}
                badgeColor={
                  a.status === "met" ? "#16a34a" :
                  a.status === "violated" ? "#dc2626" :
                  a.status === "not_tested" ? "#d97706" : "#64748b"
                }
              >
                <div className="space-y-2">
                  <LabelValue label="Evidence" value={a.evidence} />
                  {a.consequence && <LabelValue label="Consequence" value={a.consequence} />}
                  {a.recommended_action && <LabelValue label="Recommended Action" value={a.recommended_action} />}
                </div>
              </ExpandCard>
            ))}
          </div>
        </div>

        {/* results interpretation */}
        <div className="border border-slate-200 bg-white p-6 space-y-4">
          <SectionHeader icon={FileText} label="Results Interpretation" color="#0F2847" />
          {interpretation.narrative_interpretation && (
            <p className="text-sm text-slate-700 leading-relaxed">{interpretation.narrative_interpretation}</p>
          )}
          {interpretation.statistical_significance_assessment && (
            <LabelValue label="Statistical Significance" value={interpretation.statistical_significance_assessment} />
          )}
          {interpretation.practical_significance && (
            <LabelValue label="Practical Significance" value={interpretation.practical_significance} />
          )}
          {interpretation.confidence_intervals && (
            <LabelValue label="Confidence Intervals" value={interpretation.confidence_intervals} />
          )}
          {interpretation.effect_sizes?.length > 0 && (
            <div>
              <div className="text-xs overline text-slate-500 mb-2">Effect Sizes</div>
              <div className="space-y-2">
                {interpretation.effect_sizes.map((es, i) => (
                  <div key={i} className="border border-slate-100 bg-slate-50 p-3 flex items-start gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium text-slate-900">{es.measure}</div>
                      {es.context && <p className="text-xs text-slate-500 mt-0.5">{es.context}</p>}
                    </div>
                    <div className="shrink-0 text-right">
                      {es.value && <div className="font-mono text-sm text-slate-900">{es.value}</div>}
                      {es.interpretation && (
                        <span className="text-xs capitalize text-slate-500">{es.interpretation}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* hypothesis evaluation */}
        {hypotheses.length > 0 && (
          <div className="border border-slate-200 bg-white p-6">
            <SectionHeader icon={Lightbulb} label="Hypothesis Evaluation" color="#16a34a" />
            <div className="space-y-3">
              {hypotheses.map((h, i) => (
                <ExpandCard
                  key={i}
                  title={h.hypothesis}
                  badge={h.verdict?.replace(/_/g, " ")}
                  badgeColor={
                    h.verdict === "supported" ? "#16a34a" :
                    h.verdict === "partially_supported" ? "#d97706" :
                    h.verdict === "not_supported" ? "#dc2626" : "#64748b"
                  }
                  defaultOpen={i === 0}
                >
                  <div className="space-y-2">
                    <LabelValue label="Rationale" value={h.rationale} />
                    {h.caveats && <LabelValue label="Caveats" value={h.caveats} />}
                  </div>
                </ExpandCard>
              ))}
            </div>
          </div>
        )}

        {/* statistical weaknesses */}
        {weaknesses.length > 0 && (
          <div className="border border-slate-200 bg-white p-6">
            <SectionHeader icon={AlertTriangle} label="Statistical Weaknesses" color="#dc2626" />
            <div className="space-y-3">
              {weaknesses.map((w, i) => (
                <ExpandCard
                  key={i}
                  title={w.weakness}
                  badge={w.severity}
                  badgeColor={
                    w.severity === "critical" || w.severity === "fatal" ? "#dc2626" :
                    w.severity === "major" ? "#ea580c" :
                    w.severity === "moderate" ? "#d97706" : "#64748b"
                  }
                >
                  <div className="space-y-2">
                    <LabelValue label="Evidence" value={w.evidence} />
                    <LabelValue label="Impact" value={w.impact} />
                    <LabelValue label="Remediation" value={w.remediation} />
                  </div>
                </ExpandCard>
              ))}
            </div>
          </div>
        )}

        {/* threats to validity */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={Shield} label="Threats to Validity" color="#dc2626" />
          <div className="space-y-6">
            <ValiditySection threats={validity.statistical_conclusion_validity} label="Statistical Conclusion Validity" color="#7c3aed" />
            <ValiditySection threats={validity.internal_validity} label="Internal Validity" color="#dc2626" />
            <ValiditySection threats={validity.external_validity} label="External Validity" color="#d97706" />
            <ValiditySection threats={validity.construct_validity} label="Construct Validity" color="#2563eb" />
          </div>
        </div>

        {/* publication risk */}
        <div className="border border-slate-200 bg-white p-6 space-y-5">
          <SectionHeader icon={AlertTriangle} label="Publication Risk Assessment" color="#ea580c" />
          {pubRisk.major_concerns?.length > 0 && (
            <div>
              <div className="text-xs overline text-[#dc2626] mb-2">Major Concerns</div>
              <div className="space-y-2">
                {pubRisk.major_concerns.map((c, i) => (
                  <div key={i} className="border border-red-100 bg-red-50 p-4 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-medium text-sm text-slate-900">{c.concern}</div>
                      {c.likelihood_of_rejection && (
                        <SeverityBadge severity={c.likelihood_of_rejection} />
                      )}
                    </div>
                    {c.action_required && <p className="text-xs text-slate-600">{c.action_required}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {pubRisk.moderate_concerns?.length > 0 && (
            <div>
              <div className="text-xs overline text-[#d97706] mb-2">Moderate Concerns</div>
              <div className="space-y-2">
                {pubRisk.moderate_concerns.map((c, i) => (
                  <div key={i} className="border border-amber-100 bg-amber-50 p-3 space-y-1">
                    <div className="font-medium text-sm text-slate-900">{c.concern}</div>
                    {c.action_required && <p className="text-xs text-slate-600">{c.action_required}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {pubRisk.minor_concerns?.length > 0 && (
            <div>
              <div className="text-xs overline text-slate-500 mb-2">Minor Concerns</div>
              <div className="space-y-2">
                {pubRisk.minor_concerns.map((c, i) => (
                  <div key={i} className="border border-slate-100 bg-slate-50 p-3 space-y-1">
                    <div className="font-medium text-sm text-slate-900">{c.concern}</div>
                    {c.action_required && <p className="text-xs text-slate-600">{c.action_required}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* recommended additional analyses */}
        {additionalAnalyses.length > 0 && (
          <div className="border border-slate-200 bg-white p-6">
            <SectionHeader icon={TrendingUp} label="Recommended Additional Analyses" color="#2563eb" />
            <div className="space-y-3">
              {additionalAnalyses.map((a, i) => (
                <div key={i} className="border border-slate-100 bg-slate-50 p-4 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-medium text-sm text-slate-900">{a.analysis}</div>
                    <span className={`text-xs border px-2 py-0.5 font-mono shrink-0 ${
                      a.priority === "essential" ? "border-red-300 text-red-700" :
                      a.priority === "recommended" ? "border-amber-300 text-amber-700" :
                      "border-slate-200 text-slate-500"
                    }`}>{a.priority}</span>
                  </div>
                  <LabelValue label="Rationale" value={a.rationale} />
                  {a.software_guidance && <LabelValue label="Software" value={a.software_guidance} />}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* reviewer perspective */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={MessageSquare} label="Reviewer Perspective" color="#7c3aed" />
          {reviewer.editorial_assessment && (
            <div className="border border-slate-100 bg-slate-50 p-4 mb-4">
              <div className="text-xs overline text-slate-500 mb-1">Editorial Assessment</div>
              <p className="text-sm text-slate-700 leading-relaxed italic">"{reviewer.editorial_assessment}"</p>
            </div>
          )}
          <div className="space-y-3">
            {(reviewer.likely_criticisms || []).map((c, i) => (
              <ExpandCard
                key={i}
                title={`Reviewer: ${c.reviewer_comment?.substring(0, 80)}…`}
                badge={c.severity}
                badgeColor={
                  c.severity === "fatal" ? "#dc2626" :
                  c.severity === "major" ? "#ea580c" : "#64748b"
                }
              >
                <div className="space-y-3">
                  <div className="border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xs overline text-slate-500 mb-1">Reviewer Comment</div>
                    <p className="text-sm text-slate-700 italic">"{c.reviewer_comment}"</p>
                  </div>
                  {c.suggested_response && (
                    <div>
                      <div className="text-xs overline text-[#0F2847] mb-1">Suggested Author Response</div>
                      <p className="text-sm text-slate-700 leading-relaxed">{c.suggested_response}</p>
                    </div>
                  )}
                </div>
              </ExpandCard>
            ))}
          </div>
        </div>

        {/* publication readiness detail */}
        <div className="border border-slate-200 bg-white p-6 space-y-4">
          <SectionHeader icon={TrendingUp} label="Publication Readiness Assessment" color={potColor} />
          {pubReady.assessment && (
            <p className="text-sm text-slate-700 leading-relaxed">{pubReady.assessment}</p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pubReady.strongest_statistical_element && (
              <div className="border border-[#16a34a] bg-green-50 p-4">
                <div className="text-xs overline text-[#16a34a] mb-1">Strongest Element</div>
                <p className="text-sm text-slate-700">{pubReady.strongest_statistical_element}</p>
              </div>
            )}
            {pubReady.most_critical_barrier && (
              <div className="border border-[#dc2626] bg-red-50 p-4">
                <div className="text-xs overline text-[#dc2626] mb-1">Most Critical Barrier</div>
                <p className="text-sm text-slate-700">{pubReady.most_critical_barrier}</p>
              </div>
            )}
          </div>
        </div>

        {/* revision roadmap */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={ListChecks} label="Revision Roadmap" color="#0F2847" />
          <div className="space-y-6">
            {roadmap.high_priority?.length > 0 && (
              <div>
                <div className="text-xs overline text-[#dc2626] mb-2">High Priority</div>
                <ImprovementList items={roadmap.high_priority} level="high" />
              </div>
            )}
            {roadmap.medium_priority?.length > 0 && (
              <div>
                <div className="text-xs overline text-[#d97706] mb-2">Medium Priority</div>
                <ImprovementList items={roadmap.medium_priority} level="medium" />
              </div>
            )}
            {roadmap.low_priority?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Low Priority</div>
                <ImprovementList items={roadmap.low_priority} level="low" />
              </div>
            )}
          </div>
        </div>

        {/* footer */}
        <div className="border border-slate-100 bg-white px-6 py-4 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-3">
            <Clock size={11} />
            <span>Reviewed {new Date(data.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}</span>
            {data.credits_used != null && <span>· {data.credits_used} credits used</span>}
          </div>
          <div className="flex items-center gap-1.5 text-amber-600">
            <AlertTriangle size={11} />
            <span>This is an AI review — not a substitute for a qualified statistician</span>
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
      data-testid={TID.statisticalReviewHistoryItem(item.id)}
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
      {item.analysis_technique && (
        <Tag>{item.analysis_technique}</Tag>
      )}
      <div className="flex items-center gap-1.5 text-xs text-slate-400">
        <Clock size={10} />
        {new Date(item.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
      </div>
    </button>
  );
}

// ─────────────────────── main page ───────────────────────────────────────────

export default function StatisticalReview() {
  const [view, setView] = useState("input");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    api.get("/statistical-review/history")
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
      const { data } = await api.get(`/statistical-review/${id}`);
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
              <div className="overline text-slate-500">Past Reviews</div>
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
      title="Statistical Review"
      subtitle="AI-powered statistical analysis review — methodology, assumptions, and reporting quality."
    >
    <div style={{ display: "flex", flex: 1, minHeight: 0, overflow: "hidden" }}>
      <div className="flex-1 overflow-y-auto">
        <InputView onResult={handleResult} />
      </div>
      {!loadingHistory && history.length > 0 && (
        <aside className="hidden xl:flex flex-col w-72 border-l border-slate-200 bg-white overflow-y-auto">
          <div className="px-4 py-4 border-b border-slate-100">
            <div className="overline text-slate-500">Past Reviews</div>
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

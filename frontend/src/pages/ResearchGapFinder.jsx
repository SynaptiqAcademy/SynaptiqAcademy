import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Search, Lock, RotateCcw, Clock, ChevronDown, ChevronUp,
  Copy, Check, AlertTriangle, Lightbulb, TrendingUp,
  Target, Microscope, Globe, Users, Database, Zap, BookOpen,
  Star, BarChart2, HelpCircle, CheckCircle2, XCircle, MinusCircle,
  FolderPlus, ArrowRight, X, Activity,
} from "lucide-react";
import api from "../lib/api";
import { useGapOpportunities } from "../hooks/useCitations";
import { TID } from "../lib/testIds";
import { NAVY, WARM } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";
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
          <span>{item}</span>
        </li>
      ))}
    </ul>
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
              className="text-xs px-2 py-0.5 font-mono border"
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

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };
  return (
    <button
      onClick={copy}
      className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-[#0F2847] transition-colors"
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

// ─────────────────────── opportunity level badge ──────────────────────────────

function OpportunityBadge({ level }) {
  const map = {
    high:   { color: "#16a34a", label: "High Opportunity" },
    medium: { color: "#d97706", label: "Medium Opportunity" },
    low:    { color: "#64748b", label: "Low Opportunity" },
  };
  const cfg = map[level?.toLowerCase()] || map.low;
  return (
    <span className="text-xs px-2 py-0.5 border font-mono"
      style={{ borderColor: cfg.color, color: cfg.color }}>
      {cfg.label}
    </span>
  );
}

function PubPotentialBadge({ level }) {
  const map = {
    high:   { color: "#16a34a" },
    medium: { color: "#d97706" },
    low:    { color: "#64748b" },
  };
  const cfg = map[level?.toLowerCase()] || map.low;
  return (
    <span className="text-xs px-2 py-0.5 border font-mono capitalize"
      style={{ borderColor: cfg.color, color: cfg.color }}>
      {level}
    </span>
  );
}

function MaturityBadge({ level }) {
  const map = {
    emerging:   { color: "#16a34a" },
    developing: { color: "#2563eb" },
    mature:     { color: "#d97706" },
    saturated:  { color: "#dc2626" },
  };
  const cfg = map[level?.toLowerCase()] || { color: "#64748b" };
  return (
    <span className="text-xs px-2 py-0.5 border font-mono capitalize"
      style={{ borderColor: cfg.color, color: cfg.color }}>
      {level}
    </span>
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

// ─────────────────────── gate view ──────────────────────────────────────────

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
            AI Research Gap Finder requires a Pro Researcher or Institution plan.
            Uncover underexplored areas, contradictions, and publishable opportunities in any field.
          </p>
        </div>
        <div className="border border-slate-200 bg-white p-4 text-left space-y-2">
          <div className="text-xs overline text-slate-500 mb-3">Included in this analysis</div>
          {[
            "Highly and underexplored research areas",
            "Contradictory findings & resolution paths",
            "Methodological, geographic & population gaps",
            "10 ranked publishable research questions",
            "Publication potential score (0–100)",
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
        <p className="text-xs text-slate-500">10 credits per analysis · Refunded if analysis fails</p>
      </div>
      </div>
    </div>
  );
}

// ─────────────────────── keyword input ───────────────────────────────────────

function KeywordInput({ keywords, setKeywords }) {
  const [input, setInput] = useState("");

  const add = (val) => {
    const trimmed = val.trim();
    if (!trimmed || keywords.includes(trimmed) || keywords.length >= 20) return;
    setKeywords([...keywords, trimmed]);
    setInput("");
  };

  const onKey = (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add(input);
    } else if (e.key === "Backspace" && !input && keywords.length) {
      setKeywords(keywords.slice(0, -1));
    }
  };

  const remove = (kw) => setKeywords(keywords.filter((k) => k !== kw));

  return (
    <div className="border border-slate-300 bg-white min-h-[42px] flex flex-wrap gap-1.5 p-2 focus-within:border-[#0F2847] transition-colors">
      {keywords.map((kw) => (
        <span key={kw} className="flex items-center gap-1 bg-[#0F2847] text-white text-xs px-2 py-1">
          {kw}
          <button type="button" onClick={() => remove(kw)} className="opacity-60 hover:opacity-100 ml-0.5">×</button>
        </span>
      ))}
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={onKey}
        onBlur={() => add(input)}
        placeholder={keywords.length ? "" : "Type keyword and press Enter…"}
        className="flex-1 min-w-[120px] outline-none text-sm text-slate-700 bg-transparent placeholder:text-slate-400"
        data-testid={TID.researchGapKeywords}
      />
    </div>
  );
}

// ─────────────────────── input form view ─────────────────────────────────────

function InputView({ onResult }) {
  const [topic, setTopic] = useState("");
  const [question, setQuestion] = useState("");
  const [keywords, setKeywords] = useState([]);
  const [showOptional, setShowOptional] = useState(false);
  const [discipline, setDiscipline] = useState("");
  const [methodology, setMethodology] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [journalType, setJournalType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const isGated = error?.code === "upgrade_required" || error?.status === 402;

  const submit = async (e) => {
    e.preventDefault();
    if (!topic.trim() || !question.trim() || !keywords.length) {
      setError({ message: "Topic, research question, and at least one keyword are required." });
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const body = {
        topic: topic.trim(),
        research_question: question.trim(),
        keywords,
        ...(discipline && { discipline }),
        ...(methodology && { methodology_preference: methodology }),
        ...(yearFrom && { year_from: parseInt(yearFrom, 10) }),
        ...(yearTo && { year_to: parseInt(yearTo, 10) }),
        ...(journalType && { target_journal_type: journalType }),
      };
      const { data } = await api.post("/research-gap-finder", body, { timeout: 180000 });
      onResult(data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 402) {
        setError({ status: 402, code: detail?.code || "upgrade_required", message: detail?.message || "Plan upgrade required." });
      } else {
        setError({ message: detail?.message || detail || "Analysis failed. Please try again." });
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
              <Target size={18} strokeWidth={1.5} className="text-[#0F2847]" />
            </div>
            <div>
              <h1 className="font-serif text-2xl text-slate-900">AI Research Gap Finder</h1>
              <p className="text-xs text-slate-500 mt-0.5">Pro Researcher · 10 credits per analysis</p>
            </div>
          </div>
          <p className="text-slate-600 text-sm leading-relaxed">
            Identify over-researched areas, under-studied territories, contradictions, and genuinely
            publishable opportunities in any academic field.
          </p>

          {/* disclaimer */}
          <div className="mt-4 border border-amber-200 bg-amber-50 p-3 flex gap-2.5">
            <AlertTriangle size={14} className="text-amber-600 shrink-0 mt-0.5" />
            <p className="text-xs text-amber-800 leading-relaxed">
              Claude identifies gaps based on training data (cut-off August 2025). Results reflect
              patterns in the literature, not a live database search. Always verify with PubMed,
              Scopus, or Web of Science before submitting a manuscript.
            </p>
          </div>
        </div>

        {/* form */}
        <form onSubmit={submit} data-testid={TID.researchGapForm} className="space-y-5">
          {/* topic */}
          <div>
            <label className="overline block mb-1.5">Research Topic *</label>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. mRNA vaccine efficacy in immunocompromised adults"
              className="w-full border border-slate-300 px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
              maxLength={300}
              data-testid={TID.researchGapTopic}
            />
          </div>

          {/* research question */}
          <div>
            <label className="overline block mb-1.5">Research Question *</label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. What methodological approaches have been underused in assessing long-term mRNA vaccine durability in solid-organ transplant recipients?"
              rows={3}
              className="w-full border border-slate-300 px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors resize-none"
              maxLength={1000}
              data-testid={TID.researchGapQuestion}
            />
          </div>

          {/* keywords */}
          <div>
            <label className="overline block mb-1.5">Keywords *</label>
            <KeywordInput keywords={keywords} setKeywords={setKeywords} />
            <p className="text-xs text-slate-400 mt-1">Press Enter or comma to add · up to 20 keywords</p>
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
                    placeholder="e.g. Immunology"
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
                <label className="overline block mb-1.5">Methodology Preference</label>
                <input
                  value={methodology}
                  onChange={(e) => setMethodology(e.target.value)}
                  placeholder="e.g. Systematic review, RCT, longitudinal cohort"
                  className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                  maxLength={200}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="overline block mb-1.5">Year From</label>
                  <input
                    type="number"
                    value={yearFrom}
                    onChange={(e) => setYearFrom(e.target.value)}
                    placeholder="e.g. 2010"
                    min={1900} max={2100}
                    className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                  />
                </div>
                <div>
                  <label className="overline block mb-1.5">Year To</label>
                  <input
                    type="number"
                    value={yearTo}
                    onChange={(e) => setYearTo(e.target.value)}
                    placeholder="e.g. 2025"
                    min={1900} max={2100}
                    className="w-full border border-slate-300 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-[#0F2847] bg-white transition-colors"
                  />
                </div>
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
            data-testid={TID.researchGapSubmitBtn}
            className="w-full bg-[#0F2847] text-white text-sm font-medium py-3 px-6 hover:bg-[#1a3a5c] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <RotateCcw size={14} className="animate-spin" />
                Analysing research landscape… (up to 3 min)
              </span>
            ) : (
              "Find Research Gaps — 10 Credits"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

// ─────────────────────── result view ─────────────────────────────────────────

function LabelValue({ label, value }) {
  if (!value) return null;
  return (
    <div>
      <div className="text-xs text-slate-500 overline mb-0.5">{label}</div>
      <div className="text-sm text-slate-700 leading-relaxed">{value}</div>
    </div>
  );
}

function PairList({ items, keyA, keyB, labelA, labelB, extra }) {
  if (!items?.length) return <p className="text-sm text-slate-400">No items identified.</p>;
  return (
    <div className="space-y-4">
      {items.map((item, i) => (
        <div key={i} className="border border-slate-100 bg-slate-50 p-4 space-y-2">
          {Object.entries(item).map(([k, v]) => v ? <LabelValue key={k} label={k.replace(/_/g, " ")} value={String(v)} /> : null)}
        </div>
      ))}
    </div>
  );
}

// ─────────────────────── gap → project modal ─────────────────────────────────

function GapToProjectModal({ data, onClose }) {
  const navigate = useNavigate();
  const g = data.gap_json || {};
  const pubPot = g.publication_potential || {};
  const questions = g.publishable_research_questions || [];
  const topQ = questions[0] || {};
  const underexplored = (g.underexplored_areas || []).slice(0, 2).map((u) => u.area || "").filter(Boolean);
  const methGaps = (g.methodological_gaps || []).slice(0, 2).map((m) => m.gap || "").filter(Boolean);

  const defaultTitle = data.topic
    ? `Research Project: ${data.topic.slice(0, 60)}`
    : "New Research Project";
  const defaultGap = pubPot.strongest_angle || underexplored.join("; ") || "";
  const defaultObjectives = [
    topQ.question ? `Investigate: ${topQ.question.slice(0, 120)}` : null,
    underexplored[0] ? `Address the underexplored area: ${underexplored[0]}` : null,
    methGaps[0] ? `Apply ${methGaps[0]} to fill methodological gap` : null,
  ].filter(Boolean);
  const defaultHypotheses = questions.slice(0, 3).map((q) =>
    q.question ? `H: ${q.question.slice(0, 100)}` : null
  ).filter(Boolean);

  const [title, setTitle] = useState(defaultTitle);
  const [description, setDescription] = useState(pubPot.assessment || "");
  const [researchGap, setResearchGap] = useState(defaultGap);
  const [objectives, setObjectives] = useState(defaultObjectives.join("\n"));
  const [hypotheses, setHypotheses] = useState(defaultHypotheses.join("\n"));
  const [methodology, setMethodology] = useState(topQ.suggested_methodology || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleCreate = async () => {
    if (!title.trim()) { setError("Project title is required."); return; }
    setSaving(true);
    setError(null);
    try {
      const { data: proj } = await api.post("/projects", {
        title: title.trim(),
        description: description.trim(),
        visibility: "team",
        source: "gap_finder",
        research_gap: researchGap.trim(),
        objectives: objectives.split("\n").map((s) => s.trim()).filter(Boolean),
        hypotheses: hypotheses.split("\n").map((s) => s.trim()).filter(Boolean),
        methodology: methodology.trim(),
        keywords: data.keywords || [],
        research_questions: data.research_question ? [data.research_question] : [],
      });
      navigate(`/projects/${proj.id}`);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create project.");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white w-full max-w-2xl max-h-[90vh] overflow-y-auto border border-slate-200 shadow-lg">
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-200 sticky top-0 bg-white z-10">
          <div>
            <div className="font-serif text-lg text-slate-900">Create Research Project</div>
            <div className="text-xs text-slate-500 mt-0.5">Pre-filled from your gap analysis · edit before saving</div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <X size={18} strokeWidth={1.5} />
          </button>
        </div>
        <div className="px-6 py-6 space-y-5">
          {error && (
            <div className="border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>
          )}
          <div>
            <label className="block overline text-slate-500 mb-2">Project Title *</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847]"
            />
          </div>
          <div>
            <label className="block overline text-slate-500 mb-2">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847] resize-none"
            />
          </div>
          <div>
            <label className="block overline text-slate-500 mb-2">Research Gap Summary</label>
            <textarea
              value={researchGap}
              onChange={(e) => setResearchGap(e.target.value)}
              rows={3}
              className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847] resize-none"
            />
          </div>
          <div>
            <label className="block overline text-slate-500 mb-2">Objectives (one per line)</label>
            <textarea
              value={objectives}
              onChange={(e) => setObjectives(e.target.value)}
              rows={4}
              className="w-full border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#0F2847] resize-none font-mono"
            />
          </div>
          <div>
            <label className="block overline text-slate-500 mb-2">Suggested Hypotheses (one per line)</label>
            <textarea
              value={hypotheses}
              onChange={(e) => setHypotheses(e.target.value)}
              rows={4}
              className="w-full border border-slate-300 px-3 py-2 text-xs focus:outline-none focus:border-[#0F2847] resize-none font-mono"
            />
          </div>
          <div>
            <label className="block overline text-slate-500 mb-2">Methodology Recommendation</label>
            <input
              value={methodology}
              onChange={(e) => setMethodology(e.target.value)}
              className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847]"
            />
          </div>
        </div>
        <div className="flex items-center justify-between gap-4 px-6 py-4 border-t border-slate-200 sticky bottom-0 bg-white">
          <button onClick={onClose} className="text-sm text-slate-500 hover:text-slate-700">Cancel</button>
          <button
            onClick={handleCreate}
            disabled={saving}
            className="flex items-center gap-2 border border-[#0F2847] bg-[#0F2847] text-white px-5 py-2.5 text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
          >
            {saving ? "Creating…" : (
              <><FolderPlus size={14} strokeWidth={1.5} /> Create Project</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────── citation opportunity analysis ───────────────────────

function ScoreBar({ label, value, color }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-600">{label}</span>
        <span className="text-xs font-mono text-slate-500">{value}</span>
      </div>
      <div className="h-1.5 bg-slate-100">
        <div className="h-full transition-all" style={{ width: `${Math.min(100, value)}%`, background: color }} />
      </div>
    </div>
  );
}

function CitationOpportunityAnalysis({ topic, keywords }) {
  const kwString = (keywords || []).join(",");
  const { data, loading, error } = useGapOpportunities({
    topic,
    keywords: kwString,
    skip: !topic,
  });

  if (loading) {
    return (
      <div className="border border-slate-200 bg-white p-6">
        <SectionHeader icon={Activity} label="Citation Opportunity Analysis" color="#0891b2" />
        <div className="py-4 flex justify-center"><Spinner size={16} /></div>
      </div>
    );
  }

  if (error || !data) return null;

  const pubPotential = data.publication_potential_score ?? 0;
  const citOpp       = data.citation_opportunity_score  ?? 0;
  const momentum     = data.research_momentum_score     ?? 0;
  const receivingCit = data.topics_receiving_citations  || [];
  const growingVel   = data.growing_velocity_topics     || [];
  const lowComp      = data.low_competition_rising      || [];

  const overallScore = Math.round((pubPotential + citOpp + momentum) / 3);
  const overallColor = overallScore >= 70 ? "#16a34a" : overallScore >= 45 ? "#d97706" : "#64748b";

  return (
    <div className="border border-[#0891b2]/20 bg-white p-6">
      <SectionHeader icon={Activity} label="Citation Opportunity Analysis" color="#0891b2" />
      <p className="text-xs text-slate-500 mb-5">
        Based on your research area's actual citation patterns in SYNAPTIQ (OpenAlex-backed).
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* left: scores */}
        <div className="md:col-span-2 space-y-4">
          <div className="flex items-center gap-4 mb-4">
            <div className="text-center shrink-0">
              <div className="font-serif text-4xl tracking-tight" style={{ color: overallColor }}>
                {overallScore}
              </div>
              <div className="text-xs text-slate-400 mt-0.5">/ 100</div>
              <div className="text-xs font-mono mt-1" style={{ color: overallColor }}>
                {overallScore >= 70 ? "Strong" : overallScore >= 45 ? "Moderate" : "Low"} Opportunity
              </div>
            </div>
            <div className="flex-1 space-y-3">
              <ScoreBar label="Publication Potential" value={pubPotential} color="#0F2847" />
              <ScoreBar label="Citation Opportunity"  value={citOpp}       color="#0891b2" />
              <ScoreBar label="Research Momentum"     value={momentum}     color="#7c3aed" />
            </div>
          </div>

          {receivingCit.length > 0 && (
            <div>
              <div className="text-xs overline text-slate-500 mb-2">Topics Receiving Citations</div>
              <div className="flex flex-wrap gap-1.5">
                {receivingCit.map((t) => (
                  <span key={t} className="text-xs border border-cyan-200 text-cyan-700 px-2 py-0.5">{t}</span>
                ))}
              </div>
            </div>
          )}

          {growingVel.length > 0 && (
            <div>
              <div className="text-xs overline text-slate-500 mb-2">Growing Velocity Topics</div>
              <div className="flex flex-wrap gap-1.5">
                {growingVel.map((t) => (
                  <span key={t} className="text-xs border border-green-200 text-green-700 px-2 py-0.5">{t}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* right: low competition */}
        <div>
          <div className="text-xs overline text-slate-500 mb-3">Low Competition, Rising</div>
          {lowComp.length > 0 ? (
            <div className="space-y-2">
              {lowComp.map((t) => (
                <div key={t} className="flex items-center gap-2">
                  <div className="w-1 h-1 rounded-full bg-amber-400 shrink-0" />
                  <span className="text-sm text-slate-700">{t}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400">
              No low-competition rising topics detected. Your area may be highly competitive.
            </p>
          )}
          <Link to="/citations"
            className="mt-4 flex items-center gap-1 text-xs text-[#0891b2] hover:text-[#0F2847] transition-colors">
            View citation tracker <ArrowRight size={10} />
          </Link>
        </div>
      </div>
    </div>
  );
}

function ResultView({ data, onReset }) {
  const navigate = useNavigate();
  const [showProjectModal, setShowProjectModal] = useState(false);
  const g = data.gap_json || {};
  const overview = g.topic_overview || {};
  const current = g.current_state_of_research || {};
  const pubPot = g.publication_potential || {};
  const questions = g.publishable_research_questions || [];

  const potColor = (pubPot.score >= 80) ? "#16a34a" : (pubPot.score >= 60) ? "#d97706" : "#dc2626";

  const handleFindCollaborators = () => {
    const params = new URLSearchParams();
    params.set("from_gap", "1");
    if (data.topic) params.set("topic", data.topic);
    if (data.research_question) params.set("question", data.research_question);
    if (data.keywords?.length) params.set("keywords", data.keywords.join(","));
    if (data.discipline) params.set("discipline", data.discipline);
    if (data.methodology_preference) params.set("methodology", data.methodology_preference);
    navigate(`/collaboration-intelligence?${params.toString()}`);
  };

  return (
    <div className="min-h-screen bg-[#F4F6FA]" data-testid={TID.researchGapResult}>
      {showProjectModal && (
        <GapToProjectModal data={data} onClose={() => setShowProjectModal(false)} />
      )}
      <div style={{ background: "#F4F6FA", padding: "13px 32px", borderBottom: "1px solid rgba(15,23,42,0.08)" }}>
      </div>
      {/* header */}
      <div className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h1 className="font-serif text-lg text-slate-900 truncate">{data.topic}</h1>
            <p className="text-xs text-slate-500 mt-0.5 truncate">{data.research_question}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0 flex-wrap">
            <button
              onClick={handleFindCollaborators}
              className="flex items-center gap-1.5 text-sm text-slate-600 border border-slate-300 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
            >
              <Users size={13} strokeWidth={1.5} />
              Find Collaborators
            </button>
            <button
              onClick={() => setShowProjectModal(true)}
              className="flex items-center gap-1.5 text-sm bg-[#0F2847] text-white border border-[#0F2847] px-3 py-1.5 hover:bg-slate-800 transition-colors"
            >
              <FolderPlus size={13} strokeWidth={1.5} />
              Create Project
            </button>
            <button
              onClick={onReset}
              className="flex items-center gap-1.5 text-sm text-slate-500 border border-slate-200 px-3 py-1.5 hover:border-slate-400 transition-colors"
            >
              <RotateCcw size={13} />
              New Analysis
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">

        {/* meta + publication score */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* overview card */}
          <div className="md:col-span-2 border border-slate-200 bg-white p-6 space-y-4">
            <SectionHeader icon={BookOpen} label="Topic Overview" />
            <p className="text-sm text-slate-700 leading-relaxed">{overview.summary}</p>
            <div className="flex flex-wrap gap-3 pt-1">
              {overview.maturity_level && <MaturityBadge level={overview.maturity_level} />}
              {overview.research_volume && (
                <span className="text-xs border border-slate-200 text-slate-500 px-2 py-0.5 font-mono capitalize">
                  {overview.research_volume}
                </span>
              )}
            </div>
            {overview.key_disciplines_involved?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {overview.key_disciplines_involved.map((d, i) => (
                  <Tag key={i}>{d}</Tag>
                ))}
              </div>
            )}
            {overview.knowledge_basis_note && (
              <div className="border border-amber-100 bg-amber-50 p-3 text-xs text-amber-800 leading-relaxed">
                <strong>Note:</strong> {overview.knowledge_basis_note}
              </div>
            )}
          </div>

          {/* publication score card */}
          <div className="border border-slate-200 bg-white p-6 flex flex-col items-center justify-center text-center gap-3">
            <div className="overline text-slate-500">Publication Potential</div>
            <ScoreRing score={pubPot.score || 0} />
            {pubPot.timing_advantage && (
              <p className="text-xs text-slate-500 leading-snug">{pubPot.timing_advantage}</p>
            )}
          </div>
        </div>

        {/* current state */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={BarChart2} label="Current State of Research" color="#2563eb" />
          {current.synthesis && (
            <p className="text-sm text-slate-700 leading-relaxed mb-5">{current.synthesis}</p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { label: "Dominant Paradigms", items: current.dominant_paradigms },
              { label: "Established Consensus", items: current.established_consensus },
              { label: "Active Frontiers", items: current.active_frontiers },
            ].map(({ label, items }) => (
              <div key={label}>
                <div className="text-xs overline text-slate-500 mb-2">{label}</div>
                <BulletList items={items} />
              </div>
            ))}
          </div>
        </div>

        {/* studied vs underexplored */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* highly studied */}
          <div className="border border-slate-200 bg-white p-6">
            <SectionHeader icon={XCircle} label="Highly Studied Areas" color="#dc2626" />
            <div className="space-y-3">
              {(g.highly_studied_areas || []).map((item, i) => (
                <ExpandCard
                  key={i}
                  title={item.area}
                  subtitle={item.saturation_signal}
                >
                  <LabelValue label="Why saturated" value={item.reason} />
                  <div className="mt-2"><LabelValue label="Saturation signal" value={item.saturation_signal} /></div>
                </ExpandCard>
              ))}
            </div>
          </div>

          {/* underexplored */}
          <div className="border border-slate-200 bg-white p-6">
            <SectionHeader icon={CheckCircle2} label="Underexplored Areas" color="#16a34a" />
            <div className="space-y-3">
              {(g.underexplored_areas || []).map((item, i) => (
                <ExpandCard
                  key={i}
                  title={item.area}
                  badge={item.opportunity_level}
                  badgeColor={item.opportunity_level === "high" ? "#16a34a" : item.opportunity_level === "medium" ? "#d97706" : "#64748b"}
                >
                  <LabelValue label="What is missing" value={item.explanation} />
                  <div className="mt-2"><LabelValue label="Why neglected" value={item.why_neglected} /></div>
                </ExpandCard>
              ))}
            </div>
          </div>
        </div>

        {/* contradictions */}
        {g.contradictory_findings?.length > 0 && (
          <div className="border border-slate-200 bg-white p-6">
            <SectionHeader icon={MinusCircle} label="Contradictory Findings" color="#7c3aed" />
            <div className="space-y-3">
              {g.contradictory_findings.map((item, i) => (
                <ExpandCard key={i} title={item.topic}>
                  <div className="grid grid-cols-2 gap-4 mb-3">
                    <div className="border border-slate-200 p-3 bg-red-50">
                      <div className="text-xs overline text-red-700 mb-1">Position A</div>
                      <p className="text-sm text-slate-700">{item.position_a}</p>
                    </div>
                    <div className="border border-slate-200 p-3 bg-blue-50">
                      <div className="text-xs overline text-blue-700 mb-1">Position B</div>
                      <p className="text-sm text-slate-700">{item.position_b}</p>
                    </div>
                  </div>
                  <LabelValue label="Source of disagreement" value={item.source_of_disagreement} />
                  <div className="mt-2"><LabelValue label="Resolution opportunity" value={item.resolution_opportunity} /></div>
                </ExpandCard>
              ))}
            </div>
          </div>
        )}

        {/* four gap columns */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { key: "methodological_gaps", label: "Methodological Gaps", icon: Microscope, color: "#0F2847",
              fields: [["gap","Gap"], ["current_approach","Current Approach"], ["missing_approach","Missing Approach"], ["impact","Impact"]] },
            { key: "geographic_gaps", label: "Geographic Gaps", icon: Globe, color: "#2563eb",
              fields: [["region","Region"], ["nature_of_gap","Nature of Gap"], ["why_it_matters","Why It Matters"]] },
            { key: "population_gaps", label: "Population Gaps", icon: Users, color: "#7c3aed",
              fields: [["population","Population"], ["nature_of_gap","Nature of Gap"], ["why_it_matters","Why It Matters"]] },
            { key: "data_gaps", label: "Data Gaps", icon: Database, color: "#d97706",
              fields: [["gap","Gap"], ["what_is_missing","What Is Missing"], ["potential_impact_if_addressed","Potential Impact"]] },
          ].map(({ key, label, icon, color, fields }) => (
            <div key={key} className="border border-slate-200 bg-white p-6">
              <SectionHeader icon={icon} label={label} color={color} />
              <div className="space-y-3">
                {(g[key] || []).map((item, i) => (
                  <ExpandCard key={i} title={item[fields[0][0]] || "Gap"}>
                    {fields.slice(1).map(([k, l]) => item[k] ? (
                      <div key={k} className="mt-2"><LabelValue label={l} value={item[k]} /></div>
                    ) : null)}
                  </ExpandCard>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* emerging opportunities */}
        {g.emerging_opportunities?.length > 0 && (
          <div className="border border-slate-200 bg-white p-6">
            <SectionHeader icon={Zap} label="Emerging Opportunities" color="#d97706" />
            <div className="space-y-3">
              {g.emerging_opportunities.map((item, i) => (
                <ExpandCard key={i} title={item.opportunity} subtitle={item.driving_forces}>
                  <LabelValue label="Driving forces" value={item.driving_forces} />
                  <div className="mt-2"><LabelValue label="Window of opportunity" value={item.window_of_opportunity} /></div>
                  <div className="mt-2"><LabelValue label="Interdisciplinary potential" value={item.interdisciplinary_potential} /></div>
                </ExpandCard>
              ))}
            </div>
          </div>
        )}

        {/* publication potential detail */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={TrendingUp} label="Publication Potential Assessment" color={potColor} />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 space-y-4">
              {pubPot.assessment && (
                <p className="text-sm text-slate-700 leading-relaxed">{pubPot.assessment}</p>
              )}
              {pubPot.strongest_angle && (
                <div className="border border-[#0F2847] bg-slate-50 p-4">
                  <div className="text-xs overline text-[#0F2847] mb-1">Strongest Publishable Angle</div>
                  <p className="text-sm text-slate-700 leading-relaxed">{pubPot.strongest_angle}</p>
                </div>
              )}
            </div>
            <div className="space-y-3">
              {pubPot.recommended_journal_types?.length > 0 && (
                <div>
                  <div className="text-xs overline text-slate-500 mb-2">Recommended Journal Types</div>
                  <div className="flex flex-wrap gap-1.5">
                    {pubPot.recommended_journal_types.map((j, i) => <Tag key={i}>{j}</Tag>)}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* citation opportunity analysis */}
        <CitationOpportunityAnalysis topic={data.topic} keywords={data.keywords} />

        {/* publishable research questions */}
        <div className="border border-slate-200 bg-white p-6">
          <SectionHeader icon={Lightbulb} label="Publishable Research Questions" color="#16a34a" />
          <p className="text-sm text-slate-500 mb-5">
            Ranked from highest to lowest publication potential. Each question is specific enough
            to begin a study design today.
          </p>
          <div className="space-y-3">
            {questions.map((q, i) => (
              <ExpandCard
                key={i}
                title={`${i + 1}. ${q.question}`}
                badge={q.publication_potential}
                badgeColor={q.publication_potential === "high" ? "#16a34a" : q.publication_potential === "medium" ? "#d97706" : "#64748b"}
                defaultOpen={i === 0}
              >
                <div className="space-y-3">
                  <LabelValue label="Rationale" value={q.rationale} />
                  <LabelValue label="Novelty" value={q.novelty} />
                  <LabelValue label="Suggested Methodology" value={q.suggested_methodology} />
                  <LabelValue label="Target Journal Type" value={q.target_journal_type} />
                </div>
              </ExpandCard>
            ))}
          </div>
        </div>

        {/* metadata footer */}
        <div className="border border-slate-100 bg-white px-6 py-4 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-3">
            <Clock size={11} />
            <span>Analysed {new Date(data.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}</span>
            {data.credits_used != null && <span>· {data.credits_used} credits used</span>}
          </div>
          <div className="flex items-center gap-1.5 text-amber-600">
            <AlertTriangle size={11} />
            <span>Verify results with a live literature database</span>
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
      data-testid={TID.researchGapHistoryItem(item.id)}
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
      <div className="flex flex-wrap gap-1">
        {(item.keywords || []).slice(0, 4).map((kw, i) => <Tag key={i}>{kw}</Tag>)}
        {(item.keywords || []).length > 4 && (
          <span className="text-xs text-slate-400">+{item.keywords.length - 4}</span>
        )}
      </div>
      <div className="flex items-center gap-1.5 text-xs text-slate-400">
        <Clock size={10} />
        {new Date(item.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
      </div>
    </button>
  );
}

// ─────────────────────── main page ───────────────────────────────────────────

export default function ResearchGapFinder() {
  const [view, setView] = useState("input"); // "input" | "result"
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    api.get("/research-gap-finder/history")
      .then((r) => setHistory(r.data))
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
  }, []);

  const handleResult = (data) => {
    setResult(data);
    setView("result");
    setHistory((h) => [{ ...data, gap_json: undefined }, ...h]);
  };

  const handleHistorySelect = async (id) => {
    try {
      const { data } = await api.get(`/research-gap-finder/${id}`);
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
              <div className="overline text-slate-500">Past Analyses</div>
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
      title="Research Gap Finder"
      subtitle="Identify unexplored research opportunities and map the frontier of knowledge in your field."
    >
    <div style={{ display: "flex", flex: 1, minHeight: 0, overflow: "hidden" }}>
      <div className="flex-1 overflow-y-auto">
        <InputView onResult={handleResult} />
      </div>

      {/* history sidebar */}
      {!loadingHistory && history.length > 0 && (
        <aside className="hidden xl:flex flex-col w-72 border-l border-slate-200 bg-white overflow-y-auto">
          <div className="px-4 py-4 border-b border-slate-100">
            <div className="overline text-slate-500">Past Analyses</div>
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

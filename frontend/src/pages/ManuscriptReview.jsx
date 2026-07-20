import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Upload, FileText, Lock, RotateCcw, ChevronDown, ChevronUp,
  Clock, CheckCircle2, AlertTriangle, XCircle, Microscope,
} from "lucide-react";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { WARM } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";



// ─────────────────────────── score utilities ─────────────────────────────────

function scoreColor(s) {
  if (s >= 80) return "#16a34a";
  if (s >= 60) return "#d97706";
  if (s >= 40) return "#ea580c";
  return "#dc2626";
}

function scoreLabel(s) {
  if (s >= 80) return "Strong";
  if (s >= 60) return "Adequate";
  if (s >= 40) return "Weak";
  return "Poor";
}

function ScoreRing({ score, size = 72 }) {
  const r = 26;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - Math.max(0, Math.min(100, score)) / 100);
  const color = scoreColor(score);
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-label={`Score: ${score}`}>
      <circle cx="32" cy="32" r={r} fill="none" stroke="#e2e8f0" strokeWidth="5" />
      <circle
        cx="32" cy="32" r={r} fill="none"
        stroke={color} strokeWidth="5"
        strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 32 32)"
        style={{ transition: "stroke-dashoffset 0.6s ease" }}
      />
      <text x="32" y="36" textAnchor="middle" fontSize="13" fontWeight="700" fill={color}>
        {score}
      </text>
    </svg>
  );
}

function ScoreBar({ score }) {
  const color = scoreColor(score);
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1.5 bg-slate-100 relative">
        <div
          className="absolute inset-y-0 left-0"
          style={{ width: `${score}%`, backgroundColor: color, transition: "width 0.5s ease" }}
        />
      </div>
      <span className="text-xs font-mono w-6 text-right" style={{ color }}>{score}</span>
    </div>
  );
}

const REC_CONFIG = {
  accept:          { label: "Accept",                cls: "bg-green-50 text-green-800 border-green-300" },
  minor_revision:  { label: "Minor Revision",        cls: "bg-blue-50 text-blue-800 border-blue-300" },
  major_revision:  { label: "Major Revision Required", cls: "bg-amber-50 text-amber-800 border-amber-300" },
  reject:          { label: "Reject",                cls: "bg-red-50 text-red-800 border-red-300" },
};

function RecBadge({ rec }) {
  const cfg = REC_CONFIG[rec] || REC_CONFIG.major_revision;
  return (
    <span className={`inline-block border px-3 py-1 text-xs font-medium tracking-wider uppercase ${cfg.cls}`}>
      {cfg.label}
    </span>
  );
}

// ─────────────────────────── section definitions ──────────────────────────────

const SECTIONS = [
  {
    key: "research_problem",
    label: "Research Problem Clarity",
    roman: "I",
    fields: [
      { key: "strengths",        label: "Strengths",        type: "list" },
      { key: "weaknesses",       label: "Weaknesses",       type: "list" },
      { key: "recommendations",  label: "Recommendations",  type: "list" },
    ],
  },
  {
    key: "literature_foundation",
    label: "Literature Foundation",
    roman: "II",
    fields: [
      { key: "coverage",              label: "Coverage",             type: "text" },
      { key: "recency",               label: "Recency",              type: "text" },
      { key: "theoretical_grounding", label: "Theoretical Grounding", type: "text" },
      { key: "recommendations",       label: "Recommendations",      type: "list" },
    ],
  },
  {
    key: "methodology",
    label: "Methodology Quality",
    roman: "III",
    fields: [
      { key: "research_design",  label: "Research Design",  type: "text" },
      { key: "sampling",         label: "Sampling",         type: "text" },
      { key: "variables",        label: "Variables",        type: "text" },
      { key: "data_collection",  label: "Data Collection",  type: "text" },
      { key: "recommendations",  label: "Recommendations",  type: "list" },
    ],
  },
  {
    key: "statistical_validity",
    label: "Statistical Validity",
    roman: "IV",
    fields: [
      { key: "analysis_quality",    label: "Analysis Quality",     type: "text" },
      { key: "threats_to_validity", label: "Threats to Validity",  type: "list" },
      { key: "recommendations",     label: "Recommendations",      type: "list" },
    ],
  },
  {
    key: "writing_quality",
    label: "Structure & Academic Writing",
    roman: "V",
    fields: [
      { key: "clarity",           label: "Clarity",       type: "text" },
      { key: "flow",              label: "Flow",          type: "text" },
      { key: "argumentation",     label: "Argumentation", type: "text" },
      { key: "recommendations",   label: "Recommendations", type: "list" },
    ],
  },
  {
    key: "publication_readiness",
    label: "Publication Readiness",
    roman: "VI",
    fields: [
      { key: "publication_probability", label: "Publication Probability", type: "text" },
      { key: "major_issues",            label: "Major Issues",            type: "list" },
      { key: "minor_issues",            label: "Minor Issues",            type: "list" },
    ],
  },
];

// ─────────────────────────── sub-components ──────────────────────────────────

function SectionCard({ def: s, data, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const score = data?.score ?? 0;
  const Chev = open ? ChevronUp : ChevronDown;

  return (
    <div className="border border-slate-200 bg-white">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-slate-50 transition-colors"
      >
        <ScoreRing score={score} size={56} />
        <div className="flex-1 min-w-0">
          <div className="overline text-slate-500 text-[10px]">Section {s.roman}</div>
          <div className="font-serif text-base text-slate-900 mt-0.5">{s.label}</div>
          <div className="text-xs mt-1" style={{ color: scoreColor(score) }}>{scoreLabel(score)}</div>
        </div>
        <Chev size={16} strokeWidth={1.5} className="text-slate-400 shrink-0" />
      </button>

      {open && (
        <div className="border-t border-slate-100 px-5 pb-5 pt-4 space-y-4">
          {s.fields.map((f) => {
            const val = data?.[f.key];
            if (!val || (Array.isArray(val) && val.length === 0)) return null;
            return (
              <div key={f.key}>
                <div className="overline text-[10px] text-slate-500 mb-1">{f.label}</div>
                {f.type === "list" ? (
                  <ul className="space-y-1">
                    {(Array.isArray(val) ? val : [val]).map((item, i) => (
                      <li key={i} className="flex gap-2 text-sm text-slate-700">
                        <span className="mt-1.5 w-1 h-1 rounded-full bg-slate-400 shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-700 leading-relaxed">{val}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ChecklistSection({ title, items, icon: Icon, iconColor }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} strokeWidth={1.5} style={{ color: iconColor }} />
        <div className="overline text-[10px]" style={{ color: iconColor }}>{title}</div>
      </div>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2.5 text-sm text-slate-700">
            <span className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: iconColor }} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function HistoryItem({ review, onSelect, active }) {
  const rec = review.review_json?.executive_summary?.recommendation;
  const cfg = REC_CONFIG[rec] || REC_CONFIG.major_revision;
  return (
    <button
      onClick={() => onSelect(review)}
      className={`w-full text-left px-4 py-3 border-b border-slate-100 hover:bg-slate-50 transition-colors ${active ? "bg-slate-50" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium text-slate-900 truncate">{review.filename}</div>
          <div className="text-xs text-slate-500 mt-0.5">
            {new Date(review.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className="font-mono text-sm font-semibold" style={{ color: scoreColor(review.overall_score) }}>
            {review.overall_score}
          </span>
          <span className={`text-[9px] font-medium tracking-wider uppercase border px-1.5 py-0.5 ${cfg.cls}`}>
            {cfg.label.split(" ")[0]}
          </span>
        </div>
      </div>
    </button>
  );
}

// ─────────────────────────── gate view ────────────────────────────────────────

function GateView() {
  return (
    <div className="space-y-6">
      <div className="border border-slate-200 bg-white p-16 flex flex-col items-center text-center gap-5">
        <Lock size={28} strokeWidth={1} className="text-slate-300" />
        <div>
          <div className="overline text-[#0F2847] mb-2">Researcher plan required</div>
          <h2 className="font-serif text-2xl text-slate-900">AI Manuscript Review is a paid feature</h2>
          <p className="text-slate-500 text-sm mt-3 max-w-sm mx-auto">
            Upgrade to Researcher to unlock full academic peer review powered by Claude — covering
            research problem, methodology, statistical validity, and publication readiness.
          </p>
        </div>
        <Link
          to="/pricing"
          className="inline-block bg-[#0F2847] text-white text-sm px-6 py-2.5 hover:opacity-90 transition-opacity"
        >
          View Plans
        </Link>
      </div>
    </div>
  );
}

// ─────────────────────────── upload view ─────────────────────────────────────

function UploadView({ onReview }) {
  const [file, setFile] = useState(null);
  const [drag, setDrag] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const accept = (f) => {
    if (!f) return;
    const ok = ["application/pdf",
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                 "application/msword"].includes(f.type);
    if (!ok) { setError("Only PDF and DOCX files are supported."); return; }
    setFile(f);
    setError(null);
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDrag(false);
    accept(e.dataTransfer.files[0]);
  }, []);

  const onDragOver = (e) => { e.preventDefault(); setDrag(true); };
  const onDragLeave = () => setDrag(false);

  const analyze = async () => {
    if (!file || analyzing) return;
    setAnalyzing(true);
    setError(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await api.post("/manuscript-review", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120_000,
      });
      onReview(res.data);
    } catch (err) {
      setAnalyzing(false);
      if (err?.response?.status === 402) return; // global UpgradeModal fires
      const detail = err?.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Analysis failed. Please try again."
      );
    }
  };

  return (
    <div className="space-y-6">

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Upload zone */}
        <div className="lg:col-span-2 space-y-4">
          <div
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onClick={() => !file && inputRef.current?.click()}
            className={`border-2 border-dashed bg-white transition-colors cursor-pointer
              flex flex-col items-center justify-center py-16 gap-4
              ${drag ? "border-[#0F2847] bg-slate-50" : "border-slate-200 hover:border-slate-300"}
              ${file ? "cursor-default" : ""}`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.doc"
              className="hidden"
              onChange={(e) => accept(e.target.files[0])}
            />
            {file ? (
              <>
                <FileText size={40} strokeWidth={1} className="text-[#0F2847]" />
                <div className="text-center">
                  <div className="font-medium text-slate-900">{file.name}</div>
                  <div className="text-sm text-slate-500 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</div>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); setFile(null); setError(null); }}
                  className="text-xs text-slate-400 hover:text-slate-700 underline"
                >
                  Remove file
                </button>
              </>
            ) : (
              <>
                <Upload size={40} strokeWidth={1} className="text-slate-300" />
                <div className="text-center">
                  <div className="font-medium text-slate-700">Drop your manuscript here</div>
                  <div className="text-sm text-slate-500 mt-1">or click to browse</div>
                  <div className="text-xs text-slate-400 mt-2">PDF or DOCX · Max 50 MB</div>
                </div>
              </>
            )}
          </div>

          {error && (
            <div className="border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            data-testid={TID.manuscriptReviewAnalyzeBtn}
            onClick={analyze}
            disabled={!file || analyzing}
            className="w-full bg-[#0F2847] text-white py-3 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {analyzing ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Running academic review — this may take up to 60 seconds…
              </>
            ) : (
              <>
                <Microscope size={15} strokeWidth={1.5} />
                Analyze Manuscript · 20 Credits
              </>
            )}
          </button>
        </div>

        {/* Info panel */}
        <div className="space-y-4">
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-3">Review covers</div>
            <ul className="space-y-2 text-sm text-slate-600">
              {[
                "Research Problem Clarity",
                "Literature Foundation",
                "Methodology Quality",
                "Statistical Validity",
                "Structure & Academic Writing",
                "Publication Readiness",
              ].map((label) => (
                <li key={label} className="flex items-center gap-2">
                  <CheckCircle2 size={13} strokeWidth={1.5} className="text-[#0F2847] shrink-0" />
                  {label}
                </li>
              ))}
            </ul>
          </div>
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-2">Credit cost</div>
            <div className="font-serif text-3xl text-slate-900">20</div>
            <div className="text-xs text-slate-500 mt-1">Research Credits per review</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────── result view ─────────────────────────────────────

function ResultView({ review, onNew }) {
  const rj = review.review_json || {};
  const exec = rj.executive_summary || {};
  const sections = rj.sections || {};
  const checklist = rj.revision_checklist || {};

  return (
    <div className="space-y-6" data-testid={TID.manuscriptReviewResult}>
      {/* Header */}
      <header className="border-b border-slate-200 pb-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="overline">AI Manuscript Review</div>
            <h1 className="font-serif text-4xl text-slate-900 mt-1 leading-tight break-words">
              {review.filename}
            </h1>
            <div className="flex items-center gap-4 mt-2 text-xs text-slate-500 font-mono">
              <span className="flex items-center gap-1">
                <Clock size={11} strokeWidth={1.5} />
                {new Date(review.review_date).toLocaleDateString("en-GB", {
                  day: "numeric", month: "long", year: "numeric",
                })}
              </span>
              <span>{review.credits_used} credits used</span>
            </div>
          </div>
          <button
            onClick={onNew}
            className="shrink-0 flex items-center gap-2 border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <RotateCcw size={13} strokeWidth={1.5} />
            New Review
          </button>
        </div>
      </header>

      {/* Executive summary */}
      <div className="border border-slate-200 bg-white p-6 space-y-4">
        <div className="flex items-start justify-between gap-6">
          <div className="flex-1">
            <div className="overline mb-2">Executive Summary</div>
            <div className="flex items-center gap-3 mb-4">
              <RecBadge rec={exec.recommendation} />
            </div>
            <p className="text-slate-700 leading-relaxed">{exec.overview}</p>
          </div>
          <div className="shrink-0 flex flex-col items-center gap-1">
            <ScoreRing score={review.overall_score} size={80} />
            <div className="text-xs text-slate-500 overline">Overall</div>
          </div>
        </div>
      </div>

      {/* Score overview grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {SECTIONS.map((s) => {
          const score = sections[s.key]?.score ?? 0;
          return (
            <div key={s.key} className="border border-slate-200 bg-white px-4 py-3">
              <div className="overline text-[10px] text-slate-400">Section {s.roman}</div>
              <div className="text-sm font-medium text-slate-800 mt-0.5">{s.label}</div>
              <ScoreBar score={score} />
            </div>
          );
        })}
      </div>

      {/* Section deep-dives */}
      <div>
        <div className="overline mb-3">Detailed Assessment</div>
        <div className="space-y-2">
          {SECTIONS.map((s) => (
            <SectionCard key={s.key} def={s} data={sections[s.key]} />
          ))}
        </div>
      </div>

      {/* Revision checklist */}
      <div className="border border-slate-200 bg-white p-6">
        <div className="overline mb-5">Priority Revision Checklist</div>
        <div className="space-y-5">
          <ChecklistSection
            title="High Priority"
            items={checklist.high_priority}
            icon={XCircle}
            iconColor="#dc2626"
          />
          <ChecklistSection
            title="Medium Priority"
            items={checklist.medium_priority}
            icon={AlertTriangle}
            iconColor="#d97706"
          />
          <ChecklistSection
            title="Low Priority"
            items={checklist.low_priority}
            icon={CheckCircle2}
            iconColor="#16a34a"
          />
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────── main page ───────────────────────────────────────

export default function ManuscriptReview() {
  const [gated, setGated] = useState(false);
  const [review, setReview] = useState(null);   // currently displayed review
  const [history, setHistory] = useState([]);

  const loadHistory = useCallback(async () => {
    try {
      const res = await api.get("/manuscript-review/history");
      setHistory(res.data || []);
    } catch (err) {
      if (err?.response?.status === 402) setGated(true);
    }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  if (gated) return <AIWorkspaceLayout title="Manuscript Review"><GateView /></AIWorkspaceLayout>;

  return (
    <AIWorkspaceLayout
      title="Manuscript Review"
      subtitle="AI-powered academic peer review — research quality, methodology, and publication readiness."
    >
    <div className="space-y-10">
      {/* Main content */}
      {review ? (
        <ResultView
          review={review}
          onNew={() => setReview(null)}
        />
      ) : (
        <UploadView
          onReview={(r) => {
            setReview(r);
            loadHistory();
          }}
        />
      )}

      {/* Review history */}
      {history.length > 0 && (
        <section>
          <div className="overline mb-3">Review History</div>
          <div className="border border-slate-200 bg-white divide-y divide-slate-100">
            {history.map((h) => (
              <HistoryItem
                key={h.id}
                review={h}
                active={review?.id === h.id}
                onSelect={async (item) => {
                  if (item.review_json) {
                    setReview(item);
                  } else {
                    try {
                      const res = await api.get(`/manuscript-review/${item.id}`);
                      setReview(res.data);
                    } catch {/* ignore */}
                  }
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              />
            ))}
          </div>
        </section>
      )}
    </div>
    </AIWorkspaceLayout>
  );
}

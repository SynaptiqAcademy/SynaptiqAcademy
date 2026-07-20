import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PenLine, Lock, RotateCcw, Clock, Copy, Check, ChevronDown, ChevronUp } from "lucide-react";
import api from "../lib/api";
import { WARM } from "@/lib/tokens";
import { ErrorState } from "@/components/ds/ErrorState";
import { AIWorkspaceLayout } from "@/layouts";



// ─────────────────────────── shared primitives ───────────────────────────────

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }
    catch {/* ignore */}
  };
  return (
    <button onClick={copy}
      className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 border border-slate-200 px-3 py-1.5 transition-colors">
      {copied ? <Check size={12} strokeWidth={2} /> : <Copy size={12} strokeWidth={1.5} />}
      {copied ? "Copied" : "Copy text"}
    </button>
  );
}

// ─────────────────────────── gate view ───────────────────────────────────────

function GateView() {
  return (
    <div className="space-y-6">
      <div className="border border-slate-200 bg-white p-16 flex flex-col items-center text-center gap-5">
        <Lock size={28} strokeWidth={1} className="text-slate-300" />
        <div>
          <div className="overline text-[#0F2847] mb-2">Researcher plan required</div>
          <h2 className="font-serif text-2xl text-slate-900">AI Rewriting is a Researcher feature</h2>
          <p className="text-slate-500 text-sm mt-3 max-w-sm mx-auto">
            Upgrade to Researcher to rewrite and refine your academic writing — improve clarity,
            tone, and style while preserving your original meaning.
          </p>
        </div>
        <Link to="/pricing"
          className="inline-block bg-[#0F2847] text-white text-sm px-6 py-2.5 hover:opacity-90 transition-opacity">
          View Plans
        </Link>
      </div>
    </div>
  );
}

// ─────────────────────────── input form ──────────────────────────────────────

const STYLES = [
  { value: "academic",   label: "Academic",   desc: "Formal scholarly register" },
  { value: "concise",    label: "Concise",    desc: "Tighter, no redundancy" },
  { value: "formal",     label: "Formal",     desc: "Professional and precise" },
  { value: "engaging",   label: "Engaging",   desc: "Accessible and readable" },
];

function InputView({ onResult, gated }) {
  const [form, setForm] = useState({ text: "", style: "academic", instruction: "" });
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const valid = form.text.trim().length >= 20;

  const submit = async (e) => {
    e.preventDefault();
    if (!valid || running) return;
    setRunning(true);
    setError(null);
    try {
      const payload = {
        text: form.text.trim(),
        style: form.style,
      };
      if (form.instruction.trim()) payload.instruction = form.instruction.trim();
      const res = await api.post("/ai/rewrite", payload, { timeout: 90_000 });
      onResult(res.data);
    } catch (err) {
      setRunning(false);
      if (err?.response?.status === 402) return;
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Rewriting failed. Please try again.");
    }
  };

  if (gated) return <GateView />;

  return (
    <div className="space-y-6">

      <div className="grid lg:grid-cols-3 gap-6">
        <form onSubmit={submit} className="lg:col-span-2 space-y-4">
          <div className="border border-slate-200 bg-white p-5 space-y-4">
            <div className="overline text-[10px] text-slate-400 mb-1">Text to rewrite</div>

            <div>
              <textarea value={form.text} onChange={set("text")} required rows={10}
                placeholder="Paste the passage you want to rewrite — a paragraph, section, or full passage (up to 5,000 characters)."
                className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847] resize-y" />
              <div className="text-[10px] text-slate-400 mt-1 font-mono">
                {form.text.length} / 5,000 characters
              </div>
            </div>
          </div>

          <div className="border border-slate-200 bg-white p-5 space-y-4">
            <div className="overline text-[10px] text-slate-400 mb-1">Options</div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Rewriting Style</label>
              <div className="grid grid-cols-2 gap-2">
                {STYLES.map((s) => (
                  <button key={s.value} type="button"
                    onClick={() => setForm((f) => ({ ...f, style: s.value }))}
                    className={`text-left border p-3 transition-colors ${
                      form.style === s.value ? "border-[#0F2847] bg-[#0F2847]/5" : "border-slate-200 hover:border-slate-400"
                    }`}>
                    <div className="text-sm font-medium text-slate-900">{s.label}</div>
                    <div className="text-[10px] text-slate-500 mt-0.5">{s.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Custom instruction <span className="font-normal text-slate-500">(optional)</span>
              </label>
              <input value={form.instruction} onChange={set("instruction")}
                placeholder='e.g. "Avoid passive voice" or "Use hedging language appropriate for a lit review"'
                className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]" />
            </div>
          </div>

          {error && (
            <ErrorState message={error} type="generic" />
          )}

          <button type="submit" disabled={!valid || running}
            className="w-full bg-[#0F2847] text-white py-3 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2">
            {running ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Rewriting — this may take 10–20 seconds…
              </>
            ) : (
              <>
                <PenLine size={15} strokeWidth={1.5} />
                Rewrite · 2 Credits
              </>
            )}
          </button>
        </form>

        {/* Info panel */}
        <div className="space-y-4">
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-3">Output includes</div>
            <ul className="space-y-2 text-sm text-slate-600">
              {["Rewritten passage", "Summary of changes made", "Before / after word count"].map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-[#0F2847]" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-2">Credit cost</div>
            <div className="font-serif text-3xl text-slate-900">2</div>
            <div className="text-xs text-slate-500 mt-1">Research Credits per rewrite</div>
          </div>
          <div className="border border-amber-100 bg-amber-50 p-4">
            <div className="overline text-[10px] text-amber-700 mb-1">Academic integrity</div>
            <p className="text-xs text-amber-800 leading-relaxed">
              This tool helps improve how ideas are expressed, not generate new content.
              Always disclose AI assistance according to your institution's policy.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────── result view ─────────────────────────────────────

function OriginalCollapsible({ text }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-slate-200 bg-white">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-slate-50 transition-colors">
        <div className="overline text-[10px] text-slate-400">Original Text</div>
        {open ? <ChevronUp size={14} strokeWidth={1.5} className="text-slate-400" /> : <ChevronDown size={14} strokeWidth={1.5} className="text-slate-400" />}
      </button>
      {open && (
        <div className="px-5 pb-5 border-t border-slate-100">
          <p className="text-sm text-slate-500 leading-relaxed whitespace-pre-wrap mt-3">{text}</p>
        </div>
      )}
    </div>
  );
}

function ResultView({ result, onNew }) {
  const r = result.result || {};
  const originalWordCount = result.original_text?.split(/\s+/).filter(Boolean).length ?? null;
  return (
    <div className="space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="overline">AI Rewriting</div>
            <h1 className="font-serif text-4xl text-slate-900 mt-1 leading-tight">
              Rewritten <span className="text-slate-400">in {result.style} style</span>
            </h1>
            <div className="flex flex-wrap items-center gap-3 mt-3">
              <span className="flex items-center gap-1 text-xs text-slate-500 font-mono">
                <Clock size={11} strokeWidth={1.5} />
                {new Date(result.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}
              </span>
              <span className="text-xs text-slate-500 font-mono">{result.credits_used} credits</span>
              {originalWordCount && r.word_count && (
                <span className="text-xs text-slate-500 font-mono">
                  {originalWordCount} → {r.word_count} words
                </span>
              )}
            </div>
          </div>
          <button onClick={onNew}
            className="shrink-0 flex items-center gap-2 border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors">
            <RotateCcw size={13} strokeWidth={1.5} /> New Rewrite
          </button>
        </div>
      </header>

      {/* Rewritten text */}
      <div className="border border-[#0F2847] bg-white p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="overline text-[#0F2847]">Rewritten Version</div>
          <CopyButton text={r.rewritten_text || ""} />
        </div>
        <p className="text-slate-800 leading-[1.85] whitespace-pre-wrap">{r.rewritten_text}</p>
      </div>

      {/* Changes summary */}
      {r.changes_summary && (
        <div className="border border-slate-200 bg-white p-5">
          <div className="overline text-[10px] text-slate-400 mb-2">Changes Made</div>
          <p className="text-sm text-slate-700 leading-relaxed">{r.changes_summary}</p>
        </div>
      )}

      {/* Original (collapsible) */}
      {result.original_text && <OriginalCollapsible text={result.original_text} />}
    </div>
  );
}

// ─────────────────────────── history ─────────────────────────────────────────

function HistoryItem({ item, active, onSelect }) {
  const preview = (item.original_text || "").slice(0, 80);
  return (
    <button onClick={() => onSelect(item)}
      className={`w-full text-left px-4 py-3 border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors ${active ? "bg-slate-50" : ""}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-sm text-slate-900 truncate">{preview}{preview.length === 80 ? "…" : ""}</div>
          <div className="text-xs text-slate-500 mt-0.5 capitalize">{item.style} style</div>
        </div>
        <div className="shrink-0 text-xs text-slate-400 font-mono whitespace-nowrap">
          {new Date(item.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
        </div>
      </div>
    </button>
  );
}

// ─────────────────────────── main page ───────────────────────────────────────

export default function AIRewriting() {
  const [gated, setGated]     = useState(false);
  const [result, setResult]   = useState(null);
  const [history, setHistory] = useState([]);

  const loadHistory = useCallback(async () => {
    try {
      const res = await api.get("/ai/rewrite/history");
      setHistory(res.data || []);
    } catch (err) {
      if (err?.response?.status === 402) setGated(true);
    }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  const openHistoryItem = async (item) => {
    if (item.result) {
      setResult(item);
    } else {
      try {
        const res = await api.get(`/ai/rewrite/${item.id}`);
        setResult(res.data);
      } catch {/* ignore */}
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <AIWorkspaceLayout
      title="AI Rewriting"
      subtitle="Paste a passage and Synaptiq AI rewrites it in your chosen academic style."
    >
      <div className="space-y-10">
        {result ? (
          <ResultView result={result} onNew={() => setResult(null)} />
        ) : (
          <InputView gated={gated} onResult={(r) => { setResult(r); loadHistory(); }} />
        )}

        {history.length > 0 && !gated && (
          <section>
            <div className="overline mb-3">Rewriting History</div>
            <div className="border border-slate-200 bg-white divide-y divide-slate-100">
              {history.map((h) => (
                <HistoryItem key={h.id} item={h} active={result?.id === h.id} onSelect={openHistoryItem} />
              ))}
            </div>
          </section>
        )}
      </div>
    </AIWorkspaceLayout>
  );
}

import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, Lock, RotateCcw, Clock, Copy, Check, Tag } from "lucide-react";
import api from "../lib/api";
import { WARM } from "@/lib/tokens";
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
          <h2 className="font-serif text-2xl text-slate-900">AI Abstract Generator is a Researcher feature</h2>
          <p className="text-slate-500 text-sm mt-3 max-w-sm mx-auto">
            Upgrade to Researcher to generate publication-quality abstracts from your paper content
            — keywords, key contribution, and multiple academic styles included.
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
  { value: "academic",    label: "Academic",    desc: "Standard IMRaD structure" },
  { value: "structured",  label: "Structured",  desc: "Explicit section labels" },
  { value: "concise",     label: "Concise",     desc: "Tight single paragraph" },
  { value: "narrative",   label: "Narrative",   desc: "Flowing prose" },
];

function InputView({ onResult, gated }) {
  const [form, setForm] = useState({ title: "", content: "", style: "academic", max_words: 250 });
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const valid = form.title.trim().length >= 3 && form.content.trim().length >= 50;

  const submit = async (e) => {
    e.preventDefault();
    if (!valid || running) return;
    setRunning(true);
    setError(null);
    try {
      const res = await api.post("/ai/abstract/generate", {
        title: form.title.trim(),
        content: form.content.trim(),
        style: form.style,
        max_words: Number(form.max_words),
      }, { timeout: 120_000 });
      onResult(res.data);
    } catch (err) {
      setRunning(false);
      if (err?.response?.status === 402) return;
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Generation failed. Please try again.");
    }
  };

  if (gated) return <GateView />;

  return (
    <div className="space-y-6">

      <div className="grid lg:grid-cols-3 gap-6">
        <form onSubmit={submit} className="lg:col-span-2 space-y-4">
          <div className="border border-slate-200 bg-white p-5 space-y-4">
            <div className="overline text-[10px] text-slate-400 mb-1">Required</div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Paper Title</label>
              <input value={form.title} onChange={set("title")} required
                placeholder="e.g. Attention mechanisms in transformer-based language models"
                className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]" />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Paper Content
                <span className="font-normal text-slate-500 ml-1">(paste sections, methods, results, or full text)</span>
              </label>
              <textarea value={form.content} onChange={set("content")} required rows={10}
                placeholder="Paste your introduction, methods, results and discussion here — the more context you provide, the more accurate the abstract."
                className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847] resize-y" />
              <div className="text-[10px] text-slate-400 mt-1 font-mono">
                {form.content.length} / 20,000 characters
              </div>
            </div>
          </div>

          <div className="border border-slate-200 bg-white p-5 space-y-4">
            <div className="overline text-[10px] text-slate-400 mb-1">Options</div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Abstract Style</label>
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
                Target length <span className="font-normal text-slate-500">({form.max_words} words)</span>
              </label>
              <input type="range" min={100} max={400} step={25}
                value={form.max_words} onChange={set("max_words")}
                className="w-full accent-[#0F2847]" />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-0.5">
                <span>100</span><span>250</span><span>400</span>
              </div>
            </div>
          </div>

          {error && (
            <div className="border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          )}

          <button type="submit" disabled={!valid || running}
            className="w-full bg-[#0F2847] text-white py-3 text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2">
            {running ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Generating abstract — this may take 15–30 seconds…
              </>
            ) : (
              <>
                <FileText size={15} strokeWidth={1.5} />
                Generate Abstract · 5 Credits
              </>
            )}
          </button>
        </form>

        {/* Info panel */}
        <div className="space-y-4">
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-3">Output includes</div>
            <ul className="space-y-2 text-sm text-slate-600">
              {["Complete abstract text", "5–8 subject keywords", "Key contribution sentence", "Word count"].map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-[#0F2847]" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="border border-slate-200 bg-white p-5">
            <div className="overline mb-2">Credit cost</div>
            <div className="font-serif text-3xl text-slate-900">5</div>
            <div className="text-xs text-slate-500 mt-1">Research Credits per abstract</div>
          </div>
          <div className="border border-amber-100 bg-amber-50 p-4">
            <div className="overline text-[10px] text-amber-700 mb-1">Accuracy note</div>
            <p className="text-xs text-amber-800 leading-relaxed">
              The abstract is synthesised from the content you provide. Always review before
              submitting — verify that all claims accurately reflect your paper's findings.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────── result view ─────────────────────────────────────

function ResultView({ result, onNew }) {
  const r = result.result || {};
  return (
    <div className="space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="overline">AI Abstract Generator</div>
            <h1 className="font-serif text-4xl text-slate-900 mt-1 leading-tight break-words">
              {result.title}
            </h1>
            <div className="flex flex-wrap items-center gap-3 mt-3">
              <span className="flex items-center gap-1 text-xs text-slate-500 font-mono">
                <Clock size={11} strokeWidth={1.5} />
                {new Date(result.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}
              </span>
              <span className="text-xs text-slate-500 font-mono">{result.credits_used} credits</span>
              <span className="text-xs border border-slate-200 px-2 py-0.5 text-slate-500 font-mono capitalize">{result.style}</span>
              {r.word_count && (
                <span className="text-xs text-slate-500 font-mono">{r.word_count} words</span>
              )}
            </div>
          </div>
          <button onClick={onNew}
            className="shrink-0 flex items-center gap-2 border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors">
            <RotateCcw size={13} strokeWidth={1.5} /> New Abstract
          </button>
        </div>
      </header>

      {/* Abstract text */}
      <div className="border border-[#0F2847] bg-white p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="overline text-[#0F2847]">Abstract</div>
          <CopyButton text={r.abstract || ""} />
        </div>
        <p className="text-slate-800 leading-[1.85] font-serif">{r.abstract}</p>
      </div>

      {/* Key contribution */}
      {r.key_contribution && (
        <div className="border border-slate-200 bg-white p-5">
          <div className="overline text-[10px] text-slate-400 mb-2">Key Contribution</div>
          <p className="text-sm text-slate-700 leading-relaxed italic">"{r.key_contribution}"</p>
        </div>
      )}

      {/* Keywords */}
      {r.keywords?.length > 0 && (
        <div className="border border-slate-200 bg-white p-5">
          <div className="overline text-[10px] text-slate-400 mb-3">Keywords</div>
          <div className="flex flex-wrap gap-2">
            {r.keywords.map((k, i) => (
              <span key={i} className="inline-flex items-center gap-1 border border-slate-200 text-slate-600 text-xs px-2.5 py-1">
                <Tag size={10} strokeWidth={1.5} /> {k}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────── history ─────────────────────────────────────────

function HistoryItem({ item, active, onSelect }) {
  return (
    <button onClick={() => onSelect(item)}
      className={`w-full text-left px-4 py-3 border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors ${active ? "bg-slate-50" : ""}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium text-slate-900 truncate">{item.title}</div>
          <div className="text-xs text-slate-500 mt-0.5 capitalize">{item.style} · {item.max_words} words</div>
        </div>
        <div className="shrink-0 text-xs text-slate-400 font-mono whitespace-nowrap">
          {new Date(item.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
        </div>
      </div>
    </button>
  );
}

// ─────────────────────────── main page ───────────────────────────────────────

export default function AbstractGenerator() {
  const [gated, setGated]     = useState(false);
  const [result, setResult]   = useState(null);
  const [history, setHistory] = useState([]);

  const loadHistory = useCallback(async () => {
    try {
      const res = await api.get("/ai/abstract/history");
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
        const res = await api.get(`/ai/abstract/${item.id}`);
        setResult(res.data);
      } catch {/* ignore */}
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <AIWorkspaceLayout
      title="Abstract Generator"
      subtitle="Generate publication-quality abstracts from your paper content."
    >
      <div className="space-y-10">
        {result ? (
          <ResultView result={result} onNew={() => setResult(null)} />
        ) : (
          <InputView gated={gated} onResult={(r) => { setResult(r); loadHistory(); }} />
        )}

        {history.length > 0 && !gated && (
          <section>
            <div className="overline mb-3">Generation History</div>
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

import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PenLine, Lock, RotateCcw, Clock, Copy, Check, ChevronDown, ChevronUp } from "lucide-react";
import api from "../lib/api";
import { WARM } from "@/lib/tokens";
import { ErrorState } from "@/components/ds/ErrorState";
import { Button, Card, Input, Textarea, EmptyState } from "@/components/ds";
import { ResearchLayout } from "@/layouts";
import { AI_NAV_ITEMS } from "@/lib/navItems";

// ─────────────────────────── shared primitives ───────────────────────────────

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }
    catch {/* ignore */}
  };
  return (
    <Button onClick={copy} variant="ghost" size="sm">
      {copied ? <Check size={12} strokeWidth={2} /> : <Copy size={12} strokeWidth={1.5} />}
      {copied ? "Copied" : "Copy text"}
    </Button>
  );
}

// ─────────────────────────── gate view ───────────────────────────────────────

function GateView() {
  return (
    <EmptyState
      icon={<Lock />}
      title={
        <>
          <div className="overline text-[#0F2847] mb-2">Researcher plan required</div>
          AI Rewriting is a Researcher feature
        </>
      }
      description="Upgrade to Researcher to rewrite and refine your academic writing — improve clarity, tone, and style while preserving your original meaning."
      action={<Button as={Link} to="/pricing">View Plans</Button>}
      size="lg"
    />
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
          <Card padding="lg" className="space-y-4">
            <div className="overline text-[10px] text-slate-400 mb-1">Text to rewrite</div>

            <div>
              <Textarea
                value={form.text} onChange={set("text")} required rows={10}
                placeholder="Paste the passage you want to rewrite — a paragraph, section, or full passage (up to 5,000 characters)."
              />
              <div className="text-[10px] text-slate-400 mt-1 font-mono">
                {form.text.length} / 5,000 characters
              </div>
            </div>
          </Card>

          <Card padding="lg" className="space-y-4">
            <div className="overline text-[10px] text-slate-400 mb-1">Options</div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Rewriting Style</label>
              <div className="grid grid-cols-2 gap-2">
                {STYLES.map((s) => (
                  <Card key={s.value}
                    as="button"
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, style: s.value }))}
                    padding="sm"
                    className={`text-left ${form.style === s.value ? "!border-[#0F2847] !bg-[#0F2847]/5" : ""}`}>
                    <div className="text-sm font-medium text-slate-900">{s.label}</div>
                    <div className="text-[10px] text-slate-500 mt-0.5">{s.desc}</div>
                  </Card>
                ))}
              </div>
            </div>

            <Input
              label={<>Custom instruction <span className="font-normal text-slate-500">(optional)</span></>}
              value={form.instruction} onChange={set("instruction")}
              placeholder='e.g. "Avoid passive voice" or "Use hedging language appropriate for a lit review"'
            />
          </Card>

          {error && (
            <ErrorState message={error} type="generic" />
          )}

          <Button type="submit" disabled={!valid} loading={running} className="w-full py-3">
            {running ? "Rewriting — this may take 10–20 seconds…" : (
              <>
                <PenLine size={15} strokeWidth={1.5} />
                Rewrite · 2 Credits
              </>
            )}
          </Button>
        </form>

        {/* Info panel */}
        <div className="space-y-4">
          <Card padding="lg">
            <div className="overline mb-3">Output includes</div>
            <ul className="space-y-2 text-sm text-slate-600">
              {["Rewritten passage", "Summary of changes made", "Before / after word count"].map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-[#0F2847]" />
                  {item}
                </li>
              ))}
            </ul>
          </Card>
          <Card padding="lg">
            <div className="overline mb-2">Credit cost</div>
            <div className="font-serif text-3xl text-slate-900">2</div>
            <div className="text-xs text-slate-500 mt-1">Research Credits per rewrite</div>
          </Card>
          <Card padding="md" className="!border-amber-100 !bg-amber-50">
            <div className="overline text-[10px] text-amber-700 mb-1">Academic integrity</div>
            <p className="text-xs text-amber-800 leading-relaxed">
              This tool helps improve how ideas are expressed, not generate new content.
              Always disclose AI assistance according to your institution's policy.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────── result view ─────────────────────────────────────

function OriginalCollapsible({ text }) {
  const [open, setOpen] = useState(false);
  return (
    <Card padding="none">
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
    </Card>
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
          <Button onClick={onNew} variant="ghost" className="shrink-0">
            <RotateCcw size={13} strokeWidth={1.5} /> New Rewrite
          </Button>
        </div>
      </header>

      {/* Rewritten text */}
      <Card padding="lg" className="!border-[#0F2847]">
        <div className="flex items-center justify-between mb-4">
          <div className="overline text-[#0F2847]">Rewritten Version</div>
          <CopyButton text={r.rewritten_text || ""} />
        </div>
        <p className="text-slate-800 leading-[1.85] whitespace-pre-wrap">{r.rewritten_text}</p>
      </Card>

      {/* Changes summary */}
      {r.changes_summary && (
        <Card padding="lg">
          <div className="overline text-[10px] text-slate-400 mb-2">Changes Made</div>
          <p className="text-sm text-slate-700 leading-relaxed">{r.changes_summary}</p>
        </Card>
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
    <ResearchLayout
      navItems={AI_NAV_ITEMS}
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
            <Card padding="none" className="divide-y divide-slate-100">
              {history.map((h) => (
                <HistoryItem key={h.id} item={h} active={result?.id === h.id} onSelect={openHistoryItem} />
              ))}
            </Card>
          </section>
        )}
      </div>
    </ResearchLayout>
  );
}

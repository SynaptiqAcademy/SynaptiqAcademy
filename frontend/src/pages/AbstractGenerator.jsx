import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, Lock, RotateCcw, Clock, Copy, Check, Tag as TagIcon } from "lucide-react";
import api from "../lib/api";
import { WARM } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { AI_NAV_ITEMS } from "@/lib/navItems";
import { Button, Card, Input, Textarea, Tag, TagGroup, EmptyState } from "@/components/ds";



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
          AI Abstract Generator is a Researcher feature
        </>
      }
      description="Upgrade to Researcher to generate publication-quality abstracts from your paper content — keywords, key contribution, and multiple academic styles included."
      action={<Button as={Link} to="/pricing">View Plans</Button>}
      size="lg"
    />
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
          <Card padding="lg" className="space-y-4">
            <div className="overline text-[10px] text-slate-400 mb-1">Required</div>

            <Input
              label="Paper Title"
              value={form.title} onChange={set("title")} required
              placeholder="e.g. Attention mechanisms in transformer-based language models"
            />

            <div>
              <Textarea
                label={
                  <>
                    Paper Content
                    <span className="font-normal text-slate-500 ml-1">(paste sections, methods, results, or full text)</span>
                  </>
                }
                value={form.content} onChange={set("content")} required rows={10}
                placeholder="Paste your introduction, methods, results and discussion here — the more context you provide, the more accurate the abstract."
              />
              <div className="text-[10px] text-slate-400 mt-1 font-mono">
                {form.content.length} / 20,000 characters
              </div>
            </div>
          </Card>

          <Card padding="lg" className="space-y-4">
            <div className="overline text-[10px] text-slate-400 mb-1">Options</div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Abstract Style</label>
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
          </Card>

          {error && (
            <div className="border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          )}

          <Button type="submit" disabled={!valid} loading={running} className="w-full py-3">
            {running ? "Generating abstract — this may take 15–30 seconds…" : (
              <>
                <FileText size={15} strokeWidth={1.5} />
                Generate Abstract · 5 Credits
              </>
            )}
          </Button>
        </form>

        {/* Info panel */}
        <div className="space-y-4">
          <Card padding="lg">
            <div className="overline mb-3">Output includes</div>
            <ul className="space-y-2 text-sm text-slate-600">
              {["Complete abstract text", "5–8 subject keywords", "Key contribution sentence", "Word count"].map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-[#0F2847]" />
                  {item}
                </li>
              ))}
            </ul>
          </Card>
          <Card padding="lg">
            <div className="overline mb-2">Credit cost</div>
            <div className="font-serif text-3xl text-slate-900">5</div>
            <div className="text-xs text-slate-500 mt-1">Research Credits per abstract</div>
          </Card>
          <Card padding="md" className="!border-amber-100 !bg-amber-50">
            <div className="overline text-[10px] text-amber-700 mb-1">Accuracy note</div>
            <p className="text-xs text-amber-800 leading-relaxed">
              The abstract is synthesised from the content you provide. Always review before
              submitting — verify that all claims accurately reflect your paper's findings.
            </p>
          </Card>
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
          <Button onClick={onNew} variant="ghost" className="shrink-0">
            <RotateCcw size={13} strokeWidth={1.5} /> New Abstract
          </Button>
        </div>
      </header>

      {/* Abstract text */}
      <Card padding="lg" className="!border-[#0F2847]">
        <div className="flex items-center justify-between mb-4">
          <div className="overline text-[#0F2847]">Abstract</div>
          <CopyButton text={r.abstract || ""} />
        </div>
        <p className="text-slate-800 leading-[1.85] font-serif">{r.abstract}</p>
      </Card>

      {/* Key contribution */}
      {r.key_contribution && (
        <Card padding="lg">
          <div className="overline text-[10px] text-slate-400 mb-2">Key Contribution</div>
          <p className="text-sm text-slate-700 leading-relaxed italic">"{r.key_contribution}"</p>
        </Card>
      )}

      {/* Keywords */}
      {r.keywords?.length > 0 && (
        <Card padding="lg">
          <div className="overline text-[10px] text-slate-400 mb-3">Keywords</div>
          <TagGroup gap={8}>
            {r.keywords.map((k, i) => (
              <Tag key={i}><TagIcon size={10} strokeWidth={1.5} /> {k}</Tag>
            ))}
          </TagGroup>
        </Card>
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
// Note: HistoryItem's button is kept as a raw <button> — it's a full-width list
// row (title + meta + date, active-state background) whose layout doesn't map
// onto Button's centered inline-flex sizing presets without losing the row layout.

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
    <ResearchLayout
      navItems={AI_NAV_ITEMS}
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

import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen, Lock, RotateCcw, Clock, ChevronDown, ChevronUp,
  Copy, Check, AlertTriangle, Lightbulb, TrendingUp,
  Users, FlaskConical, MessageSquare, BookMarked, Compass,
} from "lucide-react";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { NAVY, WARM } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { AI_NAV_ITEMS } from "@/lib/navItems";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Tag as DsTag } from "@/components/ds/Tag";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { InlineError, Callout } from "@/components/ds/Alert";

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
  return <DsTag size="sm" className={className}>{children}</DsTag>;
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

function ExpandCard({ title, subtitle, badge, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const Chev = open ? ChevronUp : ChevronDown;
  return (
    <Card padding="none">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-start justify-between gap-4 px-5 py-4 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="font-serif text-base text-slate-900 leading-snug">{title}</div>
          {subtitle && <div className="text-sm text-slate-500 mt-0.5">{subtitle}</div>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {badge && <Badge variant="outline" size="sm" className="font-mono">{badge}</Badge>}
          <Chev size={15} strokeWidth={1.5} className="text-slate-400" />
        </div>
      </button>
      {open && (
        <div className="border-t border-slate-100 px-5 pb-5 pt-4">
          {children}
        </div>
      )}
    </Card>
  );
}

// ─────────────────────────── copy button ─────────────────────────────────────

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {/* ignore */}
  };
  return (
    <Button onClick={copy} variant="outline" size="sm">
      {copied ? <Check size={12} strokeWidth={2} /> : <Copy size={12} strokeWidth={1.5} />}
      {copied ? "Copied" : "Copy text"}
    </Button>
  );
}

// ─────────────────────────── prevalence badge ─────────────────────────────────

const PREVALENCE_CFG = {
  common:     { label: "Common",     variant: "danger"  },
  occasional: { label: "Occasional", variant: "warning" },
  notable:    { label: "Notable",    variant: "info"    },
};
function PrevalenceBadge({ value }) {
  const cfg = PREVALENCE_CFG[value] || PREVALENCE_CFG.notable;
  return (
    <Badge variant={cfg.variant} size="sm" className="uppercase tracking-wider">
      {cfg.label}
    </Badge>
  );
}

// ─────────────────────────── gate view ───────────────────────────────────────

function GateView() {
  return (
    <div className="space-y-6">
      <Card padding="xl" className="!p-16 flex flex-col items-center text-center gap-5">
        <Lock size={28} strokeWidth={1} className="text-slate-300" />
        <div>
          <div className="overline text-[#0F2847] mb-2">Pro Researcher plan required</div>
          <h2 className="font-serif text-2xl text-slate-900">AI Literature Review is a Pro feature</h2>
          <p className="text-slate-500 text-sm mt-3 max-w-sm mx-auto">
            Upgrade to Pro Researcher to generate structured, publication-ready literature reviews
            covering themes, debates, theoretical foundations, and future research directions.
          </p>
        </div>
        <Button as={Link} to="/pricing" variant="primary">
          View Plans
        </Button>
      </Card>
    </div>
  );
}

// ─────────────────────────── input form ──────────────────────────────────────

const DISCIPLINES = [
  "", "Biomedical Sciences", "Computer Science", "Economics", "Education",
  "Engineering", "Environmental Science", "Law", "Management", "Medicine",
  "Philosophy", "Political Science", "Psychology", "Public Health",
  "Sociology", "Other",
];

function InputView({ onResult, gated }) {
  const [form, setForm] = useState({
    topic: "", research_question: "", keywords: "",
    discipline: "", methodology_preference: "", year_from: "", year_to: "",
  });
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [showOptional, setShowOptional] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const valid = form.topic.trim().length >= 3 &&
                form.research_question.trim().length >= 10 &&
                form.keywords.trim().length >= 2;

  const submit = async (e) => {
    e.preventDefault();
    if (!valid || running) return;
    setRunning(true);
    setError(null);
    const keywords = form.keywords.split(",").map((k) => k.trim()).filter(Boolean);
    const payload = {
      topic: form.topic.trim(),
      research_question: form.research_question.trim(),
      keywords,
      discipline: form.discipline || undefined,
      methodology_preference: form.methodology_preference || undefined,
      year_from: form.year_from ? parseInt(form.year_from, 10) : undefined,
      year_to: form.year_to ? parseInt(form.year_to, 10) : undefined,
    };
    try {
      const res = await api.post("/literature-review", payload, { timeout: 180_000 });
      onResult(res.data);
    } catch (err) {
      setRunning(false);
      if (err?.response?.status === 402) return; // global UpgradeModal fires
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Generation failed. Please try again.");
    }
  };

  if (gated) return <GateView />;

  return (
    <div className="space-y-6">
      <div className="grid lg:grid-cols-3 gap-6">
        <form
          onSubmit={submit}
          data-testid={TID.literatureReviewForm}
          className="lg:col-span-2 space-y-4"
        >
          {/* Required fields */}
          <Card padding="lg" className="space-y-4">
            <div className="overline text-[10px] text-slate-400 mb-1">Required</div>

            <Input
              label="Research Topic"
              data-testid={TID.literatureReviewTopic}
              value={form.topic}
              onChange={set("topic")}
              placeholder="e.g. Machine learning in clinical decision support systems"
              required
            />

            <Textarea
              label="Research Question"
              data-testid={TID.literatureReviewQuestion}
              value={form.research_question}
              onChange={set("research_question")}
              rows={3}
              placeholder="e.g. What are the key barriers to clinical adoption of ML-based diagnostic tools, and how have researchers proposed overcoming them?"
              required
            />

            <Input
              label="Keywords"
              hint="Comma-separated"
              data-testid={TID.literatureReviewKeywords}
              value={form.keywords}
              onChange={set("keywords")}
              placeholder="e.g. clinical decision support, machine learning, interoperability, EHR integration"
              required
            />
          </Card>

          {/* Optional fields */}
          <Card padding="none">
            <button
              type="button"
              onClick={() => setShowOptional((o) => !o)}
              className="w-full flex items-center justify-between px-5 py-3 text-sm text-slate-600 hover:bg-slate-50"
            >
              <span className="overline text-[10px]">Optional parameters</span>
              {showOptional
                ? <ChevronUp size={13} strokeWidth={1.5} className="text-slate-400" />
                : <ChevronDown size={13} strokeWidth={1.5} className="text-slate-400" />
              }
            </button>

            {showOptional && (
              <div className="border-t border-slate-100 px-5 pb-5 pt-4 space-y-4">
                <FormSelect label="Discipline" value={form.discipline} onChange={set("discipline")}>
                  {DISCIPLINES.map((d) => (
                    <option key={d} value={d}>{d || "Select discipline…"}</option>
                  ))}
                </FormSelect>

                <Input
                  label="Methodology Preference"
                  value={form.methodology_preference}
                  onChange={set("methodology_preference")}
                  placeholder="e.g. qualitative, mixed-methods, systematic review, RCT-focused"
                />

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <Input
                    label="Year from"
                    type="number"
                    value={form.year_from}
                    onChange={set("year_from")}
                    placeholder="2000"
                    min="1900" max="2100"
                  />
                  <Input
                    label="Year to"
                    type="number"
                    value={form.year_to}
                    onChange={set("year_to")}
                    placeholder="2024"
                    min="1900" max="2100"
                  />
                </div>
              </div>
            )}
          </Card>

          {error && <InlineError>{error}</InlineError>}

          <Button
            type="submit"
            data-testid={TID.literatureReviewSubmitBtn}
            disabled={!valid || running}
            loading={running}
            variant="primary"
            size="lg"
            className="w-full"
          >
            {running ? (
              "Generating literature review — this may take up to 90 seconds…"
            ) : (
              <>
                <BookOpen size={15} strokeWidth={1.5} />
                Generate Literature Review · 20 Credits
              </>
            )}
          </Button>
        </form>

        {/* Info panel */}
        <div className="space-y-4">
          <Card padding="lg">
            <div className="overline mb-3">Output includes</div>
            <ul className="space-y-2 text-sm text-slate-600">
              {[
                ["BookOpen", "Executive Summary"],
                ["Compass", "Major Research Themes"],
                ["Users", "Key Authors & Contributions"],
                ["BookMarked", "Theoretical Foundations"],
                ["FlaskConical", "Methodological Trends"],
                ["MessageSquare", "Current Debates"],
                ["AlertTriangle", "Research Limitations"],
                ["TrendingUp", "Emerging Directions"],
                ["Lightbulb", "Future Research Opportunities"],
                ["BookOpen", "Literature Review Draft"],
              ].map(([, label]) => (
                <li key={label} className="flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-[#0F2847]" />
                  {label}
                </li>
              ))}
            </ul>
          </Card>
          <Card padding="lg">
            <div className="overline mb-2">Credit cost</div>
            <div className="font-serif text-3xl text-slate-900">20</div>
            <div className="text-xs text-slate-500 mt-1">Research Credits per review</div>
          </Card>
          <Callout variant="warning" title="Knowledge basis">
            This review is synthesised from Claude's training knowledge — not live database
            retrieval. Author names and works cited are based on what Claude genuinely knows;
            verify specific citations before submitting to a journal.
          </Callout>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────── result sections ─────────────────────────────────

function ExecutiveSummary({ data }) {
  if (!data) return null;
  return (
    <Card padding="xl" className="space-y-4">
      <SectionHeader icon={BookOpen} label="Executive Summary" />
      <p className="text-slate-700 leading-relaxed">{data.overview}</p>
      {data.scope_assessment && (
        <div>
          <div className="overline text-[10px] text-slate-400 mb-1">Scope Assessment</div>
          <p className="text-sm text-slate-600 leading-relaxed">{data.scope_assessment}</p>
        </div>
      )}
      {data.review_confidence && (
        <div>
          <div className="overline text-[10px] text-slate-400 mb-1">Review Confidence</div>
          <p className="text-sm text-slate-600 leading-relaxed">{data.review_confidence}</p>
        </div>
      )}
    </Card>
  );
}

function MajorThemes({ items }) {
  if (!items?.length) return null;
  return (
    <section>
      <SectionHeader icon={Compass} label="Major Research Themes" />
      <div className="space-y-2">
        {items.map((t, i) => (
          <ExpandCard
            key={i}
            title={t.theme}
            badge={`Theme ${i + 1}`}
            defaultOpen={i === 0}
          >
            <div className="space-y-3">
              <div>
                <div className="overline text-[10px] text-slate-400 mb-1">Explanation</div>
                <p className="text-sm text-slate-700 leading-relaxed">{t.explanation}</p>
              </div>
              {t.importance && (
                <div>
                  <div className="overline text-[10px] text-slate-400 mb-1">Importance</div>
                  <p className="text-sm text-slate-700 leading-relaxed">{t.importance}</p>
                </div>
              )}
              {t.current_direction && (
                <div>
                  <div className="overline text-[10px] text-slate-400 mb-1">Current Direction</div>
                  <p className="text-sm text-slate-700 leading-relaxed">{t.current_direction}</p>
                </div>
              )}
            </div>
          </ExpandCard>
        ))}
      </div>
    </section>
  );
}

function KeyAuthors({ items }) {
  if (!items?.length) return null;
  return (
    <section>
      <SectionHeader icon={Users} label="Key Authors & Contributions" />
      <div className="space-y-2">
        {items.map((a, i) => (
          <ExpandCard
            key={i}
            title={a.name}
            subtitle={a.affiliation || undefined}
          >
            <div className="space-y-3">
              <div>
                <div className="overline text-[10px] text-slate-400 mb-1">Primary Contribution</div>
                <p className="text-sm text-slate-700 leading-relaxed">{a.primary_contribution}</p>
              </div>
              {a.notable_works?.length > 0 && (
                <div>
                  <div className="overline text-[10px] text-slate-400 mb-1">Notable Works</div>
                  <ul className="space-y-1">
                    {a.notable_works.map((w, j) => (
                      <li key={j} className="text-sm text-slate-600 italic">{w}</li>
                    ))}
                  </ul>
                </div>
              )}
              {a.theoretical_stance && (
                <div>
                  <div className="overline text-[10px] text-slate-400 mb-1">Theoretical Stance</div>
                  <p className="text-sm text-slate-600">{a.theoretical_stance}</p>
                </div>
              )}
            </div>
          </ExpandCard>
        ))}
      </div>
    </section>
  );
}

function TheoreticalFoundations({ items }) {
  if (!items?.length) return null;
  return (
    <section>
      <SectionHeader icon={BookMarked} label="Theoretical Foundations" />
      <div className="space-y-2">
        {items.map((t, i) => (
          <ExpandCard key={i} title={t.theory} subtitle={t.origin || undefined}>
            <div className="space-y-3">
              <div>
                <div className="overline text-[10px] text-slate-400 mb-1">Relevance to Topic</div>
                <p className="text-sm text-slate-700 leading-relaxed">{t.relevance_to_topic}</p>
              </div>
              {t.key_proponents?.length > 0 && (
                <div>
                  <div className="overline text-[10px] text-slate-400 mb-1">Key Proponents</div>
                  <div className="flex flex-wrap gap-1.5">
                    {t.key_proponents.map((p, j) => <Tag key={j}>{p}</Tag>)}
                  </div>
                </div>
              )}
            </div>
          </ExpandCard>
        ))}
      </div>
    </section>
  );
}

function MethodologicalTrends({ data }) {
  if (!data) return null;
  return (
    <section>
      <SectionHeader icon={FlaskConical} label="Methodological Trends" />
      <Card padding="lg" className="space-y-5">
        {data.synthesis && (
          <p className="text-sm text-slate-700 leading-relaxed">{data.synthesis}</p>
        )}
        <div className="grid sm:grid-cols-3 gap-4">
          {[
            { label: "Dominant Methods", items: data.dominant_methods, color: "#0F2847" },
            { label: "Emerging Methods", items: data.emerging_methods, color: "#16a34a" },
            { label: "Methodological Gaps", items: data.methodological_gaps, color: "#dc2626" },
          ].map(({ label, items, color }) =>
            items?.length ? (
              <div key={label}>
                <div className="overline text-[10px] mb-2" style={{ color }}>{label}</div>
                <BulletList items={items} />
              </div>
            ) : null
          )}
        </div>
      </Card>
    </section>
  );
}

function CurrentDebates({ items }) {
  if (!items?.length) return null;
  return (
    <section>
      <SectionHeader icon={MessageSquare} label="Current Debates" />
      <div className="space-y-2">
        {items.map((d, i) => (
          <ExpandCard key={i} title={d.debate_title}>
            <div className="space-y-4">
              {d.positions?.map((p, j) => (
                <div key={j} className="border-l-2 border-slate-200 pl-4">
                  <div className="flex items-center gap-2 mb-1">
                    <div className="overline text-[10px] text-slate-500">{p.stance}</div>
                    {p.proponents?.length > 0 && (
                      <div className="flex gap-1">
                        {p.proponents.map((name, k) => <Tag key={k}>{name}</Tag>)}
                      </div>
                    )}
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed">{p.key_argument}</p>
                </div>
              ))}
              {d.current_state && (
                <div>
                  <div className="overline text-[10px] text-slate-400 mb-1">Current State</div>
                  <p className="text-sm text-slate-600 leading-relaxed">{d.current_state}</p>
                </div>
              )}
            </div>
          </ExpandCard>
        ))}
      </div>
    </section>
  );
}

function ResearchLimitations({ items }) {
  if (!items?.length) return null;
  return (
    <section>
      <SectionHeader icon={AlertTriangle} label="Research Limitations in Existing Literature" />
      <Card padding="none" className="divide-y divide-slate-100">
        {items.map((l, i) => (
          <div key={i} className="px-5 py-4">
            <div className="flex items-start justify-between gap-3">
              <div className="font-medium text-sm text-slate-800">{l.limitation}</div>
              <PrevalenceBadge value={l.prevalence} />
            </div>
            {l.impact_on_field && (
              <p className="text-sm text-slate-600 mt-1.5 leading-relaxed">{l.impact_on_field}</p>
            )}
          </div>
        ))}
      </Card>
    </section>
  );
}

function EmergingDirections({ items }) {
  if (!items?.length) return null;
  return (
    <section>
      <SectionHeader icon={TrendingUp} label="Emerging Research Directions" />
      <div className="space-y-2">
        {items.map((d, i) => (
          <ExpandCard key={i} title={d.direction}>
            <div className="space-y-3">
              {d.rationale && (
                <div>
                  <div className="overline text-[10px] text-slate-400 mb-1">Rationale</div>
                  <p className="text-sm text-slate-700 leading-relaxed">{d.rationale}</p>
                </div>
              )}
              {d.potential_impact && (
                <div>
                  <div className="overline text-[10px] text-slate-400 mb-1">Potential Impact</div>
                  <p className="text-sm text-slate-700 leading-relaxed">{d.potential_impact}</p>
                </div>
              )}
              {d.early_indicators && (
                <div>
                  <div className="overline text-[10px] text-slate-400 mb-1">Early Indicators</div>
                  <p className="text-sm text-slate-600 leading-relaxed">{d.early_indicators}</p>
                </div>
              )}
            </div>
          </ExpandCard>
        ))}
      </div>
    </section>
  );
}

function FutureResearch({ items }) {
  if (!items?.length) return null;
  return (
    <section>
      <SectionHeader icon={Lightbulb} label="Suggested Future Research Opportunities" />
      <div className="space-y-2">
        {items.map((r, i) => (
          <ExpandCard key={i} title={r.opportunity}>
            <div className="space-y-3">
              {r.suggested_research_question && (
                <Card padding="none" variant="ghost" className="!bg-slate-50 border border-[#0F2847] px-4 py-3">
                  <div className="overline text-[10px] text-[#0F2847] mb-1">Research Question</div>
                  <p className="text-sm text-slate-700 italic leading-relaxed">
                    "{r.suggested_research_question}"
                  </p>
                </Card>
              )}
              {r.suggested_methodology && (
                <div>
                  <div className="overline text-[10px] text-slate-400 mb-1">Suggested Methodology</div>
                  <p className="text-sm text-slate-600">{r.suggested_methodology}</p>
                </div>
              )}
              {r.potential_contribution && (
                <div>
                  <div className="overline text-[10px] text-slate-400 mb-1">Potential Contribution</div>
                  <p className="text-sm text-slate-600 leading-relaxed">{r.potential_contribution}</p>
                </div>
              )}
            </div>
          </ExpandCard>
        ))}
      </div>
    </section>
  );
}

function LiteratureDraft({ text }) {
  if (!text) return null;
  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <SectionHeader icon={BookOpen} label="Literature Review Draft" />
        <CopyButton text={text} />
      </div>
      <Card padding="xl" style={{ borderColor: "#0F2847" }}>
        <div className="text-sm text-slate-700 leading-[1.85] whitespace-pre-wrap font-serif">
          {text}
        </div>
        <div className="mt-4 pt-4 border-t border-slate-100">
          <p className="text-xs text-slate-400">
            This draft is synthesised from Claude's training knowledge. Verify specific citations
            and supplement with live database searches before journal submission.
          </p>
        </div>
      </Card>
    </section>
  );
}

// ─────────────────────────── result view ─────────────────────────────────────

function ResultView({ review, onNew }) {
  const rj = review.review_json || {};

  return (
    <div className="space-y-8" data-testid={TID.literatureReviewResult}>
      {/* Page header */}
      <header className="border-b border-slate-200 pb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="overline">AI Literature Review</div>
            <h1 className="font-serif text-4xl text-slate-900 mt-1 leading-tight break-words">
              {review.topic}
            </h1>
            <p className="text-slate-500 text-sm mt-2 italic max-w-2xl line-clamp-2">
              {review.research_question}
            </p>
            <div className="flex flex-wrap items-center gap-3 mt-3">
              <span className="flex items-center gap-1 text-xs text-slate-500 font-mono">
                <Clock size={11} strokeWidth={1.5} />
                {new Date(review.created_at).toLocaleDateString("en-GB", {
                  day: "numeric", month: "long", year: "numeric",
                })}
              </span>
              <span className="text-xs text-slate-500 font-mono">{review.credits_used} credits</span>
              {review.discipline && <Tag>{review.discipline}</Tag>}
              {(review.year_from || review.year_to) && (
                <Tag>{review.year_from || "–"}–{review.year_to || "present"}</Tag>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {(review.keywords || []).map((k, i) => <Tag key={i}>{k}</Tag>)}
            </div>
          </div>
          <Button onClick={onNew} variant="outline" size="sm" className="shrink-0">
            <RotateCcw size={13} strokeWidth={1.5} />
            New Review
          </Button>
        </div>
      </header>

      <ExecutiveSummary   data={rj.executive_summary} />
      <MajorThemes        items={rj.major_themes} />
      <KeyAuthors         items={rj.key_authors} />
      <TheoreticalFoundations items={rj.theoretical_foundations} />
      <MethodologicalTrends   data={rj.methodological_trends} />
      <CurrentDebates     items={rj.current_debates} />
      <ResearchLimitations items={rj.research_limitations} />
      <EmergingDirections items={rj.emerging_directions} />
      <FutureResearch     items={rj.future_research} />
      <LiteratureDraft    text={rj.literature_draft} />
    </div>
  );
}

// ─────────────────────────── history item ────────────────────────────────────

function HistoryItem({ review, active, onSelect }) {
  return (
    <Card
      onClick={() => onSelect(review)}
      variant="ghost"
      padding="none"
      className={`w-full text-left px-4 py-3 border-b border-slate-100 last:border-0 hover:bg-slate-50 ${active ? "bg-slate-50" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium text-slate-900 truncate">{review.topic}</div>
          <div className="text-xs text-slate-500 mt-0.5 truncate italic">{review.research_question}</div>
          <div className="flex flex-wrap gap-1 mt-1.5">
            {(review.keywords || []).slice(0, 3).map((k, i) => <Tag key={i}>{k}</Tag>)}
          </div>
        </div>
        <div className="shrink-0 text-xs text-slate-400 font-mono whitespace-nowrap">
          {new Date(review.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
        </div>
      </div>
    </Card>
  );
}

// ─────────────────────────── main page ───────────────────────────────────────

export default function LiteratureReview() {
  const [gated, setGated]     = useState(false);
  const [review, setReview]   = useState(null);
  const [history, setHistory] = useState([]);

  const loadHistory = useCallback(async () => {
    try {
      const res = await api.get("/literature-review/history");
      setHistory(res.data || []);
    } catch (err) {
      if (err?.response?.status === 402) setGated(true);
    }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  const openHistoryItem = async (item) => {
    if (item.review_json) {
      setReview(item);
    } else {
      try {
        const res = await api.get(`/literature-review/${item.id}`);
        setReview(res.data);
      } catch {/* ignore */}
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <ResearchLayout
      navItems={AI_NAV_ITEMS}
      title="Literature Review"
      subtitle="AI-powered literature intelligence — synthesise research, map themes, and identify key findings."
    >
      <div className="space-y-10">
        {review ? (
          <ResultView review={review} onNew={() => setReview(null)} />
        ) : (
          <InputView
            gated={gated}
            onResult={(r) => {
              setReview(r);
              loadHistory();
            }}
          />
        )}

        {history.length > 0 && !gated && (
          <section>
            <div className="overline mb-3">Review History</div>
            <Card padding="none" className="divide-y divide-slate-100">
              {history.map((h) => (
                <HistoryItem
                  key={h.id}
                  review={h}
                  active={review?.id === h.id}
                  onSelect={openHistoryItem}
                />
              ))}
            </Card>
          </section>
        )}
      </div>
    </ResearchLayout>
  );
}

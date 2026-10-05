import React, { createContext, useContext, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import api from "../lib/api";
import { setPageSeo } from "../lib/seo";
import { trackMarketingEvent as track } from "../lib/marketingAnalytics";
import { loadCreditCatalogue } from "../components/billing/creditCatalogue";
import "../components/landing/landing.css";
import "../components/ai-workspace/ai-workspace.css";

/**
 * /ai-workspace — AI that starts from the research, not an empty chat.
 *
 * Every statement maps to shipped behaviour:
 * - Context: routers/assistant.py::_build_context (manuscript / project /
 *   workspace fields) + services/ai/manuscript_context.py (named sections,
 *   ~24k chars). Research Assistant: agents/memory.py (profile interests).
 * - Full manuscript review areas: routers/manuscript_review.py prompt schema.
 * - Literature review / gap finder are generated from model knowledge, not a
 *   database search (routers/literature_review.py).
 * - Costs and monthly allowances are read from the server catalogue
 *   (/billing/credit-usage-catalogue, /billing/plans); never hardcoded. A
 *   number that hasn't loaded is simply not shown.
 * - Plan depth: FEATURE_MIN_PLAN + services/ai/pricing.py guard limits
 *   (60k vs 150k input tokens ≈ 45,000 vs 112,000 words).
 * Outputs shown are illustrative and contain no citations, studies or results.
 */

const FONT_HREF = "https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=swap";

function useDisplayFont() {
  useEffect(() => {
    if (document.querySelector(`link[href="${FONT_HREF}"]`)) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = FONT_HREF;
    document.head.appendChild(link);
  }, []);
}

/* Server price list: { actions, operations } plus monthly allowances by plan. */
const Costs = createContext(null);
const useCost = (key) => {
  const c = useContext(Costs);
  return c ? (c.actions?.[key] ?? c.operations?.[key] ?? null) : null;
};
/** "<n> <unit>" once the catalogue has loaded; nothing (not a placeholder) before. */
function Cost({ k, unit = "AI Credits", before = "", after = "" }) {
  const n = useCost(k);
  if (n == null) return null;
  return <>{before}{n} {n === 1 ? unit.replace(/s$/, "") : unit}{after}</>;
}

function scrollTo(id, e) {
  e?.preventDefault?.();
  const el = document.getElementById(id);
  if (!el) return;
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
}

/* ── 01 Contexts: what the AI is given, and what you can ask ─────────── */
const CONTEXTS = [
  {
    k: "manuscript", name: "A manuscript",
    sees: ["Title, abstract and keywords", "Status, and which sections are written", "The current text of any section you name"],
    ask: ["Review a section", "Tighten the wording", "Draft a response to reviewers", "Format the references you supply"],
    cost: { k: "ai_chat_message", after: " a message" },
  },
  {
    k: "project", name: "A project",
    sees: ["Title and description", "Objectives and methodology", "Skills the project needs"],
    ask: ["Sharpen the research questions", "Think through the method", "Explain whether a journal, conference or grant fits"],
    cost: { k: "ai_chat_message", after: " a message" },
  },
  {
    k: "workspace", name: "A workspace",
    sees: ["Name and description", "Its projects and manuscripts, by title and status", "Its milestones"],
    ask: ["Summarise where things stand", "Plan the next steps"],
    cost: { k: "ai_chat_message", after: " a message" },
  },
  {
    k: "need", name: "A research question",
    sees: ["The question as you wrote it"],
    ask: ["Turn it into a Research Need you can edit before anyone is searched"],
    cost: { k: "research_need_interpret", after: " with AI, or none with the fixed vocabulary" },
    link: ["/research", "See the research workflow"],
  },
];

function ContextExplorer() {
  const [sel, setSel] = useState("manuscript");
  const c = CONTEXTS.find((x) => x.k === sel);
  const choose = (k) => { setSel(k); track("ai_context_explored", { context: k }); };
  const onKey = (e) => {
    const i = CONTEXTS.findIndex((x) => x.k === sel);
    const next = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : null;
    if (next === null) return;
    e.preventDefault();
    const k = CONTEXTS[(next + CONTEXTS.length) % CONTEXTS.length].k;
    choose(k);
    document.getElementById(`aw-tab-${k}`)?.focus();
  };
  return (
    <div className="aw-ctx">
      <div className="aw-ctx-tabs" role="tablist" aria-label="Research contexts" onKeyDown={onKey}>
        {CONTEXTS.map((x) => (
          <button key={x.k} type="button" role="tab" id={`aw-tab-${x.k}`} aria-selected={sel === x.k}
            aria-controls="aw-ctx-panel" tabIndex={sel === x.k ? 0 : -1} className={sel === x.k ? "is-sel" : ""}
            onClick={() => choose(x.k)}>
            {x.name}
          </button>
        ))}
      </div>
      <div id="aw-ctx-panel" role="tabpanel" aria-labelledby={`aw-tab-${sel}`} className="aw-ctx-panel">
        <div>
          <div className="lp-mono aw-label">What the AI is given</div>
          <ul>{c.sees.map((s) => <li key={s}>{s}</li>)}</ul>
        </div>
        <div>
          <div className="lp-mono aw-label">What you can ask</div>
          <ul>{c.ask.map((s) => <li key={s}>{s}</li>)}</ul>
        </div>
        <div className="aw-ctx-foot">
          <span className="lp-mono"><Cost {...c.cost} /></span>
          {c.link && <Link to={c.link[0]} className="lp-link">{c.link[1]} →</Link>}
        </div>
      </div>
    </div>
  );
}

/* ── 03 Tasks grouped by research intent ─────────────────────────────── */
const INTENTS = [
  { intent: "Understand", tools: [
    ["Literature review", "A structured overview of a topic from the model's general knowledge. It doesn't search databases, so check every name and source.", "Pro Advanced", "ai_literature_review"],
    ["Research gap finder", "Potential gaps and underexplored questions, also from model knowledge, for you to test against the literature.", "Pro Advanced", "ai_research_gap_finder"],
  ] },
  { intent: "Design", tools: [
    ["Study design advisor", "Design options, trade-offs and questions to settle before you collect data.", "Pro Advanced", "ai_research_design_advisor"],
  ] },
  { intent: "Check", tools: [
    ["Statistical review", "Paste the results you report. It flags reporting gaps and assumptions to check. It doesn't rerun your analysis.", "Pro Advanced", "ai_statistical_review"],
  ] },
  { intent: "Place", tools: [
    ["Journal, conference and grant fit", "Where the work might fit, and the criteria worth checking before you decide.", "Pro", "ai_journal_matching"],
  ] },
];

/* ── 05 Credit strip: real, fixed costs ─────────────────────────────── */
const COSTS = [
  ["Rewrite a passage", "ai_rewriting"], ["Copilot message", "ai_chat_message"], ["Journal fit", "ai_journal_matching"],
  ["Statistical review", "ai_statistical_review"], ["Literature review", "ai_literature_review"],
  ["Full manuscript review", "ai_manuscript_review"], ["Research Assistant run", "DEEP_RESEARCH"],
];

function CostStrip() {
  const c = useContext(Costs);
  if (!c) return null;
  return (
    <ul className="aw-costs" aria-label="AI Credit cost per action">
      {COSTS.map(([label, key]) => <li key={key}><span>{label}</span><span className="lp-mono"><Cost k={key} unit="" /></span></li>)}
    </ul>
  );
}

function Allowance({ code }) {
  const c = useContext(Costs);
  const n = c?.plans?.[code];
  if (n == null) return null;
  return <div><dt className="lp-mono">Each month</dt><dd>{n} AI Credits</dd></div>;
}

export default function AIWorkspaceLanding() {
  useDisplayFont();
  const [registrationOpen, setRegistrationOpen] = useState(null);
  const [costs, setCosts] = useState(null);
  useEffect(() => {
    let alive = true;
    Promise.all([
      loadCreditCatalogue(),
      api.get("/billing/plans").then((r) => r.data).catch(() => []),
    ]).then(([cat, plans]) => {
      if (!alive) return;
      const allowance = {};
      (Array.isArray(plans) ? plans : []).forEach((p) => { allowance[p.code] = p.credits_per_month; });
      if (cat?.actions || cat?.operations) setCosts({ ...cat, plans: allowance });
    });
    return () => { alive = false; };
  }, []);

  useEffect(() => setPageSeo({
    title: "AI Workspace — AI that starts from your research",
    description: "Synaptiq's AI works on the manuscript, project or research question you choose: section reviews, manuscript feedback, literature and study-design support. Fixed AI Credit costs shown before each action. Pro and Pro Advanced.",
    path: "/ai-workspace",
  }), []);
  useEffect(() => { track("ai_workspace_viewed"); }, []);
  useEffect(() => {
    api.get("/auth/registration-status")
      .then((r) => setRegistrationOpen(r.data?.open !== false))
      .catch(() => setRegistrationOpen(null));
  }, []);

  const comparePlans = (location) => () => track("ai_compare_plans_clicked", { location });

  return (
    <MarketingLayout>
      <Costs.Provider value={costs}>
      <div className="lp aw">
        {/* ── Hero + Context Window ──────────────────────────────────── */}
        <section className="lp-hero aw-hero" aria-labelledby="aw-hero-title">
          <div className="lp-wrap lp-hero-grid">
            <div>
              <div className="lp-index"><b>—</b> AI Workspace</div>
              <h1 id="aw-hero-title" className="lp-h1">Your research already has context. The AI starts from it.</h1>
              <p className="lp-hero-copy">
                Open the AI on a manuscript, a project or a question. It works with that material
                in view, suggests, and leaves the decisions to you.
              </p>
              <div className="lp-hero-actions">
                <a href="#aw-context" className="lp-btn lp-btn--primary"
                  onClick={(e) => { scrollTo("aw-context", e); track("ai_start_clicked", { location: "hero" }); }}>
                  See how it works
                </a>
                <Link to="/pricing" className="lp-btn lp-btn--ghost" onClick={comparePlans("hero")}>Compare plans</Link>
              </div>
              <p className="lp-hero-note lp-small">AI is part of Pro and Pro Advanced. The Free plan has no AI Credits.</p>
            </div>

            <figure className="aw-window" aria-labelledby="aw-fig1">
              <figcaption id="aw-fig1" className="lp-figcaption lp-mono">
                <span>Fig. 1 — The context window</span><span aria-hidden="true">illustrative</span>
              </figcaption>
              <div className="aw-window-grid">
                <div className="aw-pane aw-pane--ctx">
                  <div className="lp-mono aw-label">Context</div>
                  <ul>
                    <li>Manuscript · title, abstract, keywords</li>
                    <li>Status · internal review</li>
                    <li className="is-on">Discussion · current text</li>
                  </ul>
                </div>
                <div className="aw-pane aw-pane--task">
                  <div className="lp-mono aw-label">Your request</div>
                  <p className="aw-request">“Review the Discussion for claims that need stronger support.”</p>
                  <div className="lp-mono aw-label aw-label--gap">Suggestions</div>
                  <ol className="aw-obs">
                    <li><span className="lp-mono">01 Evidence</span>A claim about all wards has no table or figure behind it.</li>
                    <li><span className="lp-mono">02 Scope</span>The conclusion reaches beyond the hospitals studied.</li>
                    <li><span className="lp-mono">03 Question</span>Was staff workload measured, or assumed?</li>
                  </ol>
                </div>
              </div>
              <div className="aw-decide" aria-label="Who does what">
                <span>AI suggests</span><span>You review</span><span>You decide</span>
                <span className="lp-mono aw-cost"><Cost k="ai_chat_message" after=" · " />cost shown before it runs</span>
              </div>
            </figure>
          </div>
        </section>

        {/* ── 01 The work, not the chat ──────────────────────────────── */}
        <section id="aw-context" className="lp-section lp-section--quiet" aria-labelledby="aw-ctx-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>01</b> The work, not the chat</div>
            <h2 id="aw-ctx-title" className="lp-h2">You choose what it works on. That is what it's given.</h2>
            <p className="lp-lede">No blank box and no re-explaining. The assistant opens on something you already have.</p>
            <ContextExplorer />
          </div>
        </section>

        {/* ── 02 Manuscript ──────────────────────────────────────────── */}
        <section className="lp-section" aria-labelledby="aw-ms-title">
          <div className="lp-wrap aw-ms-grid">
            <div>
              <div className="lp-index"><b>02</b> The manuscript stays the object</div>
              <h2 id="aw-ms-title" className="lp-h2">Feedback in the margin, not a new document.</h2>
              <p className="lp-lede">
                Manuscript Copilot works section by section inside your manuscript. For a whole draft, a full
                review reads the file you upload and returns a revision checklist, ordered by priority.
              </p>
              <ul className="aw-areas" aria-label="Full review areas">
                {["Research problem", "Literature foundation", "Methodology", "Statistical validity", "Writing quality"].map((a) => <li key={a}>{a}</li>)}
              </ul>
              <p className="lp-small">Pro<Cost k="ai_chat_message" before=" · Copilot: " after=" a message" /><Cost k="ai_manuscript_review" before=" · Full review: " /></p>
            </div>
            <figure className="aw-page" aria-labelledby="aw-fig2"
              onMouseEnter={() => track("ai_manuscript_copilot_explored")} onFocus={() => track("ai_manuscript_copilot_explored")}>
              <figcaption id="aw-fig2" className="lp-figcaption lp-mono">
                <span>Fig. 2 — Section 4, Discussion</span><span aria-hidden="true">illustrative</span>
              </figcaption>
              <div className="aw-page-body">
                <p>
                  Waiting times fell after the triage change. <mark>The effect held across all wards</mark>,
                  which suggests the approach can be adopted widely. <mark>Staff reported no additional burden</mark>,
                  and the change required no new hires.
                </p>
                <aside className="aw-margin" aria-label="Review notes">
                  <div><span className="lp-mono">Evidence</span>Point to the ward-level table, or narrow the claim.</div>
                  <div><span className="lp-mono">Method</span>Say how burden was measured.</div>
                </aside>
              </div>
              <div className="aw-check">
                <div className="lp-mono aw-label">Revision checklist</div>
                <div className="aw-check-row"><span className="lp-mono">High</span>Support the all-wards claim</div>
                <div className="aw-check-row"><span className="lp-mono">Medium</span>Define workload before reporting it</div>
              </div>
            </figure>
          </div>
        </section>

        {/* ── 03 Research tasks ──────────────────────────────────────── */}
        <section className="lp-section lp-section--quiet" aria-labelledby="aw-tasks-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>03</b> Research tasks</div>
            <h2 id="aw-tasks-title" className="lp-h2">Grouped by what you're trying to do.</h2>
            <div className="aw-intents">
              {INTENTS.map((g) => (
                <div key={g.intent} className="aw-intent">
                  <div className="aw-intent-name">{g.intent}</div>
                  {g.tools.map(([name, line, plan, cost]) => (
                    <div key={name} className="aw-tool">
                      <div className="aw-tool-head"><span>{name}</span><span className="lp-mono">{plan}<Cost k={cost} unit="credits" before=" · " /></span></div>
                      <p>{line}</p>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            <p className="lp-small aw-also">
              Also on Pro: the Research Assistant for open questions about your work<Cost k="DEEP_RESEARCH" unit="credits a run" before=" (" after=")" />, rewriting
              for clarity and tone, abstract drafts, and lesson plans and assessments in the Teaching Hub.
            </p>
          </div>
        </section>

        {/* ── 04 Depth ───────────────────────────────────────────────── */}
        <section className="lp-section" aria-labelledby="aw-depth-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>04</b> Pro and Pro Advanced</div>
            <h2 id="aw-depth-title" className="lp-h2">Same approach. More room and more kinds of analysis.</h2>
            <div className="aw-depth" onMouseEnter={() => track("ai_advanced_features_explored")}>
              <div>
                <div className="aw-depth-name">Pro</div>
                <p>Manuscript Copilot, full manuscript review, the Research Assistant, journal, conference and grant fit, writing and teaching help.</p>
                <dl>
                  <div><dt className="lp-mono">Per request</dt><dd>up to about 45,000 words</dd></div>
                  <Allowance code="researcher" />
                </dl>
              </div>
              <div>
                <div className="aw-depth-name">Pro Advanced</div>
                <p>Everything in Pro, plus literature review, the research gap finder, the study design advisor and statistical review.</p>
                <dl>
                  <div><dt className="lp-mono">Per request</dt><dd>up to about 112,000 words, with longer responses</dd></div>
                  <Allowance code="pro_researcher" />
                </dl>
              </div>
            </div>
            <p style={{ marginTop: 22 }}>
              <Link to="/pricing" className="lp-link" onClick={comparePlans("depth")}>Compare plans →</Link>
            </p>
          </div>
        </section>

        {/* ── 05 Control and credits ─────────────────────────────────── */}
        <section className="lp-section lp-section--quiet" aria-labelledby="aw-credits-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>05</b> Control and credits</div>
            <h2 id="aw-credits-title" className="lp-h2">You see the cost before anything runs.</h2>
            <ol className="aw-control">
              {["You choose the material", "You choose the task", "You see the cost", "AI suggests", "You decide"].map((s, i) => (
                <li key={s} className={i === 3 ? "is-ai" : ""}><span className="lp-mono">{String(i + 1).padStart(2, "0")}</span>{s}</li>
              ))}
            </ol>
            <div className="aw-credits" onMouseEnter={() => track("ai_credits_explored")}>
              <CostStrip />
              <div className="aw-rules">
                <p>Each action has a fixed cost, shown before it runs. If a request fails, the credits go back.</p>
                <p>Monthly credits renew with your plan and don't roll over. Credit packs, on paid plans, don't expire and are used after the monthly credits.</p>
                <p>Your AI usage page lists what you've used and when.</p>
              </div>
            </div>
            <p className="aw-integrity">
              AI can be wrong. Check sources, especially names and references. Methods and conclusions stay
              your judgment, and nothing here can secure a publication, a grant or a review outcome. The AI
              never contacts anyone for you.
            </p>
          </div>
        </section>

        {/* ── Final call to action ───────────────────────────────────── */}
        <section className="lp-final" aria-labelledby="aw-final-title">
          <div className="lp-wrap">
            <div className="lp-final-inner">
              <h2 id="aw-final-title" className="lp-h2">The research stays yours. The AI works on it when you ask.</h2>
              <div className="lp-hero-actions">
                <Link to="/pricing" className="lp-btn lp-btn--primary" onClick={comparePlans("final")}>Compare plans</Link>
                <Link to="/register" className="lp-btn lp-btn--ghost"
                  onClick={() => { track("ai_start_clicked", { location: "final" }); track("signup_started", { location: "ai_workspace_final" }); }}>
                  Start Free
                </Link>
              </div>
              <p className="lp-small" style={{ marginTop: 16 }}>
                {registrationOpen === false
                  ? "New sign-ups are paused while billing is set up."
                  : "Free starts your Academic Passport. AI comes with Pro."}
              </p>
            </div>
          </div>
        </section>
      </div>
      </Costs.Provider>
    </MarketingLayout>
  );
}

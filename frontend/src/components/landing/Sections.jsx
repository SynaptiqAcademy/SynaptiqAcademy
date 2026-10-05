import React from "react";
import { Link } from "react-router-dom";
import { trackMarketingEvent as track } from "@/lib/marketingAnalytics";
import { CreditCostNumber } from "@/components/billing/CreditCost";
import { PLAN_PREVIEW, FAQ } from "./content";

/* ── 05 — the rest of a research life ─────────────────────────────────── */
const ENTRIES = [
  {
    n: "5.1", title: "Teaching",
    body: "The Teaching Hub keeps courses, lesson plans, assessments and teaching workspaces together. Generating teaching material with AI uses AI Credits.",
    plan: "Pro · advanced AI teaching tools on Pro Advanced",
  },
  {
    n: "5.2", title: "Funding",
    body: "Grant discovery for your areas, and grant applications that hold the team, the budget, the deliverables and earlier versions in one place.",
    plan: "Pro",
  },
  {
    n: "5.3", title: "Publishing",
    body: "Journal and conference discovery, manuscripts with versions and co-authors, review requests, and a record of where each submission stands.",
    plan: "Pro",
  },
  {
    n: "5.4", title: "Impact",
    body: "Publication tracking on Pro. Citation Monitoring and the Research Impact Dashboard follow how your work is picked up over time.",
    plan: "Pro · Pro Advanced",
  },
];

export function Workflows() {
  return (
    <section className="lp-section lp-section--quiet" aria-labelledby="lp-wf-title">
      <div className="lp-wrap">
        <div className="lp-index"><b>05</b> Beyond the first project</div>
        <h2 id="lp-wf-title" className="lp-h2">Teaching, funding, publishing, impact.</h2>
        <p className="lp-lede">
          Research doesn't happen one project at a time, and the rest of the work
          shouldn't live somewhere else.
        </p>
        <div className="lp-entries">
          {ENTRIES.map((e) => (
            <article key={e.title} className="lp-entry">
              <div className="lp-mono" style={{ color: "var(--muted)" }}>{e.n}</div>
              <h3>{e.title}</h3>
              <p>{e.body}</p>
              <div className="lp-plan lp-mono">{e.plan}</div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── 06 — AI ──────────────────────────────────────────────────────────── */
const PRO_AI = [
  ["AI Research Assistant or Manuscript Copilot message", "AI_ASSISTANT_SIMPLE"],
  ["Review of one manuscript section", "MANUSCRIPT_SECTION_REVIEW"],
  ["Full manuscript review", "FULL_MANUSCRIPT_REVIEW"],
  ["Journal, conference or grant fit", "JOURNAL_FIT"],
  ["Teaching content generation", "TEACHING_CONTENT_GENERATION"],
];
const ADV_AI = [
  ["Advanced AI Research Assistant, extended research context", null],
  ["Advanced Manuscript Intelligence", "ADVANCED_MANUSCRIPT_INTELLIGENCE"],
  ["Collaboration Intelligence", null],
  ["Advanced AI Teaching Tools", null],
  ["Priority AI processing", null],
];

export function AIAssistance() {
  return (
    <section className="lp-section" aria-labelledby="lp-ai-title">
      <div className="lp-wrap">
        <div className="lp-index"><b>06</b> Where AI helps</div>
        <h2 id="lp-ai-title" className="lp-h2">AI for the parts that are slow. Your judgment for the rest.</h2>
        <p className="lp-lede">
          The AI tools sit inside the work described above: reviewing a manuscript
          section, checking whether a journal fits, drafting a lesson. Each action
          shows its cost in AI Credits before it runs, and if a request fails the
          credits go back.
        </p>
        <div className="lp-ai">
          <div>
            <h3>On Pro</h3>
            <ul>
              {PRO_AI.map(([label, op]) => (
                <li key={label}>
                  <span>{label}</span>
                  {op && <span className="lp-cost"><CreditCostNumber operation={op} /> AI Credits</span>}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3>Pro Advanced adds</h3>
            <ul>
              {ADV_AI.map(([label, op]) => (
                <li key={label}>
                  <span>{label}</span>
                  {op && <span className="lp-cost"><CreditCostNumber operation={op} /> AI Credits</span>}
                </li>
              ))}
            </ul>
          </div>
        </div>
        <p className="lp-caveat lp-small">
          AI output can be wrong. It doesn't replace your own reading, a statistician,
          or peer review, and it can't make a journal accept a paper or a funder award a
          grant. Who to contact, what to collaborate on and what to publish stay your
          decisions.
        </p>
      </div>
    </section>
  );
}

/* ── 07 — audience ────────────────────────────────────────────────────── */
export function Audience() {
  return (
    <section className="lp-section lp-section--quiet" aria-labelledby="lp-aud-title">
      <div className="lp-wrap">
        <div className="lp-index" aria-hidden="true"><b>07</b> Who it's for</div>
        <h2 id="lp-aud-title" className="sr-only">Who Synaptiq is for</h2>
        <p className="lp-audience">
          People who do research, whatever their title says: academic and doctoral
          researchers, educators, clinicians and scientists, people working in policy
          and the public sector, and anyone whose questions <em>sit between disciplines</em>.
        </p>
        <p className="lp-small" style={{ marginTop: 18, maxWidth: "46rem" }}>
          Your plan reflects what you use, not who you are. A doctoral researcher and a
          department head choose the same way.
        </p>
      </div>
    </section>
  );
}

/* ── 08 — plans ───────────────────────────────────────────────────────── */
export function Plans() {
  return (
    <section className="lp-section" aria-labelledby="lp-plans-title" id="plans">
      <div className="lp-wrap">
        <div className="lp-index"><b>08</b> Plans</div>
        <h2 id="lp-plans-title" className="lp-h2">Be found for free. Pay when you want to do the work here.</h2>
        <div className="lp-plans">
          {PLAN_PREVIEW.map((p) => (
            <div key={p.key} className={`lp-plan-col ${p.key === "pro" ? "lp-plan-col--lead" : ""}`} data-testid={`landing-plan-${p.key}`}>
              <div className="lp-plan-name">
                <h3 style={{ fontSize: "inherit", fontWeight: "inherit" }}>{p.name}</h3>
                {p.status && <span className="lp-plan-status">{p.status}</span>}
              </div>
              <div className="lp-price">{p.price}{p.period && <small>{p.period}</small>}</div>
              {p.futurePrice && <div className="lp-future lp-small">{p.futurePrice}</div>}
              <div className="lp-credits">{p.credits}</div>
              <div className="lp-role">{p.role}</div>
              <ul>{p.includes.map((x) => <li key={x}>{x}</li>)}</ul>
              <Link
                to={p.href}
                className={`lp-btn ${p.key === "pro" ? "lp-btn--primary" : "lp-btn--ghost"}`}
                style={{ alignSelf: "flex-start" }}
                onClick={() => {
                  track("plan_selected", { plan: p.key, location: "landing" });
                  if (p.key === "free") track("signup_started", { location: "plans" });
                }}
              >
                {p.cta}
              </Link>
            </div>
          ))}
        </div>
        <div className="lp-plans-foot lp-small">
          <p>
            AI Credits pay for AI-assisted actions only. Actions cost different amounts and
            each one shows its cost before you run it, so 200 credits isn't 200 requests.
            Profiles, networking, messaging and collaboration don't use them.
          </p>
          <p>
            Pro is €9.99/month during Early Access. The intended future price is
            €14.99/month. Prices in EUR.
          </p>
          <p>
            <Link to="/pricing" className="lp-link" onClick={() => track("pricing_viewed", { from: "landing_plans" })}>
              Compare plans in full
            </Link>
          </p>
        </div>
      </div>
    </section>
  );
}

/* ── 09 — FAQ ─────────────────────────────────────────────────────────── */
export function LandingFAQ() {
  return (
    <section className="lp-section lp-section--quiet" aria-labelledby="lp-faq-title" id="faq" data-testid="landing-faq">
      <div className="lp-wrap lp-faq-grid">
        <div>
          <div className="lp-index"><b>09</b> Questions</div>
          <h2 id="lp-faq-title" className="lp-h2">Before you sign up.</h2>
          <p className="lp-small" style={{ marginTop: 16 }}>
            Something else? <Link to="/contact" className="lp-link">Write to us</Link>.
          </p>
        </div>
        <div className="lp-faq">
          {FAQ.map((f, i) => (
            <details key={f.q} data-testid={`faq-item-${i}`}>
              <summary>{f.q}</summary>
              <p>{f.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── closing ──────────────────────────────────────────────────────────── */
export function Closing({ registrationOpen, onAsk }) {
  return (
    <section className="lp-section lp-close" aria-labelledby="lp-close-title">
      <div className="lp-wrap">
        <div className="lp-index"><b>—</b> Back to the beginning</div>
        <h2 id="lp-close-title">Every project starts as a question.</h2>
        <p>
          You probably have one you haven't written down yet. Put it in, see what it
          needs, and decide from there.
        </p>
        <div className="lp-hero-actions">
          <a href="#research-question" className="lp-btn lp-btn--primary" onClick={onAsk}>
            Try it with your question
          </a>
          <Link to="/register" className="lp-btn lp-btn--ghost"
            onClick={() => { track("landing_primary_cta", { location: "closing" }); track("signup_started", { location: "closing" }); }}>
            Start Free
          </Link>
        </div>
        {registrationOpen === false && (
          <p style={{ fontSize: "0.88rem", marginTop: 18 }}>
            New sign-ups are paused while we finish setting up billing.
          </p>
        )}
      </div>
    </section>
  );
}

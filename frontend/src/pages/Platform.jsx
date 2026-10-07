import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import { setPageSeo } from "../lib/seo";
import { trackMarketingEvent as track } from "../lib/marketingAnalytics";
import SystemMap from "../components/platform/SystemMap";
import "../components/landing/landing.css";
import "../components/platform/platform.css";


function scrollToSystem(e) {
  e.preventDefault();
  const el = document.getElementById("system");
  if (!el) return;
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
}

const startFree = (location) => () => {
  track("platform_start_free_clicked", { location });
  track("signup_started", { location: `platform_${location}` });
};

/* Where a project's context usually ends up. */
const SCATTER = ["Profile page", "Directory search", "Email thread", "Shared drive", "Task board", "Journal search", "Grant portal", "AI chat"];

/* 02 — one project followed through. Statuses are the manuscript model's own. */
const TRACE = [
  ["Team", "Roles from Team Builder, filled by accepted requests"],
  ["Project", "Tasks and milestones"],
  ["Workspace", "Documents, notes, files, comments"],
  ["Manuscript", "Linked to this project · internal review"],
  ["Grant application", "Same workspace · budget, deliverables, versions"],
  ["Research record", "Publications, then tracking and citations"],
];
const STATUSES = ["draft", "internal review", "ready for submission", "submitted", "under review", "revision", "accepted"];

/* 03 — the wider index. Links only where a public page exists. */
const TOOLS = [
  ["Research", "Develop the work inside the project, with the AI Research Assistant.", "Pro", "/research", "Explore Research", "platform_research_clicked"],
  ["Funding", "Find calls in your areas and build the application with the team.", "Pro"],
  ["Publishing", "Choose where to submit, write with co-authors and follow each submission.", "Pro"],
  ["Teaching", "Plan lessons, build assessments, keep teaching workspaces.", "Pro"],
  ["Impact", "Follow how published work is picked up over time.", "Pro Advanced"],
  ["AI assistance", "Help with specific tasks, priced in AI Credits before it runs.", "Pro", "/ai-workspace", "Explore AI Workspace", "platform_ai_workspace_clicked"],
];

export default function Platform() {

  useEffect(() => setPageSeo({
    title: "Platform — How Synaptiq fits together",
    description: "Synaptiq connects a researcher's Academic Passport, expertise discovery, collaboration requests and the projects, manuscripts and grant applications that follow, so the context of the work stays with it.",
    path: "/platform",
  }), []);

  useEffect(() => { track("platform_viewed"); }, []);

  return (
    <MarketingLayout>
      <div className="lp pf">
        {/* ── Hero ─────────────────────────────────────────────────────── */}
        <section className="lp-hero pf-hero" aria-labelledby="pf-hero-title">
          <div className="lp-wrap lp-hero-grid">
            <div>
              <div className="lp-index lp-eyebrow">The platform</div>
              <h1 id="pf-hero-title" className="lp-h1">The work moves on. The context comes with it.</h1>
              <p className="lp-hero-copy">
                Synaptiq links your research identity, the expertise a problem needs,
                the people who have it, and the projects, manuscripts and grant work that follow.
              </p>
              <div className="lp-hero-actions">
                <Link to="/register" className="lp-btn lp-btn--primary" onClick={startFree("hero")}>Start Free</Link>
                <a href="#system" className="lp-btn lp-btn--ghost" onClick={scrollToSystem}>Explore the system</a>
              </div>
              <p className="lp-hero-note lp-small">
                Free: Academic Passport and ORCID. Collaboration and projects are on Pro.
              </p>
            </div>

            <figure className="lp-figure pf-scatter" aria-labelledby="pf-fig1-caption">
              <figcaption id="pf-fig1-caption" className="lp-figcaption lp-mono">
                <span>Fig. 1 — Where a project's context usually lives</span>
              </figcaption>
              <ul>
                {SCATTER.map((s) => <li key={s}>{s}</li>)}
              </ul>
              <p className="lp-small pf-scatter-note">Each one starts from zero.</p>
            </figure>
          </div>
        </section>

        {/* ── 01 The system ────────────────────────────────────────────── */}
        <section id="system" className="lp-section lp-section--quiet" aria-labelledby="pf-system-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>01</b> The system</div>
            <h2 id="pf-system-title" className="lp-h2">From the person, to the people, to the work, and back to the record.</h2>
            <p className="lp-lede">Select any part to see what it does and what it connects to.</p>
            <SystemMap />
          </div>
        </section>

        {/* ── 02 Collaboration to output ───────────────────────────────── */}
        <section className="lp-section" aria-labelledby="pf-output-title">
          <div className="lp-wrap pf-output-grid">
            <div>
              <div className="lp-index"><b>02</b> After the team says yes</div>
              <h2 id="pf-output-title" className="lp-h2">The project carries the work forward.</h2>
              <p className="lp-lede">
                Manuscripts and grant applications stay linked to the project they came from,
                with the team, the files and the history.
              </p>
            </div>
            <figure className="pf-trace" aria-labelledby="pf-fig3-caption">
              <figcaption id="pf-fig3-caption" className="lp-figcaption lp-mono">
                <span>Fig. 3 — One project, followed through</span><span aria-hidden="true">illustrative</span>
              </figcaption>
              <ol>
                {TRACE.map(([k, v]) => (
                  <li key={k}><span className="pf-trace-k">{k}</span><span className="pf-trace-v">{v}</span></li>
                ))}
              </ol>
              <div className="pf-statuses lp-mono" aria-label="Manuscript statuses">
                {STATUSES.map((s, i) => <span key={s} className={i === 1 ? "is-at" : ""}>{s}</span>)}
              </div>
            </figure>
          </div>
        </section>

        {/* ── 03 One context, different tools ──────────────────────────── */}
        <section className="lp-section lp-section--quiet" aria-labelledby="pf-tools-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>03</b> One context, different tools</div>
            <h2 id="pf-tools-title" className="lp-h2">Each part of the work, starting from what you already have.</h2>
            <dl className="pf-tools">
              {TOOLS.map(([name, line, plan, href, cta, ev]) => (
                <div key={name} className="pf-tool">
                  <dt>{name}</dt>
                  <dd>
                    <span>{line}</span>
                    <span className="lp-mono pf-tool-plan">{plan}</span>
                    {href && <Link to={href} className="lp-link pf-tool-link" onClick={() => track(ev, { location: "tools_index" })}>{cta} →</Link>}
                  </dd>
                </div>
              ))}
            </dl>
            <dl className="pf-id" aria-label="What everything starts from">
              <div>
                <dt className="lp-state lp-state--self">Academic Passport</dt>
                <dd>Your research identity. Free on every plan.</dd>
              </div>
              <div>
                <dt className="lp-state lp-state--connected">Suggestions</dt>
                <dd>Each shows the evidence behind it. No match percentages.</dd>
              </div>
              <div>
                <dt className="lp-state lp-state--verified">Verified</dt>
                <dd>Institutional affiliation only. Not degrees, licences or competence.</dd>
              </div>
            </dl>
            <p className="pf-inst">
              Using Synaptiq across a department or research organisation?{" "}
              <Link to="/for-institutions" className="lp-link" onClick={() => track("platform_institutions_clicked")}>For Institutions →</Link>
            </p>
          </div>
        </section>

        {/* ── Final call to action ─────────────────────────────────────── */}
        <section className="lp-final" aria-labelledby="pf-final-title">
          <div className="lp-wrap">
            <div className="lp-final-inner">
              <h2 id="pf-final-title" className="lp-h2">Start with your Passport. Add the rest when the work needs it.</h2>
              <div className="lp-hero-actions">
                <Link to="/register" className="lp-btn lp-btn--primary" onClick={startFree("final")}>Start Free</Link>
                <Link to="/pricing" className="lp-btn lp-btn--ghost" onClick={() => track("platform_pricing_clicked", { location: "final" })}>
                  Explore Pricing
                </Link>
              </div>
            </div>
          </div>
        </section>
      </div>
    </MarketingLayout>
  );
}

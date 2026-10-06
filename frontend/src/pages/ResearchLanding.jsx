import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import { setPageSeo } from "../lib/seo";
import { trackMarketingEvent as track } from "../lib/marketingAnalytics";
import "../components/landing/landing.css";
import "../components/research/research.css";

/**
 * /research — one research problem followed through Synaptiq.
 *
 * Everything shown is a specimen of a real product shape:
 * - Research Need fields: services/research_need/models.py (user-editable;
 *   interpreted with AI on request, otherwise deterministically).
 * - Groups, evidence wording, missing expertise: services/research_need/
 *   relevance.py + evidence.py (deterministic, zero-credit, eligibility and
 *   privacy rules of discovery apply).
 * - Roles, priorities, "you cover this", cross-role hints, blueprint
 *   lifecycle, project handoff: routers/team_builder.py, team_builder/models.py.
 * No real or invented people: candidates are "Researcher A/B/C".
 */


const STATES = [
  ["rs-question", "Question"],
  ["rs-need", "Structured"],
  ["rs-expertise", "Expertise"],
  ["rs-people", "People"],
  ["rs-team", "Team"],
  ["rs-work", "Work"],
];

function scrollTo(id, e) {
  e?.preventDefault?.();
  const el = document.getElementById(id);
  if (!el) return;
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
}

/* ── The Research Margin: annotation column that follows the problem ── */
function ResearchMargin() {
  const [active, setActive] = useState(STATES[0][0]);
  useEffect(() => {
    if (!("IntersectionObserver" in window)) return undefined;
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) setActive(en.target.id); });
    }, { rootMargin: "-35% 0px -60% 0px" });
    STATES.forEach(([id]) => { const el = document.getElementById(id); if (el) io.observe(el); });
    return () => io.disconnect();
  }, []);
  return (
    <nav className="rs-margin" aria-label="The research need, step by step">
      <div className="lp-mono rs-margin-head">The need, so far</div>
      <ol>
        {STATES.map(([id, label], i) => (
          <li key={id} className={active === id ? "is-on" : ""}>
            <a href={`#${id}`} aria-current={active === id ? "step" : undefined}
              onClick={(e) => { scrollTo(id, e); track("research_workflow_explored", { step: label.toLowerCase(), source: "margin" }); }}>
              <span className="lp-mono">{String(i + 1).padStart(2, "0")}</span> {label}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

function State({ n, label }) {
  return <div className="lp-index rs-state"><b>{String(n).padStart(2, "0")}</b> {label}</div>;
}

/* ── 02 Research Need specimen ────────────────────────────────────── */
const NEED = [
  ["Problem statement", "Reduce patient waiting times in public hospitals within current staffing."],
  ["Research domains", "Health services research"],
  ["Required expertise", "Patient flow · hospital operations"],
  ["Complementary expertise", "Operations research · quality management · health policy"],
  ["Useful methods", "Process mapping · discrete-event simulation"],
  ["Professional roles", "Hospital operations manager"],
];

/* ── 03 Expertise map: each entry points at the part of the question it serves ── */
const PARTS = { context: "public hospitals", problem: "reduce patient waiting times", constraint: "without increasing staff workload" };
const MAP = [
  { group: "Directly relevant", items: [
    { k: "hsr", name: "Health services research", why: "the problem itself", part: "problem" },
  ] },
  { group: "Complementary", items: [
    { k: "or", name: "Operations research", why: "patient flow under fixed capacity", part: "constraint" },
    { k: "qm", name: "Quality management", why: "improving a service process", part: "problem" },
    { k: "hp", name: "Health policy", why: "how public hospitals are organised", part: "context" },
  ] },
  { group: "Methods", items: [
    { k: "pm", name: "Process mapping", why: "seeing where the waiting happens", part: "problem" },
    { k: "des", name: "Discrete-event simulation", why: "testing changes before staff feel them", part: "constraint" },
  ] },
  { group: "Context", items: [
    { k: "ops", name: "Hospital operations", why: "practice inside the setting", part: "context" },
  ] },
];

function ExpertiseMap() {
  const [sel, setSel] = useState("or");
  const item = MAP.flatMap((g) => g.items).find((x) => x.k === sel);
  const pick = (k) => { setSel(k); track("research_expertise_map_explored", { item: k }); };
  return (
    <figure className="rs-map" aria-labelledby="rs-fig3">
      <figcaption id="rs-fig3" className="lp-figcaption lp-mono">
        <span>Fig. 3 — Where the expertise sits</span><span aria-hidden="true">select an entry</span>
      </figcaption>
      <p className="rs-map-q" aria-live="polite">
        How can{" "}
        <span className={`rs-part ${item.part === "context" ? "is-on" : ""}`}>{PARTS.context}</span>{" "}
        <span className={`rs-part ${item.part === "problem" ? "is-on" : ""}`}>{PARTS.problem}</span>{" "}
        <span className={`rs-part ${item.part === "constraint" ? "is-on" : ""}`}>{PARTS.constraint}</span>?
        <span className="sr-only"> {item.name} relates to the {item.part}: {PARTS[item.part]}.</span>
      </p>
      <div className="rs-map-cols">
        {MAP.map((g) => (
          <div key={g.group} className="rs-map-col">
            <div className="lp-mono rs-map-group">{g.group}</div>
            <ul>
              {g.items.map((x) => (
                <li key={x.k}>
                  <button type="button" className={`rs-entry ${sel === x.k ? "is-sel" : ""}`} aria-pressed={sel === x.k} onClick={() => pick(x.k)}>
                    <span className="rs-entry-name">{x.name}</span>
                    <span className="rs-entry-why">may contribute: {x.why}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </figure>
  );
}

/* ── 04 Candidates with evidence ──────────────────────────────────── */
const PEOPLE = [
  { k: "a", name: "Researcher A", group: "Directly relevant", evidence: [
    ["Research areas", "lists Health services research"], ["Methods", "uses process mapping"],
  ], contribution: "Could contribute experience with process mapping.", also: "Quality improvement" },
  { k: "b", name: "Researcher B", group: "Complementary expertise", evidence: [
    ["Professional expertise", "lists hospital operations"], ["Professional role", "operations manager"],
  ], contribution: "Could contribute a hospital operations perspective." },
  { k: "c", name: "Researcher C", group: "Methods specialist", evidence: [
    ["Methods", "uses discrete-event simulation"], ["Publication", "title mentions patient flow"],
  ], contribution: "Could contribute experience with discrete-event simulation." },
];

function Candidate({ p }) {
  const [open, setOpen] = useState(p.k === "a");
  return (
    <article className="rs-card">
      <header>
        <span className="rs-card-name">{p.name}</span>
        <span className="lp-mono rs-card-group">{p.group}</span>
      </header>
      <button type="button" className="lp-textbtn rs-why-btn" aria-expanded={open} aria-controls={`rs-why-${p.k}`}
        onClick={() => { setOpen(!open); if (!open) track("research_match_reason_opened", { card: p.k }); }}>
        Why this person?
      </button>
      <div id={`rs-why-${p.k}`} hidden={!open}>
        <dl className="rs-evidence">
          {p.evidence.map(([f, v]) => <div key={f}><dt className="lp-mono">{f}</dt><dd>{v}</dd></div>)}
        </dl>
        <p className="rs-contrib">{p.contribution}</p>
        {p.also && <p className="lp-small">Also relevant to: {p.also}</p>}
      </div>
      <footer className="lp-mono">select for team · send request</footer>
    </article>
  );
}

/* ── 05 Team blueprint ────────────────────────────────────────────── */
const ROLES = [
  { role: "Health services lead", priority: "essential", state: "You cover this", tone: "self" },
  { role: "Operations researcher", priority: "essential", state: "Researcher C · request pending", tone: "pending", why: "Models patient flow under fixed staffing." },
  { role: "Quality improvement", priority: "useful", state: "Researcher A · also fits the lead role", tone: "pending", why: "Process improvement inside a working service." },
  { role: "Health policy", priority: "optional", state: "Missing expertise · no eligible match yet", tone: "missing", why: "How decisions about hospital capacity are made." },
];

/* ── 06 Hand-off ──────────────────────────────────────────────────── */
const HANDOFF = [
  ["Blueprint", "ready when essential roles have accepted"],
  ["Project", "problem statement and keywords from the need"],
  ["Workspace", "members who accepted, with their team roles"],
  ["Manuscript", "linked to the project and its workspace"],
];

export default function ResearchLanding() {

  useEffect(() => setPageSeo({
    title: "Research — From a research problem to the people it needs",
    description: "Describe a research problem and Synaptiq structures the expertise it requires, shows which members' work fits and why, helps you plan an interdisciplinary team, and carries accepted collaborators into a project.",
    path: "/research",
  }), []);
  useEffect(() => { track("research_page_viewed"); }, []);

  const startFree = (location) => () => {
    track("research_start_free_clicked", { location });
    track("signup_started", { location: `research_${location}` });
  };

  return (
    <MarketingLayout>
      <div className="lp rs">
        {/* ── Hero ───────────────────────────────────────────────────── */}
        <section id="rs-question" className="lp-hero rs-hero" aria-labelledby="rs-hero-title">
          <div className="lp-wrap lp-hero-grid">
            <div>
              <State n={1} label="Question" />
              <h1 id="rs-hero-title" className="lp-h1">Before the answer, work out what the question needs.</h1>
              <p className="lp-hero-copy">
                Synaptiq reads a research problem for the fields, methods and expertise it calls for,
                then shows whose work fits, and why.
              </p>
              <div className="lp-hero-actions">
                <Link to="/register" className="lp-btn lp-btn--primary" onClick={startFree("hero")}>Start Free</Link>
                <a href="#rs-need" className="lp-btn lp-btn--ghost"
                  onClick={(e) => { scrollTo("rs-need", e); track("research_workflow_explored", { step: "structured", source: "hero" }); }}>
                  See the research workflow
                </a>
              </div>
              <p className="lp-hero-note lp-small">
                Free: your Academic Passport, so the right projects can find you. Searching, inviting and team building are on Pro.
              </p>
            </div>

            <figure className="rs-note" aria-labelledby="rs-fig1">
              <figcaption id="rs-fig1" className="lp-figcaption lp-mono">
                <span>Research note / 01</span><span aria-hidden="true">example</span>
              </figcaption>
              <p className="rs-note-q">
                How can <span className="rs-u" data-n="1">public hospitals</span>{" "}
                <span className="rs-u" data-n="2">reduce patient waiting times</span>{" "}
                <span className="rs-u" data-n="3">without increasing staff workload</span>?
              </p>
              <ol className="rs-note-marg">
                <li><span className="lp-mono">1 · context</span> public hospitals</li>
                <li><span className="lp-mono">2 · problem</span> patient waiting times</li>
                <li><span className="lp-mono">3 · constraint</span> no added staff workload</li>
              </ol>
              <p className="rs-note-next lp-mono">What this question may require →</p>
            </figure>
          </div>
        </section>

        <div className="lp-wrap rs-body">
          <ResearchMargin />

          <div className="rs-main">
            {/* ── 02 Research Need ───────────────────────────────────── */}
            <section id="rs-need" className="rs-sec" aria-labelledby="rs-need-title">
              <State n={2} label="Structured" />
              <h2 id="rs-need-title" className="lp-h2">What does this question require?</h2>
              <p className="lp-lede">
                The question becomes a Research Need: a short record of what the problem calls for.
                It describes the need. It doesn't answer the question.
              </p>
              <figure className="rs-record" aria-labelledby="rs-fig2">
                <figcaption id="rs-fig2" className="lp-figcaption lp-mono">
                  <span>Fig. 2 — Research Need · draft</span><span aria-hidden="true">illustrative</span>
                </figcaption>
                <dl>
                  {NEED.map(([k, v]) => (
                    <div key={k} className="rs-record-row">
                      <dt className="lp-mono">{k}</dt><dd>{v}</dd><span className="lp-mono rs-edit" aria-hidden="true">edit</span>
                    </div>
                  ))}
                </dl>
                <p className="lp-small rs-record-foot">
                  Read with AI when you ask for it (it uses AI Credits), otherwise with a fixed research
                  vocabulary. Either way, you review and edit it before anyone is searched.
                </p>
              </figure>
            </section>

            {/* ── 03 Expertise ───────────────────────────────────────── */}
            <section id="rs-expertise" className="rs-sec" aria-labelledby="rs-exp-title">
              <State n={3} label="Expertise" />
              <h2 id="rs-exp-title" className="lp-h2">Where is the expertise you don't have?</h2>
              <p className="lp-lede">
                Part of it sits in your own field. Part sits next door, in fields that see a different side of the same problem.
              </p>
              <ExpertiseMap />
            </section>

            {/* ── 04 People ──────────────────────────────────────────── */}
            <section id="rs-people" className="rs-sec" aria-labelledby="rs-people-title">
              <State n={4} label="People" />
              <h2 id="rs-people-title" className="lp-h2">Why does this person appear?</h2>
              <p className="lp-lede">
                A directory starts from a name. This starts from the need, and searches eligible members'
                Academic Passports against it. Every suggestion shows its evidence. There are no scores.
              </p>
              <div className="rs-cards">
                {PEOPLE.map((p) => <Candidate key={p.k} p={p} />)}
              </div>
              <p className="lp-small rs-fields">
                Matched against research areas, interests and keywords, methods and software, professional
                expertise and role, and publication titles. Specimens, not real members.{" "}
                <Link to="/platform" className="lp-link">Explore the Platform →</Link>
              </p>
            </section>

            {/* ── 05 Team ────────────────────────────────────────────── */}
            <section id="rs-team" className="rs-sec" aria-labelledby="rs-team-title">
              <State n={5} label="Team" />
              <h2 id="rs-team-title" className="lp-h2">What is the team still missing?</h2>
              <p className="lp-lede">
                Team Builder turns the need into roles. Mark the ones you cover, choose people for the rest,
                and invite each person yourself. They accept or decline.
              </p>
              <figure className="rs-blueprint" aria-labelledby="rs-fig5">
                <figcaption id="rs-fig5" className="lp-figcaption lp-mono">
                  <span>Fig. 5 — Team blueprint · inviting</span><span aria-hidden="true">illustrative</span>
                </figcaption>
                <ul>
                  {ROLES.map((r) => (
                    <li key={r.role} className={`rs-role rs-role--${r.tone}`}>
                      {r.why ? (
                        <details onToggle={(e) => e.currentTarget.open && track("research_team_builder_explored", { role: r.priority })}>
                          <summary>
                            <span className="rs-role-name">{r.role}</span>
                            <span className="lp-mono rs-role-pri">{r.priority}</span>
                            <span className="rs-role-state">{r.state}</span>
                          </summary>
                          <p className="lp-small">Why needed: {r.why}</p>
                        </details>
                      ) : (
                        <div className="rs-role-row">
                          <span className="rs-role-name">{r.role}</span>
                          <span className="lp-mono rs-role-pri">{r.priority}</span>
                          <span className="rs-role-state">{r.state}</span>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
                <p className="lp-small rs-blueprint-foot">
                  One person can cover more than one role. Nobody joins until they accept.
                </p>
              </figure>
            </section>

            {/* ── 06 Work ────────────────────────────────────────────── */}
            <section id="rs-work" className="rs-sec" aria-labelledby="rs-work-title">
              <State n={6} label="Work" />
              <h2 id="rs-work-title" className="lp-h2">Where does the work go next?</h2>
              <p className="lp-lede">
                When you decide the team is ready, you create the project. The need comes with it.
              </p>
              <ol className="rs-handoff">
                {HANDOFF.map(([k, v]) => (
                  <li key={k}><span className="rs-handoff-k">{k}</span><span className="rs-handoff-v">{v}</span></li>
                ))}
              </ol>
              <p className="rs-bridge">
                As the work develops, journal, conference and grant discovery are there on Pro, and AI
                assistance sits inside the project.{" "}
                <Link to="/ai-workspace" className="lp-link" onClick={() => track("research_ai_workspace_clicked")}>Explore AI Workspace →</Link>
              </p>
            </section>
          </div>
        </div>

        {/* ── Final call to action ───────────────────────────────────── */}
        <section className="lp-final" aria-labelledby="rs-final-title">
          <div className="lp-wrap">
            <div className="lp-final-inner">
              <h2 id="rs-final-title" className="lp-h2">Bring the question. Work out who it needs.</h2>
              <p className="lp-lede">
                Start with a free Academic Passport and connect ORCID so others can find your work.
                Pro adds the search, the requests and the team.
              </p>
              <div className="lp-hero-actions">
                <Link to="/register" className="lp-btn lp-btn--primary" onClick={startFree("final")}>Start Free</Link>
                <Link to="/pricing" className="lp-btn lp-btn--ghost" onClick={() => track("research_pricing_clicked", { location: "final" })}>
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

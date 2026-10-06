import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import api from "../lib/api";
import { setPageSeo } from "../lib/seo";
import { trackMarketingEvent as track } from "../lib/marketingAnalytics";
import "../components/landing/landing.css";
import "../components/about/about.css";

/**
 * /about — why Synaptiq exists. No team, history, numbers, logos or
 * testimonials: none are verified or approved for publication. Statements
 * about what exists today are limited to shipped behaviour (Research Need,
 * evidence-based suggestions, individual requests, project + workspace
 * handoff, manuscripts linked to projects, discovery visibility settings,
 * narrow verification). Direction is written as direction.
 */


/* The gaps between the stages of research work. */
const STAGES = [
  ["The question", "What does it actually need?"],
  ["The expertise", "Who has it, and how would you know?"],
  ["The people", "Will they want to work on this together?"],
  ["The collaboration", "Where does the work happen once they say yes?"],
  ["The work", "What does it leave behind?"],
  ["The record", null],
];

const PRINCIPLES = [
  ["Context travels with the question.",
    "A question means more when its disciplines, methods and constraints stay attached to it, from the first draft to the people you approach."],
  ["People are more than their titles.",
    "Relevance lives in what someone works on and how. When Synaptiq suggests a person, it shows the evidence, so you can judge it yourself."],
  ["AI assists. People decide.",
    "AI can structure a question, review a section or compare options, and it shows its cost before it runs. Who to contact, what to claim and where to submit stay with you. Synaptiq never contacts anyone on your behalf."],
  ["Missing expertise is information.",
    "Knowing what a team still lacks is as useful as knowing who already fits. It tells you who to look for next."],
];

export default function About() {
  const [registrationOpen, setRegistrationOpen] = useState(null);

  useEffect(() => setPageSeo({
    title: "About — Why Synaptiq exists",
    description: "Research questions often cross disciplines before the people working on them do. Synaptiq is being built for the steps between a question, the expertise it needs, the people who have it and the work they do together.",
    path: "/about",
  }), []);
  useEffect(() => { track("about_viewed"); }, []);
  useEffect(() => {
    api.get("/auth/registration-status").then((r) => setRegistrationOpen(r.data?.open !== false)).catch(() => setRegistrationOpen(null));
  }, []);

  return (
    <MarketingLayout>
      <div className="lp ab">
        {/* ── Hero ───────────────────────────────────────────────────── */}
        <section className="lp-hero ab-hero" aria-labelledby="ab-h1">
          <div className="lp-wrap">
            <div className="lp-index"><b>—</b> About</div>
            <h1 id="ab-h1" className="lp-h1">A research question can cross disciplines before the team working on it does.</h1>
            <p className="lp-hero-copy">
              Synaptiq is being built for what happens next: finding the expertise a question needs,
              the people who have it, and a place for them to work together.
            </p>
          </div>
        </section>

        {/* ── 01 The problem ─────────────────────────────────────────── */}
        <section className="lp-section lp-section--quiet" aria-labelledby="ab-problem">
          <div className="lp-wrap ab-prose">
            <div className="lp-index"><b>01</b> What we noticed</div>
            <h2 id="ab-problem" className="lp-h2">The tools are fine. The context gets lost between them.</h2>
            <p className="lp-prose">
              A researcher's identity sits in one system and their publications in another. Possible collaborators are
              found through email, conferences or word of mouth. The project lives in shared folders, the AI in a separate
              window, the submission somewhere else again.
            </p>
            <p className="lp-prose">
              Each of these can work well on its own. What doesn't survive the move between them is the reasoning: why
              this question, what it needs, who was approached and why, what was agreed.
            </p>
            <p className="lp-prose">
              And a question rarely needs only information. It may need a statistician, someone who knows the clinical
              setting, someone who has modelled this kind of system before. Titles and departments seldom tell you who
              that is.
            </p>
          </div>
        </section>

        {/* ── 02 The gaps ────────────────────────────────────────────── */}
        <section className="lp-section" aria-labelledby="ab-gaps">
          <div className="lp-wrap">
            <div className="lp-index"><b>02</b> Why Synaptiq</div>
            <h2 id="ab-gaps" className="lp-h2">Synaptiq is built in the gaps between the steps.</h2>
            <figure className="ab-gaps" aria-labelledby="ab-gaps-cap">
              <figcaption id="ab-gaps-cap" className="lp-figcaption lp-mono"><span>The steps of research work, and the question between each pair</span></figcaption>
              <ol>
                {STAGES.map(([stage, gap], i) => (
                  <li key={stage} className="ab-stage">
                    <span className="lp-mono ab-n" aria-hidden="true">{String(i + 1).padStart(2, "0")}</span>
                    <span className="ab-stage-name">{stage}</span>
                    {gap && <span className="ab-gap"><span className="sr-only">Then: </span>{gap}</span>}
                  </li>
                ))}
              </ol>
            </figure>
            <div className="ab-prose ab-now">
              <p className="lp-prose">
                Today a question can become a structured Research Need. Synaptiq can suggest people for it, showing what in
                their profile makes them relevant. You invite each person yourself; those who accept can start a project and
                workspace together, and manuscripts stay linked to the project they came from.
              </p>
              <p className="lp-prose">
                The aim is that the next step never has to begin from zero.
              </p>
            </div>
          </div>
        </section>

        {/* ── 03 Principles ──────────────────────────────────────────── */}
        <section className="lp-section lp-section--quiet" aria-labelledby="ab-principles">
          <div className="lp-wrap">
            <div className="lp-index"><b>03</b> Principles</div>
            <h2 id="ab-principles" className="lp-h2">Four ideas the product is held to.</h2>
            <ol className="ab-principles">
              {PRINCIPLES.map(([t, b], i) => (
                <li key={t}>
                  <span className="lp-mono ab-n" aria-hidden="true">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <h3>{t}</h3>
                    <p>{b}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* ── 04 Direction ───────────────────────────────────────────── */}
        <section className="lp-section" aria-labelledby="ab-direction">
          <div className="lp-wrap ab-prose">
            <div className="lp-index"><b>04</b> What we're building toward</div>
            <h2 id="ab-direction" className="lp-h2">From the question to the record, without starting over.</h2>
            <p className="lp-prose">
              Not all of this exists yet. The direction is a place where a question keeps its context from the first
              draft to the published work, where suggestions improve as profiles describe people more fully, including
              expertise that sits outside universities, and where what a project produces becomes part of a credible
              research record.
            </p>
            <p className="lp-prose">
              Research also happens inside organisations, and a department chart rarely shows how expertise connects
              across it. Making that visible, with people's consent, is part of the same idea.
            </p>
          </div>
        </section>

        {/* ── 05 Control ─────────────────────────────────────────────── */}
        <section className="lp-section lp-section--quiet" aria-labelledby="ab-control">
          <div className="lp-wrap ab-prose">
            <div className="lp-index"><b>05</b> Built for researchers, not around them</div>
            <h2 id="ab-control" className="lp-h2">The researcher stays in charge of the decisions.</h2>
            <p className="lp-prose">
              You choose what your Academic Passport shows and whether you appear in discovery. You decide who to
              contact and which invitations to accept. Nothing an AI produces becomes part of your work unless you put
              it there.
            </p>
            <p className="lp-prose">
              Verification confirms specific things, such as an institutional affiliation. It never vouches for a person
              as a whole. And a research identity is not tied to one job: when someone leaves an institution, its access
              ends and their Passport stays with them.
            </p>
          </div>
        </section>

        {/* ── Final ──────────────────────────────────────────────────── */}
        <section className="lp-final" aria-labelledby="ab-final">
          <div className="lp-wrap">
            <div className="lp-final-inner">
              <h2 id="ab-final" className="lp-h2">Start with your research identity.</h2>
              <p className="lp-lede">Create your Academic Passport and explore Synaptiq from there.</p>
              <div className="lp-hero-actions">
                <Link to="/register" className="lp-btn lp-btn--primary" onClick={() => track("about_signup_clicked")}>Start Free</Link>
                <Link to="/platform" className="lp-btn lp-btn--ghost" onClick={() => track("about_platform_clicked")}>Explore the Platform</Link>
              </div>
              {registrationOpen === false && <p className="lp-small" style={{ marginTop: 16 }}>New sign-ups are paused while billing is set up.</p>}
              <ul className="ab-more">
                <li><Link to="/blog" onClick={() => track("about_blog_clicked")}>Blog</Link><span>Thinking on research and how it's changing</span></li>
                <li><Link to="/resources" onClick={() => track("about_resources_clicked")}>Research Library</Link><span>Practical guidance</span></li>
                <li><Link to="/whats-new">What's New</Link><span>What has changed in Synaptiq</span></li>
                <li><Link to="/contact" onClick={() => track("about_contact_clicked")}>Contact</Link><span>Get in touch</span></li>
              </ul>
            </div>
          </div>
        </section>
      </div>
    </MarketingLayout>
  );
}

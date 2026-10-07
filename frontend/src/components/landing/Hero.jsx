import React from "react";
import { Link } from "react-router-dom";
import { trackMarketingEvent as track } from "@/lib/marketingAnalytics";
import { TID } from "@/lib/testIds";

/**
 * Quiet hero. The figure on the right is the example question marked up
 * exactly the way the public preview reads it (services/public_demo/
 * research_preview.py::_read_structure returns this subject / aim /
 * constraint split for this sentence) — a demonstration, not decoration.
 */
export default function Hero({ registrationOpen, onSeeHow }) {
  return (
    <section className="lp-hero" aria-labelledby="lp-hero-title" data-testid={TID.landingHero}>
      <div className="lp-wrap lp-hero-grid">
        <div>
          <div className="lp-index lp-eyebrow">Research collaboration platform</div>
          <h1 id="lp-hero-title" className="lp-h1">Research starts with a question.</h1>
          <p className="lp-hero-copy">
            Synaptiq shows the expertise your question needs, helps you find the people
            who have it, and gives the team one place to work.
          </p>
          <div className="lp-hero-actions">
            <Link
              to="/register"
              className="lp-btn lp-btn--primary"
              data-testid={TID.landingGetStarted}
              onClick={() => { track("landing_primary_cta", { location: "hero" }); track("signup_started", { location: "hero" }); }}
            >
              Start Free
            </Link>
            <a href="#research-question" className="lp-btn lp-btn--ghost" onClick={onSeeHow}>
              See how it works
            </a>
          </div>
          <p className="lp-hero-note lp-small">
            {registrationOpen === false
              ? "New sign-ups are paused while billing is set up. You can still try the preview below."
              : "Free: Academic Passport, public research page and ORCID. No credit card."}
          </p>
        </div>

        <figure className="lp-figure" aria-labelledby="lp-fig1-caption">
          <figcaption id="lp-fig1-caption" className="lp-figcaption lp-mono">
            <span>Fig. 1 — One question, read for structure</span>
            <span aria-hidden="true">example</span>
          </figcaption>
          <p className="lp-specimen">
            How can <span className="lp-mk lp-mk--subject">public hospitals</span>{" "}
            <span className="lp-mk lp-mk--aim">reduce patient waiting times</span>{" "}
            <span className="lp-mk lp-mk--constraint">without increasing staff workload</span>?
          </p>
          <dl className="lp-legend">
            <div><dt><span className="lp-swatch lp-swatch--subject" aria-hidden="true" />Subject</dt><dd>public hospitals</dd></div>
            <div><dt><span className="lp-swatch lp-swatch--aim" aria-hidden="true" />Aim</dt><dd>reduce waiting times</dd></div>
            <div><dt><span className="lp-swatch lp-swatch--constraint" aria-hidden="true" />Constraint</dt><dd>no added staff workload</dd></div>
          </dl>
        </figure>
      </div>
    </section>
  );
}

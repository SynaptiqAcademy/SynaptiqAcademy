import React from "react";
import { Link } from "react-router-dom";
import { trackMarketingEvent as track } from "@/lib/marketingAnalytics";

/* ── 04 — why Synaptiq ────────────────────────────────────────────────── */
const AREAS = ["Teaching", "Funding", "Publishing", "Impact"];

export function WhySynaptiq() {
  return (
    <section className="lp-section" aria-labelledby="lp-why-title">
      <div className="lp-wrap">
        <div className="lp-index"><b>04</b> AI, where it helps</div>
        <h2 id="lp-why-title" className="lp-h2">AI where it helps. Your judgment where it matters.</h2>
        <p className="lp-lede">
          AI handles the slow parts, such as reviewing a section or checking a journal's fit.
          Each action shows its cost first. Who to work with and what to publish stay your decisions.
        </p>
        <p style={{ marginTop: 16 }}>
          <Link to="/ai-workspace" className="lp-link">Explore AI Workspace →</Link>
        </p>

        <div className="lp-why-strip">
          <span className="lp-mono">Also in Synaptiq</span>
          <ul>{AREAS.map((a) => <li key={a}>{a}</li>)}</ul>
          <Link to="/platform" className="lp-link">See the platform →</Link>
        </div>
      </div>
    </section>
  );
}

/* ── 05 — final call to action ────────────────────────────────────────── */
export function FinalCTA({ registrationOpen }) {
  return (
    <section className="lp-final" aria-labelledby="lp-final-title">
      <div className="lp-wrap">
        <div className="lp-final-inner">
          <h2 id="lp-final-title" className="lp-h2">You already have the question.</h2>
          <p className="lp-lede">Start with your Academic Passport. Add Pro when you need the people and the workspace.</p>
          <div className="lp-hero-actions">
            <Link to="/register" className="lp-btn lp-btn--primary"
              onClick={() => { track("landing_primary_cta", { location: "final" }); track("signup_started", { location: "final" }); }}>
              Start Free
            </Link>
            <Link to="/pricing" className="lp-btn lp-btn--ghost"
              onClick={() => track("pricing_viewed", { location: "landing_final" })}>
              Explore Pricing
            </Link>
          </div>
          {registrationOpen === false && (
            <p className="lp-small" style={{ marginTop: 16 }}>New sign-ups are paused while billing is set up.</p>
          )}
        </div>
      </div>
    </section>
  );
}

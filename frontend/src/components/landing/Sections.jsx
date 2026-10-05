import React from "react";
import { Link } from "react-router-dom";
import { trackMarketingEvent as track } from "@/lib/marketingAnalytics";

/* ── 04 — why Synaptiq ────────────────────────────────────────────────── */
const AREAS = ["Teaching", "Funding", "Publishing", "Impact"];

export function WhySynaptiq() {
  return (
    <section className="lp-section" aria-labelledby="lp-why-title">
      <div className="lp-wrap">
        <div className="lp-index"><b>04</b> Why Synaptiq</div>
        <h2 id="lp-why-title" className="lp-h2">AI where it helps. Your judgment where it matters.</h2>
        <p className="lp-lede">
          AI handles the slow parts: reviewing a section, checking a journal's fit,
          drafting a lesson. Each action shows its cost before it runs. Who to work
          with and what to publish stay your decisions.
        </p>
        <p style={{ marginTop: 18 }}>
          <Link to="/ai-workspace" className="lp-link">Explore AI Workspace →</Link>
        </p>

        <div className="lp-why-strip">
          <span className="lp-mono">The rest of the work, in the same place</span>
          <ul>{AREAS.map((a) => <li key={a}>{a}</li>)}</ul>
          <Link to="/platform" className="lp-link">See the platform →</Link>
        </div>

        <p className="lp-why-who">
          For people who do research, whatever their title says, and for questions
          that sit between disciplines. <Link to="/for-institutions" className="lp-link">For institutions →</Link>
        </p>
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

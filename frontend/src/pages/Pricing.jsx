import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import MarketingLayout from "../components/layout/MarketingLayout";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { setPageSeo } from "../lib/seo";
import { trackMarketingEvent as track } from "../lib/marketingAnalytics";
import { trackMonetizationEvent } from "../lib/analytics";
import "../components/landing/landing.css";
import "../components/pricing/pricing.css";

/**
 * /pricing — the commercial source of truth, rendered from the server:
 * GET /billing/plans (names, prices, credits, limits, checkout_available),
 * GET /billing/feature-matrix (grouped comparison) and
 * GET /auth/registration-status. Nothing commercial is hardcoded here except
 * each plan's one-line purpose and short highlight list (no numbers — those
 * come from the API).
 *
 * Paid plans are offered for purchase only when the server says checkout can
 * be completed and fulfilled (plan.checkout_available). Monthly billing only.
 */


const PURPOSE = {
  free: "Your research identity, visible to the people looking for it.",
  researcher: "Where finding people turns into working with them.",
  pro_researcher: "Deeper analysis, and a view of how your work is picked up.",
  institution: "Synaptiq across a research organisation.",
};
const HIGHLIGHTS = {
  free: ["Academic Passport and public research page", "ORCID and publication import", "Can be found by Pro members"],
  researcher: ["Research network, matching and messaging", "Collaboration requests and projects", "Journal, conference and grant discovery", "AI Research Assistant and Manuscript Copilot"],
  pro_researcher: ["Everything in Pro", "Literature review, gap finder, study design and statistical review", "Collaboration Intelligence", "Impact Dashboard and Citation Monitoring"],
  institution: ["Approved membership and departments", "Member directory by research area", "Admin roles and activity log"],
};
const INTENTS = [
  ["free", "Be found"],
  ["researcher", "Collaborate and do the work"],
  ["pro_researcher", "Go deeper"],
  ["institution", "Bring Synaptiq to an organisation"],
];
const EVENT = { free: "pricing_free_clicked", researcher: "pricing_pro_clicked", pro_researcher: "pricing_pro_advanced_clicked", institution: "pricing_institutional_clicked" };

const eur = (n) => `€${Number(n).toFixed(n % 1 ? 2 : 0)}`;
const quota = (n, unit) => (n === -1 ? `Unlimited ${unit}` : `${n} ${unit}`);

/* ── One rung of the access ladder ─────────────────────────────────── */
function Rung({ plan, index, focus, registrationOpen, onChoose, busy }) {
  const c = plan.code;
  const paid = c === "researcher" || c === "pro_researcher";
  const L = plan.limits || {};
  return (
    <article className={`pr-rung pr-rung--${index} ${focus === c ? "is-focus" : ""} ${focus && focus !== c ? "is-dim" : ""}`}
      aria-labelledby={`pr-name-${c}`}>
      <div className="lp-mono pr-code">Individual · 0{index + 1}</div>
      <h3 id={`pr-name-${c}`} className="pr-name">{plan.name}</h3>
      <p className="pr-purpose">{PURPOSE[c]}</p>
      <div className="pr-price">
        <span className="pr-amount">{eur(plan.price_eur_monthly)}</span>
        {paid && <span className="pr-per">/ month</span>}
      </div>
      {plan.badge && plan.future_price_eur_monthly && (
        <p className="lp-mono pr-early">{plan.badge} price · planned standard price {eur(plan.future_price_eur_monthly)} / month</p>
      )}
      <ul className="pr-facts">
        <li>{plan.credits_per_month} AI Credits a month</li>
        {paid && <li>{quota(L.workspaces, "workspaces")} · {L.repository_gb} GB storage</li>}
      </ul>
      <ul className="pr-high">{(HIGHLIGHTS[c] || []).map((h) => <li key={h}>{h}</li>)}</ul>
      <div className="pr-cta">
        {c === "free" ? (
          <>
            <Link to="/register" className="lp-btn lp-btn--ghost" onClick={() => track(EVENT.free, { location: "ladder" })}>Start Free</Link>
            {registrationOpen === false && <p className="lp-small pr-note">New sign-ups are paused while billing is set up.</p>}
          </>
        ) : plan.checkout_available ? (
          <button type="button" className="lp-btn lp-btn--primary" disabled={busy === c} onClick={() => onChoose(plan)}>
            {busy === c ? "Opening…" : `Choose ${plan.name}`}
          </button>
        ) : (
          <p className="lp-small pr-note">Online purchase isn't open yet. You can start on Free now.</p>
        )}
      </div>
    </article>
  );
}

/* ── Comparison: table on desktop, plan-by-plan on mobile ──────────── */
function Compare({ matrix, plans }) {
  const [mobilePlan, setMobilePlan] = useState("researcher");
  const names = Object.fromEntries(plans.map((p) => [p.code, p.name]));
  const groups = [];
  matrix.rows.forEach((r) => {
    let g = groups.find((x) => x.name === r.group);
    if (!g) { g = { name: r.group, rows: [] }; groups.push(g); }
    g.rows.push(r);
  });
  const ORDER = ["Identity", "Network & collaboration", "Research work", "Discovery", "AI", "Impact & analytics", "Teaching"];
  groups.sort((x, y) => (ORDER.indexOf(x.name) + 99 * (ORDER.indexOf(x.name) < 0)) - (ORDER.indexOf(y.name) + 99 * (ORDER.indexOf(y.name) < 0)));
  const cell = (v) => (v === true ? "Included" : v === false ? "Not included" : v);
  const col = matrix.columns;
  return (
    <>
      <table className="pr-table">
        <caption className="sr-only">Plan comparison by feature</caption>
        <thead>
          <tr><th scope="col"><span className="sr-only">Feature</span></th>{col.map((c) => <th key={c} scope="col">{names[c]}</th>)}</tr>
        </thead>
        {groups.map((g) => (
          <tbody key={g.name}>
            <tr className="pr-group"><th scope="rowgroup" colSpan={col.length + 1}>{g.name}</th></tr>
            {g.rows.map((r) => (
              <tr key={r.label}>
                <th scope="row">{r.label}</th>
                {r.values.map((v, i) => <td key={col[i]} className={v === false ? "is-no" : ""}>{cell(v)}</td>)}
              </tr>
            ))}
          </tbody>
        ))}
      </table>

      <div className="pr-mcompare">
        <div className="pr-mtabs" role="tablist" aria-label="Choose a plan to compare">
          {col.map((c) => (
            <button key={c} type="button" role="tab" aria-selected={mobilePlan === c} className={mobilePlan === c ? "is-sel" : ""}
              onClick={() => { setMobilePlan(c); track("pricing_comparison_opened", { plan: c, view: "mobile" }); }}>
              {names[c]}
            </button>
          ))}
        </div>
        <div role="tabpanel" aria-label={names[mobilePlan]}>
          {groups.map((g) => (
            <div key={g.name} className="pr-mgroup">
              <div className="lp-mono pr-mgroup-name">{g.name}</div>
              <dl>
                {g.rows.map((r) => {
                  const v = r.values[col.indexOf(mobilePlan)];
                  return <div key={r.label} className={v === false ? "is-no" : ""}><dt>{r.label}</dt><dd>{cell(v)}</dd></div>;
                })}
              </dl>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

export default function Pricing() {
  const { user } = useAuth() || {};
  const navigate = useNavigate();
  const [plans, setPlans] = useState(null);
  const [matrix, setMatrix] = useState(null);
  const [registrationOpen, setRegistrationOpen] = useState(null);
  const [failed, setFailed] = useState(false);
  const [focus, setFocus] = useState(null);
  const [busy, setBusy] = useState(null);
  const creditsRef = useRef(null);

  useEffect(() => setPageSeo({
    title: "Pricing — Free, Pro, Pro Advanced and Institutional | Synaptiq",
    description: "Free gives you an academic identity others can find. Pro adds the research network, collaboration, projects and AI. Pro Advanced adds deeper research tools and impact. Institutional plans are arranged per organisation.",
    path: "/pricing",
  }), []);
  useEffect(() => { track("pricing_viewed"); }, []);

  const load = () => {
    setFailed(false);
    Promise.all([api.get("/billing/plans"), api.get("/billing/feature-matrix")])
      .then(([p, m]) => {
        setPlans(p.data || []);
        setMatrix(m.data || { columns: [], rows: [] });
      })
      .catch(() => setFailed(true));
    api.get("/auth/registration-status").then((r) => setRegistrationOpen(r.data?.open !== false)).catch(() => setRegistrationOpen(null));
  };
  useEffect(load, []);

  useEffect(() => {
    const el = creditsRef.current;
    if (!el || !("IntersectionObserver" in window)) return undefined;
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { track("pricing_ai_credits_viewed"); io.disconnect(); } });
    io.observe(el);
    return () => io.disconnect();
  }, [plans]);

  const choose = async (plan) => {
    track(EVENT[plan.code], { location: "ladder" });
    trackMonetizationEvent("upgrade_clicked", { plan_code: plan.code, source: "pricing" });
    if (!user) { navigate("/register"); return; }
    setBusy(plan.code);
    track("pricing_checkout_started", { plan: plan.key });
    trackMonetizationEvent("checkout_started", { plan_code: plan.code });
    try {
      const res = await api.post("/billing/checkout-session", { plan: plan.key, billing_period: "monthly" });
      if (res.data?.url) { window.location.href = res.data.url; return; }
      if (res.data?.changed) toast.success(res.data.message || "Your plan change is being confirmed.");
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.info(d?.code === "already_subscribed" ? d.message : "We couldn't open checkout right now. Please try again later.");
    } finally {
      setBusy(null);
    }
  };

  const individual = (plans || []).filter((p) => ["free", "researcher", "pro_researcher"].includes(p.code));
  const inst = (plans || []).find((p) => p.code === "institution");
  const paidOpen = individual.some((p) => p.checkout_available);

  return (
    <MarketingLayout>
      <div className="lp pr">
        {/* ── Hero ───────────────────────────────────────────────────── */}
        <section className="lp-hero pr-hero" aria-labelledby="pr-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>—</b> Pricing</div>
            <h1 id="pr-title" className="lp-h1">Be found for free. Pay when the work moves here.</h1>
            <p className="lp-hero-copy">
              Free gives you an academic identity others can find. Pro and Pro Advanced add the network,
              the projects and AI-assisted work.
            </p>
          </div>
        </section>

        {/* ── 01 Access ladder ───────────────────────────────────────── */}
        <section className="lp-section lp-section--quiet pr-access" aria-labelledby="pr-access-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>01</b> Access</div>
            <h2 id="pr-access-title" className="sr-only">Plans</h2>

            <div className="pr-intent" role="group" aria-label="What do you want to do? (optional)">
              <span className="lp-mono pr-intent-label">I want to</span>
              {INTENTS.map(([code, label]) => (
                <button key={code} type="button" aria-pressed={focus === code} className={focus === code ? "is-sel" : ""}
                  onClick={() => { const next = focus === code ? null : code; setFocus(next); if (next) track("pricing_intent_selected", { intent: code }); }}>
                  {label}
                </button>
              ))}
            </div>

            {failed && (
              <div className="pr-failed" role="alert">
                <p>Plans couldn't be loaded just now.</p>
                <button type="button" className="lp-btn lp-btn--ghost" onClick={load}>Try again</button>
              </div>
            )}
            {!plans && !failed && <p className="lp-small" aria-live="polite">Loading plans…</p>}

            {plans && (
              <div className="pr-ladder">
                <div className="pr-individual">
                  <div className="lp-mono pr-track-label">For individuals · each step adds to the one before</div>
                  <div className="pr-rungs">
                    {individual.map((p, i) => (
                      <Rung key={p.code} plan={p} index={i} focus={focus} registrationOpen={registrationOpen} onChoose={choose} busy={busy} />
                    ))}
                  </div>
                  <p className="lp-small pr-terms">Prices in euros, billed monthly. {!paidOpen && "Paid plans can't be bought online yet."}</p>
                </div>

                {inst && (
                  <article className={`pr-org ${focus === "institution" ? "is-focus" : ""} ${focus && focus !== "institution" ? "is-dim" : ""}`} aria-labelledby="pr-name-institution">
                    <div className="lp-mono pr-track-label">For organisations</div>
                    <div className="lp-mono pr-code">Organisation · 01</div>
                    <h3 id="pr-name-institution" className="pr-name">{inst.name}</h3>
                    <p className="pr-purpose">{PURPOSE.institution}</p>
                    <div className="pr-price"><span className="pr-amount pr-amount--custom">Custom</span></div>
                    <ul className="pr-high">{HIGHLIGHTS.institution.map((h) => <li key={h}>{h}</li>)}</ul>
                    <p className="lp-small">Membership comes from the organisation, not from an individual plan.</p>
                    <div className="pr-cta">
                      <Link to="/for-institutions#inquiry" className="lp-btn lp-btn--ghost" onClick={() => track(EVENT.institution, { location: "ladder" })}>Contact Sales</Link>
                    </div>
                  </article>
                )}
              </div>
            )}
          </div>
        </section>

        {/* ── 02 Compare ─────────────────────────────────────────────── */}
        {matrix && plans && (
          <section className="lp-section pr-compare" aria-labelledby="pr-compare-title">
            <div className="lp-wrap">
              <div className="lp-index"><b>02</b> Compare</div>
              <h2 id="pr-compare-title" className="lp-h2">The individual plans, side by side.</h2>
              <Compare matrix={matrix} plans={plans} />
            </div>
          </section>
        )}

        {/* ── Section three: credits ──────────────────────────────────────────── */}
        <section ref={creditsRef} className="lp-section lp-section--quiet" aria-labelledby="pr-credits-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>03</b> AI credits</div>
            <h2 id="pr-credits-title" className="lp-h2">Credits are only for AI actions.</h2>
            <dl className="pr-qa">
              <div><dt>What uses them</dt><dd>
                AI actions such as a Copilot message, a manuscript review or a literature review. Each action has a
                fixed cost, shown before it runs.
              </dd></div>
              <div><dt>What doesn't</dt><dd>
                Your profile and ORCID, browsing the network, messaging, projects and workspaces, journal, conference
                and grant discovery, and matching people to a Research Need.
              </dd></div>
              <div><dt>Each month</dt><dd>
                {individual.length ? individual.map((p) => `${p.name} ${p.credits_per_month}`).join(" · ") : "Pro and Pro Advanced include monthly credits"}.
                Monthly credits renew with your plan and don't roll over.
              </dd></div>
              <div><dt>If something fails</dt><dd>If an AI action fails, its credits go back.</dd></div>
              <div><dt>Extra credits</dt><dd>
                Credit packs for Pro and Pro Advanced don't expire and are used after your monthly credits. They aren't
                on sale online yet.
              </dd></div>
            </dl>
            <p style={{ marginTop: 20 }}><Link to="/ai-workspace" className="lp-link">See what AI does in Synaptiq →</Link></p>
          </div>
        </section>

        {/* ── 04 Questions ───────────────────────────────────────────── */}
        <section className="lp-section" aria-labelledby="pr-faq-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>04</b> Questions</div>
            <h2 id="pr-faq-title" className="lp-h2">Before you choose.</h2>
            <div className="pr-faq">
              <details><summary>Is Free a trial?</summary><p>No. Free is a plan with no time limit. It covers your Academic Passport, public research page and ORCID.</p></details>
              <details><summary>Can I change plans?</summary><p>Yes. Moving up is charged pro rata straight away; moving down is credited pro rata on your next invoice. Your access changes once the payment is confirmed.</p></details>
              <details><summary>What happens if I cancel?</summary><p>Your plan runs to the end of the period you've paid for, then your account moves to Free. Projects and workspaces become read-only rather than deleted, and purchased credits stay on your account for when you're on a paid plan again.</p></details>
              <details><summary>What if a payment fails?</summary><p>Your plan continues while the payment is retried. If it still can't be collected, your account moves to Free features until it is.</p></details>
              <details><summary>Does Pro Advanced include institutional access?</summary><p>No. Institutional access comes from approved membership of an institution on Synaptiq, not from an individual plan.</p></details>
              <details><summary>Is there annual billing?</summary><p>Not at the moment. All plans are billed monthly.</p></details>
            </div>
          </div>
        </section>

        {/* ── Final ──────────────────────────────────────────────────── */}
        <section className="lp-final" aria-labelledby="pr-final-title">
          <div className="lp-wrap">
            <div className="lp-final-inner">
              <h2 id="pr-final-title" className="lp-h2">Start with your research identity. Add the work when you need it.</h2>
              <div className="lp-hero-actions">
                <Link to="/register" className="lp-btn lp-btn--primary" onClick={() => track(EVENT.free, { location: "final" })}>Start Free</Link>
                <Link to="/for-institutions#inquiry" className="lp-btn lp-btn--ghost" onClick={() => track(EVENT.institution, { location: "final" })}>Contact Sales</Link>
              </div>
              {registrationOpen === false && <p className="lp-small" style={{ marginTop: 16 }}>New sign-ups are paused while billing is set up.</p>}
            </div>
          </div>
        </section>
      </div>
    </MarketingLayout>
  );
}

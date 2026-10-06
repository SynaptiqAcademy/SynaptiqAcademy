import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import api from "../lib/api";
import { setPageSeo } from "../lib/seo";
import { trackMarketingEvent as track } from "../lib/marketingAnalytics";
import "../components/landing/landing.css";
import "../components/institutions/institutions.css";

/**
 * /for-institutions — the research layer across an organisation.
 *
 * Capabilities shown are the shipped institution model:
 * - membership only via an approved institution_memberships row
 *   (services/permissions.require_institution_member): institutional email
 *   domain, an accepted invitation, or admin review of evidence;
 * - departments, department admins/coordinators and rosters
 *   (routers/departments.py); member directory with research areas
 *   (routers/institution_hub.py research-directory);
 * - admin approval / invitation / revocation with an audit log
 *   (routers/institutions.py).
 * Organisation billing does not exist, so the only commercial action is a
 * Contact Sales inquiry (POST /api/contact, topic "institution", stored and
 * emailed). Every person and department below is illustrative.
 */


function scrollTo(id, e) {
  e?.preventDefault?.();
  const el = document.getElementById(id);
  if (!el) return;
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
}

/* ── Fig. 1 — org chart vs research map (illustrative) ───────────────── */
const DEPTS = [
  { name: "Department A", field: "Health sciences", people: [["01", ["Health services research", "Survey research"]], ["02", ["Health policy"]]] },
  { name: "Department B", field: "Engineering", people: [["03", ["Operations research", "Simulation"]], ["04", ["Data science", "Simulation"]]] },
  { name: "Department C", field: "Economics", people: [["05", ["Health economics", "Health policy"]], ["06", ["Survey research", "Econometrics"]]] },
];
const AREAS = ["Health policy", "Simulation", "Survey research", "Data science", "Health economics"];

const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

function ResearchMap() {
  const [area, setArea] = useState("Health policy");
  const who = DEPTS.flatMap((d) => d.people.filter(([, a]) => a.includes(area)).map(([n]) => ({ n, dept: d.name })));
  const pick = (a) => { setArea(a); track("institutional_map_explored", { area: a }); };
  return (
    <figure className="in-map" aria-labelledby="in-fig1">
      <figcaption id="in-fig1" className="lp-figcaption lp-mono">
        <span>Fig. 1 — The same six people, two ways</span><span aria-hidden="true">illustrative</span>
      </figcaption>

      <div className="in-map-grid">
        <div className="in-org">
          <div className="lp-mono in-label">The org chart · where people sit</div>
          <div className="in-org-root">Illustrative institution</div>
          <div className="in-org-depts">
            {DEPTS.map((d) => (
              <div key={d.name} className="in-dept">
                <div className="in-dept-name">{d.name}</div>
                <div className="lp-mono in-dept-field">{d.field}</div>
                <ul>
                  {d.people.map(([n, a]) => (
                    <li key={n} className={a.includes(area) ? "is-on" : ""}>Researcher {n}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="in-res">
          <div className="lp-mono in-label">The research map · what they work on</div>
          <div className="in-areas" role="group" aria-label="Research areas">
            {AREAS.map((a) => (
              <button key={a} type="button" aria-pressed={area === a} className={area === a ? "is-sel" : ""} onClick={() => pick(a)}>{a}</button>
            ))}
          </div>
          <div className="in-result" aria-live="polite">
            <div className="in-result-head"><span className="in-result-area">{area}</span><span className="lp-mono">{plural(who.length, "person", "people")} · {plural(new Set(who.map((w) => w.dept)).size, "department", "departments")}</span></div>
            <ul>
              {who.map((w) => <li key={w.n}><span>Researcher {w.n}</span><span className="lp-mono">{w.dept}</span></li>)}
            </ul>
          </div>
        </div>
      </div>
      <p className="lp-small in-map-note">
        Built from what members list as their research areas in their own Academic Passports. The map is only
        as complete as those profiles.
      </p>
    </figure>
  );
}

/* ── Contact Sales ────────────────────────────────────────────────────── */
function Inquiry() {
  const [f, setF] = useState({ name: "", email: "", organization: "", role: "", message: "" });
  const [state, setState] = useState("idle");
  const [error, setError] = useState("");
  const started = useRef(false);
  const set = (k) => (e) => {
    if (!started.current) { started.current = true; track("institutional_contact_started", { location: "form" }); }
    setF({ ...f, [k]: e.target.value });
  };
  const submit = async (e) => {
    e.preventDefault();
    setState("sending"); setError("");
    try {
      await api.post("/contact", {
        name: f.name, email: f.email, topic: "institution", message: f.message,
        organization: f.organization || null, role: f.role || null,
      });
      setState("sent");
      track("institutional_inquiry_submitted");
    } catch (err) {
      const s = err?.response?.status;
      setError(s === 429 ? "That's several messages in a short time. Please try again in an hour."
        : s === 422 ? "Please check the email address and fill in each required field."
        : (typeof err?.response?.data?.detail === "string" ? err.response.data.detail : "Your message couldn't be sent. Please try again."));
      setState("idle");
    }
  };
  if (state === "sent") {
    return (
      <div className="in-sent" role="status">
        <div className="in-sent-title">Thank you. Your message has reached the Synaptiq team.</div>
        <p className="lp-small">We'll reply to {f.email}.</p>
      </div>
    );
  }
  return (
    <form className="in-form" onSubmit={submit} noValidate={false}>
      <div className="in-form-row">
        <label>Your name<input required maxLength={120} value={f.name} onChange={set("name")} autoComplete="name" /></label>
        <label>Work email<input required type="email" value={f.email} onChange={set("email")} autoComplete="email" /></label>
      </div>
      <div className="in-form-row">
        <label>Institution or organisation<input required maxLength={200} value={f.organization} onChange={set("organization")} autoComplete="organization" /></label>
        <label>Your role <span className="lp-small">(optional)</span><input maxLength={200} value={f.role} onChange={set("role")} autoComplete="organization-title" /></label>
      </div>
      <label>What are you looking for?<textarea required rows={4} maxLength={4000} value={f.message} onChange={set("message")} /></label>
      {error && <p role="alert" className="in-error">{error}</p>}
      <div className="in-form-foot">
        <button type="submit" className="lp-btn lp-btn--primary" disabled={state === "sending"}>
          {state === "sending" ? "Sending…" : "Contact Sales"}
        </button>
        <span className="lp-small">We use these details only to reply. <Link to="/privacy" className="lp-link">Privacy Policy</Link></span>
      </div>
    </form>
  );
}

export default function InstitutionsLanding() {

  useEffect(() => setPageSeo({
    title: "For Institutions — See how your research expertise connects",
    description: "An institutional layer for Synaptiq: approved membership, departments and a member directory built from researchers' own Academic Passports, so expertise is visible across departments. Contact Sales.",
    path: "/for-institutions",
  }), []);
  useEffect(() => { track("institutions_page_viewed"); }, []);
  // Arriving from another page at /for-institutions#inquiry (e.g. Pricing's
  // Contact Sales) — the router doesn't scroll to hashes on its own.
  useEffect(() => {
    const id = window.location.hash.replace("#", "");
    if (id) setTimeout(() => document.getElementById(id)?.scrollIntoView({ block: "start" }), 50);
  }, []);

  const toInquiry = (location) => (e) => { scrollTo("inquiry", e); track("institutional_contact_started", { location }); };

  return (
    <MarketingLayout>
      <div className="lp in">
        {/* ── Hero ───────────────────────────────────────────────────── */}
        <section className="lp-hero in-hero" aria-labelledby="in-hero-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>—</b> For institutions</div>
            <h1 id="in-hero-title" className="lp-h1">The org chart shows where people sit. Not how the research connects.</h1>
            <p className="lp-hero-copy">
              Synaptiq adds an institutional layer to researchers' own Academic Passports, so the expertise
              already inside your organisation can be seen across its departments.
            </p>
            <div className="lp-hero-actions">
              <a href="#inquiry" className="lp-btn lp-btn--primary" onClick={toInquiry("hero")}>Contact Sales</a>
              <a href="#map" className="lp-btn lp-btn--ghost" onClick={(e) => { scrollTo("map", e); track("institutional_map_explored", { source: "hero" }); }}>
                See the institutional model
              </a>
            </div>
            <p className="lp-hero-note lp-small">Institutional plans are arranged with us. Pricing is custom.</p>
          </div>
        </section>

        {/* ── 01 Map ─────────────────────────────────────────────────── */}
        <section id="map" className="lp-section lp-section--quiet" aria-labelledby="in-map-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>01</b> The research map</div>
            <h2 id="in-map-title" className="lp-h2">The expertise is often already there, in another department.</h2>
            <p className="lp-lede">Pick a research area and see who works on it, wherever they report.</p>
            <ResearchMap />
          </div>
        </section>

        {/* ── 02 Identity ────────────────────────────────────────────── */}
        <section className="lp-section" aria-labelledby="in-id-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>02</b> People keep their research identity</div>
            <h2 id="in-id-title" className="lp-h2">Membership is a relationship to the Passport, not ownership of it.</h2>
            <ol className="in-chain">
              <li>
                <div className="lp-mono in-label">The person</div>
                <div className="in-chain-name">Academic Passport</div>
                <p>Research areas, methods, professional expertise, and publications from ORCID. Kept by the researcher.</p>
              </li>
              <li className="in-chain-link">
                <div className="lp-mono in-label">The relationship</div>
                <div className="in-chain-name">Approved membership</div>
                <p>Through your institutional email domain, an invitation the person accepts, or an admin's review of evidence.</p>
              </li>
              <li>
                <div className="lp-mono in-label">The institution</div>
                <div className="in-chain-name">Departments and directory</div>
                <p>Where they sit, who else works on what, and who administers it.</p>
              </li>
            </ol>
            <p className="in-aside">
              A name typed into a profile or an ORCID affiliation is not membership. When someone leaves, institutional
              access ends and their Passport and research record stay with them.
            </p>
          </div>
        </section>

        {/* ── 03 Departments ─────────────────────────────────────────── */}
        <section className="lp-section lp-section--quiet" aria-labelledby="in-dept-title">
          <div className="lp-wrap in-two">
            <div>
              <div className="lp-index"><b>03</b> Organise without flattening</div>
              <h2 id="in-dept-title" className="lp-h2">Departments for structure. Research areas for everything else.</h2>
              <p className="lp-lede">
                Admins set up departments and give them their own admins and research coordinators. Members can
                belong to more than one, and projects their members own can be linked to a department.
              </p>
            </div>
            <figure className="in-roster" aria-labelledby="in-fig2" onMouseEnter={() => track("institutional_members_explored")}>
              <figcaption id="in-fig2" className="lp-figcaption lp-mono">
                <span>Fig. 2 — Department B roster</span><span aria-hidden="true">illustrative</span>
              </figcaption>
              <div className="in-row in-row--head lp-mono"><span>Member</span><span>Role</span><span>Research areas</span></div>
              <div className="in-row"><span>Researcher 03</span><span className="lp-mono">Department admin</span><span>Operations research · Simulation</span></div>
              <div className="in-row"><span>Researcher 04</span><span className="lp-mono">Research coordinator</span><span>Data science · Simulation</span></div>
              <div className="in-row"><span>Researcher 05</span><span className="lp-mono">Researcher</span><span>Health economics · also Department C</span></div>
            </figure>
          </div>
        </section>

        {/* ── 04 Administration ──────────────────────────────────────── */}
        <section className="lp-section" aria-labelledby="in-admin-title">
          <div className="lp-wrap in-two">
            <figure className="in-roster" aria-labelledby="in-fig3">
              <figcaption id="in-fig3" className="lp-figcaption lp-mono">
                <span>Fig. 3 — Membership requests</span><span aria-hidden="true">illustrative</span>
              </figcaption>
              <div className="in-row in-row--head lp-mono"><span>Person</span><span>How</span><span>State</span></div>
              <div className="in-row"><span>Researcher 07</span><span>Institutional email</span><span className="lp-mono">approved</span></div>
              <div className="in-row"><span>Researcher 08</span><span>Evidence link for review</span><span className="lp-mono in-act">approve · decline</span></div>
              <div className="in-row"><span>Researcher 09</span><span>Invited by an admin</span><span className="lp-mono">awaiting acceptance</span></div>
            </figure>
            <div>
              <div className="lp-index"><b>04</b> Administration</div>
              <h2 id="in-admin-title" className="lp-h2">Admins decide who belongs. Every decision is recorded.</h2>
              <p className="lp-lede">
                Approve or decline requests, invite people by email, assign roles and revoke membership. Each of these
                actions appears in the institution's activity log.
              </p>
            </div>
          </div>
        </section>

        {/* ── 05 Permissions ─────────────────────────────────────────── */}
        <section className="lp-section lp-section--quiet" aria-labelledby="in-gov-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>05</b> Permissions</div>
            <h2 id="in-gov-title" className="lp-h2">What belonging to an institution does, and doesn't, open.</h2>
            <dl className="in-perms" onMouseEnter={() => track("institutional_governance_explored")}>
              <div><dt>Members see</dt><dd>Colleagues' names and research areas, department rosters, and projects linked to their departments.</dd></div>
              <div><dt>Admins also see</dt><dd>Email addresses, membership requests with their evidence, and the activity log.</dd></div>
              <div><dt>Nobody gains</dt><dd>Access to a member's messages, private projects, manuscripts or AI conversations through membership.</dd></div>
              <div><dt>Beyond the institution</dt><dd>Members stay part of the wider Synaptiq network, under their own settings and plan.</dd></div>
            </dl>
          </div>
        </section>

        {/* ── Contact Sales ──────────────────────────────────────────── */}
        <section id="inquiry" className="lp-final in-final" aria-labelledby="in-final-title">
          <div className="lp-wrap in-two">
            <div>
              <h2 id="in-final-title" className="lp-h2">Your institution already has a research network. Tell us about it.</h2>
              <p className="lp-lede">
                We'll talk through your departments, how membership should work, and what you'd like people to be able to find.
              </p>
              <p className="in-links">
                <Link to="/platform" className="lp-link" onClick={() => track("institutional_platform_clicked")}>Explore the Platform →</Link>
              </p>
              <p className="lp-small in-indiv">
                Looking for an individual account? <Link to="/register" className="lp-link">Start Free →</Link>
              </p>
            </div>
            <Inquiry />
          </div>
        </section>
      </div>
    </MarketingLayout>
  );
}

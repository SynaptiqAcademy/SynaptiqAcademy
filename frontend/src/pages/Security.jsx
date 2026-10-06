import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import { setPageSeo } from "../lib/seo";
import { LEGAL, LEGAL_DOCS } from "../content/legal/meta";
import { openPreferences } from "../lib/cookieConsent";
import "../components/landing/landing.css";
import "./security.css";

/*
 * Security — the trust page. Every statement here is listed, with its
 * evidence, in docs/privacy/public-security-claims.md; anything not marked
 * "Publish: YES" there must not appear here. No certifications, response
 * times, backup schedules, encryption-at-rest or data-location promises.
 */

const MODEL = [
  ["Identity", "You sign in with a password or ORCID."],
  ["Access", "Our servers check each request against your account and memberships."],
  ["Private work", "Projects, drafts and AI conversations belong to you and the people you add."],
  ["Controlled sharing", "What you share, and what you make public, is your deliberate choice."],
  ["External processing", "AI features and email use named providers, only when needed."],
  ["Monitoring & response", "Security events are logged, and incidents are assessed and handled."],
];

const Rows = ({ items }) => (
  <dl className="sc-rows">
    {items.map(([k, v]) => (
      <div key={k}><dt className="lp-mono">{k}</dt><dd>{v}</dd></div>
    ))}
  </dl>
);

const SECTIONS = [
  { id: "authentication", title: "Account & authentication", body: (<>
    <ul>
      <li>You sign in with email and password, or with ORCID. Other sign-in options appear only when they are actually available.</li>
      <li>Passwords are stored with one-way hashing, never as readable text.</li>
      <li>Sessions use short-lived cookies that scripts on the page can't read, and forms are protected against requests sent from other sites.</li>
      <li>Repeated failed sign-ins lock the account for a while.</li>
      <li>Every way of creating an account requires confirming you are 18 or older and accepting the Terms.</li>
      <li>Deleting your account requires your password or a recent sign-in, and ends every session at once.</li>
    </ul>
  </>) },
  { id: "access", title: "Access & privacy boundaries", body: (<>
    <p>Access is decided on Synaptiq's servers for each request, not by what a page happens to display.</p>
    <aside className="sc-callout" aria-label="Identity is not authorisation">
      <div className="lp-mono sc-callout-label">Identity is not authorisation</div>
      <p>Having an account doesn't open anyone else's private work, and none of these grants access on its own:</p>
      <Rows items={[
        ["A paid plan", "Plans change features and AI Credits. They don't give access to an institution or to other members' work."],
        ["An affiliation", "An institution on your profile, or an ORCID affiliation, isn't membership. Institution features require membership the institution has approved."],
        ["Membership", "Being an approved member isn't administration. Managing an institution requires an administrator role."],
        ["Administration", "Synaptiq's administrative functions require an administrator account, and administrative actions are logged."],
      ]} />
    </aside>
    <h4 className="sc-sub">Public and private</h4>
    <p>A public research profile shows only the academic sections you leave on. Projects, grants, collaborations and your email address stay off unless you turn them on. Messages, AI conversations, private projects and workspaces, and account details are never part of it.</p>
    <p>A profile set to private has no public page. Turning off discovery removes you from researcher discovery and the directory. Blocking someone hides each of you from the other in discovery and stops their requests. The controls are explained in <Link to="/gdpr">Data Protection</Link>.</p>
  </>) },
  { id: "content", title: "Research content & files", body: (<>
    <p>Synaptiq is built for collaboration: the boundary is membership, not isolation.</p>
    <ul>
      <li>Projects, workspaces and manuscripts are available to their members. A file belongs to the project, workspace or manuscript it's added to, and is available to that space's members.</li>
      <li>When you add people to your work, they can read what you share, and they keep access to what was shared after you leave.</li>
      <li>A project you mark public is visible to signed-in members. It appears on your public research page only if you turn that section on.</li>
      <li>Deleting a file also deletes the stored file, not just its listing.</li>
      <li>Messages are stored on Synaptiq's servers and are not end-to-end encrypted.</li>
    </ul>
    <p>Synaptiq staff access stored content only where needed to run the service, keep it safe or meet a legal obligation.</p>
  </>) },
  { id: "ai", title: "AI & external processing", body: (<>
    <p>AI features run only when you use one. The material that feature works with (your question, text you choose, manuscript sections or project details) is sent to an AI provider:</p>
    <ul>
      <li><strong>Anthropic</strong> answers most requests; <strong>OpenAI</strong> answers if Anthropic is unavailable, and creates search embeddings for documents you add to a knowledge base. Both process data in the United States.</li>
      <li>Under their API terms they don't train their models on this content by default, and they keep it for a limited period under their own policies.</li>
      <li>Our AI usage records keep the feature used, duration and credits, not the text of your request. Your AI conversations stay in your account until you delete them.</li>
    </ul>
    <p>Notification emails say what happened, not what it's about: they don't carry manuscript or project titles, review notes or messages.</p>
  </>) },
  { id: "infrastructure", title: "Application & infrastructure", body: (<>
    <ul>
      <li>Connections to Synaptiq are served over HTTPS, and plain HTTP is redirected to it.</li>
      <li>Browsers are told not to load Synaptiq inside other websites, and other standard browser protections are switched on.</li>
      <li>Typefaces are served by Synaptiq itself, and nothing is loaded from an analytics provider until you allow analytics.</li>
      <li>Synaptiq runs on cloud infrastructure for application hosting, the database and website delivery, with separate providers for email, AI and analytics. Application servers are in the United States, and a choice of data location isn't currently offered.</li>
    </ul>
    <p>The <Link to="/privacy#providers">Privacy Policy</Link> names each provider and where it processes data.</p>
  </>) },
  { id: "analytics", title: "Analytics & operational data", body: (<>
    <p>Analytics stays off until you allow it. It records page views and named events only, with no automatic click capture and no session recording, and research content isn't sent to it. You can withdraw at any time in <button type="button" className="sc-linkbtn" onClick={openPreferences}>Cookie settings</button>; see the <Link to="/cookies">Cookie Policy</Link>.</p>
    <p>Security events, such as failed sign-ins, and administrative actions are logged for security and accountability, and deleted after set periods listed in the <Link to="/privacy#retention">Privacy Policy</Link>.</p>
  </>) },
  { id: "response", title: "Monitoring & incident response", body: (<>
    <p>Security-relevant events are recorded so suspicious activity can be investigated. Synaptiq maintains an internal process for responding to security incidents: containing the problem, establishing what data and people are affected, and deciding whether a personal data breach must be reported to the supervisory authority and to the people affected, as data-protection law requires.</p>
  </>) },
  { id: "not-claimed", title: "What we do not claim", body: (<>
    <Rows items={[
      ["Certifications", "Synaptiq doesn't hold SOC 2 or ISO 27001 certification and doesn't claim HIPAA compliance. Our providers' certifications are theirs, not Synaptiq's."],
      ["GDPR", <>Data protection is described as controls and rights in <Link to="/gdpr">Data Protection</Link>, not presented as a certification or badge.</>],
      ["Testing", "No external penetration test has been published."],
      ["Commitments", "We don't publish backup, encryption-at-rest or data-location commitments until they are confirmed with our providers."],
      ["Sensitive data", "Synaptiq isn't designed for directly identifiable patient or research-participant data, clinical records, or classified or otherwise regulated material. You remain responsible for your research governance."],
      ["Institutions", "Institutional arrangements are agreed separately. This page doesn't replace a security questionnaire, data processing agreement or security schedule. Single sign-on, dedicated hosting and customer-managed keys aren't offered."],
    ]} />
  </>) },
  { id: "report", title: "Reporting a security issue", body: (<>
    <p>If you think you've found a vulnerability, tell us through the <Link to="/contact?topic=security">contact form</Link>, choosing the Security topic. Describe what you found and how to reproduce it.</p>
    <p>Don't access, change or delete other people's data, don't run tests that could disrupt the service, and give us a chance to investigate before disclosing anything publicly. There is no bug bounty. A dedicated security contact will be published here once it's in place.</p>
  </>) },
];

const num = (i) => String(i + 1).padStart(2, "0");

export default function Security() {
  useEffect(() => setPageSeo({
    title: "Security | Synaptiq",
    description: "How Synaptiq controls access to accounts, private research and shared work, what goes to outside providers, and what Synaptiq does not claim.",
    path: "/security",
  }), []);
  useEffect(() => {
    const id = window.location.hash.replace("#", "");
    if (id) setTimeout(() => document.getElementById(id)?.scrollIntoView({ block: "start" }), 50);
  }, []);

  return (
    <MarketingLayout>
      <div className="lp sc">
        <header className="sc-head">
          <div className="lp-wrap">
            <div className="lp-mono sc-crumb"><b>Trust</b><span aria-hidden="true"> / </span>Security</div>
            <h1 className="sc-title">Security</h1>
            <p className="sc-lede">Protecting the work behind the profile.</p>
            <p className="sc-dek">How Synaptiq decides who can see and change what, which outside services are involved, and what happens when something goes wrong. Each statement describes how the platform works today.</p>
            <dl className="sc-meta">
              <div><dt className="lp-mono">Last reviewed</dt><dd>{LEGAL.security.reviewed}</dd></div>
            </dl>
          </div>
        </header>

        <section className="sc-model" aria-labelledby="sc-model-h">
          <div className="lp-wrap">
            <h2 id="sc-model-h" className="lp-mono sc-model-label">The security model</h2>
            <ol className="sc-model-steps">
              {MODEL.map(([k, v], i) => (
                <li key={k}>
                  <span className="lp-mono sc-model-n">{num(i)}</span>
                  <span className="sc-model-k">{k}</span>
                  <span className="sc-model-v">{v}</span>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <div className="lp-wrap sc-body">
          <nav className="sc-index" aria-label="On this page">
            <div className="lp-mono sc-index-label">On this page</div>
            <ol>{SECTIONS.map((s, i) => <li key={s.id}><a href={`#${s.id}`}><span className="lp-mono">{num(i)}</span>{s.title}</a></li>)}</ol>
          </nav>
          <article className="sc-article" aria-labelledby="sc-article-h">
            <h2 id="sc-article-h" className="sc-sr">Security details</h2>
            {SECTIONS.map((s, i) => (
              <section key={s.id} id={s.id} className="sc-section" aria-labelledby={`${s.id}-h`}>
                <h3 id={`${s.id}-h`}><span className="lp-mono sc-num">{num(i)}</span>{s.title}</h3>
                {s.body}
              </section>
            ))}
            <nav className="sc-continue" aria-labelledby="sc-continue-h">
              <h2 id="sc-continue-h" className="lp-mono">Legal &amp; Trust</h2>
              <ul>
                {LEGAL_DOCS.map((d) => (
                  <li key={d.id}><Link to={d.path}><span className="sc-continue-title">{d.title}</span><span className="sc-continue-dek">{d.dek}</span></Link></li>
                ))}
              </ul>
            </nav>
          </article>
        </div>
      </div>
    </MarketingLayout>
  );
}

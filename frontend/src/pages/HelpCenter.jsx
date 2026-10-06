import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import { setPageSeo } from "../lib/seo";
import { openPreferences } from "../lib/cookieConsent";
import "../components/landing/landing.css";
import "./support.css";

/*
 * Help Center — answers to common questions, each matching how the product
 * works today. Paths in <Path> are real menu locations. No article counts,
 * no "most viewed" lists, no response-time promises.
 */
const Path = ({ children }) => <span className="sp-path">{children}</span>;

const GROUPS = [
  { id: "account", title: "Account and sign-in", items: [
    ["How do I create an account?", <>Sign-ups are paused while billing is set up. When they reopen, you'll sign up with your email or with ORCID, confirm you're 18 or older and accept the <Link to="/terms">Terms</Link>.</>],
    ["I forgot my password.", <>Choose <em>Forgot password</em> on the <Link to="/login">sign-in page</Link>. We email a single-use link that expires after 30 minutes. If it doesn't arrive, check your spam folder and try again.</>],
    ["How do I connect ORCID?", <>Open <Path>Academic Passport → Research</Path> and connect your ORCID iD. Your public works are imported, and the ORCID connection is marked as connected on your Passport.</>],
  ] },
  { id: "visibility", title: "Profile and visibility", items: [
    ["What's on my public research page?", <>Your name, affiliation, research interests and the academic sections you leave on. Projects, grants, collaborations and your email stay off unless you turn them on in <Path>Academic Passport → Portfolio</Path>.</>],
    ["How do I stop appearing in discovery?", <>In <Path>Network → Network Settings</Path>, turn off <em>Show my profile in researcher discovery</em>, or set your profile to <em>Private</em>. <Link to="/gdpr">Data Protection</Link> explains what each setting does.</>],
  ] },
  { id: "plans", title: "Plans and AI Credits", items: [
    ["What can I do on the Free plan?", <>Create your Academic Passport and public research page, connect ORCID and be found by Pro members. Messaging, projects, discovery tools and AI are on Pro and Pro Advanced. See <Link to="/pricing">Pricing</Link>.</>],
    ["Can I buy Pro now?", <>Not yet. Online purchase of paid plans isn't open; you can start on Free. Institutions can <Link to="/contact?topic=institution">contact us</Link> about institutional plans.</>],
    ["What are AI Credits?", <>They measure AI use. Each AI action has a fixed cost, shown before it runs, and failed actions return their credits. <Path>AI Usage</Path> lists what you've used. The <Link to="/ai-workspace">AI Workspace</Link> page has the details.</>],
  ] },
  { id: "data", title: "Your data", items: [
    ["How do I download my data?", <>Go to <Path>Settings → Privacy → Export my data</Path>. You get a structured JSON file of your account data; passwords and security tokens are never included.</>],
    ["How do I delete my account?", <>Go to <Path>Settings → Privacy → Delete my account</Path> and confirm with your password or a recent sign-in. What's deleted, what stays with people you shared it with, and what we must keep is in the <Link to="/privacy#deletion">Privacy Policy</Link>.</>],
    ["How do I change my cookie choices?", <>Use <button type="button" className="sp-linkbtn" onClick={openPreferences}>Cookie settings</button>, also in the site footer. Analytics stays off unless you allow it.</>],
  ] },
  { id: "security", title: "Security", items: [
    ["How do I report a security issue?", <>Use the <Link to="/contact?topic=security">contact form</Link> and choose the Security topic. The <Link to="/security">Security</Link> page explains what to include and what not to do.</>],
  ] },
];

export default function HelpCenter() {
  useEffect(() => setPageSeo({
    title: "Help Center | Synaptiq",
    description: "Answers about accounts, visibility, plans and AI Credits, your data and security on Synaptiq.",
    path: "/help-center",
  }), []);

  return (
    <MarketingLayout>
      <div className="lp sp">
        <header className="sp-head">
          <div className="lp-wrap">
            <div className="lp-mono sp-crumb"><b>Support</b><span aria-hidden="true"> / </span>Help Center</div>
            <h1 className="sp-title">Help Center</h1>
            <p className="sp-dek">Answers to the questions people ask most. If yours isn't here, <Link to="/contact?topic=support">ask us</Link>.</p>
          </div>
        </header>
        <div className="lp-wrap sp-body">
          {GROUPS.map((g) => (
            <section key={g.id} id={g.id} className="sp-section" aria-labelledby={`${g.id}-h`}>
              <h2 id={`${g.id}-h`} className="sp-h2">{g.title}</h2>
              <div className="sp-faq">
                {g.items.map(([q, a]) => (
                  <details key={q}>
                    <summary>{q}</summary>
                    <div className="sp-answer">{a}</div>
                  </details>
                ))}
              </div>
            </section>
          ))}
          <p className="sp-next">
            Still stuck? <Link to="/contact?topic=support">Contact us</Link> · <Link to="/status">System status</Link> · <Link to="/whats-new">What's New</Link>
          </p>
        </div>
      </div>
    </MarketingLayout>
  );
}

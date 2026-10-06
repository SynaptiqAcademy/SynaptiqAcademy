import React from "react";
import { Link } from "react-router-dom";
import { LegalLayout, LegalCallout, LegalOperator } from "../components/legal/LegalLayout";
import { LEGAL } from "../content/legal/meta";
import { openPreferences } from "../lib/cookieConsent";

/*
 * Data Protection (route /gdpr) — a guide to what members control, who can
 * see what, and their rights. It does not repeat the Privacy Policy: legal
 * bases, the provider table, retention periods and the deletion matrix live
 * there, and this page links to them. Every statement describes current
 * behaviour (see docs/privacy/).
 */
const P = LEGAL.contact.privacy;
const mail = <a href={`mailto:${P}`}>{P}</a>;
const Path = ({ children }) => <span className="lg-path">{children}</span>;

function Rows({ items, numbered }) {
  return (
    <ul className="lg-rows">
      {items.map(([term, def], i) => (
        <li key={term}>
          <div className="lg-rows-term">{numbered && <span className="lg-rows-n">{String(i + 1).padStart(2, "0")}</span>}{term}</div>
          <p className="lg-rows-def">{def}</p>
        </li>
      ))}
    </ul>
  );
}

const SECTIONS = [
  { id: "control", title: "What you control", body: (<>
    <p>These are the controls Synaptiq offers today. Not every kind of data has its own switch; where it doesn't, the rights in section 06 apply.</p>
    <Rows items={[
      ["Profile details", <>Edit or remove what your Academic Passport says about you, in <Path>Academic Passport</Path>. Fields you leave empty aren't shown.</>],
      ["Public research page", <>Choose which sections appear on your public page, in <Path>Academic Passport → Portfolio</Path>.</>],
      ["Discovery and visibility", <>Turn off <em>Show my profile in researcher discovery</em>, or set your profile to <em>Private</em>, in <Path>Network → Network Settings</Path>.</>],
      ["Analytics", <>Allow or refuse analytics, and change your mind at any time: <button type="button" className="lg-linkbtn" onClick={openPreferences}>Cookie settings</button>, also in the site footer and in <Path>Settings → Privacy</Path>.</>],
      ["Your data", <>Download a copy, or delete your account, in <Path>Settings → Privacy</Path> (section 05).</>],
    ]} />
    <p>Your plan isn't a privacy setting: a Free profile isn't hidden, and a paid plan doesn't make a profile more visible to the public. Only the settings above decide visibility.</p>
  </>) },
  { id: "visibility", title: "Who can see what", body: (<>
    <LegalCallout label="In practice">
      <p>Your profile and your research workspace follow different rules. Your profile is meant to be found, within your settings. Your work is visible only to the people you share it with.</p>
    </LegalCallout>
    <Rows items={[
      ["Public research page", <>Anyone with the link can see your name, affiliation, research interests and the academic sections you leave on (publications, impact, teaching, reputation, timeline). Projects, grants, collaborations and your email address are off unless you turn them on. Search engines are asked not to index these pages.</>],
      ["Researcher directory", <>Your name, photo, institution, department, country, career stage and research interests can appear in the researcher directory, which is visible without signing in.</>],
      ["Discovery and matching", <>Signed-in members can find you through discovery and suggestions. Choosing <em>Private</em> or turning off discovery removes you from the directory, discovery and your public page.</>],
      ["Shared work", <>Projects, workspaces, manuscripts, messages and comments are visible to the people you share them with. They keep access to what you shared, even after you leave or delete your account.</>],
      ["Private to you", <>Your email address (unless you make it public), password and sign-in details, AI conversations, unshared drafts and projects, billing details and cookie choices.</>],
    ]} />
    <p>Some Passport details are self-declared. Synaptiq marks connected and verified details, such as an ORCID record or a confirmed affiliation, separately; verification confirms only the fact that was checked.</p>
    <p>Institution administrators can see the members of their own institution. The <Link to="/privacy#public">Privacy Policy</Link> sets out exactly what other people can see.</p>
  </>) },
  { id: "private", title: "How private work stays private", body: (<>
    <p>Private content is available only to signed-in members you have given access to. Synaptiq staff access it only where needed to run the service, keep it safe or meet a legal obligation, and administrative actions are logged.</p>
    <p>The measures we use are described in the Privacy Policy's <Link to="/privacy#security">security section</Link>.</p>
  </>) },
  { id: "ai", title: "AI and your research content", body: (<>
    <p>AI features run only when you use them. To produce an answer, the material you give that feature (your question, the text or manuscript sections you choose, or project details it works with) is sent to an AI provider.</p>
    <ul>
      <li><strong>Anthropic</strong> (Claude) is the main provider. <strong>OpenAI</strong> answers if Anthropic is unavailable, and creates search embeddings for documents you add to a knowledge base. Both process data in the United States.</li>
      <li>Under their API terms they don't train their models on this content by default; they keep it for a limited period under their own policies. Synaptiq doesn't train AI models on your content.</li>
      <li>Your AI conversations stay in your account until you delete them or your account.</li>
    </ul>
    <p>Details are in the <Link to="/privacy#ai">Privacy Policy</Link> and the <Link to="/ai-policy">AI Usage Policy</Link>.</p>
  </>) },
  { id: "export-delete", title: "Export and deletion", body: (<>
    <h3>Export</h3>
    <p><Path>Settings → Privacy → Export my data</Path> downloads a structured JSON file of your account data: your profile, Terms acceptance, connections, projects, workspaces and manuscripts, publications, file details, messages you sent, AI conversations, requests, memberships, notifications, consent and billing records. Passwords and security tokens are never included. Large accounts are limited per section; for anything not included, write to {mail}.</p>
    <h3>Deleting your account</h3>
    <p><Path>Settings → Privacy → Delete my account</Path>, after confirming with your password or a recent sign-in.</p>
    <ul>
      <li>What only you could access is deleted: your profile, AI conversations, notes, requests, memberships, and projects or workspaces nobody else uses.</li>
      <li>What you shared stays with the people you shared it with, shown as "Deleted user"; shared spaces pass to another member.</li>
      <li>Some records are kept where the law or security requires it, such as billing records and security logs, until their periods end.</li>
    </ul>
    <h3>How long data is kept</h3>
    <p>Each kind of data has its own rule. Some expire automatically, some are kept while your account exists, and a few (for example messages sent through our contact form) don't yet have a fixed period and are kept only while needed. The <Link to="/privacy#retention">Privacy Policy</Link> lists them, and its <Link to="/privacy#deletion">deletion section</Link> gives the full detail.</p>
  </>) },
  { id: "rights", title: "Your rights", body: (<>
    <p>European data-protection law (the GDPR) gives you these rights. Some depend on why we process the data, so not every right applies the same way in every case; we'll explain if one doesn't.</p>
    <Rows numbered items={[
      ["Access", "Ask what personal data we hold about you and how we use it, and get a copy."],
      ["Rectification", "Have inaccurate or incomplete data corrected. Most of it you can edit yourself."],
      ["Erasure", "Have your data deleted, apart from what we must keep by law."],
      ["Restriction", "Ask us to limit use of your data, for example while a correction is checked."],
      ["Objection", "Object to processing based on our legitimate interests, such as showing your profile in suggestions."],
      ["Portability", "Receive data you gave us in a structured, machine-readable format."],
      ["Withdraw consent", "Where we rely on consent, such as analytics, withdraw it at any time; earlier processing stays lawful."],
      ["Complain", <>Complain to a data protection authority: in Romania, the {LEGAL.authority.name} (<a href={LEGAL.authority.url} target="_blank" rel="noopener noreferrer">{LEGAL.authority.url.replace("https://", "")}</a>), or the authority where you live or work.</>],
    ]} />
  </>) },
  { id: "participants", title: "Research participant data", body: (<>
    <LegalCallout label="Research data">
      <p>Synaptiq isn't designed for directly identifiable data about research participants or patients. Don't upload it, or special categories of data such as health data, unless you have a lawful basis and permission to do so.</p>
    </LegalCallout>
    <p>Research materials can contain sensitive personal data. You remain responsible for ethics approval, participant consent and your institution's rules; Synaptiq provides no ethics approval and no participant-consent tools. See <Link to="/terms#research">Research content and ethics</Link> in the Terms.</p>
  </>) },
  { id: "providers", title: "Service providers and transfers", body: (<>
    <p>Other companies process data on our behalf, each for a specific job:</p>
    <ul>
      <li><strong>Infrastructure:</strong> application hosting, the database and website delivery.</li>
      <li><strong>Email:</strong> sending account and notification emails.</li>
      <li><strong>AI services:</strong> the AI features in section 04.</li>
      <li><strong>Analytics:</strong> usage statistics, only if you allow them.</li>
      <li><strong>Research metadata:</strong> public bibliographic sources we read from.</li>
      <li><strong>Payments:</strong> once online payments open.</li>
    </ul>
    <p>Our application servers and AI providers are in the United States, so your data is transferred outside the European Economic Area. The <Link to="/privacy#providers">Privacy Policy</Link> names each provider and where it processes data, and its <Link to="/privacy#transfers">transfers section</Link> explains the safeguards.</p>
  </>) },
  { id: "contact", title: "Using your rights", body: (<>
    <p>Write to {mail} for anything you can't do in your account. We reply within one month; for complex requests this can be extended by up to two further months, and we'll tell you within the first month. We may ask you to confirm your identity. Requests are free unless they are manifestly unfounded or excessive.</p>
    <h3>Who is responsible</h3>
    <LegalOperator />
  </>) },
];

export default function GDPR() {
  return (
    <LegalLayout
      doc="dataProtection"
      tocLabel="On this page"
      seo={{ title: "Data Protection | Synaptiq", description: "What you control on Synaptiq, who can see what, and your rights under European data-protection law.", path: "/gdpr" }}
      sections={SECTIONS}
    />
  );
}

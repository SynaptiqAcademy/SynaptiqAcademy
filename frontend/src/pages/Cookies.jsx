import React from "react";
import { Link } from "react-router-dom";
import { LegalLayout, LegalTable } from "../components/legal/LegalLayout";
import { LEGAL } from "../content/legal/meta";
import { STORAGE_INVENTORY } from "../content/legal/cookies";
import { openPreferences } from "../lib/cookieConsent";

const P = LEGAL.contact.privacy;
const rows = (cat) => STORAGE_INVENTORY.filter((i) => i.category === cat)
  .map((i) => [<code key="n">{i.name}</code>, i.type, i.provider, i.purpose, i.duration]);
const HEAD = ["Name", "Type", "Provider", "Purpose", "Duration"];

const SECTIONS = [
  { id: "scope", title: "What this policy covers", body: (<>
    <p>This policy explains the cookies and similar technologies, such as your browser's local storage, that Synaptiq uses on synaptiq.academy and in the application. It sits alongside the <Link to="/privacy">Privacy Policy</Link>.</p>
  </>) },
  { id: "what", title: "Cookies and local storage", body: (<>
    <p>A cookie is a small file a website stores in your browser and reads back later. Local storage does a similar job but stays in your browser and isn't sent to our servers automatically. The law treats both the same way: we may use them without asking only when they are strictly necessary for something you asked for. Anything else needs your consent.</p>
  </>) },
  { id: "necessary", title: "Strictly necessary", body: (<>
    <p>These keep you signed in and secure, remember your cookie choice, or store something you asked the app to remember, such as a pinned conversation. They don't need consent and can't be switched off in Synaptiq.</p>
    <LegalTable caption="Strictly necessary" head={HEAD} rows={rows("necessary")} />
  </>) },
  { id: "analytics", title: "Analytics", body: (<>
    <p>If you allow analytics, we use PostHog to count which pages and features are used. Nothing loads, and nothing is stored, until you allow it.</p>
    <ul>
      <li>We send named events and page views only. Automatic click capture and session recording are switched off.</li>
      <li>We don't send the content of your research, messages, AI requests or search text.</li>
      <li>You are not identified to PostHog by name or email. PostHog processes data in the United States and receives your IP address as part of each request.</li>
    </ul>
    <LegalTable caption="Analytics (with your consent)" head={HEAD} rows={rows("analytics")} />
    <p>We don't use advertising or marketing cookies, and there are no social media embeds or tracking pixels.</p>
  </>) },
  { id: "third-party", title: "Fonts", body: (<>
    <p>Our typefaces are served from Synaptiq's own website. Loading a page doesn't send a request to Google Fonts or any other font service.</p>
  </>) },
  { id: "choice", title: "Changing your choice", body: (<>
    <p>When you first visit we ask whether you allow analytics, with equal choices to allow or reject it. You can change your mind at any time:</p>
    <ul>
      <li><button type="button" className="lg-linkbtn" onClick={openPreferences}>Open cookie settings</button>, also available as "Cookie settings" in the footer;</li>
      <li>if you're signed in, in Settings → Privacy.</li>
    </ul>
    <p>Withdrawing consent stops analytics immediately. Your choice is kept for 12 months, after which we ask again. We record each choice (the choice, a random consent identifier, your browser type and a one-way hash of your IP address) so we can show what was agreed.</p>
  </>) },
  { id: "browser", title: "Browser controls", body: (<>
    <p>You can also block or delete cookies and site data in your browser settings. If you block strictly necessary cookies, you won't be able to sign in.</p>
  </>) },
  { id: "changes", title: "Changes to this policy", body: (<>
    <p>If we start using a new kind of technology that needs consent, we'll update this policy and ask you again before using it.</p>
  </>) },
  { id: "contact", title: "Contact", body: (<>
    <p>Questions: <a href={`mailto:${P}`}>{P}</a>.</p>
  </>) },
];

export default function Cookies() {
  return (
    <LegalLayout
      kind="Cookies"
      title="Cookie Policy"
      updated={LEGAL.cookies.updated}
      version={LEGAL.cookies.version}
      seo={{ title: "Cookie Policy | Synaptiq", description: "The cookies and browser storage Synaptiq uses, why, for how long, and how to change your choice.", path: "/cookies" }}
      summary={(<p>We use cookies to keep you signed in and secure. Analytics runs only if you allow it. There are no advertising cookies or third-party trackers.</p>)}
      sections={SECTIONS}
    />
  );
}

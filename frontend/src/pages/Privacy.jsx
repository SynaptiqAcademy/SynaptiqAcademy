import React from "react";
import { Link } from "react-router-dom";
import { LegalLayout, LegalTable } from "../components/legal/LegalLayout";
import { LEGAL, OPERATOR_PENDING } from "../content/legal/meta";

const P = LEGAL.contact.privacy;
const mail = <a href={`mailto:${P}`}>{P}</a>;

const SECTIONS = [
  { id: "about", title: "About this policy", body: (<>
    <p>This policy explains how personal data is handled when you use Synaptiq, the research collaboration platform at synaptiq.academy, including the website, the application and its emails.</p>
    <p>It covers people who visit the site, people with an account, and people whose information appears on Synaptiq because someone else added it (for example, a co-author named on a manuscript).</p>
  </>) },
  { id: "controller", title: "Who is responsible for your data", body: (<>
    <p>The controller of the personal data described here is the operator of Synaptiq.</p>
    <p>{LEGAL.operator ? `${LEGAL.operator.name}, ${LEGAL.operator.address}, ${LEGAL.operator.registration}.` : OPERATOR_PENDING}</p>
    <p>For anything about your personal data, write to {mail}. Synaptiq has not appointed a Data Protection Officer.</p>
  </>) },
  { id: "data", title: "What we collect", body: (<>
    <h3>Account</h3>
    <p>Email address, name, a hashed password (we never store it in readable form), sign-in sessions, and whether your email is verified.</p>
    <h3>Academic Passport and profile</h3>
    <p>What you choose to add: academic and professional role, institution and department, country, languages, biography, research areas, interests and keywords, methods and software, professional expertise, teaching areas, what you're open to, and links to other profiles.</p>
    <h3>Research record</h3>
    <p>Your ORCID iD and, if you connect ORCID, the publication metadata imported from it, plus publication metadata from OpenAlex and Crossref (titles, authors, venues, DOIs, citation counts).</p>
    <h3>Your work in Synaptiq</h3>
    <p>Research questions and Research Needs, collaboration requests, messages, projects, workspaces, tasks, notes, manuscripts, uploaded files, grant applications, teaching material, and your requests to AI features with the responses.</p>
    <h3>Institutions</h3>
    <p>Membership requests and their status, the role you hold, departments you belong to, and any evidence link or note you give when asking to join.</p>
    <h3>Billing</h3>
    <p>Your plan, subscription status, AI Credit balance and usage, and the identifiers Stripe returns for your customer and subscription. Card details are handled by Stripe and never reach Synaptiq.</p>
    <h3>Technical and security data</h3>
    <p>IP address, browser and device type, sign-in and security events, and request logs. With your permission only, anonymous usage statistics (see <a href="#cookies">Cookies and analytics</a>).</p>
    <h3>Messages to us</h3>
    <p>What you send through the contact form or by email: your name, email, organisation and role if given, and the message.</p>
  </>) },
  { id: "purposes", title: "Why we use it, and on what legal basis", body: (<>
    <LegalTable caption="Purposes and legal bases (GDPR Article 6)" head={["Purpose", "Legal basis"]} rows={[
      ["Creating and running your account, and providing the features you use", "Contract (Art. 6(1)(b))"],
      ["Showing your profile to other members and in discovery, according to your settings", "Contract (Art. 6(1)(b))"],
      ["Importing your record from ORCID when you connect it", "Contract (Art. 6(1)(b))"],
      ["Sending account, security, collaboration and billing emails", "Contract (Art. 6(1)(b))"],
      ["Keeping Synaptiq secure: rate limits, fraud and abuse prevention, security logs", "Legitimate interests (Art. 6(1)(f))"],
      ["Answering messages you send us", "Legitimate interests (Art. 6(1)(f)), or steps before a contract"],
      ["Anonymous usage statistics", "Consent (Art. 6(1)(a)), only if you allow analytics"],
      ["Keeping billing records and responding to lawful requests", "Legal obligation (Art. 6(1)(c))"],
    ]} />
    <p>Where we rely on legitimate interests, you can object (see <a href="#rights">Your rights</a>).</p>
  </>) },
  { id: "public", title: "What other people can see", body: (<>
    <p>Your Academic Passport is shown to other signed-in members, and on your public research page, unless you make your profile private. Fields you leave empty are not shown.</p>
    <ul>
      <li><strong>Discovery.</strong> Members on Pro and Pro Advanced can find profiles in researcher discovery and matching, including profiles of Free members. You can hide yourself from discovery in your network settings, or make your profile private.</li>
      <li><strong>Search engines.</strong> Public research pages are not currently offered to search engines: our robots file asks them not to index profile pages.</li>
      <li><strong>Not shown to others:</strong> your email address (except to institution admins, see <a href="#institutions">Institutions</a>, or if you choose to show it on your public research page), your messages, private projects and workspaces, your AI requests, your billing details, and any membership evidence.</li>
    </ul>
    <p>Blocking someone hides each of you from the other in discovery and stops them sending you collaboration requests.</p>
  </>) },
  { id: "external", title: "ORCID and other research sources", body: (<>
    <p>You can type your ORCID iD into your profile, or connect your ORCID account. Only a connected account is marked as connected: a typed iD is shown as self-declared.</p>
    <p>When you connect ORCID, ORCID tells us your iD and lets us read the public parts of your ORCID record, which we use to import your publications. You can disconnect ORCID at any time; imported publications stay on your Passport until you remove them.</p>
    <p>We also read public bibliographic metadata from OpenAlex and Crossref to complete publication records and to power journal, conference and grant discovery. That metadata belongs to its sources; we use it to describe works, not to claim ownership of it.</p>
  </>) },
  { id: "matching", title: "Discovery and matching", body: (<>
    <p>When a member searches for people or describes a Research Need, Synaptiq compares the words in the request with fields in eligible profiles (research areas, interests and keywords, methods and software, professional expertise and role, publication titles) and shows matching people with the evidence for each match.</p>
    <p>This is rule-based matching, not an AI model. It organises and explains search results; it does not make decisions about you that have legal or similarly significant effects, and every contact is a choice made by a person. You can stop appearing in discovery at any time.</p>
  </>) },
  { id: "collaboration", title: "Collaboration and messages", body: (<>
    <p>Collaboration requests and messages are visible to their participants. Messages are stored on our servers, not end-to-end encrypted.</p>
    <p>Synaptiq staff do not read your messages in the course of running the service. Administrators can see conversation metadata (who took part, when, how many messages) for security and abuse handling. People with technical access to our database could access content; that access is limited to what is needed to operate, secure and repair the service, or to comply with the law.</p>
  </>) },
  { id: "content", title: "Projects, manuscripts and files", body: (<>
    <p>Projects, workspaces and manuscripts are visible to the members you add. When you share something, the people you shared it with keep access to it, including after you leave a project or delete your account.</p>
    <p>If you upload research material that contains personal data about other people, such as research participants, you are responsible for having a lawful basis and any ethics approval for doing so (see the <Link to="/terms#research">Terms</Link>). Please don't upload identifiable participant data or special categories of data (for example health data) unless you need to and are permitted to. We store this material to provide the service to you; if your institution needs a data processing agreement for it, contact us.</p>
  </>) },
  { id: "ai", title: "AI features", body: (<>
    <p>AI features run only when you use them. The material you choose is sent to an AI provider to produce the response: for example the question you write, the manuscript sections you name, project or workspace details, or the text you paste.</p>
    <ul>
      <li><strong>Providers.</strong> Anthropic (Claude) is our main provider; OpenAI is used if Anthropic is unavailable and to create search embeddings for documents you add to a knowledge base. Both process data in the United States.</li>
      <li><strong>Training.</strong> Under these providers' API terms, content sent through their APIs is not used to train their models by default. Synaptiq does not train AI models on your content.</li>
      <li><strong>What we keep.</strong> Your AI conversations and results are saved in your account so you can return to them; you can delete conversations. Our AI usage records keep sizes, costs and timings, not the text of your request.</li>
    </ul>
    <p>Avoid putting personal or confidential details about other people into AI requests unless they are needed.</p>
  </>) },
  { id: "institutions", title: "Institutions", body: (<>
    <p>Typing an institution into your profile does not make you a member of it on Synaptiq. Membership exists only when you are approved: through your institutional email domain, by accepting an invitation, or after an institution admin reviews your request.</p>
    <p>Members of an institution can see each other's names, research areas and department rosters. Institution admins can also see members' email addresses, membership requests with any evidence you gave, and a log of admin actions. Membership does not give anyone access to your messages, private projects, manuscripts or AI conversations. When membership ends, institutional access ends; your Passport stays with you.</p>
  </>) },
  { id: "verification", title: "Verification", body: (<>
    <p>Verification confirms specific facts, such as an institutional affiliation through an email at that institution or an admin's review. It does not verify degrees, licences or professional competence. Evidence you give is seen only by the people reviewing it and is never shown on your profile.</p>
  </>) },
  { id: "billing", title: "Payments", body: (<>
    <p>Online purchase of paid plans is not open yet. When it opens, payments will be handled by Stripe, which acts as an independent controller for payment processing. Synaptiq receives your plan, subscription and payment status and Stripe's identifiers, never your full card details.</p>
  </>) },
  { id: "emails", title: "Emails", body: (<>
    <p>We send emails that are part of the service: verifying your address, security and sign-in notices, collaboration and institution invitations, and billing messages. You can change which notification emails you receive in your settings. We do not currently send marketing email.</p>
  </>) },
  { id: "cookies", title: "Cookies and analytics", body: (<>
    <p>We use strictly necessary cookies to keep you signed in and secure. Analytics (PostHog, United States) runs only if you allow it, sends only named events and page views, and never includes the content of your research, messages or AI requests. See the <Link to="/cookies">Cookie Policy</Link>, and change your choice at any time from "Cookie settings" in the footer.</p>
  </>) },
  { id: "providers", title: "Who processes data for us", body: (<>
    <LegalTable caption="Service providers" head={["Provider", "What for", "Where"]} rows={[
      ["Railway", "Application servers", "United States"],
      ["MongoDB Atlas", "Database", "Region being confirmed; may be outside the EEA"],
      ["Vercel", "Website delivery", "Global network"],
      ["Resend", "Sending email", "United States"],
      ["Anthropic", "AI features", "United States"],
      ["OpenAI", "AI when Claude is unavailable, and knowledge-base search embeddings", "United States"],
      ["PostHog", "Analytics, only with your consent", "United States"],
      ["Stripe", "Payments, once open (independent controller)", "EU and United States"],
      ["ORCID", "Connecting your ORCID record (at your request)", "Independent organisation"],
    ]} />
    <p>We also read public metadata from OpenAlex and Crossref; we don't send them your personal data.</p>
  </>) },
  { id: "transfers", title: "Transfers outside the EEA", body: (<>
    <p>Some providers above process data in the United States. Those transfers rely on the safeguards in each provider's data-processing terms: the EU–U.S. Data Privacy Framework where the provider is certified, or the European Commission's Standard Contractual Clauses. You can ask us for details at {mail}.</p>
  </>) },
  { id: "retention", title: "How long we keep data", body: (<>
    <LegalTable caption="Retention" head={["Data", "How long"]} rows={[
      ["Account and profile", "While your account exists; removed or anonymised when you delete it"],
      ["Messages, projects, manuscripts, files", "Until you or their owner delete them. Content shared with others stays available to them after you delete your account"],
      ["AI conversations and results", "Until you delete them or your account"],
      ["Sign-in sessions and security tokens", "Expire automatically (sessions up to 14 days)"],
      ["Security event logs", "1 year"],
      ["Records of administrative and account actions (for example, that an account was deleted)", "90 days"],
      ["Log of emails we send you (address, subject, delivery status)", "90 days, or until you delete your account"],
      ["Read notifications", "90 days"],
      ["Cookie choices not linked to an account", "2 years"],
      ["Cookie choices linked to your account", "Until you delete your account"],
      ["Email verification and password-reset links", "Expire automatically (24 hours and 30 minutes)"],
      ["Billing records", "As long as Romanian tax and accounting law requires"],
      ["Messages sent to us through the contact form, and billing-related audit records", "No automatic deletion period is set yet; kept while needed for their purpose and deleted on request where the law allows"],
      ["Backups", "Overwritten on our database provider's backup cycle"],
    ]} />
  </>) },
  { id: "deletion", title: "Deleting your account", body: (<>
    <p>You can delete your account in Settings → Privacy. We ask for your password, or, if you sign in with ORCID rather than a password, a sign-in within the last 10 minutes. You're signed out everywhere straight away. Then:</p>
    <ul>
      <li><strong>Deleted:</strong> your profile, AI conversations and knowledge-base documents, saved searches, goals and notes, requests and invitations, memberships, notifications and cookie choices; and projects, workspaces and manuscripts that only you can access, with their files.</li>
      <li><strong>Kept for others:</strong> projects, workspaces and manuscripts you share pass to another member or co-author. Messages you sent, comments and contributions stay with the people you shared them with, shown as "Deleted user".</li>
      <li><strong>Kept because the law or security requires it:</strong> billing records, as long as tax and accounting law requires; security logs and a record that the account was deleted (without your name or email) until their periods above end.</li>
    </ul>
    <p>Your account record remains only as an anonymous placeholder, so shared content still works. Deleted data disappears from backups as they are overwritten on our database provider's backup cycle.</p>
  </>) },
  { id: "rights", title: "Your rights", body: (<>
    <p>Under the GDPR you can ask to access your data, correct it, delete it, restrict or object to its use, and receive it in a portable format. Where we rely on consent, you can withdraw it at any time.</p>
    <ul>
      <li><strong>Yourself:</strong> edit your Passport; change visibility and discovery settings; download a copy of your data in Settings → Privacy → Export my data; delete your account there too; change cookie choices from the footer.</li>
      <li><strong>By email:</strong> anything else, at {mail}. We answer within one month, as the GDPR requires, and may ask you to confirm your identity.</li>
    </ul>
    <p>You can also complain to a data protection authority. In Romania that is the {LEGAL.authority.name}, <a href={LEGAL.authority.url} rel="noopener noreferrer" target="_blank">{LEGAL.authority.url.replace("https://", "")}</a>; you may also go to the authority where you live or work.</p>
  </>) },
  { id: "age", title: "Age", body: (<>
    <p>Synaptiq is for people aged 18 and over. We don't knowingly collect data from younger people; if you believe we have, write to {mail} and we will delete it.</p>
  </>) },
  { id: "security", title: "Security", body: (<>
    <p>We use technical and organisational measures appropriate to the risk, including encrypted connections, hashed passwords, short-lived sessions, access controls and security logging. No system is perfectly secure. If a personal data breach is likely to put your rights at risk, we will notify the supervisory authority and, where the GDPR requires, you.</p>
  </>) },
  { id: "changes", title: "Changes to this policy", body: (<>
    <p>When we change this policy we update the date and version above. For material changes we will tell signed-in members in the product before the change takes effect.</p>
  </>) },
  { id: "contact", title: "Contact", body: (<>
    <p>Privacy questions and requests: {mail}.</p>
  </>) },
];

export default function Privacy() {
  return (
    <LegalLayout
      doc="privacy"
      seo={{ title: "Privacy Policy | Synaptiq", description: "How Synaptiq handles personal data: what we collect, why, who processes it, how long we keep it, and your rights.", path: "/privacy" }}
      summary={(<>
        <p>We use your account and research-profile information to run Synaptiq, connect your work with people and projects, provide the features you use, keep the service secure, and handle paid plans when they open.</p>
        <ul>
          <li>Your Passport is visible to other members unless you make it private, and you can hide from discovery.</li>
          <li>Content you send to AI features goes to our AI providers to produce the answer.</li>
          <li>Analytics runs only if you allow it, and never includes your research content.</li>
          <li>You can export your data and delete your account in Settings → Privacy.</li>
        </ul>
      </>)}
      sections={SECTIONS}
    />
  );
}

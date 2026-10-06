import React from "react";
import { Link } from "react-router-dom";
import { LegalLayout } from "../components/legal/LegalLayout";
import { LEGAL, OPERATOR_PENDING } from "../content/legal/meta";

const C = LEGAL.contact.general;
const P = LEGAL.contact.privacy;
const mail = (a) => <a href={`mailto:${a}`}>{a}</a>;

const SECTIONS = [
  { id: "about", title: "About these terms", body: (<>
    <p>These terms are the agreement between you and the operator of Synaptiq ("we") for using synaptiq.academy and its application. {LEGAL.operator ? `The operator is ${LEGAL.operator.name}, ${LEGAL.operator.address}.` : OPERATOR_PENDING}</p>
    <p>By creating an account you accept these terms. The <Link to="/privacy">Privacy Policy</Link> explains how we handle personal data.</p>
  </>) },
  { id: "eligibility", title: "Who can use Synaptiq", body: (<>
    <p>You must be at least 18. If you use Synaptiq for an organisation, you confirm you may act for it.</p>
  </>) },
  { id: "accounts", title: "Your account", body: (<>
    <p>Keep your sign-in details secure and tell us at {mail(C)} if you think someone else has accessed your account. You are responsible for what happens under your account unless it was used without your fault.</p>
  </>) },
  { id: "identity", title: "Academic and professional identity", body: (<>
    <p>What you put on your Academic Passport must be true and yours: your name, roles, institution, credentials, publications, authorship and ORCID iD. Most of it is self-declared; Synaptiq marks connected and verified details separately and does not verify everything. Verification confirms only the specific fact checked, such as an institutional affiliation.</p>
  </>) },
  { id: "content", title: "Your content", body: (<>
    <p>You keep the rights in what you create and upload: research questions, manuscripts, files, messages, projects and profile content. Synaptiq does not own it.</p>
    <p>You give us a non-exclusive, worldwide, royalty-free licence to host, store, copy, process, format and display your content only as needed to run Synaptiq for you and for the people you share it with, including showing your public profile according to your settings. The licence ends when the content is deleted, except for copies others still have access to because you shared them, and for backups until they are overwritten.</p>
    <p>You confirm you have the rights to everything you upload.</p>
  </>) },
  { id: "research", title: "Research content and ethics", body: (<>
    <p>You are responsible for the research you carry out and the material you put into Synaptiq, including ethics approvals, participant consent, data protection for research participants, and your institution's rules. Synaptiq does not give ethics approval.</p>
    <p>Do not upload identifiable personal data about research participants, or special categories of data such as health data, unless you have a lawful basis and permission to do so. Synaptiq is not a medical, legal or financial adviser, and nothing on it is official advice from a government or other authority.</p>
  </>) },
  { id: "collaboration", title: "Collaboration", body: (<>
    <p>Suggestions and matches indicate possible relevance; they do not guarantee that someone is suitable. Accepting an invitation does not create employment, a partnership or any contract with Synaptiq.</p>
    <p>Synaptiq is not a party to your collaborations. Authorship, contribution credit, ownership of results, inventorship and intellectual property between collaborators are for you, your collaborators and your institutions to agree.</p>
    <p>Synaptiq doesn't keep ideas confidential beyond the sharing settings you choose, and placing an idea on Synaptiq does not protect it legally.</p>
  </>) },
  { id: "ai", title: "AI features", body: (<>
    <p>Some features use AI, and they are labelled as such. AI output can be wrong, incomplete or unoriginal, and can contain incorrect citations. Review it before you rely on it. It does not replace your judgment and does not make a manuscript, grant application or study valid, accepted or funded.</p>
    <p>You are responsible for how you use AI output, including disclosing AI assistance where your journal, funder or institution requires it.</p>
  </>) },
  { id: "integrity", title: "Academic integrity", body: (<>
    <p>Do not use Synaptiq to fabricate or falsify data or citations, plagiarise, misrepresent authorship or credentials, impersonate someone, claim an affiliation you don't have, or manipulate peer review.</p>
  </>) },
  { id: "use", title: "Acceptable use", body: (<>
    <p>Do not:</p>
    <ul>
      <li>access accounts or data you're not allowed to, or get around access controls, plan limits or AI Credit metering;</li>
      <li>send spam or unsolicited bulk requests, or harass anyone;</li>
      <li>upload malware or attack, overload or probe the service;</li>
      <li>create accounts automatically, or collect other members' data by scraping or automated means;</li>
      <li>post unlawful content, or content that infringes someone's rights or privacy.</li>
    </ul>
    <p>Search engines may index our public pages as our robots file allows.</p>
    <p>To report content you believe is illegal, write to {mail(C)} with the link and the reason. We will review it and tell you what we decided.</p>
  </>) },
  { id: "ip", title: "Synaptiq's rights", body: (<>
    <p>Synaptiq's software, design, name and documentation belong to the operator or its licensors, except open-source components under their own licences and bibliographic metadata, which belongs to its sources. You may use Synaptiq as these terms allow; nothing else is licensed to you.</p>
  </>) },
  { id: "third-party", title: "Other services", body: (<>
    <p>Some features rely on other services, such as ORCID, OpenAlex, Crossref, AI providers and Stripe. Their terms apply to your use of them. We aren't responsible for their content or availability.</p>
  </>) },
  { id: "plans", title: "Plans", body: (<>
    <p>Synaptiq has a Free plan and two paid individual plans, Pro and Pro Advanced. What each includes and costs is on the <Link to="/pricing">Pricing page</Link>. Institutional plans are agreed separately with organisations, under their own agreement.</p>
    <p>Online purchase of paid plans is not open yet. The sections below on AI Credits, billing, changing plans, cancelling and withdrawal apply once it opens.</p>
  </>) },
  { id: "credits", title: "AI Credits", body: (<>
    <p>AI Credits measure use of AI features. They are not money, have no cash value, can't be transferred or exchanged, and are used only on Synaptiq.</p>
    <ul>
      <li>Each AI action uses a fixed number of credits, shown before it runs. If an action fails, its credits are returned.</li>
      <li>Paid plans include a monthly allowance. It renews at the start of each billing period; unused monthly credits don't carry over.</li>
      <li>Credits bought as a pack don't expire, are used after your monthly credits, and can be used only while you have a paid plan.</li>
      <li>If you delete your account, unused credits are lost.</li>
    </ul>
  </>) },
  { id: "billing", title: "Billing and renewal", body: (<>
    <p>Paid plans are monthly subscriptions paid in advance through Stripe. They renew automatically each month until you cancel. The price you pay is the one shown at checkout.</p>
    <p>If we change the price of your plan, we will tell you at least 30 days before the next billing period it applies to; you can cancel before then.</p>
    <p>If a payment fails, your plan continues while the payment is retried. If it still can't be collected, your account moves to the Free plan's features until it is.</p>
  </>) },
  { id: "changes-plan", title: "Changing plans", body: (<>
    <p>Moving up from Pro to Pro Advanced takes effect once the payment is confirmed and is charged pro rata. Moving down is credited pro rata on your next invoice. If you move to a plan with lower limits, content above those limits becomes read-only; nothing is deleted.</p>
  </>) },
  { id: "cancellation", title: "Cancelling", body: (<>
    <p>You can cancel at any time in your account. Your plan continues to the end of the period you've paid for and then moves to Free. Projects and workspaces then become read-only, and purchased credits stay on your account for when you're on a paid plan again.</p>
  </>) },
  { id: "withdrawal", title: "Your right of withdrawal", body: (<>
    <p>If you are a consumer in the EU, you have the right to withdraw from a paid plan within 14 days of buying it, without giving a reason, by writing to {mail(C)}.</p>
    <p>If you ask us to start the service during those 14 days and then withdraw, you pay only for the service provided up to the point you told us, in proportion to the full price. Where the law allows the right to end once a credit pack has been used with your agreement, we will ask for that agreement at checkout.</p>
    <p>This doesn't limit any other rights you have under consumer law.</p>
  </>) },
  { id: "suspension", title: "Suspension and termination", body: (<>
    <p>We may suspend or close an account, or remove content, if it poses a security risk, involves fraud, breaks these terms seriously or repeatedly, is unlawful, or if we are required to by law. Where possible and lawful we will tell you first, explain why, and give you the chance to respond or export your data.</p>
    <p>You can close your account at any time in Settings → Privacy. What happens to your data is described in the <Link to="/privacy#deletion">Privacy Policy</Link>.</p>
  </>) },
  { id: "service", title: "Changes and availability", body: (<>
    <p>Synaptiq is developing and features may change. If we remove something central to a paid plan you're on, we'll tell you in advance and you can cancel. We work to keep Synaptiq available but don't promise it will always be uninterrupted or error-free.</p>
  </>) },
  { id: "liability", title: "Liability", body: (<>
    <p>We are responsible for loss we cause by breaking these terms where that loss was foreseeable. We are not responsible for loss that wasn't foreseeable, for business losses if you use Synaptiq for a business, or for decisions you make based on content or AI output on Synaptiq.</p>
    <p>Nothing in these terms limits liability that can't be limited by law, including for death or personal injury caused by negligence, for fraud, for gross negligence or wilful misconduct, or your rights as a consumer.</p>
  </>) },
  { id: "law", title: "Law and disputes", body: (<>
    <p>These terms are governed by Romanian law. If you are a consumer, you keep the protection of the mandatory laws of the country where you live, and you can bring a claim in the courts there or in Romania.</p>
    <p>Please contact us first at {mail(C)} so we can try to resolve the issue.</p>
  </>) },
  { id: "changes", title: "Changes to these terms", body: (<>
    <p>When we change these terms we update the date and version above. For material changes we will tell you in the product at least 30 days before they take effect. If you don't agree, you can close your account before then.</p>
  </>) },
  { id: "contact", title: "Contact", body: (<>
    <p>Questions about these terms: {mail(C)}. Personal data: {mail(P)}.</p>
  </>) },
];

export default function Terms() {
  return (
    <LegalLayout
      kind="Terms"
      title="Terms of Service"
      updated={LEGAL.terms.updated}
      version={LEGAL.terms.version}
      seo={{ title: "Terms of Service | Synaptiq", description: "The agreement for using Synaptiq: accounts, your content, AI features, academic integrity, plans, AI Credits, cancellation and your rights.", path: "/terms" }}
      summary={(<>
        <ul>
          <li>You keep the rights in your content. We use it only to run Synaptiq for you and the people you share it with.</li>
          <li>Synaptiq doesn't decide authorship or ownership between collaborators. You and your institutions do.</li>
          <li>AI output can be wrong. Review it; you're responsible for how you use it.</li>
          <li>Paid plans are monthly, renew until cancelled, and can be cancelled any time. EU consumers have a 14-day right of withdrawal.</li>
        </ul>
      </>)}
      sections={SECTIONS}
    />
  );
}

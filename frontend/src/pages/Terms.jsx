import React from "react";
import { Link } from "react-router-dom";
import { LegalLayout, Section } from "./legal/LegalLayout";

const SECTIONS = [
  { id: "acceptance",     label: "1. Acceptance" },
  { id: "eligibility",    label: "2. Eligibility & Accounts" },
  { id: "plans",          label: "3. Plans & Credits" },
  { id: "subscriptions",  label: "4. Subscriptions & Billing" },
  { id: "refunds",        label: "5. Refunds" },
  { id: "credits",        label: "6. Research Credits" },
  { id: "acceptable-use", label: "7. Acceptable Use" },
  { id: "ip",             label: "8. Intellectual Property" },
  { id: "ai-content",     label: "9. AI-Generated Content" },
  { id: "collaboration",  label: "10. Collaboration" },
  { id: "repository",     label: "11. Repository & Files" },
  { id: "availability",   label: "12. Service Availability" },
  { id: "liability",      label: "13. Limitation of Liability" },
  { id: "termination",    label: "14. Termination" },
  { id: "institution",    label: "15. Institutional Accounts" },
  { id: "governing-law",  label: "16. Governing Law" },
  { id: "general",        label: "17. General Provisions" },
];

export default function Terms() {
  React.useEffect(() => {
    document.title = "Terms of Service — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  return (
    <LegalLayout
      eyebrow="Legal"
      title="Terms of Service"
      subtitle="Platform rules, subscription terms, Research Credits, intellectual property, and your obligations as a user."
      lastUpdated="29 June 2026"
      readingTime="10 min"
      version="v1.4"
      sections={SECTIONS}
    >
      <Section id="acceptance" title="1. Acceptance of Terms">
        <p>By accessing or using SYNAPTIQ (the &ldquo;Service&rdquo;, &ldquo;Platform&rdquo;), you agree to be bound by these Terms of Service (&ldquo;Terms&rdquo;). If you do not agree, do not use the Service.</p>
        <p className="mt-3">These Terms constitute a binding agreement between you and the entity operating SYNAPTIQ (&ldquo;we&rdquo;, &ldquo;us&rdquo;, &ldquo;our&rdquo;). By creating an account, linking ORCID, or using any feature of the Platform, you confirm that you have read, understood, and accepted these Terms.</p>
      </Section>

      <Section id="eligibility" title="2. Eligibility & Accounts">
        <p><strong>Eligibility.</strong> You must be at least 18 years old and capable of entering a binding contract. SYNAPTIQ is not directed at users under 18. We may require proof of academic or professional affiliation for certain account types.</p>
        <p className="mt-3"><strong>Account registration.</strong> You must provide accurate, complete information during registration. You are responsible for keeping your credentials confidential and for all activity that occurs under your account. Notify us immediately at <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a> if you suspect unauthorised access.</p>
        <p className="mt-3"><strong>Disposable emails.</strong> Registration with temporary or disposable email addresses is not permitted and will be rejected automatically.</p>
        <p className="mt-3"><strong>One account per person.</strong> Creating multiple accounts to circumvent plan limits, credit allowances, or enforcement actions is prohibited.</p>
        <p className="mt-3"><strong>Account security.</strong> We implement account lockout after repeated failed login attempts (soft lock after 5 failures, hard lock after 10 failures for up to 24 hours). We use CSRF protection and signed, expiring tokens for all authentication flows.</p>
      </Section>

      <Section id="plans" title="3. Plans & Research Credits">
        <p>SYNAPTIQ is available on four subscription tiers:</p>
        <ul className="mt-3 space-y-1 text-sm">
          <li><strong>Free</strong> — 50 Research Credits / month, 1 project, 1 workspace, 500 MB repository storage.</li>
          <li><strong>Researcher</strong> — 300 Credits / month, unlimited projects, 10 workspaces, 100 GB storage.</li>
          <li><strong>Pro Researcher</strong> — 1,000 Credits / month, unlimited projects, unlimited workspaces, 500 GB storage.</li>
          <li><strong>Institution</strong> — 20,000 Credits / month, 25 user seats, unlimited projects and workspaces, 2 TB storage.</li>
        </ul>
        <p className="mt-3"><strong>Credit Packs</strong> are available as one-time purchases (100 credits for €5, 250 for €10, 1,000 for €29, 5,000 for €99). Credit Pack credits never expire and are not affected by plan changes or cancellation.</p>
        <p className="mt-3">Feature availability varies by plan. The authoritative feature matrix is published on the <Link to="/pricing" className="editorial-link">Pricing page</Link> and may be updated as new capabilities are introduced.</p>
      </Section>

      <Section id="subscriptions" title="4. Subscriptions & Billing">
        <p><strong>Billing currency.</strong> All subscription and credit-pack prices are quoted in Euros (EUR). Payment processing is handled by Stripe. We do not store card numbers or CVV codes.</p>
        <p className="mt-3"><strong>Automatic renewal.</strong> Paid subscriptions renew automatically at the end of each billing period (monthly or annual) at the then-current price, unless cancelled before the renewal date.</p>
        <p className="mt-3"><strong>Cancellation.</strong> You may cancel at any time from the Settings page. Your subscription remains active until the end of the current billing period. After that date, your account downgrades to the Free plan. Your data, projects, and Credit Pack balance are retained on cancellation.</p>
        <p className="mt-3"><strong>Upgrades.</strong> When you upgrade mid-cycle, your monthly Research Credit balance is topped up to the new plan&rsquo;s allowance immediately. You are billed a prorated amount for the remainder of the current period (handled by Stripe).</p>
        <p className="mt-3"><strong>Downgrades.</strong> When you downgrade, your monthly credit allowance adjusts to the new plan at the next billing cycle. Existing Credit Pack credits are unaffected.</p>
        <p className="mt-3"><strong>Price changes.</strong> We will notify you of any price change by email at least 30 days before it takes effect. Continued use after the effective date constitutes acceptance. If you do not accept the new price, you may cancel before the effective date.</p>
        <p className="mt-3"><strong>Chargebacks.</strong> If you believe a charge is incorrect, contact <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a> before initiating a chargeback. Initiating a chargeback without first contacting support may result in account suspension pending investigation.</p>
      </Section>

      <Section id="refunds" title="5. Refunds">
        <p><strong>Subscription fees</strong> are non-refundable except where required by the EU Consumer Rights Directive or other mandatory consumer protection law applicable in your jurisdiction.</p>
        <p className="mt-3"><strong>Right of withdrawal.</strong> EU consumers have a statutory 14-day right of withdrawal from a new subscription. By using AI features or otherwise accessing paid functionality before the 14-day period expires, you expressly acknowledge that performance has begun and waive this right to the extent permitted by applicable law.</p>
        <p className="mt-3"><strong>Service credit.</strong> If the Service is unavailable for more than 48 consecutive hours due to our fault, you may request a pro-rata account credit by emailing <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a>. Credits issued in this way expire after 12 months.</p>
        <p className="mt-3"><strong>Credit Packs</strong> are non-refundable once credits have been consumed. Unconsumed Credit Pack credits on a cancelled account are forfeited; retained for accounts that downgrade to Free.</p>
      </Section>

      <Section id="credits" title="6. Research Credits">
        <p>Research Credits (&ldquo;Credits&rdquo;) are a consumable unit used to access AI-powered features on the Platform. Credits are not currency, have no cash value, and cannot be transferred between accounts or redeemed for cash.</p>
        <p className="mt-3"><strong>Monthly Credits</strong> are granted at the start of each billing cycle and reset at the next renewal. Unused monthly Credits do not roll over.</p>
        <p className="mt-3"><strong>Credit Pack credits</strong> are one-time purchases. They do not expire and are consumed after your monthly Credits are exhausted in any given cycle.</p>
        <p className="mt-3"><strong>Costs.</strong> Each AI action deducts a specific number of Credits. Representative costs: AI Research Assistant (2 credits/query), AI Manuscript Review (20 credits/review), AI Literature Review (20 credits/review), AI Statistical Review (25 credits/review). A full credit cost schedule is published on the <Link to="/pricing" className="editorial-link">Pricing page</Link>.</p>
        <p className="mt-3"><strong>No guarantee.</strong> Credits are consumed when a request is submitted, not when a response is received. Failed requests due to system errors are typically refunded; we reserve the right to determine final credit dispositions.</p>
      </Section>

      <Section id="acceptable-use" title="7. Acceptable Use & Prohibited Activities">
        <p>You agree not to use the Platform to:</p>
        <ul className="mt-3 list-disc ml-6 space-y-1 text-sm">
          <li>Violate any applicable law or regulation.</li>
          <li>Infringe intellectual property, privacy, or other rights of any person.</li>
          <li>Upload or transmit malicious code, viruses, or scripts designed to interfere with the Platform or other users&rsquo; systems.</li>
          <li>Misrepresent your academic identity, institutional affiliation, or credentials.</li>
          <li>Send unsolicited bulk communications or use the messaging system for spam.</li>
          <li>Scrape, harvest, or systematically extract data from the Platform without our written permission.</li>
          <li>Attempt to circumvent authentication, access controls, or rate limits.</li>
          <li>Sell, resell, or commercially exploit access to the Platform or Research Credits without authorisation.</li>
          <li>Create fake researcher profiles or manipulate discovery results.</li>
          <li>Engage in academic misconduct, research fraud, data fabrication, or plagiarism using Platform tools.</li>
          <li>Use AI features to fabricate citations, data, or results that are then submitted as genuine findings.</li>
        </ul>
        <p className="mt-3">Violation of this section may result in immediate suspension or termination of your account.</p>
      </Section>

      <Section id="ip" title="8. Intellectual Property & Content Ownership">
        <p><strong>Your content.</strong> You retain all copyright and moral rights over manuscripts, datasets, notes, annotations, and other content you create or upload (&ldquo;User Content&rdquo;). You grant SYNAPTIQ a limited, non-exclusive, royalty-free licence to store, display, and process your User Content solely to provide the Service. This licence terminates when you delete the content or close your account.</p>
        <p className="mt-3"><strong>Collaboration content.</strong> Content you share within a collaboration is accessible to invited collaborators only for the purpose of that collaboration. Collaborators receive no broader rights to your User Content through the Platform.</p>
        <p className="mt-3"><strong>Public profile.</strong> Information you choose to publish on your public researcher profile is visible to other authenticated users and, where applicable, to the public. You control which fields appear on your public profile.</p>
        <p className="mt-3"><strong>AI-generated outputs.</strong> Text suggestions, summaries, and analysis generated by the AI assistant are produced in response to your inputs. You are responsible for reviewing, verifying, and taking ownership of any AI-assisted output before submitting it for publication or institutional use. We do not claim ownership over AI-generated content produced during your use of the Service. See Section 9 and our <Link to="/ai-policy" className="editorial-link">AI Usage Policy</Link> for limitations.</p>
        <p className="mt-3"><strong>Platform.</strong> SYNAPTIQ retains all rights to the Platform, code, design, branding, trademarks, and research algorithms. Nothing in these Terms grants you any licence to those assets.</p>
        <p className="mt-3"><strong>Feedback.</strong> If you provide suggestions, ideas, or feedback about the Platform, we may use them without compensation or attribution.</p>
      </Section>

      <Section id="ai-content" title="9. AI-Generated Content & Academic Integrity">
        <p>AI features on SYNAPTIQ generate content using large language models operated by third-party providers (currently Anthropic Claude as primary; OpenAI GPT as optional). These outputs:</p>
        <ul className="mt-3 list-disc ml-6 space-y-1 text-sm">
          <li>Are not independently verified for accuracy, factual correctness, or originality.</li>
          <li>May contain errors, outdated information, or fabricated content (&ldquo;hallucinations&rdquo;).</li>
          <li>May reflect biases present in the underlying model&rsquo;s training data.</li>
          <li>Should not be relied upon as legal, medical, or scientific advice without independent expert review.</li>
        </ul>
        <p className="mt-3"><strong>Citation risk.</strong> AI models can generate plausible-sounding but non-existent references. You must independently verify all citations before including them in submitted work.</p>
        <p className="mt-3"><strong>Your responsibility.</strong> You are solely responsible for reviewing all AI-generated content before incorporating it into manuscripts, grant applications, or other academic submissions. Where your institution, target journal, conference, or funding body requires disclosure of AI tool use, you must make such disclosures. Failing to do so where required may constitute academic misconduct and is a violation of these Terms.</p>
        <p className="mt-3">For full details on AI limitations, providers, and data handling, see the <Link to="/ai-policy" className="editorial-link">AI Usage Policy</Link>.</p>
      </Section>

      <Section id="collaboration" title="10. Collaboration & Co-authorship">
        <p>SYNAPTIQ facilitates collaboration matching and project management but is not a party to any co-authorship agreement between researchers. The determination of authorship, contributor roles, and authorship order is the sole responsibility of the collaborating parties.</p>
        <p className="mt-3">We strongly encourage all collaborators to document contribution roles within the project workspace from the outset, using recognised frameworks such as CRediT (Contributor Roles Taxonomy).</p>
        <p className="mt-3">SYNAPTIQ will not adjudicate authorship or research disputes, but may take action under Section 7 where clear evidence of academic misconduct exists.</p>
      </Section>

      <Section id="repository" title="11. Repository & File Storage">
        <p><strong>File types.</strong> The repository accepts: PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT, CSV, ZIP, PNG, JPEG, WEBP, and GIF files. Individual file uploads are limited to 50 MB.</p>
        <p className="mt-3"><strong>Storage limits.</strong> Available repository storage depends on your plan (Free: 500 MB; Researcher: 100 GB; Pro Researcher: 500 GB; Institution: 2 TB). Uploads beyond your plan&rsquo;s storage quota will be rejected.</p>
        <p className="mt-3"><strong>Version history.</strong> Files are versioned within their parent entity. Deleting a file version removes it from the repository interface; it may be retained in backup systems for up to 14 days.</p>
        <p className="mt-3"><strong>Your responsibility.</strong> You must not upload files that infringe third-party intellectual property rights or that contain malicious content. We reserve the right to remove files that violate these Terms.</p>
        <p className="mt-3"><strong>Storage location.</strong> Files are stored in AWS S3-compatible object storage. Your data is encrypted in transit and at rest.</p>
      </Section>

      <Section id="availability" title="12. Service Availability & Modifications">
        <p>We aim for high availability but make no guarantee of uninterrupted service. Scheduled maintenance will be communicated in advance where reasonably practicable. We are not liable for downtime attributable to third-party infrastructure, including MongoDB Atlas, AWS S3, Stripe, or AI provider outages.</p>
        <p className="mt-3">We may add, modify, or remove features with reasonable notice. Material changes to the core functionality or pricing will be communicated by email or in-app notification at least 14 days before taking effect. Continued use after the effective date constitutes acceptance. If you do not accept a material change, you may cancel your subscription before the effective date and receive a pro-rata credit for any unused period.</p>
      </Section>

      <Section id="liability" title="13. Limitation of Liability">
        <p>To the maximum extent permitted by applicable law, SYNAPTIQ&rsquo;s aggregate liability for any claim arising from these Terms or your use of the Service is limited to the fees you paid to us in the twelve months preceding the claim.</p>
        <p className="mt-3">We are not liable for: (a) indirect, consequential, incidental, or punitive damages; (b) loss of data, revenue, research output, academic opportunities, or professional reputation; (c) errors or inaccuracies in AI-generated content; (d) reliance on recommendations produced by any matching, scoring, or prediction engine on the Platform.</p>
        <p className="mt-3">Nothing in these Terms limits liability for death or personal injury caused by our negligence, fraud or fraudulent misrepresentation, or any other liability that cannot be excluded by law.</p>
      </Section>

      <Section id="termination" title="14. Termination & Account Suspension">
        <p><strong>By you.</strong> You may request account deletion at any time by emailing <a href="mailto:privacy@synaptiq.academy" className="editorial-link">privacy@synaptiq.academy</a>. Account deletion is also available via the Settings page. Upon deletion, personal data is removed within 30 days, subject to legal retention obligations (see Privacy Policy).</p>
        <p className="mt-3"><strong>By us.</strong> We may suspend or terminate accounts that violate these Terms, particularly Sections 7 (Acceptable Use) and 9 (Academic Integrity). Suspension takes effect immediately. If your account is suspended, you may appeal by emailing <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a>; we will respond within 5 business days. Accounts suspended for research misconduct, fraud, or illegal activity will not be reinstated.</p>
        <p className="mt-3"><strong>Effect of termination.</strong> On termination, your right to use the Service ceases immediately. Your subscription is cancelled and Credit Pack credits are forfeited. Billing records are retained for 7 years as required by EU tax law.</p>
      </Section>

      <Section id="institution" title="15. Institutional Accounts">
        <p>The Institution plan permits up to 25 named researcher seats. The account administrator is responsible for managing seat assignments, ensuring all seat holders comply with these Terms, and paying all fees associated with the institutional subscription.</p>
        <p className="mt-3">Institutional customers may request a Data Processing Agreement (DPA) by emailing <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a>. The DPA governs data processing in the context of institutional use and is required for EU institutional customers processing personal data of EU residents.</p>
        <p className="mt-3">Institutional seats cannot be shared between individuals. Each seat must be assigned to a named, individual researcher at the subscribing institution.</p>
      </Section>

      <Section id="governing-law" title="16. Governing Law & Dispute Resolution">
        <p>These Terms are governed by the laws of the European Union and the country in which SYNAPTIQ is registered. You agree that disputes arising from these Terms or your use of the Service will be subject to the exclusive jurisdiction of the competent courts of that country, except where mandatory local consumer protection law provides otherwise.</p>
        <p className="mt-3"><strong>Informal resolution.</strong> Before initiating formal legal proceedings, we ask that you contact us at <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a> to allow a good-faith attempt at informal resolution. Most concerns can be resolved this way.</p>
        <p className="mt-3"><strong>EU Online Dispute Resolution.</strong> EU consumers may use the European Commission&rsquo;s Online Dispute Resolution (ODR) platform to resolve disputes. Nothing in this section limits your statutory consumer rights.</p>
      </Section>

      <Section id="general" title="17. General Provisions">
        <p><strong>Entire agreement.</strong> These Terms, together with the <Link to="/privacy" className="editorial-link">Privacy Policy</Link>, <Link to="/cookies" className="editorial-link">Cookie Policy</Link>, <Link to="/ai-policy" className="editorial-link">AI Usage Policy</Link>, and any applicable DPA, constitute the entire agreement between you and SYNAPTIQ regarding the Service.</p>
        <p className="mt-3"><strong>Severability.</strong> If any provision of these Terms is found unenforceable, that provision will be limited or eliminated to the minimum extent necessary, and the remaining provisions will continue in full force.</p>
        <p className="mt-3"><strong>No waiver.</strong> Our failure to enforce any right or provision of these Terms is not a waiver of that right or provision.</p>
        <p className="mt-3"><strong>Assignment.</strong> You may not transfer or assign your account or rights under these Terms without our prior written consent. We may assign our rights and obligations under these Terms in connection with a merger, acquisition, or sale of assets.</p>
        <p className="mt-3"><strong>Changes to Terms.</strong> We may update these Terms from time to time. Material changes will be communicated by email or in-app notification at least 14 days before taking effect. Continued use after the effective date constitutes acceptance of the updated Terms.</p>
        <p className="mt-3"><strong>Contact.</strong> Questions about these Terms? Email <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a>.</p>
      </Section>
    </LegalLayout>
  );
}

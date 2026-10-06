import React from "react";
import { Link } from "react-router-dom";
import { LegalLayout, Section } from "./legal/LegalLayout";
import { LEGAL, OPERATOR_PENDING } from "../content/legal/meta";

/*
 * GDPR Notice — a short guide to the rights the GDPR gives and how to use
 * them on Synaptiq. Every factual statement here is verified against the
 * product; processing details, providers, transfers and retention live in
 * the Privacy Policy only, so the two documents can't contradict each other.
 */
const SECTIONS = [
  { id: "applicability", label: "1. Who This Covers" },
  { id: "rights",        label: "2. Your Rights" },
  { id: "exercising",    label: "3. Using Your Rights" },
  { id: "automated",     label: "4. Automated Decisions" },
  { id: "details",       label: "5. Processing Details" },
  { id: "complaints",    label: "6. Complaints" },
];

const P = LEGAL.contact.privacy;
const mail = <a href={`mailto:${P}`} className="editorial-link">{P}</a>;

export default function GDPR() {
  React.useEffect(() => {
    document.title = "GDPR — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  return (
    <LegalLayout
      eyebrow="Legal"
      title="GDPR Notice"
      subtitle="Your rights under the General Data Protection Regulation (EU) 2016/679, and how to use them on Synaptiq."
      lastUpdated="6 October 2026"
      readingTime="3 min"
      version="2026-10-06"
      sections={SECTIONS}
    >
      <Section id="applicability" title="1. Who This Notice Covers">
        <p>This notice is for anyone whose personal data Synaptiq processes. It supplements the <Link to="/privacy" className="editorial-link">Privacy Policy</Link>, which is the full description of what we collect, why, who processes it, where, and for how long.</p>
        <p className="mt-3">{LEGAL.operator ? `The controller is ${LEGAL.operator.name}, ${LEGAL.operator.address}.` : OPERATOR_PENDING}</p>
      </Section>

      <Section id="rights" title="2. Your Rights">
        <ul className="mt-3 list-disc ml-6 space-y-2">
          <li><strong>Access (Article 15)</strong>: get a copy of your personal data and information about how it is used.</li>
          <li><strong>Rectification (Article 16)</strong>: correct inaccurate or incomplete data.</li>
          <li><strong>Erasure (Article 17)</strong>: have your data deleted, subject to what the law requires us to keep.</li>
          <li><strong>Restriction (Article 18)</strong>: ask us to limit use of your data, for example while a correction is checked.</li>
          <li><strong>Portability (Article 20)</strong>: receive data you gave us in a structured, machine-readable format.</li>
          <li><strong>Objection (Article 21)</strong>: object to processing based on our legitimate interests.</li>
          <li><strong>Withdrawing consent</strong>: where we rely on consent, such as analytics, you can withdraw it at any time. This doesn't affect processing before you withdrew.</li>
        </ul>
      </Section>

      <Section id="exercising" title="3. Using Your Rights">
        <p>Some rights you can use yourself, straight away:</p>
        <ul className="mt-3 list-disc ml-6 space-y-2">
          <li><strong>Correct your details</strong> by editing your Academic Passport and settings.</li>
          <li><strong>Download your data</strong> as a JSON file: Settings → Privacy → Export my data.</li>
          <li><strong>Delete your account</strong>: Settings → Privacy → Delete my account. The Privacy Policy explains what is deleted, what stays with people you shared it with, and what we must keep.</li>
          <li><strong>Limit who sees you</strong> with your profile visibility and discovery settings.</li>
          <li><strong>Change your analytics choice</strong> with "Cookie settings" in the site footer, or in Settings → Privacy.</li>
        </ul>
        <p className="mt-3">For anything else, email {mail}. We reply within one month, as the GDPR requires; for complex requests this can be extended by up to two further months, and we will tell you within the first month if so. We may ask you to confirm your identity. Requests are free unless they are manifestly unfounded or excessive.</p>
      </Section>

      <Section id="automated" title="4. Automated Decisions">
        <p>Synaptiq suggests possible collaborators, journals, conferences and funding calls, and shows indicators on profiles. These are suggestions you can ignore; they don't make decisions with legal or similarly significant effects on you. Every decision, such as submitting a manuscript or joining a collaboration, is yours.</p>
        <p className="mt-3">If you'd like an explanation of a suggestion, email {mail}.</p>
      </Section>

      <Section id="details" title="5. Processing Details">
        <p>The <Link to="/privacy" className="editorial-link">Privacy Policy</Link> sets out the legal basis for each use of your data, our service providers and where they process data, transfers outside the European Economic Area and their safeguards, and how long each kind of data is kept.</p>
      </Section>

      <Section id="complaints" title="6. Complaints">
        <p>You can complain to a data protection authority. In Romania that is the {LEGAL.authority.name}, <a href={LEGAL.authority.url} target="_blank" rel="noopener noreferrer" className="editorial-link">{LEGAL.authority.url.replace("https://", "")}</a>. You may also go to the authority where you live or work; the European Data Protection Board lists them at <a href="https://www.edpb.europa.eu" target="_blank" rel="noopener noreferrer" className="editorial-link">edpb.europa.eu</a>.</p>
        <p className="mt-3">You're welcome to contact us first at {mail}, but you don't have to.</p>
      </Section>
    </LegalLayout>
  );
}

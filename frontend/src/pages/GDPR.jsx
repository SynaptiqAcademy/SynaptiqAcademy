import React from "react";
import { Link } from "react-router-dom";
import { LegalLayout, Section } from "./legal/LegalLayout";
import { NAVY } from "@/lib/tokens";

const SECTIONS = [
  { id: "applicability", label: "1. Who This Covers" },
  { id: "rights",        label: "2. Your Rights" },
  { id: "legal-bases",   label: "3. Legal Bases" },
  { id: "automated",     label: "4. Automated Decisions" },
  { id: "transfers",     label: "5. International Transfers" },
  { id: "processors",    label: "6. Sub-processors" },
  { id: "dpo",           label: "7. Data Protection" },
  { id: "retention",     label: "8. Retention" },
  { id: "exercising",    label: "9. Exercising Your Rights" },
  { id: "complaints",    label: "10. Complaints" },
];

export default function GDPR() {
  React.useEffect(() => {
    document.title = "GDPR — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  return (
    <LegalLayout
      eyebrow="Legal"
      title="GDPR Notice"
      subtitle="Rights of EU and EEA residents under Regulation (EU) 2016/679 — access, erasure, portability, and supervisory authority contacts."
      lastUpdated="29 June 2026"
      readingTime="6 min"
      version="v1.3"
      sections={SECTIONS}
    >
      <Section id="applicability" title="1. Who This Notice Covers">
        <p>This GDPR Notice applies to individuals in the European Union (EU) and European Economic Area (EEA). It supplements the <Link to="/privacy" className="editorial-link">Privacy Policy</Link> and describes rights and processing details specific to Regulation (EU) 2016/679 (the &ldquo;GDPR&rdquo;).</p>
        <p className="mt-3">The data controller for personal data processed through SYNAPTIQ is the entity operating the Platform. Contact details are at the end of this notice.</p>
      </Section>

      <Section id="rights" title="2. Your Rights Under the GDPR">
        <p>As an EU/EEA resident, you have the following rights under the GDPR. We respond to all rights requests within 30 days, free of charge, unless a request is manifestly unfounded or excessive.</p>

        <div className="mt-4 space-y-4">
          {[
            {
              right: "Right of access (Article 15)",
              detail: "Obtain a copy of all personal data we hold about you, along with information about how it is processed. You can download a machine-readable export of your data directly from Settings → Privacy → Export my data. For a full access request covering all systems, email privacy@synaptiq.academy.",
            },
            {
              right: "Right to rectification (Article 16)",
              detail: "Correct inaccurate or incomplete data. Most profile fields can be updated directly in your account settings. For data you cannot update yourself, contact privacy@synaptiq.academy.",
            },
            {
              right: "Right to erasure — 'right to be forgotten' (Article 17)",
              detail: "Request deletion of your account and personal data. Account deletion is available via Settings or by emailing privacy@synaptiq.academy. Note: billing records are retained for 7 years under EU tax law; audit log entries may be retained for 3 years for compliance.",
            },
            {
              right: "Right to restriction of processing (Article 18)",
              detail: "Request that we limit how we process your data — for example, while a rectification request is being verified, or where you contest the legal basis for processing.",
            },
            {
              right: "Right to data portability (Article 20)",
              detail: "Receive a copy of the data you provided to us, in a structured, commonly used, machine-readable format (JSON), for transfer to another controller. Use the self-service export at Settings → Privacy → Export my data, or email privacy@synaptiq.academy.",
            },
            {
              right: "Right to object (Article 21)",
              detail: "Object to processing based on legitimate interests, including our use of your profile data for matching recommendations and aggregate analytics. We will cease processing unless we can demonstrate compelling legitimate grounds that override your interests.",
            },
            {
              right: "Right to withdraw consent",
              detail: "Withdraw consent for analytics cookies and session recording at any time via the cookie consent banner or Settings → Privacy → Cookie preferences. Withdrawal does not affect the lawfulness of processing before withdrawal.",
            },
            {
              right: "Right not to be subject to solely automated decisions (Article 22)",
              detail: "See Section 4 below.",
            },
          ].map((item) => (
            <div key={item.right} style={{ padding: "14px 16px", background: "#F7F8FA", borderRadius: 8, borderLeft: "3px solid #0F2847" }}>
              <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "#0f172a", marginBottom: 4 }}>{item.right}</div>
              <p style={{ fontSize: "0.85rem", color: "#475569", lineHeight: 1.6, margin: 0 }}>{item.detail}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section id="legal-bases" title="3. Legal Bases for Processing">
        <p>We rely on the following lawful bases under Article 6 GDPR:</p>
        <div className="mt-4 overflow-x-auto">
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#F7F8FA" }}>
                <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, borderBottom: "1px solid #e2e8f0" }}>Processing activity</th>
                <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, borderBottom: "1px solid #e2e8f0" }}>Legal basis</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Account creation, authentication, and session management", "Performance of contract (Art. 6(1)(b))"],
                ["Subscription billing and payment processing", "Performance of contract (Art. 6(1)(b))"],
                ["Research profile, collaboration matching, and recommendations", "Performance of contract (Art. 6(1)(b))"],
                ["AI feature processing (manuscript, literature, statistical)", "Performance of contract (Art. 6(1)(b))"],
                ["Transactional emails (verification, password reset, billing)", "Performance of contract (Art. 6(1)(b))"],
                ["Account security, lockout, and fraud prevention", "Legitimate interests (Art. 6(1)(f)) — protecting platform integrity"],
                ["Aggregate API monitoring and platform stability", "Legitimate interests (Art. 6(1)(f)) — operating a reliable service"],
                ["Audit logging of administrative actions", "Legitimate interests (Art. 6(1)(f)) — accountability and compliance"],
                ["Analytics and session recording (PostHog)", "Consent (Art. 6(1)(a)) — managed via cookie consent banner"],
                ["Marketing communications", "Consent (Art. 6(1)(a))"],
                ["Billing record retention (7 years)", "Legal obligation (Art. 6(1)(c)) — EU VAT Directive and national tax law"],
              ].map(([activity, basis]) => (
                <tr key={activity} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "8px 12px" }}>{activity}</td>
                  <td style={{ padding: "8px 12px", color: "#374151" }}>{basis}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section id="automated" title="4. Automated Decision-Making">
        <p>SYNAPTIQ uses algorithmic systems to generate recommendations (journals, conferences, grants, collaborators) and to compute platform scores (reputation score, research impact score). These systems assist your research workflows but do not produce decisions that produce legal or similarly significant effects on you.</p>
        <p className="mt-3">You are not required to act on any recommendation or score produced by the Platform. All material decisions — such as submitting a manuscript, joining a collaboration, or applying for a grant — are made by you. The Platform provides information and suggestions; it does not decide on your behalf.</p>
        <p className="mt-3">If you have concerns about a specific score or recommendation, contact <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a> and we will explain the factors contributing to it.</p>
      </Section>

      <Section id="transfers" title="5. International Data Transfers">
        <p>Personal data may be transferred outside the EEA to the following categories of recipients:</p>
        <ul className="mt-3 list-disc ml-6 space-y-2 text-sm">
          <li><strong>United States</strong> — Anthropic (Claude API), OpenAI (GPT API, optional), Stripe (payments), Resend (email), PostHog (analytics), MongoDB Atlas (database, US region by default). These transfers are governed by Standard Contractual Clauses (SCCs) under Commission Implementing Decision (EU) 2021/914, supplemented by technical safeguards.</li>
          <li><strong>Global</strong> — ORCID (researcher identity, international non-profit). Data shared with ORCID is limited to your ORCID iD and sync requests; your ORCID public record is retrieved from ORCID servers.</li>
        </ul>
        <p className="mt-3">EU data residency for database storage is available for institutional customers via a Data Processing Agreement. Contact <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a>.</p>
        <p className="mt-3">Copies of applicable Standard Contractual Clauses are available upon request from <a href="mailto:privacy@synaptiq.academy" className="editorial-link">privacy@synaptiq.academy</a>.</p>
      </Section>

      <Section id="processors" title="6. Sub-processors">
        <p>We maintain a list of sub-processors authorised to process personal data on our behalf. The current list is published in the <Link to="/privacy" className="editorial-link">Privacy Policy</Link> (Section 5) and is available in full on request for institutional customers as part of a Data Processing Agreement.</p>
        <p className="mt-3">We perform due diligence on sub-processors before engaging them and require all sub-processors to maintain appropriate technical and organisational measures. We will notify institutional customers of any changes to sub-processors that may affect their DPA.</p>
      </Section>

      <Section id="dpo" title="7. Data Protection Contact">
        <p>SYNAPTIQ does not currently meet the thresholds that require mandatory appointment of a Data Protection Officer under GDPR Article 37. However, privacy-related enquiries, rights requests, and complaints should be directed to our privacy contact:</p>
        <ul className="mt-3 text-sm space-y-1">
          <li><strong>Email:</strong> <a href="mailto:privacy@synaptiq.academy" className="editorial-link">privacy@synaptiq.academy</a></li>
          <li><strong>Response time:</strong> We acknowledge within 5 business days and respond fully within 30 days.</li>
        </ul>
      </Section>

      <Section id="retention" title="8. Retention Periods">
        <p>A summary of retention periods for key data categories:</p>
        <div className="mt-4 overflow-x-auto">
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#F7F8FA" }}>
                <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, borderBottom: "1px solid #e2e8f0" }}>Data category</th>
                <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, borderBottom: "1px solid #e2e8f0" }}>Retention period</th>
                <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, borderBottom: "1px solid #e2e8f0" }}>Basis</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Profile, content, projects, files", "Duration of account; removed within 30 days of deletion", "Contract performance"],
                ["Billing and transaction records", "7 years post-transaction", "EU VAT / tax law obligation"],
                ["Audit log (administrative actions)", "3 years", "Legitimate interests (compliance)"],
                ["Security event log (failed logins, lockouts)", "12 months post-account deletion", "Legitimate interests (security)"],
                ["Application server logs", "30 days rolling", "Legitimate interests (incident response)"],
                ["Database backups", "14 days (point-in-time recovery)", "Contract performance"],
                ["Consent records", "3 years", "Legal obligation (demonstrate consent)"],
                ["ORCID tokens", "Duration of ORCID connection; removed on disconnect or account deletion", "Contract performance"],
              ].map(([cat, period, basis]) => (
                <tr key={cat} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "8px 12px" }}>{cat}</td>
                  <td style={{ padding: "8px 12px" }}>{period}</td>
                  <td style={{ padding: "8px 12px", color: "#64748b" }}>{basis}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section id="exercising" title="9. Exercising Your Rights">
        <p>To exercise any GDPR right:</p>
        <ol className="mt-3 space-y-2 text-sm list-decimal ml-6">
          <li><strong>Self-service (fastest):</strong> Data export is available at <em>Settings → Privacy → Export my data</em>. Cookie consent preferences can be managed in <em>Settings → Privacy → Cookie preferences</em>.</li>
          <li><strong>Email request:</strong> For all other rights (access, rectification, erasure, restriction, portability, objection), email <a href="mailto:privacy@synaptiq.academy" className="editorial-link">privacy@synaptiq.academy</a> with your request and sufficient information to verify your identity.</li>
          <li>We will respond within 30 days. Complex requests may take up to 90 days; we will inform you of any extension within the initial 30-day period.</li>
          <li>Rights requests are free of charge unless manifestly unfounded or excessive, in which case we may charge a reasonable fee or decline to act.</li>
        </ol>
      </Section>

      <Section id="complaints" title="10. Right to Lodge a Complaint">
        <p>If you believe that we have not handled your personal data in accordance with the GDPR, you have the right to lodge a complaint with the supervisory authority in your country of residence, place of work, or the location of the alleged infringement.</p>
        <p className="mt-3">We encourage you to contact us at <a href="mailto:privacy@synaptiq.academy" className="editorial-link">privacy@synaptiq.academy</a> first, as most concerns can be resolved directly. However, you are entitled to contact your supervisory authority at any time without first contacting us.</p>
        <p className="mt-3">A list of EU supervisory authorities is maintained by the European Data Protection Board at <a href="https://www.edpb.europa.eu" target="_blank" rel="noopener noreferrer" className="editorial-link">edpb.europa.eu</a>.</p>
      </Section>
    </LegalLayout>
  );
}

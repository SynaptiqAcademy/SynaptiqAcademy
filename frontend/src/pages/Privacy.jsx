import React from "react";
import { Link } from "react-router-dom";
import { LegalLayout, Section } from "./legal/LegalLayout";

const SECTIONS = [
  { id: "scope",          label: "1. Scope" },
  { id: "data-collected", label: "2. Data We Collect" },
  { id: "how-we-use",     label: "3. How We Use Data" },
  { id: "legal-bases",    label: "4. Legal Bases" },
  { id: "sharing",        label: "5. Sub-processors" },
  { id: "cookies",        label: "6. Cookies & Analytics" },
  { id: "orcid",          label: "7. ORCID & Integrations" },
  { id: "logging",        label: "8. Logs & Diagnostics" },
  { id: "retention",      label: "9. Retention" },
  { id: "transfers",      label: "10. International Transfers" },
  { id: "rights",         label: "11. Your Rights" },
  { id: "security",       label: "12. Security" },
  { id: "children",       label: "13. Children" },
  { id: "changes",        label: "14. Policy Changes" },
  { id: "contact",        label: "15. Contact" },
];

export default function Privacy() {
  React.useEffect(() => {
    document.title = "Privacy Policy — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  return (
    <LegalLayout
      eyebrow="Legal"
      title="Privacy Policy"
      subtitle="How we collect, use, and protect your personal data — including AI context handling, cookies, and your rights."
      lastUpdated="29 June 2026"
      readingTime="8 min"
      version="v1.4"
      sections={SECTIONS}
    >
      <Section id="scope" title="1. Scope of This Policy">
        <p>This Privacy Policy explains what personal data SYNAPTIQ collects when you use the Platform, why we collect it, how we use it, who we share it with, and your rights as a data subject. It applies to all users of the Service, including visitors to our marketing pages.</p>
        <p className="mt-3">EU and EEA residents have additional rights described in the <Link to="/gdpr" className="editorial-link">GDPR Notice</Link>, including the right to lodge a complaint with a supervisory authority.</p>
      </Section>

      <Section id="data-collected" title="2. Data We Collect">
        <p><strong>Account and identity data</strong> — collected during registration and profile setup:</p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li>Email address, hashed password, full name, first name, last name.</li>
          <li>Institution, department, country, city.</li>
          <li>Academic role, career stage, user type, primary domain (research / teaching / both).</li>
        </ul>

        <p className="mt-4"><strong>Academic profile data</strong> — optional, provided by you:</p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li>ORCID iD (linked via OAuth), Google Scholar URL, ResearchGate URL, Scopus ID, LinkedIn URL, personal website.</li>
          <li>Research areas, research interests, keywords, methodological expertise, software skills, languages, skills.</li>
          <li>Teaching areas, professional expertise, availability preferences.</li>
          <li>Biography, awards, certifications, professional memberships.</li>
          <li>Avatar image and cover photo (URLs hosted externally and provided by you).</li>
        </ul>

        <p className="mt-4"><strong>ORCID-imported data</strong> — synced when you connect your ORCID iD:</p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li>Employment history, education history, funded works (from your ORCID public record).</li>
          <li>ORCID access and refresh tokens (stored server-side; never exposed in API responses).</li>
        </ul>

        <p className="mt-4"><strong>OpenAlex-derived data</strong> — fetched automatically if your ORCID or name matches an OpenAlex author record:</p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li>OpenAlex author ID, profile URL, h-index, publications count.</li>
        </ul>

        <p className="mt-4"><strong>Content data</strong> — created by you during use of the Platform:</p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li>Research projects, workspaces, manuscripts, notes, and tasks.</li>
          <li>Files uploaded to the repository (PDF, DOCX, images, etc.).</li>
          <li>Collaboration records, messages, and expertise requests.</li>
          <li>Teaching lessons, assessments, and teaching workspace content.</li>
          <li>Grant applications and funding records.</li>
        </ul>

        <p className="mt-4"><strong>Billing data</strong> — for paid plans:</p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li>Payment processing is handled entirely by Stripe. We never receive, store, or process card numbers or CVV codes.</li>
          <li>We retain transaction IDs, amounts, dates, subscription status, and Stripe customer and subscription identifiers for billing history and tax compliance purposes.</li>
        </ul>

        <p className="mt-4"><strong>Usage and behavioural data</strong> — collected automatically:</p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li>Pages visited, features accessed, Research Credit consumption, and feature interaction patterns — collected via our internal analytics system and PostHog (see Section 6).</li>
          <li>Browser type, operating system, device type (collected by PostHog).</li>
          <li>Session recordings of your interactions with the Platform (collected by PostHog, subject to your consent).</li>
        </ul>

        <p className="mt-4"><strong>Security and authentication data</strong> — maintained to protect accounts:</p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li>Failed login count and timestamps, account lockout status, last successful login timestamp.</li>
          <li>Email verification status, MFA enrollment status and secret (hashed).</li>
          <li>Refresh token JTI (a unique identifier for each session token; not the token itself).</li>
        </ul>

        <p className="mt-4"><strong>Consent records:</strong> We store your cookie consent choices (accepted / rejected / custom preferences) along with a consent ID, user agent string, hashed and truncated IP address, and timestamp.</p>
      </Section>

      <Section id="how-we-use" title="3. How We Use Your Data">
        <ul className="space-y-2 text-sm">
          <li><strong>Providing the Service</strong> — authenticating you, serving your content, enforcing plan limits.</li>
          <li><strong>Research matching</strong> — using your profile, research areas, and availability to power collaboration, reviewer, and co-author matching.</li>
          <li><strong>AI features</strong> — transmitting relevant context (e.g. manuscript text, project description) to AI providers to generate responses. No more context than necessary for the specific feature is transmitted. See Section 5 and the <Link to="/ai-policy" className="editorial-link">AI Usage Policy</Link>.</li>
          <li><strong>Recommendations</strong> — generating journal, conference, and grant recommendations based on your research profile.</li>
          <li><strong>Notifications</strong> — sending in-app and email notifications for platform events (collaboration requests, workspace invitations, citation alerts).</li>
          <li><strong>Transactional emails</strong> — email verification, password reset, billing confirmations.</li>
          <li><strong>Security</strong> — detecting and responding to account abuse, credential stuffing, and suspicious access patterns.</li>
          <li><strong>Analytics and product improvement</strong> — understanding how features are used to improve the Platform. We use PostHog for this purpose (see Section 6).</li>
          <li><strong>Legal compliance</strong> — retaining billing records, responding to legal requests, exercising and defending legal claims.</li>
        </ul>
        <p className="mt-4">We <strong>do not</strong> sell personal data to third parties. We <strong>do not</strong> use your User Content to train our own AI models or permit AI providers to train on your data.</p>
      </Section>

      <Section id="legal-bases" title="4. Legal Bases for Processing (GDPR)">
        <p>For EU/EEA users, we rely on the following lawful bases under Regulation (EU) 2016/679:</p>
        <ul className="mt-3 space-y-2 text-sm">
          <li><strong>Performance of a contract</strong> — processing your account data, subscription, content, and billing information to provide the Service you have subscribed to.</li>
          <li><strong>Legitimate interests</strong> — security monitoring, platform abuse prevention, aggregate product analytics (where we apply appropriate safeguards), and improving the Platform&rsquo;s matching and recommendation algorithms.</li>
          <li><strong>Consent</strong> — analytics cookies and session recording (PostHog), marketing communications, and any other processing for which we have requested your consent via the cookie consent banner or other mechanism. You may withdraw consent at any time without affecting the lawfulness of prior processing.</li>
          <li><strong>Legal obligation</strong> — retaining billing records for 7 years under EU tax law; responding to valid law enforcement requests.</li>
        </ul>
      </Section>

      <Section id="sharing" title="5. Sub-processors & Data Sharing">
        <p>We share personal data only with sub-processors strictly necessary to operate SYNAPTIQ. All sub-processors are bound by data protection agreements. We do not share personal data with advertisers, data brokers, or any unrelated third party.</p>

        <div className="mt-4 overflow-x-auto">
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#F7F8FA" }}>
                <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, borderBottom: "1px solid #e2e8f0" }}>Provider</th>
                <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, borderBottom: "1px solid #e2e8f0" }}>Purpose</th>
                <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, borderBottom: "1px solid #e2e8f0" }}>Data location</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["MongoDB Atlas", "Primary database (user data, content, billing records)", "EU residency available on request"],
                ["Amazon Web Services (S3)", "File and attachment storage (repository files, avatars)", "Configurable region"],
                ["Anthropic (Claude API)", "AI features: manuscript review, literature review, gap analysis, assistant", "US (enterprise API terms — no model training on your data)"],
                ["OpenAI (GPT API)", "Optional secondary AI provider for selected features", "US (enterprise API terms — no model training on your data)"],
                ["Stripe", "Payment processing, subscription management, invoicing", "US/EU (Stripe global infrastructure)"],
                ["Resend", "Transactional email (verification, password reset, notifications)", "US"],
                ["PostHog", "Product analytics, feature flags, session recording", "US (us.i.posthog.com)"],
                ["ORCID", "Researcher identity OAuth and profile synchronisation", "Global (ORCID is an international non-profit)"],
                ["OpenAlex", "Academic publication and author data enrichment", "US (open data API)"],
                ["Redis (optional)", "Rate limit counters (IP-keyed, no personal data)", "Configurable (same region as app)"],
              ].map(([name, purpose, loc]) => (
                <tr key={name} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "8px 12px", fontWeight: 500 }}>{name}</td>
                  <td style={{ padding: "8px 12px" }}>{purpose}</td>
                  <td style={{ padding: "8px 12px", color: "#64748b" }}>{loc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4">The above list is maintained on a best-efforts basis. A complete and current list of sub-processors is available on request from <a href="mailto:privacy@synaptiq.academy" className="editorial-link">privacy@synaptiq.academy</a>.</p>
        <p className="mt-3"><strong>AI context minimisation.</strong> When you use an AI feature, only the context necessary for that specific feature is transmitted to the AI provider (e.g., your manuscript text for a manuscript review — not your full profile, billing data, or unrelated project data).</p>
        <p className="mt-3"><strong>Compelled disclosure.</strong> We may disclose personal data if required to do so by law, court order, or to protect our legal rights or those of our users. We will notify affected users where legally permitted to do so.</p>
      </Section>

      <Section id="cookies" title="6. Cookies & Analytics">
        <p>We use cookies and similar technologies to operate the Platform and to understand how it is used. For a complete list of cookies we set, see the <Link to="/cookies" className="editorial-link">Cookie Policy</Link>.</p>

        <p className="mt-4"><strong>Essential cookies</strong> (always active):</p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li><code>access_token</code> — JWT authentication token. httpOnly, 15-minute lifetime.</li>
          <li><code>refresh_token</code> — Session renewal token. httpOnly, 14-day lifetime.</li>
          <li><code>csrf_token</code> — CSRF double-submit token. JavaScript-readable (required by design), 15-minute lifetime.</li>
        </ul>

        <p className="mt-4"><strong>Analytics and session recording (PostHog)</strong> — subject to your consent:</p>
        <p className="mt-2 text-sm">We use <a href="https://posthog.com" target="_blank" rel="noopener noreferrer" className="editorial-link">PostHog</a>, a US-based product analytics platform, to collect aggregate usage data and session recordings. PostHog sets cookies on your device to identify your session and track interactions within the Platform. When analytics consent is given, PostHog may link your session data to your account identity.</p>
        <p className="mt-2 text-sm">You can control analytics consent via the cookie consent banner shown on first visit, or by updating preferences in the Settings page. Selecting &ldquo;Reject Non-Essential&rdquo; opts you out of PostHog analytics and session recording.</p>
        <p className="mt-2 text-sm"><strong>Note:</strong> PostHog&rsquo;s JavaScript initialises on page load to support certain product features (feature flags) regardless of consent status. PostHog is configured with <code>person_profiles: "identified_only"</code>, meaning it does not build a personal profile unless you are signed in and analytics consent has been given.</p>

        <p className="mt-4"><strong>No advertising or marketing trackers.</strong> We do not use Google Analytics, Facebook Pixel, or any third-party advertising network trackers.</p>
      </Section>

      <Section id="orcid" title="7. ORCID, OpenAlex & External Integrations">
        <p><strong>ORCID.</strong> When you connect your ORCID iD, SYNAPTIQ uses the ORCID OAuth2 flow to retrieve your public ORCID record (employment, education, funded works, and researcher URLs). ORCID access tokens are stored server-side and are never exposed in API responses. You can disconnect ORCID from your account settings at any time, which revokes the stored tokens and removes imported ORCID data from your profile.</p>
        <p className="mt-3"><strong>OpenAlex.</strong> We query the OpenAlex public API to enrich your profile with publication metadata and bibliometric indicators (h-index, citation counts). No personal data is sent to OpenAlex; queries use your ORCID iD or name as a search key. OpenAlex is a fully open, public database maintained by OurResearch.</p>
        <p className="mt-3"><strong>Google OAuth.</strong> If you sign in with Google, we receive your Google account email address and display name. We do not receive your Google password or access other Google services.</p>
        <p className="mt-3"><strong>Stripe.</strong> Payment flows redirect to a Stripe-hosted checkout page. Your payment card data is entered directly into Stripe&rsquo;s systems and is never transmitted to or stored by SYNAPTIQ.</p>
      </Section>

      <Section id="logging" title="8. Logs & Diagnostics">
        <p><strong>API monitoring.</strong> We log aggregate per-endpoint statistics (request count, response time, status codes) by endpoint and date. Individual server errors (HTTP 5xx) are logged with the requesting IP address, endpoint, method, and timestamp. This data is used exclusively for platform stability monitoring.</p>
        <p className="mt-3"><strong>Security event log.</strong> Failed login attempts, account lockouts, and other security-relevant events are logged with the requesting IP address, user agent string, and timestamp. This data is retained for the duration of the account plus 12 months, and is used to detect and respond to credential-based attacks.</p>
        <p className="mt-3"><strong>Audit log.</strong> Significant administrative actions (billing changes, subscription transitions, admin access to user accounts) are logged in an append-only audit log. The audit log includes the actor&rsquo;s identity, IP address, and action taken. This data supports compliance, dispute resolution, and admin accountability.</p>
        <p className="mt-3"><strong>Login history.</strong> Your user record stores the timestamp of your most recent successful login and the count and timestamp of recent failed login attempts. This data is used to implement account lockout and to notify you of suspicious access patterns.</p>
        <p className="mt-3"><strong>Application logs.</strong> Our application server generates structured logs for debugging and incident response. These logs may contain user IDs, email addresses, and request metadata. They are retained for 30 days and are accessible only to authorised engineering staff.</p>
      </Section>

      <Section id="retention" title="9. Data Retention">
        <p><strong>Active accounts</strong> — personal data is retained for the duration of your account.</p>
        <p className="mt-3"><strong>After account deletion</strong> — we process deletion requests by email to <a href="mailto:privacy@synaptiq.academy" className="editorial-link">privacy@synaptiq.academy</a>. Upon deletion:</p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li>Personal profile data (name, email, institution, biography, research profile) is removed or anonymised within 30 days.</li>
          <li>User-created content (manuscripts, projects, workspaces, files) is deleted within 30 days, except where it is part of an active collaboration to which other users have access.</li>
          <li>Billing and transaction records are retained for 7 years as required by EU VAT and accounting law.</li>
          <li>Audit log entries referencing your account may be retained for up to 3 years for compliance purposes.</li>
        </ul>
        <p className="mt-3"><strong>Backups</strong> — database backups are retained for 14 days with point-in-time recovery. Deleted data may persist in backups for up to 14 days beyond the deletion date.</p>
        <p className="mt-3"><strong>Consent records</strong> — retained for 3 years to demonstrate regulatory compliance with consent obligations.</p>
        <p className="mt-3"><strong>Legal hold</strong> — data subject to a valid law enforcement request or legal proceeding may be retained beyond these standard periods.</p>
      </Section>

      <Section id="transfers" title="10. International Data Transfers">
        <p>SYNAPTIQ processes data globally through sub-processors. Some sub-processors (Anthropic, OpenAI, Stripe, Resend, PostHog) are based in the United States. Where personal data is transferred outside the European Economic Area, we rely on:</p>
        <ul className="mt-3 list-disc ml-6 space-y-1 text-sm">
          <li><strong>Standard Contractual Clauses (SCCs)</strong> approved by the European Commission — the primary mechanism for transfers to US-based sub-processors.</li>
          <li><strong>Adequacy decisions</strong> where applicable.</li>
          <li>Additional technical and organisational safeguards consistent with EDPB recommendations.</li>
        </ul>
        <p className="mt-3">EU data residency is available for database storage (MongoDB Atlas) on request for institutional customers. Contact <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a> to request EU-only data residency as part of a Data Processing Agreement.</p>
      </Section>

      <Section id="rights" title="11. Your Rights">
        <p>You have the right to:</p>
        <ul className="mt-3 list-disc ml-6 space-y-1 text-sm">
          <li><strong>Access</strong> — obtain a copy of personal data we hold about you.</li>
          <li><strong>Rectification</strong> — correct inaccurate data via your profile settings or by contacting us.</li>
          <li><strong>Erasure</strong> — request deletion of your account and personal data.</li>
          <li><strong>Data portability</strong> — download a machine-readable export of your SYNAPTIQ data via <em>Settings → Privacy → Export my data</em> (JSON format).</li>
          <li><strong>Restriction</strong> — request that we limit processing of your data in certain circumstances.</li>
          <li><strong>Object</strong> — object to processing based on legitimate interests, including use of your data for analytics.</li>
          <li><strong>Withdraw consent</strong> — withdraw consent for analytics cookies at any time via the cookie consent banner or Settings.</li>
        </ul>
        <p className="mt-4">To exercise rights other than consent withdrawal and data export (available in-product), email <a href="mailto:privacy@synaptiq.academy" className="editorial-link">privacy@synaptiq.academy</a>. We will respond within 30 days, free of charge, unless a request is manifestly unfounded or excessive.</p>
        <p className="mt-3">EU/EEA residents: see the <Link to="/gdpr" className="editorial-link">GDPR Notice</Link> for supervisory authority contacts and additional rights information.</p>
      </Section>

      <Section id="security" title="12. Security">
        <p>We implement technical and organisational measures appropriate to the risk of processing, including:</p>
        <ul className="mt-3 list-disc ml-6 space-y-1 text-sm">
          <li>TLS 1.2+ for all data in transit.</li>
          <li>AES-256 encryption at rest (MongoDB Atlas and AWS S3).</li>
          <li>bcrypt password hashing with per-user salts.</li>
          <li>httpOnly session cookies, CSRF double-submit protection, SameSite=Lax cookies.</li>
          <li>Rate limiting on authentication endpoints (5 requests/minute per IP).</li>
          <li>Account lockout after repeated failed login attempts.</li>
          <li>Role-based access control enforced server-side on every API request.</li>
          <li>Row-level data isolation: each user&rsquo;s data is accessible only to them and their authorised collaborators.</li>
          <li>Minimum-privilege AI context: only context necessary for the specific AI feature is transmitted.</li>
        </ul>
        <p className="mt-3">For full security details, see the <Link to="/security" className="editorial-link">Security page</Link>.</p>
        <p className="mt-3"><strong>Data breach notification.</strong> In the event of a personal data breach, we will notify the relevant supervisory authority within 72 hours of becoming aware, where required by GDPR Article 33. If a breach is likely to result in high risk to your rights and freedoms, we will notify you directly without undue delay at the email address on your account.</p>
      </Section>

      <Section id="children" title="13. Children">
        <p>SYNAPTIQ is not directed at users under 18 years of age. We do not knowingly collect personal data from anyone under 18. If we become aware that we have collected data from a person under 18 without appropriate consent, we will delete it promptly.</p>
      </Section>

      <Section id="changes" title="14. Changes to This Policy">
        <p>We may update this Privacy Policy when our practices change or applicable law requires it. Material changes will be communicated by email or in-app notification at least 14 days before taking effect. The &ldquo;last updated&rdquo; date at the top of this page reflects the current version. Continued use after the effective date constitutes acceptance of the updated policy.</p>
      </Section>

      <Section id="contact" title="15. Contact">
        <p>For privacy questions, data subject requests, or concerns about our data practices:</p>
        <ul className="mt-3 text-sm space-y-1">
          <li><strong>Email:</strong> <a href="mailto:privacy@synaptiq.academy" className="editorial-link">privacy@synaptiq.academy</a></li>
          <li><strong>Data export (self-service):</strong> Settings → Privacy → Export my data</li>
          <li><strong>General enquiries:</strong> <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a></li>
        </ul>
      </Section>
    </LegalLayout>
  );
}

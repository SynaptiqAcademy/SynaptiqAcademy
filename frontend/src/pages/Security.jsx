import React from "react";
import { Link } from "react-router-dom";
import { LegalLayout, Section, Callout } from "./legal/LegalLayout";

const SECTIONS = [
  { id: "infrastructure",          label: "1. Infrastructure" },
  { id: "authentication",          label: "2. Authentication" },
  { id: "encryption",              label: "3. Encryption" },
  { id: "data-protection",         label: "4. Data Protection" },
  { id: "ai-privacy",              label: "5. AI Privacy" },
  { id: "backups",                 label: "6. Backups" },
  { id: "monitoring",              label: "7. Monitoring" },
  { id: "incident-response",       label: "8. Incident Response" },
  { id: "compliance",              label: "9. Compliance" },
  { id: "responsible-disclosure",  label: "10. Responsible Disclosure" },
  { id: "contact-security",        label: "11. Contact Security" },
];

/* ── Status badge ──────────────────────────────────────────────────────────── */
function Enabled() {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      fontSize: "0.67rem", fontWeight: 600, letterSpacing: "0.06em",
      textTransform: "uppercase", flexShrink: 0,
      color: "var(--lc-muted)",
      background: "var(--lc-bg-alt)",
      border: "1px solid var(--lc-border)",
      borderRadius: 4, padding: "2px 8px",
    }}>
      ✓ Enabled
    </span>
  );
}

/* ── Feature card — lc-right-card style with Enabled badge ────────────────── */
function FeatureCard({ label, detail }) {
  return (
    <div className="lc-right-card" style={{ marginBottom: 10 }}>
      <div style={{
        display: "flex", alignItems: "flex-start",
        justifyContent: "space-between", gap: 12, marginBottom: 6,
      }}>
        <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--lc-text)" }}>
          {label}
        </span>
        <Enabled />
      </div>
      <p style={{ fontSize: "0.85rem", color: "var(--lc-muted)", lineHeight: 1.6, margin: 0 }}>
        {detail}
      </p>
    </div>
  );
}

/* ── Data ──────────────────────────────────────────────────────────────────── */
const INFRA_CARDS = [
  {
    label: "HTTPS Everywhere",
    detail: "All production traffic is served over HTTPS. HTTP connections are rejected outright at the network edge — not redirected, rejected. Traffic between internal services is also encrypted.",
  },
  {
    label: "Multi-Availability Zone",
    detail: "Infrastructure is distributed across multiple availability zones to eliminate single-point-of-failure risk and maintain availability during partial outages.",
  },
  {
    label: "Managed Database Hosting",
    detail: "Databases are hosted on MongoDB Atlas, which provides encryption at rest, automated patching, network-level isolation, and independent security certifications.",
  },
  {
    label: "EU Data Residency",
    detail: "EU data residency for database storage is available for institutional customers as part of a Data Processing Agreement. Contact contact@synaptiq.academy to request one.",
  },
];

const AUTH_FEATURES = [
  {
    label: "bcrypt Password Hashing",
    detail: "Passwords are hashed with bcrypt using per-user random salts. Plaintext passwords are never stored, logged, or transmitted internally after initial hashing.",
  },
  {
    label: "Short-Lived JWT Access Tokens",
    detail: "JWT access tokens are signed with HS256 and are short-lived. Refresh tokens are long-lived, stored in httpOnly cookies, and rotated on each use. All tokens are invalidated immediately on logout.",
  },
  {
    label: "httpOnly Cookie Security",
    detail: "Session cookies are httpOnly (not readable by JavaScript), Secure (HTTPS only in production), and SameSite=Lax to mitigate CSRF. A CSRF double-submit token is required for all state-changing requests.",
  },
  {
    label: "Single-Use Password Reset Tokens",
    detail: "Reset tokens are cryptographically signed, single-use, and expire within 30 minutes. Requesting a reset does not reveal whether an account exists for the given email address.",
  },
  {
    label: "Rate Limiting",
    detail: "Authentication endpoints are rate-limited by IP. Repeated failed login attempts trigger progressive delays. Automated credential-stuffing attempts are detected and rejected.",
  },
  {
    label: "Role-Based Access Control",
    detail: "Every API endpoint enforces role checks server-side. Users access only their own data. Administrative interfaces require elevated roles verified on every request — no client-side trust.",
  },
];

const ENCRYPTION_FEATURES = [
  {
    label: "TLS 1.3 in Transit",
    detail: "All data in transit is encrypted using TLS 1.3. TLS 1.2 is accepted for legacy client compatibility. Plaintext HTTP connections are rejected at the network edge.",
  },
  {
    label: "AES-256 at Rest",
    detail: "All stored data — databases, backups, and uploaded files — is encrypted at rest using AES-256. Encryption keys are managed by the cloud provider's key management service.",
  },
  {
    label: "HSTS Enforcement",
    detail: "HTTP Strict Transport Security is enforced with a minimum max-age of one year, instructing browsers to connect exclusively over HTTPS for all future requests.",
  },
];

const DATA_PROTECTION_CARDS = [
  {
    label: "Row-Level Ownership Enforcement",
    detail: "Authentication-enforced ownership checks are applied on every database read and write. There are no shared data tables without per-row ownership filtering.",
  },
  {
    label: "Collaboration Scope",
    detail: "Content shared in a collaboration is accessible only to invited collaborators, for the duration and scope of that collaboration. No content is publicly visible unless you explicitly publish it.",
  },
  {
    label: "Public Profile Control",
    detail: "Your public researcher profile surfaces only the fields you choose to display. Private notes, project details, draft manuscripts, and unpublished work are never surfaced on public pages.",
  },
  {
    label: "Staff Access",
    detail: "Synaptiq staff access to production data is restricted to personnel who require it for their role, follows the principle of least privilege, and is fully logged in the administrative audit log.",
  },
];

const BACKUP_CARDS = [
  {
    label: "Daily Automated Backups",
    detail: "Production databases are backed up daily. All backup data is encrypted at rest using AES-256, the same standard applied to live data.",
  },
  {
    label: "14-Day Point-in-Time Recovery",
    detail: "Point-in-time recovery is available for the preceding 14 days, allowing restoration to any one-minute interval within that window.",
  },
  {
    label: "Backup Isolation",
    detail: "Backups are stored in a separate storage environment from the primary database. A compromise of the primary environment does not affect backup integrity.",
  },
  {
    label: "Recovery Testing",
    detail: "Backup restoration procedures are tested periodically to verify recoverability. Recovery time objectives are evaluated as part of disaster recovery planning.",
  },
];

const MONITORING_FEATURES = [
  {
    label: "Administrative Audit Log",
    detail: "All administrative actions — role changes, account deletions, content moderation decisions — are recorded in a tamper-evident audit log retained for 3 years.",
  },
  {
    label: "Security Event Log",
    detail: "Failed logins, account lockouts, and anomalous access patterns are logged and retained for 12 months after account deletion.",
  },
  {
    label: "Application Server Logs",
    detail: "Application server logs are retained on a 30-day rolling basis for incident investigation and service reliability. Logs are not used for user profiling or advertising.",
  },
];

/* ════════════════════════════════════════════════════════════════════════════ */
export default function Security() {
  React.useEffect(() => {
    document.title = "Security Center — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  return (
    <LegalLayout
      eyebrow="Legal"
      title="Security Center"
      subtitle="How Synaptiq protects your research data — encryption, access controls, AI data handling, backups, and compliance. Everything documented, nothing vague."
      lastUpdated="29 June 2026"
      readingTime="7 min"
      version="v1.3"
      sections={SECTIONS}
    >

      {/* 1 ── Infrastructure ─────────────────────────────────────────────── */}
      <Section id="infrastructure" title="1. Infrastructure">
        <p>Synaptiq is hosted on managed cloud infrastructure. We do not operate physical data centres — instead we rely on cloud providers with enterprise-grade security controls and independent security audits. This allows us to inherit a hardened physical and network security baseline without managing it directly.</p>
        <p className="mt-3">All production traffic is served over HTTPS. HTTP connections are rejected at the network edge — not redirected, rejected. Traffic between internal services is also encrypted in transit.</p>
        <div className="mt-4 space-y-2">
          {INFRA_CARDS.map((item) => (
            <div key={item.label} className="lc-right-card">
              <div>{item.label}</div>
              <p>{item.detail}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* 2 ── Authentication ─────────────────────────────────────────────── */}
      <Section id="authentication" title="2. Authentication &amp; Session Security">
        <p>Every authentication flow is designed to eliminate the most common account compromise vectors: credential stuffing, session hijacking, and phishing. Authentication logic is enforced exclusively server-side — no security-relevant decisions are delegated to client code.</p>
        <div className="mt-4">
          {AUTH_FEATURES.map((f) => (
            <FeatureCard key={f.label} label={f.label} detail={f.detail} />
          ))}
        </div>
      </Section>

      {/* 3 ── Encryption ─────────────────────────────────────────────────── */}
      <Section id="encryption" title="3. Encryption">
        <p>Synaptiq applies encryption at every layer of the data path — in transit between the client and server, between internal services, and at rest in all storage systems including databases, backups, and file uploads.</p>
        <div className="mt-4">
          {ENCRYPTION_FEATURES.map((f) => (
            <FeatureCard key={f.label} label={f.label} detail={f.detail} />
          ))}
        </div>
      </Section>

      {/* 4 ── Data Protection ────────────────────────────────────────────── */}
      <Section id="data-protection" title="4. Data Protection &amp; Access Control">
        <p>Every read and write on the Synaptiq platform is governed by server-side authentication checks. There is no mechanism by which one user can access another user's data without an explicit collaboration invitation.</p>
        <div className="mt-4 space-y-2">
          {DATA_PROTECTION_CARDS.map((item) => (
            <div key={item.label} className="lc-right-card">
              <div>{item.label}</div>
              <p>{item.detail}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* 5 ── AI Privacy ─────────────────────────────────────────────────── */}
      <Section id="ai-privacy" title="5. AI Privacy">
        <p>Synaptiq AI features are powered by Anthropic's Claude API under enterprise API terms. These terms explicitly prohibit Anthropic from training models on your data. The following principles govern how your content interacts with AI services on the platform.</p>
        <Callout>
          You can use all non-AI features — researcher discovery, project management, collaboration, file repository, and analytics — without any content being sent to an AI provider.
        </Callout>
        <ul className="mt-3 list-disc ml-6 space-y-2">
          <li>Only the context strictly necessary for the specific AI feature is transmitted to the AI provider — not your full account, project list, or unrelated data.</li>
          <li>Context is sent over TLS-encrypted connections to Anthropic (Claude) under enterprise API terms that prohibit model training on your data.</li>
          <li>AI processing requests are not logged by Synaptiq in a way that associates them with your identity beyond what is necessary for credit accounting.</li>
          <li>AI-generated responses are processed ephemerally. Context from one AI request is not retained or reused in a subsequent, unrelated AI request.</li>
          <li>Synaptiq does not use your manuscript content, research notes, or project data to train, fine-tune, or improve any AI model.</li>
        </ul>
        <p className="mt-3">
          For the full policy governing AI data handling, see the{" "}
          <Link to="/ai-policy" className="editorial-link">AI Usage Policy</Link>.
        </p>
      </Section>

      {/* 6 ── Backups ────────────────────────────────────────────────────── */}
      <Section id="backups" title="6. Backups &amp; Recovery">
        <p>Synaptiq maintains automated backups of all production databases to protect against data loss from hardware failure, software defects, or accidental deletion.</p>
        <div className="mt-4 space-y-2">
          {BACKUP_CARDS.map((item) => (
            <div key={item.label} className="lc-right-card">
              <div>{item.label}</div>
              <p>{item.detail}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* 7 ── Monitoring ─────────────────────────────────────────────────── */}
      <Section id="monitoring" title="7. Monitoring &amp; Audit Logging">
        <p>Synaptiq maintains layered logging to support incident investigation, compliance verification, and accountability for administrative actions. Full retention periods are documented in the <Link to="/gdpr" className="editorial-link">GDPR Notice</Link> (Section 8).</p>
        <div className="mt-4">
          {MONITORING_FEATURES.map((f) => (
            <FeatureCard key={f.label} label={f.label} detail={f.detail} />
          ))}
        </div>
        <p className="mt-3">Logs are not used for behavioural profiling, advertising, or any purpose beyond platform security, reliability, and compliance.</p>
      </Section>

      {/* 8 ── Incident Response ──────────────────────────────────────────── */}
      <Section id="incident-response" title="8. Incident Response">
        <p>Synaptiq maintains an incident response process for security events, including suspected data breaches, unauthorised access, and service disruptions.</p>
        <ul className="mt-3 list-disc ml-6 space-y-2">
          <li><strong>Detection.</strong> Anomalous access patterns and security events are logged and subject to review. Critical alerts trigger an immediate investigation.</li>
          <li><strong>Containment.</strong> On confirmation of a security incident, affected systems are isolated and the attack surface is reduced before remediation begins.</li>
          <li><strong>GDPR notification.</strong> Where a personal data breach is likely to result in a risk to individuals' rights and freedoms, we will notify the relevant supervisory authority within 72 hours of becoming aware, as required under GDPR Article 33.</li>
          <li><strong>User notification.</strong> Where a breach is likely to result in a high risk to affected individuals, we will notify those individuals directly without undue delay, as required under GDPR Article 34.</li>
          <li><strong>Post-incident review.</strong> All significant security incidents are subject to a post-incident review to identify root cause and implement preventative measures.</li>
        </ul>
        <p className="mt-3">
          Institutional customers can request information about our incident response procedures as part of a Data Processing Agreement. Contact{" "}
          <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a>.
        </p>
      </Section>

      {/* 9 ── Compliance ─────────────────────────────────────────────────── */}
      <Section id="compliance" title="9. Compliance">
        <p>Synaptiq is designed with privacy and security compliance as a baseline requirement, not an afterthought. The following frameworks and obligations shape our security posture.</p>
        <div className="mt-4 overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Framework / Obligation</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["GDPR (Regulation (EU) 2016/679)", "Compliant — see GDPR Notice for detailed rights and processing bases"],
                ["Standard Contractual Clauses (EU 2021/914)", "Applied for EEA → US data transfers (Anthropic, Stripe, MongoDB Atlas, Resend, PostHog)"],
                ["Data Processing Agreements", "Available on request for institutional customers"],
                ["AI provider no-training commitment", "Anthropic enterprise API terms explicitly prohibit training on customer data"],
                ["GDPR Article 33 — breach notification (72 hours)", "Implemented in incident response process"],
                ["GDPR Article 17 — right to erasure", "Implemented: account deletion removes personal data within 30 days"],
              ].map(([framework, status]) => (
                <tr key={framework}>
                  <td>{framework}</td>
                  <td>{status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3">
          Synaptiq does not yet hold independent third-party security certifications (such as ISO 27001 or SOC 2 Type II) as a standalone entity. We rely on certifications held by our infrastructure and service providers. Enterprise customers may request our security posture documentation via{" "}
          <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a>.
        </p>
      </Section>

      {/* 10 ── Responsible Disclosure ────────────────────────────────────── */}
      <Section id="responsible-disclosure" title="10. Responsible Disclosure">
        <p>We take vulnerability reports seriously and are committed to working with security researchers to identify and resolve issues responsibly.</p>
        <p className="mt-3">
          To report a suspected security vulnerability, email a clear description of the issue and reproduction steps to{" "}
          <a href="mailto:security@synaptiq.academy" className="editorial-link">security@synaptiq.academy</a>. Please include:
        </p>
        <ul className="mt-3 list-disc ml-6 space-y-2">
          <li>A description of the vulnerability and its potential impact.</li>
          <li>Step-by-step reproduction instructions.</li>
          <li>Any proof-of-concept code or screenshots, if applicable.</li>
          <li>Your preferred contact method for follow-up.</li>
        </ul>
        <Callout>
          Please do not disclose vulnerabilities publicly before we have had reasonable time to investigate and respond. We will coordinate disclosure timing with you and aim to resolve critical issues within 30 days of confirmation.
        </Callout>
        <p className="mt-3">
          We acknowledge all reports within <strong>48 hours</strong> and publicly credit researchers who disclose responsibly, unless they prefer to remain anonymous. We do not pursue legal action against researchers who follow these guidelines and act in good faith.
        </p>
      </Section>

      {/* 11 ── Contact Security ──────────────────────────────────────────── */}
      <Section id="contact-security" title="11. Contact Security">
        <p>For security-related enquiries, use the most appropriate contact below.</p>
        <div className="mt-4 space-y-2">
          {[
            {
              label: "Vulnerability Reports",
              detail: "Report suspected security vulnerabilities, including reproduction steps and impact assessment.",
              email: "security@synaptiq.academy",
            },
            {
              label: "Privacy &amp; GDPR Requests",
              detail: "Exercise GDPR rights, request data exports, or raise privacy concerns.",
              email: "privacy@synaptiq.academy",
            },
            {
              label: "Enterprise &amp; Institutional",
              detail: "Request a Data Processing Agreement, sub-processor list, or security overview documentation.",
              email: "contact@synaptiq.academy",
            },
          ].map((item) => (
            <div key={item.label} className="lc-right-card">
              <div dangerouslySetInnerHTML={{ __html: item.label }} />
              <p>
                {item.detail}{" "}
                <a href={`mailto:${item.email}`} className="editorial-link">{item.email}</a>
              </p>
            </div>
          ))}
        </div>
        <p className="mt-4">
          For general questions about the platform, visit the{" "}
          <Link to="/contact" className="editorial-link">Contact page</Link>, or see the{" "}
          <Link to="/privacy" className="editorial-link">Privacy Policy</Link> and{" "}
          <Link to="/gdpr" className="editorial-link">GDPR Notice</Link> for data rights information.
        </p>
      </Section>

    </LegalLayout>
  );
}

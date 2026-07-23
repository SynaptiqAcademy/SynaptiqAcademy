import React from "react";
import { Link } from "react-router-dom";
import { LegalLayout, Section } from "./legal/LegalLayout";
import { Badge } from "@/components/ds";

const SECTIONS = [
  { id: "what",       label: "1. What Are Cookies" },
  { id: "essential",  label: "2. Essential Cookies" },
  { id: "analytics",  label: "3. Analytics Cookies" },
  { id: "posthog",    label: "4. PostHog (Analytics)" },
  { id: "other",      label: "5. Other Technologies" },
  { id: "consent",    label: "6. Your Consent Choices" },
  { id: "manage",     label: "7. Managing Cookies" },
  { id: "changes",    label: "8. Policy Changes" },
];

export default function Cookies() {
  React.useEffect(() => {
    document.title = "Cookie Policy — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  return (
    <LegalLayout
      eyebrow="Legal"
      title="Cookie Policy"
      subtitle="Every cookie and tracking technology on Synaptiq — what we set, why, and exactly how to control or remove them."
      lastUpdated="29 June 2026"
      readingTime="5 min"
      version="v1.2"
      sections={SECTIONS}
    >
      <Section id="what" title="1. What Are Cookies">
        <p>Cookies are small text files placed on your device by a website you visit. They allow the site to remember information about your visit — such as your authentication state, preferences, and how you interact with the Platform.</p>
        <p className="mt-3">We also use similar technologies such as localStorage (browser storage accessible to JavaScript) to store your consent preferences on your device.</p>
        <p className="mt-3">This policy describes every cookie and tracking technology we use on SYNAPTIQ, why we use it, and how to control it.</p>
      </Section>

      <Section id="essential" title="2. Essential Cookies">
        <p>Essential cookies are strictly necessary to operate the Platform. They cannot be disabled without breaking core functionality. We do not use them for tracking or advertising.</p>

        <div className="mt-4 space-y-4">
          <div style={{ border: "1px solid #e2e8f0", borderRadius: 8, overflow: "hidden" }}>
            <div style={{ background: "#F7F8FA", padding: "12px 16px", borderBottom: "1px solid #e2e8f0" }}>
              <span style={{ fontFamily: "monospace", fontWeight: 700, fontSize: "0.88rem", color: "#0f172a" }}>access_token</span>
              <Badge variant="success" style={{ marginLeft: 12 }}>Essential</Badge>
            </div>
            <div style={{ padding: "12px 16px" }}>
              <table style={{ width: "100%", fontSize: "0.82rem", borderCollapse: "collapse" }}>
                <tbody>
                  {[
                    ["Purpose", "Stores your JWT authentication token to keep you signed in"],
                    ["Type", "httpOnly cookie — cannot be read by JavaScript (XSS-resistant)"],
                    ["SameSite", "Lax — sent on same-site requests and top-level cross-site navigations"],
                    ["Lifetime", "15 minutes (refreshed automatically via refresh_token)"],
                    ["Set by", "SYNAPTIQ backend (synaptiq.academy)"],
                    ["Third party", "No — first-party only"],
                  ].map(([k, v]) => (
                    <tr key={k} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "5px 8px 5px 0", color: "#64748b", fontWeight: 500, width: 100 }}>{k}</td>
                      <td style={{ padding: "5px 0", color: "#374151" }}>{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div style={{ border: "1px solid #e2e8f0", borderRadius: 8, overflow: "hidden" }}>
            <div style={{ background: "#F7F8FA", padding: "12px 16px", borderBottom: "1px solid #e2e8f0" }}>
              <span style={{ fontFamily: "monospace", fontWeight: 700, fontSize: "0.88rem", color: "#0f172a" }}>refresh_token</span>
              <Badge variant="success" style={{ marginLeft: 12 }}>Essential</Badge>
            </div>
            <div style={{ padding: "12px 16px" }}>
              <table style={{ width: "100%", fontSize: "0.82rem", borderCollapse: "collapse" }}>
                <tbody>
                  {[
                    ["Purpose", "Allows the Platform to obtain a new access_token without requiring you to sign in again"],
                    ["Type", "httpOnly cookie — cannot be read by JavaScript (XSS-resistant)"],
                    ["SameSite", "Lax"],
                    ["Lifetime", "14 days"],
                    ["Set by", "SYNAPTIQ backend (synaptiq.academy)"],
                    ["Third party", "No — first-party only"],
                  ].map(([k, v]) => (
                    <tr key={k} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "5px 8px 5px 0", color: "#64748b", fontWeight: 500, width: 100 }}>{k}</td>
                      <td style={{ padding: "5px 0", color: "#374151" }}>{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div style={{ border: "1px solid #e2e8f0", borderRadius: 8, overflow: "hidden" }}>
            <div style={{ background: "#F7F8FA", padding: "12px 16px", borderBottom: "1px solid #e2e8f0" }}>
              <span style={{ fontFamily: "monospace", fontWeight: 700, fontSize: "0.88rem", color: "#0f172a" }}>csrf_token</span>
              <Badge variant="success" style={{ marginLeft: 12 }}>Essential</Badge>
            </div>
            <div style={{ padding: "12px 16px" }}>
              <table style={{ width: "100%", fontSize: "0.82rem", borderCollapse: "collapse" }}>
                <tbody>
                  {[
                    ["Purpose", "Cross-Site Request Forgery (CSRF) protection token, submitted as a header on every API request"],
                    ["Type", "JavaScript-readable (NOT httpOnly) — this is by design: the browser reads this value and includes it in request headers so the server can verify the request originates from our site"],
                    ["SameSite", "Lax"],
                    ["Lifetime", "15 minutes (refreshed with each access_token renewal)"],
                    ["Set by", "SYNAPTIQ backend (synaptiq.academy)"],
                    ["Third party", "No — first-party only"],
                  ].map(([k, v]) => (
                    <tr key={k} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "5px 8px 5px 0", color: "#64748b", fontWeight: 500, width: 110 }}>{k}</td>
                      <td style={{ padding: "5px 0", color: "#374151" }}>{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p style={{ fontSize: "0.78rem", color: "#94a3b8", marginTop: 10, lineHeight: 1.5 }}>
                <strong>Note on csrf_token JavaScript access:</strong> CSRF protection requires the frontend JavaScript to be able to read this cookie value and include it as a header in every API request. This is a standard &ldquo;double-submit cookie&rdquo; pattern. If this cookie were httpOnly, the CSRF protection mechanism would not function. The value has no authentication or session capability on its own.
              </p>
            </div>
          </div>
        </div>

        <p className="mt-4">These three cookies are the only cookies set by SYNAPTIQ&rsquo;s own servers. They are set when you sign in and cleared when you sign out or when they expire.</p>
      </Section>

      <Section id="analytics" title="3. Analytics Cookies (Third-Party)">
        <p>We use PostHog, a third-party product analytics platform, to understand how the Platform is used. PostHog sets its own cookies on your device when analytics consent is given via the cookie consent banner.</p>
        <p className="mt-3">Analytics cookies are <strong>optional</strong>. You can accept or reject them when the consent banner appears, or update your preferences at any time from <em>Settings &rarr; Privacy &rarr; Cookie preferences</em>.</p>
        <p className="mt-3">The following PostHog cookies may be set:</p>

        <div className="mt-4 space-y-4">
          {[
            {
              name: "ph_phc_*_posthog",
              purpose: "PostHog&rsquo;s primary persistence cookie. Stores an anonymous session/device identifier used to track product usage patterns across page loads.",
              lifetime: "365 days",
              type: "Analytics",
            },
            {
              name: "__ph_opt_in_out_*",
              purpose: "Stores your PostHog opt-in/opt-out preference.",
              lifetime: "365 days",
              type: "Analytics",
            },
          ].map((c) => (
            <div key={c.name} style={{ border: "1px solid #e2e8f0", borderRadius: 8, overflow: "hidden" }}>
              <div style={{ background: "#F7F8FA", padding: "12px 16px", borderBottom: "1px solid #e2e8f0" }}>
                <span style={{ fontFamily: "monospace", fontWeight: 700, fontSize: "0.88rem", color: "#0f172a" }}>{c.name}</span>
                <span style={{ marginLeft: 12, fontSize: "0.72rem", fontWeight: 600, background: "#DBEAFE", color: "#1e40af", padding: "2px 8px", borderRadius: 999 }}>Analytics</span>
                <span style={{ marginLeft: 8, fontSize: "0.72rem", fontWeight: 600, background: "#FEF9C3", color: "#854d0e", padding: "2px 8px", borderRadius: 999 }}>Consent required</span>
              </div>
              <div style={{ padding: "12px 16px" }}>
                <table style={{ width: "100%", fontSize: "0.82rem", borderCollapse: "collapse" }}>
                  <tbody>
                    {[
                      ["Purpose", c.purpose],
                      ["Lifetime", c.lifetime],
                      ["Set by", "PostHog (us.i.posthog.com)"],
                      ["Third party", "Yes — PostHog, US-based"],
                    ].map(([k, v]) => (
                      <tr key={k} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "5px 8px 5px 0", color: "#64748b", fontWeight: 500, width: 100 }}>{k}</td>
                        <td style={{ padding: "5px 0", color: "#374151" }} dangerouslySetInnerHTML={{ __html: v }} />
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section id="posthog" title="4. PostHog — Analytics Provider Details">
        <p>PostHog is a US-based product analytics and session recording platform. We use PostHog to understand which features are used, how users navigate the Platform, and where experience improvements are needed. We use this information solely to improve SYNAPTIQ; we do not share PostHog analytics data with advertisers.</p>

        <div className="mt-4 space-y-3">
          <div style={{ padding: "14px 16px", background: "#F7F8FA", borderRadius: 8 }}>
            <div style={{ fontWeight: 600, fontSize: "0.88rem", color: "#0f172a", marginBottom: 6 }}>What PostHog collects (subject to analytics consent)</div>
            <ul style={{ fontSize: "0.83rem", color: "#475569", lineHeight: 1.65, margin: 0, paddingLeft: 18 }}>
              <li>Pages visited and features used within the Platform.</li>
              <li>Browser type, operating system, and device type.</li>
              <li>Approximate geographic location (country/city level, derived from IP — IP is not stored by PostHog).</li>
              <li>Session recordings of your interactions with the Platform interface (mouse movements, clicks, scroll depth).</li>
              <li>When you are signed in and have given consent: your PostHog session is linked to your account identity.</li>
            </ul>
          </div>
          <div style={{ padding: "14px 16px", background: "#F7F8FA", borderRadius: 8 }}>
            <div style={{ fontWeight: 600, fontSize: "0.88rem", color: "#0f172a", marginBottom: 6 }}>PostHog configuration on SYNAPTIQ</div>
            <ul style={{ fontSize: "0.83rem", color: "#475569", lineHeight: 1.65, margin: 0, paddingLeft: 18 }}>
              <li><code>person_profiles: "identified_only"</code> — PostHog does not build a personal profile unless you are signed in and have given analytics consent.</li>
              <li>Session recording is enabled for authenticated users who have given analytics consent.</li>
              <li>PostHog&rsquo;s JavaScript initialises on page load to support feature flags and performance monitoring. When consent is not given, session recording and personal profiling are disabled; some anonymous event data may still be collected.</li>
              <li>Data is processed on PostHog&rsquo;s US infrastructure (<code>us.i.posthog.com</code>). Transfers are governed by Standard Contractual Clauses.</li>
            </ul>
          </div>
        </div>

        <p className="mt-4"><strong>Opting out of PostHog.</strong> Select &ldquo;Reject Non-Essential&rdquo; on the consent banner, or navigate to <em>Settings &rarr; Privacy &rarr; Cookie preferences</em> and disable the Analytics category. PostHog will not profile your session or record your interactions.</p>
        <p className="mt-3">PostHog&rsquo;s own privacy policy is available at <a href="https://posthog.com/privacy" target="_blank" rel="noopener noreferrer" className="editorial-link">posthog.com/privacy</a>.</p>
      </Section>

      <Section id="other" title="5. Other Browser Storage Technologies">
        <p><strong>localStorage.</strong> We use your browser&rsquo;s localStorage to store your cookie consent preferences (key: <code>synaptiq_consent_v1</code>). This is a first-party storage item; it does not leave your device except as reflected in the consent record sent to our backend when you make a consent decision.</p>
        <p className="mt-3"><strong>No advertising pixels.</strong> We do not use Facebook Pixel, Google Analytics, Google Tag Manager, Google Ads, or any other advertising network trackers. We do not serve targeted advertising on SYNAPTIQ.</p>
        <p className="mt-3"><strong>Stripe.</strong> The payment checkout flow is hosted by Stripe and may set Stripe&rsquo;s own cookies during a payment session. These cookies operate on Stripe&rsquo;s domain, not on SYNAPTIQ&rsquo;s domain. See <a href="https://stripe.com/privacy" target="_blank" rel="noopener noreferrer" className="editorial-link">stripe.com/privacy</a>.</p>
        <p className="mt-3"><strong>ORCID.</strong> If you connect your ORCID account, you will briefly visit ORCID&rsquo;s website during the OAuth flow. ORCID may set its own cookies during that session. See <a href="https://orcid.org/privacy-policy" target="_blank" rel="noopener noreferrer" className="editorial-link">orcid.org/privacy-policy</a>.</p>
      </Section>

      <Section id="consent" title="6. Your Consent Choices">
        <p>The cookie consent banner is shown to all new visitors. It presents four categories:</p>
        <div className="mt-4 space-y-2">
          {[
            { name: "Essential", locked: true, desc: "Always active. Required to operate the Platform. Cannot be disabled." },
            { name: "Analytics", locked: false, desc: "PostHog product analytics and session recording. Opt in to help us improve SYNAPTIQ." },
            { name: "Preferences", locked: false, desc: "Stores UI preferences and personalisation settings." },
            { name: "Marketing", locked: false, desc: "Used for marketing communications if you opt in. We do not currently serve advertising on the Platform." },
          ].map((cat) => (
            <div key={cat.name} style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: "12px 14px", background: "#F7F8FA", borderRadius: 8 }}>
              <div style={{ minWidth: 90, fontWeight: 600, fontSize: "0.85rem", color: "#0f172a", paddingTop: 1 }}>{cat.name}</div>
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: "0.83rem", color: "#475569", margin: 0, lineHeight: 1.55 }}>{cat.desc}</p>
              </div>
              <div>
                <span style={{ fontSize: "0.7rem", fontWeight: 600, padding: "2px 7px", borderRadius: 999, background: cat.locked ? "#DCFCE7" : "#F1F5F9", color: cat.locked ? "#166534" : "#64748b" }}>
                  {cat.locked ? "Always on" : "Optional"}
                </span>
              </div>
            </div>
          ))}
        </div>
        <p className="mt-4">Your consent decision is stored in localStorage (<code>synaptiq_consent_v1</code>) on your device and in a consent record on our servers. The server-side consent record stores a hashed and truncated IP address (not the full IP), your user agent, the consent preferences chosen, and the timestamp.</p>
        <p className="mt-3">You can update or withdraw consent at any time from <em>Settings &rarr; Privacy &rarr; Cookie preferences</em>. Withdrawing analytics consent stops new PostHog data collection; it does not erase historical PostHog event data already collected.</p>
      </Section>

      <Section id="manage" title="7. Managing Cookies via Your Browser">
        <p>You can also control cookies directly through your browser settings. Most browsers allow you to:</p>
        <ul className="mt-3 list-disc ml-6 space-y-1 text-sm">
          <li>View and delete cookies stored by specific sites.</li>
          <li>Block all third-party cookies.</li>
          <li>Set cookie preferences per site.</li>
        </ul>
        <p className="mt-3">Note that disabling essential cookies (such as <code>access_token</code> and <code>refresh_token</code>) will prevent you from signing in to SYNAPTIQ.</p>
        <p className="mt-3">Browser-level cookie deletion is independent of your consent settings in the Platform. If you delete cookies at the browser level, you may be prompted to make consent choices again on your next visit.</p>
        <p className="mt-3">For browser-specific instructions: <a href="https://support.google.com/chrome/answer/95647" target="_blank" rel="noopener noreferrer" className="editorial-link">Chrome</a>, <a href="https://support.mozilla.org/en-US/kb/cookies-information-websites-store-on-your-computer" target="_blank" rel="noopener noreferrer" className="editorial-link">Firefox</a>, <a href="https://support.apple.com/en-gb/guide/safari/sfri11471/mac" target="_blank" rel="noopener noreferrer" className="editorial-link">Safari</a>, <a href="https://support.microsoft.com/en-us/microsoft-edge/delete-cookies-in-microsoft-edge-63947406-40ac-c3b8-57b9-2a946a29ae09" target="_blank" rel="noopener noreferrer" className="editorial-link">Edge</a>.</p>
      </Section>

      <Section id="changes" title="8. Changes to This Policy">
        <p>We update this Cookie Policy when we add new tracking technologies, remove existing ones, or when a provider&rsquo;s data practices change. The &ldquo;last updated&rdquo; date at the top of this page reflects the current version.</p>
        <p className="mt-3">Material changes (such as adding a new third-party analytics provider) will be communicated by in-app notification and an updated consent prompt where required.</p>
        <p className="mt-3">Questions about cookies or tracking? Email <a href="mailto:privacy@synaptiq.academy" className="editorial-link">privacy@synaptiq.academy</a>.</p>
      </Section>
    </LegalLayout>
  );
}

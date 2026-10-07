import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import { TID } from "../lib/testIds";
import { fetchApi } from "@/lib/api";
import { setPageSeo } from "../lib/seo";
import { trackMarketingEvent as track } from "@/lib/marketingAnalytics";
import "../components/landing/landing.css";
import "./support.css";
import "./contact.css";

/*
 * Contact — one form for every kind of enquiry. Submissions go to POST
 * /api/contact, which stores each one before notifying the team. A topic
 * can be preselected from a link (/contact?topic=security|institution|...).
 * Institution enquiries show a few extra fields instead of a second form.
 */
const TOPICS = [
  ["", "Choose a topic"],
  ["general", "General question"],
  ["individual", "Individual plans"],
  ["institution", "Institutional plans"],
  ["support", "Help with your account"],
  ["security", "Security"],
  ["research", "Research collaboration"],
  ["partnership", "Partnerships and integrations"],
  ["press", "Press"],
  ["other", "Something else"],
];
const SIZES = ["", "1–10", "11–50", "51–200", "201–500", "500+"];

const QUESTIONS = [
  ["Can institutions ask about custom pricing?", <>Yes. Institutional plans are arranged directly with us and priced for the organisation. Choose <em>Institutional plans</em> above, or read <Link to="/for-institutions">For Institutions</Link> first.</>],
  ["Where do I find help with my account?", <>Most answers are in the <Link to="/help-center">Help Center</Link>. If yours isn't, choose <em>Help with your account</em> above.</>],
  ["How do I report a security issue?", <>Choose <em>Security</em> above and describe what you found and how to reproduce it. The <Link to="/security">Security</Link> page explains what to include, and asks you not to disclose the issue publicly before we've investigated.</>],
  ["How do I make a data protection request?", <>You can download or delete your data yourself in Settings → Privacy. For anything else, choose <em>General question</em> above and say it's a data protection request; <Link to="/gdpr">Data Protection</Link> lists your rights.</>],
];

export default function Contact() {
  const [params] = useSearchParams();
  const initialTopic = TOPICS.some(([v]) => v && v === params.get("topic")) ? params.get("topic") : "";
  const [f, setF] = useState({ name: "", email: "", organization: "", role: "", topic: initialTopic, message: "", size: "", country: "" });
  const [state, setState] = useState("idle"); // idle | sending | sent | error
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const isInstitution = f.topic === "institution";

  useEffect(() => setPageSeo({
    title: "Contact | Synaptiq",
    description: "Contact Synaptiq about plans, institutional use, your account, security or research collaboration.",
    path: "/contact",
  }), []);

  const submit = async (e) => {
    e.preventDefault();
    setState("sending");
    const extra = isInstitution
      ? `\n\nCountry: ${f.country || "—"}\nResearchers: ${f.size || "—"}`
      : "";
    try {
      const res = await fetchApi("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: f.name.trim(), email: f.email.trim(), topic: f.topic || "general",
          message: `${f.message.trim()}${extra}`,
          organization: f.organization.trim() || null, role: f.role.trim() || null,
        }),
      });
      if (!res.ok) throw new Error("not ok");
      setState("sent");
      if (["institution", "enterprise"].includes(f.topic)) track("institutional_inquiry_submitted", { topic: f.topic, source: "contact_form" });
    } catch {
      setState("error");
    }
  };

  return (
    <MarketingLayout>
      <div className="lp sp ct">
        <header className="sp-head">
          <div className="lp-wrap">
            <div className="lp-mono sp-crumb"><b>Company</b><span aria-hidden="true"> / </span>Contact</div>
            <h1 className="sp-title">Contact Synaptiq</h1>
            <p className="sp-dek">Questions about plans, institutional use, your account or security. Tell us what you need and we'll reply by email.</p>
          </div>
        </header>

        <div className="lp-wrap sp-body">
          <section className="sp-section" aria-labelledby="ct-form-h">
            <h2 id="ct-form-h" className="sp-h2">Send us a message</h2>
            {state === "sent" ? (
              <div className="ct-done" role="status">
                <p><strong>Thank you. Your message has been received.</strong></p>
                <p>We'll reply to {f.email}.</p>
              </div>
            ) : (
              <form className="ct-form" data-testid={TID.contactForm} onSubmit={submit} noValidate={false}>
                <div className="ct-grid">
                  <label className="ct-field"><span>Name</span>
                    <input data-testid={TID.contactName} required value={f.name} onChange={set("name")} autoComplete="name" maxLength={120} /></label>
                  <label className="ct-field"><span>Email</span>
                    <input data-testid={TID.contactEmail} required type="email" value={f.email} onChange={set("email")} autoComplete="email" maxLength={200} /></label>
                  <label className="ct-field"><span>Organisation <em>(optional)</em></span>
                    <input value={f.organization} onChange={set("organization")} autoComplete="organization" maxLength={200} /></label>
                  <label className="ct-field"><span>Role <em>(optional)</em></span>
                    <input value={f.role} onChange={set("role")} maxLength={120} /></label>
                </div>
                <label className="ct-field"><span>Topic</span>
                  <select id="ct-topic" required value={f.topic} onChange={set("topic")}>
                    {TOPICS.map(([v, l]) => <option key={v} value={v} disabled={!v}>{l}</option>)}
                  </select></label>
                {isInstitution && (
                  <div className="ct-grid">
                    <label className="ct-field"><span>Country <em>(optional)</em></span>
                      <input value={f.country} onChange={set("country")} autoComplete="country-name" maxLength={80} /></label>
                    <label className="ct-field"><span>Number of researchers <em>(optional)</em></span>
                      <select value={f.size} onChange={set("size")}>
                        {SIZES.map((s) => <option key={s} value={s}>{s || "Choose a range"}</option>)}
                      </select></label>
                  </div>
                )}
                <label className="ct-field"><span>Message</span>
                  <textarea data-testid={TID.contactMessage} required rows={6} value={f.message} onChange={set("message")} maxLength={5000}
                    placeholder={isInstitution ? "Your departments, how membership should work, and what you'd like people to be able to find." : ""} /></label>
                {state === "error" && <p className="ct-error" role="alert">Your message couldn't be sent. Please try again in a moment.</p>}
                <div className="ct-actions">
                  <button data-testid={TID.contactSubmit} type="submit" className="lp-btn lp-btn--primary" disabled={state === "sending"}>
                    {state === "sending" ? "Sending…" : "Send message"}
                  </button>
                  <p className="ct-fine">We use what you send only to reply. See the <Link to="/privacy">Privacy Policy</Link>.</p>
                </div>
              </form>
            )}
          </section>

          <section className="sp-section" aria-labelledby="ct-q-h">
            <h2 id="ct-q-h" className="sp-h2">Before you write</h2>
            <div className="sp-faq">
              {QUESTIONS.map(([q, a]) => (
                <details key={q}><summary>{q}</summary><div className="sp-answer">{a}</div></details>
              ))}
            </div>
          </section>

          <p className="sp-next">New to Synaptiq? <Link to="/platform">See how the platform fits together</Link> · <Link to="/pricing">Pricing</Link></p>
        </div>
      </div>
    </MarketingLayout>
  );
}

import React, { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import { toast } from "sonner";
import { Mail, ArrowRight, Send, CheckCircle2, ChevronDown } from "lucide-react";
import { TID } from "../lib/testIds";

/* ─── Design tokens ──────────────────────────────────────────────────────── */
const NAVY   = "#0F2847";
const SLATE  = "#64748b";
const BORDER = "#e2e8f0";
const BG_ALT = "#f9fafb";

/* ─── Data ───────────────────────────────────────────────────────────────── */

const CHANNELS = [
  { label: "Sales",    email: "sales@synaptiq.academy",    description: "Questions about subscriptions, pricing and institutions." },
  { label: "Support",  email: "support@synaptiq.academy",  description: "Technical support and account assistance." },
  { label: "Security", email: "security@synaptiq.academy", description: "Security reports and vulnerability disclosure." },
  { label: "Privacy",  email: "privacy@synaptiq.academy",  description: "GDPR and personal data requests." },
  { label: "General",  email: "hello@synaptiq.academy",    description: "General questions." },
];

const TOPICS = [
  { value: "",            label: "I want information about…" },
  { value: "individual",  label: "Individual subscription" },
  { value: "institution", label: "Institution" },
  { value: "enterprise",  label: "Enterprise" },
  { value: "support",     label: "Technical Support" },
  { value: "security",    label: "Security" },
  { value: "partnership", label: "Partnership" },
  { value: "research",    label: "Research Collaboration" },
  { value: "other",       label: "Other" },
];

const RESEARCHER_COUNTS = [
  { value: "",       label: "Number of researchers" },
  { value: "1-10",   label: "1–10" },
  { value: "11-50",  label: "11–50" },
  { value: "51-200", label: "51–200" },
  { value: "201-500",label: "201–500" },
  { value: "500+",   label: "500+" },
];

const CONTACT_METHODS = [
  { value: "",       label: "Preferred contact method" },
  { value: "email",  label: "Email" },
  { value: "video",  label: "Video call" },
  { value: "phone",  label: "Phone" },
];

const FAQ = [
  {
    q: "How long does it take to receive a reply?",
    a: "We aim to reply to all messages within 2 working days. For urgent security issues, email security@synaptiq.academy — we acknowledge all reports within 48 hours.",
  },
  {
    q: "Can institutions request custom pricing?",
    a: "Yes. Institutional pricing is available for universities, research institutes, and government research agencies. Submit a demo request or email sales@synaptiq.academy with the subject 'Institutional pricing' and we will arrange a conversation.",
  },
  {
    q: "Can I migrate existing research?",
    a: "Yes. Synaptiq supports importing references, manuscripts, and project data from common research formats. Institutional customers can request dedicated onboarding support and data migration assistance.",
  },
  {
    q: "Do you support universities?",
    a: "Yes. Synaptiq is built specifically for academic institutions. We work with universities, medical schools, research institutes, doctoral schools, and government research agencies. Institutional plans include team management, analytics, compliance reporting, and dedicated support.",
  },
  {
    q: "How do I report a security issue?",
    a: "Email security@synaptiq.academy with a description of the vulnerability and reproduction steps. We acknowledge all reports within 48 hours and credit researchers who disclose responsibly. Please do not disclose publicly until we have had time to respond.",
  },
];

const TRUST = [
  { label: "GDPR Compliant",             desc: "Data processed in accordance with EU Regulation 2016/679." },
  { label: "Privacy First",              desc: "No data sold. No advertising. No hidden profiling." },
  { label: "Research Data Ownership",    desc: "Your research, manuscripts, and projects remain yours." },
  { label: "Enterprise Security",        desc: "TLS 1.3, AES-256 at rest, HTTPS everywhere." },
  { label: "AI Privacy",                 desc: "AI providers are contractually prohibited from training on your data." },
];

/* ─── Form primitives ────────────────────────────────────────────────────── */

const INPUT_BASE = {
  width: "100%", boxSizing: "border-box",
  padding: "11px 14px",
  borderRadius: 8,
  border: `1px solid ${BORDER}`,
  fontSize: "0.875rem",
  color: "#0f172a",
  background: "#fff",
  outline: "none",
  fontFamily: "inherit",
  lineHeight: 1.5,
  transition: "border-color 140ms, box-shadow 140ms",
};

function FL({ children, htmlFor }) {
  return (
    <label htmlFor={htmlFor} style={{ display: "block", fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: SLATE, marginBottom: 7 }}>
      {children}
    </label>
  );
}

function Input(props) {
  const [focused, setFocused] = useState(false);
  return (
    <input
      {...props}
      style={{ ...INPUT_BASE, borderColor: focused ? NAVY : BORDER, boxShadow: focused ? "0 0 0 3px rgba(15,40,71,0.07)" : "none" }}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    />
  );
}

function Textarea(props) {
  const [focused, setFocused] = useState(false);
  return (
    <textarea
      {...props}
      style={{ ...INPUT_BASE, resize: "vertical", minHeight: 120, borderColor: focused ? NAVY : BORDER, boxShadow: focused ? "0 0 0 3px rgba(15,40,71,0.07)" : "none" }}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    />
  );
}

function Select({ children, ...props }) {
  const [focused, setFocused] = useState(false);
  return (
    <select
      {...props}
      style={{
        ...INPUT_BASE, cursor: "pointer",
        appearance: "none",
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E")`,
        backgroundRepeat: "no-repeat", backgroundPosition: "right 13px center", paddingRight: 36,
        borderColor: focused ? NAVY : BORDER, boxShadow: focused ? "0 0 0 3px rgba(15,40,71,0.07)" : "none",
      }}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    >
      {children}
    </select>
  );
}

function FaqItem({ q, a, open, onToggle }) {
  return (
    <div style={{ borderBottom: `1px solid ${BORDER}` }}>
      <button
        onClick={onToggle}
        style={{ width: "100%", background: "none", border: "none", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "20px 0", textAlign: "left", gap: 16, fontFamily: "inherit" }}
      >
        <span style={{ fontSize: "0.93rem", fontWeight: 600, color: "#0f172a", lineHeight: 1.5 }}>{q}</span>
        <ChevronDown size={16} strokeWidth={2} style={{ color: SLATE, flexShrink: 0, transition: "transform 200ms", transform: open ? "rotate(180deg)" : "none" }} />
      </button>
      <div style={{ maxHeight: open ? 400 : 0, overflow: "hidden", transition: "max-height 220ms ease-out" }}>
        <p style={{ fontSize: "0.875rem", color: "#475569", lineHeight: 1.8, paddingBottom: 20, margin: 0 }}>{a}</p>
      </div>
    </div>
  );
}

function SuccessCard({ onReset }) {
  return (
    <div style={{ textAlign: "center", padding: "56px 24px" }}>
      <div style={{ width: 48, height: 48, borderRadius: "50%", background: "#f0fdf4", border: "1px solid #bbf7d0", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px" }}>
        <CheckCircle2 size={22} strokeWidth={1.5} style={{ color: "#16a34a" }} />
      </div>
      <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#0f172a", marginBottom: 10 }}>Message received</div>
      <p style={{ fontSize: "0.875rem", color: SLATE, lineHeight: 1.75, maxWidth: 360, margin: "0 auto 24px" }}>
        We've received your message and will get back to you personally within 2 working days.
      </p>
      <button onClick={onReset} style={{ fontSize: "0.8rem", color: SLATE, background: "none", border: "none", cursor: "pointer", textDecoration: "underline", fontFamily: "inherit" }}>
        Send another message
      </button>
    </div>
  );
}

/* ─── Component ──────────────────────────────────────────────────────────── */

export default function Contact() {
  useEffect(() => {
    document.title = "Contact — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const [searchParams] = useSearchParams();

  const [form, setForm] = useState({
    firstName: "", lastName: "", email: "", organization: "",
    country: "", role: "", subject: "", message: "",
    topic: searchParams.get("topic") || "",
  });
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [demo, setDemo] = useState({
    name: "", email: "", organization: "", country: "",
    researchers: "", challenges: "", contactMethod: "",
  });
  const [demoSent, setDemoSent] = useState(false);
  const [demoSubmitting, setDemoSubmitting] = useState(false);

  const [faqOpen, setFaqOpen] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const setD  = (k) => (e) => setDemo((d) => ({ ...d, [k]: e.target.value }));

  const submitContact = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: `${form.firstName} ${form.lastName}`.trim(),
          email: form.email,
          topic: form.topic || "general",
          message: `[${form.subject || "No subject"}]\n\nOrganization: ${form.organization}\nCountry: ${form.country}\nRole: ${form.role}\n\n${form.message}`,
        }),
      });
      if (!res.ok) throw new Error("Server error");
      setSent(true);
      toast.success("Message sent — we'll reply within 2 working days.");
    } catch {
      toast.error("Could not send message. Please email hello@synaptiq.academy directly.");
    } finally {
      setSubmitting(false);
    }
  };

  const submitDemo = async (e) => {
    e.preventDefault();
    setDemoSubmitting(true);
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: demo.name,
          email: demo.email,
          topic: "institution",
          message: `[Demo Request]\n\nOrganization: ${demo.organization}\nCountry: ${demo.country}\nResearchers: ${demo.researchers}\nPreferred contact: ${demo.contactMethod}\n\nChallenges:\n${demo.challenges}`,
        }),
      });
      if (!res.ok) throw new Error("Server error");
      setDemoSent(true);
      toast.success("Demo request received — we'll be in touch shortly.");
    } catch {
      toast.error("Could not send request. Please email sales@synaptiq.academy directly.");
    } finally {
      setDemoSubmitting(false);
    }
  };

  const SUBMIT_BTN = {
    display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
    width: "100%", padding: "13px 28px", borderRadius: 8, border: "none",
    background: NAVY, color: "#fff", fontSize: "0.9rem", fontWeight: 600,
    fontFamily: "inherit", cursor: "pointer", transition: "opacity 140ms",
  };

  return (
    <MarketingLayout>
      <style>{`
        .ct-channel:hover { box-shadow: 0 4px 20px rgba(15,40,71,0.07) !important; border-color: #c9d4e0 !important; }
        .ct-trust:hover   { border-color: #c9d4e0 !important; }
        @media (max-width: 900px) {
          .ct-ch-grid  { grid-template-columns: repeat(3, 1fr) !important; }
          .ct-tr-grid  { grid-template-columns: repeat(3, 1fr) !important; }
        }
        @media (max-width: 580px) {
          .ct-ch-grid  { grid-template-columns: 1fr 1fr !important; }
          .ct-tr-grid  { grid-template-columns: 1fr 1fr !important; }
          .ct-row2     { grid-template-columns: 1fr !important; }
        }
        @media (max-width: 380px) {
          .ct-ch-grid  { grid-template-columns: 1fr !important; }
          .ct-tr-grid  { grid-template-columns: 1fr !important; }
        }
      `}</style>

      {/* ═══════════════════════════════════════════════════════════════════
          HERO
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, padding: "96px 0 88px" }}>
        <div style={{ maxWidth: 680, margin: "0 auto", padding: "0 32px", textAlign: "center" }}>
          <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 20 }}>
            Contact
          </div>
          <h1 style={{
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: "clamp(2.2rem, 5vw, 3.2rem)",
            fontWeight: 700, color: "#0f172a",
            lineHeight: 1.1, letterSpacing: "-0.025em",
            margin: "0 0 20px",
          }}>
            Contact Synaptiq
          </h1>
          <p style={{ fontSize: "1.05rem", color: "#334155", lineHeight: 1.75, maxWidth: 500, margin: "0 auto 10px" }}>
            Helping researchers and institutions build better research.
          </p>
          <p style={{ fontSize: "0.9rem", color: SLATE, lineHeight: 1.7, maxWidth: 460, margin: "0 auto 36px" }}>
            We respond to every message personally — whether you're an individual researcher, a department head, or an institution.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <a
              href="#contact-form"
              style={{ display: "inline-flex", alignItems: "center", gap: 8, background: NAVY, color: "#fff", padding: "12px 28px", borderRadius: 8, fontSize: "0.9rem", fontWeight: 600, textDecoration: "none" }}
            >
              Contact Sales
            </a>
            <Link
              to="/register"
              style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "#fff", color: "#0f172a", padding: "11px 24px", borderRadius: 8, fontSize: "0.9rem", fontWeight: 600, textDecoration: "none", border: `1px solid ${BORDER}` }}
            >
              Get Started <ArrowRight size={14} strokeWidth={2} />
            </Link>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 1 — CONTACT CARDS
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: BG_ALT, padding: "72px 0" }}>
        <div style={{ maxWidth: 1040, margin: "0 auto", padding: "0 32px" }}>
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 12 }}>
              Direct channels
            </div>
            <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.4rem, 2.5vw, 1.85rem)", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: 0 }}>
              Reach the right team.
            </h2>
          </div>
          <div className="ct-ch-grid" style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14 }}>
            {CHANNELS.map((ch) => (
              <div
                key={ch.label}
                className="ct-channel"
                style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 12, padding: "22px 18px", display: "flex", flexDirection: "column", gap: 10, transition: "box-shadow 160ms, border-color 160ms" }}
              >
                <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8" }}>{ch.label}</div>
                <a
                  href={`mailto:${ch.email}`}
                  style={{ fontSize: "0.76rem", fontWeight: 600, color: NAVY, textDecoration: "none", display: "flex", alignItems: "center", gap: 5, wordBreak: "break-all", lineHeight: 1.4 }}
                  onMouseEnter={(e) => { e.currentTarget.style.textDecoration = "underline"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.textDecoration = "none"; }}
                >
                  <Mail size={11} strokeWidth={1.5} style={{ flexShrink: 0 }} />
                  {ch.email}
                </a>
                <p style={{ fontSize: "0.78rem", color: SLATE, lineHeight: 1.65, margin: 0 }}>{ch.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 2 — CONTACT FORM
      ═══════════════════════════════════════════════════════════════════ */}
      <section id="contact-form" style={{ background: "#fff", borderTop: `1px solid ${BORDER}`, padding: "80px 0" }}>
        <div style={{ maxWidth: 680, margin: "0 auto", padding: "0 32px" }}>
          <div style={{ marginBottom: 44 }}>
            <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 12 }}>Get in touch</div>
            <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.4rem, 2.5vw, 1.85rem)", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 12px" }}>
              Send us a message.
            </h2>
            <p style={{ fontSize: "0.9rem", color: SLATE, lineHeight: 1.7, margin: 0 }}>
              We read every message and respond within 2 working days.
            </p>
          </div>

          {sent ? (
            <SuccessCard onReset={() => setSent(false)} />
          ) : (
            <form data-testid={TID.contactForm} onSubmit={submitContact} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div className="ct-row2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>
                  <FL htmlFor="ct-firstName">First Name</FL>
                  <Input id="ct-firstName" data-testid={TID.contactName} required placeholder="Jane" value={form.firstName} onChange={set("firstName")} autoComplete="given-name" />
                </div>
                <div>
                  <FL htmlFor="ct-lastName">Last Name</FL>
                  <Input id="ct-lastName" required placeholder="Researcher" value={form.lastName} onChange={set("lastName")} autoComplete="family-name" />
                </div>
              </div>

              <div className="ct-row2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>
                  <FL htmlFor="ct-email">Email</FL>
                  <Input id="ct-email" data-testid={TID.contactEmail} required type="email" placeholder="jane@university.edu" value={form.email} onChange={set("email")} autoComplete="email" />
                </div>
                <div>
                  <FL htmlFor="ct-org">Organization</FL>
                  <Input id="ct-org" placeholder="University of…" value={form.organization} onChange={set("organization")} autoComplete="organization" />
                </div>
              </div>

              <div className="ct-row2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>
                  <FL htmlFor="ct-country">Country</FL>
                  <Input id="ct-country" placeholder="Country" value={form.country} onChange={set("country")} autoComplete="country-name" />
                </div>
                <div>
                  <FL htmlFor="ct-role">Role</FL>
                  <Input id="ct-role" placeholder="Researcher / Director / Other" value={form.role} onChange={set("role")} />
                </div>
              </div>

              <div>
                <FL htmlFor="ct-subject">Subject</FL>
                <Input id="ct-subject" placeholder="How can we help?" value={form.subject} onChange={set("subject")} />
              </div>

              <div>
                <FL htmlFor="ct-topic">I want information about</FL>
                <Select id="ct-topic" value={form.topic} onChange={set("topic")}>
                  {TOPICS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </Select>
              </div>

              <div>
                <FL htmlFor="ct-message">Message</FL>
                <Textarea
                  id="ct-message"
                  data-testid={TID.contactMessage}
                  required rows={5}
                  placeholder="Tell us what you're working on, what you need, or any question you have…"
                  value={form.message} onChange={set("message")}
                />
              </div>

              <div style={{ height: 1, background: "#f1f5f9" }} />

              <button data-testid={TID.contactSubmit} type="submit" disabled={submitting} style={{ ...SUBMIT_BTN, opacity: submitting ? 0.65 : 1, cursor: submitting ? "not-allowed" : "pointer" }}>
                <Send size={14} strokeWidth={2} />
                {submitting ? "Sending…" : "Send Message"}
              </button>

              <p style={{ fontSize: "0.72rem", color: "#94a3b8", textAlign: "center", margin: 0 }}>
                By submitting you agree to our{" "}
                <Link to="/privacy" style={{ color: SLATE, textDecoration: "underline" }}>Privacy Policy</Link>.
                {" "}We do not use this form for marketing.
              </p>
            </form>
          )}
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 3 — BOOK A DEMO
      ═══════════════════════════════════════════════════════════════════ */}
      <section id="book-demo" style={{ background: BG_ALT, borderTop: `1px solid ${BORDER}`, padding: "80px 0" }}>
        <div style={{ maxWidth: 680, margin: "0 auto", padding: "0 32px" }}>
          <div style={{ marginBottom: 44 }}>
            <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 12 }}>Institution</div>
            <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.4rem, 2.5vw, 1.85rem)", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 12px" }}>
              Book a Demo
            </h2>
            <p style={{ fontSize: "0.9rem", color: SLATE, lineHeight: 1.7, margin: 0 }}>
              We will reach out to understand your institution's needs and arrange a conversation with the right team member. No scheduling tools, no calendar links.
            </p>
          </div>

          {demoSent ? (
            <SuccessCard onReset={() => setDemoSent(false)} />
          ) : (
            <form onSubmit={submitDemo} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <div className="ct-row2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>
                  <FL>Name</FL>
                  <Input required placeholder="Your full name" value={demo.name} onChange={setD("name")} autoComplete="name" />
                </div>
                <div>
                  <FL>Work Email</FL>
                  <Input required type="email" placeholder="name@institution.edu" value={demo.email} onChange={setD("email")} autoComplete="email" />
                </div>
              </div>

              <div className="ct-row2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>
                  <FL>Organization</FL>
                  <Input required placeholder="University / Institute" value={demo.organization} onChange={setD("organization")} />
                </div>
                <div>
                  <FL>Country</FL>
                  <Input placeholder="Country" value={demo.country} onChange={setD("country")} autoComplete="country-name" />
                </div>
              </div>

              <div className="ct-row2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>
                  <FL>Number of Researchers</FL>
                  <Select value={demo.researchers} onChange={setD("researchers")}>
                    {RESEARCHER_COUNTS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                  </Select>
                </div>
                <div>
                  <FL>Preferred Contact Method</FL>
                  <Select value={demo.contactMethod} onChange={setD("contactMethod")}>
                    {CONTACT_METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
                  </Select>
                </div>
              </div>

              <div>
                <FL>Current Challenges</FL>
                <Textarea
                  rows={4}
                  placeholder="What research management challenges is your institution facing? What are you hoping Synaptiq can help with?"
                  value={demo.challenges} onChange={setD("challenges")}
                />
              </div>

              <div style={{ height: 1, background: BORDER }} />

              <button type="submit" disabled={demoSubmitting} style={{ ...SUBMIT_BTN, opacity: demoSubmitting ? 0.65 : 1, cursor: demoSubmitting ? "not-allowed" : "pointer" }}>
                {demoSubmitting ? "Sending…" : "Submit Request"}
              </button>

              <p style={{ fontSize: "0.72rem", color: "#94a3b8", textAlign: "center", margin: 0 }}>
                No scheduling tool. We will contact you directly within 2 working days.
              </p>
            </form>
          )}
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 4 — FAQ
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderTop: `1px solid ${BORDER}`, padding: "80px 0" }}>
        <div style={{ maxWidth: 680, margin: "0 auto", padding: "0 32px" }}>
          <div style={{ marginBottom: 44 }}>
            <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 12 }}>Questions</div>
            <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.4rem, 2.5vw, 1.85rem)", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: 0 }}>
              Frequently asked.
            </h2>
          </div>
          <div>
            {FAQ.map((item, i) => (
              <FaqItem key={i} q={item.q} a={item.a} open={faqOpen === i} onToggle={() => setFaqOpen(faqOpen === i ? null : i)} />
            ))}
          </div>
          <p style={{ fontSize: "0.85rem", color: SLATE, lineHeight: 1.7, marginTop: 36 }}>
            Didn't find your answer?{" "}
            <a href="mailto:hello@synaptiq.academy" style={{ color: NAVY, fontWeight: 600, textDecoration: "underline" }}>Email us directly</a>
            {" "}or use the contact form above.
          </p>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 5 — ENTERPRISE TRUST
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: BG_ALT, borderTop: `1px solid ${BORDER}`, padding: "72px 0" }}>
        <div style={{ maxWidth: 1040, margin: "0 auto", padding: "0 32px" }}>
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 12 }}>Platform foundations</div>
            <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.4rem, 2.5vw, 1.85rem)", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: 0 }}>
              Built on trust.
            </h2>
          </div>
          <div className="ct-tr-grid" style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14 }}>
            {TRUST.map((t) => (
              <div key={t.label} className="ct-trust" style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 12, padding: "20px 18px", transition: "border-color 160ms" }}>
                <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>{t.label}</div>
                <p style={{ fontSize: "0.77rem", color: SLATE, lineHeight: 1.65, margin: 0 }}>{t.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          FOOTER CTA
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderTop: `1px solid ${BORDER}`, padding: "80px 0" }}>
        <div style={{ maxWidth: 560, margin: "0 auto", padding: "0 32px", textAlign: "center" }}>
          <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.5rem, 3vw, 2.1rem)", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 16px" }}>
            Ready to modernize research?
          </h2>
          <p style={{ fontSize: "0.9rem", color: SLATE, lineHeight: 1.7, margin: "0 0 36px" }}>
            Start for free and explore the platform at your own pace. No credit card required.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <Link
              to="/register"
              style={{ display: "inline-flex", alignItems: "center", gap: 8, background: NAVY, color: "#fff", padding: "12px 28px", borderRadius: 8, fontSize: "0.9rem", fontWeight: 600, textDecoration: "none" }}
            >
              Get Started <ArrowRight size={14} strokeWidth={2} />
            </Link>
            <a
              href="#contact-form"
              style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "#fff", color: "#0f172a", padding: "11px 24px", borderRadius: 8, fontSize: "0.9rem", fontWeight: 600, textDecoration: "none", border: `1px solid ${BORDER}` }}
            >
              Contact Sales
            </a>
          </div>
        </div>
      </section>

    </MarketingLayout>
  );
}

/* eslint-disable */
import React, { useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import {
  Shield, FileText, Cookie, Globe, Lock,
  ArrowRight, Clock, Calendar, ChevronRight,
  Mail, ExternalLink,
} from "lucide-react";

/* ─── Shared reveal hook ────────────────────────────────────────────────────── */
function useReveal(threshold = 0.06) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    if (typeof IntersectionObserver === "undefined") { el.classList.add("lc-hub-in"); return; }
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { el.classList.add("lc-hub-in"); obs.disconnect(); }
    }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return ref;
}

const HUB_CSS = `
  .lc-hub-fade { opacity: 0; transform: translateY(20px); transition: opacity 0.6s ease, transform 0.6s ease; }
  .lc-hub-fade.lc-hub-in { opacity: 1; transform: none; }
  .lc-hub-fade.d1.lc-hub-in { transition-delay: 0.08s; }
  .lc-hub-fade.d2.lc-hub-in { transition-delay: 0.16s; }
  .lc-hub-fade.d3.lc-hub-in { transition-delay: 0.24s; }
  .lc-hub-fade.d4.lc-hub-in { transition-delay: 0.32s; }
  .lc-hub-fade.d5.lc-hub-in { transition-delay: 0.40s; }

  .lc-doc-card {
    display: flex;
    flex-direction: column;
    text-decoration: none;
    background: #fff;
    border: 1px solid #e4e8ef;
    border-radius: 14px;
    padding: 28px 28px 24px;
    transition: border-color 160ms, box-shadow 160ms, transform 160ms;
    cursor: pointer;
  }
  .lc-doc-card:hover {
    border-color: #0F2847;
    box-shadow: 0 8px 36px rgba(15,40,71,0.1);
    transform: translateY(-2px);
  }

  @media (max-width: 768px) {
    .lc-hub-grid { grid-template-columns: 1fr !important; }
  }
`;

/* ─── Document catalogue ────────────────────────────────────────────────────── */
const DOCS = [
  {
    to: "/privacy",
    icon: Shield,
    color: "#0F2847",
    bg: "#EEF2F9",
    title: "Privacy Policy",
    desc: "How we collect, use, and protect your personal data — including ORCID integration, PostHog analytics, and AI context handling.",
    updated: "29 Jun 2026",
    readingTime: "8 min",
    version: "v1.4",
  },
  {
    to: "/terms",
    icon: FileText,
    color: "#1d4ed8",
    bg: "#EFF6FF",
    title: "Terms of Service",
    desc: "Platform rules, subscription terms, Research Credits, acceptable use, intellectual property, and account termination.",
    updated: "29 Jun 2026",
    readingTime: "10 min",
    version: "v1.4",
  },
  {
    to: "/cookies",
    icon: Cookie,
    color: "#92400e",
    bg: "#FEF3C7",
    title: "Cookie Policy",
    desc: "Every cookie and tracking technology on Synaptiq — including essential session cookies, PostHog analytics, and your consent choices.",
    updated: "29 Jun 2026",
    readingTime: "5 min",
    version: "v1.2",
  },
  {
    to: "/gdpr",
    icon: Globe,
    color: "#1e40af",
    bg: "#EFF6FF",
    title: "GDPR Notice",
    desc: "Rights of EU/EEA residents under Regulation (EU) 2016/679 — including access, erasure, portability, and supervisory authority contacts.",
    updated: "29 Jun 2026",
    readingTime: "6 min",
    version: "v1.3",
  },
  {
    to: "/security",
    icon: Lock,
    color: "#065f46",
    bg: "#ECFDF5",
    title: "Security Center",
    desc: "Infrastructure, encryption, authentication, data isolation, AI privacy, and responsible disclosure — with no vague claims.",
    updated: "29 Jun 2026",
    readingTime: "7 min",
    version: "v1.3",
  },
];

/* ─── Related links ─────────────────────────────────────────────────────────── */
const RELATED = [
  { label: "AI Usage Policy", to: "/ai-policy", desc: "How AI features handle your data" },
  { label: "Contact us", to: "/contact", desc: "General enquiries and support" },
  { label: "Data export", to: "/settings/profile", desc: "Settings → Privacy → Export my data" },
  { label: "Cookie preferences", to: "/settings/profile", desc: "Settings → Privacy → Cookie preferences" },
];

/* ────────────────────────────────────────────────────────────────────────────── */
export default function LegalCenter() {
  const heroRef = useReveal();
  const gridRef = useReveal();
  const relRef  = useReveal();
  const ctaRef  = useReveal();

  return (
    <MarketingLayout>
      <style>{HUB_CSS}</style>

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", borderBottom: "1px solid #e4e8ef", padding: "88px 0 72px" }}>
        <div style={{ maxWidth: 760, margin: "0 auto", padding: "0 32px" }}>
          <div ref={heroRef} className="lc-hub-fade" style={{ textAlign: "center" }}>
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 7,
              fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase",
              color: "#64748b", marginBottom: 20,
              padding: "5px 12px", borderRadius: 20,
              background: "#f8fafb", border: "1px solid #e4e8ef",
            }}>
              <Shield size={10} strokeWidth={2} />
              Legal Center
            </div>

            <h1 style={{
              fontFamily: "Georgia, 'Times New Roman', serif",
              fontSize: "clamp(2.2rem, 4.5vw, 3.2rem)",
              fontWeight: 700,
              color: "#0c1a2e",
              lineHeight: 1.1,
              letterSpacing: "-0.025em",
              margin: "0 0 18px",
            }}>
              Transparency by design.
            </h1>

            <p style={{ fontSize: "1.05rem", color: "#475569", lineHeight: 1.75, maxWidth: 520, margin: "0 auto 32px" }}>
              Everything you need to know about privacy, security, and your use of Synaptiq — written to be read, not avoided.
            </p>

            {/* Trust signals */}
            <div style={{ display: "flex", justifyContent: "center", flexWrap: "wrap", gap: 10 }}>
              {[
                { icon: Shield, label: "GDPR aligned" },
                { icon: Lock,   label: "AES-256 encryption" },
                { icon: Globe,  label: "No data selling" },
              ].map((s) => (
                <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 14px", borderRadius: 20, background: "#f8fafb", border: "1px solid #e4e8ef" }}>
                  <s.icon size={12} strokeWidth={1.5} style={{ color: "#0F2847" }} />
                  <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#475569" }}>{s.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Document cards ────────────────────────────────────────────────── */}
      <section style={{ background: "#f8fafb", padding: "80px 0 100px" }}>
        <div style={{ maxWidth: 1120, margin: "0 auto", padding: "0 32px" }}>
          <div ref={gridRef} className="lc-hub-fade">
            <div
              className="lc-hub-grid"
              style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}
            >
              {DOCS.map((doc, i) => (
                <Link
                  key={doc.to}
                  to={doc.to}
                  className={`lc-doc-card lc-hub-fade d${i + 1}`}
                >
                  {/* Icon */}
                  <div style={{ width: 48, height: 48, borderRadius: 12, background: doc.bg, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 18 }}>
                    <doc.icon size={22} strokeWidth={1.4} style={{ color: doc.color }} />
                  </div>

                  {/* Title + description */}
                  <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0f172a", marginBottom: 8, letterSpacing: "-0.01em" }}>
                    {doc.title}
                  </div>
                  <p style={{ fontSize: "0.84rem", color: "#64748b", lineHeight: 1.65, margin: "0 0 20px", flex: 1 }}>
                    {doc.desc}
                  </p>

                  {/* Footer */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 16, borderTop: "1px solid #f1f5f9" }}>
                    <div style={{ display: "flex", gap: 10 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.66rem", color: "#94a3b8" }}>
                        <Clock size={9} strokeWidth={1.5} />
                        <span>{doc.readingTime}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.66rem", color: "#94a3b8" }}>
                        <Calendar size={9} strokeWidth={1.5} />
                        <span>{doc.updated}</span>
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.72rem", fontWeight: 600, color: "#0F2847" }}>
                      Read <ArrowRight size={12} />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Related links ──────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", padding: "72px 0" }}>
        <div style={{ maxWidth: 780, margin: "0 auto", padding: "0 32px" }}>
          <div ref={relRef} className="lc-hub-fade">
            <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1.4rem", fontWeight: 700, color: "#0f172a", marginBottom: 24, letterSpacing: "-0.015em" }}>
              Related
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {RELATED.map((r) => (
                <Link
                  key={r.label}
                  to={r.to}
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 16px", borderRadius: 8, textDecoration: "none", transition: "background 140ms", background: "transparent" }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "#f8fafb"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                >
                  <div>
                    <div style={{ fontSize: "0.9rem", fontWeight: 600, color: "#0f172a", marginBottom: 2 }}>{r.label}</div>
                    <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>{r.desc}</div>
                  </div>
                  <ChevronRight size={16} strokeWidth={1.5} style={{ color: "#94a3b8", flexShrink: 0 }} />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Contact CTA ────────────────────────────────────────────────────── */}
      <section style={{ background: "#f8fafb", borderTop: "1px solid #e4e8ef", padding: "72px 0" }}>
        <div style={{ maxWidth: 600, margin: "0 auto", padding: "0 32px", textAlign: "center" }}>
          <div ref={ctaRef} className="lc-hub-fade">
            <div style={{ width: 52, height: 52, borderRadius: 14, background: "#EEF2F9", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px" }}>
              <Mail size={22} strokeWidth={1.4} style={{ color: "#0F2847" }} />
            </div>
            <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", margin: "0 0 12px", letterSpacing: "-0.015em" }}>
              Questions about our policies?
            </h2>
            <p style={{ fontSize: "0.95rem", color: "#64748b", lineHeight: 1.7, marginBottom: 28 }}>
              We read every email. For privacy questions, data requests, or legal enquiries, reach us directly.
            </p>
            <div style={{ display: "flex", justifyContent: "center", gap: 10, flexWrap: "wrap" }}>
              <a
                href="mailto:privacy@synaptiq.academy"
                style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "11px 22px", borderRadius: 9, background: "#0F2847", color: "#fff", textDecoration: "none", fontSize: "0.875rem", fontWeight: 600 }}
              >
                <Mail size={14} />
                privacy@synaptiq.academy
              </a>
              <Link
                to="/contact"
                style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "11px 22px", borderRadius: 9, background: "#fff", color: "#0f172a", textDecoration: "none", fontSize: "0.875rem", fontWeight: 600, border: "1px solid #e4e8ef" }}
              >
                Contact page <ExternalLink size={13} />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}

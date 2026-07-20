import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import {
  Search, User, CreditCard, RefreshCw, FolderOpen, Zap, Archive,
  FileText, Building2, Shield, Lock, Wrench, Mail, ChevronRight,
  ArrowRight, ChevronDown, BookOpen, MessageCircle, AlertCircle,
  Activity, Clock,
} from "lucide-react";
import { NAVY, TEXT_TERTIARY as SLATE } from "@/lib/tokens";

/* ─── Design tokens ──────────────────────────────────────────────────────── */
// BORDER/BG_ALT are near-identical to the DS's BRD/SURF2 but not byte-exact,
// and this page's sibling marketing pages (Security, Privacy, Contact — out
// of this audit's scope) still use these same local values; swapping only
// here would create a new, subtler inconsistency instead of removing one.
// NAVY and SLATE above *are* exact matches for existing tokens, so those are
// now imported instead of redeclared.
const BORDER = "#e2e8f0";
const BG_ALT = "#f9fafb";

/* ─── Data ───────────────────────────────────────────────────────────────── */

const QUICK_ACTIONS = [
  { icon: Mail,         label: "Contact Support",  desc: "Email our support team directly",   href: "mailto:support@synaptiq.academy" },
  { icon: AlertCircle,  label: "Report a Bug",     desc: "Submit a bug or unexpected behavior", href: "mailto:support@synaptiq.academy?subject=Bug+Report" },
  { icon: Activity,     label: "System Status",    desc: "Check live service availability",   href: "/status"    },
  { icon: MessageCircle,label: "Contact Us",        desc: "Get in touch with our team",        href: "/contact"  },
];

const CATEGORIES = [
  { icon: User,       title: "Account",         desc: "Profile, ORCID, password, and account settings.",    count: 18 },
  { icon: CreditCard, title: "Billing",         desc: "Invoices, payment methods, and billing history.",    count: 11 },
  { icon: RefreshCw,  title: "Subscriptions",   desc: "Plans, upgrades, downgrades, and cancellations.",    count: 8  },
  { icon: FolderOpen, title: "Projects",        desc: "Creating, managing, and sharing research projects.",  count: 24 },
  { icon: Zap,        title: "AI",              desc: "AI tools, credits, and feature-specific guidance.",   count: 27 },
  { icon: Archive,    title: "Repository",      desc: "File upload, storage limits, and versioning.",        count: 14 },
  { icon: FileText,   title: "Publications",    desc: "Submitting manuscripts, citations, and publishing.",  count: 19 },
  { icon: Building2,  title: "Institutions",    desc: "Institutional setup, departments, and SSO.",          count: 16 },
  { icon: Shield,     title: "Security",        desc: "MFA, sessions, and account security.",               count: 9  },
  { icon: Lock,       title: "Privacy",         desc: "Data export, deletion, and GDPR rights.",            count: 7  },
  { icon: Wrench,     title: "Troubleshooting", desc: "Common issues and step-by-step fixes.",              count: 32 },
];

const MOST_VIEWED = [
  { title: "Getting started with Synaptiq",        cat: "Getting Started"  },
  { title: "How to reset your password",            cat: "Account"          },
  { title: "Managing your subscription plan",       cat: "Subscriptions"    },
  { title: "How to recover a deleted project",      cat: "Projects"         },
  { title: "Inviting team members to a project",   cat: "Projects"         },
  { title: "Understanding AI credits",              cat: "AI"               },
  { title: "Repository storage limits explained",   cat: "Repository"       },
  { title: "Institution management guide",          cat: "Institutions"     },
];

const FAQ_ITEMS = [
  {
    q: "How do I reset my password?",
    a: "Go to the sign-in page and click 'Forgot password'. Enter your email address and we'll send you a secure, single-use reset link that expires in 30 minutes. If you don't receive the email within a few minutes, check your spam folder or contact support@synaptiq.academy.",
  },
  {
    q: "How do I cancel or downgrade my subscription?",
    a: "Go to Settings → Billing → Manage subscription. You can cancel anytime — your access continues until the end of the current billing period. To downgrade, select a lower plan and the change takes effect at your next renewal date. No cancellation fees apply.",
  },
  {
    q: "Why is my AI feature not working?",
    a: "First, check your AI credit balance in Settings → AI Credits. If you have credits remaining, try refreshing the page. If the issue persists, check the System Status page. For ongoing issues, email support@synaptiq.academy with a description of the feature, what you expected to happen, and what actually occurred.",
  },
  {
    q: "How do I export my research data?",
    a: "Email privacy@synaptiq.academy from your account address requesting a data export. You'll receive a machine-readable archive (JSON format) of your profile, projects, manuscripts, and associated data. This fulfils your GDPR right to data portability.",
  },
  {
    q: "How do I delete my account?",
    a: "Email privacy@synaptiq.academy from your account address requesting account deletion. Personal data, projects, and content are removed within 30 days. Billing records are retained for 7 years as required by EU tax law. This action is permanent and cannot be undone.",
  },
  {
    q: "Can I recover a project I accidentally deleted?",
    a: "Project deletion is soft-deleted for 7 days before permanent removal. Contact support@synaptiq.academy as soon as possible with your account email and the project name. Recovery is possible within the 7-day window. After that, the project is permanently removed and cannot be restored.",
  },
  {
    q: "How do I invite someone to a project?",
    a: "Open the project, go to the Members tab, and click 'Invite'. Enter the collaborator's email address and select their role (Viewer, Editor, or Admin). They'll receive an invitation email. If they don't have a Synaptiq account, they'll be prompted to create one for free.",
  },
  {
    q: "How do I report a security vulnerability?",
    a: "Email security@synaptiq.academy with a description of the vulnerability and reproduction steps. We acknowledge all reports within 48 hours. Please do not disclose publicly before we have had reasonable time to investigate and respond. We credit responsible disclosures.",
  },
];

const CONTACT_CHANNELS = [
  { email: "sales@synaptiq.academy",    label: "Sales",    desc: "Subscriptions, pricing, and institutional plans." },
  { email: "support@synaptiq.academy",  label: "Support",  desc: "Technical issues and account assistance."         },
  { email: "security@synaptiq.academy", label: "Security", desc: "Vulnerability reports and security concerns."     },
  { email: "privacy@synaptiq.academy",  label: "Privacy",  desc: "GDPR and personal data requests."                },
];

const RESPONSE_TIMES = [
  { team: "Sales",    time: "Within 1 working day"  },
  { team: "Support",  time: "Within 2 working days" },
  { team: "Security", time: "Within 48 hours"       },
  { team: "General",  time: "Within 2 working days" },
];

const RESOURCES = [
  { label: "Documentation", desc: "Full product documentation and guides",    to: "/documentation"                 },
  { label: "Blog",           desc: "Product updates, research tips, and news", to: "/resources/blog"               },
  { label: "Customer Stories", desc: "How researchers use Synaptiq",           to: "/resources/customer-stories"   },
  { label: "Privacy Policy", desc: "How we handle your data",                  to: "/privacy"                      },
  { label: "Security Center", desc: "Security architecture and policies",      to: "/security"                     },
  { label: "Contact",        desc: "All contact options in one place",          to: "/contact"                      },
];

/* ─── FAQ item ───────────────────────────────────────────────────────────── */
function FaqItem({ q, a, open, onToggle }) {
  return (
    <div style={{ borderBottom: `1px solid ${BORDER}` }}>
      <button
        onClick={onToggle}
        aria-expanded={open}
        style={{ width: "100%", background: "none", border: "none", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "18px 0", textAlign: "left", gap: 16, fontFamily: "inherit" }}
      >
        <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "#0f172a", lineHeight: 1.5 }}>{q}</span>
        <ChevronDown size={15} strokeWidth={2} style={{ color: SLATE, flexShrink: 0, transition: "transform 200ms", transform: open ? "rotate(180deg)" : "none" }} />
      </button>
      <div style={{ maxHeight: open ? 400 : 0, overflow: "hidden", transition: "max-height 220ms ease-out" }}>
        <p style={{ fontSize: "0.85rem", color: "#475569", lineHeight: 1.8, paddingBottom: 20, margin: 0 }}>{a}</p>
      </div>
    </div>
  );
}

/* ─── Component ──────────────────────────────────────────────────────────── */

export default function HelpCenter() {
  useEffect(() => {
    document.title = "Help Center — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const [query, setQuery]   = useState("");
  const [faqOpen, setFaqOpen] = useState(null);

  const q = query.trim().toLowerCase();
  const filteredCats = q
    ? CATEGORIES.filter((c) =>
        c.title.toLowerCase().includes(q) ||
        c.desc.toLowerCase().includes(q)
      )
    : CATEGORIES;
  const filteredFaqs = q
    ? FAQ_ITEMS.filter((item) =>
        item.q.toLowerCase().includes(q) ||
        item.a.toLowerCase().includes(q)
      )
    : FAQ_ITEMS;

  return (
    <MarketingLayout>
      <style>{`
        .hc-action:hover { box-shadow: 0 4px 20px rgba(15,40,71,0.07); border-color: #c9d4e0 !important; }
        .hc-cat:hover    { box-shadow: 0 4px 20px rgba(15,40,71,0.07); border-color: #c9d4e0 !important; }
        .hc-article:hover { background: ${BG_ALT}; }
        .hc-resource:hover { background: ${BG_ALT}; }
        .hc-search:focus { border-color: ${NAVY} !important; box-shadow: 0 0 0 3px rgba(15,40,71,0.07) !important; }
        @media (max-width: 1024px) { .hc-cat-grid { grid-template-columns: repeat(3, 1fr) !important; } }
        @media (max-width: 780px)  { .hc-cat-grid { grid-template-columns: repeat(2, 1fr) !important; } .hc-2col { grid-template-columns: 1fr !important; } .hc-action-grid { grid-template-columns: repeat(2, 1fr) !important; } }
        @media (max-width: 480px)  { .hc-cat-grid { grid-template-columns: 1fr !important; } .hc-action-grid { grid-template-columns: 1fr !important; } }
      `}</style>

      {/* ═══════════════════════════════════════════════════════════════════
          HERO
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, padding: "80px 0 64px" }}>
        <div style={{ maxWidth: 640, margin: "0 auto", padding: "0 32px", textAlign: "center" }}>
          <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 18 }}>
            Help Center
          </div>
          <h1 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(2rem, 4.5vw, 3rem)", fontWeight: 700, color: "#0f172a", lineHeight: 1.1, letterSpacing: "-0.025em", margin: "0 0 32px" }}>
            Find answers in seconds.
          </h1>

          {/* Large search bar */}
          <form onSubmit={(e) => e.preventDefault()} style={{ position: "relative" }}>
            <Search size={18} strokeWidth={1.5} style={{ position: "absolute", left: 18, top: "50%", transform: "translateY(-50%)", color: "#94a3b8", pointerEvents: "none" }} />
            <input
              className="hc-search"
              aria-label="Search help articles"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for answers…"
              style={{ width: "100%", boxSizing: "border-box", padding: "16px 18px 16px 50px", borderRadius: 12, border: `1px solid ${BORDER}`, fontSize: "1rem", color: "#0f172a", background: "#fff", outline: "none", fontFamily: "inherit", transition: "border-color 140ms, box-shadow 140ms" }}
            />
          </form>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          QUICK ACTIONS
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: BG_ALT, borderBottom: `1px solid ${BORDER}`, padding: "48px 0" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "0 32px" }}>
          <div className="hc-action-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
            {QUICK_ACTIONS.map((a) => {
              const Icon = a.icon;
              const inner = (
                <>
                  <div style={{ width: 34, height: 34, borderRadius: 8, background: BG_ALT, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Icon size={15} strokeWidth={1.5} style={{ color: NAVY }} />
                  </div>
                  <div>
                    <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a", marginBottom: 3 }}>{a.label}</div>
                    <p style={{ fontSize: "0.76rem", color: SLATE, lineHeight: 1.5, margin: 0 }}>{a.desc}</p>
                  </div>
                </>
              );
              const sharedStyle = { background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 12, padding: "20px 18px", display: "flex", alignItems: "flex-start", gap: 14, textDecoration: "none", transition: "box-shadow 160ms, border-color 160ms" };
              return a.href.startsWith("/") ? (
                <Link key={a.label} to={a.href} className="hc-action" style={sharedStyle}>{inner}</Link>
              ) : (
                <a key={a.label} href={a.href} className="hc-action" style={sharedStyle}>{inner}</a>
              );
            })}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          CATEGORIES
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, padding: "64px 0" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "0 32px" }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 36 }}>
            <div>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>Browse</div>
              <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.35rem, 2.5vw, 1.75rem)", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: 0 }}>
                {query.trim() ? `Results for "${query}"` : "Browse by topic."}
              </h2>
            </div>
            {query.trim() && (
              <button onClick={() => setQuery("")} style={{ fontSize: "0.78rem", color: SLATE, background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", textDecoration: "underline" }}>Clear</button>
            )}
          </div>

          {filteredCats.length === 0 ? (
            <div style={{ textAlign: "center", padding: "48px 0", color: SLATE }}>
              <div style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: 8 }}>No topics found</div>
              <p style={{ fontSize: "0.85rem", margin: "0 0 16px" }}>Try a different search or contact our support team.</p>
              <button onClick={() => setQuery("")} style={{ fontSize: "0.82rem", color: NAVY, fontWeight: 600, background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", textDecoration: "underline" }}>Show all topics</button>
            </div>
          ) : (
            <div className="hc-cat-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
              {filteredCats.map((cat) => {
                const Icon = cat.icon;
                return (
                  <div
                    key={cat.title}
                    className="hc-cat"
                    role="button"
                    tabIndex={0}
                    onClick={() => setQuery(cat.title)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setQuery(cat.title); } }}
                    aria-label={`Search for ${cat.title} questions`}
                    style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 12, padding: "20px 18px", display: "flex", flexDirection: "column", gap: 10, cursor: "pointer", transition: "box-shadow 160ms, border-color 160ms" }}
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
                      <div style={{ width: 34, height: 34, borderRadius: 8, background: BG_ALT, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        <Icon size={16} strokeWidth={1.5} style={{ color: NAVY }} />
                      </div>
                      <span style={{ fontSize: "0.68rem", color: "#94a3b8" }}>{cat.count} articles</span>
                    </div>
                    <div style={{ fontSize: "0.88rem", fontWeight: 700, color: "#0f172a" }}>{cat.title}</div>
                    <p style={{ fontSize: "0.78rem", color: SLATE, lineHeight: 1.65, margin: 0, flex: 1 }}>{cat.desc}</p>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: "0.73rem", fontWeight: 600, color: NAVY, marginTop: "auto", paddingTop: 8 }}>
                      Browse <ChevronRight size={11} strokeWidth={2.5} />
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          MOST VIEWED + FAQ
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: BG_ALT, borderBottom: `1px solid ${BORDER}`, padding: "64px 0" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "0 32px" }}>
          <div className="hc-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 48 }}>

            {/* Most Viewed */}
            <div>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>Most Viewed</div>
              <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "1.35rem", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 24px" }}>
                Popular articles.
              </h2>
              <div style={{ border: `1px solid ${BORDER}`, borderRadius: 12, background: "#fff", overflow: "hidden" }}>
                {MOST_VIEWED.map((a, i) => (
                  <div
                    key={a.title}
                    className="hc-article"
                    role="button"
                    tabIndex={0}
                    onClick={() => setQuery(a.title)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setQuery(a.title); } }}
                    aria-label={`Search for ${a.title}`}
                    style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "13px 18px", borderBottom: i < MOST_VIEWED.length - 1 ? `1px solid ${BORDER}` : "none", cursor: "pointer", transition: "background 120ms" }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "0.82rem", fontWeight: 500, color: "#0f172a", lineHeight: 1.4, marginBottom: 2 }}>{a.title}</div>
                      <span style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "#94a3b8" }}>{a.cat}</span>
                    </div>
                    <ChevronRight size={13} strokeWidth={2} style={{ color: "#94a3b8", flexShrink: 0 }} />
                  </div>
                ))}
              </div>
            </div>

            {/* FAQ */}
            <div>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>FAQ</div>
              <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "1.35rem", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 24px" }}>
                {q ? `Questions matching "${query}"` : "Frequently asked questions."}
              </h2>
              <div>
                {filteredFaqs.length === 0 ? (
                  <p style={{ fontSize: "0.85rem", color: SLATE }}>No matching questions. Try a different search or contact support.</p>
                ) : (
                  filteredFaqs.map((item, i) => (
                    <FaqItem key={item.q} q={item.q} a={item.a} open={faqOpen === i} onToggle={() => setFaqOpen(faqOpen === i ? null : i)} />
                  ))
                )}
              </div>
              <Link
                to="/contact"
                style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.82rem", fontWeight: 600, color: NAVY, textDecoration: "none", marginTop: 20 }}
              >
                More questions? Contact us <ArrowRight size={13} strokeWidth={2} />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          CONTACT OPTIONS
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, padding: "64px 0" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "0 32px" }}>
          <div className="hc-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 48 }}>

            {/* Email contacts */}
            <div>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>Email Support</div>
              <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "1.35rem", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 24px" }}>
                Contact options.
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {CONTACT_CHANNELS.map((ch) => (
                  <div key={ch.label} style={{ background: BG_ALT, border: `1px solid ${BORDER}`, borderRadius: 10, padding: "14px 18px" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 4 }}>
                      <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#0f172a" }}>{ch.label}</span>
                      <a href={`mailto:${ch.email}`} style={{ fontSize: "0.75rem", fontWeight: 600, color: NAVY, textDecoration: "none" }}
                        onMouseEnter={(e) => { e.currentTarget.style.textDecoration = "underline"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.textDecoration = "none"; }}
                      >
                        {ch.email}
                      </a>
                    </div>
                    <p style={{ fontSize: "0.77rem", color: SLATE, margin: 0, lineHeight: 1.5 }}>{ch.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Response times */}
            <div>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>Response Times</div>
              <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "1.35rem", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 24px" }}>
                When to expect a reply.
              </h2>
              <div style={{ border: `1px solid ${BORDER}`, borderRadius: 12, overflow: "hidden" }}>
                {RESPONSE_TIMES.map((r, i) => (
                  <div key={r.team} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", borderBottom: i < RESPONSE_TIMES.length - 1 ? `1px solid ${BORDER}` : "none", background: "#fff" }}>
                    <span style={{ fontSize: "0.875rem", fontWeight: 600, color: "#0f172a" }}>{r.team}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <Clock size={12} strokeWidth={1.5} style={{ color: "#94a3b8" }} />
                      <span style={{ fontSize: "0.8rem", color: SLATE }}>{r.time}</span>
                    </div>
                  </div>
                ))}
              </div>
              <p style={{ fontSize: "0.8rem", color: "#94a3b8", lineHeight: 1.65, marginTop: 14 }}>
                Response times are for business days (Monday–Friday, UTC). Security reports are acknowledged within 48 hours including weekends.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          RESOURCES
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: BG_ALT, padding: "64px 0" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "0 32px" }}>
          <div style={{ marginBottom: 36 }}>
            <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>Resources</div>
            <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.35rem, 2.5vw, 1.75rem)", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: 0 }}>
              More places to explore.
            </h2>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
            {RESOURCES.map((r) => (
              <Link
                key={r.label}
                to={r.to}
                className="hc-resource"
                style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 10, padding: "16px 18px", textDecoration: "none", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, transition: "background 120ms" }}
              >
                <div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a", marginBottom: 3 }}>{r.label}</div>
                  <p style={{ fontSize: "0.77rem", color: SLATE, margin: 0, lineHeight: 1.5 }}>{r.desc}</p>
                </div>
                <ChevronRight size={14} strokeWidth={2} style={{ color: "#94a3b8", flexShrink: 0 }} />
              </Link>
            ))}
          </div>

          {/* Link to Documentation */}
          <div style={{ marginTop: 40, textAlign: "center", paddingTop: 32, borderTop: `1px solid ${BORDER}` }}>
            <p style={{ fontSize: "0.875rem", color: SLATE, marginBottom: 16 }}>
              Looking for full product documentation?
            </p>
            <Link
              to="/documentation"
              style={{ display: "inline-flex", alignItems: "center", gap: 8, background: NAVY, color: "#fff", padding: "12px 24px", borderRadius: 8, fontSize: "0.875rem", fontWeight: 600, textDecoration: "none" }}
            >
              <BookOpen size={14} strokeWidth={2} />
              Browse Documentation <ArrowRight size={14} strokeWidth={2} />
            </Link>
          </div>
        </div>
      </section>

    </MarketingLayout>
  );
}

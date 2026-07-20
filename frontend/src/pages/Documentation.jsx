import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import {
  Search, Rocket, User, FolderOpen, BookOpen, Zap, Archive,
  FileText, Users, Building2, Settings, CreditCard, Shield,
  Code, ChevronRight, Clock, ArrowRight, HelpCircle,
} from "lucide-react";

/* ─── Design tokens ──────────────────────────────────────────────────────── */
const NAVY   = "#0F2847";
const SLATE  = "#64748b";
const BORDER = "#e2e8f0";
const BG_ALT = "#f9fafb";

/* ─── Data ───────────────────────────────────────────────────────────────── */

const POPULAR_SEARCHES = [
  "Projects", "AI Assistant", "Workspaces", "Institution Dashboard",
  "Repository", "Publishing", "Research Analytics",
];

const QUICK_START = [
  { num: "01", title: "Create Account",           desc: "Sign up with email or Google. Connect your ORCID for instant academic verification.",                    time: "2 min"  },
  { num: "02", title: "Create Your First Project", desc: "Set up a workspace for your research. Define scope, add collaborators, and set milestones.",             time: "5 min"  },
  { num: "03", title: "Invite Collaborators",      desc: "Add team members, assign roles, and manage access permissions within your project.",                    time: "3 min"  },
  { num: "04", title: "Use AI Assistant",          desc: "Ask the AI anything about your research. Manuscript review, literature search, and more.",               time: "2 min"  },
  { num: "05", title: "Publish Research",          desc: "Match your manuscript to journals, track submissions, and manage your full citation pipeline.",           time: "10 min" },
  { num: "06", title: "Institution Setup",         desc: "Configure your institution's workspace, manage departments, and onboard researchers at scale.",           time: "15 min" },
];

const CATEGORIES = [
  { icon: Rocket,     title: "Getting Started",    desc: "Account setup, first steps, and orientation to the platform.",               count: 12             },
  { icon: User,       title: "Account & Profile",  desc: "Profile settings, ORCID integration, security, and account management.",     count: 18             },
  { icon: FolderOpen, title: "Projects",           desc: "Create, manage, and collaborate on research projects and workspaces.",        count: 24             },
  { icon: BookOpen,   title: "Research Workspace", desc: "Literature review, gap finder, design advisor, and statistical tools.",       count: 31             },
  { icon: Zap,        title: "AI Workspace",       desc: "AI Assistant, manuscript review, abstract generator, and rewriting tools.",   count: 27             },
  { icon: Archive,    title: "Repository",         desc: "Upload, organize, and version-control your research files and datasets.",      count: 14             },
  { icon: FileText,   title: "Publications",       desc: "Submit to journals, track citations, and manage your publication pipeline.",  count: 19             },
  { icon: Users,      title: "Collaboration",      desc: "Invite collaborators, manage permissions, and work together in real time.",   count: 22             },
  { icon: Building2,  title: "Institutions",       desc: "Institutional workspace, department management, analytics, and SSO.",         count: 16             },
  { icon: Settings,   title: "Administration",     desc: "Platform settings, user management, audit logs, and compliance tools.",      count: 21             },
  { icon: CreditCard, title: "Billing",            desc: "Subscriptions, plan upgrades, billing history, and invoices.",               count: 11             },
  { icon: Shield,     title: "Security",           desc: "Two-factor authentication, session management, and data security.",          count: 9              },
  { icon: Code,       title: "API",                desc: "API reference, authentication, rate limits, and integration guides.",        count: 0, badge: "Soon" },
];

const FEATURED_GUIDES = [
  { tag: "Getting Started",  title: "Create your first workspace",         time: "5 min"  },
  { tag: "AI Workspace",     title: "Run your first AI manuscript review",  time: "8 min"  },
  { tag: "Repository",       title: "Upload and organize manuscripts",      time: "3 min"  },
  { tag: "Collaboration",    title: "Invite collaborators to a project",    time: "4 min"  },
  { tag: "Institutions",     title: "Institution onboarding guide",         time: "15 min" },
];

const POPULAR_ARTICLES = [
  { title: "How to connect your ORCID account",           cat: "Account"    },
  { title: "Understanding AI credit usage",                cat: "AI"         },
  { title: "Setting up two-factor authentication",         cat: "Security"   },
  { title: "Exporting your research data (GDPR)",          cat: "Account"    },
  { title: "Managing collaborator permissions",            cat: "Collaboration" },
  { title: "Journal matching and manuscript submission",   cat: "Publications" },
  { title: "Upgrading to an Institution plan",             cat: "Billing"    },
  { title: "Research impact score explained",              cat: "Research"   },
];

const RECENTLY_UPDATED = [
  { title: "AI Assistant: new capabilities in 2026",       cat: "AI Workspace",       date: "2 days ago"  },
  { title: "Reputation system: understanding your score",  cat: "Research Workspace", date: "5 days ago"  },
  { title: "Institution analytics: new dashboard layout",  cat: "Institutions",       date: "1 week ago"  },
  { title: "GDPR data export: step-by-step guide",        cat: "Account & Profile",  date: "1 week ago"  },
  { title: "Grant Collaboration Hub: getting started",     cat: "Collaboration",      date: "2 weeks ago" },
];

/* ─── Component ──────────────────────────────────────────────────────────── */

export default function Documentation() {
  useEffect(() => {
    document.title = "Documentation — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const [query, setQuery] = useState("");

  const filtered = query.trim()
    ? CATEGORIES.filter(
        (c) =>
          c.title.toLowerCase().includes(query.toLowerCase()) ||
          c.desc.toLowerCase().includes(query.toLowerCase())
      )
    : CATEGORIES;

  return (
    <MarketingLayout>
      <style>{`
        .doc-cat:hover  { box-shadow: 0 4px 20px rgba(15,40,71,0.07); border-color: #c9d4e0 !important; }
        .doc-guide:hover { border-color: #c9d4e0 !important; background: #fff !important; }
        .doc-article:hover { background: ${BG_ALT}; }
        .doc-recent:hover  { background: ${BG_ALT}; }
        .doc-pill:hover { background: #e8edf5 !important; color: ${NAVY} !important; }
        .doc-search:focus { border-color: ${NAVY} !important; box-shadow: 0 0 0 3px rgba(15,40,71,0.07) !important; }
        @media (max-width: 1024px) { .doc-cat-grid { grid-template-columns: repeat(3, 1fr) !important; } }
        @media (max-width: 780px)  { .doc-qs-grid  { grid-template-columns: repeat(2, 1fr) !important; } .doc-cat-grid { grid-template-columns: repeat(2, 1fr) !important; } .doc-2col { grid-template-columns: 1fr !important; } }
        @media (max-width: 480px)  { .doc-qs-grid  { grid-template-columns: 1fr !important; } .doc-cat-grid { grid-template-columns: 1fr !important; } }
      `}</style>

      {/* ═══════════════════════════════════════════════════════════════════
          HERO
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, padding: "80px 0 64px" }}>
        <div style={{ maxWidth: 720, margin: "0 auto", padding: "0 32px", textAlign: "center" }}>
          <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 18 }}>
            Documentation
          </div>
          <h1 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(2rem, 4.5vw, 3rem)", fontWeight: 700, color: "#0f172a", lineHeight: 1.1, letterSpacing: "-0.025em", margin: "0 0 36px" }}>
            Everything you need to master Synaptiq.
          </h1>

          {/* Search */}
          <form onSubmit={(e) => e.preventDefault()} style={{ position: "relative", marginBottom: 20 }}>
            <Search size={16} strokeWidth={1.5} style={{ position: "absolute", left: 16, top: "50%", transform: "translateY(-50%)", color: "#94a3b8", pointerEvents: "none" }} />
            <input
              className="doc-search"
              aria-label="Search documentation"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search documentation…"
              style={{ width: "100%", boxSizing: "border-box", padding: "14px 16px 14px 44px", borderRadius: 10, border: `1px solid ${BORDER}`, fontSize: "0.95rem", color: "#0f172a", background: "#fff", outline: "none", fontFamily: "inherit", transition: "border-color 140ms, box-shadow 140ms" }}
            />
          </form>

          {/* Popular searches */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
            <span style={{ fontSize: "0.72rem", color: "#94a3b8", paddingTop: 4 }}>Popular:</span>
            {POPULAR_SEARCHES.map((term) => (
              <button
                key={term}
                className="doc-pill"
                onClick={() => setQuery(term)}
                style={{ fontSize: "0.78rem", color: SLATE, background: BG_ALT, border: `1px solid ${BORDER}`, borderRadius: 20, padding: "4px 12px", cursor: "pointer", fontFamily: "inherit", transition: "background 120ms, color 120ms" }}
              >
                {term}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          QUICK START
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: BG_ALT, borderBottom: `1px solid ${BORDER}`, padding: "64px 0" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "0 32px" }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 36 }}>
            <div>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>Quick Start</div>
              <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.35rem, 2.5vw, 1.75rem)", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: 0 }}>
                Get up and running in minutes.
              </h2>
            </div>
          </div>
          <div className="doc-qs-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
            {QUICK_START.map((step) => (
              <div
                key={step.num}
                style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 12, padding: "22px 22px 18px", display: "flex", flexDirection: "column", gap: 10 }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "0.65rem", fontWeight: 800, letterSpacing: "0.1em", color: "#94a3b8" }}>{step.num}</span>
                  <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.68rem", color: "#94a3b8" }}>
                    <Clock size={10} strokeWidth={2} />{step.time}
                  </span>
                </div>
                <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#0f172a" }}>{step.title}</div>
                <p style={{ fontSize: "0.8rem", color: SLATE, lineHeight: 1.65, margin: 0 }}>{step.desc}</p>
                <div style={{ marginTop: 4 }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: "0.75rem", fontWeight: 600, color: NAVY, cursor: "pointer" }}>
                    Get started <ChevronRight size={12} strokeWidth={2.5} />
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          CATEGORIES
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, padding: "64px 0" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "0 32px" }}>
          <div style={{ marginBottom: 36 }}>
            <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>Browse</div>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
              <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.35rem, 2.5vw, 1.75rem)", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: 0 }}>
                {query.trim() ? `Results for "${query}"` : "Browse by category."}
              </h2>
              {query.trim() && (
                <button onClick={() => setQuery("")} style={{ fontSize: "0.78rem", color: SLATE, background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", textDecoration: "underline" }}>
                  Clear
                </button>
              )}
            </div>
          </div>

          {filtered.length === 0 ? (
            <div style={{ textAlign: "center", padding: "48px 0", color: SLATE }}>
              <div style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: 8 }}>No categories found</div>
              <p style={{ fontSize: "0.85rem", margin: "0 0 16px" }}>Try a different search term or browse all categories.</p>
              <button onClick={() => setQuery("")} style={{ fontSize: "0.82rem", color: NAVY, fontWeight: 600, background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", textDecoration: "underline" }}>Show all categories</button>
            </div>
          ) : (
            <div className="doc-cat-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
              {filtered.map((cat) => {
                const Icon = cat.icon;
                return (
                  <div
                    key={cat.title}
                    className="doc-cat"
                    style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 12, padding: "20px 18px", display: "flex", flexDirection: "column", gap: 10, cursor: "pointer", transition: "box-shadow 160ms, border-color 160ms" }}
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
                      <div style={{ width: 34, height: 34, borderRadius: 8, background: BG_ALT, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        <Icon size={16} strokeWidth={1.5} style={{ color: NAVY }} />
                      </div>
                      {cat.badge ? (
                        <span style={{ fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94a3b8", border: `1px solid ${BORDER}`, borderRadius: 4, padding: "2px 7px", whiteSpace: "nowrap" }}>{cat.badge}</span>
                      ) : (
                        <span style={{ fontSize: "0.7rem", color: "#94a3b8" }}>{cat.count} articles</span>
                      )}
                    </div>
                    <div style={{ fontSize: "0.88rem", fontWeight: 700, color: "#0f172a" }}>{cat.title}</div>
                    <p style={{ fontSize: "0.78rem", color: SLATE, lineHeight: 1.65, margin: 0 }}>{cat.desc}</p>
                    {!cat.badge && (
                      <div style={{ marginTop: "auto", paddingTop: 8 }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: "0.73rem", fontWeight: 600, color: NAVY }}>
                          Browse <ChevronRight size={11} strokeWidth={2.5} />
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          FEATURED GUIDES + POPULAR ARTICLES
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: BG_ALT, borderBottom: `1px solid ${BORDER}`, padding: "64px 0" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "0 32px" }}>
          <div className="doc-2col" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 48 }}>

            {/* Featured Guides */}
            <div>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>Featured</div>
              <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "1.35rem", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 24px" }}>
                Featured guides.
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {FEATURED_GUIDES.map((g) => (
                  <div
                    key={g.title}
                    className="doc-guide"
                    style={{ background: BG_ALT, border: `1px solid ${BORDER}`, borderRadius: 10, padding: "16px 18px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, cursor: "pointer", transition: "border-color 140ms, background 140ms" }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 4 }}>{g.tag}</div>
                      <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#0f172a", lineHeight: 1.4 }}>{g.title}</div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
                      <span style={{ fontSize: "0.7rem", color: "#94a3b8" }}>{g.time}</span>
                      <ChevronRight size={14} strokeWidth={2} style={{ color: "#94a3b8" }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Popular Articles */}
            <div>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>Popular</div>
              <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "1.35rem", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 24px" }}>
                Popular articles.
              </h2>
              <div style={{ border: `1px solid ${BORDER}`, borderRadius: 10, background: "#fff", overflow: "hidden" }}>
                {POPULAR_ARTICLES.map((a, i) => (
                  <div
                    key={a.title}
                    className="doc-article"
                    style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "13px 18px", borderBottom: i < POPULAR_ARTICLES.length - 1 ? `1px solid ${BORDER}` : "none", cursor: "pointer", transition: "background 120ms" }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: "0.82rem", fontWeight: 500, color: "#0f172a", lineHeight: 1.4 }}>{a.title}</div>
                      <span style={{ fontSize: "0.65rem", color: "#94a3b8", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>{a.cat}</span>
                    </div>
                    <ChevronRight size={13} strokeWidth={2} style={{ color: "#94a3b8", flexShrink: 0 }} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          RECENTLY UPDATED
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, padding: "64px 0" }}>
        <div style={{ maxWidth: 1080, margin: "0 auto", padding: "0 32px" }}>
          <div style={{ marginBottom: 32 }}>
            <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 8 }}>Latest</div>
            <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.35rem, 2.5vw, 1.75rem)", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: 0 }}>
              Recently updated.
            </h2>
          </div>
          <div style={{ border: `1px solid ${BORDER}`, borderRadius: 12, overflow: "hidden" }}>
            {RECENTLY_UPDATED.map((a, i) => (
              <div
                key={a.title}
                className="doc-recent"
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, padding: "16px 22px", borderBottom: i < RECENTLY_UPDATED.length - 1 ? `1px solid ${BORDER}` : "none", cursor: "pointer", transition: "background 120ms" }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "0.875rem", fontWeight: 500, color: "#0f172a", marginBottom: 3 }}>{a.title}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "#94a3b8" }}>{a.cat}</span>
                    <span style={{ width: 3, height: 3, borderRadius: "50%", background: "#d1d5db", flexShrink: 0 }} />
                    <span style={{ fontSize: "0.7rem", color: "#94a3b8" }}>{a.date}</span>
                  </div>
                </div>
                <ChevronRight size={14} strokeWidth={2} style={{ color: "#94a3b8", flexShrink: 0 }} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          FOOTER CTA
      ═══════════════════════════════════════════════════════════════════ */}
      <section style={{ background: BG_ALT, padding: "72px 0" }}>
        <div style={{ maxWidth: 560, margin: "0 auto", padding: "0 32px", textAlign: "center" }}>
          <div style={{ width: 44, height: 44, borderRadius: "50%", background: "#fff", border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px" }}>
            <HelpCircle size={20} strokeWidth={1.5} style={{ color: NAVY }} />
          </div>
          <h2 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "clamp(1.35rem, 2.5vw, 1.85rem)", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 12px" }}>
            Still need help?
          </h2>
          <p style={{ fontSize: "0.9rem", color: SLATE, lineHeight: 1.7, margin: "0 0 32px" }}>
            Can't find what you're looking for? Our support team is here to help.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <Link
              to="/help-center"
              style={{ display: "inline-flex", alignItems: "center", gap: 8, background: NAVY, color: "#fff", padding: "12px 26px", borderRadius: 8, fontSize: "0.875rem", fontWeight: 600, textDecoration: "none" }}
            >
              Visit Help Center <ArrowRight size={14} strokeWidth={2} />
            </Link>
            <Link
              to="/contact"
              style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "#fff", color: "#0f172a", padding: "11px 22px", borderRadius: 8, fontSize: "0.875rem", fontWeight: 600, textDecoration: "none", border: `1px solid ${BORDER}` }}
            >
              Contact Support
            </Link>
          </div>
        </div>
      </section>

    </MarketingLayout>
  );
}

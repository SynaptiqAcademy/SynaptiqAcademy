/* eslint-disable */
import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import {
  ArrowRight, Terminal, Shield, Database, Bot, FileText,
  BarChart3, Building2, GitBranch, Bell, CreditCard,
  Settings, Lock, Users, Check, Copy,
} from "lucide-react";

/* ── Design tokens ─────────────────────────────────────────────────────────── */
const NAVY   = "#0F2847";
const NAVY2  = "#1e3a5f";
const SLATE  = "#475569";
const BORDER = "#e8edf3";
const LIGHT  = "#f8fafc";
const MONO   = "'Menlo','Monaco','Consolas',monospace";
const INDIGO = "#6366f1";

/* ── Data ───────────────────────────────────────────────────────────────────── */
const CAPABILITIES = [
  { name: "Authentication",  prefix: "/api/auth",          Icon: Lock,         desc: "Register users, manage sessions, issue JWT tokens and support OAuth 2.0 flows." },
  { name: "Projects",        prefix: "/api/projects",      Icon: GitBranch,    desc: "Create research projects, manage collaborators, track milestones and deliverables." },
  { name: "Researchers",     prefix: "/api/researchers",   Icon: Users,        desc: "Access researcher profiles, publication stats, reputation scores and networks." },
  { name: "Institutions",    prefix: "/api/institutions",  Icon: Building2,    desc: "Manage institution data, departments, units, affiliations and analytics." },
  { name: "Workspaces",      prefix: "/api/workspaces",    Icon: Database,     desc: "Create shared research environments with version-controlled documents." },
  { name: "Publications",    prefix: "/api/manuscripts",   Icon: FileText,     desc: "Submit, track and manage manuscripts through the full publication lifecycle." },
  { name: "Repository",      prefix: "/api/files",         Icon: Database,     desc: "Upload, version and retrieve research files, datasets and supplementary materials." },
  { name: "AI Services",     prefix: "/api/ai",            Icon: Bot,          desc: "Literature review, gap detection, manuscript analysis and statistical advisory." },
  { name: "Credits",         prefix: "/api/credits",       Icon: CreditCard,   desc: "Query AI credit balances, track usage per service and manage allocations." },
  { name: "Notifications",   prefix: "/api/notifications", Icon: Bell,         desc: "Send and receive platform notifications and configure delivery preferences." },
  { name: "Admin",           prefix: "/api/admin",         Icon: Settings,     desc: "Platform governance, user management, analytics and system configuration. Admin only." },
];

const BUILD_ITEMS = [
  { Icon: GitBranch,  title: "Research Management",       desc: "Automate project creation, milestone tracking and researcher onboarding at scale." },
  { Icon: Building2,  title: "Institution Dashboards",    desc: "Pull publication stats, researcher activity and grant data into custom reporting systems." },
  { Icon: Bot,        title: "AI Assistants",             desc: "Integrate Synaptiq's literature and gap intelligence into your own research tools." },
  { Icon: FileText,   title: "Publication Automation",    desc: "Streamline manuscript submission, status tracking and journal matching workflows." },
  { Icon: BarChart3,  title: "Analytics",                 desc: "Embed research impact scores, citation metrics and productivity analytics." },
  { Icon: Shield,     title: "Academic Verification",     desc: "Verify institutional affiliation, qualifications and researcher identity." },
  { Icon: Database,   title: "Repository Integrations",   desc: "Sync research files, datasets and outputs with external repository systems." },
];

const AUTH_METHODS = [
  { name: "JWT Tokens",         desc: "Stateless JSON Web Tokens with configurable expiry for every request." },
  { name: "API Keys",           desc: "Long-lived keys for server-to-server integrations and CI/CD pipelines." },
  { name: "OAuth 2.0",          desc: "Standard OAuth 2.0 flow for delegated access and third-party integrations." },
  { name: "Enterprise SSO",     desc: "SAML 2.0 and OIDC-compatible single sign-on for institutional deployments." },
  { name: "Role Based Access",  desc: "Fine-grained RBAC with researcher, admin and super_admin permission tiers." },
];

const SDKS = [
  { name: "Python",       tag: "pip install synaptiq",      desc: "Async Python SDK for research automation scripts and data pipelines." },
  { name: "JavaScript",   tag: "npm install @synaptiq/api", desc: "Node.js and browser-compatible SDK for web integrations and workflows." },
  { name: "REST API",     tag: "OpenAPI 3.1",               desc: "Direct HTTP access using any language or HTTP client that speaks REST." },
  { name: "OpenAPI",      tag: "YAML / JSON",               desc: "Machine-readable schema for code generation, mocking and contract testing." },
];

const SECURITY_ITEMS = [
  { name: "TLS 1.3 Encryption",    desc: "All data in transit is encrypted end-to-end with TLS 1.3." },
  { name: "Rate Limiting",          desc: "Per-key, per-IP and per-endpoint limits with clear 429 responses." },
  { name: "Audit Logs",             desc: "Immutable, timestamped audit trail covering every API call." },
  { name: "GDPR Compliance",        desc: "Data residency controls, right-to-erasure and portability endpoints." },
  { name: "Permission Scopes",      desc: "Granular OAuth scopes to minimize each token's access surface." },
  { name: "API Versioning",         desc: "Stable versioned endpoints with a 12-month deprecation window." },
];

/* ── Component ──────────────────────────────────────────────────────────────── */
export default function ApiPortal() {
  useEffect(() => {
    document.title = "Developer API — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const [copied, setCopied] = useState(false);

  const copyCmd = () => {
    navigator.clipboard.writeText(
      'curl -X GET "https://api.synaptiq.academy/api/status" -H "Accept: application/json"'
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <MarketingLayout>
      <style>{`
        .ap-build-card   { transition: transform 200ms, box-shadow 200ms; }
        .ap-build-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(15,40,71,0.08); }
        .ap-cap-card     { transition: border-color 150ms; }
        .ap-cap-card:hover { border-color: ${NAVY} !important; }
        .ap-auth-card    { transition: border-color 150ms, background 150ms; }
        .ap-auth-card:hover { border-color: ${NAVY} !important; background: #f0f5ff !important; }
        .ap-sdk-card     { transition: border-color 150ms; }
        .ap-sdk-card:hover { border-color: ${NAVY} !important; }
        .ap-code-grid    { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .ap-build-grid   { display: grid; grid-template-columns: repeat(auto-fill,minmax(260px,1fr)); gap: 16px; }
        .ap-cap-grid     { display: grid; grid-template-columns: repeat(auto-fill,minmax(290px,1fr)); gap: 14px; }
        .ap-auth-grid    { display: grid; grid-template-columns: repeat(auto-fill,minmax(230px,1fr)); gap: 12px; }
        .ap-sdk-grid     { display: grid; grid-template-columns: repeat(auto-fill,minmax(220px,1fr)); gap: 14px; }
        .ap-sec-grid     { display: grid; grid-template-columns: repeat(auto-fill,minmax(280px,1fr)); gap: 20px; }
        @media (max-width: 700px) { .ap-code-grid { grid-template-columns: 1fr; } }
        .ap-hero-btn-primary { background: ${NAVY}; color: #fff; }
        .ap-hero-btn-primary:hover { opacity: 0.88; }
        .ap-hero-btn-secondary { background: #fff; color: ${NAVY}; border: 1.5px solid ${BORDER}; }
        .ap-hero-btn-secondary:hover { border-color: ${NAVY}; }
      `}</style>

      {/* ── Hero ─────────────────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", padding: "120px 24px 88px", textAlign: "center" }}>
        <div style={{ maxWidth: 720, margin: "0 auto" }}>
          <div style={{ display: "inline-block", fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: NAVY, border: `1px solid ${BORDER}`, padding: "4px 14px", borderRadius: 20, marginBottom: 28 }}>
            Developer Platform
          </div>
          <h1 style={{ fontSize: "clamp(2.4rem, 5vw, 3.8rem)", fontWeight: 800, color: NAVY, letterSpacing: "-0.03em", lineHeight: 1.08, marginBottom: 24 }}>
            Build on top of Synaptiq.
          </h1>
          <p style={{ fontSize: "1.15rem", color: SLATE, lineHeight: 1.75, maxWidth: 580, margin: "0 auto 44px" }}>
            Power your research workflows, institutions and AI experiences through a secure, well-documented API.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <Link to="/documentation" className="ap-hero-btn-primary" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "13px 28px", borderRadius: 8, fontWeight: 600, fontSize: "0.9rem", textDecoration: "none", transition: "opacity 150ms" }}>
              View Documentation <ArrowRight size={16} />
            </Link>
            <Link to="/documentation" className="ap-hero-btn-secondary" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "13px 28px", borderRadius: 8, fontWeight: 600, fontSize: "0.9rem", textDecoration: "none", transition: "border-color 150ms" }}>
              API Reference
            </Link>
          </div>
        </div>
      </section>

      {/* ── Trusted by ───────────────────────────────────────────────────────── */}
      <section style={{ background: LIGHT, borderTop: `1px solid ${BORDER}`, borderBottom: `1px solid ${BORDER}`, padding: "32px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "center", gap: "10px 36px" }}>
          <span style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8" }}>Trusted by</span>
          {["Universities", "Research Institutes", "Publishers", "Healthcare Organizations", "Government"].map(n => (
            <span key={n} style={{ fontSize: "0.87rem", fontWeight: 500, color: SLATE }}>{n}</span>
          ))}
        </div>
      </section>

      {/* ── What you can build ───────────────────────────────────────────────── */}
      <section style={{ background: "#fff", padding: "96px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ marginBottom: 52 }}>
            <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: NAVY, marginBottom: 14 }}>Use cases</div>
            <h2 style={{ fontSize: "clamp(1.75rem, 3vw, 2.4rem)", fontWeight: 800, color: NAVY, letterSpacing: "-0.025em", lineHeight: 1.2, maxWidth: 480 }}>
              What you can build
            </h2>
          </div>
          <div className="ap-build-grid">
            {BUILD_ITEMS.map(({ Icon, title, desc }) => (
              <div key={title} className="ap-build-card" style={{ border: `1px solid ${BORDER}`, borderRadius: 10, padding: "28px 24px" }}>
                <Icon size={20} strokeWidth={1.5} color={NAVY} style={{ marginBottom: 14 }} />
                <div style={{ fontSize: "0.95rem", fontWeight: 700, color: NAVY, marginBottom: 8 }}>{title}</div>
                <div style={{ fontSize: "0.84rem", color: SLATE, lineHeight: 1.7 }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── API Capabilities ─────────────────────────────────────────────────── */}
      <section style={{ background: LIGHT, borderTop: `1px solid ${BORDER}`, padding: "96px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ marginBottom: 52 }}>
            <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: NAVY, marginBottom: 14 }}>Endpoints</div>
            <h2 style={{ fontSize: "clamp(1.75rem, 3vw, 2.4rem)", fontWeight: 800, color: NAVY, letterSpacing: "-0.025em", lineHeight: 1.2 }}>
              API Capabilities
            </h2>
          </div>
          <div className="ap-cap-grid">
            {CAPABILITIES.map(({ name, prefix, Icon, desc }) => (
              <div key={name} className="ap-cap-card" style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 10, padding: "22px" }}>
                <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                  <Icon size={17} strokeWidth={1.5} color={NAVY} style={{ marginTop: 2, flexShrink: 0 }} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 700, color: NAVY, fontSize: "0.9rem", marginBottom: 5 }}>{name}</div>
                    <code style={{ fontSize: "0.7rem", fontFamily: MONO, color: INDIGO, background: "#f0f0ff", padding: "2px 6px", borderRadius: 4 }}>{prefix}</code>
                    <p style={{ fontSize: "0.83rem", color: SLATE, lineHeight: 1.65, marginTop: 8, marginBottom: 0 }}>{desc}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Authentication ───────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", borderTop: `1px solid ${BORDER}`, padding: "96px 24px" }}>
        <div style={{ maxWidth: 960, margin: "0 auto" }}>
          <div style={{ marginBottom: 48 }}>
            <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: NAVY, marginBottom: 14 }}>Access control</div>
            <h2 style={{ fontSize: "clamp(1.75rem, 3vw, 2.4rem)", fontWeight: 800, color: NAVY, letterSpacing: "-0.025em", lineHeight: 1.2, marginBottom: 14 }}>
              Authentication
            </h2>
            <p style={{ fontSize: "1rem", color: SLATE, lineHeight: 1.75, maxWidth: 560 }}>
              Multiple authentication methods to fit every integration pattern — from quick prototypes to enterprise deployments with single sign-on.
            </p>
          </div>
          <div className="ap-auth-grid">
            {AUTH_METHODS.map(({ name, desc }) => (
              <div key={name} className="ap-auth-card" style={{ border: `1px solid ${BORDER}`, borderRadius: 10, padding: "22px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: NAVY, flexShrink: 0 }} />
                  <div style={{ fontWeight: 700, color: NAVY, fontSize: "0.9rem" }}>{name}</div>
                </div>
                <div style={{ fontSize: "0.83rem", color: SLATE, lineHeight: 1.65 }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Example Request ──────────────────────────────────────────────────── */}
      <section style={{ background: LIGHT, borderTop: `1px solid ${BORDER}`, padding: "96px 24px" }}>
        <div style={{ maxWidth: 1040, margin: "0 auto" }}>
          <div style={{ marginBottom: 48 }}>
            <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: NAVY, marginBottom: 14 }}>Quickstart</div>
            <h2 style={{ fontSize: "clamp(1.75rem, 3vw, 2.4rem)", fontWeight: 800, color: NAVY, letterSpacing: "-0.025em", lineHeight: 1.2 }}>
              Example Request
            </h2>
          </div>
          <div className="ap-code-grid">
            {/* Request panel */}
            <div style={{ background: "#0d1117", borderRadius: 12, overflow: "hidden" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "13px 18px", borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                  <Terminal size={13} color="#8b949e" />
                  <span style={{ fontSize: "0.75rem", fontFamily: MONO, color: "#8b949e" }}>curl</span>
                </div>
                <button onClick={copyCmd} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: "0.72rem", color: copied ? "#3fb950" : "#8b949e", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
              <pre style={{ margin: 0, padding: "22px 18px", fontFamily: MONO, fontSize: "0.78rem", lineHeight: 1.9, overflowX: "auto", whiteSpace: "pre" }}>
                <span style={{ color: "#8b949e" }}>{"# Public — no auth required\n"}</span>
                <span style={{ color: "#79c0ff" }}>curl</span>
                <span style={{ color: "#c9d1d9" }}>{" -X "}</span>
                <span style={{ color: "#a5d6ff" }}>GET</span>
                <span style={{ color: "#c9d1d9" }}>{" \\\n  "}</span>
                <span style={{ color: "#a5d6ff" }}>{"\"https://api.synaptiq.academy/api/status\""}</span>
                <span style={{ color: "#c9d1d9" }}>{" \\\n  -H "}</span>
                <span style={{ color: "#a5d6ff" }}>{"\"Accept: application/json\""}</span>
              </pre>
            </div>
            {/* Response panel */}
            <div style={{ background: "#0d1117", borderRadius: 12, overflow: "hidden" }}>
              <div style={{ padding: "13px 18px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", gap: 10 }}>
                <span style={{ fontSize: "0.75rem", fontFamily: MONO, color: "#3fb950", fontWeight: 600 }}>200 OK</span>
                <span style={{ fontSize: "0.75rem", fontFamily: MONO, color: "#8b949e" }}>Response</span>
              </div>
              <pre style={{ margin: 0, padding: "22px 18px", fontFamily: MONO, fontSize: "0.75rem", lineHeight: 1.9, overflowX: "auto", color: "#c9d1d9", whiteSpace: "pre" }}>
                {"{\n  "}<span style={{ color: "#79c0ff" }}>{"\"platform\""}</span>{": "}<span style={{ color: "#a5d6ff" }}>{"\"Synaptiq\""}</span>{",\n  "}
                <span style={{ color: "#79c0ff" }}>{"\"status\""}</span>{": "}<span style={{ color: "#a5d6ff" }}>{"\"operational\""}</span>{",\n  "}
                <span style={{ color: "#79c0ff" }}>{"\"components\""}</span>{":\n    "}
                <span style={{ color: "#79c0ff" }}>{"\"api\""}</span>{": "}<span style={{ color: "#a5d6ff" }}>{"\"operational\""}</span>{",\n    "}
                <span style={{ color: "#79c0ff" }}>{"\"database\""}</span>{": "}<span style={{ color: "#a5d6ff" }}>{"\"operational\""}</span>{",\n    "}
                <span style={{ color: "#79c0ff" }}>{"\"ai\""}</span>{": "}<span style={{ color: "#a5d6ff" }}>{"\"operational\""}</span>{",\n    "}
                <span style={{ color: "#79c0ff" }}>{"\"billing\""}</span>{": "}<span style={{ color: "#a5d6ff" }}>{"\"operational\""}</span>{"\n}"}
              </pre>
            </div>
          </div>
          <p style={{ marginTop: 16, fontSize: "0.8rem", color: "#94a3b8" }}>
            This is the live <code style={{ fontFamily: MONO, fontSize: "0.78rem" }}>GET /api/status</code> endpoint. No authentication required.
          </p>
        </div>
      </section>

      {/* ── SDKs ─────────────────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", borderTop: `1px solid ${BORDER}`, padding: "96px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ marginBottom: 52 }}>
            <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: NAVY, marginBottom: 14 }}>Client libraries</div>
            <h2 style={{ fontSize: "clamp(1.75rem, 3vw, 2.4rem)", fontWeight: 800, color: NAVY, letterSpacing: "-0.025em", lineHeight: 1.2 }}>
              SDKs &amp; Libraries
            </h2>
          </div>
          <div className="ap-sdk-grid">
            {SDKS.map(({ name, tag, desc }) => (
              <div key={name} className="ap-sdk-card" style={{ border: `1px solid ${BORDER}`, borderRadius: 10, padding: "28px 24px" }}>
                <div style={{ fontWeight: 700, color: NAVY, fontSize: "1rem", marginBottom: 10 }}>{name}</div>
                <code style={{ fontSize: "0.7rem", fontFamily: MONO, color: INDIGO, background: "#f0f0ff", padding: "3px 8px", borderRadius: 4 }}>{tag}</code>
                <p style={{ fontSize: "0.84rem", color: SLATE, lineHeight: 1.7, marginTop: 12, marginBottom: 0 }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Security ─────────────────────────────────────────────────────────── */}
      <section style={{ background: LIGHT, borderTop: `1px solid ${BORDER}`, padding: "96px 24px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ marginBottom: 52 }}>
            <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: NAVY, marginBottom: 14 }}>Trust</div>
            <h2 style={{ fontSize: "clamp(1.75rem, 3vw, 2.4rem)", fontWeight: 800, color: NAVY, letterSpacing: "-0.025em", lineHeight: 1.2 }}>
              Security by design
            </h2>
          </div>
          <div className="ap-sec-grid">
            {SECURITY_ITEMS.map(({ name, desc }) => (
              <div key={name} style={{ display: "flex", gap: 14 }}>
                <div style={{ width: 20, height: 20, borderRadius: "50%", background: "#dbeafe", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
                  <Check size={11} color={NAVY} strokeWidth={2.5} />
                </div>
                <div>
                  <div style={{ fontWeight: 700, color: NAVY, fontSize: "0.92rem", marginBottom: 4 }}>{name}</div>
                  <div style={{ fontSize: "0.84rem", color: SLATE, lineHeight: 1.65 }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", borderTop: `1px solid ${BORDER}`, padding: "96px 24px", textAlign: "center" }}>
        <div style={{ maxWidth: 560, margin: "0 auto" }}>
          <h2 style={{ fontSize: "clamp(1.75rem, 3vw, 2.5rem)", fontWeight: 800, color: NAVY, letterSpacing: "-0.025em", marginBottom: 18 }}>
            Ready to build with Synaptiq?
          </h2>
          <p style={{ fontSize: "1rem", color: SLATE, lineHeight: 1.75, marginBottom: 40 }}>
            Explore the documentation to get started, or contact us to discuss your integration requirements.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <Link to="/documentation" style={{ display: "inline-flex", alignItems: "center", gap: 8, background: NAVY, color: "#fff", padding: "13px 28px", borderRadius: 8, fontWeight: 600, fontSize: "0.9rem", textDecoration: "none" }}>
              Read Documentation <ArrowRight size={16} />
            </Link>
            <Link to="/contact" style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "#fff", color: NAVY, padding: "13px 28px", borderRadius: 8, fontWeight: 600, fontSize: "0.9rem", textDecoration: "none", border: `1.5px solid ${BORDER}` }}>
              Contact Us
            </Link>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}

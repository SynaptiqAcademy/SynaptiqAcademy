/* eslint-disable */
import React, { useState, useRef, useCallback, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { ChevronDown, Menu, X } from "lucide-react";

const NAVY   = "#0F2847";
const T_GRAY = "#64748b";
const T_MAIN = "#0a0f1a";
const T_FAINT= "#94a3b8";
const BORDER = "#e8edf3";

// ─── Nav data ─────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { href: "/platform",         label: "Platform"      },
  { href: "/research",         label: "Research"      },
  { href: "/ai-workspace",     label: "AI Workspace"  },
  { href: "/for-institutions", label: "Institutions"  },
  { type: "resources" },
  { href: "/pricing",          label: "Pricing"       },
  { href: "/about",            label: "About"         },
];

const RESOURCES = [
  { href: "/resources/whats-new",        label: "What's New"       },
  { href: "/resources/customer-stories", label: "Customer Stories" },
  { href: "/resources/blog",             label: "Blog"             },
];

// ─── Shared link style helper ─────────────────────────────────────────────────

const linkStyle = {
  fontSize: "0.875rem",
  fontWeight: 500,
  color: T_GRAY,
  textDecoration: "none",
  padding: "8px 12px",
  borderRadius: 6,
  transition: "color 120ms",
  letterSpacing: "-0.005em",
  whiteSpace: "nowrap",
  display: "inline-block",
};

function NavLink({ href, label }) {
  return (
    <Link
      to={href}
      style={linkStyle}
      onMouseEnter={function(e) { e.currentTarget.style.color = T_MAIN; }}
      onMouseLeave={function(e) { e.currentTarget.style.color = T_GRAY; }}
    >
      {label}
    </Link>
  );
}

// ─── Resources dropdown ───────────────────────────────────────────────────────

function ResourcesDropdown() {
  const [open, setOpen] = useState(false);
  const timer = useRef(null);

  const enter = useCallback(function() { clearTimeout(timer.current); setOpen(true); }, []);
  const leave = useCallback(function() { timer.current = setTimeout(function() { setOpen(false); }, 120); }, []);
  useEffect(function() { return function() { clearTimeout(timer.current); }; }, []);

  return (
    <div style={{ position: "relative" }} onMouseEnter={enter} onMouseLeave={leave}>
      <button
        style={{
          display: "flex", alignItems: "center", gap: 4,
          fontSize: "0.875rem", fontWeight: 500, letterSpacing: "-0.005em",
          color: open ? T_MAIN : T_GRAY,
          padding: "8px 12px", borderRadius: 6,
          border: "none", background: "transparent", cursor: "pointer",
          transition: "color 120ms", whiteSpace: "nowrap",
        }}
      >
        Resources
        <ChevronDown
          size={11} strokeWidth={2.5}
          style={{ transition: "transform 200ms, color 120ms", transform: open ? "rotate(180deg)" : "none", color: open ? T_GRAY : T_FAINT }}
        />
      </button>

      {open && (
        <div
          style={{ position: "absolute", top: "calc(100% + 6px)", left: "50%", transform: "translateX(-50%)", zIndex: 200, paddingTop: 4 }}
          onMouseEnter={enter}
          onMouseLeave={leave}
        >
          <div style={{
            background: "#fff",
            border: `1px solid ${BORDER}`,
            borderRadius: 10,
            boxShadow: "0 4px 24px rgba(0,0,0,0.07), 0 1px 4px rgba(0,0,0,0.04)",
            padding: "4px",
            minWidth: 196,
            animation: "resFadeIn 120ms ease",
          }}>
            {RESOURCES.map(function(item) {
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  style={{ display: "block", padding: "9px 14px", fontSize: "0.84rem", fontWeight: 500, color: T_GRAY, textDecoration: "none", borderRadius: 7, transition: "color 100ms, background 100ms" }}
                  onMouseEnter={function(e) { e.currentTarget.style.color = T_MAIN; e.currentTarget.style.background = "#f8fafc"; }}
                  onMouseLeave={function(e) { e.currentTarget.style.color = T_GRAY; e.currentTarget.style.background = "transparent"; }}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Mobile resources accordion ───────────────────────────────────────────────

function MobileResources({ onClose }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        onClick={function() { setOpen(function(o) { return !o; }); }}
        style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", fontSize: "0.9rem", fontWeight: 500, color: T_GRAY, padding: "10px 0", background: "transparent", border: "none", cursor: "pointer" }}
      >
        Resources
        <ChevronDown size={12} strokeWidth={2.5} style={{ transition: "transform 200ms", transform: open ? "rotate(180deg)" : "none", color: T_FAINT }} />
      </button>
      {open && (
        <div style={{ paddingLeft: 12, paddingBottom: 4 }}>
          {RESOURCES.map(function(item) {
            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={onClose}
                style={{ display: "block", padding: "8px 6px", fontSize: "0.875rem", fontWeight: 500, color: T_FAINT, textDecoration: "none", transition: "color 100ms" }}
                onMouseEnter={function(e) { e.currentTarget.style.color = T_MAIN; }}
                onMouseLeave={function(e) { e.currentTarget.style.color = T_FAINT; }}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Layout ───────────────────────────────────────────────────────────────────

export default function MarketingLayout({ children }) {
  const { user, logout } = useAuth();
  const navigate         = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled,   setScrolled]   = useState(false);

  useEffect(function() {
    const onScroll = function() { setScrolled(window.scrollY > 12); };
    window.addEventListener("scroll", onScroll, { passive: true });
    return function() { window.removeEventListener("scroll", onScroll); };
  }, []);

  function closeMobile() { setMobileOpen(false); }

  return (
    <div className="marketing-page min-h-screen bg-white flex flex-col">

      {/* Animation */}
      <style>{`@keyframes resFadeIn { from { opacity: 0; } to { opacity: 1; } }`}</style>

      {/* ── Header ───────────────────────────────────────────────────────────── */}
      <header
        className="bg-white sticky top-0 z-30"
        style={{
          borderBottom: scrolled ? `1px solid ${BORDER}` : "1px solid transparent",
          boxShadow: scrolled ? "0 1px 12px rgba(0,0,0,.04)" : "none",
          transition: "border-color 200ms, box-shadow 200ms",
        }}
      >
        <div
          style={{
            maxWidth: 1280, margin: "0 auto", padding: "0 40px", height: 64,
            display: "grid",
            gridTemplateColumns: "1fr auto 1fr",
            alignItems: "center",
          }}
        >
          {/* Logo */}
          <div>
            <Link to="/" style={{ textDecoration: "none" }} onClick={closeMobile}>
              <span style={{ fontSize: "1rem", fontWeight: 800, color: NAVY, letterSpacing: "-0.04em" }}>SYNAPTIQ</span>
            </Link>
          </div>

          {/* Desktop nav — centered */}
          <nav className="hidden lg:flex items-center" style={{ gap: 0 }}>
            {NAV_ITEMS.map(function(item, i) {
              if (item.type === "resources") return <ResourcesDropdown key="resources" />;
              return <NavLink key={item.href} href={item.href} label={item.label} />;
            })}
          </nav>

          {/* Right: Sign In + Get Started + mobile toggle */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 8 }}>
            {/* Desktop */}
            <div className="hidden lg:flex items-center" style={{ gap: 8 }}>
              {user ? (
                <>
                  <Link to="/discover"
                    style={{ fontSize: "0.875rem", fontWeight: 500, color: T_GRAY, textDecoration: "none", padding: "8px 12px", transition: "color 120ms" }}
                    onMouseEnter={function(e) { e.currentTarget.style.color = T_MAIN; }}
                    onMouseLeave={function(e) { e.currentTarget.style.color = T_GRAY; }}>
                    Go to app
                  </Link>
                  <button
                    onClick={async function() { await logout(); navigate("/"); }}
                    style={{ fontSize: "0.875rem", fontWeight: 400, color: T_FAINT, background: "transparent", border: "none", cursor: "pointer", padding: "8px 10px", transition: "color 120ms" }}
                    onMouseEnter={function(e) { e.currentTarget.style.color = T_GRAY; }}
                    onMouseLeave={function(e) { e.currentTarget.style.color = T_FAINT; }}>
                    Sign out
                  </button>
                </>
              ) : (
                <>
                  {/* Sign In */}
                  <Link
                    to="/login"
                    data-testid="marketing-signin-link"
                    style={{ fontSize: "0.875rem", fontWeight: 500, color: T_GRAY, textDecoration: "none", padding: "8px 12px", borderRadius: 6, transition: "color 120ms" }}
                    onMouseEnter={function(e) { e.currentTarget.style.color = T_MAIN; }}
                    onMouseLeave={function(e) { e.currentTarget.style.color = T_GRAY; }}
                  >
                    Sign In
                  </Link>
                  {/* Get Started */}
                  <Link
                    to="/register"
                    data-testid="marketing-join-link"
                    style={{
                      fontSize: "0.875rem", fontWeight: 600, letterSpacing: "-0.01em",
                      color: "#fff", textDecoration: "none",
                      background: NAVY, padding: "8px 18px", borderRadius: 10,
                      transition: "opacity 150ms", display: "inline-block",
                    }}
                    onMouseEnter={function(e) { e.currentTarget.style.opacity = "0.85"; }}
                    onMouseLeave={function(e) { e.currentTarget.style.opacity = "1"; }}
                  >
                    Get Started
                  </Link>
                </>
              )}
            </div>

            {/* Mobile toggle */}
            <button
              className="lg:hidden"
              onClick={function() { setMobileOpen(function(o) { return !o; }); }}
              style={{ padding: 6, color: T_GRAY, background: "transparent", border: "none", cursor: "pointer", borderRadius: 6 }}
              aria-label="Toggle navigation"
            >
              {mobileOpen ? <X size={20} strokeWidth={1.5} /> : <Menu size={20} strokeWidth={1.5} />}
            </button>
          </div>
        </div>

        {/* Mobile drawer */}
        {mobileOpen && (
          <div
            className="lg:hidden"
            style={{ borderTop: `1px solid ${BORDER}`, background: "#fff", padding: "14px 24px 22px" }}
          >
            <div style={{ display: "flex", flexDirection: "column" }}>
              {NAV_ITEMS.map(function(item, i) {
                if (item.type === "resources") return <MobileResources key="resources" onClose={closeMobile} />;
                return (
                  <Link
                    key={item.href}
                    to={item.href}
                    onClick={closeMobile}
                    style={{ fontSize: "0.9rem", fontWeight: 500, color: T_GRAY, textDecoration: "none", padding: "10px 0", transition: "color 120ms" }}
                    onMouseEnter={function(e) { e.currentTarget.style.color = T_MAIN; }}
                    onMouseLeave={function(e) { e.currentTarget.style.color = T_GRAY; }}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>

            <div style={{ borderTop: `1px solid ${BORDER}`, marginTop: 14, paddingTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
              {user ? (
                <>
                  <Link to="/discover" onClick={closeMobile} style={{ fontSize: "0.88rem", fontWeight: 600, color: T_MAIN, textDecoration: "none" }}>Go to app →</Link>
                  <button onClick={async function() { await logout(); navigate("/"); closeMobile(); }}
                    style={{ fontSize: "0.88rem", color: T_FAINT, background: "transparent", border: "none", cursor: "pointer", textAlign: "left" }}>
                    Sign out
                  </button>
                </>
              ) : (
                <>
                  <Link to="/login" onClick={closeMobile} style={{ fontSize: "0.88rem", fontWeight: 500, color: T_MAIN, textDecoration: "none" }}>Sign in</Link>
                  <Link to="/register" onClick={closeMobile}
                    style={{ display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.88rem", fontWeight: 600, color: "#fff", background: NAVY, padding: "12px 0", borderRadius: 10, textDecoration: "none" }}>
                    Get Started
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      {/* ── Main ─────────────────────────────────────────────────────────────── */}
      <main className="flex-1">{children}</main>

      {/* ── Footer ───────────────────────────────────────────────────────────── */}
      <footer style={{ background: "#0a1220", color: "#94a3b8" }}>
        <style>{`
          .ft-nav { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0 48px; }
          @media (max-width: 1023px) { .ft-nav { grid-template-columns: repeat(2, 1fr); gap: 40px; } }
          @media (max-width: 599px)  { .ft-nav { grid-template-columns: 1fr; gap: 32px; } }
          .ft-bottom { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px; }
          @media (max-width: 599px)  { .ft-bottom { flex-direction: column; align-items: flex-start; } }
          .ft-legal-links { display: flex; align-items: center; flex-wrap: wrap; gap: 24px; }
          @media (max-width: 599px)  { .ft-legal-links { gap: 16px; } }
        `}</style>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10" style={{ paddingTop: 72, paddingBottom: 0 }}>

          {/* Brand */}
          <div style={{ marginBottom: 56 }}>
            <div style={{ fontSize: "1.05rem", fontWeight: 800, color: "#fff", letterSpacing: "-0.02em", marginBottom: 10 }}>SYNAPTIQ</div>
            <p style={{ fontSize: "0.82rem", lineHeight: 1.75, color: "#64748b", maxWidth: 320, margin: 0 }}>
              The research platform for modern academics. Research, collaborate, and publish without borders.
            </p>
          </div>

          {/* Four equal nav columns */}
          <div className="ft-nav" style={{ marginBottom: 56 }}>

            <FCol title="Product">
              <FL href="/platform">Platform</FL>
              <FL href="/research">Research</FL>
              <FL href="/ai-workspace">AI Workspace</FL>
              <FL href="/for-institutions">Institutions</FL>
              <FL href="/pricing">Pricing</FL>
            </FCol>

            <FCol title="Resources">
              <FL href="/documentation">Documentation</FL>
              <FL href="/help-center">Help Center</FL>
              <FL href="/developers">Developers</FL>
              <FL href="/resources/whats-new">What's New</FL>
              <FL href="/resources/customer-stories">Customer Stories</FL>
              <FL href="/resources/blog">Blog</FL>
            </FCol>

            <FCol title="Company">
              <FL href="/about">About Us</FL>
              <FL href="/contact">Contact</FL>
            </FCol>

            <FCol title="Legal">
              <FL href="/privacy">Privacy Policy</FL>
              <FL href="/terms">Terms of Service</FL>
              <FL href="/cookies">Cookie Policy</FL>
              <FL href="/gdpr">GDPR</FL>
              <FL href="/security">Security Center</FL>
            </FCol>
          </div>

          {/* Compliance badges */}
          <div className="flex flex-wrap items-center gap-3 pb-10" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
            {["ORCID Integrated", "GDPR Aligned", "TLS 1.2+ Encrypted", "SOC 2 (Coming Soon)", "ISO 27001 (Coming Soon)"].map(function(b) {
              return (
                <span key={b} style={{ fontSize: "0.62rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#475569", border: "1px solid rgba(255,255,255,0.08)", padding: "3px 10px", borderRadius: 4 }}>{b}</span>
              );
            })}
          </div>

          {/* Bottom bar */}
          <div className="ft-bottom" style={{ paddingTop: 28, paddingBottom: 40 }}>
            <div style={{ fontSize: "0.75rem", color: "#475569" }}>© 2026 Synaptiq. All rights reserved.</div>
            <div className="ft-legal-links">
              {[["Privacy Policy", "/privacy"], ["Terms", "/terms"], ["Cookies", "/cookies"], ["GDPR", "/gdpr"], ["Security", "/security"], ["Status", "/status"]].map(function([label, href]) {
                return (
                  <Link key={label} to={href} className="hover:text-white transition-colors" style={{ fontSize: "0.75rem", color: "#475569", textDecoration: "none" }}>{label}</Link>
                );
              })}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FCol({ title, children }) {
  return (
    <div>
      <div style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#fff", marginBottom: 16 }}>{title}</div>
      <div className="flex flex-col gap-3">{children}</div>
    </div>
  );
}

function FL({ href, children }) {
  return (
    <Link to={href} className="hover:text-white transition-colors block" style={{ fontSize: "0.82rem", color: "#64748b", textDecoration: "none" }}>
      {children}
    </Link>
  );
}

/* eslint-disable */
import React, { useState, useRef, useCallback, useEffect } from "react";
import { Button } from "@/components/ds";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { ChevronDown, Menu, X } from "lucide-react";
import { openPreferences } from "../../lib/cookieConsent";

const NAVY   = "var(--sq-brand-navy)";   // #0F2847, index.css
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

// Resources is both a section and a destination: the Research Library is
// /resources itself; What's New and the Blog sit beside it.
const RESOURCES = [
  { href: "/resources", label: "Research Library", desc: "Practical guidance for doing research well." },
  { href: "/whats-new", label: "What's New",       desc: "Product changes and release notes." },
  { href: "/blog",      label: "Blog",             desc: "Ideas about research and how it's changing." },
];
const RESOURCE_PREFIXES = ["/resources", "/whats-new", "/blog"];
const inResources = (path) => RESOURCE_PREFIXES.some((p) => path === p || path.startsWith(p + "/"));
const isCurrent = (path, href) => path === href || (href !== "/resources" && path.startsWith(href + "/"))
  || (href === "/resources" && path.startsWith("/resources/guides"));

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
  const wrap = useRef(null);
  const btn = useRef(null);
  const { pathname } = useLocation();
  const active = inResources(pathname);

  // Hover opens the menu. A click shortly after a hover-open (mouse users
  // hover, then click) keeps it open; otherwise a click toggles it (keyboard,
  // touch). Side effects live in handlers, not in state updaters.
  const openRef = useRef(false);
  const hoverOpenedAt = useRef(0);
  useEffect(function() { openRef.current = open; }, [open]);
  const enter = useCallback(function() {
    clearTimeout(timer.current);
    if (!openRef.current) hoverOpenedAt.current = Date.now();
    openRef.current = true;
    setOpen(true);
  }, []);
  const leave = useCallback(function() { timer.current = setTimeout(function() { openRef.current = false; setOpen(false); }, 120); }, []);
  useEffect(function() { return function() { clearTimeout(timer.current); }; }, []);
  useEffect(function() { setOpen(false); }, [pathname]);
  function toggle() {
    if (Date.now() - hoverOpenedAt.current < 600) { hoverOpenedAt.current = 0; openRef.current = true; setOpen(true); return; }
    hoverOpenedAt.current = 0;
    const next = !openRef.current;
    openRef.current = next;
    setOpen(next);
  }

  // Close on outside click or when focus leaves the menu.
  useEffect(function() {
    if (!open) return undefined;
    function onDoc(e) { if (wrap.current && !wrap.current.contains(e.target)) setOpen(false); }
    document.addEventListener("mousedown", onDoc);
    return function() { document.removeEventListener("mousedown", onDoc); };
  }, [open]);

  function onKeyDown(e) {
    if (e.key === "Escape" && open) { e.preventDefault(); setOpen(false); btn.current && btn.current.focus(); }
    if (e.key === "ArrowDown" && !open) { e.preventDefault(); setOpen(true); setTimeout(function() { var l = wrap.current && wrap.current.querySelector("a"); l && l.focus(); }, 0); }
  }
  function onBlur(e) { if (wrap.current && !wrap.current.contains(e.relatedTarget)) setOpen(false); }

  return (
    <div ref={wrap} style={{ position: "relative" }} onMouseEnter={enter} onMouseLeave={leave} onKeyDown={onKeyDown} onBlur={onBlur}>
      <button
        ref={btn}
        type="button"
        aria-expanded={open}
        aria-controls="nav-resources-menu"
        onClick={toggle}
        style={{
          display: "flex", alignItems: "center", gap: 4,
          fontSize: "0.875rem", fontWeight: 500, letterSpacing: "-0.005em",
          color: open || active ? T_MAIN : T_GRAY,
          padding: "8px 12px", borderRadius: 6,
          border: "none", background: "transparent", cursor: "pointer",
          transition: "color 120ms", whiteSpace: "nowrap",
          boxShadow: active ? "inset 0 -2px 0 " + NAVY : "none",
        }}
      >
        Resources
        <ChevronDown
          size={11} strokeWidth={2.5} aria-hidden="true"
          style={{ transition: "transform 200ms, color 120ms", transform: open ? "rotate(180deg)" : "none", color: open ? T_GRAY : T_FAINT }}
        />
      </button>

      {open && (
        <div
          id="nav-resources-menu"
          style={{ position: "absolute", top: "calc(100% + 6px)", left: "50%", transform: "translateX(-50%)", zIndex: 200, paddingTop: 4 }}
          onMouseEnter={enter}
          onMouseLeave={leave}
        >
          <ul style={{
            listStyle: "none", margin: 0,
            background: "#fff",
            border: `1px solid ${BORDER}`,
            borderRadius: 10,
            boxShadow: "0 4px 24px rgba(0,0,0,0.07), 0 1px 4px rgba(0,0,0,0.04)",
            padding: "6px",
            width: 280,
            animation: "resFadeIn 120ms ease",
          }}>
            {RESOURCES.map(function(item) {
              const current = isCurrent(pathname, item.href);
              return (
                <li key={item.href}>
                  <Link
                    to={item.href}
                    aria-current={current ? "page" : undefined}
                    style={{ display: "block", padding: "10px 14px", textDecoration: "none", borderRadius: 7, transition: "background 100ms", background: current ? "#f8fafc" : "transparent" }}
                    onMouseEnter={function(e) { e.currentTarget.style.background = "#f8fafc"; }}
                    onMouseLeave={function(e) { e.currentTarget.style.background = current ? "#f8fafc" : "transparent"; }}
                  >
                    <span style={{ display: "block", fontSize: "0.86rem", fontWeight: 600, color: T_MAIN }}>{item.label}</span>
                    <span style={{ display: "block", fontSize: "0.78rem", color: T_GRAY, marginTop: 2, lineHeight: 1.4 }}>{item.desc}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

// ─── Mobile resources accordion ───────────────────────────────────────────────

function MobileResources({ onClose }) {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(inResources(pathname));
  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls="mobile-resources-menu"
        onClick={function() { setOpen(function(o) { return !o; }); }}
        style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", fontSize: "0.9rem", fontWeight: 500, color: inResources(pathname) ? T_MAIN : T_GRAY, padding: "10px 0", background: "transparent", border: "none", cursor: "pointer" }}
      >
        Resources
        <ChevronDown size={12} strokeWidth={2.5} aria-hidden="true" style={{ transition: "transform 200ms", transform: open ? "rotate(180deg)" : "none", color: T_FAINT }} />
      </button>
      {open && (
        <ul id="mobile-resources-menu" style={{ listStyle: "none", margin: 0, paddingLeft: 12, paddingBottom: 4 }}>
          {RESOURCES.map(function(item) {
            const current = isCurrent(pathname, item.href);
            return (
              <li key={item.href}>
                <Link
                  to={item.href}
                  onClick={onClose}
                  aria-current={current ? "page" : undefined}
                  style={{ display: "block", padding: "8px 6px", fontSize: "0.875rem", fontWeight: current ? 600 : 500, color: current ? T_MAIN : T_GRAY, textDecoration: "none" }}
                >
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
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

          {/* Right: Sign In + Start Free + mobile toggle */}
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
                  {/* Start Free */}
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
                    Start Free
                  </Link>
                </>
              )}
            </div>

            {/* Mobile toggle */}
            <Button
              size="icon"
              variant="ghost"
              className="lg:hidden"
              onClick={function() { setMobileOpen(function(o) { return !o; }); }}
              aria-label="Toggle navigation"
              style={{
                padding: 6,
                color: T_GRAY,
                borderRadius: 6
              }}>
              {mobileOpen ? <X size={20} strokeWidth={1.5} /> : <Menu size={20} strokeWidth={1.5} />}
            </Button>
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
                  <Link to="/login" onClick={closeMobile} style={{ fontSize: "0.88rem", fontWeight: 500, color: T_MAIN, textDecoration: "none" }}>Sign In</Link>
                  <Link to="/register" onClick={closeMobile}
                    style={{ display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.88rem", fontWeight: 600, color: "#fff", background: NAVY, padding: "12px 0", borderRadius: 10, textDecoration: "none" }}>
                    Start Free
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
      <footer style={{ background: "var(--sq-brand-navy)", color: "#a3adbb" }}>
        <style>{`
          .ft-nav { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0 48px; }
          @media (max-width: 1023px) { .ft-nav { grid-template-columns: repeat(2, 1fr); gap: 40px; } }
          @media (max-width: 599px)  { .ft-nav { grid-template-columns: 1fr; gap: 32px; } }
        `}</style>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10" style={{ paddingTop: 72, paddingBottom: 0 }}>

          {/* Brand */}
          <div style={{ marginBottom: 56 }}>
            <div style={{ fontSize: "1.05rem", fontWeight: 800, color: "#fff", letterSpacing: "-0.02em", marginBottom: 10 }}>SYNAPTIQ</div>
            <p style={{ fontSize: "0.82rem", lineHeight: 1.75, color: "#a3adbb", maxWidth: 340, margin: 0 }}>
              Research starts with a question. Synaptiq helps you find the expertise and the people it needs, and keeps the work together.
            </p>
          </div>

          {/* Four equal nav columns */}
          <div className="ft-nav" style={{ marginBottom: 56 }}>

            <FCol title="Product">
              <FL href="/platform">Platform</FL>
              <FL href="/research">Research</FL>
              <FL href="/ai-workspace">AI Workspace</FL>
              <FL href="/for-institutions">Institutions</FL>
            </FCol>

            <FCol title="Resources">
              <FL href="/pricing">Pricing</FL>
              <FL href="/help-center">Help Center</FL>
              <FL href="/resources">Research Library</FL>
              <FL href="/whats-new">What's New</FL>
              <FL href="/blog">Blog</FL>
            </FCol>

            <FCol title="Company">
              <FL href="/about">About Us</FL>
              <FL href="/contact">Contact</FL>
            </FCol>

            <FCol title="Legal & Trust">
              <FL href="/privacy">Privacy Policy</FL>
              <FL href="/terms">Terms of Service</FL>
              <FL href="/cookies">Cookie Policy</FL>
              <FL href="/gdpr">Data Protection</FL>
              <FL href="/security">Security</FL>
              <FL href="/status">Status</FL>
              <div>
                <button type="button" onClick={openPreferences} className="hover:text-white transition-colors" data-testid="footer-cookie-settings"
                  style={{ display: "block", fontSize: "0.82rem", lineHeight: "inherit", color: "#a3adbb", background: "none", border: "none", padding: 0, cursor: "pointer", textAlign: "left", fontFamily: "inherit" }}>
                  Cookie settings
                </button>
              </div>
            </FCol>
          </div>

          {/* No certification-style badges: none are held. Factual security
              detail lives on /security, privacy detail in /privacy. */}
          <div style={{ borderBottom: "1px solid rgba(255,255,255,0.12)" }} />

          {/* Bottom bar: ownership only; navigation lives in the columns above. */}
          <div style={{ paddingTop: 28, paddingBottom: 40 }}>
            <div style={{ fontSize: "0.75rem", color: "#a3adbb" }}>© 2026 Synaptiq. All rights reserved.</div>
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
    <Link to={href} className="hover:text-white transition-colors block" style={{ fontSize: "0.82rem", color: "#a3adbb", textDecoration: "none" }}>
      {children}
    </Link>
  );
}

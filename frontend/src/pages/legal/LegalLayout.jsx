/* eslint-disable */
import React, { useState, useEffect, useRef, useCallback } from "react";
import { Search, Clock, Calendar, Tag, ChevronUp, Printer } from "lucide-react";
import MarketingLayout from "../../components/layout/MarketingLayout";

/* ─── CSS injected once ──────────────────────────────────────────────────────── */
const LEGAL_CSS = `
  :root {
    --lc-bg:         #ffffff;
    --lc-bg-alt:     #f8fafb;
    --lc-bg-hero:    #ffffff;
    --lc-text:       #0f172a;
    --lc-body:       #334155;
    --lc-muted:      #64748b;
    --lc-faint:      #94a3b8;
    --lc-border:     #e4e8ef;
    --lc-border-alt: #f1f5f9;
    --lc-navy:       #0F2847;
    --lc-link:       #0F2847;
    --lc-accent:     #3b82f6;
    --lc-toc-dot:    #0F2847;
    --lc-callout-bg: #f0f6ff;
    --lc-callout-bd: #93c5fd;
    --lc-tag-bg:     rgba(15,40,71,0.07);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --lc-bg:         #0f1117;
      --lc-bg-alt:     #171b24;
      --lc-bg-hero:    #0f1117;
      --lc-text:       #f1f5f9;
      --lc-body:       #cbd5e1;
      --lc-muted:      #94a3b8;
      --lc-faint:      #64748b;
      --lc-border:     #1e2535;
      --lc-border-alt: #222839;
      --lc-navy:       #60a5fa;
      --lc-link:       #60a5fa;
      --lc-accent:     #60a5fa;
      --lc-toc-dot:    #60a5fa;
      --lc-callout-bg: #1a2235;
      --lc-callout-bd: #2d4a7a;
      --lc-tag-bg:     rgba(96,165,250,0.1);
    }
  }

  /* ── Article typography ──────────────────────────────────────────────────── */
  .legal-article {
    font-size: 0.97rem;
    line-height: 1.8;
    color: var(--lc-body);
  }
  .legal-article p {
    margin: 0 0 0.9rem;
    color: var(--lc-body);
    line-height: 1.8;
  }
  .legal-article strong {
    color: var(--lc-text);
    font-weight: 600;
  }
  .legal-article em { font-style: italic; }
  .legal-article ul {
    margin: 0.25rem 0 0.9rem 1.5rem;
    list-style-type: disc;
  }
  .legal-article ol {
    margin: 0.25rem 0 0.9rem 1.5rem;
    list-style-type: decimal;
  }
  .legal-article li {
    margin-bottom: 0.3rem;
    line-height: 1.7;
    color: var(--lc-body);
  }
  .legal-article code {
    font-family: "SFMono-Regular", "Fira Code", "Menlo", monospace;
    font-size: 0.84em;
    background: var(--lc-bg-alt);
    color: var(--lc-navy);
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid var(--lc-border);
  }
  .legal-article table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
    border: 1px solid var(--lc-border);
    border-radius: 8px;
    overflow: hidden;
  }
  .legal-article th {
    background: var(--lc-bg-alt);
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    color: var(--lc-text);
    border-bottom: 1px solid var(--lc-border);
    font-size: 0.82rem;
  }
  .legal-article td {
    padding: 9px 14px;
    border-bottom: 1px solid var(--lc-border-alt);
    color: var(--lc-body);
    vertical-align: top;
  }
  .legal-article tr:last-child td { border-bottom: none; }
  .legal-article tr:hover td { background: var(--lc-bg-alt); }

  /* ── Tailwind utility class equivalents ──────────────────────────────────── */
  .legal-article .mt-3  { margin-top: 0.75rem; }
  .legal-article .mt-4  { margin-top: 1rem; }
  .legal-article .mt-6  { margin-top: 1.5rem; }
  .legal-article .space-y-1 > * + * { margin-top: 0.25rem; }
  .legal-article .space-y-2 > * + * { margin-top: 0.5rem; }
  .legal-article .space-y-4 > * + * { margin-top: 1rem; }
  .legal-article .text-sm { font-size: 0.875rem; }
  .legal-article .text-xs { font-size: 0.75rem; }
  .legal-article .list-disc    { list-style-type: disc; }
  .legal-article .list-decimal { list-style-type: decimal; }
  .legal-article .ml-5  { margin-left: 1.25rem; }
  .legal-article .ml-6  { margin-left: 1.5rem; }
  .legal-article .overflow-x-auto { overflow-x: auto; }
  .legal-article .font-serif { font-family: Georgia, "Times New Roman", serif; }
  .legal-article .font-medium { font-weight: 500; }
  .legal-article .font-semibold { font-weight: 600; }
  .legal-article .font-bold { font-weight: 700; }

  /* ── Links ───────────────────────────────────────────────────────────────── */
  .editorial-link {
    color: var(--lc-link);
    text-decoration: underline;
    text-decoration-color: transparent;
    text-underline-offset: 3px;
    transition: text-decoration-color 140ms;
  }
  .editorial-link:hover { text-decoration-color: currentColor; }

  /* ── Reading progress bar ────────────────────────────────────────────────── */
  #lc-progress-bar {
    position: fixed;
    top: 0;
    left: 0;
    height: 2px;
    background: var(--lc-navy);
    z-index: 9999;
    transition: width 80ms linear;
    pointer-events: none;
  }

  /* ── TOC ─────────────────────────────────────────────────────────────────── */
  .lc-toc-item {
    display: block;
    width: 100%;
    padding: 5px 10px;
    border-radius: 6px;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
    font-size: 0.78rem;
    line-height: 1.4;
    color: var(--lc-muted);
    border-left: 2px solid transparent;
    transition: color 120ms, border-color 120ms, background 120ms;
    font-family: inherit;
  }
  .lc-toc-item.active {
    color: var(--lc-toc-dot);
    font-weight: 600;
    border-left-color: var(--lc-toc-dot);
    background: var(--lc-tag-bg);
  }
  .lc-toc-item:hover:not(.active) {
    color: var(--lc-body);
    background: var(--lc-bg-alt);
  }

  /* ── Section highlight ───────────────────────────────────────────────────── */
  .legal-section-search-match {
    outline: 2px solid var(--lc-accent);
    border-radius: 4px;
    scroll-margin-top: 100px;
  }

  /* ── Print ───────────────────────────────────────────────────────────────── */
  @media print {
    #lc-progress-bar { display: none; }
    .lc-toc-sidebar  { display: none !important; }
    .lc-hero-meta    { display: none; }
    .lc-search-wrap  { display: none; }
    .lc-back-top     { display: none; }
    .legal-article   { max-width: 100% !important; font-size: 10pt; }
    .legal-article table { page-break-inside: avoid; }
    .lc-section-card { page-break-inside: avoid; }
  }

  /* ── Callout box ─────────────────────────────────────────────────────────── */
  .legal-callout {
    background: var(--lc-callout-bg);
    border: 1px solid var(--lc-callout-bd);
    border-left: 4px solid var(--lc-accent);
    border-radius: 8px;
    padding: 14px 18px;
    margin: 1rem 0;
    font-size: 0.9rem;
    color: var(--lc-body);
    line-height: 1.7;
  }

  /* ── Info box (GDPR-style cards) ─────────────────────────────────────────── */
  .lc-right-card {
    background: var(--lc-bg-alt);
    border: 1px solid var(--lc-border);
    border-left: 3px solid var(--lc-navy);
    border-radius: 8px;
    padding: 14px 16px;
  }
  .lc-right-card > div:first-child {
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--lc-text);
    margin-bottom: 4px;
  }
  .lc-right-card > p {
    font-size: 0.85rem;
    color: var(--lc-muted);
    line-height: 1.6;
    margin: 0;
  }
`;

function InjectCSS() {
  return <style>{LEGAL_CSS}</style>;
}

/* ─── Reading progress bar ──────────────────────────────────────────────────── */
function ReadingProgress() {
  useEffect(() => {
    const bar = document.getElementById("lc-progress-bar");
    if (!bar) return;
    function update() {
      const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
      const pct = scrollHeight <= clientHeight ? 100 : (scrollTop / (scrollHeight - clientHeight)) * 100;
      bar.style.width = pct + "%";
    }
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);
  return <div id="lc-progress-bar" />;
}

/* ─── Section spy ───────────────────────────────────────────────────────────── */
function useSectionSpy(ids) {
  const [active, setActive] = useState(ids[0] || "");
  useEffect(() => {
    if (!ids.length || typeof IntersectionObserver === "undefined") return;
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting);
        if (visible.length) setActive(visible[0].target.id);
      },
      { rootMargin: "-80px 0px -60% 0px", threshold: 0 }
    );
    ids.forEach((id) => { const el = document.getElementById(id); if (el) obs.observe(el); });
    return () => obs.disconnect();
  }, [ids.join(",")]);
  return active;
}

/* ─── Back to top ───────────────────────────────────────────────────────────── */
function BackToTop() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    function onScroll() { setShow(window.scrollY > 600); }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  if (!show) return null;
  return (
    <button
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      className="lc-back-top"
      title="Back to top"
      style={{
        position: "fixed", bottom: 32, right: 32, zIndex: 50,
        width: 40, height: 40, borderRadius: "50%",
        background: "var(--lc-navy)", color: "#fff",
        border: "none", cursor: "pointer",
        display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
        transition: "opacity 180ms",
      }}
    >
      <ChevronUp size={16} strokeWidth={2} />
    </button>
  );
}

/* ════════════════════════════════════════════════════════════════════════════════
   EXPORTS
════════════════════════════════════════════════════════════════════════════════ */
export function LegalLayout({ eyebrow = "Legal", title, subtitle, lastUpdated, readingTime, version = "v1", sections = [], children }) {
  const [query, setQuery] = useState("");
  const tocIds = sections.map((s) => s.id);
  const activeSection = useSectionSpy(tocIds);

  const visibleSections = query.trim()
    ? sections.filter((s) => s.label.toLowerCase().includes(query.toLowerCase()))
    : sections;

  function scrollTo(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    /* flash highlight */
    el.classList.add("legal-section-search-match");
    setTimeout(() => el.classList.remove("legal-section-search-match"), 1800);
  }

  function handleSearch(e) {
    e.preventDefault();
    if (!query.trim()) return;
    const match = sections.find((s) => s.label.toLowerCase().includes(query.toLowerCase()));
    if (match) scrollTo(match.id);
  }

  return (
    <MarketingLayout>
      <InjectCSS />
      <ReadingProgress />

      {/* ── Hero ─────────────────────────────────────────────────────────────── */}
      <section style={{
        background: "var(--lc-bg-hero)",
        borderBottom: "1px solid var(--lc-border)",
        padding: "72px 0 52px",
      }}>
        <div style={{ maxWidth: 900, margin: "0 auto", padding: "0 32px" }}>
          {/* Eyebrow */}
          <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--lc-faint)", marginBottom: 14 }}>
            {eyebrow}
          </div>

          {/* Title */}
          <h1 style={{
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: "clamp(2rem, 4vw, 3rem)",
            fontWeight: 700,
            color: "var(--lc-text)",
            lineHeight: 1.1,
            letterSpacing: "-0.025em",
            margin: "0 0 14px",
          }}>
            {title}
          </h1>

          {/* Subtitle */}
          {subtitle && (
            <p style={{ fontSize: "1rem", color: "var(--lc-muted)", lineHeight: 1.7, maxWidth: 620, margin: "0 0 24px" }}>
              {subtitle}
            </p>
          )}

          {/* Meta pills */}
          <div className="lc-hero-meta" style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: subtitle ? 0 : 0 }}>
            {lastUpdated && (
              <div style={{ display: "flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 20, background: "var(--lc-bg-alt)", border: "1px solid var(--lc-border)", fontSize: "0.72rem", color: "var(--lc-muted)" }}>
                <Calendar size={11} strokeWidth={1.5} />
                <span>Updated {lastUpdated}</span>
              </div>
            )}
            {readingTime && (
              <div style={{ display: "flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 20, background: "var(--lc-bg-alt)", border: "1px solid var(--lc-border)", fontSize: "0.72rem", color: "var(--lc-muted)" }}>
                <Clock size={11} strokeWidth={1.5} />
                <span>{readingTime} read</span>
              </div>
            )}
            {version && (
              <div style={{ display: "flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 20, background: "var(--lc-tag-bg)", border: "1px solid var(--lc-border)", fontSize: "0.72rem", color: "var(--lc-navy)", fontWeight: 600 }}>
                <Tag size={10} strokeWidth={2} />
                <span>{version}</span>
              </div>
            )}
            <button
              onClick={() => window.print()}
              style={{ display: "flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 20, background: "var(--lc-bg-alt)", border: "1px solid var(--lc-border)", fontSize: "0.72rem", color: "var(--lc-muted)", cursor: "pointer", fontFamily: "inherit" }}
              title="Print this page"
            >
              <Printer size={11} strokeWidth={1.5} />
              <span>Print</span>
            </button>
          </div>
        </div>
      </section>

      {/* ── Body ─────────────────────────────────────────────────────────────── */}
      <div style={{ background: "var(--lc-bg)", minHeight: "60vh" }}>
        <div style={{ maxWidth: sections.length ? 1160 : 900, margin: "0 auto", padding: "56px 32px 120px" }}>
          {sections.length ? (
            <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: "0 64px", alignItems: "start" }}>

              {/* ── Sticky TOC ── */}
              <aside
                className="lc-toc-sidebar"
                style={{ position: "sticky", top: 24 }}
              >
                {/* Search */}
                <form onSubmit={handleSearch} className="lc-search-wrap" style={{ marginBottom: 20 }}>
                  <div style={{ position: "relative" }}>
                    <Search size={13} strokeWidth={1.5} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--lc-faint)", pointerEvents: "none" }} />
                    <input
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Search sections…"
                      style={{
                        width: "100%", boxSizing: "border-box",
                        padding: "7px 10px 7px 30px",
                        borderRadius: 7,
                        border: "1px solid var(--lc-border)",
                        background: "var(--lc-bg-alt)",
                        color: "var(--lc-text)",
                        fontSize: "0.75rem",
                        outline: "none",
                        fontFamily: "inherit",
                        transition: "border-color 140ms",
                      }}
                      onFocus={(e) => { e.target.style.borderColor = "var(--lc-navy)"; }}
                      onBlur={(e) => { e.target.style.borderColor = "var(--lc-border)"; }}
                    />
                  </div>
                </form>

                {/* TOC label */}
                <div style={{ fontSize: "0.62rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--lc-faint)", marginBottom: 8, padding: "0 10px" }}>
                  On this page
                </div>

                {/* TOC items */}
                <nav aria-label="Page sections">
                  {visibleSections.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => scrollTo(s.id)}
                      className={`lc-toc-item${activeSection === s.id ? " active" : ""}`}
                    >
                      {s.label}
                    </button>
                  ))}
                  {visibleSections.length === 0 && (
                    <div style={{ padding: "6px 10px", fontSize: "0.75rem", color: "var(--lc-faint)" }}>
                      No matching sections
                    </div>
                  )}
                </nav>
              </aside>

              {/* ── Article ── */}
              <article className="legal-article">
                {children}
              </article>
            </div>
          ) : (
            <article className="legal-article" style={{ maxWidth: 860, margin: "0 auto" }}>
              {children}
            </article>
          )}
        </div>
      </div>

      <BackToTop />
    </MarketingLayout>
  );
}

/* ─── Section ───────────────────────────────────────────────────────────────── */
export function Section({ id, title, children }) {
  return (
    <section
      id={id}
      className="lc-section-card"
      style={{ marginBottom: 56, scrollMarginTop: 96 }}
    >
      <h2
        style={{
          fontFamily: "Georgia, 'Times New Roman', serif",
          fontSize: "1.35rem",
          fontWeight: 700,
          color: "var(--lc-text)",
          margin: "0 0 18px",
          paddingBottom: 14,
          borderBottom: "1px solid var(--lc-border)",
          lineHeight: 1.3,
          letterSpacing: "-0.01em",
        }}
      >
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}

/* ─── Callout ───────────────────────────────────────────────────────────────── */
export function Callout({ children }) {
  return <div className="legal-callout">{children}</div>;
}

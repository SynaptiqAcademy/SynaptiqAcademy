import React, { useEffect } from "react";
import MarketingLayout from "../layout/MarketingLayout";
import { setPageSeo } from "../../lib/seo";
import "../landing/landing.css";
import "./legal.css";

/**
 * Shared reading layout for Privacy, Terms and Cookies: document header with
 * real version metadata, an optional plain-language summary, a contents list
 * (sticky beside the text on wide screens, a disclosure on narrow ones) and
 * numbered sections with stable anchors. Prints cleanly.
 */
export function LegalLayout({ kind, title, updated, version, summary, sections, seo, children }) {
  useEffect(() => setPageSeo(seo), [seo]);
  useEffect(() => {
    const id = window.location.hash.replace("#", "");
    if (id) setTimeout(() => document.getElementById(id)?.scrollIntoView({ block: "start" }), 50);
  }, []);

  const toc = (
    <ol>
      {sections.map((s, i) => <li key={s.id}><a href={`#${s.id}`}>{i + 1}. {s.title}</a></li>)}
    </ol>
  );

  return (
    <MarketingLayout>
      <div className="lp lg">
        <header className="lg-head">
          <div className="lp-wrap">
            <div className="lp-index"><b>Legal</b> {kind}</div>
            <h1 className="lg-title">{title}</h1>
            <p className="lp-mono lg-meta">Last updated {updated} · Version {version}</p>
          </div>
        </header>

        <div className="lp-wrap lg-body">
          <nav className="lg-toc" aria-label="Contents">
            <div className="lp-mono lg-toc-label">Contents</div>
            {toc}
          </nav>
          <details className="lg-toc-mobile">
            <summary>Contents</summary>
            <nav aria-label="Contents">{toc}</nav>
          </details>

          <article className="lg-article">
            {summary && (
              <section className="lg-summary" aria-labelledby="lg-summary-title">
                <h2 id="lg-summary-title" className="lp-mono">The short version</h2>
                {summary}
                <p className="lg-summary-note">The full text below is what applies.</p>
              </section>
            )}
            {sections.map((s, i) => (
              <section key={s.id} id={s.id} className="lg-section" aria-labelledby={`${s.id}-h`}>
                <h2 id={`${s.id}-h`}><span className="lp-mono lg-num">{i + 1}</span>{s.title}</h2>
                {s.body}
              </section>
            ))}
            {children}
          </article>
        </div>
      </div>
    </MarketingLayout>
  );
}

/** Accessible, mobile-safe table for inventories and retention. */
export function LegalTable({ caption, head, rows }) {
  return (
    <div className="lg-table" role="region" aria-label={caption} tabIndex={0}>
      <table>
        <caption>{caption}</caption>
        <thead><tr>{head.map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => (j === 0 ? <th key={j} scope="row">{c}</th> : <td key={j}>{c}</td>))}</tr>)}</tbody>
      </table>
    </div>
  );
}

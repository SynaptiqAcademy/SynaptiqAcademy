import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../layout/MarketingLayout";
import { setPageSeo } from "../../lib/seo";
import { LEGAL, LEGAL_DOCS, OPERATOR_PENDING } from "../../content/legal/meta";
import "../landing/landing.css";
import "./legal.css";

/**
 * The one reading layout for the Legal & Trust area: Privacy, Terms, Cookies
 * and Data Protection. Title, description and dates come from the canonical
 * metadata (content/legal/meta.js), never from the page.
 *
 *   LegalHeader      breadcrumb, title, one-line description, last updated /
 *                    version, optional actions (e.g. Manage cookie settings)
 *   LegalDocNav      the four documents, current one marked
 *   Contents         sticky beside the text on wide screens, a disclosure on
 *                    narrow ones
 *   sections         numbered, with stable anchors
 *   LegalContinue    the other documents, as a closing index
 *
 * Prints cleanly: navigation, actions and the closing index are hidden.
 */
const num = (i) => String(i + 1).padStart(2, "0");

function LegalDocNav({ current }) {
  return (
    <nav className="lg-docnav" aria-label="Legal documents">
      <ol>
        {LEGAL_DOCS.map((d) => (
          <li key={d.id}>
            {d.id === current
              ? <span className="lg-docnav-current" aria-current="page">{d.label}</span>
              : <Link to={d.path}>{d.label}</Link>}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function LegalHeader({ doc, actions }) {
  const meta = LEGAL[doc.id] || {};
  return (
    <header className="lg-head">
      <div className="lp-wrap">
        <div className="lp-mono lg-crumb"><b>Legal</b><span aria-hidden="true"> / </span>{doc.label}</div>
        <h1 id="lg-doc-title" className="lg-title">{doc.title}</h1>
        <p className="lg-dek">{doc.dek}</p>
        <dl className="lg-meta">
          {meta.updated && <div><dt className="lp-mono">Last updated</dt><dd>{meta.updated}</dd></div>}
          {meta.version && <div><dt className="lp-mono">Version</dt><dd className="lp-mono">{meta.version}</dd></div>}
        </dl>
        {actions && <div className="lg-actions">{actions}</div>}
        <LegalDocNav current={doc.id} />
      </div>
    </header>
  );
}

function LegalContinue({ current }) {
  return (
    <nav className="lg-continue" aria-labelledby="lg-continue-h">
      <h2 id="lg-continue-h" className="lp-mono">Continue</h2>
      <ul>
        {LEGAL_DOCS.filter((d) => d.id !== current).map((d) => (
          <li key={d.id}>
            <Link to={d.path}>
              <span className="lg-continue-title">{d.title}</span>
              <span className="lg-continue-dek">{d.dek}</span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function LegalLayout({ doc: docId, summary, sections, seo, actions, tocLabel = "Contents", children }) {
  const doc = LEGAL_DOCS.find((d) => d.id === docId);
  useEffect(() => setPageSeo(seo), [seo]);
  useEffect(() => {
    const id = window.location.hash.replace("#", "");
    if (id) setTimeout(() => document.getElementById(id)?.scrollIntoView({ block: "start" }), 50);
  }, []);

  const toc = (
    <ol>
      {sections.map((s, i) => <li key={s.id}><a href={`#${s.id}`}><span className="lp-mono lg-toc-num">{num(i)}</span>{s.title}</a></li>)}
    </ol>
  );

  return (
    <MarketingLayout>
      <div className="lp lg">
        <LegalHeader doc={doc} actions={actions} />

        <div className="lp-wrap lg-body">
          <nav className="lg-toc" aria-label={tocLabel}>
            <div className="lp-mono lg-toc-label">{tocLabel}</div>
            {toc}
          </nav>
          <details className="lg-toc-mobile">
            <summary>{tocLabel}</summary>
            <nav aria-label={tocLabel}>{toc}</nav>
          </details>

          <article className="lg-article" aria-labelledby="lg-doc-title">
            {summary && (
              <section className="lg-summary" aria-labelledby="lg-summary-title">
                <h2 id="lg-summary-title" className="lp-mono">In short</h2>
                {summary}
                <p className="lg-summary-note">The full text below is what applies.</p>
              </section>
            )}
            {sections.map((s, i) => (
              <section key={s.id} id={s.id} className="lg-section" aria-labelledby={`${s.id}-h`}>
                <h2 id={`${s.id}-h`}><span className="lp-mono lg-num">{num(i)}</span>{s.title}</h2>
                {s.body}
              </section>
            ))}
            {children}
            <LegalContinue current={doc.id} />
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

/** A labelled aside inside a section ("In practice", "Research data"...). */
export function LegalCallout({ label, children }) {
  return (
    <aside className="lg-callout" aria-label={label}>
      <div className="lp-mono lg-callout-label">{label}</div>
      {children}
    </aside>
  );
}

/** The controller's identity, from canonical metadata; says plainly when it
 *  isn't published yet. Renders name, address and registration details
 *  without layout changes once LEGAL.operator is filled in. */
export function LegalOperator() {
  const o = LEGAL.operator;
  if (!o) return <p>{OPERATOR_PENDING}</p>;
  return (
    <dl className="lg-operator">
      <div><dt className="lp-mono">Controller</dt><dd>{o.name}</dd></div>
      {o.address && <div><dt className="lp-mono">Registered address</dt><dd>{o.address}</dd></div>}
      {o.registration && <div><dt className="lp-mono">Registration</dt><dd>{o.registration}</dd></div>}
      {o.vat && <div><dt className="lp-mono">VAT</dt><dd>{o.vat}</dd></div>}
    </dl>
  );
}

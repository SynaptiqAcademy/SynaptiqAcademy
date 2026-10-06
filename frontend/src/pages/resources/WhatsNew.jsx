import React, { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../../components/layout/MarketingLayout";
import { setPageSeo } from "../../lib/seo";
import { trackMarketingEvent as track } from "../../lib/marketingAnalytics";
import { TYPES, AREAS, publishedNotes, formatDay } from "../../content/whats-new";
import "../../components/landing/landing.css";
import "../../components/whats-new/whats-new.css";

/**
 * /whats-new — the product ledger. Every note comes from
 * content/whats-new (published notes only), dated by production release.
 * Each note has a stable anchor (#note-<slug>) for sharing and support.
 */


function Note({ n, latest }) {
  return (
    <article id={`note-${n.slug}`} className={`wn-note ${latest ? "is-latest" : ""}`} aria-labelledby={`t-${n.slug}`}>
      <div className="wn-rail">
        <time dateTime={n.released_at} className="lp-mono wn-date">{formatDay(n.released_at)}</time>
        <a href={`#note-${n.slug}`} className="lp-mono wn-num" aria-label={`Permalink to product note ${n.number}`}
          onClick={() => track("product_note_opened", { note: n.slug })}>Note {String(n.number).padStart(3, "0")}</a>
      </div>
      <div className="wn-body">
        <div className="lp-mono wn-kind">
          <span className={`wn-type wn-type--${n.type}`}>{TYPES[n.type].label}</span>
          <span aria-hidden="true"> · </span>{AREAS[n.area]}
        </div>
        <h3 id={`t-${n.slug}`} className="wn-title">{n.title}</h3>
        <p className="wn-summary">{n.summary}</p>
        {n.details?.length > 0 && <ul className="wn-details">{n.details.map((d) => <li key={d}>{d}</li>)}</ul>}
        <div className="wn-foot">
          <span className="lp-mono wn-avail">{n.availability}</span>
          {n.link && (
            <Link to={n.link.href} className="lp-link" onClick={() => track("product_note_product_clicked", { note: n.slug, to: n.link.href })}>
              {n.link.label} →
            </Link>
          )}
        </div>
      </div>
    </article>
  );
}

export default function WhatsNew() {
  const notes = useMemo(() => publishedNotes(), []);

  useEffect(() => setPageSeo({
    title: "What's New — Synaptiq product notes",
    description: "A dated record of meaningful changes to Synaptiq: new capabilities, improvements and fixes that affect how the product works.",
    path: "/whats-new",
  }), []);
  useEffect(() => { track("whats_new_viewed", { notes: notes.length }); }, [notes.length]);
  useEffect(() => {
    const id = window.location.hash.replace("#", "");
    if (id) setTimeout(() => document.getElementById(id)?.scrollIntoView({ block: "start" }), 50);
  }, []);

  // Group by year, then month, newest first; no empty groups.
  const groups = [];
  notes.forEach((n) => {
    const key = n.released_at.slice(0, 7);
    let g = groups.find((x) => x.key === key);
    if (!g) {
      const d = new Date(`${key}-01T00:00:00Z`);
      g = { key, label: d.toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" }), notes: [] };
      groups.push(g);
    }
    g.notes.push(n);
  });
  const latest = notes[0];

  return (
    <MarketingLayout>
      <div className="lp wn">
        <section className="lp-hero wn-hero" aria-labelledby="wn-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>—</b> What's New</div>
            <h1 id="wn-title" className="lp-h1">What changed, and what it means.</h1>
            <p className="lp-hero-copy">A dated record of changes to Synaptiq that affect how you use it.</p>
            <dl className="wn-key" aria-label="Note types">
              {Object.values(TYPES).map((t) => (
                <div key={t.label}><dt className="lp-mono">{t.label}</dt><dd>{t.meaning}</dd></div>
              ))}
            </dl>
          </div>
        </section>

        <section className="lp-section lp-section--quiet" aria-labelledby="wn-ledger-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>01</b> The product ledger</div>
            <h2 id="wn-ledger-title" className="sr-only">Product notes, newest first</h2>
            {notes.length === 0 ? (
              <p className="lp-lede">No product notes have been published yet.</p>
            ) : (
              groups.map((g) => (
                <section key={g.key} className="wn-month" aria-label={g.label}>
                  <h3 className="lp-mono wn-month-label">{g.label}</h3>
                  {g.notes.map((n) => <Note key={n.slug} n={n} latest={latest && n.slug === latest.slug} />)}
                </section>
              ))
            )}
          </div>
        </section>

        <section className="lp-section wn-bridge" aria-labelledby="wn-bridge-title">
          <div className="lp-wrap">
            <h2 id="wn-bridge-title" className="sr-only">Elsewhere</h2>
            <dl className="wn-else">
              <div>
                <dt><Link to="/resources" className="wn-else-link" onClick={() => track("whats_new_resources_clicked")}>Resources</Link></dt>
                <dd>Need the method rather than the release note? Practical guidance on doing research.</dd>
              </div>
              <div>
                <dt><Link to="/blog" className="wn-else-link" onClick={() => track("whats_new_blog_clicked")}>Blog</Link></dt>
                <dd>Longer reads and perspectives.</dd>
              </div>
            </dl>
          </div>
        </section>
      </div>
    </MarketingLayout>
  );
}

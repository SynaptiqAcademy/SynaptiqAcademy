import React, { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import MarketingLayout from "../../components/layout/MarketingLayout";
import { setPageSeo } from "../../lib/seo";
import { trackMarketingEvent as track } from "../../lib/marketingAnalytics";
import { TASKS, TYPES, findPublished, publishedResources, readingMinutes, formatDate } from "../../content/resources";
import "../../components/landing/landing.css";
import "../../components/resources/resources.css";

/**
 * /resources/guides/:slug — one published guide. Unknown or unpublished
 * slugs render a not-found state marked noindex, never a draft.
 */

function useNoIndex(active) {
  useEffect(() => {
    if (!active) return undefined;
    const m = document.createElement("meta");
    m.name = "robots";
    m.content = "noindex";
    document.head.appendChild(m);
    return () => m.remove();
  }, [active]);
}

export default function ResourceArticle() {
  const { slug } = useParams();
  const r = findPublished(slug);
  useNoIndex(!r);

  useEffect(() => {
    if (!r) return undefined;
    track("resource_opened", { slug: r.slug, from: "direct" });
    return setPageSeo({ title: `${r.title} | Synaptiq Resources`, description: r.description, path: `/resources/guides/${r.slug}` });
  }, [r]);

  if (!r) {
    return (
      <MarketingLayout>
        <div className="lp rx">
          <section className="lp-hero rx-hero">
            <div className="lp-wrap">
              <div className="lp-index"><b>—</b> Resources</div>
              <h1 className="lp-h1">This guide isn't available.</h1>
              <p className="lp-hero-copy">It may have moved or not be published yet.</p>
              <p style={{ marginTop: 24 }}><Link to="/resources" className="lp-link">Back to the library →</Link></p>
            </div>
          </section>
        </div>
      </MarketingLayout>
    );
  }

  const related = publishedResources().filter((x) => x.task === r.task && x.slug !== r.slug).slice(0, 3);
  const updated = r.updated_at && r.updated_at !== r.published_at;

  return (
    <MarketingLayout>
      <div className="lp rx">
        <article className="rx-article" aria-labelledby="rx-a-title">
          <div className="lp-wrap rx-a-wrap">
            <div className="lp-index"><b>{String(r.number).padStart(3, "0")}</b> {TASKS[r.task]}</div>
            <h1 id="rx-a-title" className="rx-a-title">{r.title}</h1>
            <p className="rx-a-desc">{r.description}</p>
            <div className="lp-mono rx-a-meta">
              {TYPES[r.type]} · {readingMinutes(r)} min · {r.byline} · Published {formatDate(r.published_at)}
              {updated && ` · Updated ${formatDate(r.updated_at)}`}
            </div>

            <div className="rx-a-body">
              {r.body.map((b, i) => {
                if (b.h) return <h2 key={i}>{b.h}</h2>;
                if (b.list) return <ul key={i}>{b.list.map((x) => <li key={x}>{x}</li>)}</ul>;
                if (b.note) return <aside key={i} className="rx-a-note">{b.note}</aside>;
                return <p key={i}>{b.p}</p>;
              })}
            </div>

            {r.references?.length > 0 && (
              <section className="rx-a-refs" aria-labelledby="rx-refs">
                <h2 id="rx-refs" className="lp-mono">References</h2>
                <ol>{r.references.map((x) => <li key={x.text}>{x.url ? <a href={x.url} rel="noopener noreferrer" target="_blank">{x.text}</a> : x.text}</li>)}</ol>
              </section>
            )}

            {r.related_product && (
              <p className="rx-a-product lp-small">
                Related in Synaptiq: <Link to={r.related_product.href} className="lp-link"
                  onClick={() => track("resources_product_link_clicked", { to: r.related_product.href, from: r.slug })}>{r.related_product.label} →</Link>
              </p>
            )}

            {related.length > 0 && (
              <nav className="rx-a-related" aria-label="Related guides">
                <div className="lp-mono rx-label">More on {TASKS[r.task].toLowerCase()}</div>
                <ul>{related.map((x) => <li key={x.slug}><Link to={`/resources/guides/${x.slug}`}>{x.title}</Link></li>)}</ul>
              </nav>
            )}
            <p style={{ marginTop: 40 }}><Link to="/resources" className="lp-link">Back to the library →</Link></p>
          </div>
        </article>
      </div>
    </MarketingLayout>
  );
}

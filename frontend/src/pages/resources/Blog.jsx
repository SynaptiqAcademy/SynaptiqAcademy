import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../../components/layout/MarketingLayout";
import { setPageSeo } from "../../lib/seo";
import { trackMarketingEvent as track } from "../../lib/marketingAnalytics";
import { CATEGORIES, publishedPosts, readingMinutes, formatDate } from "../../content/blog";
import "../../components/landing/landing.css";
import "../../components/blog/blog.css";

/**
 * /blog — the Synaptiq Blog index. Everything listed comes from
 * content/blog (published posts only). Sections appear only when there is
 * content for them: the lead essay needs an editorial selection, subject
 * filters need more than one subject, search needs enough posts.
 */

const SEARCH_FROM = 8;


function Row({ p }) {
  return (
    <li className="bl-row">
      <div className="lp-mono bl-cat">{CATEGORIES[p.category]}</div>
      <h3 className="bl-title">
        <Link to={`/blog/${p.slug}`} onClick={() => track("blog_article_opened", { slug: p.slug, from: "index" })}>{p.title}</Link>
      </h3>
      <p className="bl-deck">{p.deck}</p>
      <div className="lp-mono bl-meta">
        <time dateTime={p.published_at}>{formatDate(p.published_at)}</time> · {readingMinutes(p)} min · {p.author.name}
      </div>
    </li>
  );
}

export default function Blog() {
  const posts = useMemo(() => publishedPosts(), []);
  const [cat, setCat] = useState("all");
  const [q, setQ] = useState("");

  useEffect(() => setPageSeo({
    title: "Blog — Notes on how research gets done | Synaptiq",
    description: "Essays on research questions, collaboration, publishing and the technology around research, from Synaptiq.",
    path: "/blog",
  }), []);
  useEffect(() => { track("blog_viewed", { posts: posts.length }); }, [posts.length]);

  const lead = posts.find((p) => p.featured) || null;
  const rest = posts.filter((p) => p !== lead);
  const cats = Object.keys(CATEGORIES).filter((k) => posts.some((p) => p.category === k));
  const needle = q.trim().toLowerCase();
  const shown = rest.filter((p) => (cat === "all" || p.category === cat)
    && (!needle || `${p.title} ${p.deck}`.toLowerCase().includes(needle)));

  return (
    <MarketingLayout>
      <div className="lp bl">
        <section className="lp-hero bl-hero" aria-labelledby="bl-h1">
          <div className="lp-wrap">
            <div className="lp-index lp-eyebrow">Blog</div>
            <h1 id="bl-h1" className="lp-h1">Notes on how research gets done.</h1>
            <p className="lp-hero-copy">
              Essays on research questions, collaboration, publishing and the technology around them.
            </p>
          </div>
        </section>

        <section className="lp-section lp-section--quiet" aria-labelledby="bl-index-title">
          <div className="lp-wrap">
            {posts.length === 0 ? (
              <>
                <div className="lp-index"><b>01</b> The publication</div>
                <h2 id="bl-index-title" className="lp-h2">The first essays are being written.</h2>
                <div className="bl-standard">
                  <p className="lp-lede">Each piece will make an argument worth sending to a colleague. It will say who wrote it, and cite real sources wherever it makes a claim.</p>
                </div>
              </>
            ) : (
              <>
                <h2 id="bl-index-title" className="sr-only">Articles</h2>
                {lead && (
                  <article className="bl-lead" aria-labelledby="bl-lead-title">
                    <div className="lp-mono bl-label">Editor's selection · {CATEGORIES[lead.category]}</div>
                    <h3 id="bl-lead-title" className="bl-lead-title">
                      <Link to={`/blog/${lead.slug}`} onClick={() => track("blog_article_opened", { slug: lead.slug, from: "lead" })}>{lead.title}</Link>
                    </h3>
                    <p className="bl-lead-deck">{lead.deck}</p>
                    <div className="lp-mono bl-meta">
                      <time dateTime={lead.published_at}>{formatDate(lead.published_at)}</time> · {readingMinutes(lead)} min · {lead.author.name}
                    </div>
                  </article>
                )}

                {(cats.length > 1 || rest.length >= SEARCH_FROM) && (
                  <div className="bl-tools">
                    {rest.length >= SEARCH_FROM && (
                      <label className="bl-search">
                        <span className="sr-only">Search the Blog</span>
                        <input type="search" placeholder="Search the Blog" value={q} onChange={(e) => setQ(e.target.value)}
                          onBlur={() => { if (needle) track("blog_search_used", { results: shown.length }); }} />
                      </label>
                    )}
                    {cats.length > 1 && (
                      <div className="bl-filters" role="group" aria-label="Filter by subject">
                        {[["all", "All subjects"], ...cats.map((k) => [k, CATEGORIES[k]])].map(([k, label]) => (
                          <button key={k} type="button" aria-pressed={cat === k} className={cat === k ? "is-sel" : ""}
                            onClick={() => { setCat(k); track("blog_category_selected", { category: k }); }}>{label}</button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {rest.length > 0 && (
                  <>
                    <div className="lp-mono bl-label bl-label--rule">Latest</div>
                    {shown.length ? <ol className="bl-list">{shown.map((p) => <Row key={p.slug} p={p} />)}</ol>
                      : <p className="lp-small" role="status">No articles match that yet.</p>}
                  </>
                )}
              </>
            )}
          </div>
        </section>

        <section className="lp-section bl-bridge" aria-labelledby="bl-else-title">
          <div className="lp-wrap">
            <h2 id="bl-else-title" className="sr-only">Elsewhere</h2>
            <dl className="bl-else">
              <div>
                <dt><Link to="/resources" className="bl-else-link" onClick={() => track("blog_resource_clicked", { from: "index" })}>Resources</Link></dt>
                <dd>Need something practical? Guidance on doing the work.</dd>
              </div>
              <div>
                <dt><Link to="/whats-new" className="bl-else-link">What's New</Link></dt>
                <dd>What has changed in Synaptiq itself.</dd>
              </div>
              <div>
                <dt><Link to="/platform" className="bl-else-link" onClick={() => track("blog_product_context_clicked", { to: "platform", from: "index" })}>The Platform</Link></dt>
                <dd>How these ideas connect to the product.</dd>
              </div>
            </dl>
          </div>
        </section>
      </div>
    </MarketingLayout>
  );
}

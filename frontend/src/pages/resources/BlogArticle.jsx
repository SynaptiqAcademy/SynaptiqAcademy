import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import MarketingLayout from "../../components/layout/MarketingLayout";
import { setPageSeo } from "../../lib/seo";
import { trackMarketingEvent as track } from "../../lib/marketingAnalytics";
import { CATEGORIES, findPost, publishedPosts, readingMinutes, formatDate, tocFor, slugify } from "../../content/blog";
import { findPublished as findResource } from "../../content/resources";
import "../../components/landing/landing.css";
import "../../components/blog/blog.css";

/**
 * /blog/:slug — one published essay. Unknown, draft or archived
 * slugs render a noindex not-found state. Structured data is emitted only
 * from real metadata (dates, byline, publisher).
 */


function useHead(post) {
  useEffect(() => {
    const added = [];
    if (!post) {
      const m = document.createElement("meta"); m.name = "robots"; m.content = "noindex";
      document.head.appendChild(m); added.push(m);
    } else {
      const s = document.createElement("script");
      s.type = "application/ld+json";
      s.text = JSON.stringify({
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        headline: post.title,
        description: post.deck,
        datePublished: post.published_at,
        ...(post.updated_at ? { dateModified: post.updated_at } : {}),
        author: post.author.name === "Synaptiq Editorial"
          ? { "@type": "Organization", name: "Synaptiq" }
          : { "@type": "Person", name: post.author.name },
        publisher: { "@type": "Organization", name: "Synaptiq" },
        mainEntityOfPage: `https://www.synaptiq.academy/blog/${post.slug}`,
      });
      document.head.appendChild(s); added.push(s);
    }
    return () => added.forEach((el) => el.remove());
  }, [post]);
}

export default function BlogArticle() {
  const { slug } = useParams();
  const post = findPost(slug);
  const [copied, setCopied] = useState(false);
  useHead(post);

  useEffect(() => {
    if (!post) return undefined;
    track("blog_article_opened", { slug: post.slug, from: "direct" });
    return setPageSeo({ title: `${post.title} | Synaptiq Blog`, description: post.deck, path: `/blog/${post.slug}` });
  }, [post]);

  if (!post) {
    return (
      <MarketingLayout>
        <div className="lp bl">
          <section className="lp-hero bl-hero">
            <div className="lp-wrap">
              <div className="lp-index"><b>—</b> Blog</div>
              <h1 className="lp-h1">This article isn't available.</h1>
              <p className="lp-hero-copy">It may have moved or not be published.</p>
              <p style={{ marginTop: 24 }}><Link to="/blog" className="lp-link">Back to the Blog →</Link></p>
            </div>
          </section>
        </div>
      </MarketingLayout>
    );
  }

  const toc = tocFor(post);
  const relatedPosts = (post.related?.posts || []).map((s) => findPost(s)).filter(Boolean)
    .concat(publishedPosts().filter((p) => p.category === post.category && p.slug !== post.slug))
    .filter((p, i, a) => a.findIndex((x) => x.slug === p.slug) === i).slice(0, 2);
  const relatedResources = (post.related?.resources || []).map((s) => findResource(s)).filter(Boolean).slice(0, 2);
  const copy = async () => {
    try { await navigator.clipboard.writeText(window.location.href); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { /* ignore */ }
    track("blog_share_clicked", { slug: post.slug, method: "copy_link" });
  };

  return (
    <MarketingLayout>
      <div className="lp bl">
        <article className="bl-article" aria-labelledby="bl-a-title">
          <div className="lp-wrap bl-a-wrap">
            <div className="lp-mono bl-a-cat">{CATEGORIES[post.category]}</div>
            <h1 id="bl-a-title" className="bl-a-title">{post.title}</h1>
            <p className="bl-a-deck">{post.deck}</p>
            <div className="lp-mono bl-a-meta">
              <span>{post.author.name}</span> · <time dateTime={post.published_at}>{formatDate(post.published_at)}</time>
              {post.updated_at && <> · Updated <time dateTime={post.updated_at}>{formatDate(post.updated_at)}</time></>}
              {" "}· {readingMinutes(post)} min
              <button type="button" className="bl-copy" onClick={copy}>{copied ? "Link copied" : "Copy link"}</button>
            </div>

            {toc.length > 2 && (
              <nav className="bl-toc" aria-label="In this article">
                <div className="lp-mono">In this article</div>
                <ol>{toc.map((t) => <li key={t.id}><a href={`#${t.id}`}>{t.text}</a></li>)}</ol>
              </nav>
            )}

            <div className="bl-a-body">
              {post.body.map((b, i) => {
                if (b.h) return <h2 key={i} id={slugify(b.h)}>{b.h}</h2>;
                if (b.quote) return <blockquote key={i}>{b.quote}</blockquote>;
                if (b.list) return <ul key={i}>{b.list.map((x) => <li key={x}>{x}</li>)}</ul>;
                if (b.figure) {
                  return (
                    <figure key={i} className="bl-fig">
                      {b.figure.rows && (
                        <div className="bl-fig-scroll" tabIndex={0} role="region" aria-label={b.figure.caption}>
                          <table><tbody>{b.figure.rows.map((r, ri) => <tr key={ri}>{r.map((c, ci) => (ri === 0 ? <th key={ci} scope="col">{c}</th> : <td key={ci}>{c}</td>))}</tr>)}</tbody></table>
                        </div>
                      )}
                      <figcaption className="lp-mono">{b.figure.caption}</figcaption>
                    </figure>
                  );
                }
                return <p key={i}>{b.p}</p>;
              })}
            </div>

            {post.author.bio && <p className="bl-a-bio"><b>{post.author.name}</b> {post.author.bio}</p>}

            {post.references?.length > 0 && (
              <section className="bl-a-refs" aria-labelledby="bl-refs">
                <h2 id="bl-refs" className="lp-mono">References</h2>
                <ol>{post.references.map((r) => <li key={r.text}>{r.url ? <a href={r.url} rel="noopener noreferrer" target="_blank">{r.text}</a> : r.text}</li>)}</ol>
              </section>
            )}

            {(relatedPosts.length > 0 || relatedResources.length > 0 || post.related?.product) && (
              <aside className="bl-a-related" aria-label="Related reading">
                <div className="lp-mono bl-label">Related reading</div>
                <ul>
                  {relatedPosts.map((p) => (
                    <li key={p.slug}><span className="lp-mono">Blog</span>
                      <Link to={`/blog/${p.slug}`} onClick={() => track("blog_related_article_clicked", { from: post.slug, to: p.slug })}>{p.title}</Link></li>
                  ))}
                  {relatedResources.map((r) => (
                    <li key={r.slug}><span className="lp-mono">Guide</span>
                      <Link to={`/resources/guides/${r.slug}`} onClick={() => track("blog_resource_clicked", { from: post.slug })}>{r.title}</Link></li>
                  ))}
                  {post.related?.product && (
                    <li><span className="lp-mono">In Synaptiq</span>
                      <Link to={post.related.product.href} onClick={() => track("blog_product_context_clicked", { from: post.slug, to: post.related.product.href })}>{post.related.product.label} →</Link></li>
                  )}
                </ul>
              </aside>
            )}

            <p style={{ marginTop: 40 }}><Link to="/blog" className="lp-link">Back to the Blog →</Link></p>
          </div>
        </article>
      </div>
    </MarketingLayout>
  );
}

import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../../components/layout/MarketingLayout";
import { setPageSeo } from "../../lib/seo";
import { trackMarketingEvent as track } from "../../lib/marketingAnalytics";
import { TASKS, TYPES, publishedResources, readingMinutes, formatDate } from "../../content/resources";
import "../../components/landing/landing.css";
import "../../components/resources/resources.css";

/**
 * /resources — the research library index. Everything listed comes from
 * content/resources (published guides only). Categories appear only when they
 * contain at least one published guide; search and filters appear only once
 * there is enough to search. Product help, editorial and product updates are
 * linked separately and labelled as what they are.
 */

const FONT_HREF = "https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=swap";
const SEARCH_FROM = 6;   // show search/filters once the library has this many guides

function useDisplayFont() {
  useEffect(() => {
    if (document.querySelector(`link[href="${FONT_HREF}"]`)) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = FONT_HREF;
    document.head.appendChild(link);
  }, []);
}

const num = (n) => String(n).padStart(3, "0");

function Entry({ r }) {
  const updated = r.updated_at && r.updated_at !== r.published_at;
  return (
    <li className="rx-entry">
      <span className="lp-mono rx-num" aria-hidden="true">{num(r.number)}</span>
      <div className="rx-body">
        <div className="lp-mono rx-task">{TASKS[r.task]}</div>
        <h3 className="rx-title">
          <Link to={`/resources/guides/${r.slug}`} onClick={() => track("resource_opened", { slug: r.slug, from: "index" })}>{r.title}</Link>
        </h3>
        <p className="rx-desc">{r.description}</p>
        <div className="lp-mono rx-meta">
          {TYPES[r.type]} · {readingMinutes(r)} min · {updated ? "Updated" : "Published"} {formatDate(updated ? r.updated_at : r.published_at)}
        </div>
      </div>
    </li>
  );
}

export default function Resources() {
  useDisplayFont();
  const all = useMemo(() => publishedResources(), []);
  const [task, setTask] = useState("all");
  const [q, setQ] = useState("");

  useEffect(() => setPageSeo({
    title: "Resources — A working library for research | Synaptiq",
    description: "Practical, evergreen guidance on defining research, working with others, publishing and using research technology responsibly, from Synaptiq.",
    path: "/resources",
  }), []);
  useEffect(() => { track("resources_viewed", { guides: all.length }); }, [all.length]);

  const tasksWithContent = Object.keys(TASKS).filter((k) => all.some((r) => r.task === k));
  const featured = all.filter((r) => r.featured).slice(0, 3);
  const needle = q.trim().toLowerCase();
  const shown = all.filter((r) => (task === "all" || r.task === task)
    && (!needle || `${r.title} ${r.description}`.toLowerCase().includes(needle)));

  return (
    <MarketingLayout>
      <div className="lp rx">
        {/* ── Intro ──────────────────────────────────────────────────── */}
        <section className="lp-hero rx-hero" aria-labelledby="rx-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>—</b> Resources</div>
            <h1 id="rx-title" className="lp-h1">A working library for research.</h1>
            <p className="lp-hero-copy">
              Practical guidance on defining research, working with others and publishing,
              written to be useful whether or not you use Synaptiq.
            </p>
          </div>
        </section>

        {/* ── The research index ─────────────────────────────────────── */}
        <section id="library" className="lp-section lp-section--quiet" aria-labelledby="rx-index-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>01</b> The research index</div>
            <h2 id="rx-index-title" className="lp-h2">{all.length ? "What are you trying to do?" : "The first guides are in preparation."}</h2>

            {all.length === 0 ? (
              <div className="rx-empty">
                <p className="lp-lede">
                  We'd rather publish a few guides that are genuinely useful than many that aren't. Each one is
                  reviewed before it appears here, with real references wherever it makes a claim.
                </p>
              </div>
            ) : (
              <>
                {featured.length > 0 && (
                  <div className="rx-start">
                    <div className="lp-mono rx-label">Start here</div>
                    <ol className="rx-list">{featured.map((r) => <Entry key={r.slug} r={r} />)}</ol>
                  </div>
                )}

                {all.length >= SEARCH_FROM && (
                  <div className="rx-tools">
                    <label className="rx-search">
                      <span className="sr-only">Search the library</span>
                      <input type="search" placeholder="Search the library" value={q}
                        onChange={(e) => setQ(e.target.value)}
                        onBlur={() => { if (needle) track("resource_search_used", { results: shown.length }); }} />
                    </label>
                    {tasksWithContent.length > 1 && (
                      <div className="rx-filters" role="group" aria-label="Filter by research task">
                        {[["all", "All"], ...tasksWithContent.map((k) => [k, TASKS[k]])].map(([k, label]) => (
                          <button key={k} type="button" aria-pressed={task === k} className={task === k ? "is-sel" : ""}
                            onClick={() => { setTask(k); track("resource_category_selected", { task: k }); }}>{label}</button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div className="lp-mono rx-label">{task === "all" ? "All guides" : TASKS[task]} · {shown.length}</div>
                {shown.length ? (
                  <ol className="rx-list">{shown.map((r) => <Entry key={r.slug} r={r} />)}</ol>
                ) : (
                  <p className="lp-small" role="status">Nothing in the library matches that yet.</p>
                )}
              </>
            )}
          </div>
        </section>

        {/* ── Elsewhere: labelled by kind ────────────────────────────── */}
        <section className="lp-section" aria-labelledby="rx-else-title">
          <div className="lp-wrap">
            <div className="lp-index"><b>02</b> Elsewhere</div>
            <h2 id="rx-else-title" className="sr-only">Other kinds of Synaptiq writing</h2>
            <dl className="rx-else">
              <div>
                <dt><span className="lp-mono rx-kind">Product help</span><Link to="/help-center" className="rx-else-link">Help Center</Link></dt>
                <dd>Answers about your account, billing, AI Credits and data.</dd>
              </div>
              <div>
                <dt><span className="lp-mono rx-kind">Editorial</span>
                  <Link to="/resources/blog" className="rx-else-link" onClick={() => track("resources_blog_clicked")}>Blog</Link></dt>
                <dd>Longer articles and perspectives.</dd>
              </div>
              <div>
                <dt><span className="lp-mono rx-kind">Product updates</span>
                  <Link to="/resources/whats-new" className="rx-else-link" onClick={() => track("resources_whats_new_clicked")}>What's New</Link></dt>
                <dd>Changes to Synaptiq itself.</dd>
              </div>
            </dl>
          </div>
        </section>

        {/* ── Quiet transition to the product ─────────────────────────── */}
        <section className="lp-section lp-section--quiet rx-quiet" aria-labelledby="rx-platform-title">
          <div className="lp-wrap">
            <h2 id="rx-platform-title" className="rx-quiet-title">Guidance helps with the method. Synaptiq organises the work around it.</h2>
            <p className="rx-quiet-links">
              <Link to="/platform" className="lp-link" onClick={() => track("resources_product_link_clicked", { to: "platform" })}>Explore the Platform →</Link>
              <Link to="/research" className="lp-link" onClick={() => track("resources_product_link_clicked", { to: "research" })}>See the research workflow →</Link>
            </p>
          </div>
        </section>
      </div>
    </MarketingLayout>
  );
}

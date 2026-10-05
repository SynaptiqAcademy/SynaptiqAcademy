import React, { useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { trackMarketingEvent as track } from "@/lib/marketingAnalytics";

const EXAMPLE = "How can public hospitals reduce patient waiting times without increasing staff workload?";

/**
 * "What are you researching?" — the Landing page's working product moment.
 *
 * Calls the public POST /api/public/research-preview: a deterministic,
 * no-AI, no-database reading of the visitor's question
 * (backend/services/public_demo/research_preview.py). It never returns or
 * shows a person. The question text is never sent to analytics.
 */
export default function ResearchQuestion({ onResult }) {
  const [query, setQuery] = useState("");
  const [asked, setAsked] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [announce, setAnnounce] = useState("");
  const mapRef = useRef(null);

  const read = async (text) => {
    const q = (text ?? query).trim();
    if (!q) return;
    setLoading(true);
    setError("");
    setAnnounce("Reading your question…");
    track("research_demo_started");
    try {
      const { data } = await api.post("/public/research-preview", { query: q });
      setAsked(q);
      setResult(data);
      onResult?.(data, q);
      track("research_demo_completed", { matched_taxonomy: !!data?.matched_taxonomy });
      const n = (data.themes?.length || 0) + (data.methods?.length || 0) + (data.complementary_disciplines?.length || 0);
      setAnnounce(`Research map ready: ${n} items across research areas, methods and complementary perspectives.`);
      setTimeout(() => mapRef.current?.focus({ preventScroll: false }), 60);
    } catch (err) {
      const status = err?.response?.status;
      const msg = status === 429
        ? "That's several questions in a short time. Please wait a minute and try again."
        : status === 422
        ? "Please keep the question under 600 characters."
        : "The preview isn't available right now. Please try again shortly.";
      setError(msg);
      setAnnounce(msg);
    } finally {
      setLoading(false);
    }
  };

  const submit = (e) => { e.preventDefault(); read(); };
  const useExample = () => { setQuery(EXAMPLE); read(EXAMPLE); };

  return (
    <section id="research-question" className="lp-section lp-section--quiet" aria-labelledby="lp-q-title">
      <div className="lp-wrap">
        <div className="lp-index"><b>01</b> The question</div>
        <h2 id="lp-q-title" className="lp-h2">What are you researching?</h2>
        <p className="lp-lede">
          Write it the way you'd put it to a colleague. Synaptiq reads the question
          for its structure and the expertise it implies. No account needed, and
          nothing you type here is saved.
        </p>

        <form className="lp-q-form" onSubmit={submit}>
          <label htmlFor="lp-q-input" className="lp-q-label lp-mono">Your question</label>
          <textarea
            id="lp-q-input"
            className="lp-q-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit(e); }}
            placeholder={EXAMPLE}
            rows={2}
            maxLength={600}
            aria-describedby="lp-q-help"
          />
          <div className="lp-q-row">
            <div className="lp-q-hint">
              <span id="lp-q-help" className="lp-small">{query.length}/600</span>
              {!query && (
                <button type="button" className="lp-textbtn" onClick={useExample} disabled={loading}>
                  Use the example
                </button>
              )}
            </div>
            <button type="submit" className="lp-btn lp-btn--primary" disabled={loading || !query.trim()}
              style={{ opacity: loading || !query.trim() ? 0.55 : 1 }}>
              {loading ? "Reading…" : "Read the question"}
            </button>
          </div>
        </form>

        <p className="sr-only" aria-live="polite">{announce}</p>
        {error && <p role="alert" className="lp-small" style={{ color: "var(--mark)", marginTop: 14 }}>{error}</p>}

        {result && <ResearchMap ref={mapRef} question={asked} result={result} />}
      </div>
    </section>
  );
}

function marked(question, structure) {
  // Underline the parts of the visitor's own sentence that the reading found.
  const spans = [];
  const add = (text, cls) => {
    if (!text) return;
    const i = question.toLowerCase().indexOf(text.toLowerCase());
    if (i >= 0) spans.push({ start: i, end: i + text.length, cls });
  };
  if (structure?.kind === "aim") {
    add(structure.subject, "lp-mk lp-mk--subject");
    add(structure.objective, "lp-mk lp-mk--aim");
  }
  (structure?.constraints || []).forEach((c) => add(c, "lp-mk lp-mk--constraint"));
  spans.sort((a, b) => a.start - b.start);
  const out = [];
  let pos = 0;
  spans.forEach((s, k) => {
    if (s.start < pos) return;
    out.push(question.slice(pos, s.start));
    out.push(<span key={k} className={s.cls}>{question.slice(s.start, s.end)}</span>);
    pos = s.end;
  });
  out.push(question.slice(pos));
  return out;
}

const ResearchMap = React.forwardRef(function ResearchMap({ question, result }, ref) {
  const s = result.structure || {};
  const reading = [];
  if (s.kind === "aim") {
    if (s.subject) reading.push(["Subject", s.subject]);
    if (s.objective) reading.push(["Aim", s.objective]);
  } else if (s.kind === "inquiry" && s.objective) {
    reading.push(["Asks", s.objective]);
  }
  (s.constraints || []).forEach((c) => reading.push(["Constraint", c]));

  const cols = [
    { title: "Research areas", items: result.themes },
    { title: "Methods that may apply", items: result.methods },
    { title: "Perspectives you may not have yet", items: result.complementary_disciplines },
  ];

  return (
    <figure className="lp-map" tabIndex={-1} ref={ref} aria-labelledby="lp-fig2-caption" style={{ outline: "none" }}>
      <figcaption id="lp-fig2-caption" className="lp-figcaption lp-mono">
        <span>Fig. 2 — Your question, read as a research need</span>
        <span>{result.matched_taxonomy ? "fixed vocabulary" : "terms from your wording"}</span>
      </figcaption>

      <p className="lp-map-question lp-in">{marked(question, s)}</p>

      {reading.length > 0 && (
        <dl className="lp-reading lp-in lp-in-2">
          {reading.map(([k, v], i) => (
            <div key={i}><dt>{k}</dt><dd>{v}</dd></div>
          ))}
        </dl>
      )}

      <div className="lp-columns">
        {cols.map((c, i) => (
          <section key={c.title} className={`lp-col lp-in lp-in-${i + 2}`} aria-label={c.title}>
            <div className="lp-mono" style={{ color: "var(--muted)" }}>{String.fromCharCode(97 + i)}.</div>
            <h3>{c.title}</h3>
            {c.items?.length ? (
              <ul>{c.items.map((x) => <li key={x}>{x}</li>)}</ul>
            ) : (
              <p className="lp-empty">
                Nothing specific from the vocabulary for this question. A full Research Need on Pro reads it in more depth.
              </p>
            )}
          </section>
        ))}
      </div>

      {result.keywords?.length > 0 && (
        <div className="lp-terms lp-mono" aria-label="Terms taken from your question">
          <span>Terms in your question:</span>
          {result.keywords.map((k) => <span key={k}>{k}</span>)}
        </div>
      )}

      <p className="lp-footnote lp-small">
        This preview uses a fixed vocabulary, not a language model. It points to where
        expertise may sit; it doesn't judge the question, and it never shows people.
      </p>

      <div className="lp-next">
        <div>
          <p style={{ fontWeight: 600, fontSize: "1rem" }}>What happens next is where Synaptiq is different.</p>
          <p className="lp-small" style={{ marginTop: 6, maxWidth: "46rem" }}>
            On Pro, a question like this becomes a Research Need: Synaptiq looks for
            members whose work covers these areas and methods, and explains why each one
            is relevant. You decide who to contact. A free account gives you your own
            Academic Passport, so the right people can find you.
          </p>
        </div>
        <div className="lp-next-actions">
          <a href="#thread" className="lp-btn lp-btn--ghost">Follow the thread</a>
          <Link to="/pricing" className="lp-btn lp-btn--ghost" onClick={() => track("pricing_viewed", { from: "research_map" })}>
            What Pro adds
          </Link>
        </div>
      </div>
    </figure>
  );
});

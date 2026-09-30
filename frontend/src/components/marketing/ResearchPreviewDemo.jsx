import React, { useState, useRef } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Sparkles, Loader2 } from "lucide-react";
import api from "@/lib/api";

const NAVY = "#0F2847";
const BORDER = "#e8edf3";

const EXAMPLE_PLACEHOLDER =
  "How can public hospitals reduce patient waiting times without increasing staff workload?";

/**
 * The landing page's signature interactive moment (Phase 9A Part 2, §17-19).
 *
 * Calls the public, unauthenticated /api/public/research-preview endpoint —
 * deterministic, zero AI cost, never returns a real person or institution
 * (see backend/services/public_demo/research_preview.py for why that's a
 * structural guarantee, not just a convention). This is genuinely LIVE
 * computation on the visitor's real input, not a fabricated demo — no
 * "example output" labeling needed here, unlike the static AI mockup
 * elsewhere on this page.
 */
export default function ResearchPreviewDemo() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const resultRef = useRef(null);

  const submit = async (e) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post("/public/research-preview", { query: trimmed });
      setResult(data);
      // Move focus/scroll to the result for keyboard and screen-reader users.
      setTimeout(() => resultRef.current?.focus(), 50);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 429) {
        setError("You've tried this a few times in a row — please wait a moment and try again.");
      } else {
        setError("Could not analyze that just now. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      aria-labelledby="research-preview-heading"
      style={{ background: "#f8fafc", borderBottom: `1px solid ${BORDER}`, padding: "72px 0" }}
    >
      <div className="max-w-[820px] mx-auto px-6 lg:px-10">
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 12 }}>
            Try it now
          </div>
          <h2 id="research-preview-heading" style={{ fontSize: "clamp(1.6rem, 3vw, 2.3rem)", fontWeight: 900, letterSpacing: "-0.03em", color: "#0a0f1a", lineHeight: 1.15 }}>
            What are you researching?
          </h2>
        </div>

        <form onSubmit={submit} style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 16, padding: 24, boxShadow: "0 4px 24px rgba(15,40,71,0.05)" }}>
          <label htmlFor="research-preview-input" className="sr-only">
            Describe your research question
          </label>
          <textarea
            id="research-preview-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={EXAMPLE_PLACEHOLDER}
            rows={3}
            maxLength={600}
            style={{
              width: "100%", border: `1px solid ${BORDER}`, borderRadius: 10, padding: "12px 14px",
              fontSize: "0.92rem", color: "#0a0f1a", lineHeight: 1.6, resize: "vertical",
              fontFamily: "inherit", outline: "none",
            }}
          />
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 12, gap: 12, flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
              Example — try your own question above.
            </span>
            <button
              type="submit"
              disabled={loading || !query.trim()}
              style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                padding: "11px 22px", borderRadius: 9, border: "none",
                background: NAVY, color: "#fff", fontSize: "0.86rem", fontWeight: 700,
                cursor: loading || !query.trim() ? "not-allowed" : "pointer",
                opacity: loading || !query.trim() ? 0.6 : 1,
              }}
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              {loading ? "Analyzing…" : "Show relevant expertise"}
            </button>
          </div>
        </form>

        {error && (
          <p role="alert" style={{ marginTop: 16, fontSize: "0.85rem", color: "#b91c1c", textAlign: "center" }}>
            {error}
          </p>
        )}

        {result && (
          <div
            ref={resultRef}
            tabIndex={-1}
            style={{ marginTop: 24, background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 16, padding: "28px 24px", outline: "none" }}
          >
            {result.themes?.length > 0 && (
              <ResultGroup label="Core themes" items={result.themes} color={NAVY} />
            )}
            {result.complementary_disciplines?.length > 0 && (
              <ResultGroup label="Complementary expertise" items={result.complementary_disciplines} color="#1d4ed8" />
            )}
            {result.methods?.length > 0 && (
              <ResultGroup label="Methods that may be relevant" items={result.methods} color="#059669" />
            )}

            <div style={{ marginTop: 20, paddingTop: 20, borderTop: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
              <p style={{ fontSize: "0.78rem", color: "#94a3b8", margin: 0, maxWidth: 420 }}>
                This shows the expertise your question may need — not real people. Create an
                account to explore eligible Synaptiq experts, with your consent required before
                anyone is contacted.
              </p>
              <Link
                to="/register"
                style={{ display: "inline-flex", alignItems: "center", gap: 6, flexShrink: 0, fontSize: "0.85rem", fontWeight: 700, color: NAVY, textDecoration: "none" }}
              >
                Create an account <ArrowRight size={14} strokeWidth={2.5} />
              </Link>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function ResultGroup({ label, items, color }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 10 }}>
        {label}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {items.map((item) => (
          <span
            key={item}
            style={{
              fontSize: "0.82rem", fontWeight: 600, color,
              background: `${color}12`, border: `1px solid ${color}25`,
              padding: "6px 14px", borderRadius: 20,
            }}
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, MessageSquare } from "lucide-react";
import { useEntitlements } from "@/lib/entitlements";
import { loadCreditCatalogue } from "@/components/billing/creditCatalogue";

/* Three starting points, not every AI action at once; the AI Workspace has the rest. */
const SUGGESTED_PROMPTS = [
  "Continue my last manuscript",
  "Find suitable journals",
  "Review my methodology",
];

/**
 * Ask the AI Research Assistant — one quiet input on Home. AI is part of
 * the workspace, not a separate surface: same input, border and button as
 * every other form. The cost per message comes from the server catalogue
 * and is shown before anything runs; on Free the input is replaced by the
 * plan explanation rather than an input that looks available.
 */
export default function AICommandCenter({ aiConvs = [], navigate }) {
  const [query, setQuery] = useState("");
  const [cost, setCost] = useState(null);
  const { lockedFor } = useEntitlements();
  const locked = !!lockedFor("/ai");

  useEffect(() => {
    let alive = true;
    loadCreditCatalogue().then((c) => {
      const n = c?.actions?.ai_os_message ?? c?.operations?.ai_os_message;
      if (alive && n != null) setCost(n);
    }).catch(() => {});
    return () => { alive = false; };
  }, []);

  const ask = (text) => {
    const q = (text ?? query).trim();
    navigate("/ai", q ? { state: { initialPrompt: q } } : undefined);
    setQuery("");
  };

  if (locked) {
    return (
      <section aria-label="AI Research Assistant" className="hm-ai hm-ai--locked">
        <p>
          <strong>AI Research Assistant</strong> is part of Pro: questions about your manuscripts,
          projects and literature, with the credit cost shown before each action.
        </p>
        <Link to="/pricing" className="hm-link">See plans <ArrowRight size={12} /></Link>
      </section>
    );
  }

  return (
    <section aria-label="AI Research Assistant" className="hm-ai">
      <form className="hm-ai-row" onSubmit={(e) => { e.preventDefault(); ask(); }}>
        <label htmlFor="hm-ai-input" className="sr-only">Ask the AI Research Assistant</label>
        <input
          id="hm-ai-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask the AI Research Assistant about your work…"
          className="hm-ai-input"
          aria-describedby="hm-ai-cost"
        />
        <button type="submit" className="hm-ai-btn">Ask</button>
      </form>
      <div className="hm-ai-meta">
        <span id="hm-ai-cost" className="hm-ai-cost">
          {cost != null ? `${cost} AI credits per message` : "Uses AI credits"} · shown before it runs
        </span>
        <span className="hm-ai-sugg">
          {SUGGESTED_PROMPTS.map((p) => (
            <button key={p} type="button" onClick={() => ask(p)}>{p}</button>
          ))}
          {aiConvs.slice(0, 2).map((c, i) => (
            <Link key={c.id || i} to={`/ai?conv=${c.id}`}>
              <MessageSquare size={11} strokeWidth={1.75} aria-hidden="true" />
              {(c.title || "Untitled session").slice(0, 28)}
            </Link>
          ))}
        </span>
      </div>
    </section>
  );
}

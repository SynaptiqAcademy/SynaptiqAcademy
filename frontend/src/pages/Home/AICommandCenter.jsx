/* eslint-disable */
import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUp, MessageSquare } from "lucide-react";
import { AMBER, NAVY } from "@/lib/tokens";
import { transition } from "@/lib/motion";

const SUGGESTED_PROMPTS = [
  "Continue my last manuscript",
  "Find suitable journals",
  "Summarise my week",
  "Review my methodology",
  "Generate abstract",
  "Search for collaborators",
];

function CreditsLine({ credits }) {
  const balance   = credits?.monthly_balance  ?? credits?.balance        ?? null;
  const allowance = credits?.monthly_allowance ?? credits?.total_credits  ?? null;
  if (balance == null) return null;

  const pct = allowance ? Math.round((balance / allowance) * 100) : null;
  const barColor = pct != null && pct < 20 ? AMBER : "#34D399";

  return (
    <div className="flex items-center gap-3" style={{ maxWidth: 320 }}>
      <div style={{ flex: 1, height: 3, borderRadius: 99, background: "rgba(255,255,255,0.12)" }}>
        <div
          style={{
            width: `${pct ?? 100}%`,
            height: "100%",
            borderRadius: 99,
            background: barColor,
            transition: "width 400ms cubic-bezier(0.16,1,0.3,1)",
          }}
        />
      </div>
      <span style={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.5)", whiteSpace: "nowrap" }}>
        {balance.toLocaleString()} credits left
      </span>
    </div>
  );
}

export default function AICommandCenter({ aiConvs = [], credits, navigate }) {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);

  const handleAsk = () => {
    navigate("/ai", query.trim() ? { state: { initialPrompt: query } } : undefined);
    setQuery("");
  };

  return (
    <section aria-label="AI Command Center" className="mt-10 sq-fade-up sq-delay-1">

      {/* The console input — the dominant surface of the entire page */}
      <div
        style={{
          position: "relative",
          borderRadius: 18,
          background: "rgba(255,255,255,0.06)",
          border: `1px solid ${focused ? "rgba(255,255,255,0.28)" : "rgba(255,255,255,0.12)"}`,
          boxShadow: focused
            ? "0 0 0 4px rgba(52,211,153,0.10), 0 20px 48px -20px rgba(0,0,0,0.5)"
            : "0 12px 32px -18px rgba(0,0,0,0.4)",
          transition: "border-color 200ms ease, box-shadow 200ms ease",
          padding: "6px 8px 6px 22px",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <span
          aria-hidden="true"
          className="animate-pulse"
          style={{
            width: 7, height: 7, borderRadius: "50%",
            background: "#34D399", flexShrink: 0,
            boxShadow: "0 0 0 4px rgba(52,211,153,0.18)",
          }}
        />
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={e => e.key === "Enter" && handleAsk()}
          placeholder="Ask Synaptiq AI anything about your research…"
          style={{
            flex: 1,
            padding: "14px 0",
            fontSize: "1.05rem",
            color: "#F8FAFC",
            background: "transparent",
            border: "none",
            outline: "none",
            fontFamily: "inherit",
          }}
        />
        <button
          onClick={handleAsk}
          aria-label="Ask Synaptiq AI"
          style={{
            width: 40, height: 40, borderRadius: "50%",
            background: query.trim() ? "#F8FAFC" : "rgba(255,255,255,0.1)",
            color: query.trim() ? NAVY : "rgba(255,255,255,0.4)",
            border: "none",
            cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
            transition: transition.hoverButton,
          }}
        >
          <ArrowUp size={17} strokeWidth={2.25} />
        </button>
      </div>

      {/* Suggested prompts — quiet chips just beneath the console */}
      <div className="flex flex-wrap items-center gap-2 mt-4">
        {SUGGESTED_PROMPTS.map((p, i) => (
          <button
            key={i}
            onClick={() => navigate("/ai", { state: { initialPrompt: p } })}
            style={{
              fontSize: "0.72rem",
              fontWeight: 500,
              color: "rgba(255,255,255,0.6)",
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 99,
              padding: "5px 12px",
              cursor: "pointer",
              transition: transition.hover,
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = "rgba(255,255,255,0.28)";
              e.currentTarget.style.color = "#F8FAFC";
              e.currentTarget.style.background = "rgba(255,255,255,0.1)";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
              e.currentTarget.style.color = "rgba(255,255,255,0.6)";
              e.currentTarget.style.background = "rgba(255,255,255,0.05)";
            }}
          >
            {p}
          </button>
        ))}

        {aiConvs.slice(0, 3).map((c, i) => (
          <Link
            key={c.id || i}
            to={`/ai?conv=${c.id}`}
            style={{
              display: "inline-flex", alignItems: "center", gap: 5,
              fontSize: "0.72rem", fontWeight: 500,
              color: "rgba(255,255,255,0.45)",
              textDecoration: "none",
              padding: "5px 12px",
              borderRadius: 99,
            }}
          >
            <MessageSquare size={10} />
            {(c.title || "Untitled session").slice(0, 28)}
          </Link>
        ))}
      </div>

      {/* Credits — a quiet system readout, not a widget */}
      <div className="mt-5">
        <CreditsLine credits={credits} />
      </div>
    </section>
  );
}

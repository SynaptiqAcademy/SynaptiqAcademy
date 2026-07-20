import React, { useState, useRef } from "react";
import { Sparkles, X, Send, ChevronDown } from "lucide-react";
import {
  NAVY,
  ACCENT,
  BRD,
  WHITE,
  SHADOW_CARD,
  RADIUS_BASE,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
} from "@/lib/tokens";

/**
 * AIAssistant — collapsible context-aware AI widget.
 *
 * Always placed in the same position (bottom of PageSidebar).
 * Collapsed: a single "Ask AI…" affordance row.
 * Expanded: quick-ask chips + free-text input.
 *
 * Props:
 *   context      string     — "manuscripts"|"grants"|"teaching"|"default"
 *   suggestions  string[]   — override the default quick-ask chips
 *   onAsk        fn(q)      — called with the question string when submitted
 *   defaultOpen  bool       — initial open state (default: false)
 */

const CONTEXT_CHIPS = {
  manuscripts:  ["Review my abstract", "Find literature gaps", "Improve clarity"],
  grants:       ["Find matching grants", "Review my proposal", "Check eligibility"],
  teaching:     ["Create quiz questions", "Simplify this concept", "Generate rubric"],
  network:      ["Suggest collaborators", "Find reviewers", "Explore my field"],
  impact:       ["Analyse my citations", "Benchmark my output", "Predict trends"],
  publishing:   ["Match a journal", "Check formatting", "Improve title"],
  default:      ["Summarise this page", "What should I focus on?", "Give me insights"],
};

export function AIAssistant({
  context = "default",
  suggestions,
  onAsk,
  defaultOpen = false,
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [query, setQuery] = useState("");
  const inputRef = useRef(null);

  const chips = suggestions ?? (CONTEXT_CHIPS[context] || CONTEXT_CHIPS.default);

  const submit = (q) => {
    const question = (q ?? query).trim();
    if (!question) return;
    onAsk?.(question);
    setQuery("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  // ── Collapsed state ────────────────────────────────────────────────────────
  if (!open) {
    return (
      <button
        onClick={() => {
          setOpen(true);
          setTimeout(() => inputRef.current?.focus(), 80);
        }}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          width: "100%",
          padding: "9px 14px",
          background: WHITE,
          border: `1px solid ${BRD}`,
          borderRadius: RADIUS_BASE,
          cursor: "pointer",
          boxShadow: SHADOW_CARD,
          textAlign: "left",
          transition: "box-shadow 150ms ease, border-color 150ms ease",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.boxShadow = "0 4px 12px rgba(15,23,42,0.09)";
          e.currentTarget.style.borderColor = "#94a3b8";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.boxShadow = SHADOW_CARD;
          e.currentTarget.style.borderColor = BRD;
        }}
      >
        <Sparkles size={13} style={{ color: ACCENT, flexShrink: 0 }} />
        <span style={{ fontSize: "0.78rem", color: TEXT_SECONDARY, flex: 1 }}>
          Ask AI…
        </span>
        <ChevronDown size={11} style={{ color: TEXT_MUTED }} />
      </button>
    );
  }

  // ── Expanded state ─────────────────────────────────────────────────────────
  return (
    <div
      style={{
        background: WHITE,
        border: `1px solid ${BRD}`,
        borderRadius: RADIUS_BASE,
        boxShadow: SHADOW_CARD,
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "9px 12px 9px 14px",
          borderBottom: `1px solid ${BRD}`,
          background: "rgba(15,40,71,0.02)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Sparkles size={12} style={{ color: ACCENT }} />
          <span
            style={{
              fontSize: "0.68rem",
              fontWeight: 700,
              letterSpacing: "0.07em",
              textTransform: "uppercase",
              color: TEXT_MUTED,
            }}
          >
            AI Assistant
          </span>
        </div>
        <button
          onClick={() => setOpen(false)}
          aria-label="Close AI assistant"
          style={{
            background: "none",
            border: "none",
            padding: "3px",
            cursor: "pointer",
            color: TEXT_MUTED,
            borderRadius: 3,
            display: "flex",
            alignItems: "center",
            transition: "color 120ms ease",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = TEXT_PRIMARY)}
          onMouseLeave={(e) => (e.currentTarget.style.color = TEXT_MUTED)}
        >
          <X size={12} />
        </button>
      </div>

      {/* Quick-ask chips */}
      <div
        style={{
          padding: "10px 14px",
          display: "flex",
          flexDirection: "column",
          gap: 5,
        }}
      >
        {chips.map((chip, i) => (
          <button
            key={i}
            onClick={() => submit(chip)}
            style={{
              textAlign: "left",
              padding: "5px 10px",
              background: "rgba(15,40,71,0.04)",
              border: `1px solid ${BRD}`,
              borderRadius: 4,
              fontSize: "0.73rem",
              color: TEXT_PRIMARY,
              cursor: "pointer",
              lineHeight: 1.45,
              transition: "background 120ms ease, border-color 120ms ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(15,40,71,0.08)";
              e.currentTarget.style.borderColor = "#94a3b8";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "rgba(15,40,71,0.04)";
              e.currentTarget.style.borderColor = BRD;
            }}
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Free-text input */}
      <div
        style={{
          display: "flex",
          gap: 6,
          padding: "0 14px 12px",
        }}
      >
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything…"
          style={{
            flex: 1,
            padding: "6px 10px",
            border: `1px solid ${BRD}`,
            borderRadius: RADIUS_BASE,
            fontSize: "0.75rem",
            color: TEXT_PRIMARY,
            outline: "none",
            background: "#FDFDFB",
            minWidth: 0,
            transition: "border-color 150ms ease",
          }}
          onFocus={(e) => (e.target.style.borderColor = NAVY)}
          onBlur={(e) => (e.target.style.borderColor = BRD)}
        />
        <button
          onClick={() => submit()}
          disabled={!query.trim()}
          aria-label="Send question"
          style={{
            width: 30,
            height: 30,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            background: query.trim() ? NAVY : "rgba(15,40,71,0.06)",
            border: "none",
            borderRadius: 5,
            cursor: query.trim() ? "pointer" : "not-allowed",
            color: query.trim() ? WHITE : TEXT_MUTED,
            transition: "background 150ms ease, color 150ms ease",
          }}
        >
          <Send size={11} />
        </button>
      </div>
    </div>
  );
}

export default AIAssistant;

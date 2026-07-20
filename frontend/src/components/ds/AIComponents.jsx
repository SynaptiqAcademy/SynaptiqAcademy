import React, { useState } from "react";
import { CheckCircle, AlertCircle, ExternalLink, ChevronDown, ChevronRight, Sparkles, Shield } from "lucide-react";
import { NAVY, ACCENT, EMERALD, AMBER, CRIMSON, BRD, BRDH, BRDX, WARM, WHITE, SURF2,
         TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, NAVY_08,
         RADIUS_MD, RADIUS_SM, RADIUS_FULL, Z } from "@/lib/tokens";

// ── AIResponsePanel ───────────────────────────────────────────────────────────
/**
 * Renders AI-generated content with consistent chrome.
 * source: "anthropic" | "openai" | "local" | string
 * status: "loading" | "streaming" | "complete" | "error"
 */
export function AIResponsePanel({
  children,
  source,
  model,
  status = "complete",
  credits,
  confidence,
  className = "",
  style = {},
}) {
  const sourceLabel = {
    anthropic: "Claude", openai: "GPT", local: "Local AI",
  }[source] || source || "AI";

  const statusDot = {
    loading:   AMBER,
    streaming: EMERALD,
    complete:  EMERALD,
    error:     CRIMSON,
  }[status] || NAVY;

  return (
    <div
      className={className}
      style={{
        background: WHITE,
        border: `1px solid ${BRD}`,
        borderRadius: RADIUS_MD,
        overflow: "hidden",
        ...style,
      }}
    >
      {/* Header chrome */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 12px", background: WARM, borderBottom: `1px solid ${BRD}`,
        gap: 8,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Sparkles size={13} style={{ color: NAVY }} />
          <span style={{ fontSize: "0.72rem", fontWeight: 600, color: NAVY, letterSpacing: "0.04em", textTransform: "uppercase" }}>
            {sourceLabel}{model ? ` · ${model}` : ""}
          </span>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: statusDot, display: "inline-block" }} />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {confidence != null && (
            <span style={{ fontSize: "0.68rem", color: TEXT_MUTED }}>
              {Math.round(confidence * 100)}% confidence
            </span>
          )}
          {credits != null && (
            <span style={{
              fontSize: "0.65rem", fontWeight: 500, padding: "1px 6px", borderRadius: RADIUS_FULL,
              background: NAVY_08, color: NAVY,
            }}>
              {credits} credits
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: "16px 20px", lineHeight: 1.7, fontSize: "0.875rem", color: TEXT_PRIMARY }}>
        {status === "loading" ? <AISkeletonContent /> : children}
      </div>
    </div>
  );
}

function AISkeletonContent() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {[100, 85, 90, 40].map((w, i) => (
        <div key={i} style={{
          height: 14, borderRadius: RADIUS_SM, width: `${w}%`,
          background: `linear-gradient(90deg, ${BRDX} 25%, ${WARM} 50%, ${BRDX} 75%)`,
          backgroundSize: "200% 100%",
          animation: "shimmer 1.5s ease-in-out infinite",
        }} />
      ))}
    </div>
  );
}

// ── EvidencePanel ─────────────────────────────────────────────────────────────
/**
 * Collapsible panel showing evidence sources behind an AI recommendation.
 * evidence: Array<{ title, source, type, confidence?, url?, year? }>
 */
export function EvidencePanel({ evidence = [], defaultOpen = false, style = {} }) {
  const [open, setOpen] = useState(defaultOpen);

  if (evidence.length === 0) return null;

  const avgConf = evidence.filter(e => e.confidence != null).length > 0
    ? evidence.reduce((s, e) => s + (e.confidence ?? 0), 0) / evidence.length
    : null;

  return (
    <div style={{
      border: `1px solid ${BRD}`, borderRadius: RADIUS_MD, overflow: "hidden", ...style,
    }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "8px 12px", background: WARM, border: "none", cursor: "pointer",
          borderBottom: open ? `1px solid ${BRD}` : "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Shield size={13} style={{ color: NAVY }} />
          <span style={{ fontSize: "0.72rem", fontWeight: 600, color: NAVY }}>
            Evidence ({evidence.length} source{evidence.length !== 1 ? "s" : ""})
          </span>
          {avgConf != null && (
            <span style={{
              fontSize: "0.65rem", padding: "1px 6px", borderRadius: RADIUS_FULL,
              background: NAVY_08, color: NAVY,
            }}>
              avg {Math.round(avgConf * 100)}% confidence
            </span>
          )}
        </div>
        {open ? <ChevronDown size={13} style={{ color: TEXT_MUTED }} /> : <ChevronRight size={13} style={{ color: TEXT_MUTED }} />}
      </button>

      {open && (
        <div style={{ padding: "8px 0" }}>
          {evidence.map((item, i) => (
            <EvidenceItem key={i} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── EvidenceItem ──────────────────────────────────────────────────────────────
export function EvidenceItem({ item }) {
  const { title, source, type, confidence, url, year, verified } = item;

  const typeColor = {
    paper:        NAVY,
    dataset:      EMERALD,
    citation:     AMBER,
    user_profile: TEXT_SECONDARY,
    platform:     TEXT_MUTED,
  }[type] || TEXT_MUTED;

  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 10,
      padding: "8px 12px", borderBottom: `1px solid ${BRD}`,
    }}>
      <div style={{ flexShrink: 0, marginTop: 1 }}>
        {verified
          ? <CheckCircle size={13} style={{ color: EMERALD }} />
          : <AlertCircle size={13} style={{ color: AMBER }} />
        }
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 6 }}>
          <p style={{ fontSize: "0.78rem", fontWeight: 500, color: TEXT_PRIMARY, margin: 0, lineHeight: 1.4, flex: 1 }}>
            {title}
          </p>
          {url && (
            <a href={url} target="_blank" rel="noreferrer" style={{ color: TEXT_MUTED, flexShrink: 0 }} aria-label="Open source">
              <ExternalLink size={11} />
            </a>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 3 }}>
          {type && (
            <span style={{ fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: typeColor }}>
              {type.replace("_", " ")}
            </span>
          )}
          {source && <span style={{ fontSize: "0.65rem", color: TEXT_MUTED }}>{source}</span>}
          {year && <span style={{ fontSize: "0.65rem", color: TEXT_MUTED }}>{year}</span>}
          {confidence != null && (
            <span style={{ fontSize: "0.65rem", color: TEXT_MUTED, marginLeft: "auto" }}>
              {Math.round(confidence * 100)}%
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── CitationInline ────────────────────────────────────────────────────────────
/**
 * Inline citation superscript within prose text.
 * number: 1-based citation index
 * tooltip: citation text shown on hover
 */
export function CitationInline({ number, tooltip, url }) {
  const [hover, setHover] = useState(false);

  const el = (
    <span style={{ position: "relative", display: "inline" }}>
      <sup
        style={{
          fontSize: "0.65em", fontWeight: 600, color: NAVY,
          cursor: url || tooltip ? "help" : "default",
          padding: "0 1px",
        }}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
      >
        [{number}]
      </sup>
      {hover && tooltip && (
        <span style={{
          position: "absolute", bottom: "calc(100% + 4px)", left: "50%",
          transform: "translateX(-50%)",
          background: "#1e293b", color: WHITE,
          fontSize: "0.72rem", lineHeight: 1.5,
          padding: "6px 10px", borderRadius: RADIUS_SM,
          width: 220, pointerEvents: "none", zIndex: Z.tooltip,
          boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
        }}>
          {tooltip}
        </span>
      )}
    </span>
  );

  if (url) return <a href={url} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>{el}</a>;
  return el;
}

// ── VerificationBadge ─────────────────────────────────────────────────────────
/**
 * Trust-level badge shown next to names, publications, institutions.
 * level: "unverified" | "basic" | "orcid" | "institutional" | "certified"
 * size: "sm" | "md" | "lg"
 */
export function VerificationBadge({ level = "unverified", size = "sm", showLabel = false }) {
  const config = {
    unverified:   { label: "Unverified",   color: TEXT_MUTED,   icon: "○" },
    basic:        { label: "Basic",         color: AMBER,        icon: "✓" },
    orcid:        { label: "ORCID",         color: EMERALD,      icon: "✓" },
    institutional:{ label: "Institutional", color: NAVY,         icon: "✓" },
    certified:    { label: "Certified",     color: NAVY,         icon: "★" },
  }[level] || { label: level, color: TEXT_MUTED, icon: "○" };

  const fontSize = { sm: "0.65rem", md: "0.75rem", lg: "0.85rem" }[size] || "0.65rem";

  return (
    <span
      title={config.label}
      style={{
        display: "inline-flex", alignItems: "center", gap: 3,
        padding: showLabel ? "2px 6px" : "2px 4px",
        borderRadius: RADIUS_FULL,
        background: showLabel ? `${config.color}14` : "transparent",
        color: config.color, fontSize,
        fontWeight: 600,
      }}
    >
      <span style={{ fontSize: "0.9em" }}>{config.icon}</span>
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}

import React from "react";
import { TYPE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, NAVY } from "@/lib/tokens";

/**
 * Typography — Synaptiq Design System V2 type scale.
 *
 * Every text element in the platform should use one of these components.
 * Do NOT define custom font sizes or weights outside of this file.
 *
 * Usage:
 *   import { H1, Body, SectionLabel } from "@/components/ds/Typography";
 *
 *   <H1>Research Impact Dashboard</H1>
 *   <Body color="muted">Last updated 2 hours ago</Body>
 *   <SectionLabel>Active Projects</SectionLabel>
 *
 * For a numeric metric display (a KPI value + label), use ds/StatCard — the
 * one canonical implementation for that job.
 */

// ── Polymorphic helper ────────────────────────────────────────────────────────

function T({ as: Tag = "p", style, className, children, ...props }) {
  return (
    <Tag style={style} className={className} {...props}>
      {children}
    </Tag>
  );
}

// ── Display & Headings ────────────────────────────────────────────────────────

/**
 * Display — hero-scale text (brand sans-serif). Use only on landing / feature highlights.
 */
export function Display({ as = "h1", color, style, children, ...props }) {
  return (
    <T
      as={as}
      style={{ ...TYPE.display, color: color || TYPE.display.color, margin: 0, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

/**
 * H1 — primary page heading. Brand sans-serif, large.
 */
export function H1({ as = "h1", color, style, children, ...props }) {
  return (
    <T
      as={as}
      style={{ ...TYPE.h1, color: color || TYPE.h1.color, margin: 0, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

/**
 * H2 — section heading. Brand sans-serif, medium.
 */
export function H2({ as = "h2", color, style, children, ...props }) {
  return (
    <T
      as={as}
      style={{ ...TYPE.h2, color: color || TYPE.h2.color, margin: 0, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

/**
 * H3 — sub-section heading. Sans-serif, semi-bold.
 */
export function H3({ as = "h3", color, style, children, ...props }) {
  return (
    <T
      as={as}
      style={{ ...TYPE.h3, color: color || TYPE.h3.color, margin: 0, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

/**
 * H4 — card heading / list item title. Sans-serif, semi-bold.
 */
export function H4({ as = "h4", color, style, children, ...props }) {
  return (
    <T
      as={as}
      style={{ ...TYPE.h4, color: color || TYPE.h4.color, margin: 0, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

// ── Section label ─────────────────────────────────────────────────────────────

/**
 * SectionLabel — uppercase overline. Use for section titles and category labels.
 * Matches the visual style used by Notion, Linear, and Stripe for section headers.
 */
export function SectionLabel({ as = "p", color, style, children, ...props }) {
  return (
    <T
      as={as}
      style={{ ...TYPE.section, color: color || TYPE.section.color, margin: 0, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

// ── Body copy ─────────────────────────────────────────────────────────────────

/**
 * BodyLarge — primary reading text for descriptions and body copy.
 */
export function BodyLarge({ as = "p", color, style, children, ...props }) {
  return (
    <T
      as={as}
      style={{ ...TYPE.bodyLg, color: color || TYPE.bodyLg.color, margin: 0, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

/**
 * Body — standard body text. 14px, 1.6 line-height.
 */
export function Body({ as = "p", color, style, children, ...props }) {
  return (
    <T
      as={as}
      style={{ ...TYPE.body, color: color || TYPE.body.color, margin: 0, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

/**
 * BodySmall — compact body text for secondary information.
 */
export function BodySmall({ as = "p", color, style, children, ...props }) {
  return (
    <T
      as={as}
      style={{ ...TYPE.bodySm, color: color || TYPE.bodySm.color, margin: 0, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

// ── Utility text ──────────────────────────────────────────────────────────────

/**
 * Caption — timestamps, metadata, helper text.
 */
export function Caption({ as = "span", color, style, children, ...props }) {
  return (
    <T
      as={as}
      style={{ ...TYPE.caption, color: color || TYPE.caption.color, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

/**
 * Label — form labels, small uppercase labels.
 */
export function Label({ as = "label", color, style, children, ...props }) {
  return (
    <T
      as={as}
      style={{ ...TYPE.label, color: color || TYPE.label.color, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

/**
 * Meta — smallest text level for fine print and micro-labels.
 */
export function Meta({ as = "span", color, style, children, ...props }) {
  return (
    <T
      as={as}
      style={{ ...TYPE.meta, color: color || TYPE.meta.color, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

// NOTE: a bare (uncarded) numeric-metric primitive used to live here as
// `Metric` — it had zero real usage and duplicated ds/StatCard.jsx's job, so
// it has been removed. Use StatCard for any numeric-metric display.

// ── Text (generic) ────────────────────────────────────────────────────────────

/**
 * Text — low-level text primitive for one-off overrides.
 * Prefer the semantic components above over this.
 */
export function Text({ as = "span", size = "body", color, style, children, ...props }) {
  const typeStyle = TYPE[size] || TYPE.body;
  return (
    <T
      as={as}
      style={{ ...typeStyle, color: color || typeStyle.color, margin: 0, ...style }}
      {...props}
    >
      {children}
    </T>
  );
}

// ── Convenience re-export ─────────────────────────────────────────────────────
export default {
  Display, H1, H2, H3, H4,
  SectionLabel,
  BodyLarge, Body, BodySmall,
  Caption, Label, Meta,
  Text,
};

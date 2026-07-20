/* eslint-disable */
import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { Activity as ActivityIcon } from "lucide-react";
import {
  TEXT_PRIMARY, TEXT_MUTED, NAVY, BRDX, EMERALD, TYPE,
} from "@/lib/tokens";
import { transition } from "@/lib/motion";
import { EmptyState } from "@/components/ds/EmptyState";

// ── Build unified activity feed from available data ───────────────────────────

function buildActivity(feed, manuscripts) {
  const items = [];

  manuscripts
    .filter(m => m.updated_at)
    .sort((a, b) => (b.updated_at > a.updated_at ? 1 : -1))
    .slice(0, 2)
    .forEach(m => {
      items.push({
        label:       m.title || "Untitled manuscript",
        description: `${m.status || "Draft"} · Manuscript`,
        to:          m.id ? `/manuscripts/${m.id}` : "/manuscripts",
        variant:     "default",
      });
    });

  (feed.collaborations || []).slice(0, 2).forEach(c => {
    items.push({
      label:   `New collaboration: ${c.title || "Collaboration opportunity"}`,
      to:      c.id ? `/collaborations/${c.id}` : "/collaborations",
      variant: "success",
    });
  });

  (feed.researchers || []).slice(0, 2).forEach(r => {
    items.push({
      label:   `${r.full_name} is active in your research area`,
      to:      r.id ? `/profile/${r.id}` : undefined,
      variant: "default",
    });
  });

  (feed.conferences || []).slice(0, 1).forEach(c => {
    items.push({
      label:   `${c.name || "Conference"} — submissions open`,
      to:      "/conferences",
      variant: "default",
    });
  });

  (feed.trending_topics || []).slice(0, 1).forEach(t => {
    items.push({
      label:   `"${t.topic}" is trending in your research field`,
      variant: "default",
    });
  });

  return items.slice(0, 6);
}

// ── Row ───────────────────────────────────────────────────────────────────────

function FeedRow({ item, last }) {
  const dotColor = item.variant === "success" ? EMERALD : "rgba(15,40,71,0.25)";

  const content = (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 14,
        padding: "18px 0",
        borderBottom: last ? "none" : `1px solid ${BRDX}`,
      }}
    >
      <span
        aria-hidden="true"
        style={{ width: 6, height: 6, borderRadius: "50%", background: dotColor, marginTop: 8, flexShrink: 0 }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: "1.05rem",
            fontWeight: 600,
            letterSpacing: "-0.01em",
            color: TEXT_PRIMARY,
            margin: 0,
            lineHeight: 1.4,
          }}
        >
          {item.label}
        </p>
        {item.description && (
          <p style={{ ...TYPE.caption, margin: "3px 0 0" }}>{item.description}</p>
        )}
      </div>
    </div>
  );

  if (!item.to) return content;
  return (
    <Link
      to={item.to}
      style={{ textDecoration: "none", color: "inherit", display: "block" }}
      onMouseEnter={e => (e.currentTarget.style.opacity = "0.7")}
      onMouseLeave={e => (e.currentTarget.style.opacity = "1")}
    >
      {content}
    </Link>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function Activity({ feed, manuscripts }) {
  const items = useMemo(
    () => buildActivity(feed || {}, manuscripts || []),
    [feed, manuscripts]
  );

  return (
    <section aria-label="Research Activity">
      <div className="flex items-baseline justify-between mb-1">
        <h2
          style={{
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: "1.35rem",
            fontWeight: 700,
            letterSpacing: "-0.02em",
            color: TEXT_PRIMARY,
            margin: 0,
          }}
        >
          What's happening in your field
        </h2>
        <Link
          to="/manuscripts"
          style={{ ...TYPE.caption, color: TEXT_MUTED, textDecoration: "none", transition: transition.colorFast }}
          onMouseEnter={e => (e.currentTarget.style.color = NAVY)}
          onMouseLeave={e => (e.currentTarget.style.color = TEXT_MUTED)}
        >
          All activity →
        </Link>
      </div>

      {items.length === 0 ? (
        <EmptyState
          icon={<ActivityIcon />}
          title="No recent activity"
          description="Start a manuscript or connect with researchers to see activity here."
        />
      ) : (
        <div>
          {items.map((item, i) => (
            <FeedRow key={i} item={item} last={i === items.length - 1} />
          ))}
        </div>
      )}
    </section>
  );
}

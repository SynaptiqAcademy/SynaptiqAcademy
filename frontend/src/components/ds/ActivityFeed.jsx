import React from "react";
import { Link } from "react-router-dom";
import { Avatar } from "./Avatar";
import { Badge } from "./Badge";
import {
  NAVY, BRD, WARM, WHITE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, RADIUS_MD,
} from "@/lib/tokens";
import { Clock } from "lucide-react";

/**
 * ActivityFeedItem — one row in a chronological activity feed (an actor did
 * a verb to/on an object, at a time). The one canonical feed row — replaces
 * the hand-rolled `FeedItem` components that used to be duplicated per-page
 * (e.g. the research activity feed, the dashboard "what's happening" strip).
 *
 * Props:
 *   icon        ReactNode   — small icon shown in the type-color chip
 *   color       string      — hex driving the icon chip + type badge tint
 *   actor       { name, avatarUrl, to? }  — who did it
 *   verb        string      — e.g. "published", "opened a collaboration"
 *   typeLabel   string      — badge text, e.g. "Published", "New Team"
 *   title       string      — optional bolded content title (renders in a
 *                             nested content box, e.g. the manuscript title)
 *   description string      — optional supporting text under the title
 *   tags        string[]    — optional small tag row
 *   meta        string      — optional trailing line (institution/venue)
 *   timestamp   string      — pre-formatted relative time ("2h ago")
 */
export function ActivityFeedItem({
  icon,
  color = NAVY,
  actor,
  verb,
  typeLabel,
  title,
  description,
  tags,
  meta,
  timestamp,
}) {
  return (
    <div
      style={{
        display: "flex", gap: 14, padding: "16px 18px",
        background: WHITE, border: `1px solid ${BRD}`, borderRadius: RADIUS_MD,
      }}
    >
      <div style={{
        width: 34, height: 34, borderRadius: RADIUS_MD, flexShrink: 0, marginTop: 2,
        background: `${color}14`, border: `1px solid ${color}25`,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {icon && React.cloneElement(icon, { size: 15, strokeWidth: 1.5, style: { color } })}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8, justifyContent: "space-between", marginBottom: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", flex: 1, minWidth: 0 }}>
            {actor && (
              <Link to={actor.to || "#"} style={{ display: "flex", alignItems: "center", gap: 7, textDecoration: "none" }}>
                <Avatar url={actor.avatarUrl} name={actor.name} size={24} />
                <span style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY }}>{actor.name}</span>
              </Link>
            )}
            {verb && <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>{verb}</span>}
            {typeLabel && (
              <Badge color={color} size="sm" style={{ textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>
                {typeLabel}
              </Badge>
            )}
          </div>
          {timestamp && (
            <span style={{ fontSize: 11, color: TEXT_MUTED, flexShrink: 0, display: "flex", alignItems: "center", gap: 3 }}>
              <Clock size={10} strokeWidth={1.5} />
              {timestamp}
            </span>
          )}
        </div>

        {(title || description) && (
          <div style={{ background: WARM, border: `1px solid ${BRD}`, padding: "12px 14px", marginTop: 8, borderRadius: RADIUS_MD }}>
            {title && <div style={{ fontSize: 13, fontWeight: 600, color: TEXT_PRIMARY, marginBottom: description ? 4 : 0 }}>{title}</div>}
            {description && (
              <div style={{
                fontSize: 12, color: TEXT_SECONDARY, lineHeight: 1.6,
                display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden",
              }}>
                {description}
              </div>
            )}
          </div>
        )}

        {tags?.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 8 }}>
            {tags.map((tag) => (
              <span key={tag} style={{ fontSize: 10, padding: "2px 7px", background: WARM, border: `1px solid ${BRD}`, color: TEXT_SECONDARY, borderRadius: 4, fontFamily: "monospace" }}>
                {tag}
              </span>
            ))}
          </div>
        )}

        {meta && (
          <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 8, fontSize: 11, color: TEXT_MUTED }}>
            {meta}
          </div>
        )}
      </div>
    </div>
  );
}

/** ActivityFeed — vertical list wrapper with consistent row spacing. */
export function ActivityFeed({ children, gap = 8, className, style }) {
  return (
    <div className={className} style={{ display: "flex", flexDirection: "column", gap, ...style }}>
      {children}
    </div>
  );
}

export default ActivityFeed;

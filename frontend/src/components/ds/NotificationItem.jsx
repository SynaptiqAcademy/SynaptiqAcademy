import React, { useState } from "react";
import {
  NAVY, ACCENT, CRIMSON, WHITE, WARM, NAVY_06,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
  RADIUS_MD, RADIUS_LG, SHADOW_CARD, ACCENT_05,
} from "@/lib/tokens";

/**
 * NotificationItem — the one canonical single-notification row.
 *
 * Use for any notification/activity feed: the in-app Inbox, a bell dropdown,
 * an admin activity feed, etc. Purely presentational — the caller owns data
 * fetching, read/pin/archive state, and routing.
 *
 * Props:
 *   icon        ReactNode component (e.g. lucide icon component, not element)
 *   title       string
 *   body        string    optional secondary line, single-line clamp
 *   time        string    pre-formatted relative time (e.g. "2h ago")
 *   unread      bool      shows the accent unread dot on the icon avatar
 *   priority    "high" | "normal"   high renders the unread dot in CRIMSON
 *                                    and shows a "Needs attention" hint
 *   category    string    small label under the body (e.g. "Mentions")
 *   selected    bool      shows the accent left rail + tinted background
 *   onClick     fn()
 *   actions     [{ icon, label, onClick, active? }]   hover-revealed row actions
 */
export function NotificationItem({
  icon: Icon,
  title,
  body,
  time,
  unread = false,
  priority = "normal",
  category,
  selected = false,
  onClick,
  actions = [],
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      role="listitem"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => { if (onClick && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onClick(e); } }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex", alignItems: "flex-start", gap: 13,
        padding: "14px 16px", borderRadius: RADIUS_LG,
        cursor: onClick ? "pointer" : "default", position: "relative",
        background: selected ? ACCENT_05 : hovered ? WARM : "transparent",
        transition: "background 120ms ease",
      }}
    >
      {selected && (
        <span aria-hidden="true" style={{
          position: "absolute", left: 0, top: 10, bottom: 10, width: 3,
          borderRadius: 3, background: ACCENT,
        }} />
      )}

      {/* Icon avatar */}
      {Icon && (
        <div style={{ position: "relative", flexShrink: 0, marginTop: 1 }}>
          <div style={{
            width: 36, height: 36, borderRadius: "50%",
            background: unread ? NAVY_06 : WARM,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Icon size={15} strokeWidth={1.6} style={{ color: unread ? NAVY : TEXT_DISABLED }} />
          </div>
          {unread && (
            <span
              aria-label="Unread"
              style={{
                position: "absolute", top: -1, right: -1, width: 9, height: 9,
                borderRadius: "50%", border: `2px solid ${WHITE}`,
                background: priority === "high" ? CRIMSON : ACCENT,
              }}
            />
          )}
        </div>
      )}

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
          <p style={{
            fontSize: "0.9rem", fontWeight: unread ? 650 : 400,
            color: unread ? TEXT_PRIMARY : TEXT_SECONDARY, lineHeight: 1.4,
            letterSpacing: "-0.005em", margin: 0, flex: 1, minWidth: 0,
          }}>
            {title}
          </p>
          {time && (
            <span style={{ fontSize: "0.68rem", color: TEXT_DISABLED, flexShrink: 0, marginTop: 2 }}>
              {time}
            </span>
          )}
        </div>

        {body && (
          <p style={{
            fontSize: "0.78rem", color: TEXT_MUTED, lineHeight: 1.55, margin: "3px 0 0",
            display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical", overflow: "hidden",
          }}>
            {body}
          </p>
        )}

        {(category || priority === "high") && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
            {category && (
              <span style={{ fontSize: "0.65rem", fontWeight: 600, color: TEXT_MUTED }}>{category}</span>
            )}
            {priority === "high" && unread && (
              <span style={{ fontSize: "0.65rem", fontWeight: 700, color: CRIMSON }}>
                {category ? "· " : ""}Needs attention
              </span>
            )}
          </div>
        )}
      </div>

      {/* Hover actions */}
      {actions.length > 0 && (
        <div style={{ display: "flex", gap: 2, flexShrink: 0, opacity: hovered ? 1 : 0, transition: "opacity 120ms ease" }}>
          {actions.map((a, i) => (
            <NotificationRowAction key={i} {...a} />
          ))}
        </div>
      )}
    </div>
  );
}

function NotificationRowAction({ icon: Icon, label, onClick, active }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick?.(e); }}
      title={label}
      aria-label={label}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        width: 24, height: 24, display: "flex", alignItems: "center", justifyContent: "center",
        borderRadius: RADIUS_MD, border: "none", cursor: "pointer",
        background: hov ? WHITE : "transparent",
        boxShadow: hov ? SHADOW_CARD : "none",
        color: active ? ACCENT : hov ? TEXT_PRIMARY : TEXT_MUTED,
      }}
    >
      <Icon size={12} strokeWidth={2} fill={active ? "currentColor" : "none"} />
    </button>
  );
}

export default NotificationItem;

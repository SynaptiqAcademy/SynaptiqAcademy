import React from "react";
import { Avatar } from "./Avatar";
import { WHITE, NAVY, NAVY_08 } from "@/lib/tokens";

/**
 * AvatarGroup — overlapping stack of avatars.
 *
 * Shows max 4 avatars + overflow count chip.
 * Each avatar has a 2px WHITE border separator.
 */
export function AvatarGroup({
  users = [],     // [{ name, avatar?, initials?, color? }]
  max = 4,
  size = "sm",    // Avatar size prop
  className = "",
  onClick,
}) {
  const visible = users.slice(0, max);
  const overflow = users.length - max;

  const sizePx = { xs: 20, sm: 24, md: 32, lg: 40, xl: 56 }[size] || 24;
  const overlap = Math.round(sizePx * 0.35);
  const fontSize = sizePx <= 24 ? "0.6rem" : "0.7rem";

  return (
    <div
      className={className}
      style={{ display: "inline-flex", alignItems: "center", cursor: onClick ? "pointer" : "default" }}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      aria-label={`${users.length} members`}
    >
      {visible.map((user, i) => (
        <div
          key={i}
          style={{
            marginLeft: i === 0 ? 0 : -overlap,
            zIndex: visible.length - i,
            position: "relative",
            borderRadius: "50%",
            border: `2px solid ${WHITE}`,
            flexShrink: 0,
          }}
          title={user.name}
        >
          <Avatar
            url={user.avatar}
            name={user.name || user.initials}
            size={sizePx}
          />
        </div>
      ))}
      {overflow > 0 && (
        <div
          style={{
            marginLeft: -overlap,
            zIndex: 0,
            width: sizePx,
            height: sizePx,
            borderRadius: "50%",
            background: NAVY_08,
            border: `2px solid ${WHITE}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize,
            fontWeight: 600,
            color: NAVY,
            flexShrink: 0,
          }}
        >
          +{overflow}
        </div>
      )}
    </div>
  );
}

export default AvatarGroup;

import React, { useState } from "react";
import { NAVY, NAVY_08 } from "@/lib/tokens";

/**
 * Avatar — canonical implementation.
 * Imported from: components/ds/Avatar
 *
 * Shows an image from `url`, falling back to initials from `name` — both on
 * first render (no url) and if the image fails to load (broken/expired url),
 * matching the fallback behavior several pages had reimplemented locally
 * (Researchers.jsx, ReviewerMarketplace.jsx, Leaderboards.jsx all carried an
 * identical `imgError` + `onError` copy of this).
 *
 * `border`: pass true for the thin hairline ring those same pages used on
 * image avatars (`1.5px solid #E4E8EF`) — off by default to match the
 * original borderless initials-only look everywhere else already used.
 */
export function Avatar({ url, name, size = 32, className = "", border = false }) {
  const [imgError, setImgError] = useState(false);
  const initials = (name || "?")
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const fontSize = size <= 24 ? 9 : size <= 32 ? 11 : size <= 40 ? 12 : 14;
  const showImage = !!url && !imgError;

  return (
    <div
      className={`shrink-0 rounded-full flex items-center justify-center overflow-hidden select-none ${className}`}
      style={{
        width: size,
        height: size,
        background: NAVY_08,
        border: border ? "1.5px solid #E4E8EF" : undefined,
      }}
      aria-label={name ? `Avatar for ${name}` : undefined}
    >
      {showImage ? (
        <img
          src={url}
          alt={name || ""}
          className="w-full h-full object-cover"
          onError={() => setImgError(true)}
        />
      ) : (
        <span
          className="font-semibold leading-none"
          style={{ fontSize, color: NAVY }}
          aria-hidden="true"
        >
          {initials}
        </span>
      )}
    </div>
  );
}

export default Avatar;

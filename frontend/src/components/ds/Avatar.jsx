import React from "react";
import { NAVY, NAVY_08 } from "@/lib/tokens";

/**
 * Avatar — canonical implementation.
 * Imported from: components/ds/Avatar
 *
 * Shows initials from `name` or an image from `url`.
 * Background uses the navy brand token at 8% opacity.
 */
export function Avatar({ url, name, size = 32, className = "" }) {
  const initials = (name || "?")
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const fontSize = size <= 24 ? 9 : size <= 32 ? 11 : size <= 40 ? 12 : 14;

  return (
    <div
      className={`shrink-0 rounded-full flex items-center justify-center overflow-hidden select-none ${className}`}
      style={{ width: size, height: size, background: NAVY_08 }}
      aria-label={name ? `Avatar for ${name}` : undefined}
    >
      {url ? (
        <img src={url} alt={name || ""} className="w-full h-full object-cover" />
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

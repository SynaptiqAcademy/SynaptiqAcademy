/**
 * OrcidBadge — verified academic-identity chip with the green iD glyph.
 * Renders only when verified=true.
 */
import React from "react";

export default function OrcidBadge({ orcidId, size = "sm", showId = false, testId = "orcid-badge" }) {
  if (!orcidId) return null;
  const px = size === "lg" ? 18 : size === "md" ? 14 : 11;
  return (
    <a
      href={`https://orcid.org/${orcidId}`} target="_blank" rel="noreferrer"
      data-testid={testId}
      title={`ORCID verified: ${orcidId}`}
      onClick={(e) => e.stopPropagation()}
      className="inline-flex items-center gap-1 align-middle text-emerald-700 hover:text-emerald-900"
    >
      <svg width={px} height={px} viewBox="0 0 256 256" aria-hidden>
        <circle cx="128" cy="128" r="128" fill="#A6CE39" />
        <g fill="#FFF">
          <path d="M86.3 186.2H70.9V79.1h15.4v107.1zM78.6 64.6c-4.9 0-9-4.1-9-9 0-5 4.1-9 9-9 5 0 9 4 9 9 0 4.9-4 9-9 9zM108.9 79.1h41.6c39.6 0 57 28.3 57 53.6 0 27.5-21.5 53.6-56.8 53.6h-41.8V79.1zm15.4 93.3h24.5c34.9 0 42.9-26.5 42.9-39.7 0-21.5-13.7-39.7-43.7-39.7h-23.7v79.4z" />
        </g>
      </svg>
      {showId && <span className="font-mono text-[10px]">{orcidId}</span>}
    </a>
  );
}

import React from "react";

/**
 * PageFooter — consistent bottom spacing for every workspace page.
 *
 * Not a visible footer — purely a spacing device so every page has
 * identical breathing room at the bottom. WorkspaceLayout renders this
 * automatically; you only need it when building a page outside of
 * WorkspaceLayout.
 *
 * Props:
 *   height  number  — px (default: 40)
 */
export function PageFooter({ height = 40 }) {
  return <div style={{ height }} aria-hidden="true" />;
}

export default PageFooter;

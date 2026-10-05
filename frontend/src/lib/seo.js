/**
 * Minimal per-page SEO helper (Phase 9A Part 3, §31). No react-helmet
 * dependency — imperative DOM updates matching the existing pattern
 * already used for document.title in every marketing page. Restores the
 * site-wide default (from public/index.html) on unmount so navigating
 * away from a page doesn't leave stale canonical/description behind.
 */
export function setPageSeo({ title, description, path }) {
  const prevTitle = document.title;
  if (title) document.title = title;

  let descEl = document.querySelector('meta[name="description"]');
  const prevDescription = descEl?.getAttribute("content");
  if (description && descEl) descEl.setAttribute("content", description);

  let ogTitleEl = document.querySelector('meta[property="og:title"]');
  let ogDescEl = document.querySelector('meta[property="og:description"]');
  const prevOgTitle = ogTitleEl?.getAttribute("content");
  const prevOgDesc = ogDescEl?.getAttribute("content");
  if (title && ogTitleEl) ogTitleEl.setAttribute("content", title);
  if (description && ogDescEl) ogDescEl.setAttribute("content", description);

  let canonicalEl = document.querySelector('link[rel="canonical"]');
  if (!canonicalEl) {
    canonicalEl = document.createElement("link");
    canonicalEl.setAttribute("rel", "canonical");
    document.head.appendChild(canonicalEl);
  }
  if (path) canonicalEl.setAttribute("href", `https://www.synaptiq.academy${path}`);

  return () => {
    document.title = prevTitle;
    if (descEl && prevDescription != null) descEl.setAttribute("content", prevDescription);
    if (ogTitleEl && prevOgTitle != null) ogTitleEl.setAttribute("content", prevOgTitle);
    if (ogDescEl && prevOgDesc != null) ogDescEl.setAttribute("content", prevOgDesc);
  };
}

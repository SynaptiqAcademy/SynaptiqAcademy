/**
 * applyPreferenceEffects — applies the subset of Application Preferences that
 * have a real, honest, app-wide effect. Everything else in the preferences
 * store is intentionally stored-only (captioned in the UI as such) rather
 * than faking behavior that doesn't exist yet.
 */
const FONT_SIZES = { small: "14px", medium: "16px", large: "18px" };

export function applyPreferenceEffects(prefs) {
  if (!prefs || typeof document === "undefined") return;
  const root = document.documentElement;

  root.dataset.reducedMotion = String(!!prefs.reducedMotion);
  root.dataset.focusIndicators = String(!!prefs.focusIndicators);
  root.dataset.highContrast = String(!!prefs.highContrast);
  root.style.fontSize = FONT_SIZES[prefs.fontSize] || FONT_SIZES.medium;
}

export default applyPreferenceEffects;

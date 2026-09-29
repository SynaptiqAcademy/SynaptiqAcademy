/**
 * pickNextBestAction — pure selection logic for the Passport's "Recommended
 * next step" card (PassportNextBestAction.jsx). Extracted into its own
 * dependency-free module (P1 Phase 7C4.1) so it's unit-testable without
 * pulling in react-router-dom — this project's react-router-dom version
 * ships ESM-only and isn't resolvable under this repo's existing Jest
 * config (a separate, pre-existing gap, not something this pass fixes).
 *
 * Deterministic: the highest-point unearned item from the one canonical
 * completion source (services/profile_completion.py via
 * GET /users/me/profile-completion). No AI, no credits, no invented
 * ranking beyond the real backend-assigned point values.
 */
export function pickNextBestAction(completion) {
  const pending = (completion?.items || []).filter((i) => !i.earned);
  if (pending.length === 0) return null;
  return pending.reduce((best, i) => (i.points > (best?.points ?? -1) ? i : best), null);
}

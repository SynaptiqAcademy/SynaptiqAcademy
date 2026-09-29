/**
 * Single shared definition of "is this account's ORCID connection
 * authenticated" — i.e. OAuth-connected via routers/orcid.py's /callback,
 * not just a self-reported/legacy string value on users.orcid.
 *
 * users.orcid is normally an object ({orcid_id, access_token, verified_at,
 * ...}) once OAuth-connected. Some accounts (legacy data / seed scripts)
 * instead hold a bare string — a never-authenticated, self-reported ORCID
 * iD. Treating that string as "connected" is exactly what caused the
 * Passport/Career ORCID status contradiction (see commit 4b4de1c5 and
 * services/verification/profile_service.py's matching backend fix).
 *
 * Every "is ORCID connected/authenticated" indicator on the Passport
 * (PassportHero's badge, QuickActionsRail's action label, etc.) must import
 * this instead of re-deriving its own check.
 *
 * NOTE: IdentityCard.jsx's own local extractOrcidId() is intentionally NOT
 * migrated to this helper — there it renders a plain outbound identifier
 * link (same treatment as Google Scholar/ResearchGate), not a
 * verified-connection indicator, so accepting a self-reported string there
 * is correct, not a bug.
 */
export function getAuthenticatedOrcidId(orcid) {
  if (orcid && typeof orcid === "object" && orcid.orcid_id) return orcid.orcid_id;
  return null;
}

export function isOrcidAuthenticated(orcid) {
  return getAuthenticatedOrcidId(orcid) !== null;
}

import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";

/**
 * Frontend-side companion to the backend's require_institution_member /
 * require_institution_admin checks (services/permissions.py). The backend
 * is the real enforcement — this only avoids rendering an institution
 * dashboard shell (which would then just fail its own data calls) for a
 * user who isn't a member, and avoids a flash of the page before
 * entitlements have loaded.
 *
 * requireAdmin gates on real per-institution admin role
 * (entitlements.institution.is_admin) rather than the legacy platform-wide
 * institution_admin/admin role — see Sidebar.jsx's canSeeInstitutionAdminItems
 * comment for the one exception (Institution Intelligence Platform routes),
 * which still checks the legacy role because that's what its backend
 * actually authorizes today.
 */
export default function RequireInstitution({ children, requireAdmin = false }) {
  const { user, entitlements } = useAuth();

  const isPlatformStaff = ["admin", "super_admin"].includes(user?.role) || !!entitlements?.is_super_admin;

  // Entitlements haven't loaded yet — render nothing rather than a
  // premature "not a member" screen (avoids the flicker §50 warns about).
  if (entitlements === null && !isPlatformStaff) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-slate-400 text-sm">Loading…</div>
      </div>
    );
  }

  const isMember = isPlatformStaff || !!entitlements?.institution?.is_member;
  const isAdmin  = isPlatformStaff || !!entitlements?.institution?.is_admin;
  const allowed  = requireAdmin ? isAdmin : isMember;

  if (!allowed) {
    // Same page language as everywhere else: a title, one line, the next step.
    return (
      <div style={{ maxWidth: 600, padding: "8px 0 24px" }}>
        <p className="pl-eyebrow">Institution</p>
        <h1 className="pl-hero-title">
          {isMember ? "This page is for institution admins." : "This page is for members of an institution."}
        </h1>
        <p className="pl-sub" style={{ marginTop: 8 }}>
          {isMember
            ? "You're a member of your institution; this page is for its owners and admins."
            : "Membership comes from your institution: through your institutional email, an invitation, or an admin approving your request."}
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
          {!isMember && (
            <Link to="/institutions" className="inline-flex items-center h-9 px-4 text-[13px] font-semibold rounded-btn bg-navy-700 text-white no-underline hover:bg-navy-800">
              Find your institution
            </Link>
          )}
          <Link to="/discover" className="inline-flex items-center h-9 px-4 text-[13px] font-semibold rounded-btn border border-hairline-strong bg-white text-[color:var(--sq-text-primary)] no-underline hover:border-[color:var(--sq-text-primary)]">
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  return children;
}

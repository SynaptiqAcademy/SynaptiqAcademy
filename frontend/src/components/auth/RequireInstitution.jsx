import React from "react";
import { Link } from "react-router-dom";
import { Building2 } from "lucide-react";
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
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-6">
        <Building2 size={28} strokeWidth={1.5} className="text-slate-300 mb-3" />
        <div className="text-slate-700 font-medium mb-1">
          {isMember ? "Institution admin access required" : "You're not part of an institution yet"}
        </div>
        <p className="text-slate-500 text-sm max-w-sm mb-4">
          {isMember
            ? "This page is only available to institution owners and admins."
            : "This page is only available to verified members of a Synaptiq institution."}
        </p>
        <Link to="/discover" className="text-sm text-[#0F2847] font-medium hover:underline">
          Back to Home
        </Link>
      </div>
    );
  }

  return children;
}

import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import VerifyEmailPending from "../../pages/VerifyEmailPending";
import {
  isCommunityUnlocked,
  isAlwaysAllowed,
} from "../../lib/profileCompletion";

export default function ProtectedRoute({ children, requireOnboarded = true }) {
  const { user } = useAuth();
  const location = useLocation();

  // Loading state
  if (user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FDFDFB]">
        <div className="text-slate-500 text-sm font-mono">Loading…</div>
      </div>
    );
  }

  // Not authenticated → redirect to login
  if (user === false) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  // AUTH-002: Email not verified → show verification pending screen
  // Super admins are always exempt (their accounts are pre-verified)
  if (!user.is_super_admin && user.email_verified === false) {
    return <VerifyEmailPending />;
  }

  // Enforce initial onboarding completion (sets basic user_type / institution)
  if (requireOnboarded && user.onboarded === false && location.pathname !== "/onboarding") {
    return <Navigate to="/onboarding" replace />;
  }

  // ── Phase 1: Profile-completion gate ────────────────────────────────────────
  // After the initial onboarding wizard, users must complete enough of their
  // academic profile before the community is unlocked.
  // Super admins bypass the gate unconditionally.
  if (
    requireOnboarded &&
    user.onboarded === true &&
    !user.is_super_admin &&
    !isCommunityUnlocked(user) &&
    location.pathname !== "/profile-setup" &&
    !isAlwaysAllowed(location.pathname)
  ) {
    return <Navigate to="/profile-setup" replace />;
  }
  // ────────────────────────────────────────────────────────────────────────────

  return children;
}

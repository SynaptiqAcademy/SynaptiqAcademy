/**
 * GoogleCallback — handles ?google_error= query params from /api/google/callback redirects.
 * On success, the backend redirects directly to /onboarding or /discover with auth cookies set.
 * On failure, the backend redirects here with a google_error query param.
 */
import React, { useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { AlertTriangle, Loader2 } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { NAVY } from "@/lib/tokens";

const ERROR_MESSAGES = {
  cancelled:              "You cancelled the Google sign-in.",
  state_invalid:          "Authentication request expired. Please try again.",
  exchange_failed:        "Could not connect to Google. Please try again.",
  no_access_token:        "Google did not return an access token. Please try again.",
  userinfo_failed:        "Could not retrieve your Google profile. Please try again.",
  missing_profile:        "Your Google account is missing required profile information.",
  already_linked_to_other_account: "This Google account is already linked to a different SYNAPTIQ account.",
  no_session:             "Your session expired. Please sign in first, then link Google.",
};

export default function GoogleCallback() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { refreshMe } = useAuth();
  const googleError = params.get("google_error");
  const googleConnected = params.get("google") === "connected";

  useEffect(() => {
    if (googleConnected) {
      refreshMe().then(() => navigate("/settings?google=connected", { replace: true }));
    }
  }, [googleConnected, navigate, refreshMe]);

  if (!googleError && !googleConnected) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FDFDFB]">
        <Loader2 className="animate-spin text-slate-400" size={28} />
      </div>
    );
  }

  if (googleError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FDFDFB] p-8">
        <div className="w-full max-w-md bg-white border border-slate-200 p-10">
          <AlertTriangle className="text-amber-600" size={40} strokeWidth={1.4} />
          <h1 className="font-serif text-3xl text-slate-900 mt-3">Google sign-in failed</h1>
          <p className="text-sm text-slate-600 mt-2">
            {ERROR_MESSAGES[googleError] || "Something went wrong. Please try again."}
          </p>
          <button
            onClick={() => navigate("/login", { replace: true })}
            className="mt-6 inline-block bg-[#0F2847] text-white px-5 py-2.5 text-sm hover:bg-slate-800"
          >
            Back to sign in
          </button>
        </div>
      </div>
    );
  }

  return null;
}

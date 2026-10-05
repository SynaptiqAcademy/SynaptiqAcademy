/**
 * RouteEntitlementGate — when the signed-in user's plan doesn't include the
 * page they opened (direct URL, bookmark, or nav), explain what the feature
 * does, why it's locked and which plan unlocks it, instead of rendering a
 * page whose API calls the server will refuse anyway (402).
 * Rendering only — the backend enforces every capability itself.
 */
import React, { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { Lock, ArrowRight } from "lucide-react";
import { useEntitlements } from "@/lib/entitlements";
import { trackMonetizationEvent } from "@/lib/analytics";

export function LockedFeature({ capability }) {
  const { paywall } = useEntitlements();
  const pw = paywall(capability);
  useEffect(() => {
    trackMonetizationEvent("paywall_viewed", { feature: capability, source: "route" });
    trackMonetizationEvent("paid_feature_attempted", { feature: capability });
  }, [capability]);
  return (
    <div className="max-w-xl mx-auto px-4 py-16" data-testid="locked-feature" data-capability={capability}>
      <div className="border border-slate-200 bg-white p-8">
        <div className="overline flex items-center gap-1.5"><Lock size={11} /> Available on {pw.required_plan_name}</div>
        <h1 className="font-serif text-3xl text-slate-900 mt-2">{pw.message}</h1>
        <p className="text-sm text-slate-600 mt-3 leading-relaxed">
          Your Free plan includes your academic profile, public research page and ORCID publications.
          {` ${pw.required_plan_name}`} adds the tools to collaborate, discover and work with AI.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/pricing" onClick={() => trackMonetizationEvent("upgrade_clicked", { feature: capability, source: "route" })}
            className="bg-[#0F2847] text-white px-4 py-2.5 text-sm hover:bg-slate-800 inline-flex items-center gap-2"
            data-testid="locked-feature-upgrade">
            Upgrade to {pw.required_plan_name} <ArrowRight size={14} />
          </Link>
          <Link to="/profile" className="border border-slate-300 text-slate-700 px-4 py-2.5 text-sm hover:bg-slate-50">
            Back to my profile
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function RouteEntitlementGate({ children }) {
  const { pathname } = useLocation();
  const { lockedFor } = useEntitlements();
  const cap = lockedFor(pathname);
  return cap ? <LockedFeature capability={cap} /> : children;
}

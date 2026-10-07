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
  const { paywall, tier } = useEntitlements();
  const pw = paywall(capability);
  // Describe the plan the person actually has, then what the required plan adds.
  const onPro = /^(PRO|RESEARCHER)$/i.test(String(tier || ""));
  const current = onPro
    ? "Your Pro plan includes collaboration, discovery, projects and the core AI tools."
    : "Your Free plan includes your Academic Passport, public research page and ORCID publications.";
  const adds = pw.required_plan_name === "Pro Advanced"
    ? "Pro Advanced adds literature review, research gap finding, study design and statistical review, Collaboration Intelligence and impact tracking."
    : `${pw.required_plan_name} adds the tools to collaborate, discover and work with AI.`;
  useEffect(() => {
    trackMonetizationEvent("paywall_viewed", { feature: capability, source: "route" });
    trackMonetizationEvent("paid_feature_attempted", { feature: capability });
  }, [capability]);
  return (
    <div className="max-w-xl mx-auto px-4 py-16" data-testid="locked-feature" data-capability={capability}>
      <div className="border border-hairline bg-white p-8 rounded-card">
        <div className="overline flex items-center gap-1.5"><Lock size={11} /> Available on {pw.required_plan_name}</div>
        <h1 className="font-display text-3xl font-normal text-[color:var(--sq-text-primary)] mt-2">{pw.message}</h1>
        <p className="text-sm text-[color:var(--sq-text-secondary)] mt-3 leading-relaxed">
          {current} {adds}
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/pricing" onClick={() => trackMonetizationEvent("upgrade_clicked", { feature: capability, source: "route" })}
            className="bg-navy-700 text-white h-10 px-4 text-sm font-semibold rounded-btn hover:bg-navy-800 inline-flex items-center gap-2"
            data-testid="locked-feature-upgrade">
            Upgrade to {pw.required_plan_name} <ArrowRight size={14} />
          </Link>
          <Link to="/profile" className="border border-hairline-strong bg-white text-[color:var(--sq-text-primary)] h-10 px-4 text-sm font-semibold rounded-btn hover:border-[color:var(--sq-text-primary)] inline-flex items-center">
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

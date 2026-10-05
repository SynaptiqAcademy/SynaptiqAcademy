/**
 * UpgradeModal — single global modal that explains a paywall.
 *
 * Opened by:
 *   - the axios interceptor (lib/api.js) when a user action gets a 402 with
 *     a structured payload from the backend, and
 *   - locked navigation items (lib/entitlements.js::openPaywall).
 *
 * Backend payload shapes (services/entitlements.py, services/credits_service.py,
 * services/monetization_middleware.py, services/permissions.py):
 *   upgrade_required   { capability, message, required_plan, required_plan_name }
 *   credits_exhausted  { message, needed, balance, monthly_balance, pack_balance }
 *   workspace_locked   { message, workspace_limit }
 *   quota_exceeded / subscription_inactive / storage_limit_exceeded { message }
 * The copy shown is the backend's own message — the client never invents
 * prices, limits or costs.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, X, ArrowRight, Zap, Lock } from "lucide-react";
import { planDisplayName } from "@/lib/planNames";
import { trackMonetizationEvent } from "@/lib/analytics";

export default function UpgradeModal() {
  const [gate, setGate] = useState(null);

  useEffect(() => {
    const handler = (e) => {
      const d = e.detail || null;
      setGate(d);
      if (d) {
        trackMonetizationEvent("paywall_viewed", {
          feature: d.capability || d.operation || d.code, code: d.code, source: d.source || "api",
        });
        if (d.code === "upgrade_required") {
          trackMonetizationEvent("paid_feature_attempted", { feature: d.capability || "unknown" });
        }
      }
    };
    window.addEventListener("synaptiq:gate", handler);
    return () => window.removeEventListener("synaptiq:gate", handler);
  }, []);

  useEffect(() => {
    if (!gate) return;
    const onKey = (e) => { if (e.key === "Escape") setGate(null); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [gate]);

  if (!gate) return null;

  const close = () => setGate(null);
  const clicked = (target) => {
    trackMonetizationEvent("upgrade_clicked", { feature: gate.capability || gate.code, target });
    close();
  };

  const code = gate.code;
  const isCredits = code === "credits_exhausted";
  const isLocked = code === "workspace_locked";
  const planName = gate.required_plan_name || planDisplayName(gate.required_plan) || "Pro";

  const title = isCredits
    ? "Not enough AI credits"
    : isLocked
    ? "This workspace is read-only"
    : code === "quota_exceeded" || code === "storage_limit_exceeded"
    ? "You've reached your plan limit"
    : code === "subscription_inactive"
    ? "Your subscription isn't active"
    : `Available on ${planName}`;

  return (
    <div className="fixed inset-0 z-[10500] flex items-center justify-center p-6 bg-slate-900/50"
         data-testid="upgrade-modal" onClick={close}>
      <div role="dialog" aria-modal="true" aria-labelledby="upgrade-modal-title"
           className="bg-white border border-slate-200 max-w-md w-full p-8" onClick={(e) => e.stopPropagation()}>
        <button onClick={close} aria-label="Close"
          className="float-right text-slate-400 hover:text-slate-900" data-testid="upgrade-modal-close">
          <X size={16} />
        </button>
        <div className="overline flex items-center gap-1.5">
          {isCredits ? <Zap size={11} /> : <Lock size={11} />}
          {isCredits ? "AI credits" : isLocked ? "Plan limit" : "Upgrade"}
        </div>
        <h2 id="upgrade-modal-title" className="font-serif text-3xl text-slate-900 mt-2">{title}</h2>
        <p className="text-slate-700 mt-3 text-sm leading-relaxed" data-testid="upgrade-modal-message">{gate.message}</p>

        {isCredits && (
          <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
            <div className="border border-slate-200 p-3">
              <div className="overline text-slate-400">This month</div>
              <div className="font-mono text-[#0F2847]">{gate.monthly_balance ?? 0}</div>
            </div>
            <div className="border border-slate-200 p-3">
              <div className="overline text-slate-400">Purchased</div>
              <div className="font-mono text-[#0F2847]">{gate.pack_balance ?? 0}</div>
            </div>
          </div>
        )}

        <div className="mt-6 flex flex-col sm:flex-row gap-3">
          {isCredits ? (
            <>
              <Link to="/ai-credits#buy-credits" onClick={() => clicked("buy_credits")}
                className="flex-1 bg-[#0F2847] text-white px-4 py-2.5 text-sm hover:bg-slate-800 inline-flex items-center justify-center gap-2"
                data-testid="upgrade-modal-buy-credits">
                <Zap size={14} /> Buy credits
              </Link>
              <Link to="/pricing" onClick={() => clicked("pricing")}
                className="flex-1 border border-[#0F2847] text-[#0F2847] px-4 py-2.5 text-sm hover:bg-[#0F2847] hover:text-white inline-flex items-center justify-center gap-2"
                data-testid="upgrade-modal-upgrade-plan">
                <Sparkles size={14} /> Compare plans
              </Link>
            </>
          ) : (
            <Link to={gate.upgrade_url || "/pricing"} onClick={() => clicked("pricing")}
              className="flex-1 bg-[#0F2847] text-white px-4 py-2.5 text-sm hover:bg-slate-800 inline-flex items-center justify-center gap-2"
              data-testid="upgrade-modal-view-plans">
              {code === "upgrade_required" ? `Upgrade to ${planName}` : "View plans"} <ArrowRight size={14} />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

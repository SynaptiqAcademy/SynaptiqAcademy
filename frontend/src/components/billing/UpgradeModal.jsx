/**
 * UpgradeModal — single global modal that surfaces whenever a 402 with an
 * upgrade-hint payload is intercepted from the API.
 *
 * Backend payload shape (from services/permissions.py):
 *   { code: 'upgrade_required'|'credits_exhausted'|'subscription_inactive'|'quota_exceeded',
 *     message, required_plan?, current_plan?, needed?, balance?,
 *     monthly_balance?, pack_balance?, upgrade_url?, buy_credits_url? }
 *
 * Other components dispatch:  window.dispatchEvent(new CustomEvent('synaptiq:gate', {detail}))
 * The axios interceptor in lib/api.js already does that.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, X, ArrowRight, Zap } from "lucide-react";

export default function UpgradeModal() {
  const [gate, setGate] = useState(null);

  useEffect(() => {
    const handler = (e) => setGate(e.detail || null);
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

  const isCredits = gate.code === "credits_exhausted";
  const isPlan = gate.code === "upgrade_required" || gate.code === "subscription_inactive";
  const isQuota = gate.code === "quota_exceeded";

  const title = isCredits
    ? "You have exhausted your monthly credits"
    : isQuota
    ? "You've reached your plan limit"
    : `Upgrade to ${(gate.required_plan || "Researcher").replace("_", " ")}`;

  return (
    <div className="fixed inset-0 z-[10500] flex items-center justify-center p-6 bg-slate-900/50"
         data-testid="upgrade-modal" onClick={() => setGate(null)}>
      <div role="dialog" aria-modal="true" aria-labelledby="upgrade-modal-title" className="bg-white border border-slate-200 max-w-md w-full p-8" onClick={(e) => e.stopPropagation()}>
        <button onClick={() => setGate(null)}
          aria-label="Close" className="float-right text-slate-400 hover:text-slate-900" data-testid="upgrade-modal-close">
          <X size={16} />
        </button>
        <div className="overline">{isCredits ? "Credits exhausted" : "Upgrade required"}</div>
        <h2 id="upgrade-modal-title" className="font-serif text-3xl text-slate-900 mt-2">{title}</h2>
        <p className="text-slate-700 mt-3 text-sm leading-relaxed">{gate.message}</p>

        {isCredits && (
          <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
            <div className="border border-slate-200 p-3">
              <div className="overline text-slate-400">Monthly</div>
              <div className="font-mono text-[#0F2847]">{gate.monthly_balance ?? 0}</div>
            </div>
            <div className="border border-slate-200 p-3">
              <div className="overline text-slate-400">Pack</div>
              <div className="font-mono text-[#0F2847]">{gate.pack_balance ?? 0}</div>
            </div>
          </div>
        )}

        <div className="mt-6 flex flex-col sm:flex-row gap-3">
          {isCredits ? (
            <>
              <Link to={gate.buy_credits_url || "/pricing#credit-packs"} onClick={() => setGate(null)}
                className="flex-1 bg-[#0F2847] text-white px-4 py-2.5 text-sm hover:bg-slate-800 inline-flex items-center justify-center gap-2"
                data-testid="upgrade-modal-buy-credits">
                <Zap size={14} /> Buy Credits
              </Link>
              <Link to={gate.upgrade_url || "/pricing"} onClick={() => setGate(null)}
                className="flex-1 border border-[#0F2847] text-[#0F2847] px-4 py-2.5 text-sm hover:bg-[#0F2847] hover:text-white inline-flex items-center justify-center gap-2"
                data-testid="upgrade-modal-upgrade-plan">
                <Sparkles size={14} /> Upgrade Plan
              </Link>
            </>
          ) : (
            <Link to={gate.upgrade_url || "/pricing"} onClick={() => setGate(null)}
              className="flex-1 bg-[#0F2847] text-white px-4 py-2.5 text-sm hover:bg-slate-800 inline-flex items-center justify-center gap-2"
              data-testid="upgrade-modal-view-plans">
              View Plans <ArrowRight size={14} />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

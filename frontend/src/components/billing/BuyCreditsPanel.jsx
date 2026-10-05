/**
 * BuyCreditsPanel — credit packs for Pro / Pro Advanced.
 *
 * Packs and prices come from GET /api/billing/credit-packs. Checkout goes to
 * Stripe; credits are added ONLY when Stripe's verified webhook confirms the
 * payment (never from the success redirect). Free plans see an upgrade
 * prompt instead — extra credits are not sold on Free.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Package, Sparkles } from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";
import { useEntitlements } from "@/lib/entitlements";
import { trackMonetizationEvent } from "@/lib/analytics";

const fmtEur = (n) => `€${Number(n).toFixed(2)}`;

export default function BuyCreditsPanel() {
  const { has, entitlements } = useEntitlements();
  const [packs, setPacks] = useState([]);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const canBuy = has("can_purchase_ai_credits");

  useEffect(() => {
    api.get("/billing/credit-packs").then((r) => setPacks(r.data || [])).catch(() => {});
    trackMonetizationEvent("credit_pack_viewed");
  }, []);

  const buy = async (pack) => {
    setBusy(pack.code);
    setError("");
    trackMonetizationEvent("credit_pack_checkout_started", { pack_code: pack.code });
    try {
      const origin = window.location.origin;
      const { data } = await api.post("/billing/credit-pack-checkout", {
        pack_code: pack.code,
        success_url: `${origin}/payment/success?kind=credits`,
        cancel_url: `${origin}/payment/cancelled?kind=credits`,
      });
      if (data?.url) window.location.assign(data.url);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  if (entitlements && !canBuy) {
    return (
      <div className="border border-slate-200 p-5" data-testid="buy-credits-upgrade">
        <div className="overline">AI credits</div>
        <p className="text-sm text-slate-700 mt-2">
          AI tools and monthly AI credits are part of Pro and Pro Advanced.
          Extra credit packs can be bought on both paid plans.
        </p>
        <Link to="/pricing" onClick={() => trackMonetizationEvent("upgrade_clicked", { source: "buy_credits" })}
          className="inline-flex items-center gap-2 mt-4 bg-[#0F2847] text-white px-4 py-2 text-sm hover:bg-slate-800">
          <Sparkles size={13} /> See plans
        </Link>
      </div>
    );
  }

  return (
    <div data-testid="buy-credits-panel">
      <div className="grid sm:grid-cols-3 gap-4">
        {packs.map((p) => (
          <div key={p.code} className="border border-slate-200 p-5 flex flex-col" data-testid={`credit-pack-${p.code}`}>
            <div className="flex items-center gap-1.5 overline">
              <Package size={12} strokeWidth={1.5} className="text-[#0F2847]" /> {p.label}
            </div>
            <div className="font-serif text-3xl text-slate-900 mt-2">{fmtEur(p.price_eur)}</div>
            <div className="text-xs text-slate-500 mt-1 font-mono">
              {fmtEur(p.price_eur / p.credits * 100)} per 100 credits
            </div>
            <button
              type="button"
              onClick={() => buy(p)}
              disabled={!p.available || busy === p.code}
              className="mt-4 w-full bg-[#0F2847] text-white px-3 py-2 text-sm hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid={`buy-pack-${p.code}`}
            >
              {busy === p.code ? "Opening checkout…" : p.available ? `Buy ${p.credits} credits` : "Coming soon"}
            </button>
          </div>
        ))}
      </div>
      {error && <p className="text-sm text-red-700 mt-3" role="alert">{error}</p>}
      <p className="text-[11px] text-slate-500 mt-3">
        Purchased credits never expire and are used after your monthly credits. They stay on your
        account if you change plan, and can be used whenever you're on Pro or Pro Advanced.
      </p>
    </div>
  );
}

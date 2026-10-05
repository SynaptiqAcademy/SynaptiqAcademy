/**
 * CreditCost — "Uses 30 AI Credits" label shown next to an AI action BEFORE
 * the user runs it. The number comes from the server catalogue by operation
 * code (e.g. "FULL_MANUSCRIPT_REVIEW"), so the label always matches what the
 * backend charges.
 */
import React, { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { loadCreditCatalogue } from "./creditCatalogue";

export default function CreditCost({ operation, className = "", prefix = "Uses" }) {
  const [cost, setCost] = useState(null);
  useEffect(() => {
    let alive = true;
    loadCreditCatalogue().then((c) => { if (alive) setCost(c.operations?.[operation] ?? c.actions?.[operation] ?? null); });
    return () => { alive = false; };
  }, [operation]);
  if (cost == null) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 text-[11px] font-mono text-slate-500 ${className}`}
      data-testid={`credit-cost-${operation}`}
      title="AI credits charged when this completes. Failed requests are refunded automatically."
    >
      <Sparkles size={10} strokeWidth={1.5} className="text-[#0F2847]" />
      {prefix} {cost} AI Credit{cost === 1 ? "" : "s"}
    </span>
  );
}

/** Just the number, for inline copy like "Review · <CreditCostNumber/> Credits". */
export function CreditCostNumber({ operation }) {
  const [cost, setCost] = useState(null);
  useEffect(() => {
    let alive = true;
    loadCreditCatalogue().then((c) => { if (alive) setCost(c.operations?.[operation] ?? c.actions?.[operation] ?? null); });
    return () => { alive = false; };
  }, [operation]);
  return <>{cost ?? "…"}</>;
}

import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

const NAVY = "#0F2847";

/**
 * Checkout was cancelled or failed before completion (§30). Calm, no
 * implication that any charge occurred — because none did; Stripe Checkout
 * only redirects here on cancel/abandon, before any charge is captured.
 */
export default function PaymentCancelled() {
  useEffect(() => {
    document.title = "Checkout cancelled — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);

  return (
    <div style={{ maxWidth: 520, margin: "0 auto", padding: "64px 24px", textAlign: "center" }}>
      <h1 style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0a0f1a", marginBottom: 8 }}>
        Checkout cancelled.
      </h1>
      <p style={{ fontSize: "0.9rem", color: "#64748b", marginBottom: 28, lineHeight: 1.7 }}>
        Nothing was charged. Your account is unchanged — you can try again whenever you're ready.
      </p>
      <Link
        to="/pricing"
        style={{ display: "inline-flex", alignItems: "center", gap: 8, background: NAVY, color: "#fff", padding: "13px 28px", borderRadius: 10, fontSize: "0.9rem", fontWeight: 700, textDecoration: "none" }}
      >
        Back to Pricing <ArrowRight size={14} strokeWidth={2.5} />
      </Link>
    </div>
  );
}

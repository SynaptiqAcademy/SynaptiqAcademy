import React, { useEffect, useState, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, ArrowRight, Loader2 } from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

const NAVY = "#0F2847";

/**
 * Dedicated payment-success page (§29). The URL param (?type=plan|pack) is
 * used ONLY to decide which message to show — it is NEVER treated as proof
 * that payment succeeded. Entitlement is read from the canonical server
 * state (GET /billing/subscription, GET /credits/balance), which is only
 * ever updated by the Stripe webhook. If that state hasn't caught up yet
 * (webhook is async), this page polls briefly rather than showing false
 * confirmation — and never fabricates a renewal date or plan it hasn't
 * actually confirmed.
 */
export default function PaymentSuccess() {
  const [searchParams] = useSearchParams();
  const type = searchParams.get("type") || "plan";
  const { user, refreshMe } = useAuth();
  const [sub, setSub] = useState(null);
  const [credits, setCredits] = useState(null);
  const [polling, setPolling] = useState(true);
  const attemptsRef = useRef(0);

  useEffect(() => {
    document.title = "Payment received — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const [subRes, creditsRes] = await Promise.all([
          api.get("/billing/subscription"),
          api.get("/credits/balance"),
        ]);
        if (!mounted) return;
        setSub(subRes.data);
        setCredits(creditsRes.data);
        const planIsPaid = subRes.data?.plan?.code && subRes.data.plan.code !== "free";
        const packJustCredited = type === "pack"; // pack credit changes balance, not plan
        if (type === "plan" && !planIsPaid && attemptsRef.current < 6) {
          attemptsRef.current += 1;
          setTimeout(poll, 2000);
          return;
        }
        setPolling(false);
        refreshMe();
      } catch {
        if (mounted) setPolling(false);
      }
    };
    poll();
    return () => { mounted = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type]);

  const confirmedPaid = sub?.plan?.code && sub.plan.code !== "free";

  // First useful action, based on onboarding intent — never a generic
  // "profile complete" message (§35/§91 of the commercial-experience spec).
  const isTeaching = user?.primary_domain === "teaching";
  const nextAction = isTeaching
    ? { label: "Go to Teaching", to: "/teaching" }
    : { label: "Describe your research", to: "/researchers" };

  return (
      <div style={{ maxWidth: 560, margin: "0 auto", padding: "64px 24px", textAlign: "center" }}>
        {polling && type === "plan" ? (
          <>
            <Loader2 size={32} className="animate-spin" style={{ color: NAVY, margin: "0 auto 20px" }} />
            <h1 style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0a0f1a", marginBottom: 8 }}>
              Confirming your payment…
            </h1>
            <p style={{ fontSize: "0.9rem", color: "#64748b" }}>
              This usually takes a few seconds.
            </p>
          </>
        ) : type === "pack" ? (
          <>
            <CheckCircle2 size={36} style={{ color: "#059669", margin: "0 auto 20px" }} />
            <h1 style={{ fontSize: "1.6rem", fontWeight: 800, color: "#0a0f1a", marginBottom: 8 }}>
              Credits added.
            </h1>
            <p style={{ fontSize: "0.92rem", color: "#64748b", marginBottom: 8 }}>
              {credits ? `You now have ${credits.balance?.toLocaleString()} credits available.` : "Your credit pack has been added to your account."}
            </p>
            <Link to="/settings/billing" style={{ display: "inline-flex", alignItems: "center", gap: 6, marginTop: 24, fontSize: "0.88rem", fontWeight: 700, color: NAVY, textDecoration: "none" }}>
              View billing <ArrowRight size={14} />
            </Link>
          </>
        ) : confirmedPaid ? (
          <>
            <CheckCircle2 size={36} style={{ color: "#059669", margin: "0 auto 20px" }} />
            <h1 style={{ fontSize: "1.6rem", fontWeight: 800, color: "#0a0f1a", marginBottom: 8 }}>
              Your {sub.plan.name} plan is active.
            </h1>
            <p style={{ fontSize: "0.92rem", color: "#64748b", marginBottom: 28 }}>
              {sub.plan.credits_per_month?.toLocaleString()} credits/month, effective now.
            </p>
            <Link
              to={nextAction.to}
              style={{ display: "inline-flex", alignItems: "center", gap: 8, background: NAVY, color: "#fff", padding: "13px 28px", borderRadius: 10, fontSize: "0.9rem", fontWeight: 700, textDecoration: "none" }}
            >
              {nextAction.label} <ArrowRight size={14} strokeWidth={2.5} />
            </Link>
          </>
        ) : (
          <>
            <h1 style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0a0f1a", marginBottom: 8 }}>
              Still confirming your payment.
            </h1>
            <p style={{ fontSize: "0.9rem", color: "#64748b", marginBottom: 24 }}>
              This can take a minute to finish processing. Your plan will update automatically —
              no action needed. If it doesn't update shortly, contact us and we'll sort it out.
            </p>
            <Link to="/settings/billing" style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.88rem", fontWeight: 700, color: NAVY, textDecoration: "none" }}>
              Check billing status <ArrowRight size={14} />
            </Link>
          </>
        )}
      </div>
  );
}

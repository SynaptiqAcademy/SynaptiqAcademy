/**
 * BillingCenter — Settings → Billing surface.
 *
 * All data hydrated from production endpoints (no mocks):
 *   GET /api/billing/subscription         current plan + credits + limits
 *   GET /api/billing/history              invoices + pack purchases + sub events
 *   GET /api/billing/subscription-history plan transitions
 *   GET /api/credits/purchases            pack purchase audit
 *   POST /api/billing/cancel              cancel at period end
 *   POST /api/billing/portal-session      Stripe customer portal
 *
 * Visual design matches Design System V2 (Card/Section/tokens) — the same
 * language as Settings and Academic Passport. Real card brand/last4 and
 * per-invoice PDF links aren't stored anywhere in this backend (Stripe's
 * hosted portal is the actual source for both), so "Payment Method" and
 * "Manage payment methods" route to the real Stripe portal instead of
 * fabricating card details or download links.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { SettingsLayout } from "@/layouts";
import api from "../lib/api";
import { toast } from "sonner";
import {
  Sparkles, AlertCircle, CreditCard, ArrowRight, Crown, CheckCircle2,
  Headphones, Zap,
} from "lucide-react";
import { Card } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { Badge } from "@/components/ds/Badge";
import { ProgressBar } from "@/components/ds/Progress";
import { EmptyState } from "@/components/ds/EmptyState";
import { SkeletonPage } from "@/components/ds/LoadingState";
import { Dialog } from "@/components/ds/Modal";
import {
  TYPE, NAVY, NAVY2, WHITE, WARM, BRD, EMERALD, AMBER, TEXT_MUTED, TEXT_SECONDARY,
  WARNING_BG, WARNING_TEXT,
} from "@/lib/tokens";

function Row({ label, value }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "9px 0", borderBottom: `1px solid ${BRD}` }}>
      <span style={{ fontSize: 12.5, color: TEXT_SECONDARY }}>{label}</span>
      <span style={{ fontSize: 12.5, fontWeight: 600, color: "#0f172a" }}>{value}</span>
    </div>
  );
}

function CreditsRing({ total, used }) {
  const dim = 128, stroke = 12;
  const r = (dim - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const pct = total > 0 ? Math.min(100, (used / total) * 100) : 0;
  const offset = circ - (pct / 100) * circ;
  return (
    <div style={{ position: "relative", width: dim, height: dim, margin: "0 auto" }}>
      <svg width={dim} height={dim} viewBox={`0 0 ${dim} ${dim}`} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke="#EDE9FE" strokeWidth={stroke} />
        <circle
          cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke="#7C3AED" strokeWidth={stroke}
          strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 800ms ease-out" }}
        />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontFamily: "Georgia, serif", fontSize: 22, fontWeight: 700, color: "#0f172a", lineHeight: 1 }}>{total.toLocaleString()}</span>
        <span style={{ fontSize: 10.5, color: TEXT_MUTED, marginTop: 2 }}>Total</span>
      </div>
    </div>
  );
}

export default function BillingCenter() {
  const [sub, setSub] = useState(null);
  const [history, setHistory] = useState([]);
  const [subHistory, setSubHistory] = useState([]);
  const [purchases, setPurchases] = useState([]);
  const [cancelling, setCancelling] = useState(false);

  const refresh = async () => {
    const tasks = [
      api.get("/billing/subscription").then((r) => setSub(r.data)).catch(() => {}),
      api.get("/billing/history").then((r) => setHistory(r.data || [])).catch(() => setHistory([])),
      api.get("/billing/subscription-history").then((r) => setSubHistory(r.data || [])).catch(() => setSubHistory([])),
      api.get("/credits/purchases").then((r) => setPurchases(r.data || [])).catch(() => setPurchases([])),
    ];
    await Promise.all(tasks);
  };
  useEffect(() => { refresh(); }, []);

  const [confirmCancelOpen, setConfirmCancelOpen] = useState(false);

  const cancel = async () => {
    setCancelling(true);
    try {
      await api.post("/billing/cancel", {});
      toast.success("Subscription will not renew.");
      await refresh();
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error((d && d.message) || (typeof d === "string" ? d : "Could not cancel."));
    } finally {
      setCancelling(false);
      setConfirmCancelOpen(false);
    }
  };

  const openPortal = async () => {
    try {
      const r = await api.post("/billing/portal-session", { return_url: window.location.href });
      if (r.data?.url) window.location.href = r.data.url;
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.info((d && d.message) || "Billing portal is available once Stripe is configured.");
    }
  };

  if (!sub) {
    return (
      <div className="p-6" data-testid="billing-center-loading">
        <SkeletonPage />
      </div>
    );
  }

  const plan = sub.plan || {};
  const credits = sub.credits || {};
  const subscription = sub.subscription;
  const planLabel = plan.name || "Free";
  const status = subscription?.status || (plan.code === "free" ? "active" : "inactive");
  const renewsAt = subscription?.current_period_end || null;
  const renewsDate = renewsAt ? new Date(renewsAt * 1000).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) : null;
  const cancelAtPeriodEnd = subscription?.cancel_at_period_end;

  const monthlyAllowance = credits.monthly_allowance ?? 0;
  const monthlyUsed = Math.max(0, monthlyAllowance - (credits.monthly_balance ?? 0));
  const totalBalance = credits.balance ?? 0;
  const seats = plan.limits?.team_seats;
  const storageGb = plan.limits?.repository_gb;
  const invoiceRows = history.filter((h) => h.kind === "subscription_charge" || h.kind === "invoice" || h.kind === "invoice_paid" || h.amount_eur);

  return (
    <SettingsLayout title="Billing & Subscription" subtitle="Manage your plan, credits, invoices and billing preferences.">
      {status === "past_due" && (
        <div className="mt-2 mb-4 flex items-start gap-3" style={{ border: "1px solid #FDE68A", background: WARNING_BG, padding: 16, borderRadius: 10 }} data-testid="past-due-banner">
          <AlertCircle size={18} style={{ color: AMBER, flexShrink: 0, marginTop: 1 }} />
          <div>
            <div style={{ fontWeight: 700, color: WARNING_TEXT }}>Payment past due</div>
            <p style={{ fontSize: 13, color: WARNING_TEXT, margin: "4px 0 0" }}>Your last invoice payment failed. Please update your billing method to keep access.</p>
            <button onClick={openPortal} style={{ marginTop: 8, fontSize: 12.5, textDecoration: "underline", color: WARNING_TEXT, background: "none", border: "none", cursor: "pointer", padding: 0 }}>Update payment method</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px]" style={{ gap: 20 }}>
        {/* ── Main column ── */}
        <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: 20 }}>

          {/* Current Plan */}
          <Card padding="none" data-testid="billing-current-plan">
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, padding: "20px 24px 0", flexWrap: "wrap" }}>
              <div style={TYPE.label}>Current Plan</div>
              <Link to="/pricing">
                <Button as="span" variant="ghost" size="sm">Compare Plans</Button>
              </Link>
            </div>

            <div style={{ margin: "16px 24px 24px", borderRadius: 14, padding: 24, background: `linear-gradient(135deg, ${NAVY} 0%, ${NAVY2} 100%)`, color: WHITE }}>
              <div className="flex flex-col sm:flex-row" style={{ alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
                <div className="flex-wrap" style={{ display: "flex", alignItems: "flex-start", gap: 14, minWidth: 0 }}>
                  <div style={{ width: 44, height: 44, borderRadius: 12, background: "rgba(124,58,237,0.35)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Crown size={20} color="#C4B5FD" />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div className="flex-wrap" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 17, fontWeight: 700 }}>{planLabel} Plan</span>
                      <Badge variant={status === "active" || status === "trialing" ? "success" : status === "past_due" ? "warning" : "neutral"} size="sm">
                        {status === "active" ? "Active" : status}
                      </Badge>
                    </div>
                    <p style={{ fontSize: 12.5, color: "rgba(255,255,255,0.65)", margin: "4px 0 0", maxWidth: 420 }}>
                      {plan.tagline || "Your current Synaptiq subscription."}
                    </p>
                  </div>
                </div>
                <div style={{ textAlign: "right", flexShrink: 0 }}>
                  <div style={{ fontFamily: "Georgia, serif", fontSize: 24, fontWeight: 700 }}>
                    {plan.price_eur_monthly ? `€${plan.price_eur_monthly}` : "Custom"}
                    {plan.price_eur_monthly > 0 && <span style={{ fontSize: 12, fontWeight: 400, color: "rgba(255,255,255,0.55)" }}>/month</span>}
                  </div>
                  <div style={{ fontSize: 11, color: "rgba(255,255,255,0.55)", marginTop: 2 }}>
                    {plan.price_eur_monthly > 0 ? "Billed monthly" : "Contact sales"}
                  </div>
                  <Button size="sm" variant="subtle" onClick={openPortal} style={{ marginTop: 10 }}>Manage Plan</Button>
                </div>
              </div>

              {(plan.features || []).length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-4" style={{ gap: 16, marginTop: 20, paddingTop: 20, borderTop: "1px solid rgba(255,255,255,0.12)" }}>
                  {plan.features.slice(0, 4).map((f) => (
                    <div key={f} style={{ display: "flex", alignItems: "flex-start", gap: 7, minWidth: 0 }}>
                      <CheckCircle2 size={14} color="#34D399" style={{ flexShrink: 0, marginTop: 1 }} />
                      <span style={{ fontSize: 12, color: "rgba(255,255,255,0.85)", lineHeight: 1.4, minWidth: 0 }}>{f}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", padding: "0 24px 20px" }}>
              <Link to="/pricing"><Button as="span" size="sm">Upgrade Plan</Button></Link>
              <Link to="/pricing#credit-packs"><Button as="span" size="sm" variant="outline">Buy Credits</Button></Link>
              {subscription && !cancelAtPeriodEnd && (
                <Button size="sm" variant="ghost" onClick={() => setConfirmCancelOpen(true)} loading={cancelling}>Cancel Subscription</Button>
              )}
              {subscription && (
                <Button size="sm" variant="ghost" onClick={openPortal}>Manage Billing</Button>
              )}
            </div>
          </Card>

          {/* Plan Details + Usage Overview */}
          <div className="grid grid-cols-1 lg:grid-cols-2" style={{ gap: 20 }}>
            <Card padding="xl" data-testid="billing-plan-details">
              <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", marginBottom: 12 }}>Plan Details</div>
              <Row label="Plan" value={planLabel} />
              <Row label="Billing Cycle" value={subscription?.billing_period === "annual" ? "Annual" : "Monthly"} />
              {renewsDate && <Row label="Next Billing Date" value={renewsDate} />}
              {seats != null && <Row label="Team Seats" value={seats === -1 ? "Unlimited" : seats} />}
              <Row label="AI Credits" value={`${(plan.credits_per_month ?? 0) === -1 ? "Unlimited" : (plan.credits_per_month ?? 0).toLocaleString()} / month`} />
              {storageGb != null && <Row label="Storage" value={storageGb === -1 ? "Unlimited" : storageGb >= 1024 ? `${(storageGb / 1024).toFixed(1)} TB` : `${storageGb} GB`} />}
              <Link to="/pricing" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12.5, fontWeight: 600, color: NAVY, textDecoration: "none", marginTop: 14 }}>
                View full plan details <ArrowRight size={12} />
              </Link>
            </Card>

            <Card padding="xl" data-testid="billing-usage-overview">
              <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", marginBottom: 14 }}>Usage Overview</div>
              <ProgressBar
                label="AI Credits (this period)"
                value={monthlyUsed}
                max={monthlyAllowance || 1}
                valueLabel={`${monthlyUsed.toLocaleString()} / ${monthlyAllowance.toLocaleString()}`}
                colorByValue
              />
              <div style={{ marginTop: 16, display: "flex", gap: 24 }}>
                <div>
                  <div style={{ fontFamily: "Georgia, serif", fontSize: 20, fontWeight: 700 }}>{(credits.pack_balance ?? 0).toLocaleString()}</div>
                  <div style={{ ...TYPE.meta, marginTop: 2 }}>Pack Credits (never expire)</div>
                </div>
                <div>
                  <div style={{ fontFamily: "Georgia, serif", fontSize: 20, fontWeight: 700, color: EMERALD }}>{totalBalance.toLocaleString()}</div>
                  <div style={{ ...TYPE.meta, marginTop: 2 }}>Total Available</div>
                </div>
              </div>
              <button onClick={openPortal} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12.5, fontWeight: 600, color: NAVY, background: "none", border: "none", cursor: "pointer", padding: 0, marginTop: 16 }}>
                View detailed usage <ArrowRight size={12} />
              </button>
            </Card>
          </div>

          {/* Recent Invoices */}
          <Card padding="none" data-testid="billing-history">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 24px", borderBottom: `1px solid ${BRD}` }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a" }}>Recent Invoices</div>
              <button onClick={openPortal} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12.5, fontWeight: 600, color: NAVY, background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                View all invoices <ArrowRight size={12} />
              </button>
            </div>
            {invoiceRows.length === 0 ? (
              <div style={{ padding: 24 }}><EmptyState icon={<CreditCard />} title="No billing activity yet." size="sm" /></div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", fontSize: 12.5, borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ textAlign: "left", borderBottom: `1px solid ${BRD}` }}>
                      <th style={{ padding: "10px 24px", fontWeight: 600, color: TEXT_MUTED }}>Date</th>
                      <th style={{ padding: "10px 12px", fontWeight: 600, color: TEXT_MUTED }}>Description</th>
                      <th style={{ padding: "10px 12px", fontWeight: 600, color: TEXT_MUTED, textAlign: "right" }}>Amount</th>
                      <th style={{ padding: "10px 24px", fontWeight: 600, color: TEXT_MUTED }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoiceRows.slice(0, 8).map((h) => (
                      <tr key={h.id} style={{ borderBottom: `1px solid ${BRD}` }} data-testid={`history-row-${h.id}`}>
                        <td style={{ padding: "12px 24px", color: TEXT_SECONDARY, whiteSpace: "nowrap" }}>{(h.created_at || "").slice(0, 10)}</td>
                        <td style={{ padding: "12px 12px", color: TEXT_SECONDARY }}>{h.description || (h.kind || "").replace(/_/g, " ")}</td>
                        <td style={{ padding: "12px 12px", color: "#0f172a", fontWeight: 600, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                          {h.amount_eur != null ? `€${Number(h.amount_eur).toFixed(2)}` : "—"}
                        </td>
                        <td style={{ padding: "12px 24px" }}>
                          <Badge variant={h.status === "paid" || h.status === "succeeded" ? "success" : h.status === "failed" ? "danger" : "neutral"} size="sm">
                            {h.status || "—"}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* Credit Pack Purchases */}
          <Card padding="none" data-testid="credit-purchases">
            <div style={{ padding: "18px 24px", borderBottom: `1px solid ${BRD}` }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a" }}>Credit Pack Purchases</div>
            </div>
            {purchases.length === 0 ? (
              <div style={{ padding: 24 }}><EmptyState icon={<Sparkles />} title="No credit pack purchases yet." size="sm" /></div>
            ) : (
              <div>
                {purchases.map((p, i) => (
                  <div key={p.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 24px", borderTop: i > 0 ? `1px solid ${BRD}` : "none" }} data-testid={`purchase-row-${p.id}`}>
                    <div style={{ fontSize: 12.5, color: TEXT_SECONDARY }}>
                      <span style={{ fontWeight: 700, color: "#0f172a" }}>+{p.credits.toLocaleString()} credits</span> · {p.pack_code}
                    </div>
                    <div style={{ fontSize: 11.5, color: TEXT_MUTED }}>{(p.created_at || "").slice(0, 10)}</div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Subscription History */}
          <Card padding="none" data-testid="sub-history">
            <div style={{ padding: "18px 24px", borderBottom: `1px solid ${BRD}` }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a" }}>Subscription History</div>
            </div>
            {subHistory.length === 0 ? (
              <div style={{ padding: 24 }}><EmptyState icon={<ArrowRight />} title="No plan changes yet." size="sm" /></div>
            ) : (
              <div>
                {subHistory.map((s, i) => (
                  <div key={s.id} style={{ padding: "12px 24px", fontSize: 12.5, color: TEXT_SECONDARY, borderTop: i > 0 ? `1px solid ${BRD}` : "none" }} data-testid={`sub-history-row-${s.id}`}>
                    <span style={{ fontFamily: "monospace", fontSize: 11, color: TEXT_MUTED, marginRight: 10 }}>{(s.created_at || "").slice(0, 10)}</span>
                    {s.from_plan || "—"} <ArrowRight size={11} style={{ display: "inline", margin: "0 4px", color: TEXT_MUTED }} /> {s.to_plan || "—"}
                    <span style={{ marginLeft: 10, color: TEXT_MUTED }}>{s.reason}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* ── Right rail ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card padding="lg">
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Credits Remaining</div>
            {renewsDate && <div style={{ ...TYPE.caption, marginTop: 2 }}>Resets {renewsDate}</div>}
            <div style={{ marginTop: 16 }}>
              <CreditsRing total={totalBalance || monthlyAllowance || 1} used={monthlyUsed} />
            </div>
            <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 12 }}>
                <span style={{ display: "flex", alignItems: "center", gap: 6, color: TEXT_SECONDARY }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#7C3AED" }} /> Used
                </span>
                <span style={{ fontWeight: 600 }}>{monthlyUsed.toLocaleString()}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 12 }}>
                <span style={{ display: "flex", alignItems: "center", gap: 6, color: TEXT_SECONDARY }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#EDE9FE" }} /> Remaining
                </span>
                <span style={{ fontWeight: 600 }}>{totalBalance.toLocaleString()}</span>
              </div>
            </div>
            <button onClick={openPortal} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600, color: NAVY, background: "none", border: "none", cursor: "pointer", padding: 0, marginTop: 14 }}>
              View usage analytics <ArrowRight size={11} />
            </button>
          </Card>

          <Card padding="lg">
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", marginBottom: 10 }}>Payment Method</div>
            {sub.stripe_configured ? (
              <>
                <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: 0, lineHeight: 1.5 }}>
                  Managed securely through Stripe. View, update, or replace your card in the billing portal.
                </p>
                <Button size="sm" variant="ghost" onClick={openPortal} style={{ width: "100%", marginTop: 12 }}>
                  Manage payment methods <ArrowRight size={12} />
                </Button>
              </>
            ) : (
              <p style={{ fontSize: 12, color: TEXT_MUTED, margin: 0, lineHeight: 1.5 }}>
                Billing isn't configured yet for this workspace.
              </p>
            )}
          </Card>

          <Card padding="lg">
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
              <Zap size={13} color={NAVY} />
              <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Need More Credits?</div>
            </div>
            <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: 0, lineHeight: 1.5 }}>
              Add extra AI credits to continue uninterrupted research.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}>
              {["Instant activation", "Pay only for what you use", "No long-term commitment"].map((t) => (
                <div key={t} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11.5, color: TEXT_SECONDARY }}>
                  <CheckCircle2 size={12} color={EMERALD} /> {t}
                </div>
              ))}
            </div>
            <Link to="/pricing#credit-packs">
              <Button as="span" size="sm" style={{ width: "100%", marginTop: 14 }}>Buy Additional Credits</Button>
            </Link>
          </Card>

          <Card padding="lg">
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
              <Headphones size={13} color={NAVY} />
              <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Billing Help</div>
            </div>
            <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: 0, lineHeight: 1.5 }}>
              Questions about billing or invoices? We're here to help.
            </p>
            <Link to="/help-center" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600, color: NAVY, textDecoration: "none", marginTop: 12 }}>
              Visit Help Center <ArrowRight size={11} />
            </Link>
          </Card>
        </div>
      </div>

      <Dialog
        open={confirmCancelOpen}
        onClose={() => setConfirmCancelOpen(false)}
        onConfirm={cancel}
        title="Cancel subscription?"
        description="You'll keep access until the end of the current billing period, then your plan will not renew."
        confirmLabel="Cancel Subscription"
        cancelLabel="Keep Subscription"
        variant="destructive"
        loading={cancelling}
      />
    </SettingsLayout>
  );
}

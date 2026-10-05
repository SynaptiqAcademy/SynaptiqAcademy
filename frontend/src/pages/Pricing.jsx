/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { trackMarketingEvent as track } from "../lib/marketingAnalytics";
import { setPageSeo } from "../lib/seo";
import { trackMonetizationEvent } from "../lib/analytics";
import {
  Check, Minus, Sparkles, ArrowRight,
  Shield, Globe, Zap, Lock, CheckCircle2, ChevronDown,
  CreditCard, Database, GraduationCap, Building2, FlaskConical, Star,
} from "lucide-react";
import { TID } from "../lib/testIds";
import { toast } from "sonner";
import { EMERALD, NAVY } from "@/lib/tokens";

// Shown for ANY checkout failure — deliberately never repeats the backend's
// raw error detail, which names the billing vendor and internal config
// state (not customer-appropriate). Paid checkout is genuinely not live
// yet in production (see Phase 9A Part 2 report) — this is an honest,
// calm statement of that, not a generic error.
const BILLING_NOT_READY_MESSAGE =
  "Paid plans aren't open for purchase yet — we're finishing billing setup. " +
  "You're welcome to keep using the Free plan in the meantime, or reach out and we'll let you know when it's ready.";

/* ─── Plans, packs, credit costs and the comparison matrix all come from the
   API (backend/plans_catalogue.py) — there is no second copy here that could
   drift. Rows of the matrix are grouped by their position in the backend
   FEATURE_MATRIX, which is ordered usage → identity → Pro → Pro Advanced. ── */

const COMPARISON_GROUPS = [
  { label: "Usage", from: 0, to: 4 },
  { label: "Academic identity (every plan)", from: 4, to: 7 },
  { label: "Research, collaboration & AI", from: 7, to: 17 },
  { label: "Advanced intelligence", from: 17, to: 24 },
  { label: "Support", from: 24, to: 25 },
];

const TRUST_ITEMS = [
  { icon: Lock,       label: "Your research stays yours",   body: "Manuscripts, datasets, and intellectual work remain your property. Synaptiq provides tools — not ownership." },
  { icon: Globe,      label: "ORCID Integration",           body: "Connect your ORCID iD and your publication record syncs automatically via the public ORCID API." },
  { icon: Shield,     label: "Encrypted at rest and in transit", body: "All data protected via TLS 1.2+ in transit and encrypted at rest. Credentials use bcrypt hashing." },
  { icon: CheckCircle2, label: "GDPR aligned",              body: "Designed for European data protection standards. We never sell your data or use it to train AI without consent." },
  { icon: Zap,        label: "Transparent credit pricing",  body: "Every AI action has a documented, fixed credit cost. No surprise charges. No vague usage metering." },
  { icon: CreditCard, label: "Cancel any time",             body: "No lock-in. Cancel from Settings and your access continues until the end of your billing period." },
];

const FAQ_ITEMS = [
  {
    q: "What does the Free plan include?",
    a: "Free is your academic identity: a profile and public research page, ORCID integration and publication import, and being discoverable by Pro researchers. Pro researchers can invite you to collaborate; responding, messaging, projects, workspaces, discovery and AI tools are part of Pro.",
  },
  {
    q: "How do AI Credits work?",
    a: "Each AI action has a fixed, published credit cost that's shown before you run it — the full list is on this page. Pro includes 200 AI credits a month and Pro Advanced 750. Credits are only charged when a request completes; failed requests are refunded automatically.",
  },
  {
    q: "Do unused credits roll over?",
    a: "Monthly credits reset at each successful renewal and don't roll over. Credits from purchased credit packs never expire and are used after your monthly credits.",
  },
  {
    q: "Can I buy extra credits?",
    a: "Yes — on Pro and Pro Advanced you can buy packs of 100, 300 or 750 AI credits. Credits are added as soon as the payment is confirmed. Purchased credits stay on your account if you change plan; they can be used whenever you're on a paid plan.",
  },
  {
    q: "What does Early Access mean for Pro?",
    a: "Pro is €9.99/month during Early Access. The regular price will be €14.99/month; we'll tell you before any change applies to your subscription.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. Paid plans are month-to-month. Cancel from your account settings and you keep access until the end of the current billing period, then your account returns to Free. Nothing is deleted: anything above the Free plan becomes read-only, and purchased credits are kept.",
  },
  {
    q: "Can I upgrade or downgrade?",
    a: "Yes. Upgrading from Pro to Pro Advanced applies immediately (prorated) and tops your monthly credits up to the Pro Advanced allowance for the current month. Downgrading keeps all your data; workspaces above the new plan's limit become read-only until you upgrade again or make room.",
  },
  {
    q: "How secure is Synaptiq?",
    a: "All data is encrypted in transit (TLS 1.2+) and at rest. Authentication uses httpOnly cookies, bcrypt password hashing, and optional 2FA. We are GDPR-aligned and never sell your data.",
  },
  {
    q: "Can universities negotiate pricing?",
    a: "Institutional pricing is always set per agreement — there is no fixed public price. We work with research offices, departments and consortia on seat counts and needs. Contact our team.",
  },
  {
    q: "How is billing calculated?",
    a: "Paid plans are billed monthly, on the same date each month. All prices are in EUR, excluding VAT where applicable. Card payments are handled by our payment processor — Synaptiq never stores card details. Institutional agreements are invoiced.",
  },
];

/* ─── Helpers ─────────────────────────────────────────────────────────────── */

const PLAN_ORDER = { free: 0, researcher: 1, pro_researcher: 2, institution: 3 };

/* ─── Component ──────────────────────────────────────────────────────────── */

export default function Pricing() {
  useEffect(() => {
    const restore = setPageSeo({
      title: "Pricing — Synaptiq",
      description: "Free to start. Pro for active individual research and collaboration. Institutional for organizations — contact sales.",
      path: "/pricing",
    });
    track("pricing_viewed");
    trackMonetizationEvent("pricing_viewed");
    return restore;
  }, []);
  const [plans,    setPlans]    = useState([]);
  const [packs,    setPacks]    = useState([]);
  const [usageCat, setUsageCat] = useState([]);
  // The primary decision (§8/§32 of the Phase 9A commercial redesign):
  // Pro is an individual product, Institutional is an organization product.
  // This is deliberately the FIRST choice on the page, not a fourth card in
  // the same row as Free/Pro.
  const [audience, setAudience] = useState("individual"); // "individual" | "organization"
  const [matrix,   setMatrix]   = useState({ columns: [], rows: [] });
  // Annual billing isn't offered until the owner approves it and annual Stripe
  // prices exist (§6) — constant, not state, so nothing can switch it on.
  const annual = false;
  const [busy,     setBusy]     = useState("");
  const [packBusy, setPackBusy] = useState("");
  const [openFaq,  setOpenFaq]  = useState(null);
  const { user } = useAuth();
  const navigate = useNavigate();

  // Plans/packs/costs come only from the API (no stale static copy). A failed
  // load shows an explicit retry state instead of empty sections.
  const [loadState, setLoadState] = useState("loading"); // loading | ready | error
  const loadCatalogue = () => {
    setLoadState("loading");
    Promise.all([
      api.get("/billing/plans"),
      api.get("/billing/credit-packs"),
      api.get("/billing/credit-usage-catalogue"),
      api.get("/billing/feature-matrix"),
    ]).then(([pl, pk, uc, fm]) => {
      setPlans(pl.data || []);
      setPacks(pk.data || []);
      setUsageCat(uc.data?.display || []);
      setMatrix(fm.data || { columns: [], rows: [] });
      setLoadState("ready");
    }).catch(() => setLoadState("error"));
  };
  useEffect(() => { loadCatalogue(); }, []);

  const startCheckout = async (code) => {
    track("plan_selected", { plan_code: code, billing_period: "monthly" });
    if (code !== "free" && code !== "institution") trackMonetizationEvent("upgrade_clicked", { plan_code: code, source: "pricing" });
    if (!user) { navigate("/register"); return; }
    if (code === "free") { navigate("/profile"); return; }
    if (code === "institution") { navigate("/contact?topic=institution"); return; }
    setBusy(code);
    track("checkout_started", { plan_code: code, billing_period: "monthly" });
    trackMonetizationEvent("checkout_started", { plan_code: code });
    try {
      // Only the public plan key is sent; the server maps it to its own
      // configured Stripe price and builds the redirect URLs itself.
      const planKey = (plans.find((p) => p.code === code) || {}).key || code;
      const res = await api.post("/billing/checkout-session", { plan: planKey, billing_period: "monthly" });
      if (res.data.url) { window.location.href = res.data.url; return; }
      if (res.data.changed) { toast.success(res.data.message || "Your plan change is being confirmed."); return; }
      toast.info(BILLING_NOT_READY_MESSAGE);
    } catch (e) {
      // Never surface the backend's raw error detail here — it names the
      // billing vendor and internal config state, which isn't customer-
      // appropriate (§3). A 402/403/etc from a signed-in, entitled request
      // still deserves a generic apology, not implementation detail.
      toast.info(BILLING_NOT_READY_MESSAGE);
    } finally { setBusy(""); }
  };

  const buyPack = async (pack) => {
    if (!user) { navigate("/register"); return; }
    if ((user.plan_code || "free") === "free") {
      toast.info("Extra AI credits are available on Pro and Pro Advanced.");
      return;
    }
    trackMonetizationEvent("credit_pack_checkout_started", { pack_code: pack.code, source: "pricing" });
    setPackBusy(pack.code);
    try {
      const res = await api.post("/billing/credit-pack-checkout", { pack: pack.key || pack.code });
      if (res.data.url) { window.location.href = res.data.url; return; }
      toast.info(BILLING_NOT_READY_MESSAGE);
    } catch (e) {
      if (e?.response?.status === 402) return; // upgrade modal explains it
      toast.info(BILLING_NOT_READY_MESSAGE);
    } finally { setPackBusy(""); }
  };

  const renderCell = (v) => {
    if (v === true)  return <span style={{ display: "flex", justifyContent: "center" }}><Check size={15} strokeWidth={2.5} style={{ color: "#0F2847" }} /></span>;
    if (v === false) return <span style={{ display: "flex", justifyContent: "center" }}><Minus size={14} strokeWidth={2} style={{ color: "#cbd5e1" }} /></span>;
    return <span style={{ fontSize: "0.8rem", color: "#334155", display: "block", textAlign: "center", fontWeight: 500 }}>{v}</span>;
  };

  const annualSavings = (plan) => {
    if (!annual || plan.price_eur_monthly === 0) return null;
    const monthly = plan.price_eur_monthly * 12;
    const ann     = plan.price_eur_annual  * 12;
    return Math.round(monthly - ann);
  };

  const VISIBLE_CODES = audience === "organization"
    ? new Set(["institution"])
    : new Set(["free", "researcher", "pro_researcher"]);
  const sortedPlans = [...plans]
    .filter((p) => VISIBLE_CODES.has(p.code))
    .sort((a, b) => (PLAN_ORDER[a.code] ?? 9) - (PLAN_ORDER[b.code] ?? 9));
  const institutionPlan = plans.find((p) => p.code === "institution");

  // Map visible column codes to their indices in matrix.columns (handles enterprise injection)
  const visibleMatrixCols = matrix.columns.reduce((acc, c, i) => {
    if (VISIBLE_CODES.has(c)) acc.push({ code: c, index: i });
    return acc;
  }, []);

  return (
    <MarketingLayout>

      {/* ══════════════════════════════════════════════════════════════════════
          HERO — white, large heading, inline toggle
      ══════════════════════════════════════════════════════════════════════ */}
      <section
        data-testid={TID.pricingHero}
        className="bg-white"
        style={{ borderBottom: "1px solid #f1f5f9", paddingTop: 80, paddingBottom: 72 }}
      >
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">

          <h1 style={{
            fontSize: "clamp(2.8rem, 6vw, 5rem)",
            fontWeight: 900, lineHeight: 1.03, letterSpacing: "-0.04em",
            color: "#0a0f1a", maxWidth: 780, textWrap: "balance",
          }}>
            Plans built for modern research.
          </h1>

          <p style={{ fontSize: "1.05rem", color: "#64748b", lineHeight: 1.7, marginTop: 20, maxWidth: 540 }}>
            {audience === "organization"
              ? "For universities, research institutes and organizations."
              : "For individual research, collaboration and teaching."}
          </p>

          {/* ── Primary decision: individual vs organization (§8/§32) ── */}
          <div style={{ marginTop: 32, display: "grid", gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 12, maxWidth: 560 }} className="grid-cols-1 sm:grid-cols-2">
            {[
              { key: "individual",   title: "For myself",        desc: "Individual research, collaboration and teaching." },
              { key: "organization", title: "For an organization", desc: "Universities, research institutes and organizations." },
            ].map(({ key, title, desc }) => (
              <button
                key={key}
                onClick={() => setAudience(key)}
                data-testid={`pricing-audience-${key}`}
                style={{
                  textAlign: "left", padding: "16px 18px", borderRadius: 12, cursor: "pointer",
                  border: audience === key ? "2px solid #0F2847" : "1px solid #e2e8f0",
                  background: audience === key ? "#0F2847" : "#fff",
                  transition: "all 150ms ease",
                }}
              >
                <div style={{ fontSize: "0.9rem", fontWeight: 800, color: audience === key ? "#fff" : "#0a0f1a", marginBottom: 4 }}>{title}</div>
                <div style={{ fontSize: "0.75rem", color: audience === key ? "rgba(255,255,255,0.6)" : "#94a3b8", lineHeight: 1.5 }}>{desc}</div>
              </button>
            ))}
          </div>

          {/* Trust row — individual plans only. (The monthly/annual toggle was removed: no annual
              Stripe price exists and annual billing isn't approved yet, so showing it implied a
              purchasable option that doesn't exist — §6. Annual prices stay in plans_catalogue.py.) */}
          {audience === "individual" && (
          <>
          {/* Trust micro-row */}
          <div className="flex flex-wrap items-center gap-6 mt-8">
            {["Cancel any time", "No credit card required for Free", "Research data owned by you"].map((t) => (
              <div key={t} className="flex items-center gap-1.5">
                <CheckCircle2 size={13} strokeWidth={2} style={{ color: "#10b981" }} />
                <span style={{ fontSize: "0.78rem", color: "#64748b", fontWeight: 500 }}>{t}</span>
              </div>
            ))}
          </div>
          </>
          )}

        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          PLAN CARDS
      ══════════════════════════════════════════════════════════════════════ */}
      <section
        data-testid={TID.pricingPlans}
        className="bg-white"
        style={{ paddingTop: 64, paddingBottom: 88 }}
      >
        <div className={audience === "organization" ? "max-w-[560px] mx-auto px-6 lg:px-10" : "max-w-[1280px] mx-auto px-6 lg:px-10"}>
          {loadState !== "ready" && (
            <div data-testid="pricing-load-state" role={loadState === "error" ? "alert" : "status"}
              style={{ textAlign: "center", padding: "48px 16px", border: "1px solid #e2e8f0", borderRadius: 16 }}>
              {loadState === "loading" ? (
                <span style={{ fontSize: "0.9rem", color: "#64748b" }}>Loading plans…</span>
              ) : (
                <>
                  <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0a0f1a" }}>Plans couldn't be loaded right now.</div>
                  <button onClick={loadCatalogue} style={{ marginTop: 12, padding: "9px 18px", borderRadius: 8, border: "1px solid #0F2847", color: "#0F2847", background: "#fff", fontWeight: 700, cursor: "pointer" }}>
                    Try again
                  </button>
                </>
              )}
            </div>
          )}
          <div
            style={{
              display: "grid",
              // Columns come from the responsive classes below (1 on phones,
              // 3 from md) — an inline repeat(3,1fr) overrode them on mobile.
              ...(audience === "organization" ? { gridTemplateColumns: "1fr" } : {}),
              gap: 20, alignItems: "stretch",
            }}
            className={audience === "organization" ? "" : "grid-cols-1 md:grid-cols-3"}
          >
            {sortedPlans.map((p) => {
              const price    = annual ? p.price_eur_annual : p.price_eur_monthly;
              const isFree   = p.code === "free";
              const isPopular = !!p.recommended;
              const isInst   = p.code === "institution";
              const savings  = annualSavings(p);
              const highlights = p.features || [];

              return (
                <div
                  key={p.code}
                  data-testid={TID.pricingPlanCard(p.code)}
                  style={{
                    borderRadius: 16,
                    padding: "32px 28px",
                    border: isPopular ? "2px solid #0F2847" : "1px solid #e2e8f0",
                    background: isPopular ? "#0F2847" : "#fff",
                    boxShadow: isPopular
                      ? "0 20px 64px rgba(15,40,71,0.24), 0 4px 20px rgba(15,40,71,0.1)"
                      : "0 1px 6px rgba(15,40,71,0.04)",
                    position: "relative",
                    display: "flex", flexDirection: "column",
                  }}
                >
                  {/* Badge */}
                  {isPopular && (
                    <div style={{
                      position: "absolute", top: -13, left: "50%", transform: "translateX(-50%)",
                      background: "#fff", color: "#0F2847",
                      fontSize: "0.6rem", fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase",
                      padding: "4px 14px", borderRadius: 999,
                      border: "1px solid rgba(15,40,71,0.15)",
                      boxShadow: "0 2px 8px rgba(15,40,71,0.1)",
                      whiteSpace: "nowrap",
                    }}>
                      Recommended{p.badge ? ` · ${p.badge}` : ""}
                    </div>
                  )}

                  {/* Plan tagline */}
                  <div style={{
                    fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase",
                    color: isPopular ? "rgba(255,255,255,0.5)" : "#94a3b8",
                    marginBottom: 12,
                  }}>
                    {p.tagline}
                  </div>

                  {/* Plan name */}
                  <div style={{
                    fontSize: "1.4rem", fontWeight: 800, letterSpacing: "-0.025em",
                    color: isPopular ? "#fff" : "#0a0f1a",
                    marginBottom: 24,
                  }}>
                    {p.name}
                  </div>

                  {/* Price block — Institutional shows no public price (§37):
                      organization-level billing doesn't exist yet, so a
                      number here would imply a self-service purchase that
                      isn't real. The historical reference value stays in
                      plans_catalogue.py for internal/sales use, just not
                      rendered publicly. */}
                  <div style={{ marginBottom: 8 }}>
                    {isInst ? (
                      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                        <span style={{ fontSize: "2rem", fontWeight: 900, lineHeight: 1, letterSpacing: "-0.03em", color: "#0a0f1a" }}>
                          Custom
                        </span>
                      </div>
                    ) : (
                      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                        <span style={{
                          fontSize: "3rem", fontWeight: 900, lineHeight: 1, letterSpacing: "-0.045em",
                          color: isPopular ? "#fff" : "#0a0f1a",
                        }}>
                          €{price % 1 === 0 ? price : price.toFixed(2).replace(".00", "")}
                        </span>
                        <span style={{ fontSize: "0.78rem", color: isPopular ? "rgba(255,255,255,0.45)" : "#94a3b8", fontWeight: 500 }}>
                          {isFree ? (p.price_label || "Forever") : "/ month"}
                        </span>
                      </div>
                    )}

                    {p.future_price_eur_monthly && !isInst && (
                      <div data-testid={`pricing-future-price-${p.code}`} style={{ fontSize: "0.72rem", fontWeight: 600, marginTop: 6,
                        color: isPopular ? "rgba(255,255,255,0.65)" : "#64748b" }}>
                        Early Access · Future price €{Number(p.future_price_eur_monthly).toFixed(2)}/month
                      </div>
                    )}

                    {savings && (
                      <div style={{ fontSize: "0.72rem", fontWeight: 600, marginTop: 4,
                        color: isPopular ? "rgba(255,255,255,0.6)" : "#059669" }}>
                        Save €{savings} per year
                      </div>
                    )}

                    
                  </div>

                  {/* Credits chip (Free has no AI credits — no chip) */}
                  {!isFree && <div style={{
                    display: "inline-flex", alignItems: "center", gap: 6,
                    background: isPopular ? "rgba(255,255,255,0.1)" : "#f1f5f9",
                    borderRadius: 7, padding: "7px 12px", marginTop: 16, marginBottom: 24, alignSelf: "flex-start",
                  }}>
                    <Sparkles size={12} strokeWidth={2} style={{ color: isPopular ? "rgba(255,255,255,0.7)" : "#0F2847" }} />
                    <span style={{ fontSize: "0.75rem", fontWeight: 700, color: isPopular ? "rgba(255,255,255,0.85)" : "#0F2847" }}>
                      {isInst ? "AI credits set per agreement"
                        : p.credits_per_month > 0 ? `${p.credits_per_month.toLocaleString()} AI Credits / month`
                        : "No AI credits"}
                    </span>
                  </div>}

                  {/* Divider */}
                  <div style={{ height: 1, background: isPopular ? "rgba(255,255,255,0.12)" : "#f1f5f9", marginBottom: 22 }} />

                  {/* Feature list */}
                  <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 11 }}>
                    {highlights.map((f) => (
                      <div key={f} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                        <div style={{
                          width: 18, height: 18, borderRadius: "50%", flexShrink: 0, marginTop: 1,
                          background: isPopular ? "rgba(255,255,255,0.12)" : "#f1f5f9",
                          display: "flex", alignItems: "center", justifyContent: "center",
                        }}>
                          <Check size={9} strokeWidth={3} style={{ color: isPopular ? "rgba(255,255,255,0.9)" : "#0F2847" }} />
                        </div>
                        <span style={{ fontSize: "0.8rem", color: isPopular ? "rgba(255,255,255,0.72)" : "#475569", lineHeight: 1.55 }}>
                          {f}
                        </span>
                      </div>
                    ))}
                  </div>

                  {/* CTA */}
                  <button
                    data-testid={TID.pricingChooseBtn(p.code)}
                    onClick={() => startCheckout(p.code)}
                    disabled={busy === p.code}
                    style={{
                      marginTop: 28, width: "100%",
                      padding: "13px 20px", borderRadius: 9,
                      fontSize: "0.88rem", fontWeight: 700,
                      cursor: busy === p.code ? "not-allowed" : "pointer",
                      opacity: busy === p.code ? 0.6 : 1,
                      border: isFree ? "1px solid #e2e8f0" : "none",
                      background: isPopular ? "#fff"
                                : isFree    ? "#fff"
                                :             "#0F2847",
                      color:      isPopular ? "#0F2847"
                                : isFree    ? "#0a0f1a"
                                :             "#fff",
                      transition: "opacity 150ms, transform 100ms",
                    }}
                    onMouseEnter={(e) => { if (busy !== p.code) e.currentTarget.style.opacity = "0.82"; }}
                    onMouseLeave={(e) => { if (busy !== p.code) e.currentTarget.style.opacity = "1"; }}
                  >
                    {busy === p.code ? "Starting…" : (p.cta || `Choose ${p.name}`)}
                  </button>

                  {isFree && (
                    <p style={{ fontSize: "0.67rem", color: isPopular ? "rgba(255,255,255,0.35)" : "#94a3b8", textAlign: "center", marginTop: 10 }}>
                      No credit card required
                    </p>
                  )}
                  {isInst && (
                    <p style={{ fontSize: "0.67rem", color: "#94a3b8", textAlign: "center", marginTop: 10 }}>
                      Custom seat counts available
                    </p>
                  )}
                </div>
              );
            })}
          </div>

          <p style={{ textAlign: "center", marginTop: 24, fontSize: "0.75rem", color: "#94a3b8" }}>
            {audience === "organization"
              ? "Institutional pricing is negotiated with our team based on your organization's seat count and needs."
              : "Only AI-assisted actions use credits; networking, messaging and collaboration never do. Monthly credits reset at each renewal. All prices in EUR, excluding VAT where applicable."}
          </p>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          PLANS AND FEATURES — sticky comparison table (Notion-style)
          Individual-only: comparing Free/Pro/Pro Advanced. The
          Institutional capability list gets its own section below instead
          (§12 — organization value isn't "Pro + a checkbox").
      ══════════════════════════════════════════════════════════════════════ */}
      {audience === "individual" && (
      <section
        data-testid="comparison-matrix"
        style={{ background: "#fff", borderTop: "1px solid #f1f5f9" }}
      >
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10" style={{ paddingTop: 80, paddingBottom: 100 }}>

          <h2 style={{
            fontSize: "clamp(2rem, 4vw, 3.2rem)", fontWeight: 900,
            letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.05,
            marginBottom: 56,
          }}>
            Plans and features
          </h2>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 680 }}>
              {/* ── Sticky header ── */}
              <thead>
                <tr style={{ position: "sticky", top: 64, zIndex: 20, background: "#fff", borderBottom: "1px solid #e2e8f0" }}>
                  <th style={{
                    textAlign: "left", padding: "20px 16px 20px 0",
                    width: "32%", verticalAlign: "bottom",
                    position: "sticky", left: 0, background: "#fff", zIndex: 21,
                    borderBottom: "1px solid #e2e8f0",
                  }}>
                    <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "#94a3b8", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                      Feature
                    </span>
                  </th>
                  {matrix.columns.filter((c) => VISIBLE_CODES.has(c)).map((c) => {
                    const plan     = sortedPlans.find((p) => p.code === c) || plans.find((p) => p.code === c);
                    const isPopular = !!plan?.recommended;
                    const price    = plan ? (annual ? plan.price_eur_annual : plan.price_eur_monthly) : 0;
                    const isFree   = c === "free";
                    const isInst   = c === "institution";
                    return (
                      <th key={c} style={{
                        textAlign: "center", padding: "16px 12px 20px",
                        verticalAlign: "bottom", width: "17%",
                        borderBottom: isPopular ? "2px solid #0F2847" : "1px solid #e2e8f0",
                        background: isPopular ? "rgba(15,40,71,0.025)" : "transparent",
                      }}>
                        <div style={{ fontSize: "0.7rem", fontWeight: 700, color: isPopular ? "#0F2847" : "#64748b", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>
                          {isPopular && <span style={{ display: "block", fontSize: "0.58rem", color: "#0F2847", marginBottom: 4 }}>RECOMMENDED</span>}
                          {plan?.name ?? c}
                        </div>
                        <div style={{ fontSize: "1.15rem", fontWeight: 800, color: "#0a0f1a", letterSpacing: "-0.025em", lineHeight: 1 }}>
                          {isInst ? "Custom" : `€${price % 1 === 0 ? price : price.toFixed(2)}`}
                        </div>
                        <div style={{ fontSize: "0.65rem", color: "#94a3b8", marginTop: 2 }}>
                          {isFree ? "free forever" : isInst ? "contact us" : annual ? "/ mo, annually" : "/ month"}
                        </div>
                        <button
                          onClick={() => startCheckout(c)}
                          style={{
                            marginTop: 10, padding: "7px 16px", borderRadius: 7,
                            fontSize: "0.73rem", fontWeight: 700,
                            border: isPopular ? "none" : "1px solid #e2e8f0",
                            background: isPopular ? "#0F2847" : "#fff",
                            color:      isPopular ? "#fff"    : "#0a0f1a",
                            cursor: "pointer", width: "100%",
                          }}
                        >
                          {plan?.cta || (isFree ? "Create Free Profile" : isInst ? "Contact us" : `Choose ${plan?.name}`)}
                        </button>
                      </th>
                    );
                  })}
                </tr>
              </thead>

              {/* ── Body ── */}
              <tbody>
                {COMPARISON_GROUPS.map((group) => {
                  const groupRows = matrix.rows.slice(group.from, group.to);
                  if (groupRows.length === 0) return null;
                  return (
                    <React.Fragment key={group.label}>
                      {/* Section header */}
                      <tr>
                        <td
                          colSpan={visibleMatrixCols.length + 1}
                          style={{
                            padding: "28px 0 10px",
                            borderBottom: "1px solid #e2e8f0",
                            position: "sticky", left: 0, background: "#fff",
                          }}
                        >
                          <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "#0a0f1a", letterSpacing: "-0.01em" }}>
                            {group.label}
                          </span>
                        </td>
                      </tr>

                      {groupRows.map((row, idx) => (
                        <tr
                          key={row.label}
                          style={{ borderBottom: "1px solid #f1f5f9" }}
                          onMouseEnter={(e) => e.currentTarget.style.background = "#fafbff"}
                          onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                        >
                          <td style={{
                            padding: "13px 16px 13px 0", fontSize: "0.82rem",
                            color: "#334155", fontWeight: 500,
                            position: "sticky", left: 0, background: "inherit",
                            zIndex: 5,
                          }}>
                            {row.label}
                          </td>
                          {visibleMatrixCols.map(({ code, index }) => {
                            const isPopular = !!plans.find((p) => p.code === code)?.recommended;
                            return (
                              <td key={code} style={{
                                padding: "13px 12px", textAlign: "center",
                                background: isPopular ? "rgba(15,40,71,0.018)" : "transparent",
                              }}>
                                {renderCell(row.values[index])}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </React.Fragment>
                  );
                })}

                {/* Final sticky CTA row */}
                <tr style={{ borderTop: "2px solid #e2e8f0" }}>
                  <td style={{ padding: "24px 0", position: "sticky", left: 0, background: "#fff", zIndex: 5 }} />
                  {matrix.columns.filter((c) => VISIBLE_CODES.has(c)).map((c) => {
                    const plan     = plans.find((p) => p.code === c);
                    const isPopular = !!plan?.recommended;
                    const isFree   = c === "free";
                    const isInst   = c === "institution";
                    return (
                      <td key={c} style={{
                        padding: "24px 12px", textAlign: "center",
                        background: isPopular ? "rgba(15,40,71,0.018)" : "transparent",
                      }}>
                        <button
                          onClick={() => startCheckout(c)}
                          style={{
                            padding: "9px 18px", borderRadius: 7,
                            fontSize: "0.78rem", fontWeight: 700,
                            border: isPopular ? "none" : "1px solid #e2e8f0",
                            background: isPopular ? "#0F2847" : "#fff",
                            color:      isPopular ? "#fff"    : "#0a0f1a",
                            cursor: "pointer", width: "100%",
                          }}
                        >
                          {plan?.cta || (isFree ? "Create Free Profile" : isInst ? "Contact us" : `Choose ${plan?.name}`)}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          INSTITUTIONAL CAPABILITIES — organization audience only (§12).
          Real, production functionality only — no invented capability.
      ══════════════════════════════════════════════════════════════════════ */}
      {audience === "organization" && institutionPlan && (
        <section style={{ background: "#fff", borderTop: "1px solid #f1f5f9" }}>
          <div className="max-w-[820px] mx-auto px-6 lg:px-10 py-20">
            <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "#0a0f1a", letterSpacing: "-0.02em", marginBottom: 8 }}>
              What Institutional includes
            </h2>
            <p style={{ fontSize: "0.9rem", color: "#64748b", lineHeight: 1.7, marginBottom: 28, maxWidth: 620 }}>
              Institutional is an organization product, not a bigger individual plan — it provisions
              a real institution workspace with member management, departments and organization-level
              analytics, scoped to your organization's actual membership.
            </p>
            <div className="grid sm:grid-cols-2 gap-x-8 gap-y-3">
              {institutionPlan.features.map((f) => (
                <div key={f} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                  <Check size={14} strokeWidth={2.5} style={{ color: "#0F2847", marginTop: 2, flexShrink: 0 }} />
                  <span style={{ fontSize: "0.85rem", color: "#334155", lineHeight: 1.6 }}>{f}</span>
                </div>
              ))}
            </div>
            <p style={{ fontSize: "0.78rem", color: "#94a3b8", marginTop: 28, lineHeight: 1.7 }}>
              Institution access is granted to verified members of your organization's Synaptiq
              institution — not by an individual's personal subscription. An existing Pro subscription
              doesn't grant it, and it isn't purchasable from an individual account.
            </p>
          </div>
        </section>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          RESEARCH CREDITS EXPLANATION
      ══════════════════════════════════════════════════════════════════════ */}
      <section id="credit-packs" data-testid="credit-usage-grid" style={{ background: "#f8fafc", borderTop: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-20 lg:py-24">
          <div className="grid lg:grid-cols-2 gap-16 items-start [&>*]:min-w-0">

            {/* Left: explanation */}
            <div>
              <div className="overline mb-4">AI Credits</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3vw, 2.6rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.1, marginBottom: 16 }}>
                AI usage, transparent by design.
              </h2>
              <p style={{ fontSize: "0.92rem", color: "#64748b", lineHeight: 1.75, marginBottom: 28, maxWidth: 480 }}>
                Every AI action has a fixed, published credit cost, shown before you run it. Pro includes monthly AI credits; Pro Advanced includes more. Failed requests are refunded automatically.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {[
                  { icon: Zap,          label: "Monthly credits reset at renewal",  body: "Your plan's monthly AI credits reset at each successful renewal. Unused monthly credits don't roll over." },
                  { icon: Database,     label: "Purchased credits never expire",    body: "Credit packs are used after your monthly credits and stay on your account, even if you change plan." },
                  { icon: CheckCircle2, label: "Collaboration never uses credits",  body: "Networking, messaging and collaboration requests on Pro cost zero credits." },
                  { icon: CreditCard,   label: "Top up on Pro and Pro Advanced",    body: "Extra credit packs are available on both paid plans." },
                ].map(({ icon: Icon, label, body }) => (
                  <div key={label} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                    <div style={{ width: 32, height: 32, borderRadius: 8, background: "#fff", border: "1px solid #e2e8f0", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <Icon size={14} strokeWidth={1.5} style={{ color: "#0F2847" }} />
                    </div>
                    <div>
                      <div style={{ fontSize: "0.83rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 2 }}>{label}</div>
                      <div style={{ fontSize: "0.78rem", color: "#64748b", lineHeight: 1.6 }}>{body}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: credit cost table + packs */}
            <div>
              {/* Always free */}
              {usageCat.some((r) => r.free) && <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 10, padding: "14px 18px", marginBottom: 16 }}>
                <div style={{ fontSize: "0.62rem", fontWeight: 700, color: "#059669", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>Always free</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 20px" }}>
                  {usageCat.filter((r) => r.free).map((r) => (
                    <div key={r.label} style={{ fontSize: "0.75rem", color: "#166534", fontWeight: 500, display: "flex", alignItems: "center", gap: 5 }}>
                      <Check size={11} strokeWidth={2.5} /> {r.label}
                    </div>
                  ))}
                </div>
              </div>}

              {/* AI credit costs */}
              <div style={{ border: "1px solid #e2e8f0", borderRadius: 10, overflow: "hidden" }}>
                <div style={{ background: "#f8fafc", padding: "10px 18px", borderBottom: "1px solid #e2e8f0" }}>
                  <span style={{ fontSize: "0.65rem", fontWeight: 700, color: "#64748b", letterSpacing: "0.1em", textTransform: "uppercase" }}>AI tool credit costs</span>
                </div>
                <div style={{ maxHeight: 300, overflowY: "auto" }}>
                  {usageCat.filter((r) => !r.free).map((r, i) => (
                    <div key={r.label} style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "10px 18px", borderBottom: "1px solid #f8fafc",
                      background: i % 2 === 0 ? "#fff" : "#fafbff",
                    }}>
                      <span style={{ fontSize: "0.79rem", color: "#334155" }}>{r.label}</span>
                      <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#0F2847", whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" }}>
                        {r.cost} credit{r.cost === 1 ? "" : "s"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Credit packs */}
              <div data-testid="credit-packs" style={{ marginTop: 20 }}>
                <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#94a3b8", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 12 }}>Credit packs — Pro & Pro Advanced</div>
                <div className="grid grid-cols-1 sm:grid-cols-3" style={{ gap: 10 }}>
                  {packs.map((pk) => (
                    <div key={pk.code} data-testid={`pack-card-${pk.code}`}
                      style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, padding: "16px 18px", display: "flex", flexDirection: "column", gap: 10 }}
                    >
                      <div style={{ fontSize: "1rem", fontWeight: 800, color: "#0a0f1a", letterSpacing: "-0.02em" }}>{pk.label}</div>
                      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                        <span style={{ fontSize: "1.5rem", fontWeight: 900, color: "#0a0f1a", letterSpacing: "-0.03em", lineHeight: 1 }}>€{Number(pk.price_eur).toFixed(2)}</span>
                        <span style={{ fontSize: "0.68rem", color: "#94a3b8" }}>one-time</span>
                      </div>
                      <button
                        onClick={() => buyPack(pk)}
                        disabled={packBusy === pk.code}
                        data-testid={`pack-buy-${pk.code}`}
                        style={{
                          padding: "9px 14px", borderRadius: 7,
                          fontSize: "0.78rem", fontWeight: 700,
                          border: "1.5px solid #0F2847",
                          background: "transparent", color: "#0F2847",
                          cursor: packBusy === pk.code ? "not-allowed" : "pointer",
                          opacity: packBusy === pk.code ? 0.6 : 1,
                          transition: "background 120ms, color 120ms",
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = "#0F2847"; e.currentTarget.style.color = "#fff"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#0F2847"; }}
                      >
                        {packBusy === pk.code ? "Starting…" : "Buy Credits"}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          FAQ
      ══════════════════════════════════════════════════════════════════════ */}
      <section data-testid="pricing-faq" className="bg-white" style={{ borderTop: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-20 lg:py-28">

          <h2 style={{
            fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 900,
            letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.05,
            marginBottom: 48,
          }}>
            Questions &amp; answers
          </h2>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 80px" }} className="grid-cols-1 md:grid-cols-2">
            {FAQ_ITEMS.map((item, idx) => (
              <div
                key={idx}
                data-testid={`faq-toggle-${idx}`}
                style={{
                  borderBottom: "1px solid #f1f5f9",
                  padding: "0",
                }}
              >
                <button
                  onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                  style={{
                    width: "100%", background: "none", border: "none", cursor: "pointer",
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    gap: 16, padding: "20px 0", textAlign: "left",
                  }}
                  aria-expanded={openFaq === idx}
                >
                  <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "#0a0f1a", lineHeight: 1.4 }}>{item.q}</span>
                  <div style={{
                    width: 24, height: 24, borderRadius: "50%",
                    border: "1px solid #e2e8f0", display: "flex", alignItems: "center", justifyContent: "center",
                    flexShrink: 0, transition: "transform 200ms ease",
                    transform: openFaq === idx ? "rotate(180deg)" : "rotate(0)",
                  }}>
                    <ChevronDown size={13} strokeWidth={2} style={{ color: "#64748b" }} />
                  </div>
                </button>
                <div style={{
                  maxHeight: openFaq === idx ? 300 : 0,
                  overflow: "hidden", transition: "max-height 220ms ease-out",
                }}>
                  <p style={{ padding: "0 0 20px", fontSize: "0.83rem", color: "#475569", lineHeight: 1.75 }}>
                    {item.a}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <p style={{ marginTop: 40, fontSize: "0.83rem", color: "#64748b" }}>
            Still have questions?{" "}
            <Link to="/contact" style={{ color: "#0F2847", fontWeight: 600, borderBottom: "1px solid #0F2847", paddingBottom: 1 }}>
              Contact us directly.
            </Link>
          </p>
        </div>
      </section>

    </MarketingLayout>
  );
}

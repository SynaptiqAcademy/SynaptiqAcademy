/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import {
  Check, Minus, Sparkles, ArrowRight,
  Shield, Globe, Zap, Lock, CheckCircle2, ChevronDown,
  CreditCard, Database, GraduationCap, Building2, FlaskConical, Star,
} from "lucide-react";
import { TID } from "../lib/testIds";
import { toast } from "sonner";
import { EMERALD, NAVY } from "@/lib/tokens";

/* ─── Static fallback data — mirrors plans_catalogue.py exactly ──────────── */

const STATIC_PLANS = [
  {
    code: "free", name: "Free", tagline: "Get started for free",
    price_eur_monthly: 0, price_eur_annual: 0,
    future_price_eur_monthly: null, badge: null,
    credits_per_month: 50,
    limits: { active_projects: 1, workspaces: 1, repository_gb: 0.5, team_seats: 1,
               journal_recs_per_month: 5, conference_recs_per_month: 5, grant_recs_per_month: 3 },
    features: [
      "50 Research Credits / month", "Academic Profile", "ORCID Integration",
      "Research Network Access", "1 Active Project", "1 Workspace",
      "500 MB Repository Storage", "5 Journal Recommendations / month",
      "5 Conference Recommendations / month", "3 Grant Recommendations / month",
      "Basic Profile Visibility",
    ],
    excluded: [
      "AI Research Assistant", "AI Manuscript Copilot", "Publication Tracking",
      "Advanced Analytics", "Unlimited Discovery Tools",
      "Advanced Collaboration Features", "Priority Support",
    ],
    cta: "Start Free",
  },
  {
    code: "researcher", name: "Researcher", tagline: "For active researchers & PhDs",
    price_eur_monthly: 9.99, price_eur_annual: 7.99,
    future_price_eur_monthly: 14.99, badge: "Most Popular",
    credits_per_month: 300,
    limits: { active_projects: -1, workspaces: 10, repository_gb: 100, team_seats: 1,
               journal_recs_per_month: -1, conference_recs_per_month: -1, grant_recs_per_month: -1 },
    features: [
      "300 Research Credits / month", "Unlimited Projects", "Up to 10 Workspaces",
      "Repository 100 GB", "Full Journal Discovery", "Full Conference Discovery",
      "Full Grant Discovery", "Publication Tracking", "Advanced Analytics",
      "AI Research Assistant", "AI Manuscript Copilot",
      "Teaching Hub — lesson planner, assessments, portfolio",
      "Priority Support",
    ],
    excluded: [],
    cta: "Get Started",
  },
  {
    code: "pro_researcher", name: "Pro Researcher", tagline: "For power users & senior researchers",
    price_eur_monthly: 29.99, price_eur_annual: 23.99,
    future_price_eur_monthly: null, badge: "Best Value",
    credits_per_month: 1000,
    limits: { active_projects: -1, workspaces: -1, repository_gb: 500, team_seats: 1,
               journal_recs_per_month: -1, conference_recs_per_month: -1, grant_recs_per_month: -1 },
    features: [
      "1,000 Research Credits / month", "Unlimited Projects", "Unlimited Workspaces",
      "Repository 500 GB", "Advanced AI Research Assistant", "Advanced Manuscript Copilot",
      "Collaboration Intelligence", "Research Analytics Suite", "Citation Monitoring",
      "Research Impact Dashboard",
      "AI Teaching Tools — lesson & assessment generator",
      "Priority Support",
    ],
    excluded: [],
    cta: "Get Started",
  },
  {
    code: "institution", name: "Institution", tagline: "Universities & research labs",
    price_eur_monthly: 299, price_eur_annual: 239,
    future_price_eur_monthly: null, badge: null,
    credits_per_month: 20000,
    limits: { active_projects: -1, workspaces: -1, repository_gb: 2048, team_seats: 25,
               journal_recs_per_month: -1, conference_recs_per_month: -1, grant_recs_per_month: -1 },
    features: [
      "20,000 Research Credits / month", "25 Researcher Seats", "Unlimited Projects",
      "Unlimited Workspaces", "Repository 2 TB",
      "Institutional Analytics Dashboard", "Department Management",
      "SSO / SAML Integration", "Audit Logs", "Dedicated Support",
    ],
    excluded: [],
    cta: "Contact Sales",
  },
];

const STATIC_PACKS = [
  { code: "pack_100",  credits: 100,  price_eur: 5,  label: "100 Credits"   },
  { code: "pack_250",  credits: 250,  price_eur: 10, label: "250 Credits"   },
  { code: "pack_1000", credits: 1000, price_eur: 29, label: "1,000 Credits" },
  { code: "pack_5000", credits: 5000, price_eur: 99, label: "5,000 Credits" },
];

const STATIC_USAGE = [
  { label: "AI Manuscript Review",       cost: 20, unit: "per review",     free: false },
  { label: "AI Literature Review",       cost: 20, unit: "per review",     free: false },
  { label: "AI Statistical Review",      cost: 25, unit: "per review",     free: false },
  { label: "AI Methodology Builder",     cost: 10, unit: "per build",      free: false },
  { label: "AI Research Design Advisor", cost: 10, unit: "per session",    free: false },
  { label: "AI Research Gap Finder",     cost: 10, unit: "per scan",       free: false },
  { label: "AI Journal Matching",        cost: 5,  unit: "per match",      free: false },
  { label: "AI Conference Matching",     cost: 5,  unit: "per match",      free: false },
  { label: "AI Grant Matching",          cost: 5,  unit: "per match",      free: false },
  { label: "AI Abstract Generator",      cost: 5,  unit: "per abstract",   free: false },
  { label: "AI Research Assistant",      cost: 2,  unit: "per query",      free: false },
  { label: "AI Manuscript Copilot",      cost: 2,  unit: "per message",    free: false },
  { label: "AI Rewriting",               cost: 2,  unit: "per request",    free: false },
  { label: "AI Lesson Generator",        cost: 10, unit: "per lesson",     free: false },
  { label: "AI Assessment Generator",    cost: 10, unit: "per assessment", free: false },
  { label: "AI Teaching Assistant",      cost: 2,  unit: "per message",    free: false },
  { label: "Researcher Discovery",       cost: 0,  unit: "",               free: true  },
  { label: "Profile Creation",           cost: 0,  unit: "",               free: true  },
  { label: "Collaboration Requests",     cost: 0,  unit: "",               free: true  },
];

const STATIC_MATRIX = {
  columns: ["free", "researcher", "pro_researcher", "institution"],
  rows: [
    // General
    { label: "Research Credits / month",   values: ["50",      "300",       "1,000",     "20,000"]    },
    { label: "Active Projects",            values: ["1",       "Unlimited", "Unlimited", "Unlimited"] },
    { label: "Workspaces",                 values: ["1",       "10",        "Unlimited", "Unlimited"] },
    { label: "Repository Storage",         values: ["500 MB",  "100 GB",    "500 GB",    "2 TB"]      },
    { label: "Version History",            values: ["7 days",  "90 days",   "Unlimited", "Unlimited"] },
    { label: "Users Included",             values: ["1",       "1",         "1",         "25"]        },
    { label: "Private Workspaces",         values: [false,     true,        true,        true]        },
    // Research Tools
    { label: "Academic Profile",           values: [true,      true,        true,        true]        },
    { label: "ORCID Integration",          values: [true,      true,        true,        true]        },
    { label: "Research Network Access",    values: [true,      true,        true,        true]        },
    { label: "Journal Discovery",          values: ["5 / mo",  "Full",      "Full",      "Full"]      },
    { label: "Conference Discovery",       values: ["5 / mo",  "Full",      "Full",      "Full"]      },
    { label: "Grant Discovery",            values: ["3 / mo",  "Full",      "Full",      "Full"]      },
    // AI Suite
    { label: "AI Research Assistant",      values: [false,     true,        "Advanced",  "Advanced"]  },
    { label: "AI Manuscript Copilot",      values: [false,     true,        "Advanced",  "Advanced"]  },
    { label: "AI Literature Review",       values: [false,     true,        true,        true]        },
    { label: "AI Research Gap Finder",     values: [false,     true,        true,        true]        },
    { label: "AI Statistical Review",      values: [false,     true,        true,        true]        },
    { label: "AI Study Design Advisor",    values: [false,     true,        true,        true]        },
    { label: "AI Agent Automation",        values: [false,     false,       true,        true]        },
    { label: "AI Teaching Tools",          values: [false,     false,       true,        true]        },
    // Collaboration
    { label: "Team Formation",             values: [true,      true,        true,        true]        },
    { label: "Real-time Collaboration",    values: [false,     true,        true,        true]        },
    { label: "Collaboration Intelligence", values: [false,     false,       true,        true]        },
    // Publishing
    { label: "Publication Tracking",       values: [false,     true,        true,        true]        },
    { label: "Citation Monitoring",        values: [false,     false,       true,        true]        },
    { label: "Research Impact Dashboard",  values: [false,     false,       true,        true]        },
    // Teaching
    { label: "Teaching Hub",               values: [false,     true,        true,        true]        },
    // Analytics
    { label: "Advanced Analytics",         values: [false,     true,        true,        true]        },
    { label: "Research Analytics Suite",   values: [false,     false,       true,        true]        },
    // Verification & Trust
    { label: "Academic Passport",          values: [true,      true,        true,        true]        },
    { label: "Verification Badge",         values: [false,     true,        true,        true]        },
    { label: "Trust Score",                values: [false,     true,        true,        true]        },
    // Institution
    { label: "Institutional Analytics",    values: [false,     false,       false,       true]        },
    { label: "Department Management",      values: [false,     false,       false,       true]        },
    { label: "Seat Administration",        values: [false,     false,       false,       true]        },
    { label: "SSO / SAML",                 values: [false,     false,       false,       true]        },
    // Admin & Security
    { label: "2-Factor Authentication",    values: [true,      true,        true,        true]        },
    { label: "End-to-end Encryption",      values: [true,      true,        true,        true]        },
    { label: "Audit Logs",                 values: [false,     false,       false,       true]        },
    { label: "GDPR Data Exports",          values: [true,      true,        true,        true]        },
    // Support
    { label: "Support Level",              values: ["Community","Priority", "Priority",  "Dedicated"] },
    { label: "Dedicated Success Manager",  values: [false,     false,       false,       true]        },
  ],
};

const COMPARISON_GROUPS = [
  { label: "General", rows: ["Research Credits / month", "Active Projects", "Workspaces", "Repository Storage", "Version History", "Users Included", "Private Workspaces"] },
  { label: "Research Tools", rows: ["Academic Profile", "ORCID Integration", "Research Network Access", "Journal Discovery", "Conference Discovery", "Grant Discovery"] },
  { label: "AI Suite", rows: ["AI Research Assistant", "AI Manuscript Copilot", "AI Literature Review", "AI Research Gap Finder", "AI Statistical Review", "AI Study Design Advisor", "AI Agent Automation", "AI Teaching Tools"] },
  { label: "Collaboration", rows: ["Team Formation", "Real-time Collaboration", "Collaboration Intelligence"] },
  { label: "Publishing", rows: ["Publication Tracking", "Citation Monitoring", "Research Impact Dashboard"] },
  { label: "Teaching", rows: ["Teaching Hub"] },
  { label: "Analytics & Intelligence", rows: ["Advanced Analytics", "Research Analytics Suite"] },
  { label: "Verification & Trust", rows: ["Academic Passport", "Verification Badge", "Trust Score"] },
  { label: "Institution", rows: ["Institutional Analytics", "Department Management", "Seat Administration", "SSO / SAML"] },
  { label: "Admin & Security", rows: ["2-Factor Authentication", "End-to-end Encryption", "Audit Logs", "GDPR Data Exports"] },
  { label: "Support", rows: ["Support Level", "Dedicated Success Manager"] },
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
    q: "How do AI Credits work?",
    a: "Research Credits are the currency for AI-powered tools on Synaptiq. Each AI action consumes a fixed, documented number of credits — for example, a literature review costs 20 credits, while a research assistant query costs 2 credits. Your plan's monthly allowance refreshes at each billing cycle. Credit packs (one-time purchases) never expire.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. Subscriptions are month-to-month (or annual) with no long-term commitment. Cancel at any time from your account settings and you keep full access until the end of the current billing period. No cancellation fees, no lock-in.",
  },
  {
    q: "Do unused credits roll over?",
    a: "Monthly plan credits do not roll over — they reset each billing cycle. However, credits from purchased Credit Packs are permanent and never expire, even if you cancel or downgrade your plan.",
  },
  {
    q: "How secure is Synaptiq?",
    a: "All data is encrypted in transit (TLS 1.2+) and at rest. Authentication uses httpOnly cookies, bcrypt password hashing, and optional 2FA. We are GDPR-aligned and never sell your data. Institution plans additionally support SSO/SAML, audit logs, and advanced access controls.",
  },
  {
    q: "Can universities negotiate pricing?",
    a: "Yes. The Institution plan is the starting point for university deployments, but we work with research offices, consortia, and funding bodies on custom arrangements — including custom seat counts, data residency, and procurement documentation. Contact our team for a tailored quote.",
  },
  {
    q: "Can I upgrade later?",
    a: "Absolutely. You can change plans at any time from Settings. Upgrades take effect immediately and your credit balance tops up to the new plan's allowance. Downgrades take effect at the start of your next billing cycle. Your Credit Pack balance is always preserved.",
  },
  {
    q: "Do students receive discounts?",
    a: "We offer a permanent Free plan with no credit card required, which covers research profiles, collaboration discovery, and a starter credit allowance. Students and early PhD candidates can do meaningful work on Free before needing to upgrade. Educational institution pricing is available for departments.",
  },
  {
    q: "Can institutions invite researchers?",
    a: "Yes. The Institution plan includes 25 researcher seats. Administrators can invite researchers, manage allocations, and monitor collective research activity from a unified dashboard. For larger deployments beyond 25 seats, contact our team.",
  },
  {
    q: "Can I buy extra credits?",
    a: "Yes. Credit Packs (100, 250, 1,000, or 5,000 credits) are available as one-time purchases on any plan including Free. They stack with your monthly allowance and never expire. You can purchase from the Pricing page or from Settings → AI Credits.",
  },
  {
    q: "How is billing calculated?",
    a: "Monthly plans are charged on the same date each month. Annual plans are charged once per year at a 20% discount. All prices are in EUR, excluding VAT where applicable. Stripe processes all transactions — Synaptiq never stores card details. Institutions can request invoicing.",
  },
];

const PLAN_HIGHLIGHTS = {
  free: [
    "Academic profile & public research page",
    "ORCID integration",
    "Research network & collaboration discovery",
    "1 active project · 1 workspace · 500 MB storage",
    "Limited discovery (5 journals, 5 conferences, 3 grants / mo)",
  ],
  researcher: [
    "Everything in Free",
    "Unlimited projects · 10 workspaces · 100 GB",
    "Full journal, conference & grant discovery",
    "AI Research Assistant & Manuscript Copilot",
    "Teaching Hub — lesson planner, assessments, portfolio",
    "Publication tracking & advanced analytics",
    "Priority support",
  ],
  pro_researcher: [
    "Everything in Researcher",
    "1,000 credits / month · Unlimited workspaces · 500 GB",
    "Advanced AI — deeper context, priority processing",
    "Collaboration Intelligence & Research Impact Dashboard",
    "Citation Monitoring & Research Analytics Suite",
    "AI Teaching Tools — lesson & assessment generator",
  ],
  institution: [
    "Everything in Pro Researcher",
    "25 researcher seats included",
    "20,000 credits / month · 2 TB shared storage",
    "Institutional Analytics Dashboard",
    "Department Management & seat administration",
    "SSO / SAML · Audit Logs · Dedicated support",
  ],
};

/* ─── Helpers ─────────────────────────────────────────────────────────────── */

const PLAN_ORDER = { free: 0, researcher: 1, pro_researcher: 2, institution: 3 };

/* ─── Component ──────────────────────────────────────────────────────────── */

export default function Pricing() {
  useEffect(() => {
    document.title = "Pricing — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const [plans,    setPlans]    = useState(STATIC_PLANS);
  const [packs,    setPacks]    = useState(STATIC_PACKS);
  const [usageCat, setUsageCat] = useState(STATIC_USAGE);
  const [matrix,   setMatrix]   = useState(STATIC_MATRIX);
  const [annual,   setAnnual]   = useState(false);
  const [busy,     setBusy]     = useState("");
  const [packBusy, setPackBusy] = useState("");
  const [openFaq,  setOpenFaq]  = useState(null);
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/billing/plans").then((r) => setPlans(r.data)).catch(() => {});
    api.get("/billing/credit-packs").then((r) => setPacks(r.data)).catch(() => {});
    api.get("/billing/credit-usage-catalogue").then((r) => setUsageCat(r.data.display || [])).catch(() => {});
    api.get("/billing/feature-matrix").then((r) => setMatrix(r.data)).catch(() => {});
  }, []);

  const startCheckout = async (code) => {
    if (!user) { navigate("/register"); return; }
    if (code === "free") { toast.success("You're on the Free plan."); navigate("/discover"); return; }
    if (code === "institution") { navigate("/contact?topic=enterprise"); return; }
    setBusy(code);
    try {
      const res = await api.post("/billing/checkout-session", {
        plan_code: code,
        billing_period: annual ? "annual" : "monthly",
        success_url: window.location.origin + "/settings?upgraded=1",
        cancel_url:  window.location.origin + "/pricing",
      });
      if (res.data.url) { window.location.href = res.data.url; return; }
      toast.info("Checkout will be available once billing is activated.");
    } catch (e) {
      const detail = e.response?.data?.detail;
      const msg = (detail && typeof detail === "object")
        ? (detail.message || "Billing activates once Stripe is wired.")
        : (typeof detail === "string" ? detail : "Billing not yet activated.");
      toast.info(msg);
    } finally { setBusy(""); }
  };

  const buyPack = async (pack) => {
    if (!user) { navigate("/register"); return; }
    setPackBusy(pack.code);
    try {
      const res = await api.post("/billing/credit-pack-checkout", {
        pack_code:   pack.code,
        success_url: window.location.origin + "/settings?pack=" + pack.code,
        cancel_url:  window.location.origin + "/pricing#credit-packs",
      });
      if (res.data.url) { window.location.href = res.data.url; return; }
      toast.info("Credit pack purchase will be available once billing is activated.");
    } catch (e) {
      const detail = e.response?.data?.detail;
      const msg = (detail && typeof detail === "object")
        ? (detail.message || "Credit pack purchase activates once Stripe is wired.")
        : (typeof detail === "string" ? detail : "Credit pack purchase not yet activated.");
      toast.info(msg);
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

  const VISIBLE_CODES = new Set(["free", "researcher", "pro_researcher", "institution"]);
  const sortedPlans = [...plans]
    .filter((p) => VISIBLE_CODES.has(p.code))
    .sort((a, b) => (PLAN_ORDER[a.code] ?? 9) - (PLAN_ORDER[b.code] ?? 9));

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
            Choose the perfect workspace for your academic journey — from solo researchers to entire institutions.
          </p>

          {/* Billing toggle */}
          <div className="flex items-center gap-4 flex-wrap" style={{ marginTop: 36 }}>
            <div style={{
              display: "inline-flex", alignItems: "center",
              border: "1px solid #e2e8f0", borderRadius: 10, overflow: "hidden",
              background: "#f8fafc",
            }}>
              <button
                data-testid={TID.pricingBillMonthly}
                onClick={() => setAnnual(false)}
                style={{
                  padding: "9px 22px", fontSize: "0.85rem", fontWeight: 600,
                  border: "none", cursor: "pointer",
                  background: !annual ? "#fff" : "transparent",
                  color: !annual ? "#0a0f1a" : "#64748b",
                  boxShadow: !annual ? "0 1px 4px rgba(0,0,0,0.08)" : "none",
                  borderRadius: !annual ? 8 : 0,
                  transition: "all 150ms ease",
                  margin: !annual ? 2 : 0,
                }}
              >
                Pay monthly
              </button>
              <button
                data-testid={TID.pricingBillAnnual}
                onClick={() => setAnnual(true)}
                style={{
                  padding: "9px 22px", fontSize: "0.85rem", fontWeight: 600,
                  border: "none", cursor: "pointer",
                  background: annual ? "#fff" : "transparent",
                  color: annual ? "#0a0f1a" : "#64748b",
                  boxShadow: annual ? "0 1px 4px rgba(0,0,0,0.08)" : "none",
                  borderRadius: annual ? 8 : 0,
                  transition: "all 150ms ease",
                  margin: annual ? 2 : 0,
                  display: "flex", alignItems: "center", gap: 8,
                }}
              >
                Pay yearly
              </button>
            </div>
            {!annual && (
              <span style={{ fontSize: "0.82rem", color: "#059669", fontWeight: 600 }}>
                Save up to 20% with yearly billing
              </span>
            )}
          </div>

          {/* Trust micro-row */}
          <div className="flex flex-wrap items-center gap-6 mt-8">
            {["Cancel any time", "No credit card required for Free", "Research data owned by you"].map((t) => (
              <div key={t} className="flex items-center gap-1.5">
                <CheckCircle2 size={13} strokeWidth={2} style={{ color: "#10b981" }} />
                <span style={{ fontSize: "0.78rem", color: "#64748b", fontWeight: 500 }}>{t}</span>
              </div>
            ))}
          </div>

          {/* Trusted-by strip */}
          <div className="flex flex-wrap items-center gap-x-8 gap-y-3 mt-10">
            <span style={{ fontSize: "0.72rem", color: "#94a3b8", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Trusted by researchers at
            </span>
            {["MIT", "Oxford", "ETH Zürich", "Kyoto Univ.", "Uppsala", "TU Berlin", "CNRS", "Nature Publishing"].map((name) => (
              <span key={name} style={{ fontSize: "0.8rem", fontWeight: 700, color: "#94a3b8", letterSpacing: "0.01em" }}>
                {name}
              </span>
            ))}
          </div>
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
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 20, alignItems: "stretch" }}
               className="grid-cols-1 md:grid-cols-2 xl:grid-cols-4">
            {sortedPlans.map((p) => {
              const price    = annual ? p.price_eur_annual : p.price_eur_monthly;
              const isFree   = p.code === "free";
              const isPopular = p.code === "researcher";
              const isInst   = p.code === "institution";
              const savings  = annualSavings(p);
              const highlights = PLAN_HIGHLIGHTS[p.code] || p.features.slice(0, 6);

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
                      Most Popular
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

                  {/* Price block */}
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                      <span style={{
                        fontSize: "3rem", fontWeight: 900, lineHeight: 1, letterSpacing: "-0.045em",
                        color: isPopular ? "#fff" : "#0a0f1a",
                      }}>
                        €{price % 1 === 0 ? price : price.toFixed(2).replace(".00", "")}
                      </span>
                      {!isFree && !isInst && (
                        <span style={{ fontSize: "0.78rem", color: isPopular ? "rgba(255,255,255,0.45)" : "#94a3b8", fontWeight: 500 }}>
                          {annual ? "/ mo, billed annually" : "/ month"}
                        </span>
                      )}
                      {isInst && (
                        <span style={{ fontSize: "0.78rem", color: "#94a3b8", fontWeight: 500 }}>/ month</span>
                      )}
                    </div>

                    {savings && (
                      <div style={{ fontSize: "0.72rem", fontWeight: 600, marginTop: 4,
                        color: isPopular ? "rgba(255,255,255,0.6)" : "#059669" }}>
                        Save €{savings} per year
                      </div>
                    )}

                    {p.code === "researcher" && p.future_price_eur_monthly && (
                      <div style={{ fontSize: "0.68rem", marginTop: 4,
                        color: isPopular ? "rgba(255,255,255,0.4)" : "#b45309", fontWeight: 500 }}>
                        Early Access — future price €{p.future_price_eur_monthly} / mo
                      </div>
                    )}
                  </div>

                  {/* Credits chip */}
                  <div style={{
                    display: "inline-flex", alignItems: "center", gap: 6,
                    background: isPopular ? "rgba(255,255,255,0.1)" : "#f1f5f9",
                    borderRadius: 7, padding: "7px 12px", marginTop: 16, marginBottom: 24, alignSelf: "flex-start",
                  }}>
                    <Sparkles size={12} strokeWidth={2} style={{ color: isPopular ? "rgba(255,255,255,0.7)" : "#0F2847" }} />
                    <span style={{ fontSize: "0.75rem", fontWeight: 700, color: isPopular ? "rgba(255,255,255,0.85)" : "#0F2847" }}>
                      {p.credits_per_month.toLocaleString()} Credits / month
                    </span>
                  </div>

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
            All prices in EUR, excluding VAT where applicable. Stripe processes all payments securely.
          </p>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          PLANS AND FEATURES — sticky comparison table (Notion-style)
      ══════════════════════════════════════════════════════════════════════ */}
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
                    const isPopular = c === "researcher";
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
                          {isPopular && <span style={{ display: "block", fontSize: "0.58rem", color: "#0F2847", marginBottom: 4 }}>MOST POPULAR</span>}
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
                          {isFree ? "Sign up" : isInst ? "Contact us" : "Get started"}
                        </button>
                      </th>
                    );
                  })}
                </tr>
              </thead>

              {/* ── Body ── */}
              <tbody>
                {COMPARISON_GROUPS.map((group) => {
                  const groupRows = group.rows
                    .map((label) => matrix.rows.find((r) => r.label === label))
                    .filter(Boolean);
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
                            const isPopular = code === "researcher";
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
                    const isPopular = c === "researcher";
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
                          {isFree ? "Sign up" : isInst ? "Contact us" : "Get started"}
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

      {/* ══════════════════════════════════════════════════════════════════════
          RESEARCH CREDITS EXPLANATION
      ══════════════════════════════════════════════════════════════════════ */}
      <section id="credit-packs" data-testid="credit-usage-grid" style={{ background: "#f8fafc", borderTop: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-20 lg:py-24">
          <div className="grid lg:grid-cols-2 gap-16 items-start">

            {/* Left: explanation */}
            <div>
              <div className="overline mb-4">Research Credits</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3vw, 2.6rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.1, marginBottom: 16 }}>
                AI usage, transparent by design.
              </h2>
              <p style={{ fontSize: "0.92rem", color: "#64748b", lineHeight: 1.75, marginBottom: 28, maxWidth: 480 }}>
                Every AI action has a fixed, documented credit cost. Your plan's monthly allowance refreshes automatically. Credit Packs top up instantly and never expire.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {[
                  { icon: Zap,          label: "Monthly credits refresh",         body: "Your plan's credit allowance resets at each billing cycle." },
                  { icon: Database,     label: "Pack credits never expire",        body: "One-time pack purchases stack with monthly credits and stay forever." },
                  { icon: CheckCircle2, label: "Core features always free",        body: "Discovery, profiles, and collaboration requests cost zero credits." },
                  { icon: CreditCard,   label: "Top up anytime",                  body: "Buy 100, 250, 1,000 or 5,000 credit packs — on any plan, at any time." },
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
              <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 10, padding: "14px 18px", marginBottom: 16 }}>
                <div style={{ fontSize: "0.62rem", fontWeight: 700, color: "#059669", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>Always free</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 20px" }}>
                  {usageCat.filter((r) => r.free).map((r) => (
                    <div key={r.label} style={{ fontSize: "0.75rem", color: "#166534", fontWeight: 500, display: "flex", alignItems: "center", gap: 5 }}>
                      <Check size={11} strokeWidth={2.5} /> {r.label}
                    </div>
                  ))}
                </div>
              </div>

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
                        {r.cost} cr {r.unit}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Credit packs */}
              <div data-testid="credit-packs" style={{ marginTop: 20 }}>
                <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#94a3b8", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 12 }}>Credit Packs — one-time purchase</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {packs.map((pk) => (
                    <div key={pk.code} data-testid={`pack-card-${pk.code}`}
                      style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, padding: "16px 18px", display: "flex", flexDirection: "column", gap: 10 }}
                    >
                      <div style={{ fontSize: "1rem", fontWeight: 800, color: "#0a0f1a", letterSpacing: "-0.02em" }}>{pk.label}</div>
                      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                        <span style={{ fontSize: "1.5rem", fontWeight: 900, color: "#0a0f1a", letterSpacing: "-0.03em", lineHeight: 1 }}>€{pk.price_eur}</span>
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

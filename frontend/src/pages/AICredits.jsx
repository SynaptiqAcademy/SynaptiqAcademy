/* eslint-disable */
/**
 * AICredits — Research Credit Economy Center.
 *
 * Separate from billing (subscriptions). Credits unlock AI — subscriptions
 * unlock collaboration. Both concepts displayed distinctly.
 *
 * Real data from:
 *   GET /api/billing/subscription   → balance + plan
 *   GET /api/ai/usage               → 30-day trend + by_kind
 *   GET /api/credits/purchases      → purchase history
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import {
  Coins, TrendingUp, ArrowRight, Sparkles, Activity, CreditCard,
  ChevronRight, Package, BarChart2, Clock, ExternalLink, Info,
  BookMarked, Target, FlaskConical, PenLine, AlignLeft, Microscope,
  Users, Bot,
} from "lucide-react";
import { Spinner, SkeletonCard } from "@/components/ds/LoadingState";
import { AIWorkspaceLayout } from "@/layouts";

// ─── Credit packs (mirrors CREDIT_PACKS in plans_catalogue.py) ───────────────
const CREDIT_PACKS = [
  { code: "pack_100",  credits: 100,  price: "€5",  label: "100 Credits",   desc: "Try a few reviews" },
  { code: "pack_250",  credits: 250,  price: "€10", label: "250 Credits",   desc: "Small project boost", popular: true },
  { code: "pack_1000", credits: 1000, price: "€29", label: "1,000 Credits", desc: "Full manuscript cycle" },
  { code: "pack_5000", credits: 5000, price: "€99", label: "5,000 Credits", desc: "Lab or team allocation" },
];

// ─── Frequently used tools with costs ────────────────────────────────────────
const TOOL_COSTS = [
  { label: "Literature Review",    cost: 20, icon: BookMarked, to: "/literature-review",    unit: "per review" },
  { label: "Manuscript Review",    cost: 20, icon: Microscope, to: "/manuscript-review",    unit: "per review" },
  { label: "Statistical Analysis", cost: 25, icon: BarChart2,  to: "/statistical-review",   unit: "per analysis" },
  { label: "Research Gap Finder",  cost: 10, icon: Target,     to: "/research-gap-finder",  unit: "per analysis" },
  { label: "Study Design Advisor", cost: 10, icon: FlaskConical, to: "/research-design-advisor", unit: "per session" },
  { label: "Collaboration AI",     cost: 15, icon: Users,      to: "/collaboration-intelligence", unit: "per analysis" },
  { label: "Abstract Generator",   cost:  5, icon: AlignLeft,  to: "/ai/abstract",          unit: "per abstract" },
  { label: "Academic Rewriting",   cost:  2, icon: PenLine,    to: "/ai/rewrite",            unit: "per rewrite" },
  { label: "AI Research Assistant",cost:  2, icon: Sparkles,   to: "/ai",                   unit: "per message" },
  { label: "Research Copilot",     cost:  3, icon: Sparkles,   to: "/copilot",              unit: "per message" },
  { label: "Agent Workflow",       cost:  8, icon: Bot,        to: "/agent-workforce",      unit: "per workflow" },
];

function SparklineBars({ data }) {
  if (!data || data.length === 0) return (
    <div className="text-xs text-slate-400 py-4">No activity in the last 30 days.</div>
  );
  const today = new Date();
  const days = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const iso = d.toISOString().slice(0, 10);
    const found = data.find((x) => x._id === iso);
    days.push({ date: iso, credits: found?.credits || 0 });
  }
  const max = Math.max(...days.map((d) => d.credits), 1);
  return (
    <div className="flex items-end gap-[2px] h-20">
      {days.map((d, i) => (
        <div
          key={i}
          title={`${d.date} · ${d.credits} credits`}
          className={`flex-1 transition-colors ${d.credits > 0 ? "bg-[#0F2847] hover:bg-amber-500" : "bg-slate-100"}`}
          style={{ height: `${Math.max(2, (d.credits / max) * 80)}px` }}
        />
      ))}
    </div>
  );
}

export default function AICredits() {
  const { user } = useAuth();
  const [sub, setSub]           = useState(null);
  const [usage, setUsage]       = useState(null);
  const [purchases, setPurchases] = useState([]);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/billing/subscription").catch(() => ({ data: null })),
      api.get("/ai/usage").catch(() => ({ data: null })),
      api.get("/credits/purchases").catch(() => ({ data: [] })),
    ]).then(([s, u, p]) => {
      setSub(s.data);
      setUsage(u.data);
      setPurchases(p.data || []);
    }).finally(() => setLoading(false));
  }, []);

  const credits    = sub?.credits || {};
  const totalUsed  = (usage?.last_30d || []).reduce((s, d) => s + (d.credits || 0), 0);
  const topKind    = (usage?.by_kind || []).sort((a, b) => (b.credits || 0) - (a.credits || 0))[0];
  const planLabel  = sub?.plan?.name || "Free";

  return (
    <AIWorkspaceLayout
      title="Research Credits"
      subtitle="Credits unlock AI tools. Subscriptions unlock collaboration. Two separate economies."
    >
      <div className="space-y-8">

        {loading ? (
          <div className="space-y-4"><SkeletonCard rows={3} /></div>
        ) : (
          <>
            {/* ── Credit balance ─────────────────────────────────────── */}
            <div className="grid sm:grid-cols-3 gap-3">
              <div className="border border-slate-200 bg-white p-5">
                <div className="overline flex items-center gap-1">
                  <Coins size={11} strokeWidth={1.5} className="text-[#0F2847]" />
                  Monthly credits
                </div>
                <div className="font-serif text-4xl text-slate-900 mt-2">{(credits.monthly_balance ?? 0).toLocaleString()}</div>
                <div className="text-xs text-slate-500 font-mono mt-1">
                  of {(credits.monthly_allowance ?? 0).toLocaleString()} · refreshes each month
                </div>
                <div className="text-[10px] text-slate-400 mt-1">{planLabel} plan</div>
              </div>
              <div className="border border-slate-200 bg-white p-5">
                <div className="overline flex items-center gap-1">
                  <Package size={11} strokeWidth={1.5} className="text-[#0F2847]" />
                  Pack credits
                </div>
                <div className="font-serif text-4xl text-slate-900 mt-2">{(credits.pack_balance ?? 0).toLocaleString()}</div>
                <div className="text-xs text-slate-500 font-mono mt-1">never expire</div>
              </div>
              <div className="border border-[#0F2847] bg-[#0F2847] text-white p-5">
                <div className="overline" style={{ color: "#94a3b8" }}>Total available</div>
                <div className="font-serif text-4xl mt-2">{(credits.balance ?? 0).toLocaleString()}</div>
                <div className="text-xs mt-1 flex items-center gap-1 text-slate-300">
                  <Sparkles size={11} strokeWidth={1.5} />
                  Research Credits
                </div>
                <Link
                  to="/settings/billing"
                  className="mt-3 inline-flex items-center gap-1 text-xs border border-white/30 text-white px-2 py-1 hover:bg-white/10"
                >
                  <CreditCard size={10} strokeWidth={1.5} />
                  Buy more
                </Link>
              </div>
            </div>

            {/* ── 30-day trend ───────────────────────────────────────── */}
            <div className="border border-slate-200 bg-white p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="overline flex items-center gap-2">
                    <Activity size={12} strokeWidth={1.5} className="text-[#0F2847]" />
                    30-day consumption
                  </div>
                  <div className="font-serif text-xl text-slate-900 mt-1">Monthly Usage Trend</div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-xs text-slate-500">Total in window</div>
                  <div className="font-serif text-2xl text-slate-900">{totalUsed.toLocaleString()}</div>
                  <div className="text-xs text-slate-400 font-mono">credits</div>
                </div>
              </div>
              <SparklineBars data={usage?.last_30d} />
              {topKind && (
                <div className="mt-3 text-xs text-slate-500 font-mono">
                  Most used: <span className="text-slate-900">{topKind._id?.replace(/_/g, " ")}</span> · {topKind.credits} credits in 30 days
                </div>
              )}
              <Link to="/ai-usage" className="mt-2 inline-flex items-center gap-1 text-xs text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
                Full analytics <ChevronRight size={10} strokeWidth={1.5} />
              </Link>
            </div>

            {/* ── Credit packages ────────────────────────────────────── */}
            <section>
              <div className="overline mb-1">Purchase Credits</div>
              <p className="text-xs text-slate-500 mb-4">
                Credits unlock AI tools and never expire. Subscription plans include monthly allocations.
              </p>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {CREDIT_PACKS.map((pack) => (
                  <div
                    key={pack.code}
                    className={`border p-5 relative ${pack.popular ? "border-[#0F2847]" : "border-slate-200 bg-white"}`}
                  >
                    {pack.popular && (
                      <div className="absolute -top-2.5 left-4 text-[10px] font-mono bg-[#0F2847] text-white px-2 py-0.5">
                        Most popular
                      </div>
                    )}
                    <div className="overline">{pack.label}</div>
                    <div className="font-serif text-3xl text-slate-900 mt-2">{pack.price}</div>
                    <div className="text-xs text-slate-500 mt-1 font-mono">{pack.desc}</div>
                    <Link
                      to="/settings/billing"
                      className={`mt-4 w-full inline-flex items-center justify-center gap-1.5 text-xs px-3 py-2 transition-colors ${
                        pack.popular
                          ? "bg-[#0F2847] text-white hover:bg-slate-800"
                          : "border border-slate-300 text-slate-700 hover:border-[#0F2847] hover:text-[#0F2847]"
                      }`}
                    >
                      Purchase <ExternalLink size={10} strokeWidth={1.5} />
                    </Link>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-slate-400 font-mono mt-3">
                Upgrade your plan for higher monthly credit allowances →{" "}
                <Link to="/pricing" className="underline hover:text-[#0F2847]">View plans</Link>
              </p>
            </section>

            {/* ── Tool costs ──────────────────────────────────────────── */}
            <section className="border border-slate-200 bg-white">
              <div className="px-5 py-4 border-b border-slate-200">
                <div className="overline flex items-center gap-2">
                  <Info size={11} strokeWidth={1.5} className="text-[#0F2847]" />
                  Credit cost reference
                </div>
                <p className="text-xs text-slate-500 mt-0.5">Costs per AI tool use. Monthly plan credits refresh automatically.</p>
              </div>
              <div className="divide-y divide-slate-100">
                {TOOL_COSTS.map((t) => {
                  const Icon = t.icon;
                  return (
                    <Link
                      key={t.to}
                      to={t.to}
                      className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50 transition-colors"
                    >
                      <Icon size={13} strokeWidth={1.5} className="text-[#0F2847] shrink-0" />
                      <div className="flex-1 text-sm text-slate-900">{t.label}</div>
                      <div className="text-xs font-mono text-slate-500 shrink-0">
                        {t.cost === 0 ? "Free" : `${t.cost} credits`}
                      </div>
                      <div className="text-[10px] font-mono text-slate-400 shrink-0 w-24 text-right">{t.unit}</div>
                      <ChevronRight size={12} strokeWidth={1.5} className="text-slate-300 shrink-0" />
                    </Link>
                  );
                })}
              </div>
            </section>

            {/* ── Purchase history ────────────────────────────────────── */}
            {purchases.length > 0 && (
              <section className="border border-slate-200 bg-white">
                <div className="px-5 py-4 border-b border-slate-200 overline">Recent pack purchases</div>
                <div className="divide-y divide-slate-100">
                  {purchases.slice(0, 8).map((p) => (
                    <div key={p.id} className="px-5 py-3 flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <Package size={12} strokeWidth={1.5} className="text-[#0F2847] shrink-0" />
                        <span className="font-medium text-slate-900">+{p.credits} credits</span>
                        <span className="text-slate-500">{p.pack_code?.replace("_", " ")}</span>
                      </div>
                      <span className="text-xs font-mono text-slate-400">{(p.created_at || "").slice(0, 10)}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}

        {/* ── Subscription vs credits explainer ─────────────────────── */}
        <div className="border border-slate-200 bg-slate-50 p-5">
          <div className="overline mb-3">Two separate economies</div>
          <div className="grid sm:grid-cols-2 gap-5">
            <div>
              <div className="text-sm font-medium text-slate-900 mb-1">Subscription → Collaboration</div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Plans unlock network features, team access, workspace limits, messaging, and institution tools.
                Collaboration is free from credits.
              </p>
              <Link to="/pricing" className="mt-2 inline-flex items-center gap-1 text-xs text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
                View plans <ArrowRight size={10} strokeWidth={1.5} />
              </Link>
            </div>
            <div>
              <div className="text-sm font-medium text-slate-900 mb-1">Credits → AI Tools</div>
              <p className="text-xs text-slate-600 leading-relaxed">
                AI tools consume Research Credits. Your plan includes a monthly allowance.
                Additional credits can be purchased as packs that never expire.
              </p>
              <Link to="/ai-suite" className="mt-2 inline-flex items-center gap-1 text-xs text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
                Browse AI tools <ArrowRight size={10} strokeWidth={1.5} />
              </Link>
            </div>
          </div>
        </div>

      </div>
    </AIWorkspaceLayout>
  );
}

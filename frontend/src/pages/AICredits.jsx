/* eslint-disable */
/**
 * AICredits — AI Credit Economy Center.
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
  Coins, TrendingUp, Sparkles, Activity, CreditCard,
  ChevronRight, Package, BarChart2, ExternalLink, Info,
  BookMarked, Target, FlaskConical, PenLine, AlignLeft, Microscope,
  Users, Bot,
} from "lucide-react";
import { Spinner, SkeletonCard } from "@/components/ds/LoadingState";
import { Card } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { Badge } from "@/components/ds/Badge";
import { BarChart } from "@/components/ds/Chart";
import { List, ListItem } from "@/components/ds/List";
import { ResearchLayout } from "@/layouts";
import { AI_NAV_ITEMS } from "@/lib/navItems";
import BuyCreditsPanel from "@/components/billing/BuyCreditsPanel";
import { loadCreditCatalogue } from "@/components/billing/creditCatalogue";

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
  const chartData = days.map((d) => ({
    label: d.date,
    value: d.credits,
    color: d.credits > 0 ? "#0F2847" : "#F1F5F9",
  }));
  return <BarChart data={chartData} height={80} gap={2} />;
}

export default function AICredits() {
  const { user } = useAuth();
  const [sub, setSub]           = useState(null);
  const [usage, setUsage]       = useState(null);
  const [purchases, setPurchases] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [catalogue, setCatalogue] = useState([]);
  const [ledger, setLedger] = useState([]);

  useEffect(() => {
    loadCreditCatalogue().then((c) => setCatalogue(c.display || []));
    api.get("/credits/transactions?limit=15")
      .then((r) => setLedger((r.data || []).filter((t) => t.ledger_type && t.ledger_type !== "AI_CONSUMPTION" && t.balance_effect)))
      .catch(() => {});
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
  const byKind     = (usage?.by_kind || []).slice().sort((a, b) => (b.credits || 0) - (a.credits || 0));
  const topKind    = byKind[0];
  const planLabel  = sub?.plan?.name || "Free";
  const lastPurchase = purchases[0];

  return (
    <ResearchLayout
      navItems={AI_NAV_ITEMS}
      title="AI Credits"
      subtitle="Every AI action shows its credit cost before you run it. Failed requests are refunded automatically."
      stats={!loading ? [
        { label: "This month",      value: (credits.subscription_credits ?? credits.monthly_balance ?? 0).toLocaleString() },
        { label: "Purchased",       value: (credits.purchased_credits ?? credits.pack_balance ?? 0).toLocaleString() },
        { label: "Total available", value: (credits.credits_usable === false ? 0 : (credits.balance ?? 0)).toLocaleString() },
        { label: "Plan",            value: planLabel },
      ] : undefined}
      sidebar={!loading ? (
        <AICreditsSidebar byKind={byKind} lastPurchase={lastPurchase} planLabel={planLabel} monthlyAllowance={credits.monthly_allowance} />
      ) : undefined}
      actions={
        <Button as="a" href="#buy-credits" variant="hero" size="sm">
          <CreditCard size={12} strokeWidth={1.5} />
          Buy credits
        </Button>
      }
    >
      <div className="space-y-8">

        {loading ? (
          <div className="space-y-4"><SkeletonCard rows={3} /></div>
        ) : (
          <>
            {/* ── 30-day trend ───────────────────────────────────────── */}
            <Card padding="lg">
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
            </Card>

            {/* ── Recent credit activity (ledger) ─────────────────────── */}
            {ledger.length > 0 && (
              <Card padding="none" data-testid="credit-activity">
                <div className="px-5 py-4 border-b border-slate-200 overline">Recent credit activity</div>
                <List border={false} divided>
                  {ledger.map((t) => (
                    <ListItem
                      key={t.id}
                      title={t.label}
                      trailing={
                        <span className={`text-xs font-mono shrink-0 ${t.balance_effect < 0 ? "text-slate-700" : "text-emerald-700"}`}>
                          {t.balance_effect > 0 ? "+" : ""}{t.balance_effect}
                        </span>
                      }
                    />
                  ))}
                </List>
              </Card>
            )}

            {/* ── Credit packs ───────────────────────────────────────── */}
            <section id="buy-credits">
              <div className="overline mb-1">Buy credits</div>
              <p className="text-xs text-slate-500 mb-4">
                Monthly credits reset at each renewal and don't roll over. Purchased credits never expire.
              </p>
              <BuyCreditsPanel />
            </section>

            {/* ── Credit costs (server catalogue) ─────────────────────── */}
            <Card padding="none">
              <div className="px-5 py-4 border-b border-slate-200">
                <div className="overline flex items-center gap-2">
                  <Info size={11} strokeWidth={1.5} className="text-[#0F2847]" />
                  Credit costs
                </div>
                <p className="text-xs text-slate-500 mt-0.5">Charged per completed request.</p>
              </div>
              <List border={false} divided>
                {catalogue.map((t) => (
                  <ListItem
                    key={t.operation}
                    title={t.label}
                    trailing={<span className="text-xs font-mono text-slate-500 shrink-0">{t.cost} credit{t.cost === 1 ? "" : "s"}</span>}
                  />
                ))}
              </List>
            </Card>

            {/* ── Purchase history ────────────────────────────────────── */}
            {purchases.length > 0 && (
              <Card padding="none">
                <div className="px-5 py-4 border-b border-slate-200 overline">Recent pack purchases</div>
                <List border={false} divided>
                  {purchases.slice(0, 8).map((p) => (
                    <ListItem
                      key={p.id}
                      leading={<Package size={12} strokeWidth={1.5} className="text-[#0F2847] shrink-0" />}
                      title={<span><span className="font-medium text-slate-900">+{p.credits} credits</span>{" "}<span className="text-slate-500">{p.pack_code?.replace("_", " ")}</span></span>}
                      trailing={<span className="text-xs font-mono text-slate-400">{(p.created_at || "").slice(0, 10)}</span>}
                    />
                  ))}
                </List>
              </Card>
            )}
          </>
        )}

      </div>
    </ResearchLayout>
  );
}

// ─── Right rail — usage breakdown, plan, and latest purchase already loaded ───

function AICreditsSidebar({ byKind, lastPurchase, planLabel, monthlyAllowance }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div className="flex items-center gap-1.5 mb-2">
          <Coins size={13} strokeWidth={1.5} className="text-[#0F2847]" />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Your Plan</div>
        </div>
        <div className="font-serif text-2xl text-slate-900">{planLabel}</div>
        <p className="text-xs text-slate-500 mt-1">
          {(monthlyAllowance ?? 0).toLocaleString()} AI credits / month
        </p>
        <Link to="/pricing" className="text-xs text-[#0F2847] border-b border-[#0F2847] inline-block mt-2 hover:opacity-70">
          Compare plans
        </Link>
      </Card>

      {byKind.length > 0 && (
        <Card padding="lg">
          <div className="flex items-center gap-1.5 mb-3">
            <TrendingUp size={13} strokeWidth={1.5} className="text-[#0F2847]" />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Usage by Tool</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {byKind.slice(0, 3).map((k) => (
              <div key={k._id} style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                <span style={{ color: "#374151" }}>{(k._id || "").replace(/_/g, " ")}</span>
                <span style={{ color: "#94A3B8", fontFamily: "monospace" }}>{k.credits} cr</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {lastPurchase && (
        <Card padding="lg">
          <div className="flex items-center gap-1.5 mb-2">
            <Package size={13} strokeWidth={1.5} className="text-[#0F2847]" />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Latest Purchase</div>
          </div>
          <p className="text-xs text-slate-600">
            +{lastPurchase.credits} credits · {(lastPurchase.pack_code || "").replace("_", " ")}
          </p>
          <p className="text-[10px] text-slate-400 font-mono mt-1">{(lastPurchase.created_at || "").slice(0, 10)}</p>
        </Card>
      )}
    </div>
  );
}

import React, { useState, useEffect } from "react";
import { DollarSign, TrendingUp, Receipt, ShieldCheck } from "lucide-react";
import { ACCENT, EMERALD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Grid, StatGrid, StatCard, H2, Caption, EmptyState, LoadingOverlay } from "@/components/ds";

const API = "/api/acad-market";

export default function WalletCenter() {
  const [wallet, setWallet] = useState(null);
  const [txns, setTxns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/wallet`).then(r => r.json()),
      fetch(`${API}/wallet/transactions`).then(r => r.json()),
    ]).then(([w, t]) => {
      setWallet(w);
      setTxns((t.results || []));
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <LoadingOverlay text="Loading..." />;

  const TX_COLORS = { deposit: EMERALD, provider_payout: EMERALD, refund: EMERALD, credit_purchase: ACCENT, escrow_refund: EMERALD, escrow_hold: "#F59E0B", credit_spend: "#DC2626", platform_fee: "#475569" };

  return (
    <ResearchLayout title="Wallet">

        {/* Balance cards */}
        <StatGrid cols={3} className="mb-7">
          {[
            { label: "Available Balance", value: `$${wallet?.balance?.toFixed(2) || "0.00"}`, icon: <DollarSign /> },
            { label: "In Escrow", value: `$${wallet?.escrow_held?.toFixed(2) || "0.00"}`, icon: <ShieldCheck /> },
            { label: "Credits", value: wallet?.credits || 0, icon: <TrendingUp /> },
          ].map(({ label, value, icon }) => (
            <StatCard key={label} label={label} value={value} icon={icon} />
          ))}
        </StatGrid>

        {/* Stats */}
        <Grid cols={2} gap="md" className="mb-7">
          <Card padding="md">
            <Caption className="mb-1">Total Spent (as Buyer)</Caption>
            <div className="text-xl font-bold text-navy-700">${wallet?.total_spent?.toFixed(2) || "0.00"}</div>
          </Card>
          <Card padding="md">
            <Caption className="mb-1">Total Earned (as Provider)</Caption>
            <div className="text-xl font-bold text-emerald-600">${wallet?.total_earned?.toFixed(2) || "0.00"}</div>
          </Card>
        </Grid>

        {/* Transaction history */}
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-4">
            <Receipt size={18} className="text-navy-700" />
            <H2 className="m-0" style={{ fontSize: "1.0625rem" }}>Transaction History</H2>
          </div>
          {txns.length === 0 ? (
            <EmptyState title="No transactions yet." size="sm" dashed={false} />
          ) : (
            txns.map((t, i) => {
              const c = TX_COLORS[t.type] || "#475569";
              const sign = ["provider_payout", "refund", "deposit", "credit_purchase", "escrow_refund"].includes(t.type) ? "+" : "-";
              return (
                <div key={i} className={`flex items-center gap-3 pb-3.5 mb-3.5 ${i < txns.length - 1 ? "border-b border-hairline" : ""}`}>
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-navy-700 capitalize">
                      {t.type?.replace(/_/g, " ")}
                    </div>
                    <div className="text-xs text-slate-600">{t.note}</div>
                    <Caption>{new Date(t.created_at).toLocaleString()}</Caption>
                  </div>
                  <div className="text-right">
                    {t.amount > 0 && (
                      <div className="text-[15px] font-bold" style={{ color: c }}>{sign}${t.amount?.toFixed(2)}</div>
                    )}
                    {t.credits !== 0 && (
                      <div className="text-[13px] font-semibold" style={{ color: c }}>{t.credits > 0 ? "+" : ""}{t.credits} credits</div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </Card>
    </ResearchLayout>
  );
}

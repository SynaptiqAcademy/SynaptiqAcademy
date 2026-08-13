import React, { useState, useEffect } from "react";
import { DollarSign, Receipt } from "lucide-react";
import { ACCENT, EMERALD, NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, H2, Caption, EmptyState, LoadingOverlay } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = "/api/acad-market";

export default function WalletCenter() {
  const [wallet, setWallet] = useState(null);
  const [txns, setTxns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchApi(`${API}/wallet`).then(r => r.json()),
      fetchApi(`${API}/wallet/transactions`).then(r => r.json()),
    ]).then(([w, t]) => {
      setWallet(w);
      setTxns((t.results || []));
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <LoadingOverlay text="Loading..." />;

  const TX_COLORS = { deposit: EMERALD, provider_payout: EMERALD, refund: EMERALD, credit_purchase: ACCENT, escrow_refund: EMERALD, escrow_hold: "#F59E0B", credit_spend: "#DC2626", platform_fee: "#475569" };

  return (
    <ResearchLayout
      title="Wallet"
      stats={[
        { label: "Available Balance", value: `$${wallet?.balance?.toFixed(2) || "0.00"}` },
        { label: "In Escrow", value: `$${wallet?.escrow_held?.toFixed(2) || "0.00"}` },
        { label: "Credits", value: wallet?.credits || 0 },
        { label: "Total Spent", value: `$${wallet?.total_spent?.toFixed(2) || "0.00"}` },
        { label: "Total Earned", value: `$${wallet?.total_earned?.toFixed(2) || "0.00"}` },
      ]}
      sidebar={<WalletCenterSidebar txns={txns} txColors={TX_COLORS} />}
    >

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

// ── Right rail — derived from the transaction list already fetched above ──────
function WalletCenterSidebar({ txns, txColors }) {
  const latest = txns[0];
  const counts = txns.reduce((acc, t) => {
    acc[t.type] = (acc[t.type] || 0) + 1;
    return acc;
  }, {});
  const typeEntries = Object.entries(counts).sort((a, b) => b[1] - a[1]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <DollarSign size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Latest Transaction</div>
        </div>
        {latest ? (
          <>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#0f172a", textTransform: "capitalize" }}>
              {latest.type?.replace(/_/g, " ")}
            </div>
            {latest.amount > 0 && (
              <div style={{ fontSize: 20, fontWeight: 700, color: txColors[latest.type] || "#475569", fontFamily: "Georgia, serif", marginTop: 4 }}>
                ${latest.amount?.toFixed(2)}
              </div>
            )}
            <p style={{ fontSize: 11, color: "#94A3B8", margin: "4px 0 0" }}>{new Date(latest.created_at).toLocaleString()}</p>
          </>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>No transactions yet.</p>
        )}
      </Card>

      {typeEntries.length > 0 && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <Receipt size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Transaction Types</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {typeEntries.map(([type, count]) => (
              <div key={type} style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                <span style={{ color: "#374151", textTransform: "capitalize" }}>{type.replace(/_/g, " ")}</span>
                <span style={{ color: "#94A3B8", fontWeight: 600 }}>{count}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

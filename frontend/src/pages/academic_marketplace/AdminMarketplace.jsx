import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, TrendingUp } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, H2, MiniBar, EmptyState, LoadingOverlay, Caption } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = "/api/admin/acad-market";

export default function AdminMarketplace() {
  const [stats, setStats] = useState(null);
  const [disputes, setDisputes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchApi(`${API}/stats`).then(r => r.json()),
      fetchApi(`${API}/disputes?status=open`).then(r => r.json()),
    ]).then(([s, d]) => {
      setStats(s.error ? null : s);
      setDisputes(d.results || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <LoadingOverlay text="Loading admin data..." />;

  const oldestDispute = disputes.length > 0
    ? [...disputes].sort((a, b) => new Date(a.opened_at) - new Date(b.opened_at))[0]
    : null;
  const topCategory = stats?.top_categories?.[0] || null;

  return (
    <AdministrationLayout
      title="Marketplace Admin Center"
      subtitle="Platform health, transactions, and dispute management"
      stats={stats ? [
        { label: "Active Providers", value: stats.providers ?? "—" },
        { label: "Active Services", value: stats.services ?? "—" },
        { label: "Total Orders", value: stats.orders?.total ?? "—" },
        { label: "Completion Rate", value: `${stats.orders?.completion_rate?.toFixed(1)}%` },
        { label: "Platform Revenue", value: `$${stats.platform_revenue?.toFixed(2)}` },
        { label: "GMV", value: `$${stats.gmv?.toFixed(2)}` },
        { label: "Unique Buyers", value: stats.buyers ?? "—" },
        { label: "Dispute Rate", value: `${stats.disputes?.rate?.toFixed(1)}%` },
      ] : undefined}
      sidebar={<AdminMarketplaceSidebar oldestDispute={oldestDispute} topCategory={topCategory} />}
    >

        {stats && (
          <>
            {/* Top categories */}
            {stats.top_categories?.length > 0 && (
              <Card padding="lg" className="mb-6">
                <H2 className="mb-4">Top Service Categories</H2>
                {stats.top_categories.map((cat, i) => {
                  const maxCount = stats.top_categories[0]?.count || 1;
                  return (
                    <div key={i} className="flex items-center gap-3 mb-2.5">
                      <div className="text-[13px] text-slate-500 w-[200px] capitalize">
                        {cat.category?.replace(/_/g, " ")}
                      </div>
                      <MiniBar value={cat.count} max={maxCount} height={8} style={{ flex: 1 }} />
                      <div className="text-[13px] font-semibold text-navy-700 w-10 text-right">{cat.count}</div>
                    </div>
                  );
                })}
              </Card>
            )}
          </>
        )}

        {/* Open Disputes */}
        <Card padding="lg">
          <H2 className="mb-4">Open Disputes Requiring Action</H2>
          {disputes.length === 0 ? (
            <EmptyState title="No open disputes." size="sm" dashed={false} />
          ) : (
            disputes.map((d, i) => (
              <div
                key={i}
                className={`flex items-center gap-3 pb-3.5 mb-3.5 ${i < disputes.length - 1 ? "border-b border-hairline-soft" : ""}`}
              >
                <AlertCircle size={14} className="text-danger-text" />
                <div className="flex-1">
                  <div className="text-sm font-semibold text-navy-700">{d.reason?.replace(/_/g, " ")?.replace(/\b\w/g, l => l.toUpperCase())}</div>
                  <Caption>Order {d.order_id?.slice(-8)?.toUpperCase()} · Opened {new Date(d.opened_at).toLocaleDateString()}</Caption>
                </div>
                <Link to={`/academic-marketplace/disputes/${d.id}`} className="text-crimson-600 text-[13px] no-underline">Resolve →</Link>
              </div>
            ))
          )}
        </Card>
    </AdministrationLayout>
  );
}

// ── Right rail — priority dispute and top category, derived from data above ───
function AdminMarketplaceSidebar({ oldestDispute, topCategory }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <AlertCircle size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Oldest Open Dispute</div>
        </div>
        {oldestDispute ? (
          <>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: "#0f172a" }}>
              {oldestDispute.reason?.replace(/_/g, " ")?.replace(/\b\w/g, l => l.toUpperCase())}
            </div>
            <p style={{ fontSize: 11, color: "#94A3B8", margin: "4px 0 10px" }}>
              Order {oldestDispute.order_id?.slice(-8)?.toUpperCase()} · Opened {new Date(oldestDispute.opened_at).toLocaleDateString()}
            </p>
            <Link to={`/academic-marketplace/disputes/${oldestDispute.id}`} style={{ fontSize: 12, fontWeight: 600, color: NAVY, textDecoration: "none" }}>
              Resolve now →
            </Link>
          </>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>No open disputes right now.</p>
        )}
      </Card>

      {topCategory && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <TrendingUp size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Top Category</div>
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", textTransform: "capitalize" }}>
            {topCategory.category?.replace(/_/g, " ")}
          </div>
          <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0" }}>
            {topCategory.count} order{topCategory.count === 1 ? "" : "s"}
          </p>
        </Card>
      )}
    </div>
  );
}

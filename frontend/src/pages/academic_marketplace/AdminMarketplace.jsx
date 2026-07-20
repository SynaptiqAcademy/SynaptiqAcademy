import React, { useState, useEffect } from "react";
import { ShoppingBag, AlertCircle, TrendingUp, DollarSign, Users, BarChart3 } from "lucide-react";
import { AdministrationLayout } from "@/layouts";
import { Card, H2, StatGrid, StatCard, MiniBar, EmptyState, LoadingOverlay, Caption } from "@/components/ds";

const API = "/api/admin/acad-market";

export default function AdminMarketplace() {
  const [stats, setStats] = useState(null);
  const [disputes, setDisputes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/stats`).then(r => r.json()),
      fetch(`${API}/disputes?status=open`).then(r => r.json()),
    ]).then(([s, d]) => {
      setStats(s.error ? null : s);
      setDisputes(d.results || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <LoadingOverlay text="Loading admin data..." />;

  return (
    <AdministrationLayout title="Marketplace Admin Center" subtitle="Platform health, transactions, and dispute management">

        {stats && (
          <>
            <StatGrid cols={4} className="mb-7">
              {[
                { label: "Active Providers", value: stats.providers, icon: <Users /> },
                { label: "Active Services", value: stats.services, icon: <ShoppingBag /> },
                { label: "Total Orders", value: stats.orders?.total, icon: <BarChart3 /> },
                { label: "Completion Rate", value: `${stats.orders?.completion_rate?.toFixed(1)}%`, icon: <TrendingUp /> },
                { label: "Platform Revenue", value: `$${stats.platform_revenue?.toFixed(2)}`, icon: <DollarSign /> },
                { label: "GMV", value: `$${stats.gmv?.toFixed(2)}`, icon: <DollarSign /> },
                { label: "Unique Buyers", value: stats.buyers, icon: <Users /> },
                { label: "Dispute Rate", value: `${stats.disputes?.rate?.toFixed(1)}%`, icon: <AlertCircle /> },
              ].map(({ label, value, icon }) => (
                <StatCard key={label} label={label} value={value ?? "—"} icon={icon} />
              ))}
            </StatGrid>

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
                <a href={`/academic-marketplace/disputes/${d.id}`} className="text-crimson-600 text-[13px] no-underline">Resolve →</a>
              </div>
            ))
          )}
        </Card>
    </AdministrationLayout>
  );
}

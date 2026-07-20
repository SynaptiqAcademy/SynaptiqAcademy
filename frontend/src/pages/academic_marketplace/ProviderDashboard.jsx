import React, { useState, useEffect } from "react";
import { Briefcase, Star, Package, TrendingUp, DollarSign, AlertCircle, ChevronRight, Zap } from "lucide-react";
import { ACCENT, EMERALD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, StatGrid, StatCard, Alert, Badge, Button, LoadingOverlay, EmptyState, H2, Caption } from "@/components/ds";

const API = "/api/acad-market";

const STATUS_COLORS = {
  pending: "#F59E0B", accepted: ACCENT, in_progress: "#0891B2",
  under_review: "#7C3AED", completed: EMERALD, cancelled: "#94A3B8",
  revision_requested: "#D97706",
};

export default function ProviderDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/analytics/provider`).then(r => r.json()).then(d => {
      setData(d.error ? null : d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <LoadingOverlay text="Loading dashboard..." />;
  if (!data) return (
    <EmptyState
      icon={<Briefcase />}
      title="No provider profile yet"
      action={<Button as="a" href="/academic-marketplace/provider/setup" variant="link" style={{ color: "#8A1538" }}>Set up your provider profile →</Button>}
    />
  );

  const cards = [
    { label: "Total Orders", value: data.orders?.total, icon: <Package /> },
    { label: "Active Orders", value: data.orders?.active, icon: <Zap /> },
    { label: "Completed", value: data.orders?.completed, icon: <TrendingUp /> },
    { label: "Avg Rating", value: data.ratings?.average?.toFixed(1) || "—", icon: <Star /> },
    { label: "Success Rate", value: `${data.success_rate?.toFixed(0)}%`, icon: <TrendingUp /> },
    { label: "Total Earned", value: `$${data.wallet?.total_earned?.toFixed(2)}`, icon: <DollarSign /> },
  ];

  return (
    <ResearchLayout
      title="Provider Dashboard"
      actions={
        <>
          <Button as="a" href="/academic-marketplace/services/create">
            + Create Service
          </Button>
          <Button as="a" href="/academic-marketplace/orders?role=provider" variant="ghost">
            View Orders
          </Button>
        </>
      }
    >

        <StatGrid cols={3} className="mb-7">
          {cards.map(({ label, value, icon }) => (
            <StatCard key={label} label={label} value={value ?? "—"} icon={icon} />
          ))}
        </StatGrid>

        {data.orders?.pending > 0 && (
          <Alert variant="warning">
            <div className="flex items-center justify-between gap-3 w-full">
              <span>You have {data.orders.pending} pending order{data.orders.pending !== 1 ? "s" : ""} waiting for your response.</span>
              <a href="/academic-marketplace/orders?role=provider&status=pending" className="text-[13px] no-underline shrink-0" style={{ color: "#D97706" }}>View →</a>
            </div>
          </Alert>
        )}

        {data.recent_orders?.length > 0 && (
          <Card padding="lg" className="mt-5">
            <div className="flex justify-between items-center mb-4">
              <H2 className="m-0" style={{ fontSize: "1.0625rem" }}>Recent Orders</H2>
              <a href="/academic-marketplace/orders?role=provider" className="text-crimson-600 text-[13px] no-underline">View all →</a>
            </div>
            {data.recent_orders.map((o, i) => {
              const c = STATUS_COLORS[o.status] || "#475569";
              return (
                <a
                  key={o.id}
                  href={`/academic-marketplace/orders/${o.id}`}
                  className={`flex items-center gap-3 pb-3.5 mb-3.5 no-underline ${i < data.recent_orders.length - 1 ? "border-b border-hairline" : ""}`}
                >
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-navy-700">{o.service_title}</div>
                    <Caption>${o.price?.toFixed(2)} · {new Date(o.updated_at).toLocaleDateString()}</Caption>
                  </div>
                  <Badge color={c} className="capitalize">
                    {o.status?.replace(/_/g, " ")}
                  </Badge>
                  <ChevronRight size={14} className="text-slate-500" />
                </a>
              );
            })}
          </Card>
        )}

        {data.disputes?.open > 0 && (
          <div className="mt-5">
            <Alert variant="error">
              <div className="flex items-center justify-between gap-3 w-full">
                <span>{data.disputes.open} open dispute{data.disputes.open !== 1 ? "s" : ""} need attention.</span>
                <a href="/academic-marketplace/disputes" className="text-crimson-600 text-[13px] no-underline shrink-0">View →</a>
              </div>
            </Alert>
          </div>
        )}
    </ResearchLayout>
  );
}

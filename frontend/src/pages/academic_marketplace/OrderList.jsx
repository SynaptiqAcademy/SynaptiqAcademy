import React, { useState, useEffect } from "react";
import { Package, ChevronRight } from "lucide-react";
import { ACCENT, EMERALD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Button, NavTabs, FormSelect, EmptyState, LoadingOverlay } from "@/components/ds";

const API = "/api/acad-market";

const STATUS_COLORS = {
  pending: "#F59E0B", accepted: ACCENT, in_progress: "#0891B2",
  under_review: "#7C3AED", completed: EMERALD, cancelled: "#94A3B8",
  declined: "#DC2626", revision_requested: "#D97706", disputed: "#DC2626",
};

export default function OrderList() {
  const [role, setRole] = useState("buyer");
  const [orders, setOrders] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    setLoading(true);
    const qs = new URLSearchParams({ role });
    if (statusFilter) qs.set("status", statusFilter);
    fetch(`${API}/orders?${qs}`).then(r => r.json()).then(d => {
      setOrders(d.results || []);
      setTotal(d.total || 0);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [role, statusFilter]);

  return (
    <ResearchLayout
      title="My Orders"
      actions={
        <Button as="a" href="/academic-marketplace/services">
          Browse Services
        </Button>
      }
    >

        <div className="flex gap-3 mb-6 flex-wrap items-center">
          <NavTabs
            variant="segment"
            tabs={[
              { id: "buyer", label: "As Buyer" },
              { id: "provider", label: "As Provider" },
            ]}
            active={role}
            onChange={setRole}
          />
          <FormSelect
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            wrapperClassName="w-auto"
            className="w-auto"
          >
            <option value="">All Statuses</option>
            {["pending", "accepted", "in_progress", "under_review", "completed", "cancelled"].map(s => (
              <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
            ))}
          </FormSelect>
        </div>

        {loading ? (
          <LoadingOverlay text="Loading orders..." />
        ) : orders.length === 0 ? (
          <EmptyState
            icon={<Package />}
            title="No orders yet"
            description={role === "buyer" ? "Browse services to place your first order." : "Create a service to start receiving orders."}
          />
        ) : (
          <div className="flex flex-col gap-3">
            {orders.map(o => {
              const c = STATUS_COLORS[o.status] || "#475569";
              return (
                <Card key={o.id} to={`/academic-marketplace/orders/${o.id}`} padding="md">
                  <div className="flex items-center gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="text-[15px] font-semibold text-navy-700 mb-1">{o.service_title}</div>
                      <div className="text-[13px] text-slate-600 flex gap-3">
                        <span className="capitalize">{o.package_tier} Package</span>
                        <span>·</span>
                        <span>${o.price?.toFixed(2)}</span>
                        <span>·</span>
                        <span>{new Date(o.updated_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <Badge color={c} className="capitalize shrink-0">
                      {o.status?.replace(/_/g, " ")}
                    </Badge>
                    <ChevronRight size={16} className="text-slate-500" />
                  </div>
                </Card>
              );
            })}
          </div>
        )}
    </ResearchLayout>
  );
}

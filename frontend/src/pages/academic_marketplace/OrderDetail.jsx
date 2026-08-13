import React, { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle, AlertCircle, Settings, FileText } from "lucide-react";
import { ACCENT, EMERALD, NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Button, Alert, Textarea, H2, H3, Caption, LoadingOverlay, ErrorState } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = "/api/acad-market";

const STATUS_COLORS = {
  pending: "#F59E0B", accepted: ACCENT, in_progress: "#0891B2",
  under_review: "#7C3AED", completed: EMERALD, cancelled: "#DC2626",
  declined: "#DC2626", revision_requested: "#D97706", disputed: "#DC2626",
};

export default function OrderDetail() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [contract, setContract] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [revNote, setRevNote] = useState("");
  const [msg, setMsg] = useState(null);

  const load = useCallback(() => {
    Promise.all([
      fetchApi(`${API}/orders/${id}`).then(r => r.json()),
      fetchApi(`${API}/contracts/${id}`).then(r => r.json()),
    ]).then(([o, c]) => {
      setOrder(o.error ? null : o);
      setContract(c.error ? null : c);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const transition = async (status, note = "") => {
    setActionLoading(true);
    const r = await fetchApi(`${API}/orders/${id}/transition`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status, note }),
    });
    const d = await r.json();
    if (d.error) setMsg({ type: "error", text: d.error });
    else { setOrder(d); setMsg(null); }
    setActionLoading(false);
  };

  const submitRevNote = async () => {
    if (!revNote.trim()) return;
    const r = await fetchApi(`${API}/orders/${id}/revision-notes`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ note: revNote }),
    });
    const d = await r.json();
    setOrder(d); setRevNote("");
  };

  if (loading) return <LoadingOverlay text="Loading..." />;
  if (!order) return <ErrorState type="not_found" message="Order not found." />;

  const statusColor = STATUS_COLORS[order.status] || "#475569";

  const canBuyerComplete = order.status === "under_review";
  const canBuyerRevision = order.status === "under_review" && order.revisions_used < order.revisions_allowed;

  return (
    <ResearchLayout
      title={`Order #${id.slice(-8).toUpperCase()}`}
      actions={
        <Badge color={statusColor} className="capitalize">
          {order.status?.replace(/_/g, " ")}
        </Badge>
      }
      sidebar={
        <OrderDetailSidebar
          order={order}
          id={id}
          contract={contract}
          actionLoading={actionLoading}
          transition={transition}
        />
      }
    >
      <div className="max-w-[900px]">
        {msg && (
          <Alert variant={msg.type === "error" ? "error" : "success"} style={{ marginBottom: 16 }}>
            {msg.text}
          </Alert>
        )}

        <div>
          {/* Order info */}
            <Card padding="lg" className="mb-4">
              <H2 className="mb-1">{order.service_title}</H2>
              <Caption className="capitalize mb-4">
                {order.category?.replace(/_/g, " ")} — {order.package_tier} Package
              </Caption>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Price", value: `$${order.price?.toFixed(2)}` },
                  { label: "Delivery Days", value: `${order.delivery_days} days` },
                  { label: "Revisions Used", value: `${order.revisions_used} / ${order.revisions_allowed}` },
                  { label: "Ordered", value: new Date(order.created_at).toLocaleDateString() },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <Caption className="mb-0.5">{label}</Caption>
                    <div className="text-sm font-semibold text-navy-700">{value}</div>
                  </div>
                ))}
              </div>
              {order.requirements && (
                <div className="mt-4 pt-4 border-t border-hairline">
                  <div className="text-[13px] font-semibold text-navy-700 mb-1.5">Requirements</div>
                  <div className="text-sm text-slate-600 leading-relaxed">{order.requirements}</div>
                </div>
              )}
            </Card>

            {/* Deliverables */}
            {order.deliverables?.length > 0 && (
              <Card padding="lg" className="mb-4">
                <H3 className="mb-3">Submitted Deliverables</H3>
                {order.deliverables.map((d, i) => (
                  <div key={i} className="border border-hairline rounded-md p-3.5 mb-2.5">
                    <div className="font-semibold text-navy-700 mb-1">{d.title}</div>
                    <div className="text-[13px] text-slate-600 mb-2">{d.description}</div>
                    {d.file_url && <a href={d.file_url} target="_blank" rel="noreferrer" className="text-[13px] text-crimson-600 no-underline">Download file →</a>}
                    <Caption className="mt-1.5">{new Date(d.submitted_at).toLocaleString()}</Caption>
                  </div>
                ))}
              </Card>
            )}

            {/* Buyer actions */}
            {(canBuyerComplete || canBuyerRevision) && (
              <Card padding="lg" className="mb-4">
                <H3 className="mb-3">Review Deliverable</H3>
                <div className="flex gap-2.5">
                  {canBuyerComplete && (
                    <Button
                      onClick={() => transition("completed", "Deliverable approved by buyer")}
                      disabled={actionLoading}
                      className="flex-1"
                      style={{ background: EMERALD }}
                    >
                      Approve & Complete
                    </Button>
                  )}
                  {canBuyerRevision && (
                    <Button
                      onClick={() => { if (revNote) transition("revision_requested", revNote); }}
                      disabled={actionLoading || !revNote}
                      className="flex-1"
                      style={{ background: "#D97706" }}
                    >
                      Request Revision
                    </Button>
                  )}
                </div>
                {canBuyerRevision && (
                  <Textarea
                    value={revNote}
                    onChange={e => setRevNote(e.target.value)}
                    placeholder="Describe what needs to be revised..."
                    rows={3}
                    resize={false}
                    wrapperClassName="mt-2.5"
                  />
                )}
              </Card>
            )}

            {/* Timeline */}
            <Card padding="lg">
              <H3 className="mb-3">Activity Timeline</H3>
              {(order.timeline || []).map((t, i) => (
                <div key={i} className="flex gap-3 mb-3">
                  <div className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ background: STATUS_COLORS[t.status] || "#475569" }} />
                  <div>
                    <div className="text-sm font-semibold text-navy-700 capitalize">{t.status?.replace(/_/g, " ")}</div>
                    <div className="text-[13px] text-slate-600">{t.note}</div>
                    <Caption>{new Date(t.at).toLocaleString()}</Caption>
                  </div>
                </div>
              ))}
            </Card>
        </div>
      </div>
    </ResearchLayout>
  );
}

// ── Right rail — order actions and contract status, already loaded above ──────
function OrderDetailSidebar({ order, id, contract, actionLoading, transition }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Settings size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Actions</div>
        </div>
        {order.status === "pending" && (
          <Button
            variant="danger"
            size="sm"
            onClick={() => transition("cancelled", "Cancelled by buyer")}
            disabled={actionLoading}
            className="w-full"
          >
            Cancel Order
          </Button>
        )}
        {order.status === "completed" && (
          <Button as={Link} to={`/academic-marketplace/rate/${id}`} size="sm" className="w-full">
            Leave a Review
          </Button>
        )}
        {["accepted", "in_progress", "under_review", "revision_requested"].includes(order.status) && (
          <Link
            to={`/academic-marketplace/disputes?order=${id}`}
            className="block text-center border border-crimson-600 text-crimson-600 rounded-md py-2.5 text-[13px] no-underline mt-2"
          >
            Open Dispute
          </Link>
        )}
        {order.status !== "pending" && order.status !== "completed" && !["accepted", "in_progress", "under_review", "revision_requested"].includes(order.status) && (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>No actions available for this order status.</p>
        )}
      </Card>

      {contract && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <FileText size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Contract</div>
          </div>
          <p style={{ fontSize: 12, color: "#64748B", margin: "0 0 10px", lineHeight: 1.5 }}>
            Status: <span style={{ color: EMERALD, fontWeight: 600 }}>{contract.status}</span>
          </p>
          <Button as={Link} to={`/academic-marketplace/contracts/${id}`} variant="ghost" size="sm" className="w-full">
            View Contract
          </Button>
        </Card>
      )}
    </div>
  );
}

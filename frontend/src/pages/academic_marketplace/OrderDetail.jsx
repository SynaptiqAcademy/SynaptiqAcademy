import React, { useState, useEffect } from "react";
import { CheckCircle, AlertCircle } from "lucide-react";
import { ACCENT, EMERALD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Button, Alert, Textarea, H2, H3, Caption, LoadingOverlay, ErrorState } from "@/components/ds";

const API = "/api/acad-market";

const STATUS_COLORS = {
  pending: "#F59E0B", accepted: ACCENT, in_progress: "#0891B2",
  under_review: "#7C3AED", completed: EMERALD, cancelled: "#DC2626",
  declined: "#DC2626", revision_requested: "#D97706", disputed: "#DC2626",
};

export default function OrderDetail() {
  const id = window.location.pathname.split("/").pop();
  const [order, setOrder] = useState(null);
  const [contract, setContract] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [revNote, setRevNote] = useState("");
  const [msg, setMsg] = useState(null);

  const load = () => {
    Promise.all([
      fetch(`${API}/orders/${id}`).then(r => r.json()),
      fetch(`${API}/contracts/${id}`).then(r => r.json()),
    ]).then(([o, c]) => {
      setOrder(o.error ? null : o);
      setContract(c.error ? null : c);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const transition = async (status, note = "") => {
    setActionLoading(true);
    const r = await fetch(`${API}/orders/${id}/transition`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status, note }),
    });
    const d = await r.json();
    if (d.error) setMsg({ type: "error", text: d.error });
    else { setOrder(d); setMsg(null); }
    setActionLoading(false);
  };

  const submitRevNote = async () => {
    if (!revNote.trim()) return;
    const r = await fetch(`${API}/orders/${id}/revision-notes`, {
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
    >
      <div className="max-w-[900px]">
        {msg && (
          <Alert variant={msg.type === "error" ? "error" : "success"} style={{ marginBottom: 16 }}>
            {msg.text}
          </Alert>
        )}

        <div className="grid grid-cols-[1fr_280px] gap-5">
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

          {/* Sidebar */}
          <div>
            <Card padding="md" className="mb-4">
              <H3 className="mb-3">Actions</H3>
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
                <Button as="a" href={`/academic-marketplace/rate/${id}`} size="sm" className="w-full">
                  Leave a Review
                </Button>
              )}
              {["accepted", "in_progress", "under_review", "revision_requested"].includes(order.status) && (
                <a
                  href={`/academic-marketplace/disputes/new?order=${id}`}
                  className="block text-center border border-crimson-600 text-crimson-600 rounded-md py-2.5 text-[13px] no-underline mt-2"
                >
                  Open Dispute
                </a>
              )}
            </Card>

            {contract && (
              <Card padding="md">
                <H3 className="mb-2">Contract</H3>
                <div className="text-[13px] text-slate-600 mb-2.5">
                  Status: <span className="text-emerald-600 font-semibold">{contract.status}</span>
                </div>
                <Button as="a" href={`/academic-marketplace/contracts/${id}`} variant="ghost" size="sm" className="w-full">
                  View Contract
                </Button>
              </Card>
            )}
          </div>
        </div>
      </div>
    </ResearchLayout>
  );
}

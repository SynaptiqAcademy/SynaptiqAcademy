import React, { useState, useEffect } from "react";
import { AlertCircle, ChevronRight, MessageSquare } from "lucide-react";
import { EMERALD, ACCENT } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Button, Alert, Input, Textarea, FormSelect, EmptyState, LoadingOverlay, Badge, H2, Caption } from "@/components/ds";

const API = "/api/acad-market";

const REASON_LABELS = {
  work_not_delivered: "Work Not Delivered",
  quality_below_expectations: "Quality Below Expectations",
  scope_mismatch: "Scope Mismatch",
  communication_breakdown: "Communication Breakdown",
  late_delivery: "Late Delivery",
  unauthorized_charges: "Unauthorized Charges",
  deliverable_inaccurate: "Inaccurate Deliverable",
  plagiarism_concern: "Plagiarism Concern",
  data_misuse: "Data Misuse",
  other: "Other",
};

const STATUS_COLORS = { open: "#F59E0B", evidence_submitted: "#0891B2", under_review: "#7C3AED", resolved_buyer: EMERALD, resolved_provider: ACCENT, resolved_mutual: EMERALD, closed: "#94A3B8", disputed: "#DC2626" };

export default function DisputeCenter() {
  const [disputes, setDisputes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(new URLSearchParams(window.location.search).has("order"));
  const [newForm, setNewForm] = useState({
    order_id: new URLSearchParams(window.location.search).get("order") || "",
    reason: "other", description: "", desired_resolution: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    fetch(`${API}/disputes`).then(r => r.json()).then(d => {
      setDisputes(Array.isArray(d) ? d : []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const submit = async () => {
    setSubmitting(true);
    const r = await fetch(`${API}/disputes`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newForm),
    });
    const d = await r.json();
    if (d.error) { setMsg({ type: "error", text: d.error }); setSubmitting(false); }
    else { setDisputes(prev => [d, ...prev]); setShowNew(false); setMsg(null); setSubmitting(false); }
  };

  return (
    <ResearchLayout
      title="Dispute Center"
      actions={
        <Button variant={showNew ? "ghost" : "primary"} onClick={() => setShowNew(!showNew)}>
          {showNew ? "Cancel" : "Open Dispute"}
        </Button>
      }
    >

        {msg && (
          <Alert variant="error" style={{ marginBottom: 16 }}>
            {msg.text}
          </Alert>
        )}

        {showNew && (
          <Card padding="lg" className="mb-6">
            <H2 className="mb-4">Open a Dispute</H2>
            <div className="mb-4">
              <Input
                label="Order ID"
                value={newForm.order_id}
                onChange={e => setNewForm(f => ({ ...f, order_id: e.target.value }))}
                placeholder="Paste order ID"
              />
            </div>
            <div className="mb-4">
              <FormSelect
                label="Reason"
                value={newForm.reason}
                onChange={e => setNewForm(f => ({ ...f, reason: e.target.value }))}
              >
                {Object.entries(REASON_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </FormSelect>
            </div>
            <div className="mb-4">
              <Textarea
                label="Description"
                value={newForm.description}
                onChange={e => setNewForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Describe the issue in detail..."
                rows={4}
              />
            </div>
            <div className="mb-5">
              <Input
                label="Desired Resolution"
                value={newForm.desired_resolution}
                onChange={e => setNewForm(f => ({ ...f, desired_resolution: e.target.value }))}
                placeholder="What outcome do you want?"
              />
            </div>
            <Button onClick={submit} disabled={submitting || !newForm.order_id} loading={submitting}>
              {submitting ? "Submitting..." : "Submit Dispute"}
            </Button>
          </Card>
        )}

        {loading ? (
          <LoadingOverlay text="Loading disputes..." />
        ) : disputes.length === 0 ? (
          <EmptyState icon={<MessageSquare />} title="No disputes" />
        ) : (
          <div className="flex flex-col gap-2.5">
            {disputes.map(d => {
              const c = STATUS_COLORS[d.status] || "#475569";
              return (
                <Card key={d.id} to={`/academic-marketplace/disputes/${d.id}`} padding="md">
                  <div className="flex items-center gap-4">
                    <AlertCircle size={16} style={{ color: c }} />
                    <div className="flex-1">
                      <div className="text-sm font-semibold text-navy-700">{REASON_LABELS[d.reason] || d.reason}</div>
                      <Caption className="mt-0.5">Order {d.order_id?.slice(-8)?.toUpperCase()} · {new Date(d.opened_at).toLocaleDateString()}</Caption>
                    </div>
                    <Badge color={c} className="capitalize shrink-0">
                      {d.status?.replace(/_/g, " ")}
                    </Badge>
                    <ChevronRight size={14} className="text-slate-500" />
                  </div>
                </Card>
              );
            })}
          </div>
        )}
    </ResearchLayout>
  );
}

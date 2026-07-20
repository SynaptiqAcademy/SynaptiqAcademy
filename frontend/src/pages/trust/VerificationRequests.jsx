/* eslint-disable */
import React, { useEffect, useState } from "react";
import { FileSearch, Upload } from "lucide-react";
import { NAVY, EMERALD, ACCENT, TEXT_SECONDARY } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Button, FormSelect, Textarea, Badge, EmptyState, InlineError, LoadingOverlay } from "@/components/ds";

const API = "/api/trust";

const STATUS_COLORS = {
  pending_review:   "#D97706",
  approved:         EMERALD,
  rejected:         ACCENT,
  auto_approved:    EMERALD,
  more_info_needed: "#0369A1",
};

export default function VerificationRequests() {
  const [requests, setRequests] = useState([]);
  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ verification_type: "", notes: "" });
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      fetch(API + "/requests", { credentials: "include" }).then(r => r.json()),
      fetch(API + "/verifications/types", { credentials: "include" }).then(r => r.json()),
    ]).then(([reqs, ts]) => {
      setRequests(reqs || []);
      setTypes(ts || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.verification_type) { setError("Please select a verification type."); return; }
    setSubmitting(true);
    setError("");
    const r = await fetch(API + "/requests", {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ verification_type: form.verification_type, notes: form.notes, payload: {} }),
    });
    if (r.ok) {
      const req = await r.json();
      setRequests(prev => [req, ...prev]);
      setForm({ verification_type: "", notes: "" });
      setShowForm(false);
    } else {
      setError("Submission failed. Please try again.");
    }
    setSubmitting(false);
  };

  const appeal = async (reqId) => {
    const notes = window.prompt("Describe why this decision should be reconsidered:");
    if (!notes) return;
    await fetch(API + `/requests/${reqId}/appeal`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notes }),
    });
    setRequests(prev => prev.map(r => r._id === reqId ? { ...r, status: "pending_review" } : r));
  };

  return (
    <ResearchLayout
      title="Verification Requests"
      subtitle="Submit evidence for manual admin review"
      actions={
        <Button onClick={() => setShowForm(!showForm)}>
          <Upload size={14} /> New Request
        </Button>
      }
    >
      {/* New request form */}
      {showForm && (
        <Card padding="lg" style={{ marginBottom: 20 }}>
          <form onSubmit={submit}>
            <div style={{ fontSize: 14, fontWeight: 600, color: NAVY, marginBottom: 14 }}>
              Submit Verification Request
            </div>
            {error && <InlineError style={{ marginBottom: 12 }}>{error}</InlineError>}
            <div style={{ marginBottom: 14 }}>
              <FormSelect
                label="Verification Type"
                value={form.verification_type}
                onChange={e => setForm(p => ({ ...p, verification_type: e.target.value }))}
              >
                <option value="">Select type…</option>
                {types.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
              </FormSelect>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Textarea
                label="Supporting Notes"
                value={form.notes}
                onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
                rows={3}
                placeholder="Describe the evidence you are providing…"
              />
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Submitting…" : "Submit Request"}
              </Button>
              <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <LoadingOverlay text="Loading…" />
      ) : requests.length === 0 ? (
        <EmptyState icon={<FileSearch />} title="No verification requests yet." />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {requests.map(req => (
            <Card key={req._id} padding="md">
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontWeight: 600, color: NAVY, fontSize: 14 }}>{req.label}</span>
                <Badge color={STATUS_COLORS[req.status] || "#666"}>
                  {req.status?.replace(/_/g, " ")}
                </Badge>
              </div>
              {req.ai_notes && (
                <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: "0 0 6px" }}>
                  AI: {req.ai_notes}
                </p>
              )}
              {req.admin_notes && (
                <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: "0 0 6px" }}>
                  Admin: {req.admin_notes}
                </p>
              )}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 6 }}>
                <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>
                  Submitted {req.submitted_at ? new Date(req.submitted_at).toLocaleDateString() : "—"}
                </span>
                {req.status === "rejected" && (
                  <Button size="sm" variant="outline" onClick={() => appeal(req._id)}>
                    Appeal
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </ResearchLayout>
  );
}

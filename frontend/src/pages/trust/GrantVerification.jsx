/* eslint-disable */
import React, { useEffect, useState } from "react";
import { BadgeDollarSign, CheckCircle2, Upload } from "lucide-react";
import { NAVY } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Input, Textarea, Button, Alert } from "@/components/ds";

const API = "/api/trust";

export default function GrantVerification() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ grant_title: "", grant_ref: "", funder: "", role: "", notes: "" });
  const [message, setMessage] = useState({ text: "", ok: true });

  useEffect(() => {
    fetch(API + "/verifications", { credentials: "include" })
      .then(r => r.json())
      .then(list => {
        setStatus((list || []).find(v => v.verification_type === "grant_participation") || null);
        setLoading(false);
      }).catch(() => setLoading(false));
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage({ text: "", ok: true });
    const r = await fetch(API + "/verify/grant", {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    if (r.ok) {
      const d = await r.json();
      const ok = d.status === "verified" || d.status === "pending_review";
      setMessage({
        text: d.status === "verified"
          ? "Grant verified from platform records."
          : "Request submitted for admin review.",
        ok,
      });
      if (d.status === "verified") setStatus(d);
    } else {
      setMessage({ text: "Submission failed. Try again.", ok: false });
    }
    setSubmitting(false);
  };

  return (
    <ResearchLayout
      title="Grant Verification"
      subtitle="Verify grant participation and funding roles"
      icon={<BadgeDollarSign size={22} color={NAVY} />}
    >
      {status?.status === "verified" && (
        <Alert variant="success" icon={CheckCircle2} style={{ marginBottom: 20 }}>
          <strong>Grant Participation Verified ({status.confidence}%)</strong>
        </Alert>
      )}

      <Card padding="lg">
        <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 14 }}>
          Submit Grant Details
        </div>
        {message.text && (
          <Alert variant={message.ok ? "success" : "error"} style={{ marginBottom: 12 }}>
            {message.text}
          </Alert>
        )}
        <form onSubmit={submit}>
          {[
            { key: "grant_title", label: "Grant Title", placeholder: "AI in Healthcare Research" },
            { key: "grant_ref",   label: "Grant Reference / ID", placeholder: "EP/X000001/1" },
            { key: "funder",      label: "Funder",               placeholder: "EPSRC / NIH / Horizon Europe" },
            { key: "role",        label: "Your Role",             placeholder: "Principal Investigator / Co-I" },
          ].map(f => (
            <div key={f.key} style={{ marginBottom: 12 }}>
              <Input
                label={f.label}
                value={form[f.key]}
                onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                placeholder={f.placeholder}
              />
            </div>
          ))}
          <div style={{ marginBottom: 16 }}>
            <Textarea
              label="Additional Notes"
              value={form.notes}
              onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
              rows={2}
              placeholder="Any additional context for the reviewer…"
            />
          </div>
          <Button type="submit" disabled={submitting}>
            <Upload size={14} />
            {submitting ? "Submitting…" : "Submit for Verification"}
          </Button>
        </form>
      </Card>
    </ResearchLayout>
  );
}

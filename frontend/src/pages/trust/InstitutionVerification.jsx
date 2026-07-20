/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Building2, CheckCircle2, Upload } from "lucide-react";
import { NAVY, TEXT_SECONDARY } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Input, Textarea, Button, Alert } from "@/components/ds";

const API = "/api/trust";

export default function InstitutionVerification() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ institution: "", department: "", position: "", notes: "" });
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch(API + "/verifications?status=verified", { credentials: "include" })
      .then(r => r.json())
      .then(list => {
        const inst = list.find(v => v.verification_type === "institution_affiliation");
        setStatus(inst || null);
        setLoading(false);
      }).catch(() => setLoading(false));
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage("");
    const r = await fetch(API + "/verify/institution", {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    if (r.ok) {
      const d = await r.json();
      setMessage(d.status === "verified" ? "Institution verified successfully." : "Request submitted for admin review.");
      setStatus(d);
    } else {
      setMessage("Submission failed. Please try again.");
    }
    setSubmitting(false);
  };

  return (
    <ResearchLayout
      title="Institution Verification"
      subtitle="Verify your institutional affiliation"
      icon={<Building2 size={22} color={NAVY} />}
    >
      {!loading && status?.status === "verified" && (
        <Alert variant="success" icon={CheckCircle2} style={{ marginBottom: 20 }}>
          <strong>Institution Verified</strong>
          <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 2 }}>
            Confidence: {status.confidence}% · Expires {status.expires_at ? new Date(status.expires_at).toLocaleDateString() : "—"}
          </div>
        </Alert>
      )}

      <Card padding="lg">
        <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 16 }}>
          Submit Institution Details
        </div>
        {message && (
          <Alert variant={message.includes("failed") ? "error" : "success"} style={{ marginBottom: 12 }}>
            {message}
          </Alert>
        )}
        <form onSubmit={submit}>
          {[
            { key: "institution", label: "Institution Name", placeholder: "University of Oxford" },
            { key: "department",  label: "Department",        placeholder: "Department of Computer Science" },
            { key: "position",    label: "Position / Title",  placeholder: "Postdoctoral Research Associate" },
          ].map(f => (
            <div key={f.key} style={{ marginBottom: 14 }}>
              <Input
                label={f.label}
                value={form[f.key]}
                onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                placeholder={f.placeholder}
              />
            </div>
          ))}
          <div style={{ marginBottom: 18 }}>
            <Textarea
              label="Supporting Notes"
              value={form.notes}
              onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
              rows={3}
              placeholder="Provide any additional evidence or context…"
            />
          </div>
          <Button type="submit" disabled={submitting}>
            <Upload size={14} />
            {submitting ? "Submitting…" : "Submit for Verification"}
          </Button>
        </form>
      </Card>

      <Card padding="md" style={{ marginTop: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: NAVY, marginBottom: 8 }}>
          How it works
        </div>
        <ol style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: TEXT_SECONDARY, lineHeight: 1.8 }}>
          <li>Submit your institution name, department and position</li>
          <li>Our AI checks your institutional email domain</li>
          <li>If auto-check is insufficient, an admin reviews your submission</li>
          <li>Verification issued with confidence score and 12-month expiry</li>
        </ol>
      </Card>
    </ResearchLayout>
  );
}

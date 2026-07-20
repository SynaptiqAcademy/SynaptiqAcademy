/* eslint-disable */
import React, { useEffect, useState } from "react";
import { UserCheck, CheckCircle2, RefreshCw } from "lucide-react";
import { NAVY, BRD, TEXT_SECONDARY } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Button, Alert } from "@/components/ds";

const API = "/api/trust";

export default function ReviewerVerification() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState({ text: "", ok: true });

  useEffect(() => {
    fetch(API + "/verifications", { credentials: "include" })
      .then(r => r.json())
      .then(list => {
        setStatus((list || []).find(v => v.verification_type === "reviewer_activity") || null);
        setLoading(false);
      }).catch(() => setLoading(false));
  }, []);

  const verify = async () => {
    setRunning(true);
    setMessage({ text: "", ok: true });
    const r = await fetch(API + "/verify/reviewer", { method: "POST", credentials: "include" });
    if (r.ok) {
      const d = await r.json();
      setStatus(d);
      setMessage({
        text: d.status === "verified"
          ? `Verified! ${d.confidence}% confidence based on your review activity.`
          : "You need at least 3 completed reviews. Keep reviewing and try again.",
        ok: d.status === "verified",
      });
    } else {
      setMessage({ text: "Check failed. Try again later.", ok: false });
    }
    setRunning(false);
  };

  return (
    <ResearchLayout
      title="Reviewer Verification"
      subtitle="Verified peer review activity on Synaptiq"
      icon={<UserCheck size={22} color={NAVY} />}
    >
      {status?.status === "verified" && (
        <Alert variant="success" icon={CheckCircle2} style={{ marginBottom: 20 }}>
          <strong>Reviewer Activity Verified</strong>
          <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 2 }}>
            Confidence: {status.confidence}% · Source: {status.source}
          </div>
        </Alert>
      )}

      <Card padding="lg">
        <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 10 }}>
          Reviewer Verification
        </div>
        <p style={{ fontSize: 13, color: TEXT_SECONDARY, margin: "0 0 16px" }}>
          This check verifies that you have completed <strong>3 or more peer reviews</strong> on the
          Synaptiq platform. Verification is automatic — no evidence upload required.
        </p>

        {message.text && (
          <Alert variant={message.ok ? "success" : "error"} style={{ marginBottom: 14 }}>
            {message.text}
          </Alert>
        )}

        <Button onClick={verify} disabled={running || loading}>
          <RefreshCw size={14} style={{ animation: running ? "spin 1s linear infinite" : "none" }} />
          {running ? "Checking…" : "Run Verification Check"}
        </Button>

        <div style={{ marginTop: 20, paddingTop: 16, borderTop: `1px solid ${BRD}` }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: NAVY, marginBottom: 6 }}>Requirements</div>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: TEXT_SECONDARY, lineHeight: 1.8 }}>
            <li>Minimum 3 completed peer reviews</li>
            <li>Reviews must be on the Synaptiq platform</li>
            <li>Auto-verified from platform data — no documents needed</li>
            <li>Verification valid for 12 months</li>
          </ul>
        </div>
      </Card>
    </ResearchLayout>
  );
}

/* eslint-disable */
import React, { useEffect, useState } from "react";
import { FileText, CheckCircle2, Search } from "lucide-react";
import { NAVY, BRD, EMERALD, TEXT_SECONDARY } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Input, Button, Alert, EmptyState, LoadingOverlay } from "@/components/ds";

const API = "/api/trust";

export default function PublicationVerification() {
  const [verified, setVerified] = useState([]);
  const [loading, setLoading] = useState(true);
  const [doi, setDoi] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState({ text: "", ok: true });

  useEffect(() => {
    fetch(API + "/verifications", { credentials: "include" })
      .then(r => r.json())
      .then(list => {
        setVerified((list || []).filter(v => ["doi", "publication"].includes(v.verification_type)));
        setLoading(false);
      }).catch(() => setLoading(false));
  }, []);

  const verifyDoi = async (e) => {
    e.preventDefault();
    if (!doi.trim()) return;
    setSubmitting(true);
    setMessage({ text: "", ok: true });
    const r = await fetch(API + "/verify/publication", {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doi: doi.trim() }),
    });
    if (r.ok) {
      const d = await r.json();
      const ok = d.status === "verified";
      setMessage({ text: ok ? `DOI verified (${d.confidence}% confidence).` : `Auto-check complete. Status: ${d.status}.`, ok });
      if (ok) setVerified(prev => [d, ...prev.filter(v => v.verification_type !== "doi")]);
      setDoi("");
    } else {
      setMessage({ text: "Verification failed. Check the DOI and try again.", ok: false });
    }
    setSubmitting(false);
  };

  return (
    <ResearchLayout
      title="Publication Verification"
      subtitle="Verify authorship via DOI — CrossRef + OpenAlex"
      icon={<FileText size={22} color={NAVY} />}
    >
      {/* DOI form */}
      <Card padding="lg" style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 14 }}>
          Verify a DOI
        </div>
        {message.text && (
          <Alert variant={message.ok ? "success" : "error"} style={{ marginBottom: 12 }}>
            {message.text}
          </Alert>
        )}
        <form onSubmit={verifyDoi} style={{ display: "flex", gap: 10 }}>
          <Input
            value={doi}
            onChange={e => setDoi(e.target.value)}
            placeholder="10.1038/s41586-021-04337-x"
            wrapperClassName="flex-1"
          />
          <Button type="submit" disabled={submitting || !doi.trim()}>
            <Search size={14} />
            {submitting ? "Checking…" : "Verify"}
          </Button>
        </form>
        <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: "10px 0 0" }}>
          We check CrossRef and OpenAlex for authorship. Your name must appear on the paper.
        </p>
      </Card>

      {/* Verified list */}
      <Card padding="lg">
        <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 12 }}>
          Verified Publications ({verified.length})
        </div>
        {loading ? (
          <LoadingOverlay text="Loading…" />
        ) : verified.length === 0 ? (
          <EmptyState title="No verified publications yet. Enter a DOI above to get started." />
        ) : (
          verified.map((v, i) => (
            <div key={v._id || i} style={{
              display: "flex", alignItems: "flex-start", gap: 10,
              padding: "10px 0", borderBottom: i < verified.length - 1 ? `1px solid ${BRD}` : "none",
            }}>
              <CheckCircle2 size={16} color={EMERALD} style={{ flexShrink: 0, marginTop: 1 }} />
              <div>
                <div style={{ fontSize: 13, color: NAVY, fontWeight: 500 }}>
                  {v.extra?.title || v.extra?.doi || "Publication"}
                </div>
                <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 2 }}>
                  DOI: {v.extra?.doi || "—"} · {v.confidence}% confidence · via {v.source}
                </div>
              </div>
            </div>
          ))
        )}
      </Card>
    </ResearchLayout>
  );
}

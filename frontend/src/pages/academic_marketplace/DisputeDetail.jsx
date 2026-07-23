import React, { useState, useEffect, useCallback } from "react";
import { ResearchLayout } from "@/layouts";
import { ACCENT } from "@/lib/tokens";
import { Card, H3, Caption, Input, Textarea, Button, LoadingOverlay, ErrorState } from "@/components/ds";

const API = "/api/acad-market";

export default function DisputeDetail() {
  const id = window.location.pathname.split("/").pop();
  const [dispute, setDispute] = useState(null);
  const [loading, setLoading] = useState(true);
  const [msgText, setMsgText] = useState("");
  const [evidTitle, setEvidTitle] = useState("");
  const [evidContent, setEvidContent] = useState("");
  const [sending, setSending] = useState(false);

  const load = useCallback(() => {
    fetch(`${API}/disputes/${id}`).then(r => r.json()).then(d => {
      setDispute(d.error ? null : d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const sendMsg = async () => {
    if (!msgText.trim()) return;
    setSending(true);
    const r = await fetch(`${API}/disputes/${id}/messages`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: msgText }),
    });
    const d = await r.json();
    setDispute(d); setMsgText(""); setSending(false);
  };

  const addEvidence = async () => {
    if (!evidContent.trim()) return;
    setSending(true);
    const r = await fetch(`${API}/disputes/${id}/evidence`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: evidTitle, content: evidContent, type: "statement" }),
    });
    const d = await r.json();
    setDispute(d); setEvidTitle(""); setEvidContent(""); setSending(false);
  };

  if (loading) return <LoadingOverlay text="Loading..." />;
  if (!dispute) return <ErrorState type="not_found" message="Dispute not found." />;

  const isClosed = ["resolved_buyer", "resolved_provider", "resolved_mutual", "closed"].includes(dispute.status);

  return (
    <ResearchLayout
      title={`Dispute #${id.slice(-8).toUpperCase()}`}
      subtitle={`Order: ${dispute.order_id?.slice(-8)?.toUpperCase()} · Opened ${new Date(dispute.opened_at).toLocaleDateString()}`}
    >
      <div className="max-w-[800px]">
        {/* Status */}
        <Card padding="lg" className="mb-4">
          <div className="flex justify-between items-center">
            <div>
              <Caption className="mb-0.5">Status</Caption>
              <div className="text-[15px] font-bold text-navy-700 capitalize">{dispute.status?.replace(/_/g, " ")}</div>
            </div>
            <div>
              <Caption className="mb-0.5">Reason</Caption>
              <div className="text-sm font-semibold text-navy-700">{dispute.reason?.replace(/_/g, " ")?.replace(/\b\w/g, l => l.toUpperCase())}</div>
            </div>
          </div>
          {dispute.resolution_note && (
            <div className="mt-4 pt-4 border-t border-hairline text-sm text-slate-600">
              <strong className="text-navy-700">Resolution: </strong>{dispute.resolution_note}
            </div>
          )}
        </Card>

        {/* Evidence */}
        {dispute.evidence?.length > 0 && (
          <Card padding="lg" className="mb-4">
            <H3 className="mb-3">Evidence Submitted</H3>
            {dispute.evidence.map((e, i) => (
              <div key={i} className="border border-hairline rounded-md p-3.5 mb-2">
                <div className="font-semibold text-navy-700 text-sm mb-1">{e.title}</div>
                <div className="text-[13px] text-slate-600 leading-normal">{e.content}</div>
                <Caption className="mt-1.5">{new Date(e.submitted_at).toLocaleString()}</Caption>
              </div>
            ))}
          </Card>
        )}

        {/* Messages */}
        <Card padding="lg" className="mb-4">
          <H3 className="mb-3">Messages</H3>
          <div className="max-h-[300px] overflow-y-auto mb-4">
            {(dispute.messages || []).map((m, i) => (
              <div
                key={i}
                className="mb-3 px-3.5 py-2.5 rounded-md border border-hairline"
                style={{ background: m.is_system ? "#F4F6FA" : (m.from === dispute.claimant_user_id ? ACCENT + "12" : "#FFFFFF") }}
              >
                <Caption className="mb-1">
                  {m.is_system ? "System" : m.from === dispute.claimant_user_id ? "You (Claimant)" : "Respondent"} · {new Date(m.at).toLocaleString()}
                </Caption>
                <div className="text-sm text-navy-700">{m.text}</div>
              </div>
            ))}
          </div>
          {!isClosed && (
            <div>
              <Textarea
                value={msgText}
                onChange={e => setMsgText(e.target.value)}
                placeholder="Add a message..."
                rows={3}
                resize={false}
                wrapperClassName="mb-2"
              />
              <Button onClick={sendMsg} disabled={sending || !msgText.trim()}>
                Send
              </Button>
            </div>
          )}
        </Card>

        {/* Add Evidence */}
        {!isClosed && (
          <Card padding="lg">
            <H3 className="mb-3">Submit Evidence</H3>
            <Input
              value={evidTitle}
              onChange={e => setEvidTitle(e.target.value)}
              placeholder="Evidence title"
              wrapperClassName="mb-2.5"
            />
            <Textarea
              value={evidContent}
              onChange={e => setEvidContent(e.target.value)}
              placeholder="Describe your evidence..."
              rows={4}
              wrapperClassName="mb-2.5"
            />
            <Button variant="danger" onClick={addEvidence} disabled={sending || !evidContent.trim()}>
              Submit Evidence
            </Button>
          </Card>
        )}
      </div>
    </ResearchLayout>
  );
}

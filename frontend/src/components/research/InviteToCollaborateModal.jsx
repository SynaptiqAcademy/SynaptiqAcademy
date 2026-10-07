/**
 * P1 Phase 8E — Structured Collaboration Requests.
 *
 * "Invite to Collaborate" composer, opened from a Research Need result
 * card. Pre-fills from Phase 8D's evidence/contribution intelligence but
 * never auto-sends — the human reviews and can edit every field before
 * submitting. Posts to the existing, canonical POST /collaboration-requests
 * (no new invitation mechanism).
 */
import React, { useState } from "react";
import api from "@/lib/api";
import { NAVY, TEXT_SECONDARY, TEXT_MUTED, BRD } from "@/lib/tokens";
import { Modal } from "@/components/ds/Modal";
import { Button } from "@/components/ds/Button";
import { FormSelect } from "@/components/ds/FormSelect";
import { Textarea } from "@/components/ds/Textarea";
import { safeErrorMessage } from "@/lib/api";

const PURPOSE_OPTIONS = [
  { value: "co_author_paper", label: "Co-author a paper" },
  { value: "join_research_project", label: "Join a research project" },
  { value: "grant_proposal", label: "Grant proposal" },
  { value: "methodological_support", label: "Methodological support" },
  { value: "data_analysis_support", label: "Data analysis / technical support" },
  { value: "peer_review", label: "Peer review / feedback" },
  { value: "policy_research", label: "Policy research" },
  { value: "research_consultation", label: "Research consultation" },
  { value: "domain_expertise", label: "Literature / domain expertise" },
  { value: "conference_collaboration", label: "Conference collaboration" },
  { value: "teaching_collaboration", label: "Teaching / educational research collaboration" },
  { value: "other", label: "Other" },
];

// Deterministic, evidence-grounded draft — never fabricates familiarity and
// never claims the sender read a specific publication unless that's exactly
// what the evidence is (§7). Purely a starting point; always editable.
function draftMessage({ recipientName, topic, evidenceSummary, contribution }) {
  const firstName = (recipientName || "there").split(" ")[0];
  const lines = [`Hello ${firstName},`, ""];
  if (topic) {
    lines.push(`I'm working on a research project concerning ${topic}.`);
  } else {
    lines.push("I'm working on a research project and think you may be a relevant collaborator.");
  }
  if (evidenceSummary) {
    lines.push(`Your profile lists ${evidenceSummary}, which looks relevant here.`);
  }
  if (contribution) {
    lines.push(`In particular, I'd value your input on: ${contribution}.`);
  }
  lines.push("", "I'd like to invite you to explore a possible collaboration.");
  return lines.join("\n");
}

export default function InviteToCollaborateModal({ open, onClose, person, need }) {
  const [purpose, setPurpose] = useState("");
  const [contribution, setContribution] = useState(person?.contribution?.[0] || "");
  const [message, setMessage] = useState(() => draftMessage({
    recipientName: person?.name,
    topic: need?.concise_problem_statement || need?.original_query || "",
    evidenceSummary: (person?.evidence || []).slice(0, 2).map((e) => e.candidate_value).join(", "),
    contribution: person?.contribution?.[0] || "",
  }));
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  if (!person) return null;

  const topic = need?.concise_problem_statement || need?.original_query || "";

  const send = async () => {
    setSending(true);
    setError("");
    try {
      await api.post("/collaboration-requests", {
        receiver_id: person.id,
        message: message.trim(),
        source: "research_need",
        invitation_type: "research_collaboration",
        collaboration_purpose: purpose || null,
        expected_contribution: contribution.trim() || null,
        context: topic ? { research_need_topic: topic } : null,
      });
      setSent(true);
    } catch (e) {
      setError(safeErrorMessage(e, "Could not send this request. Please try again."));
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Invite ${person.name || "this researcher"} to collaborate`}
      size="md"
      footer={
        sent ? (
          <Button variant="primary" onClick={onClose}>Done</Button>
        ) : (
          <>
            <Button variant="ghost" onClick={onClose} disabled={sending}>Cancel</Button>
            <Button variant="primary" onClick={send} loading={sending}>Send collaboration request</Button>
          </>
        )
      }
    >
      {sent ? (
        <div style={{ fontSize: 13, color: TEXT_SECONDARY, lineHeight: 1.6 }}>
          Your collaboration request has been sent to {person.name}. You can track its status under Collaboration Requests.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {topic && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: TEXT_SECONDARY, textTransform: "uppercase", letterSpacing: 0.3, marginBottom: 3 }}>
                Research topic
              </div>
              <div style={{ fontSize: 12.5, color: TEXT_SECONDARY, padding: "6px 8px", background: "#F8FAFC", border: `1px solid ${BRD}` }}>
                {topic}
              </div>
            </div>
          )}

          <FormSelect label="Collaboration type" value={purpose} onChange={(e) => setPurpose(e.target.value)}>
            <option value="">Select a collaboration type…</option>
            {PURPOSE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </FormSelect>

          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: TEXT_SECONDARY, textTransform: "uppercase", letterSpacing: 0.3, display: "block", marginBottom: 3 }}>
              Requested contribution
            </label>
            <Textarea rows={2} value={contribution} onChange={(e) => setContribution(e.target.value)} placeholder="What would you like this person to contribute?" />
          </div>

          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: TEXT_SECONDARY, textTransform: "uppercase", letterSpacing: 0.3, display: "block", marginBottom: 3 }}>
              Message
            </label>
            <Textarea rows={6} value={message} onChange={(e) => setMessage(e.target.value)} />
            <div style={{ fontSize: 10.5, color: TEXT_MUTED, marginTop: 3 }}>
              This is a suggested draft — please review and edit before sending.
            </div>
          </div>

          {person.available_for_collaboration === false && (
            <div style={{ fontSize: 11.5, color: "#92400E", background: "#FFFBEB", border: "1px solid #FDE68A", padding: "6px 8px" }}>
              This researcher has indicated they're not currently open to collaboration. You may still send a request, but they may be less likely to respond.
            </div>
          )}

          {error && <div style={{ fontSize: 12, color: "#B91C1C" }}>{error}</div>}
        </div>
      )}
    </Modal>
  );
}

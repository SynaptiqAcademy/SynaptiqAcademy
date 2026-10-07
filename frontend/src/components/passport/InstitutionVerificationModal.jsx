import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Search, Mail, FileText, CheckCircle2, Link2, ExternalLink } from "lucide-react";
import { Modal } from "@/components/ds/Modal";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { FormField } from "@/components/ds/Form";
import { NAVY, EMERALD, BRD, TEXT_SECONDARY, TEXT_MUTED, TEXT_PRIMARY, WARM } from "@/lib/tokens";
import api from "@/lib/api";
import { safeErrorMessage } from "@/lib/api";

const EVIDENCE_KINDS = [
  { value: "staff_page", label: "Official staff / profile page" },
  { value: "directory_page", label: "Institutional directory listing" },
  { value: "employment_letter", label: "Employment / appointment letter" },
  { value: "enrollment_evidence", label: "Student / doctoral enrollment evidence" },
  { value: "other", label: "Other official evidence" },
];

/**
 * fuzzyAffiliationMatch — deliberately simple, deliberately not authoritative.
 * P1 Phase 7C4.4 §D Method 3: ORCID affiliation is supporting evidence for a
 * human reviewer, never an auto-verification signal — so this only needs to
 * be good enough to surface a helpful hint, never good enough to be trusted
 * on its own (no fuzzy-matching library, no scoring, no auto-approval).
 */
function fuzzyAffiliationMatch(institutionName, employments = [], educations = []) {
  if (!institutionName) return null;
  const norm = (s) => (s || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  const target = norm(institutionName);
  if (!target) return null;
  const all = [...employments, ...educations];
  return all.find((e) => {
    const n = norm(e.institution);
    return n && (n.includes(target) || target.includes(n));
  }) || null;
}

/**
 * InstitutionVerificationModal — P1 Phase 7C4.4. Opens directly from the
 * Academic Passport (no navigation to a separate page — same pattern as
 * ORCID connect and Edit Identity). Three real, existing-architecture-backed
 * paths:
 *  - Method 1 (preferred): institutional email domain check against the
 *    institution's real email_domains, then a one-time confirmation link —
 *    POST /api/institutions/:iid/verify-email/start.
 *  - Method 2: manual evidence for admin review — POST /api/institutions/
 *    :iid/claim (institution known) or POST /verification/me/institution
 *    (institution not yet in the directory, free-text name).
 *  - Method 3: if the connected ORCID record's employment/education has a
 *    plausibly matching affiliation, shown as a supporting hint only — never
 *    auto-verifies anything.
 */
export function InstitutionVerificationModal({ open, onClose, profile, onSubmitted }) {
  const [query, setQuery] = useState(profile?.institution || "");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState(null);
  const [method, setMethod] = useState(null); // "email" | "evidence" | null
  const [email, setEmail] = useState("");
  const [evidenceKind, setEvidenceKind] = useState(EVIDENCE_KINDS[0].value);
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [emailSentTo, setEmailSentTo] = useState(null);
  const [evidenceSubmitted, setEvidenceSubmitted] = useState(false);

  useEffect(() => {
    if (!open) return;
    setQuery(profile?.institution || "");
    setResults([]); setSelected(null); setMethod(null);
    setEmail(""); setEvidenceUrl(""); setNotes("");
    setEmailSentTo(null); setEvidenceSubmitted(false);
  }, [open, profile?.institution]);

  useEffect(() => {
    if (!open || !query.trim()) { setResults([]); return; }
    setSearching(true);
    const t = setTimeout(() => {
      api.get("/institutions", { params: { q: query.trim(), limit: 6 } })
        .then((r) => setResults(r.data?.results || []))
        .catch(() => setResults([]))
        .finally(() => setSearching(false));
    }, 350);
    return () => clearTimeout(t);
  }, [query, open]);

  const orcidHint = useMemo(() => {
    if (!selected) return null;
    return fuzzyAffiliationMatch(selected.name, profile?.orcid_employments, profile?.orcid_educations);
  }, [selected, profile?.orcid_employments, profile?.orcid_educations]);

  if (!open) return null;

  const startEmailVerification = async () => {
    if (!email.trim() || !selected) return;
    setSubmitting(true);
    try {
      const { data } = await api.post(`/institutions/${selected.id}/verify-email/start`, { email: email.trim() });
      setEmailSentTo(data.sent_to_domain);
      toast.success("Verification email sent — check your inbox");
    } catch (e) {
      toast.error(safeErrorMessage(e, "Could not verify that email"));
    } finally {
      setSubmitting(false);
    }
  };

  const submitEvidence = async () => {
    setSubmitting(true);
    try {
      if (selected) {
        const { data } = await api.post(`/institutions/${selected.id}/claim`, {
          note: notes, evidence_kind: evidenceKind, evidence_url: evidenceUrl || undefined,
        });
        if (data.status === "approved") {
          toast.success("Institution verified");
        } else {
          toast.success("Submitted for admin review");
        }
      } else {
        await api.post("/verification/me/institution", {
          institution_name: query.trim(), department: "", role: "",
          evidence_kind: evidenceKind, evidence_url: evidenceUrl || undefined, notes,
        });
        toast.success("Submitted for admin review");
      }
      setEvidenceSubmitted(true);
      onSubmitted?.();
    } catch (e) {
      toast.error(safeErrorMessage(e, "Could not submit for review"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Verify your institution" size="md">
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {!selected && !evidenceSubmitted && (
          <>
            <FormField label="Your institution">
              <div style={{ position: "relative" }}>
                <Search size={13} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: TEXT_MUTED }} />
                <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search for your institution…" style={{ paddingLeft: 30 }} />
              </div>
            </FormField>

            {searching && <div style={{ fontSize: 12, color: TEXT_MUTED }}>Searching…</div>}

            {results.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {results.map((inst) => (
                  <button
                    key={inst.id}
                    onClick={() => setSelected(inst)}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8,
                      padding: "10px 12px", border: `1px solid ${BRD}`, borderRadius: 8, background: "#fff",
                      cursor: "pointer", textAlign: "left",
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: 600, color: TEXT_PRIMARY }}>{inst.name}</span>
                    <span style={{ fontSize: 11, color: TEXT_MUTED }}>{inst.country || ""}</span>
                  </button>
                ))}
              </div>
            )}

            {query.trim() && !searching && results.length === 0 && (
              <div style={{ fontSize: 12.5, color: TEXT_SECONDARY, padding: "10px 12px", background: WARM, borderRadius: 8, border: `1px solid ${BRD}` }}>
                We don't have "{query.trim()}" in our institution directory yet. You can still submit evidence below —
                Synaptiq will review it and add your institution.
                <div style={{ marginTop: 10 }}>
                  <Button size="sm" onClick={() => setMethod("evidence")}>
                    <FileText size={12} /> Submit affiliation evidence
                  </Button>
                </div>
              </div>
            )}
          </>
        )}

        {selected && !method && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY }}>{selected.name}</div>
            {orcidHint && (
              <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: EMERALD, background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: 8, padding: "8px 10px" }}>
                <Link2 size={12} /> Affiliation found in your connected ORCID record ({orcidHint.role || "affiliation"}
                {orcidHint.start_year ? `, ${orcidHint.start_year}–${orcidHint.end_year || "present"}` : ""}) — you can
                reference this as supporting evidence below.
              </div>
            )}
            {(selected.email_domains || []).length > 0 && (
              <button onClick={() => setMethod("email")} style={cardBtnStyle}>
                <Mail size={14} style={{ color: NAVY, flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY }}>Verify with institutional email</div>
                  <div style={{ fontSize: 11.5, color: TEXT_SECONDARY, marginTop: 2 }}>Recommended — fastest, confirmed automatically.</div>
                </div>
              </button>
            )}
            <button onClick={() => setMethod("evidence")} style={cardBtnStyle}>
              <FileText size={14} style={{ color: NAVY, flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY }}>I don't have an institutional email</div>
                <div style={{ fontSize: 11.5, color: TEXT_SECONDARY, marginTop: 2 }}>Submit evidence for a Synaptiq admin to review.</div>
              </div>
            </button>
            <button onClick={() => setSelected(null)} style={{ fontSize: 12, color: TEXT_MUTED, background: "none", border: "none", cursor: "pointer", padding: 0, alignSelf: "flex-start" }}>
              ← Choose a different institution
            </button>
          </div>
        )}

        {selected && method === "email" && !emailSentTo && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <FormField label={`Your ${selected.name} email address`} hint={`Must end in one of: ${(selected.email_domains || []).map((d) => "@" + d).join(", ")}`}>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@institution-domain" />
            </FormField>
            <div style={{ display: "flex", gap: 8 }}>
              <Button onClick={startEmailVerification} loading={submitting} disabled={!email.trim()}>Send verification link</Button>
              <Button variant="ghost" onClick={() => setMethod(null)}>Back</Button>
            </div>
          </div>
        )}

        {emailSentTo && (
          <div style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "12px 14px", background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: 10 }}>
            <CheckCircle2 size={16} style={{ color: EMERALD, flexShrink: 0, marginTop: 1 }} />
            <div style={{ fontSize: 13, color: TEXT_PRIMARY }}>
              We sent a confirmation link to your @{emailSentTo} address. Click it to confirm — your Passport will
              update automatically, no need to come back here.
            </div>
          </div>
        )}

        {method === "evidence" && !evidenceSubmitted && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {selected && orcidHint && (
              <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: EMERALD, background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: 8, padding: "8px 10px" }}>
                <Link2 size={12} /> Affiliation found in your connected ORCID record — mention this below if helpful.
              </div>
            )}
            <FormField label="Evidence type">
              <FormSelect value={evidenceKind} onChange={(e) => setEvidenceKind(e.target.value)}>
                {EVIDENCE_KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
              </FormSelect>
            </FormField>
            <FormField label="Link to evidence" hint="e.g. your official staff/profile page or directory listing">
              <Input value={evidenceUrl} onChange={(e) => setEvidenceUrl(e.target.value)} placeholder="https://" />
            </FormField>
            <FormField label="Additional notes (optional)">
              <Textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Anything that helps a reviewer confirm your affiliation…" />
            </FormField>
            <div style={{ display: "flex", gap: 8 }}>
              <Button onClick={submitEvidence} loading={submitting}>Submit for review</Button>
              <Button variant="ghost" onClick={() => setMethod(null)} disabled={!selected}>Back</Button>
            </div>
          </div>
        )}

        {evidenceSubmitted && (
          <div style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "12px 14px", background: WARM, border: `1px solid ${BRD}`, borderRadius: 10 }}>
            <CheckCircle2 size={16} style={{ color: NAVY, flexShrink: 0, marginTop: 1 }} />
            <div style={{ fontSize: 13, color: TEXT_PRIMARY }}>
              Submitted. A Synaptiq admin will review your evidence — your Institution status will update to
              "Verification in progress" and you'll see the outcome on your Passport.
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}

const cardBtnStyle = {
  display: "flex", alignItems: "flex-start", gap: 10, width: "100%", padding: "12px 14px",
  border: `1px solid ${BRD}`, borderRadius: 10, background: "#fff", cursor: "pointer", textAlign: "left",
};

export default InstitutionVerificationModal;

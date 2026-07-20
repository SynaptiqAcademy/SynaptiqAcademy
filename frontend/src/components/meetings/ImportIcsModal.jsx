import React, { useState, useRef } from "react";
import { Modal } from "@/components/ds/Modal";
import { Button } from "@/components/ds/Button";
import { UploadCloud, CheckCircle2, AlertTriangle } from "lucide-react";
import { BRD, TEXT_MUTED, NAVY, EMERALD } from "@/lib/tokens";
import { importIcs } from "@/hooks/useMeetings";
import { toast } from "sonner";

/**
 * ImportIcsModal — upload a .ics calendar export and create Meeting records.
 */
export function ImportIcsModal({ open, onClose, onImported }) {
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const inputRef = useRef(null);

  if (!open) return null;

  const reset = () => { setFile(null); setResult(null); };

  const handleImport = async () => {
    if (!file) return;
    setSubmitting(true);
    try {
      const res = await importIcs(file);
      setResult(res);
      if (res.imported > 0) {
        toast.success(`Imported ${res.imported} meeting${res.imported === 1 ? "" : "s"}`);
        onImported?.();
      }
    } catch (e) {
      setResult({ imported: 0, errors: [e?.response?.data?.detail || "Import failed. Please check the file and try again."] });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={() => { reset(); onClose?.(); }}
      title="Import Calendar"
      description="Upload a .ics export from Google Calendar, Outlook, or Apple Calendar."
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={() => { reset(); onClose?.(); }}>Close</Button>
          <Button onClick={handleImport} disabled={!file} loading={submitting}>Import</Button>
        </>
      }
    >
      <div
        role="button"
        tabIndex={0}
        aria-label="Choose a .ics file to import"
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files?.[0]; if (f) setFile(f); }}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inputRef.current?.click(); } }}
        style={{
          border: `1.5px dashed ${dragOver ? NAVY : BRD}`,
          borderRadius: 8,
          padding: "32px 20px",
          textAlign: "center",
          cursor: "pointer",
          background: dragOver ? "rgba(15,40,71,0.03)" : "#FAFBFC",
          transition: "all 150ms",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".ics"
          hidden
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <UploadCloud size={28} style={{ color: TEXT_MUTED, margin: "0 auto 10px" }} />
        <div style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>
          {file ? file.name : "Click to choose or drop a .ics file"}
        </div>
        <div style={{ fontSize: 11.5, color: TEXT_MUTED, marginTop: 4 }}>
          Events are imported as scheduled Research Meetings
        </div>
      </div>

      {result && (
        <div style={{ marginTop: 16, fontSize: 12.5 }}>
          {result.imported > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: EMERALD, marginBottom: 6 }}>
              <CheckCircle2 size={14} /> Imported {result.imported} of {result.total_found ?? result.imported} events
            </div>
          )}
          {result.errors?.length > 0 && (
            <div style={{ display: "flex", alignItems: "flex-start", gap: 8, color: "#B45309" }}>
              <AlertTriangle size={14} style={{ marginTop: 1, flexShrink: 0 }} />
              <span>{result.errors.join("; ")}</span>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

export default ImportIcsModal;

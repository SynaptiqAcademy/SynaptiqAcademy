/**
 * PreviewDrawer — inline preview for PDF / image / CSV / text.
 * Renders to the right of file rows (slide-in from right).
 */
import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../../lib/api";
import { X, Loader2, Download, ExternalLink } from "lucide-react";
import { NAVY } from "@/lib/tokens";

const REACT_APP_BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function PreviewDrawer({ file, onClose }) {
  const [csvData, setCsvData] = useState(null);
  const [textData, setTextData] = useState(null);
  const [error, setError] = useState(null);
  const [blobUrl, setBlobUrl] = useState(null);

  // Escape key closes the drawer; dismiss any pending toasts on open so the
  // close button is never occluded by a notification.
  useEffect(() => {
    if (!file) return;
    toast.dismiss();
    const onKey = (e) => { if (e.key === "Escape") onClose?.(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [file, onClose]);

  useEffect(() => {
    if (!file) return;
    setCsvData(null); setTextData(null); setError(null); setBlobUrl(null);
    const ext = (file.ext || "").toLowerCase();
    (async () => {
      try {
        if (ext === "csv" || ext === "tsv") {
          const { data } = await api.get(`/files/${file.id}/preview-csv?rows=100`);
          setCsvData(data);
        } else if (["txt", "md", "json"].includes(ext)) {
          const r = await api.get(`/files/${file.id}/preview`, { responseType: "blob" });
          const text = await r.data.text();
          setTextData(text.slice(0, 200_000));
        } else if (["pdf", "png", "jpg", "jpeg", "webp", "gif", "svg"].includes(ext)) {
          const r = await api.get(`/files/${file.id}/preview`, { responseType: "blob" });
          setBlobUrl(URL.createObjectURL(r.data));
        } else {
          setError("Preview is not supported for this file type. Download to view.");
        }
      } catch (e) {
        setError(e?.response?.data?.detail || "Preview failed");
      }
    })();
    return () => { if (blobUrl) URL.revokeObjectURL(blobUrl); };
    // eslint-disable-next-line
  }, [file?.id]);

  if (!file) return null;
  const ext = (file.ext || "").toLowerCase();
  const isPdf = ext === "pdf";
  const isImg = ["png","jpg","jpeg","webp","gif","svg"].includes(ext);

  const download = async () => {
    try {
      const r = await api.get(`/files/${file.id}/download`, { responseType: "blob" });
      const u = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = u; a.download = file.filename;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(u);
    } catch {}
  };

  return (
    <div className="fixed inset-0 z-[10000] flex" onClick={onClose} data-testid="file-preview-drawer">
      <div className="absolute inset-0 bg-slate-900/40" />
      <div className="ml-auto relative w-full max-w-3xl h-full bg-white border-l border-slate-200 flex flex-col shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-slate-200 px-5 py-4 flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="overline text-[#0F2847]">{ext.toUpperCase()} preview</div>
            <h3 className="font-serif text-lg text-slate-900 truncate mt-0.5">{file.filename}</h3>
            <div className="text-[10px] font-mono text-slate-400">v{file.version} · {(file.size_bytes / 1024).toFixed(1)} KB</div>
          </div>
          <div className="shrink-0 flex items-center gap-1">
            <button onClick={download} className="text-slate-500 hover:text-[#0F2847] p-1.5 border border-slate-200" title="Download" data-testid="preview-download">
              <Download size={12} strokeWidth={1.5} />
            </button>
            {blobUrl && (
              <a href={blobUrl} target="_blank" rel="noreferrer" className="text-slate-500 hover:text-[#0F2847] p-1.5 border border-slate-200" title="Open in new tab" data-testid="preview-newtab">
                <ExternalLink size={12} strokeWidth={1.5} />
              </a>
            )}
            <button onClick={onClose} aria-label="Close preview" title="Close (Esc)" className="text-slate-500 hover:text-slate-900 p-1.5 border border-slate-200 hover:bg-slate-50" data-testid="preview-close">
              <X size={14} strokeWidth={1.5} />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-auto bg-slate-50">
          {error && <div className="p-6 text-sm text-red-600" data-testid="preview-error">{error}</div>}
          {!error && !csvData && !textData && !blobUrl && (
            <div className="p-10 text-center text-sm text-slate-500 font-mono"><Loader2 size={12} className="animate-spin inline mr-2" />Loading preview…</div>
          )}
          {blobUrl && isPdf && (
            <iframe src={blobUrl} title={file.filename} className="w-full h-full border-0 bg-white" data-testid="preview-pdf-frame" />
          )}
          {blobUrl && isImg && (
            <div className="p-6 flex items-center justify-center min-h-full bg-slate-100">
              <img src={blobUrl} alt={file.filename} className="max-w-full max-h-[calc(100vh-180px)] shadow-lg" data-testid="preview-image" />
            </div>
          )}
          {csvData && <CsvTable data={csvData} />}
          {textData && (
            <pre className="p-4 text-xs font-mono text-slate-900 whitespace-pre-wrap break-words bg-white" data-testid="preview-text">{textData}</pre>
          )}
        </div>
      </div>
    </div>
  );
}

function CsvTable({ data }) {
  const { headers, rows, delimiter } = data;
  return (
    <div className="overflow-auto p-4" data-testid="preview-csv-table">
      <div className="text-[10px] font-mono text-slate-400 mb-2">delimiter: "{delimiter === "\t" ? "\\t" : delimiter}" · {rows.length} rows shown</div>
      <table className="text-xs border border-slate-200 bg-white">
        <thead className="bg-slate-100">
          <tr>
            <th className="px-2 py-1 border-r border-slate-200 text-slate-400 font-mono">#</th>
            {headers.map((h, i) => (
              <th key={i} className="px-2 py-1 border-r border-slate-200 text-left font-mono text-slate-700">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-slate-100">
              <td className="px-2 py-1 border-r border-slate-200 text-slate-400 font-mono">{i + 1}</td>
              {row.map((c, j) => (
                <td key={j} className="px-2 py-1 border-r border-slate-100 text-slate-800 font-mono whitespace-nowrap">{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

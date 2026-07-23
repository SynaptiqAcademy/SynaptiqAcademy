/**
 * FilePanel — embeddable Research File Layer for any entity
 * (workspace | project | manuscript).
 *
 * Props:
 *   entityKind, entityId
 *
 * Features: upload, list (current versions), version history, activity log,
 * metadata edit, download, delete.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import api from "../../lib/api";
import { toast } from "sonner";
import {
  Upload, Download, Trash2, History, Edit3, FileText, FileSpreadsheet, FilePlus,
  FileImage, Loader2, Clock, X, Activity, ChevronDown, ChevronRight, Eye,
} from "lucide-react";
import PreviewDrawer from "./PreviewDrawer";
import { NAVY } from "@/lib/tokens";

const TYPE_ICON = {
  pdf: FileText, docx: FileText, doc: FileText,
  xlsx: FileSpreadsheet, xls: FileSpreadsheet, csv: FileSpreadsheet,
  pptx: FilePlus, ppt: FilePlus,
  zip: FilePlus,
  png: FileImage, jpg: FileImage, jpeg: FileImage, webp: FileImage, gif: FileImage, svg: FileImage,
};

const ACCEPT_TYPES = ".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.csv,.zip,.png,.jpg,.jpeg,.webp,.gif,.svg";

function bytesH(n) {
  if (!n) return "0 B";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

export default function FilePanel({ entityKind, entityId }) {
  const [files, setFiles] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [expanded, setExpanded] = useState(null); // file id whose versions/activity is open
  const [previewing, setPreviewing] = useState(null);
  const inputRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/files?entity_kind=${entityKind}&entity_id=${entityId}`);
      setFiles(data || []);
    } catch (e) { setFiles([]); }
  }, [entityKind, entityId]);
  useEffect(() => { load(); }, [load]);

  const upload = async (e, replacesId = null) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 50 * 1024 * 1024) { toast.error("File exceeds 50 MB"); return; }
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("entity_kind", entityKind);
      fd.append("entity_id", entityId);
      fd.append("file", f);
      if (replacesId) fd.append("replaces_id", replacesId);
      await api.post("/files/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(replacesId ? "New version uploaded" : "File uploaded");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Upload failed"); }
    finally { setUploading(false); if (inputRef.current) inputRef.current.value = ""; }
  };

  const download = async (f) => {
    try {
      const resp = await api.get(`/files/${f.id}/download`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url; a.download = f.filename || "download";
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) { toast.error("Download failed"); }
  };

  const del = async (f) => {
    if (!confirm(`Delete "${f.filename}"?`)) return;
    try {
      await api.delete(`/files/${f.id}`);
      toast.success("Deleted");
      load();
    } catch (e) { toast.error("Failed"); }
  };

  return (
    <section className="border border-slate-200 bg-white p-5 space-y-3" data-testid="file-panel">
      <header className="flex items-center justify-between gap-3">
        <div>
          <div className="overline">Files</div>
          <p className="text-[11px] text-slate-500">PDF / DOCX / XLSX / PPTX / CSV / ZIP / images · 50 MB max.</p>
        </div>
        <label className="inline-flex items-center gap-1.5 text-xs bg-[#0F2847] text-white px-3 py-2 hover:bg-slate-800 cursor-pointer" data-testid="file-upload-btn">
          {uploading ? <Loader2 size={11} className="animate-spin" /> : <Upload size={11} strokeWidth={1.5} />}
          Upload
          <input ref={inputRef} type="file" className="hidden" accept={ACCEPT_TYPES} onChange={(e) => upload(e)} data-testid="file-upload-input" />
        </label>
      </header>

      {files === null && <div className="text-xs font-mono text-slate-500"><Loader2 size={10} className="animate-spin inline mr-1" />Loading…</div>}
      {files && files.length === 0 && (
        <div className="text-center py-8 border border-dashed border-slate-200 text-xs text-slate-500" data-testid="file-empty">
          No files yet. Drop one above to begin the research file trail.
        </div>
      )}
      {files && files.length > 0 && (
        <div className="divide-y divide-slate-100" data-testid="file-list">
          {files.map((f) => (
            <FileRow key={f.id} f={f}
              expanded={expanded === f.id} onExpand={() => setExpanded(expanded === f.id ? null : f.id)}
              onPreview={() => setPreviewing(f)}
              onDownload={() => download(f)}
              onDelete={() => del(f)}
              onUploadVersion={(e) => upload(e, f.id)}
            />
          ))}
        </div>
      )}
      {previewing && <PreviewDrawer file={previewing} onClose={() => setPreviewing(null)} />}
    </section>
  );
}

function FileRow({ f, expanded, onExpand, onPreview, onDownload, onDelete, onUploadVersion }) {
  const [versions, setVersions] = useState(null);
  const [activity, setActivity] = useState(null);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(f.filename);
  const Icon = TYPE_ICON[f.ext] || FileText;

  const loadAux = useCallback(async () => {
    if (versions !== null) return;
    try {
      const [v, a] = await Promise.all([
        api.get(`/files/${f.id}/versions`),
        api.get(`/files/${f.id}/activity`),
      ]);
      setVersions(v.data || []); setActivity(a.data || []);
    } catch (e) {}
  }, [versions, f.id]);
  useEffect(() => { if (expanded) loadAux(); }, [expanded, loadAux]);

  const saveRename = async () => {
    if (!name.trim() || name === f.filename) { setEditing(false); return; }
    try {
      await api.patch(`/files/${f.id}`, { filename: name.trim() });
      toast.success("Renamed");
      f.filename = name.trim();
      setEditing(false);
    } catch (e) { toast.error("Failed"); }
  };

  return (
    <div className="py-2.5" data-testid={`file-row-${f.id}`}>
      <div className="flex items-center gap-3">
        <button onClick={onExpand} className="text-slate-400 hover:text-slate-700">
          {expanded ? <ChevronDown size={12} strokeWidth={1.5} /> : <ChevronRight size={12} strokeWidth={1.5} />}
        </button>
        <Icon size={14} strokeWidth={1.5} className="text-[#0F2847] shrink-0" />
        <div className="flex-1 min-w-0">
          {editing ? (
            <input
              value={name} onChange={(e) => setName(e.target.value)}
              onBlur={saveRename}
              onKeyDown={(e) => e.key === "Enter" && saveRename()}
              autoFocus
              className="text-sm w-full px-2 py-1 border border-slate-300"
            />
          ) : (
            <button onDoubleClick={() => setEditing(true)} className="font-serif text-sm text-slate-900 truncate text-left">
              {f.filename}
            </button>
          )}
          <div className="text-[10px] font-mono text-slate-400 truncate">
            v{f.version} · {bytesH(f.size_bytes)} · {f.ext.toUpperCase()} · {new Date(f.created_at).toLocaleDateString()}
            {f.description && <span className="ml-2">{f.description}</span>}
          </div>
        </div>
        <button onClick={onPreview} data-testid={`file-preview-${f.id}`} className="text-slate-400 hover:text-[#0F2847]" title="Preview">
          <Eye size={12} strokeWidth={1.5} />
        </button>
        <button onClick={onDownload} data-testid={`file-download-${f.id}`} className="text-slate-400 hover:text-[#0F2847]" title="Download">
          <Download size={12} strokeWidth={1.5} />
        </button>
        <label className="text-slate-400 hover:text-[#0F2847] cursor-pointer" title="Upload new version" data-testid={`file-newversion-${f.id}`}>
          <Upload size={12} strokeWidth={1.5} />
          <input type="file" className="hidden" accept=".pdf,.docx,.xlsx,.pptx,.csv,.zip,.png,.jpg,.jpeg" onChange={onUploadVersion} />
        </label>
        <button onClick={() => setEditing(true)} className="text-slate-400 hover:text-[#0F2847]" title="Rename"><Edit3 size={12} strokeWidth={1.5} /></button>
        <button onClick={onDelete} data-testid={`file-delete-${f.id}`} className="text-slate-400 hover:text-red-600" title="Delete">
          <Trash2 size={12} strokeWidth={1.5} />
        </button>
      </div>

      {expanded && (
        <div className="mt-2 ml-7 grid sm:grid-cols-2 gap-3" data-testid={`file-detail-${f.id}`}>
          <div className="border border-slate-200 p-3">
            <div className="overline mb-1 flex items-center gap-1"><History size={10} strokeWidth={1.5} /> Versions</div>
            {versions === null && <div className="text-[10px] font-mono text-slate-400">Loading…</div>}
            {versions && versions.length === 0 && <div className="text-[11px] text-slate-500">—</div>}
            {versions && versions.map((v) => (
              <div key={v.id} className="text-[11px] flex items-center gap-2">
                <span className="font-mono text-slate-400">v{v.version}</span>
                <span className="flex-1 truncate">{v.filename}</span>
                <span className="font-mono text-slate-400">{bytesH(v.size_bytes)}</span>
              </div>
            ))}
          </div>
          <div className="border border-slate-200 p-3">
            <div className="overline mb-1 flex items-center gap-1"><Activity size={10} strokeWidth={1.5} /> Activity</div>
            {activity === null && <div className="text-[10px] font-mono text-slate-400">Loading…</div>}
            {activity && activity.length === 0 && <div className="text-[11px] text-slate-500">—</div>}
            {activity && activity.slice(0, 8).map((a) => (
              <div key={a.id} className="text-[11px] flex items-center gap-2">
                <span className="font-mono text-slate-400">{new Date(a.created_at).toLocaleString()}</span>
                <span className="overline">{a.action}</span>
                <span className="truncate">{a.actor_name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

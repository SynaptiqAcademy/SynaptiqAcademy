import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, Plus, Tag, ChevronDown, ChevronRight } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

function useX(path, params = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const query = new URLSearchParams(params).toString();
  const load = useCallback(() => {
    setLoading(true);
    api.get(`/admin/x/${path}${query ? "?" + query : ""}`)
      .then(r => setData(r.data)).catch(() => setData(null)).finally(() => setLoading(false));
  }, [path, query]);
  useEffect(() => { load(); }, [load]);
  return { data, loading, refetch: load };
}

const KIND_COLORS = {
  release:   "text-green-400 border-green-700",
  hotfix:    "text-red-400 border-red-700",
  rollback:  "text-yellow-400 border-yellow-700",
  migration: "text-blue-400 border-blue-700",
};

const STATUS_COLORS = {
  deployed:     "text-green-400",
  planned:      "text-yellow-400",
  rolled_back:  "text-red-400",
};

function ReleaseRow({ release, onRefresh }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr className="border-t border-[#1a3050] hover:bg-[#1a3050]/30 cursor-pointer" onClick={() => setExpanded(v => !v)}>
        <td className="px-3 py-2">
          {expanded ? <ChevronDown size={12} className="text-slate-400" /> : <ChevronRight size={12} className="text-slate-400" />}
        </td>
        <td className="px-3 py-2 font-mono text-white text-xs">{release.version}</td>
        <td className="px-3 py-2 text-slate-300 text-xs">{release.name || "—"}</td>
        <td className="px-3 py-2">
          <span className={`text-[10px] px-2 py-0.5 border ${KIND_COLORS[release.kind] || "text-slate-400 border-slate-700"}`}>
            {(release.kind || "release").toUpperCase()}
          </span>
        </td>
        <td className="px-3 py-2">
          <span className={`text-xs ${STATUS_COLORS[release.status] || "text-slate-400"}`}>{release.status}</span>
        </td>
        <td className="px-3 py-2 text-xs text-green-400">{(release.features || []).length}</td>
        <td className="px-3 py-2 text-xs text-blue-400">{(release.bugs_fixed || []).length}</td>
        <td className="px-3 py-2 text-xs">
          {(release.breaking_changes || []).length > 0 ? (
            <span className="text-red-400">{release.breaking_changes.length} breaking</span>
          ) : <span className="text-slate-500">none</span>}
        </td>
        <td className="px-3 py-2 text-xs text-slate-500">{release.released_by || "—"}</td>
        <td className="px-3 py-2 text-xs text-slate-500">{(release.released_at || "").slice(0, 10)}</td>
      </tr>
      {expanded && (
        <tr className="border-t border-[#1a3050] bg-[#080f1f]">
          <td colSpan={10} className="px-4 py-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              {[
                { label: "Features", items: release.features, color: "text-green-400" },
                { label: "Bugs Fixed", items: release.bugs_fixed, color: "text-blue-400" },
                { label: "Breaking Changes", items: release.breaking_changes, color: "text-red-400" },
              ].map(({ label, items, color }) => (
                <div key={label}>
                  <div className={`font-medium ${color} mb-1`}>{label} ({(items || []).length})</div>
                  <ul className="space-y-0.5">
                    {(items || []).map((item, i) => <li key={i} className="text-slate-400">• {item}</li>)}
                    {(items || []).length === 0 && <li className="text-slate-600">None</li>}
                  </ul>
                </div>
              ))}
            </div>
            {release.release_notes && (
              <div className="mt-3">
                <div className="text-xs text-slate-500 font-medium mb-1">Release Notes</div>
                <div className="text-xs text-slate-300 whitespace-pre-wrap">{release.release_notes}</div>
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function CreateReleaseModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    version: "", name: "", kind: "release", status: "deployed",
    features: "", bugs_fixed: "", breaking_changes: "",
    release_notes: "", rollback_available: true,
  });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const save = async () => {
    if (!form.version) { setMsg("Version required"); return; }
    setSaving(true);
    try {
      await api.post("/admin/x/releases", {
        ...form,
        features: form.features.split("\n").filter(Boolean),
        bugs_fixed: form.bugs_fixed.split("\n").filter(Boolean),
        breaking_changes: form.breaking_changes.split("\n").filter(Boolean),
      });
      onCreated();
    } catch (e) { setMsg(e?.response?.data?.detail || "Error"); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-[#0B1C35] border border-[#1a3050] w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1a3050]">
          <span className="text-sm font-semibold text-white">Log New Release</span>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">×</button>
        </div>
        <div className="p-5 space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] text-slate-500 mb-1">Version *</label>
              <input value={form.version} onChange={e => setForm(f => ({...f, version: e.target.value}))}
                placeholder="v2.4.1" className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5" />
            </div>
            <div>
              <label className="block text-[10px] text-slate-500 mb-1">Name</label>
              <input value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))}
                placeholder="Search Overhaul" className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5" />
            </div>
            <div>
              <label className="block text-[10px] text-slate-500 mb-1">Kind</label>
              <select value={form.kind} onChange={e => setForm(f => ({...f, kind: e.target.value}))}
                className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5">
                {["release","hotfix","rollback","migration"].map(k => <option key={k} value={k}>{k}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-slate-500 mb-1">Status</label>
              <select value={form.status} onChange={e => setForm(f => ({...f, status: e.target.value}))}
                className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5">
                {["planned","deployed","rolled_back"].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          {[
            { key: "features", label: "Features (one per line)" },
            { key: "bugs_fixed", label: "Bugs Fixed (one per line)" },
            { key: "breaking_changes", label: "Breaking Changes (one per line)" },
          ].map(({ key, label }) => (
            <div key={key}>
              <label className="block text-[10px] text-slate-500 mb-1">{label}</label>
              <textarea rows={3} value={form[key]}
                onChange={e => setForm(f => ({...f, [key]: e.target.value}))}
                className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5 resize-none" />
            </div>
          ))}
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Release Notes</label>
            <textarea rows={4} value={form.release_notes}
              onChange={e => setForm(f => ({...f, release_notes: e.target.value}))}
              className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5 resize-none" />
          </div>
          {msg && <div className="text-red-400 text-xs">{msg}</div>}
          <div className="flex gap-2 pt-1">
            <button onClick={onClose} className="flex-1 text-xs text-slate-400 border border-[#1a3050] px-3 py-2 hover:text-white">Cancel</button>
            <button onClick={save} disabled={saving} className="flex-1 text-xs bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white px-3 py-2">
              {saving ? "Saving..." : "Log Release"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AdminReleases() {
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const { data, loading, refetch } = useX("releases", { page, limit: 20 });

  const items = data?.items || [];
  const total = data?.total || 0;

  const counts = items.reduce((acc, r) => { acc[r.kind] = (acc[r.kind] || 0) + 1; return acc; }, {});

  return (
    <AdministrationLayout
      title="Release Management Center"
      subtitle="Deployment history, feature tracking, rollback status"
      actions={
        <div className="flex gap-2">
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-1.5 text-xs bg-green-700 hover:bg-green-600 text-white px-3 py-1.5">
            <Plus size={12} /> Log Release
          </button>
          <button onClick={refetch} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      }
    >

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Total Releases", value: total, color: "text-white" },
          { label: "Releases", value: counts.release || 0, color: "text-green-400" },
          { label: "Hotfixes", value: counts.hotfix || 0, color: "text-red-400" },
          { label: "Rollbacks", value: counts.rollback || 0, color: "text-yellow-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className={`text-2xl font-bold ${color}`}>{value}</div>
            <div className="text-xs text-slate-400">{label}</div>
          </div>
        ))}
      </div>

      <div className="bg-[#0F2847] border border-[#1a3050] overflow-x-auto">
        <table className="w-full text-xs text-slate-300">
          <thead className="text-slate-500 border-b border-[#1a3050]">
            <tr>
              <th className="px-3 py-2 w-6" />
              <th className="text-left px-3 py-2 font-medium">Version</th>
              <th className="text-left px-3 py-2 font-medium">Name</th>
              <th className="text-left px-3 py-2 font-medium">Kind</th>
              <th className="text-left px-3 py-2 font-medium">Status</th>
              <th className="text-right px-3 py-2 font-medium">Features</th>
              <th className="text-right px-3 py-2 font-medium">Fixes</th>
              <th className="text-left px-3 py-2 font-medium">Breaking</th>
              <th className="text-left px-3 py-2 font-medium">By</th>
              <th className="text-left px-3 py-2 font-medium">Date</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={10} className="px-3 py-8 text-center text-slate-500">Loading...</td></tr>}
            {!loading && items.map(r => <ReleaseRow key={r.id} release={r} onRefresh={refetch} />)}
            {!loading && items.length === 0 && (
              <tr><td colSpan={10} className="px-3 py-8 text-center text-slate-500">No releases logged yet</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {total > 20 && (
        <div className="flex items-center gap-2">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="text-xs px-2 py-1 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white disabled:opacity-50">← Prev</button>
          <span className="text-xs text-slate-500">Page {page} of {Math.ceil(total / 20)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page * 20 >= total}
            className="text-xs px-2 py-1 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white disabled:opacity-50">Next →</button>
        </div>
      )}

      {showCreate && <CreateReleaseModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); refetch(); }} />}
    </AdministrationLayout>
  );
}

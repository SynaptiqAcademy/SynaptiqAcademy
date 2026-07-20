/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { Toggle, RefreshCw, Plus, Trash2, ChevronDown, ChevronRight, BarChart3, AlertTriangle } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

function useX(path, params = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const query = new URLSearchParams(params).toString();
  const fetch = useCallback(() => {
    setLoading(true);
    api.get(`/admin/x/${path}${query ? "?" + query : ""}`)
      .then((r) => setData(r.data)).catch(() => setData(null)).finally(() => setLoading(false));
  }, [path, query]);
  useEffect(() => { fetch(); }, [fetch]);
  return { data, loading, refetch: fetch };
}

const MODULES = [
  "orcid","openalex","stripe_billing","messaging","collaborations","workspaces","projects",
  "teaching","research_os","journal_finder","conference_finder","funding_finder",
  "publication_tracking","ai_features","platform_auditor",
];

function CreateFlagModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: "", enabled: false, rollout_pct: 100, description: "", beta_only: false });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const save = async () => {
    if (!form.name) { setMsg("Name required"); return; }
    setSaving(true);
    try {
      await api.post("/admin/x/feature-flags", form);
      onCreated();
    } catch (e) { setMsg(e?.response?.data?.detail || "Error"); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-[#0B1C35] border border-[#1a3050] w-full max-w-md">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1a3050]">
          <span className="text-sm font-semibold text-white">New Feature Flag</span>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">×</button>
        </div>
        <div className="p-5 space-y-3">
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Module Name</label>
            <select value={form.name} onChange={(e) => setForm(f => ({...f, name: e.target.value}))}
              className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5">
              <option value="">Select module...</option>
              {MODULES.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Description</label>
            <input type="text" value={form.description} onChange={(e) => setForm(f => ({...f, description: e.target.value}))}
              className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5" />
          </div>
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-[10px] text-slate-500 mb-1">Rollout %</label>
              <input type="number" min={0} max={100} value={form.rollout_pct}
                onChange={(e) => setForm(f => ({...f, rollout_pct: Number(e.target.value)}))}
                className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5" />
            </div>
            <div className="flex items-end gap-2 pb-1.5">
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input type="checkbox" checked={form.enabled} onChange={(e) => setForm(f => ({...f, enabled: e.target.checked}))}
                  className="w-3.5 h-3.5" />
                Enabled
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input type="checkbox" checked={form.beta_only} onChange={(e) => setForm(f => ({...f, beta_only: e.target.checked}))}
                  className="w-3.5 h-3.5" />
                Beta only
              </label>
            </div>
          </div>
          {msg && <div className="text-xs text-slate-400">{msg}</div>}
          <div className="flex gap-2 pt-1">
            <button onClick={onClose} className="flex-1 text-xs text-slate-400 border border-[#1a3050] px-3 py-2 hover:text-white">Cancel</button>
            <button onClick={save} disabled={saving} className="flex-1 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-2">
              {saving ? "Saving..." : "Create Flag"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function FlagRow({ flag, onToggle, onDelete }) {
  const [expanded, setExpanded] = useState(false);
  const [toggling, setToggling] = useState(false);

  const toggle = async () => {
    setToggling(true);
    try {
      await api.post("/admin/x/feature-flags", { ...flag, enabled: !flag.enabled });
      onToggle();
    } catch (e) { console.error(e); }
    finally { setToggling(false); }
  };

  const del = async () => {
    if (!window.confirm(`Delete flag "${flag.name}"?`)) return;
    try { await api.delete(`/admin/x/feature-flags/${flag.name}`); onDelete(); }
    catch (e) { console.error(e); }
  };

  return (
    <>
      <tr className="border-t border-[#1a3050] hover:bg-[#1a3050]/30 cursor-pointer" onClick={() => setExpanded(v => !v)}>
        <td className="px-3 py-2">
          {expanded ? <ChevronDown size={12} className="text-slate-400" /> : <ChevronRight size={12} className="text-slate-400" />}
        </td>
        <td className="px-3 py-2 font-mono text-white text-xs">{flag.name}</td>
        <td className="px-3 py-2">
          <button onClick={(e) => { e.stopPropagation(); toggle(); }} disabled={toggling}
            className={`text-[10px] px-2 py-0.5 font-medium border transition-colors ${flag.enabled
              ? "text-green-400 border-green-700 hover:bg-green-900/30"
              : "text-slate-400 border-slate-700 hover:bg-slate-800"}`}>
            {toggling ? "..." : flag.enabled ? "ENABLED" : "DISABLED"}
          </button>
        </td>
        <td className="px-3 py-2">
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-20 bg-[#1a3050] rounded-full overflow-hidden">
              <div className="h-full bg-blue-500" style={{ width: `${flag.rollout_pct || 100}%` }} />
            </div>
            <span className="text-xs text-slate-400">{flag.rollout_pct ?? 100}%</span>
          </div>
        </td>
        <td className="px-3 py-2 text-xs text-slate-400">{flag.adopters_30d ?? 0}</td>
        <td className="px-3 py-2 text-xs">
          {flag.errors_30d > 0 ? (
            <span className="text-red-400">{flag.errors_30d}</span>
          ) : <span className="text-slate-500">0</span>}
        </td>
        <td className="px-3 py-2 text-xs text-slate-500">{(flag.updated_at || "").slice(0, 10)}</td>
        <td className="px-3 py-2">
          <button onClick={(e) => { e.stopPropagation(); del(); }} className="text-slate-500 hover:text-red-400 transition-colors">
            <Trash2 size={12} />
          </button>
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-[#1a3050] bg-[#080f1f]">
          <td colSpan={8} className="px-4 py-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              <div><span className="text-slate-500">Beta only:</span> <span className="text-white">{flag.beta_only ? "Yes" : "No"}</span></div>
              <div><span className="text-slate-500">Allowed plans:</span> <span className="text-white">{(flag.allowed_plans || []).join(", ") || "All"}</span></div>
              <div><span className="text-slate-500">Activates at:</span> <span className="text-white">{(flag.activates_at || "").slice(0, 16) || "—"}</span></div>
              <div><span className="text-slate-500">Deactivates at:</span> <span className="text-white">{(flag.deactivates_at || "").slice(0, 16) || "—"}</span></div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function AdminFeatureFlags() {
  const { data, loading, refetch } = useX("feature-flags");
  const [showCreate, setShowCreate] = useState(false);

  const flags = data?.flags || [];
  const missing = data?.missing_modules || [];
  const coverage = data?.coverage_pct ?? 0;

  return (
    <AdministrationLayout
      title="Feature Flags Control Center"
      subtitle="Manage gradual rollouts, scheduled flags, and module gating"
      actions={
        <div className="flex gap-2">
          <button onClick={() => setShowCreate(true)} className="flex items-center gap-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5">
            <Plus size={12} /> New Flag
          </button>
          <button onClick={refetch} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      }
    >

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="text-2xl font-bold text-white">{data?.total ?? 0}</div>
          <div className="text-xs text-slate-400">Total Flags</div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="text-2xl font-bold text-green-400">{data?.active ?? 0}</div>
          <div className="text-xs text-slate-400">Active</div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className={`text-2xl font-bold ${coverage >= 80 ? "text-green-400" : coverage >= 50 ? "text-yellow-400" : "text-red-400"}`}>{coverage}%</div>
          <div className="text-xs text-slate-400">Module Coverage</div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="text-2xl font-bold text-yellow-400">{missing.length}</div>
          <div className="text-xs text-slate-400">Unmanaged Modules</div>
        </div>
      </div>

      {/* Missing modules */}
      {missing.length > 0 && (
        <div className="bg-yellow-900/20 border border-yellow-700/40 p-3 flex items-start gap-2">
          <AlertTriangle size={14} className="text-yellow-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-yellow-300">
            <span className="font-medium">Unmanaged modules:</span> {missing.join(", ")}
          </div>
        </div>
      )}

      {/* Flags table */}
      <div className="bg-[#0F2847] border border-[#1a3050] overflow-x-auto">
        <table className="w-full text-xs text-slate-300">
          <thead className="text-slate-500 border-b border-[#1a3050]">
            <tr>
              <th className="px-3 py-2 w-6" />
              <th className="text-left px-3 py-2 font-medium">Name</th>
              <th className="text-left px-3 py-2 font-medium">Status</th>
              <th className="text-left px-3 py-2 font-medium">Rollout</th>
              <th className="text-left px-3 py-2 font-medium">Adopters (30d)</th>
              <th className="text-left px-3 py-2 font-medium">Errors (30d)</th>
              <th className="text-left px-3 py-2 font-medium">Updated</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-500">Loading...</td></tr>}
            {!loading && flags.map(f => (
              <FlagRow key={f.id} flag={f} onToggle={refetch} onDelete={refetch} />
            ))}
            {!loading && flags.length === 0 && (
              <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-500">No feature flags defined</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showCreate && <CreateFlagModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); refetch(); }} />}
    </AdministrationLayout>
  );
}

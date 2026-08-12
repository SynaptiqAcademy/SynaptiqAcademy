/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, Plus, Trash2, ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";
import api from "@/lib/api";
import { EMERALD, AMBER, CRIMSON } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Modal, Button, Input, FormSelect, Checkbox, Alert, StatCard, StatGrid } from "@/components/ds";

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
    <Modal
      open
      onClose={onClose}
      title="New Feature Flag"
      size="sm"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button variant="primary" size="sm" onClick={save} loading={saving}>Create Flag</Button>
        </>
      }
    >
      <div className="space-y-3">
        <FormSelect
          label="Module Name"
          value={form.name}
          onChange={(e) => setForm(f => ({...f, name: e.target.value}))}
        >
          <option value="">Select module...</option>
          {MODULES.map(m => <option key={m} value={m}>{m}</option>)}
        </FormSelect>
        <Input
          type="text"
          label="Description"
          value={form.description}
          onChange={(e) => setForm(f => ({...f, description: e.target.value}))}
        />
        <div className="flex gap-4">
          <Input
            type="number"
            label="Rollout %"
            min={0}
            max={100}
            value={form.rollout_pct}
            onChange={(e) => setForm(f => ({...f, rollout_pct: Number(e.target.value)}))}
            wrapperClassName="flex-1"
          />
          <div className="flex items-end gap-4 pb-1.5">
            <Checkbox
              label="Enabled"
              checked={form.enabled}
              onChange={(e) => setForm(f => ({...f, enabled: e.target.checked}))}
            />
            <Checkbox
              label="Beta only"
              checked={form.beta_only}
              onChange={(e) => setForm(f => ({...f, beta_only: e.target.checked}))}
            />
          </div>
        </div>
        {msg && <Alert variant="error">{msg}</Alert>}
      </div>
    </Modal>
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
      <tr className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer" onClick={() => setExpanded(v => !v)}>
        <td className="px-3 py-2">
          {expanded ? <ChevronDown size={12} className="text-slate-400" /> : <ChevronRight size={12} className="text-slate-400" />}
        </td>
        <td className="px-3 py-2 font-mono text-slate-800 text-xs">{flag.name}</td>
        <td className="px-3 py-2">
          {/* Hand-rolled rather than ds/Badge: this pill is clickable (toggles
              enabled/disabled) and Badge doesn't forward onClick/props — it
              only accepts variant/size/dot/color/className/style. Styled to
              match Badge's success/neutral variant colors exactly. */}
          <button onClick={(e) => { e.stopPropagation(); toggle(); }} disabled={toggling}
            className={`text-[10px] px-2 py-0.5 rounded-badge font-medium border transition-colors ${flag.enabled
              ? "text-emerald-700 bg-emerald-50 border-emerald-200 hover:bg-emerald-100"
              : "text-slate-500 bg-slate-100 border-slate-200 hover:bg-slate-200"}`}>
            {toggling ? "..." : flag.enabled ? "ENABLED" : "DISABLED"}
          </button>
        </td>
        <td className="px-3 py-2">
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-20 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-blue-500" style={{ width: `${flag.rollout_pct || 100}%` }} />
            </div>
            <span className="text-xs text-slate-500">{flag.rollout_pct ?? 100}%</span>
          </div>
        </td>
        <td className="px-3 py-2 text-xs text-slate-500">{flag.adopters_30d ?? 0}</td>
        <td className="px-3 py-2 text-xs">
          {flag.errors_30d > 0 ? (
            <span className="text-red-600 font-medium">{flag.errors_30d}</span>
          ) : <span className="text-slate-400">0</span>}
        </td>
        <td className="px-3 py-2 text-xs text-slate-400">{(flag.updated_at || "").slice(0, 10)}</td>
        <td className="px-3 py-2">
          <button onClick={(e) => { e.stopPropagation(); del(); }} aria-label={`Delete ${flag.name} flag`} className="text-slate-400 hover:text-red-600 transition-colors">
            <Trash2 size={12} />
          </button>
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-slate-100 bg-slate-50">
          <td colSpan={8} className="px-4 py-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              <div><span className="text-slate-400">Beta only:</span> <span className="text-slate-700">{flag.beta_only ? "Yes" : "No"}</span></div>
              <div><span className="text-slate-400">Allowed plans:</span> <span className="text-slate-700">{(flag.allowed_plans || []).join(", ") || "All"}</span></div>
              <div><span className="text-slate-400">Activates at:</span> <span className="text-slate-700">{(flag.activates_at || "").slice(0, 16) || "—"}</span></div>
              <div><span className="text-slate-400">Deactivates at:</span> <span className="text-slate-700">{(flag.deactivates_at || "").slice(0, 16) || "—"}</span></div>
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
          <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
            <Plus size={12} /> New Flag
          </Button>
          <Button variant="ghost" size="icon" onClick={refetch} aria-label="Refresh">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </Button>
        </div>
      }
    >

      {/* Stats */}
      <StatGrid cols={4}>
        <StatCard label="Total Flags" value={data?.total ?? 0} />
        <StatCard label="Active" value={data?.active ?? 0} />
        <StatCard
          label="Module Coverage"
          value={<span style={{ color: coverage >= 80 ? EMERALD : coverage >= 50 ? AMBER : CRIMSON }}>{coverage}%</span>}
        />
        <StatCard label="Unmanaged Modules" value={missing.length} />
      </StatGrid>

      {/* Missing modules */}
      {missing.length > 0 && (
        <Alert variant="warning" icon={AlertTriangle}>
          <span className="font-medium">Unmanaged modules:</span> {missing.join(", ")}
        </Alert>
      )}

      {/* Flags table — kept as a raw <table> (not ds/DataTable): rows expand
          in-place to show a flag-detail row and carry a per-row delete
          action, which DataTable's per-cell `render` API can't express (it
          renders exactly one <tr> per row, no inserted detail row). */}
      <div className="bg-white border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-slate-600">
            <thead className="text-slate-400 border-b border-slate-100 bg-slate-50">
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
              {loading && <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-400">Loading...</td></tr>}
              {!loading && flags.map(f => (
                <FlagRow key={f.id} flag={f} onToggle={refetch} onDelete={refetch} />
              ))}
              {!loading && flags.length === 0 && (
                <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-400">No feature flags defined</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showCreate && <CreateFlagModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); refetch(); }} />}
    </AdministrationLayout>
  );
}

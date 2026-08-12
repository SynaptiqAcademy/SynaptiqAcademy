import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, Plus, Tag, ChevronDown, ChevronRight } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  Card, Button, Badge, Input, Textarea, FormSelect, Modal,
  StatCard, StatGrid, Pagination,
} from "@/components/ds";

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

const KIND_BADGE = {
  release:   "success",
  hotfix:    "danger",
  rollback:  "warning",
  migration: "info",
};

const STATUS_BADGE = {
  deployed:     "success",
  planned:      "warning",
  rolled_back:  "danger",
};

// NOTE: this table uses an inline expand/collapse detail row per release
// (features/bugs/breaking changes/notes). ds/DataTable's column+render API
// renders exactly one <tr> per row and has no expandable-detail-row concept,
// so the table markup is left hand-rolled here (only re-themed to the
// standard light palette + Badge for pills) rather than converted to
// DataTable, to avoid dropping the expand behavior.
function ReleaseRow({ release, onRefresh }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer" onClick={() => setExpanded(v => !v)}>
        <td className="px-3 py-2">
          {expanded ? <ChevronDown size={12} className="text-slate-400" /> : <ChevronRight size={12} className="text-slate-400" />}
        </td>
        <td className="px-3 py-2 font-mono text-slate-800 text-xs">{release.version}</td>
        <td className="px-3 py-2 text-slate-600 text-xs">{release.name || "—"}</td>
        <td className="px-3 py-2">
          <Badge variant={KIND_BADGE[release.kind] || "neutral"} size="sm">
            {(release.kind || "release").toUpperCase()}
          </Badge>
        </td>
        <td className="px-3 py-2">
          <Badge variant={STATUS_BADGE[release.status] || "neutral"} size="sm">{release.status}</Badge>
        </td>
        <td className="px-3 py-2 text-xs text-emerald-600">{(release.features || []).length}</td>
        <td className="px-3 py-2 text-xs text-blue-600">{(release.bugs_fixed || []).length}</td>
        <td className="px-3 py-2 text-xs">
          {(release.breaking_changes || []).length > 0 ? (
            <span className="text-red-600">{release.breaking_changes.length} breaking</span>
          ) : <span className="text-slate-400">none</span>}
        </td>
        <td className="px-3 py-2 text-xs text-slate-500">{release.released_by || "—"}</td>
        <td className="px-3 py-2 text-xs text-slate-500">{(release.released_at || "").slice(0, 10)}</td>
      </tr>
      {expanded && (
        <tr className="border-t border-slate-100 bg-slate-50">
          <td colSpan={10} className="px-4 py-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              {[
                { label: "Features", items: release.features, color: "text-emerald-600" },
                { label: "Bugs Fixed", items: release.bugs_fixed, color: "text-blue-600" },
                { label: "Breaking Changes", items: release.breaking_changes, color: "text-red-600" },
              ].map(({ label, items, color }) => (
                <div key={label}>
                  <div className={`font-medium ${color} mb-1`}>{label} ({(items || []).length})</div>
                  <ul className="space-y-0.5">
                    {(items || []).map((item, i) => <li key={i} className="text-slate-500">• {item}</li>)}
                    {(items || []).length === 0 && <li className="text-slate-400">None</li>}
                  </ul>
                </div>
              ))}
            </div>
            {release.release_notes && (
              <div className="mt-3">
                <div className="text-xs text-slate-500 font-medium mb-1">Release Notes</div>
                <div className="text-xs text-slate-600 whitespace-pre-wrap">{release.release_notes}</div>
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
    <Modal
      open
      onClose={onClose}
      title="Log New Release"
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={save} loading={saving}>
            {saving ? "Saving..." : "Log Release"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3 text-xs">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input
            label="Version *"
            value={form.version}
            onChange={e => setForm(f => ({...f, version: e.target.value}))}
            placeholder="v2.4.1"
          />
          <Input
            label="Name"
            value={form.name}
            onChange={e => setForm(f => ({...f, name: e.target.value}))}
            placeholder="Search Overhaul"
          />
          <FormSelect
            label="Kind"
            value={form.kind}
            onChange={e => setForm(f => ({...f, kind: e.target.value}))}
          >
            {["release","hotfix","rollback","migration"].map(k => <option key={k} value={k}>{k}</option>)}
          </FormSelect>
          <FormSelect
            label="Status"
            value={form.status}
            onChange={e => setForm(f => ({...f, status: e.target.value}))}
          >
            {["planned","deployed","rolled_back"].map(s => <option key={s} value={s}>{s}</option>)}
          </FormSelect>
        </div>
        {[
          { key: "features", label: "Features (one per line)" },
          { key: "bugs_fixed", label: "Bugs Fixed (one per line)" },
          { key: "breaking_changes", label: "Breaking Changes (one per line)" },
        ].map(({ key, label }) => (
          <Textarea
            key={key}
            label={label}
            rows={3}
            value={form[key]}
            onChange={e => setForm(f => ({...f, [key]: e.target.value}))}
          />
        ))}
        <Textarea
          label="Release Notes"
          rows={4}
          value={form.release_notes}
          onChange={e => setForm(f => ({...f, release_notes: e.target.value}))}
        />
        {msg && <div className="text-red-600 text-xs">{msg}</div>}
      </div>
    </Modal>
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
          <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
            <Plus size={12} /> Log Release
          </Button>
          <Button variant="ghost" size="icon" onClick={refetch} aria-label="Refresh">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-6">
        <StatGrid cols={4}>
          <StatCard label="Total Releases" value={total} />
          <StatCard label="Releases" value={counts.release || 0} />
          <StatCard label="Hotfixes" value={counts.hotfix || 0} />
          <StatCard label="Rollbacks" value={counts.rollback || 0} />
        </StatGrid>

        <Card padding="none" className="overflow-x-auto">
          <table className="w-full text-xs text-slate-600">
            <thead className="text-slate-500 border-b border-slate-200 bg-slate-50">
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
              {loading && <tr><td colSpan={10} className="px-3 py-8 text-center text-slate-400">Loading...</td></tr>}
              {!loading && items.map(r => <ReleaseRow key={r.id} release={r} onRefresh={refetch} />)}
              {!loading && items.length === 0 && (
                <tr><td colSpan={10} className="px-3 py-8 text-center text-slate-400">No releases logged yet</td></tr>
              )}
            </tbody>
          </table>
        </Card>

        {total > 20 && (
          <Pagination page={page} totalPages={Math.ceil(total / 20)} onPage={(p) => setPage(p)} />
        )}

        {showCreate && <CreateReleaseModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); refetch(); }} />}
      </div>
    </AdministrationLayout>
  );
}

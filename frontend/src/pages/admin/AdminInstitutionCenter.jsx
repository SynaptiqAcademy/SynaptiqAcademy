/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, Search, Building2, ChevronRight, X, TrendingUp } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Drawer, Modal, Button, Input, FormSelect, Badge, StatCard, Alert, Card } from "@/components/ds";

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

function DetailPanel({ instId, onClose }) {
  const { data, loading } = useX(`institutions-center/${instId}`);
  const d = data || {};
  const s = d.stats || {};

  return (
    <Drawer open onClose={onClose} title={d.name || "Institution"}>
      {loading ? (
        <div className="text-sm text-slate-500">Loading...</div>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div><span className="text-slate-500">Country:</span> <span className="text-slate-700 ml-1">{d.country || "—"}</span></div>
            <div><span className="text-slate-500">Type:</span> <span className="text-slate-700 ml-1">{d.type || "—"}</span></div>
            <div className="flex items-center gap-1">
              <span className="text-slate-500">Status:</span>
              <Badge variant={d.status === "active" ? "success" : "danger"}>{d.status || "active"}</Badge>
            </div>
            <div><span className="text-slate-500">Website:</span>
              <a href={d.website} target="_blank" rel="noreferrer" className="text-blue-600 ml-1 hover:underline">
                {d.website ? "Link" : "—"}
              </a>
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 font-medium mb-3">Platform Statistics</div>
            <div className="grid grid-cols-2 gap-2">
              {[
                ["Total Users", s.users], ["Researchers", s.researchers],
                ["Professors", s.professors], ["Publications", s.publications],
                ["Projects", s.projects], ["Collaborations", s.collaborations],
                ["Grants", s.grants], ["Units", s.units],
              ].map(([label, val]) => (
                <StatCard key={label} label={label} value={val ?? 0} />
              ))}
            </div>
          </div>
        </div>
      )}
    </Drawer>
  );
}

function PatchModal({ inst, onClose, onSaved }) {
  const [form, setForm] = useState({ status: inst.status || "active", name: inst.name || "" });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const save = async () => {
    setSaving(true);
    try {
      await api.patch(`/admin/x/institutions-center/${inst.id}`, form);
      onSaved();
    } catch (e) { setMsg(e?.response?.data?.detail || "Error"); }
    finally { setSaving(false); }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Edit Institution"
      size="sm"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button variant="primary" size="sm" onClick={save} loading={saving}>Save</Button>
        </>
      }
    >
      <div className="space-y-3">
        <Input
          label="Name"
          value={form.name}
          onChange={e => setForm(f => ({...f, name: e.target.value}))}
        />
        <FormSelect
          label="Status"
          value={form.status}
          onChange={e => setForm(f => ({...f, status: e.target.value}))}
        >
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
        </FormSelect>
        {msg && <Alert variant="error">{msg}</Alert>}
      </div>
    </Modal>
  );
}

export default function AdminInstitutionCenter() {
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);
  const [editInst, setEditInst] = useState(null);

  const { data, loading, refetch } = useX("institutions-center", { page, limit: 30, search });

  const items = data?.items || [];
  const total = data?.total || 0;

  const doSearch = () => { setSearch(searchInput); setPage(1); };

  return (
    <AdministrationLayout
      title="Institution Management Center"
      subtitle="Academic institution governance — users, publications, grants, departments"
      actions={
        <button onClick={refetch} aria-label="Refresh institutions" className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      }
      sidebar={!loading && items.length > 0 ? <InstitutionCenterSidebar items={items} total={total} /> : undefined}
    >

      {/* Search */}
      <div className="flex gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input value={searchInput} onChange={e => setSearchInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && doSearch()}
            placeholder="Search by name or country..."
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 placeholder-slate-600" />
        </div>
        <button onClick={doSearch} className="text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5">Search</button>
        {search && <button onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }} aria-label="Clear search" className="text-xs text-slate-400 hover:text-white px-2">
          <X size={13} />
        </button>}
        <span className="text-xs text-slate-500 self-center">{total} institutions</span>
      </div>

      {/* Table */}
      <div className="bg-[#0F2847] border border-[#1a3050] overflow-x-auto">
        <table className="w-full text-xs text-slate-300">
          <thead className="text-slate-500 border-b border-[#1a3050]">
            <tr>
              <th className="text-left px-3 py-2 font-medium">Institution</th>
              <th className="text-left px-3 py-2 font-medium">Country</th>
              <th className="text-left px-3 py-2 font-medium">Type</th>
              <th className="text-left px-3 py-2 font-medium">Status</th>
              <th className="text-right px-3 py-2 font-medium">Users</th>
              <th className="text-right px-3 py-2 font-medium">Pubs</th>
              <th className="text-right px-3 py-2 font-medium">Projects</th>
              <th className="text-right px-3 py-2 font-medium">Score</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={9} className="px-3 py-8 text-center text-slate-500">Loading...</td></tr>}
            {!loading && items.map(inst => (
              <tr key={inst.id} className="border-t border-[#1a3050] hover:bg-[#1a3050]/30">
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <Building2 size={12} className="text-blue-400 flex-shrink-0" />
                    <span className="text-white max-w-[200px] truncate">{inst.name}</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-slate-400">{inst.country || "—"}</td>
                <td className="px-3 py-2 text-slate-400">{inst.type || "—"}</td>
                <td className="px-3 py-2">
                  <span className={inst.status === "active" ? "text-green-400" : "text-red-400"}>{inst.status || "active"}</span>
                </td>
                <td className="px-3 py-2 text-right text-white">{inst.users}</td>
                <td className="px-3 py-2 text-right text-slate-300">{inst.publications}</td>
                <td className="px-3 py-2 text-right text-slate-300">{inst.projects}</td>
                <td className="px-3 py-2 text-right">
                  <span className={inst.engagement_score >= 70 ? "text-green-400" : inst.engagement_score >= 40 ? "text-yellow-400" : "text-red-400"}>
                    {inst.engagement_score}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <div className="flex gap-1">
                    <button onClick={() => setSelected(inst.id)} aria-label={`View ${inst.name} details`} className="text-slate-400 hover:text-blue-400">
                      <ChevronRight size={13} />
                    </button>
                    <button onClick={() => setEditInst(inst)} className="text-slate-400 hover:text-white text-[10px] px-1 border border-[#1a3050] hover:border-slate-500">
                      Edit
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr><td colSpan={9} className="px-3 py-8 text-center text-slate-500">No institutions found</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > 30 && (
        <div className="flex items-center gap-2">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="text-xs px-2 py-1 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white disabled:opacity-50">← Prev</button>
          <span className="text-xs text-slate-500">Page {page} of {Math.ceil(total / 30)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page * 30 >= total}
            className="text-xs px-2 py-1 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white disabled:opacity-50">Next →</button>
        </div>
      )}

      {selected && <DetailPanel instId={selected} onClose={() => setSelected(null)} />}
      {editInst && <PatchModal inst={editInst} onClose={() => setEditInst(null)} onSaved={() => { setEditInst(null); refetch(); }} />}
    </AdministrationLayout>
  );
}

// ── Right rail — computed from the institutions already loaded on this page ───
function InstitutionCenterSidebar({ items, total }) {
  const activeCount = items.filter((i) => (i.status || "active") === "active").length;
  const topByEngagement = [...items].sort((a, b) => (b.engagement_score || 0) - (a.engagement_score || 0)).slice(0, 3);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Building2 size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Directory</div>
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 24, color: "#0f172a" }}>{total}</div>
        <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0" }}>
          {activeCount} of {items.length} on this page are active
        </p>
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <TrendingUp size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Top by Engagement</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {topByEngagement.map((i) => (
            <div key={i.id} style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
              <span style={{ fontSize: 12, color: "#374151", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{i.name}</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a", flexShrink: 0 }}>{i.engagement_score}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

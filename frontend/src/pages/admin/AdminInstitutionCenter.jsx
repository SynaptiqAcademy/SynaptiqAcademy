/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, Search, Building2, ChevronRight, X } from "lucide-react";
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

function DetailPanel({ instId, onClose }) {
  const { data, loading } = useX(`institutions-center/${instId}`);
  const d = data || {};
  const s = d.stats || {};

  return (
    <div className="fixed inset-0 bg-black/60 flex items-start justify-end z-50">
      <div className="bg-[#0B1C35] border-l border-[#1a3050] w-full max-w-md h-full overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1a3050] sticky top-0 bg-[#0B1C35]">
          <span className="text-sm font-semibold text-white">{d.name || "Institution"}</span>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">×</button>
        </div>
        {loading ? (
          <div className="p-5 text-sm text-slate-500">Loading...</div>
        ) : (
          <div className="p-5 space-y-5">
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div><span className="text-slate-500">Country:</span> <span className="text-slate-300 ml-1">{d.country || "—"}</span></div>
              <div><span className="text-slate-500">Type:</span> <span className="text-slate-300 ml-1">{d.type || "—"}</span></div>
              <div><span className="text-slate-500">Status:</span>
                <span className={`ml-1 ${d.status === "active" ? "text-green-400" : "text-red-400"}`}>{d.status || "active"}</span>
              </div>
              <div><span className="text-slate-500">Website:</span>
                <a href={d.website} target="_blank" rel="noreferrer" className="text-blue-400 ml-1 hover:underline">
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
                  <div key={label} className="bg-[#0F2847] border border-[#1a3050] p-3">
                    <div className="text-lg font-bold text-white">{val ?? 0}</div>
                    <div className="text-[10px] text-slate-500">{label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
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
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-[#0B1C35] border border-[#1a3050] w-full max-w-sm">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1a3050]">
          <span className="text-sm font-semibold text-white">Edit Institution</span>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">×</button>
        </div>
        <div className="p-5 space-y-3">
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Name</label>
            <input value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))}
              className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5" />
          </div>
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Status</label>
            <select value={form.status} onChange={e => setForm(f => ({...f, status: e.target.value}))}
              className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5">
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
            </select>
          </div>
          {msg && <div className="text-xs text-red-400">{msg}</div>}
          <div className="flex gap-2 pt-1">
            <button onClick={onClose} className="flex-1 text-xs text-slate-400 border border-[#1a3050] px-3 py-2 hover:text-white">Cancel</button>
            <button onClick={save} disabled={saving} className="flex-1 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-2">
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
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
        <button onClick={refetch} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      }
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
        {search && <button onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }} className="text-xs text-slate-400 hover:text-white px-2">
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
                    <button onClick={() => setSelected(inst.id)} className="text-slate-400 hover:text-blue-400">
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

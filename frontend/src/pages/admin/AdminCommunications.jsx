/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { Megaphone, Plus, Trash2, RefreshCw, CheckCircle } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

function useAOS(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch = useCallback(() => {
    setLoading(true);
    api.get(`/admin/aos/${path}`)
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [path]);
  useEffect(() => { fetch(); }, [fetch]);
  return { data, loading, refetch: fetch };
}

const KIND_COLORS = {
  info:    "text-blue-400 bg-blue-900/30",
  warning: "text-yellow-400 bg-yellow-900/30",
  success: "text-green-400 bg-green-900/30",
  promo:   "text-purple-400 bg-purple-900/30",
};

export default function AdminCommunications() {
  const { data: stats, loading: sLoad, refetch: refStats } = useAOS("communications/stats");
  const { data: banners, loading: bLoad, refetch: refBanners } = useAOS("banners");

  const [form, setForm] = useState({ title: "", message: "", kind: "info", segment: "all", link: "" });
  const [creating, setCreating] = useState(false);
  const [msg, setMsg] = useState("");

  const createBanner = async () => {
    if (!form.title || !form.message) { setMsg("Title and message required"); return; }
    setCreating(true);
    setMsg("");
    try {
      await api.post("/admin/aos/banners", form);
      setMsg("Banner created");
      setForm({ title: "", message: "", kind: "info", segment: "all", link: "" });
      refBanners();
      refStats();
    } catch (e) {
      setMsg(e?.response?.data?.detail || "Error");
    } finally {
      setCreating(false);
    }
  };

  const deleteBanner = async (id) => {
    try {
      await api.delete(`/admin/aos/banners/${id}`);
      refBanners();
    } catch (e) {
      console.error(e);
    }
  };

  const loading = sLoad || bLoad;

  return (
    <AdministrationLayout
      title="Communications Center"
      subtitle="Platform banners, announcements, and campaign analytics"
      actions={
        <button onClick={() => { refStats(); refBanners(); }} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      }
    >

      {/* Stats */}
      {!sLoad && stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Total Announcements", value: stats.total_announcements },
            { label: "Total Banners", value: stats.total_banners },
            { label: "Active Banners", value: stats.active_banners },
            { label: "Email Campaigns", value: stats.total_campaigns },
          ].map(({ label, value }) => (
            <div key={label} className="bg-[#0F2847] border border-[#1a3050] p-4">
              <div className="text-2xl font-bold text-white">{value ?? 0}</div>
              <div className="text-xs text-slate-400">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Create Banner */}
      <div className="bg-[#0F2847] border border-[#1a3050] p-4">
        <div className="flex items-center gap-2 mb-4">
          <Plus size={14} className="text-blue-400" />
          <div className="text-sm font-semibold text-white">Create Platform Banner</div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Title</label>
            <input
              type="text"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              placeholder="Banner title"
              className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5"
            />
          </div>
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Link (optional)</label>
            <input
              type="text"
              value={form.link}
              onChange={(e) => setForm((f) => ({ ...f, link: e.target.value }))}
              placeholder="https://..."
              className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5"
            />
          </div>
        </div>
        <div className="mb-3">
          <label className="block text-[10px] text-slate-500 mb-1">Message</label>
          <textarea
            value={form.message}
            onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))}
            placeholder="Banner message..."
            rows={2}
            className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5 resize-none"
          />
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Kind</label>
            <select
              value={form.kind}
              onChange={(e) => setForm((f) => ({ ...f, kind: e.target.value }))}
              className="text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5"
            >
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="success">Success</option>
              <option value="promo">Promotion</option>
            </select>
          </div>
          <div>
            <label className="block text-[10px] text-slate-500 mb-1">Segment</label>
            <select
              value={form.segment}
              onChange={(e) => setForm((f) => ({ ...f, segment: e.target.value }))}
              className="text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5"
            >
              <option value="all">All Users</option>
              <option value="free">Free Only</option>
              <option value="paid">Paid Only</option>
            </select>
          </div>
          <button
            onClick={createBanner}
            disabled={creating}
            className="text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-4 py-1.5 transition-colors self-end"
          >
            {creating ? "Creating..." : "Create Banner"}
          </button>
          {msg && <span className="text-xs text-slate-400 self-end">{msg}</span>}
        </div>
      </div>

      {/* Banner list */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Active Banners</div>
        {bLoad ? (
          <div className="text-slate-500 text-sm py-8 text-center">Loading banners...</div>
        ) : (banners?.items || []).filter((b) => b.active).length === 0 ? (
          <div className="bg-[#0F2847] border border-[#1a3050] p-8 text-center text-slate-500 text-sm">
            No active banners
          </div>
        ) : (
          <div className="space-y-3">
            {(banners?.items || []).filter((b) => b.active).map((b) => (
              <div key={b.id} className="bg-[#0F2847] border border-[#1a3050] p-4 flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] px-2 py-0.5 font-medium ${KIND_COLORS[b.kind] || "text-slate-400 bg-slate-800"}`}>
                      {b.kind}
                    </span>
                    <span className="text-[10px] text-slate-500">{b.segment} · {b.created_at?.slice(0, 10)}</span>
                  </div>
                  <div className="text-sm text-white font-medium">{b.title}</div>
                  <div className="text-xs text-slate-400 mt-0.5">{b.message}</div>
                  {b.link && <div className="text-[10px] text-blue-400 mt-1">{b.link}</div>}
                </div>
                <button
                  onClick={() => deleteBanner(b.id)}
                  className="text-slate-500 hover:text-red-400 transition-colors flex-shrink-0"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent announcements */}
      {!sLoad && (stats?.recent_announcements || []).length > 0 && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Recent Announcements</div>
          <div className="bg-[#0F2847] border border-[#1a3050] overflow-x-auto">
            <table className="w-full text-xs text-slate-300">
              <thead className="text-slate-500 border-b border-[#1a3050]">
                <tr>
                  {["Title", "Segment", "Sent By", "Date"].map((h) => (
                    <th key={h} className="text-left px-3 py-2 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {stats.recent_announcements.map((a) => (
                  <tr key={a.id} className="border-t border-[#1a3050]">
                    <td className="px-3 py-2 text-white">{a.title}</td>
                    <td className="px-3 py-2 text-slate-400">{a.segment}</td>
                    <td className="px-3 py-2 text-slate-400">{a.sent_by || "system"}</td>
                    <td className="px-3 py-2 text-slate-400">{(a.created_at || "").slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AdministrationLayout>
  );
}

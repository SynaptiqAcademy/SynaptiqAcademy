import React, { useState, useCallback, useEffect } from "react";
import { Gift, TrendingUp, Users, RefreshCw, Plus, Check } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

function useAOS(path, params = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const query = new URLSearchParams(params).toString();
  const fetch = useCallback(() => {
    setLoading(true);
    api.get(`/admin/aos/${path}${query ? "?" + query : ""}`)
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [path, query]);
  useEffect(() => { fetch(); }, [fetch]);
  return { data, loading, refetch: fetch };
}

function CreateCampaignModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    name: "", description: "", kind: "credits", segment: "free", value: 100, expires_at: "",
  });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const submit = async () => {
    if (!form.name) { setMsg("Name required"); return; }
    setLoading(true);
    try {
      await api.post("/admin/aos/promotions/campaign", form);
      setMsg("Campaign created");
      onCreated();
    } catch (e) {
      setMsg(e?.response?.data?.detail || "Error");
    } finally {
      setLoading(false);
    }
  };

  const field = (key, label, type = "text", opts = {}) => (
    <div>
      <label className="block text-[10px] text-slate-500 mb-1">{label}</label>
      {opts.options ? (
        <select
          value={form[key]}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
          className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5"
        >
          {opts.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      ) : (
        <input
          type={type}
          value={form[key]}
          onChange={(e) => setForm((f) => ({ ...f, [key]: type === "number" ? Number(e.target.value) : e.target.value }))}
          placeholder={opts.placeholder || ""}
          className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5"
        />
      )}
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-[#0B1C35] border border-[#1a3050] w-full max-w-md">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1a3050]">
          <h2 className="text-sm font-semibold text-white">Create Campaign</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg leading-none">×</button>
        </div>
        <div className="p-5 space-y-3">
          {field("name",        "Campaign Name",  "text", { placeholder: "e.g. Summer Research Boost" })}
          {field("description", "Description",    "text")}
          {field("kind",        "Kind",           "select", { options: [
            { value: "credits",  label: "Credits Grant" },
            { value: "trial",    label: "Free Trial" },
            { value: "discount", label: "Discount" },
          ]})}
          {field("segment",     "Target Segment", "select", { options: [
            { value: "all",  label: "All Users" },
            { value: "free", label: "Free Users" },
            { value: "paid", label: "Paid Users" },
          ]})}
          {field("value",       "Value (credits/days/pct)", "number")}
          {field("expires_at",  "Expires At", "date")}
          {msg && <div className="text-xs text-slate-400">{msg}</div>}
          <div className="flex gap-2 pt-2">
            <button onClick={onClose} className="flex-1 text-xs text-slate-400 border border-[#1a3050] px-3 py-2 hover:text-white transition-colors">
              Cancel
            </button>
            <button onClick={submit} disabled={loading} className="flex-1 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-2 transition-colors">
              {loading ? "Creating..." : "Create Campaign"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AdminPromotions() {
  const [days, setDays] = useState(30);
  const [showCreate, setShowCreate] = useState(false);

  const { data: stats, loading: stLoad, refetch: refStats } = useAOS("promotions/stats", { days });
  const { data: campaigns, loading: cLoad, refetch: refCampaigns } = useAOS("promotions/campaigns");

  const loading = stLoad || cLoad;
  const s = stats || {};

  return (
    <AdministrationLayout
      title="Promotion & Growth Engine"
      subtitle="Campaigns, redemptions, and conversion analytics"
      actions={
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5"
          >
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 transition-colors"
          >
            <Plus size={12} />
            New Campaign
          </button>
          <button onClick={() => { refStats(); refCampaigns(); }} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      }
    >

      {/* Stats */}
      {!stLoad && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-[#0F2847] border border-[#1a3050] p-4 flex items-center gap-3">
            <Gift size={18} className="text-purple-400 flex-shrink-0" />
            <div>
              <div className="text-xl font-bold text-white">{s.total_promotions?.toLocaleString()}</div>
              <div className="text-xs text-slate-400">Total Promotions</div>
            </div>
          </div>
          <div className="bg-[#0F2847] border border-[#1a3050] p-4 flex items-center gap-3">
            <Users size={18} className="text-blue-400 flex-shrink-0" />
            <div>
              <div className="text-xl font-bold text-white">{s.unique_recipients?.toLocaleString()}</div>
              <div className="text-xs text-slate-400">Unique Recipients ({days}d)</div>
            </div>
          </div>
          <div className="bg-[#0F2847] border border-[#1a3050] p-4 flex items-center gap-3">
            <TrendingUp size={18} className="text-green-400 flex-shrink-0" />
            <div>
              <div className="text-xl font-bold text-white">{s.conversions}</div>
              <div className="text-xs text-slate-400">Conversions</div>
              <div className="text-[10px] text-slate-500">from promo recipients</div>
            </div>
          </div>
          <div className="bg-[#0F2847] border border-[#1a3050] p-4">
            <div className="text-xl font-bold text-green-400">{s.conversion_rate_pct}%</div>
            <div className="text-xs text-slate-400">Promo Conversion Rate</div>
            <div className="text-[10px] text-slate-500">recipients who upgraded</div>
          </div>
        </div>
      )}

      {/* By kind breakdown */}
      {!stLoad && (s.by_kind || []).length > 0 && (
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="text-sm font-semibold text-white mb-3">Promotion Types</div>
          <div className="space-y-2">
            {s.by_kind.map((k) => (
              <div key={k._id} className="flex items-center gap-3">
                <div className="text-xs text-slate-400 w-24 truncate">{k._id || "Unknown"}</div>
                <div className="flex-1 h-2 bg-[#1a3050] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-purple-500"
                    style={{ width: `${Math.min(100, (k.count / Math.max(...s.by_kind.map((x) => x.count), 1)) * 100)}%` }}
                  />
                </div>
                <div className="text-xs text-white w-12 text-right">{k.count}</div>
                <div className="text-xs text-slate-500 w-20 text-right">
                  {k.credits_granted ? `${k.credits_granted} credits` : ""}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Campaigns */}
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Campaigns</h2>
        {cLoad ? (
          <div className="text-slate-500 text-sm py-8 text-center">Loading campaigns...</div>
        ) : (campaigns?.items || []).length === 0 ? (
          <div className="bg-[#0F2847] border border-[#1a3050] p-8 text-center">
            <Gift size={24} className="text-slate-500 mx-auto mb-2" />
            <div className="text-slate-400 text-sm">No campaigns yet</div>
            <button
              onClick={() => setShowCreate(true)}
              className="mt-3 inline-flex items-center gap-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5"
            >
              <Plus size={12} />
              Create First Campaign
            </button>
          </div>
        ) : (
          <div className="bg-[#0F2847] border border-[#1a3050] overflow-x-auto">
            <table className="w-full text-xs text-slate-300">
              <thead className="text-slate-500 border-b border-[#1a3050]">
                <tr>
                  {["Campaign", "Kind", "Segment", "Value", "Redemptions", "Conversions", "Rate", "Status", "Created"].map((h) => (
                    <th key={h} className="text-left px-3 py-2 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(campaigns.items || []).map((c) => (
                  <tr key={c.id} className="border-t border-[#1a3050] hover:bg-[#1a3050]/30">
                    <td className="px-3 py-2 text-white font-medium">{c.name}</td>
                    <td className="px-3 py-2 text-slate-400">{c.kind}</td>
                    <td className="px-3 py-2 text-slate-400">{c.segment}</td>
                    <td className="px-3 py-2">{c.value}</td>
                    <td className="px-3 py-2">{c.redemptions || 0}</td>
                    <td className="px-3 py-2 text-green-400">{c.conversions || 0}</td>
                    <td className="px-3 py-2 text-green-400">{c.conversion_rate}%</td>
                    <td className="px-3 py-2">
                      <span className={`text-[10px] px-1.5 py-0.5 ${c.active ? "text-green-400" : "text-slate-500"}`}>
                        {c.active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-400">{(c.created_at || "").slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreate && (
        <CreateCampaignModal
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); refCampaigns(); refStats(); }}
        />
      )}
    </AdministrationLayout>
  );
}

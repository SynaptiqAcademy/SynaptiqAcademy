import React, { useState, useEffect, useCallback } from "react";
import { CreditCard, TrendingDown, Clock, RefreshCw, Check, X } from "lucide-react";
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

const PLAN_COLORS = {
  free:           "text-slate-400 bg-slate-800",
  researcher:     "text-blue-400 bg-blue-900/30",
  pro_researcher: "text-purple-400 bg-purple-900/30",
  institution:    "text-green-400 bg-green-900/30",
};

function PlanBadge({ plan }) {
  const cls = PLAN_COLORS[plan] || "text-slate-400 bg-slate-800";
  return <span className={`text-[10px] px-2 py-0.5 font-medium ${cls}`}>{plan}</span>;
}

function SubscriptionAction({ uid, onDone }) {
  const [action, setAction] = useState("cancel");
  const [plan, setPlan] = useState("free");
  const [days, setDays] = useState(30);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const submit = async () => {
    setLoading(true);
    setMsg("");
    try {
      const body = { action, reason };
      if (action === "upgrade" || action === "downgrade") body.plan = plan;
      if (action === "extend") body.days = days;
      await api.patch(`/admin/aos/subscriptions/${uid}`, body);
      setMsg("Done");
      onDone();
    } catch (e) {
      setMsg(e?.response?.data?.detail || "Error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <select
        value={action}
        onChange={(e) => setAction(e.target.value)}
        className="text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1"
      >
        <option value="cancel">Cancel</option>
        <option value="extend">Extend</option>
        <option value="upgrade">Upgrade</option>
        <option value="downgrade">Downgrade</option>
      </select>
      {(action === "upgrade" || action === "downgrade") && (
        <select
          value={plan}
          onChange={(e) => setPlan(e.target.value)}
          className="text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1"
        >
          <option value="free">Free</option>
          <option value="researcher">Researcher</option>
          <option value="pro_researcher">Pro Researcher</option>
          <option value="institution">Institution</option>
        </select>
      )}
      {action === "extend" && (
        <input
          type="number"
          min={1}
          max={365}
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1 w-16"
          placeholder="days"
        />
      )}
      <input
        type="text"
        placeholder="Reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1 w-28"
      />
      <button
        onClick={submit}
        disabled={loading}
        className="text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-1 transition-colors"
      >
        {loading ? "..." : "Apply"}
      </button>
      {msg && <span className="text-xs text-slate-400">{msg}</span>}
    </div>
  );
}

export default function AdminSubscriptions() {
  const [tab, setTab] = useState("all");
  const [page, setPage] = useState(1);
  const [planFilter, setPlanFilter] = useState("");
  const [expanded, setExpanded] = useState(null);

  const params = { page, limit: 40 };
  if (planFilter) params.plan = planFilter;
  if (tab === "free") params.status = "free";
  else if (tab === "active") params.status = "active";
  else if (tab === "suspended") params.status = "suspended";

  const { data, loading, refetch } = useAOS("subscriptions", params);
  const { data: churned } = useAOS("subscriptions/churned", { days: 30 });
  const { data: trials } = useAOS("subscriptions/trials");

  const items = data?.items || [];
  const total = data?.total || 0;

  const TABS = [
    { key: "all",       label: "All" },
    { key: "active",    label: "Active" },
    { key: "free",      label: "Free" },
    { key: "suspended", label: "Suspended" },
    { key: "trials",    label: `Trials (${trials?.items?.length ?? 0})` },
    { key: "churned",   label: `Churned (${churned?.count ?? 0})` },
  ];

  return (
    <AdministrationLayout
      title="Subscription Control Center"
      subtitle="Manage all user subscriptions"
      actions={
        <button onClick={refetch} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      }
    >

      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-[#0F2847] border border-[#1a3050] p-3 flex items-center gap-3">
          <CreditCard size={18} className="text-blue-400 flex-shrink-0" />
          <div>
            <div className="text-lg font-bold text-white">{total.toLocaleString()}</div>
            <div className="text-xs text-slate-400">Total Subscriptions</div>
          </div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-3 flex items-center gap-3">
          <TrendingDown size={18} className="text-red-400 flex-shrink-0" />
          <div>
            <div className="text-lg font-bold text-white">{churned?.count ?? 0}</div>
            <div className="text-xs text-slate-400">Churned (30d)</div>
          </div>
        </div>
        <div className="bg-[#0F2847] border border-[#1a3050] p-3 flex items-center gap-3">
          <Clock size={18} className="text-yellow-400 flex-shrink-0" />
          <div>
            <div className="text-lg font-bold text-white">{trials?.items?.length ?? 0}</div>
            <div className="text-xs text-slate-400">On Trial</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[#1a3050]">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); setPage(1); }}
            className={`px-3 py-2 text-xs transition-colors ${
              tab === t.key ? "text-white border-b-2 border-blue-400" : "text-slate-400 hover:text-white"
            }`}
          >
            {t.label}
          </button>
        ))}
        <div className="ml-auto flex items-center">
          <select
            value={planFilter}
            onChange={(e) => { setPlanFilter(e.target.value); setPage(1); }}
            className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1"
          >
            <option value="">All plans</option>
            <option value="free">Free</option>
            <option value="researcher">Researcher</option>
            <option value="pro_researcher">Pro Researcher</option>
            <option value="institution">Institution</option>
          </select>
        </div>
      </div>

      {/* Churned tab */}
      {tab === "churned" && (
        <div className="bg-[#0F2847] border border-[#1a3050] overflow-x-auto">
          <table className="w-full text-xs text-slate-300">
            <thead className="text-slate-500 border-b border-[#1a3050]">
              <tr>
                {["User ID", "From Plan", "To Plan", "Action", "Reason", "By Admin", "Date"].map((h) => (
                  <th key={h} className="text-left px-3 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(churned?.items || []).map((c, i) => (
                <tr key={i} className="border-t border-[#1a3050] hover:bg-[#1a3050]/40">
                  <td className="px-3 py-2 font-mono text-slate-400">{c.user_id?.slice(-8)}</td>
                  <td className="px-3 py-2"><PlanBadge plan={c.from_plan} /></td>
                  <td className="px-3 py-2"><PlanBadge plan={c.to_plan || "free"} /></td>
                  <td className="px-3 py-2">{c.action}</td>
                  <td className="px-3 py-2 text-slate-400">{c.reason || "—"}</td>
                  <td className="px-3 py-2 text-slate-400">{c.by_admin || "user"}</td>
                  <td className="px-3 py-2 text-slate-400">{(c.created_at || "").slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Trials tab */}
      {tab === "trials" && (
        <div className="bg-[#0F2847] border border-[#1a3050] overflow-x-auto">
          <table className="w-full text-xs text-slate-300">
            <thead className="text-slate-500 border-b border-[#1a3050]">
              <tr>
                {["Name", "Email", "Plan", "Trial Ends", "Joined"].map((h) => (
                  <th key={h} className="text-left px-3 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(trials?.items || []).map((u) => (
                <tr key={u.id} className="border-t border-[#1a3050] hover:bg-[#1a3050]/40">
                  <td className="px-3 py-2">{u.full_name || "—"}</td>
                  <td className="px-3 py-2 text-slate-400">{u.email}</td>
                  <td className="px-3 py-2"><PlanBadge plan={u.plan_code || "free"} /></td>
                  <td className="px-3 py-2 text-slate-400">{(u.trial_ends_at || "").slice(0, 10)}</td>
                  <td className="px-3 py-2 text-slate-400">{(u.created_at || "").slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Main list */}
      {tab !== "churned" && tab !== "trials" && (
        <div className="bg-[#0F2847] border border-[#1a3050] overflow-x-auto">
          <table className="w-full text-xs text-slate-300">
            <thead className="text-slate-500 border-b border-[#1a3050]">
              <tr>
                {["Name", "Email", "Plan", "Status", "Credits", "Joined", "Actions"].map((h) => (
                  <th key={h} className="text-left px-3 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">Loading...</td></tr>
              )}
              {!loading && items.map((u) => (
                <React.Fragment key={u.id}>
                  <tr className="border-t border-[#1a3050] hover:bg-[#1a3050]/40">
                    <td className="px-3 py-2">{u.name || "—"}</td>
                    <td className="px-3 py-2 text-slate-400">{u.email}</td>
                    <td className="px-3 py-2"><PlanBadge plan={u.plan} /></td>
                    <td className="px-3 py-2">
                      <span className={`text-[10px] px-1.5 py-0.5 ${u.account_status === "active" ? "text-green-400" : "text-red-400"}`}>
                        {u.account_status}
                      </span>
                    </td>
                    <td className="px-3 py-2">{u.credits?.toLocaleString()}</td>
                    <td className="px-3 py-2 text-slate-400">{(u.created_at || "").slice(0, 10)}</td>
                    <td className="px-3 py-2">
                      <button
                        onClick={() => setExpanded(expanded === u.id ? null : u.id)}
                        className="text-[10px] text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        {expanded === u.id ? "Close" : "Manage"}
                      </button>
                    </td>
                  </tr>
                  {expanded === u.id && (
                    <tr className="border-t border-[#1a3050] bg-[#0B1C35]">
                      <td colSpan={7} className="px-3 py-3">
                        <SubscriptionAction uid={u.id} onDone={refetch} />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
              {!loading && items.length === 0 && (
                <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-500">No subscriptions found</td></tr>
              )}
            </tbody>
          </table>
          {/* Pagination */}
          <div className="flex items-center justify-between px-3 py-2 border-t border-[#1a3050]">
            <span className="text-xs text-slate-500">{total} total</span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="text-xs text-slate-400 hover:text-white disabled:opacity-40 px-2 py-1 bg-[#0B1C35] border border-[#1a3050]"
              >
                Prev
              </button>
              <span className="text-xs text-slate-400 px-2 py-1">Page {page}</span>
              <button
                disabled={items.length < 40}
                onClick={() => setPage((p) => p + 1)}
                className="text-xs text-slate-400 hover:text-white disabled:opacity-40 px-2 py-1 bg-[#0B1C35] border border-[#1a3050]"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </AdministrationLayout>
  );
}

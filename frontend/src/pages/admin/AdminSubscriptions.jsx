import React, { useState, useEffect, useCallback } from "react";
import { CreditCard, TrendingDown, Clock, RefreshCw, Check, X } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  Card, Button, Input, FormSelect, Badge, NavTabs, StatCard, StatGrid, DataTable,
} from "@/components/ds";

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

const PLAN_BADGE = {
  free:           "neutral",
  researcher:     "info",
  pro_researcher: "purple",
  institution:    "success",
};

function PlanBadge({ plan }) {
  return <Badge variant={PLAN_BADGE[plan] || "neutral"} size="sm">{plan}</Badge>;
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
      <FormSelect value={action} onChange={(e) => setAction(e.target.value)} size="sm" wrapperClassName="!mb-0">
        <option value="cancel">Cancel</option>
        <option value="extend">Extend</option>
        <option value="upgrade">Upgrade</option>
        <option value="downgrade">Downgrade</option>
      </FormSelect>
      {(action === "upgrade" || action === "downgrade") && (
        <FormSelect value={plan} onChange={(e) => setPlan(e.target.value)} size="sm" wrapperClassName="!mb-0">
          <option value="free">Free</option>
          <option value="researcher">Researcher</option>
          <option value="pro_researcher">Pro Researcher</option>
          <option value="institution">Institution</option>
        </FormSelect>
      )}
      {action === "extend" && (
        <Input
          type="number"
          min={1}
          max={365}
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          size="sm"
          wrapperClassName="w-16 !mb-0"
          placeholder="days"
        />
      )}
      <Input
        type="text"
        placeholder="Reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        size="sm"
        wrapperClassName="w-28 !mb-0"
      />
      <Button variant="primary" size="sm" onClick={submit} disabled={loading} loading={loading}>
        {loading ? "..." : "Apply"}
      </Button>
      {msg && <span className="text-xs text-slate-500">{msg}</span>}
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
    { id: "all",       label: "All" },
    { id: "active",    label: "Active" },
    { id: "free",      label: "Free" },
    { id: "suspended", label: "Suspended" },
    { id: "trials",    label: `Trials (${trials?.items?.length ?? 0})` },
    { id: "churned",   label: `Churned (${churned?.count ?? 0})` },
  ];

  const churnedColumns = [
    { key: "user_id", label: "User ID", render: (v) => <span className="font-mono text-slate-500">{v?.slice(-8)}</span> },
    { key: "from_plan", label: "From Plan", render: (v) => <PlanBadge plan={v} /> },
    { key: "to_plan", label: "To Plan", render: (v) => <PlanBadge plan={v || "free"} /> },
    { key: "action", label: "Action" },
    { key: "reason", label: "Reason", render: (v) => v || "—" },
    { key: "by_admin", label: "By Admin", render: (v) => v || "user" },
    { key: "created_at", label: "Date", render: (v) => (v || "").slice(0, 10) },
  ];

  const trialsColumns = [
    { key: "full_name", label: "Name", render: (v) => v || "—" },
    { key: "email", label: "Email" },
    { key: "plan_code", label: "Plan", render: (v) => <PlanBadge plan={v || "free"} /> },
    { key: "trial_ends_at", label: "Trial Ends", render: (v) => (v || "").slice(0, 10) },
    { key: "created_at", label: "Joined", render: (v) => (v || "").slice(0, 10) },
  ];

  return (
    <AdministrationLayout
      title="Subscription Control Center"
      subtitle="Manage all user subscriptions"
      actions={
        <Button variant="ghost" size="icon" onClick={refetch} aria-label="Refresh">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </Button>
      }
    >
      <div className="flex flex-col gap-6">
        {/* Summary */}
        <StatGrid cols={3}>
          <StatCard icon={<CreditCard />} label="Total Subscriptions" value={total.toLocaleString()} />
          <StatCard icon={<TrendingDown />} label="Churned (30d)" value={churned?.count ?? 0} />
          <StatCard icon={<Clock />} label="On Trial" value={trials?.items?.length ?? 0} />
        </StatGrid>

        {/* Tabs */}
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <NavTabs
            tabs={TABS}
            active={tab}
            onChange={(id) => { setTab(id); setPage(1); }}
            variant="underline"
          />
          <FormSelect
            value={planFilter}
            onChange={(e) => { setPlanFilter(e.target.value); setPage(1); }}
            size="sm"
            wrapperClassName="!mb-0"
          >
            <option value="">All plans</option>
            <option value="free">Free</option>
            <option value="researcher">Researcher</option>
            <option value="pro_researcher">Pro Researcher</option>
            <option value="institution">Institution</option>
          </FormSelect>
        </div>

        {/* Churned tab */}
        {tab === "churned" && (
          <DataTable columns={churnedColumns} rows={churned?.items || []} />
        )}

        {/* Trials tab */}
        {tab === "trials" && (
          <DataTable columns={trialsColumns} rows={trials?.items || []} />
        )}

        {/* Main list — kept hand-rolled: each row can expand into an inline
            management form (SubscriptionAction), which ds/DataTable's
            column+render API can't express (no per-row expandable detail
            row support), same exception as AdminReleases.jsx. */}
        {tab !== "churned" && tab !== "trials" && (
          <Card padding="none" className="overflow-x-auto">
            <table className="w-full text-xs text-slate-600">
              <thead className="text-slate-500 border-b border-slate-200 bg-slate-50">
                <tr>
                  {["Name", "Email", "Plan", "Status", "Credits", "Joined", "Actions"].map((h) => (
                    <th key={h} className="text-left px-3 py-2 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-400">Loading...</td></tr>
                )}
                {!loading && items.map((u) => (
                  <React.Fragment key={u.id}>
                    <tr className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="px-3 py-2">{u.name || "—"}</td>
                      <td className="px-3 py-2 text-slate-500">{u.email}</td>
                      <td className="px-3 py-2"><PlanBadge plan={u.plan} /></td>
                      <td className="px-3 py-2">
                        <Badge variant={u.account_status === "active" ? "success" : "danger"} size="sm">
                          {u.account_status}
                        </Badge>
                      </td>
                      <td className="px-3 py-2">{u.credits?.toLocaleString()}</td>
                      <td className="px-3 py-2 text-slate-500">{(u.created_at || "").slice(0, 10)}</td>
                      <td className="px-3 py-2">
                        <Button variant="link" size="sm" onClick={() => setExpanded(expanded === u.id ? null : u.id)}>
                          {expanded === u.id ? "Close" : "Manage"}
                        </Button>
                      </td>
                    </tr>
                    {expanded === u.id && (
                      <tr className="border-t border-slate-100 bg-slate-50">
                        <td colSpan={7} className="px-3 py-3">
                          <SubscriptionAction uid={u.id} onDone={refetch} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
                {!loading && items.length === 0 && (
                  <tr><td colSpan={7} className="px-3 py-6 text-center text-slate-400">No subscriptions found</td></tr>
                )}
              </tbody>
            </table>
            {/* Pagination — kept hand-rolled: total page count is unknown
                (only "has more" via items.length < 40), so ds/Pagination's
                page/totalPages API doesn't apply here. */}
            <div className="flex items-center justify-between px-3 py-2 border-t border-slate-200">
              <span className="text-xs text-slate-500">{total} total</span>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Prev
                </Button>
                <span className="text-xs text-slate-500 px-2 py-1">Page {page}</span>
                <Button variant="ghost" size="sm" disabled={items.length < 40} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          </Card>
        )}
      </div>
    </AdministrationLayout>
  );
}

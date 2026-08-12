import React, { useState, useCallback, useEffect } from "react";
import { Gift, TrendingUp, Users, RefreshCw, Plus, Check } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  Card, Button, Badge, FormSelect, Input, Modal,
  StatCard, StatGrid, DataTable, EmptyState, ProgressBar,
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
    opts.options ? (
      <FormSelect
        label={label}
        value={form[key]}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
      >
        {opts.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </FormSelect>
    ) : (
      <Input
        label={label}
        type={type}
        value={form[key]}
        onChange={(e) => setForm((f) => ({ ...f, [key]: type === "number" ? Number(e.target.value) : e.target.value }))}
        placeholder={opts.placeholder || ""}
      />
    )
  );

  return (
    <Modal
      open
      onClose={onClose}
      title="Create Campaign"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} loading={loading}>
            {loading ? "Creating..." : "Create Campaign"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
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
        {msg && <div className="text-xs text-slate-500">{msg}</div>}
      </div>
    </Modal>
  );
}

export default function AdminPromotions() {
  const [days, setDays] = useState(30);
  const [showCreate, setShowCreate] = useState(false);

  const { data: stats, loading: stLoad, refetch: refStats } = useAOS("promotions/stats", { days });
  const { data: campaigns, loading: cLoad, refetch: refCampaigns } = useAOS("promotions/campaigns");

  const loading = stLoad || cLoad;
  const s = stats || {};

  const columns = [
    { key: "name", label: "Campaign", render: (v) => <span className="font-medium text-slate-800">{v}</span> },
    { key: "kind", label: "Kind" },
    { key: "segment", label: "Segment" },
    { key: "value", label: "Value" },
    { key: "redemptions", label: "Redemptions", render: (v) => v || 0 },
    { key: "conversions", label: "Conversions", render: (v) => <span className="text-emerald-600">{v || 0}</span> },
    { key: "conversion_rate", label: "Rate", render: (v) => <span className="text-emerald-600">{v}%</span> },
    {
      key: "active",
      label: "Status",
      render: (v) => <Badge variant={v ? "success" : "neutral"} size="sm">{v ? "Active" : "Inactive"}</Badge>,
    },
    { key: "created_at", label: "Created", render: (v) => (v || "").slice(0, 10) },
  ];

  return (
    <AdministrationLayout
      title="Promotion & Growth Engine"
      subtitle="Campaigns, redemptions, and conversion analytics"
      actions={
        <div className="flex items-center gap-2">
          <FormSelect
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            wrapperClassName="!mb-0"
            size="sm"
          >
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </FormSelect>
          <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
            <Plus size={12} />
            New Campaign
          </Button>
          <Button variant="ghost" size="icon" onClick={() => { refStats(); refCampaigns(); }} aria-label="Refresh">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-6">
        {/* Stats */}
        {!stLoad && (
          <StatGrid cols={4}>
            <StatCard icon={<Gift />} label="Total Promotions" value={s.total_promotions?.toLocaleString()} />
            <StatCard icon={<Users />} label={`Unique Recipients (${days}d)`} value={s.unique_recipients?.toLocaleString()} />
            <StatCard icon={<TrendingUp />} label="Conversions" value={s.conversions} sub="from promo recipients" />
            <StatCard label="Promo Conversion Rate" value={`${s.conversion_rate_pct}%`} sub="recipients who upgraded" />
          </StatGrid>
        )}

        {/* By kind breakdown */}
        {!stLoad && (s.by_kind || []).length > 0 && (
          <Card padding="md">
            <div className="text-sm font-semibold text-slate-800 mb-3">Promotion Types</div>
            <div className="flex flex-col gap-3">
              {s.by_kind.map((k) => (
                <div key={k._id} className="flex items-center gap-3">
                  <div className="text-xs text-slate-500 w-24 truncate">{k._id || "Unknown"}</div>
                  <ProgressBar
                    value={k.count}
                    max={Math.max(...s.by_kind.map((x) => x.count), 1)}
                    showValue={false}
                    className="flex-1"
                  />
                  <div className="text-xs text-slate-800 w-12 text-right">{k.count}</div>
                  <div className="text-xs text-slate-500 w-20 text-right">
                    {k.credits_granted ? `${k.credits_granted} credits` : ""}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Campaigns */}
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Campaigns</h2>
          {(campaigns?.items || []).length === 0 && !cLoad ? (
            <EmptyState
              icon={<Gift />}
              title="No campaigns yet"
              action={
                <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
                  <Plus size={12} />
                  Create First Campaign
                </Button>
              }
            />
          ) : (
            <DataTable columns={columns} rows={campaigns?.items || []} loading={cLoad} />
          )}
        </div>

        {showCreate && (
          <CreateCampaignModal
            onClose={() => setShowCreate(false)}
            onCreated={() => { setShowCreate(false); refCampaigns(); refStats(); }}
          />
        )}
      </div>
    </AdministrationLayout>
  );
}

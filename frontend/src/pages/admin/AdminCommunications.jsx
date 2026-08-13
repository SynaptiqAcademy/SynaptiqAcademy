/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { Megaphone, Plus, Trash2, RefreshCw } from "lucide-react";
import api from "@/lib/api";
import { INFO } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  Button, Card, StatCard, StatGrid, Badge, DataTable,
  Input, Textarea, FormSelect, EmptyState, Spinner,
} from "@/components/ds";
import { confirmDialog } from "@/lib/confirm";

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

const KIND_VARIANT = { info: "info", warning: "warning", success: "success", promo: "purple" };

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
    if (!(await confirmDialog({ title: "Delete this banner?", danger: true }))) return;
    try {
      await api.delete(`/admin/aos/banners/${id}`);
      refBanners();
    } catch (e) {
      console.error(e);
    }
  };

  const loading = sLoad || bLoad;

  const announcementColumns = [
    { key: "title", label: "Title" },
    { key: "segment", label: "Segment" },
    { key: "sent_by", label: "Sent By", render: (v) => v || "system" },
    { key: "created_at", label: "Date", render: (v) => (v || "").slice(0, 10) },
  ];

  return (
    <AdministrationLayout
      title="Communications Center"
      subtitle="Platform banners, announcements, and campaign analytics"
      actions={
        <Button variant="ghost" size="icon" onClick={() => { refStats(); refBanners(); }} aria-label="Refresh">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </Button>
      }
    >

      {/* Stats */}
      {!sLoad && stats && (
        <StatGrid cols={4}>
          <StatCard label="Total Announcements" value={stats.total_announcements ?? 0} />
          <StatCard label="Total Banners" value={stats.total_banners ?? 0} />
          <StatCard label="Active Banners" value={stats.active_banners ?? 0} />
          <StatCard label="Email Campaigns" value={stats.total_campaigns ?? 0} />
        </StatGrid>
      )}

      {/* Create Banner */}
      <Card padding="lg">
        <div className="flex items-center gap-2 mb-4">
          <Plus size={14} style={{ color: INFO }} />
          <div className="text-sm font-semibold text-slate-800">Create Platform Banner</div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <Input
            label="Title"
            type="text"
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            placeholder="Banner title"
          />
          <Input
            label="Link (optional)"
            type="text"
            value={form.link}
            onChange={(e) => setForm((f) => ({ ...f, link: e.target.value }))}
            placeholder="https://..."
          />
        </div>
        <div className="mb-3">
          <Textarea
            label="Message"
            value={form.message}
            onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))}
            placeholder="Banner message..."
            rows={2}
          />
        </div>
        <div className="flex items-end gap-3 flex-wrap">
          <FormSelect
            label="Kind"
            value={form.kind}
            onChange={(e) => setForm((f) => ({ ...f, kind: e.target.value }))}
            wrapperClassName="w-40"
          >
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="success">Success</option>
            <option value="promo">Promotion</option>
          </FormSelect>
          <FormSelect
            label="Segment"
            value={form.segment}
            onChange={(e) => setForm((f) => ({ ...f, segment: e.target.value }))}
            wrapperClassName="w-40"
          >
            <option value="all">All Users</option>
            <option value="free">Free Only</option>
            <option value="paid">Paid Only</option>
          </FormSelect>
          <Button variant="primary" size="md" onClick={createBanner} loading={creating}>
            {creating ? "Creating..." : "Create Banner"}
          </Button>
          {msg && <span className="text-xs text-slate-500 self-center">{msg}</span>}
        </div>
      </Card>

      {/* Banner list */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Active Banners</div>
        {bLoad ? (
          <div className="flex items-center justify-center gap-2 text-slate-500 text-sm py-8">
            <Spinner size={16} />
            Loading banners...
          </div>
        ) : (banners?.items || []).filter((b) => b.active).length === 0 ? (
          <EmptyState icon={<Megaphone />} title="No active banners" size="sm" />
        ) : (
          <div className="space-y-3">
            {(banners?.items || []).filter((b) => b.active).map((b) => (
              <Card key={b.id} padding="lg">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant={KIND_VARIANT[b.kind] || "neutral"} size="sm">{b.kind}</Badge>
                      <span className="text-[10px] text-slate-400">{b.segment} · {b.created_at?.slice(0, 10)}</span>
                    </div>
                    <div className="text-sm text-slate-800 font-medium">{b.title}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{b.message}</div>
                    {b.link && <div className="text-[10px] mt-1" style={{ color: INFO }}>{b.link}</div>}
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => deleteBanner(b.id)} aria-label="Delete banner">
                    <Trash2 size={14} />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Recent announcements */}
      {!sLoad && (stats?.recent_announcements || []).length > 0 && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Recent Announcements</div>
          <DataTable columns={announcementColumns} rows={stats.recent_announcements} />
        </div>
      )}
    </AdministrationLayout>
  );
}

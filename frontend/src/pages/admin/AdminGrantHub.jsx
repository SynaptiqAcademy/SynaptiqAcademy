/* eslint-disable */
import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { GitBranch, Users, TrendingUp, Activity } from "lucide-react";
import { AdministrationLayout } from "@/layouts";
import { StatCard, StatGrid, Card, DataTable, Badge, LoadingOverlay, ErrorState } from "@/components/ds";

export default function AdminGrantHub() {
  const [stats, setStats] = useState(null);
  const [collabs, setCollabs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let mounted = true;
    Promise.all([
      api.get("/grant-hub/admin/stats"),
      api.get("/grant-hub/admin/collaborations"),
    ])
      .then(([s, c]) => {
        if (!mounted) return;
        setStats(s.data);
        setCollabs(c.data || []);
      })
      .catch((e) => { if (mounted) setErr(e?.response?.data?.detail || "Failed to load"); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);

  if (loading) return <LoadingOverlay text="Loading…" />;
  if (err) return <ErrorState message={err} />;

  const columns = [
    { key: "title", label: "Title", render: (v) => <span className="font-medium text-slate-800">{v || "Untitled"}</span> },
    {
      key: "status",
      label: "Status",
      render: (v) => <Badge variant={v === "active" ? "success" : "neutral"}>{v || "draft"}</Badge>,
    },
    { key: "partner_count", label: "Partners", render: (_, row) => row.partner_count ?? row.partners?.length ?? 0 },
    {
      key: "created_at",
      label: "Created",
      render: (v) => (v ? new Date(v).toLocaleDateString() : "—"),
    },
  ];

  return (
    <AdministrationLayout
      title="Grant Collaboration Hub"
      subtitle="Consortium builder and grant collaboration platform overview"
      stats={[
        { label: "Total Collaborations", value: stats?.total_collaborations ?? 0 },
        { label: "Active Partners", value: stats?.active_partners ?? 0 },
        { label: "Funding Sought", value: stats?.total_funding_sought ?? 0 },
        { label: "Avg Readiness", value: stats?.avg_readiness_score ? `${stats.avg_readiness_score}%` : "—" },
      ]}
      sidebar={collabs.length > 0 ? <GrantHubSidebar collabs={collabs} /> : undefined}
    >
      <Card padding="none" className="mt-4">
        <div className="px-4 py-3 border-b border-slate-100 text-xs font-semibold uppercase tracking-widest text-slate-500">
          Recent Grant Collaborations
        </div>
        <DataTable
          columns={columns}
          rows={collabs.slice(0, 20)}
          emptyNode={<div className="p-8 text-center text-slate-400 text-sm">No collaborations yet</div>}
        />
      </Card>
    </AdministrationLayout>
  );
}

// ── Right rail — computed from the collaborations already loaded above ────────
function GrantHubSidebar({ collabs }) {
  const statusCounts = collabs.reduce((acc, c) => {
    const s = c.status || "draft";
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});
  const latest = collabs[0];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Activity size={13} style={{ color: "#0F2847" }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>By Status</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {Object.entries(statusCounts).map(([status, count]) => (
            <div key={status} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <Badge variant={status === "active" ? "success" : "neutral"} size="sm">{status}</Badge>
              <span style={{ fontSize: 12, color: "#374151" }}>{count}</span>
            </div>
          ))}
        </div>
      </Card>

      {latest && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <GitBranch size={13} style={{ color: "#0F2847" }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Latest Collaboration</div>
          </div>
          <div style={{ fontFamily: "Georgia, serif", fontSize: 14, color: "#0f172a" }}>{latest.title || "Untitled"}</div>
          <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0" }}>
            {latest.partner_count ?? latest.partners?.length ?? 0} partner{(latest.partner_count ?? latest.partners?.length ?? 0) !== 1 ? "s" : ""}
            {latest.created_at ? ` · ${new Date(latest.created_at).toLocaleDateString()}` : ""}
          </p>
        </Card>
      )}
    </div>
  );
}

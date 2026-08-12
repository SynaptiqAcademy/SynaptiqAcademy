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
    <AdministrationLayout title="Grant Collaboration Hub" subtitle="Consortium builder and grant collaboration platform overview">
      <StatGrid cols={4}>
        <StatCard label="Total Collaborations" value={stats?.total_collaborations} icon={<GitBranch />} />
        <StatCard label="Active Partners" value={stats?.active_partners} icon={<Users />} />
        <StatCard label="Funding Sought" value={stats?.total_funding_sought} icon={<TrendingUp />} />
        <StatCard label="Avg Readiness" value={stats?.avg_readiness_score ? `${stats.avg_readiness_score}%` : "—"} icon={<Activity />} />
      </StatGrid>

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

import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { ShieldCheck, AlertTriangle, CheckCircle, Clock, Users } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  Card, Button, Badge, StatCard, StatGrid, DataTable, ProgressBar,
  EmptyState, ErrorState, Spinner,
} from "@/components/ds";

const LEVEL_LABELS = ["Unverified","Email","Identity","ORCID","Institution","Researcher","Expert","Trusted","Distinguished"];

export default function AdminVerification() {
  const [stats, setStats] = useState(null);
  const [queue, setQueue] = useState([]);
  const [fraud, setFraud] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let mounted = true;
    Promise.all([
      api.get("/verification/admin/stats"),
      api.get("/verification/admin/queue"),
      api.get("/verification/admin/fraud-overview"),
    ])
      .then(([s, q, f]) => {
        if (!mounted) return;
        setStats(s.data);
        setQueue(q.data?.queue || []);
        setFraud(f.data);
      })
      .catch((e) => { if (mounted) setErr(e?.response?.data?.detail || "Failed to load"); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);

  const handleDecide = async (rid, decision) => {
    try {
      await api.post(`/verification/admin/request/${rid}/decide`, { decision, notes: "" });
      setQueue((q) => q.filter((r) => r.id !== rid));
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    }
  };

  if (loading) return <div className="p-8 flex items-center gap-2 text-slate-500 text-sm"><Spinner size={16} /> Loading…</div>;
  if (err) return <div className="p-8"><ErrorState message={err} /></div>;

  const columns = [
    { key: "user_id", label: "User", render: (v) => <span className="text-slate-700">{v}</span> },
    { key: "request_type", label: "Type", render: (v) => <span className="text-slate-600">{v}</span> },
    { key: "status", label: "Status", render: (v) => <Badge variant="warning" size="sm">{v}</Badge> },
    {
      key: "_actions", label: "Actions", align: "right",
      render: (_, r) => (
        <div className="flex justify-end gap-2">
          <Button variant="primary" size="sm" className="!bg-emerald-600 hover:!bg-emerald-700" onClick={() => handleDecide(r.id, "approved")}>Approve</Button>
          <Button variant="subtle" size="sm" onClick={() => handleDecide(r.id, "rejected")}>Reject</Button>
        </div>
      ),
    },
  ];

  return (
    <AdministrationLayout
      title="Verification Admin Center"
      subtitle="Identity verification, trust scores, and fraud detection"
    >
      <div className="flex flex-col gap-6">
        <StatGrid cols={4}>
          <StatCard label="Total Profiles" value={stats?.total_profiles} icon={<Users />} />
          <StatCard label="Verified (≥L2)" value={stats?.verified_count} icon={<ShieldCheck />} />
          <StatCard label="Pending Reviews" value={queue.length} icon={<Clock />} />
          <StatCard label="Fraud Flags" value={fraud?.flagged_count ?? 0} icon={<AlertTriangle />} />
        </StatGrid>

        {/* Level distribution */}
        {stats?.level_distribution && (
          <Card padding="md">
            <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Level Distribution</div>
            <div className="space-y-2">
              {Object.entries(stats.level_distribution).map(([lvl, cnt]) => (
                <div key={lvl} className="flex items-center gap-3">
                  <span className="w-28 text-xs text-slate-600 flex-shrink-0">{LEVEL_LABELS[parseInt(lvl)] || `L${lvl}`}</span>
                  <ProgressBar
                    value={cnt}
                    max={stats?.total_profiles || 1}
                    showValue={false}
                    className="flex-1"
                  />
                  <span className="text-xs font-mono text-slate-500 w-8 text-right">{cnt}</span>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Verification queue */}
        <Card padding="none">
          <div className="px-4 py-3 border-b border-slate-100 text-xs font-semibold uppercase tracking-widest text-slate-500">
            Pending Verification Requests ({queue.length})
          </div>
          {queue.length === 0 ? (
            <EmptyState icon={<CheckCircle />} title="Queue is clear" dashed={false} />
          ) : (
            <DataTable columns={columns} rows={queue.slice(0, 20)} />
          )}
        </Card>
      </div>
    </AdministrationLayout>
  );
}

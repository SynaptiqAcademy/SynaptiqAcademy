import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { AlertTriangle, CheckCircle, Clock } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  Card, Button, Badge, DataTable, ProgressBar,
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
      stats={[
        { label: "Total Profiles",    value: stats?.total_profiles ?? "—" },
        { label: "Verified (≥L2)",    value: stats?.verified_count ?? "—" },
        { label: "Pending Reviews",   value: queue.length },
        { label: "Fraud Flags",       value: fraud?.flagged_count ?? 0 },
      ]}
      sidebar={<VerificationSidebar fraud={fraud} queue={queue} />}
    >
      <div className="flex flex-col gap-6">
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

// ── Right rail — fraud breakdown & queue composition, real data already fetched
function VerificationSidebar({ fraud, queue }) {
  const byType = {};
  queue.forEach((r) => { byType[r.request_type] = (byType[r.request_type] || 0) + 1; });
  const typeEntries = Object.entries(byType).sort((a, b) => b[1] - a[1]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <AlertTriangle size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Fraud Overview (30d)</div>
        </div>
        {fraud ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 4 }}>
              <span className="font-serif" style={{ fontSize: 22, color: "#0f172a" }}>{fraud.flag_rate_pct ?? 0}%</span>
              <span style={{ fontSize: 11, color: "#94A3B8" }}>flag rate</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <span style={{ fontSize: 11.5, color: "#64748B" }}>Flagged users</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>{fraud.total_flagged_users_30d ?? 0}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <span style={{ fontSize: 11.5, color: "#64748B" }}>Review recommended</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>{fraud.review_recommended_count ?? 0}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <span style={{ fontSize: 11.5, color: "#64748B" }}>Manual review required</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>{fraud.manual_review_required_count ?? 0}</span>
            </div>
          </div>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>No fraud data yet.</p>
        )}
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Clock size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Queue by Type</div>
        </div>
        {typeEntries.length === 0 ? (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>Queue is clear.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {typeEntries.map(([type, count]) => (
              <div key={type} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <span style={{ fontSize: 11.5, color: "#374151" }}>{type}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a", fontFamily: "monospace" }}>{count}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

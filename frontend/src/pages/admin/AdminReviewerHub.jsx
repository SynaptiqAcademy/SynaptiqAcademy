import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Star, UserCheck, Award, BarChart2 } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, Input, StatCard, StatGrid, ErrorState, Spinner } from "@/components/ds";

export default function AdminReviewerHub() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [certifyId, setCertifyId] = useState("");
  const [certifyMsg, setCertifyMsg] = useState("");

  useEffect(() => {
    api.get("/reviewer-marketplace/admin/stats")
      .then((r) => setStats(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  const handleCertify = async (e) => {
    e.preventDefault();
    if (!certifyId.trim()) return;
    try {
      await api.post(`/reviewer-marketplace/admin/certify/${certifyId.trim()}`);
      setCertifyMsg("Certification granted successfully.");
      setCertifyId("");
    } catch (err) {
      setCertifyMsg(err?.response?.data?.detail || "Certification failed.");
    }
  };

  if (loading) return <div className="p-8 flex items-center gap-2 text-slate-500 text-sm"><Spinner size={16} /> Loading…</div>;
  if (err) return <div className="p-8"><ErrorState message={err} /></div>;

  return (
    <AdministrationLayout
      title="Reviewer Hub Admin"
      subtitle="Peer review marketplace overview and certification management"
    >
      <div className="flex flex-col gap-4">
        <StatGrid cols={4}>
          <StatCard label="Total Reviewers" value={stats?.total_reviewers} icon={<UserCheck />} />
          <StatCard label="Active Reviews" value={stats?.active_reviews} icon={<Star />} />
          <StatCard label="Certified" value={stats?.certified_reviewers} icon={<Award />} />
          <StatCard label="Avg Quality" value={stats?.avg_quality_score ? `${stats.avg_quality_score.toFixed(1)}` : "—"} icon={<BarChart2 />} />
        </StatGrid>

        <Card padding="md">
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Grant Certification</div>
          <form onSubmit={handleCertify} className="flex gap-2 items-start">
            <Input
              value={certifyId}
              onChange={(e) => setCertifyId(e.target.value)}
              placeholder="User ID to certify…"
              wrapperClassName="flex-1 !mb-0"
            />
            <Button variant="primary" type="submit">Certify</Button>
          </form>
          {certifyMsg && <div className="mt-2 text-sm text-slate-600">{certifyMsg}</div>}
        </Card>

        {stats?.top_areas?.length > 0 && (
          <Card padding="none">
            <div className="px-4 py-3 border-b border-slate-100 text-xs font-semibold uppercase tracking-widest text-slate-500">
              Top Review Areas
            </div>
            <div className="p-4 space-y-2">
              {stats.top_areas.map((a) => (
                <div key={a.area} className="flex items-center justify-between text-sm">
                  <span className="text-slate-700">{a.area}</span>
                  <span className="text-slate-500 font-mono">{a.count}</span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </AdministrationLayout>
  );
}

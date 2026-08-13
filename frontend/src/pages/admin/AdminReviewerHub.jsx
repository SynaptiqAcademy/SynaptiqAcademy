import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Award, BarChart2 } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, Input, ErrorState, Spinner } from "@/components/ds";

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
      stats={[
        { label: "Total Reviewers", value: stats?.total_reviewers ?? "—" },
        { label: "Active Reviews",  value: stats?.active_reviews ?? "—" },
        { label: "Certified",       value: stats?.certified_reviewers ?? "—" },
        { label: "Avg Quality",     value: stats?.avg_quality_score ? stats.avg_quality_score.toFixed(1) : "—" },
      ]}
      sidebar={<ReviewerHubSidebar stats={stats} />}
    >
      <div className="flex flex-col gap-4">
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

// ── Right rail — certification rate & top areas, real data already fetched ────
function ReviewerHubSidebar({ stats }) {
  const total = stats?.total_reviewers || 0;
  const certified = stats?.certified_reviewers || 0;
  const certRate = total > 0 ? Math.round((certified / total) * 100) : null;
  const topAreas = (stats?.top_areas || []).slice(0, 3);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Award size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Certification Rate</div>
        </div>
        {certRate != null ? (
          <div>
            <span className="font-serif" style={{ fontSize: 26, color: "#0f172a" }}>{certRate}%</span>
            <p style={{ fontSize: 11.5, color: "#94A3B8", margin: "6px 0 0" }}>
              {certified.toLocaleString()} of {total.toLocaleString()} reviewers certified
            </p>
          </div>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>No reviewer data yet.</p>
        )}
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <BarChart2 size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Top Review Areas</div>
        </div>
        {topAreas.length === 0 ? (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>No area data yet.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {topAreas.map((a) => (
              <div key={a.area} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <span style={{ fontSize: 11.5, color: "#374151" }}>{a.area}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a", fontFamily: "monospace" }}>{a.count}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

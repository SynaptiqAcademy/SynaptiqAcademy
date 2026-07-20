import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Star, UserCheck, Award, BarChart2 } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

function StatCard({ label, value, icon: Icon, color = "text-blue-600" }) {
  return (
    <div className="bg-white border border-slate-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs uppercase tracking-widest text-slate-500">{label}</span>
        <Icon size={14} className={color} />
      </div>
      <div className="font-serif text-2xl text-slate-900">{value ?? "—"}</div>
    </div>
  );
}

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

  if (loading) return <div className="p-8 text-slate-500 text-sm">Loading…</div>;
  if (err) return <div className="p-8 text-red-600 text-sm">{err}</div>;

  return (
    <AdministrationLayout
      title="Reviewer Hub Admin"
      subtitle="Peer review marketplace overview and certification management"
    >

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Reviewers" value={stats?.total_reviewers} icon={UserCheck} />
        <StatCard label="Active Reviews" value={stats?.active_reviews} icon={Star} color="text-amber-600" />
        <StatCard label="Certified" value={stats?.certified_reviewers} icon={Award} color="text-emerald-600" />
        <StatCard label="Avg Quality" value={stats?.avg_quality_score ? `${stats.avg_quality_score.toFixed(1)}` : "—"} icon={BarChart2} color="text-purple-600" />
      </div>

      <div className="bg-white border border-slate-200 p-4">
        <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Grant Certification</div>
        <form onSubmit={handleCertify} className="flex gap-2">
          <input
            value={certifyId}
            onChange={(e) => setCertifyId(e.target.value)}
            placeholder="User ID to certify…"
            className="flex-1 border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:border-slate-900"
          />
          <button type="submit" className="bg-[#0F2847] text-white px-4 py-2 text-sm hover:bg-slate-800 transition-colors">
            Certify
          </button>
        </form>
        {certifyMsg && <div className="mt-2 text-sm text-slate-600">{certifyMsg}</div>}
      </div>

      {stats?.top_areas?.length > 0 && (
        <div className="bg-white border border-slate-200">
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
        </div>
      )}
    </AdministrationLayout>
  );
}

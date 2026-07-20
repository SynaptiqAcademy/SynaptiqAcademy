/* eslint-disable */
import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { GitBranch, Users, TrendingUp, Activity } from "lucide-react";
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

  if (loading) return <div className="p-8 text-slate-500 text-sm">Loading…</div>;
  if (err) return <div className="p-8 text-red-600 text-sm">{err}</div>;

  return (
    <AdministrationLayout title="Grant Collaboration Hub" subtitle="Consortium builder and grant collaboration platform overview">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Collaborations" value={stats?.total_collaborations} icon={GitBranch} />
        <StatCard label="Active Partners" value={stats?.active_partners} icon={Users} color="text-emerald-600" />
        <StatCard label="Funding Sought" value={stats?.total_funding_sought} icon={TrendingUp} color="text-amber-600" />
        <StatCard label="Avg Readiness" value={stats?.avg_readiness_score ? `${stats.avg_readiness_score}%` : "—"} icon={Activity} color="text-purple-600" />
      </div>

      <div className="bg-white border border-slate-200">
        <div className="px-4 py-3 border-b border-slate-100 text-xs font-semibold uppercase tracking-widest text-slate-500">
          Recent Grant Collaborations
        </div>
        {collabs.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">No collaborations yet</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs uppercase tracking-widest text-slate-400">
                <th className="px-4 py-2 text-left">Title</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Partners</th>
                <th className="px-4 py-2 text-left">Created</th>
              </tr>
            </thead>
            <tbody>
              {collabs.slice(0, 20).map((c) => (
                <tr key={c.id || c._id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-4 py-2.5 text-slate-800 font-medium">{c.title || "Untitled"}</td>
                  <td className="px-4 py-2.5">
                    <span className={`text-xs px-2 py-0.5 ${c.status === "active" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                      {c.status || "draft"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-slate-600">{c.partner_count ?? c.partners?.length ?? 0}</td>
                  <td className="px-4 py-2.5 text-slate-400">{c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AdministrationLayout>
  );
}

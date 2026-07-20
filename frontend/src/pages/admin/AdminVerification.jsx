import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { ShieldCheck, AlertTriangle, CheckCircle, Clock, Users } from "lucide-react";
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
      alert(e?.response?.data?.detail || "Failed");
    }
  };

  if (loading) return <div className="p-8 text-slate-500 text-sm">Loading…</div>;
  if (err) return <div className="p-8 text-red-600 text-sm">{err}</div>;

  return (
    <AdministrationLayout
      title="Verification Admin Center"
      subtitle="Identity verification, trust scores, and fraud detection"
    >

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Profiles" value={stats?.total_profiles} icon={Users} />
        <StatCard label="Verified (≥L2)" value={stats?.verified_count} icon={ShieldCheck} color="text-emerald-600" />
        <StatCard label="Pending Reviews" value={queue.length} icon={Clock} color="text-amber-600" />
        <StatCard label="Fraud Flags" value={fraud?.flagged_count ?? 0} icon={AlertTriangle} color="text-red-600" />
      </div>

      {/* Level distribution */}
      {stats?.level_distribution && (
        <div className="bg-white border border-slate-200 p-4">
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Level Distribution</div>
          <div className="space-y-2">
            {Object.entries(stats.level_distribution).map(([lvl, cnt]) => (
              <div key={lvl} className="flex items-center gap-3">
                <span className="w-28 text-xs text-slate-600">{LEVEL_LABELS[parseInt(lvl)] || `L${lvl}`}</span>
                <div className="flex-1 h-2 bg-slate-100">
                  <div className="h-2 bg-[#0F2847]" style={{ width: `${Math.min(100, (cnt / (stats?.total_profiles || 1)) * 100)}%` }} />
                </div>
                <span className="text-xs font-mono text-slate-500 w-8 text-right">{cnt}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Verification queue */}
      <div className="bg-white border border-slate-200">
        <div className="px-4 py-3 border-b border-slate-100 text-xs font-semibold uppercase tracking-widest text-slate-500">
          Pending Verification Requests ({queue.length})
        </div>
        {queue.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm flex items-center justify-center gap-2">
            <CheckCircle size={16} className="text-emerald-500" /> Queue is clear
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs uppercase tracking-widest text-slate-400">
                <th className="px-4 py-2 text-left">User</th>
                <th className="px-4 py-2 text-left">Type</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {queue.slice(0, 20).map((r) => (
                <tr key={r.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-4 py-2.5 text-slate-700">{r.user_id}</td>
                  <td className="px-4 py-2.5 text-slate-600">{r.request_type}</td>
                  <td className="px-4 py-2.5">
                    <span className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5">{r.status}</span>
                  </td>
                  <td className="px-4 py-2.5 flex justify-end gap-2">
                    <button onClick={() => handleDecide(r.id, "approved")}
                      className="text-xs bg-emerald-600 text-white px-2 py-1 hover:bg-emerald-700">Approve</button>
                    <button onClick={() => handleDecide(r.id, "rejected")}
                      className="text-xs bg-slate-200 text-slate-700 px-2 py-1 hover:bg-slate-300">Reject</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AdministrationLayout>
  );
}

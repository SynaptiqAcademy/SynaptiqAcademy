import React, { useState, useEffect } from "react";
import { Lock, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

function Section({ title, children }) {
  return (
    <div className="bg-white border border-slate-200 mb-6">
      <div className="px-5 py-4 border-b border-slate-200">
        <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

export default function AdminSecurity() {
  const [failedLogins, setFailedLogins] = useState([]);
  const [blockedIps, setBlockedIps] = useState([]);
  const [hours, setHours] = useState(24);
  const [loading, setLoading] = useState(true);
  const [blockingIp, setBlockingIp] = useState(null);
  const [blockReason, setBlockReason] = useState("");
  const [forceLogoutReason, setForceLogoutReason] = useState("");
  const [showForceConfirm, setShowForceConfirm] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [fl, bi] = await Promise.all([
        api.get(`/admin/security/failed-logins?hours=${hours}`),
        api.get("/admin/security/blocked-ips"),
      ]);
      setFailedLogins(fl.data || []);
      setBlockedIps(bi.data || []);
    } catch (e) {
      toast.error("Failed to load security data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [hours]);

  const blockIp = async (ip) => {
    if (!blockReason.trim()) { toast.error("Please provide a reason"); return; }
    setActionLoading(true);
    try {
      await api.post("/admin/security/block-ip", { ip, reason: blockReason });
      toast.success(`IP ${ip} blocked`);
      setBlockingIp(null);
      setBlockReason("");
      await loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to block IP");
    } finally {
      setActionLoading(false);
    }
  };

  const unblockIp = async (ip) => {
    setActionLoading(true);
    try {
      await api.post("/admin/security/unblock-ip", { ip });
      toast.success(`IP ${ip} unblocked`);
      await loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to unblock IP");
    } finally {
      setActionLoading(false);
    }
  };

  const forceLogoutAll = async () => {
    setActionLoading(true);
    try {
      await api.post("/admin/security/force-logout-all", { reason: forceLogoutReason });
      toast.success("All users have been signed out");
      setShowForceConfirm(false);
      setForceLogoutReason("");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to force logout");
    } finally {
      setActionLoading(false);
    }
  };

  const fmt = (d) => d ? new Date(d).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

  return (
    <AdministrationLayout
      title="Security Center"
      subtitle="Monitor threats and manage platform access"
    >
      {/* Failed Logins */}
      <Section title="Failed Login Attempts">
        <div className="flex gap-3 mb-4">
          <span className="text-sm text-slate-600">Time window:</span>
          {[1, 6, 24, 72].map((h) => (
            <button key={h} onClick={() => setHours(h)}
              className={`px-3 py-1 text-xs border ${hours === h ? "bg-[#0F2847] text-white border-[#0F2847]" : "border-slate-300 text-slate-600 hover:bg-slate-50"}`}>
              {h}h
            </button>
          ))}
        </div>
        {loading ? (
          <div className="space-y-2">{[...Array(4)].map((_, i) => <div key={i} className="h-10 animate-pulse bg-gray-200" />)}</div>
        ) : failedLogins.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-6">No failed login attempts in this window</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 text-xs font-semibold uppercase tracking-widest text-slate-500">IP Address</th>
                <th className="text-left py-2 text-xs font-semibold uppercase tracking-widest text-slate-500">Attempts</th>
                <th className="text-left py-2 text-xs font-semibold uppercase tracking-widest text-slate-500">Latest</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {failedLogins.map((item, i) => (
                <React.Fragment key={i}>
                  <tr className="border-b border-slate-100">
                    <td className="py-2.5 font-mono text-xs">{item.ip}</td>
                    <td className="py-2.5">
                      <span className={`inline-block px-2 py-0.5 text-xs font-medium ${item.count > 10 ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>
                        {item.count}
                      </span>
                    </td>
                    <td className="py-2.5 text-xs text-slate-500">{fmt(item.latest)}</td>
                    <td className="py-2.5 text-right">
                      {blockingIp === item.ip ? (
                        <div className="flex items-center gap-2">
                          <input value={blockReason} onChange={(e) => setBlockReason(e.target.value)}
                            placeholder="Reason…" className="px-2 py-1 text-xs border border-slate-300 focus:outline-none w-32" />
                          <button onClick={() => blockIp(item.ip)} disabled={actionLoading}
                            className="px-2 py-1 text-xs bg-red-700 text-white hover:bg-red-800 disabled:opacity-50">Block</button>
                          <button onClick={() => { setBlockingIp(null); setBlockReason(""); }} className="px-2 py-1 text-xs border border-slate-300 hover:bg-slate-50">Cancel</button>
                        </div>
                      ) : (
                        <button onClick={() => setBlockingIp(item.ip)} className="text-xs text-red-700 hover:underline">Block IP</button>
                      )}
                    </td>
                  </tr>
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      {/* Blocked IPs */}
      <Section title="Blocked IP Addresses">
        {blockedIps.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-6">No blocked IPs</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 text-xs font-semibold uppercase tracking-widest text-slate-500">IP Address</th>
                <th className="text-left py-2 text-xs font-semibold uppercase tracking-widest text-slate-500">Reason</th>
                <th className="text-left py-2 text-xs font-semibold uppercase tracking-widest text-slate-500">Blocked At</th>
                <th className="text-left py-2 text-xs font-semibold uppercase tracking-widest text-slate-500">By</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {blockedIps.map((item, i) => (
                <tr key={i} className="border-b border-slate-100">
                  <td className="py-2.5 font-mono text-xs">{item.ip}</td>
                  <td className="py-2.5 text-xs text-slate-600">{item.reason || "—"}</td>
                  <td className="py-2.5 text-xs text-slate-500">{fmt(item.blocked_at)}</td>
                  <td className="py-2.5 text-xs text-slate-500">{item.blocked_by || "—"}</td>
                  <td className="py-2.5 text-right">
                    <button onClick={() => unblockIp(item.ip)} disabled={actionLoading}
                      className="text-xs text-green-700 hover:underline disabled:opacity-50">Unblock</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      {/* Emergency Controls */}
      <div className="border-2 border-red-200 bg-red-50 p-5">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle size={16} className="text-red-700" />
          <h2 className="text-sm font-semibold text-red-800">Emergency Controls</h2>
        </div>
        <p className="text-sm text-red-700 mb-4">These actions affect all users on the platform and cannot be undone.</p>
        {showForceConfirm ? (
          <div className="space-y-3">
            <p className="text-sm font-medium text-red-800">Are you sure you want to force sign out ALL users?</p>
            <textarea
              value={forceLogoutReason}
              onChange={(e) => setForceLogoutReason(e.target.value)}
              placeholder="Reason for emergency logout (required)…"
              rows={2}
              className="w-full px-3 py-2 text-sm border border-red-300 bg-white focus:outline-none"
            />
            <div className="flex gap-2">
              <button onClick={forceLogoutAll} disabled={actionLoading || !forceLogoutReason.trim()}
                className="px-4 py-2 bg-red-700 text-white text-sm hover:bg-red-800 disabled:opacity-50">
                {actionLoading ? "Working…" : "Confirm — Sign out all users"}
              </button>
              <button onClick={() => { setShowForceConfirm(false); setForceLogoutReason(""); }}
                className="px-4 py-2 border border-slate-300 text-sm text-slate-700 hover:bg-white">
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button onClick={() => setShowForceConfirm(true)}
            className="px-4 py-2 bg-red-700 text-white text-sm font-medium hover:bg-red-800 flex items-center gap-2">
            <Lock size={14} />
            Force Sign Out ALL Users
          </button>
        )}
      </div>
    </AdministrationLayout>
  );
}

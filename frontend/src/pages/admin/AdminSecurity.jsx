import React, { useState, useEffect, useCallback } from "react";
import { Lock, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { NAVY, CRIMSON } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, Input, Textarea, Badge, DataTable, SkeletonTable } from "@/components/ds";

function Section({ title, children }) {
  return (
    <Card padding="none" className="mb-6">
      <div className="px-5 py-4 border-b border-slate-200">
        <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </Card>
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

  const loadData = useCallback(async () => {
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
  }, [hours]);

  useEffect(() => { loadData(); }, [loadData]);

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

  const failedLoginColumns = [
    { key: "ip", label: "IP Address", render: (v) => <span className="font-mono text-xs">{v}</span> },
    {
      key: "count", label: "Attempts",
      render: (v) => <Badge variant={v > 10 ? "danger" : "warning"} size="sm">{v}</Badge>,
    },
    { key: "latest", label: "Latest", render: (v) => <span className="text-xs text-slate-500">{fmt(v)}</span> },
    {
      key: "_actions", label: "", align: "right",
      render: (_, item) =>
        blockingIp === item.ip ? (
          <div className="flex items-center justify-end gap-2">
            <Input
              value={blockReason}
              onChange={(e) => setBlockReason(e.target.value)}
              placeholder="Reason…"
              size="sm"
              wrapperClassName="!mb-0 w-32"
            />
            <Button variant="danger" size="sm" onClick={() => blockIp(item.ip)} disabled={actionLoading}>Block</Button>
            <Button variant="ghost" size="sm" onClick={() => { setBlockingIp(null); setBlockReason(""); }}>Cancel</Button>
          </div>
        ) : (
          <Button variant="link" size="sm" onClick={() => setBlockingIp(item.ip)} className="!text-red-700">Block IP</Button>
        ),
    },
  ];

  const blockedIpColumns = [
    { key: "ip", label: "IP Address", render: (v) => <span className="font-mono text-xs">{v}</span> },
    { key: "reason", label: "Reason", render: (v) => <span className="text-xs text-slate-600">{v || "—"}</span> },
    { key: "blocked_at", label: "Blocked At", render: (v) => <span className="text-xs text-slate-500">{fmt(v)}</span> },
    { key: "blocked_by", label: "By", render: (v) => <span className="text-xs text-slate-500">{v || "—"}</span> },
    {
      key: "_actions", label: "", align: "right",
      render: (_, item) => (
        <Button variant="link" size="sm" onClick={() => unblockIp(item.ip)} disabled={actionLoading} className="!text-emerald-700">
          Unblock
        </Button>
      ),
    },
  ];

  return (
    <AdministrationLayout
      title="Security Center"
      subtitle="Monitor threats and manage platform access"
    >
      {/* Failed Logins */}
      <Section title="Failed Login Attempts">
        <div className="flex gap-3 mb-4 items-center">
          <span className="text-sm text-slate-600">Time window:</span>
          {[1, 6, 24, 72].map((h) => (
            <Button key={h} variant={hours === h ? "primary" : "ghost"} size="sm" onClick={() => setHours(h)}>
              {h}h
            </Button>
          ))}
        </div>
        {loading ? (
          <SkeletonTable rows={4} cols={4} />
        ) : (
          <DataTable
            columns={failedLoginColumns}
            rows={failedLogins}
            emptyNode={<p className="text-sm text-slate-400 text-center py-6">No failed login attempts in this window</p>}
          />
        )}
      </Section>

      {/* Blocked IPs */}
      <Section title="Blocked IP Addresses">
        <DataTable
          columns={blockedIpColumns}
          rows={blockedIps}
          emptyNode={<p className="text-sm text-slate-400 text-center py-6">No blocked IPs</p>}
        />
      </Section>

      {/* Emergency Controls */}
      <Card accent={CRIMSON} className="bg-red-50" padding="lg">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle size={16} className="text-red-700" />
          <h2 className="text-sm font-semibold text-red-800">Emergency Controls</h2>
        </div>
        <p className="text-sm text-red-700 mb-4">These actions affect all users on the platform and cannot be undone.</p>
        {showForceConfirm ? (
          <div className="space-y-3">
            <p className="text-sm font-medium text-red-800">Are you sure you want to force sign out ALL users?</p>
            <Textarea
              value={forceLogoutReason}
              onChange={(e) => setForceLogoutReason(e.target.value)}
              placeholder="Reason for emergency logout (required)…"
              rows={2}
            />
            <div className="flex gap-2">
              <Button variant="danger" onClick={forceLogoutAll} disabled={actionLoading || !forceLogoutReason.trim()} loading={actionLoading}>
                {actionLoading ? "Working…" : "Confirm — Sign out all users"}
              </Button>
              <Button variant="ghost" onClick={() => { setShowForceConfirm(false); setForceLogoutReason(""); }}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <Button variant="danger" onClick={() => setShowForceConfirm(true)}>
            <Lock size={14} />
            Force Sign Out ALL Users
          </Button>
        )}
      </Card>
    </AdministrationLayout>
  );
}

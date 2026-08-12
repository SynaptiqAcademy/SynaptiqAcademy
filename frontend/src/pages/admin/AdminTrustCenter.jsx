import React, { useEffect, useState } from "react";
import { ShieldCheck, CheckCircle2, XCircle, Clock } from "lucide-react";
import { NAVY, WARM, BRD, EMERALD, ACCENT, TEXT_SECONDARY, WHITE } from "../../lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, StatCard, StatGrid, StatusDot } from "@/components/ds";

const API = "/api/trust";

export default function AdminTrustCenter() {
  const [stats, setStats] = useState(null);
  const [pending, setPending] = useState([]);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingPending, setLoadingPending] = useState(true);
  const [auditLog, setAuditLog] = useState([]);
  const [reviewLoading, setReviewLoading] = useState({});

  useEffect(() => {
    fetch(API + "/admin/stats", { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(d => { setStats(d); setLoadingStats(false); })
      .catch(() => setLoadingStats(false));

    fetch(API + "/requests/pending?limit=20", { credentials: "include" })
      .then(r => r.ok ? r.json() : [])
      .then(d => { setPending(d || []); setLoadingPending(false); })
      .catch(() => setLoadingPending(false));

    fetch(API + "/audit/admin?limit=20", { credentials: "include" })
      .then(r => r.ok ? r.json() : [])
      .then(d => setAuditLog(d || []))
      .catch(() => {});
  }, []);

  const review = async (reqId, action) => {
    setReviewLoading(p => ({ ...p, [reqId]: action }));
    const r = await fetch(API + `/requests/${reqId}/review`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    if (r.ok) {
      setPending(prev => prev.filter(p => p._id !== reqId));
    }
    setReviewLoading(p => ({ ...p, [reqId]: null }));
  };

  return (
    <AdministrationLayout
      title="Admin Trust Center"
      subtitle="Review verification requests, manage badges and monitor platform trust"
      icon={<ShieldCheck size={24} />}
    >
        {/* Stats grid */}
        {loadingStats ? (
          <div style={{ color: TEXT_SECONDARY, marginBottom: 20 }}>Loading stats…</div>
        ) : (
          <StatGrid cols={4} className="mb-6">
            <StatCard label="Total Users" value={stats?.total_users} />
            <StatCard label="Verifications" value={stats?.verifications_total}
              sub={`${stats?.verifications_verified} verified (${stats?.verification_rate}%)`} />
            <StatCard label="Pending Reviews" value={stats?.requests_pending} />
            <StatCard label="Badges Awarded" value={stats?.badges_awarded} />
            <StatCard label="Passports" value={stats?.passports_generated} />
            <StatCard label="Audit Events" value={stats?.audit_events} />
            <StatCard label="Total Requests" value={stats?.requests_total} />
            <StatCard label="Verification Rate" value={`${stats?.verification_rate || 0}%`} />
          </StatGrid>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Pending requests */}
          <Card padding="lg">
            <div style={{ fontSize: 14, fontWeight: 600, color: NAVY, marginBottom: 16,
              display: "flex", alignItems: "center", gap: 6 }}>
              <Clock size={15} color="#D97706" /> Pending Reviews ({pending.length})
            </div>
            {loadingPending ? (
              <div style={{ color: TEXT_SECONDARY, fontSize: 13 }}>Loading…</div>
            ) : pending.length === 0 ? (
              <div style={{ color: TEXT_SECONDARY, fontSize: 13, textAlign: "center", padding: 20 }}>
                No pending requests.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {pending.map(req => (
                  <Card key={req._id} padding="sm">
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: NAVY }}>{req.label}</span>
                      <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>
                        AI: {req.ai_confidence}%
                      </span>
                    </div>
                    {req.user_notes && (
                      <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: "0 0 8px" }}>
                        "{req.user_notes}"
                      </p>
                    )}
                    <div style={{ display: "flex", gap: 8 }}>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => review(req._id, "approve")}
                        disabled={!!reviewLoading[req._id]}
                        className="flex-1 !bg-emerald-50 !text-emerald-700 !border-emerald-200"
                      >
                        <CheckCircle2 size={11} />
                        {reviewLoading[req._id] === "approve" ? "…" : "Approve"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => review(req._id, "reject")}
                        disabled={!!reviewLoading[req._id]}
                        className="flex-1 !bg-red-50 !text-red-700 !border-red-200"
                      >
                        <XCircle size={11} />
                        {reviewLoading[req._id] === "reject" ? "…" : "Reject"}
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </Card>

          {/* Audit log */}
          <Card padding="lg">
            <div style={{ fontSize: 14, fontWeight: 600, color: NAVY, marginBottom: 16 }}>
              Recent Audit Events
            </div>
            {auditLog.length === 0 ? (
              <div style={{ color: TEXT_SECONDARY, fontSize: 13, textAlign: "center", padding: 20 }}>
                No events.
              </div>
            ) : (
              auditLog.map((e, i) => (
                <div key={e._id || i} style={{
                  display: "flex", alignItems: "flex-start", gap: 10,
                  padding: "8px 0",
                  borderBottom: i < auditLog.length - 1 ? `1px solid ${BRD}` : "none",
                }}>
                  <div style={{ marginTop: 5 }}>
                    <StatusDot color={NAVY} size={7} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: NAVY }}>
                      {e.event?.replace(/_/g, " ")}
                    </div>
                    <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>
                      User: {e.user_id?.slice(-8)}
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: TEXT_SECONDARY, whiteSpace: "nowrap" }}>
                    {e.created_at ? new Date(e.created_at).toLocaleDateString() : ""}
                  </div>
                </div>
              ))
            )}
          </Card>
        </div>
    </AdministrationLayout>
  );
}

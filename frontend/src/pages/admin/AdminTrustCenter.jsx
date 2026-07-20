import React, { useEffect, useState } from "react";
import { ShieldCheck, CheckCircle2, XCircle, Clock } from "lucide-react";
import { NAVY, WARM, BRD, EMERALD, ACCENT, TEXT_SECONDARY, WHITE } from "../../lib/tokens";
import { AdministrationLayout } from "@/layouts";

const API = "/api/trust";

function StatCard({ label, value, color = NAVY, sub }) {
  return (
    <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 10, padding: "18px 20px" }}>
      <div style={{ fontSize: 28, fontWeight: 800, color }}>{value ?? "—"}</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginTop: 2 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

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
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 24 }}>
            <StatCard label="Total Users" value={stats?.total_users} />
            <StatCard label="Verifications" value={stats?.verifications_total}
              sub={`${stats?.verifications_verified} verified (${stats?.verification_rate}%)`} />
            <StatCard label="Pending Reviews" value={stats?.requests_pending} color="#D97706" />
            <StatCard label="Badges Awarded" value={stats?.badges_awarded} color="#7C3AED" />
            <StatCard label="Passports" value={stats?.passports_generated} color={EMERALD} />
            <StatCard label="Audit Events" value={stats?.audit_events} />
            <StatCard label="Total Requests" value={stats?.requests_total} />
            <StatCard label="Verification Rate" value={`${stats?.verification_rate || 0}%`} color={EMERALD} />
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Pending requests */}
          <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12, padding: 20 }}>
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
                  <div key={req._id} style={{ border: `1px solid ${BRD}`, borderRadius: 8, padding: 14 }}>
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
                      <button
                        onClick={() => review(req._id, "approve")}
                        disabled={!!reviewLoading[req._id]}
                        style={{
                          flex: 1, padding: "5px 10px", borderRadius: 6, fontSize: 11, fontWeight: 600,
                          background: EMERALD + "14", color: EMERALD,
                          border: `1px solid ${EMERALD}28`, cursor: "pointer",
                          opacity: reviewLoading[req._id] ? 0.5 : 1,
                          display: "flex", alignItems: "center", justifyContent: "center", gap: 4,
                        }}>
                        <CheckCircle2 size={11} />
                        {reviewLoading[req._id] === "approve" ? "…" : "Approve"}
                      </button>
                      <button
                        onClick={() => review(req._id, "reject")}
                        disabled={!!reviewLoading[req._id]}
                        style={{
                          flex: 1, padding: "5px 10px", borderRadius: 6, fontSize: 11, fontWeight: 600,
                          background: ACCENT + "14", color: ACCENT,
                          border: `1px solid ${ACCENT}28`, cursor: "pointer",
                          opacity: reviewLoading[req._id] ? 0.5 : 1,
                          display: "flex", alignItems: "center", justifyContent: "center", gap: 4,
                        }}>
                        <XCircle size={11} />
                        {reviewLoading[req._id] === "reject" ? "…" : "Reject"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Audit log */}
          <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12, padding: 20 }}>
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
                  <div style={{ width: 7, height: 7, borderRadius: 3.5, background: NAVY,
                    flexShrink: 0, marginTop: 5 }} />
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
          </div>
        </div>
    </AdministrationLayout>
  );
}

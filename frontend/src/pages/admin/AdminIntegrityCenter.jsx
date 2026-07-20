import React, { useState, useEffect, useCallback } from "react";
import {
  Shield, AlertTriangle, CheckCircle, XCircle, RefreshCw,
  Users, BarChart2, Activity, Search, ChevronDown, Loader2,
} from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, EMERALD, WHITE, TEXT_SECONDARY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

const API = process.env.REACT_APP_API_URL || "";
const token = () => localStorage.getItem("token");
const authH = () => ({ Authorization: `Bearer ${token()}` });

const GRADE_COLOR = {
  "A+": EMERALD, A: EMERALD, B: "#0ea5e9", C: "#f59e0b", D: "#f97316", F: ACCENT,
};

const STATUS_COLOR = {
  complete: EMERALD, running: "#0ea5e9", pending: "#f59e0b", error: ACCENT, not_started: "#94a3b8",
};

function StatCard({ label, value, color, icon: Icon }) {
  return (
    <div style={{
      background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12,
      padding: "16px 20px", display: "flex", alignItems: "center", gap: 14,
    }}>
      <div style={{
        width: 44, height: 44, borderRadius: 10,
        background: `${color || NAVY}15`,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {Icon && <Icon size={20} color={color || NAVY} />}
      </div>
      <div>
        <div style={{ fontSize: 22, fontWeight: 800, color: NAVY }}>{value ?? "—"}</div>
        <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{label}</div>
      </div>
    </div>
  );
}

function ProviderBadge({ provider }) {
  const ok = provider.available;
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 6,
      background: ok ? "#f0fdf4" : "#fef2f2",
      border: `1px solid ${ok ? "#bbf7d0" : "#fecaca"}`,
      borderRadius: 8, padding: "6px 12px",
    }}>
      {ok
        ? <CheckCircle size={13} color={EMERALD} />
        : <XCircle size={13} color={ACCENT} />}
      <span style={{ fontSize: 12, fontWeight: 600, color: ok ? "#166534" : "#991b1b" }}>
        {provider.label}
      </span>
    </div>
  );
}

export default function AdminIntegrityCenter() {
  const [stats, setStats]       = useState(null);
  const [reports, setReports]   = useState([]);
  const [total, setTotal]       = useState(0);
  const [loading, setLoading]   = useState(true);
  const [page, setPage]         = useState(0);
  const [grade, setGrade]       = useState("");
  const [critical, setCritical] = useState("");

  const LIMIT = 20;

  const loadStats = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/admin/integrity/stats`, { headers: authH() });
      if (r.ok) setStats(await r.json());
    } catch (_) {}
  }, []);

  const loadReports = useCallback(async (pg = 0) => {
    try {
      const params = new URLSearchParams({ skip: pg * LIMIT, limit: LIMIT });
      if (grade) params.append("grade", grade);
      if (critical !== "") params.append("has_critical", critical);
      const r = await fetch(`${API}/api/admin/integrity/reports?${params}`, { headers: authH() });
      if (r.ok) {
        const d = await r.json();
        setReports(d.reports || []);
        setTotal(d.total || 0);
      }
    } catch (_) {}
  }, [grade, critical]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      await Promise.all([loadStats(), loadReports(0)]);
      setLoading(false);
    })();
  }, [loadStats, loadReports]);

  const handleTriggerUser = async (uid) => {
    await fetch(`${API}/api/admin/integrity/analyze/${uid}`, {
      method: "POST", headers: authH(),
    });
    loadStats();
  };

  if (loading) {
    return (
      <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Loader2 size={32} color={ACCENT} style={{ animation: "spin 1s linear infinite" }} />
      </div>
    );
  }

  return (
    <AdministrationLayout
      title="Integrity Admin Center"
      subtitle="Platform-wide integrity scores, risk flags, provider health, and job queue"
      icon={<Shield size={22} />}
    >

      {/* Stats grid */}
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 24 }}>
          <StatCard label="Total Reports" value={stats.total_reports} icon={BarChart2} color={NAVY} />
          <StatCard label="Pending Jobs" value={stats.pending_jobs} icon={Activity} color="#f59e0b" />
          <StatCard label="Complete" value={stats.complete_jobs} icon={CheckCircle} color={EMERALD} />
          <StatCard label="Errors" value={stats.error_jobs} icon={XCircle} color={ACCENT} />
          <StatCard label="Critical Risks" value={stats.critical_reports} icon={AlertTriangle} color="#dc2626" />
          <StatCard label="High Risks" value={stats.high_risk_reports} icon={AlertTriangle} color="#f97316" />
        </div>
      )}

      {/* Score stats */}
      {stats?.score_stats && (
        <div style={{
          background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12,
          padding: "16px 20px", marginBottom: 20,
          display: "flex", gap: 32, alignItems: "center",
        }}>
          <span style={{ fontWeight: 700, fontSize: 14, color: NAVY }}>Score Distribution</span>
          {[
            { label: "Avg", val: stats.score_stats.avg_score?.toFixed(1) ?? "—" },
            { label: "Min", val: stats.score_stats.min_score?.toFixed(1) ?? "—" },
            { label: "Max", val: stats.score_stats.max_score?.toFixed(1) ?? "—" },
          ].map(({ label, val }) => (
            <div key={label} style={{ textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 800, color: NAVY }}>{val}</div>
              <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Providers */}
      {stats?.providers && (
        <div style={{
          background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12,
          padding: "16px 20px", marginBottom: 20,
        }}>
          <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 700, color: NAVY }}>
            External Provider Health
          </h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {stats.providers.map(p => <ProviderBadge key={p.name} provider={p} />)}
          </div>
        </div>
      )}

      {/* Reports table */}
      <div style={{
        background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12, overflow: "hidden",
      }}>
        {/* Filters */}
        <div style={{
          padding: "14px 20px", borderBottom: `1px solid ${BRD}`,
          display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap",
        }}>
          <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: NAVY, flex: 1 }}>
            User Reports ({total})
          </h3>
          <select
            value={grade}
            onChange={e => { setGrade(e.target.value); setPage(0); loadReports(0); }}
            style={{
              padding: "6px 10px", border: `1px solid ${BRD}`, borderRadius: 6,
              fontSize: 13, color: NAVY, background: WHITE,
            }}
          >
            <option value="">All Grades</option>
            {["A+", "A", "B", "C", "D", "F"].map(g => <option key={g} value={g}>Grade {g}</option>)}
          </select>
          <select
            value={critical}
            onChange={e => { setCritical(e.target.value); setPage(0); loadReports(0); }}
            style={{
              padding: "6px 10px", border: `1px solid ${BRD}`, borderRadius: 6,
              fontSize: 13, color: NAVY, background: WHITE,
            }}
          >
            <option value="">All Risk Levels</option>
            <option value="true">Has Critical Risks</option>
            <option value="false">No Critical Risks</option>
          </select>
        </div>

        {/* Table */}
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: WARM }}>
                {["User ID", "Score", "Grade", "Risks", "Critical", "High", "Generated"].map(h => (
                  <th key={h} style={{
                    padding: "10px 16px", textAlign: "left",
                    fontWeight: 600, color: TEXT_SECONDARY, fontSize: 12,
                    borderBottom: `1px solid ${BRD}`,
                  }}>{h}</th>
                ))}
                <th style={{ padding: "10px 16px", borderBottom: `1px solid ${BRD}` }} />
              </tr>
            </thead>
            <tbody>
              {reports.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ textAlign: "center", padding: 32, color: TEXT_SECONDARY }}>
                    No reports found
                  </td>
                </tr>
              )}
              {reports.map((r, i) => (
                <tr key={r.user_id || i}
                  style={{ borderBottom: `1px solid ${BRD}`, background: i % 2 === 0 ? WHITE : `${WARM}60` }}>
                  <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 11, color: TEXT_SECONDARY }}>
                    {r.user_id?.slice(-8) ?? "—"}
                  </td>
                  <td style={{ padding: "10px 16px", fontWeight: 700, color: NAVY }}>
                    {r.integrity_score ?? "—"}
                  </td>
                  <td style={{ padding: "10px 16px" }}>
                    <span style={{
                      fontWeight: 700, color: GRADE_COLOR[r.grade] || TEXT_SECONDARY,
                      background: `${GRADE_COLOR[r.grade] || "#94a3b8"}15`,
                      padding: "2px 8px", borderRadius: 6, fontSize: 12,
                    }}>{r.grade ?? "—"}</span>
                  </td>
                  <td style={{ padding: "10px 16px", color: TEXT_SECONDARY }}>{r.risk_count ?? 0}</td>
                  <td style={{ padding: "10px 16px" }}>
                    {r.critical_risks > 0
                      ? <span style={{ color: "#dc2626", fontWeight: 700 }}>{r.critical_risks}</span>
                      : <span style={{ color: TEXT_SECONDARY }}>0</span>}
                  </td>
                  <td style={{ padding: "10px 16px" }}>
                    {r.high_risks > 0
                      ? <span style={{ color: "#f97316", fontWeight: 700 }}>{r.high_risks}</span>
                      : <span style={{ color: TEXT_SECONDARY }}>0</span>}
                  </td>
                  <td style={{ padding: "10px 16px", color: TEXT_SECONDARY, fontSize: 11 }}>
                    {r.generated_at ? new Date(r.generated_at).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ padding: "10px 16px" }}>
                    <button
                      onClick={() => handleTriggerUser(r.user_id)}
                      style={{
                        background: WARM, border: `1px solid ${BRD}`, borderRadius: 6,
                        padding: "4px 10px", fontSize: 11, cursor: "pointer", color: NAVY,
                        fontWeight: 600,
                      }}
                    >
                      Re-Run
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > LIMIT && (
          <div style={{
            padding: "12px 20px", borderTop: `1px solid ${BRD}`,
            display: "flex", justifyContent: "space-between", alignItems: "center",
          }}>
            <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>
              Page {page + 1} of {Math.ceil(total / LIMIT)} ({total} total)
            </span>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                disabled={page === 0}
                onClick={() => { const p = page - 1; setPage(p); loadReports(p); }}
                style={{
                  padding: "6px 12px", border: `1px solid ${BRD}`, borderRadius: 6,
                  background: WHITE, fontSize: 12, cursor: page === 0 ? "not-allowed" : "pointer",
                  opacity: page === 0 ? 0.4 : 1,
                }}
              >Prev</button>
              <button
                disabled={(page + 1) * LIMIT >= total}
                onClick={() => { const p = page + 1; setPage(p); loadReports(p); }}
                style={{
                  padding: "6px 12px", border: `1px solid ${BRD}`, borderRadius: 6,
                  background: WHITE, fontSize: 12,
                  cursor: (page + 1) * LIMIT >= total ? "not-allowed" : "pointer",
                  opacity: (page + 1) * LIMIT >= total ? 0.4 : 1,
                }}
              >Next</button>
            </div>
          </div>
        )}
      </div>
    </AdministrationLayout>
  );
}

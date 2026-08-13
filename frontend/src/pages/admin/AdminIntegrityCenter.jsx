import React, { useState, useEffect, useCallback } from "react";
import {
  Shield, AlertTriangle, CheckCircle, XCircle, RefreshCw,
  Users, BarChart2, Activity, Search, ChevronDown,
} from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, EMERALD, WHITE, TEXT_SECONDARY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { StatCard, StatGrid, Card, Badge, FormSelect, Button, DataTable, Pagination, Spinner, H3 } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = process.env.REACT_APP_API_URL || "";
const token = () => localStorage.getItem("token");
const authH = () => ({ Authorization: `Bearer ${token()}` });

const GRADE_COLOR = {
  "A+": EMERALD, A: EMERALD, B: "#0ea5e9", C: "#f59e0b", D: "#f97316", F: ACCENT,
};

const STATUS_COLOR = {
  complete: EMERALD, running: "#0ea5e9", pending: "#f59e0b", error: ACCENT, not_started: "#94a3b8",
};

function ProviderBadge({ provider }) {
  const ok = provider.available;
  return (
    <Badge color={ok ? EMERALD : ACCENT}>
      {ok ? <CheckCircle size={13} /> : <XCircle size={13} />}
      {provider.label}
    </Badge>
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
      const r = await fetchApi(`${API}/api/admin/integrity/stats`, { headers: authH() });
      if (r.ok) setStats(await r.json());
    } catch (_) {}
  }, []);

  const loadReports = useCallback(async (pg = 0) => {
    try {
      const params = new URLSearchParams({ skip: pg * LIMIT, limit: LIMIT });
      if (grade) params.append("grade", grade);
      if (critical !== "") params.append("has_critical", critical);
      const r = await fetchApi(`${API}/api/admin/integrity/reports?${params}`, { headers: authH() });
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
    await fetchApi(`${API}/api/admin/integrity/analyze/${uid}`, {
      method: "POST", headers: authH(),
    });
    loadStats();
  };

  if (loading) {
    return (
      <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Spinner size={32} color={ACCENT} />
      </div>
    );
  }

  const reportColumns = [
    {
      key: "user_id", label: "User ID",
      render: (v) => <span style={{ fontFamily: "monospace", fontSize: 11, color: TEXT_SECONDARY }}>{v?.slice(-8) ?? "—"}</span>,
    },
    {
      key: "integrity_score", label: "Score",
      render: (v) => <span style={{ fontWeight: 700, color: NAVY }}>{v ?? "—"}</span>,
    },
    {
      key: "grade", label: "Grade",
      render: (v) => <Badge color={GRADE_COLOR[v] || "#94a3b8"}>{v ?? "—"}</Badge>,
    },
    {
      key: "risk_count", label: "Risks",
      render: (v) => <span style={{ color: TEXT_SECONDARY }}>{v ?? 0}</span>,
    },
    {
      key: "critical_risks", label: "Critical",
      render: (v) => v > 0
        ? <span style={{ color: "#dc2626", fontWeight: 700 }}>{v}</span>
        : <span style={{ color: TEXT_SECONDARY }}>0</span>,
    },
    {
      key: "high_risks", label: "High",
      render: (v) => v > 0
        ? <span style={{ color: "#f97316", fontWeight: 700 }}>{v}</span>
        : <span style={{ color: TEXT_SECONDARY }}>0</span>,
    },
    {
      key: "generated_at", label: "Generated",
      render: (v) => <span style={{ color: TEXT_SECONDARY, fontSize: 11 }}>{v ? new Date(v).toLocaleDateString() : "—"}</span>,
    },
    {
      key: "_actions", label: "",
      render: (_, row) => (
        <Button size="sm" variant="ghost" onClick={() => handleTriggerUser(row.user_id)}>
          Re-Run
        </Button>
      ),
    },
  ];

  return (
    <AdministrationLayout
      title="Integrity Admin Center"
      subtitle="Platform-wide integrity scores, risk flags, provider health, and job queue"
      icon={<Shield size={22} />}
    >

      {/* Stats grid */}
      {stats && (
        <StatGrid cols={6} className="mb-6">
          <StatCard label="Total Reports" value={stats.total_reports} icon={<BarChart2 style={{ color: NAVY }} />} />
          <StatCard label="Pending Jobs" value={stats.pending_jobs} icon={<Activity style={{ color: "#f59e0b" }} />} />
          <StatCard label="Complete" value={stats.complete_jobs} icon={<CheckCircle style={{ color: EMERALD }} />} />
          <StatCard label="Errors" value={stats.error_jobs} icon={<XCircle style={{ color: ACCENT }} />} />
          <StatCard label="Critical Risks" value={stats.critical_reports} icon={<AlertTriangle style={{ color: "#dc2626" }} />} />
          <StatCard label="High Risks" value={stats.high_risk_reports} icon={<AlertTriangle style={{ color: "#f97316" }} />} />
        </StatGrid>
      )}

      {/* Score stats */}
      {stats?.score_stats && (
        <Card padding="lg" className="mb-5" style={{ display: "flex", gap: 32, alignItems: "center" }}>
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
        </Card>
      )}

      {/* Providers */}
      {stats?.providers && (
        <Card padding="lg" className="mb-5">
          <H3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 700, color: NAVY }}>
            External Provider Health
          </H3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {stats.providers.map(p => <ProviderBadge key={p.name} provider={p} />)}
          </div>
        </Card>
      )}

      {/* Reports table */}
      {/* Filters */}
      <div style={{
        padding: "14px 20px", border: `1px solid ${BRD}`, borderBottom: "none",
        borderRadius: "12px 12px 0 0", background: WHITE,
        display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap",
      }}>
        <H3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: NAVY, flex: 1 }}>
          User Reports ({total})
        </H3>
        <FormSelect
          value={grade}
          onChange={e => { setGrade(e.target.value); setPage(0); loadReports(0); }}
          wrapperClassName="!mb-0"
          style={{ width: 160 }}
        >
          <option value="">All Grades</option>
          {["A+", "A", "B", "C", "D", "F"].map(g => <option key={g} value={g}>Grade {g}</option>)}
        </FormSelect>
        <FormSelect
          value={critical}
          onChange={e => { setCritical(e.target.value); setPage(0); loadReports(0); }}
          wrapperClassName="!mb-0"
          style={{ width: 180 }}
        >
          <option value="">All Risk Levels</option>
          <option value="true">Has Critical Risks</option>
          <option value="false">No Critical Risks</option>
        </FormSelect>
      </div>

      {/* Table */}
      <DataTable
        columns={reportColumns}
        rows={reports}
        emptyNode={<div style={{ textAlign: "center", padding: 32, color: TEXT_SECONDARY }}>No reports found</div>}
        className="!rounded-t-none"
      />

      {/* Pagination */}
      {total > LIMIT && (
        <div style={{
          padding: "12px 20px", display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>
            Page {page + 1} of {Math.ceil(total / LIMIT)} ({total} total)
          </span>
          <Pagination
            page={page + 1}
            totalPages={Math.ceil(total / LIMIT)}
            onPage={(p) => { const newPage = p - 1; setPage(newPage); loadReports(newPage); }}
          />
        </div>
      )}
    </AdministrationLayout>
  );
}

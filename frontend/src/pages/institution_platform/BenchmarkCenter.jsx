import React, { useState, useEffect, useCallback } from "react";
import { TrendingUp, TrendingDown, Award, Building2 } from "lucide-react";
import { NAVY, WARM, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { NavTabs, DataTable, Badge, Card, Spinner } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

function TrendCell({ v }) {
  const color = v >= 0 ? EMERALD : ACCENT;
  return (
    <span style={{ fontSize: 12, fontWeight: 700, color }}>
      {v >= 0 ? "+" : ""}{v.toFixed(1)}
      {v >= 0 ? <TrendingUp size={11} style={{ marginLeft: 3 }} /> : <TrendingDown size={11} style={{ marginLeft: 3 }} />}
    </span>
  );
}

const SECTOR_COLUMNS = [
  {
    key: "metric", label: "Metric",
    render: (_, b) => <span style={{ fontWeight: 600, color: NAVY, fontSize: 13 }}>{b.metric.replace(/_/g, " ").replace(/pct/, "%")}</span>,
  },
  {
    key: "current", label: "Your Value",
    render: (v) => <span style={{ fontWeight: 800, color: NAVY, fontSize: 14 }}>{v.toFixed(1)}</span>,
  },
  {
    key: "national_average", label: "National Avg",
    render: (v) => <span style={{ color: TEXT_SECONDARY }}>{v.toFixed(1)}</span>,
  },
  { key: "vs_national", label: "vs National", render: (v) => <TrendCell v={v} /> },
  {
    key: "sector_average", label: "Sector Avg",
    render: (v) => <span style={{ color: TEXT_SECONDARY }}>{v.toFixed(1)}</span>,
  },
  { key: "vs_sector", label: "vs Sector", render: (v) => <TrendCell v={v} /> },
  {
    key: "sector_status", label: "Status",
    render: (v) => <Badge variant={v === "above" ? "success" : "warning"}>{v}</Badge>,
  },
];

export default function BenchmarkCenter() {
  const [bench, setBench] = useState(null);
  const [deptBench, setDeptBench] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("sector");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [br, dr] = await Promise.all([
        fetchApi(`${API}/api/iip/benchmarks/overview`, { headers: authH() }),
        fetchApi(`${API}/api/iip/benchmarks/departments`, { headers: authH() }),
      ]);
      if (br.ok) setBench(await br.json());
      if (dr.ok) setDeptBench(await dr.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={32} color={ACCENT} />
    </div>
  );

  const aboveSector = (bench?.benchmarks || []).filter(b => b.sector_status === "above").length;
  const total = (bench?.benchmarks || []).length;

  const deptColumns = [
    {
      key: "institution_rank", label: "Rank",
      render: (v, row) => {
        const i = deptBench.indexOf(row);
        const color = i === 0 ? EMERALD : i === deptBench.length - 1 ? ACCENT : NAVY;
        return <span style={{ fontWeight: 800, color }}>#{v}</span>;
      },
    },
    { key: "department", label: "Department", render: (v) => <span style={{ fontWeight: 600, color: NAVY }}>{v}</span> },
    {
      key: "health_score", label: "Health Score",
      render: (v) => <span style={{ fontWeight: 700, color: v >= 70 ? EMERALD : v >= 50 ? "#f59e0b" : ACCENT }}>{v}</span>,
    },
    {
      key: "vs_institution_health", label: "vs Institution",
      render: (v) => <span style={{ fontSize: 12, fontWeight: 700, color: v >= 0 ? EMERALD : ACCENT }}>{v >= 0 ? "+" : ""}{v}</span>,
    },
    { key: "pubs_per_faculty", label: "Pubs/Faculty", render: (v) => <span style={{ color: TEXT_SECONDARY }}>{v}</span> },
    { key: "grant_success_rate", label: "Grant Rate %", render: (v) => <span style={{ color: TEXT_SECONDARY }}>{v}%</span> },
    { key: "collaborations", label: "Collabs", render: (v) => <span style={{ color: TEXT_SECONDARY }}>{v}</span> },
  ];

  return (
    <InstitutionLayout
      title="Benchmark Center"
      subtitle={`${bench?.institution ?? ""} · Above sector average in ${aboveSector}/${total} metrics · Health Score: ${bench?.overall_health ?? "—"}/100 (Grade ${bench?.overall_grade ?? "—"})`}
      sidebar={<BenchmarkCenterSidebar bench={bench} deptBench={deptBench} aboveSector={aboveSector} total={total} />}
    >
      <div style={{ marginBottom: 16 }}>
        <NavTabs
          variant="pill"
          active={tab}
          onChange={setTab}
          tabs={[
            { id: "sector", label: "Sector Benchmarks" },
            { id: "departments", label: "Department Benchmarks" },
          ]}
        />
      </div>

      {tab === "sector" && (
        <>
          <DataTable columns={SECTOR_COLUMNS} rows={bench?.benchmarks || []} />
          {bench?.note && (
            <div style={{ padding: "10px 16px", background: WARM, borderRadius: 8, fontSize: 11, color: TEXT_SECONDARY, marginTop: 8 }}>
              {bench.note}
            </div>
          )}
        </>
      )}

      {tab === "departments" && (
        <DataTable columns={deptColumns} rows={deptBench} />
      )}
    </InstitutionLayout>
  );
}

// ── Right rail — real benchmark data already fetched by this page ─────────────
function BenchmarkCenterSidebar({ bench, deptBench, aboveSector, total }) {
  const topDept = deptBench && deptBench.length > 0 ? deptBench[0] : null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Award size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Overall Grade</div>
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 28, fontWeight: 700, color: "#0f172a" }}>
          {bench?.overall_grade ?? "—"}
        </div>
        <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0", lineHeight: 1.5 }}>
          Health score {bench?.overall_health ?? "—"}/100 · above sector average in {aboveSector}/{total} metrics.
        </p>
      </Card>

      {topDept && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Building2 size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Top Department</div>
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", fontFamily: "Georgia, serif" }}>{topDept.department}</div>
          <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0", lineHeight: 1.5 }}>
            Health score {topDept.health_score} · rank #{topDept.institution_rank}
          </p>
        </Card>
      )}
    </div>
  );
}

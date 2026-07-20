import React, { useState, useEffect, useCallback } from "react";
import { TrendingUp, TrendingDown } from "lucide-react";
import { NAVY, WARM, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { NavTabs, DataTable, Badge, Spinner } from "@/components/ds";

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
        fetch(`${API}/api/iip/benchmarks/overview`, { headers: authH() }),
        fetch(`${API}/api/iip/benchmarks/departments`, { headers: authH() }),
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

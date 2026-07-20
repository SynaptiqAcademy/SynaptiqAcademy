import React, { useState, useEffect, useCallback } from "react";
import { AlertTriangle, Star, TrendingUp, ChevronDown, ChevronUp } from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { Card, NavTabs, DataTable, StatCard, StatGrid, ProgressBar, List, ListItem, Badge, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

// ScoreBar's 70/40 qualitative thresholds don't match ProgressBar's colorByValue
// 80/100 overrun-style thresholds — left hand-rolled.
function ScoreBar({ value, max = 100 }) {
  const pct = Math.min(100, (value / max) * 100);
  const color = pct >= 70 ? EMERALD : pct >= 40 ? "#f59e0b" : ACCENT;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ flex: 1, height: 5, background: `${NAVY}15`, borderRadius: 99 }}>
        <div style={{ height: "100%", borderRadius: 99, background: color, width: `${pct}%` }} />
      </div>
      <span style={{ fontSize: 11, color: NAVY, fontWeight: 700, minWidth: 28 }}>{Math.round(value)}</span>
    </div>
  );
}

const FACULTY_COLUMNS = [
  { key: "name", label: "Name", render: (v) => <span style={{ fontWeight: 600, color: NAVY }}>{v || "—"}</span> },
  { key: "department", label: "Department", render: (v) => <span style={{ color: TEXT_SECONDARY }}>{v || "—"}</span> },
  { key: "position", label: "Position", render: (v) => <span style={{ color: TEXT_SECONDARY, fontSize: 12 }}>{v || "—"}</span> },
  { key: "publications_recent", label: "Pubs (recent)", render: (v) => <span style={{ fontWeight: 700, color: NAVY }}>{v ?? 0}</span> },
  { key: "grants", label: "Grants", render: (v) => <span style={{ color: TEXT_SECONDARY }}>{v ?? 0}</span> },
  { key: "courses", label: "Courses", render: (v) => <span style={{ color: TEXT_SECONDARY }}>{v ?? 0}</span> },
  { key: "productivity_score", label: "Score", render: (v) => <ScoreBar value={v ?? 0} /> },
];

function FacultyTable({ data, title }) {
  const [expanded, setExpanded] = useState(true);
  return (
    <Card padding="none" className="mb-4 overflow-hidden">
      <button onClick={() => setExpanded(v => !v)} style={{
        width: "100%", padding: "14px 20px", display: "flex", justifyContent: "space-between",
        alignItems: "center", background: WARM, border: "none", cursor: "pointer",
      }}>
        <span style={{ fontWeight: 700, fontSize: 14, color: NAVY }}>{title} ({data.length})</span>
        {expanded ? <ChevronUp size={16} color={TEXT_SECONDARY} /> : <ChevronDown size={16} color={TEXT_SECONDARY} />}
      </button>
      {expanded && (
        <DataTable columns={FACULTY_COLUMNS} rows={data.slice(0, 20)} />
      )}
    </Card>
  );
}

export default function FacultyIntelligence() {
  const [overview, setOverview] = useState(null);
  const [top, setTop] = useState([]);
  const [atRisk, setAtRisk] = useState([]);
  const [promo, setPromo] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("top");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [or, tr, ar, pr] = await Promise.all([
        fetch(`${API}/api/iip/faculty/overview`, { headers: authH() }),
        fetch(`${API}/api/iip/faculty/top-performers?limit=20`, { headers: authH() }),
        fetch(`${API}/api/iip/faculty/at-risk`, { headers: authH() }),
        fetch(`${API}/api/iip/faculty/promotion-candidates`, { headers: authH() }),
      ]);
      if (or.ok) setOverview(await or.json());
      if (tr.ok) setTop(await tr.json());
      if (ar.ok) setAtRisk(await ar.json());
      if (pr.ok) setPromo(await pr.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={32} color={ACCENT} />
    </div>
  );

  const tabs = [
    { id: "top", label: "Top Performers", count: top.length, icon: Star },
    { id: "at_risk", label: "At Risk", count: atRisk.length, icon: AlertTriangle },
    { id: "promo", label: "Promotion Ready", count: promo.length, icon: TrendingUp },
  ];

  return (
    <InstitutionLayout
      title="Faculty Intelligence"
      subtitle={overview?.institution ?? ""}
    >
      {/* Overview stats — StatCard has no per-tile value-color override, so the
          original color-coded KPI values are flattened to StatCard's fixed navy. */}
      {overview && (
        <StatGrid cols={5} className="mb-5">
          <StatCard label="Total Faculty" value={overview.total} />
          <StatCard label="Active Researchers" value={overview.active} />
          <StatCard label="Inactive" value={overview.inactive} />
          <StatCard label="Engagement Rate" value={`${overview.engagement_rate ?? 0}%`} />
          <StatCard label="Departments" value={overview.departments?.length ?? 0} />
        </StatGrid>
      )}

      {/* Department breakdown */}
      {overview?.departments?.length > 0 && (
        <Card padding="lg" className="mb-5">
          <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 700, color: NAVY }}>Faculty by Department</h3>
          {overview.departments.slice(0, 8).map(d => {
            const pct = Math.round(d.count / overview.total * 100);
            return (
              <ProgressBar
                key={d.name}
                label={d.name}
                value={pct}
                max={100}
                valueLabel={`${d.count} (${pct}%)`}
                size="sm"
                className="mb-2"
              />
            );
          })}
        </Card>
      )}

      {/* Tabs */}
      <div style={{ marginBottom: 16 }}>
        <NavTabs variant="pill" active={tab} onChange={setTab} tabs={tabs} />
      </div>

      {tab === "top" && <FacultyTable data={top} title="Top Performers" />}
      {tab === "at_risk" && (
        <Card padding="none" className="overflow-hidden">
          <div style={{ padding: "14px 20px", background: "#fff7ed", borderBottom: `1px solid ${BRD}` }}>
            <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "#9a3412" }}>
              At-Risk Researchers ({atRisk.length})
            </h3>
            <p style={{ margin: "4px 0 0", fontSize: 12, color: "#9a3412", opacity: 0.8 }}>
              No publications in the last 3 years. Consider outreach and support.
            </p>
          </div>
          <List border={false} radius={0}>
            {atRisk.slice(0, 20).map((f, i) => (
              <ListItem
                key={i}
                title={f.name || "—"}
                subtitle={`${f.department} · ${f.position}`}
                trailing={
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>Grants ever: {f.grants_ever ?? 0}</span>
                    <Badge variant={f.risk_level === "high" ? "danger" : "warning"}>{f.risk_level}</Badge>
                  </div>
                }
              />
            ))}
          </List>
        </Card>
      )}
      {tab === "promo" && <FacultyTable data={promo} title="Promotion Candidates" />}
    </InstitutionLayout>
  );
}

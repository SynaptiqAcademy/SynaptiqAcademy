import React, { useState, useEffect, useCallback } from "react";
import { Award, AlertTriangle } from "lucide-react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { Card, Badge, Modal, StatCard, StatGrid, BarChart, List, ListItem, Spinner } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });
const GRADE_COLOR = { A: EMERALD, B: "#0ea5e9", C: "#f59e0b", D: "#f97316", F: ACCENT };

function DeptCard({ dept, onClick }) {
  const score = dept.health_score || 0;
  // Health-score bar color follows 70/50 thresholds tied to grade semantics —
  // ProgressBar's colorByValue only maps by 80/100 thresholds, so it can't
  // express this scheme; left hand-rolled.
  const barColor = score >= 70 ? EMERALD : score >= 50 ? "#f59e0b" : ACCENT;
  return (
    <Card onClick={onClick} padding="lg">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 14, color: NAVY, marginBottom: 2 }}>{dept.department}</div>
          <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{dept.faculty_count} faculty</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 16, fontWeight: 800, color: NAVY }}>{score}</span>
          <Badge color={GRADE_COLOR[dept.health_grade] || "#94a3b8"}>{dept.health_grade}</Badge>
        </div>
      </div>
      <div style={{ height: 5, background: `${NAVY}12`, borderRadius: 99, marginBottom: 10 }}>
        <div style={{ height: "100%", borderRadius: 99, background: barColor, width: `${score}%` }} />
      </div>
      {/* Compact inline mini-stats (no card chrome) — StatCard always renders
          its own bordered/shadowed box, so this borderless nested grid is
          left hand-rolled rather than nesting cards-in-a-card. */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        {[
          { label: "Publications", val: dept.publications_recent },
          { label: "Grant rate", val: `${dept.grant_success_rate}%` },
          { label: "Collabs", val: dept.collaborations },
        ].map(({ label, val }) => (
          <div key={label}>
            <div style={{ fontSize: 14, fontWeight: 700, color: NAVY }}>{val}</div>
            <div style={{ fontSize: 10, color: TEXT_SECONDARY }}>{label}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function DeptDetail({ dept, data, onClose }) {
  const years = Object.entries(data?.publications_by_year || {}).slice(-8);
  return (
    <Modal open onClose={onClose} title={dept.department} size="lg">
      {data ? (
        <>
          <StatGrid cols={5} className="mb-5">
            <StatCard label="Faculty" value={data.faculty_count} />
            <StatCard label="Publications" value={data.total_publications} />
            <StatCard label="Funding Approved" value={`€${(data.total_funding_approved || 0).toFixed(0)}`} />
            <StatCard label="Q1/Q2 %" value={`${data.publication_quality_pct ?? 0}%`} />
            <StatCard label="Collaborations" value={data.collaborations} />
          </StatGrid>
          {years.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <h4 style={{ margin: "0 0 10px", fontSize: 13, fontWeight: 700, color: NAVY }}>Publications by Year</h4>
              <BarChart
                data={years.map(([yr, count]) => ({ label: yr.slice(-2), value: count }))}
                height={50}
                showLabels
                color={ACCENT}
              />
            </div>
          )}
          <h4 style={{ margin: "0 0 10px", fontSize: 13, fontWeight: 700, color: NAVY }}>Faculty Members</h4>
          <List>
            {(data.faculty || []).slice(0, 10).map((f, i) => (
              <ListItem
                key={i}
                compact
                title={f.name || "—"}
                trailing={<span style={{ fontSize: 12, color: TEXT_SECONDARY }}>{f.position}</span>}
              />
            ))}
          </List>
        </>
      ) : (
        <div style={{ textAlign: "center", padding: 40 }}><Spinner size={24} color={ACCENT} /></div>
      )}
    </Modal>
  );
}

export default function DepartmentIntelligence() {
  const [depts, setDepts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetchApi(`${API}/api/iip/departments/overview`, { headers: authH() });
      if (r.ok) setDepts(await r.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const openDetail = async (dept) => {
    setSelected(dept);
    setDetail(null);
    try {
      const r = await fetchApi(`${API}/api/iip/departments/${encodeURIComponent(dept.department)}`, { headers: authH() });
      if (r.ok) setDetail(await r.json());
    } catch (_) {}
  };

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={32} color={ACCENT} />
    </div>
  );

  return (
    <InstitutionLayout
      title="Department Intelligence"
      subtitle={`${depts.length} departments · Click any card for details`}
      sidebar={<DepartmentIntelligenceSidebar depts={depts} />}
    >
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 14 }}>
        {depts.map((d, i) => <DeptCard key={i} dept={d} onClick={() => openDetail(d)} />)}
      </div>

      {selected && (
        <DeptDetail dept={selected} data={detail} onClose={() => { setSelected(null); setDetail(null); }} />
      )}
    </InstitutionLayout>
  );
}

// ── Right rail — department metrics already fetched by this page ──────────────
function DepartmentIntelligenceSidebar({ depts }) {
  if (!depts || depts.length === 0) return null;
  const top = [...depts].sort((a, b) => (b.health_score || 0) - (a.health_score || 0))[0];
  const atRisk = depts.filter(d => (d.health_score || 0) < 50);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Award size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Top Performing Department</div>
        </div>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", fontFamily: "Georgia, serif" }}>{top.department}</div>
        <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0", lineHeight: 1.5 }}>
          Health score {top.health_score} (Grade {top.health_grade}) · {top.faculty_count} faculty
        </p>
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <AlertTriangle size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Needs Attention</div>
        </div>
        {atRisk.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {atRisk.slice(0, 4).map((d, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 12.5, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.department}</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: ACCENT }}>{d.health_score}</span>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>
            No department is currently below a health score of 50.
          </p>
        )}
      </Card>
    </div>
  );
}

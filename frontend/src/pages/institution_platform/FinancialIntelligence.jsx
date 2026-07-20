import React, { useState, useEffect, useCallback } from "react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { Card, StatCard, StatGrid, Alert, List, ListItem, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

export default function FinancialIntelligence() {
  const [fin, setFin] = useState(null);
  const [byDept, setByDept] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [fr, dr] = await Promise.all([
        fetch(`${API}/api/iip/financial/overview`, { headers: authH() }),
        fetch(`${API}/api/iip/financial/by-department`, { headers: authH() }),
      ]);
      if (fr.ok) setFin(await fr.json());
      if (dr.ok) setByDept(await dr.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={32} color={ACCENT} />
    </div>
  );

  const growthPos = (fin?.income_growth_pct || 0) >= 0;

  return (
    <InstitutionLayout
      title="Financial Intelligence"
      subtitle={`Income ${growthPos ? "+" : ""}${fin?.income_growth_pct ?? 0}% year-on-year`}
    >
      {/* StatCard has no per-tile value-color override, so the original
          color-coded KPI values (emerald/navy/blue/purple) are flattened. */}
      <StatGrid cols={4} className="mb-5">
        <StatCard label="Total Research Income" value={`€${((fin?.total_research_income || 0) / 1000).toFixed(0)}k`} />
        <StatCard label="Current Year" value={`€${((fin?.current_year_income || 0) / 1000).toFixed(0)}k`} />
        <StatCard label="Active Grants" value={fin?.active_grants_count ?? 0} />
        <StatCard label="Avg Grant Size" value={`€${((fin?.avg_grant_size || 0) / 1000).toFixed(0)}k`} />
      </StatGrid>

      {fin?.funding_dependency_risk === "high" && (
        <Alert variant="warning" style={{ marginBottom: 16 }}>
          High funding concentration risk (index: {fin.funding_concentration_index?.toFixed(2)}).
          Consider diversifying funding sources.
        </Alert>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card padding="lg">
          <h3 style={{ margin: "0 0 14px", fontSize: 14, fontWeight: 700, color: NAVY }}>Top Funding Sources (by income)</h3>
          <List>
            {(fin?.top_funding_sources || []).slice(0, 8).map((f, i) => (
              <ListItem
                key={i}
                compact
                title={f.funder}
                trailing={<span style={{ fontSize: 12, fontWeight: 700, color: EMERALD }}>€{(f.income / 1000).toFixed(0)}k</span>}
              />
            ))}
          </List>
        </Card>

        <Card padding="lg">
          <h3 style={{ margin: "0 0 14px", fontSize: 14, fontWeight: 700, color: NAVY }}>Income by Department</h3>
          {byDept.slice(0, 8).map((d, i) => {
            const max = byDept[0]?.total_income || 1;
            const pct = Math.round(d.total_income / max * 100);
            return (
              <div key={i} style={{ marginBottom: 9 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ fontSize: 12, color: NAVY, fontWeight: 500, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginRight: 8 }}>{d.department}</span>
                  <span style={{ fontSize: 11, color: TEXT_SECONDARY, flexShrink: 0 }}>€{(d.total_income / 1000).toFixed(0)}k</span>
                </div>
                {/* Fixed purple fill is a deliberate per-metric brand color;
                    ProgressBar's colorByValue can't express an arbitrary fixed
                    color, so left hand-rolled. */}
                <div style={{ height: 5, background: `${NAVY}12`, borderRadius: 99 }}>
                  <div style={{ height: "100%", borderRadius: 99, background: "#8b5cf6", width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </Card>
      </div>
    </InstitutionLayout>
  );
}

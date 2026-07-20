import React, { useState, useEffect, useCallback } from "react";
import { NAVY, WARM, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { Card, StatCard, StatGrid, List, ListItem, DataTable, Badge, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const PIPELINE_COLUMNS = [
  {
    key: "title", label: "Title",
    render: (v) => <span style={{ fontWeight: 600, color: NAVY, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "inline-block" }}>{v}</span>,
  },
  { key: "funder", label: "Funder", render: (v) => <span style={{ color: TEXT_SECONDARY }}>{v}</span> },
  { key: "amount", label: "Amount", render: (v) => <span style={{ color: EMERALD, fontWeight: 700 }}>€{Number(v || 0).toLocaleString()}</span> },
  { key: "researcher", label: "Researcher", render: (v) => <span style={{ color: TEXT_SECONDARY }}>{v}</span> },
  { key: "status", label: "Status", render: (v) => <Badge variant="warning">{v}</Badge> },
];

export default function GrantIntelligence() {
  const [grants, setGrants] = useState(null);
  const [pipeline, setPipeline] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [gr, pr] = await Promise.all([
        fetch(`${API}/api/iip/grants/overview`, { headers: authH() }),
        fetch(`${API}/api/iip/grants/pipeline`, { headers: authH() }),
      ]);
      if (gr.ok) setGrants(await gr.json());
      if (pr.ok) setPipeline(await pr.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={32} color={ACCENT} />
    </div>
  );

  return (
    <InstitutionLayout
      title="Grant Intelligence"
      subtitle={grants ? `Success rate: ${grants.success_rate ?? 0}% · Total funding: €${(grants.total_funding || 0).toLocaleString()}` : "Grant funding overview and pipeline analysis"}
    >
      {/* StatCard has no per-tile value-color override, so the original
          color-coded KPI values are flattened. */}
      <StatGrid cols={5} className="mb-5">
        <StatCard label="Total Applications" value={grants?.total ?? 0} />
        <StatCard label="Approved" value={grants?.approved ?? 0} />
        <StatCard label="In Pipeline" value={grants?.submitted ?? 0} />
        <StatCard label="Rejected" value={grants?.rejected ?? 0} />
        <StatCard label="Avg Grant Size" value={`€${((grants?.avg_grant_size || 0) / 1000).toFixed(0)}k`} />
      </StatGrid>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        {/* Top funders */}
        <Card padding="lg">
          <h3 style={{ margin: "0 0 14px", fontSize: 14, fontWeight: 700, color: NAVY }}>Top Funding Agencies</h3>
          <List>
            {(grants?.top_funders || []).slice(0, 8).map((f, i) => (
              <ListItem
                key={i}
                compact
                title={f.funder}
                trailing={<span style={{ fontSize: 12, fontWeight: 700, color: TEXT_SECONDARY }}>{f.count} grants</span>}
              />
            ))}
          </List>
        </Card>

        {/* Funding by dept */}
        <Card padding="lg">
          <h3 style={{ margin: "0 0 14px", fontSize: 14, fontWeight: 700, color: NAVY }}>Funding by Department</h3>
          {(grants?.funding_by_department || []).slice(0, 8).map((d, i) => {
            const max = grants.funding_by_department[0]?.funding || 1;
            const pct = Math.round(d.funding / max * 100);
            return (
              <div key={i} style={{ marginBottom: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ fontSize: 12, color: NAVY, fontWeight: 500, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginRight: 8 }}>{d.department}</span>
                  <span style={{ fontSize: 12, color: TEXT_SECONDARY, flexShrink: 0 }}>€{(d.funding / 1000).toFixed(0)}k</span>
                </div>
                {/* Fixed emerald fill regardless of pct — ProgressBar's colorByValue
                    only turns emerald at exactly 100%, so it can't express this;
                    left hand-rolled. */}
                <div style={{ height: 5, background: `${NAVY}12`, borderRadius: 99 }}>
                  <div style={{ height: "100%", borderRadius: 99, background: EMERALD, width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </Card>
      </div>

      {/* Pipeline — DataTable owns its own bordered/rounded chrome, so the tinted
          header strip is placed directly above it rather than nested inside a
          second Card (which would double up the border). */}
      {pipeline.length > 0 && (
        <div>
          <div style={{ padding: "14px 20px", background: WARM, borderRadius: "10px 10px 0 0" }}>
            <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: NAVY }}>Active Pipeline ({pipeline.length})</h3>
          </div>
          <DataTable columns={PIPELINE_COLUMNS} rows={pipeline.slice(0, 20)} />
        </div>
      )}
    </InstitutionLayout>
  );
}

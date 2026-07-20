import React, { useState, useEffect, useCallback } from "react";
import { AlertTriangle, CheckCircle, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import { NAVY, WARM, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { Card, Button, NavTabs, EmptyState, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const LEVEL_COLOR = { critical: "#dc2626", high: "#f97316", medium: "#f59e0b", low: "#64748b" };
const LEVEL_BG    = { critical: "#fee2e2", high: "#fff7ed", medium: "#fefce8", low: WARM };

function RiskCard({ risk }) {
  const [open, setOpen] = useState(risk.level === "critical");
  const color = LEVEL_COLOR[risk.level] || "#94a3b8";
  const bg = LEVEL_BG[risk.level] || WARM;
  return (
    <Card padding="none" accent={color} className="mb-2 overflow-hidden">
      <button onClick={() => setOpen(v => !v)} style={{
        width: "100%", padding: "12px 16px", display: "flex", alignItems: "center", gap: 10,
        background: open ? bg : "transparent", border: "none", cursor: "pointer", textAlign: "left",
      }}>
        <AlertTriangle size={15} color={color} />
        <span style={{ flex: 1, fontWeight: 700, fontSize: 13, color: NAVY }}>{risk.title}</span>
        <span style={{ fontSize: 11, fontWeight: 700, color, textTransform: "uppercase", letterSpacing: "0.05em", minWidth: 54 }}>{risk.level}</span>
        {open ? <ChevronUp size={14} color={TEXT_SECONDARY} /> : <ChevronDown size={14} color={TEXT_SECONDARY} />}
      </button>
      {open && (
        <div style={{ padding: "0 16px 14px 16px" }}>
          <p style={{ fontSize: 13, color: "#334155", margin: "0 0 10px" }}>{risk.description}</p>
          <div style={{ display: "flex", gap: 16, marginBottom: 10 }}>
            <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>
              Metric: <strong style={{ color: NAVY }}>{risk.metric}</strong>
            </span>
            <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>
              Value: <strong style={{ color }}>{typeof risk.value === "number" ? risk.value.toFixed(1) : risk.value}</strong>
            </span>
            <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>
              Threshold: <strong>{typeof risk.threshold === "number" ? risk.threshold : risk.threshold}</strong>
            </span>
          </div>
          <div style={{ background: `${color}10`, borderRadius: 7, padding: "8px 12px", fontSize: 13, color: "#334155" }}>
            <strong>Recommended Action:</strong> {risk.action}
          </div>
        </div>
      )}
    </Card>
  );
}

export default function RiskIntelligence() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/iip/risks`, { headers: authH() });
      if (r.ok) setData(await r.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={32} color={ACCENT} />
    </div>
  );

  const flags = (data?.flags || []).filter(f => filter === "all" || f.level === filter);

  return (
    <InstitutionLayout
      title="Risk Intelligence"
      subtitle={data ? `${data.total ?? 0} flags · ${data.critical ?? 0} critical · ${data.high ?? 0} high` : "Institutional risk monitoring and flag management"}
      actions={
        <Button variant="ghost" size="md" onClick={load}>
          <RefreshCw size={14} /> Refresh
        </Button>
      }
    >

      {/* Summary tiles — per-level tinted background/border plus a
          selected-outline state have no match on StatCard (fixed navy value,
          no bg/border/selection styling), so left hand-rolled. */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 20 }}>
        {["critical", "high", "medium", "low"].map(level => (
          <div key={level} style={{
            background: LEVEL_BG[level], border: `1px solid ${LEVEL_COLOR[level]}44`,
            borderRadius: 10, padding: "12px 16px", cursor: "pointer",
            outline: filter === level ? `2px solid ${LEVEL_COLOR[level]}` : "none",
          }} onClick={() => setFilter(filter === level ? "all" : level)}>
            <div style={{ fontSize: 24, fontWeight: 800, color: LEVEL_COLOR[level] }}>{data?.[level] ?? 0}</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: LEVEL_COLOR[level], textTransform: "capitalize" }}>{level}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ marginBottom: 16 }}>
        <NavTabs
          variant="pill"
          active={filter}
          onChange={setFilter}
          tabs={[
            { id: "all", label: `All (${data?.total ?? 0})` },
            { id: "critical", label: "Critical" },
            { id: "high", label: "High" },
            { id: "medium", label: "Medium" },
            { id: "low", label: "Low" },
          ]}
        />
      </div>

      {flags.length === 0 ? (
        <EmptyState
          icon={<CheckCircle color={EMERALD} />}
          title="No risks in this category"
          description={filter === "all" ? "Institution health looks strong across all monitored areas." : `No ${filter} risks detected.`}
        />
      ) : (
        flags.map((r, i) => <RiskCard key={r.key || i} risk={r} />)
      )}
    </InstitutionLayout>
  );
}

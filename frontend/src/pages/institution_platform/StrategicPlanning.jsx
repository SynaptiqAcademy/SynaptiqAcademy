import React, { useState, useEffect, useCallback } from "react";
import { AlertTriangle, TrendingUp, BarChart2, ChevronDown, ChevronUp } from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { Card, StatCard, StatGrid, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const LEVEL_COLOR = { critical: "#dc2626", high: "#f97316", medium: "#f59e0b", low: "#64748b" };

function PriorityItem({ item, index }) {
  const [open, setOpen] = useState(index < 3);
  const color = LEVEL_COLOR[item.priority] || ACCENT;
  return (
    <Card padding="none" accent={color} className="mb-2 overflow-hidden">
      <button onClick={() => setOpen(v => !v)} style={{
        width: "100%", padding: "12px 16px", display: "flex", alignItems: "center", gap: 10,
        background: "none", border: "none", cursor: "pointer", textAlign: "left",
      }}>
        <span style={{ width: 22, height: 22, borderRadius: "50%", background: `${color}20`, color, fontWeight: 800, fontSize: 11, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{index + 1}</span>
        <span style={{ flex: 1, fontWeight: 700, fontSize: 13, color: NAVY }}>{item.title}</span>
        <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 6, background: `${color}15`, color, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>{item.priority}</span>
        {open ? <ChevronUp size={14} color={TEXT_SECONDARY} /> : <ChevronDown size={14} color={TEXT_SECONDARY} />}
      </button>
      {open && (
        <div style={{ padding: "0 16px 14px 42px" }}>
          <p style={{ margin: "0 0 10px", fontSize: 13, color: "#334155", lineHeight: 1.6 }}>{item.description}</p>
          {item.action && (
            <div style={{ background: `${color}08`, border: `1px solid ${color}25`, borderRadius: 8, padding: "8px 12px", fontSize: 13 }}>
              <strong style={{ color: NAVY }}>Recommended action: </strong>
              <span style={{ color: "#334155" }}>{item.action}</span>
            </div>
          )}
          {item.forecast_note && (
            <div style={{ marginTop: 8, fontSize: 12, color: TEXT_SECONDARY, fontStyle: "italic" }}>{item.forecast_note}</div>
          )}
          {item.gap && (
            <div style={{ marginTop: 8, fontSize: 12, color: TEXT_SECONDARY }}>
              Benchmark gap: <strong style={{ color: ACCENT }}>{item.gap}</strong>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

// A titled panel with a tinted (WARM) header strip — reimplemented on top of
// Card since Card.Header only draws a border-bottom, not a background tint;
// the header here stays a custom div for that reason.
function Section({ icon: Icon, title, children, color }) {
  return (
    <Card padding="none" className="mb-5 overflow-hidden">
      <div style={{ padding: "14px 20px", background: WARM, borderBottom: `1px solid ${BRD}`, display: "flex", alignItems: "center", gap: 8 }}>
        <Icon size={16} color={color || NAVY} />
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: NAVY }}>{title}</h3>
      </div>
      <div style={{ padding: 20 }}>{children}</div>
    </Card>
  );
}

export default function StrategicPlanning() {
  const [risks, setRisks] = useState(null);
  const [bench, setBench] = useState(null);
  const [pubF, setPubF] = useState(null);
  const [grantF, setGrantF] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [rr, br, pr, gr] = await Promise.all([
        fetch(`${API}/api/iip/risks`, { headers: authH() }),
        fetch(`${API}/api/iip/benchmarks/overview`, { headers: authH() }),
        fetch(`${API}/api/iip/forecasts/publications?horizon=3`, { headers: authH() }),
        fetch(`${API}/api/iip/forecasts/grants?horizon=3`, { headers: authH() }),
      ]);
      if (rr.ok) setRisks(await rr.json());
      if (br.ok) setBench(await br.json());
      if (pr.ok) setPubF(await pr.json());
      if (gr.ok) setGrantF(await gr.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={32} color={ACCENT} />
    </div>
  );

  // Build strategic priorities from risks + benchmark gaps
  const priorities = [];

  // Top risks → priorities
  const topRisks = (risks?.flags || []).filter(f => f.level === "critical" || f.level === "high").slice(0, 5);
  topRisks.forEach(r => {
    priorities.push({
      title: r.title,
      priority: r.level,
      description: r.description,
      action: r.action,
    });
  });

  // Benchmark gaps → priorities
  const belowNational = (bench?.benchmarks || []).filter(b => b.vs_national < -10).slice(0, 3);
  belowNational.forEach(b => {
    priorities.push({
      title: `Close gap in ${b.metric.replace(/_/g, " ")}`,
      priority: "medium",
      description: `Your institution is ${Math.abs(b.vs_national).toFixed(1)} points below the national average on ${b.metric.replace(/_/g, " ")}.`,
      gap: `${b.vs_national.toFixed(1)} vs national average`,
    });
  });

  // Forecast-driven priorities
  if (pubF?.trend_slope < 0) {
    priorities.push({
      title: "Reverse declining publication trend",
      priority: "high",
      description: "Publication output is trending downward. Without intervention, this trajectory will continue for the next 3 years.",
      forecast_note: `Forecast slope: ${pubF.trend_slope.toFixed(2)} publications/year`,
      action: "Review faculty workloads, mentoring support, and research infrastructure. Consider targeted writing retreats or publication incentives.",
    });
  }
  if (grantF?.trend_slope < 0) {
    priorities.push({
      title: "Strengthen grant acquisition pipeline",
      priority: "high",
      description: "Grant approval trends are declining. The institution may face funding shortfalls in the coming years.",
      forecast_note: `Forecast slope: ${grantF.trend_slope.toFixed(2)} grants/year`,
      action: "Invest in a research development office. Provide dedicated grant writing support and identify high-probability funding opportunities.",
    });
  }

  // Sort: critical first
  const levelOrder = { critical: 0, high: 1, medium: 2, low: 3 };
  priorities.sort((a, b) => (levelOrder[a.priority] ?? 4) - (levelOrder[b.priority] ?? 4));

  const criticalCount = priorities.filter(p => p.priority === "critical").length;
  const highCount = priorities.filter(p => p.priority === "high").length;

  return (
    <InstitutionLayout
      title="Strategic Planning"
      subtitle={bench ? `${bench.institution} · ${priorities.length} strategic priorities · ${criticalCount} critical · ${highCount} high` : "Strategic priorities derived from risk, benchmark, and forecast analysis"}
    >

      {/* Summary strip — StatCard has no per-tile value-color override, so
          the original color-coded KPI values are flattened. */}
      <StatGrid cols={4} className="mb-5">
        <StatCard label="Total Priorities" value={priorities.length} />
        <StatCard label="Critical" value={criticalCount} />
        <StatCard label="High Priority" value={highCount} />
        <StatCard label="Benchmark Gaps" value={belowNational.length} />
      </StatGrid>

      {/* Strategic Priorities */}
      <Section icon={AlertTriangle} title="Strategic Priority List" color={ACCENT}>
        {priorities.length === 0 ? (
          <div style={{ textAlign: "center", padding: 24, color: TEXT_SECONDARY, fontSize: 13 }}>
            No strategic priorities identified. Institution health is strong across all monitored dimensions.
          </div>
        ) : (
          priorities.map((item, i) => <PriorityItem key={i} item={item} index={i} />)
        )}
      </Section>

      {/* Benchmark context — compact horizontal label/value comparison chips
          arranged in a 2-col grid; distinct shape from StatCard's vertical
          label-then-big-value layout, so left hand-rolled. */}
      {bench && (
        <Section icon={BarChart2} title="Benchmark Context" color="#8b5cf6">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {(bench.benchmarks || []).slice(0, 8).map((b, i) => {
              const isBelow = b.vs_national < 0;
              return (
                <div key={i} style={{ background: WARM, borderRadius: 8, padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, color: NAVY, fontWeight: 500 }}>{b.metric.replace(/_/g, " ")}</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: isBelow ? ACCENT : EMERALD }}>
                    {b.vs_national >= 0 ? "+" : ""}{b.vs_national.toFixed(1)} vs national
                  </span>
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* Forecast outlook — the tinted WARM sub-panels and their compact
          year/value rows have no flat (borderless, backgroundless) ds/
          equivalent to nest inside, so left hand-rolled. */}
      <Section icon={TrendingUp} title="3-Year Outlook" color={EMERALD}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {pubF && (
            <div style={{ background: WARM, borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: NAVY, marginBottom: 6 }}>Publications</div>
              <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 8 }}>
                Trend: <strong style={{ color: pubF.trend_slope >= 0 ? EMERALD : ACCENT }}>
                  {pubF.trend_slope >= 0 ? "+" : ""}{pubF.trend_slope.toFixed(1)}/yr
                </strong>
              </div>
              {(pubF.forecasts || []).map((f, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "3px 0", borderBottom: i < pubF.forecasts.length - 1 ? `1px solid ${BRD}` : "none" }}>
                  <span style={{ color: TEXT_SECONDARY }}>{f.year}</span>
                  <span style={{ fontWeight: 700, color: NAVY }}>{f.projected ?? "—"}</span>
                </div>
              ))}
            </div>
          )}
          {grantF && (
            <div style={{ background: WARM, borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: NAVY, marginBottom: 6 }}>Grants</div>
              <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 8 }}>
                Trend: <strong style={{ color: grantF.trend_slope >= 0 ? EMERALD : ACCENT }}>
                  {grantF.trend_slope >= 0 ? "+" : ""}{grantF.trend_slope.toFixed(1)}/yr
                </strong>
              </div>
              {(grantF.forecasts || []).map((f, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "3px 0", borderBottom: i < grantF.forecasts.length - 1 ? `1px solid ${BRD}` : "none" }}>
                  <span style={{ color: TEXT_SECONDARY }}>{f.year}</span>
                  <span style={{ fontWeight: 700, color: NAVY }}>{f.projected_approved ?? f.projected ?? "—"}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div style={{ marginTop: 12, fontSize: 11, color: TEXT_SECONDARY }}>
          Forecasts based on linear extrapolation of historical data. Indicative only — use alongside expert judgement.
        </div>
      </Section>
    </InstitutionLayout>
  );
}

import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Activity, Users, BookOpen, BadgeDollarSign, Network,
  AlertTriangle, TrendingUp, RefreshCw,
  ChevronRight, Zap, Shield, Building2, Coins,
} from "lucide-react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { Card, Button, StatCard, StatGrid, ErrorState, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const GRADE_COLOR = { "A+": EMERALD, A: EMERALD, B: "#0ea5e9", C: "#f59e0b", D: "#f97316", F: ACCENT };
const LEVEL_BG = { critical: "#fee2e2", high: "#fff7ed", medium: "#fefce8", low: "#f8f5f0" };
const LEVEL_COLOR = { critical: "#dc2626", high: "#f97316", medium: "#f59e0b", low: "#64748b" };

// GradeRing is unused dead code in the original file (never rendered in the
// return JSX below) — left exactly as-is rather than migrating unreferenced code.
function GradeRing({ score, grade, size = 100 }) {
  const r = size * 0.38;
  const circ = 2 * Math.PI * r;
  const progress = ((score || 0) / 100) * circ;
  const color = GRADE_COLOR[grade] || ACCENT;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={`${color}22`} strokeWidth={size * 0.08} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color}
          strokeWidth={size * 0.08} strokeDasharray={`${progress} ${circ}`} strokeLinecap="round" />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: size * 0.22, fontWeight: 800, color: NAVY, lineHeight: 1 }}>{score ?? "—"}</span>
        <span style={{ fontSize: size * 0.13, fontWeight: 700, color }}>{grade}</span>
      </div>
    </div>
  );
}

// Left-accent + tinted-background risk row: no ds/ component combines a
// per-severity background tint, a left accent bar, title+subtitle, AND a
// trailing level tag in one row (Alert has no trailing badge slot; Card's
// `accent` only adds a border, not a background tint) — left hand-rolled.
function RiskBadge({ risk }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10,
      background: LEVEL_BG[risk.level] || "#f8f5f0",
      borderLeft: `3px solid ${LEVEL_COLOR[risk.level] || "#94a3b8"}`,
      borderRadius: "0 8px 8px 0", padding: "8px 12px", marginBottom: 6,
    }}>
      <AlertTriangle size={13} color={LEVEL_COLOR[risk.level]} />
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: NAVY }}>{risk.title}</div>
        <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>{risk.action}</div>
      </div>
      <span style={{
        fontSize: 10, fontWeight: 700, color: LEVEL_COLOR[risk.level],
        textTransform: "uppercase", letterSpacing: "0.05em",
      }}>{risk.level}</span>
    </div>
  );
}

export default function ExecutiveDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const r = await fetch(`${API}/api/iip/executive/overview`, { headers: authH() });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || `HTTP ${r.status}`);
      }
      setData(await r.json());
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={36} color={ACCENT} />
    </div>
  );

  if (err) return (
    <div style={{ maxWidth: 700, margin: "60px auto", padding: 32 }}>
      <ErrorState
        message="Unable to Load Dashboard"
        detail={`${err} — This platform requires an institution administrator account with an institution set in your profile.`}
        onRetry={load}
      />
    </div>
  );

  const h = data.health || {};
  const p = data.publications || {};
  const g = data.grants || {};
  const f = data.faculty || {};
  const c = data.collaboration || {};
  const fi = data.financial || {};
  const r = data.risks || {};

  return (
    <InstitutionLayout
      title="Executive Dashboard"
      subtitle={data.institution}
      actions={
        <Button variant="primary" size="md" onClick={load}>
          <RefreshCw size={14} /> Refresh
        </Button>
      }
    >
      {/* KPI Grid — icon/value accent colors from the original hand-rolled tiles
          have no override prop on StatCard (fixed navy value, fixed icon tint),
          so per-tile coloring is flattened here. */}
      <StatGrid cols={4} className="mb-6">
        <StatCard label="Total Publications" value={p.total} sub={`${p.q1q2_pct ?? 0}% in Q1/Q2`}
          icon={<BookOpen />} trend={p.growth_rate_pct}
          onClick={() => navigate("/institution-platform/publications")} />
        <StatCard label="Grant Success Rate" value={`${g.success_rate ?? 0}%`} sub={`${g.approved ?? 0} approved`}
          icon={<BadgeDollarSign />}
          onClick={() => navigate("/institution-platform/grants")} />
        <StatCard label="Research Income" value={`€${((fi.total_research_income || 0) / 1000).toFixed(0)}k`}
          sub="Approved grants" icon={<Coins />} trend={fi.income_growth_pct}
          onClick={() => navigate("/institution-platform/financial")} />
        <StatCard label="Active Faculty" value={f.active} sub={`${f.engagement_rate ?? 0}% engaged`}
          icon={<Users />}
          onClick={() => navigate("/institution-platform/faculty")} />
        <StatCard label="Avg Citations" value={p.avg_citations} sub="Per publication"
          icon={<Zap />}
          onClick={() => navigate("/institution-platform/publications")} />
        <StatCard label="Collaborations" value={c.total} sub={`${c.international_pct ?? 0}% international`}
          icon={<Network />}
          onClick={() => navigate("/institution-platform/collaborations")} />
        <StatCard label="Integrity Score" value={h.score} sub="Institution health"
          icon={<Shield />}
          onClick={() => navigate("/institution-platform/health")} />
        <StatCard label="Active Risks" value={r.total} sub={`${r.critical ?? 0} critical`}
          icon={<AlertTriangle />}
          onClick={() => navigate("/institution-platform/risks")} />
      </StatGrid>

      {/* Lower panels */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Health indicators snippet */}
        <Card padding="lg">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Activity size={16} color={ACCENT} />
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: NAVY }}>Health Indicators</h3>
            </div>
            <Button variant="link" size="sm" onClick={() => navigate("/institution-platform/health")}>
              View all <ChevronRight size={13} />
            </Button>
          </div>
          {/* Health-score bar color follows 70/50 qualitative bands, distinct from
              ProgressBar's colorByValue 80/100 overrun thresholds — left hand-rolled. */}
          {[...Array(5)].map((_, i) => {
            const ind = (data.health?.indicators || [])[i];
            if (!ind) return null;
            const barColor = ind.value >= 70 ? EMERALD : ind.value >= 50 ? "#f59e0b" : ACCENT;
            return (
              <div key={ind.key} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ fontSize: 12, color: NAVY, fontWeight: 500 }}>{ind.label}</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: barColor }}>{ind.value}/100</span>
                </div>
                <div style={{ height: 5, background: `${NAVY}12`, borderRadius: 99 }}>
                  <div style={{ height: "100%", borderRadius: 99, background: barColor, width: `${ind.value}%`, transition: "width 0.6s" }} />
                </div>
              </div>
            );
          })}
        </Card>

        {/* Top risks */}
        <Card padding="lg">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <AlertTriangle size={16} color={ACCENT} />
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: NAVY }}>
                Active Risk Flags ({r.total ?? 0})
              </h3>
            </div>
            <Button variant="link" size="sm" onClick={() => navigate("/institution-platform/risks")}>
              View all <ChevronRight size={13} />
            </Button>
          </div>
          {(!data.risks?.flags || data.risks.flags.length === 0)
            ? <div style={{ textAlign: "center", padding: 20, color: TEXT_SECONDARY, fontSize: 13 }}>
                No active risks — institution health looks strong.
              </div>
            : data.risks.flags?.slice(0, 4).map((risk, i) => <RiskBadge key={i} risk={risk} />)
          }
        </Card>
      </div>

      {/* Quick navigation */}
      <div style={{ marginTop: 20, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 8 }}>
        {[
          { label: "Faculty", path: "/institution-platform/faculty", icon: Users, color: NAVY },
          { label: "Departments", path: "/institution-platform/departments", icon: Building2, color: "#6366f1" },
          { label: "Grants", path: "/institution-platform/grants", icon: BadgeDollarSign, color: EMERALD },
          { label: "Collaborations", path: "/institution-platform/collaborations", icon: Network, color: "#06b6d4" },
          { label: "Forecasts", path: "/institution-platform/forecasts", icon: TrendingUp, color: "#8b5cf6" },
          { label: "Benchmarks", path: "/institution-platform/benchmarks", icon: Activity, color: "#f59e0b" },
          { label: "AI Assistant", path: "/institution-platform/assistant", icon: Zap, color: ACCENT },
          { label: "Reports", path: "/institution-platform/reports", icon: BookOpen, color: "#475569" },
        ].map(({ label, path, icon: Icon, color }) => (
          <Card key={path} onClick={() => navigate(path)} padding="sm">
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Icon size={15} color={color} />
              <span style={{ fontSize: 12, fontWeight: 600, color: NAVY }}>{label}</span>
            </div>
          </Card>
        ))}
      </div>
    </InstitutionLayout>
  );
}

import React, { useState, useEffect, useCallback } from "react";
import { RefreshCw, TrendingUp, TrendingDown } from "lucide-react";
import { NAVY, BRD, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { Card, Button, BarChart, Alert, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });
const GRADE_COLOR = { "A+": EMERALD, A: EMERALD, B: "#0ea5e9", C: "#f59e0b", D: "#f97316", F: ACCENT };

// Grade-colored ring with a custom "Grade X" subtext has no equivalent in
// ProgressRing (which only supports colorByValue's fixed 80/50/30 thresholds
// or a plain navy fill, and always labels "/ 100") — left hand-rolled.
function ScoreRing({ score, grade }) {
  const r = 52, circ = 2 * Math.PI * r, progress = (score / 100) * circ;
  const color = GRADE_COLOR[grade] || ACCENT;
  return (
    <div style={{ position: "relative", width: 130, height: 130 }}>
      <svg width={130} height={130} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={65} cy={65} r={r} fill="none" stroke={`${color}22`} strokeWidth={10} />
        <circle cx={65} cy={65} r={r} fill="none" stroke={color} strokeWidth={10}
          strokeDasharray={`${progress} ${circ}`} strokeLinecap="round"
          style={{ transition: "stroke-dasharray 0.8s ease" }} />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: 26, fontWeight: 800, color: NAVY }}>{score}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color }}>Grade {grade}</span>
      </div>
    </div>
  );
}

// Two-line row (label+description header, status+value, bar+weight footer) —
// left hand-rolled; its 70/50 qualitative bar-color bands don't match
// ProgressBar's colorByValue 80/100 overrun thresholds.
function IndicatorRow({ ind }) {
  const barColor = ind.value >= 70 ? EMERALD : ind.value >= 50 ? "#f59e0b" : ACCENT;
  const statusColor = { good: EMERALD, warning: "#f59e0b", critical: ACCENT }[ind.status] || TEXT_SECONDARY;
  return (
    <div style={{ padding: "12px 0", borderBottom: `1px solid ${BRD}` }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <div>
          <span style={{ fontWeight: 600, fontSize: 13, color: NAVY }}>{ind.label}</span>
          <span style={{ fontSize: 11, color: TEXT_SECONDARY, marginLeft: 8 }}>{ind.description}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 11, color: statusColor, fontWeight: 700, textTransform: "uppercase" }}>{ind.status}</span>
          <span style={{ fontSize: 14, fontWeight: 800, color: NAVY, minWidth: 48, textAlign: "right" }}>{ind.value}/100</span>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ flex: 1, height: 6, background: `${NAVY}12`, borderRadius: 99 }}>
          <div style={{ height: "100%", borderRadius: 99, background: barColor, width: `${ind.value}%`, transition: "width 0.6s" }} />
        </div>
        <span style={{ fontSize: 11, color: TEXT_SECONDARY, minWidth: 40, textAlign: "right" }}>
          {(ind.weight * 100).toFixed(0)}% wt
        </span>
      </div>
    </div>
  );
}

export default function InstitutionHealth() {
  const [health, setHealth] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [hr, hhr] = await Promise.all([
        fetch(`${API}/api/iip/health/score`, { headers: authH() }),
        fetch(`${API}/api/iip/health/history?days=90`, { headers: authH() }),
      ]);
      if (hr.ok) setHealth(await hr.json());
      if (hhr.ok) setHistory(await hhr.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={32} color={ACCENT} />
    </div>
  );

  const sorted = (health?.indicators || []).slice().sort((a, b) => a.value - b.value);
  const weakest = sorted.slice(0, 3);
  const strongest = sorted.slice(-3).reverse();

  return (
    <InstitutionLayout
      title="Institution Health"
      subtitle={health ? `${health.institution} · ${health.faculty_count} researchers · Grade ${health.grade}` : "Monitor your institution's health across all key indicators"}
      actions={
        <Button variant="ghost" size="md" onClick={load}>
          <RefreshCw size={14} /> Refresh
        </Button>
      }
    >
      {/* Health score ring */}
      {health && (
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 24 }}>
          <ScoreRing score={health.score} grade={health.grade} />
        </div>
      )}

      {/* Score snapshot history */}
      {history.length > 0 && (
        <Card padding="lg" className="mb-4">
          <h3 style={{ margin: "0 0 14px", fontSize: 14, fontWeight: 700, color: NAVY }}>Score History (90 days)</h3>
          <BarChart
            data={history.map(h => ({
              label: h.date,
              value: h.score,
              color: h.score >= 70 ? EMERALD : h.score >= 50 ? "#f59e0b" : ACCENT,
            }))}
            height={60}
            gap={4}
          />
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 10, color: TEXT_SECONDARY }}>
            <span>{history[0]?.date}</span><span>{history[history.length - 1]?.date}</span>
          </div>
        </Card>
      )}

      {/* Strengths + Weaknesses */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <Alert variant="success" title="Strongest Areas" icon={TrendingUp}>
          {strongest.map(ind => (
            <div key={ind.key} style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span>{ind.label}</span>
              <span style={{ fontWeight: 700 }}>{ind.value}/100</span>
            </div>
          ))}
        </Alert>
        <Alert variant="warning" title="Needs Attention" icon={TrendingDown}>
          {weakest.map(ind => (
            <div key={ind.key} style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span>{ind.label}</span>
              <span style={{ fontWeight: 700 }}>{ind.value}/100</span>
            </div>
          ))}
        </Alert>
      </div>

      {/* All indicators */}
      <Card padding="lg">
        <h3 style={{ margin: "0 0 4px", fontSize: 14, fontWeight: 700, color: NAVY }}>All Health Indicators</h3>
        <p style={{ margin: "0 0 12px", fontSize: 12, color: TEXT_SECONDARY }}>Weights reflect relative importance to overall score.</p>
        {(health?.indicators || []).map(ind => <IndicatorRow key={ind.key} ind={ind} />)}
      </Card>
    </InstitutionLayout>
  );
}

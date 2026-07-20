import React, { useEffect, useState } from "react";
import { BarChart2, TrendingUp, TrendingDown, Lightbulb, Trophy, Activity, CalendarDays } from "lucide-react";
import { NAVY, WARM, BRD, EMERALD, ACCENT, TEXT_SECONDARY, WHITE } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";

const API = "/api/timeline";

const CATEGORY_COLORS = {
  research:      "#0369A1",
  teaching:      "#7C3AED",
  grant:         "#059669",
  collaboration: "#0F2847",
  review:        "#D97706",
  verification:  "#059669",
  recognition:   "#D97706",
  community:     "#0369A1",
  ai:            "#7C3AED",
};

function MonthBar({ month, maxTotal }) {
  const pct = maxTotal > 0 ? Math.round((month.total / maxTotal) * 100) : 0;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "5px 0" }}>
      <span style={{ width: 54, fontSize: 11, color: TEXT_SECONDARY, flexShrink: 0, textAlign: "right" }}>
        {month.label.slice(0, 6)}
      </span>
      <div style={{ flex: 1, height: 18, background: BRD, borderRadius: 4, position: "relative" }}>
        <div style={{
          height: "100%", borderRadius: 4,
          width: `${pct}%`,
          background: `linear-gradient(90deg, ${NAVY} 0%, #1e4080 100%)`,
          transition: "width .4s ease",
        }} />
        {month.total > 0 && (
          <span style={{
            position: "absolute", left: `${Math.min(pct, 85)}%`, top: "50%",
            transform: "translateY(-50%)", paddingLeft: 6,
            fontSize: 10, color: pct > 40 ? WHITE : NAVY, fontWeight: 600,
          }}>{month.total}</span>
        )}
      </div>
    </div>
  );
}

function CategoryBar({ cat, count, total }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  const color = CATEGORY_COLORS[cat] || NAVY;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "5px 0" }}>
      <span style={{ width: 90, fontSize: 12, color: NAVY, fontWeight: 500, flexShrink: 0, textTransform: "capitalize" }}>
        {cat}
      </span>
      <div style={{ flex: 1, height: 10, background: BRD, borderRadius: 10 }}>
        <div style={{
          width: `${pct}%`, height: "100%", borderRadius: 10,
          background: color, transition: "width .4s ease",
        }} />
      </div>
      <span style={{ width: 42, fontSize: 11, color: TEXT_SECONDARY, flexShrink: 0, textAlign: "right" }}>
        {count} ({pct}%)
      </span>
    </div>
  );
}

export default function TimelineAnalytics() {
  const [analytics, setAnalytics] = useState(null);
  const [milestones, setMilestones] = useState([]);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(12);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch(`${API}/analytics?months=${period}`, { credentials: "include" }).then(r => r.json()).catch(() => null),
      fetch(`${API}/milestones`, { credentials: "include" }).then(r => r.json()).catch(() => []),
      fetch(`${API}/insights`, { credentials: "include" }).then(r => r.json()).catch(() => []),
    ]).then(([a, m, i]) => {
      setAnalytics(a);
      setMilestones(m || []);
      setInsights(i || []);
      setLoading(false);
    });
  }, [period]);

  if (loading) {
    return (
      <ResearchLayout title="Activity Analytics" subtitle="Research productivity and career progression analysis" icon={<BarChart2 size={18} />}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 80, color: TEXT_SECONDARY }}>
          Loading analytics…
        </div>
      </ResearchLayout>
    );
  }

  const monthly = analytics?.monthly_breakdown || [];
  const maxTotal = Math.max(...monthly.map(m => m.total), 1);
  const categoryTotals = analytics?.category_totals || {};
  const totalEvents = Object.values(categoryTotals).reduce((a, b) => a + b, 0);
  const trend = analytics?.trend_pct ?? 0;

  const periodPicker = (
    <div style={{ display: "flex", gap: 6 }}>
      {[3, 6, 12, 24].map(p => (
        <button key={p} onClick={() => setPeriod(p)}
          style={{
            padding: "6px 12px", borderRadius: 6, fontSize: 12, fontWeight: 600,
            border: `1px solid ${period === p ? NAVY : BRD}`,
            background: period === p ? NAVY : WHITE,
            color: period === p ? WHITE : NAVY, cursor: "pointer",
          }}>
          {p}m
        </button>
      ))}
    </div>
  );

  return (
    <ResearchLayout
      title="Activity Analytics"
      subtitle="Research productivity and career progression analysis"
      icon={<BarChart2 size={18} />}
      actions={periodPicker}
    >
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>

        {/* Trend card */}
        <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 200px", background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12, padding: 20 }}>
            <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 6 }}>Recent 3-Month Trend</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {trend >= 0
                ? <TrendingUp size={22} color={EMERALD} />
                : <TrendingDown size={22} color={ACCENT} />
              }
              <span style={{ fontSize: 28, fontWeight: 800, color: trend >= 0 ? EMERALD : ACCENT }}>
                {trend >= 0 ? "+" : ""}{trend}%
              </span>
            </div>
            <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 4 }}>
              {analytics?.recent_3_months || 0} events vs {analytics?.prior_3_months || 0} prior
            </div>
          </div>

          <div style={{ flex: "1 1 200px", background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12, padding: 20 }}>
            <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 6 }}>Total Events (Period)</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: NAVY }}>{totalEvents}</div>
            {analytics?.peak_month && (
              <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 4 }}>
                Peak: {analytics.peak_month.label} ({analytics.peak_month.total})
              </div>
            )}
          </div>

          <div style={{ flex: "1 1 200px", background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12, padding: 20 }}>
            <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 6 }}>Milestones Reached</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Trophy size={22} color="#D97706" />
              <span style={{ fontSize: 28, fontWeight: 800, color: "#D97706" }}>{milestones.length}</span>
            </div>
            {milestones[0] && (
              <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 4 }}>
                Latest: {milestones[0].label}
              </div>
            )}
          </div>
        </div>

        <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
          {/* Monthly bar chart */}
          <div style={{ flex: "1 1 420px", background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12, padding: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 14, display: "flex", alignItems: "center", gap: 6 }}>
              <CalendarDays size={14} /> Monthly Activity
            </div>
            <div>
              {monthly.slice(-period).map(m => (
                <MonthBar key={m.month} month={m} maxTotal={maxTotal} />
              ))}
            </div>
          </div>

          <div style={{ flex: "1 1 300px", display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Category breakdown */}
            <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12, padding: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 14, display: "flex", alignItems: "center", gap: 6 }}>
                <Activity size={14} /> By Category
              </div>
              {Object.entries(categoryTotals)
                .sort(([, a], [, b]) => b - a)
                .filter(([, v]) => v > 0)
                .map(([cat, count]) => (
                  <CategoryBar key={cat} cat={cat} count={count} total={totalEvents} />
                ))}
              {totalEvents === 0 && (
                <p style={{ color: TEXT_SECONDARY, fontSize: 13, textAlign: "center", padding: "20px 0" }}>No events yet</p>
              )}
            </div>

            {/* Top event types */}
            {analytics?.top_event_types?.length > 0 && (
              <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12, padding: 20 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 12 }}>Top Event Types</div>
                {analytics.top_event_types.slice(0, 6).map((t, i) => (
                  <div key={t.type} style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "5px 0",
                    borderBottom: i < 5 ? `1px solid ${BRD}` : "none",
                    fontSize: 12,
                  }}>
                    <span style={{ color: NAVY, fontWeight: 500, textTransform: "capitalize" }}>
                      {t.type.replace(/_/g, " ")}
                    </span>
                    <span style={{ color: TEXT_SECONDARY, fontWeight: 600 }}>{t.count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Insights */}
        {insights.length > 0 && (
          <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12, padding: 20, marginTop: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 14, display: "flex", alignItems: "center", gap: 6 }}>
              <Lightbulb size={14} color="#D97706" /> Timeline Insights
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {insights.map(ins => (
                <div key={ins.key} style={{
                  display: "flex", gap: 12, padding: "12px 16px",
                  borderRadius: 9, border: `1px solid ${BRD}`,
                  background: ins.type === "positive" ? EMERALD + "06"
                    : ins.type === "warning" ? "#D97706" + "06" : WARM,
                }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: "50%", flexShrink: 0, marginTop: 5,
                    background: ins.type === "positive" ? EMERALD
                      : ins.type === "warning" ? "#D97706" : TEXT_SECONDARY,
                  }} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: NAVY }}>{ins.title}</div>
                    <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 3 }}>{ins.body}</div>
                    <div style={{ fontSize: 11, color: "#0369A1", marginTop: 5, fontWeight: 500 }}>→ {ins.action}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Career milestones timeline */}
        {milestones.length > 0 && (
          <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12, padding: 20, marginTop: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 14, display: "flex", alignItems: "center", gap: 6 }}>
              <Trophy size={14} color="#D97706" /> Career Milestones
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {milestones.map((m, i) => (
                <div key={m.milestone_key} style={{
                  display: "flex", gap: 14, alignItems: "flex-start",
                  paddingBottom: i < milestones.length - 1 ? 10 : 0,
                  borderBottom: i < milestones.length - 1 ? `1px solid ${BRD}` : "none",
                }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: "50%",
                    background: "#D97706" + "14",
                    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                  }}>
                    <Trophy size={13} color="#D97706" />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: NAVY }}>{m.label}</div>
                    <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 2 }}>
                      {m.achieved_at ? new Date(m.achieved_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "—"}
                      &nbsp;·&nbsp; {m.category}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </ResearchLayout>
  );
}

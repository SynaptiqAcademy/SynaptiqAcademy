import React, { useState, useEffect, useCallback } from "react";
import { Clock, CheckSquare } from "lucide-react";
import { NAVY, WARM, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Tag, StatCard, StatGrid, Spinner } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const TYPE_COLOR = {
  writing: ACCENT, literature_review: "#8b5cf6", data_collection: "#0ea5e9",
  submission: EMERALD, revision: "#f97316", conference: "#f59e0b",
  grant_application: "#ec4899", collaboration: "#14b8a6", analysis: NAVY,
  admin: "#94a3b8", teaching: "#a78bfa", other: "#cbd5e1",
};

function DayCard({ day }) {
  const totalH = day.total_hours || 0;
  return (
    <Card padding="none" style={{ overflow: "hidden" }}>
      <Card.Header style={{ margin: 0, padding: "10px 14px", background: WARM }}>
        <div style={{ fontSize: 13, fontWeight: 800, color: NAVY }}>{day.weekday}</div>
        <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>{day.date} · {totalH}h planned</div>
      </Card.Header>
      <div style={{ padding: 12, minHeight: 80 }}>
        {(day.missions || []).length === 0 ? (
          <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: 0 }}>Free day</p>
        ) : (
          (day.missions || []).map((m, i) => {
            const color = TYPE_COLOR[m.type] || "#94a3b8";
            return (
              <div key={i} style={{ display: "flex", gap: 6, marginBottom: 6, alignItems: "center" }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0 }} />
                <span style={{ fontSize: 12, color: NAVY, fontWeight: 500, flex: 1 }}>{m.title}</span>
                <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>{m.hours}h</span>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}

export default function WeeklyPlanner() {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/sie/agenda/weekly`, { headers: authH() });
      if (r.ok) setPlan(await r.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const refresh = async () => {
    setRefreshing(true);
    try {
      const r = await fetch(`${API}/api/sie/agenda/weekly/refresh`, { method: "POST", headers: authH() });
      if (r.ok) setPlan(await r.json());
    } catch (_) {}
    setRefreshing(false);
  };

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={32} color={ACCENT} />
    </div>
  );

  return (
    <AIWorkspaceLayout
      title="Weekly Planner"
      subtitle="Weekly view of missions, goals, and research commitments."
      navItems={SIE_NAV_ITEMS}
    >

      {/* Weekly goals */}
      {(plan?.weekly_goals || []).length > 0 && (
        <Card padding="none" style={{ padding: "14px 18px", marginBottom: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: ACCENT, letterSpacing: "0.05em", marginBottom: 8 }}>WEEKLY GOALS</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {(plan.weekly_goals || []).map((g, i) => <Tag key={i} color={ACCENT}>{g}</Tag>)}
          </div>
          {plan.ai_focus && <p style={{ margin: "10px 0 0", fontSize: 12, color: TEXT_SECONDARY, fontStyle: "italic" }}>{plan.ai_focus}</p>}
        </Card>
      )}

      {/* Days grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
        {(plan?.days || []).map((day, i) => <DayCard key={i} day={day} />)}
      </div>

      {/* Stats */}
      <div style={{ marginTop: 16 }}>
        <StatGrid cols={3}>
          <StatCard label="Total Missions" value={plan?.total_missions ?? 0} icon={<CheckSquare />} />
          <StatCard label="Hours Planned" value={`${plan?.estimated_hours_total ?? 0}h`} icon={<Clock />} />
          <StatCard label="Completed This Week" value={plan?.completed_this_week ?? 0} icon={<CheckSquare />} />
        </StatGrid>
      </div>
    </AIWorkspaceLayout>
  );
}

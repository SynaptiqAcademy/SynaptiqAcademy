import React, { useState, useEffect, useCallback } from "react";
import { Calendar, Zap, AlertTriangle, CheckSquare, Sparkles, Target } from "lucide-react";
import { NAVY, WARM, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Badge, StatCard, StatGrid, EmptyState, LoadingOverlay, H4 } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const CATEGORY_ICON = {
  mission: CheckSquare,
  deadline: AlertTriangle,
  recommendation: Sparkles,
  goal: Target,
};
const CATEGORY_COLOR = {
  mission: ACCENT,
  deadline: "#dc2626",
  recommendation: "#8b5cf6",
  goal: "#f59e0b",
};

function AgendaItem({ item }) {
  const Icon = CATEGORY_ICON[item.category] || Zap;
  const color = CATEGORY_COLOR[item.category] || ACCENT;
  return (
    <Card accent={color} padding="md" style={{ marginBottom: 8, display: "flex", gap: 12, alignItems: "flex-start" }}>
      <div style={{ width: 32, height: 32, borderRadius: "50%", background: `${color}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <Icon size={15} color={color} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: NAVY, marginBottom: 2 }}>{item.title}</div>
        <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{item.description}</div>
      </div>
      <div style={{ flexShrink: 0 }}>
        <Badge color={color} size="sm">P{item.priority}</Badge>
      </div>
    </Card>
  );
}

export default function DailyAgenda() {
  const [agenda, setAgenda] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/sie/agenda/daily`, { headers: authH() });
      if (r.ok) setAgenda(await r.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const refresh = async () => {
    setRefreshing(true);
    try {
      const r = await fetch(`${API}/api/sie/agenda/daily/refresh`, { method: "POST", headers: authH() });
      if (r.ok) setAgenda(await r.json());
    } catch (_) {}
    setRefreshing(false);
  };

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <LoadingOverlay text={null} />
    </div>
  );

  return (
    <AIWorkspaceLayout
      title="Daily Agenda"
      subtitle="Your AI-generated daily research schedule and priorities."
      navItems={SIE_NAV_ITEMS}
    >

      {/* Stats strip */}
      <div style={{ marginBottom: 20 }}>
        <StatGrid cols={3}>
          {[
            { label: "Active Goals", value: agenda?.active_goals ?? 0 },
            { label: "Pending Missions", value: agenda?.pending_missions ?? 0 },
            { label: "Upcoming Deadlines", value: agenda?.upcoming_deadlines ?? 0 },
          ].map(({ label, value }) => (
            <StatCard key={label} label={label} value={value} />
          ))}
        </StatGrid>
      </div>

      {/* Today's priorities */}
      <Card padding="none" style={{ marginBottom: 20, overflow: "hidden" }}>
        <Card.Header style={{ margin: 0, padding: "12px 16px", background: WARM }}>
          <H4>Today's Priorities</H4>
        </Card.Header>
        <div style={{ padding: 16 }}>
          {(agenda?.priorities || []).length === 0 ? (
            <EmptyState
              icon={<Calendar />}
              title="No priorities today"
              description="Set goals and missions to get your daily AI agenda."
              size="sm"
            />
          ) : (
            (agenda?.priorities || []).map((item, i) => <AgendaItem key={i} item={item} />)
          )}
        </div>
      </Card>

      {/* AI Recommendations */}
      {(agenda?.ai_recommendations || []).length > 0 && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
            <Sparkles size={15} color={ACCENT} />
            <H4>AI Recommendations</H4>
          </div>
          {(agenda.ai_recommendations || []).map((rec, i) => (
            <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6 }}>
              <span style={{ color: ACCENT, fontSize: 14 }}>→</span>
              <span style={{ fontSize: 13, color: "#334155" }}>{rec}</span>
            </div>
          ))}
        </Card>
      )}
    </AIWorkspaceLayout>
  );
}

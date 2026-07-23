import React, { useState, useEffect, useCallback } from "react";
import { Sparkles, RefreshCw, X, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Badge, Tag, Button, Spinner, EmptyState, TypeSectionLabel } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const CATEGORY_COLORS = {
  research_ideas: ACCENT,
  collaborations: "#14b8a6",
  grants: "#ec4899",
  journals: "#8b5cf6",
  conferences: "#f59e0b",
  career_actions: "#f97316",
  ai_tools: NAVY,
  publication_improvements: EMERALD,
  training: "#0ea5e9",
  datasets: "#64748b",
};

const CATEGORIES = [
  "all", "research_ideas", "collaborations", "grants", "journals", "conferences",
  "career_actions", "ai_tools", "publication_improvements", "training",
];

function RecCard({ rec, onDismiss }) {
  const navigate = useNavigate();
  const color = CATEGORY_COLORS[rec.category] || ACCENT;
  return (
    <Card padding="md" style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
      <div style={{ width: 36, height: 36, borderRadius: 10, background: `${color}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <Sparkles size={16} color={color} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 3 }}>
          <div>
            <TypeSectionLabel color={color} style={{ fontSize: 10 }}>{rec.category?.replace(/_/g, " ")}</TypeSectionLabel>
            <div style={{ fontSize: 13, fontWeight: 700, color: NAVY }}>{rec.title}</div>
          </div>
          <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <Badge color={color} size="sm">P{rec.priority}</Badge>
            {/* Dismiss control: bare 13px icon-only button — Button's smallest
                ("icon", 36px) size would visually overpower this compact card
                row, so it's left hand-rolled */}
            <Button
              size="icon"
              variant="ghost"
              onClick={() => onDismiss(rec.id)}
              style={{
                padding: 2
              }}>
              <X size={13} color={TEXT_SECONDARY} />
            </Button>
          </div>
        </div>
        <p style={{ margin: "0 0 8px", fontSize: 12, color: "#334155" }}>{rec.description}</p>
        {rec.action_url && (
          <Button
            onClick={() => navigate(rec.action_url)}
            variant="outline"
            size="sm"
            style={{ color, borderColor: `${color}30` }}
          >
            Open in Synaptiq <ArrowRight size={11} />
          </Button>
        )}
      </div>
    </Card>
  );
}

export default function Recommendations() {
  const [recs, setRecs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [category, setCategory] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const url = category !== "all" ? `${API}/api/sie/recommendations?category=${category}` : `${API}/api/sie/recommendations`;
      const r = await fetch(url, { headers: authH() });
      if (r.ok) setRecs(await r.json());
    } catch (_) {}
    setLoading(false);
  }, [category]);

  useEffect(() => { load(); }, [load]);

  const refresh = async () => {
    setRefreshing(true);
    try {
      await fetch(`${API}/api/sie/recommendations/refresh`, { method: "POST", headers: authH() });
      load();
    } catch (_) {}
    setRefreshing(false);
  };

  const dismiss = async (id) => {
    await fetch(`${API}/api/sie/recommendations/${id}/dismiss`, { method: "POST", headers: authH() });
    setRecs(rs => rs.filter(r => r.id !== id));
  };

  return (
    <AIWorkspaceLayout
      title="AI Recommendations"
      subtitle={`${recs.length} active recommendations personalised to your research profile.`}
      navItems={SIE_NAV_ITEMS}
      actions={
        <Button onClick={refresh} loading={refreshing} disabled={refreshing} variant="primary" size="sm" style={{ background: "#0F2847" }}>
          {!refreshing && <RefreshCw size={13} />}
          Refresh
        </Button>
      }
    >
      {/* Category filter */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16, overflowX: "auto", paddingBottom: 4 }}>
        {CATEGORIES.map(c => {
          const color = CATEGORY_COLORS[c] || ACCENT;
          const active = category === c;
          return (
            <Tag key={c} variant={active ? "active" : "default"} color={active ? color : undefined} onClick={() => setCategory(c)}>
              {c === "all" ? "All" : c.replace(/_/g, " ")}
            </Tag>
          );
        })}
      </div>
      {loading ? (
        <div style={{ textAlign: "center", padding: 40 }}><Spinner size={28} color={ACCENT} /></div>
      ) : recs.length === 0 ? (
        <EmptyState
          icon={<Sparkles />}
          title="No recommendations in this category"
          description="Click Refresh to generate new ones."
          action={
            <Button onClick={refresh} style={{ background: "#8b5cf6" }}>
              Generate Recommendations
            </Button>
          }
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {recs.map(r => <RecCard key={r.id} rec={r} onDismiss={dismiss} />)}
        </div>
      )}
    </AIWorkspaceLayout>
  );
}

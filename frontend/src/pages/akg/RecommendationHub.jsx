/* eslint-disable */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Lightbulb, RefreshCw, Users, Building2, Tag, Cpu, ShoppingBag, BookOpen } from "lucide-react";
import { NAVY, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Button, Badge, Tag as ChipTag, EmptyState, LoadingOverlay } from "@/components/ds";

const API = (p) => `/api/akg${p}`;

const CATEGORY_META = {
  people:        { label: "People",          icon: Users,       color: "#3b82f6" },
  institutions:  { label: "Institutions",    icon: Building2,   color: "#d97706" },
  topics:        { label: "Research Topics", icon: Tag,         color: "#059669" },
  methods:       { label: "Methods",         icon: Cpu,         color: "#7c3aed" },
  software:      { label: "Software",        icon: Cpu,         color: "#0891b2" },
  communities:   { label: "Communities",     icon: Users,       color: "#ec4899" },
  marketplace:   { label: "Marketplace",     icon: ShoppingBag, color: "#8b5cf6" },
};

const RecCard = ({ item, color, onView }) => (
  <Card onClick={onView}>
    <div style={{ fontWeight: 600, color: NAVY, marginBottom: 4 }}>{item.label}</div>
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      {item.entity_type && (
        <Badge color={color}>{item.entity_type.replace(/_/g, " ")}</Badge>
      )}
      {item.rec_score !== undefined && (
        <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>Match: {(item.rec_score * 100).toFixed(0)}%</span>
      )}
    </div>
    {item.properties?.description && (
      <p style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 6, lineHeight: 1.5, margin: "6px 0 0" }}>
        {item.properties.description.substring(0, 100)}
      </p>
    )}
  </Card>
);

export default function RecommendationHub() {
  const nav = useNavigate();
  const [recs, setRecs] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeCategory, setActiveCategory] = useState("people");

  const loadRecs = async () => {
    setLoading(true);
    const data = await fetch(API("/me/recommendations")).then(r => r.json()).catch(() => null);
    setRecs(data?.recommendations || data || null);
    setLoading(false);
  };

  const refresh = async () => {
    setRefreshing(true);
    await fetch(API("/me/recommendations"), { method: "POST" }).catch(() => {});
    setTimeout(async () => {
      await loadRecs();
      setRefreshing(false);
    }, 1500);
  };

  useEffect(() => { loadRecs(); }, []);

  const categories = Object.entries(CATEGORY_META);
  const currentItems = recs?.[activeCategory] || [];
  const meta = CATEGORY_META[activeCategory] || {};
  const Icon = meta.icon || Lightbulb;

  return (
    <ResearchLayout
      title="Graph Recommendations"
      subtitle="Algorithmic recommendations powered by your knowledge graph neighborhood. No LLM."
      icon={<Lightbulb size={22} color={ACCENT} />}
      actions={
        <Button variant="outline" onClick={refresh} disabled={refreshing} loading={refreshing}>
          {!refreshing && <RefreshCw size={14} />}
          {refreshing ? "Refreshing…" : "Refresh"}
        </Button>
      }
    >

      <div style={{ display: "flex", gap: 8, marginBottom: 24, flexWrap: "wrap" }}>
        {categories.map(([key, m]) => {
          const I = m.icon;
          const active = activeCategory === key;
          const count = recs?.[key]?.length || 0;
          return (
            <ChipTag key={key} onClick={() => setActiveCategory(key)} color={active ? m.color : undefined} size="lg">
              <I size={14} />
              {m.label}
              {count > 0 && <Badge size="sm" color={active ? m.color : undefined} variant={active ? undefined : "neutral"}>{count}</Badge>}
            </ChipTag>
          );
        })}
      </div>

      {loading ? (
        <LoadingOverlay text="Loading recommendations…" />
      ) : currentItems.length === 0 ? (
        <EmptyState
          icon={<Icon />}
          title={`No ${meta.label?.toLowerCase()} recommendations yet.`}
          description={<>Your recommendations improve as the graph syncs more data. <Button as="span" variant="link" onClick={refresh}>Trigger a refresh.</Button></>}
          size="lg"
        />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {currentItems.map((item, i) => (
            <RecCard key={i} item={item} color={meta.color || ACCENT}
              onView={() => item.entity_id && nav(`/akg/entity/${item.entity_id}`)} />
          ))}
        </div>
      )}
    </ResearchLayout>
  );
}

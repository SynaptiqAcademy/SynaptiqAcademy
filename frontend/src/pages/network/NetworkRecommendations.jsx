import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { Brain, RefreshCw, X, ArrowRight, Loader } from "lucide-react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import { Card, Badge, Tag, Button, EmptyState, LoadingOverlay } from "@/components/ds";

const CAT_COLOR = {
  collaborator: ACCENT, institution: "#0ea5e9", community: "#f97316",
  group: "#8b5cf6", event: "#06b6d4", collaboration: EMERALD,
  mentor: "#ec4899", conference: NAVY, dataset: "#7c3aed", software: "#059669",
};
const CAT_LABEL = {
  collaborator: "Collaborator", institution: "Institution", community: "Community",
  group: "Research Group", event: "Event", collaboration: "Open Collab",
  mentor: "Mentor", conference: "Conference", dataset: "Dataset", software: "Software",
};

function RecCard({ rec, onDismiss }) {
  const color = CAT_COLOR[rec.category] || ACCENT;
  return (
    <Card accent={color} padding="md">
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 4 }}>
            <Badge color={color} size="sm">{CAT_LABEL[rec.category] || rec.category}</Badge>
          </div>
          <div style={{ fontWeight: 700, fontSize: 14, color: NAVY }}>{rec.title}</div>
          {rec.description && <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 4, lineHeight: 1.5 }}>{rec.description}</div>}
        </div>
        <div style={{ display: "flex", gap: 6, flexShrink: 0, flexDirection: "column" }}>
          <Button variant="subtle" size="sm" onClick={() => onDismiss(rec.id)}>
            <X size={12} />
          </Button>
        </div>
      </div>
      {rec.action_url && (
        <a href={rec.action_url} style={{ display: "inline-flex", alignItems: "center", gap: 4, marginTop: 10, fontSize: 12, fontWeight: 700, color, textDecoration: "none" }}>
          Open in Synaptiq <ArrowRight size={11} />
        </a>
      )}
    </Card>
  );
}

export default function NetworkRecommendations() {
  const [recs, setRecs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [catFilter, setCatFilter] = useState("");

  const fetchRecs = useCallback(async () => {
    setLoading(true);
    try {
      const params = catFilter ? { category: catFilter } : {};
      const r = await axios.get("/api/network/recommendations", { params });
      setRecs(r.data || []);
    } catch { } finally { setLoading(false); }
  }, [catFilter]);

  useEffect(() => { fetchRecs(); }, [fetchRecs]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await axios.post("/api/network/recommendations/generate");
      setTimeout(() => { setGenerating(false); fetchRecs(); }, 2500);
    } catch { setGenerating(false); }
  };

  const handleDismiss = async id => {
    await axios.post(`/api/network/recommendations/${id}/dismiss`);
    setRecs(r => r.filter(x => x.id !== id));
  };

  const categories = Object.keys(CAT_LABEL);
  const visible = recs.filter(r => !r.dismissed);

  return (
    <DiscoveryLayout
      title="AI Recommendations"
      subtitle="Personalised recommendations based on your research profile. Every recommendation is explained."
      icon={<Brain size={22} color={NAVY} />}
      actions={
        <Button variant="subtle" onClick={handleGenerate} disabled={generating}>
          {generating ? <Loader size={14} className="spin" /> : <RefreshCw size={14} />}
          {generating ? "Generating…" : "Refresh"}
        </Button>
      }
      filters={
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <Tag color={!catFilter ? ACCENT : undefined} onClick={() => setCatFilter("")}>
            All
          </Tag>
          {categories.map(c => (
            <Tag key={c} color={catFilter === c ? CAT_COLOR[c] : undefined} onClick={() => setCatFilter(c)}>
              {CAT_LABEL[c]}
            </Tag>
          ))}
        </div>
      }
    >
      {loading ? (
        <LoadingOverlay text="Loading…" />
      ) : generating ? (
        <Card padding="lg" style={{ background: `${ACCENT}08`, borderColor: `${ACCENT}30`, textAlign: "center" }}>
          <Brain size={28} color={ACCENT} style={{ marginBottom: 10 }} />
          <div style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 4 }}>Generating recommendations…</div>
          <div style={{ fontSize: 13, color: TEXT_SECONDARY }}>Analysing your research profile and platform data.</div>
        </Card>
      ) : visible.length === 0 ? (
        <EmptyState
          icon={<Brain />}
          title="No recommendations yet"
          description="Generate personalised recommendations based on your research profile."
          action={<Button variant="primary" onClick={handleGenerate}>Generate Recommendations</Button>}
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {visible.map((rec, i) => <RecCard key={rec.id || i} rec={rec} onDismiss={handleDismiss} />)}
        </div>
      )}
    </DiscoveryLayout>
  );
}

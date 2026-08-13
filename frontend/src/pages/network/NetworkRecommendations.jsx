import React, { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { Brain, RefreshCw, X, ArrowRight, Loader } from "lucide-react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
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
          <Button variant="subtle" size="sm" onClick={() => onDismiss(rec.id)} aria-label="Dismiss recommendation">
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
      const r = await api.get("/network/recommendations", { params });
      setRecs(r.data || []);
    } catch { } finally { setLoading(false); }
  }, [catFilter]);

  useEffect(() => { fetchRecs(); }, [fetchRecs]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await api.post("/network/recommendations/generate");
      setTimeout(() => { setGenerating(false); fetchRecs(); }, 2500);
    } catch { setGenerating(false); }
  };

  const handleDismiss = async id => {
    await api.post(`/network/recommendations/${id}/dismiss`);
    setRecs(r => r.filter(x => x.id !== id));
  };

  const categories = Object.keys(CAT_LABEL);
  const visible = recs.filter(r => !r.dismissed);

  return (
    <ResearchLayout
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
      sidebar={visible.length > 0 ? <NetworkRecommendationsSidebar recs={visible} /> : undefined}
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
    </ResearchLayout>
  );
}

// ── Right rail — breakdown of the recommendations already loaded by this page ──
function NetworkRecommendationsSidebar({ recs }) {
  const byCategory = recs.reduce((acc, r) => {
    acc[r.category] = (acc[r.category] || 0) + 1;
    return acc;
  }, {});
  const entries = Object.entries(byCategory).sort((a, b) => b[1] - a[1]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Brain size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Active Recommendations</div>
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 28, fontWeight: 700, color: "#0f172a" }}>{recs.length}</div>
        <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0", lineHeight: 1.5 }}>
          Personalised suggestions currently on your list.
        </p>
      </Card>

      <Card padding="lg">
        <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>By Category</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {entries.map(([cat, count]) => (
            <div key={cat} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 12 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6, color: "#374151" }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: CAT_COLOR[cat] || ACCENT, flexShrink: 0 }} />
                {CAT_LABEL[cat] || cat}
              </span>
              <span style={{ fontWeight: 700, color: NAVY }}>{count}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { Bookmark, Trash2, FileText, Building2, Layers, MessageSquare, Handshake, Calendar } from "lucide-react";
import { NAVY, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Tag, Button, EmptyState, LoadingOverlay } from "@/components/ds";

const TYPE_META = {
  person:        { label: "Researcher",  icon: FileText,      color: ACCENT },
  institution:   { label: "Institution", icon: Building2,     color: "#0ea5e9" },
  group:         { label: "Group",       icon: Layers,        color: "#8b5cf6" },
  community:     { label: "Community",   icon: MessageSquare, color: "#f97316" },
  collaboration: { label: "Collaboration", icon: Handshake,   color: "#059669" },
  event:         { label: "Event",       icon: Calendar,      color: "#06b6d4" },
  grant:         { label: "Grant",       icon: FileText,      color: "#ec4899" },
  project:       { label: "Project",     icon: Layers,        color: NAVY },
};

function SavedCard({ item, onUnsave }) {
  const meta = TYPE_META[item.item_type] || { label: item.item_type, icon: Bookmark, color: ACCENT };
  const Icon = meta.icon;
  return (
    <Card padding="md" style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
      <div style={{ width: 38, height: 38, borderRadius: 10, background: `${meta.color}12`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <Icon size={18} color={meta.color} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ fontWeight: 700, fontSize: 13, color: NAVY }}>{item.title || "Saved Item"}</span>
          <Badge color={meta.color} size="sm">{meta.label}</Badge>
        </div>
        {item.description && <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 2 }}>{item.description}</div>}
        {item.notes && <div style={{ fontSize: 12, color: ACCENT, marginTop: 4, fontStyle: "italic" }}>Note: {item.notes}</div>}
        <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 4 }}>Saved {item.saved_at?.slice(0, 10)}</div>
      </div>
      <Button variant="ghost" size="sm" onClick={() => onUnsave(item)}>
        <Trash2 size={15} />
      </Button>
    </Card>
  );
}

export default function SavedOpportunities() {
  const [saved, setSaved] = useState({ items: [], by_type: {}, total: 0 });
  const [loading, setLoading] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");

  const fetchSaved = useCallback(async () => {
    setLoading(true);
    try {
      const params = typeFilter ? { item_type: typeFilter } : {};
      const r = await axios.get("/api/network/saved", { params });
      setSaved(r.data || { items: [], by_type: {}, total: 0 });
    } catch { } finally { setLoading(false); }
  }, [typeFilter]);

  useEffect(() => { fetchSaved(); }, [fetchSaved]);

  const handleUnsave = async item => {
    await axios.delete("/api/network/saved", { data: { item_type: item.item_type, item_id: item.item_id } });
    fetchSaved();
  };

  const types = Object.keys(saved.by_type || {});
  const items = saved.items || [];
  const visible = typeFilter ? items.filter(i => i.item_type === typeFilter) : items;

  return (
    <ResearchLayout
      title="Saved Opportunities"
      subtitle="Save researchers, institutions, collaborations, events, and grants for later review."
    >

      {types.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 16 }}>
          <Tag color={!typeFilter ? ACCENT : undefined} onClick={() => setTypeFilter("")}>
            All ({saved.total})
          </Tag>
          {types.map(t => {
            const count = (saved.by_type[t] || []).length;
            const meta = TYPE_META[t] || {};
            return (
              <Tag key={t} color={typeFilter === t ? (meta.color || ACCENT) : undefined} onClick={() => setTypeFilter(t)}>
                {meta.label || t} ({count})
              </Tag>
            );
          })}
        </div>
      )}

      {loading ? (
        <LoadingOverlay text="Loading…" />
      ) : visible.length === 0 ? (
        <EmptyState
          icon={<Bookmark />}
          title="No saved items yet"
          description="Bookmark researchers, collaborations, institutions, and events from any part of the network."
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {visible.map((item, i) => <SavedCard key={item.id || i} item={item} onUnsave={handleUnsave} />)}
        </div>
      )}
    </ResearchLayout>
  );
}

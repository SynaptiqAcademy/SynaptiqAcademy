import React, { useState, useEffect } from "react";
import axios from "axios";
import { Radio, Plus, BookOpen, Trophy, Handshake, Calendar, Star, Layers, Megaphone, Globe } from "lucide-react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Button, Input, Textarea, FormSelect, Modal, NavTabs, EmptyState, LoadingOverlay } from "@/components/ds";

const TYPE_META = {
  publication_added:       { label: "Publication",        icon: BookOpen,    color: ACCENT },
  grant_awarded:           { label: "Grant Awarded",      icon: Trophy,      color: "#f59e0b" },
  collaboration_started:   { label: "Collaboration",      icon: Handshake,   color: EMERALD },
  conference_accepted:     { label: "Conference",         icon: Calendar,    color: "#06b6d4" },
  review_completed:        { label: "Review",             icon: Star,        color: "#8b5cf6" },
  project_launched:        { label: "Project",            icon: Layers,      color: "#f97316" },
  community_announcement:  { label: "Announcement",       icon: Megaphone,   color: "#ec4899" },
  group_created:           { label: "Group Created",      icon: Layers,      color: NAVY },
  event_created:           { label: "Event",              icon: Calendar,    color: "#0ea5e9" },
  mentorship_started:      { label: "Mentorship",         icon: Star,        color: EMERALD },
  collaboration_opportunity:{ label: "Opportunity",       icon: Handshake,   color: ACCENT },
  open_access_published:   { label: "Open Access",        icon: Globe,       color: EMERALD },
  dataset_released:        { label: "Dataset",            icon: BookOpen,    color: "#7c3aed" },
  award_received:          { label: "Award",              icon: Trophy,      color: "#f59e0b" },
  position_started:        { label: "New Position",       icon: Star,        color: NAVY },
};

const ACTIVITY_TYPES = Object.keys(TYPE_META);

function ActivityItem({ item }) {
  const meta = TYPE_META[item.type] || { label: item.type, icon: Radio, color: TEXT_SECONDARY };
  const Icon = meta.icon;
  return (
    <Card accent={meta.color} padding="md" style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
      <div style={{ width: 38, height: 38, borderRadius: 10, background: `${meta.color}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <Icon size={18} color={meta.color} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontWeight: 700, fontSize: 13, color: NAVY }}>{item.title || meta.label}</span>
          <Badge color={meta.color} size="sm">{meta.label}</Badge>
        </div>
        {(item.author_name || item.author_institution) && (
          <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 2 }}>{item.author_name}{item.author_institution ? ` · ${item.author_institution}` : ""}</div>
        )}
        {item.description && <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 4, lineHeight: 1.5 }}>{item.description}</div>}
        <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 6 }}>{item.created_at?.slice(0, 10)}</div>
      </div>
      {item.priority_score >= 9 && (
        // Small floating corner indicator dot, not a semantic badge — Badge's `dot`
        // renders inline-before-content, not a standalone positioned marker, so this
        // stays hand-rolled.
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: ACCENT, flexShrink: 0, marginTop: 6 }} title="High importance" />
      )}
    </Card>
  );
}

function PostActivityModal({ onClose, onSuccess }) {
  const [form, setForm] = useState({ type: "publication_added", title: "", description: "", visibility: "public" });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try { await axios.post("/api/network/activity", form); onSuccess(); onClose(); }
    catch { setSaving(false); }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Share Academic Update"
      description="Share relevant academic events only — no likes, no vanity metrics. Prioritise research value."
      size="sm"
      footer={
        <Button variant="primary" onClick={handleSubmit} disabled={saving || !form.title.trim()} loading={saving} style={{ width: "100%" }}>
          {saving ? "Posting…" : "Share Update"}
        </Button>
      }
    >
      <FormSelect
        label="Activity Type"
        value={form.type}
        onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
      >
        {ACTIVITY_TYPES.map(t => <option key={t} value={t}>{TYPE_META[t]?.label || t}</option>)}
      </FormSelect>
      <Input
        label="Title *"
        value={form.title}
        onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
        placeholder="E.g. Published in Nature Medicine"
      />
      <Textarea
        label="Description"
        value={form.description}
        onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
        rows={3}
      />
    </Modal>
  );
}

export default function ActivityCenter() {
  const [feed, setFeed] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState("feed");
  const [myActivity, setMyActivity] = useState([]);
  const [showPost, setShowPost] = useState(false);

  const fetchFeed = async (pg = 1) => {
    setLoading(true);
    try {
      const r = await axios.get("/api/network/activity", { params: { page: pg, limit: 30 } });
      setFeed(r.data.results || []);
      setTotal(r.data.total || 0);
    } catch { } finally { setLoading(false); }
  };

  const fetchMyActivity = async () => {
    try { const r = await axios.get("/api/network/activity/mine"); setMyActivity(r.data.results || []); } catch { }
  };

  useEffect(() => { fetchFeed(); fetchMyActivity(); }, []);

  return (
    <ResearchLayout
      title="Activity Center"
      subtitle="Professional academic events only. No likes, no engagement metrics. Sorted by academic relevance."
      actions={<Button variant="primary" onClick={() => setShowPost(true)}><Plus size={15} />Share Update</Button>}
    >

      <div style={{ marginBottom: 16 }}>
        <NavTabs
          variant="pill"
          tabs={[
            { id: "feed", label: "Academic Feed" },
            { id: "mine", label: "My Activity", count: myActivity.length },
          ]}
          active={tab}
          onChange={setTab}
        />
      </div>

      {tab === "feed" && (
        <>
          {loading ? <LoadingOverlay text="Loading feed…" /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {feed.length === 0 ? (
                <EmptyState title="No activity yet" description="Researchers on the platform will share academic updates here." />
              ) : feed.map((item, i) => <ActivityItem key={item.id || i} item={item} />)}
            </div>
          )}
        </>
      )}

      {tab === "mine" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {myActivity.length === 0 ? (
            <EmptyState title="You haven't shared any updates yet" />
          ) : myActivity.map((item, i) => <ActivityItem key={item.id || i} item={item} />)}
        </div>
      )}

      {showPost && <PostActivityModal onClose={() => setShowPost(false)} onSuccess={() => { fetchFeed(); fetchMyActivity(); }} />}
    </ResearchLayout>
  );
}

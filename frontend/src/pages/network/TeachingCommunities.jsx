import React, { useState, useEffect } from "react";
import axios from "axios";
import { BookOpen, Plus, Users } from "lucide-react";
import { NAVY, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import { Card, Button, Input, Textarea, Modal, EmptyState, LoadingOverlay } from "@/components/ds";

export default function TeachingCommunities() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", discipline: "", visibility: "public" });
  const [saving, setSaving] = useState(false);

  const fetchGroups = async () => {
    setLoading(true);
    try {
      const r = await axios.get("/api/network/groups", { params: { type: "teaching_community", limit: 30 } });
      setGroups(r.data.results || []);
    } catch { } finally { setLoading(false); }
  };

  useEffect(() => { fetchGroups(); }, []);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      await axios.post("/api/network/groups", { ...form, type: "teaching_community" });
      fetchGroups(); setShowCreate(false); setForm({ name: "", description: "", discipline: "", visibility: "public" });
    } catch { } finally { setSaving(false); }
  };

  const handleJoin = async id => { await axios.post(`/api/network/groups/${id}/join`); fetchGroups(); };
  const handleLeave = async id => { await axios.post(`/api/network/groups/${id}/leave`); fetchGroups(); };

  return (
    <DiscoveryLayout
      title="Teaching Communities"
      subtitle="Collaborative spaces for educators — share pedagogy, resources, and teaching strategies."
      actions={<Button variant="primary" onClick={() => setShowCreate(true)}><Plus size={15} />Create</Button>}
    >

      {loading ? <LoadingOverlay text="Loading…" /> : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {groups.length === 0 ? (
            <EmptyState
              icon={<BookOpen />}
              title="No teaching communities yet"
              description="Start the first teaching community for your discipline."
              action={<Button variant="primary" onClick={() => setShowCreate(true)}>Create Teaching Community</Button>}
            />
          ) : groups.map((g, i) => (
            <Card key={i} padding="md" style={{ display: "flex", gap: 12 }}>
              <div style={{ width: 44, height: 44, borderRadius: 12, background: `${EMERALD}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <BookOpen size={20} color={EMERALD} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 14, color: NAVY }}>{g.name}</div>
                {g.discipline && <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{g.discipline}</div>}
                {g.description && <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 4, lineHeight: 1.5 }}>{g.description.slice(0, 80)}{g.description.length > 80 ? "…" : ""}</div>}
                <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 6, display: "flex", alignItems: "center", gap: 4 }}>
                  <Users size={11} />{g.member_count || 0} members
                </div>
              </div>
              {g.is_member ? (
                <Button variant="subtle" size="sm" onClick={() => handleLeave(g.id)} style={{ alignSelf: "flex-start" }}>Leave</Button>
              ) : (
                <Button variant="primary" size="sm" onClick={() => handleJoin(g.id)} style={{ alignSelf: "flex-start" }}>Join</Button>
              )}
            </Card>
          ))}
        </div>
      )}

      {showCreate && (
        <Modal
          open
          onClose={() => setShowCreate(false)}
          title="Create Teaching Community"
          size="sm"
          footer={
            <Button variant="primary" onClick={handleCreate} disabled={saving} loading={saving} style={{ width: "100%" }}>
              {saving ? "Creating…" : "Create"}
            </Button>
          }
        >
          <Input
            label="Name *"
            value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          />
          <Input
            label="Discipline"
            value={form.discipline}
            onChange={e => setForm(f => ({ ...f, discipline: e.target.value }))}
          />
          <Textarea
            label="Description"
            value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            rows={2}
          />
        </Modal>
      )}
    </DiscoveryLayout>
  );
}

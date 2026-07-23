import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { Plus, Users, Search, Lock } from "lucide-react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import { Card, Badge, Button, Input, Textarea, FormSelect, FormRow, Modal, NavTabs, EmptyState, LoadingOverlay } from "@/components/ds";

const TYPE_COLOR = {
  research_group: ACCENT, research_lab: "#8b5cf6", center_of_excellence: "#f97316",
  teaching_community: EMERALD, reading_group: "#06b6d4", working_group: NAVY,
  grant_team: "#ec4899", task_force: "#dc2626",
};
const TYPE_LABEL = {
  research_group: "Research Group", research_lab: "Research Lab",
  center_of_excellence: "Centre of Excellence", teaching_community: "Teaching Community",
  reading_group: "Reading Group", working_group: "Working Group",
  grant_team: "Grant Team", task_force: "Task Force",
};

function GroupCard({ group, onJoin, onLeave }) {
  const color = TYPE_COLOR[group.type] || NAVY;
  return (
    <Card padding="md">
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span style={{ fontWeight: 700, fontSize: 14, color: NAVY }}>{group.name}</span>
            <Badge color={color} size="sm">{TYPE_LABEL[group.type] || group.type}</Badge>
            {group.visibility === "private" && <Lock size={11} color={TEXT_SECONDARY} />}
          </div>
          {group.discipline && <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 2 }}>{group.discipline}</div>}
          {group.description && (
            <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 6, lineHeight: 1.5 }}>
              {group.description.slice(0, 100)}{group.description.length > 100 ? "…" : ""}
            </div>
          )}
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 10 }}>
            <span style={{ fontSize: 12, color: TEXT_SECONDARY, display: "flex", alignItems: "center", gap: 4 }}>
              <Users size={12} />{group.member_count || 0} members
            </span>
          </div>
        </div>
        <div style={{ flexShrink: 0 }}>
          {group.is_member ? (
            <Button variant="subtle" size="sm" onClick={() => onLeave(group.id)}>
              Leave
            </Button>
          ) : (
            <Button variant="primary" size="sm" onClick={() => onJoin(group.id)}>
              Join
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}

function CreateModal({ onClose, onCreate }) {
  const [form, setForm] = useState({ name: "", description: "", type: "research_group", discipline: "", visibility: "public" });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      await axios.post("/api/network/groups", form);
      onCreate();
      onClose();
    } catch { setSaving(false); }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Create Group"
      size="sm"
      footer={
        <Button variant="primary" onClick={handleSubmit} disabled={saving} loading={saving} style={{ width: "100%" }}>
          {saving ? "Creating…" : "Create Group"}
        </Button>
      }
    >
      <Input
        label="Group Name *"
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
        rows={3}
      />
      <FormRow cols={2}>
        <FormSelect
          label="Type"
          value={form.type}
          onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
        >
          {Object.entries(TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </FormSelect>
        <FormSelect
          label="Visibility"
          value={form.visibility}
          onChange={e => setForm(f => ({ ...f, visibility: e.target.value }))}
        >
          <option value="public">Public</option>
          <option value="private">Private</option>
        </FormSelect>
      </FormRow>
    </Modal>
  );
}

export default function ResearchGroups() {
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [tab, setTab] = useState("discover");
  const [myGroups, setMyGroups] = useState([]);

  const fetchGroups = useCallback(async () => {
    setLoading(true);
    try {
      const params = { limit: 30 };
      if (q) params.q = q;
      if (typeFilter) params.type = typeFilter;
      const r = await axios.get("/api/network/groups", { params });
      setResults(r.data.results || []);
      setTotal(r.data.total || 0);
    } catch { } finally { setLoading(false); }
  }, [q, typeFilter]);

  const fetchMyGroups = useCallback(async () => {
    try {
      const r = await axios.get("/api/network/groups/mine");
      setMyGroups(r.data || []);
    } catch { }
  }, []);

  const fetchGroupsRef = useRef(fetchGroups);
  useEffect(() => { fetchGroupsRef.current = fetchGroups; }, [fetchGroups]);
  useEffect(() => { fetchGroupsRef.current(); fetchMyGroups(); }, [fetchMyGroups]);

  const handleJoin = async (id) => {
    await axios.post(`/api/network/groups/${id}/join`);
    fetchGroups(); fetchMyGroups();
  };

  const handleLeave = async (id) => {
    await axios.post(`/api/network/groups/${id}/leave`);
    fetchGroups(); fetchMyGroups();
  };

  return (
    <DiscoveryLayout
      title="Research Groups"
      actions={<Button variant="primary" onClick={() => setShowCreate(true)}><Plus size={15} />Create</Button>}
    >

      {/* Tabs */}
      <div style={{ marginBottom: 16 }}>
        <NavTabs
          variant="pill"
          tabs={[
            { id: "discover", label: "Discover" },
            { id: "mine", label: "My Groups", count: myGroups.length },
          ]}
          active={tab}
          onChange={setTab}
        />
      </div>

      {tab === "discover" && (
        <>
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
            <Input
              value={q}
              onChange={e => setQ(e.target.value)}
              onKeyDown={e => e.key === "Enter" && fetchGroups()}
              placeholder="Search groups…"
              prefix={<Search size={14} />}
              style={{ minWidth: 200 }}
              wrapperClassName="flex-1"
            />
            <FormSelect value={typeFilter} onChange={e => { setTypeFilter(e.target.value); }}>
              <option value="">All types</option>
              {Object.entries(TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </FormSelect>
            <Button variant="primary" onClick={fetchGroups}>Search</Button>
          </div>
          {loading ? <LoadingOverlay text="Loading…" /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {results.map((g, i) => <GroupCard key={g.id || i} group={g} onJoin={handleJoin} onLeave={handleLeave} />)}
            </div>
          )}
        </>
      )}

      {tab === "mine" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {myGroups.length === 0 ? (
            <EmptyState title="You haven't joined any groups yet." description="Discover groups or create your own." />
          ) : myGroups.map((g, i) => <GroupCard key={g.id || i} group={{ ...g, is_member: true }} onJoin={handleJoin} onLeave={handleLeave} />)}
        </div>
      )}

      {showCreate && <CreateModal onClose={() => setShowCreate(false)} onCreate={() => { fetchGroups(); fetchMyGroups(); }} />}
    </DiscoveryLayout>
  );
}

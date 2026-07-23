import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { MessageSquare, Plus, Users, ChevronRight, Send } from "lucide-react";
import { NAVY, BRD, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import { Card, Badge, Button, Input, Textarea, FormSelect, Modal, NavTabs, EmptyState, LoadingOverlay } from "@/components/ds";

const TOPIC_COLOR = {
  research_methods: ACCENT, ai_in_research: "#8b5cf6", statistics: "#f97316",
  open_science: EMERALD, peer_review: "#06b6d4", grant_writing: "#ec4899",
  scientific_publishing: NAVY, teaching: "#0ea5e9", innovation: "#dc2626",
  discipline_specific: "#7c3aed", software: "#059669", datasets: "#92400e",
};

function CommunityCard({ c, onJoin, onLeave, onOpen }) {
  const color = TOPIC_COLOR[c.topic] || ACCENT;
  return (
    <Card padding="md">
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <div style={{ width: 44, height: 44, borderRadius: 12, background: `${color}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <MessageSquare size={20} color={color} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: NAVY }}>{c.name}</div>
          <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 3 }}>
            <Badge color={color} size="sm">{c.topic?.replace(/_/g, " ")}</Badge>
            <span style={{ fontSize: 12, color: TEXT_SECONDARY, display: "flex", alignItems: "center", gap: 3 }}>
              <Users size={11} />{c.member_count || 0}
            </span>
            <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>{c.post_count || 0} posts</span>
          </div>
          {c.description && <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 6, lineHeight: 1.5 }}>{c.description.slice(0, 80)}{c.description.length > 80 ? "…" : ""}</div>}
        </div>
        <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
          {c.is_member && (
            <Button variant="subtle" size="sm" onClick={() => onOpen(c)}>
              Open <ChevronRight size={12} />
            </Button>
          )}
          {c.is_member ? (
            <Button variant="subtle" size="sm" onClick={() => onLeave(c.id)}>Leave</Button>
          ) : (
            <Button variant="primary" size="sm" onClick={() => onJoin(c.id)}>Join</Button>
          )}
        </div>
      </div>
    </Card>
  );
}

function CommunityDetail({ community, onClose }) {
  const [posts, setPosts] = useState([]);
  const [form, setForm] = useState({ content: "", title: "", type: "discussion" });
  const [posting, setPosting] = useState(false);

  const fetchPosts = useCallback(async () => {
    try {
      const r = await axios.get(`/api/network/communities/${community.id}/posts`);
      setPosts(r.data.results || []);
    } catch { }
  }, [community.id]);

  useEffect(() => { fetchPosts(); }, [fetchPosts]);

  const handlePost = async () => {
    if (!form.content.trim()) return;
    setPosting(true);
    try {
      await axios.post("/api/network/communities/posts", { ...form, community_id: community.id });
      setForm(f => ({ ...f, content: "", title: "" }));
      fetchPosts();
    } catch { } finally { setPosting(false); }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={community.name}
      size="md"
      footer={
        <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 8 }}>
          <Input
            value={form.title}
            onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            placeholder="Post title (optional)"
          />
          <div style={{ display: "flex", gap: 8 }}>
            <Textarea
              value={form.content}
              onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
              rows={2}
              resize={false}
              placeholder="Share your thoughts, resources, or questions…"
              wrapperClassName="flex-1"
            />
            <Button variant="primary" onClick={handlePost} disabled={posting || !form.content.trim()} loading={posting}>
              <Send size={16} />
            </Button>
          </div>
        </div>
      }
    >
      {posts.length === 0 ? (
        <div style={{ textAlign: "center", color: TEXT_SECONDARY, padding: 20, fontSize: 13 }}>No posts yet. Start the conversation!</div>
      ) : posts.map((p, i) => (
        <div key={i} style={{ marginBottom: 14, borderBottom: i < posts.length - 1 ? `1px solid ${BRD}` : "none", paddingBottom: 14 }}>
          {p.title && <div style={{ fontWeight: 700, fontSize: 13, color: NAVY, marginBottom: 4 }}>{p.title}</div>}
          <div style={{ fontSize: 13, color: "#334155", lineHeight: 1.6 }}>{p.content}</div>
          <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 6 }}>{p.created_at?.slice(0, 10)} · {p.type}</div>
        </div>
      ))}
    </Modal>
  );
}

function CreateCommunityModal({ onClose, onCreate }) {
  const topics = ["research_methods","ai_in_research","statistics","open_science","peer_review","grant_writing","scientific_publishing","teaching","innovation","discipline_specific","software","datasets"];
  const [form, setForm] = useState({ name: "", description: "", topic: "research_methods", visibility: "public" });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try { await axios.post("/api/network/communities", form); onCreate(); onClose(); }
    catch { setSaving(false); }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Create Community"
      size="sm"
      footer={
        <Button variant="primary" onClick={handleSubmit} disabled={saving} loading={saving} style={{ width: "100%" }}>
          {saving ? "Creating…" : "Create Community"}
        </Button>
      }
    >
      <Input
        label="Name *"
        value={form.name}
        onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
      />
      <Textarea
        label="Description"
        value={form.description}
        onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
        rows={2}
      />
      <FormSelect
        label="Topic"
        value={form.topic}
        onChange={e => setForm(f => ({ ...f, topic: e.target.value }))}
      >
        {topics.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
      </FormSelect>
    </Modal>
  );
}

export default function Communities() {
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState("");
  const [topicFilter, setTopicFilter] = useState("");
  const [tab, setTab] = useState("discover");
  const [myCommunities, setMyCommunities] = useState([]);
  const [openCommunity, setOpenCommunity] = useState(null);
  const [showCreate, setShowCreate] = useState(false);

  const fetchCommunities = useCallback(async () => {
    setLoading(true);
    try {
      const params = { limit: 30 };
      if (q) params.q = q;
      if (topicFilter) params.topic = topicFilter;
      const r = await axios.get("/api/network/communities", { params });
      setResults(r.data.results || []);
      setTotal(r.data.total || 0);
    } catch { } finally { setLoading(false); }
  }, [q, topicFilter]);

  const fetchMyCommunities = useCallback(async () => {
    try { const r = await axios.get("/api/network/communities/mine"); setMyCommunities(r.data || []); } catch { }
  }, []);

  // Only auto-fetch on mount; subsequent searches are user-triggered (Enter / Search button).
  const fetchCommunitiesRef = useRef(fetchCommunities);
  useEffect(() => { fetchCommunitiesRef.current = fetchCommunities; }, [fetchCommunities]);
  useEffect(() => { fetchCommunitiesRef.current(); fetchMyCommunities(); }, [fetchMyCommunities]);

  const handleJoin = async id => { await axios.post(`/api/network/communities/${id}/join`); fetchCommunities(); fetchMyCommunities(); };
  const handleLeave = async id => { await axios.post(`/api/network/communities/${id}/leave`); fetchCommunities(); fetchMyCommunities(); };

  return (
    <DiscoveryLayout
      title="Academic Communities"
      actions={<Button variant="primary" onClick={() => setShowCreate(true)}><Plus size={15} />Create</Button>}
    >

      <div style={{ marginBottom: 16 }}>
        <NavTabs
          variant="pill"
          tabs={[
            { id: "discover", label: "Discover" },
            { id: "mine", label: "Joined", count: myCommunities.length },
          ]}
          active={tab}
          onChange={setTab}
        />
      </div>

      {tab === "discover" && (
        <>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <Input
              value={q}
              onChange={e => setQ(e.target.value)}
              onKeyDown={e => e.key === "Enter" && fetchCommunities()}
              placeholder="Search communities…"
              wrapperClassName="flex-1"
            />
            <FormSelect value={topicFilter} onChange={e => setTopicFilter(e.target.value)}>
              <option value="">All topics</option>
              {Object.keys(TOPIC_COLOR).map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </FormSelect>
            <Button variant="primary" onClick={fetchCommunities}>Search</Button>
          </div>
          {loading ? <LoadingOverlay text="Loading…" /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {results.map((c, i) => <CommunityCard key={c.id || i} c={c} onJoin={handleJoin} onLeave={handleLeave} onOpen={setOpenCommunity} />)}
            </div>
          )}
        </>
      )}

      {tab === "mine" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {myCommunities.length === 0 ? (
            <EmptyState title="No communities joined yet." />
          ) : myCommunities.map((c, i) => <CommunityCard key={c.id || i} c={{ ...c, is_member: true }} onJoin={handleJoin} onLeave={handleLeave} onOpen={setOpenCommunity} />)}
        </div>
      )}

      {openCommunity && <CommunityDetail community={openCommunity} onClose={() => setOpenCommunity(null)} />}
      {showCreate && <CreateCommunityModal onClose={() => setShowCreate(false)} onCreate={() => { fetchCommunities(); fetchMyCommunities(); }} />}
    </DiscoveryLayout>
  );
}

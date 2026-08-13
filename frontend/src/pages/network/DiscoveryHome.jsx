import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import {
  Users, Building2, Layers, Handshake, Calendar,
  MessageSquare, UserCheck, Brain, Search, ArrowRight,
} from "lucide-react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Button, Input, StatCard, StatGrid } from "@/components/ds";

const TILES = [
  { label: "Researchers", desc: "Find collaborators by expertise, method, career stage", url: "/network/people", icon: Users, color: ACCENT },
  { label: "Institutions", desc: "Discover universities, labs, research centres", url: "/network/institutions", icon: Building2, color: "#0ea5e9" },
  { label: "Research Groups", desc: "Join or create research groups and labs", url: "/network/groups", icon: Layers, color: "#8b5cf6" },
  { label: "Open Collaborations", desc: "Post and apply for collaboration opportunities", url: "/network/collaborations", icon: Handshake, color: EMERALD },
  { label: "Communities", desc: "Topic-based academic communities", url: "/network/communities", icon: MessageSquare, color: "#f97316" },
  { label: "Mentorship", desc: "Connect with mentors or become one", url: "/network/mentorship", icon: UserCheck, color: "#ec4899" },
  { label: "Events", desc: "Seminars, conferences, workshops, webinars", url: "/network/conferences", icon: Calendar, color: "#06b6d4" },
  { label: "AI Recommendations", desc: "Personalised discovery powered by AI", url: "/network/recommendations", icon: Brain, color: NAVY },
];

export default function DiscoveryHome() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    api.get("/network/stats").then(r => setStats(r.data)).catch(() => {});
  }, []);

  const handleSearch = e => {
    e.preventDefault();
    if (query.trim()) navigate(`/network/people?q=${encodeURIComponent(query.trim())}`);
  };

  return (
    <ResearchLayout
      title="Academic Network"
      subtitle="Discover researchers, institutions, projects and opportunities."
      actions={
        <form onSubmit={handleSearch} style={{ display: "flex", gap: 8 }}>
          <Input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search researchers, topics, expertise…"
            prefix={<Search size={14} />}
            wrapperClassName="w-64"
          />
          <Button type="submit" variant="primary" size="sm">Search</Button>
        </form>
      }
    >
      {/* Stats */}
      {stats && (
        <div style={{ marginBottom: 28 }}>
          <StatGrid cols={6}>
            <StatCard label="Researchers" value={stats.researchers?.toLocaleString?.() ?? stats.researchers} />
            <StatCard label="Institutions" value={stats.institutions?.toLocaleString?.() ?? stats.institutions} />
            <StatCard label="Open Collaborations" value={stats.open_collaborations?.toLocaleString?.() ?? stats.open_collaborations} />
            <StatCard label="Research Groups" value={stats.research_groups?.toLocaleString?.() ?? stats.research_groups} />
            <StatCard label="Communities" value={stats.communities?.toLocaleString?.() ?? stats.communities} />
            <StatCard label="Upcoming Events" value={stats.upcoming_events?.toLocaleString?.() ?? stats.upcoming_events} />
          </StatGrid>
        </div>
      )}

      {/* Tiles */}
      <h2 style={{ margin: "0 0 14px", fontSize: 16, fontWeight: 800, color: NAVY }}>Explore the Network</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 12, marginBottom: 28 }}>
        {TILES.map(({ label, desc, url, icon: Icon, color }) => (
          <Card key={url} to={url} padding="lg">
            <div style={{ width: 40, height: 40, borderRadius: 10, background: `${color}15`, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 12 }}>
              <Icon size={20} color={color} />
            </div>
            <div style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 12, color: TEXT_SECONDARY, lineHeight: 1.5 }}>{desc}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 10, color, fontSize: 12, fontWeight: 600 }}>
              Explore <ArrowRight size={12} />
            </div>
          </Card>
        ))}
      </div>
    </ResearchLayout>
  );
}

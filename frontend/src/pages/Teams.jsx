/* eslint-disable */
import React, { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ResearchLayout } from "@/layouts";
import api from "../lib/api";
import { Avatar } from "@/components/ds/Avatar";
import EmptyState from "@/components/ds/EmptyState";
import { SkeletonCard, Spinner } from "@/components/ds/LoadingState";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import {
  Plus, Search, Users, BookOpen, Award, FileText,
  Microscope, BookMarked, GraduationCap, Briefcase,
  Globe, Building2, CheckSquare, Star, ArrowRight,
  UserPlus, CheckCircle, Layers, Lock, Filter,
  FlaskConical, Lightbulb, PenTool, Shield, X,
} from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Tag } from "@/components/ds/Tag";
import { Button } from "@/components/ds/Button";
import { SearchBar, FilterChip } from "@/components/ds/SearchBar";
import { NavTabs } from "@/components/ds/NavTabs";

const BORDER = "#E4E8EF";

export const TEAM_TYPES = [
  { value: "",                   label: "All Types",          icon: Layers,        color: "#64748B" },
  { value: "research_paper",     label: "Research Paper",     icon: FileText,      color: "#7C3AED" },
  { value: "conference_paper",   label: "Conference Paper",   icon: BookOpen,      color: "#0891B2" },
  { value: "grant",              label: "Grant Team",         icon: Award,         color: "#D97706" },
  { value: "book",               label: "Book",               icon: BookMarked,    color: "#059669" },
  { value: "monograph",          label: "Monograph",          icon: BookMarked,    color: "#065F46" },
  { value: "teaching",           label: "Teaching",           icon: GraduationCap, color: "#8B5CF6" },
  { value: "course_development", label: "Course Development", icon: PenTool,       color: "#2563EB" },
  { value: "innovation",         label: "Innovation",         icon: Lightbulb,     color: "#F59E0B" },
  { value: "interdisciplinary",  label: "Interdisciplinary",  icon: FlaskConical,  color: "#06B6D4" },
  { value: "institution",        label: "Institution",        icon: Building2,     color: "#374151" },
  { value: "review_team",        label: "Review Team",        icon: CheckSquare,   color: "#DC2626" },
  { value: "editorial_team",     label: "Editorial Team",     icon: Shield,        color: "#EA580C" },
];

function typeInfo(typeValue) {
  return TEAM_TYPES.find((t) => t.value === typeValue) || TEAM_TYPES.find((t) => t.value === "research_paper");
}

function TypeBadge({ type }) {
  const info = typeInfo(type);
  const Icon = info.icon;
  return (
    <Badge color={info.color} size="sm">
      <Icon size={9} strokeWidth={2} />
      {info.label}
    </Badge>
  );
}

function TeamCard({ group, myIds, onJoin, onLeave, busy }) {
  const isMember = myIds.has(group._id || group.id);
  const count = group.member_count ?? group.members_count ?? 0;
  const typeInfo_ = typeInfo(group.type);

  return (
    <Card padding="none" style={{ display: "flex", flexDirection: "column" }}>
      <Link to={`/teams/${group._id || group.id}`} style={{ display: "block", padding: "18px 18px 14px", textDecoration: "none" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10, marginBottom: 10 }}>
          <div style={{ width: 36, height: 36, background: typeInfo_.color + "18", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            {React.createElement(typeInfo_.icon, { size: 16, strokeWidth: 1.5, style: { color: typeInfo_.color } })}
          </div>
          {group.visibility === "private" && (
            <Lock size={11} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0 }} />
          )}
        </div>

        <div style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", marginBottom: 6, lineHeight: 1.3, letterSpacing: "-0.01em" }}>{group.name}</div>
        <TypeBadge type={group.type} />

        {group.discipline && (
          <div style={{ fontSize: 11, color: "#64748B", marginTop: 8, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{group.discipline}</div>
        )}

        {group.description && (
          <div style={{ fontSize: 12, color: "#94A3B8", marginTop: 8, lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
            {group.description}
          </div>
        )}

        {group.keywords?.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 10 }}>
            {group.keywords.slice(0, 3).map((kw) => (
              <Tag key={kw} size="sm">{kw}</Tag>
            ))}
            {group.keywords.length > 3 && (
              <span style={{ fontSize: 10, padding: "2px 6px", color: "#94A3B8" }}>+{group.keywords.length - 3}</span>
            )}
          </div>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 14, paddingTop: 12, borderTop: `1px solid ${BORDER}`, fontSize: 11, color: "#94A3B8" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <Users size={10} strokeWidth={1.5} />
            {count} member{count !== 1 ? "s" : ""}
          </span>
          {group.max_members && (
            <span style={{ fontFamily: "monospace" }}>cap {group.max_members}</span>
          )}
          {group.institution && (
            <span style={{ display: "flex", alignItems: "center", gap: 3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              <Building2 size={9} strokeWidth={1.5} />
              {group.institution}
            </span>
          )}
        </div>
      </Link>

      <div style={{ padding: "10px 18px 14px", borderTop: `1px solid ${BORDER}` }}>
        {isMember ? (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: "#059669", fontWeight: 600 }}>
              <CheckCircle size={11} strokeWidth={2} />
              Member
            </span>
            <Link to={`/teams/${group._id || group.id}`} style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: NAVY, textDecoration: "none", fontWeight: 600 }}>
              Open <ArrowRight size={10} strokeWidth={2} />
            </Link>
            <Button
              variant="link"
              size="sm"
              onClick={() => onLeave(group._id || group.id)}
              disabled={busy}
              className="text-slate-400"
            >
              Leave
            </Button>
          </div>
        ) : (
          <Button
            onClick={() => onJoin(group._id || group.id)}
            disabled={busy || group.visibility === "private"}
            loading={busy}
            variant={group.visibility === "private" ? "subtle" : "primary"}
            className="w-full"
          >
            {group.visibility === "private" ? (
              <><Lock size={11} strokeWidth={1.5} />Private Team</>
            ) : (
              <><UserPlus size={11} strokeWidth={1.5} />Request to Join</>
            )}
          </Button>
        )}
      </div>
    </Card>
  );
}

export default function Teams() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState("browse");
  const [groups, setGroups]       = useState([]);
  const [myGroups, setMyGroups]   = useState([]);
  const [myIds, setMyIds]         = useState(new Set());
  const [loading, setLoading]     = useState(true);
  const [busy, setBusy]           = useState(false);
  const [q, setQ]                 = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const loadGroups = useCallback(async () => {
    setLoading(true);
    try {
      const params = { limit: 60 };
      if (q)          params.q = q;
      if (typeFilter) params.type = typeFilter;
      const { data } = await api.get("/network/groups", { params });
      const items = Array.isArray(data) ? data : (data.items || data.groups || []);
      setGroups(items);
    } catch {
      toast.error("Failed to load teams");
    } finally {
      setLoading(false);
    }
  }, [q, typeFilter]);

  const loadMyGroups = useCallback(async () => {
    try {
      const { data } = await api.get("/network/groups/mine");
      const items = Array.isArray(data) ? data : (data.items || data.groups || []);
      setMyGroups(items);
      setMyIds(new Set(items.map((g) => g._id || g.id)));
    } catch {}
  }, []);

  useEffect(() => { loadGroups(); }, [loadGroups]);
  useEffect(() => { loadMyGroups(); }, [loadMyGroups]);

  const handleJoin = async (groupId) => {
    setBusy(true);
    try {
      await api.post(`/network/groups/${groupId}/join`);
      toast.success("Joined team");
      await loadMyGroups();
      await loadGroups();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to join");
    } finally {
      setBusy(false);
    }
  };

  const handleLeave = async (groupId) => {
    setBusy(true);
    try {
      await api.post(`/network/groups/${groupId}/leave`);
      toast.success("Left team");
      await loadMyGroups();
      await loadGroups();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to leave");
    } finally {
      setBusy(false);
    }
  };

  const visibleGroups = activeTab === "my" ? myGroups : groups;

  return (
    <ResearchLayout
      title="Research Teams"
      subtitle="Find, create and manage research teams across all academic disciplines."
      actions={
        <Button onClick={() => navigate("/teams/create")}>
          <Plus size={14} strokeWidth={2} />
          Create Team
        </Button>
      }
      nav={
        <NavTabs
          tabs={[
            { id: "browse", label: "Browse All", count: groups.length },
            { id: "my",     label: "My Teams",   count: myIds.size },
          ]}
          active={activeTab}
          onChange={setActiveTab}
        />
      }
    >
    <div>

      {/* ── SEARCH + TYPE FILTER ────────────────────────────────────────────── */}
      {activeTab === "browse" && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <div style={{ flex: 1 }}>
              <SearchBar
                value={q}
                onChange={setQ}
                onKeyDown={(e) => { if (e.key === "Enter") loadGroups(); }}
                placeholder="Search teams by name, discipline, keyword…"
                onClear={() => setQ("")}
              />
            </div>
            <Button variant="outline" onClick={loadGroups}>Search</Button>
            {(q || typeFilter) && (
              <Button variant="ghost" onClick={() => { setQ(""); setTypeFilter(""); }}>
                <X size={11} strokeWidth={2} /> Clear
              </Button>
            )}
          </div>

          {/* Type filter chips */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {TEAM_TYPES.map((t) => (
              <FilterChip
                key={t.value}
                label={t.label}
                active={typeFilter === t.value}
                onClick={() => setTypeFilter(t.value === typeFilter ? "" : t.value)}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── RESULTS ─────────────────────────────────────────────────────────── */}
      {loading && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
          {[1,2,3,4,5,6].map((i) => <SkeletonCard key={i} rows={4} />)}
        </div>
      )}

      {!loading && visibleGroups.length === 0 && (
        <EmptyState
          icon={<Users />}
          title={activeTab === "my" ? "You haven't joined any teams yet" : "No teams found"}
          description={activeTab === "my" ? "Browse all teams and join one, or create your own." : "Try a different search or create a new team for your research."}
          action={
            <div style={{ display: "flex", gap: 10 }}>
              {activeTab === "my" && (
                <Button variant="outline" onClick={() => setActiveTab("browse")}>
                  Browse Teams
                </Button>
              )}
              <Button onClick={() => navigate("/teams/create")}>
                <Plus size={13} strokeWidth={2} /> Create a Team
              </Button>
            </div>
          }
          size="md"
          dashed={true}
        />
      )}

      {!loading && visibleGroups.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
          {visibleGroups.map((g) => (
            <TeamCard key={g._id || g.id} group={g} myIds={myIds} onJoin={handleJoin} onLeave={handleLeave} busy={busy} />
          ))}
        </div>
      )}

    </div>
    </ResearchLayout>
  );
}

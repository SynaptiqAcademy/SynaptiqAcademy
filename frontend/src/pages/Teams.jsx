/* eslint-disable */
import React, { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { DiscoveryLayout } from "@/layouts";
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
import { NAVY, WARM, ACCENT } from "@/lib/tokens";

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
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 10, fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase", color: info.color, background: info.color + "14", border: `1px solid ${info.color}30`, padding: "2px 8px" }}>
      <Icon size={9} strokeWidth={2} />
      {info.label}
    </span>
  );
}

function TeamCard({ group, myIds, onJoin, onLeave, busy }) {
  const [hovered, setHovered] = useState(false);
  const isMember = myIds.has(group._id || group.id);
  const count = group.member_count ?? group.members_count ?? 0;
  const typeInfo_ = typeInfo(group.type);

  return (
    <div
      style={{ display: "flex", flexDirection: "column", border: `1px solid ${hovered ? NAVY + "50" : BORDER}`, background: "white", transition: "all 0.15s", transform: hovered ? "translateY(-2px)" : "none", boxShadow: hovered ? "0 4px 16px rgba(15,40,71,0.08)" : "none", cursor: "pointer" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
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
              <span key={kw} style={{ fontSize: 10, padding: "2px 6px", background: WARM, border: `1px solid ${BORDER}`, color: "#64748B", fontFamily: "monospace" }}>{kw}</span>
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
            <button
              onClick={() => onLeave(group._id || group.id)}
              disabled={busy}
              style={{ fontSize: 11, color: "#94A3B8", background: "none", border: "none", cursor: "pointer", padding: "0 4px" }}
            >
              Leave
            </button>
          </div>
        ) : (
          <button
            onClick={() => onJoin(group._id || group.id)}
            disabled={busy || group.visibility === "private"}
            style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 6, fontSize: 12, fontWeight: 600, padding: "7px 0", background: group.visibility === "private" ? WARM : NAVY, color: group.visibility === "private" ? "#94A3B8" : "white", border: "none", cursor: group.visibility === "private" ? "not-allowed" : "pointer", transition: "opacity 0.15s", opacity: busy ? 0.6 : 1 }}
          >
            {group.visibility === "private" ? (
              <><Lock size={11} strokeWidth={1.5} />Private Team</>
            ) : (
              <><UserPlus size={11} strokeWidth={1.5} />Request to Join</>
            )}
          </button>
        )}
      </div>
    </div>
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
    <DiscoveryLayout title="Research Teams" subtitle="Find, create and manage research teams across all academic disciplines.">
    <div>

      {/* ── HEADER ─────────────────────────────────────────────────────────── */}
      <div style={{ background: NAVY, margin: "-24px -24px 0", padding: "36px 28px 28px" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600, marginBottom: 8 }}>
              ACADEMIC NETWORK
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 700, color: "white", margin: "0 0 6px", letterSpacing: "-0.03em", lineHeight: 1.15 }}>Research Teams</h1>
            <p style={{ fontSize: 13, color: "rgba(255,255,255,0.45)", margin: 0, maxWidth: 460 }}>
              Collaborate on research papers, grants, books, courses and more. Find your team or start a new one.
            </p>
          </div>
          <button
            onClick={() => navigate("/teams/create")}
            style={{ display: "inline-flex", alignItems: "center", gap: 8, background: ACCENT, color: "white", border: "none", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
          >
            <Plus size={14} strokeWidth={2} />
            Create Team
          </button>
        </div>
      </div>

      {/* ── TAB BAR ────────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 0, borderBottom: `1px solid ${BORDER}`, background: "white", marginBottom: 24 }}>
        {[
          { key: "browse", label: "Browse All", sub: `${groups.length} teams` },
          { key: "my",     label: "My Teams",   sub: `${myIds.size} joined` },
        ].map((t) => {
          const active = activeTab === t.key;
          return (
            <button key={t.key} onClick={() => setActiveTab(t.key)} style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 2, padding: "14px 20px", borderBottom: `2px solid ${active ? NAVY : "transparent"}`, background: "transparent", cursor: "pointer", transition: "border-color 0.15s", border: "none", borderBottom: `2px solid ${active ? NAVY : "transparent"}`, minWidth: 130 }}>
              <span style={{ fontSize: 13, fontWeight: active ? 700 : 500, color: active ? NAVY : "#64748B" }}>{t.label}</span>
              <span style={{ fontSize: 10, color: "#CBD5E1" }}>{t.sub}</span>
            </button>
          );
        })}
      </div>

      {/* ── SEARCH + TYPE FILTER ────────────────────────────────────────────── */}
      {activeTab === "browse" && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <div style={{ position: "relative", flex: 1 }}>
              <Search size={13} strokeWidth={1.5} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "#94A3B8" }} />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") loadGroups(); }}
                placeholder="Search teams by name, discipline, keyword…"
                style={{ width: "100%", paddingLeft: 34, paddingRight: 12, paddingTop: 9, paddingBottom: 9, border: `1px solid ${BORDER}`, fontSize: 13, color: "#374151", outline: "none", boxSizing: "border-box" }}
                onFocus={(e) => e.currentTarget.style.borderColor = NAVY + "70"}
                onBlur={(e) => e.currentTarget.style.borderColor = BORDER}
              />
            </div>
            <button onClick={loadGroups} style={{ background: NAVY, color: "white", border: "none", padding: "9px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>Search</button>
            {(q || typeFilter) && (
              <button onClick={() => { setQ(""); setTypeFilter(""); }} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "#64748B", border: `1px solid ${BORDER}`, background: "white", padding: "9px 12px", cursor: "pointer" }}>
                <X size={11} strokeWidth={2} /> Clear
              </button>
            )}
          </div>

          {/* Type filter chips */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {TEAM_TYPES.map((t) => {
              const active = typeFilter === t.value;
              const Icon = t.icon;
              return (
                <button
                  key={t.value}
                  onClick={() => { setTypeFilter(t.value === typeFilter ? "" : t.value); }}
                  style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, padding: "5px 12px", border: `1px solid ${active ? t.color : BORDER}`, background: active ? t.color + "14" : "white", color: active ? t.color : "#64748B", cursor: "pointer", fontWeight: active ? 600 : 400, transition: "all 0.15s" }}
                >
                  <Icon size={10} strokeWidth={1.5} />
                  {t.label}
                </button>
              );
            })}
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
                <button onClick={() => setActiveTab("browse")} style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "white", color: NAVY, border: `1px solid ${NAVY}40`, padding: "9px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
                  Browse Teams
                </button>
              )}
              <button onClick={() => navigate("/teams/create")} style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", border: "none", padding: "9px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
                <Plus size={13} strokeWidth={2} /> Create a Team
              </button>
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
    </DiscoveryLayout>
  );
}

/* eslint-disable */
import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { DiscoveryLayout } from "@/layouts";
import api from "../lib/api";
import { Avatar } from "@/components/ds/Avatar";
import EmptyState from "@/components/ds/EmptyState";
import { Spinner } from "@/components/ds/LoadingState";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { TEAM_TYPES } from "./Teams";
import { NAVY, WARM, ACCENT } from "@/lib/tokens";
import {
  Users, ArrowLeft, Settings, UserPlus, LogOut,
  CheckCircle, Lock, Globe, Crown, LayoutGrid,
  Archive, MessageSquare, FolderOpen, Calendar,
  FileText, Activity, BookOpen, Eye, MoreHorizontal,
  Trash2, PenLine, UserCheck, Clock,
} from "lucide-react";

const BORDER = "#E4E8EF";

function typeInfo(typeValue) {
  return TEAM_TYPES.find((t) => t.value === typeValue) || TEAM_TYPES[1];
}

const ROLE_LABELS = {
  owner:       { label: "Owner",            color: "#D97706" },
  admin:       { label: "Admin",            color: "#7C3AED" },
  lead:        { label: "Lead",             color: "#0891B2" },
  senior:      { label: "Senior Member",    color: "#059669" },
  member:      { label: "Member",           color: "#64748B" },
  collaborator:{ label: "Collaborator",     color: "#94A3B8" },
};

function roleBadge(role) {
  const r = ROLE_LABELS[role] || ROLE_LABELS.member;
  return (
    <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase", color: r.color, background: r.color + "14", border: `1px solid ${r.color}30`, padding: "2px 7px" }}>
      {r.label}
    </span>
  );
}

const TABS = [
  { key: "overview",   label: "Overview",   icon: Eye },
  { key: "members",    label: "Members",    icon: Users },
  { key: "workspace",  label: "Workspace",  icon: LayoutGrid },
  { key: "repository", label: "Repository", icon: Archive },
  { key: "chat",       label: "Chat",       icon: MessageSquare },
  { key: "tasks",      label: "Tasks",      icon: CheckCircle },
  { key: "files",      label: "Files",      icon: FolderOpen },
  { key: "activity",   label: "Activity",   icon: Activity },
  { key: "publications", label: "Publications", icon: BookOpen },
];

export default function TeamHome() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [group, setGroup]     = useState(null);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab]         = useState("overview");
  const [busy, setBusy]       = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");

  const isMember = members.some((m) => (m.user_id || m.id) === user?.id);
  const isOwner  = members.some((m) => (m.user_id || m.id) === user?.id && (m.role === "owner" || m.role === "admin"));
  const myRole   = members.find((m) => (m.user_id || m.id) === user?.id)?.role || null;

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      api.get(`/network/groups/${id}`).catch(() => null),
      api.get(`/network/groups/${id}/members`).catch(() => ({ data: [] })),
    ]).then(([gRes, mRes]) => {
      if (gRes) setGroup(gRes.data);
      const mems = Array.isArray(mRes.data) ? mRes.data : (mRes.data?.members || mRes.data?.items || []);
      setMembers(mems);
    }).finally(() => setLoading(false));
  }, [id]);

  const handleJoin = async () => {
    setBusy(true);
    try {
      await api.post(`/network/groups/${id}/join`);
      toast.success("Joined team");
      const mRes = await api.get(`/network/groups/${id}/members`);
      const mems = Array.isArray(mRes.data) ? mRes.data : (mRes.data?.members || []);
      setMembers(mems);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to join");
    } finally {
      setBusy(false);
    }
  };

  const handleLeave = async () => {
    if (!window.confirm("Leave this team?")) return;
    setBusy(true);
    try {
      await api.post(`/network/groups/${id}/leave`);
      toast.success("Left team");
      navigate("/teams");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to leave");
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <DiscoveryLayout title="Team" subtitle="">
        <div style={{ display: "flex", justifyContent: "center", padding: 80 }}><Spinner size={24} /></div>
      </DiscoveryLayout>
    );
  }

  if (!group) {
    return (
      <DiscoveryLayout title="Team" subtitle="">
        <EmptyState icon={<Users />} title="Team not found" description="This team may have been removed or is no longer accessible." action={<Link to="/teams" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", padding: "9px 20px", fontSize: 13, fontWeight: 600, textDecoration: "none" }}>Back to Teams</Link>} size="md" dashed />
      </DiscoveryLayout>
    );
  }

  const tInfo = typeInfo(group.type);
  const TypeIcon = tInfo.icon;
  const count = group.member_count ?? members.length;

  return (
    <DiscoveryLayout title={group.name} subtitle={tInfo.label}>
    <div>

      {/* ── TEAM HEADER ─────────────────────────────────────────────────────── */}
      <div style={{ background: NAVY, margin: "-24px -24px 0", padding: "36px 28px 28px" }}>
        <button onClick={() => navigate("/teams")} style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, color: "rgba(255,255,255,0.45)", background: "none", border: "none", cursor: "pointer", padding: 0, marginBottom: 18, letterSpacing: "0.05em" }}>
          <ArrowLeft size={11} strokeWidth={2} />TEAMS
        </button>

        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 20, flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
            <div style={{ width: 52, height: 52, background: tInfo.color + "30", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <TypeIcon size={24} strokeWidth={1.5} style={{ color: tInfo.color }} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
                <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: tInfo.color, background: tInfo.color + "25", border: `1px solid ${tInfo.color}40`, padding: "2px 8px" }}>
                  {tInfo.label}
                </span>
                {group.visibility === "private" ? (
                  <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", display: "flex", alignItems: "center", gap: 4 }}>
                    <Lock size={9} strokeWidth={1.5} />Private
                  </span>
                ) : (
                  <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", display: "flex", alignItems: "center", gap: 4 }}>
                    <Globe size={9} strokeWidth={1.5} />Public
                  </span>
                )}
              </div>
              <h1 style={{ fontSize: 24, fontWeight: 700, color: "white", margin: 0, letterSpacing: "-0.02em", lineHeight: 1.2 }}>{group.name}</h1>
              {group.discipline && (
                <div style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", marginTop: 6 }}>{group.discipline}</div>
              )}
              <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 10, fontSize: 12, color: "rgba(255,255,255,0.45)" }}>
                <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <Users size={11} strokeWidth={1.5} />
                  {count} member{count !== 1 ? "s" : ""}
                </span>
                {group.institution && (
                  <span>{group.institution}</span>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {isMember ? (
              <>
                {myRole && roleBadge(myRole)}
                {isOwner && (
                  <button style={{ display: "inline-flex", alignItems: "center", gap: 6, border: "1px solid rgba(255,255,255,0.2)", color: "rgba(255,255,255,0.7)", padding: "7px 14px", fontSize: 12, background: "transparent", cursor: "pointer" }}>
                    <Settings size={12} strokeWidth={1.5} />Settings
                  </button>
                )}
                <button
                  onClick={handleLeave}
                  disabled={busy}
                  style={{ display: "inline-flex", alignItems: "center", gap: 6, border: "1px solid rgba(255,255,255,0.12)", color: "rgba(255,255,255,0.4)", padding: "7px 14px", fontSize: 12, background: "transparent", cursor: "pointer", opacity: busy ? 0.5 : 1 }}
                >
                  <LogOut size={12} strokeWidth={1.5} />Leave
                </button>
              </>
            ) : (
              <button
                onClick={group.visibility === "private" ? undefined : handleJoin}
                disabled={busy || group.visibility === "private"}
                style={{ display: "inline-flex", alignItems: "center", gap: 8, background: group.visibility === "private" ? "rgba(255,255,255,0.08)" : ACCENT, color: group.visibility === "private" ? "rgba(255,255,255,0.35)" : "white", border: "none", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: group.visibility === "private" ? "not-allowed" : "pointer", opacity: busy ? 0.6 : 1 }}
              >
                {group.visibility === "private" ? <><Lock size={13} strokeWidth={1.5} />Private Team</> : <><UserPlus size={13} strokeWidth={1.5} />Join Team</>}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── TAB NAVIGATION ─────────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 0, borderBottom: `1px solid ${BORDER}`, background: "white", marginBottom: 28, overflowX: "auto" }}>
        {TABS.map((t) => {
          const active = tab === t.key;
          const Icon = t.icon;
          return (
            <button key={t.key} onClick={() => setTab(t.key)} style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "14px 18px", borderBottom: `2px solid ${active ? NAVY : "transparent"}`, background: "transparent", cursor: "pointer", transition: "border-color 0.15s", border: "none", borderBottom: `2px solid ${active ? NAVY : "transparent"}`, whiteSpace: "nowrap", fontSize: 13, fontWeight: active ? 700 : 400, color: active ? NAVY : "#64748B" }}>
              <Icon size={13} strokeWidth={active ? 2 : 1.5} />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* ── TAB CONTENT ────────────────────────────────────────────────────── */}

      {/* OVERVIEW */}
      {tab === "overview" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 28 }}>
          <div>
            {group.description ? (
              <div style={{ background: "white", border: `1px solid ${BORDER}`, padding: 24, marginBottom: 20 }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 12 }}>About</div>
                <p style={{ fontSize: 13, color: "#374151", lineHeight: 1.7, margin: 0 }}>{group.description}</p>
              </div>
            ) : (
              <div style={{ background: WARM, border: `1px dashed ${BORDER}`, padding: 24, marginBottom: 20, textAlign: "center" }}>
                <div style={{ fontSize: 13, color: "#94A3B8" }}>No description yet.{isOwner && " Edit team settings to add one."}</div>
              </div>
            )}

            {group.keywords?.length > 0 && (
              <div style={{ background: "white", border: `1px solid ${BORDER}`, padding: 20, marginBottom: 20 }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 10 }}>Keywords</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {group.keywords.map((kw) => (
                    <span key={kw} style={{ fontSize: 11, padding: "4px 10px", background: WARM, border: `1px solid ${BORDER}`, color: "#64748B", fontFamily: "monospace" }}>{kw}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Quick links to integrated features */}
            <div style={{ background: "white", border: `1px solid ${BORDER}`, padding: 20 }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 14 }}>Integrated Features</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10 }}>
                {[
                  { label: "Workspace",    icon: LayoutGrid,    to: "/workspaces",     desc: "Shared writing workspace" },
                  { label: "Repository",   icon: Archive,       to: "/repository",     desc: "Files & version history" },
                  { label: "Messages",     icon: MessageSquare, to: "/messages",       desc: "Team group chat" },
                  { label: "Projects",     icon: FolderOpen,    to: "/projects",       desc: "Tasks & milestones" },
                  { label: "Publications", icon: BookOpen,      to: "/publications",   desc: "Publication pipeline" },
                  { label: "Calendar",     icon: Calendar,      to: "/sie/daily",      desc: "Deadlines & schedule" },
                ].map(({ label, icon: Icon, to, desc }) => (
                  <Link key={to} to={to} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 14px", border: `1px solid ${BORDER}`, textDecoration: "none", transition: "border-color 0.15s, background 0.15s" }}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY + "40"; e.currentTarget.style.background = WARM; }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.background = "white"; }}
                  >
                    <div style={{ width: 32, height: 32, background: NAVY + "10", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <Icon size={14} strokeWidth={1.5} style={{ color: NAVY }} />
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: "#0f172a" }}>{label}</div>
                      <div style={{ fontSize: 11, color: "#94A3B8" }}>{desc}</div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar: members preview */}
          <div>
            <div style={{ background: "white", border: `1px solid ${BORDER}`, padding: 20 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8" }}>Members ({count})</div>
                {isMember && <button onClick={() => setTab("members")} style={{ fontSize: 11, color: NAVY, background: "none", border: "none", cursor: "pointer", fontWeight: 600 }}>View all</button>}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {members.slice(0, 8).map((m) => {
                  const uid = m.user_id || m.id;
                  return (
                    <Link to={`/profile/${uid}`} key={uid} style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
                      <Avatar url={m.avatar_url} name={m.full_name || m.name} size={28} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.full_name || m.name || "Member"}</div>
                        <div style={{ fontSize: 10, color: "#94A3B8" }}>{m.institution || ""}</div>
                      </div>
                      {m.role === "owner" && <Crown size={10} strokeWidth={1.5} style={{ color: "#D97706", flexShrink: 0 }} />}
                    </Link>
                  );
                })}
                {members.length === 0 && (
                  <div style={{ fontSize: 12, color: "#94A3B8", textAlign: "center", padding: "12px 0" }}>No members loaded</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MEMBERS */}
      {tab === "members" && (
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8" }}>{count} member{count !== 1 ? "s" : ""}</div>
            {isOwner && (
              <button style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", border: "none", padding: "8px 16px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
                <UserPlus size={12} strokeWidth={2} />Invite Member
              </button>
            )}
          </div>
          {members.length === 0 ? (
            <EmptyState icon={<Users />} title="No members yet" size="sm" />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 0, border: `1px solid ${BORDER}`, background: "white" }}>
              {members.map((m, i) => {
                const uid = m.user_id || m.id;
                return (
                  <div key={uid} style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 18px", borderBottom: i < members.length - 1 ? `1px solid ${BORDER}` : "none" }}>
                    <Link to={`/profile/${uid}`} style={{ display: "flex", alignItems: "center", gap: 12, flex: 1, textDecoration: "none", minWidth: 0 }}>
                      <Avatar url={m.avatar_url} name={m.full_name || m.name} size={36} />
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {m.full_name || m.name || "Member"}
                          {m.role === "owner" && <Crown size={11} strokeWidth={1.5} style={{ color: "#D97706", marginLeft: 6, display: "inline" }} />}
                        </div>
                        <div style={{ fontSize: 11, color: "#94A3B8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.institution || m.email || ""}</div>
                      </div>
                    </Link>
                    <div style={{ flexShrink: 0 }}>
                      {roleBadge(m.role || "member")}
                    </div>
                    {isOwner && uid !== user?.id && (
                      <button style={{ background: "none", border: "none", cursor: "pointer", color: "#CBD5E1", padding: 4, display: "flex" }}>
                        <MoreHorizontal size={14} strokeWidth={1.5} />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* PASS-THROUGH TABS — link to integrated features */}
      {["workspace", "repository", "chat", "tasks", "files", "activity", "publications"].includes(tab) && (
        <div style={{ textAlign: "center", padding: "64px 24px" }}>
          <div style={{ fontSize: 32, marginBottom: 16 }}>
            {tab === "workspace"    && <LayoutGrid  size={40} strokeWidth={1.2} style={{ color: NAVY, margin: "0 auto" }} />}
            {tab === "repository"   && <Archive     size={40} strokeWidth={1.2} style={{ color: NAVY, margin: "0 auto" }} />}
            {tab === "chat"         && <MessageSquare size={40} strokeWidth={1.2} style={{ color: NAVY, margin: "0 auto" }} />}
            {tab === "tasks"        && <CheckCircle size={40} strokeWidth={1.2} style={{ color: NAVY, margin: "0 auto" }} />}
            {tab === "files"        && <FolderOpen  size={40} strokeWidth={1.2} style={{ color: NAVY, margin: "0 auto" }} />}
            {tab === "activity"     && <Activity    size={40} strokeWidth={1.2} style={{ color: NAVY, margin: "0 auto" }} />}
            {tab === "publications" && <BookOpen    size={40} strokeWidth={1.2} style={{ color: NAVY, margin: "0 auto" }} />}
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", marginBottom: 8, letterSpacing: "-0.02em" }}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </div>
          <div style={{ fontSize: 13, color: "#94A3B8", maxWidth: 360, margin: "0 auto 24px" }}>
            {tab === "workspace"    && "Access your shared writing workspace and collaborative documents."}
            {tab === "repository"   && "Manage files, versions and shared research assets."}
            {tab === "chat"         && "Team messaging and real-time collaboration."}
            {tab === "tasks"        && "Manage tasks, milestones and project progress."}
            {tab === "files"        && "Browse shared files, data and documents."}
            {tab === "activity"     && "Track team activity and research milestones."}
            {tab === "publications" && "Manage your team's publication pipeline and submissions."}
          </div>
          <Link
            to={
              tab === "workspace"    ? "/workspaces" :
              tab === "repository"   ? "/repository" :
              tab === "chat"         ? "/messages" :
              tab === "tasks"        ? "/projects" :
              tab === "files"        ? "/repository" :
              tab === "activity"     ? "/network/activity" :
              "/publications"
            }
            style={{ display: "inline-flex", alignItems: "center", gap: 8, background: NAVY, color: "white", padding: "10px 24px", fontSize: 13, fontWeight: 600, textDecoration: "none" }}
          >
            Open {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </Link>
        </div>
      )}

    </div>
    </DiscoveryLayout>
  );
}

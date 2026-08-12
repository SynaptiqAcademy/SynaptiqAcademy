/* eslint-disable */
import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ResearchLayout } from "@/layouts";
import api from "../lib/api";
import { Avatar } from "@/components/ds/Avatar";
import EmptyState from "@/components/ds/EmptyState";
import { Spinner } from "@/components/ds/LoadingState";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { TEAM_TYPES } from "./Teams";
import { NAVY, WARM } from "@/lib/tokens";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Tag } from "@/components/ds/Tag";
import { Button } from "@/components/ds/Button";
import { NavTabs } from "@/components/ds/NavTabs";
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
    <Badge color={r.color} size="sm">{r.label}</Badge>
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
      <ResearchLayout title="Team" subtitle="">
        <div style={{ display: "flex", justifyContent: "center", padding: 80 }}><Spinner size={24} /></div>
      </ResearchLayout>
    );
  }

  if (!group) {
    return (
      <ResearchLayout title="Team" subtitle="">
        <EmptyState icon={<Users />} title="Team not found" description="This team may have been removed or is no longer accessible." action={<Button as={Link} to="/teams">Back to Teams</Button>} size="md" dashed />
      </ResearchLayout>
    );
  }

  const tInfo = typeInfo(group.type);
  const TypeIcon = tInfo.icon;
  const count = group.member_count ?? members.length;

  return (
    <ResearchLayout
      title={group.name}
      subtitle={tInfo.label}
      actions={
        isMember ? (
          <>
            {myRole && roleBadge(myRole)}
            {isOwner && (
              <Button variant="outline" size="sm">
                <Settings size={12} strokeWidth={1.5} />Settings
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={handleLeave} disabled={busy}>
              <LogOut size={12} strokeWidth={1.5} />Leave
            </Button>
          </>
        ) : (
          <Button
            onClick={group.visibility === "private" ? undefined : handleJoin}
            disabled={busy || group.visibility === "private"}
            loading={busy}
          >
            {group.visibility === "private" ? <><Lock size={13} strokeWidth={1.5} />Private Team</> : <><UserPlus size={13} strokeWidth={1.5} />Join Team</>}
          </Button>
        )
      }
      nav={
        <NavTabs
          tabs={TABS.map((t) => ({ id: t.key, label: t.label, icon: t.icon }))}
          active={tab}
          onChange={setTab}
        />
      }
    >
    <div>

      {/* ── Meta bar ──────────────────────────────────────────────────────── */}
      <div className="border-b border-slate-200 pb-4 mb-6">
        <Button variant="link" size="sm" onClick={() => navigate("/teams")} className="!text-slate-500 mb-3">
          <ArrowLeft size={11} strokeWidth={2} />TEAMS
        </Button>
        <div className="flex items-start gap-4">
          <div style={{ width: 44, height: 44, background: tInfo.color + "20", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <TypeIcon size={20} strokeWidth={1.5} style={{ color: tInfo.color }} />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap text-xs text-slate-500">
              {group.visibility === "private" ? (
                <span className="flex items-center gap-1"><Lock size={10} strokeWidth={1.5} />Private</span>
              ) : (
                <span className="flex items-center gap-1"><Globe size={10} strokeWidth={1.5} />Public</span>
              )}
              {group.discipline && <><span className="text-slate-300">·</span><span>{group.discipline}</span></>}
              <span className="text-slate-300">·</span>
              <span className="flex items-center gap-1"><Users size={11} strokeWidth={1.5} />{count} member{count !== 1 ? "s" : ""}</span>
              {group.institution && <><span className="text-slate-300">·</span><span>{group.institution}</span></>}
            </div>
          </div>
        </div>
      </div>

      {/* ── TAB CONTENT ────────────────────────────────────────────────────── */}

      {/* OVERVIEW */}
      {tab === "overview" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 28 }}>
          <div>
            {group.description ? (
              <Card padding="lg" className="mb-5">
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 12 }}>About</div>
                <p style={{ fontSize: 13, color: "#374151", lineHeight: 1.7, margin: 0 }}>{group.description}</p>
              </Card>
            ) : (
              <div style={{ background: WARM, border: `1px dashed ${BORDER}`, padding: 24, marginBottom: 20, textAlign: "center" }}>
                <div style={{ fontSize: 13, color: "#94A3B8" }}>No description yet.{isOwner && " Edit team settings to add one."}</div>
              </div>
            )}

            {group.keywords?.length > 0 && (
              <Card padding="md" className="mb-5">
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 10 }}>Keywords</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {group.keywords.map((kw) => (
                    <Tag key={kw}>{kw}</Tag>
                  ))}
                </div>
              </Card>
            )}

            {/* Quick links to integrated features */}
            <Card padding="md">
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
                  <Card key={to} to={to} padding="sm" style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ width: 32, height: 32, background: NAVY + "10", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <Icon size={14} strokeWidth={1.5} style={{ color: NAVY }} />
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: "#0f172a" }}>{label}</div>
                      <div style={{ fontSize: 11, color: "#94A3B8" }}>{desc}</div>
                    </div>
                  </Card>
                ))}
              </div>
            </Card>
          </div>

          {/* Sidebar: members preview */}
          <div>
            <Card padding="md">
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8" }}>Members ({count})</div>
                {isMember && <Button variant="link" size="sm" onClick={() => setTab("members")}>View all</Button>}
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
            </Card>
          </div>
        </div>
      )}

      {/* MEMBERS */}
      {tab === "members" && (
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8" }}>{count} member{count !== 1 ? "s" : ""}</div>
            {isOwner && (
              <Button size="sm">
                <UserPlus size={12} strokeWidth={2} />Invite Member
              </Button>
            )}
          </div>
          {members.length === 0 ? (
            <EmptyState icon={<Users />} title="No members yet" size="sm" />
          ) : (
            <Card padding="none" className="divide-y divide-slate-100">
              {members.map((m) => {
                const uid = m.user_id || m.id;
                return (
                  <div key={uid} style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 18px" }}>
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
                      <Button variant="ghost" size="icon" aria-label="More options" className="text-slate-300">
                        <MoreHorizontal size={14} strokeWidth={1.5} />
                      </Button>
                    )}
                  </div>
                );
              })}
            </Card>
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
          <Button
            as={Link}
            to={
              tab === "workspace"    ? "/workspaces" :
              tab === "repository"   ? "/repository" :
              tab === "chat"         ? "/messages" :
              tab === "tasks"        ? "/projects" :
              tab === "files"        ? "/repository" :
              tab === "activity"     ? "/network/activity" :
              "/publications"
            }
          >
            Open {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </Button>
        </div>
      )}

    </div>
    </ResearchLayout>
  );
}

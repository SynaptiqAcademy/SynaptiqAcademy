import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { useAuth } from "../contexts/AuthContext";
import {
  Plus, Building2, Mail, Check, X, Users2, FlaskConical,
  Microscope, FileText, DollarSign, GraduationCap, Presentation, BookOpen,
  ChevronRight, Search, ArrowRight, BrainCircuit, Layers,
  Globe, Lock, Shield, Activity, Sparkles, Target,
  FolderOpen, Zap, BookMarked, Users, AlertCircle,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ds/Button";
import { Input } from "../components/ds/Input";
import { Textarea } from "../components/ds/Textarea";
import { FormSelect } from "../components/ds/FormSelect";
import { ACCENT, NAVY, WARM, BRD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { SkeletonPage } from "../components/ds/LoadingState";
import { EmptyState } from "../components/ds/EmptyState";
import { SearchBar, FilterChip } from "../components/ds/SearchBar";

// ─── Brand tokens ─────────────────────────────────────────────────────────────
const BORDER = "#E4E8EF";

// ─── Workspace type config ────────────────────────────────────────────────────
const WS_TYPES = [
  "Research Project", "Manuscript", "Grant Proposal", "Conference Paper",
  "Doctoral Thesis", "Book", "Monograph", "Dissertation", "Thesis",
  "Research Group", "Teaching Project", "Course Development", "Innovation Project",
  "Institutional Research Team", "Consulting Project", "Systematic Review",
  "Custom Workspace",
];

const TYPE_CONFIG = {
  "Manuscript":                  { icon: FileText,    color: "#0891B2", bg: "#F0F9FF" },
  "Grant Proposal":              { icon: DollarSign,  color: "#D97706", bg: "#FFFBEB" },
  "Research Group":              { icon: Users2,      color: "#059669", bg: "#F0FDF4" },
  "Doctoral Thesis":             { icon: GraduationCap, color: ACCENT, bg: "#FFF1F2" },
  "Conference Paper":            { icon: Presentation, color: "#7C3AED", bg: "#FAF5FF" },
  "Systematic Review":           { icon: BookOpen,    color: "#7C3AED", bg: "#FAF5FF" },
  "Institutional Research Team": { icon: Building2,   color: "#64748B", bg: "#F8FAFC" },
  "Consulting Project":          { icon: Target,      color: "#0891B2", bg: "#F0F9FF" },
  "Custom Workspace":            { icon: Layers,      color: "#94A3B8", bg: "#F8FAFC" },
  "Book":                        { icon: BookMarked,  color: "#059669", bg: "#F0FDF4" },
  "Monograph":                   { icon: BookOpen,    color: "#065F46", bg: "#ECFDF5" },
  "Dissertation":                { icon: GraduationCap, color: "#8B5CF6", bg: "#FAF5FF" },
  "Thesis":                      { icon: GraduationCap, color: "#6D28D9", bg: "#F5F3FF" },
  "Teaching Project":            { icon: GraduationCap, color: "#0891B2", bg: "#F0F9FF" },
  "Course Development":          { icon: BookOpen,    color: "#2563EB", bg: "#EFF6FF" },
  "Innovation Project":          { icon: Zap,         color: "#F59E0B", bg: "#FFFBEB" },
};

const DEFAULT_TYPE_CFG = { icon: Microscope, color: NAVY, bg: "#EFF6FF" };

function typeConfig(t) { return TYPE_CONFIG[t] || DEFAULT_TYPE_CFG; }

function fmtDate(d) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function Workspaces() {
  const { user } = useAuth();

  const [items, setItems]     = useState(null);
  const [invitations, setInvitations] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [name, setName]             = useState("");
  const [desc, setDesc]             = useState("");
  const [wsType, setWsType]         = useState("Research Project");
  const [visibility, setVisibility] = useState("private");
  const [institution, setInstitution] = useState("");
  const [creating, setCreating]     = useState(false);
  const [q, setQ]                   = useState("");
  const [filterType, setFilterType] = useState("");

  const loadWorkspaces = async () => {
    try {
      const { data } = await api.get("/workspaces");
      setItems(data || []);
    } catch { setItems([]); }
  };

  const loadInvitations = async () => {
    try {
      const { data } = await api.get("/workspaces/invitations/mine");
      setInvitations(data || []);
    } catch { setInvitations([]); }
  };

  useEffect(() => {
    loadWorkspaces();
    loadInvitations();
  }, []);

  const respondInvitation = async (id, decision) => {
    try {
      await api.post(`/workspaces/invitations/${id}/respond`, { decision });
      toast.success(decision === "accept" ? "Invitation accepted — workspace added." : "Invitation declined.");
      loadInvitations();
      if (decision === "accept") loadWorkspaces();
    } catch { toast.error("Action failed."); }
  };

  const create = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await api.post("/workspaces", {
        name: name.trim(), description: desc.trim(),
        workspace_type: wsType, visibility, institution: institution.trim(),
      });
      setName(""); setDesc(""); setWsType("Research Project");
      setVisibility("private"); setInstitution(""); setShowNew(false);
      toast.success("Workspace created.");
      loadWorkspaces();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed to create workspace."); }
    finally { setCreating(false); }
  };

  // Client-side filtering
  const filtered = useMemo(() => {
    if (!items) return [];
    return items.filter((w) => {
      if (filterType && w.workspace_type !== filterType) return false;
      if (q) {
        const text = ((w.name || "") + " " + (w.description || "") + " " + (w.institution || "") + " " + (w.research_area || "") + " " + (w.keywords || []).join(" ")).toLowerCase();
        if (!text.includes(q.toLowerCase())) return false;
      }
      return true;
    });
  }, [items, filterType, q]);

  // Portfolio stats
  const stats = useMemo(() => {
    if (!items) return null;
    const uid = user?.id;
    return {
      total:  items.length,
      owned:  items.filter((w) => w.owner_id === uid).length,
      collab: items.filter((w) => w.owner_id !== uid).length,
      active: items.filter((w) => w.status === "active" || !w.status).length,
    };
  }, [items, user]);

  // Unique types present
  const presentTypes = useMemo(() => {
    if (!items) return [];
    return [...new Set(items.map((w) => w.workspace_type).filter(Boolean))];
  }, [items]);

  if (items === null) return <SkeletonPage />;

  const firstName = user?.full_name?.split(" ")[0] || "Researcher";

  const statsMeta = stats && stats.total > 0 ? (
    <div style={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
      {[
        { label: "Total Workspaces", value: stats.total,  icon: Layers },
        { label: "My Workspaces",    value: stats.owned,  icon: Shield },
        { label: "Collaborative",    value: stats.collab, icon: Users2 },
        { label: "Active",           value: stats.active, icon: Activity },
      ].map(({ label, value, icon: Icon }) => (
        <div key={label} style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 10px", border: `1px solid ${BRD}`, background: "#F8FAFC" }}>
          <Icon size={11} strokeWidth={1.5} style={{ color: "#94A3B8" }} />
          <span style={{ fontSize: 11, color: "#64748B" }}>{label}:</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: NAVY, fontFamily: "monospace" }}>{value}</span>
        </div>
      ))}
    </div>
  ) : null;

  return (
    <ResearchLayout
      title="Research Workspaces"
      subtitle={`${getGreeting()}, ${firstName}. Your research headquarters — projects, manuscripts, team and AI in one place.`}
      actions={
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <Link
            to="/collaboration-requests"
            className="flex items-center gap-1.5 border border-slate-200 text-slate-600 text-xs px-3 py-1.5 hover:bg-slate-50 transition-colors"
          >
            <Users size={12} strokeWidth={1.5} />
            Find Collaborators
          </Link>
          <button
            data-testid={TID.workspaceCreateBtn}
            onClick={() => setShowNew((v) => !v)}
            className="flex items-center gap-1.5 bg-[#6B0E28] text-white text-sm px-3 py-1.5 hover:opacity-90 transition-opacity"
          >
            <Plus size={13} strokeWidth={2} />
            New Workspace
          </button>
        </div>
      }
      meta={statsMeta}
    >

      {/* ── PENDING INVITATIONS ───────────────────────────────────────────── */}
      {invitations.length > 0 && (
        <div style={{ background: "#FFFBEB", border: "1px solid #FDE68A", borderLeft: "3px solid #F59E0B", padding: "16px 20px", marginTop: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <Mail size={13} strokeWidth={1.5} style={{ color: "#D97706" }} />
            <span style={{ fontSize: 12, fontWeight: 700, color: "#92400E" }}>Workspace Invitations</span>
            <span style={{ fontSize: 11, background: "#D97706", color: "white", padding: "1px 7px", fontFamily: "monospace", fontWeight: 600 }}>{invitations.length}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {invitations.map((inv) => (
              <div key={inv.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, background: "white", border: "1px solid #FDE68A", padding: "12px 16px" }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {inv.workspace?.name || "Workspace"}
                  </div>
                  <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 2, fontFamily: "monospace" }}>
                    Role offered: <span style={{ color: "#374151", fontWeight: 600 }}>{inv.role}</span>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                  <Button size="sm" data-testid={TID.workspaceInvitationAccept(inv.id)} onClick={() => respondInvitation(inv.id, "accept")}>
                    <Check size={11} strokeWidth={2} /> Accept
                  </Button>
                  <Button size="sm" variant="ghost" data-testid={TID.workspaceInvitationDecline(inv.id)} onClick={() => respondInvitation(inv.id, "decline")}>
                    <X size={11} strokeWidth={2} /> Decline
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── CREATE FORM ──────────────────────────────────────────────────── */}
      {showNew && (
        <div style={{ border: `1px solid ${BORDER}`, background: "white", padding: 24, marginTop: 24 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 18 }}>
            New Research Workspace
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div style={{ gridColumn: "1/-1" }}>
              <Input
                label="Workspace name *"
                data-testid={TID.workspaceNewName}
                placeholder="e.g. SymGraph Lab · Aging & Cognition Study"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && create()}
                autoFocus
              />
            </div>
            <FormSelect label="Workspace type" value={wsType} onChange={(e) => setWsType(e.target.value)}>
              {WS_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </FormSelect>
            <FormSelect label="Visibility" value={visibility} onChange={(e) => setVisibility(e.target.value)}>
              <option value="private">Private (members only)</option>
              <option value="institutional">Institutional</option>
              <option value="public">Public</option>
            </FormSelect>
            <div style={{ gridColumn: "1/-1" }}>
              <Input
                label="Institution (optional)"
                placeholder="Affiliated institution or research centre"
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
              />
            </div>
            <div style={{ gridColumn: "1/-1" }}>
              <Textarea
                label="Description (optional)"
                rows={3}
                placeholder="Short description of this workspace's scope and goals"
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
              />
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
            <Button data-testid={TID.workspaceNewSubmit} onClick={create} disabled={creating || !name.trim()} loading={creating}>
              Create workspace
            </Button>
            <Button variant="ghost" onClick={() => { setShowNew(false); setName(""); setDesc(""); setWsType("Research Project"); setVisibility("private"); setInstitution(""); }}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* ── SEARCH + TYPE FILTER ─────────────────────────────────────────── */}
      {items.length > 0 && (
        <div style={{ marginTop: 24, marginBottom: 20 }}>
          <div style={{ marginBottom: 12 }}>
            <SearchBar
              value={q}
              onChange={setQ}
              placeholder="Search workspaces, institutions, research areas…"
              onClear={() => setQ("")}
            />
          </div>
          {presentTypes.length > 1 && (
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <FilterChip label="All" active={!filterType} onClick={() => setFilterType("")} />
              {presentTypes.map((t) => (
                <FilterChip
                  key={t}
                  label={t}
                  active={filterType === t}
                  onClick={() => setFilterType(filterType === t ? "" : t)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── WORKSPACE GRID ───────────────────────────────────────────────── */}
      <div data-testid={TID.workspaceList}>

        {/* Empty — no workspaces */}
        {items.length === 0 && <WorkspaceEmptyState onNew={() => setShowNew(true)} />}

        {/* Filtered empty */}
        {items.length > 0 && filtered.length === 0 && (
          <EmptyState
            icon={<Layers size={24} />}
            title="No workspaces match your filters"
            action={
              <button
                onClick={() => { setQ(""); setFilterType(""); }}
                style={{ fontSize: 12, color: NAVY, background: "white", border: `1px solid ${BORDER}`, padding: "7px 16px", cursor: "pointer" }}
              >
                Clear filters
              </button>
            }
            size="sm"
            dashed={true}
          />
        )}

        {/* Workspace cards */}
        {filtered.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
            {filtered.map((w) => (
              <WorkspaceCard key={w.id} w={w} userId={user?.id} />
            ))}
          </div>
        )}
      </div>

      {/* ── QUICK ACTIONS ────────────────────────────────────────────────── */}
      {items.length > 0 && <WorkspaceQuickActions />}
    </ResearchLayout>
  );
}

// ─── Workspace Card ───────────────────────────────────────────────────────────

function WorkspaceCard({ w, userId }) {
  const cfg         = typeConfig(w.workspace_type);
  const WsIcon      = cfg.icon;
  const memberCount = (w.members || []).length;
  const projCount   = (w.project_ids || []).length;
  const roles       = w.member_roles || {};
  const myRole      = roles[userId] || (w.owner_id === userId ? "Owner" : "Member");
  const isOwner     = w.owner_id === userId;

  const visLabel = w.visibility === "public" ? "Open" : w.visibility === "institutional" ? "Institutional" : "Private";
  const VisIcon  = w.visibility === "public" ? Globe : w.visibility === "institutional" ? Building2 : Lock;
  const statusOk = !w.status || w.status === "active";

  return (
    <Link
      to={`/workspaces/${w.id}`}
      data-testid={TID.workspaceCard(w.id)}
      style={{ display: "flex", flexDirection: "column", border: `1px solid ${BORDER}`, background: "white", textDecoration: "none", transition: "border-color 0.15s, box-shadow 0.15s, transform 0.12s" }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = cfg.color + "60"; e.currentTarget.style.boxShadow = "0 4px 20px rgba(15,40,71,0.1)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "none"; }}
    >
      {/* Type accent bar */}
      <div style={{ height: 3, background: cfg.color, flexShrink: 0 }} />

      <div style={{ padding: "18px 20px", flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Top row */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 14 }}>
          <div style={{ width: 34, height: 34, background: cfg.bg, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <WsIcon size={15} strokeWidth={1.5} style={{ color: cfg.color }} />
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end", alignItems: "center" }}>
            {!isOwner && (
              <span style={{ fontSize: 10, fontFamily: "monospace", fontWeight: 600, color: "#7C3AED", background: "#FAF5FF", border: "1px solid #DDD6FE", padding: "2px 6px" }}>
                Collab
              </span>
            )}
            <span style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 10, color: "#94A3B8", border: `1px solid ${BORDER}`, padding: "2px 7px", fontFamily: "monospace" }}>
              <VisIcon size={9} strokeWidth={1.5} />
              {visLabel}
            </span>
            <span style={{ fontSize: 10, fontFamily: "monospace", fontWeight: 600, color: statusOk ? "#10B981" : "#94A3B8", background: statusOk ? "#F0FDF4" : WARM, border: `1px solid ${statusOk ? "#A7F3D0" : BORDER}`, padding: "2px 6px" }}>
              {w.status || "active"}
            </span>
          </div>
        </div>

        {/* Type label */}
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: cfg.color, marginBottom: 6 }}>
          {w.workspace_type || "Research Project"}
        </div>

        {/* Name */}
        <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", margin: "0 0 6px", lineHeight: 1.35, letterSpacing: "-0.015em" }}>
          {w.name}
        </h3>

        {/* Institution */}
        {w.institution && (
          <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "#94A3B8", marginBottom: 8, fontFamily: "monospace" }}>
            <Building2 size={10} strokeWidth={1.5} />
            {w.institution}
          </div>
        )}

        {/* Description */}
        {w.description && (
          <p style={{ fontSize: 12, color: "#64748B", margin: "0 0 12px", lineHeight: 1.6, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
            {w.description}
          </p>
        )}

        {/* Research area + Keywords */}
        {(w.research_area || (w.keywords || []).length > 0) && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 12 }}>
            {w.research_area && (
              <span style={{ fontSize: 10, padding: "2px 8px", background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.color}30`, fontWeight: 600 }}>{w.research_area}</span>
            )}
            {(w.keywords || []).slice(0, 3).map((k) => (
              <span key={k} style={{ fontSize: 10, padding: "2px 7px", background: WARM, color: "#475569", border: `1px solid ${BORDER}` }}>{k}</span>
            ))}
          </div>
        )}

        {/* Role badge */}
        <div style={{ marginTop: "auto", marginBottom: 14 }}>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: isOwner ? NAVY : "#64748B", background: isOwner ? WARM : "#F8FAFC", border: `1px solid ${isOwner ? BORDER : BORDER}`, padding: "3px 8px" }}>
            {myRole}
          </span>
        </div>

        {/* Footer */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 12, borderTop: `1px solid ${BORDER}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "#94A3B8" }}>
              <Users2 size={10} strokeWidth={1.5} />
              {memberCount} {memberCount === 1 ? "member" : "members"}
            </span>
            {projCount > 0 && (
              <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "#94A3B8" }}>
                <FolderOpen size={10} strokeWidth={1.5} />
                {projCount} {projCount === 1 ? "project" : "projects"}
              </span>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
            {w.updated_at && (
              <span style={{ fontSize: 10, color: "#CBD5E1", fontFamily: "monospace" }}>{fmtDate(w.updated_at)}</span>
            )}
            <ChevronRight size={12} strokeWidth={1.5} style={{ color: "#CBD5E1" }} />
          </div>
        </div>
      </div>
    </Link>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function WorkspaceEmptyState({ onNew }) {
  return (
    <div style={{ marginTop: 28 }}>
      <div style={{ border: `1px solid ${BORDER}`, background: "white", padding: "56px 40px", textAlign: "center", marginBottom: 20 }}>
        <div style={{ width: 56, height: 56, background: WARM, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px" }}>
          <Layers size={24} strokeWidth={0.75} style={{ color: "#CBD5E1" }} />
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "#0f172a", margin: "0 0 10px", letterSpacing: "-0.02em" }}>
          Create your research headquarters
        </h2>
        <p style={{ fontSize: 14, color: "#64748B", lineHeight: 1.7, margin: "0 auto 28px", maxWidth: 480 }}>
          Workspaces are role-governed research environments — bring your team, manuscripts, AI tools, repository, and project tasks together in a secure, shared space built for academic research.
        </p>
        <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
          <button
            data-testid={TID.workspaceCreateBtn}
            onClick={onNew}
            style={{ display: "inline-flex", alignItems: "center", gap: 7, background: NAVY, color: "white", border: "none", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
          >
            <Plus size={13} strokeWidth={2} />
            Create a workspace
          </button>
          <Link
            to="/collaborations"
            style={{ display: "inline-flex", alignItems: "center", gap: 7, border: `1px solid ${BORDER}`, color: "#374151", padding: "10px 18px", fontSize: 13, fontWeight: 500, textDecoration: "none" }}
          >
            Browse collaborations
            <ArrowRight size={12} strokeWidth={1.5} />
          </Link>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        {[
          { icon: BrainCircuit, title: "AI-integrated research",     desc: "Launch literature reviews, manuscript analysis, and gap detection directly from your workspace." },
          { icon: Users2,       title: "Role-governed collaboration", desc: "Invite team members with specific roles — Owner, Admin, Researcher, or Observer." },
          { icon: Shield,       title: "Secure & private",           desc: "Private by default. Control visibility per workspace — private, institutional, or open." },
        ].map(({ icon: Icon, title, desc }) => (
          <div key={title} style={{ border: `1px solid ${BORDER}`, background: WARM, padding: "20px 18px" }}>
            <div style={{ width: 32, height: 32, background: "white", border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 12 }}>
              <Icon size={14} strokeWidth={1.5} style={{ color: NAVY }} />
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#0f172a", marginBottom: 6 }}>{title}</div>
            <p style={{ fontSize: 12, color: "#64748B", lineHeight: 1.55, margin: 0 }}>{desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Quick Actions ────────────────────────────────────────────────────────────

function WorkspaceQuickActions() {
  return (
    <div style={{ marginTop: 36, paddingTop: 24, borderTop: `1px solid ${BORDER}` }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 14 }}>
        Research Tools
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
        {[
          { label: "Synaptiq AI",              to: "/ai",                         icon: BrainCircuit, desc: "AI research assistant for every workspace" },
          { label: "Literature Review",         to: "/literature-review",          icon: BookMarked,   desc: "AI synthesis of academic literature" },
          { label: "Find Collaborators",        to: "/collaboration-intelligence", icon: Users,        desc: "AI-matched co-investigator suggestions" },
          { label: "Manuscript Review",         to: "/manuscript-review",          icon: FileText,     desc: "Structured AI feedback on your paper" },
          { label: "Research Projects",         to: "/projects",                   icon: FolderOpen,   desc: "Manage your research project portfolio" },
          { label: "Collaboration Requests",    to: "/collaboration-requests",     icon: Users2,       desc: "Manage sent and received invitations" },
        ].map(({ label, to, icon: Icon, desc }) => (
          <Link
            key={to}
            to={to}
            style={{ display: "flex", gap: 12, alignItems: "flex-start", border: `1px solid ${BORDER}`, background: "white", padding: "14px 16px", textDecoration: "none", transition: "border-color 0.15s, box-shadow 0.15s" }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY + "50"; e.currentTarget.style.boxShadow = "0 2px 10px rgba(15,40,71,0.07)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.boxShadow = "none"; }}
          >
            <div style={{ width: 30, height: 30, background: WARM, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Icon size={13} strokeWidth={1.5} style={{ color: NAVY }} />
            </div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#0f172a", marginBottom: 3 }}>{label}</div>
              <div style={{ fontSize: 11, color: "#94A3B8", lineHeight: 1.4 }}>{desc}</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}


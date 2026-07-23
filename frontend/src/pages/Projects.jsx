import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { EmptyState } from "../components/ds/EmptyState";
import { SkeletonPage } from "../components/ds/LoadingState";
import { SearchBar, FilterChip } from "../components/ds/SearchBar";
import { Button } from "../components/ds/Button";
import { Input } from "../components/ds/Input";
import { Textarea } from "../components/ds/Textarea";
import { Card } from "../components/ds/Card";
import { Badge } from "../components/ds/Badge";
import { Tag } from "../components/ds/Tag";
import { ACCENT, NAVY, WARM, BRD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import {
  Plus, FolderOpen, Users, ChevronRight, Search,
  Globe, Lock, Layers, BookOpen, Target, Microscope,
  BarChart2, ArrowRight, BrainCircuit, Sparkles,
  FileText, TrendingUp, Clock, CheckCircle2, Zap,
  FlaskConical, BookMarked, Activity,
} from "lucide-react";

// ─── Brand tokens ─────────────────────────────────────────────────────────────
const BORDER = "#E4E8EF";

// ─── Research lifecycle stages ────────────────────────────────────────────────
const STAGES = [
  { key: "draft",   label: "Draft",           color: "#94A3B8", bg: "#F1F5F9" },
  { key: "idea",    label: "Ideation",         color: "#EA580C", bg: "#FFF7ED" },
  { key: "scope",   label: "Scoping",          color: "#D97706", bg: "#FFFBEB" },
  { key: "lit",     label: "Lit. Review",      color: "#059669", bg: "#F0FDF4" },
  { key: "design",  label: "Research Design",  color: "#0891B2", bg: "#F0F9FF" },
  { key: "data",    label: "Data Collection",  color: "#7C3AED", bg: "#FAF5FF" },
  { key: "writing", label: "Writing",          color: NAVY,      bg: "#EFF6FF" },
];

function detectStage(p) {
  if (p.analysis_methods?.trim()) return STAGES[6]; // Writing
  if (p.methodology?.trim())      return STAGES[4]; // Research Design
  if ((p.research_questions || []).length > 0) return STAGES[3]; // Lit Review
  if (p.research_gap?.trim() || (p.objectives || []).length > 0) return STAGES[2]; // Scoping
  if (p.description?.trim())      return STAGES[1]; // Ideation
  return STAGES[0]; // Draft
}

function getCompleteness(p) {
  const checks = [
    !!p.title?.trim(),
    !!p.description?.trim(),
    !!p.research_gap?.trim(),
    (p.objectives || []).length > 0,
    (p.research_questions || []).length > 0,
    !!p.methodology?.trim(),
    (p.keywords || []).length > 0,
    !!p.analysis_methods?.trim(),
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

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

// ─── Source badge ─────────────────────────────────────────────────────────────
const SOURCE_META = {
  gap_finder:  { label: "Via Gap Finder",  color: "#7C3AED" },
  collab_intel: { label: "Via Collab AI",  color: "#0891B2" },
};

// ─── Projects Page ────────────────────────────────────────────────────────────

export default function Projects() {
  const { user } = useAuth();
  const [items, setItems]     = useState(null);
  const [showNew, setShowNew] = useState(false);
  const [newTitle, setNewTitle]   = useState("");
  const [newDesc, setNewDesc]     = useState("");
  const [newVis, setNewVis]       = useState("team");
  const [creating, setCreating]   = useState(false);
  const [q, setQ]                 = useState("");
  const [stageFilter, setStageFilter] = useState("");
  const [visFilter, setVisFilter]     = useState("");

  const load = async () => {
    try {
      const { data } = await api.get("/projects");
      setItems(data || []);
    } catch {
      setItems([]);
    }
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      await api.post("/projects", {
        title: newTitle.trim(),
        description: newDesc.trim(),
        visibility: newVis,
      });
      setNewTitle(""); setNewDesc(""); setNewVis("team"); setShowNew(false);
      toast.success("Project created successfully.");
      load();
    } catch {
      toast.error("Failed to create project.");
    } finally {
      setCreating(false);
    }
  };

  // Client-side filtering
  const filtered = useMemo(() => {
    if (!items) return [];
    return items.filter((p) => {
      const text = (p.title + " " + p.description + " " + (p.keywords || []).join(" ")).toLowerCase();
      if (q && !text.includes(q.toLowerCase())) return false;
      if (visFilter && p.visibility !== visFilter) return false;
      if (stageFilter) {
        const stage = detectStage(p);
        if (stage.key !== stageFilter) return false;
      }
      return true;
    });
  }, [items, q, stageFilter, visFilter]);

  // Portfolio stats
  const stats = useMemo(() => {
    if (!items) return null;
    const uid = user?.id;
    return {
      total:         items.length,
      owned:         items.filter((p) => p.owner_id === uid).length,
      collab:        items.filter((p) => p.owner_id !== uid).length,
      advanced:      items.filter((p) => p.methodology?.trim()).length,
    };
  }, [items, user]);

  if (items === null) return <SkeletonPage />;

  const firstName = user?.full_name?.split(" ")[0] || "Researcher";

  const statsMeta = stats && stats.total > 0 ? (
    <div style={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
      {[
        { label: "Total Projects",  value: stats.total,    icon: FolderOpen },
        { label: "My Projects",     value: stats.owned,    icon: Target },
        { label: "Collaborations",  value: stats.collab,   icon: Users },
        { label: "Advanced Stage",  value: stats.advanced, icon: TrendingUp },
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
      title="Research Projects"
      subtitle={`${getGreeting()}, ${firstName}. From question to publication — every study starts here.`}
      actions={
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <Button as={Link} to="/collaboration-intelligence" variant="ghost" size="sm">
            <BrainCircuit size={12} strokeWidth={1.5} />
            Find Collaborators
          </Button>
          <Button
            data-testid={TID.projectCreateBtn}
            onClick={() => setShowNew((v) => !v)}
            variant="primary"
            size="sm"
          >
            <Plus size={13} strokeWidth={2} />
            New Project
          </Button>
        </div>
      }
      meta={statsMeta}
    >

      {/* ── CREATE FORM ──────────────────────────────────────────────────── */}
      {showNew && (
        <Card padding="xl" style={{ marginTop: 24, maxWidth: 640 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 18 }}>
            New Research Project
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <Input
              label="Project title *"
              placeholder="e.g. Climate impact on neurological development"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && create()}
              autoFocus
            />
            <Textarea
              label="Description (optional)"
              rows={3}
              placeholder="Brief description of your research scope and goals"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
            />
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 6 }}>Visibility</label>
              <div style={{ display: "flex", gap: 8 }}>
                {[
                  { val: "private", label: "Private", icon: Lock, desc: "Only you" },
                  { val: "team",    label: "Team",    icon: Users, desc: "Members only" },
                  { val: "public",  label: "Open",    icon: Globe, desc: "Discoverable" },
                ].map(({ val, label, icon: Icon, desc }) => (
                  <button
                    key={val}
                    onClick={() => setNewVis(val)}
                    style={{
                      flex: 1, padding: "10px 12px", border: `1px solid ${newVis === val ? NAVY : BORDER}`,
                      background: newVis === val ? WARM : "white", cursor: "pointer", textAlign: "center",
                    }}
                  >
                    <Icon size={14} strokeWidth={1.5} style={{ color: newVis === val ? NAVY : "#94A3B8", margin: "0 auto 4px" }} />
                    <div style={{ fontSize: 12, fontWeight: 600, color: newVis === val ? NAVY : "#374151" }}>{label}</div>
                    <div style={{ fontSize: 10, color: "#94A3B8", marginTop: 2 }}>{desc}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
            <Button onClick={create} disabled={creating || !newTitle.trim()} loading={creating}>
              Create project
            </Button>
            <Button variant="ghost" onClick={() => { setShowNew(false); setNewTitle(""); setNewDesc(""); setNewVis("team"); }}>
              Cancel
            </Button>
          </div>
        </Card>
      )}

      {/* ── SEARCH + FILTER ──────────────────────────────────────────────── */}
      {items.length > 0 && (
        <div style={{ marginTop: 24, marginBottom: 20 }}>
          <div style={{ marginBottom: 10 }}>
            <SearchBar
              value={q}
              onChange={setQ}
              placeholder="Search projects, keywords…"
              onClear={() => setQ("")}
            />
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <FilterChip label="All stages" active={!stageFilter} onClick={() => setStageFilter("")} />
            {STAGES.map((s) => (
              <FilterChip
                key={s.key}
                label={s.label}
                active={stageFilter === s.key}
                onClick={() => setStageFilter(stageFilter === s.key ? "" : s.key)}
              />
            ))}
            <span style={{ display: "inline-block", width: 1, background: BORDER, margin: "0 4px" }} />
            {["private", "team", "public"].map((v) => (
              <FilterChip
                key={v}
                label={v.charAt(0).toUpperCase() + v.slice(1)}
                active={visFilter === v}
                onClick={() => setVisFilter(visFilter === v ? "" : v)}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── PROJECT GRID ─────────────────────────────────────────────────── */}
      <div data-testid={TID.projectList}>

        {/* Empty state — no projects at all */}
        {items.length === 0 && (
          <ProjectEmptyState onNew={() => setShowNew(true)} />
        )}

        {/* Filtered empty */}
        {items.length > 0 && filtered.length === 0 && (
          <EmptyState
            icon={<Search size={24} />}
            title="No projects match your filters"
            description="Try adjusting or clearing your search."
            action={
              <Button
                variant="outline"
                size="sm"
                onClick={() => { setQ(""); setStageFilter(""); setVisFilter(""); }}
              >
                Clear filters
              </Button>
            }
            size="sm"
            dashed={true}
          />
        )}

        {/* Project cards */}
        {filtered.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
            {filtered.map((p, idx) => (
              <ProjectCard key={p.id} p={p} idx={idx} userId={user?.id} />
            ))}
          </div>
        )}
      </div>

      {/* ── LIFECYCLE GUIDE (shown when projects exist) ───────────────────── */}
      {items.length > 0 && (
        <ResearchLifecycleGuide projects={filtered} />
      )}

      {/* ── QUICK ACTIONS ────────────────────────────────────────────────── */}
      <QuickActions />
    </ResearchLayout>
  );
}

// ─── Project Card ─────────────────────────────────────────────────────────────

function ProjectCard({ p, idx, userId }) {
  const stage      = detectStage(p);
  const complete   = getCompleteness(p);
  const isOwner    = p.owner_id === userId;
  const memberCount = (p.members || []).length;
  const src        = SOURCE_META[p.source];

  const visIcon = p.visibility === "private" ? Lock :
                  p.visibility === "public"  ? Globe : Users;
  const VisIcon = visIcon;

  return (
    <Card
      to={`/projects/${p.id}`}
      data-testid={TID.projectCard(p.id)}
      padding="none"
      style={{ display: "flex", flexDirection: "column" }}
    >
      {/* Stage accent bar */}
      <div style={{ height: 3, background: stage.color, flexShrink: 0 }} />

      <div style={{ padding: "18px 20px", flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Top row: icon + badges */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 14 }}>
          <div style={{ width: 34, height: 34, background: stage.bg, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <FolderOpen size={15} strokeWidth={1.5} style={{ color: stage.color }} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" }}>
            {src && (
              <Badge color={src.color} size="sm">{src.label}</Badge>
            )}
            <Badge variant="outline" size="sm">
              <VisIcon size={9} strokeWidth={1.5} />
              {p.visibility}
            </Badge>
          </div>
        </div>

        {/* Title */}
        <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", margin: "0 0 8px", lineHeight: 1.35, letterSpacing: "-0.015em" }}>
          {p.title}
        </h3>

        {/* Description */}
        {p.description && (
          <p style={{ fontSize: 12, color: "#64748B", margin: "0 0 12px", lineHeight: 1.6, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", flex: "0 0 auto" }}>
            {p.description}
          </p>
        )}

        {/* Keywords */}
        {(p.keywords || []).length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 14 }}>
            {p.keywords.slice(0, 4).map((k) => (
              <Tag key={k} size="sm">{k}</Tag>
            ))}
          </div>
        )}

        {/* Stage badge */}
        <div style={{ marginTop: "auto", marginBottom: 14 }}>
          <Badge color={stage.color} size="sm">{stage.label}</Badge>
        </div>

        {/* Completeness bar */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 5 }}>
            <span style={{ fontSize: 10, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>Profile</span>
            <span style={{ fontSize: 10, fontFamily: "monospace", color: complete >= 75 ? "#10B981" : complete >= 40 ? "#D97706" : "#94A3B8", fontWeight: 600 }}>
              {complete}%
            </span>
          </div>
          <div style={{ height: 3, background: "#E2E8F0", borderRadius: 2 }}>
            <div style={{ height: "100%", width: `${complete}%`, background: complete >= 75 ? "#10B981" : complete >= 40 ? "#D97706" : "#94A3B8", borderRadius: 2, transition: "width 0.6s ease" }} />
          </div>
        </div>

        {/* Footer */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 12, borderTop: `1px solid ${BORDER}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "#94A3B8" }}>
              <Users size={10} strokeWidth={1.5} />
              {memberCount} {memberCount === 1 ? "member" : "members"}
            </span>
            {!isOwner && (
              <Badge variant="purple" size="sm">Collab</Badge>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {p.created_at && (
              <span style={{ fontSize: 10, color: "#CBD5E1", fontFamily: "monospace" }}>{fmtDate(p.created_at)}</span>
            )}
            <ChevronRight size={12} strokeWidth={1.5} style={{ color: "#CBD5E1" }} />
          </div>
        </div>
      </div>
    </Card>
  );
}

// ─── Research Lifecycle Guide ─────────────────────────────────────────────────

function ResearchLifecycleGuide({ projects }) {
  const stageCounts = useMemo(() => {
    const counts = {};
    projects.forEach((p) => {
      const s = detectStage(p);
      counts[s.key] = (counts[s.key] || 0) + 1;
    });
    return counts;
  }, [projects]);

  if (!projects.length) return null;

  return (
    <div style={{ marginTop: 36, paddingTop: 24, borderTop: `1px solid ${BORDER}` }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 14 }}>
        Research Lifecycle — Portfolio Overview
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 0, overflowX: "auto" }}>
        {STAGES.map((s, i) => {
          const count = stageCounts[s.key] || 0;
          return (
            <React.Fragment key={s.key}>
              <div style={{ textAlign: "center", padding: "12px 16px", background: count > 0 ? s.bg : WARM, border: `1px solid ${count > 0 ? s.color + "40" : BORDER}`, minWidth: 110, flexShrink: 0 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: count > 0 ? s.color : "#CBD5E1", fontFamily: "monospace" }}>{count}</div>
                <div style={{ fontSize: 10, fontWeight: 600, color: count > 0 ? s.color : "#CBD5E1", textTransform: "uppercase", letterSpacing: "0.07em", marginTop: 4 }}>
                  {s.label}
                </div>
              </div>
              {i < STAGES.length - 1 && (
                <div style={{ width: 20, height: 1, background: BORDER, flexShrink: 0 }} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

// ─── Quick Actions ────────────────────────────────────────────────────────────

function QuickActions() {
  const actions = [
    { label: "AI Research Assistant",  to: "/ai",                         icon: BrainCircuit, desc: "Chat with Synaptiq AI about your research" },
    { label: "Literature Review",      to: "/literature-review",          icon: BookMarked,   desc: "AI-powered literature synthesis" },
    { label: "Research Gap Finder",    to: "/research-gap-finder",        icon: Target,       desc: "Identify gaps in your field" },
    { label: "Find Collaborators",     to: "/collaboration-intelligence", icon: Users,        desc: "AI-matched co-author suggestions" },
    { label: "Manuscript Review",      to: "/manuscript-review",          icon: FileText,     desc: "Get structured feedback on your paper" },
    { label: "Research Workspaces",    to: "/workspaces",                 icon: Layers,       desc: "Shared workspaces for your team" },
  ];

  return (
    <div style={{ marginTop: 36, paddingTop: 24, borderTop: `1px solid ${BORDER}` }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 14 }}>
        Research Tools
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
        {actions.map(({ label, to, icon: Icon, desc }) => (
          <Card key={to} to={to} padding="md" style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
            <div style={{ width: 30, height: 30, background: WARM, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Icon size={13} strokeWidth={1.5} style={{ color: NAVY }} />
            </div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#0f172a", marginBottom: 3 }}>{label}</div>
              <div style={{ fontSize: 11, color: "#94A3B8", lineHeight: 1.4 }}>{desc}</div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function ProjectEmptyState({ onNew }) {
  return (
    <div style={{ marginTop: 28 }}>
      <EmptyState
        icon={<FolderOpen strokeWidth={0.75} />}
        title="Start your first research project"
        description="Projects are your research command centers — each one integrates AI tools, team collaboration, literature, tasks, milestones, and manuscript workflows in one place."
        size="lg"
        className="mb-6"
        action={
          <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
            <Button data-testid={TID.projectCreateBtn} onClick={onNew}>
              <Plus size={13} strokeWidth={2} />
              Create a project
            </Button>
            <Button as={Link} to="/collaborations" variant="ghost">
              Browse collaborations
              <ArrowRight size={12} strokeWidth={1.5} />
            </Button>
          </div>
        }
      />

      {/* Feature highlights */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginTop: 24 }}>
        {[
          { icon: BrainCircuit, title: "AI-powered research",  desc: "From literature review to manuscript review — AI assists every stage." },
          { icon: Users,        title: "Team collaboration",   desc: "Invite co-investigators, assign tasks, share workspaces seamlessly." },
          { icon: Target,       title: "Full lifecycle",        desc: "Manage from first idea through publication and citation tracking." },
        ].map(({ icon: Icon, title, desc }) => (
          <Card key={title} variant="ghost" padding="md" style={{ background: WARM, border: `1px solid ${BORDER}` }}>
            <div style={{ width: 32, height: 32, background: "white", border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 12 }}>
              <Icon size={14} strokeWidth={1.5} style={{ color: NAVY }} />
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#0f172a", marginBottom: 6 }}>{title}</div>
            <p style={{ fontSize: 12, color: "#64748B", lineHeight: 1.55, margin: 0 }}>{desc}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}


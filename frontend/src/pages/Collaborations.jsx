import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { useAuth } from "../contexts/AuthContext";
import { Avatar } from "@/components/ds/Avatar";
import { userTypeLabel } from "../lib/userTypes";
import { toast } from "sonner";
import { ACCENT, NAVY, WARM, BRD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { SkeletonCard } from "@/components/ds/LoadingState";
import EmptyState from "@/components/ds/EmptyState";
import {
  Search, Plus, Handshake, Users, Check, X, ArrowRight,
  BrainCircuit, Coins, Calendar, FolderOpen, MessageSquare, Send,
  Activity, Globe, FileText, Layers, Zap,
  AlertCircle, Clock, TrendingUp, Sparkles, ChevronRight,
} from "lucide-react";

// ─── Brand tokens ─────────────────────────────────────────────────────────────
const BORDER = "#E4E8EF";

// ─── Constants ────────────────────────────────────────────────────────────────
const TYPES = [
  "Journal Article", "Conference Paper", "Research Project",
  "Book Chapter", "Book", "Grant Proposal",
  "Systematic Review", "Meta-analysis", "Dataset Development",
];
const AREAS = [
  "Artificial Intelligence", "Healthcare", "Management",
  "Economics", "Education", "Public Health",
  "Cybersecurity", "Engineering", "Psychology",
];

const INV_TYPE_LABELS = {
  research_collaboration:    "Research Collaboration",
  project_invitation:        "Project Invitation",
  workspace_invitation:      "Workspace Invitation",
  manuscript_invitation:     "Manuscript Invitation",
  grant_team:                "Grant Team",
  conference_team:           "Conference Team",
  reviewer:                  "Reviewer",
  mentorship:                "Mentorship",
  institutional_collaboration: "Institutional Collaboration",
};

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function fmtDate(d) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function Collaborations() {
  const { user }  = useAuth();
  const navigate  = useNavigate();

  // Open marketplace
  const [items, setItems]     = useState([]);
  const [q, setQ]             = useState("");
  const [type, setType]       = useState("");
  const [area, setArea]       = useState("");
  const [loading, setLoading] = useState(true);

  // Hub data
  const [mine, setMine]         = useState({ active: [], pending: [], completed: [] });
  const [requests, setRequests] = useState([]);
  const [metrics, setMetrics]   = useState(null);
  const [hubLoading, setHubLoading] = useState(true);

  // Fetch open collaborations (marketplace)
  const fetchOpen = async () => {
    setLoading(true);
    try {
      const params = {};
      if (q)    params.q             = q;
      if (type) params.collab_type   = type;
      if (area) params.research_area = area;
      const { data } = await api.get("/collaborations", { params });
      setItems(data || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch hub data (mine, requests, metrics) in parallel
  const fetchHub = () => {
    setHubLoading(true);
    Promise.all([
      api.get("/collaborations/mine")
        .then((r) => setMine(r.data || { active: [], pending: [], completed: [] }))
        .catch(() => {}),
      api.get("/collaboration-requests?kind=received")
        .then((r) => setRequests((r.data || []).filter((req) => req.status === "pending" || req.status === "viewed")))
        .catch(() => {}),
      api.get("/collaboration-requests/metrics")
        .then((r) => setMetrics(r.data))
        .catch(() => {}),
    ]).finally(() => setHubLoading(false));
  };

  useEffect(() => {
    fetchOpen();
    fetchHub();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAccept = async (reqId) => {
    try {
      await api.patch(`/collaboration-requests/${reqId}`, { status: "accepted" });
      setRequests((prev) => prev.filter((r) => r.id !== reqId));
      toast.success("Collaboration accepted — check your workspace.");
    } catch {
      toast.error("Could not accept the request.");
    }
  };

  const handleDecline = async (reqId) => {
    try {
      await api.patch(`/collaboration-requests/${reqId}`, { status: "declined" });
      setRequests((prev) => prev.filter((r) => r.id !== reqId));
      toast.info("Request declined.");
    } catch {
      toast.error("Could not decline the request.");
    }
  };

  const firstName = user?.full_name?.split(" ")[0] || "Researcher";
  const activeCount = mine.active?.length || 0;
  const pendingCount = requests.length;
  const totalProjects = metrics?.total_projects ?? null;
  const acceptedCount = metrics?.requests_accepted ?? null;

  const statsMeta = (
    <div style={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
      {[
        { label: "Active Collaborations", value: hubLoading ? "…" : activeCount,   icon: Users,      highlight: false },
        { label: "Pending Invitations",   value: hubLoading ? "…" : pendingCount,  icon: Clock,      highlight: pendingCount > 0 },
        { label: "Accepted Requests",     value: hubLoading ? "…" : acceptedCount, icon: Check,      highlight: false },
        { label: "Research Projects",     value: hubLoading ? "…" : totalProjects, icon: FolderOpen, highlight: false },
      ].map(({ label, value, icon: Icon, highlight }) => (
        <div key={label} style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 10px", border: `1px solid ${highlight ? "#FECDD3" : BRD}`, background: highlight ? "#FFF1F2" : "#F8FAFC" }}>
          <Icon size={11} strokeWidth={1.5} style={{ color: highlight ? "#E11D48" : "#94A3B8" }} />
          <span style={{ fontSize: 11, color: "#64748B" }}>{label}:</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: highlight ? "#E11D48" : NAVY, fontFamily: "monospace" }}>{value ?? "—"}</span>
        </div>
      ))}
    </div>
  );

  return (
    <ResearchLayout
      title="Collaboration Hub"
      subtitle="Build your research network. Collaborate globally. Publish together."
      actions={
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <Link to="/collaborations/my" className="flex items-center gap-1.5 border border-slate-200 text-slate-600 text-xs px-3 py-1.5 hover:bg-slate-50 transition-colors">
            <FolderOpen size={12} strokeWidth={1.5} /> My Collaborations
          </Link>
          <Link to="/collaboration-intelligence" className="flex items-center gap-1.5 border border-slate-200 text-slate-600 text-xs px-3 py-1.5 hover:bg-slate-50 transition-colors">
            <BrainCircuit size={12} strokeWidth={1.5} /> Find Researchers
          </Link>
          <button
            data-testid={TID.collabCreateBtn}
            onClick={() => navigate("/collaborations/new")}
            className="flex items-center gap-1.5 bg-[#6B0E28] text-white text-sm px-3 py-1.5 hover:opacity-90 transition-opacity"
          >
            <Plus size={13} strokeWidth={2} /> Post Collaboration
          </button>
        </div>
      }
      meta={statsMeta}
    >

      {/* ── PRIORITY INVITATIONS ───────────────────────────────────────────── */}
      {requests.length > 0 && (
        <div style={{ background: "#FFFBEB", borderLeft: "3px solid #F59E0B", border: "1px solid #FDE68A", borderTop: "none", padding: "18px 20px 16px", marginBottom: 0 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <AlertCircle size={14} strokeWidth={1.5} style={{ color: "#D97706" }} />
              <span style={{ fontSize: 13, fontWeight: 700, color: "#92400E" }}>
                Requires your attention
              </span>
              <span style={{ fontSize: 11, background: "#D97706", color: "white", padding: "1px 7px", fontFamily: "monospace", fontWeight: 600 }}>
                {requests.length}
              </span>
            </div>
            <Link
              to="/collaboration-requests"
              style={{ fontSize: 12, color: "#92400E", textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}
            >
              View all requests <ChevronRight size={12} strokeWidth={2} />
            </Link>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 10 }}>
            {requests.slice(0, 4).map((req) => (
              <InvitationCard
                key={req.id}
                req={req}
                onAccept={() => handleAccept(req.id)}
                onDecline={() => handleDecline(req.id)}
              />
            ))}
          </div>
          {requests.length > 4 && (
            <div style={{ textAlign: "center", marginTop: 12 }}>
              <Link to="/collaboration-requests" style={{ fontSize: 12, color: "#92400E", textDecoration: "none" }}>
                + {requests.length - 4} more invitation{requests.length - 4 > 1 ? "s" : ""} →
              </Link>
            </div>
          )}
        </div>
      )}

      {/* ── MAIN CONTENT GRID ──────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 28, marginTop: 28, alignItems: "start" }}>

        {/* ── LEFT COLUMN ─────────────────────────────────────────────────── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>

          {/* My Active Collaborations (if any) */}
          {!hubLoading && activeCount > 0 && (
            <section>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14, paddingBottom: 12, borderBottom: `1px solid ${BORDER}` }}>
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 3 }}>My Workspace</div>
                  <h2 style={{ fontSize: 17, fontWeight: 700, color: "#0f172a", margin: 0, letterSpacing: "-0.02em" }}>Active Collaborations</h2>
                </div>
                <Link to="/collaborations/my" style={{ fontSize: 12, color: NAVY, textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}>
                  View all <ChevronRight size={12} strokeWidth={2} />
                </Link>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {mine.active.slice(0, 3).map((c) => (
                  <ActiveCollabCard key={c.id} c={c} />
                ))}
              </div>
            </section>
          )}

          {/* Marketplace Header + Search */}
          <section>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, paddingBottom: 12, borderBottom: `1px solid ${BORDER}` }}>
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 3 }}>Open Marketplace</div>
                <h2 style={{ fontSize: 17, fontWeight: 700, color: "#0f172a", margin: 0, letterSpacing: "-0.02em" }}>Open Collaborations</h2>
              </div>
              <button
                onClick={() => navigate("/collaborations/new")}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", border: "none", padding: "7px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}
                onMouseEnter={(e) => e.currentTarget.style.background = "#1a3d65"}
                onMouseLeave={(e) => e.currentTarget.style.background = NAVY}
              >
                <Plus size={12} strokeWidth={2} />
                Post opportunity
              </button>
            </div>

            {/* Search + Filters */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto auto", gap: 8, marginBottom: 16 }}>
              <div style={{ position: "relative" }}>
                <Search size={13} strokeWidth={1.5} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "#94A3B8" }} />
                <input
                  data-testid={TID.collabSearch}
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") fetchOpen(); }}
                  placeholder="Search title, description…"
                  style={{ width: "100%", paddingLeft: 32, paddingRight: 12, paddingTop: 8, paddingBottom: 8, border: `1px solid ${BORDER}`, background: "white", fontSize: 13, color: "#374151", outline: "none", boxSizing: "border-box" }}
                  onFocus={(e) => e.currentTarget.style.borderColor = NAVY + "80"}
                  onBlur={(e) => e.currentTarget.style.borderColor = BORDER}
                />
              </div>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                style={{ padding: "8px 12px", border: `1px solid ${BORDER}`, background: "white", fontSize: 12, color: "#374151", cursor: "pointer" }}
              >
                <option value="">All types</option>
                {TYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
              <select
                value={area}
                onChange={(e) => setArea(e.target.value)}
                style={{ padding: "8px 12px", border: `1px solid ${BORDER}`, background: "white", fontSize: 12, color: "#374151", cursor: "pointer" }}
              >
                <option value="">All areas</option>
                {AREAS.map((a) => <option key={a}>{a}</option>)}
              </select>
              <button
                onClick={fetchOpen}
                style={{ padding: "8px 14px", background: WARM, border: `1px solid ${BORDER}`, fontSize: 12, fontWeight: 600, color: NAVY, cursor: "pointer" }}
                onMouseEnter={(e) => e.currentTarget.style.background = "#E4E8EF"}
                onMouseLeave={(e) => e.currentTarget.style.background = WARM}
              >
                Search
              </button>
            </div>

            {/* Collaborations List */}
            <div data-testid={TID.collabList} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {loading && (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {[1, 2, 3].map((i) => <SkeletonCard key={i} rows={3} />)}
                </div>
              )}
              {!loading && items.length === 0 && (
                <EmptyState
                  icon={<Handshake />}
                  title={q || type || area ? "No matches for your filters" : "No open collaborations yet"}
                  description={
                    q || type || area
                      ? "Try removing a filter or clearing the search to see all open opportunities."
                      : "Post the first open collaboration — describe your project, the skills you need, and the team you're building."
                  }
                  action={
                    (q || type || area) ? (
                      <button
                        onClick={() => { setQ(""); setType(""); setArea(""); }}
                        style={{ fontSize: 12, color: NAVY, background: "white", border: `1px solid ${BORDER}`, padding: "7px 16px", cursor: "pointer" }}
                      >
                        Clear filters
                      </button>
                    ) : (
                      <button
                        data-testid={TID.collabCreateBtn}
                        onClick={() => navigate("/collaborations/new")}
                        style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", border: "none", padding: "9px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
                      >
                        <Plus size={13} strokeWidth={2} />
                        Post a collaboration
                      </button>
                    )
                  }
                  size="md"
                  dashed={true}
                />
              )}
              {items.map((c) => (
                <CollabCard key={c.id} c={c} />
              ))}
            </div>
          </section>
        </div>

        {/* ── RIGHT SIDEBAR ───────────────────────────────────────────────── */}
        <aside style={{ display: "flex", flexDirection: "column", gap: 24 }}>

          {/* Metrics panel */}
          {metrics && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#64748B", marginBottom: 12, paddingBottom: 10, borderBottom: `1px solid ${BORDER}` }}>
                Your Activity
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                {[
                  { label: "Requests sent",    value: metrics.requests_sent,     icon: Send      },
                  { label: "Received",         value: metrics.requests_received,  icon: Users     },
                  { label: "Accepted",         value: metrics.requests_accepted,  icon: Check     },
                  { label: "Projects",         value: metrics.total_projects,     icon: FolderOpen },
                ].map(({ label, value, icon: Icon }) => (
                  <div key={label} style={{ background: WARM, border: `1px solid ${BORDER}`, padding: "12px 14px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 6 }}>
                      <Icon size={11} strokeWidth={1.5} style={{ color: "#94A3B8" }} />
                      <span style={{ fontSize: 10, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600 }}>{label}</span>
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 700, color: "#0f172a", fontFamily: "monospace" }}>{value ?? 0}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Actions */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#64748B", marginBottom: 12, paddingBottom: 10, borderBottom: `1px solid ${BORDER}` }}>
              Quick Actions
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
              {[
                { label: "Collaboration Intelligence",  to: "/collaboration-intelligence", icon: BrainCircuit, desc: "AI-matched co-author suggestions" },
                { label: "Browse Researchers",          to: "/network",                    icon: Users,       desc: "Explore the research network" },
                { label: "Collaboration Requests",      to: "/collaboration-requests",     icon: Send,        desc: "Manage sent & received invitations", badge: pendingCount > 0 ? pendingCount : null },
                { label: "Shared Workspaces",           to: "/workspaces",                 icon: Layers,      desc: "Collaborative project workspaces" },
                { label: "Research Projects",           to: "/projects",                   icon: FolderOpen,  desc: "Manage your active projects" },
                { label: "Research Gap Finder",         to: "/research-gap-finder",        icon: Sparkles,    desc: "Find gaps to drive collaborations" },
              ].map(({ label, to, icon: Icon, desc, badge }) => (
                <Link
                  key={to}
                  to={to}
                  style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 4px", textDecoration: "none", borderBottom: `1px solid ${BORDER}`, transition: "background 0.1s" }}
                  onMouseEnter={(e) => e.currentTarget.style.background = WARM}
                  onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                >
                  <div style={{ width: 30, height: 30, background: WARM, border: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Icon size={13} strokeWidth={1.5} style={{ color: NAVY }} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "#0f172a", display: "flex", alignItems: "center", gap: 6 }}>
                      {label}
                      {badge && (
                        <span style={{ fontSize: 10, background: ACCENT, color: "white", padding: "1px 6px", fontFamily: "monospace" }}>{badge}</span>
                      )}
                    </div>
                    <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 1 }}>{desc}</div>
                  </div>
                  <ArrowRight size={11} strokeWidth={1.5} style={{ color: "#CBD5E1", flexShrink: 0 }} />
                </Link>
              ))}
            </div>
          </div>

          {/* My Collaborations Panel */}
          {!hubLoading && (mine.pending?.length > 0 || mine.completed?.length > 0) && (
            <div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, paddingBottom: 10, borderBottom: `1px solid ${BORDER}` }}>
                <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#64748B" }}>My Status</span>
                <Link to="/collaborations/my" style={{ fontSize: 11, color: NAVY, textDecoration: "none" }}>View all</Link>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {mine.pending?.slice(0, 2).map((c) => (
                  <Link
                    key={c.id}
                    to={`/collaborations/${c.id}`}
                    style={{ display: "block", padding: "10px 12px", border: `1px solid ${BORDER}`, textDecoration: "none", background: "#FFFBEB" }}
                  >
                    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#D97706", marginBottom: 4 }}>Application pending</div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.title}</div>
                    <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 2 }}>{c.research_area}</div>
                  </Link>
                ))}
                {mine.completed?.slice(0, 2).map((c) => (
                  <Link
                    key={c.id}
                    to={`/collaborations/${c.id}`}
                    style={{ display: "block", padding: "10px 12px", border: `1px solid ${BORDER}`, textDecoration: "none", background: WARM }}
                  >
                    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#10B981", marginBottom: 4 }}>Completed</div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.title}</div>
                    <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 2 }}>{c.research_area}</div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Network CTA */}
          <div style={{ background: NAVY, padding: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 8 }}>
              <BrainCircuit size={13} strokeWidth={1.5} style={{ color: "rgba(255,255,255,0.55)" }} />
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" }}>AI Powered</span>
            </div>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: "white", margin: "0 0 6px" }}>Find your ideal collaborators</h3>
            <p style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", lineHeight: 1.55, margin: "0 0 14px" }}>
              Collaboration Intelligence analyses your research profile and surfaces the best co-author matches.
            </p>
            <Link
              to="/collaboration-intelligence"
              style={{ display: "inline-flex", alignItems: "center", gap: 6, background: ACCENT, color: "white", padding: "8px 14px", fontSize: 12, fontWeight: 600, textDecoration: "none" }}
              onMouseEnter={(e) => e.currentTarget.style.background = "#a01a42"}
              onMouseLeave={(e) => e.currentTarget.style.background = ACCENT}
            >
              <Sparkles size={12} strokeWidth={1.5} />
              Match me with researchers
            </Link>
          </div>

        </aside>
      </div>
    </ResearchLayout>
  );
}

// ─── Invitation Card (priority) ───────────────────────────────────────────────

function InvitationCard({ req, onAccept, onDecline }) {
  const [acting, setActing] = useState(false);
  const sender = req.sender_profile || {};
  const invLabel = INV_TYPE_LABELS[req.invitation_type] || "Research Collaboration";

  const act = async (fn) => {
    setActing(true);
    await fn();
    setActing(false);
  };

  return (
    <div style={{ background: "white", border: "1px solid #FDE68A", padding: "14px 16px" }}>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <Avatar url={sender.avatar_url} name={sender.full_name} size={38} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>
                {sender.full_name || "Unknown Researcher"}
              </div>
              <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 2 }}>
                {[userTypeLabel(sender), sender.institution].filter(Boolean).join(" · ")}
              </div>
            </div>
            <span style={{ fontSize: 10, fontFamily: "monospace", fontWeight: 600, color: "#D97706", background: "#FEF3C7", border: "1px solid #FDE68A", padding: "2px 7px", flexShrink: 0, whiteSpace: "nowrap" }}>
              {invLabel}
            </span>
          </div>
          {req.message && (
            <div style={{ fontSize: 12, color: "#475569", marginTop: 8, lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", background: "#FFFBEB", border: "1px solid #FEF3C7", padding: "6px 10px", fontStyle: "italic" }}>
              "{req.message}"
            </div>
          )}
          <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
            <button
              onClick={() => act(onAccept)}
              disabled={acting}
              style={{ display: "inline-flex", alignItems: "center", gap: 5, background: NAVY, color: "white", border: "none", padding: "5px 12px", fontSize: 11, fontWeight: 600, cursor: "pointer", opacity: acting ? 0.6 : 1 }}
            >
              <Check size={10} strokeWidth={2.5} />
              Accept
            </button>
            <button
              onClick={() => act(onDecline)}
              disabled={acting}
              style={{ display: "inline-flex", alignItems: "center", gap: 5, background: "transparent", color: "#6B7280", border: `1px solid ${BORDER}`, padding: "5px 10px", fontSize: 11, fontWeight: 500, cursor: "pointer", opacity: acting ? 0.6 : 1 }}
            >
              <X size={10} strokeWidth={2.5} />
              Decline
            </button>
            {sender.id && (
              <Link
                to={`/messages/${sender.id}`}
                style={{ display: "inline-flex", alignItems: "center", gap: 5, border: `1px solid ${BORDER}`, color: "#6B7280", padding: "5px 10px", fontSize: 11, textDecoration: "none" }}
              >
                <MessageSquare size={10} strokeWidth={1.5} />
                Message
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Active Collaboration Card (compact) ──────────────────────────────────────

function ActiveCollabCard({ c }) {
  const statusColor = c.status === "active" ? "#10B981" : c.status === "open" ? NAVY : "#94A3B8";
  return (
    <Link
      to={`/collaborations/${c.id}`}
      style={{ display: "flex", alignItems: "center", gap: 14, border: `1px solid ${BORDER}`, background: "white", padding: "14px 18px", textDecoration: "none", transition: "border-color 0.15s, box-shadow 0.15s" }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY + "50"; e.currentTarget.style.boxShadow = "0 2px 10px rgba(15,40,71,0.07)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.boxShadow = "none"; }}
    >
      <div style={{ width: 4, height: 44, background: statusColor, flexShrink: 0, borderRadius: 2 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 3 }}>{c.collab_type}</div>
        <div style={{ fontSize: 14, fontWeight: 600, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", letterSpacing: "-0.01em" }}>{c.title}</div>
        <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 2 }}>{c.research_area} {c.duration ? `· ${c.duration}` : ""}</div>
      </div>
      {c.creator && (
        <Avatar url={c.creator.avatar_url} name={c.creator.full_name} size={28} />
      )}
    </Link>
  );
}

// ─── Collaboration Marketplace Card ───────────────────────────────────────────

function CollabCard({ c }) {
  return (
    <Link
      to={`/collaborations/${c.id}`}
      data-testid={TID.collabCard(c.id)}
      style={{ display: "block", border: `1px solid ${BORDER}`, background: "white", padding: "20px 22px", textDecoration: "none", transition: "border-color 0.15s, box-shadow 0.15s" }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = NAVY + "55"; e.currentTarget.style.boxShadow = "0 2px 14px rgba(15,40,71,0.08)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.boxShadow = "none"; }}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 20, alignItems: "start" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: NAVY, marginBottom: 8 }}>
            {c.collab_type}
          </div>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", margin: "0 0 8px", lineHeight: 1.35, letterSpacing: "-0.02em" }}>
            {c.title}
          </h3>
          <p style={{ fontSize: 13, color: "#64748B", margin: "0 0 12px", lineHeight: 1.6, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
            {c.description}
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
            {(c.skills_needed || []).slice(0, 5).map((s) => (
              <span key={s} style={{ fontSize: 11, padding: "3px 8px", background: WARM, color: "#475569", border: `1px solid ${BORDER}` }}>{s}</span>
            ))}
          </div>
          {c.creator && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, paddingTop: 12, borderTop: `1px solid ${BORDER}` }}>
              <Avatar url={c.creator.avatar_url} name={c.creator.full_name} size={24} />
              <div style={{ fontSize: 12, color: "#374151" }}>
                <span style={{ fontWeight: 500 }}>{c.creator.full_name || "Anonymous"}</span>
                {c.creator.institution && <span style={{ color: "#94A3B8" }}> · {c.creator.institution}</span>}
              </div>
            </div>
          )}
        </div>
        <div style={{ textAlign: "right", fontSize: 12, color: "#94A3B8", whiteSpace: "nowrap", flexShrink: 0 }}>
          {c.research_area && (
            <div style={{ fontFamily: "monospace", fontSize: 11, color: "#64748B", marginBottom: 8 }}>{c.research_area}</div>
          )}
          {c.team_size && (
            <div style={{ marginBottom: 4 }}>
              <span style={{ color: "#94A3B8" }}>Team: </span>
              <span style={{ color: "#374151", fontWeight: 500 }}>{c.team_size}</span>
            </div>
          )}
          {c.duration && (
            <div style={{ marginBottom: 4 }}>
              <span style={{ color: "#94A3B8" }}>Duration: </span>
              <span style={{ color: "#374151", fontWeight: 500 }}>{c.duration}</span>
            </div>
          )}
          {c.funding_status && c.funding_status !== "—" && (
            <div>
              <span style={{ color: "#94A3B8" }}>Funding: </span>
              <span style={{ color: "#374151", fontWeight: 500 }}>{c.funding_status}</span>
            </div>
          )}
          <div style={{ marginTop: 12 }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, color: NAVY, fontWeight: 600 }}>
              View details <ArrowRight size={10} strokeWidth={2} />
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}

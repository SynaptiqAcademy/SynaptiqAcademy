import React, { useEffect, useState, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { useAuth } from "../contexts/AuthContext";
import { Avatar } from "@/components/ds/Avatar";
import { userTypeLabel } from "../lib/userTypes";
import { toast } from "sonner";
import { NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { SkeletonCard } from "@/components/ds/LoadingState";
import EmptyState from "@/components/ds/EmptyState";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Tag } from "@/components/ds/Tag";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { FormSelect } from "@/components/ds/FormSelect";
import { Alert } from "@/components/ds/Alert";
import {
  Search, X, Plus, Handshake, Check, ArrowRight,
  BrainCircuit, MessageSquare,
  AlertCircle, ChevronRight,
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
  const explorerRef = useRef(null);

  // Open marketplace
  const [items, setItems]     = useState([]);
  const [q, setQ]             = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [type, setType]       = useState("");
  const [area, setArea]       = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [loading, setLoading] = useState(true);

  // Hub data
  const [mine, setMine]         = useState({ active: [], pending: [], completed: [] });
  const [requests, setRequests] = useState([]);
  const [metrics, setMetrics]   = useState(null);
  const [hubLoading, setHubLoading] = useState(true);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 400);
    return () => clearTimeout(t);
  }, [q]);

  // Fetch open collaborations (marketplace)
  const fetchOpen = async () => {
    setLoading(true);
    try {
      const params = {};
      if (debouncedQ) params.q             = debouncedQ;
      if (type)       params.collab_type   = type;
      if (area)       params.research_area = area;
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
    fetchHub();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchOpen();
  }, [debouncedQ, type, area]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const activeCount = mine.active?.length || 0;
  const pendingCount = requests.length;
  const totalProjects = metrics?.total_projects ?? null;
  const acceptedCount = metrics?.requests_accepted ?? null;
  const hasFilters = !!(type || area);

  return (
    <ResearchLayout
      title="Collaborations"
      subtitle="Build your research network. Collaborate globally. Publish together."
      actions={
        <>
          <Button onClick={() => explorerRef.current?.scrollIntoView({ behavior: "smooth" })} size="sm">
            <Search size={13} strokeWidth={2} /> Find Collaborations
          </Button>
          <Button as={Link} to="/collaboration-intelligence" variant="ghost" size="sm">
            <BrainCircuit size={12} strokeWidth={1.5} /> Find Researchers
          </Button>
          <Button
            data-testid={TID.collabCreateBtn}
            onClick={() => navigate("/collaborations/new")}
            size="sm"
          >
            <Plus size={13} strokeWidth={2} /> Post Collaboration
          </Button>
        </>
      }
    >
      {/* ── Stats strip ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 max-w-lg mb-8">
        {[
          { label: "Active",   value: hubLoading ? "—" : activeCount },
          { label: "Pending",  value: hubLoading ? "—" : pendingCount },
          { label: "Accepted", value: hubLoading ? "—" : (acceptedCount ?? "—") },
          { label: "Projects", value: hubLoading ? "—" : (totalProjects ?? "—") },
        ].map(({ label, value }) => (
          <div key={label} className="text-center">
            <div className="font-serif text-3xl text-slate-900">{value}</div>
            <div className="overline mt-1 text-xs">{label}</div>
          </div>
        ))}
      </div>

      {/* ── PRIORITY INVITATIONS ───────────────────────────────────────────── */}
      {requests.length > 0 && (
        <Alert
          variant="warning"
          icon={AlertCircle}
          style={{ marginBottom: 24 }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontWeight: 700 }}>Requires your attention</span>
              <Badge variant="warning" size="sm">{requests.length}</Badge>
            </div>
            <Link
              to="/collaboration-requests"
              style={{ fontSize: 12, color: "#92400E", textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}
            >
              View all requests <ChevronRight size={12} strokeWidth={2} />
            </Link>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 10, marginTop: 6 }}>
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
        </Alert>
      )}

      {/* ── My Active Collaborations (if any) ───────────────────────────────── */}
      {!hubLoading && activeCount > 0 && (
        <section style={{ marginBottom: 32 }}>
          <div className="overline mb-4">My Active Collaborations</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {mine.active.slice(0, 3).map((c) => (
              <ActiveCollabCard key={c.id} c={c} />
            ))}
          </div>
        </section>
      )}

      {/* ── Open Collaborations explorer ────────────────────────────────────── */}
      <div ref={explorerRef} style={{ marginTop: 32 }}>
        <h2 style={{ fontFamily: "Georgia, serif", fontSize: 24, color: NAVY, fontWeight: 400, marginBottom: 14 }}>
          Open Collaborations
        </h2>

        {/* Search + filter toggle */}
        <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
          <div style={{ flex: 1 }}>
            <Input
              data-testid={TID.collabSearch}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search title, description…"
              prefix={<Search size={14} strokeWidth={1.5} />}
              suffix={q && (
                <button
                  type="button"
                  onClick={() => setQ("")}
                  aria-label="Clear search"
                  style={{ color: "#94A3B8", display: "flex", alignItems: "center", background: "none", border: "none", cursor: "pointer", pointerEvents: "auto" }}
                >
                  <X size={13} strokeWidth={1.5} />
                </button>
              )}
            />
          </div>
          <Button
            variant={showFilters ? "primary" : "outline"}
            onClick={() => setShowFilters((v) => !v)}
          >
            Filters{hasFilters ? ` (${[type, area].filter(Boolean).length})` : ""}
          </Button>
        </div>

        {showFilters && (
          <div style={{ marginBottom: 16, background: "white", border: "1px solid #E4E8EF", padding: "16px 14px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <span style={{ fontSize: 10, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.1em" }}>Filters</span>
              {hasFilters && (
                <Button variant="link" onClick={() => { setType(""); setArea(""); }} style={{ fontSize: 10, color: "#94A3B8", textDecoration: "underline" }}>Clear</Button>
              )}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <div>
                <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Type</div>
                <FormSelect size="sm" value={type} onChange={(e) => setType(e.target.value)}>
                  <option value="">All types</option>
                  {TYPES.map((t) => <option key={t}>{t}</option>)}
                </FormSelect>
              </div>
              <div>
                <div style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Research Area</div>
                <FormSelect size="sm" value={area} onChange={(e) => setArea(e.target.value)}>
                  <option value="">All areas</option>
                  {AREAS.map((a) => <option key={a}>{a}</option>)}
                </FormSelect>
              </div>
            </div>
          </div>
        )}

        {/* Count */}
        {!loading && (
          <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 12, fontFamily: "monospace" }}>
            {items.length} open collaboration{items.length !== 1 ? "s" : ""}
          </div>
        )}

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
              title={q || hasFilters ? "No matches for your filters" : "No open collaborations yet"}
              description={
                q || hasFilters
                  ? "Try removing a filter or clearing the search to see all open opportunities."
                  : "Post the first open collaboration — describe your project, the skills you need, and the team you're building."
              }
              action={
                (q || hasFilters) ? (
                  <Button variant="outline" size="sm" onClick={() => { setQ(""); setType(""); setArea(""); }}>
                    Clear filters
                  </Button>
                ) : (
                  <Button data-testid={TID.collabCreateBtn} onClick={() => navigate("/collaborations/new")}>
                    <Plus size={13} strokeWidth={2} />
                    Post a collaboration
                  </Button>
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
    <Card padding="sm" style={{ border: "1px solid #FDE68A" }}>
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
            <Badge variant="warning" size="sm" className="shrink-0 whitespace-nowrap">
              {invLabel}
            </Badge>
          </div>
          {req.message && (
            <div style={{ fontSize: 12, color: "#475569", marginTop: 8, lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", background: "#FFFBEB", border: "1px solid #FEF3C7", padding: "6px 10px", fontStyle: "italic" }}>
              "{req.message}"
            </div>
          )}
          <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
            <Button size="sm" onClick={() => act(onAccept)} disabled={acting} loading={acting}>
              <Check size={10} strokeWidth={2.5} />
              Accept
            </Button>
            <Button variant="ghost" size="sm" onClick={() => act(onDecline)} disabled={acting}>
              <X size={10} strokeWidth={2.5} />
              Decline
            </Button>
            {sender.id && (
              <Button as={Link} to={`/messages/${sender.id}`} variant="ghost" size="sm">
                <MessageSquare size={10} strokeWidth={1.5} />
                Message
              </Button>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

// ─── Active Collaboration Card (compact) ──────────────────────────────────────

function ActiveCollabCard({ c }) {
  const statusColor = c.status === "active" ? "#10B981" : c.status === "open" ? NAVY : "#94A3B8";
  return (
    <Card to={`/collaborations/${c.id}`} padding="md" style={{ display: "flex", alignItems: "center", gap: 14 }}>
      <div style={{ width: 4, height: 44, background: statusColor, flexShrink: 0, borderRadius: 2 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 3 }}>{c.collab_type}</div>
        <div style={{ fontSize: 14, fontWeight: 600, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", letterSpacing: "-0.01em" }}>{c.title}</div>
        <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 2 }}>{c.research_area} {c.duration ? `· ${c.duration}` : ""}</div>
      </div>
      {c.creator && (
        <Avatar url={c.creator.avatar_url} name={c.creator.full_name} size={28} />
      )}
    </Card>
  );
}

// ─── Collaboration Marketplace Card ───────────────────────────────────────────

function CollabCard({ c }) {
  return (
    <Card to={`/collaborations/${c.id}`} data-testid={TID.collabCard(c.id)} padding="lg">
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
              <Tag key={s}>{s}</Tag>
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
    </Card>
  );
}

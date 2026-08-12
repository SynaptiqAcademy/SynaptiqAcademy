import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { toast } from "sonner";
import { BRD, BRDH, NAVY, WARM } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import {
  FileText, Plus, ChevronRight, Search, X,
  BookMarked, Microscope, Send, CheckCircle2, XCircle,
  AlertCircle, RotateCcw, FolderOpen,
  Layers, Archive, Coins,
} from "lucide-react";
import { EmptyState } from "@/components/ds/EmptyState";
import { SkeletonPage } from "@/components/ds/LoadingState";
import { SearchBar, FilterChip } from "@/components/ds/SearchBar";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { StatCard } from "@/components/ds/StatCard";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";

// ─── Brand tokens ─────────────────────────────────────────────────────────────
const EMRL  = "#059669";

// ─── Status system ────────────────────────────────────────────────────────────
const STATUS = {
  draft:                 { label: "Draft",           color: "#64748B", bg: "#F8FAFC", border: "#CBD5E1", icon: FileText   },
  internal_review:       { label: "Internal Review", color: "#0369A1", bg: "#EFF6FF", border: "#BAE6FD", icon: AlertCircle },
  ready_for_submission:  { label: "Ready to Submit", color: "#0891B2", bg: "#ECFEFF", border: "#67E8F9", icon: Send       },
  submitted:             { label: "Submitted",       color: "#4338CA", bg: "#EEF2FF", border: "#A5B4FC", icon: Send       },
  under_review:          { label: "Under Review",    color: "#B45309", bg: "#FFFBEB", border: "#FCD34D", icon: AlertCircle },
  major_revision:        { label: "Major Revision",  color: "#C2410C", bg: "#FFF7ED", border: "#FDBA74", icon: RotateCcw  },
  minor_revision:        { label: "Minor Revision",  color: "#B45309", bg: "#FFFBEB", border: "#FCD34D", icon: RotateCcw  },
  revision_requested:    { label: "Revising",        color: "#7C3AED", bg: "#F5F3FF", border: "#C4B5FD", icon: RotateCcw  },
  accepted:              { label: "Accepted",        color: EMRL,      bg: "#ECFDF5", border: "#6EE7B7", icon: CheckCircle2 },
  published:             { label: "Published",       color: "#065F46", bg: "#D1FAE5", border: "#34D399", icon: CheckCircle2 },
  rejected:              { label: "Rejected",        color: "#DC2626", bg: "#FEF2F2", border: "#FCA5A5", icon: XCircle    },
  withdrawn:             { label: "Withdrawn",       color: "#94A3B8", bg: "#F8FAFC", border: "#CBD5E1", icon: XCircle    },
};

const PIPELINE_ORDER = [
  "draft","internal_review","ready_for_submission","submitted",
  "under_review","revision_requested","minor_revision","major_revision","accepted","published",
];

const MS_TYPES = [
  "Journal Article","Conference Paper","Review Paper","Systematic Review",
  "Meta-Analysis","Book Chapter","Research Proposal","Grant Proposal",
  "Doctoral Thesis Chapter","White Paper",
];

// ─── Lifecycle navigation (shared across Publications section) ────────────────
function LifecycleNav({ current }) {
  const steps = [
    { to: "/manuscripts",        label: "Writing"      },
    { to: "/reviews",            label: "Peer Review"  },
    { to: "/publication-hub",    label: "Publishing"   },
    { to: "/repository",         label: "Archive"      },
    { to: "/grant-applications", label: "Applications" },
  ];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
      {steps.map((s, i) => {
        const isCur = s.to === current;
        return (
          <React.Fragment key={s.to}>
            {i > 0 && <ChevronRight size={10} strokeWidth={1.5} style={{ color: "#CBD5E1", flexShrink: 0 }} />}
            <Link
              to={s.to}
              style={{
                fontSize: 11, fontWeight: isCur ? 700 : 400,
                color: isCur ? NAVY : "#94A3B8",
                padding: "3px 7px",
                background: isCur ? `rgba(15,40,71,0.07)` : "transparent",
                borderRadius: 3, textDecoration: "none",
                letterSpacing: isCur ? "0.02em" : 0,
                whiteSpace: "nowrap",
                transition: "color 150ms",
              }}
            >
              {s.label}
            </Link>
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Status badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const s = STATUS[status] || { label: status || "—", color: "#64748B" };
  return (
    <Badge color={s.color} size="sm" style={{ textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 700, whiteSpace: "nowrap" }}>
      {s.label}
    </Badge>
  );
}

// ─── Pipeline progress strip ──────────────────────────────────────────────────
function PipelineStrip({ status }) {
  const idx = PIPELINE_ORDER.indexOf(status);
  const pct = idx < 0 ? 0 : Math.round(((idx + 1) / PIPELINE_ORDER.length) * 100);
  const color = status === "published" ? EMRL : status === "rejected" ? "#DC2626" : NAVY;
  return (
    <div style={{ height: 2, background: BRD, position: "relative", marginTop: 10 }}>
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${pct}%`, background: color, transition: "width 400ms ease" }} />
    </div>
  );
}

// ─── Skeleton ────────────────────────────────────────────────────────────────
function Skeleton() {
  return (
    <>
      <style>{`@keyframes rl-pulse{0%,100%{opacity:.45}50%{opacity:.2}}.rl-skel{background:#E2E8F0;animation:rl-pulse 1.8s ease-in-out infinite}`}</style>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {[1,2,3].map((i) => (
          <div key={i} className="rl-skel" style={{ height: 100, borderRadius: 2 }} />
        ))}
      </div>
    </>
  );
}

// ─── Manuscript card ──────────────────────────────────────────────────────────
function ManuscriptCard({ m }) {
  const [hov, setHov] = useState(false);
  return (
    <Card
      to={`/manuscripts/${m.id}`}
      data-testid={TID.manuscriptCard(m.id)}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      padding="lg"
      style={{
        borderColor: hov ? BRDH : BRD,
        boxShadow: hov ? "0 4px 20px rgba(15,23,42,0.09)" : "none",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 20, justifyContent: "space-between" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94A3B8" }}>
              {m.manuscript_type}
            </span>
            {m.current_version > 0 && (
              <span style={{ fontSize: 10, fontFamily: "monospace", color: "#CBD5E1", paddingLeft: 8, borderLeft: `1px solid ${BRD}` }}>
                v{m.current_version}
              </span>
            )}
          </div>
          <h3 style={{
            fontSize: 15, fontWeight: 600, color: hov ? NAVY : "#0F172A",
            lineHeight: 1.4, margin: 0, transition: "color 180ms",
          }}>
            {m.title || "Untitled"}
          </h3>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8, flexWrap: "wrap" }}>
            {m.authors?.length > 0 && (
              <span style={{ fontSize: 11, color: "#94A3B8", fontFamily: "monospace" }}>
                {m.authors.length} author{m.authors.length !== 1 ? "s" : ""}
              </span>
            )}
            {m.target_journal?.title && (
              <span style={{ fontSize: 11, color: "#64748B" }}>
                → <strong style={{ fontWeight: 600, color: "#475569" }}>{m.target_journal.title}</strong>
                {m.target_journal.quartile && <span style={{ color: "#94A3B8" }}> · {m.target_journal.quartile}</span>}
              </span>
            )}
            {m.updated_at && (
              <span style={{ fontSize: 10, color: "#CBD5E1", fontFamily: "monospace" }}>
                {new Date(m.updated_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
              </span>
            )}
          </div>
          <PipelineStrip status={m.status} />
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8, flexShrink: 0 }}>
          <StatusBadge status={m.status} />
          <ChevronRight size={14} strokeWidth={1.5} style={{ color: hov ? NAVY : "#E2E8F0", transition: "color 150ms" }} />
        </div>
      </div>
    </Card>
  );
}

// ─── New manuscript form ──────────────────────────────────────────────────────
function NewManuscriptForm({ projects, workspaces, onCreated, onCancel }) {
  const [form, setForm] = useState({
    title: "", abstract: "", manuscript_type: "Journal Article",
    project_id: "", workspace_id: "",
  });
  const [busy, setBusy] = useState(false);
  const titleRef = useRef(null);
  useEffect(() => { titleRef.current?.focus(); }, []);

  const create = async () => {
    if (!form.title.trim()) return;
    setBusy(true);
    try {
      await api.post("/manuscripts", form);
      toast.success("Manuscript created");
      onCreated();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed to create"); }
    finally { setBusy(false); }
  };

  return (
    <Card padding="lg" style={{ maxWidth: 680 }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 16 }}>
        New Manuscript
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <Input
          ref={titleRef}
          data-testid={TID.manuscriptNewTitle}
          placeholder="Manuscript title *"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          onKeyDown={(e) => e.key === "Enter" && create()}
        />
        <Textarea
          placeholder="Abstract (optional)"
          value={form.abstract}
          onChange={(e) => setForm({ ...form, abstract: e.target.value })}
          rows={3}
        />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <FormSelect value={form.manuscript_type} onChange={(e) => setForm({ ...form, manuscript_type: e.target.value })}>
            {MS_TYPES.map((t) => <option key={t}>{t}</option>)}
          </FormSelect>
          <FormSelect value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })}>
            <option value="">No project</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
          </FormSelect>
          <FormSelect value={form.workspace_id} onChange={(e) => setForm({ ...form, workspace_id: e.target.value })}>
            <option value="">No workspace</option>
            {workspaces.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </FormSelect>
        </div>
      </div>
      <div style={{ marginTop: 20, display: "flex", gap: 10 }}>
        <Button
          data-testid={TID.manuscriptNewSubmit}
          onClick={create}
          disabled={busy || !form.title.trim()}
          loading={busy}
          variant="primary"
        >
          {busy ? "Creating…" : "Create manuscript"}
        </Button>
        <Button onClick={onCancel} variant="ghost">
          Cancel
        </Button>
      </div>
    </Card>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function Manuscripts() {
  const [items, setItems]       = useState(null);
  const [projects, setProjects] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [showNew, setShowNew]   = useState(false);
  const [filterStatus, setFilterStatus] = useState("");
  const [q, setQ]               = useState("");

  const load = async () => {
    try {
      const [m, p, w] = await Promise.all([
        api.get("/manuscripts"),
        api.get("/projects"),
        api.get("/workspaces"),
      ]);
      setItems(m.data || []);
      setProjects(p.data || []);
      setWorkspaces(w.data || []);
    } catch { setItems([]); }
  };
  useEffect(() => { load(); }, []);

  if (items === null) {
    return <SkeletonPage />;
  }

  const filtered = items.filter((m) => {
    if (filterStatus && m.status !== filterStatus) return false;
    if (q && !m.title?.toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });

  const activeStatuses = [...new Set(items.map((m) => m.status).filter(Boolean))];

  const counts = {
    total:     items.length,
    drafts:    items.filter((m) => m.status === "draft").length,
    active:    items.filter((m) => ["submitted","under_review","revision_requested","minor_revision","major_revision"].includes(m.status)).length,
    accepted:  items.filter((m) => m.status === "accepted").length,
    published: items.filter((m) => m.status === "published").length,
  };

  const priority = filtered.filter((m) =>
    ["under_review","revision_requested","major_revision","minor_revision","ready_for_submission"].includes(m.status)
  );
  const rest = filtered.filter((m) => !priority.includes(m));

  const actions = (
    <div style={{ display: "flex", gap: 8 }}>
      <Button as={Link} to="/manuscript-review" variant="outline" size="sm">
        <Microscope size={12} strokeWidth={1.5} /> AI Review
      </Button>
      <Button as={Link} to="/publication-hub" variant="outline" size="sm">
        <Layers size={12} strokeWidth={1.5} /> Publication Hub
      </Button>
      <Button
        data-testid={TID.manuscriptCreateBtn}
        onClick={() => setShowNew(true)}
        variant="primary"
        size="sm"
      >
        <Plus size={13} strokeWidth={1.5} /> New Manuscript
      </Button>
    </div>
  );

  return (
    <ResearchLayout
      title="Manuscripts"
      subtitle="From blank page to publication. Track every manuscript through drafting, review, revision, and acceptance."
      nav={<LifecycleNav current="/manuscripts" />}
      actions={actions}
    >
      <style>{`
        @keyframes rl-pulse{0%,100%{opacity:.45}50%{opacity:.2}}
        .rl-skel{background:#E2E8F0;animation:rl-pulse 1.8s ease-in-out infinite}
        .rl-action:hover{text-decoration:underline}
      `}</style>
      <div style={{ padding: "0 0 64px" }}>
        {/* ── Stats ─────────────────────────────────────────────────────── */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 28 }}>
          <StatCard label="Total"     value={counts.total}     icon={<FileText size={13} strokeWidth={1.5} style={{ color: "#CBD5E1" }} />} />
          <StatCard label="Drafting"  value={counts.drafts}    icon={<BookMarked size={13} strokeWidth={1.5} style={{ color: "#CBD5E1" }} />} />
          <StatCard label="Active"    value={counts.active}    icon={<Send size={13} strokeWidth={1.5} style={{ color: "#B45309" }} />} />
          <StatCard label="Accepted"  value={counts.accepted}  icon={<CheckCircle2 size={13} strokeWidth={1.5} style={{ color: EMRL }} />} />
          <StatCard label="Published" value={counts.published} icon={<CheckCircle2 size={13} strokeWidth={1.5} style={{ color: EMRL }} />} />
        </div>

        {/* ── New manuscript form ────────────────────────────────────────── */}
        {showNew && (
          <div style={{ marginBottom: 28 }}>
            <NewManuscriptForm
              projects={projects}
              workspaces={workspaces}
              onCreated={() => { setShowNew(false); load(); }}
              onCancel={() => setShowNew(false)}
            />
          </div>
        )}

        {/* ── Search + filters ───────────────────────────────────────────── */}
        {items.length > 0 && (
          <div style={{ display: "flex", gap: 12, marginBottom: 20, alignItems: "center", flexWrap: "wrap" }}>
            <div style={{ flex: "0 0 260px" }}>
              <SearchBar
                value={q}
                onChange={setQ}
                placeholder="Search manuscripts…"
                onClear={() => setQ("")}
                size="sm"
              />
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <FilterChip
                label="All"
                active={!filterStatus}
                onClick={() => setFilterStatus("")}
              />
              {activeStatuses.map((s) => {
                const st = STATUS[s];
                return (
                  <FilterChip
                    key={s}
                    label={st?.label || s}
                    active={filterStatus === s}
                    onClick={() => setFilterStatus(filterStatus === s ? "" : s)}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* ── Priority manuscripts ───────────────────────────────────────── */}
        {priority.length > 0 && (
          <div style={{ marginBottom: 28 }}>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#B45309", marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
              <AlertCircle size={11} strokeWidth={2} />
              Needs Attention
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {priority.map((m) => <ManuscriptCard key={m.id} m={m} />)}
            </div>
          </div>
        )}

        {/* ── All other manuscripts ──────────────────────────────────────── */}
        {rest.length > 0 && (
          <div>
            {priority.length > 0 && (
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 12 }}>
                All Manuscripts
              </div>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {rest.map((m) => <ManuscriptCard key={m.id} m={m} />)}
            </div>
          </div>
        )}

        {/* ── Empty states ──────────────────────────────────────────────── */}
        {filtered.length === 0 && items.length === 0 && !showNew && (
          <EmptyState
            icon={<FileText />}
            title="Start your first manuscript"
            description="Track papers from blank page to publication. Each manuscript has version history, co-author management, AI review tools, and journal matching."
            action={
              <Button data-testid={TID.manuscriptCreateBtn} onClick={() => setShowNew(true)} variant="primary">
                <Plus size={14} strokeWidth={1.5} /> Create your first manuscript
              </Button>
            }
            size="lg"
            dashed={false}
          />
        )}
        {filtered.length === 0 && items.length > 0 && (
          <EmptyState
            icon={<Search />}
            title="No manuscripts match your search"
            action={
              <Button onClick={() => { setQ(""); setFilterStatus(""); }} variant="link">
                Clear filters
              </Button>
            }
            size="sm"
          />
        )}

      </div>
    </ResearchLayout>
  );
}

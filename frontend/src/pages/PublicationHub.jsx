import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { toast } from "sonner";
import { BRD, BRDH, NAVY, WARM } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import {
  FileText, Send, Inbox, CheckCircle2, BookOpen,
  CalendarDays, Search, Lock, ChevronRight, ArrowRight,
  Plus, ExternalLink, AlertCircle, XCircle, RotateCcw,
  ClipboardCheck, Archive, Coins, Layers,
} from "lucide-react";
import { EmptyState } from "@/components/ds/EmptyState";
import { SkeletonPage } from "@/components/ds/LoadingState";
import { Badge } from "@/components/ds/Badge";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Input } from "@/components/ds/Input";
import { Tag, TagGroup } from "@/components/ds/Tag";
import { Modal } from "@/components/ds/Modal";
import { StatCard, StatGrid } from "@/components/ds/StatCard";

// ─── Brand tokens ─────────────────────────────────────────────────────────────
const EMRL  = "#059669";

// ─── Stage system ─────────────────────────────────────────────────────────────
const STAGES = [
  { key: "selected",           label: "Selected",     color: "#64748B", bg: "#F8FAFC", border: "#CBD5E1", accent: "#CBD5E1" },
  { key: "ready",              label: "Ready",        color: "#0369A1", bg: "#EFF6FF", border: "#BAE6FD", accent: "#BAE6FD" },
  { key: "submitted",          label: "Submitted",    color: "#4338CA", bg: "#EEF2FF", border: "#A5B4FC", accent: "#A5B4FC" },
  { key: "under_review",       label: "Under Review", color: "#B45309", bg: "#FFFBEB", border: "#FCD34D", accent: "#FCD34D" },
  { key: "revision_requested", label: "Revising",     color: "#7C3AED", bg: "#F5F3FF", border: "#C4B5FD", accent: "#C4B5FD" },
  { key: "accepted",           label: "Accepted",     color: EMRL,      bg: "#ECFDF5", border: "#6EE7B7", accent: "#6EE7B7" },
  { key: "published",          label: "Published",    color: "#065F46", bg: "#D1FAE5", border: "#34D399", accent: "#34D399" },
  { key: "rejected",           label: "Rejected",     color: "#DC2626", bg: "#FEF2F2", border: "#FCA5A5", accent: "#FCA5A5" },
  { key: "withdrawn",          label: "Withdrawn",    color: "#94A3B8", bg: "#F8FAFC", border: "#CBD5E1", accent: "#CBD5E1" },
];

// ─── Lifecycle nav ─────────────────────────────────────────────────────────────
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
                background: isCur ? "rgba(15,40,71,0.07)" : "transparent",
                borderRadius: 3, textDecoration: "none", whiteSpace: "nowrap",
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

// ─── Venue Picker Modal ────────────────────────────────────────────────────────
function VenuePicker({ manuscriptId, onPicked, onClose }) {
  const [kind, setKind] = useState("journal");
  const [q, setQ]       = useState("");
  const [results, setResults] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = setTimeout(async () => {
      if (!q.trim()) { setResults([]); return; }
      try {
        const path = kind === "journal" ? "/journals" : "/conferences";
        const { data } = await api.get(path, { params: { q, page_size: 8 } });
        setResults(data.items || []);
      } catch { setResults([]); }
    }, 250);
    return () => clearTimeout(t);
  }, [q, kind]);

  const pick = async (venue) => {
    setBusy(true);
    try {
      const { data } = await api.post("/publication-hub/submissions", {
        manuscript_id: manuscriptId, venue_kind: kind, venue_id: venue.id, stage: "selected",
      });
      toast.success(`Venue selected: ${kind === "journal" ? venue.title : venue.name}`);
      onPicked?.(data); onClose();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <Modal
      open
      onClose={onClose}
      closeOnOverlay
      title="Select Target Venue"
      description="Publication Hub"
      size="sm"
      className="!max-w-[520px]"
    >
      <div data-testid="venue-picker-modal">
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          {[{k:"journal",label:"Journal",icon:BookOpen},{k:"conference",label:"Conference",icon:CalendarDays}].map(({k,label,icon:Icon}) => (
            <Button
              key={k}
              onClick={() => { setKind(k); setResults([]); setQ(""); }}
              variant={kind === k ? "primary" : "outline"}
              className="flex-1"
            >
              <Icon size={12} strokeWidth={1.5} /> {label}
            </Button>
          ))}
        </div>
        <Input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={`Search ${kind}s…`}
          prefix={<Search size={13} strokeWidth={1.5} />}
          wrapperClassName="mb-3"
        />
        <div style={{ maxHeight: 280, overflowY: "auto", borderTop: q && results.length > 0 ? `1px solid ${BRD}` : "none" }}>
          {q && results.length === 0 && <div style={{ fontSize: 13, color: "#94A3B8", padding: "12px 0" }}>No matches found.</div>}
          {results.map((v) => (
            <button
              key={v.id}
              disabled={busy}
              onClick={() => pick(v)}
              style={{ width: "100%", textAlign: "left", padding: "10px 4px", borderBottom: `1px solid ${BRD}`, background: "none", border: "none", borderBottom: `1px solid ${BRD}`, cursor: "pointer", fontFamily: "inherit" }}
            >
              <div style={{ fontSize: 13, fontWeight: 600, color: "#0F172A" }}>{kind === "journal" ? v.title : v.name}</div>
              <div style={{ fontSize: 10, fontFamily: "monospace", color: "#94A3B8", marginTop: 2 }}>
                {kind === "journal"
                  ? [v.publisher, v.quartile ? v.quartile : null, v.open_access ? "Open Access" : null].filter(Boolean).join(" · ")
                  : [v.acronym, v.submission_deadline ? `deadline ${v.submission_deadline}` : null].filter(Boolean).join(" · ")
                }
              </div>
            </button>
          ))}
        </div>
      </div>
    </Modal>
  );
}

// ─── Pipeline card (kanban item) ──────────────────────────────────────────────
function PipelineCard({ row, onAction }) {
  const m = row.manuscript;
  const s = row.submission;
  const stage = row.stage;
  const cfg = STAGES.find((x) => x.key === stage) || STAGES[0];
  const venueText = s?.venue_snapshot ? (s.venue_snapshot.name || s.venue_snapshot.title || "") + (s.venue_snapshot.quartile ? ` · ${s.venue_snapshot.quartile}` : "") : null;

  return (
    <Card data-testid={TID.pubhubManuscript(m.id)} padding="sm">
      <Link to={`/manuscripts/${m.id}`} style={{ display: "block", textDecoration: "none" }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: "#0F172A", lineHeight: 1.4 }}>{m.title || "Untitled"}</div>
      </Link>
      <div style={{ fontSize: 10, fontFamily: "monospace", color: "#94A3B8", marginTop: 4 }}>
        {m.manuscript_type} · v{m.current_version || 0}
      </div>
      {venueText && (
        <div style={{ marginTop: 6, fontSize: 11, color: "#475569", display: "flex", alignItems: "center", gap: 4 }}>
          {s.venue_kind === "journal" ? <BookOpen size={10} strokeWidth={1.5} /> : <CalendarDays size={10} strokeWidth={1.5} />}
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{venueText}</span>
        </div>
      )}
      <div style={{ marginTop: 10, paddingTop: 8, borderTop: `1px solid ${BRD}`, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
        <Badge color={cfg.color}>{cfg.label}</Badge>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {!s && (
            <Button data-testid={TID.pubhubSelectVenueBtn(m.id)} onClick={() => onAction("pick", row)} variant="link" size="sm" className="!text-[#0F2847]">
              Select venue
            </Button>
          )}
          {s && !["submitted","under_review","accepted","published","rejected"].includes(stage) && (
            <Button data-testid={TID.pubhubSubmitBtn(m.id)} onClick={() => onAction("submit", row)} variant="link" size="sm" className="!text-emerald-600">
              Mark submitted
            </Button>
          )}
          {s && stage === "submitted" && (
            <Button onClick={() => onAction("under_review", row)} variant="link" size="sm" className="!text-amber-700">
              Under review
            </Button>
          )}
          {s && stage === "under_review" && (
            <>
              <Button onClick={() => onAction("accept", row)} variant="link" size="sm" className="!text-emerald-600">Accept</Button>
              <Button onClick={() => onAction("reject", row)} variant="link" size="sm" className="!text-red-600">Reject</Button>
              <Button onClick={() => onAction("revision", row)} variant="link" size="sm" className="!text-violet-600">Revision</Button>
            </>
          )}
          {s && stage === "accepted" && (
            <Button onClick={() => onAction("publish", row)} variant="link" size="sm" className="!text-emerald-800">
              Publish
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}

// ─── ORCID publications section ───────────────────────────────────────────────
function OrcidSection() {
  const [pubs, setPubs]     = useState(null);
  const [status, setStatus] = useState(null);

  useEffect(() => {
    api.get("/orcid/status").then(({ data }) => setStatus(data)).catch(() => {});
    api.get("/orcid/publications?limit=50").then(({ data }) => setPubs(data.results || [])).catch(() => setPubs([]));
  }, []);

  if (!status || !pubs) return null;

  if (!status.connected && pubs.length === 0) {
    return (
      <section data-testid="pubhub-orcid-cta" style={{ marginTop: 40 }}>
        <EmptyState
          icon={<BookOpen />}
          title={
            <>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: NAVY, marginBottom: 8 }}>
                ORCID — Academic Identity
              </div>
              Connect ORCID to import your publications
            </>
          }
          description="Link your ORCID iD in your Academic Passport to auto-import publications, conference papers, and preprints — verified by ORCID, enriched by OpenAlex."
          action={<Button as={Link} to="/academic-passport">Connect ORCID in Academic Passport</Button>}
          size="lg"
        />
      </section>
    );
  }

  return (
    <section data-testid="pubhub-orcid-section" style={{ marginTop: 40 }}>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: EMRL, marginBottom: 4 }}>
            Imported from ORCID
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 700, color: "#0F172A", margin: 0, fontFamily: "Georgia, serif" }}>
            Registered Publications
          </h3>
        </div>
        <span style={{ fontSize: 11, fontFamily: "monospace", color: "#94A3B8" }}>
          {pubs.length} record{pubs.length !== 1 ? "s" : ""}
        </span>
      </div>
      {pubs.length === 0 ? (
        <div style={{ fontSize: 13, color: "#94A3B8", background: "#fff", border: `1px solid ${BRD}`, padding: "24px", textAlign: "center" }}>
          No publications imported yet — sync in Settings.
        </div>
      ) : (
        <div style={{ border: `1px solid ${BRD}`, background: "#fff" }}>
          {pubs.map((p, i) => (
            <div
              key={p.id}
              data-testid={`orcid-pub-${p.id}`}
              style={{ padding: "14px 20px", borderBottom: i < pubs.length - 1 ? `1px solid ${BRD}` : "none" }}
            >
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "#0F172A", lineHeight: 1.4, fontFamily: "Georgia, serif" }}>{p.title}</div>
                  <div style={{ fontSize: 10, fontFamily: "monospace", color: "#94A3B8", marginTop: 4 }}>
                    {[p.journal, p.year, (p.type || "").replace(/_/g," "), p.doi ? `DOI: ${p.doi}` : null].filter(Boolean).join(" · ")}
                    {p.doi && (
                      <a
                        href={`https://doi.org/${p.doi}`}
                        target="_blank"
                        rel="noreferrer"
                        style={{ marginLeft: 8, color: NAVY, textDecoration: "none" }}
                      >
                        <ExternalLink size={9} strokeWidth={1.5} style={{ verticalAlign: "middle" }} />
                      </a>
                    )}
                  </div>
                  {p.concepts?.length > 0 && (
                    <TagGroup gap={4} className="mt-1.5">
                      {p.concepts.slice(0, 5).map((c, ci) => (
                        <Tag key={ci} size="sm" className="font-mono">{c}</Tag>
                      ))}
                    </TagGroup>
                  )}
                </div>
                <div style={{ textAlign: "right", flexShrink: 0 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: EMRL, letterSpacing: "0.05em" }}>ORCID</span>
                  {p.manuscript_id && (
                    <Link to={`/manuscripts/${p.manuscript_id}`} style={{ display: "block", fontSize: 10, fontFamily: "monospace", color: NAVY, marginTop: 2 }}>
                      → linked
                    </Link>
                  )}
                  {p.citations != null && (
                    <div style={{ fontSize: 10, fontFamily: "monospace", color: "#94A3B8", marginTop: 2 }}>
                      {p.citations} cites
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function PublicationHub() {
  const [data, setData]         = useState(null);
  const [pickerFor, setPickerFor] = useState(null);
  const [gated, setGated]       = useState(false);

  const load = async () => {
    try {
      const r = await api.get("/publication-hub/pipeline");
      setData(r.data);
    } catch (e) {
      if (e?.response?.status === 402) { setGated(true); return; }
      setData({ summary: { total: 0, active: 0, under_review: 0, accepted: 0, published: 0 }, stages: {}, stage_order: STAGES.map(s => s.key) });
    }
  };
  useEffect(() => { load(); }, []);

  const columns = useMemo(() =>
    STAGES.map((s) => ({ ...s, rows: (data?.stages?.[s.key]) || [] })),
    [data]
  );

  const act = async (action, row) => {
    if (action === "pick") { setPickerFor(row.manuscript.id); return; }
    const subId = row.submission?.id;
    const mid = row.manuscript.id;
    const stageMap = { submit: "submitted", under_review: "under_review", accept: "accepted", reject: "rejected", revision: "revision_requested", publish: "published" };
    const decisionMap = { accept: "accept", reject: "reject", revision: "minor_revision" };
    try {
      if (subId) {
        await api.patch(`/publication-hub/submissions/${subId}`, {
          stage: stageMap[action], decision: decisionMap[action] || undefined,
        });
      } else if (stageMap[action] === "submitted") {
        toast.error("Select a venue first"); return;
      }
      const msStatusMap = { submit: "submitted", under_review: "submitted", accept: "accepted", reject: "rejected", revision: "revision_requested", publish: "published" };
      if (msStatusMap[action]) {
        try { await api.patch(`/manuscripts/${mid}`, { status: msStatusMap[action] }); } catch {}
      }
      toast.success("Updated");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  if (gated) {
    return (
      <ResearchLayout
        title="Publication Hub"
        nav={<LifecycleNav current="/publication-hub" />}
      >
        <div style={{ maxWidth: 520 }}>
          <EmptyState
            icon={<Lock />}
            title={
              <>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: NAVY, marginBottom: 8 }}>
                  Researcher Plan Required
                </div>
                Publication Tracking is a paid feature
              </>
            }
            description="Upgrade to Researcher to manage your manuscript submission pipeline, track review stages, and link to journals and conferences."
            action={<Button as={Link} to="/pricing">View Plans</Button>}
            size="lg"
          />
        </div>
      </ResearchLayout>
    );
  }

  if (!data) {
    return <SkeletonPage />;
  }

  const sum = data.summary || {};

  const pubHubActions = (
    <div style={{ display: "flex", gap: 8 }}>
      <Button as={Link} to="/manuscripts" variant="ghost" size="sm">
        <FileText size={12} strokeWidth={1.5} /> Manuscripts
      </Button>
      <Button as={Link} to="/journals" variant="ghost" size="sm">
        <BookOpen size={12} strokeWidth={1.5} /> Browse Journals
      </Button>
    </div>
  );

  return (
    <ResearchLayout
      title="Publication Hub"
      subtitle="Move manuscripts through the publication pipeline. Select venues, log submission events, capture reviewer decisions, and track revisions through to publication."
      nav={<LifecycleNav current="/publication-hub" />}
      actions={pubHubActions}
    >
      <div style={{ paddingBottom: 64 }}>
        {/* ── Summary stats ─────────────────────────────────────────────── */}
        <StatGrid cols={5} className="mb-8">
          <StatCard label="Total" value={sum.total || 0} icon={<FileText />} />
          <StatCard label="Active" value={sum.active || 0} icon={<Send />} />
          <StatCard label="Under Review" value={sum.under_review || 0} icon={<Inbox />} />
          <StatCard label="Accepted" value={sum.accepted || 0} icon={<CheckCircle2 />} />
          <StatCard label="Published" value={sum.published || 0} icon={<BookOpen />} />
        </StatGrid>

        {/* ── Pipeline kanban ───────────────────────────────────────────── */}
        {sum.total === 0 ? (
          <EmptyState
            icon={<Layers />}
            title="No manuscripts in the pipeline"
            description="Create a manuscript and link it to a target journal or conference to begin tracking its publication journey."
            action={
              <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
                <Button as={Link} to="/manuscripts">
                  <FileText size={13} strokeWidth={1.5} /> Manuscripts
                </Button>
                <Button as={Link} to="/journals" variant="outline">
                  Browse Journals
                </Button>
              </div>
            }
            size="lg"
            dashed={false}
          />
        ) : (
          <div style={{ overflowX: "auto", paddingBottom: 8 }}>
            <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(columns.filter(c=>c.rows.length>0||["selected","submitted","under_review"].includes(c.key)).length, 7)}, minmax(180px, 1fr))`, gap: 10, minWidth: 900 }}>
              {columns.slice(0, 7).map((col) => (
                <div
                  key={col.key}
                  data-testid={TID.pubhubStageColumn(col.key)}
                  style={{ borderTop: `3px solid ${col.accent}`, background: WARM }}
                >
                  <div style={{ padding: "10px 12px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: `1px solid ${BRD}` }}>
                    <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: col.color }}>{col.label}</span>
                    <span style={{ fontSize: 10, fontFamily: "monospace", color: "#94A3B8" }}>{col.rows.length}</span>
                  </div>
                  <div style={{ padding: "8px", display: "flex", flexDirection: "column", gap: 8, minHeight: 100 }}>
                    {col.rows.length === 0 && (
                      <div style={{ fontSize: 11, color: "#CBD5E1", textAlign: "center", padding: "16px 0", fontFamily: "monospace" }}>—</div>
                    )}
                    {col.rows.map((r) => (
                      <PipelineCard key={r.manuscript.id + (r.submission?.id || "")} row={r} onAction={act} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── ORCID publications ────────────────────────────────────────── */}
        <OrcidSection />

        {/* ── Lifecycle footer ──────────────────────────────────────────── */}
        <div style={{ marginTop: 48, paddingTop: 24, borderTop: `1px solid ${BRD}`, display: "flex", gap: 16, flexWrap: "wrap" }}>
          {[
            { to: "/manuscripts",        label: "Manuscripts",          icon: FileText },
            { to: "/reviews",            label: "Peer Reviews",         icon: ClipboardCheck },
            { to: "/repository",         label: "Repository",           icon: Archive },
            { to: "/grant-applications", label: "Applications",         icon: Coins },
            { to: "/journals",           label: "Browse Journals",      icon: BookOpen },
            { to: "/conferences",        label: "Browse Conferences",   icon: CalendarDays },
          ].map(({ to, label, icon: Icon }) => (
            <Link key={to} to={to} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none" }}>
              <Icon size={12} strokeWidth={1.5} /> {label}
              <ArrowRight size={10} strokeWidth={1.5} />
            </Link>
          ))}
        </div>
      </div>

      {pickerFor && (
        <VenuePicker manuscriptId={pickerFor} onClose={() => setPickerFor(null)} onPicked={() => load()} />
      )}
    </ResearchLayout>
  );
}

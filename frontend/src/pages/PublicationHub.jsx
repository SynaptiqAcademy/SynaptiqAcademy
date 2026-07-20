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
    <div
      style={{ position: "fixed", inset: 0, zIndex: 50, background: "rgba(15,23,42,0.5)", display: "flex", alignItems: "center", justifyContent: "center", padding: "0 16px" }}
      onClick={onClose}
    >
      <div
        data-testid="venue-picker-modal"
        role="dialog" aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        style={{ background: "#fff", width: "100%", maxWidth: 520, border: `1px solid ${BRD}`, boxShadow: "0 20px 60px rgba(15,23,42,0.2)" }}
      >
        <div style={{ padding: "20px 24px", borderBottom: `1px solid ${BRD}`, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 4 }}>Publication Hub</div>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: "#0F172A", margin: 0, fontFamily: "Georgia, serif" }}>Select Target Venue</h3>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#94A3B8", fontSize: 13 }}>Close</button>
        </div>
        <div style={{ padding: "20px 24px" }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            {[{k:"journal",label:"Journal",icon:BookOpen},{k:"conference",label:"Conference",icon:CalendarDays}].map(({k,label,icon:Icon}) => (
              <button
                key={k}
                onClick={() => { setKind(k); setResults([]); setQ(""); }}
                style={{ flex: 1, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "8px 12px", fontSize: 12, fontWeight: 600, cursor: "pointer", border: `1px solid ${kind===k ? NAVY : BRD}`, background: kind===k ? NAVY : "#fff", color: kind===k ? "#fff" : "#64748B", fontFamily: "inherit" }}
              >
                <Icon size={12} strokeWidth={1.5} /> {label}
              </button>
            ))}
          </div>
          <div style={{ position: "relative", marginBottom: 12 }}>
            <Search size={13} strokeWidth={1.5} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#CBD5E1" }} />
            <input
              autoFocus value={q} onChange={(e) => setQ(e.target.value)}
              placeholder={`Search ${kind}s…`}
              style={{ width: "100%", boxSizing: "border-box", paddingLeft: 34, paddingRight: 12, paddingTop: 9, paddingBottom: 9, border: `1px solid ${BRD}`, fontSize: 13, outline: "none", fontFamily: "inherit", color: "#0F172A" }}
            />
          </div>
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
      </div>
    </div>
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
    <div
      data-testid={TID.pubhubManuscript(m.id)}
      style={{ background: "#fff", border: `1px solid ${BRD}`, padding: "12px 14px" }}
    >
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
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.05em", background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}`, padding: "2px 6px" }}>
          {cfg.label}
        </span>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {!s && (
            <button data-testid={TID.pubhubSelectVenueBtn(m.id)} onClick={() => onAction("pick", row)} style={{ fontSize: 11, color: NAVY, background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", padding: 0, textDecoration: "underline" }}>
              Select venue
            </button>
          )}
          {s && !["submitted","under_review","accepted","published","rejected"].includes(stage) && (
            <button data-testid={TID.pubhubSubmitBtn(m.id)} onClick={() => onAction("submit", row)} style={{ fontSize: 11, color: EMRL, background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", padding: 0, textDecoration: "underline" }}>
              Mark submitted
            </button>
          )}
          {s && stage === "submitted" && (
            <button onClick={() => onAction("under_review", row)} style={{ fontSize: 11, color: "#B45309", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", padding: 0, textDecoration: "underline" }}>
              Under review
            </button>
          )}
          {s && stage === "under_review" && (
            <>
              <button onClick={() => onAction("accept", row)} style={{ fontSize: 11, color: EMRL, background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", padding: 0, textDecoration: "underline" }}>Accept</button>
              <button onClick={() => onAction("reject", row)} style={{ fontSize: 11, color: "#DC2626", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", padding: 0, textDecoration: "underline" }}>Reject</button>
              <button onClick={() => onAction("revision", row)} style={{ fontSize: 11, color: "#7C3AED", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", padding: 0, textDecoration: "underline" }}>Revision</button>
            </>
          )}
          {s && stage === "accepted" && (
            <button onClick={() => onAction("publish", row)} style={{ fontSize: 11, color: "#065F46", background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", padding: 0, textDecoration: "underline" }}>
              Publish
            </button>
          )}
        </div>
      </div>
    </div>
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
      <section
        data-testid="pubhub-orcid-cta"
        style={{ background: "#fff", border: `1px solid ${BRD}`, padding: "48px 32px", textAlign: "center", marginTop: 40 }}
      >
        <div style={{ width: 48, height: 48, background: WARM, border: `1px solid ${BRD}`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
          <BookOpen size={20} strokeWidth={1} style={{ color: NAVY }} />
        </div>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: NAVY, marginBottom: 8 }}>ORCID — Academic Identity</div>
        <h3 style={{ fontSize: 18, fontWeight: 700, color: "#0F172A", margin: "0 0 8px", fontFamily: "Georgia, serif" }}>
          Connect ORCID to import your publications
        </h3>
        <p style={{ fontSize: 13, color: "#64748B", margin: "0 auto 24px", maxWidth: 440, lineHeight: 1.7 }}>
          Link your ORCID iD in your Academic Passport to auto-import publications, conference papers, and preprints — verified by ORCID, enriched by OpenAlex.
        </p>
        <Link to="/academic-passport" style={{ display: "inline-block", background: NAVY, color: "#fff", textDecoration: "none", padding: "10px 20px", fontSize: 13, fontWeight: 600 }}>
          Connect ORCID in Academic Passport
        </Link>
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
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
                      {p.concepts.slice(0, 5).map((c, ci) => (
                        <span key={ci} style={{ fontSize: 9, fontFamily: "monospace", border: `1px solid ${BRD}`, background: WARM, padding: "2px 6px", color: "#64748B" }}>{c}</span>
                      ))}
                    </div>
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
        <div style={{ background: "#fff", border: `1px solid ${BRD}`, padding: "64px 32px", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", gap: 16, maxWidth: 520 }}>
          <Lock size={28} strokeWidth={1} style={{ color: "#CBD5E1" }} />
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: NAVY }}>Researcher Plan Required</div>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: "#0F172A", margin: 0, fontFamily: "Georgia, serif" }}>Publication Tracking is a paid feature</h2>
          <p style={{ fontSize: 13, color: "#64748B", margin: 0, lineHeight: 1.7 }}>
            Upgrade to Researcher to manage your manuscript submission pipeline, track review stages, and link to journals and conferences.
          </p>
          <Link to="/pricing" style={{ display: "inline-block", background: NAVY, color: "#fff", textDecoration: "none", padding: "10px 24px", fontSize: 13, fontWeight: 600, marginTop: 8 }}>
            View Plans
          </Link>
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
      <Link to="/manuscripts" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none", padding: "8px 14px", border: `1px solid ${BRD}`, background: "#fff" }}>
        <FileText size={12} strokeWidth={1.5} /> Manuscripts
      </Link>
      <Link to="/journals" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none", padding: "8px 14px", border: `1px solid ${BRD}`, background: "#fff" }}>
        <BookOpen size={12} strokeWidth={1.5} /> Browse Journals
      </Link>
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
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 32 }}>
          {[
            { label: "Total",        value: sum.total,        icon: FileText,     accent: null },
            { label: "Active",       value: sum.active,       icon: Send,         accent: "#4338CA" },
            { label: "Under Review", value: sum.under_review, icon: Inbox,        accent: "#B45309" },
            { label: "Accepted",     value: sum.accepted,     icon: CheckCircle2, accent: EMRL },
            { label: "Published",    value: sum.published,    icon: BookOpen,     accent: "#065F46" },
          ].map(({ label, value, icon: Icon, accent }) => (
            <div key={label} style={{ background: "#fff", border: `1px solid ${BRD}`, padding: "16px 20px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94A3B8" }}>{label}</span>
                <Icon size={13} strokeWidth={1.5} style={{ color: accent || "#CBD5E1" }} />
              </div>
              <span style={{ fontSize: 26, fontWeight: 700, color: "#0F172A", fontFamily: "Georgia, serif", letterSpacing: "-0.02em", lineHeight: 1 }}>
                {value || 0}
              </span>
            </div>
          ))}
        </div>

        {/* ── Pipeline kanban ───────────────────────────────────────────── */}
        {sum.total === 0 ? (
          <EmptyState
            icon={<Layers />}
            title="No manuscripts in the pipeline"
            description="Create a manuscript and link it to a target journal or conference to begin tracking its publication journey."
            action={
              <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
                <Link to="/manuscripts" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "#fff", textDecoration: "none", padding: "10px 18px", fontSize: 13, fontWeight: 600 }}>
                  <FileText size={13} strokeWidth={1.5} /> Manuscripts
                </Link>
                <Link to="/journals" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "#fff", color: NAVY, textDecoration: "none", padding: "10px 18px", fontSize: 13, fontWeight: 600, border: `1px solid ${BRD}` }}>
                  Browse Journals
                </Link>
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

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { toast } from "sonner";
import { BRD, BRDH, NAVY, WARM } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import {
  ClipboardCheck, ChevronRight, Check, X, Send,
  CheckCircle2, AlertCircle, XCircle, Clock, User,
  ArrowRight, Layers, FileText, Archive, Coins, Microscope,
} from "lucide-react";
import { EmptyState } from "@/components/ds/EmptyState";
import { SkeletonCard } from "@/components/ds/LoadingState";
import { NavTabs } from "@/components/ds/NavTabs";

// ─── Brand tokens ─────────────────────────────────────────────────────────────
const EMRL  = "#059669";

// ─── Review status system ─────────────────────────────────────────────────────
const VERDICT_CONFIG = {
  accepted:       { label: "Accepted",        color: EMRL,      bg: "#ECFDF5", border: "#6EE7B7" },
  minor_revision: { label: "Minor Revision",  color: "#B45309", bg: "#FFFBEB", border: "#FCD34D" },
  major_revision: { label: "Major Revision",  color: "#C2410C", bg: "#FFF7ED", border: "#FDBA74" },
  rejected:       { label: "Rejected",        color: "#DC2626", bg: "#FEF2F2", border: "#FCA5A5" },
};
const STATUS_CONFIG = {
  pending:   { label: "Invitation Pending", color: "#B45309", bg: "#FFFBEB", border: "#FCD34D", icon: Clock },
  accepted:  { label: "In Progress",        color: "#4338CA", bg: "#EEF2FF", border: "#A5B4FC", icon: ClipboardCheck },
  completed: { label: "Completed",          color: EMRL,      bg: "#ECFDF5", border: "#6EE7B7", icon: CheckCircle2 },
  declined:  { label: "Declined",           color: "#64748B", bg: "#F8FAFC", border: "#CBD5E1", icon: XCircle },
};

// ─── Lifecycle nav ────────────────────────────────────────────────────────────
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
                borderRadius: 3, textDecoration: "none",
                whiteSpace: "nowrap",
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

// ─── Badge ───────────────────────────────────────────────────────────────────
function Badge({ verdict, status }) {
  let cfg;
  if (verdict && VERDICT_CONFIG[verdict]) {
    cfg = VERDICT_CONFIG[verdict];
  } else {
    cfg = STATUS_CONFIG[status] || { label: status || "—", color: "#64748B", bg: "#F8FAFC", border: "#CBD5E1" };
  }
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase",
      padding: "3px 8px", background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}`,
      whiteSpace: "nowrap",
    }}>
      {cfg.label}
    </span>
  );
}

// ─── Verdict submission form ──────────────────────────────────────────────────
function VerdictForm({ rr, onSubmitted }) {
  const [verdict, setVerdict] = useState("minor_revision");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      await api.post(`/review-requests/${rr.id}/verdict`, { verdict, comment });
      toast.success(`Verdict submitted: ${verdict.replace(/_/g, " ")}`);
      onSubmitted?.();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div style={{ marginTop: 16, paddingTop: 16, borderTop: `1px solid ${BRD}`, display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94A3B8" }}>
        Submit Verdict
      </div>
      <select
        data-testid={TID.reviewVerdictSelect(rr.id)}
        value={verdict}
        onChange={(e) => setVerdict(e.target.value)}
        style={{ padding: "8px 12px", border: `1px solid ${BRD}`, fontSize: 13, fontFamily: "inherit", outline: "none", background: "#fff", color: "#0F172A" }}
      >
        <option value="accepted">Accept</option>
        <option value="minor_revision">Minor Revision</option>
        <option value="major_revision">Major Revision</option>
        <option value="rejected">Reject</option>
      </select>
      <textarea
        data-testid={TID.reviewVerdictComment(rr.id)}
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Reviewer comments (visible to authors)…"
        rows={4}
        style={{ padding: "10px 12px", border: `1px solid ${BRD}`, fontSize: 13, fontFamily: "inherit", resize: "vertical", outline: "none", color: "#0F172A", lineHeight: 1.6 }}
      />
      <div style={{ display: "flex", gap: 8 }}>
        <button
          data-testid={TID.reviewVerdictSubmit(rr.id)}
          onClick={submit}
          disabled={busy}
          style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "#fff", border: "none", padding: "8px 18px", fontSize: 13, fontWeight: 600, cursor: busy ? "wait" : "pointer", opacity: busy ? 0.7 : 1 }}
        >
          <Send size={12} strokeWidth={1.5} />
          {busy ? "Submitting…" : "Submit verdict"}
        </button>
      </div>
    </div>
  );
}

// ─── Review card ─────────────────────────────────────────────────────────────
function ReviewCard({ rr, onLoad }) {
  const [hov, setHov] = useState(false);
  const [showVerdict, setShowVerdict] = useState(false);

  const respond = async (decision) => {
    try {
      await api.post(`/review-requests/${rr.id}/respond`, { decision });
      toast.success(decision === "accept" ? "Review accepted" : "Review declined");
      onLoad();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <div
      data-testid={TID.reviewItem(rr.id)}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: "#fff",
        border: `1px solid ${hov ? BRDH : BRD}`,
        padding: "20px 24px",
        transition: "border-color 150ms, box-shadow 150ms",
        boxShadow: hov ? "0 2px 12px rgba(15,23,42,0.07)" : "none",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 16, justifyContent: "space-between" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 6 }}>
            {rr.manuscript?.manuscript_type || "Manuscript"}
            {rr.section && <span style={{ marginLeft: 8, color: "#CBD5E1" }}>· {rr.section.replace(/_/g," ")}</span>}
          </div>
          <Link
            to={`/manuscripts/${rr.manuscript_id}`}
            style={{ fontSize: 16, fontWeight: 600, color: "#0F172A", textDecoration: "none", lineHeight: 1.4, display: "block" }}
          >
            {rr.manuscript?.title || "Untitled Manuscript"}
          </Link>

          {rr.note && (
            <p style={{ fontSize: 13, color: "#475569", marginTop: 10, paddingLeft: 12, borderLeft: `3px solid ${NAVY}`, lineHeight: 1.6, fontStyle: "italic" }}>
              {rr.note}
            </p>
          )}

          {rr.requester && (
            <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{
                width: 24, height: 24, borderRadius: "50%", background: "rgba(15,40,71,0.07)",
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, overflow: "hidden",
              }}>
                {rr.requester.avatar_url
                  ? <img src={rr.requester.avatar_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  : <User size={12} strokeWidth={1.5} style={{ color: NAVY }} />}
              </div>
              <span style={{ fontSize: 12, color: "#475569" }}>
                {rr.requester.full_name}
                {rr.requester.institution && <span style={{ color: "#94A3B8" }}> · {rr.requester.institution}</span>}
              </span>
            </div>
          )}

          {rr.verdict_comment && (
            <div style={{ marginTop: 14, background: "#ECFDF5", borderLeft: `3px solid #34D399`, padding: "10px 14px" }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: EMRL, marginBottom: 4 }}>
                Your Verdict Comment
              </div>
              <p style={{ fontSize: 13, color: "#065F46", margin: 0, lineHeight: 1.6 }}>{rr.verdict_comment}</p>
            </div>
          )}

          {/* Actions */}
          {rr.status === "pending" && (
            <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
              <button
                data-testid={TID.reviewAcceptBtn(rr.id)}
                onClick={() => respond("accept")}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "#fff", border: "none", padding: "8px 16px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}
              >
                <Check size={12} strokeWidth={2} /> Accept Review
              </button>
              <button
                data-testid={TID.reviewDeclineBtn(rr.id)}
                onClick={() => respond("decline")}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "#fff", color: "#64748B", border: `1px solid ${BRD}`, padding: "8px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}
              >
                <X size={12} strokeWidth={2} /> Decline
              </button>
            </div>
          )}
          {rr.status === "accepted" && (
            showVerdict ? (
              <VerdictForm rr={rr} onSubmitted={() => { setShowVerdict(false); onLoad(); }} />
            ) : (
              <button
                data-testid={TID.reviewVerdictBtn(rr.id)}
                onClick={() => setShowVerdict(true)}
                style={{ marginTop: 16, display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "#fff", border: "none", padding: "8px 16px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}
              >
                <Send size={12} strokeWidth={1.5} /> Submit Verdict
              </button>
            )
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8, flexShrink: 0 }}>
          <Badge verdict={rr.verdict} status={rr.status} />
          <span style={{ fontSize: 10, fontFamily: "monospace", color: "#CBD5E1" }}>
            {new Date(rr.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function Reviews() {
  const [items, setItems] = useState([]);
  const [tab, setTab]     = useState("pending");
  const [loaded, setLoaded] = useState(false);

  const load = async () => {
    try { const { data } = await api.get("/review-requests/mine"); setItems(data || []); }
    catch { setItems([]); }
    finally { setLoaded(true); }
  };
  useEffect(() => { load(); }, []);

  const buckets = {
    pending:   items.filter((r) => r.status === "pending"),
    accepted:  items.filter((r) => r.status === "accepted"),
    completed: items.filter((r) => r.status === "completed"),
    declined:  items.filter((r) => r.status === "declined"),
  };
  const TABS = [
    { key: "pending",   label: "Invitations",  count: buckets.pending.length   },
    { key: "accepted",  label: "In Progress",  count: buckets.accepted.length  },
    { key: "completed", label: "Completed",    count: buckets.completed.length },
    { key: "declined",  label: "Declined",     count: buckets.declined.length  },
  ];

  const actions = (
    <div style={{ display: "flex", gap: 8 }}>
      <Link to="/manuscripts" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none", padding: "8px 14px", border: `1px solid ${BRD}`, background: "#fff" }}>
        <FileText size={12} strokeWidth={1.5} /> My Manuscripts
      </Link>
      <Link to="/reviewer-marketplace" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none", padding: "8px 14px", border: `1px solid ${BRD}`, background: "#fff" }}>
        <ClipboardCheck size={12} strokeWidth={1.5} /> Reviewer Marketplace
      </Link>
    </div>
  );

  return (
    <ResearchLayout
      title="Reviews"
      subtitle="Accept or decline review invitations. Return verdicts that advance manuscripts through the publication pipeline."
      nav={
        <>
          <LifecycleNav current="/reviews" />
          <div style={{ marginTop: 4 }}>
            <NavTabs
              tabs={TABS.map((t) => ({ id: t.key, label: t.label, count: t.count > 0 ? t.count : undefined }))}
              active={tab}
              onChange={setTab}
              variant="underline"
            />
          </div>
        </>
      }
      actions={actions}
    >
      <div data-testid={TID.reviewsDashboard} style={{ maxWidth: 840, paddingBottom: 64 }}>
        {!loaded ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <SkeletonCard rows={3} />
            <SkeletonCard rows={3} />
          </div>
        ) : buckets[tab].length === 0 ? (
          <EmptyState
            icon={tab === "declined" ? <XCircle /> : <ClipboardCheck />}
            title={
              tab === "pending"   ? "No pending invitations" :
              tab === "accepted"  ? "No reviews in progress" :
              tab === "completed" ? "No completed reviews yet" :
              "No declined reviews"
            }
            description={
              tab === "pending" ? "You'll be notified when a researcher invites you to review their manuscript." :
              tab === "accepted" ? "Accept a review invitation to begin reviewing here." :
              undefined
            }
            size="md"
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {buckets[tab].map((rr) => (
              <ReviewCard key={rr.id} rr={rr} onLoad={load} />
            ))}
          </div>
        )}

        {/* ── Lifecycle footer ──────────────────────────────────────────── */}
        {loaded && (
          <div style={{ marginTop: 48, paddingTop: 24, borderTop: `1px solid ${BRD}`, display: "flex", gap: 16, flexWrap: "wrap" }}>
            {[
              { to: "/manuscripts",        label: "My Manuscripts",   icon: FileText },
              { to: "/manuscript-review",  label: "AI Manuscript Review", icon: Microscope },
              { to: "/publication-hub",    label: "Publication Hub",  icon: Layers },
              { to: "/repository",         label: "Repository",       icon: Archive },
              { to: "/grant-applications", label: "Applications",     icon: Coins },
            ].map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none" }}
              >
                <Icon size={12} strokeWidth={1.5} />
                {label}
                <ArrowRight size={10} strokeWidth={1.5} />
              </Link>
            ))}
          </div>
        )}
      </div>
    </ResearchLayout>
  );
}

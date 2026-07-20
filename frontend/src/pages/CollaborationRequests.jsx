import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Users, Check, X, RotateCcw, Clock, MessageSquare, FolderPlus,
  Layers, ArrowRight, AlertCircle, Send, Building2, Globe,
  ChevronDown, Eye, Ban,
} from "lucide-react";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { userTypeLabel } from "../lib/userTypes";
import { NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";

// ─────────────────────── helpers ─────────────────────────────────────────────

function Avatar({ url, name, size = 40 }) {
  const initials = (name || "?").split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2);
  return (
    <div
      className="shrink-0 bg-slate-100 flex items-center justify-center text-xs font-medium text-slate-600 overflow-hidden"
      style={{ width: size, height: size }}
    >
      {url ? <img src={url} alt="" className="w-full h-full object-cover" /> : initials}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    pending:   { cls: "border-amber-400 text-amber-700 bg-amber-50",   label: "Pending" },
    viewed:    { cls: "border-sky-400 text-sky-700 bg-sky-50",         label: "Viewed" },
    accepted:  { cls: "border-green-500 text-green-700 bg-green-50",   label: "Accepted" },
    declined:  { cls: "border-rose-400 text-rose-700 bg-rose-50",      label: "Declined" },
    withdrawn: { cls: "border-slate-300 text-slate-500 bg-slate-50",   label: "Withdrawn" },
    cancelled: { cls: "border-slate-300 text-slate-500 bg-slate-50",   label: "Cancelled" },
    expired:   { cls: "border-orange-300 text-orange-600 bg-orange-50", label: "Expired" },
  };
  const cfg = map[status] || map.pending;
  return (
    <span className={`text-[10px] font-mono border px-2 py-0.5 ${cfg.cls}`}>{cfg.label}</span>
  );
}

function InvTypeLabel({ type }) {
  const labels = {
    research_collaboration:   "Research Collaboration",
    project_invitation:       "Project Invitation",
    workspace_invitation:     "Workspace Invitation",
    manuscript_invitation:    "Manuscript Invitation",
    grant_team:               "Grant Team",
    conference_team:          "Conference Team",
    reviewer:                 "Reviewer",
    mentorship:               "Mentorship",
    institutional_collaboration: "Institutional Collaboration",
  };
  const label = labels[type] || type;
  if (!label || type === "research_collaboration") return null;
  return (
    <span className="text-[10px] font-mono border border-[#0F2847]/20 text-[#0F2847] bg-[#0F2847]/5 px-2 py-0.5">
      {label}
    </span>
  );
}

// ─────────────────────── request card ────────────────────────────────────────

function RequestCard({ req, isSender, onStatusChange }) {
  const [acting, setActing] = useState(false);
  const [error, setError] = useState(null);
  const [showWorkspaceHint, setShowWorkspaceHint] = useState(false);
  const [declining, setDeclining] = useState(false);
  const [declineReason, setDeclineReason] = useState("");
  const [withdrawConfirm, setWithdrawConfirm] = useState(false);
  const declineRef = useRef(null);

  const other = isSender ? req.receiver_profile : req.sender_profile;
  const date = req.created_at
    ? new Date(req.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
    : "—";

  const isActive = req.status === "pending" || req.status === "viewed";

  const act = async (status, extras = {}) => {
    setActing(true);
    setError(null);
    try {
      await api.patch(`/collaboration-requests/${req.id}`, { status, ...extras });
      onStatusChange(req.id, status);
      if (status === "accepted") setShowWorkspaceHint(true);
      if (status === "declined") setDeclining(false);
      if (status === "withdrawn" || status === "cancelled") setWithdrawConfirm(false);
    } catch (err) {
      setError(err?.response?.data?.detail || "Action failed.");
    } finally {
      setActing(false);
    }
  };

  const handleDeclineConfirm = () => {
    act("declined", declineReason.trim() ? { decline_reason: declineReason.trim() } : {});
  };

  return (
    <div
      data-testid={TID.collabRequestCard(req.id)}
      className="border border-slate-200 bg-white"
    >
      <div className="flex items-start gap-4 p-5">
        <Avatar url={other?.avatar_url} name={other?.full_name} size={44} />
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div>
              <Link
                to={other?.id ? `/profile/${other.id}` : "#"}
                className="text-[13px] font-semibold text-slate-900 hover:text-[#0F2847]"
              >
                {other?.full_name || "Unknown Researcher"}
              </Link>
              <div className="text-xs text-slate-500 mt-0.5">
                {[userTypeLabel(other), other?.institution].filter(Boolean).join(" · ")}
              </div>
              {other?.country && (
                <div className="flex items-center gap-1 mt-0.5 text-xs text-slate-400">
                  <Globe size={10} strokeWidth={1.5} />
                  {other.country}
                </div>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
              <InvTypeLabel type={req.invitation_type} />
              <StatusBadge status={req.status} />
              <span className="text-xs text-slate-400">{date}</span>
            </div>
          </div>

          {/* Metadata row */}
          {(req.role || req.estimated_duration) && (
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
              {req.role && <span>Role: <strong className="text-slate-700">{req.role}</strong></span>}
              {req.estimated_duration && <span>Duration: <strong className="text-slate-700">{req.estimated_duration}</strong></span>}
            </div>
          )}

          {req.project_title && (
            <div className="mt-2 flex items-center gap-1.5 text-xs text-slate-500">
              <FolderPlus size={11} strokeWidth={1.5} />
              Project: <span className="font-medium text-slate-700">{req.project_title}</span>
            </div>
          )}

          {req.source && req.source !== "manual" && (
            <div className="mt-1 text-xs text-slate-400 italic">
              Via {req.source === "gap_finder" ? "Research Gap Finder" : req.source === "collab_intel" ? "Collaboration Intelligence" : req.source}
            </div>
          )}

          {req.message && (
            <div className="mt-3 bg-slate-50 border border-slate-100 px-3 py-2.5 text-sm text-slate-700 leading-relaxed">
              "{req.message}"
            </div>
          )}

          {req.expected_contribution && (
            <div className="mt-2 text-xs text-slate-500">
              Expected contribution: <span className="text-slate-700">{req.expected_contribution}</span>
            </div>
          )}

          {req.decline_reason && req.status === "declined" && (
            <div className="mt-2 flex items-start gap-1.5 text-xs text-rose-600 bg-rose-50 border border-rose-100 px-2 py-1.5">
              <Ban size={10} strokeWidth={1.5} className="mt-0.5 shrink-0" />
              Reason: {req.decline_reason}
            </div>
          )}

          {req.viewed_at && req.status === "viewed" && isSender && (
            <div className="mt-2 flex items-center gap-1 text-xs text-sky-600">
              <Eye size={10} strokeWidth={1.5} />
              Viewed {new Date(req.viewed_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
            </div>
          )}

          {error && (
            <div className="mt-2 flex items-center gap-1.5 text-xs text-rose-600">
              <AlertCircle size={11} strokeWidth={1.5} />
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Two-step decline panel */}
      {declining && (
        <div className="mx-5 mb-4 border border-rose-200 bg-rose-50 p-3 space-y-2" ref={declineRef}>
          <p className="text-xs text-rose-700 font-medium">Decline this request?</p>
          <textarea
            rows={2}
            value={declineReason}
            onChange={(e) => setDeclineReason(e.target.value)}
            placeholder="Optional: share a reason with the sender"
            className="w-full text-xs px-2 py-1.5 border border-rose-200 bg-white resize-none focus:outline-none focus:ring-1 focus:ring-rose-400"
          />
          <div className="flex gap-2">
            <button
              onClick={handleDeclineConfirm}
              disabled={acting}
              className="text-xs bg-rose-600 text-white px-3 py-1.5 hover:bg-rose-700 disabled:opacity-50"
            >
              Confirm decline
            </button>
            <button
              onClick={() => { setDeclining(false); setDeclineReason(""); }}
              className="text-xs text-slate-600 px-3 py-1.5 border border-slate-200 hover:border-slate-400"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Withdraw confirm */}
      {withdrawConfirm && (
        <div className="mx-5 mb-4 border border-amber-200 bg-amber-50 p-3 space-y-2">
          <p className="text-xs text-amber-700 font-medium">Withdraw this request? The recipient will be notified.</p>
          <div className="flex gap-2">
            <button
              onClick={() => act("withdrawn")}
              disabled={acting}
              className="text-xs bg-amber-600 text-white px-3 py-1.5 hover:bg-amber-700 disabled:opacity-50"
            >
              Yes, withdraw
            </button>
            <button
              onClick={() => setWithdrawConfirm(false)}
              className="text-xs text-slate-600 px-3 py-1.5 border border-slate-200 hover:border-slate-400"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Actions */}
      {isActive && !declining && !withdrawConfirm && (
        <div className="px-5 pb-4 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
          {!isSender ? (
            <>
              <button
                onClick={() => act("accepted")}
                disabled={acting}
                className="flex items-center gap-1.5 text-xs bg-[#0F2847] text-white border border-[#0F2847] px-3 py-1.5 hover:bg-slate-800 disabled:opacity-50 transition-colors"
              >
                <Check size={11} strokeWidth={2} />
                Accept
              </button>
              <button
                onClick={() => { setDeclining(true); setTimeout(() => declineRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 50); }}
                disabled={acting}
                className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-1.5 hover:border-rose-400 hover:text-rose-600 disabled:opacity-50 transition-colors"
              >
                <X size={11} strokeWidth={2} />
                Decline
              </button>
            </>
          ) : (
            <button
              onClick={() => setWithdrawConfirm(true)}
              disabled={acting}
              className="flex items-center gap-1.5 text-xs text-slate-500 border border-slate-200 px-3 py-1.5 hover:border-slate-400 disabled:opacity-50 transition-colors"
            >
              <RotateCcw size={11} strokeWidth={1.5} />
              Withdraw
            </button>
          )}
          {other?.id && (
            <Link
              to={`/messages/${other.id}`}
              className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
            >
              <MessageSquare size={11} strokeWidth={1.5} />
              Message
            </Link>
          )}
        </div>
      )}

      {/* Post-accept CTA */}
      {req.status === "accepted" && showWorkspaceHint && (
        <div className="px-5 pb-4 pt-3 border-t border-slate-100 bg-green-50">
          <p className="text-xs text-green-800 mb-2 font-medium">Request accepted! What next?</p>
          <div className="flex flex-wrap gap-2">
            <Link
              to="/workspaces"
              className="flex items-center gap-1.5 text-xs text-slate-700 border border-slate-300 bg-white px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
            >
              <Layers size={11} strokeWidth={1.5} />
              Create Workspace
            </Link>
            <Link
              to="/projects"
              className="flex items-center gap-1.5 text-xs text-slate-700 border border-slate-300 bg-white px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
            >
              <FolderPlus size={11} strokeWidth={1.5} />
              Start Project
            </Link>
            {other?.id && (
              <Link
                to={`/messages/${other.id}`}
                className="flex items-center gap-1.5 text-xs text-slate-700 border border-slate-300 bg-white px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
              >
                <MessageSquare size={11} strokeWidth={1.5} />
                Open DM
              </Link>
            )}
          </div>
        </div>
      )}

      {req.status === "accepted" && !showWorkspaceHint && (
        <div className="px-5 pb-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2">
          <Link
            to="/workspaces"
            className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
          >
            <Layers size={11} strokeWidth={1.5} />
            Workspaces
          </Link>
          <Link
            to="/projects"
            className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
          >
            <FolderPlus size={11} strokeWidth={1.5} />
            Projects
          </Link>
          {other?.id && (
            <Link
              to={`/messages/${other.id}`}
              className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
            >
              <MessageSquare size={11} strokeWidth={1.5} />
              Message
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────── empty state ─────────────────────────────────────────

function EmptyState({ tab }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-14 h-14 bg-slate-100 flex items-center justify-center mb-5">
        <Users size={24} strokeWidth={1} className="text-slate-400" />
      </div>
      <div className="text-base font-semibold text-slate-700 mb-2">
        {tab === "received" ? "No incoming requests" : "No outgoing requests"}
      </div>
      <p className="text-sm text-slate-500 max-w-xs leading-relaxed mb-6">
        {tab === "received"
          ? "When researchers send you collaboration requests, they'll appear here."
          : "Use Collaboration Intelligence to find researchers and send collaboration requests."}
      </p>
      {tab === "sent" && (
        <Link
          to="/collaboration-intelligence"
          className="flex items-center gap-2 border border-[#0F2847] bg-[#0F2847] text-white px-5 py-2.5 text-sm hover:bg-slate-800"
        >
          <Send size={13} strokeWidth={1.5} />
          Find Collaborators
        </Link>
      )}
    </div>
  );
}

// ─────────────────────── main page ───────────────────────────────────────────

export default function CollaborationRequests() {
  const [tab, setTab] = useState("received");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [receivedReqs, setReceivedReqs] = useState([]);
  const [sentReqsList, setSentReqsList] = useState([]);

  useEffect(() => {
    const loadBoth = async () => {
      setLoading(true);
      setError(null);
      try {
        const [recRes, sentRes] = await Promise.all([
          api.get("/collaboration-requests?kind=received"),
          api.get("/collaboration-requests?kind=sent"),
        ]);
        const received = recRes.data || [];
        setReceivedReqs(received);
        setSentReqsList(sentRes.data || []);

        // Mark pending received requests as viewed
        const pendingIds = received.filter((r) => r.status === "pending").map((r) => r.id);
        if (pendingIds.length > 0) {
          await Promise.allSettled(
            pendingIds.map((id) => api.patch(`/collaboration-requests/${id}`, { status: "viewed" }))
          );
          setReceivedReqs((prev) =>
            prev.map((r) => pendingIds.includes(r.id) ? { ...r, status: "viewed" } : r)
          );
        }
      } catch (err) {
        setError(err?.response?.data?.detail || "Failed to load requests.");
      } finally {
        setLoading(false);
      }
    };
    loadBoth();
  }, []);

  const handleStatusChangeReceived = (id, status) => {
    setReceivedReqs((prev) => prev.map((r) => r.id === id ? { ...r, status } : r));
  };
  const handleStatusChangeSent = (id, status) => {
    setSentReqsList((prev) => prev.map((r) => r.id === id ? { ...r, status } : r));
  };

  const pendingCount = receivedReqs.filter((r) => r.status === "pending" || r.status === "viewed").length;
  const activeList = tab === "received" ? receivedReqs : sentReqsList;
  const handleChange = tab === "received" ? handleStatusChangeReceived : handleStatusChangeSent;

  return (
    <ResearchLayout
      title="Collaboration Requests"
      subtitle="Manage your incoming and outgoing collaboration invitations."
    >
      <div data-testid={TID.collabRequestsDashboard} className="space-y-6">

      {error && (
        <div className="flex items-center gap-2.5 border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <AlertCircle size={14} strokeWidth={1.5} />
          {error}
        </div>
      )}

      {/* Tabs */}
      <nav className="flex gap-6 border-b border-slate-200">
        {[
          { key: "received", label: "Received", count: pendingCount },
          { key: "sent", label: "Sent", count: sentReqsList.filter((r) => r.status === "pending" || r.status === "viewed").length },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`pb-3 text-sm font-medium border-b-2 -mb-px flex items-center gap-2 ${
              tab === t.key ? "border-[#0F2847] text-slate-900" : "border-transparent text-slate-500 hover:text-slate-900"
            }`}
          >
            {t.label}
            {t.count > 0 && (
              <span className="text-[10px] bg-[#0F2847] text-white px-1.5 py-0.5 font-mono min-w-[18px] text-center">
                {t.count}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* Quick actions */}
      <div className="flex items-center gap-3">
        <Link
          to="/collaboration-intelligence"
          className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-2 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
        >
          <Send size={12} strokeWidth={1.5} />
          Find & Invite Collaborators
        </Link>
        <Link
          to="/network"
          className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-2 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
        >
          <Users size={12} strokeWidth={1.5} />
          Browse Network
        </Link>
        <Link
          to="/research-gap-finder"
          className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-2 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
        >
          <ArrowRight size={12} strokeWidth={1.5} />
          Research Gap Finder
        </Link>
      </div>

      {/* Request list */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => <div key={i} className="h-36 bg-slate-200 animate-pulse" />)}
        </div>
      ) : activeList.length === 0 ? (
        <EmptyState tab={tab} />
      ) : (
        <div className="space-y-4">
          {activeList.map((req) => (
            <RequestCard
              key={req.id}
              req={req}
              isSender={tab === "sent"}
              onStatusChange={handleChange}
            />
          ))}
        </div>
      )}
      </div>
    </ResearchLayout>
  );
}

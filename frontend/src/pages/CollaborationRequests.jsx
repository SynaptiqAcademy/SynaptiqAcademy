import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
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
import { Avatar } from "@/components/ds/Avatar";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Button } from "@/components/ds/Button";
import { Textarea } from "@/components/ds/Textarea";
import { NavTabs } from "@/components/ds/NavTabs";
import { EmptyState as DsEmptyState } from "@/components/ds/EmptyState";
import { SkeletonCard } from "@/components/ds/LoadingState";
import { Alert } from "@/components/ds/Alert";

// ─────────────────────── helpers ─────────────────────────────────────────────

function StatusBadge({ status }) {
  const map = {
    pending:   { variant: "warning", label: "Pending" },
    viewed:    { variant: "info",    label: "Viewed" },
    accepted:  { variant: "success", label: "Accepted" },
    declined:  { variant: "danger",  label: "Declined" },
    withdrawn: { variant: "neutral", label: "Withdrawn" },
    cancelled: { variant: "neutral", label: "Cancelled" },
    expired:   { variant: "warning", label: "Expired" },
  };
  const cfg = map[status] || map.pending;
  return <Badge variant={cfg.variant} size="sm">{cfg.label}</Badge>;
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
  return <Badge variant="default" size="sm">{label}</Badge>;
}

// ─────────────────────── request card ────────────────────────────────────────

function RequestCard({ req, isSender, onStatusChange }) {
  const navigate = useNavigate();
  const [acting, setActing] = useState(false);
  const [error, setError] = useState(null);
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
      const res = await api.patch(`/collaboration-requests/${req.id}`, { status, ...extras });
      onStatusChange(req.id, status, res.data?.workspace_id);
      if (status === "accepted" && res.data?.workspace_id) {
        navigate(`/workspaces/${res.data.workspace_id}`);
        return;
      }
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
    <Card
      data-testid={TID.collabRequestCard(req.id)}
      padding="none"
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
          <Textarea
            rows={2}
            value={declineReason}
            onChange={(e) => setDeclineReason(e.target.value)}
            placeholder="Optional: share a reason with the sender"
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="danger"
              onClick={handleDeclineConfirm}
              disabled={acting}
              loading={acting}
            >
              Confirm decline
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => { setDeclining(false); setDeclineReason(""); }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Withdraw confirm */}
      {withdrawConfirm && (
        <Card variant="ghost" padding="sm" className="mx-5 mb-4 border border-amber-200 bg-amber-50 space-y-2">
          <p className="text-xs text-amber-700 font-medium">Withdraw this request? The recipient will be notified.</p>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={() => act("withdrawn")}
              disabled={acting}
              loading={acting}
              className="bg-amber-600 hover:bg-amber-700"
            >
              Yes, withdraw
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setWithdrawConfirm(false)}>
              Cancel
            </Button>
          </div>
        </Card>
      )}

      {/* Actions */}
      {isActive && !declining && !withdrawConfirm && (
        <div className="px-5 pb-4 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
          {!isSender ? (
            <>
              <Button
                size="sm"
                onClick={() => act("accepted")}
                disabled={acting}
                loading={acting}
              >
                <Check size={11} strokeWidth={2} />
                Accept
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => { setDeclining(true); setTimeout(() => declineRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 50); }}
                disabled={acting}
                className="hover:border-rose-400 hover:text-rose-600"
              >
                <X size={11} strokeWidth={2} />
                Decline
              </Button>
            </>
          ) : (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setWithdrawConfirm(true)}
              disabled={acting}
            >
              <RotateCcw size={11} strokeWidth={1.5} />
              Withdraw
            </Button>
          )}
          {other?.id && (
            <Button as={Link} to={`/messages/${other.id}`} size="sm" variant="ghost">
              <MessageSquare size={11} strokeWidth={1.5} />
              Message
            </Button>
          )}
        </div>
      )}

      {/* Post-accept — the shared workspace is auto-provisioned on accept (see
          `act()` above, which navigates there immediately). This row is the
          fallback for a request the user already accepted in a past visit. */}
      {req.status === "accepted" && (
        <div className="px-5 pb-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2">
          {req.workspace_id ? (
            <Button as={Link} to={`/workspaces/${req.workspace_id}`} size="sm" variant="outline">
              <Layers size={11} strokeWidth={1.5} />
              Open Workspace
            </Button>
          ) : (
            <Button as={Link} to="/workspaces" size="sm" variant="ghost">
              <Layers size={11} strokeWidth={1.5} />
              Workspaces
            </Button>
          )}
          {other?.id && (
            <Button as={Link} to={`/messages/${other.id}`} size="sm" variant="ghost">
              <MessageSquare size={11} strokeWidth={1.5} />
              Message
            </Button>
          )}
        </div>
      )}
    </Card>
  );
}

// ─────────────────────── empty state ─────────────────────────────────────────

function EmptyState({ tab }) {
  return (
    <DsEmptyState
      icon={<Users strokeWidth={1} />}
      title={tab === "received" ? "No incoming requests" : "No outgoing requests"}
      description={
        tab === "received"
          ? "When researchers send you collaboration requests, they'll appear here."
          : "Use Collaboration Intelligence to find researchers and send collaboration requests."
      }
      action={
        tab === "sent" ? (
          <Button as={Link} to="/collaboration-intelligence">
            <Send size={13} strokeWidth={1.5} />
            Find Collaborators
          </Button>
        ) : undefined
      }
      size="lg"
      dashed={false}
    />
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

  const handleStatusChangeReceived = (id, status, workspaceId) => {
    setReceivedReqs((prev) => prev.map((r) => r.id === id ? { ...r, status, workspace_id: workspaceId ?? r.workspace_id } : r));
  };
  const handleStatusChangeSent = (id, status, workspaceId) => {
    setSentReqsList((prev) => prev.map((r) => r.id === id ? { ...r, status, workspace_id: workspaceId ?? r.workspace_id } : r));
  };

  const pendingCount = receivedReqs.filter((r) => r.status === "pending" || r.status === "viewed").length;
  const activeList = tab === "received" ? receivedReqs : sentReqsList;
  const handleChange = tab === "received" ? handleStatusChangeReceived : handleStatusChangeSent;

  return (
    <ResearchLayout
      title="Collaboration Requests"
      subtitle="Manage your incoming and outgoing collaboration invitations."
      nav={
        <NavTabs
          tabs={[
            { id: "received", label: "Received", count: pendingCount },
            { id: "sent", label: "Sent", count: sentReqsList.filter((r) => r.status === "pending" || r.status === "viewed").length },
          ]}
          active={tab}
          onChange={setTab}
        />
      }
    >
      <div data-testid={TID.collabRequestsDashboard} className="space-y-6">

      {error && (
        <Alert variant="error">{error}</Alert>
      )}

      {/* Quick actions */}
      <div className="flex items-center gap-3">
        <Button as={Link} to="/collaboration-intelligence" variant="ghost" size="sm">
          <Send size={12} strokeWidth={1.5} />
          Find & Invite Collaborators
        </Button>
        <Button as={Link} to="/network" variant="ghost" size="sm">
          <Users size={12} strokeWidth={1.5} />
          Browse Network
        </Button>
        <Button as={Link} to="/research-gap-finder" variant="ghost" size="sm">
          <ArrowRight size={12} strokeWidth={1.5} />
          Research Gap Finder
        </Button>
      </div>

      {/* Request list */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => <SkeletonCard key={i} rows={3} />)}
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

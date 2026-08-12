/**
 * Invitations — sent + received marketplace invitations with accept/decline/withdraw.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { Mail, Check, X, ArrowRight, Send, Inbox, RotateCcw, Eye, Clock, Ban } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Spinner } from "@/components/ds/LoadingState";
import EmptyState from "@/components/ds/EmptyState";
import { NavTabs } from "@/components/ds/NavTabs";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Button } from "@/components/ds/Button";
import { Textarea } from "@/components/ds/Textarea";

const KIND_LABELS = {
  collaboration:              "Research Collaboration",
  project:                    "Project Invitation",
  workspace:                  "Workspace Invitation",
  manuscript:                 "Manuscript Invitation",
  expertise_request:          "Expertise Request",
  grant_team:                 "Grant Team",
  conference_team:            "Conference Team",
  reviewer:                   "Reviewer",
  mentorship:                 "Mentorship",
  institutional_collaboration: "Institutional Collaboration",
};

function StatusChip({ status }) {
  const map = {
    pending:   "warning",
    accepted:  "success",
    declined:  "danger",
    withdrawn: "neutral",
    expired:   "warning",
  };
  return <Badge variant={map[status] || "warning"} size="sm">{status}</Badge>;
}

function InvitationRow({ inv, tab, onDecide, onWithdraw }) {
  const [decliningOpen, setDecliningOpen] = useState(false);
  const [declineReason, setDeclineReason] = useState("");
  const [withdrawConfirm, setWithdrawConfirm] = useState(false);
  const [acting, setActing] = useState(false);
  const declineRef = useRef(null);

  const isReceived = tab === "received";
  const isPending = inv.status === "pending";

  const handleDecide = async (decision, extras = {}) => {
    setActing(true);
    try {
      await onDecide(inv.id, decision, extras);
      setDecliningOpen(false);
      setDeclineReason("");
    } finally {
      setActing(false);
    }
  };

  const handleWithdraw = async () => {
    setActing(true);
    try {
      await onWithdraw(inv.id);
      setWithdrawConfirm(false);
    } finally {
      setActing(false);
    }
  };

  return (
    <Card padding="none" data-testid={`inv-row-${inv.id}`}>
      <div className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="overline text-[#0F2847]">{KIND_LABELS[inv.kind] || inv.kind?.replace(/_/g, " ")}</span>
              <StatusChip status={inv.status} />
              {inv.viewed_at && !isReceived && inv.status !== "pending" && (
                <span className="text-[10px] text-sky-600 flex items-center gap-0.5">
                  <Eye size={9} strokeWidth={1.5} /> Seen
                </span>
              )}
              {inv.expires_at && isPending && (
                <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
                  <Clock size={9} strokeWidth={1.5} />
                  Expires {new Date(inv.expires_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
                </span>
              )}
            </div>
            {inv.counterpart && (
              <Link to={`/profile/${inv.counterpart.id}`} className="font-serif text-lg text-slate-900 hover:text-[#0F2847] mt-1 block">
                {isReceived ? "From" : "To"} {inv.counterpart.full_name}
                {inv.counterpart.institution && <span className="text-sm text-slate-500 font-sans font-normal ml-2">· {inv.counterpart.institution}</span>}
              </Link>
            )}
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
              {inv.role && <span>Role: <strong className="text-slate-700">{inv.role}</strong></span>}
              {inv.estimated_duration && <span>Duration: <strong className="text-slate-700">{inv.estimated_duration}</strong></span>}
            </div>
            {inv.expected_contribution && (
              <div className="mt-1 text-xs text-slate-500">
                Contribution: <span className="text-slate-700">{inv.expected_contribution}</span>
              </div>
            )}
            {inv.message && <p className="text-sm text-slate-700 mt-2 font-serif italic">"{inv.message}"</p>}
            {inv.decline_reason && inv.status === "declined" && (
              <div className="mt-2 flex items-start gap-1.5 text-xs text-rose-600 bg-rose-50 border border-rose-100 px-2 py-1.5">
                <Ban size={10} strokeWidth={1.5} className="mt-0.5 shrink-0" />
                Reason: {inv.decline_reason}
              </div>
            )}
            <div className="text-[10px] font-mono text-slate-400 mt-2">{new Date(inv.created_at).toLocaleString()}</div>
          </div>

          <div className="flex flex-col gap-1 shrink-0">
            {isReceived && isPending && !decliningOpen && (
              <>
                <Button
                  size="sm"
                  data-testid={`inv-accept-${inv.id}`}
                  onClick={() => handleDecide("accepted")}
                  disabled={acting}
                  loading={acting}
                >
                  <Check size={11} strokeWidth={1.5} />
                  Accept
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  data-testid={`inv-decline-${inv.id}`}
                  onClick={() => { setDecliningOpen(true); setTimeout(() => declineRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 50); }}
                  disabled={acting}
                  className="border-red-200 text-red-700 hover:bg-red-50"
                >
                  <X size={11} strokeWidth={1.5} />
                  Decline
                </Button>
              </>
            )}
            {!isReceived && isPending && !withdrawConfirm && (
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
          </div>
        </div>
      </div>

      {/* Decline panel */}
      {decliningOpen && (
        <div className="mx-4 mb-4 border border-rose-200 bg-rose-50 p-3 space-y-2" ref={declineRef}>
          <p className="text-xs text-rose-700 font-medium">Decline this invitation?</p>
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
              onClick={() => handleDecide("declined", declineReason.trim() ? { decline_reason: declineReason.trim() } : {})}
              disabled={acting}
              loading={acting}
            >
              Confirm decline
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => { setDecliningOpen(false); setDeclineReason(""); }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Withdraw confirm */}
      {withdrawConfirm && (
        <div className="mx-4 mb-4 border border-amber-200 bg-amber-50 p-3 space-y-2">
          <p className="text-xs text-amber-700 font-medium">Withdraw this invitation? The recipient will be notified.</p>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={handleWithdraw}
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
        </div>
      )}
    </Card>
  );
}

export default function Invitations() {
  const [tab, setTab] = useState("received");
  const [items, setItems] = useState(null);

  const load = useCallback(async () => {
    setItems(null);
    try {
      const { data } = await api.get(`/marketplace/invitations?direction=${tab}`);
      setItems(data || []);
    } catch {
      setItems([]);
    }
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  const handleDecide = async (id, decision, extras = {}) => {
    try {
      await api.post(`/marketplace/invitations/${id}/decide`, { decision, ...extras });
      toast.success(`Invitation ${decision}`);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
      throw e;
    }
  };

  const handleWithdraw = async (id) => {
    try {
      await api.delete(`/marketplace/invitations/${id}`);
      toast.success("Invitation withdrawn");
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to withdraw");
      throw e;
    }
  };

  const pendingCount = (items || []).filter((i) => i.status === "pending").length;

  return (
    <ResearchLayout
      title="Invitations"
      subtitle="Manage collaboration invitations you've sent or received."
      icon={<Mail size={16} strokeWidth={1.5} />}
      nav={
        <NavTabs
          tabs={[
            { id: "received", label: "Received", count: tab === "received" ? pendingCount : undefined },
            { id: "sent",     label: "Sent" },
          ]}
          active={tab}
          onChange={setTab}
          variant="underline"
        />
      }
    >
      <div className="space-y-8">
      {items === null && (
        <div className="flex items-center gap-2 py-4">
          <Spinner size={14} />
          <span className="text-sm text-slate-500">Loading…</span>
        </div>
      )}
      {items && items.length === 0 && (
        <EmptyState
          icon={<Mail />}
          title={`No invitations ${tab === "received" ? "received yet" : "sent yet"}`}
          size="md"
          dashed={true}
        />
      )}
      {items && items.length > 0 && (
        <div className="space-y-3" data-testid="invitations-list">
          {items.map((inv) => (
            <InvitationRow
              key={inv.id}
              inv={inv}
              tab={tab}
              onDecide={handleDecide}
              onWithdraw={handleWithdraw}
            />
          ))}
        </div>
      )}
      </div>
    </ResearchLayout>
  );
}

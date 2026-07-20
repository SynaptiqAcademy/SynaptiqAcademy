import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Loader2, Users, Calendar, CheckCircle, XCircle,
  AlertTriangle, Shield, FileText, Star, Plus, Trash2, RefreshCw,
  X, ChevronDown, Eye, Lock, Edit2, Save, BarChart2, UserCheck,
  AlertCircle, Archive
} from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";

// ─── helpers ──────────────────────────────────────────────────────────────────

function fmt(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function cap(s) {
  if (!s) return "";
  return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ");
}

const REQ_STATUS_COLORS = {
  draft:      "bg-blue-50 text-blue-700 border border-blue-200",
  open:       "bg-blue-100 text-blue-700 border border-blue-200",
  matching:   "bg-amber-100 text-amber-700 border border-amber-200",
  assigned:   "bg-purple-100 text-purple-700 border border-purple-200",
  in_review:  "bg-purple-100 text-purple-700 border border-purple-200",
  completed:  "bg-emerald-100 text-emerald-700 border border-emerald-200",
  archived:   "bg-slate-100 text-slate-500 border border-slate-200",
};

const ASSIGN_STATUS_COLORS = {
  invited:    "bg-amber-100 text-amber-700 border border-amber-200",
  accepted:   "bg-blue-100 text-blue-700 border border-blue-200",
  declined:   "bg-red-100 text-red-700 border border-red-200",
  completed:  "bg-emerald-100 text-emerald-700 border border-emerald-200",
  withdrawn:  "bg-slate-100 text-slate-500 border border-slate-200",
};

const CONF_COLORS = {
  anonymous:    "bg-slate-100 text-slate-600",
  "double-blind": "bg-indigo-100 text-indigo-700",
  "single-blind": "bg-amber-100 text-amber-700",
  public:       "bg-emerald-100 text-emerald-700",
};

const TYPE_COLORS = {
  manuscript:   "bg-blue-100 text-blue-700",
  grant:        "bg-indigo-100 text-indigo-700",
  thesis:       "bg-purple-100 text-purple-700",
  conference:   "bg-amber-100 text-amber-700",
  methodology:  "bg-emerald-100 text-emerald-700",
  statistical:  "bg-rose-100 text-rose-700",
  dissertation: "bg-purple-100 text-purple-700",
  custom:       "bg-slate-100 text-slate-600",
};

function StatusBadge({ status, map = REQ_STATUS_COLORS }) {
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${map[status] || "bg-slate-100 text-slate-600 border border-slate-200"}`}>
      {cap(status)}
    </span>
  );
}

function TypeBadge({ type }) {
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${TYPE_COLORS[type] || TYPE_COLORS.custom}`}>
      {cap(type)}
    </span>
  );
}

function ConfBadge({ value }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${CONF_COLORS[value] || "bg-slate-100 text-slate-600"}`}>
      <Lock size={10} />
      {cap(value)}
    </span>
  );
}

function Chip({ label, color = "slate" }) {
  const map = {
    slate:   "bg-slate-100 text-slate-700",
    blue:    "bg-blue-100 text-blue-700",
    indigo:  "bg-indigo-100 text-indigo-700",
    purple:  "bg-purple-100 text-purple-700",
    amber:   "bg-amber-100 text-amber-700",
    emerald: "bg-emerald-100 text-emerald-700",
    rose:    "bg-rose-100 text-rose-700",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${map[color] || map.slate}`}>
      {label}
    </span>
  );
}

function DivBar({ value = 0, max = 100, color = "bg-[#0F2847]", className = "" }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className={`h-1.5 bg-slate-100 rounded-full overflow-hidden ${className}`}>
      <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function ScoreBar({ value = 0, max = 100, color = "bg-[#0F2847]" }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-semibold text-slate-700 w-8 text-right">{value}</span>
    </div>
  );
}

function InitialAvatar({ name, size = "md" }) {
  const sz = size === "sm" ? "w-7 h-7 text-xs" : "w-9 h-9 text-sm";
  const initials = (name || "?").split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase();
  return (
    <div className={`${sz} rounded-full bg-[#0F2847] text-white flex items-center justify-center font-semibold flex-shrink-0`}>
      {initials}
    </div>
  );
}

function StarRatingInput({ value, onChange, max = 5 }) {
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: max }).map((_, i) => (
        <button
          key={i}
          type="button"
          onClick={() => onChange(i + 1)}
          className={`text-xl transition-colors ${i < value ? "text-amber-400 hover:text-amber-500" : "text-slate-200 hover:text-amber-300"}`}
        >
          ★
        </button>
      ))}
    </div>
  );
}

function StarDisplay({ rating, max = 5 }) {
  const r = Math.round(rating || 0);
  return (
    <span className="text-amber-400 text-base tracking-tight">
      {Array.from({ length: max }).map((_, i) => (
        <span key={i} className={i < r ? "text-amber-400" : "text-slate-200"}>★</span>
      ))}
    </span>
  );
}

function SectionCard({ title, children, action, className = "" }) {
  return (
    <div className={`bg-white border border-slate-200 rounded-md ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
          {title && <h3 className="text-sm font-semibold text-slate-900">{title}</h3>}
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

function TabLoading() {
  return (
    <div className="flex items-center justify-center py-16 gap-2 text-slate-400">
      <Loader2 size={16} className="animate-spin" />
      <span className="text-sm">Loading...</span>
    </div>
  );
}

function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="text-center py-12">
      <Icon size={32} className="mx-auto text-slate-300 mb-3" />
      <div className="text-sm font-medium text-slate-600">{title}</div>
      {description && <p className="text-xs text-slate-400 mt-1">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

function Input({ className = "", ...props }) {
  return (
    <input
      className={`w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] ${className}`}
      {...props}
    />
  );
}

function Textarea({ className = "", ...props }) {
  return (
    <textarea
      className={`w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] resize-none ${className}`}
      {...props}
    />
  );
}

function Select({ className = "", children, ...props }) {
  return (
    <select
      className={`w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] bg-white ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}

function Label({ children, required }) {
  return (
    <label className="block text-xs font-semibold text-slate-700 mb-1">
      {children}{required && <span className="text-red-500 ml-0.5">*</span>}
    </label>
  );
}

function PrimaryBtn({ children, loading, className = "", ...props }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 bg-[#0F2847] text-white text-sm px-4 py-2 rounded-lg hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors ${className}`}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading && <Loader2 size={13} className="animate-spin" />}
      {children}
    </button>
  );
}

function GhostBtn({ children, className = "", ...props }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 text-sm px-4 py-2 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 font-medium transition-colors ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

const RECOMMENDATIONS = [
  { value: "accept", label: "Accept" },
  { value: "minor_revisions", label: "Minor Revisions" },
  { value: "major_revisions", label: "Major Revisions" },
  { value: "reject", label: "Reject" },
  { value: "resubmit", label: "Resubmit Elsewhere" },
];

const REC_COLORS = {
  accept:           "bg-emerald-100 text-emerald-700 border border-emerald-200",
  minor_revisions:  "bg-blue-100 text-blue-700 border border-blue-200",
  major_revisions:  "bg-amber-100 text-amber-700 border border-amber-200",
  reject:           "bg-red-100 text-red-700 border border-red-200",
  resubmit:         "bg-slate-100 text-slate-600 border border-slate-200",
};

const CONFLICT_TYPE_COLORS = {
  coauthor:         "bg-red-100 text-red-700",
  same_institution: "bg-amber-100 text-amber-700",
  advisor:          "bg-orange-100 text-orange-700",
  competing:        "bg-purple-100 text-purple-700",
  personal:         "bg-rose-100 text-rose-700",
};

// ─── Overview Tab ─────────────────────────────────────────────────────────────

function OverviewTab({ request, user, onInvite }) {
  const [inviteUserId, setInviteUserId] = useState("");
  const [inviteDue, setInviteDue] = useState("");
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState(null);

  const isOwner = request?.owner_id === user?.id || request?.owner_id === user?._id;

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!inviteUserId.trim()) return;
    setInviting(true);
    setInviteMsg(null);
    try {
      await api.post(`/reviewer-marketplace/requests/${request._id || request.id}/invite`, {
        reviewer_user_id: inviteUserId.trim(),
        ...(inviteDue ? { due_date: inviteDue } : {}),
      });
      setInviteMsg({ type: "success", text: "Invitation sent successfully." });
      setInviteUserId("");
      setInviteDue("");
      if (onInvite) onInvite();
    } catch (err) {
      setInviteMsg({ type: "error", text: err?.response?.data?.detail || "Failed to send invitation." });
    } finally {
      setInviting(false);
    }
  };

  if (!request) return null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left — main content */}
      <div className="lg:col-span-2 space-y-5">
        {request.description && (
          <SectionCard title="Description">
            <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{request.description}</p>
          </SectionCard>
        )}

        {(request.required_expertise || []).length > 0 && (
          <SectionCard title="Required Expertise">
            <div className="flex flex-wrap gap-1.5">
              {request.required_expertise.map((e, i) => (
                <Chip key={i} label={e} color="indigo" />
              ))}
            </div>
          </SectionCard>
        )}

        {(request.keywords || []).length > 0 && (
          <SectionCard title="Keywords">
            <div className="flex flex-wrap gap-1.5">
              {request.keywords.map((k, i) => (
                <Chip key={i} label={k} color="slate" />
              ))}
            </div>
          </SectionCard>
        )}

        {(request.research_area || request.methodology) && (
          <SectionCard title="Research Details">
            <div className="space-y-2">
              {request.research_area && (
                <div className="flex gap-3 text-sm">
                  <span className="text-slate-500 w-28 flex-shrink-0">Research Area</span>
                  <span className="text-slate-900 font-medium">{request.research_area}</span>
                </div>
              )}
              {request.methodology && (
                <div className="flex gap-3 text-sm">
                  <span className="text-slate-500 w-28 flex-shrink-0">Methodology</span>
                  <span className="text-slate-900">{request.methodology}</span>
                </div>
              )}
            </div>
          </SectionCard>
        )}
      </div>

      {/* Right — stats + invite */}
      <div className="space-y-4">
        <SectionCard title="Request Details">
          <div className="space-y-3">
            {[
              { label: "Status", value: <StatusBadge status={request.status} /> },
              { label: "Type", value: <TypeBadge type={request.review_type} /> },
              { label: "Confidentiality", value: <ConfBadge value={request.confidentiality} /> },
              { label: "Deadline", value: <span className="text-sm text-slate-700">{fmt(request.deadline)}</span> },
              { label: "Assignments", value: <span className="text-sm font-semibold text-slate-900">{request.assignments_count ?? (request.assignments || []).length}</span> },
              { label: "Conflicts", value: <span className="text-sm font-semibold text-slate-900">{request.conflicts_count ?? 0}</span> },
              { label: "Visibility", value: <span className="text-sm text-slate-700">{cap(request.visibility)}</span> },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center justify-between gap-2">
                <span className="text-xs text-slate-500">{label}</span>
                {value}
              </div>
            ))}
          </div>
        </SectionCard>

        {isOwner && (
          <SectionCard title="Quick Invite">
            <form onSubmit={handleInvite} className="space-y-3">
              <div>
                <Label>Reviewer User ID</Label>
                <Input
                  value={inviteUserId}
                  onChange={e => setInviteUserId(e.target.value)}
                  placeholder="Enter user ID..."
                />
              </div>
              <div>
                <Label>Due Date (optional)</Label>
                <Input type="date" value={inviteDue} onChange={e => setInviteDue(e.target.value)} />
              </div>
              {inviteMsg && (
                <div className={`text-xs px-3 py-2 rounded-lg ${inviteMsg.type === "success" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-red-50 text-red-600 border border-red-200"}`}>
                  {inviteMsg.text}
                </div>
              )}
              <PrimaryBtn type="submit" loading={inviting} className="w-full">
                <UserCheck size={13} />
                Send Invitation
              </PrimaryBtn>
            </form>
          </SectionCard>
        )}
      </div>
    </div>
  );
}

// ─── Matches Tab ─────────────────────────────────────────────────────────────

function MatchesTab({ requestId, data, loading, onRefresh }) {
  const [inviting, setInviting] = useState({});
  const [invitedSet, setInvitedSet] = useState(new Set());
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await api.post(`/reviewer-marketplace/requests/${requestId}/matches/refresh`);
      if (onRefresh) await onRefresh();
    } catch {}
    setRefreshing(false);
  };

  const handleInvite = async (reviewer) => {
    const uid = reviewer.user_id || reviewer._id;
    setInviting(prev => ({ ...prev, [uid]: true }));
    try {
      await api.post(`/reviewer-marketplace/requests/${requestId}/invite`, {
        reviewer_user_id: uid,
      });
      setInvitedSet(prev => new Set([...prev, uid]));
    } catch {}
    setInviting(prev => ({ ...prev, [uid]: false }));
  };

  if (loading) return <TabLoading />;

  const matches = data?.matches || data || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-500">{matches.length} match{matches.length !== 1 ? "es" : ""} found</div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 text-xs text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw size={12} className={refreshing ? "animate-spin" : ""} />
          Refresh Matches
        </button>
      </div>

      {matches.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No matches found"
          description="Click Refresh Matches to find qualified reviewers for this request."
        />
      ) : (
        <div className="space-y-3">
          {matches.map((match, idx) => {
            const uid = match.user_id || match.reviewer_user_id || match._id;
            const name = match.user?.full_name || match.user?.name || match.name || "Reviewer";
            const institution = match.user?.institution || match.institution || "";
            const score = match.reviewer?.reviewer_score || match.reviewer_score || 0;
            const matchScore = match.match_score || {};
            const isInvited = invitedSet.has(uid) || match.is_invited;

            return (
              <div key={uid || idx} className="bg-white border border-slate-200 rounded-md p-5 flex items-start gap-4 hover:border-slate-300 hover:shadow-sm transition-all">
                <InitialAvatar name={name} />
                <div className="flex-1 min-w-0 space-y-3">
                  <div>
                    <div className="font-semibold text-slate-900 text-sm">{name}</div>
                    {institution && <div className="text-xs text-slate-400">{institution}</div>}
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs text-slate-600 mb-0.5">
                      <span>Reviewer Score</span>
                      <span className="font-semibold">{score.toFixed(0)}/100</span>
                    </div>
                    <DivBar value={score} max={100} />
                  </div>
                  {Object.keys(matchScore).length > 0 && (
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                      {[
                        { key: "area_match", label: "Area Match", color: "bg-blue-500" },
                        { key: "quality", label: "Quality", color: "bg-indigo-500" },
                        { key: "availability", label: "Availability", color: "bg-emerald-500" },
                        { key: "diversity", label: "Diversity", color: "bg-amber-500" },
                      ].map(({ key, label, color }) => (
                        matchScore[key] != null && (
                          <div key={key} className="space-y-0.5">
                            <div className="flex justify-between text-xs text-slate-500">
                              <span>{label}</span>
                              <span className="font-medium">{(matchScore[key] * 100).toFixed(0)}%</span>
                            </div>
                            <DivBar value={matchScore[key] * 100} max={100} color={color} />
                          </div>
                        )
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex-shrink-0 mt-1">
                  {isInvited ? (
                    <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <CheckCircle size={12} />
                      Invited
                    </span>
                  ) : (
                    <PrimaryBtn
                      onClick={() => handleInvite(match)}
                      loading={inviting[uid]}
                    >
                      Invite
                    </PrimaryBtn>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Assignments Tab ──────────────────────────────────────────────────────────

function AssignmentsTab({ request, user }) {
  const assignments = request?.assignments || [];
  const [actionLoading, setActionLoading] = useState({});
  const [updated, setUpdated] = useState({});

  const ownerId = request?.owner_id;
  const userId = user?.id || user?._id;
  const isOwner = ownerId === userId;

  const myAssignment = assignments.find(a => (a.reviewer_user_id === userId || a.reviewer?.id === userId));

  const handleAction = async (assignId, status) => {
    setActionLoading(prev => ({ ...prev, [assignId]: status }));
    try {
      await api.patch(`/reviewer-marketplace/assignments/${assignId}`, { status });
      setUpdated(prev => ({ ...prev, [assignId]: status }));
    } catch {}
    setActionLoading(prev => ({ ...prev, [assignId]: null }));
  };

  if (assignments.length === 0) {
    return (
      <EmptyState
        icon={Users}
        title="No assignments yet"
        description="Invite reviewers from the Matches tab to get assignments."
      />
    );
  }

  return (
    <div className="space-y-3">
      {assignments.map((assignment, idx) => {
        const aId = assignment._id || assignment.id;
        const status = updated[aId] || assignment.status;
        const isMyAssignment = assignment.reviewer_user_id === userId || assignment.reviewer?.id === userId;
        const reviewerName = assignment.reviewer?.full_name || assignment.reviewer?.name || "Reviewer";

        return (
          <div key={aId || idx} className="bg-white border border-slate-200 rounded-md p-5 flex items-start gap-4 hover:border-slate-300 transition-all">
            <InitialAvatar name={isOwner ? reviewerName : "You"} />
            <div className="flex-1 min-w-0 space-y-1">
              {isOwner ? (
                <div className="font-semibold text-slate-900 text-sm">{reviewerName}</div>
              ) : (
                <div className="font-semibold text-slate-900 text-sm">Your Assignment</div>
              )}
              {isOwner && assignment.reviewer?.institution && (
                <div className="text-xs text-slate-400">{assignment.reviewer.institution}</div>
              )}
              <div className="flex items-center gap-2 flex-wrap mt-1">
                <StatusBadge status={status} map={ASSIGN_STATUS_COLORS} />
                {assignment.due_date && (
                  <span className="text-xs text-slate-400">Due {fmt(assignment.due_date)}</span>
                )}
                <span className="text-xs text-slate-400">Invited {fmt(assignment.invited_at)}</span>
              </div>
            </div>
            {isMyAssignment && status === "invited" && (
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={() => handleAction(aId, "accepted")}
                  disabled={!!actionLoading[aId]}
                  className="text-xs text-white bg-emerald-600 px-3 py-1.5 rounded-lg hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-1"
                >
                  {actionLoading[aId] === "accepted" && <Loader2 size={11} className="animate-spin" />}
                  <CheckCircle size={12} />
                  Accept
                </button>
                <button
                  onClick={() => handleAction(aId, "declined")}
                  disabled={!!actionLoading[aId]}
                  className="text-xs text-red-600 border border-red-200 px-3 py-1.5 rounded-lg hover:bg-red-50 disabled:opacity-50 flex items-center gap-1"
                >
                  {actionLoading[aId] === "declined" && <Loader2 size={11} className="animate-spin" />}
                  <XCircle size={12} />
                  Decline
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Report Section Form ──────────────────────────────────────────────────────

function ReportSection({ section, onChange, onRemove }) {
  return (
    <div className="border border-slate-200 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <Input
          value={section.title}
          onChange={e => onChange({ ...section, title: e.target.value })}
          placeholder="Section title (e.g. Introduction, Methods)"
          className="flex-1"
        />
        <button onClick={onRemove} className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors">
          <Trash2 size={14} />
        </button>
      </div>
      <div>
        <Label>Score (0–10)</Label>
        <div className="flex items-center gap-3">
          <input
            type="range"
            min={0}
            max={10}
            step={0.5}
            value={section.score || 0}
            onChange={e => onChange({ ...section, score: parseFloat(e.target.value) })}
            className="flex-1 h-1.5 accent-[#0F2847]"
          />
          <span className="text-sm font-semibold text-[#0F2847] w-8 text-right">{section.score || 0}</span>
        </div>
      </div>
      <div>
        <Label>Comments</Label>
        <Textarea
          rows={3}
          value={section.comments}
          onChange={e => onChange({ ...section, comments: e.target.value })}
          placeholder="Provide detailed feedback for this section..."
        />
      </div>
    </div>
  );
}

// ─── Report Tab ───────────────────────────────────────────────────────────────

function ReportTab({ requestId, request, data, loading, user, onSubmit }) {
  const assignments = request?.assignments || [];
  const userId = user?.id || user?._id;
  const ownerId = request?.owner_id;
  const isOwner = ownerId === userId;

  const myAssignment = assignments.find(
    a => (a.reviewer_user_id === userId || a.reviewer?.id === userId) && a.status === "accepted"
  );

  const report = data?.report || data;

  // Rating state (for owner)
  const [rating, setRating] = useState({ rating: 0, timeliness: 0, quality: 0, helpfulness: 0, comment: "" });
  const [rating_submitted, setRatingSubmitted] = useState(false);
  const [rating_loading, setRatingLoading] = useState(false);
  const [rating_error, setRatingError] = useState("");

  // Report form state (for reviewer)
  const [form, setForm] = useState({
    overall_recommendation: "",
    overall_score: 5,
    summary_comments: "",
    sections: [],
    confidential_comments: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const setForm2 = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const addSection = () => setForm(f => ({ ...f, sections: [...f.sections, { title: "", score: 5, comments: "" }] }));
  const updateSection = (i, s) => setForm(f => ({ ...f, sections: f.sections.map((sec, idx) => idx === i ? s : sec) }));
  const removeSection = (i) => setForm(f => ({ ...f, sections: f.sections.filter((_, idx) => idx !== i) }));

  const handleSubmitReport = async (e) => {
    e.preventDefault();
    if (!myAssignment) return;
    if (!form.overall_recommendation) { setSubmitError("Please select a recommendation."); return; }
    setSubmitting(true);
    setSubmitError("");
    try {
      const aId = myAssignment._id || myAssignment.id;
      await api.post(`/reviewer-marketplace/assignments/${aId}/report`, form);
      if (onSubmit) onSubmit();
    } catch (err) {
      setSubmitError(err?.response?.data?.detail || "Failed to submit report.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRateReviewer = async (e) => {
    e.preventDefault();
    setRatingLoading(true);
    setRatingError("");
    try {
      await api.post(`/reviewer-marketplace/requests/${requestId}/rate-reviewer`, rating);
      setRatingSubmitted(true);
    } catch (err) {
      setRatingError(err?.response?.data?.detail || "Failed to submit rating.");
    } finally {
      setRatingLoading(false);
    }
  };

  if (loading) return <TabLoading />;

  // Reviewer with accepted assignment — show form or submitted confirmation
  if (myAssignment && !isOwner) {
    if (report && (report.overall_recommendation || report.summary_comments)) {
      return (
        <div className="space-y-4">
          <div className="bg-emerald-50 border border-emerald-200 rounded-md p-4 flex items-center gap-3">
            <CheckCircle size={16} className="text-emerald-600" />
            <span className="text-sm font-medium text-emerald-700">Your report has been submitted.</span>
          </div>
          <SectionCard title="Submitted Report">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${REC_COLORS[report.overall_recommendation] || "bg-slate-100 text-slate-600"}`}>
                  {cap(report.overall_recommendation)}
                </span>
                <span className="text-sm text-slate-600">Overall Score: <strong className="text-[#0F2847]">{report.overall_score}/10</strong></span>
              </div>
              {report.summary_comments && (
                <div>
                  <div className="text-xs font-semibold text-slate-500 mb-1">Summary</div>
                  <p className="text-sm text-slate-700 whitespace-pre-wrap">{report.summary_comments}</p>
                </div>
              )}
            </div>
          </SectionCard>
        </div>
      );
    }

    return (
      <form onSubmit={handleSubmitReport} className="space-y-5">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-slate-900">Submit Review Report</h3>
        </div>
        {submitError && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{submitError}</div>
        )}
        <SectionCard title="Recommendation & Score">
          <div className="space-y-4">
            <div>
              <Label required>Overall Recommendation</Label>
              <Select value={form.overall_recommendation} onChange={e => setForm2("overall_recommendation", e.target.value)}>
                <option value="">Select recommendation...</option>
                {RECOMMENDATIONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
              </Select>
            </div>
            <div>
              <div className="flex justify-between text-xs font-semibold text-slate-700 mb-2">
                <Label>Overall Score</Label>
                <span className="text-[#0F2847] font-bold">{form.overall_score}/10</span>
              </div>
              <input
                type="range"
                min={0}
                max={10}
                step={0.5}
                value={form.overall_score}
                onChange={e => setForm2("overall_score", parseFloat(e.target.value))}
                className="w-full h-1.5 accent-[#0F2847]"
              />
              <div className="flex justify-between text-xs text-slate-400 mt-1">
                <span>0 — Poor</span>
                <span>10 — Excellent</span>
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Summary Comments">
          <Textarea
            rows={6}
            value={form.summary_comments}
            onChange={e => setForm2("summary_comments", e.target.value)}
            placeholder="Provide a comprehensive summary of your review, major findings, and key recommendations..."
          />
        </SectionCard>

        <SectionCard
          title="Review Sections"
          action={
            <button type="button" onClick={addSection} className="inline-flex items-center gap-1 text-xs text-[#0F2847] font-medium hover:underline">
              <Plus size={12} /> Add Section
            </button>
          }
        >
          {form.sections.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-sm text-slate-400">No sections added. Sections let you organize feedback by topic.</p>
              <button type="button" onClick={addSection} className="mt-3 text-xs text-[#0F2847] font-medium hover:underline">
                + Add your first section
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {form.sections.map((section, i) => (
                <ReportSection
                  key={i}
                  section={section}
                  onChange={(s) => updateSection(i, s)}
                  onRemove={() => removeSection(i)}
                />
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Confidential Comments">
          <p className="text-xs text-slate-400 mb-2">These comments are visible only to the requester, not to the author.</p>
          <Textarea
            rows={4}
            value={form.confidential_comments}
            onChange={e => setForm2("confidential_comments", e.target.value)}
            placeholder="Comments for the requester only (not visible to the author)..."
          />
        </SectionCard>

        <div className="flex justify-end gap-3">
          <PrimaryBtn type="submit" loading={submitting}>
            <FileText size={13} />
            Submit Report
          </PrimaryBtn>
        </div>
      </form>
    );
  }

  // Owner view — see submitted report(s)
  if (isOwner) {
    if (!report || (!report.overall_recommendation && !report.summary_comments)) {
      return (
        <EmptyState
          icon={FileText}
          title="No report submitted yet"
          description="The reviewer has not submitted their report yet."
        />
      );
    }

    return (
      <div className="space-y-5">
        <SectionCard title="Review Report">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${REC_COLORS[report.overall_recommendation] || "bg-slate-100 text-slate-600"}`}>
                {cap(report.overall_recommendation)}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-500">Overall Score:</span>
                <span className="text-xl font-bold text-[#0F2847]">{report.overall_score}</span>
                <span className="text-sm text-slate-400">/10</span>
              </div>
            </div>

            {report.summary_comments && (
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Summary</div>
                <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{report.summary_comments}</p>
              </div>
            )}

            {(report.sections || []).length > 0 && (
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Section Reviews</div>
                <div className="space-y-3">
                  {report.sections.map((section, i) => (
                    <div key={i} className="border border-slate-200 rounded-lg p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-slate-900 text-sm">{section.title}</span>
                        <span className="text-sm font-bold text-[#0F2847]">{section.score}/10</span>
                      </div>
                      <DivBar value={section.score} max={10} />
                      {section.comments && (
                        <p className="text-xs text-slate-600 leading-relaxed pt-1">{section.comments}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {report.confidential_comments && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Lock size={12} className="text-amber-600" />
                  <span className="text-xs font-semibold text-amber-700">Confidential Comments</span>
                </div>
                <p className="text-sm text-amber-900 whitespace-pre-wrap">{report.confidential_comments}</p>
              </div>
            )}
          </div>
        </SectionCard>

        {/* Rate Reviewer */}
        {!rating_submitted ? (
          <SectionCard title="Rate This Reviewer">
            <form onSubmit={handleRateReviewer} className="space-y-4">
              {rating_error && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{rating_error}</div>
              )}
              {[
                { key: "rating", label: "Overall Rating" },
                { key: "timeliness", label: "Timeliness" },
                { key: "quality", label: "Review Quality" },
                { key: "helpfulness", label: "Helpfulness" },
              ].map(({ key, label }) => (
                <div key={key} className="flex items-center justify-between gap-4">
                  <span className="text-sm text-slate-700 w-32">{label}</span>
                  <StarRatingInput
                    value={rating[key]}
                    onChange={v => setRating(r => ({ ...r, [key]: v }))}
                  />
                </div>
              ))}
              <div>
                <Label>Comment (optional)</Label>
                <Textarea
                  rows={3}
                  value={rating.comment}
                  onChange={e => setRating(r => ({ ...r, comment: e.target.value }))}
                  placeholder="Share your experience with this reviewer..."
                />
              </div>
              <div className="flex justify-end">
                <PrimaryBtn type="submit" loading={rating_loading}>
                  <Star size={13} />
                  Submit Rating
                </PrimaryBtn>
              </div>
            </form>
          </SectionCard>
        ) : (
          <div className="bg-emerald-50 border border-emerald-200 rounded-md p-4 flex items-center gap-3">
            <CheckCircle size={16} className="text-emerald-600" />
            <span className="text-sm font-medium text-emerald-700">Thank you — your rating has been submitted.</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <EmptyState
      icon={FileText}
      title="No access to report"
      description="You do not have permission to view this report."
    />
  );
}

// ─── Conflicts Tab ────────────────────────────────────────────────────────────

function ConflictsTab({ requestId, data, loading }) {
  const [checkUid, setCheckUid] = useState("");
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState(null);
  const [checkError, setCheckError] = useState("");

  const handleCheck = async (e) => {
    e.preventDefault();
    if (!checkUid.trim()) return;
    setChecking(true);
    setCheckResult(null);
    setCheckError("");
    try {
      const res = await api.post(`/reviewer-marketplace/requests/${requestId}/check-conflict/${checkUid.trim()}`);
      setCheckResult(res.data);
    } catch (err) {
      setCheckError(err?.response?.data?.detail || "Failed to check conflict.");
    } finally {
      setChecking(false);
    }
  };

  if (loading) return <TabLoading />;

  const conflicts = data?.conflicts || data || [];

  return (
    <div className="space-y-5">
      {conflicts.length === 0 ? (
        <div className="bg-emerald-50 border border-emerald-200 rounded-md p-6 flex items-start gap-3">
          <CheckCircle size={18} className="text-emerald-600 mt-0.5 flex-shrink-0" />
          <div>
            <div className="font-medium text-emerald-800 text-sm">No conflicts detected</div>
            <p className="text-xs text-emerald-600 mt-0.5">This request has no identified conflicts of interest.</p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {conflicts.map((conflict, i) => (
            <div key={conflict._id || i} className="bg-white border border-slate-200 rounded-md p-4 flex items-start gap-3">
              <AlertTriangle size={16} className="text-amber-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${CONFLICT_TYPE_COLORS[conflict.type] || "bg-slate-100 text-slate-600"}`}>
                    {cap(conflict.type)}
                  </span>
                  {conflict.auto_detected && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-600 border border-blue-200">
                      <Shield size={10} />
                      Auto-detected
                    </span>
                  )}
                </div>
                {conflict.details && (
                  <p className="text-sm text-slate-700">{conflict.details}</p>
                )}
                {conflict.detected_at && (
                  <div className="text-xs text-slate-400">{fmt(conflict.detected_at)}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Manual conflict check */}
      <SectionCard title="Manual Conflict Check">
        <form onSubmit={handleCheck} className="space-y-3">
          <p className="text-xs text-slate-500">Check if a specific user has any conflicts with this review request.</p>
          <div className="flex gap-2">
            <Input
              value={checkUid}
              onChange={e => setCheckUid(e.target.value)}
              placeholder="Enter user ID to check..."
              className="flex-1"
            />
            <PrimaryBtn type="submit" loading={checking}>
              Check
            </PrimaryBtn>
          </div>
          {checkError && (
            <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{checkError}</div>
          )}
          {checkResult && (
            <div className={`rounded-lg px-4 py-3 text-sm ${checkResult.has_conflict ? "bg-red-50 border border-red-200 text-red-700" : "bg-emerald-50 border border-emerald-200 text-emerald-700"}`}>
              <div className="flex items-center gap-2 font-medium">
                {checkResult.has_conflict ? <AlertTriangle size={14} /> : <CheckCircle size={14} />}
                {checkResult.has_conflict ? "Conflict detected" : "No conflict found"}
              </div>
              {checkResult.conflicts && checkResult.conflicts.length > 0 && (
                <ul className="mt-2 text-xs space-y-0.5">
                  {checkResult.conflicts.map((c, i) => (
                    <li key={i}>• {cap(c.type)}: {c.details}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </form>
      </SectionCard>
    </div>
  );
}

// ─── Settings Tab ─────────────────────────────────────────────────────────────

function SettingsTab({ requestId, request, user, onUpdate }) {
  const ownerId = request?.owner_id;
  const userId = user?.id || user?._id;
  const isOwner = ownerId === userId;

  const [form, setForm] = useState({
    title: request?.title || "",
    description: request?.description || "",
    required_expertise: (request?.required_expertise || []).join(", "),
    deadline: request?.deadline ? request.deadline.split("T")[0] : "",
    visibility: request?.visibility || "public",
  });
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);
  const [archiving, setArchiving] = useState(false);

  const setF = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveMsg(null);
    try {
      const payload = {
        ...form,
        required_expertise: form.required_expertise.split(",").map(s => s.trim()).filter(Boolean),
      };
      const res = await api.patch(`/reviewer-marketplace/requests/${requestId}`, payload);
      setSaveMsg({ type: "success", text: "Settings saved successfully." });
      if (onUpdate) onUpdate(res.data);
    } catch (err) {
      setSaveMsg({ type: "error", text: err?.response?.data?.detail || "Failed to save settings." });
    } finally {
      setSaving(false);
    }
  };

  const handleArchive = async () => {
    if (!window.confirm("Archive this review request? This cannot be undone.")) return;
    setArchiving(true);
    try {
      const res = await api.patch(`/reviewer-marketplace/requests/${requestId}`, { status: "archived" });
      if (onUpdate) onUpdate(res.data);
      setSaveMsg({ type: "success", text: "Request archived." });
    } catch (err) {
      setSaveMsg({ type: "error", text: err?.response?.data?.detail || "Failed to archive request." });
    } finally {
      setArchiving(false);
    }
  };

  if (!isOwner) {
    return (
      <EmptyState
        icon={Shield}
        title="Access restricted"
        description="Only the request owner can access settings."
      />
    );
  }

  return (
    <form onSubmit={handleSave} className="space-y-5 max-w-2xl">
      <SectionCard title="Edit Request">
        <div className="space-y-4">
          {saveMsg && (
            <div className={`text-sm px-3 py-2 rounded-lg ${saveMsg.type === "success" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-red-50 text-red-600 border border-red-200"}`}>
              {saveMsg.text}
            </div>
          )}
          <div>
            <Label required>Title</Label>
            <Input value={form.title} onChange={e => setF("title", e.target.value)} />
          </div>
          <div>
            <Label>Description</Label>
            <Textarea rows={5} value={form.description} onChange={e => setF("description", e.target.value)} />
          </div>
          <div>
            <Label>Required Expertise</Label>
            <Input
              value={form.required_expertise}
              onChange={e => setF("required_expertise", e.target.value)}
              placeholder="Comma-separated expertise areas"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Deadline</Label>
              <Input type="date" value={form.deadline} onChange={e => setF("deadline", e.target.value)} />
            </div>
            <div>
              <Label>Visibility</Label>
              <Select value={form.visibility} onChange={e => setF("visibility", e.target.value)}>
                <option value="public">Public</option>
                <option value="private">Private</option>
              </Select>
            </div>
          </div>
          <div className="flex justify-end">
            <PrimaryBtn type="submit" loading={saving}>
              <Save size={13} />
              Save Changes
            </PrimaryBtn>
          </div>
        </div>
      </SectionCard>

      <div className="border border-red-200 rounded-md p-5 bg-red-50">
        <h4 className="text-sm font-semibold text-red-800 mb-1">Danger Zone</h4>
        <p className="text-xs text-red-600 mb-4">Archiving this request will close it and stop all matching. This cannot be undone.</p>
        <button
          type="button"
          onClick={handleArchive}
          disabled={archiving || request?.status === "archived"}
          className="inline-flex items-center gap-2 text-sm text-red-700 border border-red-300 px-4 py-2 rounded-lg hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {archiving ? <Loader2 size={13} className="animate-spin" /> : <Archive size={13} />}
          Archive Request
        </button>
      </div>
    </form>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function ReviewWorkspace() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [request, setRequest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [tabData, setTabData] = useState({});
  const [tabLoading, setTabLoading] = useState({});
  const [closing, setClosing] = useState(false);

  const loadedTabs = useRef(new Set());

  const fetchRequest = useCallback(async () => {
    try {
      const res = await api.get(`/reviewer-marketplace/requests/${id}`);
      setRequest(res.data);
    } catch {
      setRequest(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchRequest();
  }, [fetchRequest]);

  const loadTab = useCallback(async (tab) => {
    if (loadedTabs.current.has(tab)) return;
    loadedTabs.current.add(tab);
    setTabLoading(prev => ({ ...prev, [tab]: true }));

    try {
      let result = null;
      if (tab === "matches") {
        const res = await api.get(`/reviewer-marketplace/requests/${id}/matches`);
        result = res.data;
      } else if (tab === "report") {
        try {
          const res = await api.get(`/reviewer-marketplace/requests/${id}/report`);
          result = res.data;
        } catch (e) {
          if (e?.response?.status === 404) result = null;
          else throw e;
        }
      } else if (tab === "conflicts") {
        const res = await api.get(`/reviewer-marketplace/requests/${id}/conflicts`);
        result = res.data;
      }
      setTabData(prev => ({ ...prev, [tab]: result }));
    } catch {}
    setTabLoading(prev => ({ ...prev, [tab]: false }));
  }, [id]);

  useEffect(() => {
    if (activeTab !== "overview" && activeTab !== "assignments" && activeTab !== "settings" && activeTab !== "analytics") {
      loadTab(activeTab);
    }
  }, [activeTab, loadTab]);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };

  const refreshTab = async (tab) => {
    loadedTabs.current.delete(tab);
    await loadTab(tab);
  };

  const handleCloseRequest = async () => {
    if (!window.confirm("Close this review request?")) return;
    setClosing(true);
    try {
      const res = await api.patch(`/reviewer-marketplace/requests/${id}`, { status: "completed" });
      setRequest(res.data);
    } catch {}
    setClosing(false);
  };

  const isOwner = request?.owner_id === (user?.id || user?._id);
  const canClose = isOwner && request && !["completed", "archived"].includes(request.status);

  const TABS = [
    { key: "overview",     label: "Overview",     icon: Eye },
    { key: "matches",      label: "Matches",      icon: Users },
    { key: "assignments",  label: "Assignments",  icon: UserCheck },
    { key: "report",       label: "Report",       icon: FileText },
    { key: "conflicts",    label: "Conflicts",    icon: AlertTriangle },
    { key: "settings",     label: "Settings",     icon: Edit2 },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 gap-2 text-slate-400">
        <Loader2 size={20} className="animate-spin" />
        <span>Loading workspace...</span>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="text-center py-24">
        <AlertCircle size={40} className="mx-auto text-slate-300 mb-4" />
        <div className="text-lg font-semibold text-slate-600">Review request not found</div>
        <p className="text-sm text-slate-400 mt-2">This request may have been removed or you don't have access.</p>
        <Link
          to="/reviewer-marketplace"
          className="mt-6 inline-flex items-center gap-2 text-sm text-[#0F2847] font-medium border border-slate-200 px-4 py-2 rounded-lg hover:bg-slate-50 transition-colors"
        >
          <ArrowLeft size={14} />
          Back to Marketplace
        </Link>
      </div>
    );
  }

  return (
    <ResearchLayout
      title={request.title}
      subtitle={cap(request.review_type) || ""}
      actions={
        canClose ? (
          <button
            onClick={handleCloseRequest}
            disabled={closing}
            className="flex-shrink-0 inline-flex items-center gap-2 text-sm text-slate-600 border border-slate-200 px-4 py-2 rounded-lg hover:bg-slate-50 disabled:opacity-50 transition-colors"
          >
            {closing ? <Loader2 size={13} className="animate-spin" /> : <XCircle size={13} />}
            Close Request
          </button>
        ) : undefined
      }
    >
    <div className="space-y-6 pb-16">
      {/* Header */}
      <div className="space-y-2">
        <Link
          to="/reviewer-marketplace"
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition-colors"
        >
          <ArrowLeft size={14} />
          Reviewer Marketplace
        </Link>
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={request.status} />
          <TypeBadge type={request.review_type} />
          <ConfBadge value={request.confidentiality} />
          {request.deadline && (
            <div className="flex items-center gap-1 text-xs text-slate-500">
              <Calendar size={11} />
              <span>Due {fmt(request.deadline)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-200 overflow-x-auto">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => handleTabChange(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px flex-shrink-0 ${
              activeTab === key
                ? "border-[#0F2847] text-[#0F2847]"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "overview" && (
          <OverviewTab
            request={request}
            user={user}
            onInvite={() => loadedTabs.current.delete("assignments")}
          />
        )}

        {activeTab === "matches" && (
          <MatchesTab
            requestId={id}
            data={tabData.matches}
            loading={!!tabLoading.matches}
            onRefresh={() => refreshTab("matches")}
          />
        )}

        {activeTab === "assignments" && (
          <AssignmentsTab request={request} user={user} />
        )}

        {activeTab === "report" && (
          <ReportTab
            requestId={id}
            request={request}
            data={tabData.report}
            loading={!!tabLoading.report}
            user={user}
            onSubmit={() => {
              loadedTabs.current.delete("report");
              loadTab("report");
            }}
          />
        )}

        {activeTab === "conflicts" && (
          <ConflictsTab
            requestId={id}
            data={tabData.conflicts}
            loading={!!tabLoading.conflicts}
          />
        )}

        {activeTab === "settings" && (
          <SettingsTab
            requestId={id}
            request={request}
            user={user}
            onUpdate={(updated) => setRequest(updated)}
          />
        )}
      </div>
    </div>
    </ResearchLayout>
  );
}

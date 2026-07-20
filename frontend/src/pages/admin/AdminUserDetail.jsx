import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ArrowLeft, User, FolderOpen, FileText, Users2, BookOpen, RadioTower } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { Spinner } from "@/components/ds/LoadingState";
import { ErrorState } from "@/components/ds/ErrorState";
import { NavTabs } from "@/components/ds/NavTabs";
import { EmptyState } from "@/components/ds/EmptyState";
import {
  RelatedEntityPanel, SmartActionsBar, Timeline, TimelineItem, Banner,
} from "@/components/ds";
import { useAdminRealtime } from "@/contexts/AdminRealtimeContext";

const TABS = ["Overview", "Timeline", "Actions"];

function PlanBadge({ plan }) {
  const styles = {
    free: "bg-slate-100 text-slate-700",
    researcher: "bg-blue-50 text-blue-700",
    pro_researcher: "bg-indigo-50 text-indigo-700",
    institution: "bg-purple-50 text-purple-700",
  };
  return <span className={`inline-block px-2 py-0.5 text-xs font-medium ${styles[plan] || styles.free}`}>{plan?.replace("_", " ") || "free"}</span>;
}

function StatusBadge({ status }) {
  const styles = { active: "bg-green-50 text-green-700", suspended: "bg-amber-50 text-amber-700", banned: "bg-red-50 text-red-800" };
  return <span className={`inline-block px-2 py-0.5 text-xs font-medium ${styles[status] || styles.active}`}>{status || "active"}</span>;
}

function KV({ label, children }) {
  return (
    <div className="flex py-2 border-b border-slate-100 last:border-0">
      <span className="text-xs font-semibold uppercase tracking-widest text-slate-400 w-40 flex-shrink-0 pt-0.5">{label}</span>
      <span className="text-sm text-slate-900">{children ?? "—"}</span>
    </div>
  );
}

function ActionCard({ title, desc, children, id }) {
  return (
    <div id={id} className="border border-slate-200 bg-white p-4 scroll-mt-4">
      <h3 className="text-sm font-semibold text-slate-800 mb-0.5">{title}</h3>
      <p className="text-xs text-slate-500 mb-3">{desc}</p>
      {children}
    </div>
  );
}

function Confirm({ message, onConfirm, onCancel }) {
  return (
    <div className="border border-red-200 bg-red-50 p-3 mt-2 text-sm">
      <p className="text-red-800 mb-2">{message}</p>
      <div className="flex gap-2">
        <button onClick={onConfirm} className="px-3 py-1 bg-red-700 text-white text-xs hover:bg-red-800">Confirm</button>
        <button onClick={onCancel} className="px-3 py-1 bg-white border border-slate-300 text-xs hover:bg-slate-50">Cancel</button>
      </div>
    </div>
  );
}

function ActionResult({ onClick, label, loading, variant = "default" }) {
  const base = "w-full py-2 text-sm font-medium transition-colors disabled:opacity-50";
  const styles = {
    default: "bg-[#0F2847] text-white hover:bg-slate-800",
    danger: "bg-red-700 text-white hover:bg-red-800",
    outline: "border border-slate-300 text-slate-700 hover:bg-slate-50",
  };
  return (
    <button onClick={onClick} disabled={loading} className={`${base} ${styles[variant]}`}>
      {loading ? "Working…" : label}
    </button>
  );
}

function fmtDateTime(d) {
  return d ? new Date(d).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";
}

export default function AdminUserDetail() {
  const { uid } = useParams();
  const navigate = useNavigate();
  const { lastEvent } = useAdminRealtime();

  const [user, setUser] = useState(null);
  const [tab, setTab] = useState("Overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actLoading, setActLoading] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null);
  const [reason, setReason] = useState("");
  const [newPlan, setNewPlan] = useState("free");
  const [creditAmount, setCreditAmount] = useState(0);
  const [creditReason, setCreditReason] = useState("");
  const [newRole, setNewRole] = useState("user");
  const [deleteEmail, setDeleteEmail] = useState("");

  const [timelineData, setTimelineData] = useState(null);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineError, setTimelineError] = useState("");
  const [liveBanner, setLiveBanner] = useState(null);

  const loadUser = async () => {
    try {
      const r = await api.get(`/admin/users/${uid}`);
      setUser(r.data);
      setNewPlan(r.data.plan_code || "free");
      setNewRole(r.data.role || "user");
    } catch (e) {
      setError(e.response?.data?.detail || "User not found");
    } finally {
      setLoading(false);
    }
  };

  const loadTimeline = async () => {
    setTimelineLoading(true);
    setTimelineError("");
    try {
      const [timelineRes, historyRes] = await Promise.all([
        api.get(`/admin/aos/users/${uid}/timeline`),
        api.get(`/admin/aos/users/${uid}/history`),
      ]);
      setTimelineData({ ...timelineRes.data, ...historyRes.data });
    } catch (e) {
      setTimelineError(e.response?.data?.detail || "Timeline requires super-admin access");
    } finally {
      setTimelineLoading(false);
    }
  };

  useEffect(() => { loadUser(); }, [uid]);
  useEffect(() => { if (tab === "Timeline" && !timelineData) loadTimeline(); }, [tab, uid]); // eslint-disable-line react-hooks/exhaustive-deps

  // Live refresh banner: surface security events tied to this user's email,
  // or domain events (e.g. user.verified) tied to this user's id.
  useEffect(() => {
    if (!user || !lastEvent) return;
    if (lastEvent.type === "security_event" && lastEvent.actor_email === user.email) {
      setLiveBanner(`New security event just recorded for this account: ${lastEvent.event_type}`);
    } else if (lastEvent.type === "domain_event" && lastEvent.user_id === uid) {
      setLiveBanner(`Live update: ${lastEvent.event_type.replace(/_/g, " ")}`);
      if (tab === "Timeline") loadTimeline();
    }
  }, [lastEvent, user, uid, tab]); // eslint-disable-line react-hooks/exhaustive-deps

  const action = async (endpoint, body = {}) => {
    setActLoading(true);
    try {
      await api.post(`/admin/users/${uid}/${endpoint}`, body);
      toast.success("Action completed successfully");
      setConfirmAction(null);
      setReason("");
      await loadUser();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Action failed");
    } finally {
      setActLoading(false);
    }
  };

  function jumpToAction(id) {
    setTab("Actions");
    setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
  }

  if (loading) return <div className="p-8 flex justify-center"><Spinner size={24} /></div>;
  if (error) return <div className="p-8"><ErrorState message={error} type="server" onRetry={loadUser} /></div>;
  if (!user) return null;

  const s = user.activity_summary || {};
  const relatedItems = [
    { label: "Projects", count: s.projects_count, icon: FolderOpen },
    { label: "Workspaces", count: s.workspaces_count, icon: FileText },
    { label: "Collaborations", count: s.collabs_count, icon: Users2 },
    { label: "Manuscripts", count: s.manuscripts_count, icon: FileText },
    { label: "Publications", count: s.publications_count, icon: BookOpen },
  ];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-start gap-4 mb-4">
        <Link to="/admin/users" className="mt-1 text-slate-400 hover:text-slate-700"><ArrowLeft size={18} /></Link>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="font-serif text-3xl text-slate-900">{user.full_name || user.email}</h1>
            <PlanBadge plan={user.plan_code} />
            <StatusBadge status={user.status} />
          </div>
          <p className="text-sm text-slate-500 mt-1">{user.email}</p>
        </div>
      </div>

      {liveBanner && (
        <div className="mb-4">
          <Banner variant="info" onDismiss={() => setLiveBanner(null)}>
            <span className="inline-flex items-center gap-1.5"><RadioTower size={12} /> {liveBanner}</span>
          </Banner>
        </div>
      )}

      {/* Smart actions — the 9 real endpoints below, promoted out of the buried tab */}
      <SmartActionsBar
        actions={[
          {
            label: "Suspend",
            variant: "outline",
            disabled: user.status === "suspended",
            onClick: () => {
              const r = window.prompt("Reason for suspension (optional):", "");
              if (r !== null) action("suspend", { reason: r });
            },
          },
          {
            label: "Unsuspend",
            variant: "ghost",
            disabled: user.status !== "suspended",
            onClick: () => action("unsuspend"),
          },
          {
            label: "Ban",
            variant: "danger",
            disabled: user.status === "banned",
            onClick: () => {
              const r = window.prompt("Reason for ban:", "");
              if (r !== null) action("ban", { reason: r });
            },
          },
          {
            label: "Unban",
            variant: "ghost",
            disabled: user.status !== "banned",
            onClick: () => action("unban"),
          },
          {
            label: "Force Sign Out",
            variant: "ghost",
            onClick: () => {
              if (window.confirm("Force sign out all sessions for this user?")) action("force-logout");
            },
          },
          { label: "Grant Credits", variant: "ghost", onClick: () => jumpToAction("action-credits") },
          { label: "Set Plan", variant: "ghost", onClick: () => jumpToAction("action-plan") },
          { label: "Set Role", variant: "ghost", onClick: () => jumpToAction("action-role") },
          { label: "View Timeline", variant: "ghost", onClick: () => setTab("Timeline") },
          { label: "Delete", variant: "danger", onClick: () => jumpToAction("action-delete") },
        ]}
      />

      {/* Tabs */}
      <div className="mb-6">
        <NavTabs
          tabs={TABS.map((t) => ({ id: t, label: t }))}
          active={tab}
          onChange={setTab}
          variant="underline"
        />
      </div>

      {/* Overview */}
      {tab === "Overview" && (
        <div className="space-y-6">
          <RelatedEntityPanel title="Related" items={relatedItems} cols={5} />
          <div className="bg-white border border-slate-200 p-5">
            <KV label="Email">{user.email}</KV>
            <KV label="Full Name">{user.full_name}</KV>
            <KV label="Role">{user.role}</KV>
            <KV label="Plan"><PlanBadge plan={user.plan_code} /></KV>
            <KV label="Status"><StatusBadge status={user.status} /></KV>
            <KV label="Joined">{fmtDateTime(user.created_at)}</KV>
            <KV label="Email Verified">{user.email_verified ? "Yes" : "No"}</KV>
            <KV label="Onboarded">{user.onboarded ? "Yes" : "No"}</KV>
            <KV label="Monthly Credits">{user.credits_balance ?? 0}</KV>
            <KV label="Pack Credits">{user.credits_pack_balance ?? 0}</KV>
            <KV label="Institution">{user.institution}</KV>
            <KV label="Department">{user.department}</KV>
            <KV label="Country">{user.country}</KV>
            {user.orcid?.orcid_id && <KV label="ORCID">{user.orcid.orcid_id}</KV>}
          </div>
        </div>
      )}

      {/* Timeline — real login/device/activity history from admin_aos.py,
          previously built but never surfaced in this page. */}
      {tab === "Timeline" && (
        <div className="space-y-6">
          {timelineLoading && <div className="p-8 flex justify-center"><Spinner size={24} /></div>}
          {!timelineLoading && timelineError && (
            <ErrorState message={timelineError} type="auth" onRetry={loadTimeline} />
          )}
          {!timelineLoading && !timelineError && timelineData && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-50 border border-slate-200 px-4 py-3 text-center">
                  <div className="font-serif text-2xl text-slate-900">{timelineData.total_logins ?? 0}</div>
                  <div className="text-xs text-slate-500 mt-0.5">Total Logins</div>
                </div>
                <div className="bg-slate-50 border border-slate-200 px-4 py-3 text-center">
                  <div className="font-serif text-2xl text-slate-900">{timelineData.unique_devices ?? 0}</div>
                  <div className="text-xs text-slate-500 mt-0.5">Unique Devices</div>
                </div>
                <div className="bg-slate-50 border border-slate-200 px-4 py-3 text-center">
                  <div className="font-serif text-2xl text-slate-900">{timelineData.total ?? 0}</div>
                  <div className="text-xs text-slate-500 mt-0.5">Total Events</div>
                </div>
              </div>

              {timelineData.device_history?.length > 0 && (
                <div className="bg-white border border-slate-200 p-4">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Devices</h3>
                  <div className="space-y-2">
                    {timelineData.device_history.map((d, i) => (
                      <div key={i} className="flex items-center justify-between text-sm border-b border-slate-100 pb-2 last:border-0">
                        <div>
                          <div className="text-slate-800">{d.user_agent}</div>
                          <div className="text-xs text-slate-400">{d.ip}</div>
                        </div>
                        <div className="text-xs text-slate-500 text-right">
                          {d.logins} logins · last {fmtDateTime(d.last_seen)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-white border border-slate-200 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Activity</h3>
                {(!timelineData.events || timelineData.events.length === 0) ? (
                  <EmptyState icon={<User size={24} />} title="No activity found" size="sm" />
                ) : (
                  <Timeline>
                    {timelineData.events.map((ev, i) => (
                      <TimelineItem
                        key={ev.id || i}
                        label={ev.action}
                        description={ev.target_type ? `${ev.target_type} · ${ev.ip || "—"}` : ev.ip}
                        time={fmtDateTime(ev.created_at)}
                        last={i === timelineData.events.length - 1}
                      />
                    ))}
                  </Timeline>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* Actions */}
      {tab === "Actions" && (
        <div className="grid grid-cols-2 gap-4">
          <ActionCard title="Suspend Account" desc="Prevents the user from signing in. Existing session stays until force logout.">
            {confirmAction === "suspend" ? (
              <>
                <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason for suspension…" className="w-full px-3 py-2 text-sm border border-slate-300 mb-2 focus:outline-none focus:ring-1 focus:ring-[#0F2847]" />
                <Confirm message="Suspend this account?" onConfirm={() => action("suspend", { reason })} onCancel={() => setConfirmAction(null)} />
              </>
            ) : (
              <ActionResult onClick={() => setConfirmAction("suspend")} label="Suspend Account" loading={actLoading} variant="outline" />
            )}
          </ActionCard>

          <ActionCard title="Unsuspend Account" desc="Restores the user's ability to sign in.">
            <ActionResult onClick={() => action("unsuspend")} label="Unsuspend Account" loading={actLoading} variant="outline" />
          </ActionCard>

          <ActionCard title="Ban User" desc="Permanently bans the user. More severe than suspension.">
            {confirmAction === "ban" ? (
              <>
                <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason for ban…" className="w-full px-3 py-2 text-sm border border-slate-300 mb-2 focus:outline-none focus:ring-1 focus:ring-[#0F2847]" />
                <Confirm message="Permanently ban this user?" onConfirm={() => action("ban", { reason })} onCancel={() => setConfirmAction(null)} />
              </>
            ) : (
              <ActionResult onClick={() => setConfirmAction("ban")} label="Ban User" loading={actLoading} variant="danger" />
            )}
          </ActionCard>

          <ActionCard title="Unban User" desc="Lifts the ban, restoring access.">
            <ActionResult onClick={() => action("unban")} label="Unban User" loading={actLoading} variant="outline" />
          </ActionCard>

          <ActionCard title="Force Sign Out" desc="Invalidates all active sessions for this user immediately.">
            {confirmAction === "force-logout" ? (
              <Confirm message="Force sign out all sessions?" onConfirm={() => action("force-logout")} onCancel={() => setConfirmAction(null)} />
            ) : (
              <ActionResult onClick={() => setConfirmAction("force-logout")} label="Force Sign Out" loading={actLoading} variant="outline" />
            )}
          </ActionCard>

          <ActionCard id="action-plan" title="Change Plan" desc="Change the user's subscription plan immediately.">
            <select value={newPlan} onChange={(e) => setNewPlan(e.target.value)} className="w-full px-3 py-2 text-sm border border-slate-300 mb-2 focus:outline-none focus:ring-1 focus:ring-[#0F2847]">
              <option value="free">Free</option>
              <option value="researcher">Researcher</option>
              <option value="pro_researcher">Pro Researcher</option>
              <option value="institution">Institution</option>
            </select>
            <ActionResult onClick={() => action("set-plan", { plan_code: newPlan })} label={`Set to ${newPlan}`} loading={actLoading} />
          </ActionCard>

          <ActionCard id="action-credits" title="Adjust Credits" desc="Grant or remove credits. Positive adds, negative deducts.">
            <input type="number" value={creditAmount} onChange={(e) => setCreditAmount(Number(e.target.value))} className="w-full px-3 py-2 text-sm border border-slate-300 mb-2 focus:outline-none" placeholder="Amount (e.g. 500 or -100)" />
            <input value={creditReason} onChange={(e) => setCreditReason(e.target.value)} placeholder="Reason…" className="w-full px-3 py-2 text-sm border border-slate-300 mb-2 focus:outline-none" />
            <ActionResult onClick={() => action("adjust-credits", { amount: creditAmount, reason: creditReason })} label="Apply Credit Adjustment" loading={actLoading} />
          </ActionCard>

          <ActionCard id="action-role" title="Change Role" desc="Assign a new platform role to this user.">
            <select value={newRole} onChange={(e) => setNewRole(e.target.value)} className="w-full px-3 py-2 text-sm border border-slate-300 mb-2 focus:outline-none focus:ring-1 focus:ring-[#0F2847]">
              <option value="user">User</option>
              <option value="moderator">Moderator</option>
              <option value="verified_researcher">Verified Researcher</option>
              <option value="verified_professor">Verified Professor</option>
              <option value="institution_admin">Institution Admin</option>
              <option value="admin">Admin</option>
            </select>
            <p className="text-xs text-slate-400 mb-2">super_admin cannot be granted via the interface — DB only.</p>
            <ActionResult onClick={() => action("set-role", { role: newRole })} label={`Set role to ${newRole}`} loading={actLoading} />
          </ActionCard>

          <ActionCard id="action-delete" title="Delete Account" desc="Soft-deletes the account and anonymises PII. Irreversible.">
            {confirmAction === "delete" ? (
              <>
                <p className="text-xs text-red-700 mb-2">Type the user's email address to confirm deletion:</p>
                <input value={deleteEmail} onChange={(e) => setDeleteEmail(e.target.value)} placeholder={user.email} className="w-full px-3 py-2 text-sm border border-red-300 mb-2 focus:outline-none" />
                {deleteEmail === user.email ? (
                  <button
                    onClick={async () => {
                      setActLoading(true);
                      try {
                        await api.delete(`/admin/users/${uid}`);
                        toast.success("User deleted");
                        navigate("/admin/users");
                      } catch (e) {
                        toast.error(e.response?.data?.detail || "Delete failed");
                      } finally { setActLoading(false); }
                    }}
                    disabled={actLoading}
                    className="w-full py-2 bg-red-700 text-white text-sm hover:bg-red-800 disabled:opacity-50"
                  >
                    {actLoading ? "Deleting…" : "Delete permanently"}
                  </button>
                ) : (
                  <p className="text-xs text-slate-400">Email must match exactly to enable deletion</p>
                )}
                <button onClick={() => { setConfirmAction(null); setDeleteEmail(""); }} className="mt-2 text-xs text-slate-500 hover:underline">Cancel</button>
              </>
            ) : (
              <ActionResult onClick={() => setConfirmAction("delete")} label="Delete Account" loading={actLoading} variant="danger" />
            )}
          </ActionCard>
        </div>
      )}
    </div>
  );
}

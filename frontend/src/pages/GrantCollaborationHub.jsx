import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Plus, Search, Users, Mail, BarChart2, ChevronLeft, ChevronRight,
  X, CheckCircle, XCircle, Loader2, Globe, Calendar, DollarSign,
  Briefcase, ArrowRight, Building2, Eye, EyeOff
} from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { ACCENT, NAVY, WARM } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Badge } from "@/components/ds/Badge";
import { Tag, TagGroup } from "@/components/ds/Tag";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { RadioGroup } from "@/components/ds/Form";
import { Modal } from "@/components/ds/Modal";
import { NavTabs } from "@/components/ds/NavTabs";
import { EmptyState } from "@/components/ds/EmptyState";
import { StatCard, StatGrid } from "@/components/ds/StatCard";
import { ProgressBar } from "@/components/ds/Progress";
import { Spinner } from "@/components/ds/LoadingState";

// ─── helpers ────────────────────────────────────────────────────────────────

const STATUS_BADGE_VARIANT = {
  open:   "success",
  active: "info",
  full:   "warning",
  closed: "neutral",
};

function StatusBadge({ status }) {
  return (
    <Badge variant={STATUS_BADGE_VARIANT[status] || "neutral"}>
      {status ? status.charAt(0).toUpperCase() + status.slice(1) : "Unknown"}
    </Badge>
  );
}

function Chip({ label, color = "slate" }) {
  const map = {
    slate:  undefined,
    indigo: "#4F46E5",
    purple: "#9333EA",
  };
  return <Tag size="sm" color={map[color]}>{label}</Tag>;
}

function CollabCard({ collab, isMyCollab, onExpressInterest, myUserId }) {
  const navigate = useNavigate();
  const isMember = collab.members?.some(m => m.user_id === myUserId || m._id === myUserId);
  const openPositions = (collab.positions || []).filter(p => p.status === "open").length;

  return (
    <Card padding="lg" className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={collab.status} />
          {collab.visibility === "private" && (
            <Badge variant="neutral"><EyeOff size={10} /> Private</Badge>
          )}
        </div>
        {collab.deadline && (
          <span className="flex items-center gap-1 text-xs text-slate-400 shrink-0">
            <Calendar size={12} /> {new Date(collab.deadline).toLocaleDateString()}
          </span>
        )}
      </div>

      <div>
        <h3 className="font-semibold text-slate-900 text-sm leading-snug">{collab.title}</h3>
        {collab.funding_source && (
          <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
            <Briefcase size={11} /> {collab.funding_source}
          </p>
        )}
      </div>

      {collab.research_areas?.length > 0 && (
        <TagGroup gap={4}>
          {collab.research_areas.slice(0, 4).map((a, i) => <Chip key={i} label={a} color="indigo" />)}
          {collab.research_areas.length > 4 && <Chip label={`+${collab.research_areas.length - 4}`} />}
        </TagGroup>
      )}

      {collab.countries_required?.length > 0 && (
        <div className="flex flex-wrap gap-1 items-center">
          <Globe size={11} className="text-slate-400" />
          {collab.countries_required.slice(0, 3).map((c, i) => <Chip key={i} label={c} color="purple" />)}
          {collab.countries_required.length > 3 && <Chip label={`+${collab.countries_required.length - 3}`} />}
        </div>
      )}

      <div className="flex items-center gap-3 text-xs text-slate-500 mt-auto">
        <span className="flex items-center gap-1"><Users size={12} /> {collab.members?.length || 0} members</span>
        {openPositions > 0 && (
          <span className="flex items-center gap-1 text-emerald-600"><Plus size={12} /> {openPositions} open</span>
        )}
      </div>

      <div className="flex items-center gap-2 pt-1 border-t border-slate-100">
        <Button as={Link} to={`/grant-hub/${collab._id}`} size="sm">
          View Workspace <ArrowRight size={11} />
        </Button>
        {isMyCollab ? (
          <Button as={Link} to={`/grant-hub/${collab._id}`} variant="ghost" size="sm">
            Manage
          </Button>
        ) : !isMember && collab.status === "open" ? (
          <Button onClick={() => onExpressInterest(collab._id)} variant="ghost" size="sm">
            Express Interest
          </Button>
        ) : null}
      </div>
    </Card>
  );
}

function CreateModal({ open, onClose, onCreate }) {
  const [form, setForm] = useState({
    title: "", description: "", grant_id: "", research_areas: "",
    countries_required: "", funding_source: "", deadline: "",
    budget_total: "", visibility: "public"
  });
  const [creating, setCreating] = useState(false);
  const [err, setErr] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e?.preventDefault?.();
    if (!form.title.trim()) { setErr("Title is required."); return; }
    setErr("");
    setCreating(true);
    try {
      const payload = {
        title: form.title.trim(),
        description: form.description.trim(),
        research_areas: form.research_areas ? form.research_areas.split(",").map(s => s.trim()).filter(Boolean) : [],
        countries_required: form.countries_required ? form.countries_required.split(",").map(s => s.trim()).filter(Boolean) : [],
        funding_source: form.funding_source.trim(),
        deadline: form.deadline || undefined,
        budget_total: form.budget_total ? Number(form.budget_total) : 0,
        visibility: form.visibility,
      };
      if (form.grant_id.trim()) payload.grant_id = form.grant_id.trim();
      const { data } = await api.post("/grant-hub/", payload);
      onCreate(data._id || data.id);
    } catch (e) {
      setErr(e?.response?.data?.error || e.message || "Failed to create collaboration.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New Grant Collaboration"
      size="md"
      footer={
        <>
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" form="create-collab-form" loading={creating}>
            {creating ? "Creating..." : "Create Collaboration"}
          </Button>
        </>
      }
    >
      <form id="create-collab-form" onSubmit={handleSubmit} className="flex flex-col gap-4">
        {err && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">{err}</div>}

        <Input
          label={<>Title <span className="text-red-500">*</span></>}
          name="title" value={form.title} onChange={handleChange}
          placeholder="e.g. EU Horizon Climate Consortium"
        />

        <Textarea
          label="Description"
          name="description" value={form.description} onChange={handleChange} rows={3}
          placeholder="Describe the collaboration goals, scope, and requirements..."
        />

        <div>
          <Input
            label="Link to Existing Grant"
            name="grant_id" value={form.grant_id} onChange={handleChange}
            placeholder="Grant ID (optional)"
          />
          <p className="text-xs text-slate-400 mt-1">Link to an existing grant from your Grants page</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Input
            label="Funding Source"
            name="funding_source" value={form.funding_source} onChange={handleChange}
            placeholder="e.g. EU Horizon, NSF"
          />
          <Input
            label="Deadline"
            type="date" name="deadline" value={form.deadline} onChange={handleChange}
          />
        </div>

        <Input
          label="Research Areas"
          name="research_areas" value={form.research_areas} onChange={handleChange}
          placeholder="AI, Healthcare, Climate Science (comma-separated)"
        />

        <Input
          label="Countries Required"
          name="countries_required" value={form.countries_required} onChange={handleChange}
          placeholder="Germany, France, Spain (comma-separated)"
        />

        <Input
          label="Total Budget (€)"
          type="number" name="budget_total" value={form.budget_total} onChange={handleChange}
          placeholder="0" min="0"
        />

        <div>
          <label className="block text-xs text-slate-500 uppercase tracking-wide mb-2">Visibility</label>
          <RadioGroup
            name="visibility"
            value={form.visibility}
            onChange={(v) => setForm(prev => ({ ...prev, visibility: v }))}
            style={{ flexDirection: "row", gap: 24 }}
            options={[
              { value: "public", label: <span className="flex items-center gap-1"><Eye size={13} /> public</span> },
              { value: "private", label: <span className="flex items-center gap-1"><EyeOff size={13} /> private</span> },
            ]}
          />
        </div>
      </form>
    </Modal>
  );
}

// ─── main component ──────────────────────────────────────────────────────────

export default function GrantCollaborationHub() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState("marketplace");
  const [collaborations, setCollaborations] = useState([]);
  const [myCollabs, setMyCollabs] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ status: "", research_area: "", country: "", funding_source: "" });
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [myInvitations, setMyInvitations] = useState([]);
  const [respondingId, setRespondingId] = useState(null);

  const LIMIT = 20;

  const initialFiltersRef = useRef(filters);

  const fetchCollaborations = useCallback(async (currentPage = 1, currentFilters = {}) => {
    try {
      const params = { page: currentPage, limit: LIMIT };
      if (currentFilters.status) params.status = currentFilters.status;
      if (currentFilters.research_area) params.research_area = currentFilters.research_area;
      if (currentFilters.country) params.country = currentFilters.country;
      if (currentFilters.funding_source) params.funding_source = currentFilters.funding_source;
      const { data } = await api.get("/grant-hub", { params });
      setCollaborations(Array.isArray(data) ? data : (data.items || data.collaborations || []));
      setTotal(data.total || (Array.isArray(data) ? data.length : 0));
    } catch (e) {
      setError(e?.response?.data?.error || e.message);
    }
  }, []);

  const fetchMyCollabs = useCallback(async () => {
    try {
      const { data } = await api.get("/grant-hub/my");
      setMyCollabs(Array.isArray(data) ? data : (data.items || data.collaborations || []));
    } catch (_) {}
  }, []);

  const fetchAnalytics = useCallback(async () => {
    try {
      const { data } = await api.get("/grant-hub/analytics/me");
      setAnalytics(data);
    } catch (_) {}
  }, []);

  const fetchMyInvitations = useCallback(async () => {
    try {
      const { data } = await api.get("/grant-hub/invitations/my");
      setMyInvitations(Array.isArray(data) ? data : (data.items || data.invitations || []));
    } catch (_) {}
  }, []);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([
        fetchCollaborations(1, initialFiltersRef.current),
        fetchMyCollabs(),
        fetchAnalytics(),
        fetchMyInvitations(),
      ]);
      setLoading(false);
    };
    init();
  }, [fetchCollaborations, fetchMyCollabs, fetchAnalytics, fetchMyInvitations]);

  const handleSearch = () => {
    setPage(1);
    fetchCollaborations(1, filters);
  };

  const handlePageChange = (newPage) => {
    setPage(newPage);
    fetchCollaborations(newPage, filters);
  };

  const handleExpressInterest = async (collabId) => {
    try {
      await api.post(`/grant-hub/${collabId}/express-interest`);
      await fetchMyInvitations();
      toast.success("Interest expressed! The collaboration lead will review your request.");
    } catch (e) {
      toast.error(e?.response?.data?.error || "Failed to express interest.");
    }
  };

  const handleInvitationRespond = async (invId, response) => {
    setRespondingId(invId);
    try {
      await api.post(`/grant-hub/invitations/${invId}/respond`, { response });
      await fetchMyInvitations();
      await fetchMyCollabs();
    } catch (e) {
      toast.error(e?.response?.data?.error || "Failed to respond to invitation.");
    } finally {
      setRespondingId(null);
    }
  };

  const handleCreated = (newId) => {
    setShowCreateModal(false);
    navigate(`/grant-hub/${newId}`);
  };

  // My collabs split
  const myLead = myCollabs.filter(c => c.lead_user_id === user?._id || c.lead_user_id === user?.id);
  const myParticipating = myCollabs.filter(c => c.lead_user_id !== user?._id && c.lead_user_id !== user?.id);
  const totalPages = Math.max(1, Math.ceil(total / LIMIT));

  const TABS = [
    { key: "marketplace", label: "Marketplace", icon: Search },
    { key: "my-hub", label: "My Hub", icon: Briefcase },
    { key: "invitations", label: "Invitations", icon: Mail, badge: myInvitations.length },
    { key: "analytics", label: "Analytics", icon: BarChart2 },
  ];

  // ─── analytics helpers ───
  const statusCounts = analytics?.collaborations_by_status || {};
  const statusKeys = Object.keys(statusCounts);
  const maxStatusCount = Math.max(1, ...Object.values(statusCounts));

  return (
    <ResearchLayout
      title="Grant Collaboration Hub"
      subtitle="Discover funding teams · Build consortia · Win grants together"
      actions={
        <Button onClick={() => setShowCreateModal(true)} className="shrink-0">
          <Plus size={15} /> New Collaboration
        </Button>
      }
    >
      {/* ── Stats strip ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-6 max-w-md mb-8">
        {[
          { label: "Active Collaborations", value: total },
          { label: "My Collaborations",     value: myCollabs.length },
          { label: "Pending Invitations",   value: myInvitations.length },
        ].map(({ label, value }) => (
          <div key={label} className="text-center">
            <div className="font-serif text-3xl text-slate-900">{value}</div>
            <div className="overline mt-1 text-xs">{label}</div>
          </div>
        ))}
      </div>

      {/* Tab bar */}
      <div className="bg-white border-b border-slate-200 -mx-6 px-6 mb-6">
        <NavTabs
          tabs={TABS.map(({ key, label, icon, badge }) => ({ id: key, label, icon, count: badge > 0 ? badge : null }))}
          active={activeTab}
          onChange={setActiveTab}
        />
      </div>

      {/* Body */}
      <div className="max-w-6xl mx-auto px-6 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Spinner size={24} />
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">{error}</div>
        ) : (
          <>
            {/* ── MARKETPLACE ── */}
            {activeTab === "marketplace" && (
              <div className="space-y-5">
                {/* Filter row */}
                <Card padding="md" className="flex flex-wrap items-end gap-3">
                  <Input
                    label="Research Area"
                    value={filters.research_area}
                    onChange={e => setFilters(f => ({ ...f, research_area: e.target.value }))}
                    placeholder="e.g. AI, Climate"
                    wrapperClassName="flex-1 min-w-[140px]"
                  />
                  <Input
                    label="Country"
                    value={filters.country}
                    onChange={e => setFilters(f => ({ ...f, country: e.target.value }))}
                    placeholder="e.g. Germany"
                    wrapperClassName="flex-1 min-w-[120px]"
                  />
                  <Input
                    label="Funding Source"
                    value={filters.funding_source}
                    onChange={e => setFilters(f => ({ ...f, funding_source: e.target.value }))}
                    placeholder="e.g. EU Horizon"
                    wrapperClassName="flex-1 min-w-[120px]"
                  />
                  <FormSelect
                    label="Status"
                    value={filters.status}
                    onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}
                    wrapperClassName="min-w-[120px]"
                  >
                    <option value="">All</option>
                    <option value="open">Open</option>
                    <option value="active">Active</option>
                    <option value="full">Full</option>
                    <option value="closed">Closed</option>
                  </FormSelect>
                  <Button onClick={handleSearch}>
                    <Search size={14} /> Search
                  </Button>
                </Card>

                {/* Cards grid */}
                {collaborations.length === 0 ? (
                  <EmptyState
                    icon={<Globe />}
                    title="No open collaborations yet"
                    description="Be the first to create one and start building your consortium."
                    action={<Button onClick={() => setShowCreateModal(true)}>Create Collaboration</Button>}
                  />
                ) : (
                  <>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {collaborations.map(c => (
                        <CollabCard
                          key={c._id}
                          collab={c}
                          isMyCollab={false}
                          onExpressInterest={handleExpressInterest}
                          myUserId={user?._id || user?.id}
                        />
                      ))}
                    </div>

                    {/* Pagination */}
                    <div className="flex items-center justify-between pt-2">
                      <p className="text-xs text-slate-500">
                        Page {page} of {totalPages} ({total} total)
                      </p>
                      <div className="flex items-center gap-2">
                        <Button
                          onClick={() => handlePageChange(page - 1)}
                          disabled={page === 1}
                          variant="ghost"
                          size="sm"
                        >
                          <ChevronLeft size={14} /> Prev
                        </Button>
                        <Button
                          onClick={() => handlePageChange(page + 1)}
                          disabled={page >= totalPages}
                          variant="ghost"
                          size="sm"
                        >
                          Next <ChevronRight size={14} />
                        </Button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* ── MY HUB ── */}
            {activeTab === "my-hub" && (
              <div className="space-y-8">
                {/* Leading */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#0F2847]" /> Leading ({myLead.length})
                    </h2>
                  </div>
                  {myLead.length === 0 ? (
                    <EmptyState
                      icon={<Briefcase />}
                      title="You're not leading any collaboration yet"
                      size="sm"
                      action={<Button onClick={() => setShowCreateModal(true)} size="sm">+ New Collaboration</Button>}
                    />
                  ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {myLead.map(c => (
                        <CollabCard key={c._id} collab={c} isMyCollab={true} onExpressInterest={() => {}} myUserId={user?._id || user?.id} />
                      ))}
                    </div>
                  )}
                </div>

                {/* Participating */}
                <div>
                  <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2 mb-3">
                    <span className="w-2 h-2 rounded-full bg-blue-500" /> Participating ({myParticipating.length})
                  </h2>
                  {myParticipating.length === 0 ? (
                    <EmptyState
                      icon={<Users />}
                      title="You haven't joined any collaboration yet"
                      description="Browse the Marketplace to find open teams"
                      size="sm"
                    />
                  ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {myParticipating.map(c => (
                        <CollabCard key={c._id} collab={c} isMyCollab={true} onExpressInterest={() => {}} myUserId={user?._id || user?.id} />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── INVITATIONS ── */}
            {activeTab === "invitations" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-slate-900">Pending Invitations ({myInvitations.length})</h2>
                  <Button onClick={fetchMyInvitations} variant="link" size="sm">Refresh</Button>
                </div>

                {myInvitations.length === 0 ? (
                  <EmptyState
                    icon={<Mail />}
                    title="No pending invitations"
                    description="When researchers invite you to their grant teams, they'll appear here."
                  />
                ) : (
                  <div className="bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
                    {myInvitations.map(inv => (
                      <div key={inv._id} className="p-4 flex items-start gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="font-medium text-slate-900 text-sm">{inv.collaboration_title || inv.collab?.title || "Untitled Collaboration"}</p>
                            {inv.role && <Badge variant="info">{inv.role}</Badge>}
                          </div>
                          {inv.invited_by_name && (
                            <p className="text-xs text-slate-500 mt-0.5">Invited by {inv.invited_by_name}</p>
                          )}
                          {inv.created_at && (
                            <p className="text-xs text-slate-400 mt-0.5">{new Date(inv.created_at).toLocaleDateString()}</p>
                          )}
                          {inv.message && (
                            <p className="text-xs text-slate-600 mt-1.5 italic line-clamp-2">"{inv.message}"</p>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <Button
                            onClick={() => handleInvitationRespond(inv._id, "accepted")}
                            loading={respondingId === inv._id}
                            size="sm"
                            className="!bg-emerald-600 hover:!bg-emerald-700"
                          >
                            {respondingId !== inv._id && <CheckCircle size={12} />} Accept
                          </Button>
                          <Button
                            onClick={() => handleInvitationRespond(inv._id, "rejected")}
                            disabled={respondingId === inv._id}
                            variant="ghost"
                            size="sm"
                          >
                            <XCircle size={12} /> Reject
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ── ANALYTICS ── */}
            {activeTab === "analytics" && (
              <div className="space-y-5">
                <h2 className="text-sm font-semibold text-slate-900">My Grant Hub Analytics</h2>

                {!analytics ? (
                  <EmptyState
                    icon={<BarChart2 />}
                    title="No analytics data yet. Start collaborating to see your stats."
                    size="sm"
                  />
                ) : (
                  <>
                    {/* Summary cards */}
                    <StatGrid cols={4}>
                      <StatCard label="Total Collaborations" value={analytics.total_collaborations ?? myCollabs.length} />
                      <StatCard label="Invitations Sent" value={analytics.invitations_sent ?? 0} />
                      <StatCard label="Invitations Accepted" value={analytics.invitations_accepted ?? 0} />
                      <StatCard label="Positions Filled" value={analytics.positions_filled ?? 0} />
                    </StatGrid>

                    {/* Acceptance rate */}
                    {analytics.invitations_sent > 0 && (
                      <Card padding="lg">
                        <p className="text-sm font-semibold text-slate-900 mb-3">Invitation Acceptance Rate</p>
                        <ProgressBar
                          value={analytics.invitations_accepted || 0}
                          max={analytics.invitations_sent}
                          valueLabel={`${Math.round(((analytics.invitations_accepted || 0) / analytics.invitations_sent) * 100)}%`}
                          showValue
                        />
                      </Card>
                    )}

                    {/* Status distribution */}
                    {statusKeys.length > 0 && (
                      <Card padding="lg">
                        <p className="text-sm font-semibold text-slate-900 mb-4">Collaborations by Status</p>
                        <div className="space-y-3">
                          {statusKeys.map(s => (
                            <div key={s} className="flex items-center gap-3">
                              <span className="w-16 text-xs text-slate-500 capitalize">{s}</span>
                              <div className="flex-1">
                                <ProgressBar value={statusCounts[s]} max={maxStatusCount} size="sm" showValue={false} />
                              </div>
                              <span className="w-6 text-xs font-medium text-slate-700 text-right">{statusCounts[s]}</span>
                            </div>
                          ))}
                        </div>
                      </Card>
                    )}
                  </>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Create Modal */}
      <CreateModal open={showCreateModal} onClose={() => setShowCreateModal(false)} onCreate={handleCreated} />
    </ResearchLayout>
  );
}

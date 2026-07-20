import React, { useState, useEffect, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Plus, Search, Users, Mail, BarChart2, ChevronLeft, ChevronRight,
  X, CheckCircle, XCircle, Loader2, Globe, Calendar, DollarSign,
  Briefcase, ArrowRight, Building2, Tag, Eye, EyeOff
} from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { ACCENT, NAVY, WARM } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";

// ─── helpers ────────────────────────────────────────────────────────────────

const STATUS_COLORS = {
  open:   "bg-emerald-100 text-emerald-700 border border-emerald-200",
  active: "bg-blue-100 text-blue-700 border border-blue-200",
  full:   "bg-amber-100 text-amber-700 border border-amber-200",
  closed: "bg-slate-100 text-slate-600 border border-slate-200",
};

function StatusBadge({ status }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[status] || STATUS_COLORS.closed}`}>
      {status ? status.charAt(0).toUpperCase() + status.slice(1) : "Unknown"}
    </span>
  );
}

function Chip({ label, color = "slate" }) {
  const map = {
    slate:  "bg-slate-100 text-slate-700",
    indigo: "bg-indigo-100 text-indigo-700",
    purple: "bg-purple-100 text-purple-700",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${map[color] || map.slate}`}>
      {label}
    </span>
  );
}

function CollabCard({ collab, isMyCollab, onExpressInterest, myUserId }) {
  const navigate = useNavigate();
  const isMember = collab.members?.some(m => m.user_id === myUserId || m._id === myUserId);
  const openPositions = (collab.positions || []).filter(p => p.status === "open").length;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 flex flex-col gap-3 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={collab.status} />
          {collab.visibility === "private" && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-500 border border-slate-200">
              <EyeOff size={10} /> Private
            </span>
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
        <div className="flex flex-wrap gap-1">
          {collab.research_areas.slice(0, 4).map((a, i) => <Chip key={i} label={a} color="indigo" />)}
          {collab.research_areas.length > 4 && <Chip label={`+${collab.research_areas.length - 4}`} />}
        </div>
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
        <Link
          to={`/grant-hub/${collab._id}`}
          className="px-3 py-1.5 bg-[#0F2847] text-white text-xs font-medium hover:bg-[#0a1f38] transition-colors rounded flex items-center gap-1"
        >
          View Workspace <ArrowRight size={11} />
        </Link>
        {isMyCollab ? (
          <Link
            to={`/grant-hub/${collab._id}`}
            className="px-3 py-1.5 border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors rounded"
          >
            Manage
          </Link>
        ) : !isMember && collab.status === "open" ? (
          <button
            onClick={() => onExpressInterest(collab._id)}
            className="px-3 py-1.5 border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors rounded"
          >
            Express Interest
          </button>
        ) : null}
      </div>
    </div>
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

  if (!open) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <h2 className="font-serif text-lg font-semibold text-slate-900">New Grant Collaboration</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 transition-colors">
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-4">
          {err && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">{err}</div>}

          <div>
            <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">Title <span className="text-red-500">*</span></label>
            <input name="title" value={form.title} onChange={handleChange} placeholder="e.g. EU Horizon Climate Consortium" className="w-full border border-slate-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20" />
          </div>

          <div>
            <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">Description</label>
            <textarea name="description" value={form.description} onChange={handleChange} rows={3} placeholder="Describe the collaboration goals, scope, and requirements..." className="w-full border border-slate-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 resize-none" />
          </div>

          <div>
            <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">Link to Existing Grant</label>
            <input name="grant_id" value={form.grant_id} onChange={handleChange} placeholder="Grant ID (optional)" className="w-full border border-slate-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20" />
            <p className="text-xs text-slate-400 mt-1">Link to an existing grant from your Grants page</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">Funding Source</label>
              <input name="funding_source" value={form.funding_source} onChange={handleChange} placeholder="e.g. EU Horizon, NSF" className="w-full border border-slate-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">Deadline</label>
              <input type="date" name="deadline" value={form.deadline} onChange={handleChange} className="w-full border border-slate-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">Research Areas</label>
            <input name="research_areas" value={form.research_areas} onChange={handleChange} placeholder="AI, Healthcare, Climate Science (comma-separated)" className="w-full border border-slate-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20" />
          </div>

          <div>
            <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">Countries Required</label>
            <input name="countries_required" value={form.countries_required} onChange={handleChange} placeholder="Germany, France, Spain (comma-separated)" className="w-full border border-slate-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20" />
          </div>

          <div>
            <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">Total Budget (€)</label>
            <input type="number" name="budget_total" value={form.budget_total} onChange={handleChange} placeholder="0" min="0" className="w-full border border-slate-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20" />
          </div>

          <div>
            <label className="block text-xs text-slate-500 uppercase tracking-wide mb-2">Visibility</label>
            <div className="flex gap-4">
              {["public", "private"].map(v => (
                <label key={v} className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="visibility" value={v} checked={form.visibility === v} onChange={handleChange} className="accent-[#0F2847]" />
                  <span className="text-sm text-slate-700 capitalize flex items-center gap-1">
                    {v === "private" ? <EyeOff size={13} /> : <Eye size={13} />} {v}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-100">
            <button type="button" onClick={onClose} className="px-4 py-2 border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors rounded">
              Cancel
            </button>
            <button type="submit" disabled={creating} className="px-4 py-2 bg-[#0F2847] text-white text-sm font-medium hover:bg-[#0a1f38] transition-colors rounded flex items-center gap-2 disabled:opacity-60">
              {creating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              {creating ? "Creating..." : "Create Collaboration"}
            </button>
          </div>
        </form>
      </div>
    </div>
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

  const fetchCollaborations = useCallback(async (currentPage = 1, currentFilters = filters) => {
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
        fetchCollaborations(1, filters),
        fetchMyCollabs(),
        fetchAnalytics(),
        fetchMyInvitations(),
      ]);
      setLoading(false);
    };
    init();
  }, []);

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
      alert("Interest expressed! The collaboration lead will review your request.");
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to express interest.");
    }
  };

  const handleInvitationRespond = async (invId, response) => {
    setRespondingId(invId);
    try {
      await api.post(`/grant-hub/invitations/${invId}/respond`, { response });
      await fetchMyInvitations();
      await fetchMyCollabs();
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to respond to invitation.");
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

  const statsMeta = (
    <div className="flex items-center gap-6">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 bg-slate-100 rounded flex items-center justify-center">
          <Globe size={14} className="text-slate-500" />
        </div>
        <div>
          <p className="text-lg font-semibold text-slate-900 leading-none">{total}</p>
          <p className="text-xs text-slate-500 mt-0.5">Active collaborations</p>
        </div>
      </div>
      <div className="w-px h-8 bg-slate-200" />
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 bg-slate-100 rounded flex items-center justify-center">
          <Briefcase size={14} className="text-slate-500" />
        </div>
        <div>
          <p className="text-lg font-semibold text-slate-900 leading-none">{myCollabs.length}</p>
          <p className="text-xs text-slate-500 mt-0.5">My collaborations</p>
        </div>
      </div>
      <div className="w-px h-8 bg-slate-200" />
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 bg-slate-100 rounded flex items-center justify-center">
          <Mail size={14} className="text-slate-500" />
        </div>
        <div>
          <p className="text-lg font-semibold text-slate-900 leading-none">{myInvitations.length}</p>
          <p className="text-xs text-slate-500 mt-0.5">Pending invitations</p>
        </div>
      </div>
    </div>
  );

  return (
    <ResearchLayout
      title="Grant Collaboration Hub"
      subtitle="Discover funding teams · Build consortia · Win grants together"
      actions={
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-[#0F2847] text-white text-sm font-medium hover:bg-[#0a1f38] transition-colors rounded shrink-0"
        >
          <Plus size={15} /> New Collaboration
        </button>
      }
      meta={statsMeta}
    >
      {/* Tab bar */}
      <div className="bg-white border-b border-slate-200 -mx-6 px-6 mb-6">
          <div className="flex items-center gap-1 -mb-px">
            {TABS.map(({ key, label, icon: Icon, badge }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`flex items-center gap-1.5 px-4 py-3 text-sm transition-colors border-b-2 ${
                  activeTab === key
                    ? "border-[#0F2847] text-[#0F2847] font-medium"
                    : "border-transparent text-slate-500 hover:text-slate-900"
                }`}
              >
                <Icon size={14} />
                {label}
                {badge > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 bg-[#8A1538] text-white text-xs rounded-full leading-none">{badge}</span>
                )}
              </button>
            ))}
          </div>
        </div>

      {/* Body */}
      <div className="max-w-6xl mx-auto px-6 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={24} className="animate-spin text-slate-400" />
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">{error}</div>
        ) : (
          <>
            {/* ── MARKETPLACE ── */}
            {activeTab === "marketplace" && (
              <div className="space-y-5">
                {/* Filter row */}
                <div className="bg-white border border-slate-200 rounded-lg p-4 flex flex-wrap items-end gap-3">
                  <div className="flex-1 min-w-[140px]">
                    <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">Research Area</label>
                    <input
                      value={filters.research_area}
                      onChange={e => setFilters(f => ({ ...f, research_area: e.target.value }))}
                      placeholder="e.g. AI, Climate"
                      className="w-full border border-slate-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20"
                    />
                  </div>
                  <div className="flex-1 min-w-[120px]">
                    <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">Country</label>
                    <input
                      value={filters.country}
                      onChange={e => setFilters(f => ({ ...f, country: e.target.value }))}
                      placeholder="e.g. Germany"
                      className="w-full border border-slate-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20"
                    />
                  </div>
                  <div className="flex-1 min-w-[120px]">
                    <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">Funding Source</label>
                    <input
                      value={filters.funding_source}
                      onChange={e => setFilters(f => ({ ...f, funding_source: e.target.value }))}
                      placeholder="e.g. EU Horizon"
                      className="w-full border border-slate-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20"
                    />
                  </div>
                  <div className="min-w-[120px]">
                    <label className="block text-xs text-slate-500 uppercase tracking-wide mb-1">Status</label>
                    <select
                      value={filters.status}
                      onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}
                      className="w-full border border-slate-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 bg-white"
                    >
                      <option value="">All</option>
                      <option value="open">Open</option>
                      <option value="active">Active</option>
                      <option value="full">Full</option>
                      <option value="closed">Closed</option>
                    </select>
                  </div>
                  <button
                    onClick={handleSearch}
                    className="flex items-center gap-2 px-4 py-1.5 bg-[#0F2847] text-white text-sm font-medium hover:bg-[#0a1f38] transition-colors rounded"
                  >
                    <Search size={14} /> Search
                  </button>
                </div>

                {/* Cards grid */}
                {collaborations.length === 0 ? (
                  <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
                    <Globe size={32} className="text-slate-300 mx-auto mb-3" />
                    <p className="font-medium text-slate-700">No open collaborations yet</p>
                    <p className="text-sm text-slate-500 mt-1">Be the first to create one and start building your consortium.</p>
                    <button
                      onClick={() => setShowCreateModal(true)}
                      className="mt-4 px-4 py-2 bg-[#0F2847] text-white text-sm font-medium hover:bg-[#0a1f38] transition-colors rounded"
                    >
                      Create Collaboration
                    </button>
                  </div>
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
                        <button
                          onClick={() => handlePageChange(page - 1)}
                          disabled={page === 1}
                          className="flex items-center gap-1 px-3 py-1.5 border border-slate-200 text-sm text-slate-700 hover:bg-slate-50 transition-colors rounded disabled:opacity-40"
                        >
                          <ChevronLeft size={14} /> Prev
                        </button>
                        <button
                          onClick={() => handlePageChange(page + 1)}
                          disabled={page >= totalPages}
                          className="flex items-center gap-1 px-3 py-1.5 border border-slate-200 text-sm text-slate-700 hover:bg-slate-50 transition-colors rounded disabled:opacity-40"
                        >
                          Next <ChevronRight size={14} />
                        </button>
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
                    <div className="bg-white border border-slate-200 rounded-lg p-8 text-center">
                      <Briefcase size={28} className="text-slate-300 mx-auto mb-2" />
                      <p className="text-sm font-medium text-slate-600">You're not leading any collaboration yet</p>
                      <button
                        onClick={() => setShowCreateModal(true)}
                        className="mt-3 px-4 py-2 bg-[#0F2847] text-white text-sm font-medium hover:bg-[#0a1f38] transition-colors rounded"
                      >
                        + New Collaboration
                      </button>
                    </div>
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
                    <div className="bg-white border border-slate-200 rounded-lg p-8 text-center">
                      <Users size={28} className="text-slate-300 mx-auto mb-2" />
                      <p className="text-sm font-medium text-slate-600">You haven't joined any collaboration yet</p>
                      <p className="text-xs text-slate-400 mt-1">Browse the Marketplace to find open teams</p>
                    </div>
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
                  <button onClick={fetchMyInvitations} className="text-xs text-[#0F2847] hover:underline">Refresh</button>
                </div>

                {myInvitations.length === 0 ? (
                  <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
                    <Mail size={32} className="text-slate-300 mx-auto mb-3" />
                    <p className="font-medium text-slate-700">No pending invitations</p>
                    <p className="text-sm text-slate-500 mt-1">When researchers invite you to their grant teams, they'll appear here.</p>
                  </div>
                ) : (
                  <div className="bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
                    {myInvitations.map(inv => (
                      <div key={inv._id} className="p-4 flex items-start gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="font-medium text-slate-900 text-sm">{inv.collaboration_title || inv.collab?.title || "Untitled Collaboration"}</p>
                            {inv.role && <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">{inv.role}</span>}
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
                          <button
                            onClick={() => handleInvitationRespond(inv._id, "accepted")}
                            disabled={respondingId === inv._id}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-700 transition-colors rounded disabled:opacity-50"
                          >
                            {respondingId === inv._id ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle size={12} />}
                            Accept
                          </button>
                          <button
                            onClick={() => handleInvitationRespond(inv._id, "rejected")}
                            disabled={respondingId === inv._id}
                            className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors rounded disabled:opacity-50"
                          >
                            <XCircle size={12} /> Reject
                          </button>
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
                  <div className="bg-white border border-slate-200 rounded-lg p-8 text-center">
                    <BarChart2 size={28} className="text-slate-300 mx-auto mb-2" />
                    <p className="text-sm text-slate-500">No analytics data yet. Start collaborating to see your stats.</p>
                  </div>
                ) : (
                  <>
                    {/* Summary cards */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                      {[
                        { label: "Total Collaborations", value: analytics.total_collaborations ?? myCollabs.length },
                        { label: "Invitations Sent", value: analytics.invitations_sent ?? 0 },
                        { label: "Invitations Accepted", value: analytics.invitations_accepted ?? 0 },
                        { label: "Positions Filled", value: analytics.positions_filled ?? 0 },
                      ].map(({ label, value }) => (
                        <div key={label} className="bg-white border border-slate-200 rounded-lg p-4">
                          <p className="text-2xl font-bold text-slate-900">{value}</p>
                          <p className="text-xs text-slate-500 mt-1 uppercase tracking-wide">{label}</p>
                        </div>
                      ))}
                    </div>

                    {/* Acceptance rate */}
                    {analytics.invitations_sent > 0 && (
                      <div className="bg-white border border-slate-200 rounded-lg p-5">
                        <p className="text-sm font-semibold text-slate-900 mb-3">Invitation Acceptance Rate</p>
                        <div className="flex items-center gap-3">
                          <div className="flex-1 bg-slate-100 rounded-full h-3">
                            <div
                              className="h-3 bg-emerald-500 rounded-full"
                              style={{ width: `${Math.round(((analytics.invitations_accepted || 0) / analytics.invitations_sent) * 100)}%` }}
                            />
                          </div>
                          <span className="text-sm font-semibold text-slate-700 w-12 text-right">
                            {Math.round(((analytics.invitations_accepted || 0) / analytics.invitations_sent) * 100)}%
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Status distribution */}
                    {statusKeys.length > 0 && (
                      <div className="bg-white border border-slate-200 rounded-lg p-5">
                        <p className="text-sm font-semibold text-slate-900 mb-4">Collaborations by Status</p>
                        <div className="space-y-3">
                          {statusKeys.map(s => (
                            <div key={s} className="flex items-center gap-3">
                              <span className="w-16 text-xs text-slate-500 capitalize">{s}</span>
                              <div className="flex-1 bg-slate-100 rounded-full h-2.5">
                                <div
                                  className="h-2.5 rounded-full bg-[#0F2847]"
                                  style={{ width: `${(statusCounts[s] / maxStatusCount) * 100}%` }}
                                />
                              </div>
                              <span className="w-6 text-xs font-medium text-slate-700 text-right">{statusCounts[s]}</span>
                            </div>
                          ))}
                        </div>
                      </div>
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

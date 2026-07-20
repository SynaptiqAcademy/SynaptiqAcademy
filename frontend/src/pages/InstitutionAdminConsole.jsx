/* eslint-disable */
import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { EMERALD, NAVY, WARM } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  Users, BookOpen, DollarSign, BarChart2, Settings, ShieldCheck,
  Download, AlertCircle, CheckCircle2, Clock, Activity, Building2,
  ChevronRight, RefreshCw, X, Check, Mail,
} from "lucide-react";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(val, fallback = "—") {
  if (val == null || val === "") return fallback;
  return val;
}

function fmtNum(val) {
  if (val == null) return "—";
  return Number(val).toLocaleString();
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function pct(val, max) {
  if (!max) return 0;
  return Math.min(100, Math.round((val / max) * 100));
}

function iisColor(score) {
  if (score >= 7500) return "#D97706";
  if (score >= 5000) return "#7C3AED";
  if (score >= 2500) return "#0891B2";
  return "#94A3B8";
}

function iisLabel(score) {
  if (score >= 7500) return "Distinguished";
  if (score >= 5000) return "Premier";
  if (score >= 2500) return "Established";
  return "Emerging";
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton({ h = "h-4", w = "w-full", className = "" }) {
  return <div className={`${h} ${w} bg-slate-200 animate-pulse ${className}`} />;
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ message, type = "success", onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);

  const colors =
    type === "success"
      ? "bg-emerald-50 border-emerald-200 text-emerald-800"
      : "bg-red-50 border-red-200 text-red-800";

  return (
    <div className={`fixed bottom-6 right-6 z-50 border px-4 py-3 text-sm shadow-lg max-w-xs ${colors}`}>
      <div className="flex items-center gap-2">
        {type === "success" ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
        <span>{message}</span>
        <button onClick={onClose} className="ml-auto opacity-60 hover:opacity-100 text-lg leading-none">&times;</button>
      </div>
    </div>
  );
}

// ── Error card ────────────────────────────────────────────────────────────────

function ErrorCard({ message, onRetry }) {
  return (
    <div className="border border-red-200 bg-red-50 p-6 text-center">
      <AlertCircle size={20} strokeWidth={1.5} className="text-red-400 mx-auto mb-2" />
      <p className="text-red-700 text-sm mb-3">{message || "Failed to load data."}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs border border-red-300 text-red-700 px-3 py-1.5 hover:bg-red-100 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ icon: Icon = AlertCircle, message, sub }) {
  return (
    <div className="border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
      <Icon size={24} strokeWidth={1.5} className="text-slate-300 mx-auto mb-2" />
      <p className="text-slate-600 text-sm font-medium">{message}</p>
      {sub && <p className="text-slate-400 text-xs mt-1 max-w-sm mx-auto">{sub}</p>}
    </div>
  );
}

// ── KPI card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, icon: Icon, highlight }) {
  return (
    <div className={`border bg-white p-5 ${highlight ? "border-[#0F2847]" : "border-slate-200"}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">{label}</span>
        {Icon && <Icon size={13} strokeWidth={1.5} className="text-slate-400" />}
      </div>
      <div className="font-serif text-3xl text-slate-900">{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  );
}

// ── Progress bar ──────────────────────────────────────────────────────────────

function ProgressBar({ label, value = 0, max = 1000, color = "#0F2847" }) {
  const p = pct(value, max);
  return (
    <div>
      {label && (
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-slate-700 capitalize">{String(label).replace(/_/g, " ")}</span>
          <span className="text-xs font-mono text-slate-500">{fmtNum(value)} / {fmtNum(max)}</span>
        </div>
      )}
      <div className="h-2 bg-slate-100 w-full overflow-hidden">
        <div
          className="h-full transition-all duration-700"
          style={{ width: `${p}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ label, color = "slate" }) {
  const palette = {
    green: "bg-emerald-50 text-emerald-700 border-emerald-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200",
    amber: "bg-amber-50 text-amber-700 border-amber-200",
    red: "bg-red-50 text-red-700 border-red-200",
    slate: "bg-slate-100 text-slate-600 border-slate-200",
    purple: "bg-purple-50 text-purple-700 border-purple-200",
  };
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 text-xs border ${palette[color] || palette.slate}`}>
      {label}
    </span>
  );
}

// ── Verification level name ───────────────────────────────────────────────────

const VERIFICATION_LEVELS = {
  0: { name: "Unverified", color: "slate" },
  1: { name: "Basic Verified", color: "blue" },
  2: { name: "Institutional", color: "green" },
  3: { name: "Elite", color: "purple" },
};

// ── Nav items ─────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { key: "overview", label: "Overview", icon: BarChart2 },
  { key: "members", label: "Members", icon: Users },
  { key: "publications", label: "Publications", icon: BookOpen },
  { key: "grants", label: "Grants", icon: DollarSign },
  { key: "impact", label: "Impact", icon: Activity },
  { key: "settings", label: "Settings", icon: Settings },
  { key: "verification", label: "Verification", icon: ShieldCheck },
  { key: "export", label: "Export", icon: Download },
];

const COMPONENT_COLORS = [
  "#0F2847", "#0891B2", "#7C3AED", "#059669",
  "#D97706", "#DC2626", "#DB2777", "#64748B",
];

// ── Main component ────────────────────────────────────────────────────────────

export default function InstitutionAdminConsole() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [activeSection, setActiveSection] = useState("overview");
  const [overview, setOverview] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState(null);
  const [accessDenied, setAccessDenied] = useState(false);

  const [toast, setToast] = useState(null);

  // Members
  const [pendingMembers, setPendingMembers] = useState([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [membersLoaded, setMembersLoaded] = useState(false);
  const [bulkInviteEmails, setBulkInviteEmails] = useState("");
  const [bulkInviteRole, setBulkInviteRole] = useState("member");
  const [bulkInviteLoading, setBulkInviteLoading] = useState(false);

  // Settings
  const [settings, setSettings] = useState(null);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsForm, setSettingsForm] = useState({
    name: "", description: "", website: "", country: "", type: "", contact_email: "",
  });

  // Verification
  const [verification, setVerification] = useState(null);
  const [verifLoading, setVerifLoading] = useState(false);
  const [verifLoaded, setVerifLoaded] = useState(false);
  const [verifForm, setVerifForm] = useState({ requested_level: 1, evidence_urls: "" });
  const [verifSubmitting, setVerifSubmitting] = useState(false);

  // Impact
  const [impactData, setImpactData] = useState(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [impactLoaded, setImpactLoaded] = useState(false);
  const [impactRefreshing, setImpactRefreshing] = useState(false);

  // Publications / Grants (read-only stats)
  const [pubStats, setPubStats] = useState(null);
  const [pubLoading, setPubLoading] = useState(false);
  const [pubLoaded, setPubLoaded] = useState(false);
  const [grantStats, setGrantStats] = useState(null);
  const [grantLoading, setGrantLoading] = useState(false);
  const [grantLoaded, setGrantLoaded] = useState(false);

  const showToast = (message, type = "success") => setToast({ message, type });

  // ── On mount: fetch overview ───────────────────────────────────────────────

  useEffect(() => {
    const init = async () => {
      setOverviewLoading(true);
      setOverviewError(null);
      try {
        const res = await api.get(`/institution-hub/${id}/admin/overview`);
        setOverview(res.data);
      } catch (e) {
        if (e?.response?.status === 403 || e?.response?.status === 401) {
          setAccessDenied(true);
          setTimeout(() => navigate("/institution-hub"), 3000);
        } else {
          setOverviewError(e?.response?.data?.message || "Failed to load admin overview.");
        }
      } finally {
        setOverviewLoading(false);
      }
    };
    init();
  }, [id, navigate]);

  // ── Section change handler ─────────────────────────────────────────────────

  const handleSection = useCallback(
    async (section) => {
      setActiveSection(section);

      if (section === "members" && !membersLoaded) {
        setMembersLoading(true);
        try {
          const res = await api.get(`/institution-hub/${id}/admin/pending-members`);
          setPendingMembers(res.data.members || res.data.data || []);
          setMembersLoaded(true);
        } catch {
          setPendingMembers([]);
        } finally {
          setMembersLoading(false);
        }
      }

      if (section === "settings" && !settingsLoaded) {
        setSettingsLoading(true);
        try {
          const res = await api.get(`/institution-hub/${id}/admin/settings`);
          const d = res.data;
          setSettings(d);
          setSettingsForm({
            name: d.name || "",
            description: d.description || "",
            website: d.website || "",
            country: d.country || "",
            type: d.type || "",
            contact_email: d.contact_email || "",
          });
          setSettingsLoaded(true);
        } catch {
          setSettings({});
        } finally {
          setSettingsLoading(false);
        }
      }

      if (section === "verification" && !verifLoaded) {
        setVerifLoading(true);
        try {
          const res = await api.get(`/institution-hub/${id}/public-profile`);
          setVerification(res.data);
          setVerifLoaded(true);
        } catch {
          setVerification({});
        } finally {
          setVerifLoading(false);
        }
      }

      if (section === "impact" && !impactLoaded) {
        setImpactLoading(true);
        try {
          const res = await api.get(`/institution-hub/${id}/impact`);
          setImpactData(res.data);
          setImpactLoaded(true);
        } catch {
          setImpactData({});
        } finally {
          setImpactLoading(false);
        }
      }

      if (section === "publications" && !pubLoaded) {
        setPubLoading(true);
        try {
          const res = await api.get(`/institution-hub/${id}/publications?page=1&limit=1`);
          setPubStats(res.data.stats || {});
          setPubLoaded(true);
        } catch {
          setPubStats({});
        } finally {
          setPubLoading(false);
        }
      }

      if (section === "grants" && !grantLoaded) {
        setGrantLoading(true);
        try {
          const res = await api.get(`/institution-hub/${id}/grants?page=1&limit=1`);
          setGrantStats(res.data.stats || {});
          setGrantLoaded(true);
        } catch {
          setGrantStats({});
        } finally {
          setGrantLoading(false);
        }
      }
    },
    [id, membersLoaded, settingsLoaded, verifLoaded, impactLoaded, pubLoaded, grantLoaded]
  );

  // ── Members actions ────────────────────────────────────────────────────────

  const handleMemberAction = async (uid, action) => {
    try {
      await api.patch(`/institutions/${id}/members/${uid}/role`, {
        action,
        role: action === "approve" ? "member" : undefined,
      });
      setPendingMembers((prev) => prev.filter((m) => m._id !== uid && m.user_id !== uid));
      showToast(`Member ${action === "approve" ? "approved" : "rejected"}.`);
    } catch (e) {
      showToast(e?.response?.data?.message || "Action failed.", "error");
    }
  };

  const handleBulkInvite = async () => {
    if (!bulkInviteEmails.trim()) return;
    setBulkInviteLoading(true);
    try {
      const emails = bulkInviteEmails
        .split(",")
        .map((e) => e.trim())
        .filter(Boolean);
      await api.post(`/institution-hub/${id}/admin/bulk-invite`, {
        emails,
        role: bulkInviteRole,
      });
      setBulkInviteEmails("");
      showToast(`Invites sent to ${emails.length} address${emails.length !== 1 ? "es" : ""}.`);
    } catch (e) {
      showToast(e?.response?.data?.message || "Bulk invite failed.", "error");
    } finally {
      setBulkInviteLoading(false);
    }
  };

  // ── Settings save ──────────────────────────────────────────────────────────

  const handleSettingsSave = async () => {
    setSettingsSaving(true);
    try {
      await api.put(`/institution-hub/${id}/admin/settings`, settingsForm);
      showToast("Settings saved.");
    } catch (e) {
      showToast(e?.response?.data?.message || "Save failed.", "error");
    } finally {
      setSettingsSaving(false);
    }
  };

  // ── Verification request ───────────────────────────────────────────────────

  const handleVerifRequest = async () => {
    setVerifSubmitting(true);
    try {
      const urls = verifForm.evidence_urls
        .split("\n")
        .map((u) => u.trim())
        .filter(Boolean);
      await api.post(`/institution-hub/${id}/verify-request`, {
        requested_level: Number(verifForm.requested_level),
        evidence_urls: urls,
      });
      showToast("Verification request submitted.");
    } catch (e) {
      showToast(e?.response?.data?.message || "Request failed.", "error");
    } finally {
      setVerifSubmitting(false);
    }
  };

  // ── Export ─────────────────────────────────────────────────────────────────

  const handleExport = async () => {
    try {
      const res = await api.get(`/institution-hub/${id}/admin/export`);
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `institution-${id}-export.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Export downloaded.");
    } catch (e) {
      showToast(e?.response?.data?.message || "Export failed.", "error");
    }
  };

  // ── Impact refresh ─────────────────────────────────────────────────────────

  const handleImpactRefresh = async () => {
    setImpactRefreshing(true);
    try {
      const res = await api.get(`/institution-hub/${id}/impact?force=true`);
      setImpactData(res.data);
      showToast("Impact score refreshed.");
    } catch (e) {
      showToast(e?.response?.data?.message || "Refresh failed.", "error");
    } finally {
      setImpactRefreshing(false);
    }
  };

  // ── Access denied ──────────────────────────────────────────────────────────

  if (accessDenied) {
    return (
      <div className="min-h-screen bg-[#F4F6FA] flex items-center justify-center p-6">
        <div className="border border-red-200 bg-white p-8 text-center max-w-md">
          <AlertCircle size={32} strokeWidth={1.5} className="text-red-400 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-slate-900 mb-2">Access Denied</h2>
          <p className="text-sm text-slate-500">
            You do not have admin access to this institution. Redirecting...
          </p>
        </div>
      </div>
    );
  }

  // ── Section content ────────────────────────────────────────────────────────

  function OverviewSection() {
    if (overviewLoading) {
      return (
        <div className="space-y-4 animate-pulse">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 bg-slate-200" />)}
          </div>
          <div className="h-48 bg-slate-200" />
        </div>
      );
    }
    if (overviewError) {
      return <ErrorCard message={overviewError} onRetry={() => window.location.reload()} />;
    }
    if (!overview) return null;

    const kpis = overview.kpis || overview;
    const timeline = overview.recent_activity || overview.timeline || [];

    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <KpiCard label="Members" value={fmtNum(kpis.member_count)} icon={Users} />
          <KpiCard label="Pending Invites" value={fmtNum(kpis.pending_invites)} icon={Mail} />
          <KpiCard label="Publications" value={fmtNum(kpis.total_publications)} icon={BookOpen} />
          <KpiCard label="Grants" value={fmtNum(kpis.total_grants)} icon={DollarSign} />
        </div>
        {kpis.iis_score != null && (
          <div className="border border-slate-200 bg-white p-4 flex items-center gap-4">
            <BarChart2 size={16} strokeWidth={1.5} className="text-slate-400 flex-shrink-0" />
            <div className="flex-1">
              <div className="text-xs text-slate-500 mb-1">Institution Impact Score</div>
              <div className="flex items-center gap-3">
                <div className="font-mono text-lg font-bold" style={{ color: iisColor(kpis.iis_score) }}>
                  {fmtNum(kpis.iis_score)}
                </div>
                <StatusBadge label={iisLabel(kpis.iis_score)} color="blue" />
              </div>
            </div>
          </div>
        )}
        {timeline.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Recent Activity</h3>
            <div className="space-y-3">
              {timeline.slice(0, 10).map((ev, idx) => (
                <div key={idx} className="flex items-start gap-3 py-2 border-b border-slate-100 last:border-0">
                  <Activity size={13} strokeWidth={1.5} className="text-slate-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-slate-800">{ev.title || ev.description || ev.event_type}</div>
                    <div className="text-xs text-slate-400">{formatDate(ev.created_at)}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  function MembersSection() {
    return (
      <div className="space-y-6">
        {/* Pending members */}
        <div className="border border-slate-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Pending Member Requests</h3>
          {membersLoading ? (
            <div className="space-y-2 animate-pulse">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-12 bg-slate-200" />)}</div>
          ) : pendingMembers.length === 0 ? (
            <EmptyState icon={Users} message="No pending member requests." />
          ) : (
            <div className="space-y-2">
              {pendingMembers.map((m) => (
                <div key={m._id || m.user_id} className="flex items-center gap-3 p-3 border border-slate-100">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-900">{m.name || m.display_name}</div>
                    <div className="text-xs text-slate-500">{m.email}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleMemberAction(m._id || m.user_id, "approve")}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs bg-emerald-50 border border-emerald-200 text-emerald-700 hover:bg-emerald-100 transition-colors"
                    >
                      <Check size={11} strokeWidth={2} />
                      Approve
                    </button>
                    <button
                      onClick={() => handleMemberAction(m._id || m.user_id, "reject")}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs bg-red-50 border border-red-200 text-red-700 hover:bg-red-100 transition-colors"
                    >
                      <X size={11} strokeWidth={2} />
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bulk invite */}
        <div className="border border-slate-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Bulk Invite</h3>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">
                Email addresses (comma-separated)
              </label>
              <textarea
                rows={4}
                placeholder="user1@example.com, user2@example.com, ..."
                value={bulkInviteEmails}
                onChange={(e) => setBulkInviteEmails(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 text-sm focus:outline-none focus:border-[#0F2847] resize-none"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Role</label>
              <select
                value={bulkInviteRole}
                onChange={(e) => setBulkInviteRole(e.target.value)}
                className="px-3 py-2 border border-slate-200 text-sm focus:outline-none focus:border-[#0F2847]"
              >
                <option value="member">Member</option>
                <option value="researcher">Researcher</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button
              onClick={handleBulkInvite}
              disabled={bulkInviteLoading || !bulkInviteEmails.trim()}
              className="px-4 py-2 bg-[#0F2847] text-white text-sm font-medium hover:bg-[#0a1f38] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {bulkInviteLoading ? "Sending..." : "Send Invites"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  function PublicationsSection() {
    if (pubLoading) {
      return <div className="h-32 bg-slate-200 animate-pulse" />;
    }
    const stats = pubStats || {};
    return (
      <div className="border border-slate-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-slate-900 mb-4">Publication Statistics</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[
            { label: "Total Publications", value: fmtNum(stats.total_publications) },
            { label: "Total Citations", value: fmtNum(stats.total_citations) },
            { label: "Avg Citations", value: stats.avg_citations != null ? stats.avg_citations.toFixed(1) : "—" },
            { label: "H-Index", value: fmtNum(stats.h_index) },
            { label: "This Year", value: fmtNum(stats.publications_this_year) },
          ].map(({ label, value }) => (
            <div key={label} className="p-3 border border-slate-100">
              <div className="text-xs text-slate-500 mb-1">{label}</div>
              <div className="font-serif text-xl text-slate-900">{value}</div>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400 mt-4">
          Publication data is read-only. Manage publications through member profiles.
        </p>
      </div>
    );
  }

  function GrantsSection() {
    if (grantLoading) {
      return <div className="h-32 bg-slate-200 animate-pulse" />;
    }
    const stats = grantStats || {};
    return (
      <div className="border border-slate-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-slate-900 mb-4">Grant Statistics</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[
            { label: "Total Applications", value: fmtNum(stats.total_applications) },
            { label: "Approved", value: fmtNum(stats.approved) },
            { label: "Success Rate", value: stats.success_rate != null ? `${stats.success_rate.toFixed(1)}%` : "—" },
            { label: "Total Awarded", value: stats.total_awarded != null ? `$${fmtNum(stats.total_awarded)}` : "—" },
            { label: "Pending", value: fmtNum(stats.pending) },
          ].map(({ label, value }) => (
            <div key={label} className="p-3 border border-slate-100">
              <div className="text-xs text-slate-500 mb-1">{label}</div>
              <div className="font-serif text-xl text-slate-900">{value}</div>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400 mt-4">
          Grant data is read-only. Grant applications are managed by individual researchers.
        </p>
      </div>
    );
  }

  function ImpactSection() {
    if (impactLoading) {
      return <div className="space-y-3 animate-pulse">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-16 bg-slate-200" />)}</div>;
    }
    const d = impactData || {};
    const components = d.components || {};
    const componentKeys = Object.keys(components);
    const score = d.iis_score || 0;

    return (
      <div className="space-y-5">
        <div className="border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="text-xs text-slate-500 mb-1">Institution Impact Score</div>
              <div className="font-mono text-3xl font-bold" style={{ color: iisColor(score) }}>
                {fmtNum(score)}
              </div>
              <div className="text-xs font-medium mt-0.5 text-slate-500">{iisLabel(score)}</div>
            </div>
            <button
              onClick={handleImpactRefresh}
              disabled={impactRefreshing}
              className="flex items-center gap-1.5 px-4 py-2 border border-slate-200 text-sm text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={13} strokeWidth={1.5} className={impactRefreshing ? "animate-spin" : ""} />
              {impactRefreshing ? "Refreshing..." : "Refresh Score"}
            </button>
          </div>

          {componentKeys.length > 0 && (
            <div className="space-y-4">
              {componentKeys.map((key, idx) => {
                const comp = components[key];
                const val = typeof comp === "object" ? comp.score || comp.value || 0 : comp || 0;
                const maxVal = typeof comp === "object" ? comp.max_score || comp.max || 1000 : 1000;
                return (
                  <ProgressBar
                    key={key}
                    label={key}
                    value={val}
                    max={maxVal}
                    color={COMPONENT_COLORS[idx % COMPONENT_COLORS.length]}
                  />
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  }

  function SettingsSection() {
    if (settingsLoading) {
      return <div className="space-y-4 animate-pulse">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-10 bg-slate-200" />)}</div>;
    }

    const fields = [
      { key: "name", label: "Institution Name", type: "text" },
      { key: "description", label: "Description", type: "textarea" },
      { key: "website", label: "Website URL", type: "url" },
      { key: "country", label: "Country", type: "text" },
      { key: "type", label: "Type", type: "select", options: ["university", "research_center", "laboratory", "hospital", "government", "ngo"] },
      { key: "contact_email", label: "Contact Email", type: "email" },
    ];

    return (
      <div className="border border-slate-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-slate-900 mb-6">Institution Settings</h3>
        <div className="space-y-4 max-w-lg">
          {fields.map(({ key, label, type, options }) => (
            <div key={key}>
              <label className="text-xs text-slate-500 block mb-1">{label}</label>
              {type === "textarea" ? (
                <textarea
                  rows={3}
                  value={settingsForm[key] || ""}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, [key]: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-200 text-sm focus:outline-none focus:border-[#0F2847] resize-none"
                />
              ) : type === "select" ? (
                <select
                  value={settingsForm[key] || ""}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, [key]: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-200 text-sm focus:outline-none focus:border-[#0F2847]"
                >
                  <option value="">Select...</option>
                  {options.map((o) => (
                    <option key={o} value={o}>{o.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</option>
                  ))}
                </select>
              ) : (
                <input
                  type={type}
                  value={settingsForm[key] || ""}
                  onChange={(e) => setSettingsForm((prev) => ({ ...prev, [key]: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-200 text-sm focus:outline-none focus:border-[#0F2847]"
                />
              )}
            </div>
          ))}
          <button
            onClick={handleSettingsSave}
            disabled={settingsSaving}
            className="px-4 py-2 bg-[#0F2847] text-white text-sm font-medium hover:bg-[#0a1f38] transition-colors disabled:opacity-50"
          >
            {settingsSaving ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </div>
    );
  }

  function VerificationSection() {
    if (verifLoading) {
      return <div className="space-y-3 animate-pulse">{Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-16 bg-slate-200" />)}</div>;
    }

    const currentLevel = verification?.verification_level ?? 0;
    const levelInfo = VERIFICATION_LEVELS[currentLevel] || VERIFICATION_LEVELS[0];
    const pendingRequests = verification?.pending_verification_requests || [];

    return (
      <div className="space-y-5">
        <div className="border border-slate-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Current Verification Status</h3>
          <div className="flex items-center gap-3">
            <ShieldCheck size={20} strokeWidth={1.5} className="text-slate-400" />
            <div>
              <div className="text-sm font-medium text-slate-900">Level {currentLevel} — {levelInfo.name}</div>
              <div className="text-xs text-slate-500">
                {currentLevel === 0
                  ? "Submit a request to begin the verification process."
                  : currentLevel === 3
                  ? "Your institution has achieved maximum verification."
                  : "Request a higher level to unlock additional visibility."}
              </div>
            </div>
            <StatusBadge label={levelInfo.name} color={levelInfo.color} />
          </div>
        </div>

        {pendingRequests.length > 0 && (
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Pending Requests</h3>
            <div className="space-y-2">
              {pendingRequests.map((r, idx) => (
                <div key={idx} className="flex items-center gap-3 p-3 border border-slate-100">
                  <Clock size={13} strokeWidth={1.5} className="text-amber-500 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="text-sm text-slate-800">Level {r.requested_level} request</div>
                    <div className="text-xs text-slate-400">Submitted {formatDate(r.submitted_at)}</div>
                  </div>
                  <StatusBadge label="Under Review" color="amber" />
                </div>
              ))}
            </div>
          </div>
        )}

        {currentLevel < 3 && (
          <div className="border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Request Higher Verification</h3>
            <div className="space-y-4 max-w-lg">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Requested Level</label>
                <select
                  value={verifForm.requested_level}
                  onChange={(e) => setVerifForm((prev) => ({ ...prev, requested_level: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-200 text-sm focus:outline-none focus:border-[#0F2847]"
                >
                  {[1, 2, 3].filter((l) => l > currentLevel).map((l) => (
                    <option key={l} value={l}>Level {l} — {VERIFICATION_LEVELS[l]?.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Evidence URLs (one per line)</label>
                <textarea
                  rows={4}
                  placeholder="https://example.com/accreditation&#10;https://example.com/certificate"
                  value={verifForm.evidence_urls}
                  onChange={(e) => setVerifForm((prev) => ({ ...prev, evidence_urls: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-200 text-sm focus:outline-none focus:border-[#0F2847] resize-none"
                />
              </div>
              <button
                onClick={handleVerifRequest}
                disabled={verifSubmitting}
                className="px-4 py-2 bg-[#0F2847] text-white text-sm font-medium hover:bg-[#0a1f38] transition-colors disabled:opacity-50"
              >
                {verifSubmitting ? "Submitting..." : "Submit Request"}
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  function ExportSection() {
    return (
      <div className="border border-slate-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-slate-900 mb-2">Export Institution Data</h3>
        <p className="text-sm text-slate-500 mb-6">
          Download a complete JSON export of your institution data including members, publications, grants, and impact scores.
        </p>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 bg-[#0F2847] text-white text-sm font-medium hover:bg-[#0a1f38] transition-colors"
        >
          <Download size={14} strokeWidth={1.5} />
          Download Export
        </button>
      </div>
    );
  }

  function SectionContent() {
    switch (activeSection) {
      case "overview":      return <OverviewSection />;
      case "members":       return <MembersSection />;
      case "publications":  return <PublicationsSection />;
      case "grants":        return <GrantsSection />;
      case "impact":        return <ImpactSection />;
      case "settings":      return <SettingsSection />;
      case "verification":  return <VerificationSection />;
      case "export":        return <ExportSection />;
      default:              return null;
    }
  }

  return (
    <AdministrationLayout
      title={overview?.institution_name || overview?.name || "Admin Console"}
      subtitle="Manage your institution settings, members, and data."
    >
      <div className="flex gap-6">
          {/* Sidebar nav */}
          <aside className="w-52 flex-shrink-0">
            <nav className="space-y-0.5">
              {NAV_ITEMS.map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => handleSection(key)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2.5 text-sm font-medium transition-colors text-left ${
                    activeSection === key
                      ? "bg-[#0F2847] text-white"
                      : "text-slate-600 hover:bg-white hover:text-slate-900"
                  }`}
                >
                  <Icon size={14} strokeWidth={1.5} />
                  {label}
                </button>
              ))}
            </nav>
          </aside>

          {/* Main content */}
          <main className="flex-1 min-w-0">
            <SectionContent />
          </main>
        </div>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </AdministrationLayout>
  );
}

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Users, UserPlus, UserCheck, MailWarning, CreditCard, ShieldAlert,
  ExternalLink, Ban, RotateCcw,
} from "lucide-react";
import api from "@/lib/api";
import { AdministrationLayout } from "@/layouts";
import { useAdminRealtime } from "@/contexts/AdminRealtimeContext";
import {
  DataTable, ContextPanel, Drawer, SmartActionsBar,
  SearchBar, FilterChip, SkeletonCard, ErrorState, EmptyState, Badge,
} from "@/components/ds";

const LIMIT = 20;
const RECENT_FILTERS_KEY = "sq_admin_recent_user_filters";
const MAX_RECENT_FILTERS = 6;

function planBadgeVariant(plan) {
  if (plan === "institution") return "purple";
  if (plan === "pro_researcher") return "info";
  if (plan === "researcher") return "info";
  return "neutral";
}

function statusBadgeVariant(status) {
  if (status === "suspended") return "warning";
  if (status === "banned") return "danger";
  return "success";
}

function saveRecentFilter(filter) {
  if (!filter.q && !filter.plan && !filter.status && !filter.role) return;
  try {
    const saved = JSON.parse(localStorage.getItem(RECENT_FILTERS_KEY) || "[]");
    const key = JSON.stringify(filter);
    const next = [filter, ...saved.filter((f) => JSON.stringify(f) !== key)].slice(0, MAX_RECENT_FILTERS);
    localStorage.setItem(RECENT_FILTERS_KEY, JSON.stringify(next));
  } catch {}
}

function getRecentFilters() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_FILTERS_KEY) || "[]");
  } catch {
    return [];
  }
}

function filterLabel(f) {
  const parts = [];
  if (f.q) parts.push(`"${f.q}"`);
  if (f.plan) parts.push(f.plan.replace("_", " "));
  if (f.status) parts.push(f.status);
  if (f.role) parts.push(f.role.replace("_", " "));
  return parts.join(" · ") || "All users";
}

export default function AdminUsers() {
  const navigate = useNavigate();
  const { lastEvent } = useAdminRealtime();

  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [plan, setPlan] = useState("");
  const [status, setStatus] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [recentFilters, setRecentFilters] = useState(getRecentFilters());

  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);

  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkLoading, setBulkLoading] = useState(false);

  const [previewUser, setPreviewUser] = useState(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ page, limit: LIMIT });
      if (q) params.set("q", q);
      if (plan) params.set("plan", plan);
      if (status) params.set("status", status);
      if (role) params.set("role", role);
      const r = await api.get(`/admin/users?${params}`);
      setUsers(r.data.items || []);
      setTotal(r.data.total || 0);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, [page, q, plan, status, role]);

  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const r = await api.get("/admin/users/stats");
      setStats(r.data);
    } catch (e) {
      // Non-fatal — the list still works without the context panel.
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);
  useEffect(() => { fetchStats(); }, [fetchStats]);

  // Live refresh: a new registration should update the context panel and,
  // if the user is currently on page 1 with no filters, the list too.
  useEffect(() => {
    if (lastEvent?.type === "user_registered") {
      fetchStats();
      if (page === 1 && !q && !plan && !status && !role) fetchUsers();
      else toast.info("A new user just registered");
    }
  }, [lastEvent, fetchStats, fetchUsers, page, q, plan, status, role]);

  // Debounce search input
  useEffect(() => {
    const t = setTimeout(() => {
      setQ(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  // Remember non-empty filter combos for the "Recent filters" row.
  useEffect(() => {
    if (loading) return;
    const t = setTimeout(() => {
      saveRecentFilter({ q, plan, status, role });
      setRecentFilters(getRecentFilters());
    }, 600);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, plan, status, role]);

  const applyRecentFilter = (f) => {
    setSearchInput(f.q || "");
    setQ(f.q || "");
    setPlan(f.plan || "");
    setStatus(f.status || "");
    setRole(f.role || "");
    setPage(1);
  };

  const start = (page - 1) * LIMIT + 1;
  const end = Math.min(page * LIMIT, total);
  const totalPages = Math.ceil(total / LIMIT);

  const contextStats = useMemo(() => ([
    { label: "New Today", value: stats?.new_today, icon: <UserPlus /> },
    { label: "Active Today", value: stats?.active_today, icon: <UserCheck /> },
    { label: "Pending Verification", value: stats?.pending_verification, icon: <MailWarning /> },
    { label: "Paid Users", value: stats?.paid_users, icon: <CreditCard />, highlight: true },
    { label: "Suspended / Banned", value: stats?.suspended_or_banned, icon: <ShieldAlert /> },
  ]), [stats]);

  const trendData = useMemo(
    () => (stats?.growth_trend || []).map((d) => d.count),
    [stats],
  );

  function toggleRow(row, checked) {
    const id = row.id;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id); else next.delete(id);
      return next;
    });
  }

  function toggleAll(checked) {
    setSelectedIds(checked ? new Set(users.map((u) => u.id)) : new Set());
  }

  async function bulkSuspend() {
    if (selectedIds.size === 0) return;
    setBulkLoading(true);
    let ok = 0, fail = 0;
    for (const id of selectedIds) {
      try {
        await api.post(`/admin/users/${id}/suspend`, { reason: "Bulk action from Users list" });
        ok += 1;
      } catch {
        fail += 1;
      }
    }
    setBulkLoading(false);
    setSelectedIds(new Set());
    toast[fail ? "warning" : "success"](`Suspended ${ok} user(s)${fail ? `, ${fail} failed` : ""}`);
    fetchUsers();
    fetchStats();
  }

  const columns = [
    {
      key: "name", label: "Name / Email", sortable: false,
      render: (_v, row) => (
        <div>
          <div style={{ fontWeight: 500, color: "#0f172a" }}>{row.full_name || "—"}</div>
          <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>{row.email}</div>
        </div>
      ),
    },
    { key: "plan_code", label: "Plan", render: (v) => <Badge variant={planBadgeVariant(v)}>{(v || "free").replace("_", " ")}</Badge> },
    { key: "status", label: "Status", render: (v) => <Badge variant={statusBadgeVariant(v)}>{v || "active"}</Badge> },
    { key: "role", label: "Role", render: (v) => v || "user" },
    {
      key: "created_at", label: "Joined",
      render: (v) => v ? new Date(v).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—",
    },
    {
      key: "credits_balance", label: "Credits",
      render: (_v, row) => (row.credits_balance || 0) + (row.credits_pack_balance || 0),
    },
  ];

  return (
    <AdministrationLayout
      title="User Management"
      subtitle="Search, filter, and manage all platform users"
    >
      <ContextPanel stats={contextStats} trend={trendData} loading={statsLoading} cols={5} />

      {/* Filters */}
      <div className="flex flex-col gap-2 mb-4">
        <div className="flex gap-3 flex-wrap">
          <div className="flex-1 max-w-sm">
            <SearchBar
              value={searchInput}
              onChange={setSearchInput}
              placeholder="Search name or email…"
              onClear={() => setSearchInput("")}
              size="md"
            />
          </div>
          <select
            value={plan}
            onChange={(e) => { setPlan(e.target.value); setPage(1); }}
            className="px-3 py-2 text-sm border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
          >
            <option value="">All plans</option>
            <option value="free">Free</option>
            <option value="researcher">Researcher</option>
            <option value="pro_researcher">Pro Researcher</option>
            <option value="institution">Institution</option>
          </select>
          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1); }}
            className="px-3 py-2 text-sm border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
            <option value="banned">Banned</option>
          </select>
          <select
            value={role}
            onChange={(e) => { setRole(e.target.value); setPage(1); }}
            className="px-3 py-2 text-sm border border-slate-300 bg-white focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
          >
            <option value="">All roles</option>
            <option value="user">User</option>
            <option value="moderator">Moderator</option>
            <option value="verified_researcher">Verified Researcher</option>
            <option value="verified_professor">Verified Professor</option>
            <option value="institution_admin">Institution Admin</option>
            <option value="admin">Admin</option>
            <option value="super_admin">Super Admin (view only)</option>
          </select>
        </div>

        {recentFilters.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94a3b8" }}>
              Recent
            </span>
            {recentFilters.map((f, i) => (
              <FilterChip
                key={i}
                label={filterLabel(f)}
                active={f.q === q && f.plan === plan && f.status === status && f.role === role}
                onClick={() => applyRecentFilter(f)}
              />
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4">
          <ErrorState message={error} type="server" onRetry={fetchUsers} />
        </div>
      )}

      {!loading && (
        <p className="text-xs text-slate-500 mb-3">
          {total > 0 ? `Showing ${start}–${end} of ${total} users` : "No users found"}
        </p>
      )}

      {selectedIds.size > 0 && (
        <SmartActionsBar
          actions={[
            {
              label: `Suspend ${selectedIds.size} selected`,
              icon: Ban,
              variant: "danger",
              loading: bulkLoading,
              onClick: bulkSuspend,
            },
            {
              label: "Clear selection",
              icon: RotateCcw,
              variant: "ghost",
              onClick: () => setSelectedIds(new Set()),
            },
          ]}
        />
      )}

      {loading ? (
        <SkeletonCard rows={6} />
      ) : users.length === 0 ? (
        <EmptyState icon={<Users size={24} />} title="No users found" description="Adjust your search filters" size="sm" />
      ) : (
        <DataTable
          columns={columns}
          rows={users}
          onRowClick={(row) => setPreviewUser(row)}
          selectable
          selectedIds={selectedIds}
          onSelectRow={toggleRow}
          onSelectAll={toggleAll}
          stickyHeader
        />
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="text-sm text-slate-600 hover:text-slate-900 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            ‹ Previous
          </button>
          <span className="text-xs text-slate-500">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="text-sm text-slate-600 hover:text-slate-900 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next ›
          </button>
        </div>
      )}

      {/* Quick-preview drawer — avoids forcing navigation for a quick look */}
      <Drawer
        open={!!previewUser}
        onClose={() => setPreviewUser(null)}
        title={previewUser?.full_name || previewUser?.email}
        width={420}
      >
        {previewUser && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant={planBadgeVariant(previewUser.plan_code)}>
                {(previewUser.plan_code || "free").replace("_", " ")}
              </Badge>
              <Badge variant={statusBadgeVariant(previewUser.status)}>
                {previewUser.status || "active"}
              </Badge>
              <span className="text-xs text-slate-500">{previewUser.role || "user"}</span>
            </div>

            <div className="text-sm text-slate-700 space-y-1.5">
              <div><span className="text-slate-400">Email:</span> {previewUser.email}</div>
              <div>
                <span className="text-slate-400">Joined:</span>{" "}
                {previewUser.created_at ? new Date(previewUser.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—"}
              </div>
              <div><span className="text-slate-400">Email verified:</span> {previewUser.email_verified ? "Yes" : "No"}</div>
              <div>
                <span className="text-slate-400">Credits:</span>{" "}
                {(previewUser.credits_balance || 0) + (previewUser.credits_pack_balance || 0)}
              </div>
            </div>

            <SmartActionsBar
              actions={[
                {
                  label: "View full profile",
                  icon: ExternalLink,
                  variant: "primary",
                  onClick: () => navigate(`/admin/users/${previewUser.id}`),
                },
              ]}
            />
          </div>
        )}
      </Drawer>
    </AdministrationLayout>
  );
}

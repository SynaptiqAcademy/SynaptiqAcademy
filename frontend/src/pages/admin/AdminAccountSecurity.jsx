/* eslint-disable */
import React, { useState, useCallback } from "react";
import {
  ShieldCheck, ShieldAlert, Shield, Users, RefreshCw,
  CheckCircle2, XCircle, AlertTriangle, Lock, Unlock,
  ChevronDown, ChevronRight, Zap, Eye,
} from "lucide-react";
import api from "@/lib/api";
import { NAVY, WARM, BRD } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

// ── tiny shared fetch hook ────────────────────────────────────────────────────
function useAdminFetch(path, deps = []) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.get(path);
      setData(r.data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Request failed");
    } finally {
      setLoading(false);
    }
  }, deps);

  return { data, loading, error, fetch };
}

// ── colour helpers ────────────────────────────────────────────────────────────
const ROLE_COLOURS = {
  super_admin:        "bg-red-100 text-red-700 border border-red-300",
  admin:              "bg-orange-100 text-orange-700 border border-orange-300",
  institution_admin:  "bg-amber-100 text-amber-700 border border-amber-300",
  moderator:          "bg-blue-100 text-blue-700 border border-blue-300",
  verified_professor: "bg-purple-100 text-purple-700 border border-purple-300",
  verified_researcher:"bg-indigo-100 text-indigo-700 border border-indigo-300",
  user:               "bg-slate-100 text-slate-600 border border-slate-300",
};
const rolePill = (role) => (
  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ROLE_COLOURS[role] || "bg-slate-100 text-slate-600"}`}>
    {role}
  </span>
);

// ─────────────────────────────────────────────────────────────────────────────
// Section: Protected Account Status
// ─────────────────────────────────────────────────────────────────────────────
function ProtectedStatus() {
  const { data, loading, error, fetch } = useAdminFetch("/api/admin/account-security/protected-status");

  React.useEffect(() => { fetch(); }, []);

  if (loading) return <div className="text-sm text-slate-400 animate-pulse">Checking protected account…</div>;
  if (error)   return <div className="text-sm text-red-500">{error}</div>;
  if (!data)   return null;

  return (
    <div className={`rounded-md border p-5 ${data.healthy ? "border-green-300 bg-green-50" : "border-red-300 bg-red-50"}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {data.healthy ? (
            <CheckCircle2 className="w-5 h-5 text-green-600" />
          ) : (
            <XCircle className="w-5 h-5 text-red-600" />
          )}
          <span className="font-semibold text-slate-800">
            {data.exists ? data.email : "Protected account not found"}
          </span>
          {data.exists && rolePill(data.role)}
        </div>
        <button onClick={fetch} className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>

      {data.exists && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div>
            <div className="text-slate-500 text-xs">Status</div>
            <div className={`font-medium ${data.status === "active" ? "text-green-700" : "text-red-700"}`}>
              {data.status}
            </div>
          </div>
          <div>
            <div className="text-slate-500 text-xs">Email verified</div>
            <div className={`font-medium ${data.email_verified ? "text-green-700" : "text-red-700"}`}>
              {data.email_verified ? "Yes" : "No"}
            </div>
          </div>
          <div>
            <div className="text-slate-500 text-xs">Protected flag</div>
            <div className={`font-medium ${data.protected ? "text-green-700" : "text-amber-700"}`}>
              {data.protected ? "Set" : "Missing"}
            </div>
          </div>
          <div>
            <div className="text-slate-500 text-xs">Plan</div>
            <div className="font-medium text-slate-700">{data.plan_code || "—"}</div>
          </div>
        </div>
      )}

      {data.issues?.length > 0 && (
        <div className="mt-3 space-y-1">
          {data.issues.map((issue, i) => (
            <div key={i} className="flex items-center gap-2 text-sm text-red-700">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
              {issue}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Role Hierarchy
// ─────────────────────────────────────────────────────────────────────────────
function RoleHierarchy() {
  const { data, loading, fetch } = useAdminFetch("/api/admin/account-security/role-hierarchy");
  React.useEffect(() => { fetch(); }, []);

  if (loading) return <div className="text-sm text-slate-400 animate-pulse">Loading hierarchy…</div>;
  if (!data)   return null;

  return (
    <div className="space-y-2">
      {(data.hierarchy || []).map((row) => (
        <div key={row.role} className="flex items-center gap-3">
          <div className="w-8 text-right text-xs font-mono text-slate-400">L{Math.round(row.level / 10)}</div>
          <div className="flex-1 flex items-center gap-2">
            <div
              className="h-2 rounded-full bg-gradient-to-r from-red-400 to-blue-400"
              style={{ width: `${row.level}%`, opacity: 0.6 + row.level / 300 }}
            />
          </div>
          {rolePill(row.role)}
          <div className="w-16 text-right text-xs text-slate-500">{row.count.toLocaleString()} users</div>
          {row.role === "super_admin" && (
            <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">DB-only</span>
          )}
          {row.api_grantable && (
            <span className="text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">API</span>
          )}
        </div>
      ))}
      <div className="text-xs text-slate-400 mt-1">Total platform users: {data.total_users?.toLocaleString()}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Privilege Audit
// ─────────────────────────────────────────────────────────────────────────────
function PrivilegeAudit() {
  const { data, loading, error, fetch } = useAdminFetch("/api/admin/account-security/audit");
  React.useEffect(() => { fetch(); }, []);

  if (loading) return <div className="text-sm text-slate-400 animate-pulse">Auditing accounts…</div>;
  if (error)   return <div className="text-sm text-red-500">{error}</div>;
  if (!data)   return null;

  return (
    <div className="space-y-4">
      {/* Risk banner */}
      {data.risk_count > 0 && (
        <div className="rounded-md border border-red-300 bg-red-50 p-4 flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-red-800 mb-1">{data.risk_count} security risk{data.risk_count > 1 ? "s" : ""} detected</div>
            {data.risks.map((r, i) => (
              <div key={i} className="text-sm text-red-700">{r.message}</div>
            ))}
          </div>
        </div>
      )}

      {/* Stats bar */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-slate-50 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-slate-700">{data.total_elevated}</div>
          <div className="text-xs text-slate-500">Elevated accounts</div>
        </div>
        <div className={`rounded-lg p-3 text-center ${data.rogue_count > 0 ? "bg-red-50" : "bg-green-50"}`}>
          <div className={`text-2xl font-bold ${data.rogue_count > 0 ? "text-red-700" : "text-green-700"}`}>{data.rogue_count}</div>
          <div className={`text-xs ${data.rogue_count > 0 ? "text-red-500" : "text-green-500"}`}>Rogue super-admins</div>
        </div>
        <div className={`rounded-lg p-3 text-center ${data.protected_account_exists ? "bg-green-50" : "bg-red-50"}`}>
          <div className={`text-2xl font-bold ${data.protected_account_exists ? "text-green-700" : "text-red-700"}`}>
            {data.protected_account_exists ? "✓" : "✗"}
          </div>
          <div className={`text-xs ${data.protected_account_exists ? "text-green-500" : "text-red-500"}`}>Protected account</div>
        </div>
      </div>

      {/* Account table */}
      <div className="overflow-x-auto rounded-md border border-slate-200">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left p-3 text-xs text-slate-500 font-medium">Email</th>
              <th className="text-left p-3 text-xs text-slate-500 font-medium">Role</th>
              <th className="text-left p-3 text-xs text-slate-500 font-medium">Status</th>
              <th className="text-left p-3 text-xs text-slate-500 font-medium">Verified</th>
              <th className="text-left p-3 text-xs text-slate-500 font-medium">Created</th>
              <th className="text-left p-3 text-xs text-slate-500 font-medium">Flags</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(data.accounts || []).map((acc) => (
              <tr key={acc.id} className={acc.is_protected ? "bg-green-50/40" : ""}>
                <td className="p-3 font-mono text-xs">
                  <span className="flex items-center gap-1.5">
                    {acc.email}
                    {acc.is_protected && <Lock className="w-3 h-3 text-green-600" title="Protected" />}
                  </span>
                </td>
                <td className="p-3">{rolePill(acc.role)}</td>
                <td className="p-3">
                  <span className={`text-xs ${acc.status === "active" ? "text-green-600" : "text-red-600"}`}>
                    {acc.status}
                  </span>
                </td>
                <td className="p-3 text-center">
                  {acc.email_verified ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500 inline" />
                  ) : (
                    <XCircle className="w-4 h-4 text-slate-300 inline" />
                  )}
                </td>
                <td className="p-3 text-xs text-slate-500">{acc.created_at}</td>
                <td className="p-3">
                  <div className="flex gap-1 flex-wrap">
                    {acc.is_protected && <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">protected</span>}
                    {acc.in_env_list  && <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">env-list</span>}
                    {acc.role === "super_admin" && !acc.is_protected && (
                      <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">ROGUE</span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-slate-400">
        Audited at {data.audited_at ? new Date(data.audited_at).toLocaleString() : "—"}
        <button onClick={fetch} className="ml-3 text-indigo-500 hover:underline">Refresh</button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section: Lockdown Panel
// ─────────────────────────────────────────────────────────────────────────────
function LockdownPanel() {
  const [dryResult, setDryResult]   = useState(null);
  const [applyResult, setApplyResult] = useState(null);
  const [loading, setLoading]       = useState(false);
  const [confirm, setConfirm]       = useState(false);

  const runDry = async () => {
    setLoading(true);
    try {
      const r = await api.post("/admin/account-security/lockdown?dry_run=true");
      setDryResult(r.data);
    } catch (e) {
      setDryResult({ error: e?.response?.data?.detail || "Failed" });
    } finally {
      setLoading(false);
    }
  };

  const runApply = async () => {
    setLoading(true);
    try {
      const r = await api.post("/admin/account-security/lockdown?dry_run=false");
      setApplyResult(r.data);
      setConfirm(false);
    } catch (e) {
      setApplyResult({ error: e?.response?.data?.detail || "Failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        The lockdown operation strips <code className="bg-slate-100 px-1 rounded">super_admin</code> from all accounts except <strong>admin@synaptiq.academy</strong>.
        Run a dry-run first to see what would be changed, then apply.
      </p>

      <div className="flex gap-3">
        <button
          onClick={runDry}
          disabled={loading}
          className="px-4 py-2 bg-slate-100 text-slate-700 text-sm rounded-lg hover:bg-slate-200 flex items-center gap-2 disabled:opacity-50"
        >
          <Eye className="w-4 h-4" /> Dry-run preview
        </button>
        <button
          onClick={() => setConfirm(true)}
          disabled={loading}
          className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 flex items-center gap-2 disabled:opacity-50"
        >
          <Zap className="w-4 h-4" /> Apply lockdown
        </button>
      </div>

      {confirm && (
        <div className="rounded-md border border-red-300 bg-red-50 p-4">
          <div className="font-semibold text-red-800 mb-2">Confirm lockdown</div>
          <p className="text-sm text-red-700 mb-3">
            This will demote ALL super_admin accounts except admin@synaptiq.academy to the "user" role.
            This action is audit-logged and irreversible via the API.
          </p>
          <div className="flex gap-2">
            <button
              onClick={runApply}
              disabled={loading}
              className="px-4 py-2 bg-red-700 text-white text-sm rounded-lg hover:bg-red-800 disabled:opacity-50"
            >
              {loading ? "Applying…" : "Yes, apply lockdown"}
            </button>
            <button
              onClick={() => setConfirm(false)}
              className="px-4 py-2 bg-white text-slate-700 text-sm rounded-lg border border-slate-200 hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {dryResult && (
        <div className="rounded-md border border-slate-200 bg-slate-50 p-4 text-sm">
          <div className="font-medium text-slate-700 mb-2">Dry-run result</div>
          {dryResult.error ? (
            <div className="text-red-600">{dryResult.error}</div>
          ) : (
            <>
              <div className="text-slate-600">Accounts that would be demoted: <strong>{dryResult.demoted_count}</strong></div>
              {dryResult.demoted_accounts?.map((a, i) => (
                <div key={i} className="font-mono text-xs text-slate-500 ml-2">{a.email} → user</div>
              ))}
              {dryResult.demoted_count === 0 && (
                <div className="text-green-700 mt-1">Platform is already locked down. No changes needed.</div>
              )}
            </>
          )}
        </div>
      )}

      {applyResult && (
        <div className={`rounded-md border p-4 text-sm ${applyResult.error ? "border-red-300 bg-red-50" : "border-green-300 bg-green-50"}`}>
          {applyResult.error ? (
            <div className="text-red-700">{applyResult.error}</div>
          ) : (
            <>
              <div className="font-medium text-green-800 mb-1">Lockdown applied successfully</div>
              <div className="text-green-700">{applyResult.demoted_count} account(s) demoted.</div>
              {applyResult.demoted_accounts?.map((a, i) => (
                <div key={i} className="font-mono text-xs text-green-600 ml-2">{a.email} → user</div>
              ))}
              <div className="text-green-700 mt-1">
                Protected account status: <strong>{applyResult.protected_status}</strong>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────
const TABS = ["overview", "audit", "lockdown", "hierarchy"];

export default function AdminAccountSecurity() {
  const [tab, setTab] = useState("overview");

  return (
    <AdministrationLayout title="Account Security" subtitle="Super-admin lockdown, privilege audit, and role hierarchy">
      {/* Quick status pill */}
      <div className="bg-slate-900 rounded-xl px-5 py-3 flex items-center gap-3 text-sm">
        <Lock className="w-4 h-4 text-green-400" />
        <span className="text-slate-300">Sole super-administrator:</span>
        <span className="font-mono text-green-400 font-semibold">admin@synaptiq.academy</span>
        <span className="text-slate-500 ml-auto text-xs">Cannot be deleted, suspended, or demoted via API</span>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize rounded-t-lg border-b-2 transition-colors
              ${tab === t
                ? "border-indigo-600 text-indigo-700 bg-indigo-50"
                : "border-transparent text-slate-500 hover:text-slate-700"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="space-y-6">
        {tab === "overview" && (
          <>
            <section>
              <h2 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Protected Account</h2>
              <ProtectedStatus />
            </section>

            <section>
              <h2 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Security Controls</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {[
                  { label: "Suspend/Ban block",       desc: "API cannot suspend or ban the protected account." },
                  { label: "Delete block",             desc: "API cannot delete the protected account." },
                  { label: "Role demotion block",      desc: "Cannot change role of the protected account via API." },
                  { label: "API super_admin grant",    desc: "super_admin role cannot be granted via any API endpoint." },
                  { label: "Hierarchy enforcement",    desc: "Admins cannot modify users at equal or higher authority level." },
                  { label: "Seed-time auto-upgrade",   desc: "On restart, the protected account is automatically corrected to super_admin if tampered with." },
                ].map((c) => (
                  <div key={c.label} className="flex gap-3 bg-white border border-slate-200 rounded-md p-3">
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="text-sm font-medium text-slate-800">{c.label}</div>
                      <div className="text-xs text-slate-500">{c.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}

        {tab === "audit" && (
          <section>
            <h2 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Privilege Audit</h2>
            <PrivilegeAudit />
          </section>
        )}

        {tab === "lockdown" && (
          <section>
            <h2 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Privilege Lockdown</h2>
            <LockdownPanel />
          </section>
        )}

        {tab === "hierarchy" && (
          <section>
            <h2 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">Role Hierarchy</h2>
            <div className="bg-white border border-slate-200 rounded-md p-5">
              <RoleHierarchy />
            </div>
            <div className="mt-4 bg-amber-50 border border-amber-200 rounded-md p-4 text-sm text-amber-800">
              <strong>API grant restrictions:</strong> The <code className="bg-amber-100 px-1 rounded">super_admin</code> role
              cannot be granted via any API endpoint. It can only be assigned through the database seed script or direct
              database intervention. All other roles in the hierarchy are API-grantable by sufficiently privileged admins.
            </div>
          </section>
        )}
      </div>
    </AdministrationLayout>
  );
}

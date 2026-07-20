/* eslint-disable */
import React, { useState, useEffect, useCallback } from "react";
import {
  Shield, ShieldCheck, ShieldAlert, Key, RefreshCw,
  CheckCircle2, XCircle, AlertTriangle, Copy, Eye, EyeOff,
  Smartphone, Lock,
} from "lucide-react";
import api from "@/lib/api";
import { NAVY, WARM, BRD } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

// ── helpers ───────────────────────────────────────────────────────────────────
function usePost(path) {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [data, setData]       = useState(null);
  const post = useCallback(async (body) => {
    setLoading(true); setError(null);
    try {
      const r = await api.post(path, body);
      setData(r.data);
      return r.data;
    } catch (e) {
      const msg = e?.response?.data?.detail || "Request failed";
      setError(msg); throw new Error(msg);
    } finally {
      setLoading(false);
    }
  }, [path]);
  return { post, loading, error, data };
}

function useFetch(path) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const fetch = useCallback(async () => {
    setLoading(true); setError(null);
    try { const r = await api.get(path); setData(r.data); }
    catch (e) { setError(e?.response?.data?.detail || "Request failed"); }
    finally { setLoading(false); }
  }, [path]);
  return { data, loading, error, fetch };
}

// ── Status card ───────────────────────────────────────────────────────────────
function MFAStatusCard({ status, onRefresh }) {
  if (!status) return null;
  const { enabled, configured_at, last_used_at, use_count, recovery_codes_remaining, enrollment_pending } = status;
  return (
    <div className={`rounded-md border p-5 ${enabled ? "border-green-300 bg-green-50" : "border-amber-300 bg-amber-50"}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {enabled
            ? <ShieldCheck className="w-6 h-6 text-green-600" />
            : <ShieldAlert className="w-6 h-6 text-amber-600" />
          }
          <span className="text-lg font-bold text-slate-800">
            {enabled ? "MFA Active" : enrollment_pending ? "Enrollment in Progress" : "MFA Not Configured"}
          </span>
        </div>
        <button onClick={onRefresh} className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>

      {enabled && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div>
            <div className="text-xs text-slate-500">Configured</div>
            <div className="font-medium text-slate-800">{configured_at ? configured_at.slice(0, 10) : "—"}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Last Used</div>
            <div className="font-medium text-slate-800">{last_used_at ? new Date(last_used_at).toLocaleString() : "—"}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Total Verifications</div>
            <div className="font-medium text-slate-800">{use_count}</div>
          </div>
          <div>
            <div className={`text-xs ${recovery_codes_remaining < 3 ? "text-red-500" : "text-slate-500"}`}>Recovery Codes Left</div>
            <div className={`font-bold ${recovery_codes_remaining < 3 ? "text-red-700" : "text-slate-800"}`}>
              {recovery_codes_remaining} / 10
            </div>
          </div>
        </div>
      )}

      {!enabled && !enrollment_pending && (
        <p className="text-sm text-amber-800">
          MFA is strongly recommended for the super-administrator account. Configure TOTP with Google Authenticator, Microsoft Authenticator, or Authy.
        </p>
      )}
    </div>
  );
}

// ── Enrollment flow ───────────────────────────────────────────────────────────
function MFAEnrollment({ onComplete }) {
  const [step, setStep]         = useState("start");   // start | scan | verify
  const [enrollData, setEnroll] = useState(null);
  const [code, setCode]         = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [copied, setCopied]     = useState(false);
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  const startEnroll = async () => {
    setLoading(true); setError("");
    try {
      const r = await api.post("/admin/mfa/enroll");
      setEnroll(r.data);
      setStep("scan");
    } catch (e) {
      setError(e?.response?.data?.detail || "Enrollment failed");
    } finally { setLoading(false); }
  };

  const confirmEnroll = async () => {
    if (code.length !== 6) { setError("Enter a 6-digit code"); return; }
    setLoading(true); setError("");
    try {
      const r = await api.post("/admin/mfa/confirm", { code });
      setRecoveryCodes(r.data.recovery_codes);
      setStep("recovery");
    } catch (e) {
      setError(e?.response?.data?.detail || "Verification failed");
    } finally { setLoading(false); }
  };

  const copyAll = () => {
    navigator.clipboard.writeText(recoveryCodes.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (step === "start") return (
    <div className="text-center py-6">
      <Smartphone className="w-12 h-12 text-indigo-500 mx-auto mb-3" />
      <h3 className="font-bold text-slate-800 mb-2">Set Up Authenticator App</h3>
      <p className="text-sm text-slate-500 mb-5 max-w-sm mx-auto">
        Use Google Authenticator, Microsoft Authenticator, or Authy to generate time-based codes.
      </p>
      <button
        onClick={startEnroll}
        disabled={loading}
        className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50"
      >
        {loading ? "Generating…" : "Start Enrollment"}
      </button>
      {error && <div className="mt-3 text-sm text-red-600">{error}</div>}
    </div>
  );

  if (step === "scan") return (
    <div className="space-y-5">
      <h3 className="font-bold text-slate-800">Step 1 — Scan QR Code</h3>
      <div className="flex gap-6 items-start">
        <div className="border-2 border-slate-200 rounded-md p-2 flex-shrink-0">
          <img
            src={`data:image/png;base64,${enrollData?.qr_png_b64}`}
            alt="TOTP QR Code"
            className="w-44 h-44"
          />
        </div>
        <div className="space-y-3 text-sm">
          <p className="text-slate-600">Scan the QR code with your authenticator app, or enter the secret manually.</p>
          <div>
            <div className="text-xs text-slate-500 mb-1">Manual entry secret</div>
            <div className="flex items-center gap-2">
              <code className="bg-slate-100 px-3 py-1.5 rounded-lg text-xs font-mono tracking-widest select-all">
                {showSecret ? enrollData?.secret : "•".repeat(32)}
              </code>
              <button onClick={() => setShowSecret(v => !v)} className="text-slate-400 hover:text-slate-600">
                {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <p className="text-slate-500 text-xs">
            Issuer: <strong>Synaptiq</strong><br />
            Account: <strong>{enrollData?.account}</strong>
          </p>
        </div>
      </div>

      <div>
        <h3 className="font-bold text-slate-800 mb-2">Step 2 — Verify Code</h3>
        <p className="text-sm text-slate-500 mb-3">Enter the 6-digit code from your authenticator to confirm enrollment.</p>
        <div className="flex gap-2">
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            placeholder="000000"
            value={code}
            onChange={e => setCode(e.target.value.replace(/\D/g, ""))}
            onKeyDown={e => e.key === "Enter" && confirmEnroll()}
            className="w-36 text-center text-xl font-mono tracking-widest border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            onClick={confirmEnroll}
            disabled={loading || code.length !== 6}
            className="px-5 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? "Verifying…" : "Verify & Activate"}
          </button>
        </div>
        {error && <div className="mt-2 text-sm text-red-600">{error}</div>}
      </div>
    </div>
  );

  if (step === "recovery") return (
    <div className="space-y-4">
      <div className="bg-green-50 border border-green-300 rounded-md p-4 flex items-start gap-3">
        <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
        <div>
          <div className="font-semibold text-green-800">MFA Successfully Activated</div>
          <div className="text-sm text-green-700">Save your recovery codes. They will not be shown again.</div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-semibold text-slate-700">Recovery Codes (10)</div>
          <button onClick={copyAll} className="text-xs text-indigo-600 hover:underline flex items-center gap-1">
            <Copy className="w-3 h-3" /> {copied ? "Copied!" : "Copy all"}
          </button>
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          {recoveryCodes.map((c, i) => (
            <code key={i} className="bg-slate-900 text-green-400 text-xs font-mono px-3 py-1.5 rounded select-all">
              {c}
            </code>
          ))}
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Each code can be used only once to log in when you cannot access your authenticator.
        </p>
      </div>

      <button
        onClick={onComplete}
        className="w-full px-4 py-2 bg-slate-900 text-white rounded-lg font-medium hover:bg-slate-800"
      >
        I've saved my recovery codes — Done
      </button>
    </div>
  );

  return null;
}

// ── Disable MFA ───────────────────────────────────────────────────────────────
function DisableMFA({ onComplete }) {
  const [code, setCode]   = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [confirm, setConfirm] = useState(false);

  const disable = async () => {
    setLoading(true); setError("");
    try {
      await api.post("/admin/mfa/disable", { code });
      onComplete();
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to disable MFA");
    } finally { setLoading(false); }
  };

  if (!confirm) return (
    <div className="rounded-md border border-red-300 bg-red-50 p-4">
      <div className="font-semibold text-red-800 mb-1">Disable MFA</div>
      <p className="text-sm text-red-700 mb-3">
        Disabling MFA removes an important layer of protection. Only do this if you are re-enrolling or replacing your authenticator device.
      </p>
      <button onClick={() => setConfirm(true)} className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700">
        Continue to disable
      </button>
    </div>
  );

  return (
    <div className="rounded-md border border-red-300 bg-red-50 p-4 space-y-3">
      <div className="font-semibold text-red-800">Confirm Disable MFA</div>
      <p className="text-sm text-red-700">Enter your current 6-digit authentication code or a recovery code:</p>
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="000000 or XXXXX-XXXXX"
          value={code}
          onChange={e => setCode(e.target.value)}
          className="flex-1 border border-red-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
        />
        <button
          onClick={disable}
          disabled={loading || !code}
          className="px-4 py-2 bg-red-700 text-white text-sm rounded-lg hover:bg-red-800 disabled:opacity-50"
        >
          {loading ? "Disabling…" : "Disable MFA"}
        </button>
      </div>
      {error && <div className="text-sm text-red-700">{error}</div>}
      <button onClick={() => setConfirm(false)} className="text-xs text-red-600 hover:underline">Cancel</button>
    </div>
  );
}

// ── Regenerate recovery codes ─────────────────────────────────────────────────
function RegenerateRecoveryCodes({ onComplete }) {
  const [code, setCode]     = useState("");
  const [newCodes, setNew]  = useState([]);
  const [error, setError]   = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const regen = async () => {
    setLoading(true); setError("");
    try {
      const r = await api.post("/admin/mfa/recovery-codes/regenerate", { code });
      setNew(r.data.recovery_codes);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed");
    } finally { setLoading(false); }
  };

  if (newCodes.length > 0) return (
    <div className="space-y-3">
      <div className="bg-amber-50 border border-amber-200 rounded-md p-3 text-sm text-amber-800">
        Old codes are now invalidated. Save these new codes.
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {newCodes.map((c, i) => (
          <code key={i} className="bg-slate-900 text-green-400 text-xs font-mono px-3 py-1.5 rounded">{c}</code>
        ))}
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => { navigator.clipboard.writeText(newCodes.join("\n")); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
          className="text-xs text-indigo-600 hover:underline"
        >
          {copied ? "Copied!" : "Copy all"}
        </button>
        <button onClick={onComplete} className="text-xs text-slate-500 hover:underline ml-auto">Done</button>
      </div>
    </div>
  );

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600">Enter your current TOTP code to regenerate all recovery codes:</p>
      <div className="flex gap-2">
        <input
          type="text"
          inputMode="numeric"
          maxLength={6}
          placeholder="000000"
          value={code}
          onChange={e => setCode(e.target.value.replace(/\D/g, ""))}
          className="w-32 text-center font-mono tracking-widest border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          onClick={regen}
          disabled={loading || code.length !== 6}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Regenerating…" : "Regenerate Codes"}
        </button>
      </div>
      {error && <div className="text-sm text-red-600">{error}</div>}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function AdminMFACenter() {
  const { data: status, loading, fetch } = useFetch("/api/admin/mfa/status");
  const [view, setView] = useState("status");  // status | enroll | disable | regen

  useEffect(() => { fetch(); }, []);

  const refresh = () => { fetch(); setView("status"); };

  return (
    <AdministrationLayout title="MFA Center" subtitle="Multi-factor authentication for admin@synaptiq.academy">
      {/* Status */}
      {loading ? (
        <div className="text-sm text-slate-400 animate-pulse">Loading MFA status…</div>
      ) : (
        <MFAStatusCard status={status} onRefresh={fetch} />
      )}

      {/* Actions */}
      {view === "status" && status && (
        <div className="flex flex-wrap gap-3">
          {!status.enabled && (
            <button
              onClick={() => setView("enroll")}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 flex items-center gap-2"
            >
              <Shield className="w-4 h-4" /> Set Up MFA
            </button>
          )}
          {status.enabled && (
            <>
              <button
                onClick={() => setView("regen")}
                className="px-4 py-2 bg-slate-100 text-slate-700 text-sm rounded-lg hover:bg-slate-200 flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" /> Regenerate Recovery Codes
              </button>
              <button
                onClick={() => setView("disable")}
                className="px-4 py-2 border border-red-300 text-red-600 text-sm rounded-lg hover:bg-red-50 flex items-center gap-2"
              >
                <Lock className="w-4 h-4" /> Disable MFA
              </button>
            </>
          )}
        </div>
      )}

      {/* Sub-panels */}
      {view === "enroll" && (
        <div className="bg-white border border-slate-200 rounded-md p-6">
          <MFAEnrollment onComplete={refresh} />
        </div>
      )}
      {view === "disable" && status?.enabled && (
        <DisableMFA onComplete={refresh} />
      )}
      {view === "regen" && status?.enabled && (
        <div className="bg-white border border-slate-200 rounded-md p-5">
          <div className="font-semibold text-slate-800 mb-3">Regenerate Recovery Codes</div>
          <RegenerateRecoveryCodes onComplete={refresh} />
        </div>
      )}

      {/* Authenticator guide */}
      <div className="bg-slate-50 border border-slate-200 rounded-md p-4 text-sm text-slate-600">
        <div className="font-medium text-slate-700 mb-2">Compatible Authenticator Apps</div>
        <div className="grid grid-cols-3 gap-2">
          {["Google Authenticator", "Microsoft Authenticator", "Authy"].map(app => (
            <div key={app} className="flex items-center gap-1.5 text-xs">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
              {app}
            </div>
          ))}
        </div>
      </div>
    </AdministrationLayout>
  );
}

/* eslint-disable */
import React, { useState, useEffect, useCallback } from "react";
import {
  Shield, ShieldCheck, ShieldAlert, Key, RefreshCw,
  CheckCircle2, XCircle, AlertTriangle, Copy, Eye, EyeOff,
  Smartphone, Lock,
} from "lucide-react";
import api from "@/lib/api";
import { NAVY, WARM, BRD, EMERALD, AMBER, CRIMSON } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, Input, Alert, Spinner } from "@/components/ds";

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
    <Card accent={enabled ? EMERALD : AMBER} padding="lg">
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
        <Button variant="link" size="sm" onClick={onRefresh}>
          <RefreshCw className="w-3 h-3" /> Refresh
        </Button>
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
    </Card>
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
      <Button variant="primary" onClick={startEnroll} loading={loading}>
        {loading ? "Generating…" : "Start Enrollment"}
      </Button>
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
        <div className="flex gap-2 items-start">
          <Input
            type="text"
            inputMode="numeric"
            maxLength={6}
            placeholder="000000"
            value={code}
            onChange={e => setCode(e.target.value.replace(/\D/g, ""))}
            onKeyDown={e => e.key === "Enter" && confirmEnroll()}
            className="w-36 text-center text-xl font-mono tracking-widest"
            wrapperClassName="!mb-0"
          />
          <Button variant="primary" onClick={confirmEnroll} disabled={loading || code.length !== 6} loading={loading}>
            {loading ? "Verifying…" : "Verify & Activate"}
          </Button>
        </div>
        {error && <div className="mt-2 text-sm text-red-600">{error}</div>}
      </div>
    </div>
  );

  if (step === "recovery") return (
    <div className="space-y-4">
      <Alert variant="success" title="MFA Successfully Activated">
        Save your recovery codes. They will not be shown again.
      </Alert>

      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-semibold text-slate-700">Recovery Codes (10)</div>
          <Button variant="link" size="sm" onClick={copyAll}>
            <Copy className="w-3 h-3" /> {copied ? "Copied!" : "Copy all"}
          </Button>
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

      <Button variant="primary" onClick={onComplete} className="w-full">
        I've saved my recovery codes — Done
      </Button>
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
    <Card accent={CRIMSON} className="bg-red-50">
      <div className="font-semibold text-red-800 mb-1">Disable MFA</div>
      <p className="text-sm text-red-700 mb-3">
        Disabling MFA removes an important layer of protection. Only do this if you are re-enrolling or replacing your authenticator device.
      </p>
      <Button variant="danger" size="sm" onClick={() => setConfirm(true)}>
        Continue to disable
      </Button>
    </Card>
  );

  return (
    <Card accent={CRIMSON} className="bg-red-50">
      <div className="space-y-3">
        <div className="font-semibold text-red-800">Confirm Disable MFA</div>
        <p className="text-sm text-red-700">Enter your current 6-digit authentication code or a recovery code:</p>
        <div className="flex gap-2 items-start">
          <Input
            type="text"
            placeholder="000000 or XXXXX-XXXXX"
            value={code}
            onChange={e => setCode(e.target.value)}
            wrapperClassName="flex-1 !mb-0"
          />
          <Button variant="danger" onClick={disable} disabled={loading || !code} loading={loading}>
            {loading ? "Disabling…" : "Disable MFA"}
          </Button>
        </div>
        {error && <div className="text-sm text-red-700">{error}</div>}
        <Button variant="link" size="sm" onClick={() => setConfirm(false)}>Cancel</Button>
      </div>
    </Card>
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
      <Alert variant="warning">
        Old codes are now invalidated. Save these new codes.
      </Alert>
      <div className="grid grid-cols-2 gap-1.5">
        {newCodes.map((c, i) => (
          <code key={i} className="bg-slate-900 text-green-400 text-xs font-mono px-3 py-1.5 rounded">{c}</code>
        ))}
      </div>
      <div className="flex gap-2 items-center">
        <Button
          variant="link"
          size="sm"
          onClick={() => { navigator.clipboard.writeText(newCodes.join("\n")); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
        >
          {copied ? "Copied!" : "Copy all"}
        </Button>
        <Button variant="link" size="sm" onClick={onComplete} className="!ml-auto">Done</Button>
      </div>
    </div>
  );

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600">Enter your current TOTP code to regenerate all recovery codes:</p>
      <div className="flex gap-2 items-start">
        <Input
          type="text"
          inputMode="numeric"
          maxLength={6}
          placeholder="000000"
          value={code}
          onChange={e => setCode(e.target.value.replace(/\D/g, ""))}
          className="w-32 text-center font-mono tracking-widest"
          wrapperClassName="!mb-0"
        />
        <Button variant="primary" onClick={regen} disabled={loading || code.length !== 6} loading={loading}>
          {loading ? "Regenerating…" : "Regenerate Codes"}
        </Button>
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
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Spinner size={16} /> Loading MFA status…
        </div>
      ) : (
        <MFAStatusCard status={status} onRefresh={fetch} />
      )}

      {/* Actions */}
      {view === "status" && status && (
        <div className="flex flex-wrap gap-3">
          {!status.enabled && (
            <Button variant="primary" onClick={() => setView("enroll")}>
              <Shield className="w-4 h-4" /> Set Up MFA
            </Button>
          )}
          {status.enabled && (
            <>
              <Button variant="subtle" onClick={() => setView("regen")}>
                <RefreshCw className="w-4 h-4" /> Regenerate Recovery Codes
              </Button>
              <Button variant="outline" className="!border-red-300 !text-red-600 hover:!bg-red-50" onClick={() => setView("disable")}>
                <Lock className="w-4 h-4" /> Disable MFA
              </Button>
            </>
          )}
        </div>
      )}

      {/* Sub-panels */}
      {view === "enroll" && (
        <Card padding="xl">
          <MFAEnrollment onComplete={refresh} />
        </Card>
      )}
      {view === "disable" && status?.enabled && (
        <DisableMFA onComplete={refresh} />
      )}
      {view === "regen" && status?.enabled && (
        <Card padding="lg">
          <div className="font-semibold text-slate-800 mb-3">Regenerate Recovery Codes</div>
          <RegenerateRecoveryCodes onComplete={refresh} />
        </Card>
      )}

      {/* Authenticator guide */}
      <Card className="bg-slate-50" padding="md">
        <div className="text-sm text-slate-600">
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
      </Card>
    </AdministrationLayout>
  );
}

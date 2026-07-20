/**
 * AccountSecurity — Security & Privacy, reached from the avatar menu / Settings nav.
 *
 * Change Password: unchanged behavior (POST /auth/change-password).
 * Two-Factor Authentication: real TOTP enroll/confirm/disable/regenerate via
 *   the new self-service /api/mfa/* endpoints (previously admin-only).
 * Active Sessions: real device sessions via /api/auth/sessions (list + revoke).
 * Security Activity: real per-user audit feed via /api/auth/security-events.
 *
 * Honest adaptations (no real data source exists for these, so they're left
 * out rather than fabricated): no "Recovery Phone" (no SMS-based MFA in this
 * backend, TOTP + recovery codes only); no city/country per session (no
 * IP-geolocation service wired up — the real IP address is shown instead);
 * password requirements list shows only the 3 rules the backend actually
 * enforces (8+ chars, one letter, one digit) — not the mockup's 5, since the
 * other 2 (uppercase, special char) aren't real server-side rules.
 */
import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Lock, ShieldCheck, Monitor, Smartphone, Activity, CheckCircle2, Circle,
  AlertTriangle, Key, LogIn, KeyRound, UserPlus, Mail, ArrowRight, Headphones,
} from "lucide-react";
import { SettingsLayout } from "@/layouts";
import { Card } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { Badge } from "@/components/ds/Badge";
import { FormField } from "@/components/ds/Form";
import { Modal } from "@/components/ds/Modal";
import { EmptyState } from "@/components/ds/EmptyState";
import { Spinner } from "@/components/ds/LoadingState";
import { NAVY, WARM, BRD, EMERALD, CRIMSON, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, TEXT_DISABLED, DANGER_BG } from "@/lib/tokens";
import { TID } from "@/lib/testIds";
import api, { formatApiError, getErrorMessage } from "@/lib/api";

function SectionHeader({ icon: Icon, title, subtitle }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 18 }}>
      <div style={{ width: 40, height: 40, borderRadius: 10, background: "rgba(15,40,71,0.08)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        <Icon size={18} color={NAVY} />
      </div>
      <div>
        <div style={{ fontSize: 15, fontWeight: 700, color: TEXT_PRIMARY }}>{title}</div>
        {subtitle && <div style={{ fontSize: 12.5, color: TEXT_SECONDARY, marginTop: 2 }}>{subtitle}</div>}
      </div>
    </div>
  );
}

function timeAgo(iso) {
  if (!iso) return "";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

const ACTIVITY_ICON = {
  "auth.login": LogIn,
  "auth.register": UserPlus,
  "auth.logout": LogIn,
  "auth.change_password": KeyRound,
  "auth.password_reset_completed": KeyRound,
  "auth.mfa_verified": ShieldCheck,
  "auth.email_verified": Mail,
  "auth.mfa.enabled": ShieldCheck,
  "auth.mfa.disabled": AlertTriangle,
};

const PW_REQUIREMENTS = [
  { key: "len", label: "At least 8 characters", test: (v) => v.length >= 8 },
  { key: "letter", label: "Contains at least one letter", test: (v) => /[A-Za-z]/.test(v) },
  { key: "digit", label: "Contains at least one number", test: (v) => /\d/.test(v) },
];

export default function AccountSecurity() {
  const [pw, setPw] = useState({ current: "", new: "", confirm: "" });
  const [pwErr, setPwErr] = useState("");
  const [pwSaving, setPwSaving] = useState(false);

  const [mfaStatus, setMfaStatus] = useState(null);
  const [sessions, setSessions] = useState(null);
  const [events, setEvents] = useState(null);

  const [mfaModal, setMfaModal] = useState(null); // "enroll" | "disable" | "regenerate" | null
  const [enrollData, setEnrollData] = useState(null);
  const [recoveryCodes, setRecoveryCodes] = useState(null);
  const [code, setCode] = useState("");
  const [mfaBusy, setMfaBusy] = useState(false);
  const [mfaErr, setMfaErr] = useState("");

  const refreshAll = async () => {
    api.get("/mfa/status").then((r) => setMfaStatus(r.data)).catch(() => {});
    api.get("/auth/sessions").then((r) => setSessions(r.data || [])).catch(() => setSessions([]));
    api.get("/auth/security-events", { params: { limit: 12 } }).then((r) => setEvents(r.data || [])).catch(() => setEvents([]));
  };
  useEffect(() => { refreshAll(); }, []);

  const changePassword = async (e) => {
    e.preventDefault();
    setPwErr("");
    if (pw.new !== pw.confirm) { setPwErr("New passwords do not match."); return; }
    if (!PW_REQUIREMENTS.every((r) => r.test(pw.new))) { setPwErr("Password does not meet the requirements below."); return; }
    setPwSaving(true);
    try {
      await api.post("/auth/change-password", { current_password: pw.current, new_password: pw.new });
      setPw({ current: "", new: "", confirm: "" });
      toast.success("Password updated.");
      refreshAll();
    } catch (e) {
      setPwErr(formatApiError(e.response?.data?.detail) || getErrorMessage(e));
    } finally {
      setPwSaving(false);
    }
  };

  const openEnroll = async () => {
    setMfaErr(""); setCode(""); setMfaModal("enroll"); setMfaBusy(true);
    try {
      const { data } = await api.post("/mfa/enroll");
      setEnrollData(data);
    } catch (e) {
      setMfaErr(getErrorMessage(e));
    } finally {
      setMfaBusy(false);
    }
  };

  const confirmEnroll = async () => {
    setMfaErr(""); setMfaBusy(true);
    try {
      const { data } = await api.post("/mfa/confirm", { code });
      setRecoveryCodes(data.recovery_codes);
    } catch (e) {
      setMfaErr(getErrorMessage(e));
    } finally {
      setMfaBusy(false);
    }
  };

  const finishEnroll = () => {
    setMfaModal(null); setEnrollData(null); setRecoveryCodes(null); setCode("");
    toast.success("Two-factor authentication enabled.");
    refreshAll();
  };

  const openDisable = () => { setMfaErr(""); setCode(""); setMfaModal("disable"); };
  const submitDisable = async () => {
    setMfaErr(""); setMfaBusy(true);
    try {
      await api.post("/mfa/disable", { code });
      setMfaModal(null); setCode("");
      toast.success("Two-factor authentication disabled.");
      refreshAll();
    } catch (e) {
      setMfaErr(getErrorMessage(e));
    } finally {
      setMfaBusy(false);
    }
  };

  const openRegenerate = () => { setMfaErr(""); setCode(""); setRecoveryCodes(null); setMfaModal("regenerate"); };
  const submitRegenerate = async () => {
    setMfaErr(""); setMfaBusy(true);
    try {
      const { data } = await api.post("/mfa/recovery-codes/regenerate", { code });
      setRecoveryCodes(data.recovery_codes);
    } catch (e) {
      setMfaErr(getErrorMessage(e));
    } finally {
      setMfaBusy(false);
    }
  };

  const revokeSession = async (sessionId) => {
    try {
      await api.post(`/auth/sessions/${sessionId}/revoke`);
      toast.success("Session revoked.");
      refreshAll();
    } catch (e) {
      toast.error(getErrorMessage(e));
    }
  };

  return (
    <SettingsLayout title="Security & Privacy" subtitle="Manage your password and security settings.">
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_280px]" style={{ gap: 20 }}>
        <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: 20 }}>

          {/* Change Password */}
          <Card padding="xl">
            <SectionHeader icon={Lock} title="Change Password" subtitle="Use a strong password to keep your account secure." />
            <form onSubmit={changePassword}>
              <div className="grid grid-cols-1 sm:grid-cols-3" style={{ gap: 14 }}>
                <FormField label="Current password" id="current-password">
                  <Input id="current-password" autoComplete="current-password" data-testid={TID.settingsCurrentPassword} type="password" required value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} />
                </FormField>
                <FormField label="New password" id="new-password">
                  <Input id="new-password" autoComplete="new-password" data-testid={TID.settingsNewPassword} type="password" required value={pw.new} onChange={(e) => setPw({ ...pw, new: e.target.value })} />
                </FormField>
                <FormField label="Confirm new password" id="confirm-new-password">
                  <Input id="confirm-new-password" autoComplete="new-password" data-testid={TID.settingsConfirmPassword} type="password" required value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} />
                </FormField>
              </div>
              {pwErr && (
                <div style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "10px 12px", background: DANGER_BG, border: `1px solid ${CRIMSON}25`, borderLeft: `3px solid ${CRIMSON}`, marginTop: 14 }}>
                  <AlertTriangle size={12} style={{ color: CRIMSON, marginTop: 1, flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: CRIMSON }}>{pwErr}</span>
                </div>
              )}
              <Button data-testid={TID.settingsChangePasswordSubmit} type="submit" loading={pwSaving} style={{ marginTop: 14 }}>
                <Key size={12} /> {pwSaving ? "Updating…" : "Update Password"}
              </Button>
            </form>
          </Card>

          {/* Two-Factor Authentication */}
          <Card padding="xl">
            <SectionHeader icon={ShieldCheck} title="Two-Factor Authentication" subtitle="Add an extra layer of security to your account." />
            {!mfaStatus ? (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0" }}>
                <Spinner size={16} /> <span style={{ fontSize: 12.5, color: TEXT_MUTED }}>Loading…</span>
              </div>
            ) : (
              <>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0", borderBottom: `1px solid ${BRD}` }}>
                    <span style={{ fontSize: 12.5, color: TEXT_SECONDARY }}>Status</span>
                    <Badge variant={mfaStatus.enabled ? "success" : "neutral"} size="sm">{mfaStatus.enabled ? "Enabled" : "Disabled"}</Badge>
                  </div>
                  {mfaStatus.enabled && (
                    <>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0", borderBottom: `1px solid ${BRD}` }}>
                        <span style={{ fontSize: 12.5, color: TEXT_SECONDARY }}>Method</span>
                        <span style={{ fontSize: 12.5, fontWeight: 600, color: TEXT_PRIMARY }}>Authenticator App (TOTP)</span>
                      </div>
                      <button onClick={openRegenerate} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0", borderBottom: `1px solid ${BRD}`, borderTop: "none", borderLeft: "none", borderRight: "none", background: "none", cursor: "pointer", width: "100%", textAlign: "left" }}>
                        <span style={{ fontSize: 12.5, color: TEXT_SECONDARY }}>Backup Codes</span>
                        <span style={{ fontSize: 12.5, fontWeight: 600, color: NAVY, display: "flex", alignItems: "center", gap: 4 }}>
                          {mfaStatus.recovery_codes_remaining} codes remaining <ArrowRight size={11} />
                        </span>
                      </button>
                    </>
                  )}
                </div>
                <div style={{ marginTop: 14 }}>
                  {mfaStatus.enabled ? (
                    <Button size="sm" variant="ghost" onClick={openDisable}>Disable 2FA</Button>
                  ) : (
                    <Button size="sm" onClick={openEnroll}>Enable 2FA</Button>
                  )}
                </div>
              </>
            )}
          </Card>

          {/* Active Sessions */}
          <Card padding="xl">
            <SectionHeader icon={Monitor} title="Active Sessions" subtitle="Manage your active sessions across devices." />
            {sessions == null ? (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0" }}>
                <Spinner size={16} /> <span style={{ fontSize: 12.5, color: TEXT_MUTED }}>Loading…</span>
              </div>
            ) : sessions.length === 0 ? (
              <EmptyState icon={<Monitor />} title="No other active sessions." size="sm" />
            ) : (
              <div style={{ display: "flex", flexDirection: "column" }}>
                {sessions.map((s, i) => {
                  const Icon = s.is_mobile ? Smartphone : Monitor;
                  return (
                    <div key={s.session_id || `${s.ip}-${s.issued_at}-${i}`} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 0", borderTop: i > 0 ? `1px solid ${BRD}` : "none" }}>
                      <div style={{ width: 34, height: 34, borderRadius: 9, background: WARM, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        <Icon size={15} color={NAVY} />
                      </div>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ fontSize: 12.5, fontWeight: 700, color: TEXT_PRIMARY }}>{s.label}</div>
                        <div style={{ fontSize: 11.5, color: TEXT_MUTED, marginTop: 1 }}>{s.ip || "Unknown IP"} · {timeAgo(s.last_seen_at)}</div>
                      </div>
                      {s.is_current ? (
                        <Badge variant="success" size="sm">Current Session</Badge>
                      ) : (
                        <Button size="sm" variant="ghost" onClick={() => revokeSession(s.session_id)}>Revoke</Button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Security Activity */}
          <Card padding="xl">
            <SectionHeader icon={Activity} title="Security Activity" subtitle="Review recent security-related activity." />
            {events == null ? (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0" }}>
                <Spinner size={16} /> <span style={{ fontSize: 12.5, color: TEXT_MUTED }}>Loading…</span>
              </div>
            ) : events.length === 0 ? (
              <EmptyState icon={<Activity />} title="No security activity recorded yet." size="sm" />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4" style={{ gap: 12 }}>
                {events.map((e) => {
                  const Icon = ACTIVITY_ICON[e.action] || Activity;
                  return (
                    <div key={e.id} style={{ padding: 12, background: WARM, borderRadius: 10 }}>
                      <div style={{ width: 26, height: 26, borderRadius: 8, background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 8 }}>
                        <Icon size={12} color={NAVY} />
                      </div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: TEXT_PRIMARY }}>{e.label}</div>
                      <div style={{ fontSize: 11, color: TEXT_MUTED, marginTop: 2 }}>{new Date(e.created_at).toLocaleString()}</div>
                      {e.ip && <div style={{ fontSize: 10.5, color: TEXT_MUTED, marginTop: 1 }}>{e.ip}</div>}
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Right rail */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card padding="lg">
            <div style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY, marginBottom: 10 }}>Password Requirements</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              {PW_REQUIREMENTS.map((r) => {
                const met = pw.new ? r.test(pw.new) : false;
                return (
                  <div key={r.key} style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 12, color: met ? TEXT_PRIMARY : TEXT_MUTED }}>
                    {met ? <CheckCircle2 size={13} color={EMERALD} /> : <Circle size={13} color={TEXT_DISABLED} />}
                    {r.label}
                  </div>
                );
              })}
            </div>
          </Card>

          <Card padding="lg">
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
              <Headphones size={13} color={NAVY} />
              <div style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY }}>Need help?</div>
            </div>
            <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: 0, lineHeight: 1.5 }}>
              Visit our Help Center or contact support.
            </p>
            <a href="/help-center" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600, color: NAVY, textDecoration: "none", marginTop: 12 }}>
              Open Help Center <ArrowRight size={11} />
            </a>
          </Card>
        </div>
      </div>

      {/* ── 2FA modals ── */}
      <Modal open={mfaModal === "enroll"} onClose={() => setMfaModal(null)} title="Enable Two-Factor Authentication" size="sm">
        {!enrollData ? (
          <p style={{ fontSize: 13, color: TEXT_SECONDARY }}>Setting up…</p>
        ) : recoveryCodes ? (
          <div>
            <p style={{ fontSize: 12.5, color: TEXT_SECONDARY, marginBottom: 10 }}>
              Save these recovery codes somewhere safe. Each can be used once if you lose access to your authenticator app.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontFamily: "monospace", fontSize: 12.5, background: WARM, borderRadius: 8, padding: 12 }}>
              {recoveryCodes.map((c) => <div key={c}>{c}</div>)}
            </div>
            <Button style={{ width: "100%", marginTop: 16 }} onClick={finishEnroll}>I've saved these codes</Button>
          </div>
        ) : (
          <div>
            <p style={{ fontSize: 12.5, color: TEXT_SECONDARY, marginBottom: 12 }}>Scan this QR code with your authenticator app, then enter the 6-digit code it shows.</p>
            <img src={`data:image/png;base64,${enrollData.qr_png_b64}`} alt="MFA QR code" style={{ width: 180, height: 180, display: "block", margin: "0 auto 12px", borderRadius: 8, border: `1px solid ${BRD}` }} />
            <div style={{ fontFamily: "monospace", fontSize: 11.5, textAlign: "center", color: TEXT_MUTED, marginBottom: 14, wordBreak: "break-all" }}>{enrollData.secret}</div>
            <FormField label="6-digit code" id="mfa-code">
              <Input id="mfa-code" autoComplete="one-time-code" inputMode="numeric" value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} placeholder="000000" />
            </FormField>
            {mfaErr && <div style={{ fontSize: 12, color: CRIMSON, marginTop: 8 }}>{mfaErr}</div>}
            <Button style={{ width: "100%", marginTop: 14 }} onClick={confirmEnroll} loading={mfaBusy}>Verify &amp; Enable</Button>
          </div>
        )}
      </Modal>

      <Modal open={mfaModal === "disable"} onClose={() => setMfaModal(null)} title="Disable Two-Factor Authentication" size="sm">
        <p style={{ fontSize: 12.5, color: TEXT_SECONDARY, marginBottom: 12 }}>Enter your current authenticator code to confirm.</p>
        <FormField label="6-digit code" id="mfa-code">
          <Input id="mfa-code" autoComplete="one-time-code" inputMode="numeric" value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} placeholder="000000" />
        </FormField>
        {mfaErr && <div style={{ fontSize: 12, color: CRIMSON, marginTop: 8 }}>{mfaErr}</div>}
        <Button variant="danger" style={{ width: "100%", marginTop: 14 }} onClick={submitDisable} loading={mfaBusy}>Disable 2FA</Button>
      </Modal>

      <Modal open={mfaModal === "regenerate"} onClose={() => setMfaModal(null)} title="Regenerate Backup Codes" size="sm">
        {recoveryCodes ? (
          <div>
            <p style={{ fontSize: 12.5, color: TEXT_SECONDARY, marginBottom: 10 }}>Your old codes no longer work. Save these new ones.</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontFamily: "monospace", fontSize: 12.5, background: WARM, borderRadius: 8, padding: 12 }}>
              {recoveryCodes.map((c) => <div key={c}>{c}</div>)}
            </div>
            <Button style={{ width: "100%", marginTop: 16 }} onClick={() => { setMfaModal(null); setRecoveryCodes(null); refreshAll(); }}>Done</Button>
          </div>
        ) : (
          <div>
            <p style={{ fontSize: 12.5, color: TEXT_SECONDARY, marginBottom: 12 }}>Enter your current authenticator code to generate a new set of backup codes.</p>
            <FormField label="6-digit code" id="mfa-code">
              <Input id="mfa-code" autoComplete="one-time-code" inputMode="numeric" value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} placeholder="000000" />
            </FormField>
            {mfaErr && <div style={{ fontSize: 12, color: CRIMSON, marginTop: 8 }}>{mfaErr}</div>}
            <Button style={{ width: "100%", marginTop: 14 }} onClick={submitRegenerate} loading={mfaBusy}>Regenerate Codes</Button>
          </div>
        )}
      </Modal>
    </SettingsLayout>
  );
}

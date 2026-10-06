import React, { useEffect, useState } from "react";
import { Cookie, ShieldCheck, Download, Trash2 } from "lucide-react";
import { LEGAL } from "../../content/legal/meta";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { SettingsGrid } from "./SettingsGrid";
import { Button } from "@/components/ds/Button";
import { Badge } from "@/components/ds/Badge";
import { List, ListItem } from "@/components/ds/List";
import { Caption, BodySmall } from "@/components/ds/Typography";
import { PreferenceCard } from "./PreferenceCard";
import {
  readConsent,
  resetConsent,
  openPreferences,
  CATEGORY_META,
  CONSENT_EVENT,
} from "@/lib/cookieConsent";

function timeAgo(iso) {
  if (!iso) return null;
  const diffMs = Date.now() - new Date(iso).getTime();
  const days = Math.round(diffMs / 86400000);
  if (days < 1) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

export function PrivacySection() {
  const [consent, setConsent] = useState(readConsent);

  useEffect(() => {
    const handler = () => setConsent(readConsent());
    window.addEventListener(CONSENT_EVENT, handler);
    return () => window.removeEventListener(CONSENT_EVENT, handler);
  }, []);

  const handleReset = () => {
    resetConsent();
    openPreferences();
  };

  return (
    <SettingsGrid>
      <PreferenceCard icon={Cookie} title="Cookie Consent" description="Your current cookie preferences">
        <List border={false} radius={0} style={{ background: "transparent" }}>
          {CATEGORY_META.map((cat) => {
            const enabled = cat.locked ? true : !!consent?.prefs?.[cat.id];
            return (
              <ListItem
                key={cat.id}
                title={cat.label}
                subtitle={cat.description}
                trailing={
                  <Badge variant={enabled ? "success" : "neutral"} size="sm">
                    {enabled ? "Enabled" : "Disabled"}
                  </Badge>
                }
                style={{ padding: "10px 0" }}
                data-testid={`privacy-consent-row-${cat.id}`}
              />
            );
          })}
        </List>
        {consent?.at && (
          <Caption style={{ marginTop: 4 }}>
            Last updated {timeAgo(consent.at)} · Decision: <span style={{ fontFamily: "monospace" }}>{consent.status}</span>
          </Caption>
        )}
      </PreferenceCard>

      <PreferenceCard icon={ShieldCheck} title="Manage Your Choice" description="Change consent or start over">
        <BodySmall style={{ margin: 0 }}>
          You can update which optional cookies Synaptiq may use at any time, or reset your
          decision entirely — the consent banner will ask again on your next action.
        </BodySmall>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 4 }}>
          <Button variant="outline" size="sm" onClick={() => openPreferences()} data-testid="privacy-manage-btn">
            Manage Cookie Preferences
          </Button>
          <Button variant="ghost" size="sm" onClick={handleReset} data-testid="privacy-reset-btn">
            Reset Cookie Preferences
          </Button>
        </div>
      </PreferenceCard>
      <YourData />
    </SettingsGrid>
  );
}

/* Export (GET /api/users/me/export) and account deletion (DELETE /api/users/me).
   What deletion does is stated exactly as implemented: the account is
   anonymised and signed out everywhere; content shared with others is not
   removed by this action. */
function YourData() {
  const { logout, user } = useAuth() || {};
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState("");
  const [confirmText, setConfirmText] = useState("");
  const [password, setPassword] = useState("");
  const hasPassword = user?.has_password !== false;
  const P = LEGAL.contact.privacy;

  const exportData = async () => {
    setBusy("export"); setMsg("");
    try {
      const { data } = await api.get("/users/me/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `synaptiq-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      setMsg("Your export has been downloaded.");
    } catch {
      setMsg(`The export couldn't be created. Please try again, or email ${P}.`);
    } finally { setBusy(""); }
  };

  const canDelete = confirmText === "DELETE" && (!hasPassword || password.length > 0);

  const deleteAccount = async () => {
    if (!canDelete) return;
    setBusy("delete"); setMsg("");
    try {
      await api.delete("/users/me", { data: { confirm: "DELETE", password: hasPassword ? password : undefined } });
      try { if (logout) await logout(); } catch { /* session already ended */ }
      window.location.href = "/";
    } catch (e) {
      const d = e?.response?.data?.detail;
      setMsg((d && (d.message || (typeof d === "string" ? d : ""))) || `Your account couldn't be deleted. Please try again, or email ${P}.`);
      setBusy("");
    }
  };

  return (
    <>
      <PreferenceCard icon={Download} title="Export my data" description="A copy of your Synaptiq data">
        <BodySmall style={{ margin: 0 }}>
          Downloads a JSON file with your profile, Terms acceptance, connections, projects, workspaces, manuscripts,
          publications, files you uploaded (details, not the files themselves), messages you sent, AI conversations,
          requests and invitations, memberships, notifications, consent records and billing records. Passwords and
          security tokens are never included. For anything else, email {P}.
        </BodySmall>
        <div style={{ marginTop: 6 }}>
          <Button variant="outline" size="sm" onClick={exportData} disabled={busy === "export"} data-testid="privacy-export-btn">
            {busy === "export" ? "Preparing…" : "Export my data"}
          </Button>
        </div>
      </PreferenceCard>

      <PreferenceCard icon={Trash2} title="Delete my account" description="Permanent">
        <BodySmall style={{ margin: 0 }}>Consider exporting your data first. When you delete your account:</BodySmall>
        <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 13, lineHeight: 1.6, color: "#334155" }} data-testid="privacy-delete-consequences">
          <li>You're signed out everywhere and can't sign in again.</li>
          <li>Your profile, AI conversations, saved searches, notes, requests, invitations and memberships are deleted.</li>
          <li>Projects, workspaces and manuscripts only you can access are deleted, with their files.</li>
          <li>Things you share with others stay with them: shared projects and workspaces pass to another member, and your messages, comments and contributions remain, shown as "Deleted user".</li>
          <li>Billing records are kept as accounting law requires, and security and audit records until their retention period ends. Unused AI Credits are lost.</li>
        </ul>
        <BodySmall style={{ margin: "6px 0 0" }}>This can't be undone.</BodySmall>
        {hasPassword ? (
          <label style={{ display: "block", marginTop: 8, fontSize: 13 }}>
            Your password
            <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}
              data-testid="privacy-delete-password"
              style={{ display: "block", marginTop: 4, width: "100%", maxWidth: 220, padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: 4 }} />
          </label>
        ) : (
          <BodySmall style={{ margin: "8px 0 0" }}>
            You sign in without a password (for example with ORCID), so we'll check that you signed in within the last 10 minutes. If not, sign out and sign in again first.
          </BodySmall>
        )}
        <label style={{ display: "block", marginTop: 8, fontSize: 13 }}>
          Type DELETE to confirm
          <input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} aria-label="Type DELETE to confirm"
            style={{ display: "block", marginTop: 4, width: "100%", maxWidth: 220, padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: 4 }} />
        </label>
        <div style={{ marginTop: 6 }}>
          <Button variant="outline" size="sm" onClick={deleteAccount} disabled={!canDelete || busy === "delete"} data-testid="privacy-delete-btn">
            {busy === "delete" ? "Deleting…" : "Delete my account"}
          </Button>
        </div>
      </PreferenceCard>
      {msg && <p role="status" style={{ fontSize: 13, color: "#334155" }}>{msg}</p>}
    </>
  );
}

export default PrivacySection;

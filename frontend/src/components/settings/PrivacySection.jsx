import React, { useEffect, useState } from "react";
import { Cookie, ShieldCheck, Download, Trash2 } from "lucide-react";
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
  const { logout } = useAuth() || {};
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState("");
  const [confirmText, setConfirmText] = useState("");

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
      setMsg("The export couldn't be created. Please try again, or email privacy@synaptiq.academy.");
    } finally { setBusy(""); }
  };

  const deleteAccount = async () => {
    if (confirmText !== "DELETE") return;
    setBusy("delete"); setMsg("");
    try {
      await api.delete("/users/me");
      if (logout) await logout();
      window.location.href = "/";
    } catch {
      setMsg("Your account couldn't be deleted. Please try again, or email privacy@synaptiq.academy.");
      setBusy("");
    }
  };

  return (
    <>
      <PreferenceCard icon={Download} title="Export my data" description="A copy of your Synaptiq data">
        <BodySmall style={{ margin: 0 }}>
          Downloads a JSON file with your profile, your projects and workspaces, manuscripts you author, your
          most recent messages and notifications, and the list of files you uploaded. For anything not included,
          email privacy@synaptiq.academy.
        </BodySmall>
        <div style={{ marginTop: 6 }}>
          <Button variant="outline" size="sm" onClick={exportData} disabled={busy === "export"} data-testid="privacy-export-btn">
            {busy === "export" ? "Preparing…" : "Export my data"}
          </Button>
        </div>
      </PreferenceCard>

      <PreferenceCard icon={Trash2} title="Delete my account" description="Permanent">
        <BodySmall style={{ margin: 0 }}>
          Your name, email, profile details and ORCID link are removed and you are signed out everywhere. Content you
          shared with others, such as messages, projects and co-authored manuscripts, stays with them. This can't be undone.
        </BodySmall>
        <label style={{ display: "block", marginTop: 8, fontSize: 13 }}>
          Type DELETE to confirm
          <input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} aria-label="Type DELETE to confirm"
            style={{ display: "block", marginTop: 4, width: "100%", maxWidth: 220, padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: 4 }} />
        </label>
        <div style={{ marginTop: 6 }}>
          <Button variant="outline" size="sm" onClick={deleteAccount} disabled={confirmText !== "DELETE" || busy === "delete"} data-testid="privacy-delete-btn">
            {busy === "delete" ? "Deleting…" : "Delete my account"}
          </Button>
        </div>
      </PreferenceCard>
      {msg && <p role="status" style={{ fontSize: 13, color: "#334155" }}>{msg}</p>}
    </>
  );
}

export default PrivacySection;

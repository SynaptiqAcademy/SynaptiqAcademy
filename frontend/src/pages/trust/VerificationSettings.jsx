/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Save } from "lucide-react";
import { ResearchLayout } from "@/layouts";
import { Button, List, ListItem, Switch, LoadingOverlay } from "@/components/ds";

const API = "/api/trust";

export default function VerificationSettings() {
  const [settings, setSettings] = useState({
    is_public: false,
    notify_verification: true,
    notify_badge: true,
    notify_score_change: true,
    notify_request_reviewed: true,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(API + "/settings", { credentials: "include" })
      .then(r => r.json())
      .then(d => { setSettings(d || {}); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    await fetch(API + "/settings", {
      method: "PATCH", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const ROWS = [
    { key: "is_public",               label: "Public Passport",        desc: "Allow anyone with the link to view your Academic Passport" },
    { key: "notify_verification",      label: "Verification Alerts",    desc: "Notify when a verification check completes" },
    { key: "notify_badge",             label: "Badge Notifications",    desc: "Notify when you earn a new badge" },
    { key: "notify_score_change",      label: "Trust Score Updates",    desc: "Notify when your trust score changes significantly" },
    { key: "notify_request_reviewed",  label: "Request Reviews",        desc: "Notify when an admin reviews your verification request" },
  ];

  return (
    <ResearchLayout
      title="Trust Settings"
      subtitle="Manage your verification preferences and privacy"
      actions={
        <Button onClick={save} disabled={saving}>
          <Save size={14} />
          {saving ? "Saving…" : saved ? "Saved!" : "Save Settings"}
        </Button>
      }
    >
      <div style={{ maxWidth: 640, margin: "0 auto" }}>

        {loading ? (
          <LoadingOverlay text="Loading…" />
        ) : (
          <List>
            {ROWS.map((row) => (
              <ListItem
                key={row.key}
                title={row.label}
                subtitle={row.desc}
                trailing={
                  <Switch
                    checked={!!settings[row.key]}
                    onChange={val => setSettings(p => ({ ...p, [row.key]: val }))}
                  />
                }
              />
            ))}
          </List>
        )}
      </div>
    </ResearchLayout>
  );
}

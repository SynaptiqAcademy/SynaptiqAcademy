import React, { useState, useEffect } from "react";
import axios from "axios";
import { Save, CheckCircle } from "lucide-react";
import { NAVY, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Tag, Button, Switch, FormSelect, LoadingOverlay } from "@/components/ds";

const DISCOVERY_CATEGORIES = [
  { key: "collaborator", label: "Collaborators" },
  { key: "mentor", label: "Mentors" },
  { key: "community", label: "Communities" },
  { key: "group", label: "Research Groups" },
  { key: "event", label: "Events" },
  { key: "collaboration", label: "Open Collaborations" },
  { key: "institution", label: "Institutions" },
  { key: "conference", label: "Conferences" },
];

export default function NetworkSettings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setLoading(true);
    axios.get("/api/network/settings").then(r => setSettings(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      await axios.put("/api/network/settings", settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch { } finally { setSaving(false); }
  };

  const toggle = key => setSettings(s => ({ ...s, [key]: !s[key] }));
  const toggleCategory = cat => setSettings(s => {
    const cats = s.discovery_categories || [];
    return { ...s, discovery_categories: cats.includes(cat) ? cats.filter(c => c !== cat) : [...cats, cat] };
  });

  if (loading) return <LoadingOverlay text="Loading settings…" />;
  if (!settings) return null;

  return (
    <ResearchLayout
      title="Network Settings"
      actions={saved ? <Badge variant="success"><CheckCircle size={14} />Saved</Badge> : null}
    >

      {/* Privacy */}
      <Card padding="lg" style={{ marginBottom: 16 }}>
        <h3 style={{ margin: "0 0 16px", fontSize: 14, fontWeight: 700, color: NAVY }}>Privacy & Visibility</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {[
            { key: "show_in_discovery", label: "Show my profile in researcher discovery", desc: "Other researchers can find you by name, expertise, and institution." },
            { key: "allow_mentorship_requests", label: "Allow mentorship requests", desc: "Other researchers can send you mentorship requests if you're a mentor." },
            { key: "allow_collaboration_requests", label: "Allow collaboration requests", desc: "Others can apply to your open collaboration opportunities." },
          ].map(({ key, label, desc }) => (
            <Switch
              key={key}
              label={label}
              hint={desc}
              checked={!!settings[key]}
              onChange={() => toggle(key)}
            />
          ))}
          <FormSelect
            label="Profile Visibility"
            value={settings.profile_visibility}
            onChange={e => setSettings(s => ({ ...s, profile_visibility: e.target.value }))}
          >
            <option value="public">Public — visible to all researchers</option>
            <option value="network">Network — visible to group/community members only</option>
            <option value="private">Private — only visible to you</option>
          </FormSelect>
        </div>
      </Card>

      {/* Notifications */}
      <Card padding="lg" style={{ marginBottom: 16 }}>
        <h3 style={{ margin: "0 0 16px", fontSize: 14, fontWeight: 700, color: NAVY }}>Notifications</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {[
            { key: "email_on_match", label: "Email on new matches", desc: "Receive email when the AI identifies strong collaborator matches." },
            { key: "email_on_request", label: "Email on collaboration/mentorship requests", desc: "Receive email when someone applies to your opportunities." },
          ].map(({ key, label, desc }) => (
            <Switch
              key={key}
              label={label}
              hint={desc}
              checked={!!settings[key]}
              onChange={() => toggle(key)}
            />
          ))}
          <FormSelect
            label="Notification Frequency"
            value={settings.notification_frequency}
            onChange={e => setSettings(s => ({ ...s, notification_frequency: e.target.value }))}
          >
            <option value="realtime">Real-time</option>
            <option value="daily">Daily digest</option>
            <option value="weekly">Weekly digest</option>
            <option value="never">Never</option>
          </FormSelect>
        </div>
      </Card>

      {/* Discovery preferences */}
      <Card padding="lg" style={{ marginBottom: 24 }}>
        <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 700, color: NAVY }}>AI Discovery Preferences</h3>
        <p style={{ margin: "0 0 12px", fontSize: 12, color: TEXT_SECONDARY }}>Choose which types of recommendations the AI generates for you.</p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {DISCOVERY_CATEGORIES.map(({ key, label }) => {
            const active = (settings.discovery_categories || []).includes(key);
            return (
              <Tag key={key} color={active ? ACCENT : undefined} onClick={() => toggleCategory(key)}>
                {label}
              </Tag>
            );
          })}
        </div>
      </Card>

      <Button variant="primary" onClick={handleSave} disabled={saving} loading={saving}>
        <Save size={16} />{saving ? "Saving…" : "Save Settings"}
      </Button>
    </ResearchLayout>
  );
}

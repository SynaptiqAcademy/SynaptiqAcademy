import React, { useEffect, useState } from "react";
import { Cookie, ShieldCheck } from "lucide-react";
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
    </SettingsGrid>
  );
}

export default PrivacySection;

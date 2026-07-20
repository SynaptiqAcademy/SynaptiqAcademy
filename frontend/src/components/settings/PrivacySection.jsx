import React, { useEffect, useState } from "react";
import { Cookie, ShieldCheck } from "lucide-react";
import { SettingsGrid } from "./SettingsGrid";
import { Button } from "@/components/ds/Button";
import { PreferenceCard } from "./PreferenceCard";
import { TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, EMERALD, BRD } from "@/lib/tokens";
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
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {CATEGORY_META.map((cat, i) => {
            const enabled = cat.locked ? true : !!consent?.prefs?.[cat.id];
            return (
              <div
                key={cat.id}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  paddingBottom: i < CATEGORY_META.length - 1 ? 10 : 0,
                  borderBottom: i < CATEGORY_META.length - 1 ? `1px solid ${BRD}` : "none",
                }}
                data-testid={`privacy-consent-row-${cat.id}`}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: TEXT_PRIMARY }}>{cat.label}</div>
                  <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 2 }}>{cat.description}</div>
                </div>
                <span
                  style={{
                    fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em",
                    color: enabled ? EMERALD : TEXT_MUTED, flexShrink: 0, marginLeft: 12,
                  }}
                >
                  {enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
            );
          })}
        </div>
        {consent?.at && (
          <p style={{ fontSize: 11, color: TEXT_MUTED, margin: "4px 0 0" }}>
            Last updated {timeAgo(consent.at)} · Decision: <span style={{ fontFamily: "monospace" }}>{consent.status}</span>
          </p>
        )}
      </PreferenceCard>

      <PreferenceCard icon={ShieldCheck} title="Manage Your Choice" description="Change consent or start over">
        <p style={{ fontSize: 12, color: TEXT_SECONDARY, lineHeight: 1.6, margin: 0 }}>
          You can update which optional cookies Synaptiq may use at any time, or reset your
          decision entirely — the consent banner will ask again on your next action.
        </p>
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

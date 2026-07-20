import React from "react";
import { toast } from "sonner";
import { FlaskConical, Code2 } from "lucide-react";
import { SettingsGrid } from "./SettingsGrid";
import { Button } from "@/components/ds/Button";
import { PreferenceCard } from "./PreferenceCard";
import { PreferenceRow } from "./PreferenceRow";
import { useAuth } from "@/contexts/AuthContext";

export function LabsSection({ prefs, setPref }) {
  const { user } = useAuth();

  const copyDebugInfo = () => {
    const info = {
      user_id: user?.id,
      plan: user?.plan_code,
      preferences: prefs,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
    };
    navigator.clipboard.writeText(JSON.stringify(info, null, 2));
    toast.success("Debug info copied to clipboard");
  };

  return (
    <SettingsGrid>
      <PreferenceCard icon={FlaskConical} title="Experimental Features" description="Early access to features still being refined">
        <PreferenceRow label="Experimental Features" value={prefs.experimentalFeatures} onChange={(v) => setPref("experimentalFeatures", v, "Experimental Features")} />
        <PreferenceRow label="Beta AI Features" value={prefs.betaAiFeatures} onChange={(v) => setPref("betaAiFeatures", v, "Beta AI Features")} />
        <PreferenceRow label="Preview Components" value={prefs.previewComponents} onChange={(v) => setPref("previewComponents", v, "Preview Components")} />
      </PreferenceCard>

      <PreferenceCard icon={Code2} title="Developer Options">
        <PreferenceRow
          label="Developer Options"
          hint="Reveals a Copy Debug Info action below"
          value={prefs.developerOptions}
          onChange={(v) => setPref("developerOptions", v, "Developer Options")}
        />
        {prefs.developerOptions && (
          <Button size="sm" variant="ghost" onClick={copyDebugInfo}>Copy Debug Info</Button>
        )}
      </PreferenceCard>
    </SettingsGrid>
  );
}

export default LabsSection;

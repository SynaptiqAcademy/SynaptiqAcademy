/**
 * Settings — Application Preferences Center.
 *
 * Configures how Synaptiq behaves (theme, language, AI defaults, workspace
 * defaults, editor, keyboard, accessibility, labs). Account management
 * (identity, billing, security, notifications) lives in the Avatar menu —
 * see frontend/src/components/layout/TopBar.jsx.
 */
import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ds/Button";
import { PageLayout } from "@/components/ds/PageLayout";
import { usePreferences } from "@/hooks/usePreferences";
import { SettingsNav, CATEGORIES } from "@/components/settings/SettingsNav";
import { SettingsSidebar } from "@/components/settings/SettingsSidebar";
import { GeneralSection } from "@/components/settings/GeneralSection";
import { AppearanceSection } from "@/components/settings/AppearanceSection";
import { LanguageRegionSection } from "@/components/settings/LanguageRegionSection";
import { AIPreferencesSection } from "@/components/settings/AIPreferencesSection";
import { WorkspaceSection } from "@/components/settings/WorkspaceSection";
import { EditorSection } from "@/components/settings/EditorSection";
import { KeyboardSection } from "@/components/settings/KeyboardSection";
import { AccessibilitySection } from "@/components/settings/AccessibilitySection";
import { LabsSection } from "@/components/settings/LabsSection";
import { PrivacySection } from "@/components/settings/PrivacySection";

const SECTION_COMPONENTS = {
  general: GeneralSection,
  appearance: AppearanceSection,
  languageRegion: LanguageRegionSection,
  ai: AIPreferencesSection,
  workspace: WorkspaceSection,
  editor: EditorSection,
  keyboard: KeyboardSection,
  accessibility: AccessibilitySection,
  labs: LabsSection,
  privacy: PrivacySection,
};

export default function Settings() {
  const loc = useLocation();
  const navigate = useNavigate();
  const { prefs, setPref, resetAll, recentChanges } = usePreferences();

  const initialCategory = useMemo(() => {
    const sp = new URLSearchParams(loc.search);
    const section = sp.get("section");
    return CATEGORIES.some((c) => c.id === section) ? section : "general";
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const [activeCategory, setActiveCategory] = useState(initialCategory);

  useEffect(() => {
    navigate(`/settings?section=${activeCategory}`, { replace: true });
  }, [activeCategory]); // eslint-disable-line react-hooks/exhaustive-deps

  const ActiveSection = SECTION_COMPONENTS[activeCategory];
  const activeMeta = CATEGORIES.find((c) => c.id === activeCategory);

  return (
    <PageLayout
      title={activeMeta?.label}
      subtitle="Configure how Synaptiq behaves. These preferences customize your experience across the platform."
      actions={
        <Button variant="ghost" size="sm" onClick={resetAll}>
          <RotateCcw size={12} /> Reset all preferences
        </Button>
      }
    >
      {/* Three-column layout — stacks vertically below the lg breakpoint */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-start" style={{ gap: 24 }}>
        <SettingsNav activeCategory={activeCategory} onSelect={setActiveCategory} />

        <div style={{ flex: 1, minWidth: 0 }}>
          {ActiveSection && (
            <ActiveSection prefs={prefs} setPref={setPref} recentChanges={recentChanges} />
          )}
        </div>

        <SettingsSidebar activeCategory={activeCategory} />
      </div>
    </PageLayout>
  );
}

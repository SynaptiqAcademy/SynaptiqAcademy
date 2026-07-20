import React from "react";
import { ResearchImpactSection } from "@/components/passport/ResearchImpactSection";
import { ResearchAreasCard } from "@/components/passport/ResearchAreasCard";
import { TopPublicationsCard } from "@/components/passport/TopPublicationsCard";
import { ProjectsCollabsFunding } from "@/components/passport/ProjectsCollabsFunding";
import { PublicationsPanel } from "@/components/passport/PublicationsPanel";
import { ResearchIntegrationsCard } from "@/components/settings/ResearchIntegrationsCard";
import { SectionShell } from "@/components/passport/PassportUI";

/**
 * ResearchTab — Publications, Projects, Grants, Research Areas, Citation
 * Metrics, and Research Integrations (ORCID/OpenAlex), all as premium cards
 * in one page — no further sub-navigation. The Academic/Research Timeline
 * lives on the Portfolio tab (same real component, shown once).
 */
export function ResearchTab({
  profile, impact, completion, pubs, pubsLoading, pubQuery, onQuery, onRefresh,
  projects, collaborations,
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <ResearchImpactSection impact={impact} completion={completion} />

      <div className="grid grid-cols-1 lg:grid-cols-2" style={{ gap: 20 }}>
        <ResearchAreasCard profile={profile} />
        <TopPublicationsCard pubs={pubs} loading={pubsLoading} />
      </div>

      <ProjectsCollabsFunding
        projects={projects}
        collaborations={collaborations}
        fundings={profile.orcid_fundings || []}
      />

      <PublicationsPanel
        pubs={pubs}
        loading={pubsLoading}
        query={pubQuery}
        onQuery={onQuery}
        onRefresh={onRefresh}
      />

      <SectionShell title="Research Integrations" subtitle="Connect ORCID and OpenAlex to auto-sync your identity and citations">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <ResearchIntegrationsCard />
        </div>
      </SectionShell>
    </div>
  );
}

export default ResearchTab;

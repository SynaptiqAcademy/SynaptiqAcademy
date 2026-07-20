import React from "react";
import { Link } from "react-router-dom";
import { FolderOpen, Users2, DollarSign, ArrowRight } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { EmptyState } from "@/components/ds/EmptyState";
import { TYPE, BRD, TEXT_MUTED, TEXT_PRIMARY, NAVY } from "@/lib/tokens";

function MiniList({ icon: Icon, title, viewAllTo, items, empty, renderItem }) {
  return (
    <Card padding="lg" style={{ flex: 1, minWidth: 260 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <span style={{ fontSize: 12.5, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
          <Icon size={13} style={{ color: NAVY }} /> {title}
        </span>
        <Link to={viewAllTo} style={{ fontSize: 11, color: TEXT_MUTED, display: "flex", alignItems: "center", gap: 3, textDecoration: "none" }}>
          View all <ArrowRight size={10} />
        </Link>
      </div>
      {items.length === 0 ? (
        <p style={{ fontSize: 12, color: TEXT_MUTED, margin: 0 }}>{empty}</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {items.slice(0, 5).map(renderItem)}
        </div>
      )}
    </Card>
  );
}

/**
 * ProjectsCollabsFunding — compact summaries of the user's projects,
 * active collaborations, and research funding (ORCID-sourced).
 */
export function ProjectsCollabsFunding({ projects = [], collaborations = [], fundings = [] }) {
  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
      <MiniList
        icon={FolderOpen}
        title="Projects"
        viewAllTo="/projects"
        items={projects}
        empty="No active projects yet."
        renderItem={(p) => (
          <div key={p.id} style={{ fontSize: 12.5, color: TEXT_PRIMARY, paddingBottom: 8, borderBottom: `1px solid ${BRD}` }}>{p.title}</div>
        )}
      />
      <MiniList
        icon={Users2}
        title="Collaborations"
        viewAllTo="/collaborations"
        items={collaborations}
        empty="No active collaborations yet."
        renderItem={(c) => (
          <div key={c.id} style={{ fontSize: 12.5, color: TEXT_PRIMARY, paddingBottom: 8, borderBottom: `1px solid ${BRD}` }}>{c.title || c.name}</div>
        )}
      />
      <MiniList
        icon={DollarSign}
        title="Funding"
        viewAllTo="/funding"
        items={fundings}
        empty="No funding records yet — sync ORCID to import."
        renderItem={(f, i) => (
          <div key={i} style={{ fontSize: 12.5, color: TEXT_PRIMARY, paddingBottom: 8, borderBottom: `1px solid ${BRD}` }}>
            {f.title || "Funding award"}
            {f.organization && <span style={{ color: TEXT_MUTED }}> · {f.organization}</span>}
          </div>
        )}
      />
    </div>
  );
}

export default ProjectsCollabsFunding;

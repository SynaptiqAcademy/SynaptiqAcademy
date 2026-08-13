import React from "react";
import { Link } from "react-router-dom";
import { ResearchLayout } from "@/layouts";
import { Button, Card } from "@/components/ds";
import {
  FolderOpen, LayoutGrid, Archive, Users, FileText, Database,
  Microscope, GitBranch, CheckSquare, BookOpen, TrendingUp, Award,
  ArrowRight, FlaskConical,
} from "lucide-react";

const MODULES = [
  { icon: FolderOpen,  label: "Research Projects",  desc: "Organise work into structured projects with milestones.", to: "/projects",          action: "Open projects" },
  { icon: LayoutGrid,  label: "Workspaces",         desc: "Shared environments for writing, thinking and planning.", to: "/workspaces",        action: "Open workspaces" },
  { icon: Archive,     label: "Repository",         desc: "Store files and datasets with full version control.",     to: "/repository",        action: "Open repository" },
  { icon: Users,       label: "Collaborations",     desc: "Research partnerships across institutions and borders.",  to: "/collaborations",    action: "Find collaborators" },
  { icon: FileText,    label: "Manuscripts",        desc: "Write from first draft through to published paper.",      to: "/manuscripts",       action: "Open manuscripts" },
  { icon: Microscope,  label: "Protocols",          desc: "Document reproducible research procedures.",               to: "/sie/planning",      action: "Plan protocol" },
  { icon: GitBranch,   label: "Version History",    desc: "Every change tracked. Nothing lost.",                      to: "/repository",        action: "View history" },
  { icon: CheckSquare, label: "Reviewer Workspace",  desc: "Structured peer review with tracked annotations.",        to: "/manuscript-review", action: "Open reviews" },
  { icon: BookOpen,    label: "Publishing",         desc: "Journal matching and submission pipeline management.",    to: "/journal-matching",  action: "Match journals" },
  { icon: TrendingUp,  label: "Impact",             desc: "Citations, H-index and influence metrics in one view.",   to: "/research-impact",   action: "View impact" },
  { icon: Award,       label: "Funding",            desc: "Grants discovery and application management.",           to: "/grant-hub",         action: "Find funding" },
  { icon: Database,    label: "Datasets",           desc: "Upload, curate and share research data.",                 to: "/repository",        action: "Open datasets" },
];

export default function ResearchCommandCenter() {
  return (
    <ResearchLayout
      title="Research"
      subtitle="One workspace for every stage of your research — from first idea to measured impact."
      icon={<FlaskConical size={15} strokeWidth={1.5} style={{ color: "#0F2847" }} />}
      actions={
        <>
          <Button as={Link} to="/projects" variant="hero" size="sm">
            Start a Project <ArrowRight size={13} />
          </Button>
          <Button as={Link} to="/workspaces" variant="hero" size="sm">
            Open Workspace
          </Button>
        </>
      }
    >
      <section>
        <div className="overline mb-4">Research Modules</div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
          {MODULES.map(({ label, to, icon: Icon, desc, action }) => (
            <Card key={label + to} to={to} padding="xl" className="group">
              <Icon size={20} strokeWidth={1.5} className="text-[#0F2847] mb-4" />
              <h3 className="font-serif text-lg text-slate-900 mb-2">{label}</h3>
              <p className="text-sm text-slate-600 leading-relaxed">{desc}</p>
              <div className="mt-4 flex items-center gap-1 text-xs text-[#0F2847] opacity-0 group-hover:opacity-100 transition-opacity">
                {action} <ArrowRight size={11} strokeWidth={1.5} />
              </div>
            </Card>
          ))}
        </div>
      </section>
    </ResearchLayout>
  );
}

import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, GraduationCap } from "lucide-react";
import { SectionShell } from "@/components/passport/PassportUI";
import { StatCard } from "@/components/ds/StatCard";
import { EmptyState } from "@/components/ds/EmptyState";
import { Button } from "@/components/ds/Button";

/**
 * TeachingTab — real teaching-analytics totals (GET /teaching-analytics/overview)
 * plus real teaching reputation. "Courses" / "Students" are not modeled in the
 * backend for this platform (this is a workspace/lesson-based teaching product,
 * not an LMS with enrolled students) — Lessons / Assessments / Workspaces /
 * Portfolio Items / AI Sessions / Collaborations are the real equivalents shown
 * here instead, deliberately not fabricated to match the requested labels.
 */
export function TeachingTab({ teachingStats }) {
  if (!teachingStats) {
    return (
      <SectionShell title="Teaching">
        <EmptyState icon={<GraduationCap />} title="No teaching activity yet" description="Create a lesson or workspace to see your teaching analytics here." />
      </SectionShell>
    );
  }

  const totals = teachingStats.totals || {};
  const rep = teachingStats.reputation || {};

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <SectionShell
        title="Teaching Overview"
        subtitle="Real activity across your teaching workspaces, lessons, and assessments"
        action={
          <Link to="/teaching/analytics">
            <Button as="span" size="sm" variant="ghost">Full Teaching Analytics <ArrowRight size={12} /></Button>
          </Link>
        }
      >
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6" style={{ gap: 12 }}>
          <StatCard label="Lessons" value={totals.lessons ?? 0} />
          <StatCard label="Assessments" value={totals.assessments ?? 0} />
          <StatCard label="Workspaces" value={totals.workspaces ?? 0} />
          <StatCard label="Portfolio Items" value={totals.portfolio_items ?? 0} />
          <StatCard label="AI Sessions" value={totals.ai_sessions ?? 0} />
          <StatCard label="Collaborations" value={totals.collaborations ?? 0} highlight />
        </div>
      </SectionShell>

      <SectionShell title="Teaching Reputation" subtitle="Computed from real teaching platform activity">
        <div className="grid grid-cols-1 sm:grid-cols-3" style={{ gap: 12 }}>
          <StatCard label="Teaching Score" value={rep.teaching_score ?? 0} highlight />
          <StatCard label="Community Score" value={rep.community_score ?? 0} />
          <StatCard label="Overall" value={rep.overall ?? 0} />
        </div>
      </SectionShell>

      <SectionShell title="Teaching Workspace &amp; Portfolio">
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link to="/teaching"><Button as="span" variant="ghost" size="sm">Teaching Workspaces</Button></Link>
          <Link to="/teaching/portfolio"><Button as="span" variant="ghost" size="sm">Teaching Portfolio</Button></Link>
          <Link to="/teaching/analytics"><Button as="span" variant="ghost" size="sm">Teaching Analytics</Button></Link>
        </div>
      </SectionShell>
    </div>
  );
}

export default TeachingTab;

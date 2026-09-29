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
 *
 * P1 Phase 7C4.1 §14: a response with every total at 0 used to still render
 * a 9-box grid of zeroes ("an empty analytics graveyard"). Now treated the
 * same as no response at all — one useful empty state instead.
 */
export function TeachingTab({ teachingStats }) {
  const totals = teachingStats?.totals || {};
  const rep = teachingStats?.reputation || {};
  const hasActivity = Object.values(totals).some((v) => v > 0) || Object.values(rep).some((v) => v > 0);

  if (!teachingStats || !hasActivity) {
    return (
      <SectionShell title="Teaching">
        <EmptyState
          icon={<GraduationCap />}
          title="Your teaching identity starts here"
          description="Create a lesson, assessment, or teaching workspace and it becomes part of your Passport automatically — no manual entry needed."
          action={
            <Link to="/teaching">
              <Button as="span" size="sm">Go to Teaching Workspaces</Button>
            </Link>
          }
        />
      </SectionShell>
    );
  }

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

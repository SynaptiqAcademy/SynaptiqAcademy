/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  GraduationCap, BookOpen, ClipboardCheck, Award, FolderOpen, ArrowRight,
  BarChart2, FlaskConical, Users, Archive, FileText, Target, Network,
  Building2, Lightbulb, BookMarked, Layers, Globe, ChevronRight,
} from "lucide-react";
import api from "../../lib/api";
import { useAuth } from "../../contexts/AuthContext";
import { NAVY } from "@/lib/tokens";
import { EmptyState } from "../../components/ds/EmptyState";
import { Spinner } from "../../components/ds/LoadingState";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { List, ListHeader, ListItem } from "@/components/ds/List";
import { ResearchLayout } from "@/layouts";

const MODULES = [
  {
    label:       "Lesson Planner",
    to:          "/teaching/lesson-planner",
    icon:        BookOpen,
    description: "Build structured lesson plans with AI assistance — objectives, activities, differentiation, and timelines.",
    action:      "Plan lessons",
  },
  {
    label:       "Assessment Builder",
    to:          "/teaching/assessment-builder",
    icon:        ClipboardCheck,
    description: "Design quizzes, exams, rubrics, and assignments aligned to your learning objectives.",
    action:      "Build assessments",
  },
  {
    label:       "Teaching Portfolio",
    to:          "/teaching/portfolio",
    icon:        Award,
    description: "Document your teaching philosophy, courses, achievements, and evidence of impact.",
    action:      "Build portfolio",
  },
  {
    label:       "Teaching Workspaces",
    to:          "/teaching/workspaces",
    icon:        FolderOpen,
    description: "Course-level collaborative spaces with an AI teaching assistant for pedagogy support.",
    action:      "Open workspaces",
  },
  {
    label:       "Teaching Analytics",
    to:          "/teaching/analytics",
    icon:        BarChart2,
    description: "Intelligence from your real teaching activity — lessons, assessments, workspaces, AI usage, reputation, and growth insights.",
    action:      "View analytics",
  },
];

function StatPill({ label, value, loading }) {
  return (
    <div className="text-center">
      <div className="font-serif text-3xl text-slate-900">{loading ? "—" : value}</div>
      <div className="overline mt-1 text-xs">{label}</div>
    </div>
  );
}

export default function TeachingHub() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [recentLessons, setRecentLessons] = useState([]);
  const [recentAssessments, setRecentAssessments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes, lessonsRes, assessmentsRes] = await Promise.all([
          api.get("/teaching/stats"),
          api.get("/teaching/lessons"),
          api.get("/teaching/assessments"),
        ]);
        setStats(statsRes.data);
        setRecentLessons((lessonsRes.data || []).slice(0, 3));
        setRecentAssessments((assessmentsRes.data || []).slice(0, 3));
      } catch (_) {
        // Stats unavailable — non-fatal
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const firstName = user?.full_name?.split(" ")[0] || "there";

  return (
    <ResearchLayout
      title={`Welcome, ${firstName}`}
      subtitle="Your central workspace for teaching — lesson planning, assessment design, portfolio building, and AI-assisted pedagogy support."
      icon={GraduationCap}
    >
      {/* Stats bar */}
      <div className="grid grid-cols-4 gap-6 max-w-lg mb-8">
        <StatPill label="Lessons"     value={stats?.lessons}         loading={loading} />
        <StatPill label="Assessments" value={stats?.assessments}     loading={loading} />
        <StatPill label="Portfolio"   value={stats?.portfolio_items} loading={loading} />
        <StatPill label="Workspaces"  value={stats?.workspaces}      loading={loading} />
      </div>

      {/* Module cards */}
      <section>
        <div className="overline mb-4">Teaching Modules</div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
          {MODULES.map(({ label, to, icon: Icon, description, action }) => (
            <Card key={to} to={to} padding="xl" className="group">
              <Icon size={20} strokeWidth={1.5} className="text-[#0F2847] mb-4" />
              <h3 className="font-serif text-lg text-slate-900 mb-2">{label}</h3>
              <p className="text-sm text-slate-600 leading-relaxed">{description}</p>
              <div className="mt-4 flex items-center gap-1 text-xs text-[#0F2847] opacity-0 group-hover:opacity-100 transition-opacity">
                {action} <ArrowRight size={11} strokeWidth={1.5} />
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* Research Integration */}
      <Card variant="flush" as="section">
        <div className="px-6 py-4 border-b border-slate-200">
          <div className="overline flex items-center gap-2">
            <FlaskConical size={12} strokeWidth={1.5} className="text-[#0F2847]" />
            Research Integration
          </div>
          <p className="text-xs text-slate-500 mt-1">Connect your teaching practice to your active research work.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-slate-200">
          {[
            { to: "/workspaces",         label: "Research Workspaces",  icon: Layers,     desc: "Link course content to live research projects" },
            { to: "/projects",           label: "Research Projects",     icon: FolderOpen, desc: "Involve students in ongoing research projects" },
            { to: "/repository",         label: "Publication Repository",icon: Archive,    desc: "Share your publications with students" },
            { to: "/collaborations",     label: "Collaborations",        icon: Users,      desc: "Build research-teaching collaboration calls" },
            { to: "/publication-hub",    label: "Publication Hub",       icon: FileText,   desc: "Guide student publications from your courses" },
            { to: "/literature-review",  label: "Literature Review",     icon: BookMarked, desc: "AI-assisted review tool for teaching seminars" },
          ].map(({ to, label, icon: Icon, desc }) => (
            <Link key={to} to={to} className="bg-white p-5 hover:bg-slate-50 transition-colors group flex items-start gap-3">
              <Icon size={16} strokeWidth={1.5} className="text-[#0F2847] mt-0.5 shrink-0" />
              <div className="min-w-0">
                <div className="text-sm font-medium text-slate-900 group-hover:text-[#0F2847] transition-colors">{label}</div>
                <div className="text-xs text-slate-500 mt-0.5 leading-relaxed">{desc}</div>
              </div>
            </Link>
          ))}
        </div>
      </Card>

      {/* Student Research Pathway */}
      <Card variant="flush" as="section">
        <div className="px-6 py-4 border-b border-slate-200">
          <div className="overline flex items-center gap-2">
            <Target size={12} strokeWidth={1.5} className="text-[#0F2847]" />
            Student Research Pathway
          </div>
          <p className="text-xs text-slate-500 mt-1">Tools for guiding students from coursework into independent research.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-px bg-slate-200">
          {[
            { to: "/workspaces?type=Doctoral+Thesis",  label: "Thesis Supervision",     icon: GraduationCap, desc: "Doctoral & master's thesis workspaces" },
            { to: "/teams",                             label: "Student Research Teams",  icon: Users,         desc: "Form teams around research questions" },
            { to: "/research-gap-finder",               label: "Gap Discovery",           icon: Lightbulb,     desc: "Help students find research opportunities" },
            { to: "/network/teaching",                  label: "Teaching Communities",    icon: Network,       desc: "Connect with peers for teaching exchange" },
          ].map(({ to, label, icon: Icon, desc }) => (
            <Link key={to} to={to} className="bg-white p-5 hover:bg-slate-50 transition-colors group">
              <Icon size={18} strokeWidth={1.5} className="text-[#0F2847] mb-3" />
              <div className="text-sm font-medium text-slate-900 group-hover:text-[#0F2847] transition-colors">{label}</div>
              <div className="text-xs text-slate-500 mt-1 leading-relaxed">{desc}</div>
            </Link>
          ))}
        </div>
      </Card>

      {/* Cross-module navigation */}
      <section>
        <div className="overline mb-3">Connected modules</div>
        <div className="flex flex-wrap gap-2">
          {[
            { to: "/institution-hub",    label: "Institution Hub",    icon: Building2 },
            { to: "/institution/departments", label: "Departments",   icon: Globe },
            { to: "/network",            label: "Academic Network",   icon: Network },
            { to: "/grants",             label: "Funding & Grants",   icon: Award },
            { to: "/workspaces",         label: "Research Workspaces",icon: Layers },
            { to: "/publication-hub",    label: "Publication Hub",    icon: BookOpen },
          ].map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="inline-flex items-center gap-1.5 text-xs border border-slate-200 bg-white text-slate-700 hover:border-[#0F2847] hover:text-[#0F2847] px-3 py-1.5 transition-colors"
            >
              <Icon size={11} strokeWidth={1.5} />
              {label}
              <ChevronRight size={10} strokeWidth={1.5} className="text-slate-400" />
            </Link>
          ))}
        </div>
      </section>

      {/* Recent activity */}
      <div className="grid md:grid-cols-2 gap-8">
        {/* Recent lessons */}
        <List>
          <ListHeader
            title="Recent lessons"
            action={
              <Link to="/teaching/lesson-planner" className="text-xs text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
                View all
              </Link>
            }
          />
          {loading && (
            <div className="px-6 py-4 flex items-center gap-2 text-sm text-slate-400">
              <Spinner size={12} /> Loading…
            </div>
          )}
          {!loading && recentLessons.length === 0 && (
            <div className="px-4 py-2">
              <EmptyState
                icon={<BookOpen />}
                title="No lessons yet"
                description="Create your first lesson plan"
                action={<Link to="/teaching/lesson-planner" className="text-xs text-[#0F2847]">Create first lesson</Link>}
                size="sm"
              />
            </div>
          )}
          {recentLessons.map((l) => (
            <ListItem
              key={l.id}
              to={`/teaching/lessons/${l.id}`}
              title={l.title}
              subtitle={`${l.subject} · ${l.duration_minutes} min`}
              trailing={
                <Badge variant={l.status === "published" ? "success" : "neutral"} size="sm">
                  {l.status}
                </Badge>
              }
            />
          ))}
        </List>

        {/* Recent assessments */}
        <List>
          <ListHeader
            title="Recent assessments"
            action={
              <Link to="/teaching/assessment-builder" className="text-xs text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
                View all
              </Link>
            }
          />
          {loading && (
            <div className="px-6 py-4 flex items-center gap-2 text-sm text-slate-400">
              <Spinner size={12} /> Loading…
            </div>
          )}
          {!loading && recentAssessments.length === 0 && (
            <div className="px-4 py-2">
              <EmptyState
                icon={<ClipboardCheck />}
                title="No assessments yet"
                description="Create your first assessment"
                action={<Link to="/teaching/assessment-builder" className="text-xs text-[#0F2847]">Create first assessment</Link>}
                size="sm"
              />
            </div>
          )}
          {recentAssessments.map((a) => (
            <ListItem
              key={a.id}
              to={`/teaching/assessments/${a.id}`}
              title={a.title}
              subtitle={`${a.subject} · ${a.assessment_type}`}
              trailing={
                <Badge variant={a.status === "published" ? "success" : "neutral"} size="sm">
                  {a.status}
                </Badge>
              }
            />
          ))}
        </List>
      </div>
    </ResearchLayout>
  );
}

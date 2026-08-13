/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import {
  User, Mail, Globe, Building2, GraduationCap, BookOpen, FileText, Users,
  Award, BarChart2, ChevronRight, ArrowLeft,
  FlaskConical, ShieldCheck, ExternalLink,
} from "lucide-react";
import { SkeletonCard, Card, Button, NavTabs, StatCard, StatGrid, Badge, EmptyState } from "@/components/ds";
import ReputationBadge from "../components/marketplace/ReputationBadge";
import { ResearchLayout } from "@/layouts";

const TABS = ["overview", "teaching", "research", "publications", "impact"];
const TAB_LABEL = {
  overview: "Overview", teaching: "Teaching", research: "Research",
  publications: "Publications", impact: "Impact",
};

function QuickLink({ to, label }) {
  return (
    <Button as={Link} to={to} variant="ghost" size="sm">
      {label}
      <ChevronRight size={10} strokeWidth={1.5} className="text-slate-400" />
    </Button>
  );
}

function StatusBadge({ status }) {
  return (
    <Badge variant={status === "published" || status === "active" ? "success" : "neutral"} size="sm">
      {status}
    </Badge>
  );
}

export default function FacultyProfile() {
  const { id } = useParams();
  const { user: currentUser } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile]         = useState(null);
  const [portfolio, setPortfolio]     = useState([]);
  const [publications, setPublications] = useState([]);
  const [projects, setProjects]       = useState([]);
  const [lessons, setLessons]         = useState([]);
  const [groups, setGroups]           = useState([]);
  const [tab, setTab]                 = useState("overview");
  const [loading, setLoading]         = useState(true);

  const isSelf = currentUser?.id === id;

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const profileRes = await api.get(`/users/${id}`);
        setProfile(profileRes.data);

        // Load secondary data in parallel — non-fatal failures
        const [portfolioRes, pubsRes, projectsRes, lessonsRes, groupsRes] = await Promise.allSettled([
          api.get("/teaching/portfolio"),
          api.get(`/publications?limit=6`),
          api.get("/projects?limit=5"),
          api.get("/teaching/lessons?limit=5"),
          api.get("/network/groups/mine"),
        ]);
        if (portfolioRes.status === "fulfilled") setPortfolio(portfolioRes.value.data || []);
        if (pubsRes.status === "fulfilled")     setPublications((pubsRes.value.data?.items || pubsRes.value.data || []).slice(0, 6));
        if (projectsRes.status === "fulfilled") setProjects((projectsRes.value.data?.items || projectsRes.value.data || []).slice(0, 5));
        if (lessonsRes.status === "fulfilled")  setLessons((lessonsRes.value.data || []).slice(0, 5));
        if (groupsRes.status === "fulfilled")   setGroups((groupsRes.value.data || []).slice(0, 4));
      } catch (_) {}
      setLoading(false);
    };
    load();
  }, [id]);

  if (loading) return (
    <div className="p-8">
      <SkeletonCard rows={6} />
    </div>
  );

  if (!profile) return (
    <div className="p-8 text-center">
      <div className="text-slate-500 text-sm">Faculty profile not found.</div>
      <Button variant="link" onClick={() => navigate(-1)} className="mt-4">Go back</Button>
    </div>
  );

  return (
    <ResearchLayout
      title={profile.full_name}
      subtitle={[profile.position, profile.institution].filter(Boolean).join(" · ")}
      icon={<User size={15} strokeWidth={1.5} style={{ color: "#0F2847" }} />}
    >
      {/* Back */}
      <div className="mb-6">
        <Button variant="link" onClick={() => navigate(-1)} className="text-slate-500 hover:text-slate-900">
          <ArrowLeft size={12} strokeWidth={1.5} />
          Back
        </Button>
      </div>

      {/* Profile header card */}
      <Card padding="lg" className="mb-6">
        <div className="flex items-start gap-5 flex-wrap">
          <div className="w-20 h-20 shrink-0 bg-[#0F2847]/5 border border-[#0F2847]/20 flex items-center justify-center">
            {profile.avatar_url
              ? <img src={profile.avatar_url} alt="" className="w-full h-full object-cover" />
              : <User size={28} strokeWidth={1.5} className="text-[#0F2847]" />}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="font-serif text-3xl text-slate-900">{profile.full_name}</h1>
            {profile.position && (
              <div className="text-sm text-slate-600 mt-1">{profile.position}</div>
            )}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-slate-500">
              {profile.institution && (
                <span className="inline-flex items-center gap-1">
                  <Building2 size={11} strokeWidth={1.5} />
                  {profile.institution}
                </span>
              )}
              {profile.email && isSelf && (
                <span className="inline-flex items-center gap-1">
                  <Mail size={11} strokeWidth={1.5} />
                  {profile.email}
                </span>
              )}
              {profile.website && (
                <a href={profile.website} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-[#0F2847]">
                  <Globe size={11} strokeWidth={1.5} />
                  {profile.website.replace(/^https?:\/\//, "").slice(0, 30)}
                </a>
              )}
            </div>
            {(profile.research_interests || []).length > 0 && (
              <div className="flex flex-wrap gap-1 mt-3">
                {profile.research_interests.slice(0, 8).map((tag) => (
                  <span key={tag} className="text-[10px] font-mono border border-slate-200 bg-slate-50 px-1.5 py-0.5">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex flex-col gap-2 shrink-0">
            {isSelf ? (
              <Button as={Link} to="/academic-passport" size="sm">Edit Profile</Button>
            ) : (
              <Button as={Link} to={`/messages/${id}`} size="sm">Message</Button>
            )}
            {profile.orcid_id && (
              <Button
                as="a"
                href={`https://orcid.org/${profile.orcid_id}`}
                target="_blank"
                rel="noreferrer"
                variant="ghost"
                size="sm"
              >
                <ShieldCheck size={11} strokeWidth={1.5} />
                ORCID
                <ExternalLink size={9} strokeWidth={1.5} />
              </Button>
            )}
          </div>
        </div>
        {profile.bio && (
          <p className="mt-5 text-sm text-slate-600 leading-relaxed border-t border-slate-100 pt-4 max-w-3xl">
            {profile.bio}
          </p>
        )}
      </Card>

      {/* Tabs */}
      <div className="mb-6">
        <NavTabs
          variant="underline"
          active={tab}
          onChange={setTab}
          tabs={TABS.map((t) => ({ id: t, label: TAB_LABEL[t] }))}
        />
      </div>

      {tab === "overview"      && <OverviewTab profile={profile} portfolio={portfolio} publications={publications} groups={groups} />}
      {tab === "teaching"      && <TeachingTab portfolio={portfolio} lessons={lessons} isSelf={isSelf} />}
      {tab === "research"      && <ResearchTab projects={projects} groups={groups} isSelf={isSelf} />}
      {tab === "publications"  && <PublicationsTab publications={publications} isSelf={isSelf} />}
      {tab === "impact"        && <ImpactTab profile={profile} />}
    </ResearchLayout>
  );
}

/* ─── Overview ──────────────────────────────────────────────────────────────── */
function OverviewTab({ profile, portfolio, publications, groups }) {
  const stats = [
    { label: "Publications",  value: publications.length || "—", icon: FileText },
    { label: "Teaching Items",value: portfolio.length || "—",    icon: GraduationCap },
    { label: "Research Groups",value: groups.length || "—",      icon: Users },
    { label: "h-index",       value: profile.h_index || "—",     icon: BarChart2 },
  ];
  return (
    <div className="space-y-6">
      <StatGrid cols={4}>
        {stats.map(({ label, value, icon: Icon }) => (
          <StatCard key={label} label={label} value={value} icon={<Icon />} />
        ))}
      </StatGrid>

      {(profile.teaching_philosophy || portfolio.length > 0) && (
        <div className="grid md:grid-cols-2 gap-5">
          {profile.teaching_philosophy && (
            <Card padding="lg">
              <div className="overline mb-3">Teaching Philosophy</div>
              <p className="text-sm text-slate-600 leading-relaxed">{profile.teaching_philosophy}</p>
            </Card>
          )}
          {portfolio.length > 0 && (
            <Card padding="lg">
              <div className="overline mb-3">Recent Portfolio</div>
              <div className="space-y-2">
                {portfolio.slice(0, 3).map((item) => (
                  <div key={item.id} className="text-sm text-slate-700 flex items-center gap-2">
                    <Award size={11} strokeWidth={1.5} className="text-[#0F2847] shrink-0" />
                    <span className="truncate">{item.title || item.type}</span>
                    {item.year && <span className="text-xs text-slate-400 font-mono ml-auto">{item.year}</span>}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {publications.length > 0 && (
        <Card padding="none">
          <div className="px-5 py-4 border-b border-slate-200 overline">Recent Publications</div>
          <div className="divide-y divide-slate-100">
            {publications.slice(0, 3).map((pub) => (
              <div key={pub.id} className="px-5 py-3">
                <div className="text-sm font-medium text-slate-900 truncate">{pub.title}</div>
                <div className="text-xs text-slate-500 mt-0.5">{pub.year} · {pub.status}</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

/* ─── Teaching ──────────────────────────────────────────────────────────────── */
function TeachingTab({ portfolio, lessons, isSelf }) {
  return (
    <div className="space-y-6">
      {/* Quick links for own profile */}
      {isSelf && (
        <div className="flex flex-wrap gap-2">
          <QuickLink to="/teaching/lesson-planner" label="Lesson Planner" />
          <QuickLink to="/teaching/assessment-builder" label="Assessment Builder" />
          <QuickLink to="/teaching/portfolio" label="Full Portfolio" />
          <QuickLink to="/teaching/analytics" label="Teaching Analytics" />
        </div>
      )}

      {portfolio.length > 0 ? (
        <Card padding="none">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <div className="overline">Teaching Portfolio</div>
            {isSelf && (
              <Link to="/teaching/portfolio" className="text-xs text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">Manage</Link>
            )}
          </div>
          <div className="divide-y divide-slate-100">
            {portfolio.map((item) => (
              <div key={item.id} className="px-5 py-3 flex items-center justify-between">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-900 truncate">{item.title || item.type}</div>
                  {item.institution && <div className="text-xs text-slate-500 mt-0.5">{item.institution}</div>}
                </div>
                {item.year && <span className="text-xs font-mono text-slate-400 ml-3 shrink-0">{item.year}</span>}
              </div>
            ))}
          </div>
        </Card>
      ) : (
        <EmptyState
          icon={<GraduationCap />}
          title="No portfolio items yet"
          action={isSelf && <Button as={Link} to="/teaching/portfolio" variant="link">Build your portfolio</Button>}
        />
      )}

      {lessons.length > 0 && (
        <Card padding="none">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <div className="overline">Recent Lessons</div>
            {isSelf && (
              <Link to="/teaching/lesson-planner" className="text-xs text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">View all</Link>
            )}
          </div>
          <div className="divide-y divide-slate-100">
            {lessons.map((l) => (
              <div key={l.id} className="px-5 py-3 flex items-center justify-between">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-900 truncate">{l.title}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{l.subject} · {l.duration_minutes} min</div>
                </div>
                <div className="ml-3 shrink-0"><StatusBadge status={l.status} /></div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

/* ─── Research ──────────────────────────────────────────────────────────────── */
function ResearchTab({ projects, groups, isSelf }) {
  return (
    <div className="space-y-6">
      {isSelf && (
        <div className="flex flex-wrap gap-2">
          <QuickLink to="/projects" label="All Projects" />
          <QuickLink to="/workspaces" label="Workspaces" />
          <QuickLink to="/collaborations" label="Collaborations" />
          <QuickLink to="/teams" label="Teams" />
        </div>
      )}

      {projects.length > 0 ? (
        <Card padding="none">
          <div className="px-5 py-4 border-b border-slate-200 overline">Research Projects</div>
          <div className="divide-y divide-slate-100">
            {projects.map((p) => (
              <Link key={p.id} to={`/projects/${p.id}`} className="px-5 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-900 truncate">{p.name || p.title}</div>
                  {p.description && (
                    <div className="text-xs text-slate-500 mt-0.5 truncate">{p.description}</div>
                  )}
                </div>
                <div className="ml-3 shrink-0"><StatusBadge status={p.status || "active"} /></div>
              </Link>
            ))}
          </div>
        </Card>
      ) : (
        <EmptyState
          icon={<FlaskConical />}
          title="No research projects"
          action={isSelf && <Button as={Link} to="/projects" variant="link">Start a project</Button>}
        />
      )}

      {groups.length > 0 && (
        <Card padding="none">
          <div className="px-5 py-4 border-b border-slate-200 overline">Research Groups</div>
          <div className="divide-y divide-slate-100">
            {groups.map((g) => (
              <Link key={g.id} to={`/teams/${g.id}`} className="px-5 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-900 truncate">{g.name}</div>
                  {g.discipline && <div className="text-xs text-slate-500 mt-0.5">{g.discipline}</div>}
                </div>
                <Badge variant="neutral" size="sm" className="ml-3 shrink-0 font-mono">
                  {(g.type || "").replace("_", " ")}
                </Badge>
              </Link>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

/* ─── Publications ──────────────────────────────────────────────────────────── */
function PublicationsTab({ publications, isSelf }) {
  return (
    <div className="space-y-4">
      {isSelf && (
        <div className="flex gap-2">
          <QuickLink to="/publication-hub" label="Publication Hub" />
          <QuickLink to="/manuscripts" label="Manuscripts" />
          <QuickLink to="/repository" label="Repository" />
        </div>
      )}

      {publications.length > 0 ? (
        <Card padding="none" className="divide-y divide-slate-100">
          {publications.map((pub) => (
            <div key={pub.id} className="px-5 py-4">
              <div className="text-sm font-medium text-slate-900">{pub.title}</div>
              <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
                {pub.year && <span className="font-mono">{pub.year}</span>}
                {pub.journal && <span>{pub.journal}</span>}
                {pub.status && <StatusBadge status={pub.status} />}
                {pub.doi && (
                  <a href={`https://doi.org/${pub.doi}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 hover:text-[#0F2847]">
                    DOI <ExternalLink size={9} strokeWidth={1.5} />
                  </a>
                )}
              </div>
            </div>
          ))}
        </Card>
      ) : (
        <EmptyState
          icon={<BookOpen />}
          title="No publications yet"
          action={isSelf && <Button as={Link} to="/publication-hub" variant="link">Add publications</Button>}
        />
      )}
    </div>
  );
}

/* ─── Impact ────────────────────────────────────────────────────────────────── */
function ImpactTab({ profile }) {
  const stats = [
    { label: "h-index",          value: profile.h_index ?? "—" },
    { label: "Total Citations",  value: profile.total_citations?.toLocaleString() ?? "—" },
    { label: "Publications",     value: profile.publication_count ?? "—" },
  ];
  const links = [
    { to: "/research-impact",      label: "Research Impact Dashboard" },
    { to: "/citations",            label: "Citation Analytics" },
    { to: "/citation-monitoring",  label: "Citation Monitoring" },
    { to: "/reputation",           label: "Reputation Score" },
    { to: "/analytics",            label: "Full Analytics" },
  ];
  return (
    <div className="space-y-5">
      <StatGrid cols={3}>
        {stats.map(({ label, value }) => (
          <StatCard key={label} label={label} value={value} />
        ))}
      </StatGrid>
      <div className="flex flex-wrap gap-2">
        {links.map(({ to, label }) => <QuickLink key={to} to={to} label={label} />)}
      </div>
    </div>
  );
}

/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import {
  User, Mail, Globe, Building2, GraduationCap, BookOpen, FileText, Users,
  Award, BarChart2, Layers, ChevronRight, ArrowLeft, Sparkles,
  BookMarked, FlaskConical, Target, ShieldCheck, ExternalLink,
} from "lucide-react";
import { SkeletonCard } from "@/components/ds/LoadingState";
import ReputationBadge from "../components/marketplace/ReputationBadge";
import { ResearchLayout } from "@/layouts";

const TABS = ["overview", "teaching", "research", "publications", "impact"];
const TAB_LABEL = {
  overview: "Overview", teaching: "Teaching", research: "Research",
  publications: "Publications", impact: "Impact",
};

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
      <button onClick={() => navigate(-1)} className="mt-4 text-xs text-[#0F2847] border-b border-[#0F2847]">Go back</button>
    </div>
  );

  return (
    <ResearchLayout
      title={profile.full_name}
      subtitle={[profile.position, profile.institution].filter(Boolean).join(" · ")}
      icon={User}
    >
      {/* Back */}
      <div className="mb-6">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft size={12} strokeWidth={1.5} />
          Back
        </button>
      </div>

      {/* Profile header card */}
      <div className="border border-slate-200 bg-white p-6 mb-6">
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
              <Link to="/academic-passport" className="text-xs bg-[#0F2847] text-white px-4 py-2 hover:bg-slate-800">
                Edit Profile
              </Link>
            ) : (
              <Link
                to={`/messages?to=${id}`}
                className="text-xs bg-[#0F2847] text-white px-4 py-2 hover:bg-slate-800"
              >
                Message
              </Link>
            )}
            {profile.orcid_id && (
              <a
                href={`https://orcid.org/${profile.orcid_id}`}
                target="_blank"
                rel="noreferrer"
                className="text-xs border border-slate-300 text-slate-600 px-4 py-2 hover:border-[#0F2847] inline-flex items-center gap-1"
              >
                <ShieldCheck size={11} strokeWidth={1.5} />
                ORCID
                <ExternalLink size={9} strokeWidth={1.5} />
              </a>
            )}
          </div>
        </div>
        {profile.bio && (
          <p className="mt-5 text-sm text-slate-600 leading-relaxed border-t border-slate-100 pt-4 max-w-3xl">
            {profile.bio}
          </p>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-200 mb-6 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm -mb-px border-b-2 whitespace-nowrap transition-colors ${tab === t ? "border-[#0F2847] text-[#0F2847]" : "border-transparent text-slate-500 hover:text-slate-900"}`}
          >
            {TAB_LABEL[t]}
          </button>
        ))}
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
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {stats.map(({ label, value, icon: Icon }) => (
          <div key={label} className="border border-slate-200 bg-white p-5">
            <div className="overline flex items-center gap-1">
              <Icon size={11} strokeWidth={1.5} className="text-[#0F2847]" />
              {label}
            </div>
            <div className="font-serif text-3xl text-slate-900 mt-2">{value}</div>
          </div>
        ))}
      </div>

      {(profile.teaching_philosophy || portfolio.length > 0) && (
        <div className="grid md:grid-cols-2 gap-5">
          {profile.teaching_philosophy && (
            <div className="border border-slate-200 bg-white p-5">
              <div className="overline mb-3">Teaching Philosophy</div>
              <p className="text-sm text-slate-600 leading-relaxed">{profile.teaching_philosophy}</p>
            </div>
          )}
          {portfolio.length > 0 && (
            <div className="border border-slate-200 bg-white p-5">
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
            </div>
          )}
        </div>
      )}

      {publications.length > 0 && (
        <div className="border border-slate-200 bg-white">
          <div className="px-5 py-4 border-b border-slate-200 overline">Recent Publications</div>
          <div className="divide-y divide-slate-100">
            {publications.slice(0, 3).map((pub) => (
              <div key={pub.id} className="px-5 py-3">
                <div className="text-sm font-medium text-slate-900 truncate">{pub.title}</div>
                <div className="text-xs text-slate-500 mt-0.5">{pub.year} · {pub.status}</div>
              </div>
            ))}
          </div>
        </div>
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
          {[
            { to: "/teaching/lesson-planner",     label: "Lesson Planner" },
            { to: "/teaching/assessment-builder",  label: "Assessment Builder" },
            { to: "/teaching/portfolio",           label: "Full Portfolio" },
            { to: "/teaching/analytics",           label: "Teaching Analytics" },
          ].map(({ to, label }) => (
            <Link key={to} to={to} className="text-xs border border-slate-200 bg-white px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] inline-flex items-center gap-1 transition-colors">
              {label}
              <ChevronRight size={10} strokeWidth={1.5} className="text-slate-400" />
            </Link>
          ))}
        </div>
      )}

      {portfolio.length > 0 ? (
        <div className="border border-slate-200 bg-white">
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
        </div>
      ) : (
        <div className="border border-slate-200 bg-white p-8 text-center">
          <GraduationCap size={24} strokeWidth={1.5} className="text-slate-300 mx-auto mb-2" />
          <div className="text-sm text-slate-500">No portfolio items yet</div>
          {isSelf && (
            <Link to="/teaching/portfolio" className="mt-3 inline-block text-xs text-[#0F2847] border-b border-[#0F2847]">
              Build your portfolio
            </Link>
          )}
        </div>
      )}

      {lessons.length > 0 && (
        <div className="border border-slate-200 bg-white">
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
                <span className={`text-[10px] px-2 py-0.5 ml-3 shrink-0 ${l.status === "published" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                  {l.status}
                </span>
              </div>
            ))}
          </div>
        </div>
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
          {[
            { to: "/projects",       label: "All Projects" },
            { to: "/workspaces",     label: "Workspaces" },
            { to: "/collaborations", label: "Collaborations" },
            { to: "/teams",          label: "Teams" },
          ].map(({ to, label }) => (
            <Link key={to} to={to} className="text-xs border border-slate-200 bg-white px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] inline-flex items-center gap-1 transition-colors">
              {label}
              <ChevronRight size={10} strokeWidth={1.5} className="text-slate-400" />
            </Link>
          ))}
        </div>
      )}

      {projects.length > 0 ? (
        <div className="border border-slate-200 bg-white">
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
                <span className={`text-[10px] px-2 py-0.5 ml-3 shrink-0 ${p.status === "active" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                  {p.status || "active"}
                </span>
              </Link>
            ))}
          </div>
        </div>
      ) : (
        <div className="border border-slate-200 bg-white p-8 text-center">
          <FlaskConical size={24} strokeWidth={1.5} className="text-slate-300 mx-auto mb-2" />
          <div className="text-sm text-slate-500">No research projects</div>
          {isSelf && (
            <Link to="/projects" className="mt-3 inline-block text-xs text-[#0F2847] border-b border-[#0F2847]">
              Start a project
            </Link>
          )}
        </div>
      )}

      {groups.length > 0 && (
        <div className="border border-slate-200 bg-white">
          <div className="px-5 py-4 border-b border-slate-200 overline">Research Groups</div>
          <div className="divide-y divide-slate-100">
            {groups.map((g) => (
              <Link key={g.id} to={`/teams/${g.id}`} className="px-5 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-900 truncate">{g.name}</div>
                  {g.discipline && <div className="text-xs text-slate-500 mt-0.5">{g.discipline}</div>}
                </div>
                <span className="text-[10px] px-2 py-0.5 ml-3 shrink-0 bg-slate-100 text-slate-600 font-mono">
                  {(g.type || "").replace("_", " ")}
                </span>
              </Link>
            ))}
          </div>
        </div>
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
          <Link to="/publication-hub" className="text-xs border border-slate-200 bg-white px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] inline-flex items-center gap-1 transition-colors">
            Publication Hub <ChevronRight size={10} strokeWidth={1.5} className="text-slate-400" />
          </Link>
          <Link to="/manuscripts" className="text-xs border border-slate-200 bg-white px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] inline-flex items-center gap-1 transition-colors">
            Manuscripts <ChevronRight size={10} strokeWidth={1.5} className="text-slate-400" />
          </Link>
          <Link to="/repository" className="text-xs border border-slate-200 bg-white px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] inline-flex items-center gap-1 transition-colors">
            Repository <ChevronRight size={10} strokeWidth={1.5} className="text-slate-400" />
          </Link>
        </div>
      )}

      {publications.length > 0 ? (
        <div className="border border-slate-200 bg-white divide-y divide-slate-100">
          {publications.map((pub) => (
            <div key={pub.id} className="px-5 py-4">
              <div className="text-sm font-medium text-slate-900">{pub.title}</div>
              <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
                {pub.year && <span className="font-mono">{pub.year}</span>}
                {pub.journal && <span>{pub.journal}</span>}
                {pub.status && (
                  <span className={`px-1.5 py-0.5 ${pub.status === "published" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                    {pub.status}
                  </span>
                )}
                {pub.doi && (
                  <a href={`https://doi.org/${pub.doi}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 hover:text-[#0F2847]">
                    DOI <ExternalLink size={9} strokeWidth={1.5} />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="border border-slate-200 bg-white p-8 text-center">
          <BookOpen size={24} strokeWidth={1.5} className="text-slate-300 mx-auto mb-2" />
          <div className="text-sm text-slate-500">No publications yet</div>
          {isSelf && (
            <Link to="/publication-hub" className="mt-3 inline-block text-xs text-[#0F2847] border-b border-[#0F2847]">
              Add publications
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Impact ────────────────────────────────────────────────────────────────── */
function ImpactTab({ profile }) {
  return (
    <div className="space-y-5">
      <div className="grid sm:grid-cols-3 gap-3">
        {[
          { label: "h-index",          value: profile.h_index ?? "—" },
          { label: "Total Citations",  value: profile.total_citations?.toLocaleString() ?? "—" },
          { label: "Publications",     value: profile.publication_count ?? "—" },
        ].map(({ label, value }) => (
          <div key={label} className="border border-slate-200 bg-white p-5">
            <div className="overline">{label}</div>
            <div className="font-serif text-4xl text-slate-900 mt-2">{value}</div>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {[
          { to: "/research-impact",      label: "Research Impact Dashboard" },
          { to: "/citations",            label: "Citation Analytics" },
          { to: "/citation-monitoring",  label: "Citation Monitoring" },
          { to: "/reputation",           label: "Reputation Score" },
          { to: "/analytics",            label: "Full Analytics" },
        ].map(({ to, label }) => (
          <Link key={to} to={to} className="text-xs border border-slate-200 bg-white px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] inline-flex items-center gap-1 transition-colors">
            {label} <ChevronRight size={10} strokeWidth={1.5} className="text-slate-400" />
          </Link>
        ))}
      </div>
    </div>
  );
}

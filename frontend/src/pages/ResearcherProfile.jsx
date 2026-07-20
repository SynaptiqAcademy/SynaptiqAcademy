import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import api from "../lib/api";
import { NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import {
  MapPin, Building2, Globe, ExternalLink, Users, BookOpen, Award,
  TrendingUp, Star, Calendar, ChevronRight, Loader2, Share2, UserPlus,
  UserCheck, BarChart3, Layers, GraduationCap, Activity, Clock,
  FileText, Briefcase, FlaskConical, ArrowLeft, Eye, Heart
} from "lucide-react";

export default function ResearcherProfile() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [tabData, setTabData] = useState({});
  const [tabLoading, setTabLoading] = useState({});
  const [isFollowing, setIsFollowing] = useState(false);
  const [followLoading, setFollowLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const loadedTabs = useRef(new Set());

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await api.get(`/profiles/researcher/${slug}`);
        setProfile(res.data);
        if (user) {
          try {
            const fRes = await api.get(`/profiles/researcher/${slug}/follow-status`);
            setIsFollowing(fRes.data.following);
          } catch {}
        }
      } catch (e) {
        setError(e.response?.data?.detail || "Profile not found");
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
    loadedTabs.current.add("overview");
  }, [slug, user]);

  const loadTab = useCallback(async (tab) => {
    if (loadedTabs.current.has(tab)) return;
    loadedTabs.current.add(tab);
    setTabLoading(prev => ({ ...prev, [tab]: true }));
    try {
      let data;
      if (tab === "publications") data = (await api.get(`/profiles/researcher/${slug}/publications`)).data;
      else if (tab === "impact") data = (await api.get(`/profiles/researcher/${slug}/impact`)).data;
      else if (tab === "projects") data = (await api.get(`/profiles/researcher/${slug}/projects`)).data;
      else if (tab === "grants") data = (await api.get(`/profiles/researcher/${slug}/grants`)).data;
      else if (tab === "collaborations") data = (await api.get(`/profiles/researcher/${slug}/collaborations`)).data;
      else if (tab === "teaching") data = (await api.get(`/profiles/researcher/${slug}/teaching`)).data;
      else if (tab === "reputation") data = (await api.get(`/profiles/researcher/${slug}/reputation`)).data;
      else if (tab === "timeline") data = (await api.get(`/profiles/researcher/${slug}/timeline`)).data;
      setTabData(prev => ({ ...prev, [tab]: data }));
    } catch (e) {
      setTabData(prev => ({ ...prev, [tab]: { _error: e.response?.data?.detail || "Failed to load" } }));
    } finally {
      setTabLoading(prev => ({ ...prev, [tab]: false }));
    }
  }, [slug]);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    loadTab(tab);
  };

  const handleFollow = async () => {
    if (!user) { navigate("/login"); return; }
    setFollowLoading(true);
    try {
      if (isFollowing) {
        await api.delete(`/profiles/follow/${profile.user_id}`);
        setIsFollowing(false);
      } else {
        await api.post(`/profiles/follow/${profile.user_id}`);
        setIsFollowing(true);
      }
    } catch {}
    setFollowLoading(false);
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderTabContent = () => {
    const data = tabData[activeTab];
    const isLoading = tabLoading[activeTab];

    if (isLoading) return (
      <div className="flex items-center gap-2 text-slate-400 py-12 justify-center">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm">Loading...</span>
      </div>
    );

    if (data?._error) return (
      <div className="py-12 text-center">
        <p className="text-sm text-slate-500">{data._error}</p>
      </div>
    );

    // OVERVIEW TAB
    if (activeTab === "overview") return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {(profile.research_interests || []).length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-slate-900 mb-3 uppercase tracking-wide">Research Focus</h3>
              <div className="flex flex-wrap gap-2">
                {profile.research_interests.map((area, i) => (
                  <span key={i} className="px-3 py-1.5 bg-slate-50 border border-slate-200 text-sm text-slate-700 rounded-full">{area}</span>
                ))}
              </div>
            </section>
          )}
          {(profile.keywords || []).length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-slate-900 mb-3 uppercase tracking-wide">Keywords</h3>
              <div className="flex flex-wrap gap-2">
                {profile.keywords.map((kw, i) => (
                  <span key={i} className="px-2.5 py-1 bg-white border border-slate-200 text-xs text-slate-600 rounded">{kw}</span>
                ))}
              </div>
            </section>
          )}
          {(profile.showcase || []).length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-slate-900 mb-3 uppercase tracking-wide">Featured Work</h3>
              <div className="space-y-2">
                {profile.showcase.map((item, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 border border-slate-100 rounded-lg hover:border-slate-200 transition-colors">
                    <Star size={14} className="text-amber-400 shrink-0" />
                    <div>
                      <div className="text-sm font-medium text-slate-900">{item.title || item.custom_label || item.item_type}</div>
                      <div className="text-xs text-slate-400 capitalize">{item.item_type}</div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
          {(profile.research_interests || []).length === 0 && (profile.keywords || []).length === 0 && (profile.showcase || []).length === 0 && (
            <div className="py-12 text-center text-sm text-slate-400">No overview data available yet</div>
          )}
        </div>
        <div className="space-y-4">
          <div className="p-4 border border-slate-100 rounded-lg">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Quick Stats</h3>
            {[
              { label: "Publications", value: profile.stats?.publications || 0, icon: BookOpen },
              { label: "Citations", value: profile.stats?.citations || 0, icon: TrendingUp },
              { label: "H-index", value: profile.stats?.h_index || 0, icon: BarChart3 },
              { label: "Projects", value: profile.stats?.projects || 0, icon: Briefcase },
              { label: "Collaborations", value: profile.stats?.collaborations || 0, icon: Users },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <Icon size={13} strokeWidth={1.5} className="text-slate-400" />
                  {label}
                </div>
                <span className="font-mono text-sm text-slate-900">{value.toLocaleString()}</span>
              </div>
            ))}
          </div>
          {(profile.impact?.sis_total || 0) > 0 && (
            <div className="p-4 border border-[#0F2847]/10 bg-[#0F2847]/5 rounded-lg text-center">
              <div className="text-xs text-[#0F2847]/60 uppercase tracking-wide mb-1">Synaptiq Impact Score</div>
              <div className="font-serif text-3xl text-[#0F2847]">{profile.impact.sis_total.toLocaleString()}</div>
              <div className="text-xs text-[#0F2847]/40 mt-0.5">out of 10,000</div>
            </div>
          )}
        </div>
      </div>
    );

    // PUBLICATIONS TAB
    if (activeTab === "publications") {
      const pubs = Array.isArray(data) ? data : [];
      return (
        <div>
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-serif text-xl text-slate-900">{pubs.length} Publications</h3>
          </div>
          {pubs.length === 0 ? (
            <div className="py-12 text-center text-sm text-slate-400">No publications available</div>
          ) : (
            <div className="space-y-3">
              {pubs.map((p, i) => (
                <div key={i} className="p-4 border border-slate-100 rounded-lg hover:border-slate-200 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <h4 className="text-sm font-medium text-slate-900">{p.title}</h4>
                      <div className="mt-1 flex items-center gap-3 text-xs text-slate-400">
                        {p.year && <span>{p.year}</span>}
                        {p.journal && <span className="truncate max-w-[200px]">{p.journal}</span>}
                        <span className="capitalize">{p.pub_type}</span>
                      </div>
                    </div>
                    {(p.citation_count || 0) > 0 && (
                      <div className="text-right shrink-0">
                        <div className="font-mono text-sm text-slate-900">{p.citation_count}</div>
                        <div className="text-[10px] text-slate-400">citations</div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    // IMPACT TAB
    if (activeTab === "impact") {
      const impact = data || {};
      return (
        <div className="max-w-2xl">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { label: "Impact Score", value: impact.sis_total || 0, suffix: "/ 10K" },
              { label: "H-index", value: impact.h_index || 0 },
              { label: "i10-index", value: impact.i10_index || 0 },
              { label: "Total Citations", value: impact.total_citations || 0 },
            ].map(({ label, value, suffix }) => (
              <div key={label} className="text-center p-4 border border-slate-100 rounded-lg">
                <div className="font-serif text-2xl text-slate-900">{value.toLocaleString()}</div>
                {suffix && <div className="text-xs text-slate-400">{suffix}</div>}
                <div className="text-xs text-slate-500 mt-1">{label}</div>
              </div>
            ))}
          </div>
          {impact.components && (
            <div>
              <h3 className="text-sm font-semibold text-slate-900 mb-4">Score Breakdown</h3>
              <div className="space-y-3">
                {Object.entries(impact.components).map(([key, val]) => {
                  const maxMap = {
                    publication_score: 2000,
                    citation_score: 2500,
                    collaboration_score: 1500,
                    grant_score: 1000,
                    teaching_score: 500,
                    reputation_score: 1500,
                    orcid_score: 1000
                  };
                  const max = maxMap[key] || 1000;
                  const pct = Math.min(100, Math.round(((val || 0) / max) * 100));
                  return (
                    <div key={key}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-slate-600 capitalize">{key.replace(/_/g, " ")}</span>
                        <span className="font-mono text-slate-900">{val || 0} / {max}</span>
                      </div>
                      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-[#0F2847] rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          {Object.keys(impact).length === 0 && (
            <div className="py-12 text-center text-sm text-slate-400">No impact data available yet</div>
          )}
        </div>
      );
    }

    // PROJECTS TAB
    if (activeTab === "projects") {
      const projects = Array.isArray(data) ? data : [];
      return (
        <div>
          <h3 className="font-serif text-xl text-slate-900 mb-6">{projects.length} Projects</h3>
          {projects.length === 0 ? (
            <div className="py-12 text-center text-sm text-slate-400">No projects visible</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {projects.map((p, i) => (
                <div key={i} className="p-4 border border-slate-100 rounded-lg">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-medium text-slate-900">{p.title}</h4>
                    <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${p.status === "active" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>{p.status}</span>
                  </div>
                  {p.description && <p className="mt-2 text-xs text-slate-500 line-clamp-2">{p.description}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    // GRANTS TAB
    if (activeTab === "grants") {
      const grants = Array.isArray(data) ? data : [];
      return (
        <div>
          <h3 className="font-serif text-xl text-slate-900 mb-6">{grants.length} Grant Applications</h3>
          {grants.length === 0 ? (
            <div className="py-12 text-center text-sm text-slate-400">No grants visible</div>
          ) : (
            <div className="space-y-3">
              {grants.map((g, i) => (
                <div key={i} className="p-4 border border-slate-100 rounded-lg">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <h4 className="text-sm font-medium text-slate-900">{g.grant_title || "Untitled Grant"}</h4>
                      <div className="mt-1 flex items-center gap-3 text-xs text-slate-400">
                        {g.funder && <span>{g.funder}</span>}
                        {g.submitted_at && <span>{g.submitted_at.slice(0, 10)}</span>}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        g.status === "approved" ? "bg-emerald-50 text-emerald-700"
                        : g.status === "rejected" ? "bg-red-50 text-red-700"
                        : "bg-amber-50 text-amber-700"
                      }`}>{g.status}</span>
                      {g.amount_requested > 0 && <div className="mt-1 text-xs font-mono text-slate-500">${g.amount_requested.toLocaleString()}</div>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    // COLLABORATIONS TAB
    if (activeTab === "collaborations") {
      const collab = data || { total: 0, recent: [] };
      return (
        <div>
          <div className="mb-6"><span className="font-serif text-xl text-slate-900">{collab.total} Collaborations</span></div>
          {(collab.recent || []).length === 0 ? (
            <div className="py-12 text-center text-sm text-slate-400">No collaborations visible</div>
          ) : (
            <div className="space-y-3">
              {collab.recent.map((c, i) => (
                <div key={i} className="flex items-center justify-between p-4 border border-slate-100 rounded-lg">
                  <div>
                    <h4 className="text-sm font-medium text-slate-900">{c.title}</h4>
                    {c.created_at && <div className="text-xs text-slate-400 mt-0.5">{c.created_at.slice(0, 10)}</div>}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${c.status === "active" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>{c.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    // TEACHING TAB
    if (activeTab === "teaching") {
      const teaching = data || {};
      return (
        <div className="max-w-lg">
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="text-center p-4 border border-slate-100 rounded-lg">
              <div className="font-serif text-3xl text-slate-900">{teaching.total_lessons || 0}</div>
              <div className="text-xs text-slate-400 mt-1">Teaching Lessons</div>
            </div>
            <div className="text-center p-4 border border-slate-100 rounded-lg">
              <div className="font-serif text-3xl text-slate-900">{(teaching.teaching_areas || []).length}</div>
              <div className="text-xs text-slate-400 mt-1">Subject Areas</div>
            </div>
          </div>
          {(teaching.teaching_areas || []).length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-slate-900 mb-3">Teaching Areas</h3>
              <div className="flex flex-wrap gap-2">
                {teaching.teaching_areas.map((a, i) => (
                  <span key={i} className="px-2.5 py-1 bg-slate-50 border border-slate-200 text-xs text-slate-600 rounded-full">{a}</span>
                ))}
              </div>
            </div>
          )}
          {!teaching.total_lessons && <div className="py-12 text-center text-sm text-slate-400">No teaching data visible</div>}
        </div>
      );
    }

    // REPUTATION TAB
    if (activeTab === "reputation") {
      const rep = data || {};
      return (
        <div className="max-w-lg">
          <div className="p-6 border border-slate-100 rounded-lg mb-6 text-center">
            <div className="text-xs text-slate-400 uppercase tracking-wide mb-2">Research Level</div>
            <div className="font-serif text-2xl text-slate-900">{rep.level_name || "New Researcher"}</div>
            <div className="mt-3 font-mono text-3xl text-[#0F2847]">{rep.overall_score || 0}</div>
            <div className="text-xs text-slate-400">Reputation Score</div>
            {rep.global_rank && <div className="mt-2 text-xs text-slate-500">Global Rank #{rep.global_rank}</div>}
          </div>
          {(rep.badges || []).length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-slate-900 mb-3">Earned Badges</h3>
              <div className="grid grid-cols-2 gap-3">
                {rep.badges.map((b, i) => (
                  <div key={i} className="flex items-center gap-2 p-3 border border-slate-100 rounded-lg">
                    <Award size={16} className="text-amber-500 shrink-0" />
                    <div>
                      <div className="text-xs font-medium text-slate-900">{b.badge_name || b.name}</div>
                      <div className="text-[10px] text-slate-400">{b.description || ""}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {!rep.overall_score && <div className="py-12 text-center text-sm text-slate-400">No reputation data visible</div>}
        </div>
      );
    }

    // TIMELINE TAB
    if (activeTab === "timeline") {
      const events = Array.isArray(data) ? data : [];
      const iconMap = { publication: BookOpen, project: Briefcase, grant: Award, badge: Star };
      const colorMap = {
        publication: "bg-blue-100 text-blue-600",
        project: "bg-emerald-100 text-emerald-600",
        grant: "bg-amber-100 text-amber-700",
        badge: "bg-purple-100 text-purple-600"
      };
      return (
        <div className="max-w-lg">
          {events.length === 0 ? (
            <div className="py-12 text-center text-sm text-slate-400">No timeline data visible</div>
          ) : (
            <div className="space-y-4">
              {events.map((e, i) => {
                const Icon = iconMap[e.type] || Activity;
                const colorClass = colorMap[e.type] || "bg-slate-100 text-slate-600";
                return (
                  <div key={i} className="flex items-start gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${colorClass}`}>
                      <Icon size={14} />
                    </div>
                    <div className="flex-1 pb-4 border-b border-slate-50 last:border-0">
                      <div className="text-sm font-medium text-slate-900">{e.title}</div>
                      <div className="text-xs text-slate-400 mt-0.5 capitalize">{e.type} · {(e.date || "").slice(0, 10)}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      );
    }

    return null;
  };

  if (loading) return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="flex items-center gap-3 text-slate-500">
        <Loader2 size={20} className="animate-spin" />
        <span className="text-sm">Loading profile...</span>
      </div>
    </div>
  );

  if (error) return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <div className="text-4xl font-serif text-slate-200 mb-4">404</div>
        <h2 className="text-lg font-semibold text-slate-900 mb-2">Profile not found</h2>
        <p className="text-sm text-slate-500 mb-6">{error}</p>
        <Link to="/discover" className="text-sm text-[#0F2847] underline">Go to Dashboard</Link>
      </div>
    </div>
  );

  const profileActions = (
    <div className="flex items-center gap-3">
      <button onClick={handleShare} className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-slate-200 text-slate-600 hover:border-slate-400 transition-colors rounded">
        <Share2 size={12} />
        {copied ? "Copied!" : "Share"}
      </button>
      {user && user.id !== profile.user_id && (
        <button
          onClick={handleFollow}
          disabled={followLoading}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors rounded ${
            isFollowing
              ? "bg-slate-100 text-slate-700 border border-slate-200 hover:bg-red-50 hover:text-red-600 hover:border-red-200"
              : "bg-[#0F2847] text-white hover:bg-[#0a1f38]"
          }`}
        >
          {followLoading ? <Loader2 size={12} className="animate-spin" /> : isFollowing ? <UserCheck size={12} /> : <UserPlus size={12} />}
          {isFollowing ? "Following" : "Follow"}
        </button>
      )}
      {user && user.id === profile.user_id && (
        <Link to="/academic-passport" className="text-xs text-slate-500 hover:text-slate-900 underline">Edit Profile</Link>
      )}
    </div>
  );

  return (
    <ResearchLayout>
      {/* Hero section */}
      <div className="border-b border-slate-100 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="flex justify-end mb-4">{profileActions}</div>
          <div className="flex items-start gap-8">
            {/* Avatar */}
            <div className="shrink-0">
              {profile.avatar_url ? (
                <img src={profile.avatar_url} alt="" className="w-24 h-24 rounded-full object-cover border-2 border-slate-100" />
              ) : (
                <div className="w-24 h-24 rounded-full bg-[#0F2847] flex items-center justify-center text-white font-serif text-2xl">
                  {(profile.full_name || "?")[0].toUpperCase()}
                </div>
              )}
            </div>

            {/* Identity */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start gap-3 flex-wrap">
                {profile.reputation?.level_name && (
                  <span className="mt-1 px-2 py-0.5 bg-[#0F2847]/10 text-[#0F2847] text-xs font-medium rounded-full">
                    {profile.reputation.level_name}
                  </span>
                )}
              </div>

              {profile.academic_title && (
                <p className="mt-1 text-slate-600 text-base">{profile.academic_title}</p>
              )}

              <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-slate-500">
                {profile.institution && (
                  <span className="flex items-center gap-1.5">
                    <Building2 size={13} strokeWidth={1.5} />
                    {profile.institution}
                  </span>
                )}
                {profile.department && (
                  <span className="flex items-center gap-1.5">
                    <Layers size={13} strokeWidth={1.5} />
                    {profile.department}
                  </span>
                )}
                {profile.country && (
                  <span className="flex items-center gap-1.5">
                    <MapPin size={13} strokeWidth={1.5} />
                    {profile.country}
                  </span>
                )}
                {profile.orcid_id && (
                  <a href={`https://orcid.org/${profile.orcid_id}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-emerald-600 hover:text-emerald-700">
                    <span className="text-xs font-mono bg-emerald-50 px-1.5 py-0.5 rounded">ORCID</span>
                    {profile.orcid_id}
                    <ExternalLink size={11} />
                  </a>
                )}
                {profile.website && (
                  <a href={profile.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-[#0F2847] hover:underline">
                    <Globe size={13} strokeWidth={1.5} />
                    Website
                    <ExternalLink size={11} />
                  </a>
                )}
              </div>

              {profile.biography && (
                <p className="mt-4 text-sm text-slate-600 leading-relaxed max-w-2xl">{profile.biography}</p>
              )}

              {(profile.research_interests || []).length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {profile.research_interests.slice(0, 8).map((area, i) => (
                    <span key={i} className="px-2.5 py-1 bg-slate-50 border border-slate-200 text-xs text-slate-600 rounded-full">
                      {area}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Stats column — desktop only */}
            <div className="shrink-0 hidden lg:block">
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Publications", value: profile.stats?.publications || 0, icon: BookOpen },
                  { label: "Citations", value: profile.stats?.citations || 0, icon: TrendingUp },
                  { label: "H-index", value: profile.stats?.h_index || 0, icon: BarChart3 },
                  { label: "Followers", value: profile.stats?.followers || 0, icon: Users },
                ].map(({ label, value, icon: Icon }) => (
                  <div key={label} className="text-center p-3 border border-slate-100 rounded-lg min-w-[80px]">
                    <Icon size={14} className="mx-auto mb-1 text-slate-400" strokeWidth={1.5} />
                    <div className="font-serif text-xl text-slate-900">{value.toLocaleString()}</div>
                    <div className="text-[10px] text-slate-400 uppercase tracking-wide mt-0.5">{label}</div>
                  </div>
                ))}
              </div>
              {(profile.impact?.sis_total || 0) > 0 && (
                <div className="mt-3 p-3 border border-slate-100 rounded-lg text-center">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Impact Score</div>
                  <div className="font-serif text-2xl text-[#0F2847]">{profile.impact.sis_total.toLocaleString()}</div>
                  <div className="text-[10px] text-slate-400">/ 10,000</div>
                  <div className="mt-2 h-1 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-[#0F2847] rounded-full" style={{ width: `${(profile.impact.sis_total / 10000) * 100}%` }} />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Mobile stats row */}
          <div className="mt-6 flex lg:hidden items-center gap-6 overflow-x-auto text-center">
            {[
              { label: "Publications", value: profile.stats?.publications || 0 },
              { label: "Citations", value: profile.stats?.citations || 0 },
              { label: "H-index", value: profile.stats?.h_index || 0 },
              { label: "Followers", value: profile.stats?.followers || 0 },
            ].map(({ label, value }) => (
              <div key={label} className="shrink-0">
                <div className="font-serif text-2xl text-slate-900">{value.toLocaleString()}</div>
                <div className="text-xs text-slate-400">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tab bar */}
      <div className="border-b border-slate-100 sticky top-14 z-10 bg-white">
        <div className="max-w-6xl mx-auto px-6">
          <div className="flex items-center gap-1 overflow-x-auto">
            {[
              { id: "overview", label: "Overview", icon: Activity },
              { id: "publications", label: "Publications", icon: BookOpen },
              { id: "impact", label: "Impact", icon: TrendingUp },
              { id: "projects", label: "Projects", icon: Briefcase },
              { id: "grants", label: "Grants", icon: Award },
              { id: "collaborations", label: "Collaborations", icon: Users },
              { id: "teaching", label: "Teaching", icon: GraduationCap },
              { id: "reputation", label: "Reputation", icon: Star },
              { id: "timeline", label: "Timeline", icon: Clock },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => handleTabChange(id)}
                className={`flex items-center gap-1.5 px-4 py-3 text-sm whitespace-nowrap border-b-2 transition-colors ${
                  activeTab === id
                    ? "border-[#0F2847] text-[#0F2847] font-medium"
                    : "border-transparent text-slate-500 hover:text-slate-900"
                }`}
              >
                <Icon size={13} strokeWidth={1.5} />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab content */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        {renderTabContent()}
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-100 mt-16 py-8">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between text-xs text-slate-400">
          <span>Powered by <span className="font-serif text-slate-600">SYNAPTIQ</span></span>
          <span>Profile views: {profile.view_count?.toLocaleString() || 0}</span>
        </div>
      </footer>
    </ResearchLayout>
  );
}

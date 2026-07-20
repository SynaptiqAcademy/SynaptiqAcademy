/**
 * DepartmentDetail — single department with 8 feature tabs.
 * Route: /institution/departments/:did
 *
 * Tabs:
 *   Overview · Faculty · Projects · Research Outputs · Funding
 *   Statistics · Rankings · Network
 */
import React, { useState, useCallback, useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import {
  Building2, Users, FolderOpen, BookOpen, Coins, Award, BarChart3,
  Network, ChevronRight, ArrowLeft, Loader2, Plus, Trash2, X,
  UserPlus, Edit3, Check, TrendingUp, Layers, ExternalLink, RefreshCw,
} from "lucide-react";
import { TID } from "../lib/testIds";
import { userTypeLabel } from "../lib/userTypes";
import { NAVY } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";
import {
  useDepartment, useDeptMembers, useDeptProjects, useDeptMetrics,
  useDeptRankings, useDeptCollaboration, useDeptPublications,
  useDeptFunding, useDeptMutations,
} from "../hooks/useDepartments";

// ─────────────────────────── shared primitives ────────────────────────────────

function Kpi({ label, value, sub, icon: Icon, highlight }) {
  return (
    <div className={`border bg-white p-5 ${highlight ? "border-[#0F2847]" : "border-slate-200"}`}>
      <div className="overline flex items-center gap-1.5">
        {Icon && <Icon size={11} strokeWidth={1.5} className="text-[#0F2847]" />}
        {label}
      </div>
      <div className={`font-serif text-3xl mt-1 ${highlight ? "text-[#0F2847]" : "text-slate-900"}`}>
        {value ?? "—"}
      </div>
      {sub && <div className="text-[10px] text-slate-500 mt-1">{sub}</div>}
    </div>
  );
}

function SectionHeader({ label, icon: Icon, action }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        {Icon && <Icon size={14} strokeWidth={1.5} className="text-slate-400" />}
        <h2 className="overline">{label}</h2>
      </div>
      {action}
    </div>
  );
}

function ResearchTag({ label }) {
  return (
    <span className="text-[10px] font-mono border border-[#0F2847]/30 bg-[#0F2847]/5 text-[#0F2847] px-1.5 py-0.5">
      {label}
    </span>
  );
}

function MemberAvatar({ name, size = "md" }) {
  const initials = (name || "?").split(" ").map((p) => p[0]).filter(Boolean).slice(0, 2).join("").toUpperCase();
  const cls = size === "sm" ? "w-7 h-7 text-[9px]" : "w-9 h-9 text-[11px]";
  return (
    <div className={`${cls} bg-[#0F2847] text-white font-serif flex items-center justify-center shrink-0`}>
      {initials}
    </div>
  );
}

function EmptyState({ icon: Icon = Layers, message, action }) {
  return (
    <div className="border border-dashed border-slate-200 bg-white p-12 text-center">
      <Icon size={22} strokeWidth={1} className="text-slate-300 mx-auto mb-3" />
      <p className="text-sm text-slate-500">{message}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

const ROLE_LABEL = {
  unit_admin:    "Department Admin",
  research_lead: "Research Coordinator",
  researcher:    "Faculty Member",
  admin:         "Institution Admin",
  owner:         "Institution Owner",
};

const TAB_LIST = ["overview", "faculty", "projects", "outputs", "funding", "statistics", "rankings", "network"];
const TAB_META = {
  overview:   { label: "Overview",        icon: Layers },
  faculty:    { label: "Faculty",          icon: Users },
  projects:   { label: "Projects",         icon: FolderOpen },
  outputs:    { label: "Research Outputs", icon: BookOpen },
  funding:    { label: "Funding",          icon: Coins },
  statistics: { label: "Statistics",       icon: BarChart3 },
  rankings:   { label: "Rankings",         icon: Award },
  network:    { label: "Network",          icon: Network },
};

// ─────────────────────────── Overview Tab ─────────────────────────────────────

function OverviewTab({ dept, metrics, metricsLoading, onRefreshMetrics, isAdmin }) {
  const m = metrics || {};
  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="Faculty"         value={m.members}               icon={Users} />
        <Kpi label="Publications"    value={m.publications}           icon={BookOpen} highlight />
        <Kpi label="Total Citations" value={m.total_citations?.toLocaleString()} icon={TrendingUp} />
        <Kpi label="Avg h-index"     value={m.avg_h_index}            icon={Award} />
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="Grants Awarded"  value={m.grants_awarded}         icon={Coins} />
        <Kpi label="Funding (USD)"   value={m.funding_usd ? `$${(m.funding_usd / 1000).toFixed(0)}k` : "—"} icon={Coins} />
        <Kpi label="Projects"        value={m.projects}               icon={FolderOpen} />
        <Kpi label="Avg Reputation"  value={m.avg_reputation}         icon={Award} />
      </div>

      {(m.research_areas || []).length > 0 && (
        <div className="border border-slate-200 bg-white p-5">
          <div className="overline mb-3">Research Areas</div>
          <div className="flex flex-wrap gap-1.5">
            {m.research_areas.map((a) => <ResearchTag key={a} label={a} />)}
          </div>
        </div>
      )}

      {dept?.description && (
        <div className="border border-slate-200 bg-white p-5">
          <div className="overline mb-2">About</div>
          <p className="text-sm text-slate-700">{dept.description}</p>
        </div>
      )}

      <div className="flex items-center justify-between border border-slate-100 bg-slate-50 p-3 text-xs text-slate-500">
        <span>
          Metrics{m.cached ? " (cached)" : ""}
          {m.computed_at ? ` — computed ${new Date(m.computed_at).toLocaleString()}` : ""}
        </span>
        {isAdmin && (
          <button
            onClick={onRefreshMetrics}
            disabled={metricsLoading}
            className="flex items-center gap-1 text-[#0F2847] hover:underline disabled:opacity-50"
          >
            <RefreshCw size={10} className={metricsLoading ? "animate-spin" : ""} />
            Refresh
          </button>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────── Faculty Tab ──────────────────────────────────────

function ManageMembersModal({ did, iid, allInstMembers, currentMemberIds, onClose, onChanged }) {
  const [selected, setSelected] = useState(new Set(currentMemberIds));
  const { manageMembers, busy } = useDeptMutations();

  const toggle = (uid) => setSelected((s) => {
    const n = new Set(s);
    n.has(uid) ? n.delete(uid) : n.add(uid);
    return n;
  });

  const save = async () => {
    const toAdd    = [...selected].filter((u) => !currentMemberIds.includes(u));
    const toRemove = currentMemberIds.filter((u) => !selected.has(u));
    try {
      if (toAdd.length)    await manageMembers(did, toAdd,    "add");
      if (toRemove.length) await manageMembers(did, toRemove, "remove");
      toast.success("Faculty updated");
      onChanged?.(); onClose?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to update members");
    }
  };

  return (
    <div className="fixed inset-0 z-[100] bg-slate-900/50 flex items-center justify-center px-4"
      onClick={onClose} data-testid={TID.deptManageMembersModal}>
      <div className="bg-white w-full max-w-lg border border-slate-200 max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <h3 className="font-serif text-lg text-slate-900">Manage Faculty</h3>
          <button onClick={onClose}><X size={16} strokeWidth={1.5} /></button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {(allInstMembers || []).length === 0 && (
            <p className="text-xs text-slate-500">No institution members available.</p>
          )}
          {(allInstMembers || []).map((m) => (
            <label key={m.user_id}
              className="flex items-center gap-3 cursor-pointer border border-slate-200 p-2.5 hover:border-[#0F2847]"
              data-testid={TID.deptPickMember(m.user_id)}>
              <input type="checkbox" checked={selected.has(m.user_id)}
                onChange={() => toggle(m.user_id)} />
              <MemberAvatar name={m.user?.full_name} size="sm" />
              <div className="flex-1 min-w-0">
                <div className="text-sm text-slate-900">{m.user?.full_name || m.user_id}</div>
                <div className="text-[10px] font-mono text-slate-500">{userTypeLabel(m.user)}</div>
              </div>
              <span className="overline text-[#0F2847] text-[9px]">
                {ROLE_LABEL[m.role] || m.role}
              </span>
            </label>
          ))}
        </div>
        <div className="border-t border-slate-200 px-5 py-3 flex justify-end gap-2">
          <button onClick={onClose} className="text-xs border border-slate-200 px-3 py-2">Cancel</button>
          <button onClick={save} disabled={busy}
            className="text-xs bg-[#0F2847] text-white px-4 py-2 hover:opacity-90 disabled:opacity-50 inline-flex items-center gap-1.5"
            data-testid={TID.deptSaveMembersBtn}>
            {busy && <Loader2 size={11} className="animate-spin" />} Save
          </button>
        </div>
      </div>
    </div>
  );
}

function FacultyTab({ did, iid, isAdmin }) {
  const { data: members, loading, refetch } = useDeptMembers(did);
  const [showManage,   setShowManage]   = useState(false);
  const [allInstMem,   setAllInstMem]   = useState([]);
  const { updateRole, busy: roleBusy } = useDeptMutations();

  const openManage = useCallback(async () => {
    const { default: api } = await import("../lib/api");
    try {
      const { data } = await api.get(`/institutions/${iid}/members?status=approved`);
      setAllInstMem(data || []);
      setShowManage(true);
    } catch {
      toast.error("Failed to load institution members");
    }
  }, [iid]);

  const handleRoleChange = useCallback(async (uid, role) => {
    try {
      await updateRole(did, uid, role);
      toast.success("Role updated");
      refetch();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    }
  }, [did, updateRole, refetch]);

  const memberList = Array.isArray(members) ? members : [];
  const currentIds = memberList.map((m) => m.user_id);

  if (loading) return <div className="py-8 flex justify-center"><Spinner size={16} /></div>;

  return (
    <div className="space-y-4">
      <SectionHeader
        label={`Faculty & Staff (${memberList.length})`}
        icon={Users}
        action={isAdmin && (
          <button onClick={openManage} data-testid={TID.deptManageMembersBtn}
            className="text-xs flex items-center gap-1.5 border border-slate-200 px-3 py-1.5 hover:border-[#0F2847]">
            <UserPlus size={11} /> Manage
          </button>
        )}
      />
      {memberList.length === 0 && (
        <EmptyState icon={Users} message="No faculty members yet."
          action={isAdmin && <button onClick={openManage} className="text-xs text-[#0F2847] underline">Add faculty</button>} />
      )}
      <div className="grid sm:grid-cols-2 gap-3" data-testid={TID.deptFacultyList}>
        {memberList.map((m) => (
          <div key={m.user_id} className="border border-slate-200 bg-white p-4 flex items-center gap-3"
            data-testid={TID.deptFacultyCard(m.user_id)}>
            <MemberAvatar name={m.user?.full_name} />
            <div className="flex-1 min-w-0">
              <Link to={`/profile/${m.user_id}`}
                className="font-serif text-sm text-slate-900 hover:text-[#0F2847] truncate block">
                {m.user?.full_name || m.user_id}
              </Link>
              <div className="text-[10px] font-mono text-slate-500 truncate">
                {userTypeLabel(m.user)}
              </div>
              {(m.user?.h_index > 0 || m.user?.citations > 0) && (
                <div className="text-[10px] text-slate-400 mt-0.5">
                  {m.user?.h_index > 0 && `h-index: ${m.user.h_index}`}
                  {m.user?.citations > 0 && ` · ${m.user.citations.toLocaleString()} citations`}
                </div>
              )}
            </div>
            {isAdmin ? (
              <select
                value={m.role}
                onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                disabled={roleBusy}
                className="text-[10px] border border-slate-200 px-1.5 py-1 focus:outline-none text-[#0F2847]"
              >
                <option value="researcher">Faculty Member</option>
                <option value="research_lead">Research Coordinator</option>
                <option value="unit_admin">Dept Admin</option>
              </select>
            ) : (
              <span className="text-[10px] overline text-[#0F2847]">
                {ROLE_LABEL[m.role] || m.role}
              </span>
            )}
          </div>
        ))}
      </div>
      {showManage && (
        <ManageMembersModal
          did={did} iid={iid}
          allInstMembers={allInstMem}
          currentMemberIds={currentIds}
          onClose={() => setShowManage(false)}
          onChanged={refetch}
        />
      )}
    </div>
  );
}

// ─────────────────────────── Projects Tab ─────────────────────────────────────

function ProjectsTab({ did, isAdmin }) {
  const { data: projects, loading, refetch } = useDeptProjects(did);
  const { linkProject, unlinkProject, busy } = useDeptMutations();
  const [linkInput, setLinkInput] = useState("");
  const [showLink,  setShowLink]  = useState(false);

  const handleLink = useCallback(async () => {
    if (!linkInput.trim()) return;
    try {
      await linkProject(did, linkInput.trim());
      toast.success("Project linked");
      setLinkInput(""); setShowLink(false);
      refetch();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to link project");
    }
  }, [did, linkInput, linkProject, refetch]);

  const handleUnlink = useCallback(async (pid) => {
    if (!window.confirm("Unlink this project from the department?")) return;
    try {
      await unlinkProject(did, pid);
      toast.success("Project unlinked");
      refetch();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    }
  }, [did, unlinkProject, refetch]);

  const list = Array.isArray(projects) ? projects : [];

  if (loading) return <div className="py-8 flex justify-center"><Spinner size={16} /></div>;

  return (
    <div className="space-y-4">
      <SectionHeader
        label={`Department Projects (${list.length})`}
        icon={FolderOpen}
        action={isAdmin && (
          <button onClick={() => setShowLink((s) => !s)}
            className="text-xs flex items-center gap-1.5 border border-slate-200 px-3 py-1.5 hover:border-[#0F2847]"
            data-testid={TID.deptLinkProjectBtn}>
            <Plus size={11} /> Link Project
          </button>
        )}
      />

      {showLink && (
        <div className="border border-slate-200 bg-white p-4 flex gap-2">
          <input
            value={linkInput}
            onChange={(e) => setLinkInput(e.target.value)}
            placeholder="Project ID"
            className="flex-1 border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847]"
            data-testid={TID.deptLinkProjectInput}
          />
          <button onClick={handleLink} disabled={busy || !linkInput.trim()}
            className="text-xs bg-[#0F2847] text-white px-3 py-2 disabled:opacity-50">
            {busy ? <Loader2 size={11} className="animate-spin" /> : <Check size={13} />}
          </button>
          <button onClick={() => setShowLink(false)} className="text-xs border border-slate-200 px-2 py-2">
            <X size={13} />
          </button>
        </div>
      )}

      {list.length === 0 && (
        <EmptyState icon={FolderOpen} message="No projects linked to this department."
          action={isAdmin && (
            <button onClick={() => setShowLink(true)} className="text-xs text-[#0F2847] underline">
              Link a project
            </button>
          )} />
      )}

      <div className="grid sm:grid-cols-2 gap-4" data-testid={TID.deptProjectsList}>
        {list.map((p) => (
          <div key={p.project_id}
            className="border border-slate-200 bg-white p-4"
            data-testid={TID.deptProjectCard(p.project_id)}>
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <Link to={`/projects/${p.project_id}`}
                  className="font-serif text-sm text-slate-900 hover:text-[#0F2847] truncate block">
                  {p.title}
                </Link>
                {p.description && (
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2">{p.description}</p>
                )}
              </div>
              {isAdmin && (
                <button onClick={() => handleUnlink(p.project_id)}
                  className="text-slate-300 hover:text-red-500 transition-colors shrink-0"
                  data-testid={TID.deptUnlinkProjectBtn(p.project_id)}>
                  <Trash2 size={13} strokeWidth={1.5} />
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-1 mt-2">
              {(p.keywords || []).map((k) => (
                <ResearchTag key={k} label={k} />
              ))}
            </div>
            <div className="text-[10px] text-slate-400 mt-2">
              {p.team_size} member{p.team_size !== 1 ? "s" : ""} ·{" "}
              <span className={p.visibility === "public" ? "text-green-700" : "text-slate-400"}>
                {p.visibility}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────── Research Outputs Tab ─────────────────────────────

function OutputsTab({ did }) {
  const { data, loading } = useDeptPublications(did);
  const pubs = data?.publications || [];

  if (loading) return <div className="py-8 flex justify-center"><Spinner size={16} /></div>;

  return (
    <div className="space-y-4">
      <SectionHeader
        label={`Publications (${(data?.total || 0).toLocaleString()})`}
        icon={BookOpen}
      />
      {pubs.length === 0 && (
        <EmptyState icon={BookOpen} message="No publications found for this department's members." />
      )}
      <div className="space-y-3" data-testid={TID.deptPublicationsList}>
        {pubs.map((p) => (
          <div key={p.id} className="border border-slate-200 bg-white p-4"
            data-testid={TID.deptPublicationRow(p.id)}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 line-clamp-2">{p.title}</p>
                <div className="flex items-center gap-3 mt-1 text-xs text-slate-500 flex-wrap">
                  {p.year && <span>{p.year}</span>}
                  {p.journal && <span>· {p.journal}</span>}
                  {p.author && <span>· {p.author}</span>}
                </div>
                {(p.topics || []).length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {p.topics.map((t) => <ResearchTag key={t} label={t} />)}
                  </div>
                )}
              </div>
              <div className="text-right shrink-0">
                <div className="font-serif text-2xl text-[#0F2847]">
                  {(p.citations || 0).toLocaleString()}
                </div>
                <div className="text-[10px] text-slate-400">citations</div>
                {p.doi && (
                  <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noreferrer"
                    className="inline-flex items-center gap-0.5 text-[10px] text-slate-400 hover:text-[#0F2847] mt-1">
                    DOI <ExternalLink size={9} />
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────── Funding Tab ──────────────────────────────────────

function FundingTab({ did }) {
  const { data, loading } = useDeptFunding(did);

  if (loading) return <div className="py-8 flex justify-center"><Spinner size={16} /></div>;

  const byStatus  = data?.by_status  || [];
  const topGrants = data?.top_grants || [];
  const totalUsd  = data?.total_usd  || 0;

  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-3 gap-4">
        <Kpi label="Awarded Funding" value={`$${(totalUsd / 1000).toFixed(0)}k`} icon={Coins} highlight />
        {byStatus.map((s) => (
          <Kpi key={s.status} label={s.status} value={s.n} icon={Coins}
            sub={s.usd ? `$${(s.usd / 1000).toFixed(0)}k` : undefined} />
        ))}
      </div>

      <SectionHeader label="Top Awarded Grants" icon={Coins} />
      {topGrants.length === 0 && (
        <EmptyState icon={Coins} message="No awarded grants found for this department's members." />
      )}
      <div className="space-y-3" data-testid={TID.deptGrantsList}>
        {topGrants.map((g) => (
          <div key={g.id} className="border border-slate-200 bg-white p-4 flex items-center justify-between gap-4"
            data-testid={TID.deptGrantRow(g.id)}>
            <div>
              <p className="text-sm font-medium text-slate-900">{g.title}</p>
              <p className="text-xs text-slate-500 mt-0.5">{g.researcher}</p>
            </div>
            <div className="text-right shrink-0">
              <div className="font-serif text-xl text-[#0F2847]">
                ${(g.amount_usd / 1000).toFixed(0)}k
              </div>
              <div className="text-[10px] text-green-700">{g.status}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────── Statistics Tab ───────────────────────────────────

function StatisticsTab({ metrics }) {
  const m = metrics || {};
  const rows = [
    ["Total Publications",  m.publications,   "ORCID-imported"],
    ["Platform Manuscripts", m.manuscripts,   "Written on SYNAPTIQ"],
    ["In Progress",         m.manuscripts_wip, "Active manuscripts"],
    ["Total Citations",     m.total_citations?.toLocaleString(), "Sum across all publications"],
    ["Avg Citations / Pub", m.avg_citations,   "Mean citations per publication"],
    ["Avg h-index",         m.avg_h_index,     "Mean h-index across faculty"],
    ["Max h-index",         m.max_h_index,     "Highest individual h-index"],
    ["Avg Reputation Score",m.avg_reputation,  "Mean reputation across faculty"],
    ["Total Grants",        m.grants_total,    "All grant applications"],
    ["Grants Awarded",      m.grants_awarded,  "Successful applications"],
    ["Funding Awarded",     m.funding_usd ? `$${(m.funding_usd / 1000).toFixed(0)}k` : "—", "Total awarded value"],
    ["Linked Projects",     m.dept_projects,   "Projects linked to this department"],
    ["Collaborations",      m.collaborations,  "Accepted collaboration requests"],
  ];

  return (
    <div className="border border-slate-200 bg-white" data-testid={TID.deptStatisticsTable}>
      <div className="overline px-5 pt-5 pb-3 border-b border-slate-100">Publication & Research Statistics</div>
      <table className="w-full text-sm">
        <tbody>
          {rows.map(([label, value, note]) => (
            <tr key={label} className="border-b border-slate-50 last:border-0">
              <td className="px-5 py-3 text-slate-700 font-medium w-48">{label}</td>
              <td className="px-5 py-3 font-serif text-slate-900">{value ?? "—"}</td>
              <td className="px-5 py-3 text-xs text-slate-400 hidden sm:table-cell">{note}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─────────────────────────── Rankings Tab ─────────────────────────────────────

function RankingsTab({ did }) {
  const { data, loading } = useDeptRankings(did);

  if (loading) return <div className="py-8 flex justify-center"><Spinner size={16} /></div>;

  const rankings = data?.rankings || [];
  if (rankings.length === 0) {
    return <EmptyState icon={Award} message="No departments to rank yet." />;
  }

  return (
    <div className="space-y-4">
      <div className="text-xs text-slate-500 border border-amber-100 bg-amber-50 p-3">
        Rankings are computed across all departments in the institution using a composite score:
        30% Citations · 25% Publications · 20% Reputation · 15% Funding · 10% Projects.
        Scores are normalised within the institution.
      </div>
      <div className="border border-slate-200 bg-white" data-testid={TID.deptRankingsTable}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="px-5 py-3 text-left overline text-slate-500 font-normal">#</th>
              <th className="px-5 py-3 text-left overline text-slate-500 font-normal">Department</th>
              <th className="px-5 py-3 text-right overline text-slate-500 font-normal hidden sm:table-cell">Citations</th>
              <th className="px-5 py-3 text-right overline text-slate-500 font-normal hidden md:table-cell">Publications</th>
              <th className="px-5 py-3 text-right overline text-slate-500 font-normal hidden md:table-cell">Reputation</th>
              <th className="px-5 py-3 text-right overline text-slate-500 font-normal">Score</th>
            </tr>
          </thead>
          <tbody>
            {rankings.map((r) => (
              <tr key={r.department_id}
                className={`border-b border-slate-50 last:border-0 ${r.is_current ? "bg-[#0F2847]/5" : ""}`}
                data-testid={TID.deptRankingRow(r.department_id)}>
                <td className="px-5 py-3">
                  <span className={`font-serif text-lg ${r.rank === 1 ? "text-amber-500" : r.rank === 2 ? "text-slate-400" : r.rank === 3 ? "text-amber-700" : "text-slate-300"}`}>
                    #{r.rank}
                  </span>
                </td>
                <td className="px-5 py-3">
                  <Link to={`/institution/departments/${r.department_id}`}
                    className={`text-sm hover:text-[#0F2847] ${r.is_current ? "font-semibold text-[#0F2847]" : "text-slate-900"}`}>
                    {r.name}
                    {r.is_current && <span className="ml-2 overline text-[9px] text-[#0F2847]">You</span>}
                  </Link>
                </td>
                <td className="px-5 py-3 text-right text-slate-700 hidden sm:table-cell">
                  {(r.metrics?.total_citations || 0).toLocaleString()}
                </td>
                <td className="px-5 py-3 text-right text-slate-700 hidden md:table-cell">
                  {r.metrics?.publications || 0}
                </td>
                <td className="px-5 py-3 text-right text-slate-700 hidden md:table-cell">
                  {r.metrics?.avg_reputation || 0}
                </td>
                <td className="px-5 py-3 text-right">
                  <span className={`font-serif text-base ${r.is_current ? "text-[#0F2847]" : "text-slate-900"}`}>
                    {Math.round((r.score || 0) * 100)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─────────────────────────── Network Tab ──────────────────────────────────────

function NetworkTab({ did }) {
  const { data, loading } = useDeptCollaboration(did);

  if (loading) return <div className="py-8 flex justify-center"><Spinner size={16} /></div>;

  const network = data?.network || [];

  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-3 gap-4">
        <Kpi label="Internal Collaborations" value={data?.internal ?? "—"} icon={Users} highlight
          sub="Between dept members" />
        <Kpi label="External Collaborations" value={data?.external ?? "—"} icon={Network}
          sub="With researchers outside dept" />
        <Kpi label="Network Connections" value={network.length} icon={Network} />
      </div>

      {network.length === 0 && (
        <EmptyState icon={Network} message="No collaboration data yet for this department's members." />
      )}

      {network.length > 0 && (
        <div className="border border-slate-200 bg-white p-5" data-testid={TID.deptNetworkList}>
          <div className="overline mb-4">Top Collaboration Connections</div>
          <div className="space-y-2">
            {network.map((edge, i) => (
              <div key={i} className="flex items-center gap-3 border border-slate-100 p-3 text-sm">
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-slate-800 truncate">{edge.source_name}</span>
                  <span className="text-slate-400 mx-2">↔</span>
                  <span className="font-medium text-slate-800 truncate">{edge.target_name}</span>
                </div>
                <div className="text-right shrink-0">
                  <div className="font-serif text-lg text-[#0F2847]">{edge.weight}</div>
                  <div className="text-[9px] text-slate-400">
                    {edge.external ? "external" : "internal"}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────── Edit Department Modal ────────────────────────────

function EditDepartmentModal({ dept, onClose, onUpdated }) {
  const [form, setForm] = useState({
    name:           dept.name || "",
    description:    dept.description || "",
    research_areas: (dept.research_areas || []).join(", "),
    head_id:        dept.head_id || "",
  });
  const { updateDepartment, busy, error } = useDeptMutations();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const updated = await updateDepartment(dept.id, {
        name:           form.name || undefined,
        description:    form.description || undefined,
        research_areas: form.research_areas.split(",").map((s) => s.trim()).filter(Boolean),
        head_id:        form.head_id || undefined,
      });
      toast.success("Department updated");
      onUpdated?.(updated);
      onClose?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    }
  };

  return (
    <div className="fixed inset-0 z-[100] bg-slate-900/50 flex items-center justify-center px-4"
      onClick={onClose} data-testid={TID.deptEditModal}>
      <div className="bg-white w-full max-w-lg border border-slate-200"
        onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <h3 className="font-serif text-xl text-slate-900">Edit Department</h3>
          <button onClick={onClose}><X size={16} strokeWidth={1.5} /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && <div className="text-xs text-red-700 border border-red-100 bg-red-50 p-3">{error}</div>}
          {[
            ["Name",           "name",           "text", "e.g. Dept of Computer Science"],
            ["Description",    "description",    "text", "Brief description"],
            ["Research Areas", "research_areas", "text", "Comma-separated"],
            ["Head User ID",   "head_id",        "text", "User ID of department head"],
          ].map(([label, key, type, placeholder]) => (
            <div key={key}>
              <label className="text-xs font-medium text-slate-700 block mb-1">{label}</label>
              <input type={type} value={form[key]}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                placeholder={placeholder}
                className="w-full border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847]" />
            </div>
          ))}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose}
              className="text-xs border border-slate-200 px-3 py-2">Cancel</button>
            <button type="submit" disabled={busy}
              className="text-xs bg-[#0F2847] text-white px-4 py-2 hover:opacity-90 disabled:opacity-50 inline-flex items-center gap-1.5"
              data-testid={TID.deptEditSubmit}>
              {busy && <Loader2 size={11} className="animate-spin" />} Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─────────────────────────── Main page ───────────────────────────────────────

export default function DepartmentDetail() {
  const { did }           = useParams();
  const { user }          = useAuth();
  const [tab, setTab]     = useState("overview");
  const [showEdit, setShowEdit] = useState(false);
  const [refreshMetrics, setRefreshMetrics] = useState(false);

  const { data: dept,    loading: deptLoading,    refetch: refetchDept }    = useDepartment(did);
  const { data: metrics, loading: metricsLoading, refetch: refetchMetrics } = useDeptMetrics(did, refreshMetrics);

  const isAdmin = useMemo(() => {
    if (!dept) return false;
    if (user?.role === "admin") return true;
    if ((dept.admin_ids || []).includes(user?.id)) return true;
    if (dept.head_id === user?.id) return true;
    return dept.is_admin || false;
  }, [dept, user]);

  const handleRefreshMetrics = useCallback(() => {
    setRefreshMetrics(true);
    refetchMetrics();
    setTimeout(() => setRefreshMetrics(false), 1000);
  }, [refetchMetrics]);

  if (deptLoading) {
    return (
      <div className="text-sm text-slate-500 font-mono py-16 text-center">
        <Loader2 size={14} className="animate-spin inline mr-2" />Loading department…
      </div>
    );
  }

  if (!dept) {
    return (
      <div className="border border-red-100 bg-red-50 p-6 text-sm text-red-700">
        Department not found or you don't have access.
      </div>
    );
  }

  const iid = dept.institution_id;

  return (
    <div className="space-y-6" data-testid={TID.deptDetailPage(did)}>

      {/* Breadcrumb */}
      <nav className="text-xs text-slate-500 flex items-center gap-1 flex-wrap">
        <Link to={`/institutions/${iid}`} className="hover:text-[#0F2847]">
          {dept.institution?.name || "Institution"}
        </Link>
        <ChevronRight size={10} strokeWidth={1.5} />
        <Link to="/institution/departments" className="hover:text-[#0F2847]">Departments</Link>
        <ChevronRight size={10} strokeWidth={1.5} />
        <span className="text-slate-900">{dept.name}</span>
      </nav>

      {/* Header */}
      <header className="border-b border-slate-200 pb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="overline text-[#0F2847] mb-1">Department</div>
            <h1 className="font-serif text-4xl text-slate-900 leading-tight" data-testid={TID.deptName}>
              {dept.name}
            </h1>
            {dept.institution?.name && (
              <Link to={`/institutions/${iid}`}
                className="text-sm text-slate-500 hover:text-[#0F2847] mt-1 block">
                {dept.institution.name}
              </Link>
            )}
            {dept.head && (
              <p className="text-sm text-slate-600 mt-2">
                Head: <Link to={`/profile/${dept.head.id}`} className="font-medium hover:text-[#0F2847]">
                  {dept.head.full_name}
                </Link>
                {dept.head.role && <span className="text-slate-400"> · {dept.head.role}</span>}
              </p>
            )}
            {(dept.research_areas || []).length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {dept.research_areas.map((a) => <ResearchTag key={a} label={a} />)}
              </div>
            )}
          </div>
          {isAdmin && (
            <button onClick={() => setShowEdit(true)}
              className="shrink-0 text-xs flex items-center gap-1.5 border border-slate-200 px-3 py-2 hover:border-[#0F2847]"
              data-testid={TID.deptEditBtn}>
              <Edit3 size={11} /> Edit
            </button>
          )}
        </div>
      </header>

      {/* Tabs */}
      <div className="flex items-center gap-0.5 border-b border-slate-200 overflow-x-auto" data-testid={TID.deptTabs}>
        {TAB_LIST.map((t) => {
          const { label, icon: Icon } = TAB_META[t];
          return (
            <button key={t} onClick={() => setTab(t)}
              data-testid={TID.deptTab(t)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm -mb-px border-b-2 transition-colors whitespace-nowrap ${
                tab === t
                  ? "border-[#0F2847] text-[#0F2847]"
                  : "border-transparent text-slate-500 hover:text-slate-900"
              }`}>
              <Icon size={12} strokeWidth={1.5} />
              {label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div>
        {tab === "overview"    && <OverviewTab dept={dept} metrics={metrics} metricsLoading={metricsLoading} onRefreshMetrics={handleRefreshMetrics} isAdmin={isAdmin} />}
        {tab === "faculty"     && <FacultyTab did={did} iid={iid} isAdmin={isAdmin} />}
        {tab === "projects"    && <ProjectsTab did={did} isAdmin={isAdmin} />}
        {tab === "outputs"     && <OutputsTab did={did} />}
        {tab === "funding"     && <FundingTab did={did} />}
        {tab === "statistics"  && <StatisticsTab metrics={metrics} />}
        {tab === "rankings"    && <RankingsTab did={did} />}
        {tab === "network"     && <NetworkTab did={did} />}
      </div>

      {showEdit && (
        <EditDepartmentModal
          dept={dept}
          onClose={() => setShowEdit(false)}
          onUpdated={() => { refetchDept(); handleRefreshMetrics(); }}
        />
      )}
    </div>
  );
}

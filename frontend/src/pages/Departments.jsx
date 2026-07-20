/**
 * Departments — department directory for the current user's institution.
 * Route: /institution/departments
 *
 * Gate: institution plan (checked server-side). Shows upgrade prompt for
 * users without an institution or whose institution lacks the plan.
 */
import React, { useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import {
  Building2, Users, FolderOpen, Lock, Plus, Search, ChevronRight,
  Loader2, BookOpen, Coins, X, Award, Layers,
} from "lucide-react";
import { TID } from "../lib/testIds";
import { useDepartments, useDeptMutations } from "../hooks/useDepartments";
import { NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";

// ─────────────────────────── primitives ──────────────────────────────────────

function Kpi({ label, value, icon: Icon }) {
  return (
    <div className="border border-slate-200 bg-white p-4">
      <div className="overline flex items-center gap-1.5">
        <Icon size={11} strokeWidth={1.5} className="text-[#0F2847]" />
        {label}
      </div>
      <div className="font-serif text-3xl text-slate-900 mt-1">{value ?? "—"}</div>
    </div>
  );
}

function ResearchAreaTag({ label }) {
  return (
    <span className="text-[10px] font-mono border border-[#0F2847]/30 bg-[#0F2847]/5 text-[#0F2847] px-1.5 py-0.5">
      {label}
    </span>
  );
}

// ─────────────────────────── no-institution state ─────────────────────────────

function NoInstitutionWall() {
  return (
    <div className="space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <div className="overline">Institution</div>
        <h1 className="font-serif text-5xl text-slate-900 mt-2">Departments</h1>
      </header>
      <div className="border border-slate-200 bg-white p-16 flex flex-col items-center text-center gap-5">
        <Building2 size={28} strokeWidth={1} className="text-slate-300" />
        <div>
          <div className="overline text-[#0F2847] mb-2">Institution membership required</div>
          <h2 className="font-serif text-2xl text-slate-900">You're not part of an institution yet</h2>
          <p className="text-slate-500 text-sm mt-3 max-w-sm mx-auto">
            Join your university or research institute to access Department Management, faculty directories, and research output analytics.
          </p>
        </div>
        <Link
          to="/institutions"
          className="inline-block bg-[#0F2847] text-white text-sm px-6 py-2.5 hover:opacity-90 transition-opacity"
        >
          Find Your Institution
        </Link>
      </div>
    </div>
  );
}

function UpgradeWall({ institutionName }) {
  return (
    <div className="space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <div className="overline">Institution</div>
        <h1 className="font-serif text-5xl text-slate-900 mt-2">Departments</h1>
        {institutionName && <p className="text-slate-500 mt-2 text-sm">{institutionName}</p>}
      </header>
      <div className="border border-slate-200 bg-white p-16 flex flex-col items-center text-center gap-5">
        <Lock size={28} strokeWidth={1} className="text-slate-300" />
        <div>
          <div className="overline text-[#0F2847] mb-2">Institution plan required</div>
          <h2 className="font-serif text-2xl text-slate-900">Department Management is a premium feature</h2>
          <p className="text-slate-500 text-sm mt-3 max-w-md mx-auto">
            Ask your institution admin to upgrade to the Institution plan to unlock Department Management, faculty directories, publication statistics, and research ranking dashboards.
          </p>
        </div>
        <Link
          to="/pricing"
          className="inline-block bg-[#0F2847] text-white text-sm px-6 py-2.5 hover:opacity-90 transition-opacity"
        >
          View Plans
        </Link>
      </div>
    </div>
  );
}

// ─────────────────────────── create department modal ─────────────────────────

function CreateDepartmentModal({ institutionId, onClose, onCreated }) {
  const [form, setForm] = useState({
    name:           "",
    description:    "",
    research_areas: "",
    head_id:        "",
  });
  const { createDepartment, busy, error } = useDeptMutations();

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    const areas = form.research_areas
      .split(",").map((s) => s.trim()).filter(Boolean);
    try {
      const dept = await createDepartment(institutionId, {
        name:           form.name,
        description:    form.description || undefined,
        research_areas: areas,
        head_id:        form.head_id || undefined,
      });
      toast.success(`Department "${dept.name}" created`);
      onCreated?.(dept);
      onClose?.();
    } catch {
      // error surfaced via hook
    }
  }, [form, institutionId, createDepartment, onCreated, onClose]);

  return (
    <div className="fixed inset-0 z-[100] bg-slate-900/50 flex items-center justify-center px-4"
      onClick={onClose} data-testid={TID.deptCreateModal}>
      <div className="bg-white w-full max-w-lg border border-slate-200"
        onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <h3 className="font-serif text-xl text-slate-900">New Department</h3>
          <button onClick={onClose}><X size={16} strokeWidth={1.5} /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="text-xs text-red-700 border border-red-100 bg-red-50 p-3">{
              typeof error === "string" ? error : JSON.stringify(error)
            }</div>
          )}
          <div>
            <label className="text-xs font-medium text-slate-700 block mb-1">
              Department Name <span className="text-red-500">*</span>
            </label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Department of Computer Science"
              className="w-full border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847]"
              data-testid={TID.deptNameInput}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-700 block mb-1">Description</label>
            <textarea
              rows={3}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Brief description of the department's research focus"
              className="w-full border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847] resize-none"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-700 block mb-1">
              Research Areas <span className="text-slate-400">(comma-separated)</span>
            </label>
            <input
              value={form.research_areas}
              onChange={(e) => setForm((f) => ({ ...f, research_areas: e.target.value }))}
              placeholder="Machine Learning, Computer Vision, NLP"
              className="w-full border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847]"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-700 block mb-1">
              Department Head <span className="text-slate-400">(user ID, optional)</span>
            </label>
            <input
              value={form.head_id}
              onChange={(e) => setForm((f) => ({ ...f, head_id: e.target.value }))}
              placeholder="Leave blank to assign later"
              className="w-full border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847]"
            />
          </div>
          <div className="flex items-center justify-end gap-2 pt-2">
            <button type="button" onClick={onClose}
              className="text-xs text-slate-600 px-3 py-2 border border-slate-200 hover:border-slate-400">
              Cancel
            </button>
            <button type="submit" disabled={busy || !form.name.trim()}
              className="text-xs bg-[#0F2847] text-white px-4 py-2 hover:opacity-90 disabled:opacity-50 inline-flex items-center gap-1.5"
              data-testid={TID.deptCreateSubmit}>
              {busy && <Loader2 size={11} className="animate-spin" />}
              Create Department
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─────────────────────────── department card ──────────────────────────────────

function DeptCard({ dept }) {
  return (
    <Link
      to={`/institution/departments/${dept.id}`}
      data-testid={TID.deptCard(dept.id)}
      className="block border border-slate-200 bg-white p-5 hover:border-[#0F2847] transition-colors"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-serif text-lg text-slate-900 leading-tight">{dept.name}</h3>
          {dept.head_name && (
            <p className="text-xs text-slate-500 mt-0.5">Head: {dept.head_name}</p>
          )}
        </div>
        <ChevronRight size={14} strokeWidth={1.5} className="text-slate-400 shrink-0 mt-1" />
      </div>
      {dept.description && (
        <p className="text-sm text-slate-600 line-clamp-2 mb-3">{dept.description}</p>
      )}
      {(dept.research_areas || []).length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {dept.research_areas.slice(0, 4).map((a) => (
            <ResearchAreaTag key={a} label={a} />
          ))}
          {dept.research_areas.length > 4 && (
            <span className="text-[10px] text-slate-400">+{dept.research_areas.length - 4} more</span>
          )}
        </div>
      )}
      <div className="flex items-center gap-4 text-xs text-slate-500 border-t border-slate-100 pt-3 mt-1">
        <span className="inline-flex items-center gap-1">
          <Users size={10} strokeWidth={1.5} /> {dept.member_count} member{dept.member_count !== 1 ? "s" : ""}
        </span>
        <span className="inline-flex items-center gap-1">
          <FolderOpen size={10} strokeWidth={1.5} /> {dept.project_count} project{dept.project_count !== 1 ? "s" : ""}
        </span>
      </div>
    </Link>
  );
}

// ─────────────────────────── main page ────────────────────────────────────────

export default function Departments() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [query,        setQuery]      = useState("");
  const [showCreate,   setShowCreate] = useState(false);

  const institutionId = user?.institution_id;

  const { data: departments, loading, error, refetch } = useDepartments(institutionId, query);

  // Gate detection from API error
  const isNoInst   = !institutionId;
  const is402      = error && (
    (typeof error === "object" && error?.code === "institution_plan_required") ||
    (typeof error === "string" && error.includes("Institution plan"))
  );

  const isAdmin = ["admin", "owner"].includes(user?.role) ||
    (user?.institution_membership?.role && ["owner", "admin"].includes(user.institution_membership.role));

  const handleCreated = useCallback(() => {
    refetch();
  }, [refetch]);

  if (isNoInst)  return <NoInstitutionWall />;
  if (is402)     return <UpgradeWall />;

  const depts = Array.isArray(departments) ? departments : [];

  const totalMembers  = depts.reduce((s, d) => s + (d.member_count || 0), 0);
  const totalProjects = depts.reduce((s, d) => s + (d.project_count || 0), 0);

  return (
    <ResearchLayout
      title="Departments"
      subtitle="Manage academic departments, faculty, research outputs, and funding for your institution."
      actions={isAdmin && (
        <button
          onClick={() => setShowCreate(true)}
          data-testid={TID.deptCreateBtn}
          className="shrink-0 flex items-center gap-1.5 text-xs bg-[#0F2847] text-white px-4 py-2.5 hover:opacity-90 transition-opacity"
        >
          <Plus size={12} /> New Department
        </button>
      )}
    >
    <div className="space-y-8" data-testid={TID.departmentsPage}>

      {/* Summary KPIs */}
      {!loading && depts.length > 0 && (
        <section>
          <div className="grid sm:grid-cols-3 gap-4">
            <Kpi label="Departments"        value={depts.length}   icon={Layers} />
            <Kpi label="Total Faculty"      value={totalMembers}   icon={Users} />
            <Kpi label="Linked Projects"    value={totalProjects}  icon={FolderOpen} />
          </div>
        </section>
      )}

      {/* Search */}
      <section>
        <div className="relative max-w-sm">
          <Search size={13} strokeWidth={1.5}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search departments…"
            className="w-full pl-9 pr-3 py-2 border border-slate-200 text-sm focus:outline-none focus:border-[#0F2847]"
            data-testid={TID.deptSearch}
          />
        </div>
      </section>

      {/* Department grid */}
      <section data-testid={TID.deptGrid}>
        {loading && (
          <div className="text-sm text-slate-500 font-mono py-12 text-center flex items-center justify-center gap-2">
            <Loader2 size={14} className="animate-spin" /> Loading departments…
          </div>
        )}

        {!loading && error && !is402 && (
          <div className="border border-red-100 bg-red-50 p-5 text-sm text-red-700">
            Failed to load departments:{" "}
            {typeof error === "object" ? (error?.message || JSON.stringify(error)) : error}
          </div>
        )}

        {!loading && !error && depts.length === 0 && (
          <div className="border border-dashed border-slate-200 bg-white p-14 text-center"
            data-testid={TID.deptEmpty}>
            <Layers size={24} strokeWidth={1} className="text-slate-300 mx-auto mb-3" />
            <p className="text-sm text-slate-500">
              {query ? "No departments match your search." : "No departments yet."}
            </p>
            {!query && isAdmin && (
              <button
                onClick={() => setShowCreate(true)}
                className="mt-4 text-xs text-[#0F2847] underline underline-offset-2"
              >
                Create the first department
              </button>
            )}
          </div>
        )}

        {!loading && depts.length > 0 && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {depts.map((d) => <DeptCard key={d.id} dept={d} />)}
          </div>
        )}
      </section>

      {/* Create modal */}
      {showCreate && (
        <CreateDepartmentModal
          institutionId={institutionId}
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
    </ResearchLayout>
  );
}

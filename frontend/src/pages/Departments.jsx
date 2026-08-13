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
  Award, Layers,
} from "lucide-react";
import { TID } from "../lib/testIds";
import { useDepartments, useDeptMutations } from "../hooks/useDepartments";
import { ResearchLayout } from "@/layouts";
import {
  StatCard, StatGrid, Tag, TagGroup, Card, Modal, Input, Textarea, Button,
  Spinner, ErrorState, EmptyState,
} from "@/components/ds";

// ─────────────────────────── no-institution state ─────────────────────────────

function NoInstitutionWall() {
  return (
    <div className="space-y-6">
      <header className="border-b border-slate-200 pb-6">
        <div className="overline">Institution</div>
        <h1 className="font-serif text-5xl text-slate-900 mt-2">Departments</h1>
      </header>
      <EmptyState
        icon={<Building2 />}
        size="lg"
        title="You're not part of an institution yet"
        description="Join your university or research institute to access Department Management, faculty directories, and research output analytics."
        action={<Button as={Link} to="/institutions">Find Your Institution</Button>}
      />
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
      <EmptyState
        icon={<Lock />}
        size="lg"
        title="Department Management is a premium feature"
        description="Ask your institution admin to upgrade to the Institution plan to unlock Department Management, faculty directories, publication statistics, and research ranking dashboards."
        action={<Button as={Link} to="/pricing">View Plans</Button>}
      />
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
    <Modal
      open
      onClose={onClose}
      closeOnOverlay
      title="New Department"
      data-testid={TID.deptCreateModal}
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
          <Button
            type="submit"
            form="create-dept-form"
            size="sm"
            disabled={busy || !form.name.trim()}
            loading={busy}
            data-testid={TID.deptCreateSubmit}
          >
            Create Department
          </Button>
        </>
      }
    >
      <form id="create-dept-form" onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="text-xs text-red-700 border border-red-100 bg-red-50 p-3">{
            typeof error === "string" ? error : JSON.stringify(error)
          }</div>
        )}
        <Input
          required
          label="Department Name *"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          placeholder="e.g. Department of Computer Science"
          data-testid={TID.deptNameInput}
        />
        <Textarea
          label="Description"
          rows={3}
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          placeholder="Brief description of the department's research focus"
        />
        <Input
          label="Research Areas (comma-separated)"
          value={form.research_areas}
          onChange={(e) => setForm((f) => ({ ...f, research_areas: e.target.value }))}
          placeholder="Machine Learning, Computer Vision, NLP"
        />
        <Input
          label="Department Head (user ID, optional)"
          value={form.head_id}
          onChange={(e) => setForm((f) => ({ ...f, head_id: e.target.value }))}
          placeholder="Leave blank to assign later"
        />
      </form>
    </Modal>
  );
}

// ─────────────────────────── department card ──────────────────────────────────

function DeptCard({ dept }) {
  return (
    <Card to={`/institution/departments/${dept.id}`} data-testid={TID.deptCard(dept.id)} padding="lg">
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
        <TagGroup gap={4} className="mb-3">
          {dept.research_areas.slice(0, 4).map((a) => (
            <Tag key={a} size="sm">{a}</Tag>
          ))}
          {dept.research_areas.length > 4 && (
            <span className="text-[10px] text-slate-400">+{dept.research_areas.length - 4} more</span>
          )}
        </TagGroup>
      )}
      <div className="flex items-center gap-4 text-xs text-slate-500 border-t border-slate-100 pt-3 mt-1">
        <span className="inline-flex items-center gap-1">
          <Users size={10} strokeWidth={1.5} /> {dept.member_count} member{dept.member_count !== 1 ? "s" : ""}
        </span>
        <span className="inline-flex items-center gap-1">
          <FolderOpen size={10} strokeWidth={1.5} /> {dept.project_count} project{dept.project_count !== 1 ? "s" : ""}
        </span>
      </div>
    </Card>
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
        <Button onClick={() => setShowCreate(true)} data-testid={TID.deptCreateBtn} variant="hero">
          <Plus size={12} /> New Department
        </Button>
      )}
    >
    <div className="space-y-8" data-testid={TID.departmentsPage}>

      {/* Summary KPIs */}
      {!loading && depts.length > 0 && (
        <section>
          <StatGrid cols={3}>
            <StatCard label="Departments"        value={depts.length}   icon={<Layers />} />
            <StatCard label="Total Faculty"      value={totalMembers}   icon={<Users />} />
            <StatCard label="Linked Projects"    value={totalProjects}  icon={<FolderOpen />} />
          </StatGrid>
        </section>
      )}

      {/* Search */}
      <section>
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search departments…"
          prefix={<Search size={13} strokeWidth={1.5} />}
          wrapperClassName="max-w-sm"
          data-testid={TID.deptSearch}
        />
      </section>

      {/* Department grid */}
      <section data-testid={TID.deptGrid}>
        {loading && (
          <div className="py-12 flex justify-center"><Spinner size={16} /></div>
        )}

        {!loading && error && !is402 && (
          <ErrorState
            message="Failed to load departments"
            detail={typeof error === "object" ? (error?.message || JSON.stringify(error)) : error}
          />
        )}

        {!loading && !error && depts.length === 0 && (
          <EmptyState
            data-testid={TID.deptEmpty}
            icon={<Layers />}
            title={query ? "No departments match your search." : "No departments yet."}
            action={!query && isAdmin && (
              <Button variant="link" onClick={() => setShowCreate(true)}>
                Create the first department
              </Button>
            )}
          />
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

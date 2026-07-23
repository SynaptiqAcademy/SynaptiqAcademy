/**
 * UnitDetail — single unit page covering /research-centers/:id and /labs/:id
 * (a flexible unit type). Shows members, child units, and aggregate stats
 * scoped to this unit's member subset.
 */
import React, { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { userTypeLabel } from "../lib/userTypes";
import { SkeletonCard, Card, StatCard, StatGrid, EmptyState, Button, Modal } from "@/components/ds";
import {
  Layers, Users, Award, ChevronRight, UserPlus,
} from "lucide-react";

const TYPE_LABEL = {
  faculty: "Faculty", department: "Department", research_center: "Research center",
  lab: "Lab", institute: "Institute", school: "School", research_group: "Research group",
  other: "Unit",
};

export default function UnitDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [u, setU] = useState(null);
  const [children, setChildren] = useState([]);
  const [members, setMembers] = useState([]);
  const [allInstMembers, setAllInstMembers] = useState([]);
  const [editingMembers, setEditingMembers] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get(`/units/${id}`);
      setU(data);
      const [childRes, instMembersRes] = await Promise.all([
        api.get(`/institutions/${data.institution_id}/units?parent_id=${id}`),
        api.get(`/institutions/${data.institution_id}/members?status=approved`),
      ]);
      setChildren(childRes.data || []);
      setAllInstMembers(instMembersRes.data || []);
      setMembers((instMembersRes.data || []).filter((m) => (m.unit_ids || []).includes(id)));
    } catch (e) {
      toast.error("Unit not found");
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const isAdmin = useMemo(() => {
    if (!u) return false;
    if (user?.role === "admin") return true;
    if ((u.admin_ids || []).includes(user?.id)) return true;
    if (u.head_id === user?.id) return true;
    return false;
  }, [u, user]);

  // Aggregate stats from this subset of users
  const userIds = members.map((m) => m.user_id);
  const [stats, setStats] = useState(null);
  useEffect(() => {
    if (!userIds.length) { setStats({ publications: 0, workspaces: 0, grants: 0, manuscripts_open: 0 }); return; }
    // Reuse profile/users endpoints for counts — best-effort via batch
    api.post("/reputation/batch", { user_ids: userIds }).then(({ data }) => {
      const overalls = Object.values(data).map((r) => r.overall || 0);
      const avg = overalls.length ? overalls.reduce((a, b) => a + b, 0) / overalls.length : 0;
      setStats((s) => ({ ...(s || {}), reputation_avg: Math.round(avg * 10) / 10 }));
    }).catch(() => {});
  }, [members.length]);

  if (!u) return <div className="p-6"><SkeletonCard rows={4} /></div>;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="text-xs text-slate-500 flex items-center gap-1 flex-wrap" data-testid="unit-breadcrumb">
        {u.institution && (
          <Link to={`/institutions/${u.institution.id}`} className="hover:text-[#0F2847]">{u.institution.name}</Link>
        )}
        {(u.breadcrumb || []).map((b) => (
          <React.Fragment key={b.id}>
            <ChevronRight size={10} strokeWidth={1.5} />
            <Link to={`/units/${b.id}`} className="hover:text-[#0F2847]">{b.name}</Link>
          </React.Fragment>
        ))}
        <ChevronRight size={10} strokeWidth={1.5} />
        <span className="text-slate-900">{u.name}</span>
      </nav>

      <header className="border-b border-slate-200 pb-6 flex items-start justify-between gap-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="overline">{TYPE_LABEL[u.type] || u.type}</span>
            {u.institution && <Link to={`/institutions/${u.institution.id}`} className="overline text-slate-500 hover:text-[#0F2847]">· {u.institution.name}</Link>}
          </div>
          <h1 className="font-serif text-4xl text-slate-900 mt-1 leading-tight" data-testid="unit-name">{u.name}</h1>
          {u.description && <p className="text-sm text-slate-600 mt-2 max-w-3xl">{u.description}</p>}
          {(u.research_areas || []).length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {(u.research_areas || []).map((a, i) => (
                <span key={i} className="text-[10px] font-mono border border-[#0F2847]/30 bg-[#0F2847]/5 text-[#0F2847] px-1.5 py-0.5">{a}</span>
              ))}
            </div>
          )}
        </div>
        {isAdmin && (
          <Button data-testid="manage-unit-members-btn" variant="ghost" size="sm" onClick={() => setEditingMembers(true)}>
            <UserPlus size={11} strokeWidth={1.5} /> Manage members
          </Button>
        )}
      </header>

      {/* KPI */}
      <StatGrid cols={4} data-testid="unit-kpis">
        <StatCard label="Members" value={u.member_count} icon={<Users />} />
        <StatCard label="Sub-units" value={u.child_count} icon={<Layers />} />
        <StatCard label="Reputation avg" value={stats?.reputation_avg ?? "—"} icon={<Award />} />
        <StatCard label="Type" value={TYPE_LABEL[u.type]} icon={<Layers />} />
      </StatGrid>

      {/* Members */}
      <Card padding="lg">
        <div className="overline mb-3">Researchers in this {TYPE_LABEL[u.type]?.toLowerCase()}</div>
        {members.length === 0 && (
          <EmptyState data-testid="unit-members-empty" size="sm" dashed={false} title="No members yet." />
        )}
        <div className="grid sm:grid-cols-2 gap-2" data-testid="unit-members-list">
          {members.map((m) => (
            <Card key={m.user_id} to={`/profile/${m.user_id}`} padding="sm" data-testid={`unit-member-${m.user_id}`}>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-[#0F2847] text-white text-[10px] font-serif flex items-center justify-center">
                  {(m.user?.full_name || "").split(" ").map((p) => p[0]).filter(Boolean).slice(0,2).join("").toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-serif text-sm text-slate-900 truncate">{m.user?.full_name || m.user_id}</div>
                  <div className="text-[10px] font-mono text-slate-500 truncate">{userTypeLabel(m.user)}</div>
                </div>
                <span className="overline text-[#0F2847]">{m.role}</span>
              </div>
            </Card>
          ))}
        </div>
      </Card>

      {/* Sub-units */}
      {children.length > 0 && (
        <Card padding="lg">
          <div className="overline mb-3">Sub-units</div>
          <div className="grid sm:grid-cols-2 gap-3" data-testid="unit-children-list">
            {children.map((c) => (
              <Card key={c.id} to={`/units/${c.id}`} padding="sm">
                <span className="overline">{TYPE_LABEL[c.type] || c.type}</span>
                <div className="font-serif text-base text-slate-900 mt-1">{c.name}</div>
                <div className="text-[10px] font-mono text-slate-500">{c.member_count} members</div>
              </Card>
            ))}
          </div>
        </Card>
      )}

      <Modal
        open={editingMembers}
        onClose={() => setEditingMembers(false)}
        title={`Manage members — ${u.name}`}
        data-testid="manage-unit-members-modal"
      >
        {editingMembers && (
          <ManageMembersBody
            unit={u} allMembers={allInstMembers} currentIds={members.map((m) => m.user_id)}
            onClose={() => setEditingMembers(false)} onChanged={load}
          />
        )}
      </Modal>
    </div>
  );
}

function ManageMembersBody({ unit, allMembers, currentIds, onClose, onChanged }) {
  const [selected, setSelected] = useState(new Set(currentIds));
  const [busy, setBusy] = useState(false);
  const toggle = (uid) => setSelected((s) => {
    const next = new Set(s);
    if (next.has(uid)) next.delete(uid); else next.add(uid);
    return next;
  });
  const save = async () => {
    setBusy(true);
    try {
      const toAdd = [...selected].filter((u) => !currentIds.includes(u));
      const toRemove = currentIds.filter((u) => !selected.has(u));
      if (toAdd.length) await api.post(`/units/${unit.id}/members`, { user_ids: toAdd, action: "add" });
      if (toRemove.length) await api.post(`/units/${unit.id}/members`, { user_ids: toRemove, action: "remove" });
      toast.success("Members updated");
      onChanged?.(); onClose?.();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };
  return (
    <div className="flex flex-col max-h-[60vh]">
      <div className="flex-1 overflow-y-auto space-y-2">
        {allMembers.length === 0 && <div className="text-xs text-slate-500">No approved institution members to add.</div>}
        {allMembers.map((m) => (
          <label key={m.user_id} className="flex items-center gap-3 cursor-pointer border border-slate-200 p-2 hover:border-[#0F2847]" data-testid={`pick-member-${m.user_id}`}>
            <Checkbox checked={selected.has(m.user_id)} onChange={() => toggle(m.user_id)} />
            <div className="flex-1 min-w-0">
              <div className="text-sm">{m.user?.full_name || m.user_id}</div>
              <div className="text-[10px] font-mono text-slate-500">{userTypeLabel(m.user)}</div>
            </div>
            <span className="overline text-[#0F2847]">{m.role}</span>
          </label>
        ))}
      </div>
      <div className="border-t border-slate-200 pt-3 mt-3 flex items-center justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
        <Button data-testid="save-unit-members" size="sm" onClick={save} disabled={busy} loading={busy}>Save</Button>
      </div>
    </div>
  );
}

/**
 * InstitutionDetail — full institution profile with 6 tabs:
 *   Overview · Researchers · Units · Publications · Funding · Reputation
 *
 * Plus a "Govern" panel for admins (members + audit + seats).
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import {
  Building2, Globe, Users, Sparkles, BookOpen, Coins, Award, Layers,
  UserPlus, ShieldCheck, ScrollText, Trash2, Check, X, Plus, ChevronRight,
  Handshake, Target, Network, Calendar,
} from "lucide-react";
import { userTypeLabel } from "../lib/userTypes";
import { NAVY } from "@/lib/tokens";
import {
  SkeletonCard, Card, Button, Badge, StatCard, StatGrid,
  EmptyState, Modal, Input, FormSelect, Textarea,
} from "@/components/ds";

const TAB_LIST = ["overview", "researchers", "units", "publications", "funding", "reputation", "collaboration", "govern"];
const TAB_LABEL = {
  overview: "Overview", researchers: "Researchers", units: "Units",
  publications: "Publications", funding: "Funding", reputation: "Reputation",
  collaboration: "Collaboration", govern: "Govern",
};

export default function InstitutionDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [inst, setInst] = useState(null);
  const [tab, setTab] = useState("overview");

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/institutions/${id}`);
      setInst(data);
    } catch { toast.error("Institution not found"); }
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const isAdmin = useMemo(() => {
    if (!inst) return false;
    if (user?.role === "admin") return true;
    return ["owner", "admin"].includes(inst.my_membership?.role);
  }, [inst, user]);

  if (!inst) return <div className="p-6"><SkeletonCard rows={4} /></div>;

  const visibleTabs = isAdmin ? TAB_LIST : TAB_LIST.filter((t) => t !== "govern");

  return (
    <div className="space-y-6">
      <Header inst={inst} onChanged={load} isAdmin={isAdmin} />

      {/* Tabs — kept hand-rolled: ds NavTabs doesn't support per-tab data-testid,
          and tests address individual tabs via data-testid={`inst-tab-${t}`}. */}
      <div className="flex items-center gap-1 border-b border-slate-200 overflow-x-auto" data-testid="inst-tabs">
        {visibleTabs.map((t) => (
          <button
            key={t}
            data-testid={`inst-tab-${t}`}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm -mb-px border-b-2 transition-colors whitespace-nowrap ${tab === t ? "border-[#0F2847] text-[#0F2847]" : "border-transparent text-slate-500 hover:text-slate-900"}`}
          >
            {TAB_LABEL[t]}
          </button>
        ))}
      </div>

      {tab === "overview"     && <OverviewTab id={id} />}
      {tab === "researchers"  && <ResearchersTab id={id} isAdmin={isAdmin} />}
      {tab === "units"        && <UnitsTab id={id} isAdmin={isAdmin} />}
      {tab === "publications" && <PublicationsTab id={id} />}
      {tab === "funding"      && <FundingTab id={id} />}
      {tab === "reputation"    && <ReputationTab id={id} />}
      {tab === "collaboration" && <CollaborationTab id={id} inst={inst} isAdmin={isAdmin} />}
      {tab === "govern" && isAdmin && <GovernTab id={id} inst={inst} onChanged={load} />}
    </div>
  );
}

/* ============================== HEADER ===================================== */
function Header({ inst, onChanged, isAdmin }) {
  const status = inst.my_membership?.status;
  const claim = async () => {
    try {
      const { data } = await api.post(`/institutions/${inst.id}/claim`, { note: null });
      toast.success(data.status === "approved" ? "Joined!" : "Request submitted — pending admin approval");
      onChanged?.();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  return (
    <header className="border-b border-slate-200 pb-6">
      <div className="flex items-start gap-5">
        <div className="w-20 h-20 shrink-0 bg-[#0F2847]/5 border border-[#0F2847]/20 flex items-center justify-center">
          {inst.logo_url
            ? <img src={inst.logo_url} alt="" className="w-full h-full object-cover" />
            : <Building2 size={28} strokeWidth={1.5} className="text-[#0F2847]" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="overline">{(inst.type || "").replace("_", " ")}</span>
            {inst.country && <span className="overline text-slate-500">· {inst.country}</span>}
          </div>
          <h1 className="font-serif text-4xl text-slate-900 mt-1 leading-tight" data-testid="institution-name">{inst.name}</h1>
          {inst.description && <p className="text-sm text-slate-600 mt-2 max-w-3xl">{inst.description}</p>}
          <div className="flex items-center gap-4 mt-3 text-xs text-slate-500 flex-wrap">
            <span className="inline-flex items-center gap-1"><Users size={11} strokeWidth={1.5} /> {inst.member_count} researchers</span>
            {inst.website && (
              <a href={inst.website} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-[#0F2847]">
                <Globe size={11} strokeWidth={1.5} /> {inst.website.replace(/^https?:\/\//, "")}
              </a>
            )}
            {(inst.email_domains || []).length > 0 && (
              <span className="font-mono text-[10px] text-slate-400">@ {(inst.email_domains || []).join(", ")}</span>
            )}
          </div>
        </div>
        <div className="shrink-0 flex flex-col gap-2 items-end">
          {!status && (
            <Button data-testid="claim-institution-btn" size="sm" onClick={claim}>
              <UserPlus size={11} strokeWidth={1.5} /> Request to join
            </Button>
          )}
          {status === "pending" && (
            <Badge variant="warning">Pending approval</Badge>
          )}
          {status === "approved" && (
            <Badge variant="success">{inst.my_membership?.role} · member</Badge>
          )}
          {isAdmin && (
            <Badge variant="default">
              <ShieldCheck size={10} strokeWidth={1.5} /> Admin
            </Badge>
          )}
        </div>
      </div>
    </header>
  );
}

/* ============================== OVERVIEW ================================== */
function OverviewTab({ id }) {
  const [d, setD] = useState(null);
  const [health, setH] = useState(null);
  useEffect(() => {
    api.get(`/institutions/${id}/analytics`).then(({ data }) => setD(data));
    api.get(`/institutions/${id}/analytics/health`).then(({ data }) => setH(data));
  }, [id]);
  if (!d) return <LoadingBlock />;
  const kpis = [
    { label: "Researchers", value: d.researchers, icon: Users },
    { label: "Publications", value: d.publications.total, sub: `${d.publications.in_progress} in progress`, icon: BookOpen },
    { label: "Awarded grants", value: d.grants.awarded, sub: `$${(d.grants.awarded_usd || 0).toLocaleString()}`, icon: Coins },
    { label: "Citations", value: (d.citations_total || 0).toLocaleString(), sub: `h-sum ${d.h_index_total}`, icon: Sparkles },
    { label: "Active workspaces", value: d.workspaces, icon: Layers },
    { label: "Reputation avg", value: d.reputation.average?.toFixed?.(1) || "—", sub: `${d.reputation.sample_size} sampled`, icon: Award },
  ];
  return (
    <div className="space-y-6">
      <StatGrid cols={3} data-testid="overview-kpis">
        {kpis.map(({ label, value, sub, icon: Icon }) => (
          <StatCard key={label} label={label} value={value} sub={sub} icon={<Icon />} />
        ))}
      </StatGrid>
      {health && (
        <Card padding="xl" data-testid="research-health">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="overline">Research Health Score</div>
              <div className="font-serif text-5xl text-[#0F2847] mt-1">{health.score}</div>
              <div className="text-[11px] font-mono text-slate-500 mt-1">Composite — blends publications, grants, funding, reputation.</div>
            </div>
            <div className="space-y-1 text-xs w-72">
              {[
                ["Publications", health.publications_component],
                ["Grants",       health.grants_component],
                ["Funding $",    health.funding_usd_component],
                ["Reputation",   health.reputation_component],
              ].map(([k, v]) => (
                <div key={k}>
                  <div className="flex items-center justify-between text-[11px]">
                    <span>{k}</span>
                    <span className="font-mono">{Math.round(v)}</span>
                  </div>
                  <div className="h-1 bg-slate-100 mt-0.5 relative overflow-hidden">
                    <div className="absolute inset-y-0 left-0 bg-[#0F2847]" style={{ width: `${Math.min(100, v)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

/* ============================== RESEARCHERS =============================== */
function ResearchersTab({ id, isAdmin }) {
  const [members, setMembers] = useState(null);
  const [status, setStatus] = useState("approved");
  const load = useCallback(async () => {
    setMembers(null);
    try {
      const { data } = await api.get(`/institutions/${id}/members?status=${status}`);
      setMembers(data);
    } catch { setMembers([]); }
  }, [status, id]);
  useEffect(() => { load(); }, [load]);
  if (members === null) return <LoadingBlock />;
  return (
    <div className="space-y-3">
      {isAdmin && (
        <div className="flex items-center gap-2">
          {["approved", "pending", "denied", "revoked"].map((s) => (
            <Button
              key={s}
              data-testid={`members-filter-${s}`}
              onClick={() => setStatus(s)}
              variant={status === s ? "primary" : "ghost"}
              size="sm"
            >
              {s}
            </Button>
          ))}
        </div>
      )}
      {members.length === 0 && (
        <EmptyState data-testid="members-empty" title={`No ${status} members.`} />
      )}
      <div className="space-y-2" data-testid="members-list">
        {members.map((m) => (
          <Card key={m.id} to={`/profile/${m.user_id}`} padding="sm" className="flex items-center gap-3" data-testid={`member-row-${m.user_id}`}>
            <div className="w-9 h-9 bg-[#0F2847] text-white text-xs font-serif flex items-center justify-center shrink-0">
              {(m.user?.full_name || "").split(" ").map((p) => p[0]).filter(Boolean).slice(0,2).join("").toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-serif text-sm text-slate-900 truncate">{m.user?.full_name || m.user_id}</div>
              <div className="text-[11px] text-slate-500 truncate">{userTypeLabel(m.user)}</div>
            </div>
            <span className="overline text-[#0F2847]">{m.role}</span>
            {m.seat_type && m.seat_type !== "personal" && (
              <Badge variant="warning" size="sm">{m.seat_type.replace("_", " ")} seat</Badge>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ============================== UNITS ===================================== */
function UnitsTab({ id, isAdmin }) {
  const [tree, setTree] = useState(null);
  const [creating, setCreating] = useState(false);
  const load = useCallback(async () => {
    setTree(null);
    try {
      const { data } = await api.get(`/institutions/${id}/units`);
      setTree(data);
    } catch { setTree([]); }
  }, [id]);
  useEffect(() => { load(); }, [load]);
  if (tree === null) return <LoadingBlock />;
  const rootUnits = tree.filter((u) => !u.parent_id);
  return (
    <div className="space-y-4">
      {isAdmin && (
        <div className="flex items-center justify-end">
          <Button data-testid="create-unit-btn" size="sm" onClick={() => setCreating(true)}>
            <Plus size={11} strokeWidth={1.5} /> New unit
          </Button>
        </div>
      )}
      {rootUnits.length === 0 && (
        <EmptyState
          data-testid="units-empty"
          title="No units yet."
          description={isAdmin ? "Create faculties, departments, research centers, or labs to model your institution." : undefined}
        />
      )}
      <div className="grid sm:grid-cols-2 gap-3" data-testid="units-list">
        {rootUnits.map((u) => <UnitCard key={u.id} u={u} />)}
      </div>
      {creating && <CreateUnitModal institutionId={id} onClose={() => setCreating(false)} onCreated={load} />}
    </div>
  );
}

function UnitCard({ u }) {
  return (
    <Card to={`/units/${u.id}`} padding="md" className="group" data-testid={`unit-card-${u.id}`}>
      <div className="flex items-center justify-between">
        <span className="overline">{(u.type || "").replace("_", " ")}</span>
        <div className="text-[10px] font-mono text-slate-400">
          {u.member_count} member{u.member_count === 1 ? "" : "s"}{u.child_count ? ` · ${u.child_count} sub-unit${u.child_count === 1 ? "" : "s"}` : ""}
        </div>
      </div>
      <div className="font-serif text-lg text-slate-900 mt-1 group-hover:text-[#0F2847]">{u.name}</div>
      {u.description && <p className="text-xs text-slate-600 mt-1 line-clamp-2">{u.description}</p>}
      {(u.research_areas || []).length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {(u.research_areas || []).slice(0, 4).map((a) => (
            <span key={a} className="text-[10px] font-mono border border-slate-200 bg-slate-50 px-1.5 py-0.5">{a}</span>
          ))}
        </div>
      )}
    </Card>
  );
}

function CreateUnitModal({ institutionId, onClose, onCreated, parentId = null }) {
  const [name, setName] = useState("");
  const [type, setType] = useState("department");
  const [description, setDescription] = useState("");
  const [areas, setAreas] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!name.trim()) { toast.error("Name required"); return; }
    setBusy(true);
    try {
      await api.post(`/institutions/${institutionId}/units`, {
        name: name.trim(), type, parent_id: parentId,
        description: description || null,
        research_areas: areas.split(",").map((s) => s.trim()).filter(Boolean),
      });
      toast.success("Unit created");
      onCreated?.(); onClose?.();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };
  return (
    <Modal
      open
      onClose={onClose}
      closeOnOverlay
      title="New unit"
      data-testid="create-unit-modal"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
          <Button data-testid="unit-submit" size="sm" disabled={busy} loading={busy} onClick={submit}>Create</Button>
        </>
      }
    >
      <div className="space-y-3">
        <Input data-testid="unit-name" label="Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Department of Computer Science / AI Lab / …" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <FormSelect data-testid="unit-type" label="Type" value={type} onChange={(e) => setType(e.target.value)}>
            {["faculty","department","research_center","lab","institute","school","research_group","other"].map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
          </FormSelect>
          <Input data-testid="unit-areas" label="Research areas (csv)" value={areas} onChange={(e) => setAreas(e.target.value)} placeholder="nlp, robotics" />
        </div>
        <Textarea data-testid="unit-description" label="Description" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
    </Modal>
  );
}

/* ============================== PUBLICATIONS ============================== */
function PublicationsTab({ id }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    api.get(`/institutions/${id}/analytics/publications`).then(({ data }) => setD(data));
  }, [id]);
  if (!d) return <LoadingBlock />;
  return (
    <div className="grid lg:grid-cols-2 gap-5" data-testid="publications-tab">
      <Card padding="lg">
        <div className="overline mb-3">By year</div>
        {d.by_year.length === 0 && <div className="text-xs text-slate-500">No published manuscripts yet.</div>}
        <YearBars data={d.by_year} />
      </Card>
      <Card padding="lg">
        <div className="overline mb-3">By unit</div>
        {d.by_unit.length === 0 && <div className="text-xs text-slate-500">No publications attributable to a unit yet.</div>}
        <div className="space-y-2">
          {d.by_unit.map((u) => (
            <Link key={u.unit_id} to={`/units/${u.unit_id}`} className="flex items-center justify-between text-sm hover:text-[#0F2847]">
              <span>{u.name} <span className="text-[10px] font-mono text-slate-400 ml-1">{u.type}</span></span>
              <span className="font-mono text-xs">{u.n}</span>
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}

function YearBars({ data }) {
  if (!data.length) return null;
  const max = Math.max(...data.map((d) => d.n), 1);
  return (
    <div className="flex items-end gap-2 h-32">
      {data.map((d) => (
        <div key={d.year} className="flex-1 flex flex-col items-center gap-1">
          <div className="w-full bg-[#0F2847]" style={{ height: `${(d.n / max) * 100}%` }} />
          <div className="text-[10px] font-mono text-slate-500">{d.year}</div>
          <div className="text-[10px] font-mono text-slate-900">{d.n}</div>
        </div>
      ))}
    </div>
  );
}

/* ============================== FUNDING =================================== */
function FundingTab({ id }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    api.get(`/institutions/${id}/analytics/funding`).then(({ data }) => setD(data));
  }, [id]);
  if (!d) return <LoadingBlock />;
  return (
    <div className="space-y-5" data-testid="funding-tab">
      <Card padding="lg">
        <div className="overline">Total awarded</div>
        <div className="font-serif text-4xl text-slate-900 mt-1">${(d.total_usd || 0).toLocaleString()}</div>
        <div className="grid sm:grid-cols-4 gap-3 mt-4">
          {(d.by_status || []).map((s) => (
            <div key={s.status} className="border border-slate-200 p-3">
              <div className="overline">{s.status || "—"}</div>
              <div className="font-serif text-2xl text-slate-900">{s.n}</div>
              <div className="text-[10px] font-mono text-slate-500">${(s.usd || 0).toLocaleString()}</div>
            </div>
          ))}
        </div>
      </Card>
      <Card padding="lg">
        <div className="overline mb-3">By unit</div>
        {d.by_unit.length === 0 && <div className="text-xs text-slate-500">No grants attributable to a unit yet.</div>}
        <div className="space-y-2">
          {d.by_unit.map((u) => (
            <Link key={u.unit_id} to={`/units/${u.unit_id}`} className="flex items-center justify-between text-sm hover:text-[#0F2847]">
              <span>{u.name} <span className="text-[10px] font-mono text-slate-400 ml-1">{u.type}</span></span>
              <span className="font-mono text-xs">${u.awarded_usd.toLocaleString()} · {u.n}</span>
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}

/* ============================== REPUTATION ================================ */
function ReputationTab({ id }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    api.get(`/institutions/${id}/analytics/reputation`).then(({ data }) => setD(data));
  }, [id]);
  if (!d) return <LoadingBlock />;
  return (
    <div className="grid lg:grid-cols-2 gap-5" data-testid="reputation-tab">
      <Card padding="lg">
        <div className="overline mb-1">Average reputation</div>
        <div className="font-serif text-4xl text-[#0F2847]">{d.average}</div>
        <div className="overline mt-5 mb-2">Top researchers</div>
        {d.top_researchers.length === 0 && <div className="text-xs text-slate-500">No researchers ranked yet.</div>}
        <div className="space-y-2">
          {d.top_researchers.map((t, i) => (
            <Link key={t.user.id} to={`/profile/${t.user.id}`} className="flex items-center gap-3 hover:text-[#0F2847]" data-testid={`top-researcher-${i}`}>
              <span className="font-mono text-[10px] text-slate-400 w-4">{i + 1}.</span>
              <span className="flex-1 truncate text-sm">{t.user.full_name}</span>
              <span className="font-mono text-xs text-[#0F2847]">{Math.round(t.overall)}</span>
            </Link>
          ))}
        </div>
      </Card>
      <Card padding="lg">
        <div className="overline mb-2">Top units by avg reputation</div>
        {d.top_units.length === 0 && <div className="text-xs text-slate-500">No unit data yet.</div>}
        <div className="space-y-2">
          {d.top_units.map((u, i) => (
            <Link key={u.unit_id} to={`/units/${u.unit_id}`} className="flex items-center gap-3 hover:text-[#0F2847]">
              <span className="font-mono text-[10px] text-slate-400 w-4">{i + 1}.</span>
              <span className="flex-1 truncate text-sm">{u.name}</span>
              <span className="text-[10px] font-mono text-slate-400">{u.n}</span>
              <span className="font-mono text-xs text-[#0F2847]">{u.average}</span>
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}

/* ============================== GOVERN ==================================== */
function GovernTab({ id, inst, onChanged }) {
  const [audit, setAudit] = useState(null);
  const [members, setMembers] = useState(null);
  const [mktActivity, setMktActivity] = useState(null);
  const [collab, setCollab] = useState(null);
  const [seatsTotal, setSeatsTotal] = useState(inst.seats?.total || 0);

  const load = useCallback(() => {
    api.get(`/institutions/${id}/audit`).then(({ data }) => setAudit(data));
    api.get(`/institutions/${id}/members`).then(({ data }) => setMembers(data));
    api.get(`/institutions/${id}/analytics/marketplace`).then(({ data }) => setMktActivity(data));
    api.get(`/institutions/${id}/analytics/collaboration`).then(({ data }) => setCollab(data));
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const decide = async (uid, decision) => {
    await api.post(`/institutions/${id}/members/${uid}/decide`, { decision });
    toast.success(`Member ${decision}`); load();
  };
  const setRole = async (uid, role) => {
    await api.post(`/institutions/${id}/members/${uid}/role`, { role });
    toast.success("Role updated"); load();
  };
  const setSeat = async (uid, seat_type) => {
    try {
      await api.post(`/institutions/${id}/members/${uid}/seat`, { seat_type });
      toast.success("Seat updated"); load(); onChanged?.();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  const revoke = async (uid) => {
    if (!confirm("Revoke this member?")) return;
    await api.post(`/institutions/${id}/members/${uid}/revoke`);
    toast.success("Revoked"); load();
  };
  const saveSeats = async () => {
    try {
      await api.patch(`/institutions/${id}`, { seats_total: Number(seatsTotal) });
      toast.success("Seat capacity updated"); onChanged?.();
    } catch (e) { toast.error("Failed"); }
  };

  return (
    <div className="space-y-6" data-testid="govern-tab">
      {/* Seats */}
      <Card padding="lg" data-testid="govern-seats">
        <div className="flex items-center justify-between mb-3">
          <div className="overline">Seat management</div>
          <div className="font-mono text-xs text-slate-500">
            Assigned {inst.seats?.assigned || 0} / {inst.seats?.total || 0}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Input data-testid="seats-total-input" type="number" min={0} step={1} max={10000} value={seatsTotal} onChange={(e) => setSeatsTotal(e.target.value)} className="font-mono" wrapperClassName="w-32" />
          <Button data-testid="seats-save" size="sm" onClick={saveSeats}>Update capacity</Button>
          <span className="text-[10px] font-mono text-slate-400">Seats apply to sponsored + institution-owned assignments.</span>
        </div>
      </Card>

      {/* Marketplace + Collab snapshot */}
      <section className="grid md:grid-cols-2 gap-5">
        {mktActivity && (
          <Card padding="lg">
            <div className="overline mb-3">Marketplace activity</div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <Stat k="Expertise open"      v={mktActivity.expertise_open} />
              <Stat k="Expertise filled"    v={mktActivity.expertise_filled} />
              <Stat k="Invitations sent"    v={mktActivity.invitations_sent} />
              <Stat k="Invitations accepted" v={mktActivity.invitations_accepted} />
            </div>
            <div className="text-[10px] font-mono text-slate-500 mt-3">Success rate: {(mktActivity.match_success_rate * 100).toFixed(0)}%</div>
          </Card>
        )}
        {collab && (
          <Card padding="lg">
            <div className="overline mb-3">Collaboration</div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <Stat k="Internal collabs" v={collab.internal} />
              <Stat k="External collabs" v={collab.external} />
            </div>
            {(collab.network || []).length > 0 && (
              <>
                <div className="overline mt-4 mb-2">Top internal edges</div>
                <div className="space-y-1 text-xs">
                  {(collab.network || []).slice(0, 5).map((e, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <span className="truncate">{e.source_name} ↔ {e.target_name}</span>
                      <span className="font-mono text-slate-500">{e.weight}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </Card>
        )}
      </section>

      {/* Member governance */}
      <Card padding="lg" data-testid="govern-members">
        <div className="overline mb-3">Members</div>
        {members === null && <LoadingBlock />}
        {members && members.length === 0 && <div className="text-xs text-slate-500">No members.</div>}
        <div className="divide-y divide-slate-100">
          {(members || []).map((m) => (
            <div key={m.id} className="py-3 flex items-center gap-3 text-sm" data-testid={`govern-row-${m.user_id}`}>
              <Link to={`/profile/${m.user_id}`} className="flex-1 truncate hover:text-[#0F2847]">
                {m.user?.full_name || m.user_id}
                {m.user?.email && <span className="text-[10px] font-mono text-slate-400 ml-2">{m.user.email}</span>}
              </Link>
              <Badge variant={
                m.status === "approved" ? "success" : m.status === "pending" ? "warning" : "neutral"
              } size="sm">{m.status}</Badge>
              {m.status === "pending" && (
                <>
                  <Button data-testid={`approve-${m.user_id}`} onClick={() => decide(m.user_id, "approved")} size="sm">
                    <Check size={9} strokeWidth={1.5} /> Approve
                  </Button>
                  <Button data-testid={`deny-${m.user_id}`} onClick={() => decide(m.user_id, "denied")} variant="ghost" size="sm">
                    <X size={9} strokeWidth={1.5} /> Deny
                  </Button>
                </>
              )}
              {m.status === "approved" && m.role !== "owner" && (
                <>
                  <FormSelect data-testid={`role-${m.user_id}`} value={m.role} onChange={(e) => setRole(m.user_id, e.target.value)} size="sm" wrapperClassName="w-auto">
                    {["admin", "unit_admin", "research_lead", "researcher"].map((r) => <option key={r} value={r}>{r}</option>)}
                  </FormSelect>
                  <FormSelect data-testid={`seat-${m.user_id}`} value={m.seat_type || "personal"} onChange={(e) => setSeat(m.user_id, e.target.value)} size="sm" wrapperClassName="w-auto">
                    <option value="personal">personal</option>
                    <option value="sponsored">sponsored</option>
                    <option value="institution_owned">institution_owned</option>
                  </FormSelect>
                  <Button data-testid={`revoke-${m.user_id}`} onClick={() => revoke(m.user_id)} variant="ghost" size="icon" aria-label="Revoke access" className="text-red-600 hover:text-red-700">
                    <Trash2 size={11} strokeWidth={1.5} />
                  </Button>
                </>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Audit */}
      <Card padding="lg" data-testid="govern-audit">
        <div className="flex items-center gap-2 mb-3">
          <ScrollText size={12} strokeWidth={1.5} className="text-[#0F2847]" />
          <div className="overline">Audit log</div>
        </div>
        {audit === null && <LoadingBlock />}
        {audit && audit.length === 0 && <div className="text-xs text-slate-500">No audit events yet.</div>}
        <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
          {(audit || []).map((row) => (
            <div key={row.id} className="py-2 text-xs flex items-center gap-3 font-mono">
              <span className="text-slate-400 w-44 shrink-0 truncate">{new Date(row.created_at).toLocaleString()}</span>
              <span className="text-[#0F2847] w-44 shrink-0 truncate">{row.action}</span>
              <span className="text-slate-700 flex-1 truncate">{row.actor_name || row.actor_id}</span>
              {row.target_kind && <span className="text-slate-400 text-[10px]">{row.target_kind}</span>}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

/* ============================== COLLABORATION ============================== */
function CollaborationTab({ id, inst, isAdmin }) {
  const [collabs, setCollabs] = useState(null);
  const [members, setMembers] = useState([]);
  const [form, setForm] = useState({ title: "", description: "", kind: "research_initiative", deadline: "" });
  const [formOpen, setFormOpen] = useState(false);
  const [posting, setPosting] = useState(false);

  const load = useCallback(async () => {
    try {
      const [collabRes, memberRes] = await Promise.allSettled([
        api.get("/collaborations?limit=10"),
        api.get(`/institutions/${id}/members`),
      ]);
      if (collabRes.status === "fulfilled") setCollabs(collabRes.value.data?.items || collabRes.value.data || []);
      if (memberRes.status === "fulfilled") setMembers(memberRes.value.data || []);
    } catch (_) {
      setCollabs([]);
    }
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const post = async () => {
    if (!form.title.trim()) { toast.error("Title required"); return; }
    setPosting(true);
    try {
      await api.post("/collaborations", {
        title: form.title,
        description: form.description,
        type: form.kind,
        deadline: form.deadline || null,
        institution_id: id,
      });
      toast.success("Collaboration call posted");
      setForm({ title: "", description: "", kind: "research_initiative", deadline: "" });
      setFormOpen(false);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    setPosting(false);
  };

  const KIND_LABELS = {
    research_initiative: "Research Initiative",
    strategic_project:   "Strategic Project",
    faculty_recruitment: "Faculty Recruitment",
    student_project:     "Student Project",
    grant_team:          "Grant Team",
    teaching_collab:     "Teaching Collaboration",
  };

  const KIND_COLORS = {
    research_initiative: "#7C3AED",
    strategic_project:   "#2563EB",
    faculty_recruitment: "#B45309",
    student_project:     "#059669",
    grant_team:          "#EA580C",
    teaching_collab:     "#0284C7",
  };

  return (
    <div className="space-y-6" data-testid="collaboration-tab">
      {/* Quick links to cross-module collaboration tools */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { to: "/collaborations",          label: "All Collaborations",   icon: Handshake,      desc: "Browse all open calls" },
          { to: "/grant-collaboration-hub", label: "Grant Collaboration",  icon: Target,          desc: "Form grant teams" },
          { to: "/network/collaborations",  label: "Open Opportunities",   icon: Network,         desc: "Network-wide search" },
          { to: "/teams",                   label: "Research Teams",        icon: Users,           desc: "Build interdisciplinary teams" },
        ].map(({ to, label, icon: Icon, desc }) => (
          <Card key={to} to={to} padding="md" className="group">
            <Icon size={16} strokeWidth={1.5} className="text-[#0F2847] mb-2" />
            <div className="text-sm font-medium text-slate-900 group-hover:text-[#0F2847] transition-colors">{label}</div>
            <div className="text-xs text-slate-500 mt-0.5">{desc}</div>
          </Card>
        ))}
      </div>

      {/* Post new collaboration call */}
      <Card padding="none">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="overline flex items-center gap-2">
            <Handshake size={12} strokeWidth={1.5} className="text-[#0F2847]" />
            Institution Collaboration Calls
          </div>
          <Button size="sm" onClick={() => setFormOpen((o) => !o)}>
            <Plus size={11} strokeWidth={1.5} />
            Post call
          </Button>
        </div>

        {formOpen && (
          <div className="px-5 py-4 border-b border-slate-200 bg-slate-50 space-y-3" data-testid="collab-form">
            <div className="grid sm:grid-cols-2 gap-3">
              <Input
                label="Title"
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="Collaboration call title"
              />
              <FormSelect
                label="Type"
                value={form.kind}
                onChange={(e) => setForm((f) => ({ ...f, kind: e.target.value }))}
              >
                {Object.entries(KIND_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </FormSelect>
            </div>
            <Textarea
              label="Description"
              rows={2}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Goals, expectations, who should apply…"
            />
            <div className="grid sm:grid-cols-2 gap-3">
              <Input
                label="Deadline (optional)"
                type="date"
                value={form.deadline}
                onChange={(e) => setForm((f) => ({ ...f, deadline: e.target.value }))}
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" size="sm" onClick={() => setFormOpen(false)}>Cancel</Button>
              <Button size="sm" disabled={posting} loading={posting} onClick={post}>Post</Button>
            </div>
          </div>
        )}

        <div className="divide-y divide-slate-100">
          {collabs === null && <div className="px-5 py-4"><SkeletonCard rows={2} /></div>}
          {collabs !== null && collabs.length === 0 && (
            <div className="px-5 py-8">
              <EmptyState
                icon={<Handshake />}
                title="No collaboration calls posted yet"
                action={<Button variant="link" onClick={() => setFormOpen(true)}>Post the first call</Button>}
              />
            </div>
          )}
          {(collabs || []).map((c) => (
            <Link
              key={c.id}
              to={`/collaborations/${c.id}`}
              className="px-5 py-4 flex items-start gap-3 hover:bg-slate-50 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-900 truncate">{c.title}</div>
                {c.description && (
                  <div className="text-xs text-slate-500 mt-0.5 line-clamp-2">{c.description}</div>
                )}
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  {c.type && (
                    <Badge size="sm" color={KIND_COLORS[c.type]}>
                      {KIND_LABELS[c.type] || c.type}
                    </Badge>
                  )}
                  {c.deadline && (
                    <span className="text-[10px] font-mono text-slate-400 inline-flex items-center gap-1">
                      <Calendar size={9} strokeWidth={1.5} />
                      {new Date(c.deadline).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
              <ChevronRight size={14} strokeWidth={1.5} className="text-slate-300 mt-1 shrink-0" />
            </Link>
          ))}
        </div>
      </Card>

      {/* Active members quick view */}
      {members.length > 0 && (
        <Card padding="none">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <div className="overline flex items-center gap-2">
              <Users size={12} strokeWidth={1.5} className="text-[#0F2847]" />
              Active Members ({members.filter((m) => m.status === "approved").length})
            </div>
            <Link to="/collaborations" className="text-xs text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
              Find collaborators
            </Link>
          </div>
          <div className="divide-y divide-slate-100">
            {members.filter((m) => m.status === "approved").slice(0, 8).map((m) => (
              <Link
                key={m.id}
                to={`/faculty/${m.user_id}`}
                className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50 transition-colors"
              >
                <div className="w-7 h-7 shrink-0 bg-[#0F2847]/5 border border-[#0F2847]/10 flex items-center justify-center">
                  <Users size={12} strokeWidth={1.5} className="text-[#0F2847]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-900 truncate">{m.user?.full_name || m.user_id}</div>
                  {m.role && <div className="text-[10px] font-mono text-slate-400 mt-0.5">{m.role}</div>}
                </div>
                <ChevronRight size={12} strokeWidth={1.5} className="text-slate-300 shrink-0" />
              </Link>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function Stat({ k, v }) {
  return (
    <div>
      <div className="font-serif text-2xl text-slate-900">{v || 0}</div>
      <div className="text-[10px] font-mono text-slate-500">{k}</div>
    </div>
  );
}

function LoadingBlock() {
  return <div className="p-6"><SkeletonCard rows={4} /></div>;
}

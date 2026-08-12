/* eslint-disable */
import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ResearchLayout } from "@/layouts";
import {
  ArrowLeft, Loader2, Users, Building2, Briefcase, Globe, Calendar,
  DollarSign, CheckCircle, XCircle, ChevronDown, ChevronUp, Plus,
  RefreshCw, Share2, X, Edit2, Save, Check, AlertTriangle, Star,
  BarChart2, Package, FileText, Target, TrendingUp, Trash2, Eye
} from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { ACCENT, EMERALD, NAVY, WARM } from "@/lib/tokens";
import { Badge } from "@/components/ds/Badge";
import { Tag } from "@/components/ds/Tag";
import { Card } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { Spinner } from "@/components/ds/LoadingState";
import { ErrorState } from "@/components/ds/ErrorState";
import { EmptyState } from "@/components/ds/EmptyState";
import { NavTabs } from "@/components/ds/NavTabs";
import { Modal } from "@/components/ds/Modal";
import { ProgressBar } from "@/components/ds/Progress";
import { Checkbox } from "@/components/ds/Form";
import { StatCard, StatGrid } from "@/components/ds/StatCard";

// ─── helpers ─────────────────────────────────────────────────────────────────

// Hex equivalents (ds Badge's `color` prop) of the status→color mapping below
const STATUS_HEX = {
  open:      "#059669",
  active:    "#2563EB",
  full:      "#D97706",
  closed:    "#64748B",
  draft:     "#64748B",
  review:    "#D97706",
  approved:  "#059669",
  filled:    "#2563EB",
  completed: "#059669",
  pending:   "#D97706",
  accepted:  "#059669",
  rejected:  "#DC2626",
};

function StatusBadge({ status }) {
  return (
    <Badge color={STATUS_HEX[status] || STATUS_HEX.draft}>
      {status ? status.charAt(0).toUpperCase() + status.slice(1) : "Unknown"}
    </Badge>
  );
}

function Chip({ label, color = "slate" }) {
  const map = {
    slate:  undefined,
    indigo: "#4F46E5",
    purple: "#9333EA",
    amber:  "#D97706",
    blue:   "#2563EB",
    emerald:"#059669",
  };
  return <Tag size="sm" color={map[color]}>{label}</Tag>;
}

function TabLoading() {
  return (
    <div className="p-8 flex items-center justify-center gap-2 text-slate-400">
      <Spinner size={16} />
      <span className="text-sm">Loading...</span>
    </div>
  );
}

function TabError({ message }) {
  return <ErrorState message="Failed to load" detail={message} />;
}

function SectionCard({ title, children, action }) {
  return (
    <Card padding="none">
      {(title || action) && (
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100">
          {title && <h3 className="text-sm font-semibold text-slate-900">{title}</h3>}
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </Card>
  );
}

function ScoreBar({ label, value, max = 100, color = "#0F2847" }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="w-36 text-xs text-slate-600 truncate">{label}</span>
      <div className="flex-1 bg-slate-100 rounded-full h-2">
        <div className="h-2 rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="w-16 text-xs text-slate-500 text-right">{value}/{max}</span>
    </div>
  );
}

function CompatBar({ label, value }) {
  const color = value >= 70 ? "#059669" : value >= 50 ? "#d97706" : "#64748b";
  return (
    <div className="flex items-center gap-2">
      <span className="w-32 text-xs text-slate-500 truncate">{label}</span>
      <div className="flex-1 bg-slate-100 rounded-full h-1.5">
        <div className="h-1.5 rounded-full" style={{ width: `${value}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-medium w-8 text-right" style={{ color }}>{value}%</span>
    </div>
  );
}

// ─── tab sub-components ───────────────────────────────────────────────────────

function OverviewTab({ data, collab }) {
  const score = data?.readiness?.total_score || 0;
  const r = 45;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  const scoreLabel = score >= 80 ? "Excellent" : score >= 60 ? "Good" : score >= 40 ? "Developing" : "Early Stage";
  const scoreColor = score >= 80 ? "#059669" : score >= 60 ? "#0F2847" : score >= 40 ? "#d97706" : "#94a3b8";

  const team = data?.team || [];
  const openPositions = (data?.positions || []).filter(p => p.status === "open").length;
  const improvements = data?.readiness?.improvement_actions || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
      {/* Left: description + details */}
      <div className="lg:col-span-2 space-y-5">
        {collab?.description && (
          <SectionCard title="About this Collaboration">
            <p className="text-sm text-slate-700 leading-relaxed">{collab.description}</p>
          </SectionCard>
        )}

        <SectionCard title="Key Details">
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
            {[
              { icon: Users, label: "Lead Researcher", value: collab?.lead_user_name || collab?.lead_user_id || "—" },
              { icon: DollarSign, label: "Total Budget", value: collab?.budget_total ? `€${collab.budget_total.toLocaleString()}` : "—" },
              { icon: Calendar, label: "Deadline", value: collab?.deadline ? new Date(collab.deadline).toLocaleDateString() : "—" },
              { icon: Eye, label: "Visibility", value: collab?.visibility ? collab.visibility.charAt(0).toUpperCase() + collab.visibility.slice(1) : "—" },
              { icon: Briefcase, label: "Funding Source", value: collab?.funding_source || "—" },
              { icon: Globe, label: "Countries Required", value: collab?.countries_required?.join(", ") || "—" },
            ].map(({ icon: Icon, label, value }) => (
              <div key={label} className="flex items-start gap-2">
                <Icon size={14} className="text-slate-400 mt-0.5 shrink-0" />
                <div>
                  <dt className="text-xs text-slate-500 uppercase tracking-wide">{label}</dt>
                  <dd className="text-sm text-slate-800 font-medium mt-0.5">{value}</dd>
                </div>
              </div>
            ))}
          </dl>
        </SectionCard>
      </div>

      {/* Right: readiness ring + team */}
      <div className="space-y-4">
        <SectionCard title="Readiness Score">
          <div className="flex flex-col items-center gap-3">
            <svg width="110" height="110" viewBox="0 0 110 110">
              <circle cx="55" cy="55" r={r} fill="none" stroke="#e2e8f0" strokeWidth="10" />
              <circle
                cx="55" cy="55" r={r} fill="none"
                stroke={scoreColor} strokeWidth="10"
                strokeDasharray={`${dash} ${circ}`}
                strokeLinecap="round"
                transform="rotate(-90 55 55)"
              />
              <text x="55" y="51" textAnchor="middle" fontSize="20" fontWeight="700" fill={scoreColor}>{score}</text>
              <text x="55" y="65" textAnchor="middle" fontSize="10" fill="#64748b">{scoreLabel}</text>
            </svg>
            <p className="text-xs text-slate-500 text-center">Grant readiness score out of 100</p>
          </div>

          {improvements.length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <p className="text-xs font-semibold text-slate-700 mb-2">Top improvements</p>
              <ul className="space-y-1">
                {improvements.slice(0, 3).map((action, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-slate-600">
                    <span className="text-[#8A1538] mt-0.5 shrink-0">•</span> {action}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </SectionCard>

        <SectionCard title="Team">
          <div className="flex flex-wrap gap-1 mb-2">
            {team.slice(0, 6).map((m, i) => (
              <div key={m._id || i} title={m.name || m.user_name}
                className="w-8 h-8 rounded-full bg-[#0F2847] text-white text-xs font-bold flex items-center justify-center uppercase"
              >
                {(m.name || m.user_name || "?").charAt(0)}
              </div>
            ))}
            {team.length > 6 && (
              <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-500 text-xs font-bold flex items-center justify-center">
                +{team.length - 6}
              </div>
            )}
          </div>
          <p className="text-xs text-slate-500">{team.length} members · <span className="text-emerald-600">{openPositions} open positions</span></p>
        </SectionCard>
      </div>
    </div>
  );
}

function TeamTab({ data, collabId, isLead, onRefresh }) {
  const team = data?.team || [];
  const positions = data?.positions || [];
  const [inviteForm, setInviteForm] = useState({ user_id: "", role: "", message: "" });
  const [inviting, setInviting] = useState(false);
  const [inviteErr, setInviteErr] = useState("");

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!inviteForm.user_id.trim()) { setInviteErr("User ID is required"); return; }
    setInviting(true); setInviteErr("");
    try {
      await api.post(`/grant-hub/${collabId}/invite`, {
        user_id: inviteForm.user_id.trim(),
        role: inviteForm.role.trim(),
        message: inviteForm.message.trim(),
      });
      setInviteForm({ user_id: "", role: "", message: "" });
      onRefresh("team");
    } catch (e) {
      setInviteErr(e?.response?.data?.error || e.message);
    } finally {
      setInviting(false);
    }
  };

  const handleRemove = async (userId) => {
    if (!window.confirm("Remove this member from the collaboration?")) return;
    try {
      await api.delete(`/grant-hub/${collabId}/team/${userId}`);
      onRefresh("team");
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to remove member.");
    }
  };

  return (
    <div className="space-y-5">
      <SectionCard title={`Team Members (${team.length})`}>
        {team.length === 0 ? (
          <p className="text-sm text-slate-500">No team members yet. Invite researchers to get started.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left text-xs text-slate-500 uppercase tracking-wide py-2 pr-4">Name</th>
                  <th className="text-left text-xs text-slate-500 uppercase tracking-wide py-2 pr-4">Role</th>
                  <th className="text-left text-xs text-slate-500 uppercase tracking-wide py-2 pr-4">Institution</th>
                  <th className="text-left text-xs text-slate-500 uppercase tracking-wide py-2 pr-4">Joined</th>
                  {isLead && <th className="text-right text-xs text-slate-500 uppercase tracking-wide py-2">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {team.map((m, i) => (
                  <tr key={m._id || i}>
                    <td className="py-2.5 pr-4 font-medium text-slate-900">{m.name || m.user_name || m.user_id}</td>
                    <td className="py-2.5 pr-4 text-slate-600">{m.role || "—"}</td>
                    <td className="py-2.5 pr-4 text-slate-500">{m.institution || "—"}</td>
                    <td className="py-2.5 pr-4 text-slate-400 text-xs">{m.joined_at ? new Date(m.joined_at).toLocaleDateString() : "—"}</td>
                    {isLead && (
                      <td className="py-2.5 text-right">
                        <Button onClick={() => handleRemove(m.user_id || m._id)} variant="ghost" size="icon" aria-label="Remove team member" className="!text-red-500 hover:!text-red-700">
                          <Trash2 size={13} />
                        </Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      {/* Invite form */}
      <SectionCard title="Invite Member">
        <form onSubmit={handleInvite} className="space-y-3">
          {inviteErr && <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">{inviteErr}</div>}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="User ID *"
              value={inviteForm.user_id}
              onChange={e => setInviteForm(f => ({ ...f, user_id: e.target.value }))}
              placeholder="Researcher user ID"
            />
            <Input
              label="Role"
              value={inviteForm.role}
              onChange={e => setInviteForm(f => ({ ...f, role: e.target.value }))}
              placeholder="e.g. Co-Investigator"
            />
          </div>
          <Textarea
            label="Personal Message"
            value={inviteForm.message}
            onChange={e => setInviteForm(f => ({ ...f, message: e.target.value }))}
            placeholder="Why would they be a great fit?"
            rows={2}
          />
          <Button type="submit" loading={inviting} size="sm">
            {!inviting && <Plus size={13} />}
            Send Invitation
          </Button>
        </form>
      </SectionCard>

      {/* Open positions */}
      {positions.length > 0 && (
        <SectionCard title="Open Positions">
          <div className="space-y-3">
            {positions.map((p, i) => (
              <div key={p._id || i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm text-slate-900">{p.role_title}</span>
                    <StatusBadge status={p.status} />
                  </div>
                  {p.description && <p className="text-xs text-slate-500 mt-1 line-clamp-2">{p.description}</p>}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}

function ConsortiumTab({ data, collabId, isLead, onRefresh }) {
  const partners = data?.partners || [];
  const validation = data?.validation || null;
  const [addForm, setAddForm] = useState({ institution_id: "", role: "", budget_share: "" });
  const [adding, setAdding] = useState(false);
  const [addErr, setAddErr] = useState("");
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!addForm.institution_id.trim()) { setAddErr("Institution ID required"); return; }
    setAdding(true); setAddErr("");
    try {
      await api.post(`/grant-hub/${collabId}/consortium/partners`, {
        institution_id: addForm.institution_id.trim(),
        role: addForm.role.trim(),
        budget_share: addForm.budget_share ? Number(addForm.budget_share) : undefined,
      });
      setAddForm({ institution_id: "", role: "", budget_share: "" });
      onRefresh("consortium");
    } catch (e) {
      setAddErr(e?.response?.data?.error || e.message);
    } finally {
      setAdding(false);
    }
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      const { data: vd } = await api.get(`/grant-hub/${collabId}/consortium/validate`);
      setValidationResult(vd);
    } catch (e) {
      setValidationResult({ _error: e.message });
    } finally {
      setValidating(false);
    }
  };

  const handleRemovePartner = async (partnerId) => {
    if (!window.confirm("Remove this partner institution?")) return;
    try {
      await api.delete(`/grant-hub/${collabId}/consortium/partners/${partnerId}`);
      onRefresh("consortium");
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to remove partner.");
    }
  };

  const checks = validationResult && !validationResult._error ? validationResult : null;

  return (
    <div className="space-y-5">
      <SectionCard
        title={`Partner Institutions (${partners.length})`}
        action={
          <Button onClick={handleValidate} loading={validating} variant="ghost" size="sm">
            {!validating && <Check size={12} />} Validate Eligibility
          </Button>
        }
      >
        {partners.length === 0 ? (
          <p className="text-sm text-slate-500">No partner institutions added yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left text-xs text-slate-500 uppercase tracking-wide py-2 pr-4">Institution</th>
                  <th className="text-left text-xs text-slate-500 uppercase tracking-wide py-2 pr-4">Role</th>
                  <th className="text-left text-xs text-slate-500 uppercase tracking-wide py-2 pr-4">Budget Share</th>
                  <th className="text-left text-xs text-slate-500 uppercase tracking-wide py-2 pr-4">Status</th>
                  {isLead && <th className="text-right text-xs text-slate-500 uppercase tracking-wide py-2">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {partners.map((p, i) => (
                  <tr key={p._id || i}>
                    <td className="py-2.5 pr-4 font-medium text-slate-900">{p.institution_name || p.institution_id}</td>
                    <td className="py-2.5 pr-4 text-slate-600">{p.role || "—"}</td>
                    <td className="py-2.5 pr-4 text-slate-600">{p.budget_share != null ? `${p.budget_share}%` : "—"}</td>
                    <td className="py-2.5 pr-4"><StatusBadge status={p.status || "active"} /></td>
                    {isLead && (
                      <td className="py-2.5 text-right">
                        <Button onClick={() => handleRemovePartner(p._id)} variant="ghost" size="icon" aria-label="Remove partner" className="!text-red-500 hover:!text-red-700"><Trash2 size={13} /></Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Validation results */}
        {checks && (
          <div className="mt-4 pt-4 border-t border-slate-100">
            <p className="text-xs font-semibold text-slate-700 mb-2">Eligibility Check</p>
            <div className="space-y-1.5">
              {Object.entries(checks).map(([key, val]) => (
                typeof val === "boolean" && (
                  <div key={key} className={`flex items-center gap-2 text-xs ${val ? "text-emerald-700" : "text-red-600"}`}>
                    {val ? <CheckCircle size={13} /> : <XCircle size={13} />}
                    <span className="capitalize">{key.replace(/_/g, " ")}</span>
                  </div>
                )
              ))}
            </div>
          </div>
        )}
        {validationResult?._error && (
          <p className="text-xs text-red-600 mt-3">Validation error: {validationResult._error}</p>
        )}
      </SectionCard>

      {isLead && (
        <SectionCard title="Add Partner Institution">
          <form onSubmit={handleAdd} className="space-y-3">
            {addErr && <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">{addErr}</div>}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Input label="Institution ID *" value={addForm.institution_id} onChange={e => setAddForm(f => ({ ...f, institution_id: e.target.value }))} placeholder="Institution ID" />
              <Input label="Role" value={addForm.role} onChange={e => setAddForm(f => ({ ...f, role: e.target.value }))} placeholder="e.g. Partner" />
              <Input label="Budget Share %" type="number" min="0" max="100" value={addForm.budget_share} onChange={e => setAddForm(f => ({ ...f, budget_share: e.target.value }))} placeholder="e.g. 25" />
            </div>
            <Button type="submit" loading={adding} size="sm">
              {!adding && <Plus size={13} />} Add Partner
            </Button>
          </form>
        </SectionCard>
      )}
    </div>
  );
}

function PositionsTab({ data, collabId, isLead, onRefresh }) {
  const positions = Array.isArray(data) ? data : (data?.positions || []);
  const [form, setForm] = useState({ role_title: "", description: "", required_expertise: "", required_publications: "", required_experience_years: "", availability_required: "", contribution: "" });
  const [creating, setCreating] = useState(false);
  const [createErr, setCreateErr] = useState("");
  const [showForm, setShowForm] = useState(false);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.role_title.trim()) { setCreateErr("Role title is required"); return; }
    setCreating(true); setCreateErr("");
    try {
      await api.post(`/grant-hub/${collabId}/positions`, {
        role_title: form.role_title.trim(),
        description: form.description.trim(),
        required_expertise: form.required_expertise ? form.required_expertise.split(",").map(s => s.trim()).filter(Boolean) : [],
        required_publications: form.required_publications ? Number(form.required_publications) : undefined,
        required_experience_years: form.required_experience_years ? Number(form.required_experience_years) : undefined,
        availability_required: form.availability_required.trim(),
        contribution: form.contribution.trim(),
      });
      setForm({ role_title: "", description: "", required_expertise: "", required_publications: "", required_experience_years: "", availability_required: "", contribution: "" });
      setShowForm(false);
      onRefresh("positions");
    } catch (e) {
      setCreateErr(e?.response?.data?.error || e.message);
    } finally {
      setCreating(false);
    }
  };

  const handleFill = async (posId) => {
    try {
      await api.patch(`/grant-hub/${collabId}/positions/${posId}`, { status: "filled" });
      onRefresh("positions");
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to mark position as filled.");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Open Positions ({positions.filter(p => p.status === "open").length})</h3>
        {isLead && (
          <Button onClick={() => setShowForm(!showForm)} size="sm">
            <Plus size={12} /> Create Position
          </Button>
        )}
      </div>

      {positions.length === 0 ? (
        <EmptyState icon={<Target />} title="No positions created yet." size="sm" />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {positions.map((p, i) => (
            <Card key={p._id || i} padding="md">
              <div className="flex items-start justify-between gap-2 mb-2">
                <h4 className="font-semibold text-sm text-slate-900">{p.role_title}</h4>
                <StatusBadge status={p.status || "open"} />
              </div>
              {p.description && <p className="text-xs text-slate-600 mb-3 line-clamp-2">{p.description}</p>}
              {p.required_expertise?.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-3">
                  {p.required_expertise.map((e, j) => <Chip key={j} label={e} color="indigo" />)}
                </div>
              )}
              <div className="flex items-center gap-4 text-xs text-slate-500 mb-3">
                {p.required_publications != null && <span>Min. {p.required_publications} pubs</span>}
                {p.required_experience_years != null && <span>{p.required_experience_years}+ yrs exp</span>}
              </div>
              {isLead && p.status === "open" && (
                <Button onClick={() => handleFill(p._id)} variant="link" size="sm" className="!text-emerald-600">
                  <Check size={12} /> Mark as Filled
                </Button>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Create form */}
      {showForm && isLead && (
        <SectionCard title="Create Position">
          <form onSubmit={handleCreate} className="space-y-3">
            {createErr && <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">{createErr}</div>}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input wrapperClassName="col-span-2" label="Role Title *" value={form.role_title} onChange={e => setForm(f => ({ ...f, role_title: e.target.value }))} placeholder="e.g. Data Science Lead" />
              <Textarea wrapperClassName="col-span-2" label="Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={2} />
              <Input wrapperClassName="col-span-2" label="Required Expertise (comma-separated)" value={form.required_expertise} onChange={e => setForm(f => ({ ...f, required_expertise: e.target.value }))} placeholder="Python, Machine Learning, Bioinformatics" />
              <Input label="Min. Publications" type="number" min="0" value={form.required_publications} onChange={e => setForm(f => ({ ...f, required_publications: e.target.value }))} />
              <Input label="Min. Experience (years)" type="number" min="0" value={form.required_experience_years} onChange={e => setForm(f => ({ ...f, required_experience_years: e.target.value }))} />
              <Input label="Availability Required" value={form.availability_required} onChange={e => setForm(f => ({ ...f, availability_required: e.target.value }))} placeholder="e.g. 50% FTE" />
              <Input label="Contribution Type" value={form.contribution} onChange={e => setForm(f => ({ ...f, contribution: e.target.value }))} placeholder="e.g. WP lead, analysis" />
            </div>
            <div className="flex gap-2">
              <Button type="submit" loading={creating} size="sm">
                {!creating && <Plus size={13} />} Create Position
              </Button>
              <Button type="button" onClick={() => setShowForm(false)} variant="ghost" size="sm">Cancel</Button>
            </div>
          </form>
        </SectionCard>
      )}
    </div>
  );
}

function MatchesTab({ data, collabId, onRefresh }) {
  const matches = Array.isArray(data) ? data : (data?.matches || []);
  const [refreshing, setRefreshing] = useState(false);
  const [inlineInvite, setInlineInvite] = useState(null);
  const [inviteForm, setInviteForm] = useState({ role: "", message: "" });
  const [inviting, setInviting] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await api.post(`/grant-hub/${collabId}/matches/refresh`);
      onRefresh("matches");
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to refresh matches.");
    } finally {
      setRefreshing(false);
    }
  };

  const handleInvite = async (userId) => {
    setInviting(true);
    try {
      await api.post(`/grant-hub/${collabId}/invite`, { user_id: userId, role: inviteForm.role, message: inviteForm.message });
      setInlineInvite(null);
      setInviteForm({ role: "", message: "" });
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to send invitation.");
    } finally {
      setInviting(false);
    }
  };

  const scoreColor = (s) => s >= 70 ? "text-emerald-600" : s >= 50 ? "text-amber-600" : "text-slate-400";

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Matched Researchers</h3>
          <p className="text-xs text-slate-500 mt-0.5">AI-powered compatibility matching across research areas, publications, and expertise</p>
        </div>
        <Button onClick={handleRefresh} loading={refreshing} size="sm">
          {!refreshing && <RefreshCw size={12} />} Refresh Matches
        </Button>
      </div>

      {matches.length === 0 ? (
        <EmptyState
          icon={<Users />}
          title="No matches yet"
          description='Click "Refresh Matches" to find compatible researchers based on your collaboration profile.'
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {matches.map((m, i) => {
            const score = m.compatibility_score || m.score || 0;
            const breakdown = m.score_breakdown || {};
            return (
              <Card key={m._id || m.user_id || i} padding="md" className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-slate-900 text-sm">{m.name || m.user_name || "Researcher"}</p>
                    {m.institution && <p className="text-xs text-slate-500 flex items-center gap-1"><Building2 size={11} /> {m.institution}</p>}
                    {m.research_areas?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {m.research_areas.slice(0, 3).map((a, j) => <Chip key={j} label={a} color="indigo" />)}
                      </div>
                    )}
                  </div>
                  <div className={`text-2xl font-bold tabular-nums shrink-0 ${scoreColor(score)}`}>{score}%</div>
                </div>

                {Object.keys(breakdown).length > 0 && (
                  <div className="space-y-1.5">
                    {Object.entries(breakdown).map(([k, v]) => (
                      <CompatBar key={k} label={k.replace(/_/g, " ")} value={typeof v === "number" ? v : 0} />
                    ))}
                  </div>
                )}

                {inlineInvite === (m.user_id || m._id) ? (
                  <div className="space-y-2 pt-2 border-t border-slate-100">
                    <Input size="sm" value={inviteForm.role} onChange={e => setInviteForm(f => ({ ...f, role: e.target.value }))} placeholder="Role (optional)" />
                    <Textarea value={inviteForm.message} onChange={e => setInviteForm(f => ({ ...f, message: e.target.value }))} placeholder="Message..." rows={2} />
                    <div className="flex gap-2">
                      <Button onClick={() => handleInvite(m.user_id || m._id)} loading={inviting} size="sm">Send Invite</Button>
                      <Button onClick={() => setInlineInvite(null)} variant="ghost" size="sm">Cancel</Button>
                    </div>
                  </div>
                ) : (
                  <Button onClick={() => setInlineInvite(m.user_id || m._id)} variant="link" size="sm" className="!text-[#0F2847]">
                    <Plus size={12} /> Invite to Team
                  </Button>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function GapAnalysisTab({ data, collabId, onRefresh }) {
  const gaps = data || {};
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await api.post(`/grant-hub/${collabId}/gaps/refresh`);
      onRefresh("gaps");
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to refresh gap analysis.");
    } finally {
      setRefreshing(false);
    }
  };

  const sections = [
    { key: "missing_expertise", label: "Missing Expertise", color: "amber", icon: AlertTriangle },
    { key: "missing_institution_types", label: "Missing Institution Types", color: "blue", icon: Building2 },
    { key: "missing_countries", label: "Missing Countries", color: "purple", icon: Globe },
    { key: "missing_seniority", label: "Missing Seniority Levels", color: "orange", icon: Star },
    { key: "missing_deliverable_owners", label: "Missing Deliverable Owners", color: "red", icon: Target },
  ];

  const chipColorMap = { amber: "amber", blue: "blue", purple: "purple", orange: "amber", red: "amber" };
  const headerBg = { amber: "bg-amber-50 border-amber-200 text-amber-800", blue: "bg-blue-50 border-blue-200 text-blue-800", purple: "bg-purple-50 border-purple-200 text-purple-800", orange: "bg-orange-50 border-orange-200 text-orange-800", red: "bg-red-50 border-red-200 text-red-800" };

  const hasAnyGap = sections.some(s => (gaps[s.key] || []).length > 0);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Gap Analysis</h3>
          <p className="text-xs text-slate-500 mt-0.5">Identifies missing capabilities, countries, and roles needed to strengthen your consortium</p>
        </div>
        <Button onClick={handleRefresh} loading={refreshing} variant="ghost" size="sm">
          {!refreshing && <RefreshCw size={12} />} Refresh Analysis
        </Button>
      </div>

      {!hasAnyGap && !gaps.ai_recommendations && !gaps.recommendations?.length ? (
        <EmptyState
          icon={<CheckCircle />}
          title="No gaps detected — your team is well-formed!"
          description="Run a refresh to re-evaluate after team changes."
        />
      ) : (
        <div className="space-y-4">
          {sections.map(({ key, label, color, icon: Icon }) => {
            const items = gaps[key] || [];
            if (items.length === 0) return null;
            return (
              <div key={key} className={`border rounded-lg overflow-hidden ${headerBg[color].split(" ").slice(2).join(" ")}`}>
                <div className={`flex items-center gap-2 px-4 py-3 border-b ${headerBg[color]}`}>
                  <Icon size={14} />
                  <span className="text-sm font-semibold">{label}</span>
                  <span className="ml-auto text-xs font-medium px-1.5 py-0.5 rounded-full bg-white/60">{items.length}</span>
                </div>
                <div className="p-4 bg-white">
                  <div className="flex flex-wrap gap-2">
                    {items.map((item, i) => <Chip key={i} label={String(item)} color={chipColorMap[color] || "slate"} />)}
                  </div>
                </div>
              </div>
            );
          })}

          {gaps.ai_recommendations && (
            <div className="bg-[#0F2847] rounded-lg p-5">
              <p className="text-xs font-semibold text-blue-300 uppercase tracking-wide mb-2">AI Recommendations</p>
              <pre className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed font-sans">{gaps.ai_recommendations}</pre>
            </div>
          )}

          {gaps.recommendations?.length > 0 && (
            <SectionCard title="Action Items">
              <ul className="space-y-2">
                {gaps.recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                    <span className="text-[#8A1538] font-bold shrink-0">{i + 1}.</span> {rec}
                  </li>
                ))}
              </ul>
            </SectionCard>
          )}
        </div>
      )}
    </div>
  );
}

function ReadinessTab({ data }) {
  const score = data?.total_score || 0;
  const label = data?.label || (score >= 80 ? "Excellent" : score >= 60 ? "Good" : score >= 40 ? "Developing" : "Early Stage");
  const dimensions = data?.dimensions || [];
  const actions = data?.improvement_actions || [];

  const scoreColor = score >= 80 ? "#059669" : score >= 60 ? "#0F2847" : score >= 40 ? "#d97706" : "#94a3b8";
  const explanation = score >= 80
    ? "Your collaboration is fully ready to submit a competitive grant application."
    : score >= 60
    ? "Your collaboration is well-positioned. A few improvements will maximize your chances."
    : score >= 40
    ? "Your collaboration is taking shape. Focus on team completion and work packages."
    : "Your collaboration is in early stages. Start by completing your team and defining positions.";

  return (
    <div className="space-y-5">
      {/* Large score */}
      <SectionCard>
        <div className="flex items-center gap-8">
          <div className="text-center">
            <div className="text-6xl font-bold tabular-nums" style={{ color: scoreColor }}>{score}</div>
            <div className="text-sm text-slate-500 mt-1">out of 100</div>
            <div className="mt-2 px-3 py-1 rounded-full text-sm font-medium" style={{ backgroundColor: `${scoreColor}15`, color: scoreColor }}>{label}</div>
          </div>
          <div className="flex-1">
            <p className="text-sm text-slate-700 leading-relaxed">{explanation}</p>
            {actions.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-semibold text-slate-700 mb-2">Top improvements</p>
                <ul className="space-y-1">
                  {actions.slice(0, 3).map((a, i) => (
                    <li key={i} className="text-xs text-slate-600 flex items-start gap-1.5">
                      <span className="text-[#8A1538] shrink-0">•</span> {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </SectionCard>

      {/* Dimension bars */}
      {dimensions.length > 0 && (
        <SectionCard title="Score Breakdown by Dimension">
          <div className="space-y-3">
            {dimensions.map((dim, i) => (
              <ProgressBar
                key={i}
                label={dim.name || dim.dimension}
                value={dim.score || 0}
                max={dim.max || 10}
              />
            ))}
          </div>
        </SectionCard>
      )}

      {/* All improvement actions */}
      {actions.length > 0 && (
        <SectionCard title="Improvement Actions">
          <ol className="space-y-3">
            {actions.map((action, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-[#0F2847] text-white text-xs flex items-center justify-center font-bold">{i + 1}</span>
                <span className="text-sm text-slate-700">{action}</span>
              </li>
            ))}
          </ol>
        </SectionCard>
      )}
    </div>
  );
}

function WorkPackagesTab({ data, collabId, onRefresh }) {
  const wps = Array.isArray(data) ? data : (data?.work_packages || data?.workPackages || []);
  const [expanded, setExpanded] = useState(new Set());
  const [showWpForm, setShowWpForm] = useState(false);
  const [wpForm, setWpForm] = useState({ title: "", description: "", lead_user_id: "", budget: "", start_date: "", end_date: "", deliverables: "" });
  const [creatingWp, setCreatingWp] = useState(false);
  const [wpErr, setWpErr] = useState("");
  const [taskForms, setTaskForms] = useState({});
  const [creatingTask, setCreatingTask] = useState({});

  const toggleExpand = (id) => {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleCreateWp = async (e) => {
    e.preventDefault();
    if (!wpForm.title.trim()) { setWpErr("Title required"); return; }
    setCreatingWp(true); setWpErr("");
    try {
      await api.post(`/grant-hub/${collabId}/work-packages`, {
        title: wpForm.title.trim(),
        description: wpForm.description.trim(),
        lead_user_id: wpForm.lead_user_id.trim() || undefined,
        budget: wpForm.budget ? Number(wpForm.budget) : undefined,
        start_date: wpForm.start_date || undefined,
        end_date: wpForm.end_date || undefined,
        deliverables: wpForm.deliverables ? wpForm.deliverables.split("\n").map(s => s.trim()).filter(Boolean) : [],
      });
      setWpForm({ title: "", description: "", lead_user_id: "", budget: "", start_date: "", end_date: "", deliverables: "" });
      setShowWpForm(false);
      onRefresh("work-packages");
    } catch (e) {
      setWpErr(e?.response?.data?.error || e.message);
    } finally {
      setCreatingWp(false);
    }
  };

  const handleTaskFormChange = (wpId, field, value) => {
    setTaskForms(prev => ({ ...prev, [wpId]: { ...(prev[wpId] || {}), [field]: value } }));
  };

  const handleCreateTask = async (wpId) => {
    const tf = taskForms[wpId] || {};
    if (!tf.title?.trim()) return;
    setCreatingTask(prev => ({ ...prev, [wpId]: true }));
    try {
      await api.post(`/grant-hub/${collabId}/work-packages/${wpId}/tasks`, {
        title: tf.title.trim(),
        assignee_user_id: tf.assignee_user_id?.trim() || undefined,
        due_date: tf.due_date || undefined,
      });
      setTaskForms(prev => ({ ...prev, [wpId]: {} }));
      onRefresh("work-packages");
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to create task.");
    } finally {
      setCreatingTask(prev => ({ ...prev, [wpId]: false }));
    }
  };

  const handleMarkTaskComplete = async (wpId, taskId) => {
    try {
      await api.patch(`/grant-hub/${collabId}/work-packages/${wpId}/tasks/${taskId}`, { status: "completed" });
      onRefresh("work-packages");
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to update task.");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Work Packages ({wps.length})</h3>
        <Button onClick={() => setShowWpForm(!showWpForm)} size="sm">
          <Plus size={12} /> Add Work Package
        </Button>
      </div>

      {wps.length === 0 && !showWpForm ? (
        <EmptyState
          icon={<Package />}
          title="No work packages yet"
          description="Add your first work package to track progress and assign tasks."
          size="sm"
        />
      ) : null}

      {/* Create WP form */}
      {showWpForm && (
        <SectionCard title="New Work Package">
          <form onSubmit={handleCreateWp} className="space-y-3">
            {wpErr && <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">{wpErr}</div>}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input wrapperClassName="col-span-2" label="Title *" value={wpForm.title} onChange={e => setWpForm(f => ({ ...f, title: e.target.value }))} placeholder="WP1: Data Collection & Analysis" />
              <Textarea wrapperClassName="col-span-2" label="Description" value={wpForm.description} onChange={e => setWpForm(f => ({ ...f, description: e.target.value }))} rows={2} />
              <Input label="Lead User ID" value={wpForm.lead_user_id} onChange={e => setWpForm(f => ({ ...f, lead_user_id: e.target.value }))} placeholder="User ID" />
              <Input label="Budget (€)" type="number" min="0" value={wpForm.budget} onChange={e => setWpForm(f => ({ ...f, budget: e.target.value }))} />
              <Input label="Start Date" type="date" value={wpForm.start_date} onChange={e => setWpForm(f => ({ ...f, start_date: e.target.value }))} />
              <Input label="End Date" type="date" value={wpForm.end_date} onChange={e => setWpForm(f => ({ ...f, end_date: e.target.value }))} />
              <Textarea wrapperClassName="col-span-2" label="Deliverables (one per line)" value={wpForm.deliverables} onChange={e => setWpForm(f => ({ ...f, deliverables: e.target.value }))} rows={3} placeholder={"D1.1 Interim report\nD1.2 Dataset"} />
            </div>
            <div className="flex gap-2">
              <Button type="submit" loading={creatingWp} size="sm">
                {!creatingWp && <Plus size={13} />} Create
              </Button>
              <Button type="button" onClick={() => setShowWpForm(false)} variant="ghost" size="sm">Cancel</Button>
            </div>
          </form>
        </SectionCard>
      )}

      {/* WP list */}
      {wps.map((wp, i) => {
        const wpId = wp._id || wp.id || i;
        const isOpen = expanded.has(wpId);
        const tasks = wp.tasks || [];
        const tf = taskForms[wpId] || {};
        return (
          <Card key={wpId} padding="none">
            <button
              className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-50 transition-colors"
              onClick={() => toggleExpand(wpId)}
            >
              {isOpen ? <ChevronUp size={16} className="text-slate-400 shrink-0" /> : <ChevronDown size={16} className="text-slate-400 shrink-0" />}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-900 text-sm">{wp.title}</span>
                  <StatusBadge status={wp.status || "active"} />
                </div>
                <div className="flex items-center gap-4 text-xs text-slate-400 mt-0.5">
                  {wp.lead_user_name && <span>{wp.lead_user_name}</span>}
                  {wp.budget != null && <span>€{wp.budget.toLocaleString()}</span>}
                  {wp.start_date && wp.end_date && <span>{new Date(wp.start_date).toLocaleDateString()} → {new Date(wp.end_date).toLocaleDateString()}</span>}
                  <span>{tasks.length} tasks</span>
                </div>
              </div>
            </button>

            {isOpen && (
              <div className="px-5 pb-5 space-y-3 border-t border-slate-100 pt-4">
                {wp.description && <p className="text-sm text-slate-600">{wp.description}</p>}

                {tasks.length > 0 ? (
                  <div className="space-y-2">
                    {tasks.map((task, j) => (
                      <div key={task._id || j} className="flex items-center gap-3 p-2.5 bg-slate-50 rounded">
                        <Checkbox
                          checked={task.status === "completed"}
                          onChange={() => handleMarkTaskComplete(wpId, task._id)}
                          disabled={task.status === "completed"}
                        />
                        <span className={`flex-1 text-sm ${task.status === "completed" ? "line-through text-slate-400" : "text-slate-700"}`}>{task.title}</span>
                        {task.assignee_name && <span className="text-xs text-slate-400">{task.assignee_name}</span>}
                        {task.due_date && <span className="text-xs text-slate-400">{new Date(task.due_date).toLocaleDateString()}</span>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">No tasks yet.</p>
                )}

                {/* Add task inline */}
                <div className="flex items-center gap-2 pt-2">
                  <Input
                    value={tf.title || ""}
                    onChange={e => handleTaskFormChange(wpId, "title", e.target.value)}
                    placeholder="Add task..."
                    onKeyDown={e => e.key === "Enter" && handleCreateTask(wpId)}
                    wrapperClassName="flex-1"
                  />
                  <Input
                    value={tf.assignee_user_id || ""}
                    onChange={e => handleTaskFormChange(wpId, "assignee_user_id", e.target.value)}
                    placeholder="Assignee ID"
                    wrapperClassName="w-24"
                  />
                  <Input
                    type="date"
                    value={tf.due_date || ""}
                    onChange={e => handleTaskFormChange(wpId, "due_date", e.target.value)}
                  />
                  <Button
                    onClick={() => handleCreateTask(wpId)}
                    loading={creatingTask[wpId]}
                    size="sm"
                  >
                    Add
                  </Button>
                </div>
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

function ProposalTab({ data, collabId, onRefresh }) {
  const sections = Array.isArray(data) ? data : (data?.sections || []);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ content: "", status: "" });
  const [saving, setSaving] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [addForm, setAddForm] = useState({ section_title: "", content: "", assigned_to_user_id: "" });
  const [adding, setAdding] = useState(false);
  const [addErr, setAddErr] = useState("");

  const approved = sections.filter(s => s.status === "approved").length;

  const startEdit = (s) => {
    setEditingId(s._id);
    setEditForm({ content: s.content || "", status: s.status || "draft" });
  };

  const handleSave = async (sid) => {
    setSaving(true);
    try {
      await api.patch(`/grant-hub/${collabId}/proposal/${sid}`, editForm);
      setEditingId(null);
      onRefresh("proposal");
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to save section.");
    } finally {
      setSaving(false);
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!addForm.section_title.trim()) { setAddErr("Section title required"); return; }
    setAdding(true); setAddErr("");
    try {
      await api.post(`/grant-hub/${collabId}/proposal`, {
        section_title: addForm.section_title.trim(),
        content: addForm.content.trim(),
        assigned_to_user_id: addForm.assigned_to_user_id.trim() || undefined,
      });
      setAddForm({ section_title: "", content: "", assigned_to_user_id: "" });
      setShowAddForm(false);
      onRefresh("proposal");
    } catch (e) {
      setAddErr(e?.response?.data?.error || e.message);
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Collaborative Proposal</h3>
          <p className="text-xs text-slate-500 mt-0.5">{sections.length} sections · {approved} approved</p>
        </div>
        <Button onClick={() => setShowAddForm(!showAddForm)} size="sm">
          <Plus size={12} /> Add Section
        </Button>
      </div>

      {/* Progress bar */}
      {sections.length > 0 && (
        <Card padding="md">
          <ProgressBar
            label="Proposal Completion"
            value={approved}
            max={sections.length}
            valueLabel={`${approved}/${sections.length} sections approved`}
          />
        </Card>
      )}

      {sections.length === 0 && !showAddForm ? (
        <EmptyState
          icon={<FileText />}
          title="Start your collaborative proposal"
          description="Add the first section to begin drafting your grant proposal together."
          size="sm"
        />
      ) : null}

      {/* Add section form */}
      {showAddForm && (
        <SectionCard title="Add Proposal Section">
          <form onSubmit={handleAdd} className="space-y-3">
            {addErr && <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">{addErr}</div>}
            <Input label="Section Title *" value={addForm.section_title} onChange={e => setAddForm(f => ({ ...f, section_title: e.target.value }))} placeholder="e.g. Executive Summary, Methodology" />
            <Textarea label="Content" value={addForm.content} onChange={e => setAddForm(f => ({ ...f, content: e.target.value }))} rows={4} />
            <Input label="Assigned To (User ID)" value={addForm.assigned_to_user_id} onChange={e => setAddForm(f => ({ ...f, assigned_to_user_id: e.target.value }))} placeholder="User ID (optional)" />
            <div className="flex gap-2">
              <Button type="submit" loading={adding} size="sm">
                {!adding && <Plus size={13} />} Add Section
              </Button>
              <Button type="button" onClick={() => setShowAddForm(false)} variant="ghost" size="sm">Cancel</Button>
            </div>
          </form>
        </SectionCard>
      )}

      {/* Sections list */}
      <div className="space-y-3">
        {sections.map((s, i) => (
          <Card key={s._id || i} padding="lg">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <h4 className="font-semibold text-slate-900 text-sm">{s.section_title || s.title}</h4>
                {s.assigned_to_name && <p className="text-xs text-slate-500 mt-0.5">Assigned to {s.assigned_to_name}</p>}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <StatusBadge status={s.status || "draft"} />
                <Button onClick={() => editingId === s._id ? setEditingId(null) : startEdit(s)} variant="link" size="sm" className="!text-slate-500">
                  <Edit2 size={12} /> {editingId === s._id ? "Cancel" : "Edit"}
                </Button>
              </div>
            </div>

            {editingId === s._id ? (
              <div className="space-y-3">
                <Textarea
                  value={editForm.content}
                  onChange={e => setEditForm(f => ({ ...f, content: e.target.value }))}
                  rows={6}
                />
                <div className="flex items-center gap-3">
                  <FormSelect
                    value={editForm.status}
                    onChange={e => setEditForm(f => ({ ...f, status: e.target.value }))}
                    wrapperClassName="!mb-0"
                  >
                    <option value="draft">Draft</option>
                    <option value="review">In Review</option>
                    <option value="approved">Approved</option>
                  </FormSelect>
                  <Button onClick={() => handleSave(s._id)} loading={saving} size="sm" className="!bg-emerald-600 hover:!bg-emerald-700">
                    {!saving && <Save size={12} />} Save
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-600 line-clamp-3">
                {s.content ? (s.content.length > 200 ? s.content.slice(0, 200) + "…" : s.content) : <span className="italic text-slate-400">No content yet.</span>}
              </p>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

function AnalyticsTab({ data, collab }) {
  const stats = data || {};
  const positions = stats.positions || {};
  const team = stats.team || {};
  const invitations = stats.invitations || {};
  const workPackages = stats.work_packages || {};
  const proposal = stats.proposal || {};
  const partnerCountries = stats.partner_countries || [];

  const fillRate = positions.total > 0 ? Math.round((positions.filled / positions.total) * 100) : 0;
  const acceptRate = invitations.sent > 0 ? Math.round((invitations.accepted / invitations.sent) * 100) : 0;
  const wpCompletion = workPackages.total > 0 ? Math.round((workPackages.completed / workPackages.total) * 100) : 0;
  const proposalPct = proposal.total > 0 ? Math.round((proposal.approved / proposal.total) * 100) : 0;

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold text-slate-900">Collaboration Analytics</h3>

      <StatGrid cols={4}>
        <StatCard label="Team Members" value={team.count ?? (collab?.members?.length ?? 0)} />
        <StatCard label="Position Fill Rate" value={`${fillRate}%`} />
        <StatCard label="Invitation Acceptance" value={`${acceptRate}%`} />
        <StatCard label="WP Completion" value={`${wpCompletion}%`} />
      </StatGrid>

      {/* Position fill rate bar */}
      <SectionCard title="Position Fill Rate">
        <ProgressBar value={fillRate} max={100} />
        <p className="text-xs text-slate-500 mt-1">{positions.filled ?? 0} of {positions.total ?? 0} positions filled</p>
      </SectionCard>

      {/* Partner countries */}
      {partnerCountries.length > 0 && (
        <SectionCard title="Partner Diversity — Countries">
          <div className="flex flex-wrap gap-2">
            {partnerCountries.map((c, i) => (
              <Chip key={i} label={c} color="purple" />
            ))}
          </div>
        </SectionCard>
      )}

      {/* Work package progress */}
      <SectionCard title="Work Package Progress">
        <ProgressBar value={wpCompletion} max={100} />
        <p className="text-xs text-slate-500 mt-1">{workPackages.completed ?? 0} of {workPackages.total ?? 0} work packages completed</p>
      </SectionCard>

      {/* Proposal progress */}
      <SectionCard title="Proposal Progress">
        <ProgressBar value={proposalPct} max={100} />
        <p className="text-xs text-slate-500 mt-1">{proposal.approved ?? 0} of {proposal.total ?? 0} sections approved</p>
      </SectionCard>
    </div>
  );
}

// ─── main workspace ───────────────────────────────────────────────────────────

const WORKSPACE_TABS = [
  { key: "overview",       label: "Overview",      icon: BarChart2 },
  { key: "team",           label: "Team",          icon: Users },
  { key: "consortium",     label: "Consortium",    icon: Building2 },
  { key: "positions",      label: "Positions",     icon: Target },
  { key: "matches",        label: "Matches",       icon: TrendingUp },
  { key: "gaps",           label: "Gap Analysis",  icon: AlertTriangle },
  { key: "readiness",      label: "Readiness",     icon: CheckCircle },
  { key: "work-packages",  label: "Work Packages", icon: Package },
  { key: "proposal",       label: "Proposal",      icon: FileText },
  { key: "analytics",      label: "Analytics",     icon: BarChart2 },
];

export default function GrantOpportunityWorkspace() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [collab, setCollab] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const loadedTabs = useRef(new Set());
  const [tabData, setTabData] = useState({});
  const [tabLoading, setTabLoading] = useState({});
  const [closing, setClosing] = useState(false);

  const isLead = collab && (collab.lead_user_id === user?._id || collab.lead_user_id === user?.id);

  const loadTabData = useCallback(async (tab) => {
    setTabLoading(prev => ({ ...prev, [tab]: true }));
    try {
      let data = {};
      if (tab === "overview") {
        const [team, positions, readiness] = await Promise.all([
          api.get(`/grant-hub/${id}/team`),
          api.get(`/grant-hub/${id}/positions`),
          api.get(`/grant-hub/${id}/readiness`),
        ]);
        data = { team: team.data, positions: positions.data, readiness: readiness.data };
      } else if (tab === "team") {
        const [team, positions] = await Promise.all([
          api.get(`/grant-hub/${id}/team`),
          api.get(`/grant-hub/${id}/positions`),
        ]);
        data = { team: team.data, positions: positions.data };
      } else if (tab === "consortium") {
        data = (await api.get(`/grant-hub/${id}/consortium`)).data;
      } else if (tab === "positions") {
        data = (await api.get(`/grant-hub/${id}/positions`)).data;
      } else if (tab === "matches") {
        data = (await api.get(`/grant-hub/${id}/matches`)).data;
      } else if (tab === "gaps") {
        data = (await api.get(`/grant-hub/${id}/gaps`)).data;
      } else if (tab === "readiness") {
        data = (await api.get(`/grant-hub/${id}/readiness`)).data;
      } else if (tab === "work-packages") {
        data = (await api.get(`/grant-hub/${id}/work-packages`)).data;
      } else if (tab === "proposal") {
        data = (await api.get(`/grant-hub/${id}/proposal`)).data;
      } else if (tab === "analytics") {
        data = (await api.get(`/grant-hub/${id}/analytics`)).data;
      }
      setTabData(prev => ({ ...prev, [tab]: data }));
    } catch (e) {
      setTabData(prev => ({ ...prev, [tab]: { _error: e?.response?.data?.error || e.message } }));
    } finally {
      setTabLoading(prev => ({ ...prev, [tab]: false }));
    }
  }, [id]);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (!loadedTabs.current.has(tab)) {
      loadedTabs.current.add(tab);
      loadTabData(tab);
    }
  };

  const handleTabRefresh = (tab) => {
    loadedTabs.current.delete(tab);
    handleTabChange(tab);
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      try {
        const { data } = await api.get(`/grant-hub/${id}`);
        setCollab(data);
        loadedTabs.current.add("overview");
        loadTabData("overview");
      } catch (e) {
        setError(e?.response?.data?.error || e.message);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [id, loadTabData]);

  const handleRefreshMatches = async () => {
    try {
      await api.post(`/grant-hub/${id}/matches/refresh`);
      handleTabRefresh("matches");
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to refresh matches.");
    }
  };

  const handleClose = async () => {
    if (!window.confirm("Close this collaboration? This cannot be undone.")) return;
    setClosing(true);
    try {
      await api.patch(`/grant-hub/${id}`, { status: "closed" });
      setCollab(prev => ({ ...prev, status: "closed" }));
    } catch (e) {
      alert(e?.response?.data?.error || "Failed to close collaboration.");
    } finally {
      setClosing(false);
    }
  };

  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href).then(() => alert("Link copied to clipboard!"));
  };

  if (loading) {
    return (
      <ResearchLayout title="Grant Workspace">
        <div className="flex items-center justify-center py-24">
          <Spinner size={28} />
        </div>
      </ResearchLayout>
    );
  }

  if (error) {
    return (
      <ResearchLayout title="Grant Workspace">
        <Card padding="lg" className="max-w-md w-full text-center mx-auto">
          <EmptyState
            icon={<XCircle />}
            title="Failed to load collaboration"
            description={error}
            action={
              <Button as={Link} to="/grant-collaboration-hub" variant="link">
                <ArrowLeft size={14} /> Back to Hub
              </Button>
            }
            size="sm"
          />
        </Card>
      </ResearchLayout>
    );
  }

  const currentTabData = tabData[activeTab];
  const isTabLoading = tabLoading[activeTab];
  const hasTabError = currentTabData?._error;

  const headerActions = (
    <>
      <Button onClick={handleRefreshMatches} variant="ghost" size="sm">
        <RefreshCw size={12} /> Refresh Matches
      </Button>
      <Button onClick={handleShare} variant="ghost" size="sm">
        <Share2 size={12} /> Share
      </Button>
      {isLead && collab?.status !== "closed" && (
        <Button onClick={handleClose} loading={closing} variant="ghost" size="sm" className="!border-red-200 !text-red-600 hover:!bg-red-50">
          {!closing && <X size={12} />} Close Collaboration
        </Button>
      )}
    </>
  );

  return (
    <ResearchLayout
      title={collab?.title}
      actions={headerActions}
      nav={
        <NavTabs
          tabs={WORKSPACE_TABS.map(({ key, label, icon }) => ({ id: key, label, icon }))}
          active={activeTab}
          onChange={handleTabChange}
        />
      }
    >
      <div className="mb-6">
          {/* Back nav */}
          <Link to="/grant-collaboration-hub" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-900 transition-colors mb-3">
            <ArrowLeft size={13} /> Grant Collaboration Hub
          </Link>

          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <StatusBadge status={collab?.status} />
            {collab?.funding_source && (
              <span className="flex items-center gap-1 text-xs text-slate-500">
                <Briefcase size={12} /> {collab.funding_source}
              </span>
            )}
            {collab?.deadline && (
              <span className="flex items-center gap-1 text-xs text-slate-500">
                <Calendar size={12} /> {new Date(collab.deadline).toLocaleDateString()}
              </span>
            )}
          </div>
          {collab?.research_areas?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {collab.research_areas.map((a, i) => <Chip key={i} label={a} color="indigo" />)}
            </div>
          )}
      </div>

      {/* Tab content */}
        {isTabLoading ? (
          <TabLoading />
        ) : hasTabError ? (
          <TabError message={currentTabData._error} />
        ) : (
          <>
            {activeTab === "overview" && (
              <OverviewTab data={currentTabData} collab={collab} />
            )}
            {activeTab === "team" && (
              <TeamTab
                data={currentTabData}
                collabId={id}
                isLead={isLead}
                onRefresh={handleTabRefresh}
              />
            )}
            {activeTab === "consortium" && (
              <ConsortiumTab
                data={currentTabData}
                collabId={id}
                isLead={isLead}
                onRefresh={handleTabRefresh}
              />
            )}
            {activeTab === "positions" && (
              <PositionsTab
                data={currentTabData}
                collabId={id}
                isLead={isLead}
                onRefresh={handleTabRefresh}
              />
            )}
            {activeTab === "matches" && (
              <MatchesTab
                data={currentTabData}
                collabId={id}
                onRefresh={handleTabRefresh}
              />
            )}
            {activeTab === "gaps" && (
              <GapAnalysisTab
                data={currentTabData}
                collabId={id}
                onRefresh={handleTabRefresh}
              />
            )}
            {activeTab === "readiness" && (
              <ReadinessTab data={currentTabData} />
            )}
            {activeTab === "work-packages" && (
              <WorkPackagesTab
                data={currentTabData}
                collabId={id}
                onRefresh={handleTabRefresh}
              />
            )}
            {activeTab === "proposal" && (
              <ProposalTab
                data={currentTabData}
                collabId={id}
                onRefresh={handleTabRefresh}
              />
            )}
            {activeTab === "analytics" && (
              <AnalyticsTab data={currentTabData} collab={collab} />
            )}
          </>
        )}
    </ResearchLayout>
  );
}

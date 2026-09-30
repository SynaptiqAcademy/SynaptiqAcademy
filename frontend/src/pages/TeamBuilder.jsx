/**
 * P1 Phase 8F — Interdisciplinary Research Team Builder.
 *
 * Research Need -> Team Blueprint (proposed roles) -> real Synaptiq
 * candidates per role -> user selects people -> review -> individual Phase
 * 8E collaboration invitations. The system proposes; the human decides —
 * nothing here ever sends an invitation without an explicit, individual
 * "Send" click, and there is no bulk-send action anywhere on this page.
 */
import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import api from "@/lib/api";
import { NAVY, TEXT_SECONDARY, TEXT_MUTED, BRD, EMERALD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Button, Badge, Input, Textarea, FormSelect, EmptyState, LoadingOverlay } from "@/components/ds";

const PRIORITY_META = {
  essential: { label: "Essential", color: "#B91C1C" },
  useful: { label: "Useful", color: NAVY },
  optional: { label: "Optional", color: TEXT_MUTED },
};

const STATUS_META = {
  proposed: { label: "Proposed", color: TEXT_MUTED },
  invitation_pending: { label: "Invitation pending", color: "#B45309" },
  accepted: { label: "Accepted", color: EMERALD },
  declined: { label: "Declined", color: "#B91C1C" },
  withdrawn: { label: "Withdrawn", color: TEXT_MUTED },
};

const PURPOSE_OPTIONS = [
  { value: "co_author_paper", label: "Co-author a paper" },
  { value: "join_research_project", label: "Join a research project" },
  { value: "grant_proposal", label: "Grant proposal" },
  { value: "methodological_support", label: "Methodological support" },
  { value: "data_analysis_support", label: "Data analysis / technical support" },
  { value: "peer_review", label: "Peer review / feedback" },
  { value: "policy_research", label: "Policy research" },
  { value: "research_consultation", label: "Research consultation" },
  { value: "domain_expertise", label: "Literature / domain expertise" },
  { value: "conference_collaboration", label: "Conference collaboration" },
  { value: "teaching_collaboration", label: "Teaching / educational research collaboration" },
  { value: "other", label: "Other" },
];

function CandidateExplorer({ blueprintId, role, onSelect, onClose }) {
  const [loading, setLoading] = useState(true);
  const [candidates, setCandidates] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    api.get(`/team-builder/blueprints/${blueprintId}/roles/${role.role_id}/candidates`)
      .then((r) => { if (mounted) setCandidates(r.data.candidates); })
      .catch((e) => { if (mounted) setError(e?.response?.data?.detail || "Could not load candidates."); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [blueprintId, role.role_id]);

  return (
    <div style={{ marginTop: 10, padding: 14, background: "#F8FAFC", border: `1px solid ${BRD}` }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: NAVY }}>Candidates for {role.label}</div>
        <Button size="sm" variant="ghost" onClick={onClose}>Close</Button>
      </div>
      {loading ? <LoadingOverlay text="Finding candidates…" /> : error ? (
        <div style={{ fontSize: 12.5, color: "#B91C1C" }}>{error}</div>
      ) : candidates.length === 0 ? (
        <EmptyState
          title="No discoverable Synaptiq member currently provides enough profile evidence for this role."
          description="Try broadening the role's expertise, or check back as more researchers join."
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {candidates.map((c) => (
            <div key={c.id} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: 10, background: "#fff", border: `1px solid ${BRD}` }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <Link to={`/profile/${c.id}`} style={{ fontSize: 13, fontWeight: 700, color: NAVY, textDecoration: "none" }}>{c.name || "Researcher"}</Link>
                <div style={{ fontSize: 11.5, color: TEXT_SECONDARY }}>
                  {[c.academic_role || c.professional_role, c.institution].filter(Boolean).join(" · ")}
                </div>
                {c.explanation && <p style={{ fontSize: 11.5, color: TEXT_SECONDARY, margin: "4px 0 0", lineHeight: 1.5 }}>{c.explanation}</p>}
                {c.also_relevant_to?.length > 0 && (
                  <div style={{ fontSize: 10.5, color: TEXT_MUTED, marginTop: 3 }}>
                    Also relevant to: {c.also_relevant_to.join(", ")}
                  </div>
                )}
                {c.available_for_collaboration === false && (
                  <div style={{ fontSize: 10.5, color: "#92400E", marginTop: 3, fontStyle: "italic" }}>
                    Not currently open to collaboration
                  </div>
                )}
              </div>
              <Button size="sm" variant={c.already_selected ? "ghost" : "primary"} disabled={c.already_selected} onClick={() => onSelect(c.id)}>
                {c.already_selected ? "Added" : "Add to proposed team"}
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RoleCard({ blueprintId, role, onChange }) {
  const [exploring, setExploring] = useState(false);
  const [busy, setBusy] = useState(false);
  const meta = PRIORITY_META[role.priority] || PRIORITY_META.useful;

  const patchRole = async (edits) => {
    setBusy(true);
    try {
      const r = await api.patch(`/team-builder/blueprints/${blueprintId}`, { role_edits: [{ role_id: role.role_id, ...edits }] });
      onChange(r.data);
    } finally {
      setBusy(false);
    }
  };

  const removeRole = async () => {
    setBusy(true);
    try {
      const r = await api.patch(`/team-builder/blueprints/${blueprintId}`, { remove_role_ids: [role.role_id] });
      onChange(r.data);
    } finally {
      setBusy(false);
    }
  };

  const selectCandidate = async (candidateId) => {
    const r = await api.post(`/team-builder/blueprints/${blueprintId}/roles/${role.role_id}/candidates/${candidateId}/select`);
    onChange(r.data);
  };

  const unselectCandidate = async (candidateId) => {
    const r = await api.delete(`/team-builder/blueprints/${blueprintId}/roles/${role.role_id}/candidates/${candidateId}`);
    onChange(r.data);
  };

  return (
    <Card padding="md" style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10, flexWrap: "wrap" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ fontSize: 14.5, fontWeight: 700, color: NAVY }}>{role.label}</div>
            <span style={{ fontSize: 10, fontWeight: 700, color: meta.color, background: `${meta.color}14`, padding: "2px 7px" }}>{meta.label}</span>
          </div>
          {role.why_needed && <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: "4px 0 0", lineHeight: 1.5, maxWidth: 480 }}>{role.why_needed}</p>}
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <Button size="sm" variant="ghost" onClick={removeRole} disabled={busy}>Remove role</Button>
        </div>
      </div>

      <div style={{ marginTop: 10 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12.5, color: TEXT_SECONDARY, cursor: "pointer" }}>
          <input type="checkbox" checked={!!role.self_covers} onChange={(e) => patchRole({ self_covers: e.target.checked })} disabled={busy} />
          I can cover this role myself
        </label>
      </div>

      {role.self_covers ? (
        <div style={{ marginTop: 8, fontSize: 12.5, color: EMERALD, fontWeight: 600 }}>You cover this role</div>
      ) : (
        <>
          {(role.selected_candidates || []).length > 0 && (
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
              {role.selected_candidates.map((c) => {
                const st = STATUS_META[c.status] || STATUS_META.proposed;
                return (
                  <div key={c.candidate_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12.5, padding: "6px 10px", background: "#F8FAFC", border: `1px solid ${BRD}` }}>
                    <Link to={`/profile/${c.candidate_id}`} style={{ color: NAVY, fontWeight: 600, textDecoration: "none" }}>{c.candidate_name || "Researcher"}</Link>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ color: st.color, fontWeight: 700, fontSize: 11 }}>{st.label}</span>
                      {c.status === "proposed" && (
                        <Button size="sm" variant="ghost" onClick={() => unselectCandidate(c.candidate_id)}>Remove</Button>
                      )}
                      {(c.status === "declined" || c.status === "withdrawn") && (
                        <Button size="sm" variant="ghost" onClick={() => unselectCandidate(c.candidate_id)}>Find another collaborator</Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          <div style={{ marginTop: 10 }}>
            <Button size="sm" variant="ghost" onClick={() => setExploring((v) => !v)}>
              {exploring ? "Hide candidates" : "Explore candidates"}
            </Button>
          </div>
          {exploring && (
            <CandidateExplorer
              blueprintId={blueprintId}
              role={role}
              onSelect={(id) => selectCandidate(id)}
              onClose={() => setExploring(false)}
            />
          )}
        </>
      )}
    </Card>
  );
}

function ReviewAndInvite({ blueprint, onChange }) {
  const [drafts, setDrafts] = useState({}); // candidate_id -> {purpose, contribution, message}
  const [sending, setSending] = useState(null);

  const proposed = [];
  for (const role of blueprint.roles) {
    for (const c of role.selected_candidates || []) {
      if (c.status === "proposed") proposed.push({ role, candidate: c });
    }
  }

  if (proposed.length === 0) return null;

  const draftFor = (candidateId, role, c) => drafts[candidateId] || {
    purpose: "", contribution: (c.contribution || [])[0] || "",
    message: `Hello,\n\nI'm building an interdisciplinary team for a research project and think your expertise in ${role.label} could be a strong fit${c.explanation ? ` — ${c.explanation}` : ""}.\n\nI'd like to invite you to explore a possible collaboration.`,
  };

  const updateDraft = (candidateId, patch, role, c) => {
    setDrafts((prev) => ({ ...prev, [candidateId]: { ...draftFor(candidateId, role, c), ...prev[candidateId], ...patch } }));
  };

  const send = async (role, c) => {
    setSending(c.candidate_id);
    try {
      const d = draftFor(c.candidate_id, role, c);
      const r = await api.post(
        `/team-builder/blueprints/${blueprint.id}/roles/${role.role_id}/candidates/${c.candidate_id}/invite`,
        { collaboration_purpose: d.purpose || null, expected_contribution: d.contribution, message: d.message },
      );
      onChange(r.data);
    } finally {
      setSending(null);
    }
  };

  return (
    <Card padding="lg" style={{ marginTop: 20, border: `1px solid ${NAVY}25` }}>
      <div style={{ fontSize: 15, fontWeight: 700, color: NAVY, marginBottom: 4 }}>Review & invite</div>
      <p style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 0, marginBottom: 14 }}>
        Each invitation below is sent individually — review and edit before sending. Nothing is sent automatically.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {proposed.map(({ role, candidate: c }) => {
          const d = draftFor(c.candidate_id, role, c);
          return (
            <div key={`${role.role_id}-${c.candidate_id}`} style={{ padding: 14, border: `1px solid ${BRD}` }}>
              <div style={{ fontSize: 12.5, fontWeight: 700, color: NAVY, marginBottom: 8 }}>
                {role.label} — <Link to={`/profile/${c.candidate_id}`} style={{ color: NAVY }}>{c.candidate_name || "View profile"}</Link>
              </div>
              <FormSelect
                label="Collaboration type" size="sm"
                value={d.purpose} onChange={(e) => updateDraft(c.candidate_id, { purpose: e.target.value }, role, c)}
              >
                <option value="">Select…</option>
                {PURPOSE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </FormSelect>
              <div style={{ marginTop: 8 }}>
                <label style={{ fontSize: 11, fontWeight: 700, color: TEXT_SECONDARY, display: "block", marginBottom: 3 }}>Requested contribution</label>
                <Textarea rows={2} value={d.contribution} onChange={(e) => updateDraft(c.candidate_id, { contribution: e.target.value }, role, c)} />
              </div>
              <div style={{ marginTop: 8 }}>
                <label style={{ fontSize: 11, fontWeight: 700, color: TEXT_SECONDARY, display: "block", marginBottom: 3 }}>Message</label>
                <Textarea rows={5} value={d.message} onChange={(e) => updateDraft(c.candidate_id, { message: e.target.value }, role, c)} />
              </div>
              <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                <Button size="sm" variant="primary" onClick={() => send(role, c)} loading={sending === c.candidate_id}>Send</Button>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// P1 Phase 8G — human-initiated project creation (§2/§3): pre-filled from
// the Research Need, but every field is a review-and-edit step, and only
// accepted collaborators (never proposed/pending/declined/withdrawn) are
// offered as project members.
function CreateProjectSection({ blueprint, onCreated }) {
  const [reviewing, setReviewing] = useState(false);
  const [title, setTitle] = useState(blueprint.research_need?.original_query?.slice(0, 120) || "");
  const [description, setDescription] = useState(blueprint.research_need?.concise_problem_statement || "");
  const [objectives, setObjectives] = useState((blueprint.research_need?.required_expertise || []).map((t) => `Address ${t}`).join("\n"));
  const [visibility, setVisibility] = useState("private");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const accepted = [];
  for (const role of blueprint.roles) {
    for (const c of role.selected_candidates || []) {
      if (c.status === "accepted") accepted.push({ role, candidate: c });
    }
  }

  if (blueprint.project_id) {
    return (
      <Card padding="lg" style={{ marginTop: 20, border: `1px solid ${EMERALD}30` }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 6 }}>Research project created</div>
        <Link to={`/projects/${blueprint.project_id}`}><Button variant="primary">Open Research Project</Button></Link>
      </Card>
    );
  }

  if (accepted.length === 0) return null;

  const create = async () => {
    setCreating(true);
    setError("");
    try {
      const r = await api.post(`/team-builder/blueprints/${blueprint.id}/create-project`, {
        title: title.trim() || "Untitled Research Project",
        description,
        objectives: objectives.split("\n").map((o) => o.trim()).filter(Boolean),
        visibility,
      });
      onCreated({ ...blueprint, project_id: r.data.project_id });
    } catch (e) {
      setError(e?.response?.data?.detail || "Could not create the project. Please try again.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <Card padding="lg" style={{ marginTop: 20, border: `1px solid ${NAVY}25` }}>
      <div style={{ fontSize: 15, fontWeight: 700, color: NAVY, marginBottom: 4 }}>Accepted collaborators</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 12 }}>
        {accepted.map(({ role, candidate: c }) => (
          <div key={c.candidate_id} style={{ fontSize: 12.5, color: TEXT_SECONDARY }}>
            <strong style={{ color: NAVY }}>{c.candidate_name || "Researcher"}</strong> — {role.label}
          </div>
        ))}
      </div>

      {!reviewing ? (
        <Button variant="primary" onClick={() => setReviewing(true)}>Create Research Project</Button>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: TEXT_SECONDARY, display: "block", marginBottom: 3 }}>Project title</label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} size="sm" />
          </div>
          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: TEXT_SECONDARY, display: "block", marginBottom: 3 }}>Research question / description</label>
            <Textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: TEXT_SECONDARY, display: "block", marginBottom: 3 }}>Objectives (one per line)</label>
            <Textarea rows={4} value={objectives} onChange={(e) => setObjectives(e.target.value)} />
          </div>
          <FormSelect label="Visibility" size="sm" value={visibility} onChange={(e) => setVisibility(e.target.value)}>
            <option value="private">Private</option>
            <option value="team">Team only</option>
            <option value="public">Public</option>
          </FormSelect>
          {error && <div style={{ fontSize: 12, color: "#B91C1C" }}>{error}</div>}
          <div style={{ display: "flex", gap: 8 }}>
            <Button variant="primary" onClick={create} loading={creating}>Create Project</Button>
            <Button variant="ghost" onClick={() => setReviewing(false)} disabled={creating}>Cancel</Button>
          </div>
        </div>
      )}
    </Card>
  );
}

export default function TeamBuilder() {
  const { id } = useParams();
  const [blueprint, setBlueprint] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newRoleLabel, setNewRoleLabel] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    api.get(`/team-builder/blueprints/${id}`)
      .then((r) => setBlueprint(r.data))
      .catch((e) => setError(e?.response?.data?.detail || "Could not load this team blueprint."))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const addRole = async () => {
    if (!newRoleLabel.trim()) return;
    const r = await api.patch(`/team-builder/blueprints/${id}`, { role_edits: [{ label: newRoleLabel.trim() }] });
    setBlueprint(r.data);
    setNewRoleLabel("");
  };

  if (loading) return <ResearchLayout title="Team Builder"><LoadingOverlay text="Loading team blueprint…" /></ResearchLayout>;
  if (error || !blueprint) return <ResearchLayout title="Team Builder"><EmptyState title="Could not load this team blueprint." description={error} /></ResearchLayout>;

  return (
    <ResearchLayout title="Interdisciplinary Team Builder" subtitle={blueprint.research_need?.concise_problem_statement || blueprint.research_need?.original_query}>
      <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 16 }}>
        The system proposes roles and real candidates — you decide who to invite. Nothing is sent without your explicit review.
      </div>

      {blueprint.roles.map((role) => (
        <RoleCard key={role.role_id} blueprintId={id} role={role} onChange={setBlueprint} />
      ))}

      <Card padding="md" style={{ marginBottom: 20, display: "flex", gap: 8, alignItems: "center" }}>
        <Input value={newRoleLabel} onChange={(e) => setNewRoleLabel(e.target.value)} placeholder="Add another role (e.g. Health Economics)" size="sm" wrapperClassName="flex-1" />
        <Button size="sm" variant="ghost" onClick={addRole}>Add role</Button>
      </Card>

      <ReviewAndInvite blueprint={blueprint} onChange={setBlueprint} />
      <CreateProjectSection blueprint={blueprint} onCreated={setBlueprint} />
    </ResearchLayout>
  );
}

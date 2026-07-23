import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { UserCheck, Star, X } from "lucide-react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import {
  Card, Badge, Tag, Button, Input, Textarea, FormSelect, FormRow, Modal,
  NavTabs, EmptyState, LoadingOverlay, InlineError,
} from "@/components/ds";

const EXPERTISE_AREAS = [
  "publication_coaching", "grant_writing", "career_planning", "peer_review",
  "statistical_methods", "research_design", "teaching", "industry_transition", "leadership", "funding",
];

const AVAIL_COLOR = { full: EMERALD, limited: "#f59e0b", unavailable: "#dc2626" };

function MentorCard({ mentor, onRequest }) {
  const avail = mentor.availability || "limited";
  const color = AVAIL_COLOR[avail] || "#f59e0b";
  return (
    <Card padding="md">
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <div style={{ width: 44, height: 44, borderRadius: "50%", background: `${ACCENT}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: 18, fontWeight: 800, color: ACCENT }}>
          {(mentor.name || "M")[0].toUpperCase()}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: NAVY }}>{mentor.name || "Mentor"}</div>
          <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{mentor.institution || ""}{mentor.country ? ` · ${mentor.country}` : ""}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
            <Badge color={color} size="sm">{avail}</Badge>
            {mentor.rating > 0 && (
              <span style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 12, color: "#f59e0b" }}>
                <Star size={12} fill="#f59e0b" />{mentor.rating.toFixed(1)} ({mentor.rating_count})
              </span>
            )}
            <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>Up to {mentor.max_mentees} mentees</span>
          </div>
          {mentor.expertise_areas?.length > 0 && (
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 8 }}>
              {mentor.expertise_areas.slice(0, 4).map(ea => (
                <Badge key={ea} color={ACCENT} size="sm">{ea.replace(/_/g, " ")}</Badge>
              ))}
            </div>
          )}
          {mentor.bio && <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 8, lineHeight: 1.5 }}>{mentor.bio.slice(0, 100)}{mentor.bio.length > 100 ? "…" : ""}</div>}
        </div>
        <Button variant="primary" size="sm" onClick={() => onRequest(mentor)} style={{ flexShrink: 0 }}>
          Request
        </Button>
      </div>
    </Card>
  );
}

function RequestModal({ mentor, onClose, onSuccess }) {
  const [form, setForm] = useState({ mentor_user_id: mentor.user_id || "", message: "", goals: [], duration_months: 6 });
  const [goalInput, setGoalInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const addGoal = () => { if (goalInput.trim()) { setForm(f => ({ ...f, goals: [...f.goals, goalInput.trim()] })); setGoalInput(""); } };
  const removeGoal = g => setForm(f => ({ ...f, goals: f.goals.filter(x => x !== g) }));

  const handleSubmit = async () => {
    setSaving(true); setError("");
    try {
      const r = await axios.post("/api/network/mentors/request", form);
      if (r.data.error) { setError(r.data.error); setSaving(false); return; }
      onSuccess(); onClose();
    } catch (e) { setError(e.response?.data?.detail || "Failed to send request"); setSaving(false); }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={`Request Mentorship from ${mentor.name}`}
      size="sm"
      footer={
        <Button variant="primary" onClick={handleSubmit} disabled={saving || !form.message.trim()} loading={saving} style={{ width: "100%" }}>
          {saving ? "Sending…" : "Send Request"}
        </Button>
      }
    >
      {error && <InlineError style={{ marginBottom: 12 }}>{error}</InlineError>}
      <Textarea
        label="Message *"
        value={form.message}
        onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
        rows={4}
        placeholder="Introduce yourself and explain what you're looking for…"
      />
      <div>
        <label style={{ fontSize: 12, fontWeight: 600, color: NAVY, display: "block", marginBottom: 4 }}>Mentorship Goals</label>
        <div style={{ display: "flex", gap: 6, marginBottom: 6 }}>
          <Input
            value={goalInput}
            onChange={e => setGoalInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addGoal(); } }}
            placeholder="E.g. Publish in Nature, Get first grant…"
            wrapperClassName="flex-1"
          />
          <Button variant="subtle" onClick={addGoal}>Add</Button>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {form.goals.map(g => (
            <Tag key={g} variant="removable" color={ACCENT} onRemove={() => removeGoal(g)}>
              {g}
            </Tag>
          ))}
        </div>
      </div>
      <FormSelect
        label="Duration (months)"
        value={form.duration_months}
        onChange={e => setForm(f => ({ ...f, duration_months: Number(e.target.value) }))}
      >
        {[3, 6, 9, 12, 18, 24].map(m => <option key={m} value={m}>{m} months</option>)}
      </FormSelect>
    </Modal>
  );
}

function BecomeMentorModal({ onClose, onSuccess }) {
  const [form, setForm] = useState({ bio: "", expertise_areas: [], availability: "limited", max_mentees: 3, languages: ["English"] });
  const [saving, setSaving] = useState(false);
  const toggleExpertise = ea => setForm(f => ({
    ...f, expertise_areas: f.expertise_areas.includes(ea) ? f.expertise_areas.filter(x => x !== ea) : [...f.expertise_areas, ea]
  }));

  const handleSubmit = async () => {
    setSaving(true);
    try { await axios.post("/api/network/mentors/me", form); onSuccess(); onClose(); }
    catch { setSaving(false); }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Become a Mentor"
      size="md"
      footer={
        <Button variant="primary" onClick={handleSubmit} disabled={saving} loading={saving} style={{ width: "100%" }}>
          {saving ? "Creating…" : "Create Mentor Profile"}
        </Button>
      }
    >
      <Textarea
        label="Mentor Bio"
        value={form.bio}
        onChange={e => setForm(f => ({ ...f, bio: e.target.value }))}
        rows={3}
        placeholder="Describe your background, research focus, and what you can offer mentees…"
      />
      <div>
        <label style={{ fontSize: 12, fontWeight: 600, color: NAVY, display: "block", marginBottom: 8 }}>Expertise Areas</label>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {EXPERTISE_AREAS.map(ea => (
            <Tag
              key={ea}
              color={form.expertise_areas.includes(ea) ? ACCENT : undefined}
              onClick={() => toggleExpertise(ea)}
            >
              {ea.replace(/_/g, " ")}
            </Tag>
          ))}
        </div>
      </div>
      <FormRow cols={2}>
        <FormSelect
          label="Availability"
          value={form.availability}
          onChange={e => setForm(f => ({ ...f, availability: e.target.value }))}
        >
          <option value="full">Full</option>
          <option value="limited">Limited</option>
          <option value="unavailable">Unavailable</option>
        </FormSelect>
        <Input
          label="Max Mentees"
          type="number"
          min={1}
          max={10}
          value={form.max_mentees}
          onChange={e => setForm(f => ({ ...f, max_mentees: Number(e.target.value) }))}
        />
      </FormRow>
    </Modal>
  );
}

export default function MentorshipPlatform() {
  const [mentors, setMentors] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({ q: "", expertise_area: "", availability: "" });
  const [tab, setTab] = useState("find");
  const [requestMentor, setRequestMentor] = useState(null);
  const [showBecomeMentor, setShowBecomeMentor] = useState(false);
  const [myRequests, setMyRequests] = useState([]);
  const [myProfile, setMyProfile] = useState(null);

  const fetchMentors = useCallback(async () => {
    setLoading(true);
    try {
      const params = { limit: 20, ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)) };
      const r = await axios.get("/api/network/mentors", { params });
      setMentors(r.data.results || []);
      setTotal(r.data.total || 0);
    } catch { } finally { setLoading(false); }
  }, [filters]);

  const fetchMyRequests = useCallback(async () => {
    try {
      const r = await axios.get("/api/network/mentors/requests?role=mentee");
      setMyRequests(r.data || []);
    } catch { }
  }, []);

  const fetchMyProfile = useCallback(async () => {
    try {
      const r = await axios.get("/api/network/mentors/me");
      setMyProfile(r.data);
    } catch { }
  }, []);

  const fetchMentorsRef = useRef(fetchMentors);
  useEffect(() => { fetchMentorsRef.current = fetchMentors; }, [fetchMentors]);
  useEffect(() => { fetchMentorsRef.current(); fetchMyRequests(); fetchMyProfile(); }, [fetchMyRequests, fetchMyProfile]);

  return (
    <DiscoveryLayout
      title="Mentorship"
      icon={<UserCheck size={22} color={NAVY} />}
      actions={
        <Button variant="subtle" onClick={() => setShowBecomeMentor(true)}>
          {myProfile ? "Edit Mentor Profile" : "Become a Mentor"}
        </Button>
      }
    >
      <div style={{ marginBottom: 16 }}>
        <NavTabs
          variant="pill"
          tabs={[
            { id: "find", label: "Find a Mentor" },
            { id: "requests", label: "My Requests", count: myRequests.length },
            { id: "mentor", label: "As a Mentor" },
          ]}
          active={tab}
          onChange={setTab}
        />
      </div>

      {tab === "find" && (
        <>
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
            <Input
              value={filters.q}
              onChange={e => setFilters(f => ({ ...f, q: e.target.value }))}
              onKeyDown={e => e.key === "Enter" && fetchMentors()}
              placeholder="Search mentors…"
              style={{ minWidth: 160 }}
              wrapperClassName="flex-1"
            />
            <FormSelect value={filters.expertise_area} onChange={e => { setFilters(f => ({ ...f, expertise_area: e.target.value })); }}>
              <option value="">Any expertise</option>
              {EXPERTISE_AREAS.map(ea => <option key={ea} value={ea}>{ea.replace(/_/g, " ")}</option>)}
            </FormSelect>
            <FormSelect value={filters.availability} onChange={e => { setFilters(f => ({ ...f, availability: e.target.value })); }}>
              <option value="">Any availability</option>
              <option value="full">Full</option>
              <option value="limited">Limited</option>
            </FormSelect>
            <Button variant="primary" onClick={fetchMentors}>Search</Button>
          </div>
          {loading ? <LoadingOverlay text="Loading…" /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {mentors.length === 0 ? (
                <EmptyState title="No mentors found." />
              ) : mentors.map((m, i) => <MentorCard key={m.id || i} mentor={m} onRequest={setRequestMentor} />)}
            </div>
          )}
        </>
      )}

      {tab === "requests" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {myRequests.length === 0 ? (
            <EmptyState title="No mentorship requests yet." />
          ) : myRequests.map((r, i) => (
            <Card key={i} padding="sm">
              <div style={{ fontWeight: 700, fontSize: 13, color: NAVY }}>Request to mentor</div>
              <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>
                Status:{" "}
                <Badge variant={r.status === "accepted" ? "success" : r.status === "rejected" ? "danger" : "warning"} size="sm">
                  {r.status}
                </Badge>
              </div>
              {r.goals?.length > 0 && <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 4 }}>Goals: {r.goals.join(", ")}</div>}
            </Card>
          ))}
        </div>
      )}

      {tab === "mentor" && (
        <div>
          {myProfile ? (
            <Card padding="lg">
              <div style={{ fontWeight: 700, fontSize: 14, color: NAVY, marginBottom: 8 }}>Your Mentor Profile</div>
              <div style={{ fontSize: 13, color: TEXT_SECONDARY }}>Availability: <b>{myProfile.availability}</b></div>
              <div style={{ fontSize: 13, color: TEXT_SECONDARY }}>Max mentees: <b>{myProfile.max_mentees}</b></div>
              {myProfile.rating > 0 && <div style={{ fontSize: 13, color: TEXT_SECONDARY }}>Rating: <b>{myProfile.rating.toFixed(1)} ({myProfile.rating_count} reviews)</b></div>}
              {myProfile.expertise_areas?.length > 0 && (
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
                  {myProfile.expertise_areas.map(ea => (
                    <Badge key={ea} color={ACCENT} size="sm">{ea.replace(/_/g, " ")}</Badge>
                  ))}
                </div>
              )}
            </Card>
          ) : (
            <EmptyState
              title="You're not a mentor yet"
              description="Share your expertise by creating a mentor profile."
              action={<Button variant="primary" onClick={() => setShowBecomeMentor(true)}>Become a Mentor</Button>}
            />
          )}
        </div>
      )}

      {requestMentor && <RequestModal mentor={requestMentor} onClose={() => setRequestMentor(null)} onSuccess={fetchMyRequests} />}
      {showBecomeMentor && <BecomeMentorModal onClose={() => setShowBecomeMentor(false)} onSuccess={fetchMyProfile} />}
    </DiscoveryLayout>
  );
}

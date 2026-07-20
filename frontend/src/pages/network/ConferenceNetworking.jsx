import React, { useState, useEffect } from "react";
import axios from "axios";
import { Plus, MapPin, Clock, Users, CheckCircle } from "lucide-react";
import { NAVY, BRD, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import { Card, Badge, Button, Input, Textarea, FormSelect, FormRow, Checkbox, Modal, NavTabs, EmptyState, LoadingOverlay } from "@/components/ds";

const TYPE_COLOR = {
  seminar: ACCENT, conference: "#f97316", webinar: "#8b5cf6", workshop: EMERALD,
  journal_club: "#06b6d4", training: NAVY, grant_info_session: "#ec4899",
  networking: "#0ea5e9", teaching_event: "#7c3aed", symposium: "#dc2626",
};
const TYPES = Object.keys(TYPE_COLOR);

function EventCard({ event, onRegister, onUnregister, isRegistered }) {
  const color = TYPE_COLOR[event.type] || ACCENT;
  return (
    <Card padding="md">
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 4 }}>
            <span style={{ fontWeight: 700, fontSize: 14, color: NAVY }}>{event.title}</span>
            <Badge color={color} size="sm">{event.type?.replace(/_/g, " ")}</Badge>
            {event.online && <Badge variant="success" size="sm">Online</Badge>}
          </div>
          {event.description && <div style={{ fontSize: 12, color: TEXT_SECONDARY, lineHeight: 1.5, marginBottom: 8 }}>{event.description.slice(0, 100)}{event.description.length > 100 ? "…" : ""}</div>}
          <div style={{ display: "flex", gap: 14, fontSize: 12, color: TEXT_SECONDARY, flexWrap: "wrap" }}>
            {event.start_date && <span style={{ display: "flex", alignItems: "center", gap: 4 }}><Clock size={11} />{event.start_date.slice(0, 10)}</span>}
            {!event.online && event.location && <span style={{ display: "flex", alignItems: "center", gap: 4 }}><MapPin size={11} />{event.location}</span>}
            {event.capacity > 0 && <span style={{ display: "flex", alignItems: "center", gap: 4 }}><Users size={11} />{event.registration_count}/{event.capacity}</span>}
            {event.discipline && <span>{event.discipline}</span>}
          </div>
        </div>
        <div style={{ flexShrink: 0 }}>
          {isRegistered ? (
            <Button variant="outline" size="sm" onClick={() => onUnregister(event.id)} style={{ color: EMERALD, borderColor: EMERALD, background: `${EMERALD}10` }}>
              <CheckCircle size={12} />Registered
            </Button>
          ) : (
            <Button variant="primary" size="sm" onClick={() => onRegister(event.id)}>
              Register
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}

function CreateEventModal({ onClose, onCreate }) {
  const [form, setForm] = useState({ title: "", description: "", type: "seminar", discipline: "", online: true, location: "", link: "", start_date: "", end_date: "", capacity: 0, registration_required: false });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try { await axios.post("/api/network/events", { ...form, capacity: Number(form.capacity) }); onCreate(); onClose(); }
    catch { setSaving(false); }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="Create Event"
      size="md"
      footer={
        <Button variant="primary" onClick={handleSubmit} disabled={saving} loading={saving} style={{ width: "100%" }}>
          {saving ? "Creating…" : "Create Event"}
        </Button>
      }
    >
      <Input
        label="Title *"
        value={form.title}
        onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
      />
      <Input
        label="Discipline"
        value={form.discipline}
        onChange={e => setForm(f => ({ ...f, discipline: e.target.value }))}
      />
      <Textarea
        label="Description"
        value={form.description}
        onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
        rows={2}
      />
      <FormRow cols={2}>
        <FormSelect
          label="Type"
          value={form.type}
          onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
        >
          {TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </FormSelect>
        <Input
          label="Capacity (0=unlimited)"
          type="number"
          min={0}
          value={form.capacity}
          onChange={e => setForm(f => ({ ...f, capacity: e.target.value }))}
        />
      </FormRow>
      <FormRow cols={2}>
        <Input
          label="Start Date"
          type="date"
          value={form.start_date}
          onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))}
        />
        <Input
          label="End Date"
          type="date"
          value={form.end_date}
          onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))}
        />
      </FormRow>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <Checkbox
          label="Online event"
          checked={form.online}
          onChange={e => setForm(f => ({ ...f, online: e.target.checked }))}
        />
        <Checkbox
          label="Registration required"
          checked={form.registration_required}
          onChange={e => setForm(f => ({ ...f, registration_required: e.target.checked }))}
        />
      </div>
      {form.online && (
        <Input
          label="Meeting Link"
          value={form.link}
          onChange={e => setForm(f => ({ ...f, link: e.target.value }))}
          placeholder="https://..."
        />
      )}
    </Modal>
  );
}

export default function ConferenceNetworking() {
  const [events, setEvents] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [tab, setTab] = useState("upcoming");
  const [myEvents, setMyEvents] = useState({ registered: [], organized: [] });
  const [registeredIds, setRegisteredIds] = useState(new Set());

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const params = { limit: 30 };
      if (typeFilter) params.type = typeFilter;
      const r = await axios.get("/api/network/events", { params });
      setEvents(r.data.results || []);
      setTotal(r.data.total || 0);
    } catch { } finally { setLoading(false); }
  };

  const fetchMyEvents = async () => {
    try {
      const r = await axios.get("/api/network/events/mine");
      setMyEvents(r.data || { registered: [], organized: [] });
      setRegisteredIds(new Set((r.data?.registered || []).map(e => e.id)));
    } catch { }
  };

  useEffect(() => { fetchEvents(); fetchMyEvents(); }, []);

  const handleRegister = async id => { await axios.post(`/api/network/events/${id}/register`); fetchEvents(); fetchMyEvents(); };
  const handleUnregister = async id => { await axios.post(`/api/network/events/${id}/unregister`); fetchEvents(); fetchMyEvents(); };

  return (
    <DiscoveryLayout
      title="Events & Conferences"
      actions={<Button variant="primary" onClick={() => setShowCreate(true)}><Plus size={15} />Create Event</Button>}
    >

      <div style={{ marginBottom: 16 }}>
        <NavTabs
          variant="pill"
          tabs={[
            { id: "upcoming", label: "Upcoming" },
            { id: "mine", label: "My Events" },
          ]}
          active={tab}
          onChange={setTab}
        />
      </div>

      {tab === "upcoming" && (
        <>
          <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
            <FormSelect value={typeFilter} onChange={e => { setTypeFilter(e.target.value); }}>
              <option value="">All types</option>
              {TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </FormSelect>
            <Button variant="primary" onClick={fetchEvents}>Filter</Button>
          </div>
          {loading ? <LoadingOverlay text="Loading…" /> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {events.length === 0 ? (
                <EmptyState title="No upcoming events" description="Create one or check back later." />
              ) : events.map((e, i) => (
                <EventCard key={e.id || i} event={e} onRegister={handleRegister} onUnregister={handleUnregister} isRegistered={registeredIds.has(e.id)} />
              ))}
            </div>
          )}
        </>
      )}

      {tab === "mine" && (
        <div>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 10 }}>Registered ({myEvents.registered.length})</h3>
          {myEvents.registered.length === 0 ? <div style={{ color: TEXT_SECONDARY, fontSize: 13, marginBottom: 20 }}>No registrations yet.</div>
            : myEvents.registered.map((e, i) => <EventCard key={i} event={e} onRegister={() => {}} onUnregister={handleUnregister} isRegistered />)}
          <h3 style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 10, marginTop: 20 }}>Organised ({myEvents.organized.length})</h3>
          {myEvents.organized.length === 0 ? <div style={{ color: TEXT_SECONDARY, fontSize: 13 }}>No events organised yet.</div>
            : myEvents.organized.map((e, i) => (
              <Card key={i} padding="sm" style={{ marginBottom: 8 }}>
                <div style={{ fontWeight: 700, fontSize: 13, color: NAVY }}>{e.title}</div>
                <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{e.type?.replace(/_/g, " ")} · {e.registration_count} registrations · {e.start_date?.slice(0, 10)}</div>
              </Card>
            ))}
        </div>
      )}

      {showCreate && <CreateEventModal onClose={() => setShowCreate(false)} onCreate={() => { fetchEvents(); fetchMyEvents(); }} />}
    </DiscoveryLayout>
  );
}

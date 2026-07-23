import React, { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ds";
import {
  Activity, CalendarDays, Search, Plus, RefreshCw, Download,
  Star, X, ChevronDown, ChevronUp, BookOpen, GraduationCap,
  DollarSign, Users, FileCheck, ShieldCheck, Award, Eye,
  Sparkles, Clock, Trophy, CheckCircle2, Filter,
} from "lucide-react";
import { NAVY, WARM, BRD, EMERALD, ACCENT, TEXT_SECONDARY, WHITE } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";

const API = "/api/timeline";

// ── Category metadata ────────────────────────────────────────────────────────

const CATEGORY_META = {
  research:      { label: "Research",      icon: BookOpen,    color: "#0369A1" },
  teaching:      { label: "Teaching",      icon: GraduationCap, color: "#7C3AED" },
  grant:         { label: "Grants",        icon: DollarSign,  color: "#059669" },
  collaboration: { label: "Collaboration", icon: Users,       color: "#0F2847" },
  review:        { label: "Review",        icon: FileCheck,   color: "#D97706" },
  verification:  { label: "Verification",  icon: ShieldCheck, color: "#059669" },
  recognition:   { label: "Recognition",   icon: Award,       color: "#D97706" },
  community:     { label: "Community",     icon: Eye,         color: "#0369A1" },
  ai:            { label: "AI",            icon: Sparkles,    color: "#7C3AED" },
};

const HEATMAP_COLORS = ["#e2e8f0", "#bfdbfe", "#93c5fd", "#3b82f6", "#1d4ed8"];

// ── Heatmap component ────────────────────────────────────────────────────────

function HeatmapGrid({ cells }) {
  // Chunk into weeks of 7 days
  const weeks = [];
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7));
  }

  return (
    <div style={{ display: "flex", gap: 3, overflowX: "auto", paddingBottom: 4 }}>
      {weeks.map((week, wi) => (
        <div key={wi} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {week.map((cell) => (
            <div
              key={cell.date}
              title={`${cell.date}: ${cell.count} event${cell.count !== 1 ? "s" : ""}${cell.has_milestone ? " ★" : ""}`}
              style={{
                width: 13, height: 13, borderRadius: 2,
                background: cell.has_milestone && cell.count > 0
                  ? "#D97706"
                  : HEATMAP_COLORS[cell.intensity],
                cursor: cell.count > 0 ? "pointer" : "default",
                border: cell.has_milestone ? "1px solid #D97706" : "none",
                flexShrink: 0,
              }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// ── Event card ───────────────────────────────────────────────────────────────

function EventCard({ event, onDelete }) {
  const [expanded, setExpanded] = useState(false);
  const meta = CATEGORY_META[event.category] || CATEGORY_META.research;
  const Icon = meta.icon;

  return (
    <div style={{
      background: WHITE,
      border: `1px solid ${BRD}`,
      borderLeft: `4px solid ${meta.color}`,
      borderRadius: 9,
      padding: "14px 18px",
      position: "relative",
    }}>
      {event.is_milestone && (
        <Star
          size={14}
          fill="#D97706"
          color="#D97706"
          style={{ position: "absolute", top: 10, right: 36 }}
        />
      )}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: meta.color + "15",
          display: "flex", alignItems: "center", justifyContent: "center",
          flexShrink: 0,
        }}>
          <Icon size={15} color={meta.color} />
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
            <span style={{
              background: meta.color + "14", color: meta.color,
              border: `1px solid ${meta.color}28`,
              borderRadius: 5, padding: "1px 8px", fontSize: 11, fontWeight: 600,
            }}>{event.label}</span>
            {event.is_milestone && (
              <span style={{
                background: "#D97706" + "14", color: "#D97706",
                border: "1px solid #D9770628",
                borderRadius: 5, padding: "1px 8px", fontSize: 11, fontWeight: 600,
              }}>Milestone</span>
            )}
            <span style={{ fontSize: 11, color: TEXT_SECONDARY, marginLeft: "auto" }}>
              {event.occurred_at ? new Date(event.occurred_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "—"}
            </span>
          </div>

          <div style={{ fontWeight: 600, color: NAVY, fontSize: 14, marginBottom: 2 }}>
            {event.title}
          </div>

          {event.description && (
            <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 4 }}>
              {event.description}
            </div>
          )}

          {event.metadata && Object.keys(event.metadata).length > 0 && (
            <button onClick={() => setExpanded(!expanded)}
              style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 4,
                fontSize: 11, color: TEXT_SECONDARY, background: "none", border: "none",
                cursor: "pointer", padding: 0 }}>
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {expanded ? "Less" : "Details"}
            </button>
          )}
          {expanded && (
            <div style={{ marginTop: 8, padding: "8px 12px", background: WARM,
              borderRadius: 6, fontSize: 12, color: TEXT_SECONDARY }}>
              {Object.entries(event.metadata).filter(([,v]) => v).map(([k, v]) => (
                <div key={k}><strong>{k}:</strong> {String(v)}</div>
              ))}
            </div>
          )}
        </div>

        {event.source === "manual" && onDelete && (
          <Button
            size="icon"
            variant="ghost"
            onClick={() => onDelete(event._id)}
            style={{
              color: TEXT_SECONDARY,
              padding: 4,
              flexShrink: 0
            }}>
            <X size={14} />
          </Button>
        )}
      </div>
    </div>
  );
}

// ── Add event modal ──────────────────────────────────────────────────────────

function AddEventModal({ catalogue, onClose, onAdd }) {
  const [form, setForm] = useState({
    event_type: "", title: "", description: "",
    visibility: "public", occurred_at: new Date().toISOString().slice(0, 10),
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!form.event_type || !form.title) { setError("Type and title are required."); return; }
    setSaving(true);
    setError("");
    const r = await fetch(API + "/events", {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        occurred_at: form.occurred_at ? form.occurred_at + "T00:00:00Z" : undefined,
      }),
    });
    if (r.ok) {
      const ev = await r.json();
      onAdd(ev);
      onClose();
    } else {
      const err = await r.json().catch(() => ({}));
      setError(err.detail || "Failed to create event.");
    }
    setSaving(false);
  };

  const categories = [...new Set(Object.values(catalogue).map(v => v.category))];

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,.4)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 1000, padding: 16,
    }}>
      <div style={{
        background: WHITE, borderRadius: 14, width: "100%", maxWidth: 500,
        padding: 28, boxShadow: "0 20px 60px rgba(0,0,0,.2)",
        maxHeight: "90vh", overflowY: "auto",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: NAVY, margin: 0 }}>Add Timeline Event</h2>
          <Button
            size="icon"
            variant="ghost"
            onClick={onClose}
            style={{
              color: TEXT_SECONDARY
            }}>
            <X size={18} />
          </Button>
        </div>

        {error && <div style={{ color: ACCENT, fontSize: 13, marginBottom: 12 }}>{error}</div>}

        <form onSubmit={submit}>
          <div style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: NAVY, display: "block", marginBottom: 5 }}>Event Type</label>
            <select value={form.event_type} onChange={e => setForm(p => ({ ...p, event_type: e.target.value }))}
              style={{ width: "100%", padding: "9px 12px", borderRadius: 7, border: `1px solid ${BRD}`, fontSize: 13, color: NAVY }}>
              <option value="">Select…</option>
              {categories.map(cat => (
                <optgroup key={cat} label={cat.charAt(0).toUpperCase() + cat.slice(1)}>
                  {Object.entries(catalogue)
                    .filter(([, v]) => v.category === cat)
                    .map(([key, v]) => (
                      <option key={key} value={key}>{v.label}</option>
                    ))}
                </optgroup>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: NAVY, display: "block", marginBottom: 5 }}>Title</label>
            <input value={form.title} onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
              placeholder="Brief title for this event"
              style={{ width: "100%", padding: "9px 12px", borderRadius: 7, border: `1px solid ${BRD}`,
                fontSize: 13, color: NAVY, boxSizing: "border-box" }} />
          </div>

          <div style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: NAVY, display: "block", marginBottom: 5 }}>Description (optional)</label>
            <textarea value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
              rows={2} placeholder="Additional details…"
              style={{ width: "100%", padding: "9px 12px", borderRadius: 7, border: `1px solid ${BRD}`,
                fontSize: 13, color: NAVY, resize: "vertical", boxSizing: "border-box" }} />
          </div>

          <div style={{ display: "flex", gap: 12, marginBottom: 14 }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: NAVY, display: "block", marginBottom: 5 }}>Date</label>
              <input type="date" value={form.occurred_at}
                onChange={e => setForm(p => ({ ...p, occurred_at: e.target.value }))}
                style={{ width: "100%", padding: "9px 12px", borderRadius: 7, border: `1px solid ${BRD}`,
                  fontSize: 13, color: NAVY, boxSizing: "border-box" }} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: NAVY, display: "block", marginBottom: 5 }}>Visibility</label>
              <select value={form.visibility} onChange={e => setForm(p => ({ ...p, visibility: e.target.value }))}
                style={{ width: "100%", padding: "9px 12px", borderRadius: 7, border: `1px solid ${BRD}`,
                  fontSize: 13, color: NAVY }}>
                <option value="public">Public</option>
                <option value="institution">Institution only</option>
                <option value="connections">Connections only</option>
                <option value="private">Private</option>
              </select>
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button type="button" onClick={onClose}
              style={{ padding: "8px 18px", borderRadius: 7, background: WHITE, color: NAVY,
                border: `1px solid ${BRD}`, fontWeight: 600, fontSize: 13, cursor: "pointer" }}>
              Cancel
            </button>
            <button type="submit" disabled={saving}
              style={{ padding: "8px 20px", borderRadius: 7, background: NAVY, color: WHITE,
                border: "none", fontWeight: 600, fontSize: 13, cursor: "pointer",
                opacity: saving ? 0.6 : 1 }}>
              {saving ? "Saving…" : "Add Event"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function ResearchTimeline() {
  const [events, setEvents]         = useState([]);
  const [heatmap, setHeatmap]       = useState(null);
  const [stats, setStats]           = useState(null);
  const [milestones, setMilestones] = useState([]);
  const [catalogue, setCatalogue]   = useState({});
  const [insights, setInsights]     = useState([]);
  const [loading, setLoading]       = useState(true);
  const [syncing, setSyncing]       = useState(false);
  const [category, setCategory]     = useState("");
  const [search, setSearch]         = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [skip, setSkip]             = useState(0);
  const [hasMore, setHasMore]       = useState(true);
  const [showAdd, setShowAdd]       = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const LIMIT = 20;

  const loadInitial = useCallback(async () => {
    setLoading(true);
    const [evRes, hmRes, stRes, catRes, insRes] = await Promise.all([
      fetch(`${API}?limit=${LIMIT}&skip=0${category ? "&category=" + category : ""}${search ? "&search=" + encodeURIComponent(search) : ""}`, { credentials: "include" }).then(r => r.json()).catch(() => []),
      fetch(`${API}/heatmap`, { credentials: "include" }).then(r => r.json()).catch(() => null),
      fetch(`${API}/stats`, { credentials: "include" }).then(r => r.json()).catch(() => null),
      fetch(`${API}/catalogue`, { credentials: "include" }).then(r => r.json()).catch(() => ({})),
      fetch(`${API}/insights`, { credentials: "include" }).then(r => r.json()).catch(() => []),
    ]);
    setEvents(evRes || []);
    setHeatmap(hmRes);
    setStats(stRes);
    setCatalogue((catRes || {}).event_types || {});
    setInsights(insRes || []);
    setHasMore((evRes || []).length === LIMIT);
    setSkip(LIMIT);
    setLoading(false);
  }, [category, search]);

  useEffect(() => {
    loadInitial();
    // Load milestones separately
    fetch(`${API}/milestones`, { credentials: "include" })
      .then(r => r.json()).then(d => setMilestones(d || [])).catch(() => {});
  }, [loadInitial]);

  const loadMore = async () => {
    const url = `${API}?limit=${LIMIT}&skip=${skip}${category ? "&category=" + category : ""}${search ? "&search=" + encodeURIComponent(search) : ""}`;
    const more = await fetch(url, { credentials: "include" }).then(r => r.json()).catch(() => []);
    setEvents(prev => [...prev, ...(more || [])]);
    setHasMore((more || []).length === LIMIT);
    setSkip(s => s + LIMIT);
  };

  const sync = async () => {
    setSyncing(true);
    await fetch(API + "/sync", { method: "POST", credentials: "include" });
    setSyncing(false);
    loadInitial();
  };

  const handleDelete = async (id) => {
    await fetch(`${API}/events/${id}`, { method: "DELETE", credentials: "include" });
    setEvents(prev => prev.filter(e => e._id !== id));
  };

  const handleAddEvent = (ev) => {
    setEvents(prev => [ev, ...prev]);
    setStats(s => s ? { ...s, total_events: (s.total_events || 0) + 1 } : s);
  };

  // Group events by year
  const grouped = {};
  for (const ev of events) {
    const year = ev.occurred_at ? new Date(ev.occurred_at).getFullYear() : "Unknown";
    if (!grouped[year]) grouped[year] = [];
    grouped[year].push(ev);
  }
  const years = Object.keys(grouped).sort((a, b) => b - a);

  const TABS = [
    { key: "", label: "All" },
    { key: "research", label: "Research" },
    { key: "teaching", label: "Teaching" },
    { key: "grant", label: "Grants" },
    { key: "collaboration", label: "Collaboration" },
    { key: "review", label: "Review" },
    { key: "verification", label: "Verification" },
    { key: "recognition", label: "Recognition" },
    { key: "ai", label: "AI" },
  ];

  if (loading) {
    return (
      <ResearchLayout
        title="Research Timeline"
        subtitle="Your complete academic activity record"
        icon={<Activity size={18} />}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 80, color: TEXT_SECONDARY }}>
          Loading timeline…
        </div>
      </ResearchLayout>
    );
  }

  const actions = (
    <div style={{ display: "flex", gap: 8 }}>
      <button onClick={sync} disabled={syncing}
        style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px",
          borderRadius: 7, background: WHITE, border: `1px solid ${BRD}`,
          color: NAVY, fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
        <RefreshCw size={13} style={{ animation: syncing ? "spin 1s linear infinite" : "none" }} />
        {syncing ? "Syncing…" : "Sync"}
      </button>
      <a href={`${API}/export/csv`}
        style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px",
          borderRadius: 7, background: WHITE, border: `1px solid ${BRD}`,
          color: NAVY, fontSize: 12, fontWeight: 600, textDecoration: "none" }}>
        <Download size={13} /> Export
      </a>
      <button onClick={() => setShowAdd(true)}
        style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 16px",
          borderRadius: 7, background: NAVY, color: WHITE,
          border: "none", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
        <Plus size={13} /> Add Event
      </button>
    </div>
  );

  return (
    <ResearchLayout
      title="Research Timeline"
      subtitle="Your complete academic activity record"
      icon={<Activity size={18} />}
      actions={actions}
    >
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>

        {/* Stats row */}
        {stats && (
          <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
            {[
              { label: "Total Events", value: stats.total_events || 0, icon: Activity, color: NAVY },
              { label: "Milestones",   value: stats.milestone_count || 0, icon: Trophy, color: "#D97706" },
              { label: "Active Days",  value: heatmap?.active_days || 0, icon: CalendarDays, color: "#0369A1" },
              { label: "Day Streak",   value: heatmap?.current_streak || 0, icon: Clock, color: EMERALD },
            ].map(s => {
              const Icon = s.icon;
              return (
                <div key={s.label} style={{
                  flex: "1 1 120px", background: WHITE, border: `1px solid ${BRD}`,
                  borderRadius: 10, padding: "14px 18px", display: "flex", alignItems: "center", gap: 12,
                }}>
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: s.color + "12",
                    display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Icon size={16} color={s.color} />
                  </div>
                  <div>
                    <div style={{ fontSize: 20, fontWeight: 700, color: NAVY }}>{s.value}</div>
                    <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>{s.label}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Activity Heatmap */}
        {heatmap && heatmap.cells && (
          <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12,
            padding: 20, marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: NAVY }}>
                Activity Heatmap — {heatmap.total_events} events in {heatmap.period_days} days
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: TEXT_SECONDARY }}>
                Less
                {HEATMAP_COLORS.map((c, i) => (
                  <div key={i} style={{ width: 11, height: 11, borderRadius: 2, background: c }} />
                ))}
                More
              </div>
            </div>
            <HeatmapGrid cells={heatmap.cells} />
            <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 8 }}>
              ★ = milestone day &nbsp;·&nbsp; Hover cells for details
            </div>
          </div>
        )}

        {/* AI Insights */}
        {insights.length > 0 && (
          <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12,
            padding: 20, marginBottom: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 12 }}>
              Timeline Insights
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {insights.slice(0, 3).map(ins => (
                <div key={ins.key} style={{
                  display: "flex", gap: 12, padding: "10px 14px",
                  borderRadius: 8, border: `1px solid ${BRD}`,
                  background: ins.type === "positive" ? EMERALD + "06"
                    : ins.type === "warning" ? "#D97706" + "06" : WARM,
                }}>
                  <CheckCircle2 size={15} color={
                    ins.type === "positive" ? EMERALD
                      : ins.type === "warning" ? "#D97706" : TEXT_SECONDARY
                  } style={{ flexShrink: 0, marginTop: 1 }} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: NAVY }}>{ins.title}</div>
                    <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 2 }}>{ins.body}</div>
                    <div style={{ fontSize: 11, color: "#0369A1", marginTop: 4, fontWeight: 500 }}>
                      → {ins.action}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Category tabs + search */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
            {TABS.map(t => (
              <button key={t.key} onClick={() => { setCategory(t.key); setSkip(0); }}
                style={{
                  padding: "6px 14px", borderRadius: 20, fontSize: 12, fontWeight: 600,
                  border: `1px solid ${category === t.key ? NAVY : BRD}`,
                  background: category === t.key ? NAVY : WHITE,
                  color: category === t.key ? WHITE : NAVY,
                  cursor: "pointer",
                }}>
                {t.label}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <div style={{ flex: 1, position: "relative" }}>
              <Search size={14} color={TEXT_SECONDARY}
                style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)" }} />
              <input
                value={searchInput}
                onChange={e => setSearchInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") { setSearch(searchInput); setSkip(0); } }}
                placeholder="Search events… (Enter to search)"
                style={{
                  width: "100%", padding: "9px 12px 9px 36px", borderRadius: 8,
                  border: `1px solid ${BRD}`, fontSize: 13, color: NAVY,
                  background: WHITE, boxSizing: "border-box",
                }}
              />
            </div>
            <button onClick={() => setShowFilters(!showFilters)}
              style={{ padding: "8px 14px", borderRadius: 8, background: showFilters ? NAVY : WHITE,
                border: `1px solid ${BRD}`, color: showFilters ? WHITE : NAVY,
                fontSize: 12, fontWeight: 600, cursor: "pointer",
                display: "flex", alignItems: "center", gap: 6 }}>
              <Filter size={13} /> Filter
            </button>
            {(category || search) && (
              <button onClick={() => { setCategory(""); setSearch(""); setSearchInput(""); setSkip(0); }}
                style={{ padding: "8px 12px", borderRadius: 8, background: WHITE,
                  border: `1px solid ${BRD}`, color: ACCENT,
                  fontSize: 12, fontWeight: 600, cursor: "pointer",
                  display: "flex", alignItems: "center", gap: 4 }}>
                <X size={12} /> Clear
              </button>
            )}
          </div>
        </div>

        {/* Milestones row (pinned, collapsible) */}
        {milestones.length > 0 && (
          <div style={{ background: "#D97706" + "08", border: `1px solid #D9770628`,
            borderRadius: 10, padding: "14px 18px", marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <Trophy size={14} color="#D97706" />
              <span style={{ fontSize: 13, fontWeight: 600, color: "#D97706" }}>
                Career Milestones ({milestones.length})
              </span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {milestones.map(m => (
                <span key={m.milestone_key} style={{
                  background: WHITE, border: "1px solid #D9770628",
                  borderRadius: 6, padding: "4px 12px", fontSize: 12, fontWeight: 600, color: "#92400E",
                }}>★ {m.label}</span>
              ))}
            </div>
          </div>
        )}

        {/* Timeline entries */}
        {events.length === 0 ? (
          <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12,
            padding: 60, textAlign: "center" }}>
            <Activity size={36} color={BRD} style={{ margin: "0 auto 16px", display: "block" }} />
            <p style={{ color: NAVY, fontWeight: 600, margin: "0 0 6px" }}>No events yet</p>
            <p style={{ color: TEXT_SECONDARY, fontSize: 13, margin: "0 0 20px" }}>
              Click Sync to import your existing academic activity, or add events manually.
            </p>
            <button onClick={sync}
              style={{ padding: "10px 24px", borderRadius: 8, background: NAVY, color: WHITE,
                border: "none", fontWeight: 600, fontSize: 13, cursor: "pointer" }}>
              Import Activity
            </button>
          </div>
        ) : (
          <>
            {years.map(year => (
              <div key={year} style={{ marginBottom: 28 }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 12, marginBottom: 14,
                }}>
                  <span style={{ fontSize: 14, fontWeight: 700, color: NAVY }}>{year}</span>
                  <div style={{ flex: 1, height: 1, background: BRD }} />
                  <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>
                    {grouped[year].length} event{grouped[year].length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {grouped[year].map(ev => (
                    <EventCard key={ev._id} event={ev} onDelete={handleDelete} />
                  ))}
                </div>
              </div>
            ))}

            {hasMore && (
              <div style={{ textAlign: "center", marginTop: 8 }}>
                <button onClick={loadMore}
                  style={{ padding: "10px 28px", borderRadius: 8, background: WHITE,
                    border: `1px solid ${BRD}`, color: NAVY, fontWeight: 600,
                    fontSize: 13, cursor: "pointer" }}>
                  Load More
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {showAdd && (
        <AddEventModal
          catalogue={catalogue}
          onClose={() => setShowAdd(false)}
          onAdd={handleAddEvent}
        />
      )}
    </ResearchLayout>
  );
}

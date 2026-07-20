/* eslint-disable */
import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { DiscoveryLayout } from "@/layouts";
import api from "../lib/api";
import { Avatar } from "@/components/ds/Avatar";
import EmptyState from "@/components/ds/EmptyState";
import { SkeletonCard, Spinner } from "@/components/ds/LoadingState";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import { NAVY, WARM, ACCENT } from "@/lib/tokens";
import {
  Radio, BookOpen, Users, Award, CalendarDays,
  GraduationCap, TrendingUp, Microscope, Milestone,
  Building2, ArrowRight, Bell, Filter, RefreshCw,
  FileText, Handshake, Star, MessageSquare, Activity,
  Sparkles, Clock,
} from "lucide-react";

const BORDER = "#E4E8EF";

const FEED_TYPES = [
  { value: "",            label: "All Activity",     icon: Radio },
  { value: "publication", label: "Publications",      icon: BookOpen },
  { value: "team",        label: "Teams",             icon: Users },
  { value: "collaboration", label: "Collaborations",  icon: Handshake },
  { value: "grant",       label: "Grants",            icon: Award },
  { value: "conference",  label: "Conferences",       icon: CalendarDays },
  { value: "teaching",    label: "Teaching",          icon: GraduationCap },
  { value: "milestone",   label: "Milestones",        icon: Milestone },
  { value: "institution", label: "Institution",       icon: Building2 },
];

const TYPE_META = {
  publication:   { color: "#7C3AED", icon: BookOpen,       label: "Published",         verb: "published" },
  team:          { color: "#0891B2", icon: Users,           label: "New Team",          verb: "created a team" },
  collaboration: { color: "#059669", icon: Handshake,       label: "Collaboration",     verb: "opened a collaboration" },
  grant:         { color: "#D97706", icon: Award,           label: "Grant",             verb: "received a grant" },
  conference:    { color: "#2563EB", icon: CalendarDays,    label: "Conference",        verb: "accepted at a conference" },
  teaching:      { color: "#8B5CF6", icon: GraduationCap,  label: "Teaching",          verb: "updated teaching" },
  milestone:     { color: "#F59E0B", icon: Star,            label: "Milestone",         verb: "reached a milestone" },
  institution:   { color: "#374151", icon: Building2,       label: "Institution",       verb: "announced" },
  profile_update:{ color: "#64748B", icon: Activity,        label: "Profile Update",    verb: "updated their profile" },
  connection:    { color: "#06B6D4", icon: MessageSquare,   label: "Connection",        verb: "connected with" },
  default:       { color: "#94A3B8", icon: Activity,        label: "Activity",          verb: "posted" },
};

function getMeta(type) {
  return TYPE_META[type] || TYPE_META.default;
}

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1)  return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7)  return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function FeedItem({ item }) {
  const [hovered, setHovered] = useState(false);
  const meta = getMeta(item.type || item.activity_type);
  const Icon = meta.icon;
  const actor = item.actor || item.user || {};
  const actorName = actor.full_name || actor.name || "Researcher";

  return (
    <div
      style={{ display: "flex", gap: 14, padding: "18px 20px", background: hovered ? WARM : "white", border: `1px solid ${hovered ? NAVY + "30" : BORDER}`, marginBottom: 8, transition: "all 0.12s", cursor: "default" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Activity type indicator */}
      <div style={{ width: 34, height: 34, background: meta.color + "14", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, border: `1px solid ${meta.color}25`, marginTop: 2 }}>
        <Icon size={15} strokeWidth={1.5} style={{ color: meta.color }} />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8, justifyContent: "space-between", marginBottom: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", flex: 1, minWidth: 0 }}>
            <Link to={actor.id ? `/profile/${actor.id}` : "#"} style={{ display: "flex", alignItems: "center", gap: 7, textDecoration: "none" }}>
              <Avatar url={actor.avatar_url} name={actorName} size={24} />
              <span style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>{actorName}</span>
            </Link>
            <span style={{ fontSize: 12, color: "#64748B" }}>{item.content || meta.verb}</span>
            <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: meta.color, background: meta.color + "12", border: `1px solid ${meta.color}28`, padding: "1px 7px" }}>
              {meta.label}
            </span>
          </div>
          <span style={{ fontSize: 11, color: "#94A3B8", flexShrink: 0, display: "flex", alignItems: "center", gap: 3 }}>
            <Clock size={10} strokeWidth={1.5} />
            {timeAgo(item.created_at || item.timestamp)}
          </span>
        </div>

        {/* Title / body */}
        {(item.title || item.description) && (
          <div style={{ background: "white", border: `1px solid ${BORDER}`, padding: "12px 14px", marginTop: 8 }}>
            {item.title && (
              <div style={{ fontSize: 13, fontWeight: 600, color: "#0f172a", marginBottom: item.description ? 4 : 0 }}>{item.title}</div>
            )}
            {item.description && (
              <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.6, display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                {item.description}
              </div>
            )}
          </div>
        )}

        {/* Tags */}
        {item.tags?.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 8 }}>
            {item.tags.map((tag) => (
              <span key={tag} style={{ fontSize: 10, padding: "2px 7px", background: WARM, border: `1px solid ${BORDER}`, color: "#64748B", fontFamily: "monospace" }}>{tag}</span>
            ))}
          </div>
        )}

        {/* Institution / venue */}
        {(item.institution || item.venue) && (
          <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 8, fontSize: 11, color: "#94A3B8" }}>
            <Building2 size={10} strokeWidth={1.5} />
            {item.institution || item.venue}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Synthetic feed when the API returns no data ──────────────────────────────
function WelcomeFeedItem({ user }) {
  const meta = getMeta("milestone");
  const Icon = meta.icon;
  return (
    <div style={{ display: "flex", gap: 14, padding: "18px 20px", background: "white", border: `1px solid ${BORDER}`, marginBottom: 8 }}>
      <div style={{ width: 34, height: 34, background: meta.color + "14", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, border: `1px solid ${meta.color}25`, marginTop: 2 }}>
        <Icon size={15} strokeWidth={1.5} style={{ color: meta.color }} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", marginBottom: 4 }}>Welcome to the Academic Network</div>
        <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.6 }}>
          The Research Feed will show academic updates from researchers you follow: new publications, collaboration requests, grant wins, conference acceptances and research milestones. Start building your network to see their activity here.
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
          <Link to="/network" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", padding: "8px 16px", fontSize: 12, fontWeight: 600, textDecoration: "none" }}>
            <Users size={12} strokeWidth={2} /> Find Researchers
          </Link>
          <Link to="/network/collaborations" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "white", color: NAVY, border: `1px solid ${NAVY}40`, padding: "8px 14px", fontSize: 12, fontWeight: 600, textDecoration: "none" }}>
            <Handshake size={12} strokeWidth={1.5} /> Open Collaborations
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ResearchFeed() {
  const { user } = useAuth();

  const [items, setItems]         = useState([]);
  const [loading, setLoading]     = useState(true);
  const [typeFilter, setTypeFilter] = useState("");
  const [cursor, setCursor]       = useState(null);
  const [hasMore, setHasMore]     = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const loadFeed = useCallback(async (reset = true) => {
    if (reset) setLoading(true); else setRefreshing(true);
    try {
      const params = { limit: 30 };
      if (typeFilter)               params.type = typeFilter;
      if (!reset && cursor)         params.cursor = cursor;
      const { data } = await api.get("/network/activity", { params });
      const newItems = Array.isArray(data) ? data : (data.items || data.feed || []);
      setItems((prev) => reset ? newItems : [...prev, ...newItems]);
      const nc = Array.isArray(data) ? null : (data.next_cursor || null);
      setCursor(nc);
      setHasMore(!!nc);
    } catch {
      // Activity feed unavailable — show empty state (not an error)
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [typeFilter, cursor]);

  useEffect(() => { loadFeed(true); }, [typeFilter]); // eslint-disable-line

  const filtered = typeFilter ? items.filter((i) => (i.type || i.activity_type) === typeFilter) : items;

  return (
    <DiscoveryLayout>
    <div>

      {/* ── HEADER ─────────────────────────────────────────────────────────── */}
      <div style={{ background: NAVY, margin: "-24px -24px 0", padding: "36px 28px 28px" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600, marginBottom: 8 }}>
              ACADEMIC NETWORK
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 700, color: "white", margin: "0 0 6px", letterSpacing: "-0.03em" }}>Research Feed</h1>
            <p style={{ fontSize: 13, color: "rgba(255,255,255,0.45)", margin: 0, maxWidth: 460 }}>
              Academic updates, publications, grants, collaborations and milestones from your network.
            </p>
          </div>
          <button
            onClick={() => loadFeed(true)}
            disabled={loading || refreshing}
            style={{ display: "inline-flex", alignItems: "center", gap: 8, border: "1px solid rgba(255,255,255,0.2)", color: "rgba(255,255,255,0.7)", padding: "8px 16px", fontSize: 12, background: "transparent", cursor: "pointer", opacity: (loading || refreshing) ? 0.6 : 1 }}
          >
            <RefreshCw size={12} strokeWidth={1.5} style={{ animation: refreshing ? "spin 1s linear infinite" : "none" }} />
            Refresh
          </button>
        </div>
      </div>

      {/* ── TYPE FILTER ─────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "16px 0 20px", borderBottom: `1px solid ${BORDER}`, marginBottom: 20 }}>
        {FEED_TYPES.map((t) => {
          const active = typeFilter === t.value;
          const Icon = t.icon;
          return (
            <button
              key={t.value}
              onClick={() => setTypeFilter(t.value === typeFilter ? "" : t.value)}
              style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, padding: "5px 12px", border: `1px solid ${active ? NAVY : BORDER}`, background: active ? NAVY : "white", color: active ? "white" : "#64748B", cursor: "pointer", fontWeight: active ? 600 : 400, transition: "all 0.12s" }}
            >
              <Icon size={10} strokeWidth={1.5} />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* ── FEED CONTENT ────────────────────────────────────────────────────── */}
      <div style={{ maxWidth: 720 }}>
        {loading && (
          <div>
            {[1,2,3,4].map((i) => (
              <div key={i} style={{ background: "white", border: `1px solid ${BORDER}`, padding: "18px 20px", marginBottom: 8 }}>
                <div style={{ display: "flex", gap: 14 }}>
                  <div style={{ width: 34, height: 34, background: WARM, flexShrink: 0 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ height: 14, background: WARM, marginBottom: 8, width: "60%" }} />
                    <div style={{ height: 12, background: WARM, width: "90%" }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <>
            <WelcomeFeedItem user={user} />
            <div style={{ marginTop: 20 }}>
              <EmptyState
                icon={<Radio />}
                title="No activity yet"
                description="Connect with researchers to see their publications, grants, collaborations and milestones in your feed."
                action={
                  <Link to="/network" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", padding: "9px 20px", fontSize: 13, fontWeight: 600, textDecoration: "none" }}>
                    <Users size={13} strokeWidth={2} />Discover Researchers
                  </Link>
                }
                size="md"
                dashed
              />
            </div>
          </>
        )}

        {!loading && filtered.length > 0 && (
          <div>
            {filtered.map((item, i) => (
              <FeedItem key={item._id || item.id || i} item={item} />
            ))}

            {hasMore && (
              <div style={{ display: "flex", justifyContent: "center", marginTop: 20 }}>
                <button
                  onClick={() => loadFeed(false)}
                  disabled={refreshing}
                  style={{ fontSize: 13, color: NAVY, border: `1px solid ${NAVY}40`, padding: "10px 28px", background: "white", cursor: "pointer", opacity: refreshing ? 0.6 : 1 }}
                >
                  {refreshing ? "Loading…" : "Load more"}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>

    </div>
    </DiscoveryLayout>
  );
}

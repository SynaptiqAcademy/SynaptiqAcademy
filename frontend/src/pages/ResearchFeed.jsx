/* eslint-disable */
import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { ResearchLayout } from "@/layouts";
import api from "../lib/api";
import EmptyState from "@/components/ds/EmptyState";
import { SkeletonCard, Spinner } from "@/components/ds/LoadingState";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Tag } from "@/components/ds/Tag";
import { ActivityFeedItem } from "@/components/ds/ActivityFeed";
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
  const meta = getMeta(item.type || item.activity_type);
  const actor = item.actor || item.user || {};
  const actorName = actor.full_name || actor.name || "Researcher";

  return (
    <div style={{ marginBottom: 8 }}>
      <ActivityFeedItem
        icon={<meta.icon />}
        color={meta.color}
        actor={{ name: actorName, avatarUrl: actor.avatar_url, to: actor.id ? `/profile/${actor.id}` : "#" }}
        verb={item.content || meta.verb}
        typeLabel={meta.label}
        title={item.title}
        description={item.description}
        tags={item.tags}
        meta={item.institution || item.venue ? (
          <><Building2 size={10} strokeWidth={1.5} />{item.institution || item.venue}</>
        ) : undefined}
        timestamp={timeAgo(item.created_at || item.timestamp)}
      />
    </div>
  );
}

// ─── Synthetic feed when the API returns no data ──────────────────────────────
function WelcomeFeedItem({ user }) {
  const meta = getMeta("milestone");
  const Icon = meta.icon;
  return (
    <Card padding="lg" style={{ display: "flex", gap: 14, marginBottom: 8 }}>
      <div style={{ width: 34, height: 34, background: meta.color + "14", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, border: `1px solid ${meta.color}25`, marginTop: 2 }}>
        <Icon size={15} strokeWidth={1.5} style={{ color: meta.color }} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", marginBottom: 4 }}>Welcome to the Academic Network</div>
        <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.6 }}>
          The Research Feed will show academic updates from researchers you follow: new publications, collaboration requests, grant wins, conference acceptances and research milestones. Start building your network to see their activity here.
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
          <Button as={Link} to="/network" variant="primary" size="sm">
            <Users size={12} strokeWidth={2} /> Find Researchers
          </Button>
          <Button as={Link} to="/network/collaborations" variant="outline" size="sm">
            <Handshake size={12} strokeWidth={1.5} /> Open Collaborations
          </Button>
        </div>
      </div>
    </Card>
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
    <ResearchLayout
      title="Research Feed"
      subtitle="Academic updates, publications, grants, collaborations and milestones from your network."
      actions={
        <Button
          variant="ghost"
          size="sm"
          onClick={() => loadFeed(true)}
          disabled={loading || refreshing}
        >
          <RefreshCw size={12} strokeWidth={1.5} style={{ animation: refreshing ? "spin 1s linear infinite" : "none" }} />
          Refresh
        </Button>
      }
    >
    <div>

      {/* ── TYPE FILTER ─────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "16px 0 20px", borderBottom: `1px solid ${BORDER}`, marginBottom: 20 }}>
        {FEED_TYPES.map((t) => {
          const active = typeFilter === t.value;
          const Icon = t.icon;
          return (
            <Tag
              key={t.value}
              variant={active ? "active" : "default"}
              onClick={() => setTypeFilter(t.value === typeFilter ? "" : t.value)}
              style={active ? { background: NAVY, borderColor: NAVY, color: "white" } : undefined}
            >
              <Icon size={10} strokeWidth={1.5} />
              {t.label}
            </Tag>
          );
        })}
      </div>

      {/* ── FEED CONTENT ────────────────────────────────────────────────────── */}
      <div style={{ maxWidth: 720 }}>
        {loading && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[1,2,3,4].map((i) => (
              <SkeletonCard key={i} rows={2} />
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
                  <Button as={Link} to="/network" variant="primary">
                    <Users size={13} strokeWidth={2} />Discover Researchers
                  </Button>
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
                <Button
                  variant="outline"
                  onClick={() => loadFeed(false)}
                  disabled={refreshing}
                  loading={refreshing}
                >
                  {refreshing ? "Loading…" : "Load more"}
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>

    </div>
    </ResearchLayout>
  );
}

/* eslint-disable */
import React, { useState, useMemo, memo } from "react";
import { Link } from "react-router-dom";
import { FileText, FolderOpen, Clock, ArrowUpRight } from "lucide-react";
import { EmptyState } from "@/components/ds";
import {
  WHITE, BRD,
  TEXT_PRIMARY, TEXT_MUTED,
  NAVY, NAVY_06, NAVY_LIGHT, NAVY2,
  SHADOW_CARD, SHADOW_CARD_HOVER,
  EMERALD, AMBER, SUCCESS_TEXT,
  RADIUS_XL,
  TYPE,
} from "@/lib/tokens";
import { transition, transform } from "@/lib/motion";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtRelative(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d)) return null;
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1)  return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "yesterday";
  if (days < 30)  return `${days}d ago`;
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function statusColor(s = "") {
  const l = s.toLowerCase();
  if (l.includes("review") || l.includes("submit")) return "#3B82F6";
  if (l.includes("draft") || l.includes("pending")) return AMBER;
  if (l.includes("active") || l.includes("complete")) return EMERALD;
  return TEXT_MUTED;
}

// Deterministic cover gradient — same item always gets the same treatment.
// Two stops per pair; the first three use exact design-token colors, the
// remaining accent stops (#3B2352, #7C2D12, #1E3A8A) are deliberate cover
// variety with no equivalent in the core palette — not a DS violation, just
// decorative range, same as an avatar-color set.
const COVERS_MANUSCRIPT = [`${NAVY},${NAVY_LIGHT}`, `${NAVY},#3B2352`, `${NAVY},${NAVY2}`];
const COVERS_WORKSPACE   = [`${SUCCESS_TEXT},${NAVY}`, `#7C2D12,${NAVY}`, `#1E3A8A,${NAVY}`];

function coverFor(item, i) {
  const set = item.type === "Manuscript" ? COVERS_MANUSCRIPT : COVERS_WORKSPACE;
  return set[i % set.length];
}

// ── WorkTile — the "continue" rail card ────────────────────────────────────────

const WorkTile = memo(function WorkTile({ item, i }) {
  const [hov, setHov] = useState(false);
  const Icon = item.type === "Manuscript" ? FileText : FolderOpen;
  const dotColor = statusColor(item.status);
  const [c1, c2] = coverFor(item, i).split(",");

  return (
    <Link
      to={item.to}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        textDecoration: "none",
        display: "block",
        flex: "0 0 auto",
        width: 260,
        scrollSnapAlign: "start",
      }}
    >
      <div
        style={{
          borderRadius: RADIUS_XL,
          overflow: "hidden",
          background: WHITE,
          border: `1px solid ${hov ? "rgba(15,40,71,0.16)" : BRD}`,
          boxShadow: hov ? SHADOW_CARD_HOVER : SHADOW_CARD,
          transform: hov ? transform.liftSm : transform.none,
          transition: transition.hoverCard,
        }}
      >
        {/* Cover band */}
        <div
          style={{
            height: 84,
            background: `linear-gradient(135deg, ${c1}, ${c2})`,
            position: "relative",
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            padding: "12px 14px",
          }}
        >
          <Icon size={16} strokeWidth={1.75} style={{ color: "rgba(255,255,255,0.85)" }} />
          <ArrowUpRight
            size={15}
            style={{
              color: "rgba(255,255,255,0.85)",
              opacity: hov ? 1 : 0,
              transform: hov ? "translate(0,0)" : "translate(-3px,3px)",
              transition: "opacity 150ms ease, transform 150ms ease",
            }}
          />
        </div>

        {/* Body */}
        <div style={{ padding: "13px 14px 12px" }}>
          <p
            style={{
              ...TYPE.h4,
              margin: "0 0 6px",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              color: hov ? NAVY : TEXT_PRIMARY,
              transition: transition.colorFast,
            }}
          >
            {item.title}
          </p>

          <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: item.progress != null ? 8 : 0 }}>
            <span style={{ width: 5, height: 5, borderRadius: "50%", background: dotColor, flexShrink: 0 }} aria-hidden="true" />
            <span style={{ ...TYPE.caption }}>{item.status}</span>
            <span style={{ color: BRD }}>·</span>
            <Clock size={9} style={{ color: TEXT_MUTED }} />
            <span style={{ ...TYPE.caption }}>{item.lastEdited ? fmtRelative(item.lastEdited) : "no edits"}</span>
          </div>

          {item.progress != null && (
            <div style={{ background: NAVY_06, borderRadius: 99, height: 3 }}>
              <div
                style={{
                  width: `${Math.min(100, item.progress)}%`,
                  height: "100%",
                  background: NAVY,
                  borderRadius: 99,
                }}
              />
            </div>
          )}
        </div>
      </div>
    </Link>
  );
});

// ── Segmented tab control ────────────────────────────────────────────────────

function TabBtn({ label, count, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "inline-flex", alignItems: "center", gap: 5,
        padding: "6px 13px", borderRadius: 99,
        fontSize: "0.8rem", fontWeight: active ? 600 : 500,
        color: active ? WHITE : TEXT_MUTED,
        background: active ? NAVY : "transparent",
        border: "none", cursor: "pointer",
        transition: transition.all,
      }}
    >
      {label}
      {count != null && count > 0 && (
        <span
          style={{
            fontSize: "0.62rem", fontWeight: 700,
            color: active ? "rgba(255,255,255,0.7)" : TEXT_MUTED,
            background: active ? "rgba(255,255,255,0.16)" : NAVY_06,
            borderRadius: 99, padding: "1px 5px",
          }}
        >
          {count}
        </span>
      )}
    </button>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

const TABS = ["Recent", "Workspaces", "Documents", "Pinned"];

export default function MyWork({ manuscripts, workspaces }) {
  const [activeTab, setActiveTab] = useState("Recent");

  const allItems = useMemo(() => [
    ...manuscripts.map(m => ({
      id:          m.id,
      type:        "Manuscript",
      title:       m.title || "Untitled manuscript",
      status:      m.status || "Draft",
      lastEdited:  m.updated_at,
      progress:    m.progress ?? null,
      pinned:      m.pinned || false,
      memberCount: m.collaborators_count || m.members?.length || 0,
      to:          m.id ? `/manuscripts/${m.id}` : "/manuscripts",
    })),
    ...workspaces.map(w => ({
      id:          w.id,
      type:        "Workspace",
      title:       w.name || "Workspace",
      status:      w.status === "active" ? "Active" : (w.status || "Active"),
      lastEdited:  w.updated_at,
      progress:    w.progress ?? null,
      pinned:      w.pinned || false,
      memberCount: w.member_count || w.members?.length || 0,
      to:          w.id ? `/workspaces/${w.id}` : "/workspaces",
    })),
  ].sort((a, b) => (b.lastEdited || "") > (a.lastEdited || "") ? 1 : -1), [manuscripts, workspaces]);

  const counts = useMemo(() => ({
    Recent:     Math.min(allItems.length, 8),
    Workspaces: allItems.filter(i => i.type === "Workspace").length,
    Documents:  allItems.filter(i => i.type === "Manuscript").length,
    Pinned:     allItems.filter(i => i.pinned).length,
  }), [allItems]);

  const displayed = useMemo(() => {
    if (activeTab === "Workspaces") return allItems.filter(i => i.type === "Workspace").slice(0, 8);
    if (activeTab === "Documents")  return allItems.filter(i => i.type === "Manuscript").slice(0, 8);
    if (activeTab === "Pinned")     return allItems.filter(i => i.pinned).slice(0, 8);
    return allItems.slice(0, 8);
  }, [activeTab, allItems]);

  return (
    <section aria-label="My Work">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3 mb-5">
        <h2
          style={{
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: "1.35rem",
            fontWeight: 700,
            letterSpacing: "-0.02em",
            color: TEXT_PRIMARY,
            margin: 0,
          }}
        >
          Continue where you left off
        </h2>
        <div className="flex gap-1 flex-wrap">
          {TABS.map(t => (
            <TabBtn
              key={t}
              label={t}
              count={counts[t]}
              active={activeTab === t}
              onClick={() => setActiveTab(t)}
            />
          ))}
        </div>
      </div>

      {/* Rail or empty state */}
      {displayed.length === 0 ? (
        <EmptyState
          icon={<FolderOpen />}
          title={activeTab === "Pinned" ? "Nothing pinned yet" : "No items here"}
          description={
            activeTab === "Pinned"
              ? "Pin manuscripts or workspaces to surface them here."
              : "Start by creating a manuscript or opening a workspace."
          }
        />
      ) : (
        <div
          className="flex gap-4 overflow-x-auto pb-2 -mx-1 px-1"
          style={{ scrollSnapType: "x proximity" }}
        >
          {displayed.map((item, i) => (
            <WorkTile key={item.id || i} item={item} i={i} />
          ))}
        </div>
      )}
    </section>
  );
}

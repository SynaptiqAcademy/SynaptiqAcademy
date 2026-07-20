/* eslint-disable */
import React from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight, Clock, Users, TrendingUp, FileText, FolderOpen,
  BookOpen, Coins, Calendar, User, Award, ExternalLink,
  ChevronRight, Sparkles,
} from "lucide-react";
import {
  NAVY, ACCENT, EMERALD, AMBER, CRIMSON,
  BRD, BRDX, WHITE, WARM,
  RADIUS_XS, RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_FULL,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
  TYPE, FONT_SERIF,
  NAVY_06, NAVY_12,
} from "@/lib/tokens";
import { transition, transform } from "@/lib/motion";
import { Card } from "./Card";
import { Avatar } from "./Avatar";
import { AvatarGroup } from "./AvatarGroup";
import { Badge } from "./Badge";
import { ProgressBar } from "./Progress";

// ── Status helpers ────────────────────────────────────────────────────────────

const STATUS_COLOR = {
  active:     EMERALD,
  published:  EMERALD,
  verified:   EMERALD,
  draft:      AMBER,
  pending:    AMBER,
  review:     "#3B82F6",
  paused:     TEXT_MUTED,
  closed:     TEXT_MUTED,
  archived:   TEXT_MUTED,
  open:       NAVY,
};

function getStatusColor(status) {
  const s = (status || "").toLowerCase();
  for (const [key, color] of Object.entries(STATUS_COLOR)) {
    if (s.includes(key)) return color;
  }
  return TEXT_MUTED;
}

export function StatusDot({ status, color, size = 5 }) {
  return (
    <span
      style={{
        display: "inline-block",
        width:  size,
        height: size,
        borderRadius: "50%",
        background:   color || getStatusColor(status),
        flexShrink:   0,
      }}
      aria-hidden="true"
    />
  );
}

function CardRow({ style, children }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, ...style }}>
      {children}
    </div>
  );
}

function MetaText({ children, style }) {
  return (
    <span style={{ ...TYPE.caption, color: TEXT_MUTED, ...style }}>
      {children}
    </span>
  );
}

function fmtRelative(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d)) return null;
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "yesterday";
  if (days < 30) return `${days}d ago`;
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

// ═══════════════════════════════════════════════════════════════════════════════
// WorkspaceCard — Manuscript / Research Project / Workspace
// ═══════════════════════════════════════════════════════════════════════════════

export function WorkspaceCard({
  title,
  type = "Workspace",
  status,
  progress,
  lastEdited,
  team = [],
  tags = [],
  to,
  onResume,
  compact = false,
}) {
  const navigate = useNavigate();
  const Icon = type?.toLowerCase().includes("manuscript") ? FileText : FolderOpen;
  const statusColor = getStatusColor(status);

  if (compact) {
    return (
      <Card
        padding="none"
        onClick={to ? () => navigate(to) : onResume}
        style={{ overflow: "hidden" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "11px 14px" }}>
          <div style={{
            width: 32, height: 32, borderRadius: RADIUS_MD, background: NAVY_06,
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <Icon size={13} strokeWidth={1.5} style={{ color: TEXT_MUTED }} />
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ ...TYPE.h4, fontSize: "0.845rem", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {title || "Untitled"}
            </p>
            <CardRow style={{ marginTop: 3 }}>
              <StatusDot status={status} color={statusColor} />
              <MetaText>{status}</MetaText>
              {lastEdited && (
                <>
                  <span style={{ color: BRDX }}>·</span>
                  <Clock size={9} style={{ color: TEXT_MUTED }} />
                  <MetaText>{fmtRelative(lastEdited)}</MetaText>
                </>
              )}
            </CardRow>
          </div>

          {team.length > 0 && (
            <AvatarGroup users={team} size={20} max={3} style={{ flexShrink: 0 }} />
          )}

          {(to || onResume) && (
            <span
              onClick={e => { e.stopPropagation(); to ? navigate(to) : onResume?.(); }}
              style={{
                display: "inline-flex", alignItems: "center", gap: 4,
                padding: "4px 10px", fontSize: "0.7rem", fontWeight: 600,
                color: TEXT_SECONDARY, background: WHITE,
                border: `1px solid ${BRD}`, borderRadius: RADIUS_SM,
                cursor: "pointer", flexShrink: 0,
              }}
            >
              Resume <ArrowRight size={9} strokeWidth={2.5} />
            </span>
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card to={to} padding="none" style={{ overflow: "hidden" }}>
      <div style={{ padding: "16px 16px 12px" }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: RADIUS_LG, background: NAVY_06,
            border: `1px solid ${BRD}`,
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <Icon size={15} strokeWidth={1.5} style={{ color: TEXT_MUTED }} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ ...TYPE.h4, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {title || "Untitled"}
            </p>
            <CardRow style={{ marginTop: 4 }}>
              <Badge variant="neutral" size="sm">{type}</Badge>
              <StatusDot status={status} color={statusColor} />
              <MetaText>{status}</MetaText>
            </CardRow>
          </div>
        </div>

        {progress != null && (
          <div style={{ marginBottom: 10 }}>
            <ProgressBar value={progress} max={100} size="sm" showValue={false} />
            <MetaText style={{ marginTop: 3 }}>{progress}% complete</MetaText>
          </div>
        )}

        {tags.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
            {tags.slice(0, 3).map((t, i) => (
              <span key={i} style={{
                fontSize: "0.65rem", fontWeight: 600, color: TEXT_MUTED,
                background: WARM, border: `1px solid ${BRD}`,
                borderRadius: RADIUS_XS, padding: "1px 6px",
              }}>{t}</span>
            ))}
          </div>
        )}
      </div>

      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 16px", borderTop: `1px solid ${BRD}`, background: WARM,
      }}>
        <CardRow>
          {team.length > 0 && <AvatarGroup users={team} size={20} max={3} />}
          {lastEdited && <MetaText>Edited {fmtRelative(lastEdited)}</MetaText>}
        </CardRow>
        <ChevronRight size={13} style={{ color: TEXT_MUTED }} />
      </div>
    </Card>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// ResearchCard — Research project / paper overview
// ═══════════════════════════════════════════════════════════════════════════════

export function ResearchCard({
  title,
  abstract,
  status,
  authors = [],
  tags = [],
  metrics = [],
  to,
  highlight = false,
}) {
  return (
    <Card
      to={to}
      padding="none"
      style={highlight ? { borderLeft: `3px solid ${NAVY}`, overflow: "hidden" } : { overflow: "hidden" }}
    >
      <div style={{ padding: "16px 16px 12px" }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 8 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            {status && (
              <CardRow style={{ marginBottom: 6 }}>
                <StatusDot status={status} />
                <MetaText style={{ textTransform: "capitalize" }}>{status}</MetaText>
              </CardRow>
            )}
            <p style={{ ...TYPE.h4, margin: 0, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
              {title}
            </p>
          </div>
          <ChevronRight size={14} style={{ color: TEXT_MUTED, flexShrink: 0, marginTop: 2 }} />
        </div>

        {abstract && (
          <p style={{ ...TYPE.bodySm, margin: "0 0 12px", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
            {abstract}
          </p>
        )}

        {authors.length > 0 && (
          <CardRow style={{ marginBottom: tags.length ? 8 : 0 }}>
            <AvatarGroup users={authors} size={18} max={4} />
            <MetaText>
              {authors.slice(0, 2).map(a => a.full_name?.split(" ")[0]).join(", ")}
              {authors.length > 2 && ` +${authors.length - 2}`}
            </MetaText>
          </CardRow>
        )}

        {tags.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 8 }}>
            {tags.slice(0, 4).map((t, i) => (
              <span key={i} style={{
                fontSize: "0.63rem", fontWeight: 600, color: TEXT_MUTED,
                background: WARM, border: `1px solid ${BRD}`,
                borderRadius: RADIUS_XS, padding: "1px 6px",
              }}>{t}</span>
            ))}
          </div>
        )}
      </div>

      {metrics.length > 0 && (
        <div style={{ display: "flex", padding: "8px 16px", borderTop: `1px solid ${BRD}`, background: WARM }}>
          {metrics.map((m, i) => (
            <div key={i} style={{
              flex: 1, display: "flex", flexDirection: "column", gap: 1,
              paddingRight: i < metrics.length - 1 ? 12 : 0,
              marginRight:  i < metrics.length - 1 ? 12 : 0,
              borderRight:  i < metrics.length - 1 ? `1px solid ${BRD}` : "none",
            }}>
              <span style={{ ...TYPE.numberSm, fontSize: "0.875rem", fontVariantNumeric: "tabular-nums" }}>
                {m.value ?? "—"}
              </span>
              <MetaText>{m.label}</MetaText>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// PublicationCard — Journal article / paper reference
// ═══════════════════════════════════════════════════════════════════════════════

export function PublicationCard({ title, authors, journal, year, doi, citations, open = false, to }) {
  return (
    <Card to={to} padding="none" style={{ overflow: "hidden" }}>
      <div style={{ padding: "14px 16px" }}>
        <CardRow style={{ marginBottom: 7 }}>
          <BookOpen size={11} style={{ color: TEXT_MUTED }} />
          <MetaText>{journal}</MetaText>
          {year && <MetaText>· {year}</MetaText>}
          {open && (
            <span style={{
              fontSize: "0.6rem", fontWeight: 700, color: EMERALD,
              background: "#ECFDF5", border: "1px solid #6EE7B7",
              borderRadius: RADIUS_XS, padding: "1px 5px",
              letterSpacing: "0.04em", textTransform: "uppercase",
            }}>Open</span>
          )}
        </CardRow>

        <p style={{ ...TYPE.h4, margin: "0 0 6px", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {title}
        </p>

        {authors && (
          <MetaText style={{ display: "block", marginBottom: doi || citations != null ? 10 : 0 }}>
            {authors}
          </MetaText>
        )}

        {(doi || citations != null) && (
          <CardRow style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${BRD}`, justifyContent: "space-between" }}>
            {doi && (
              <CardRow>
                <ExternalLink size={10} style={{ color: TEXT_MUTED }} />
                <MetaText style={{ fontFamily: "monospace", fontSize: "0.6rem" }}>
                  {doi.replace("https://doi.org/", "")}
                </MetaText>
              </CardRow>
            )}
            {citations != null && (
              <CardRow>
                <TrendingUp size={10} style={{ color: EMERALD }} />
                <MetaText>{citations} citations</MetaText>
              </CardRow>
            )}
          </CardRow>
        )}
      </div>
    </Card>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// PersonCard — Researcher profile card
// ═══════════════════════════════════════════════════════════════════════════════

export function PersonCard({ user = {}, stats = [], tags = [], to, onConnect }) {
  const { full_name, avatar_url, institution, user_type } = user;

  return (
    <Card to={to} padding="none" style={{ overflow: "hidden" }}>
      <div style={{ padding: "16px 16px 12px" }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
          <Avatar url={avatar_url} name={full_name} size={38} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ ...TYPE.h4, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {full_name || "Researcher"}
            </p>
            {institution && <MetaText style={{ display: "block", marginTop: 2 }}>{institution}</MetaText>}
            {user_type && <Badge variant="neutral" size="sm" style={{ marginTop: 4 }}>{user_type}</Badge>}
          </div>
        </div>

        {tags.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
            {tags.slice(0, 3).map((t, i) => (
              <span key={i} style={{
                fontSize: "0.63rem", fontWeight: 600, color: NAVY,
                background: NAVY_06, border: `1px solid ${NAVY_12}`,
                borderRadius: RADIUS_XS, padding: "1px 6px",
              }}>{t}</span>
            ))}
          </div>
        )}

        {stats.length > 0 && (
          <div style={{ display: "flex", borderTop: `1px solid ${BRD}`, paddingTop: 10, marginTop: 4 }}>
            {stats.slice(0, 3).map((s, i) => (
              <div key={i} style={{
                flex: 1, textAlign: "center",
                borderRight: i < stats.length - 1 ? `1px solid ${BRD}` : "none",
              }}>
                <p style={{ ...TYPE.numberSm, fontSize: "0.95rem", margin: "0 0 1px", fontVariantNumeric: "tabular-nums" }}>
                  {s.value ?? "—"}
                </p>
                <MetaText>{s.label}</MetaText>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

// NOTE: the KPI/stat display card that used to live here as `MetricCard` has
// been consolidated into ds/StatCard.jsx — that is the one canonical
// implementation for numeric metric cards (it gained `to`-link support so
// nothing was lost in the merge). Never re-add a second one here.

// ═══════════════════════════════════════════════════════════════════════════════
// Timeline — Activity / event feed (not card-based, layout utility)
// ═══════════════════════════════════════════════════════════════════════════════

export function Timeline({ children, style, ...props }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", ...style }} {...props}>
      {children}
    </div>
  );
}

export function TimelineItem({
  label,
  description,
  time,
  icon,
  to,
  variant = "default",
  last = false,
}) {
  const dotColors = { default: "#CBD5E1", success: EMERALD, warning: AMBER, danger: CRIMSON };
  const dotColor = dotColors[variant] || dotColors.default;

  const inner = (
    <div style={{
      display: "flex", gap: 12,
      paddingBottom: last ? 0 : 14,
      marginBottom:  last ? 0 : 14,
      borderBottom:  last ? "none" : `1px solid ${BRDX}`,
    }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
        {icon ? (
          <div style={{
            width: 22, height: 22, borderRadius: "50%",
            background: WARM, border: `1px solid ${BRDX}`,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            {React.cloneElement(icon, { size: 11, style: { color: dotColor, ...(icon.props.style || {}) } })}
          </div>
        ) : (
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: dotColor, marginTop: 6, flexShrink: 0,
          }} aria-hidden="true" />
        )}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, justifyContent: "space-between" }}>
          <span style={{ ...TYPE.bodySm, fontWeight: 500, color: TEXT_PRIMARY }}>{label}</span>
          {time && <MetaText style={{ flexShrink: 0 }}>{time}</MetaText>}
        </div>
        {description && (
          <MetaText style={{ display: "block", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {description}
          </MetaText>
        )}
      </div>
    </div>
  );

  if (to) {
    return (
      <Link to={to} style={{ textDecoration: "none", color: "inherit" }}
        onMouseEnter={e => (e.currentTarget.style.opacity = "0.8")}
        onMouseLeave={e => (e.currentTarget.style.opacity = "1")}
      >
        {inner}
      </Link>
    );
  }

  return inner;
}

export default WorkspaceCard;

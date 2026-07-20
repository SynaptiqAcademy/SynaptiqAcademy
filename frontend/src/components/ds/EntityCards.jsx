/* eslint-disable */
import React from "react";
import {
  FileText, BookOpen, DollarSign, Calendar, Building2,
  Users, Bookmark, BookmarkCheck, ExternalLink, Star,
  Clock, ArrowUpRight, Globe, Award, Sparkles,
} from "lucide-react";
import { NAVY, ACCENT, EMERALD, AMBER, CRIMSON, BRD, WARM, WHITE,
         TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
         RADIUS_MD, RADIUS_FULL, FONT_SERIF } from "@/lib/tokens";
import { Card } from "./Card";
import { Badge } from "./Badge";
import { Tag, TagGroup } from "./Tag";
import { Avatar } from "./Avatar";
import { AvatarGroup } from "./AvatarGroup";
import { ProgressBar } from "./Progress";

// ── Shared helpers ────────────────────────────────────────────────────────────

function CardDivider() {
  return <div style={{ height: 1, background: BRD, margin: "12px 0" }} />;
}

function MetricPill({ label, value }) {
  return (
    <span style={{ display: "inline-flex", flexDirection: "column", gap: 1 }}>
      <span style={{ fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: TEXT_MUTED }}>{label}</span>
      <span style={{ fontSize: "0.78rem", fontWeight: 600, color: TEXT_PRIMARY, fontFamily: FONT_SERIF }}>{value ?? "—"}</span>
    </span>
  );
}

// ── GRANT CARD ────────────────────────────────────────────────────────────────
export function GrantCard({ grant, onClick, saved, onSave }) {
  const {
    title, funder, amount, currency = "EUR", deadline,
    research_areas = [], match_score, status,
  } = grant || {};

  const days = deadline ? Math.round((new Date(deadline) - new Date()) / 86_400_000) : null;
  const urgency = days === null ? null
    : days < 0   ? { label: "Closed",     color: TEXT_MUTED }
    : days === 0  ? { label: "Due today",  color: CRIMSON }
    : days <= 7   ? { label: `${days}d`,   color: CRIMSON }
    : days <= 30  ? { label: `${days}d`,   color: AMBER }
    :               { label: new Date(deadline).toLocaleDateString("en-GB", { day: "numeric", month: "short" }), color: TEXT_MUTED };

  const fmtAmt = amount
    ? amount >= 1_000_000 ? `${(amount / 1_000_000).toFixed(1)}M ${currency}`
      : amount >= 1_000   ? `${Math.round(amount / 1000)}K ${currency}`
      : `${amount} ${currency}`
    : null;

  return (
    <Card onClick={onClick} padding="md">
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
        <div style={{
          width: 32, height: 32, borderRadius: RADIUS_MD, background: WARM, border: `1px solid ${BRD}`,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}>
          <DollarSign size={14} style={{ color: NAVY }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: "0.68rem", color: TEXT_MUTED, margin: "0 0 2px" }}>{funder}</p>
          <h3 style={{ fontSize: "0.88rem", fontWeight: 600, color: TEXT_PRIMARY, margin: 0, lineHeight: 1.3,
                       display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
            {title}
          </h3>
        </div>
        {onSave && (
          <button onClick={e => { e.stopPropagation(); onSave?.(); }}
            style={{ background: "none", border: "none", cursor: "pointer", color: saved ? AMBER : TEXT_MUTED, flexShrink: 0, padding: 0 }}
            aria-label={saved ? "Unsave grant" : "Save grant"}>
            {saved ? <BookmarkCheck size={15} /> : <Bookmark size={15} />}
          </button>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
        {fmtAmt && (
          <span style={{ fontFamily: FONT_SERIF, fontSize: "1rem", fontWeight: 700, color: NAVY }}>{fmtAmt}</span>
        )}
        {urgency && (
          <span style={{
            fontSize: "0.7rem", fontWeight: 600, padding: "2px 8px", borderRadius: RADIUS_FULL,
            background: `${urgency.color}18`, color: urgency.color,
          }}>
            {urgency.label}
          </span>
        )}
      </div>

      {match_score != null && (
        <div style={{ marginBottom: 10 }}>
          <ProgressBar value={match_score} max={100} size="sm"
            label="Match" valueLabel={`${match_score}%`} colorByValue />
        </div>
      )}

      <TagGroup gap={4}>
        {research_areas.slice(0, 2).map(a => <Tag key={a} size="sm">{a}</Tag>)}
      </TagGroup>
    </Card>
  );
}

// ── CONFERENCE CARD ───────────────────────────────────────────────────────────
export function ConferenceCard({ conference, onClick }) {
  const {
    name, location, start_date, end_date, submission_deadline,
    acceptance_rate, status, research_areas = [], virtual,
  } = conference || {};

  const dateStr = start_date ? new Date(start_date).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : null;
  const statusColor = {
    "accepting submissions": EMERALD,
    "submission closed": AMBER,
    "decisions sent": NAVY,
    "registration open": EMERALD,
  }[status?.toLowerCase()] || TEXT_MUTED;

  return (
    <Card onClick={onClick} padding="md">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div>
          <p style={{ fontSize: "0.68rem", color: TEXT_MUTED, margin: "0 0 2px" }}>
            {dateStr}{virtual ? " · Virtual" : location ? ` · ${location}` : ""}
          </p>
          <h3 style={{ fontSize: "0.88rem", fontWeight: 600, color: TEXT_PRIMARY, margin: 0, lineHeight: 1.3,
                       display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
            {name}
          </h3>
        </div>
        {status && (
          <Badge size="sm" style={{ color: statusColor, borderColor: statusColor, flexShrink: 0, marginLeft: 8 }}>
            {status}
          </Badge>
        )}
      </div>

      <CardDivider />
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        {submission_deadline && (
          <MetricPill label="Deadline" value={new Date(submission_deadline).toLocaleDateString("en-GB", { day: "numeric", month: "short" })} />
        )}
        {acceptance_rate != null && <MetricPill label="Acceptance" value={`${acceptance_rate}%`} />}
      </div>
      {research_areas.length > 0 && (
        <TagGroup gap={4} style={{ marginTop: 10 }}>
          {research_areas.slice(0, 3).map(a => <Tag key={a} size="sm">{a}</Tag>)}
        </TagGroup>
      )}
    </Card>
  );
}

// ── JOURNAL CARD ──────────────────────────────────────────────────────────────
export function JournalCard({ journal, onClick, matchScore }) {
  const {
    name, publisher, impact_factor, cite_score, h_index,
    acceptance_rate, review_time_weeks, open_access,
    research_areas = [],
  } = journal || {};

  const initials = name?.split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase() || "J";

  return (
    <Card onClick={onClick} padding="md">
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 12 }}>
        <div style={{
          width: 40, height: 40, borderRadius: RADIUS_MD, background: NAVY,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}>
          <span style={{ fontSize: "0.72rem", fontWeight: 700, color: WHITE, letterSpacing: "0.05em" }}>{initials}</span>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h3 style={{ fontSize: "0.88rem", fontWeight: 600, color: TEXT_PRIMARY, margin: "0 0 2px", lineHeight: 1.3,
                       display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
            {name}
          </h3>
          <p style={{ fontSize: "0.7rem", color: TEXT_MUTED, margin: 0 }}>{publisher}</p>
        </div>
        {open_access && <Badge size="sm" variant="success">OA</Badge>}
        {matchScore != null && (
          <span style={{ fontSize: "0.75rem", fontWeight: 700, color: EMERALD }}>{matchScore}%</span>
        )}
      </div>

      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 10 }}>
        {impact_factor != null && <MetricPill label="Impact Factor" value={impact_factor.toFixed(2)} />}
        {h_index != null && <MetricPill label="H-index" value={h_index} />}
        {acceptance_rate != null && <MetricPill label="Acceptance" value={`${acceptance_rate}%`} />}
        {review_time_weeks != null && <MetricPill label="Review" value={`${review_time_weeks}w`} />}
      </div>

      <TagGroup gap={4}>
        {research_areas.slice(0, 3).map(a => <Tag key={a} size="sm">{a}</Tag>)}
      </TagGroup>
    </Card>
  );
}

// ── RESEARCHER CARD ───────────────────────────────────────────────────────────
export function ResearcherCard({ researcher, onClick, onFollow, layout = "grid" }) {
  const {
    name, title: jobTitle, institution, expertise = [],
    publications, citations, h_index, match_score,
    avatar, verified, following,
  } = researcher || {};

  if (layout === "list") {
    return (
      <Card onClick={onClick} padding="md">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Avatar src={avatar} name={name} size="lg" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <h3 style={{ fontSize: "0.88rem", fontWeight: 600, color: TEXT_PRIMARY, margin: 0 }}>{name}</h3>
              {verified && <span title="Verified" style={{ color: EMERALD }}>✓</span>}
            </div>
            <p style={{ fontSize: "0.73rem", color: TEXT_SECONDARY, margin: "2px 0 0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {[jobTitle, institution].filter(Boolean).join(" · ")}
            </p>
          </div>
          <div style={{ display: "flex", gap: 16, flexShrink: 0 }}>
            {publications != null && <MetricPill label="Pubs" value={publications} />}
            {h_index != null && <MetricPill label="H-index" value={h_index} />}
          </div>
          {match_score != null && (
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: EMERALD, flexShrink: 0 }}>{match_score}%</span>
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card onClick={onClick} padding="md">
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", marginBottom: 12 }}>
        <Avatar src={avatar} name={name} size="xl" style={{ marginBottom: 10 }} />
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <h3 style={{ fontSize: "0.9rem", fontWeight: 600, color: TEXT_PRIMARY, margin: 0 }}>{name}</h3>
          {verified && <span title="Verified" style={{ color: EMERALD, fontSize: "0.85rem" }}>✓</span>}
        </div>
        <p style={{ fontSize: "0.73rem", color: TEXT_SECONDARY, margin: "3px 0 0", lineHeight: 1.4 }}>
          {jobTitle}{institution ? `\n${institution}` : ""}
        </p>
      </div>

      {expertise.length > 0 && (
        <TagGroup gap={4} style={{ justifyContent: "center", marginBottom: 12 }}>
          {expertise.slice(0, 3).map(e => <Tag key={e} size="sm">{e}</Tag>)}
        </TagGroup>
      )}

      <CardDivider />
      <div style={{ display: "flex", justifyContent: "space-around" }}>
        {publications != null && <MetricPill label="Publications" value={publications} />}
        {citations != null && <MetricPill label="Citations" value={citations?.toLocaleString()} />}
        {h_index != null && <MetricPill label="H-index" value={h_index} />}
      </div>

      {match_score != null && (
        <div style={{ marginTop: 12 }}>
          <ProgressBar value={match_score} max={100} size="sm" label="Match" colorByValue />
        </div>
      )}

      {onFollow && (
        <button
          onClick={e => { e.stopPropagation(); onFollow?.(); }}
          style={{
            marginTop: 12, width: "100%", height: 32, borderRadius: RADIUS_MD,
            border: `1px solid ${following ? BRD : NAVY}`,
            background: following ? "transparent" : NAVY,
            color: following ? TEXT_SECONDARY : WHITE,
            fontSize: "0.78rem", fontWeight: 500, cursor: "pointer",
            transition: "all 150ms",
          }}
        >
          {following ? "Following" : "Follow"}
        </button>
      )}
    </Card>
  );
}

// ── INSTITUTION CARD ──────────────────────────────────────────────────────────
export function InstitutionCard({ institution, onClick }) {
  const {
    name, country, type, researchers, publications, grants,
    iis_score, rank, research_areas = [], logo,
  } = institution || {};

  const initials = name?.split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase() || "IN";

  return (
    <Card onClick={onClick} padding="md">
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 12 }}>
        <div style={{
          width: 40, height: 40, borderRadius: RADIUS_MD, background: NAVY,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}>
          {logo
            ? <img src={logo} alt="" style={{ width: 28, height: 28, objectFit: "contain" }} />
            : <span style={{ fontSize: "0.72rem", fontWeight: 700, color: WHITE }}>{initials}</span>
          }
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h3 style={{ fontSize: "0.88rem", fontWeight: 600, color: TEXT_PRIMARY, margin: "0 0 2px", lineHeight: 1.3 }}>
            {name}
          </h3>
          <p style={{ fontSize: "0.7rem", color: TEXT_MUTED, margin: 0 }}>
            {[country, type].filter(Boolean).join(" · ")}
          </p>
        </div>
        {iis_score != null && (
          <div style={{ textAlign: "right", flexShrink: 0 }}>
            <div style={{ fontFamily: FONT_SERIF, fontSize: "1.1rem", fontWeight: 700, color: NAVY }}>{iis_score}</div>
            <div style={{ fontSize: "0.6rem", color: TEXT_MUTED }}>IIS</div>
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 10 }}>
        {researchers != null && <MetricPill label="Researchers" value={researchers?.toLocaleString()} />}
        {publications != null && <MetricPill label="Publications" value={publications?.toLocaleString()} />}
        {rank != null && <MetricPill label="Rank" value={`#${rank}`} />}
      </div>

      <TagGroup gap={4}>
        {research_areas.slice(0, 3).map(a => <Tag key={a} size="sm">{a}</Tag>)}
      </TagGroup>
    </Card>
  );
}

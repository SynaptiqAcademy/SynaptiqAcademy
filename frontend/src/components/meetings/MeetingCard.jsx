import React from "react";
import { useNavigate } from "react-router-dom";
import { Video, MapPin, Pencil, Sparkles, FolderOpen, Layers } from "lucide-react";
import { Badge } from "@/components/ds/Badge";
import { Button } from "@/components/ds/Button";
import { AvatarGroup } from "@/components/ds/AvatarGroup";
import { NAVY, BRD, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, EMERALD, AMBER, WHITE } from "@/lib/tokens";

const STATUS_VARIANT = { scheduled: "info", completed: "success", cancelled: "neutral" };

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  } catch {
    return "";
  }
}

function isJoinable(meeting) {
  if (!meeting.video_link) return false;
  try {
    const start = new Date(meeting.start_at).getTime();
    const end = new Date(meeting.end_at).getTime();
    const now = Date.now();
    return now >= start - 10 * 60 * 1000 && now <= end;
  } catch {
    return false;
  }
}

/**
 * MeetingCard — timeline list-item.
 * Shows time/title/participants/workspace/project/type/status/join/edit/AI badge.
 */
export function MeetingCard({ meeting, onEdit }) {
  const navigate = useNavigate();
  const joinable = isJoinable(meeting);
  const participants = (meeting.participants || []).map((p) => ({ name: p.full_name, avatar: p.avatar_url }));

  return (
    <div
      style={{
        display: "flex",
        gap: 16,
        padding: "16px 18px",
        background: WHITE,
        border: `1px solid ${BRD}`,
        borderRadius: 8,
        cursor: "pointer",
        transition: "border-color 150ms, box-shadow 150ms",
      }}
      onClick={() => navigate(`/meetings/${meeting.id}`)}
      onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 4px 12px rgba(15,23,42,0.08)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "none"; }}
    >
      {/* Time column */}
      <div style={{ width: 64, flexShrink: 0, textAlign: "right" }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: NAVY }}>{formatTime(meeting.start_at)}</div>
        <div style={{ fontSize: 10.5, color: TEXT_MUTED, marginTop: 2 }}>{formatTime(meeting.end_at)}</div>
      </div>

      {/* Body */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: TEXT_PRIMARY, letterSpacing: "-0.01em" }}>
            {meeting.title}
          </span>
          <Badge variant={STATUS_VARIANT[meeting.status] || "neutral"} size="sm" dot>
            {meeting.status}
          </Badge>
          {meeting.ai_summary && (
            <Badge variant="purple" size="sm">
              <Sparkles size={10} style={{ marginRight: 2 }} /> AI summary
            </Badge>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", fontSize: 12, color: TEXT_SECONDARY }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>{meeting.meeting_type}</span>
          {meeting.workspace_name && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              <Layers size={11} /> {meeting.workspace_name}
            </span>
          )}
          {meeting.project_title && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              <FolderOpen size={11} /> {meeting.project_title}
            </span>
          )}
          {meeting.location && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              <MapPin size={11} /> {meeting.location}
            </span>
          )}
        </div>

        {participants.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <AvatarGroup users={participants} size="xs" max={5} />
          </div>
        )}
      </div>

      {/* Actions */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6, flexShrink: 0, alignItems: "flex-end" }} onClick={(e) => e.stopPropagation()}>
        {meeting.video_link && (
          <Button
            size="sm"
            variant={joinable ? "primary" : "ghost"}
            disabled={!joinable}
            onClick={() => window.open(meeting.video_link, "_blank", "noopener,noreferrer")}
          >
            <Video size={12} /> Join
          </Button>
        )}
        <Button size="sm" variant="ghost" onClick={() => onEdit?.(meeting)}>
          <Pencil size={12} /> Edit
        </Button>
      </div>
    </div>
  );
}

export default MeetingCard;

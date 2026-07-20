/* eslint-disable */
import React from "react";
import { Link } from "react-router-dom";
import { Calendar } from "lucide-react";
import {
  TEXT_PRIMARY, TEXT_MUTED, NAVY, BRDX, TYPE, CRIMSON, AMBER,
} from "@/lib/tokens";
import { transition } from "@/lib/motion";
import { EmptyState } from "@/components/ds/EmptyState";

const URGENCY_COLOR = {
  missed:   CRIMSON,
  critical: AMBER,
  due_soon: AMBER,
  upcoming: TEXT_MUTED,
};

function getColor(d) {
  return URGENCY_COLOR[d.urgency] || URGENCY_COLOR.upcoming;
}

function DeadlineRow({ item, last }) {
  const color = getColor(item);
  const title = item.label || item.title || item.name || "Deadline";
  const rowStyle = {
    display: "flex",
    gap: 10,
    paddingBottom: last ? 0 : 14,
    marginBottom: last ? 0 : 14,
    borderBottom: last ? "none" : `1px solid ${BRDX}`,
    textDecoration: "none",
    color: "inherit",
  };

  const content = (
    <>
      <span
        aria-hidden="true"
        style={{ width: 6, height: 6, borderRadius: "50%", background: color, marginTop: 6, flexShrink: 0 }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            ...TYPE.bodySm, fontWeight: 600, margin: "0 0 2px",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}
        >
          {title}
        </p>
        <span style={{ ...TYPE.caption }}>
          {item.due_display || item.due_date || item.due || "—"}
        </span>
      </div>
    </>
  );

  return item.link ? (
    <Link to={item.link} style={rowStyle}>{content}</Link>
  ) : (
    <div style={rowStyle}>{content}</div>
  );
}

export default function Upcoming({ deadlines = [] }) {
  return (
    <section aria-label="Upcoming Deadlines">
      <div className="flex items-baseline justify-between mb-4">
        <h2 style={{ ...TYPE.label, margin: 0, fontSize: "0.72rem" }}>What's next</h2>
        <Link
          to="/today"
          style={{ ...TYPE.caption, color: TEXT_MUTED, textDecoration: "none", transition: transition.colorFast }}
          onMouseEnter={e => (e.currentTarget.style.color = NAVY)}
          onMouseLeave={e => (e.currentTarget.style.color = TEXT_MUTED)}
        >
          All →
        </Link>
      </div>

      {deadlines.length === 0 ? (
        <EmptyState
          icon={<Calendar />}
          title="Nothing on the horizon"
          description="Deadlines from your grants, manuscripts, and workspaces will show up here."
          size="sm"
          action={
            <Link to="/grants" style={{ ...TYPE.caption, color: NAVY, textDecoration: "none" }}>
              Track a grant deadline →
            </Link>
          }
        />
      ) : (
        deadlines.map((d, i) => (
          <DeadlineRow key={i} item={d} last={i === deadlines.length - 1} />
        ))
      )}
    </section>
  );
}

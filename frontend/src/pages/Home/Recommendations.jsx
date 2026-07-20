/* eslint-disable */
import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { User, Calendar, Coins, TrendingUp, ArrowUpRight } from "lucide-react";
import { Avatar } from "@/components/ds/Avatar";
import { userTypeLabel } from "@/lib/userTypes";
import {
  TEXT_PRIMARY, TEXT_MUTED, NAVY, NAVY_06, BRDX, EMERALD, TYPE,
  DANGER_BG, DANGER_TEXT, INFO, INFO_BG, SUCCESS_BG,
} from "@/lib/tokens";
import { EmptyState } from "@/components/ds/EmptyState";
import { transition } from "@/lib/motion";

function RecRow({ type, icon: Icon, iconBg, iconColor, title, desc, to, avatarUrl, name, last }) {
  return (
    <Link
      to={to}
      style={{
        display: "flex", alignItems: "center", gap: 14,
        padding: "16px 0",
        borderBottom: last ? "none" : `1px solid ${BRDX}`,
        textDecoration: "none",
      }}
      className="group"
    >
      {avatarUrl || name ? (
        <Avatar url={avatarUrl} name={name} size={36} />
      ) : (
        <div
          style={{
            width: 36, height: 36, borderRadius: 9, flexShrink: 0,
            background: iconBg || NAVY_06,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}
        >
          <Icon size={15} strokeWidth={1.75} style={{ color: iconColor || NAVY }} />
        </div>
      )}

      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="flex items-center gap-2">
          <span
            style={{
              fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.08em",
              textTransform: "uppercase", color: TEXT_MUTED,
            }}
          >
            {type}
          </span>
        </div>
        <p
          style={{
            ...TYPE.h4, margin: "2px 0 0",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}
        >
          {title}
        </p>
        {desc && (
          <p style={{ ...TYPE.caption, margin: "2px 0 0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {desc}
          </p>
        )}
      </div>

      <ArrowUpRight
        size={15}
        className="opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0"
        style={{ color: TEXT_MUTED, transition: "opacity 150ms ease, transform 150ms ease", flexShrink: 0 }}
      />
    </Link>
  );
}

export default function Recommendations({ feed }) {
  const items = useMemo(() => {
    if (!feed) return [];
    const out = [];

    (feed.researchers || []).slice(0, 1).forEach(r => {
      out.push({
        type:      "Collaborator",
        icon:      User,
        title:     r.full_name,
        desc:      [userTypeLabel?.(r) || r.user_type, r.institution].filter(Boolean).join(" · "),
        to:        r.id ? `/profile/${r.id}` : "/network",
        avatarUrl: r.avatar_url,
        name:      r.full_name,
      });
    });

    (feed.grants || []).slice(0, 1).forEach(g => {
      out.push({
        type: "Grant", icon: Coins, iconBg: DANGER_BG, iconColor: DANGER_TEXT,
        title: g.title, desc: g.amount || g.description, to: "/funding",
      });
    });

    (feed.conferences || []).slice(0, 1).forEach(c => {
      out.push({
        type: "Conference", icon: Calendar, iconBg: INFO_BG, iconColor: INFO,
        title: c.name, desc: [c.date, c.location].filter(Boolean).join(" · "), to: "/conferences",
      });
    });

    (feed.trending_topics || []).slice(0, 1).forEach(t => {
      out.push({
        type: "Trending", icon: TrendingUp, iconBg: SUCCESS_BG, iconColor: EMERALD,
        title: t.topic, desc: t.description || "Trending in your research field", to: "/discover",
      });
    });

    return out;
  }, [feed]);

  return (
    <section aria-label="Recommendations">
      <div className="flex items-baseline justify-between mb-1">
        <h2
          style={{
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: "1.35rem", fontWeight: 700, letterSpacing: "-0.02em",
            color: TEXT_PRIMARY, margin: 0,
          }}
        >
          Recommended for you
        </h2>
        <Link
          to="/discover"
          style={{ ...TYPE.caption, color: TEXT_MUTED, textDecoration: "none", transition: transition.colorFast }}
          onMouseEnter={e => (e.currentTarget.style.color = NAVY)}
          onMouseLeave={e => (e.currentTarget.style.color = TEXT_MUTED)}
        >
          Explore more →
        </Link>
      </div>
      {items.length === 0 ? (
        <EmptyState
          icon={<TrendingUp />}
          title="No recommendations yet"
          description="Keep using Synaptiq and we'll surface collaborators, grants, and conferences suited to your research."
        />
      ) : (
        <div>
          {items.map((item, i) => (
            <RecRow key={i} {...item} last={i === items.length - 1} />
          ))}
        </div>
      )}
    </section>
  );
}

/* eslint-disable */
import React from "react";
import { FolderOpen, Users, BookOpen, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";

/**
 * KpiCards — the dashboard's at-a-glance metric row.
 *
 * Every value here comes directly from data already fetched by Home/index.jsx
 * (research-impact KPIs, the discover feed, billing, manuscripts/workspaces)
 * or the live unread-messages count — nothing here is invented. A card is
 * only rendered when its backing value actually exists, rather than showing
 * a fabricated placeholder number.
 */
export default function KpiCards({ kpi, feed, manuscripts, workspaces, billing }) {

  const cards = [
    {
      key: "projects",
      label: "Active projects",
      value: kpi?.projects_count ?? ((manuscripts.length + workspaces.length) || null),
      icon: <FolderOpen size={16} strokeWidth={1.75} />,
      to: "/workspaces",
    },
    {
      key: "collaborators",
      label: "Collaborators",
      value: feed?.researchers?.length ?? null,
      icon: <Users size={16} strokeWidth={1.75} />,
      to: "/network",
    },
    {
      key: "publications",
      label: "Publications",
      value: kpi?.publications_count ?? null,
      icon: <BookOpen size={16} strokeWidth={1.75} />,
      to: "/manuscripts",
    },
    {
      key: "impact",
      label: "Impact score",
      value: kpi?.sis_score != null ? Math.round(kpi.sis_score) : null,
      icon: <TrendingUp size={16} strokeWidth={1.75} />,
      to: "/research-impact",
      highlight: true,
    },
  // A metric earns space only when it says something: zero or missing values
  // are left out. Credits and unread messages live in the app shell.
  ].filter(c => c.value != null && c.value !== 0 && c.value !== "0");

  if (cards.length === 0) return null;

  return (
    <section aria-label="Overview">
      <dl className="pl-stats" style={{ marginTop: 0 }}>
        {cards.map((c) => (
          <div key={c.key}>
            <dd><Link to={c.to} className="hm-stat">{c.value}</Link></dd>
            <dt>{c.label}</dt>
          </div>
        ))}
      </dl>
    </section>
  );
}

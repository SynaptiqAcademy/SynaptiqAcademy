/* eslint-disable */
import React from "react";
import { FolderOpen, Users, BookOpen, TrendingUp, Zap, MessageSquare } from "lucide-react";
import { StatGrid, StatCard } from "@/components/ds/StatCard";
import { useUnread } from "@/contexts/UnreadContext";

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
  const { total: unreadMessages } = useUnread();
  const credits = billing?.credits;
  const creditBalance = credits?.monthly_balance ?? credits?.balance ?? null;

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
    {
      key: "credits",
      label: "AI credits",
      value: creditBalance != null ? creditBalance.toLocaleString() : null,
      icon: <Zap size={16} strokeWidth={1.75} />,
      to: "/ai-credits",
    },
    {
      key: "messages",
      label: "Unread messages",
      value: unreadMessages > 0 ? unreadMessages : (unreadMessages === 0 ? 0 : null),
      icon: <MessageSquare size={16} strokeWidth={1.75} />,
      to: "/messages",
    },
  ].filter(c => c.value != null);

  if (cards.length === 0) return null;

  return (
    <section aria-label="Overview Metrics">
      <StatGrid cols={cards.length >= 4 ? 4 : cards.length}>
        {cards.map(c => (
          <StatCard
            key={c.key}
            label={c.label}
            value={c.value}
            icon={c.icon}
            to={c.to}
            highlight={c.highlight}
          />
        ))}
      </StatGrid>
    </section>
  );
}

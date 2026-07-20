/* eslint-disable */
import React from "react";
import { Link } from "react-router-dom";
import { BookOpen, Lightbulb, Zap, ArrowUpRight } from "lucide-react";
import {
  TEXT_PRIMARY, TEXT_MUTED, NAVY, AMBER, EMERALD, BRDX, TYPE,
} from "@/lib/tokens";

const ITEMS = [
  {
    icon:  BookOpen,
    color: NAVY,
    title: "Getting started with Synaptiq AI",
    to:    "/ai",
  },
  {
    icon:  Lightbulb,
    color: AMBER,
    title: "Research Impact Score explained",
    to:    "/research-impact",
  },
  {
    icon:  Zap,
    color: EMERALD,
    title: "Collaborate on grant applications",
    to:    "/grant-collaboration-hub",
  },
];

function ResourceRow({ item, last }) {
  const Icon = item.icon;
  return (
    <Link
      to={item.to}
      className="group"
      style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "11px 0",
        borderBottom: last ? "none" : `1px solid ${BRDX}`,
        textDecoration: "none",
      }}
    >
      <Icon size={13} strokeWidth={1.75} style={{ color: item.color, flexShrink: 0 }} />
      <span style={{ ...TYPE.bodySm, fontWeight: 500, color: TEXT_PRIMARY, flex: 1 }}>
        {item.title}
      </span>
      <ArrowUpRight
        size={12}
        className="opacity-0 group-hover:opacity-100"
        style={{ color: TEXT_MUTED, transition: "opacity 150ms ease", flexShrink: 0 }}
      />
    </Link>
  );
}

export default function Learning() {
  return (
    <section aria-label="Learning and Tips">
      <h2 style={{ ...TYPE.label, margin: "0 0 4px", fontSize: "0.72rem" }}>Resources</h2>
      <div>
        {ITEMS.map((item, i) => (
          <ResourceRow key={i} item={item} last={i === ITEMS.length - 1} />
        ))}
      </div>
    </section>
  );
}

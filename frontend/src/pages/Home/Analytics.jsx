/* eslint-disable */
import React from "react";
import { Link } from "react-router-dom";

function Stat({ label, value, to }) {
  const inner = (
    <div className="flex items-baseline gap-2">
      <span
        style={{
          fontFamily: "Georgia, 'Times New Roman', serif",
          fontSize: "1.15rem",
          fontWeight: 700,
          color: "#F8FAFC",
          fontVariantNumeric: "tabular-nums",
          letterSpacing: "-0.02em",
        }}
      >
        {value ?? "—"}
      </span>
      <span
        style={{
          fontSize: "0.7rem",
          fontWeight: 500,
          color: "rgba(255,255,255,0.45)",
        }}
      >
        {label}
      </span>
    </div>
  );

  if (!to) return inner;
  return (
    <Link to={to} style={{ textDecoration: "none" }} className="group">
      {inner}
    </Link>
  );
}

export default function Analytics({ kpi, feed, manuscripts, workspaces }) {
  const metrics = [
    {
      label: "active projects",
      value: kpi?.projects_count ?? ((manuscripts.length + workspaces.length) || "—"),
      to:    "/workspaces",
    },
    {
      label: "collaborators",
      value: feed?.researchers?.length ?? "—",
      to:    "/network",
    },
    {
      label: "publications",
      value: kpi?.publications_count ?? "—",
      to:    "/manuscripts",
    },
    {
      label: "impact score",
      value: kpi?.sis_score != null ? Math.round(kpi.sis_score) : "—",
      to:    "/research-impact",
    },
  ];

  return (
    <section
      aria-label="Analytics Overview"
      className="mt-10 pt-6 flex flex-wrap items-center gap-x-8 gap-y-3 sq-fade-up sq-delay-2"
      style={{ borderTop: "1px solid rgba(255,255,255,0.08)" }}
    >
      {metrics.map((m, i) => (
        <React.Fragment key={m.label}>
          <Stat {...m} />
          {i < metrics.length - 1 && (
            <span aria-hidden="true" style={{ width: 3, height: 3, borderRadius: "50%", background: "rgba(255,255,255,0.15)" }} />
          )}
        </React.Fragment>
      ))}
    </section>
  );
}

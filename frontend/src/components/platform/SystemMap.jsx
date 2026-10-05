import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { trackMarketingEvent as track } from "@/lib/marketingAnalytics";

/**
 * The Synaptiq research system, drawn as a figure.
 *
 * Every node is a shipped capability and every edge is a real data link:
 * - discovery reads Academic Passports (services/research_need/evidence.py)
 * - Team Builder turns expertise needs into roles and creates the project
 *   and workspace (routers/team_builder.py)
 * - manuscripts and grant applications keep their project / workspace ids
 *   (routers/manuscripts.py, routers/grant_applications.py)
 * Plan labels follow services/monetization_middleware.py and
 * plans_catalogue.py. AI marks are on the steps with credit-metered AI.
 *
 * Desktop: an interactive figure (select a node to read it and light its
 * connections). Below 1024px: a vertical layered index with the same text.
 * Both are plain buttons / details, so nothing depends on hover.
 */
export const NODES = {
  passport: {
    x: 610, y: 60, layer: 0, title: "Academic Passport", plan: "Free",
    body: "Research areas, methods, professional expertise and what you're open to, with your ORCID record attached. Discovery reads it when someone needs what you know.",
  },
  need: {
    x: 200, y: 200, layer: 1, title: "Research Need", plan: "Pro", ai: true,
    body: "A problem written as what it requires: fields, methods, setting. Not a keyword search.",
  },
  expertise: {
    x: 405, y: 200, layer: 1, title: "Expertise", plan: "Pro",
    body: "The need split into what to look for: directly relevant, complementary, methods and context.",
  },
  people: {
    x: 610, y: 200, layer: 1, title: "Discovery", plan: "Pro",
    body: "Members whose Passports fit, each shown with the evidence: what their profile lists and which methods they use. No match scores.",
  },
  request: {
    x: 815, y: 200, layer: 1, title: "Collaboration request", plan: "Pro",
    body: "You write to someone with the context attached. They accept or decline. Nothing is sent on your behalf.",
  },
  team: {
    x: 405, y: 340, layer: 2, title: "Team Builder", plan: "Pro", ai: true,
    body: "Turns the expertise a project needs into roles marked essential, useful or optional, and fills them from discovery.",
  },
  project: {
    x: 610, y: 340, layer: 2, title: "Project & workspace", plan: "Pro",
    body: "Where the team works: tasks, documents, notes, milestones, files and comments. Team Builder can create it directly.",
  },
  teaching: {
    x: 200, y: 480, layer: 3, title: "Teaching", plan: "Pro", ai: true,
    body: "Lesson plans, assessments and teaching workspaces. Its own context, next to your research rather than inside it.",
  },
  research: {
    x: 405, y: 480, layer: 3, title: "Research", plan: "Pro", ai: true, href: "/research", event: "platform_research_clicked", cta: "Explore Research",
    body: "Develop the work inside the project, with the AI Research Assistant. Literature review and study-design tools are on Pro Advanced.",
  },
  funding: {
    x: 610, y: 480, layer: 3, title: "Funding", plan: "Pro", ai: true,
    body: "Grant discovery for your areas, and applications that keep the team, budget, deliverables and versions in the project's workspace.",
  },
  publishing: {
    x: 815, y: 480, layer: 3, title: "Publishing", plan: "Pro", ai: true,
    body: "Manuscripts linked to their project, journal and conference discovery, and each submission's status from draft to decision.",
  },
  record: {
    x: 610, y: 610, layer: 4, title: "Research record", plan: "Free · more on paid plans",
    body: "Publications from ORCID on every plan. Publication tracking on Pro; citation monitoring and the impact dashboard on Pro Advanced. It returns to your Passport.",
  },
};

export const AI_NOTE = {
  title: "AI assistance", plan: "Pro · more on Pro Advanced", href: "/ai-workspace", event: "platform_ai_workspace_clicked", cta: "Explore AI Workspace",
  body: "Available at the marked steps. Each action shows its AI Credit cost before it runs. It doesn't choose your collaborators or contact anyone.",
};

export const LAYERS = ["Identity", "Network", "Work", "Output", "Record"];

const EDGES = [
  ["passport", "people", "M610,88 V172"],
  ["need", "expertise", "M280,200 H325"],
  ["expertise", "people", "M485,200 H530"],
  ["people", "request", "M690,200 H735"],
  ["expertise", "team", "M405,228 V312"],
  ["team", "project", "M485,340 H530"],
  ["request", "project", "M815,228 V340 H690"],
  ["project", "research", "M610,368 V410 H405 V452"],
  ["project", "funding", "M610,368 V452"],
  ["project", "publishing", "M610,368 V410 H815 V452"],
  ["teaching", "project", "M200,452 V410 H405", true],
  ["research", "record", "M405,508 V560 H610 V582"],
  ["funding", "record", "M610,508 V582"],
  ["publishing", "record", "M815,508 V560 H610 V582"],
  ["record", "passport", "M690,610 H955 V60 H690"],
];

export function neighbours(key) {
  const out = [];
  EDGES.forEach(([a, b]) => {
    if (a === key && !out.includes(b)) out.push(b);
    if (b === key && !out.includes(a)) out.push(a);
  });
  return out;
}

function Detail({ k, onSelect }) {
  const n = k === "ai" ? AI_NOTE : NODES[k];
  const links = k === "ai" ? Object.keys(NODES).filter((x) => NODES[x].ai) : neighbours(k);
  return (
    <>
      <div className="lp-mono pf-detail-kicker">
        {k === "ai" ? "Supporting layer" : LAYERS[n.layer]} · {n.plan}
      </div>
      <h3 className="pf-detail-title">{n.title}</h3>
      <p className="pf-detail-body">{n.body}</p>
      <div className="pf-detail-links">
        <span className="lp-mono">{k === "ai" ? "At" : "Connects to"}</span>
        {links.map((x) => (
          <button key={x} type="button" className="lp-textbtn" onClick={() => onSelect(x)}>{NODES[x].title}</button>
        ))}
      </div>
      {n.href && (
        <Link to={n.href} className="lp-link pf-detail-cta" onClick={() => track(n.event, { location: "system_map" })}>
          {n.cta} →
        </Link>
      )}
    </>
  );
}

export default function SystemMap() {
  const [sel, setSel] = useState("passport");
  const select = (k) => {
    setSel(k);
    track("platform_system_explored", { node: k });
  };
  const lit = useMemo(() => new Set(
    sel === "ai" ? Object.keys(NODES).filter((k) => NODES[k].ai) : [sel, ...neighbours(sel)]
  ), [sel]);

  return (
    <figure className="pf-map" aria-labelledby="pf-map-caption">
      <figcaption id="pf-map-caption" className="lp-figcaption lp-mono">
        <span>Fig. 2 — The research system</span>
        <span aria-hidden="true">select a part</span>
      </figcaption>

      {/* Desktop figure */}
      <div className="pf-canvas-wrap">
        <div className={`pf-canvas ${sel === "ai" ? "is-ai" : ""}`}>
          <svg className="pf-lines" viewBox="0 0 1000 660" aria-hidden="true" focusable="false">
            <defs>
              <marker id="pf-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M0,0.5 L7,4 L0,7.5" fill="none" stroke="currentColor" strokeWidth="1" />
              </marker>
            </defs>
            {EDGES.map(([a, b, d, dashed]) => {
              const on = sel !== "ai" && (a === sel || b === sel);
              return (
                <path key={`${a}-${b}`} d={d} className={`pf-edge ${on ? "is-on" : ""} ${dashed ? "is-dashed" : ""}`}
                  markerEnd={dashed ? undefined : "url(#pf-arrow)"} />
              );
            })}
          </svg>

          {LAYERS.map((l, i) => (
            <div key={l} className="pf-layer-label lp-mono" style={{ top: `${([60, 200, 340, 480, 610][i] / 660) * 100}%` }}>
              <b>{["I", "II", "III", "IV", "V"][i]}</b> {l}
            </div>
          ))}
          <div className="pf-loop-label lp-mono" aria-hidden="true">returns to the Passport</div>

          {Object.entries(NODES).map(([k, n]) => (
            <button
              key={k}
              type="button"
              className={`pf-node ${sel === k ? "is-sel" : ""} ${lit.has(k) ? "is-lit" : ""}`}
              style={{ left: `${n.x / 10}%`, top: `${(n.y / 660) * 100}%` }}
              aria-pressed={sel === k}
              aria-controls="pf-detail"
              onClick={() => select(k)}
            >
              <span className="pf-node-title">{n.title}</span>
              <span className="pf-node-plan lp-mono">{n.plan.split(" ·")[0]}</span>
              {n.ai && <span className="pf-ai-mark" aria-hidden="true" />}
              {n.ai && <span className="sr-only">, AI assistance available</span>}
            </button>
          ))}
        </div>

        <div className="pf-map-foot">
          <button type="button" className={`pf-ai-key ${sel === "ai" ? "is-sel" : ""}`} aria-pressed={sel === "ai"}
            aria-controls="pf-detail" onClick={() => select("ai")}>
            <span className="pf-ai-mark pf-ai-mark--inline" aria-hidden="true" /> AI assistance is available at the marked steps
          </button>
          <span className="lp-mono pf-dash-key"><span aria-hidden="true" className="pf-dash-swatch" /> separate context, same workspace model</span>
        </div>

        <div id="pf-detail" className="pf-detail" aria-live="polite">
          <Detail k={sel} onSelect={select} />
        </div>
      </div>

      {/* Below 1024px: the same system as a vertical index */}
      <ol className="pf-index">
        {LAYERS.map((l, i) => (
          <li key={l} className="pf-index-layer">
            <div className="pf-index-head lp-mono"><b>{["I", "II", "III", "IV", "V"][i]}</b> {l}</div>
            {Object.entries(NODES).filter(([, n]) => n.layer === i).map(([k, n]) => (
              <details key={k} className="pf-index-item" onToggle={(e) => e.currentTarget.open && track("platform_system_explored", { node: k })}>
                <summary>
                  <span>{n.title}{n.ai && <span className="pf-ai-mark pf-ai-mark--inline" aria-label="AI assistance available" />}</span>
                  <span className="lp-mono">{n.plan.split(" ·")[0]}</span>
                </summary>
                <p>{n.body}</p>
                {n.href && (
                  <Link to={n.href} className="lp-link" onClick={() => track(n.event, { location: "system_index" })}>{n.cta} →</Link>
                )}
              </details>
            ))}
          </li>
        ))}
        <li className="pf-index-layer pf-index-ai">
          <div className="pf-index-head lp-mono"><span className="pf-ai-mark pf-ai-mark--inline" aria-hidden="true" /> Across the system</div>
          <p><b>{AI_NOTE.title}.</b> {AI_NOTE.body}</p>
          <Link to={AI_NOTE.href} className="lp-link" onClick={() => track(AI_NOTE.event, { location: "system_index" })}>{AI_NOTE.cta} →</Link>
        </li>
      </ol>
    </figure>
  );
}

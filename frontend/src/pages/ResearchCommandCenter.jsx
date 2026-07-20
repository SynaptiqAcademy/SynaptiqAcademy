/* eslint-disable */
import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ResearchLayout } from "@/layouts";
import { NAVY, WARM, ACCENT } from "@/lib/tokens";
import {
  Search, BookOpen, Target, Lightbulb, Database, BarChart2, FileText,
  Users, Send, Globe, TrendingUp, FolderOpen, LayoutGrid, Archive,
  Microscope, GitBranch, CheckSquare, Award, ArrowRight, Check, Layers,
  FlaskConical, GraduationCap, Building2,
} from "lucide-react";

const BORDER = "#E4E8EF";
const MID    = "#64748b";
const FAINT  = "#94a3b8";
const NAVY2  = "#0a1c34";

// ─── Static data ──────────────────────────────────────────────────────────────

const LIFECYCLE = [
  { n:  1, label: "Discover",         icon: Search,       desc: "Explore the research landscape and find your entry point.",          href: "/akg/search"             },
  { n:  2, label: "Literature",       icon: BookOpen,     desc: "Map existing knowledge and understand the state of the field.",       href: "/literature-review"       },
  { n:  3, label: "Identify Gaps",    icon: Target,       desc: "Find where new knowledge is genuinely needed.",                      href: "/research-gap-finder"     },
  { n:  4, label: "Develop Ideas",    icon: Lightbulb,    desc: "Formulate hypotheses, research questions, and objectives.",          href: "/workspaces"              },
  { n:  5, label: "Methodology",      icon: Layers,       desc: "Design your study and select the right methods.",                    href: "/research-design-advisor" },
  { n:  6, label: "Collect Data",     icon: Database,     desc: "Gather, store and organise your research materials.",                href: "/repository"              },
  { n:  7, label: "Analyse",          icon: BarChart2,    desc: "Apply statistical methods and extract meaningful insights.",         href: "/statistical-review"      },
  { n:  8, label: "Write",            icon: FileText,     desc: "Draft and refine your manuscript with structured writing tools.",   href: "/manuscripts"             },
  { n:  9, label: "Collaborate",      icon: Users,        desc: "Invite colleagues to review, annotate and contribute.",              href: "/collaborations"          },
  { n: 10, label: "Submit",           icon: Send,         desc: "Find the right journal and manage your submission.",                 href: "/journal-matching"        },
  { n: 11, label: "Publish",          icon: Globe,        desc: "Share your findings with the global academic community.",            href: "/manuscripts"             },
  { n: 12, label: "Measure Impact",   icon: TrendingUp,   desc: "Track citations, visibility and real-world influence.",              href: "/research-impact"         },
];

const MODULES = [
  { icon: FolderOpen,   label: "Research Projects",   desc: "Organise work into structured projects with milestones.",     href: "/projects"          },
  { icon: LayoutGrid,   label: "Workspaces",          desc: "Shared environments for writing, thinking and planning.",     href: "/workspaces"        },
  { icon: Archive,      label: "Repository",          desc: "Store files and datasets with full version control.",         href: "/repository"        },
  { icon: Users,        label: "Collaborations",      desc: "Research partnerships across institutions and borders.",      href: "/collaborations"    },
  { icon: FileText,     label: "Manuscripts",         desc: "Write from first draft through to published paper.",         href: "/manuscripts"       },
  { icon: Database,     label: "Datasets",            desc: "Upload, curate and share research data.",                    href: "/repository"        },
  { icon: Microscope,   label: "Protocols",           desc: "Document reproducible research procedures.",                 href: "/sie/planning"      },
  { icon: GitBranch,    label: "Version History",     desc: "Every change tracked. Nothing lost.",                        href: "/repository"        },
  { icon: CheckSquare,  label: "Reviewer Workspace",  desc: "Structured peer review with tracked annotations.",           href: "/manuscript-review" },
  { icon: BookOpen,     label: "Publishing",          desc: "Journal matching and submission pipeline management.",       href: "/journal-matching"  },
  { icon: TrendingUp,   label: "Impact",              desc: "Citations, H-index and influence metrics in one view.",      href: "/research-impact"   },
  { icon: Award,        label: "Funding",             desc: "Grants discovery and application management.",               href: "/grant-hub"         },
];

const WORKFLOW = [
  { label: "Idea",         desc: "Define your research question and scope."         },
  { label: "Evidence",     desc: "Review existing literature and map the field."    },
  { label: "Methodology",  desc: "Design your study and select your methods."       },
  { label: "Analysis",     desc: "Collect, clean and interpret your data."          },
  { label: "Manuscript",   desc: "Write and edit your paper iteratively."           },
  { label: "Peer Review",  desc: "Submit, respond to reviewers, revise."            },
  { label: "Publication",  desc: "Publish in a peer-reviewed journal."              },
  { label: "Impact",       desc: "Track citations, reach and real-world influence." },
];

const RESEARCHER_TYPES = [
  { icon: GraduationCap, label: "Undergraduate",    desc: "Structure your first research project with guided workflows."       },
  { icon: GraduationCap, label: "Master's",         desc: "Manage literature, data and thesis writing in one place."           },
  { icon: GraduationCap, label: "PhD",              desc: "Track experiments, milestones and supervisor feedback."              },
  { icon: GraduationCap, label: "Postdoctoral",     desc: "Balance multiple projects, grants and publications efficiently."    },
  { icon: FlaskConical,  label: "Researcher",       desc: "Focus on discovery with organised, reproducible workflows."         },
  { icon: FlaskConical,  label: "Professor",        desc: "Coordinate teams, students and institution-level research."         },
  { icon: Users,         label: "Research Team",    desc: "Collaborate across disciplines with shared workspaces."             },
  { icon: Building2,     label: "Institution",      desc: "Govern research outputs and measure institutional impact."          },
];

const COLLAB_FEATURES = [
  "Invite researchers by email or ORCID",
  "Assign roles: author, reviewer, observer",
  "Annotate and review collaboratively in real time",
  "Full version history on every document",
  "Threaded comments and @mentions",
  "Task assignments with deadlines",
  "Approval workflows for submissions",
  "Shared repository with access controls",
];

const OUTCOMES = [
  { label: "Publish faster",        desc: "Streamlined workflows from idea to submission reduce time-to-publish significantly." },
  { label: "Stay organised",        desc: "Every project, document and dataset in one structured, searchable workspace."        },
  { label: "Never lose versions",   desc: "Complete version history across all documents, data and research materials."          },
  { label: "Track contributions",   desc: "Clear authorship and contribution records across every collaborative project."        },
  { label: "Measure impact",        desc: "Citations, H-index and influence metrics in one unified dashboard."                  },
  { label: "Collaborate globally",  desc: "Work with researchers anywhere — asynchronously or in real time."                   },
];

// ─── Layout primitives ────────────────────────────────────────────────────────

function Eyebrow({ text }) {
  return (
    <div style={{ fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase", color: FAINT, marginBottom: 16 }}>
      {text}
    </div>
  );
}

function H2({ children, center, light }) {
  return (
    <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.8rem, 3vw, 2.5rem)", fontWeight: 700, color: light ? "#fff" : NAVY, lineHeight: 1.15, letterSpacing: "-0.025em", margin: 0, textAlign: center ? "center" : "left" }}>
      {children}
    </h2>
  );
}

function Body({ children, center, light }) {
  return (
    <p style={{ fontSize: "1rem", color: light ? "rgba(255,255,255,0.55)" : MID, lineHeight: 1.8, margin: "18px 0 0", textAlign: center ? "center" : "left", maxWidth: 560 }}>
      {children}
    </p>
  );
}

function SectionDivider() {
  return <div style={{ height: 1, background: BORDER, margin: "0 -24px" }} />;
}

function Sec({ bg = "#fff", py = 72, px = 48, children }) {
  return (
    <section style={{ background: bg, margin: "0 -24px", padding: `${py}px ${px}px` }}>
      {children}
    </section>
  );
}

function Inner({ mw = 960, children }) {
  return <div style={{ maxWidth: mw, margin: "0 auto" }}>{children}</div>;
}

// ─── Hero ─────────────────────────────────────────────────────────────────────

function HeroSection() {
  return (
    <Sec py={80} px={48} bg="#fff">
      <Inner mw={680}>
        <div style={{ textAlign: "center" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 22 }}>
            <FlaskConical size={13} style={{ color: FAINT }} />
            <span style={{ fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase", color: FAINT }}>Research Workspace</span>
          </div>
          <h1 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(2.4rem, 5vw, 3.6rem)", fontWeight: 700, color: NAVY, lineHeight: 1.1, letterSpacing: "-0.035em", margin: "0 0 20px" }}>
            Research without<br />fragmentation.
          </h1>
          <p style={{ fontSize: "1.1rem", color: MID, lineHeight: 1.8, margin: "0 auto 36px", maxWidth: 480 }}>
            One workspace for every stage of your research.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <Link to="/projects" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "13px 26px", background: NAVY, color: "#fff", borderRadius: 10, fontSize: "0.88rem", fontWeight: 700, textDecoration: "none", letterSpacing: "-0.01em" }}>
              Open Research Hub <ArrowRight size={13} />
            </Link>
            <Link to="/workspaces" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "13px 22px", background: "#fff", color: NAVY, border: `1px solid ${BORDER}`, borderRadius: 10, fontSize: "0.88rem", fontWeight: 500, textDecoration: "none" }}>
              Create Workspace
            </Link>
          </div>
        </div>
      </Inner>
    </Sec>
  );
}

// ─── Research Lifecycle ───────────────────────────────────────────────────────

function LifecycleSection() {
  const [active, setActive] = useState(null);
  return (
    <Sec bg={WARM} py={72} px={48}>
      <Inner mw={1100}>
        <Eyebrow text="Stage by stage" />
        <H2>The research lifecycle, connected.</H2>
        <Body>Every stage of the research process links directly to the tools built for it. Nothing lives in isolation.</Body>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8, marginTop: 48 }}>
          {LIFECYCLE.map(function(stage) {
            const Icon = stage.icon;
            const on = active === stage.n;
            return (
              <Link key={stage.n} to={stage.href} style={{ textDecoration: "none" }}
                onMouseEnter={function(){ setActive(stage.n); }}
                onMouseLeave={function(){ setActive(null); }}>
                <div style={{ background: on ? NAVY : "#fff", border: `1px solid ${on ? NAVY : BORDER}`, borderRadius: 12, padding: "18px 16px 16px", transition: "all 160ms", cursor: "pointer", minHeight: 130, display: "flex", flexDirection: "column" }}>
                  <div style={{ fontSize: "0.6rem", fontWeight: 800, letterSpacing: "0.06em", color: on ? "rgba(255,255,255,0.35)" : FAINT, marginBottom: 10 }}>
                    {String(stage.n).padStart(2, "0")}
                  </div>
                  <Icon size={17} strokeWidth={1.5} style={{ color: on ? "#fff" : NAVY, marginBottom: 10, flexShrink: 0 }} />
                  <div style={{ fontSize: "0.8rem", fontWeight: 700, color: on ? "#fff" : "#0f172a", lineHeight: 1.3, marginBottom: on ? 8 : 0 }}>{stage.label}</div>
                  {on && (
                    <div style={{ fontSize: "0.71rem", color: "rgba(255,255,255,0.65)", lineHeight: 1.55, marginTop: "auto" }}>{stage.desc}</div>
                  )}
                </div>
              </Link>
            );
          })}
        </div>
      </Inner>
    </Sec>
  );
}

// ─── Research Modules ─────────────────────────────────────────────────────────

function ModulesSection() {
  return (
    <Sec bg="#fff" py={72} px={48}>
      <Inner mw={1100}>
        <Eyebrow text="Research Modules" />
        <H2>Everything you need to conduct research.</H2>
        <Body>Twelve modules covering every dimension of the research process — from first idea to measured impact.</Body>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", marginTop: 48, border: `1px solid ${BORDER}`, borderRadius: 16, overflow: "hidden" }}>
          {MODULES.map(function(mod, i) {
            const Icon = mod.icon;
            const row = Math.floor(i / 4);
            const col = i % 4;
            const isLastRow = row === Math.floor((MODULES.length - 1) / 4);
            const isLastCol = col === 3;
            return (
              <Link key={mod.label} to={mod.href} style={{ textDecoration: "none" }}>
                <div style={{ padding: "26px 22px", borderRight: isLastCol ? "none" : `1px solid ${BORDER}`, borderBottom: isLastRow ? "none" : `1px solid ${BORDER}`, transition: "background 140ms", background: "#fff" }}
                  onMouseEnter={function(e){ e.currentTarget.style.background = WARM; }}
                  onMouseLeave={function(e){ e.currentTarget.style.background = "#fff"; }}>
                  <Icon size={18} strokeWidth={1.5} style={{ color: NAVY, marginBottom: 14, display: "block" }} />
                  <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#0f172a", marginBottom: 7, lineHeight: 1.3 }}>{mod.label}</div>
                  <div style={{ fontSize: "0.74rem", color: MID, lineHeight: 1.65, marginBottom: 14 }}>{mod.desc}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.71rem", fontWeight: 600, color: NAVY, opacity: 0.6 }}>
                    Open <ArrowRight size={10} />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </Inner>
    </Sec>
  );
}

// ─── Research Workflow ────────────────────────────────────────────────────────

function WorkflowSection() {
  return (
    <section style={{ background: NAVY2, margin: "0 -24px", padding: "80px 48px" }}>
      <Inner mw={1000}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: 80, alignItems: "center" }}>
          {/* Flow diagram */}
          <div>
            {WORKFLOW.map(function(step, i) {
              const isLast = i === WORKFLOW.length - 1;
              return (
                <div key={step.label} style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
                    <div style={{ width: 34, height: 34, borderRadius: "50%", background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.18)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <span style={{ fontSize: "0.62rem", fontWeight: 800, color: "#fff", letterSpacing: "0.02em" }}>{String(i + 1).padStart(2, "0")}</span>
                    </div>
                    {!isLast && <div style={{ width: 1, height: 24, background: "rgba(255,255,255,0.1)", margin: "4px 0" }} />}
                  </div>
                  <div style={{ paddingTop: 7, paddingBottom: isLast ? 0 : 28 }}>
                    <div style={{ fontSize: "0.88rem", fontWeight: 700, color: "#fff", marginBottom: 4, lineHeight: 1.3 }}>{step.label}</div>
                    <div style={{ fontSize: "0.73rem", color: "rgba(255,255,255,0.45)", lineHeight: 1.6 }}>{step.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right: description */}
          <div>
            <div style={{ fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase", color: "rgba(255,255,255,0.3)", marginBottom: 18 }}>Research Workflow</div>
            <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.8rem, 3vw, 2.5rem)", fontWeight: 700, color: "#fff", lineHeight: 1.15, letterSpacing: "-0.025em", margin: "0 0 20px" }}>
              A structured path from idea to impact.
            </h2>
            <p style={{ fontSize: "1rem", color: "rgba(255,255,255,0.5)", lineHeight: 1.8, margin: "0 0 32px" }}>
              Research is not linear, but it has a structure. Synaptiq maps that structure so nothing falls through the gaps between tools, emails and file systems.
            </p>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <Link to="/projects" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "12px 22px", background: "#fff", color: NAVY, borderRadius: 9, fontSize: "0.86rem", fontWeight: 700, textDecoration: "none" }}>
                Start a project <ArrowRight size={13} />
              </Link>
              <Link to="/workspaces" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "12px 18px", background: "transparent", color: "rgba(255,255,255,0.65)", border: "1px solid rgba(255,255,255,0.18)", borderRadius: 9, fontSize: "0.86rem", fontWeight: 500, textDecoration: "none" }}>
                Open Workspace
              </Link>
            </div>
          </div>
        </div>
      </Inner>
    </section>
  );
}

// ─── Researcher Types ────────────────────────────────────────────────────────

function ResearcherTypesSection() {
  return (
    <Sec bg={WARM} py={72} px={48}>
      <Inner mw={1100}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <Eyebrow text="For every researcher" />
          <H2 center>Designed for every stage of an academic career.</H2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          {RESEARCHER_TYPES.map(function(r) {
            const Icon = r.icon;
            return (
              <div key={r.label} style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 12, padding: "24px 20px", transition: "border-color 150ms" }}
                onMouseEnter={function(e){ e.currentTarget.style.borderColor = NAVY; }}
                onMouseLeave={function(e){ e.currentTarget.style.borderColor = BORDER; }}>
                <Icon size={16} strokeWidth={1.5} style={{ color: NAVY, marginBottom: 12, opacity: 0.6 }} />
                <div style={{ fontSize: "0.88rem", fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>{r.label}</div>
                <div style={{ fontSize: "0.76rem", color: MID, lineHeight: 1.65 }}>{r.desc}</div>
              </div>
            );
          })}
        </div>
      </Inner>
    </Sec>
  );
}

// ─── Collaboration ────────────────────────────────────────────────────────────

function CollaborationSection() {
  return (
    <Sec bg="#fff" py={72} px={48}>
      <Inner mw={1000}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 80, alignItems: "start" }}>
          <div>
            <Eyebrow text="Collaboration" />
            <H2>Research is a team effort.</H2>
            <Body>Synaptiq makes it easy to work with anyone, anywhere — whether you are co-authoring with a colleague across the hall or coordinating an international consortium.</Body>
            <Link to="/collaborations" style={{ display: "inline-flex", alignItems: "center", gap: 6, marginTop: 32, padding: "11px 20px", background: NAVY, color: "#fff", borderRadius: 9, fontSize: "0.84rem", fontWeight: 600, textDecoration: "none" }}>
              Open Collaborations <ArrowRight size={13} />
            </Link>
          </div>
          <div>
            {COLLAB_FEATURES.map(function(f, i) {
              const isLast = i === COLLAB_FEATURES.length - 1;
              return (
                <div key={f} style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: `${i === 0 ? 0 : 14}px 0 14px`, borderBottom: isLast ? "none" : `1px solid ${BORDER}` }}>
                  <div style={{ width: 20, height: 20, borderRadius: "50%", background: NAVY + "10", border: `1px solid ${NAVY}20`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
                    <Check size={10} style={{ color: NAVY }} />
                  </div>
                  <span style={{ fontSize: "0.84rem", color: "#374151", lineHeight: 1.6 }}>{f}</span>
                </div>
              );
            })}
          </div>
        </div>
      </Inner>
    </Sec>
  );
}

// ─── Everything Connected ─────────────────────────────────────────────────────

function ConnectedSection() {
  const nodes = [
    { label: "Research Projects",  x: 280, y: 210, r: 48, main: true  },
    { label: "Repository",         x: 100, y: 110, r: 34              },
    { label: "Workspaces",         x: 280, y: 56,  r: 34              },
    { label: "Publications",       x: 460, y: 110, r: 34              },
    { label: "Collaborations",     x: 490, y: 250, r: 32              },
    { label: "Impact",             x: 400, y: 370, r: 30              },
    { label: "Teaching",           x: 180, y: 380, r: 28              },
    { label: "Institution",        x: 64,  y: 290, r: 28              },
    { label: "AI",                 x: 108, y: 210, r: 22, dim: true   },
  ];

  return (
    <Sec bg={WARM} py={72} px={48}>
      <Inner mw={1000}>
        <div style={{ textAlign: "center", marginBottom: 56 }}>
          <Eyebrow text="Connected" />
          <H2 center>Everything connected.</H2>
          <p style={{ fontSize: "1rem", color: MID, lineHeight: 1.8, margin: "18px auto 0", maxWidth: 520 }}>
            Your research does not happen in silos. Every module connects — so your work flows naturally from one stage to the next.
          </p>
        </div>

        <div style={{ display: "flex", justifyContent: "center" }}>
          <svg viewBox="0 0 560 440" width="100%" style={{ maxWidth: 520, overflow: "visible" }}>
            {nodes.slice(1).map(function(n) {
              return (
                <line key={n.label} x1={nodes[0].x} y1={nodes[0].y} x2={n.x} y2={n.y}
                  stroke={n.dim ? "#e2e8f0" : BORDER} strokeWidth={n.dim ? 1 : 1.5} />
              );
            })}
            {nodes.map(function(n) {
              const words = n.label.split(" ");
              const line1 = words[0];
              const line2 = words.slice(1).join(" ");
              return (
                <g key={n.label}>
                  <circle cx={n.x} cy={n.y} r={n.r} fill={n.main ? NAVY : "#fff"} stroke={n.dim ? "#e2e8f0" : n.main ? NAVY : BORDER} strokeWidth={1.5} />
                  <text x={n.x} y={n.y + (line2 ? -4 : 4)} textAnchor="middle" fontSize={n.main ? 9 : 7} fontWeight={n.main ? 700 : 600} fill={n.main ? "#fff" : n.dim ? FAINT : "#374151"}>{line1}</text>
                  {line2 && (
                    <text x={n.x} y={n.y + 8} textAnchor="middle" fontSize={n.main ? 9 : 7} fontWeight={n.main ? 700 : 600} fill={n.main ? "#fff" : n.dim ? FAINT : "#374151"}>{line2}</text>
                  )}
                </g>
              );
            })}
            {/* AI label note */}
            <text x={nodes[8].x} y={nodes[8].y + nodes[8].r + 13} textAnchor="middle" fontSize="6" fill={FAINT}>AI — one of many</text>
          </svg>
        </div>

        <div style={{ display: "flex", justifyContent: "center", gap: 10, marginTop: 32, flexWrap: "wrap" }}>
          {nodes.filter(n => !n.main).map(function(n) {
            return (
              <span key={n.label} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.72rem", color: n.dim ? FAINT : MID }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: n.dim ? "#e2e8f0" : BORDER, display: "inline-block" }} />
                {n.label}
              </span>
            );
          })}
        </div>
      </Inner>
    </Sec>
  );
}

// ─── Research Outcomes ────────────────────────────────────────────────────────

function OutcomesSection() {
  return (
    <Sec bg="#fff" py={72} px={48}>
      <Inner mw={1100}>
        <Eyebrow text="What you get" />
        <H2>Research outcomes that matter.</H2>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", marginTop: 48, border: `1px solid ${BORDER}`, borderRadius: 16, overflow: "hidden" }}>
          {OUTCOMES.map(function(o, i) {
            const row = Math.floor(i / 3);
            const col = i % 3;
            const isLastRow = row === Math.floor((OUTCOMES.length - 1) / 3);
            const isLastCol = col === 2;
            return (
              <div key={o.label} style={{ padding: "28px 26px", borderRight: isLastCol ? "none" : `1px solid ${BORDER}`, borderBottom: isLastRow ? "none" : `1px solid ${BORDER}` }}>
                <div style={{ fontSize: "0.93rem", fontWeight: 700, color: "#0f172a", marginBottom: 10 }}>{o.label}</div>
                <div style={{ fontSize: "0.78rem", color: MID, lineHeight: 1.75 }}>{o.desc}</div>
              </div>
            );
          })}
        </div>
      </Inner>
    </Sec>
  );
}

// ─── CTA ─────────────────────────────────────────────────────────────────────

function CTASection() {
  return (
    <section style={{ background: NAVY2, margin: "0 -24px", padding: "88px 48px" }}>
      <div style={{ maxWidth: 580, margin: "0 auto", textAlign: "center" }}>
        <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.9rem, 4vw, 3rem)", fontWeight: 700, color: "#fff", lineHeight: 1.1, letterSpacing: "-0.03em", margin: "0 0 18px" }}>
          Start your next research project.
        </h2>
        <p style={{ fontSize: "1rem", color: "rgba(255,255,255,0.45)", lineHeight: 1.8, margin: "0 0 40px" }}>
          Every stage of the research lifecycle — in one place. It takes less than a minute to create your first project.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
          <Link to="/projects" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "14px 28px", background: "#fff", color: NAVY, borderRadius: 10, fontSize: "0.9rem", fontWeight: 700, textDecoration: "none", letterSpacing: "-0.01em" }}>
            Create a Project <ArrowRight size={14} />
          </Link>
          <Link to="/workspaces" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "14px 24px", background: "transparent", color: "rgba(255,255,255,0.65)", border: "1px solid rgba(255,255,255,0.18)", borderRadius: 10, fontSize: "0.9rem", fontWeight: 500, textDecoration: "none" }}>
            Open a Workspace
          </Link>
        </div>
      </div>
    </section>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ResearchCommandCenter() {
  return (
    <ResearchLayout title="" subtitle="" actions={null}>
      <HeroSection />
      <SectionDivider />
      <LifecycleSection />
      <SectionDivider />
      <ModulesSection />
      <WorkflowSection />
      <SectionDivider />
      <ResearcherTypesSection />
      <SectionDivider />
      <CollaborationSection />
      <SectionDivider />
      <ConnectedSection />
      <SectionDivider />
      <OutcomesSection />
      <CTASection />
    </ResearchLayout>
  );
}

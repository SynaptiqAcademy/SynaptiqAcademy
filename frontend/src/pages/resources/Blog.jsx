/* eslint-disable */
import React, { useState, useRef, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../../components/layout/MarketingLayout";
import { ArrowRight, Search, Clock, Calendar, Tag, ChevronRight, X, BookOpen, BrainCircuit, Globe, Building2, TrendingUp, Shield, Lightbulb, Layers } from "lucide-react";

const NAVY  = "#0F2847";
const LIGHT = "#f8fafc";
const BORDER= "#e8edf3";

function useReveal(threshold = 0.06) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    if (typeof IntersectionObserver === "undefined") { el.classList.add("sq-in"); return; }
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { el.classList.add("sq-in"); obs.disconnect(); } }, { threshold });
    obs.observe(el); return () => obs.disconnect();
  }, []);
  return ref;
}

const CATEGORIES = [
  { name: "All",         icon: Layers       },
  { name: "AI",         icon: BrainCircuit },
  { name: "Research",   icon: BookOpen     },
  { name: "Teaching",   icon: Building2    },
  { name: "Publishing", icon: Globe        },
  { name: "Innovation", icon: Lightbulb    },
  { name: "Technology", icon: TrendingUp   },
  { name: "Universities",icon: Building2   },
  { name: "Leadership", icon: Tag          },
  { name: "Security",   icon: Shield       },
  { name: "Engineering",icon: Layers       },
];

/* ─── Article data ────────────────────────────────────────────────────────── */
const ARTICLES = [
  {
    id: 1,
    category: "AI",
    title: "The Future of Academic AI: From Assistant to Research Partner",
    summary: "AI in academia has moved from summarization to genuine intellectual assistance. We examine what the next five years look like for AI that truly understands the scientific method.",
    author: "Dr. Sarah Chen",
    role: "Head of AI Research",
    date: "June 28, 2026",
    readTime: "8 min",
    tags: ["AI", "Research", "Future"],
    featured: true,
    color: "#1d4ed8",
    initials: "SC",
  },
  {
    id: 2,
    category: "Research",
    title: "Why Research Collaboration Still Fails — And How to Fix It",
    summary: "Despite digital tools, most cross-institutional collaborations still break down at the coordination layer. We analyzed 1,200 failed research partnerships to find the patterns.",
    author: "Prof. Marcus Weber",
    role: "Research Collaboration Lab",
    date: "June 22, 2026",
    readTime: "11 min",
    tags: ["Collaboration", "Research Teams"],
    featured: false,
    color: "#7c3aed",
    initials: "MW",
  },
  {
    id: 3,
    category: "Publishing",
    title: "The Peer Review Crisis: Data, Causes, and AI-Assisted Solutions",
    summary: "Review turnaround times have doubled in a decade. Reviewer pools are shrinking. We look at the structural causes and how AI-assisted preliminary review can help.",
    author: "Dr. Amara Diallo",
    role: "Publishing Intelligence",
    date: "June 18, 2026",
    readTime: "13 min",
    tags: ["Publishing", "Peer Review", "AI"],
    featured: false,
    color: "#dc2626",
    initials: "AD",
  },
  {
    id: 4,
    category: "Universities",
    title: "Digital Transformation in Research Universities: A 2026 Benchmark",
    summary: "We surveyed 340 research office leaders across 42 countries. Here's what the most digitally mature institutions have in common — and what's holding others back.",
    author: "Ingrid Sörensen",
    role: "Research Strategy",
    date: "June 14, 2026",
    readTime: "15 min",
    tags: ["Digital Transformation", "Institutions", "Analytics"],
    featured: false,
    color: "#059669",
    initials: "IS",
  },
  {
    id: 5,
    category: "AI",
    title: "What Makes an AI Tool Actually Useful for Academic Research?",
    summary: "Generic AI fails in academic contexts for predictable reasons. We break down the 6 dimensions that separate academic-grade AI from consumer-grade AI wrapped in a research skin.",
    author: "Dr. Klaus Mettler",
    role: "Academic Intelligence",
    date: "June 10, 2026",
    readTime: "9 min",
    tags: ["AI", "Academic Integrity", "Research"],
    featured: false,
    color: "#1d4ed8",
    initials: "KM",
  },
  {
    id: 6,
    category: "Research",
    title: "Open Science in 2026: Progress, Gaps, and the Platforms Enabling It",
    summary: "Open access has grown, but reproducibility, data sharing and preprint adoption still lag. This is where the infrastructure bottleneck lies and what it takes to clear it.",
    author: "Prof. Lena Bjork",
    role: "Open Science Initiative",
    date: "June 7, 2026",
    readTime: "10 min",
    tags: ["Open Science", "Reproducibility", "Data"],
    featured: false,
    color: "#0891b2",
    initials: "LB",
  },
  {
    id: 7,
    category: "Leadership",
    title: "The Research VP's Playbook for AI Governance in the Academy",
    summary: "AI is being adopted faster than governance frameworks can keep up. We outline a practical 5-stage governance model for research office leaders.",
    author: "Prof. David Okafor",
    role: "Research Governance",
    date: "June 4, 2026",
    readTime: "12 min",
    tags: ["AI Governance", "Leadership", "Institution"],
    featured: false,
    color: NAVY,
    initials: "DO",
  },
  {
    id: 8,
    category: "Publishing",
    title: "Journal Selection in the Age of AI: How Researchers Should Think About It",
    summary: "Desk rejection rates hit 70%+ at top journals. AI-assisted journal matching is closing that gap — but it requires understanding how editors actually make decisions.",
    author: "Dr. Sofia Romano",
    role: "Publishing Intelligence",
    date: "May 31, 2026",
    readTime: "8 min",
    tags: ["Publishing", "Journal Matching"],
    featured: false,
    color: "#dc2626",
    initials: "SR",
  },
  {
    id: 9,
    category: "Technology",
    title: "Knowledge Graphs in Academic Research: From Theory to Production",
    summary: "Knowledge graphs have been discussed in academia for 20 years. Now they're finally production-ready. We explain what changed and what the practical use cases look like.",
    author: "Dr. Wei Lim",
    role: "Knowledge Engineering",
    date: "May 28, 2026",
    readTime: "14 min",
    tags: ["Knowledge Graph", "Technology", "AI"],
    featured: false,
    color: "#4c1d95",
    initials: "WL",
  },
  {
    id: 10,
    category: "Research",
    title: "Citation Analysis Done Right: Beyond H-Index and Impact Factor",
    summary: "H-index and impact factor are broken metrics — they punish interdisciplinary researchers and incentivize citation cartels. Here are better ways to measure research contribution.",
    author: "Prof. Kenji Watanabe",
    role: "Research Analytics",
    date: "May 24, 2026",
    readTime: "11 min",
    tags: ["Citation Analysis", "Bibliometrics", "Analytics"],
    featured: false,
    color: "#b45309",
    initials: "KW",
  },
  {
    id: 11,
    category: "Teaching",
    title: "Supervising PhD Candidates at Scale: What Actually Works",
    summary: "Supervision quality is the single biggest predictor of PhD completion rates. Yet most universities have no shared infrastructure for it. We look at what the best supervisors do differently.",
    author: "Prof. Hans Richter",
    role: "Doctoral School Director",
    date: "May 20, 2026",
    readTime: "10 min",
    tags: ["Teaching", "PhD", "Supervision"],
    featured: false,
    color: "#c2410c",
    initials: "HR",
  },
  {
    id: 12,
    category: "AI",
    title: "Research Gap Detection: How AI Finds What Human Reviewers Miss",
    summary: "The academic literature is too large for any human to fully survey. AI gap detection doesn't replace expertise — it surfaces the corners of the map that expertise hasn't reached yet.",
    author: "Dr. Amara Diallo",
    role: "AI Research",
    date: "May 17, 2026",
    readTime: "9 min",
    tags: ["AI", "Literature Review", "Research"],
    featured: false,
    color: "#1d4ed8",
    initials: "AD",
  },
  {
    id: 13,
    category: "Security",
    title: "Academic Data Governance in the GDPR Era: A Practical Guide",
    summary: "Research data governance has become a compliance requirement, not just a best practice. This guide covers the 8 areas every research office needs to get right.",
    author: "Dr. Marie Lefevre",
    role: "Research Integrity",
    date: "May 14, 2026",
    readTime: "13 min",
    tags: ["GDPR", "Data Governance", "Compliance"],
    featured: false,
    color: "#374151",
    initials: "ML",
  },
  {
    id: 14,
    category: "Innovation",
    title: "Grant Writing in 2026: The Shift from Prose to Evidence Architecture",
    summary: "Funding agencies are reading AI-assisted applications. The competitive edge has moved from writing quality to evidence architecture — how you structure and trace every claim.",
    author: "Prof. Barnabas Nawangwe",
    role: "Research Strategy",
    date: "May 10, 2026",
    readTime: "10 min",
    tags: ["Grants", "Research Strategy", "Innovation"],
    featured: false,
    color: "#8B4513",
    initials: "BN",
  },
  {
    id: 15,
    category: "Technology",
    title: "The Digital Twin for Research: A New Way to Model Your Academic Trajectory",
    summary: "Digital twins aren't just for engineering. A research digital twin simulates the impact of career decisions before you make them. Here's what that looks like in practice.",
    author: "Dr. Sarah Chen",
    role: "Research Technology",
    date: "May 7, 2026",
    readTime: "11 min",
    tags: ["Digital Twin", "Career", "Technology"],
    featured: false,
    color: "#0891b2",
    initials: "SC",
  },
  {
    id: 16,
    category: "Research",
    title: "Statistical Errors in Academic Papers: How Common, How Fixable",
    summary: "A meta-analysis of 12,000 papers found statistical errors in 38% of published research. Most are fixable at the draft stage. AI-assisted statistical review is changing the pre-submission norm.",
    author: "Prof. Stefan Lindqvist",
    role: "Biostatistics",
    date: "May 3, 2026",
    readTime: "12 min",
    tags: ["Statistics", "Research Integrity", "Methods"],
    featured: false,
    color: "#059669",
    initials: "SL",
  },
  {
    id: 17,
    category: "Universities",
    title: "The Research Office of the Future: From Administrator to Strategic Partner",
    summary: "Research offices that were once administrative support functions are becoming strategic partners in institutional performance. Here's what that transformation requires.",
    author: "Dr. Aoife Murphy",
    role: "Research Strategy",
    date: "April 29, 2026",
    readTime: "9 min",
    tags: ["Research Office", "Strategy", "Institution"],
    featured: false,
    color: "#065f46",
    initials: "AM",
  },
  {
    id: 18,
    category: "AI",
    title: "Multi-Agent AI for Research: How Orchestrated Agents Handle Complex Workflows",
    summary: "Single AI assistants have a ceiling. Multi-agent orchestration doesn't — but it requires a different architecture. We explain how the agent patterns that work in academic research.",
    author: "Dr. Klaus Mettler",
    role: "AI Architecture",
    date: "April 25, 2026",
    readTime: "15 min",
    tags: ["AI Agents", "Technology", "Research"],
    featured: false,
    color: "#1d4ed8",
    initials: "KM",
  },
  {
    id: 19,
    category: "Publishing",
    title: "Open Access Mandates: What They Mean for Your Publication Strategy",
    summary: "Plan S, NIH mandates, Wellcome Trust requirements — open access is no longer optional for most funded research. Here's how to navigate compliance without sacrificing journal quality.",
    author: "Prof. Margaret Thornton",
    role: "Academic Publishing",
    date: "April 21, 2026",
    readTime: "10 min",
    tags: ["Open Access", "Publishing", "Policy"],
    featured: false,
    color: "#dc2626",
    initials: "MT",
  },
  {
    id: 20,
    category: "Leadership",
    title: "Building a Culture of Research Integrity From the Department Level",
    summary: "Institutional integrity programs often fail because they're top-down. The departments that perform best treat integrity as a shared professional norm, not a compliance checkbox.",
    author: "Dr. Marie Lefevre",
    role: "Research Ethics",
    date: "April 18, 2026",
    readTime: "8 min",
    tags: ["Research Integrity", "Culture", "Leadership"],
    featured: false,
    color: NAVY,
    initials: "ML",
  },
  {
    id: 21,
    category: "Innovation",
    title: "The Knowledge Graph as Academic Infrastructure: Lessons from Early Adopters",
    summary: "Three institutions share what they learned deploying production knowledge graphs for research: what worked, what didn't, and what they wish they'd known.",
    author: "Dr. Wei Lim",
    role: "Knowledge Infrastructure",
    date: "April 14, 2026",
    readTime: "13 min",
    tags: ["Knowledge Graph", "Innovation", "Infrastructure"],
    featured: false,
    color: "#4c1d95",
    initials: "WL",
  },
  {
    id: 22,
    category: "Research",
    title: "International Research Consortia: A Legal and Operational Playbook",
    summary: "Multi-country research consortia are complex to form and costly to manage badly. This operational guide covers consortium agreements, IP ownership, and governance structures.",
    author: "Prof. Ingrid Sörensen",
    role: "Research Partnerships",
    date: "April 10, 2026",
    readTime: "16 min",
    tags: ["Consortium", "Research Strategy", "Legal"],
    featured: false,
    color: "#0891b2",
    initials: "IS",
  },
  {
    id: 23,
    category: "Teaching",
    title: "Teaching with AI: What Academic Honesty Actually Requires Now",
    summary: "Academic honesty policies written in 2020 don't cover 2026 AI tools. We look at what universities getting this right are actually doing — and what the wrong approaches look like.",
    author: "Prof. Hans Richter",
    role: "Academic Ethics",
    date: "April 6, 2026",
    readTime: "11 min",
    tags: ["Teaching", "AI", "Academic Integrity"],
    featured: false,
    color: "#c2410c",
    initials: "HR",
  },
  {
    id: 24,
    category: "Technology",
    title: "RAG for Research: How Retrieval-Augmented Generation Changes Academic AI",
    summary: "RAG is the reason academic AI is finally reliable. By grounding responses in your own literature, it eliminates the hallucination problem that made earlier AI tools unusable in research.",
    author: "Dr. Sarah Chen",
    role: "AI Research",
    date: "April 2, 2026",
    readTime: "12 min",
    tags: ["RAG", "AI", "Technology"],
    featured: false,
    color: "#4c1d95",
    initials: "SC",
  },
  {
    id: 25,
    category: "Universities",
    title: "Research Excellence Frameworks: How to Prepare Without Gaming Them",
    summary: "REF, ERA, and national research evaluation schemes create perverse incentives. The institutions that perform best don't game them — they align their genuine strengths with the criteria.",
    author: "Dr. David Okafor",
    role: "Research Strategy",
    date: "March 28, 2026",
    readTime: "10 min",
    tags: ["REF", "Research Strategy", "Universities"],
    featured: false,
    color: "#065f46",
    initials: "DO",
  },
  {
    id: 26,
    category: "AI",
    title: "Evidence-Based AI: Why Academic AI Must Cite Its Sources",
    summary: "AI that generates plausible-sounding academic content without citations is worse than useless — it's dangerous. Here's how evidence-grounded AI works and why it's the only acceptable standard.",
    author: "Dr. Amara Diallo",
    role: "AI Ethics",
    date: "March 24, 2026",
    readTime: "9 min",
    tags: ["AI Ethics", "Evidence", "Academic Integrity"],
    featured: false,
    color: "#1d4ed8",
    initials: "AD",
  },
  {
    id: 27,
    category: "Research",
    title: "Preprint Culture: How arXiv, bioRxiv and SSRN Are Changing Academic Publishing",
    summary: "Preprints are accelerating science — but they're also introducing new risks around premature citations and media amplification of non-peer-reviewed findings.",
    author: "Prof. Marcus Weber",
    role: "Science Publishing",
    date: "March 20, 2026",
    readTime: "10 min",
    tags: ["Preprints", "Publishing", "Open Science"],
    featured: false,
    color: "#7c3aed",
    initials: "MW",
  },
  {
    id: 28,
    category: "Innovation",
    title: "Academic Marketplaces: The Rise of Verified Expert Services for Research",
    summary: "Statistical consulting, peer review, translation and editing are increasingly available through verified academic marketplaces. We look at how this market is developing and what it means for research quality.",
    author: "Dr. Sofia Romano",
    role: "Research Services",
    date: "March 16, 2026",
    readTime: "9 min",
    tags: ["Marketplace", "Research Services", "Innovation"],
    featured: false,
    color: "#d97706",
    initials: "SR",
  },
  {
    id: 29,
    category: "Security",
    title: "Zero Trust for Research Infrastructure: Why Academic Networks Need a Rethink",
    summary: "Research institutions are high-value targets for nation-state actors and IP theft. Classic perimeter security doesn't work for distributed, international research teams.",
    author: "Dr. Marie Lefevre",
    role: "Cybersecurity",
    date: "March 12, 2026",
    readTime: "13 min",
    tags: ["Security", "Zero Trust", "Infrastructure"],
    featured: false,
    color: "#374151",
    initials: "ML",
  },
  {
    id: 30,
    category: "Leadership",
    title: "The Case for Research-First Culture in Teaching-Intensive Universities",
    summary: "Teaching-intensive institutions often treat research as secondary. The evidence suggests this is a false trade-off — research activity improves teaching quality and student outcomes.",
    author: "Prof. Barnabas Nawangwe",
    role: "Academic Leadership",
    date: "March 8, 2026",
    readTime: "8 min",
    tags: ["Leadership", "Research Culture", "Teaching"],
    featured: false,
    color: NAVY,
    initials: "BN",
  },
  {
    id: 31,
    category: "Technology",
    title: "Embeddings, Vectors and Semantic Search: An Academic Primer",
    summary: "Vector search is powering the new generation of academic tools. This primer explains the technology in terms that are useful for research administrators and faculty who want to evaluate AI tools.",
    author: "Dr. Wei Lim",
    role: "AI Technology",
    date: "March 4, 2026",
    readTime: "11 min",
    tags: ["Technology", "AI", "Search"],
    featured: false,
    color: "#4c1d95",
    initials: "WL",
  },
  {
    id: 32,
    category: "Research",
    title: "Data Management Plans: From Compliance Burden to Research Asset",
    summary: "DMPs are required by most funders but treated as a compliance formality. The institutions that treat them as live research assets get more value from their data and win more grants.",
    author: "Dr. Lena Bjork",
    role: "Research Data",
    date: "February 28, 2026",
    readTime: "9 min",
    tags: ["Data Management", "Research", "Compliance"],
    featured: false,
    color: "#0891b2",
    initials: "LB",
  },
  {
    id: 33,
    category: "Publishing",
    title: "How to Write a Cover Letter That Actually Gets Read by Journal Editors",
    summary: "Cover letters are read in 60 seconds or less. We analyzed what journal editors are looking for and what makes them reach for the reject button before reading the abstract.",
    author: "Dr. Sofia Romano",
    role: "Publishing Intelligence",
    date: "February 24, 2026",
    readTime: "7 min",
    tags: ["Publishing", "Cover Letter", "Journals"],
    featured: false,
    color: "#dc2626",
    initials: "SR",
  },
  {
    id: 34,
    category: "AI",
    title: "Proactive AI: The Shift from Tool to Research Companion",
    summary: "Reactive AI answers questions. Proactive AI knows when to surface insights before you ask. This architectural shift is what separates the next generation of academic AI tools.",
    author: "Dr. Klaus Mettler",
    role: "AI Product",
    date: "February 20, 2026",
    readTime: "10 min",
    tags: ["AI", "Proactive AI", "Research"],
    featured: false,
    color: "#1d4ed8",
    initials: "KM",
  },
  {
    id: 35,
    category: "Universities",
    title: "Benchmarking Research Performance Across Disciplines: What Metrics Actually Work",
    summary: "Cross-disciplinary benchmarking is notoriously difficult — publication rates, citation norms and collaboration patterns vary enormously. We propose a composite metric framework that holds up.",
    author: "Assoc. Prof. Lim Wei",
    role: "Research Analytics",
    date: "February 16, 2026",
    readTime: "14 min",
    tags: ["Benchmarking", "Analytics", "Universities"],
    featured: false,
    color: "#003D7C",
    initials: "LW",
  },
  {
    id: 36,
    category: "Engineering",
    title: "How We Built the Synaptiq Event Bus: Enterprise Messaging for Academic Infrastructure",
    summary: "Academic platforms have unique messaging requirements — eventual consistency, compliance audit trails, and multi-institution event routing. Here's the architectural decisions we made.",
    author: "Engineering Team",
    role: "Synaptiq Engineering",
    date: "February 12, 2026",
    readTime: "16 min",
    tags: ["Engineering", "Architecture", "Technology"],
    featured: false,
    color: "#475569",
    initials: "ET",
  },
  {
    id: 37,
    category: "Innovation",
    title: "Science Diplomacy and Research Infrastructure: How Platform Choices Shape International Collaboration",
    summary: "The platforms researchers use shape which collaborations form. Infrastructure is politics — and the decisions made at the IT procurement level have geopolitical consequences.",
    author: "Prof. David Okafor",
    role: "Science Policy",
    date: "February 8, 2026",
    readTime: "12 min",
    tags: ["Science Policy", "Innovation", "Global Research"],
    featured: false,
    color: "#8B4513",
    initials: "DO",
  },
  {
    id: 38,
    category: "Security",
    title: "GDPR Article 17 and Research Data: The Right to Erasure in Academic Contexts",
    summary: "Article 17 exemptions for scientific research are frequently misunderstood. We break down exactly when they apply, when they don't, and how to build compliant data retention policies.",
    author: "Dr. Marie Lefevre",
    role: "Data Protection",
    date: "February 4, 2026",
    readTime: "11 min",
    tags: ["GDPR", "Security", "Data Governance"],
    featured: false,
    color: "#374151",
    initials: "ML",
  },
  {
    id: 39,
    category: "Teaching",
    title: "Research-Informed Teaching: How Active Researchers Build Better Courses",
    summary: "Courses taught by active researchers consistently outperform those that aren't — on student outcomes, graduate employment, and student satisfaction. Here's the mechanism and what it requires.",
    author: "Prof. Ingrid Sörensen",
    role: "Academic Development",
    date: "January 30, 2026",
    readTime: "9 min",
    tags: ["Teaching", "Research", "Pedagogy"],
    featured: false,
    color: "#c2410c",
    initials: "IS",
  },
  {
    id: 40,
    category: "Research",
    title: "The Reproducibility Crisis in 2026: Progress Made, Problems Remaining",
    summary: "The reproducibility crisis is real but unevenly distributed. Some fields have made genuine progress; others have barely engaged. A field-by-field update on where things stand.",
    author: "Prof. Stefan Lindqvist",
    role: "Research Methodology",
    date: "January 26, 2026",
    readTime: "13 min",
    tags: ["Reproducibility", "Research Methods", "Science"],
    featured: false,
    color: "#059669",
    initials: "SL",
  },
];

const PAGE_SIZE = 9;

/* ─── Article card ────────────────────────────────────────────────────────── */
function ArticleCard({ article }) {
  return (
    <div style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 16, overflow: "hidden", display: "flex", flexDirection: "column",
      transition: "box-shadow 200ms, transform 200ms" }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 8px 32px rgba(15,40,71,0.08)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "none"; }}
    >
      {/* Color band */}
      <div style={{ height: 5, background: article.color }} />
      <div style={{ padding: "22px 24px", flex: 1, display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <span style={{ fontSize: "0.62rem", fontWeight: 700, color: article.color, background: `${article.color}12`, border: `1px solid ${article.color}20`, padding: "2px 9px", borderRadius: 20 }}>{article.category}</span>
          <span style={{ fontSize: "0.65rem", color: "#94a3b8", display: "flex", alignItems: "center", gap: 3 }}><Clock size={10} strokeWidth={1.5} />{article.readTime}</span>
        </div>
        <h3 style={{ fontSize: "0.92rem", fontWeight: 800, color: "#0a0f1a", lineHeight: 1.4, marginBottom: 10, textWrap: "balance" }}>{article.title}</h3>
        <p style={{ fontSize: "0.78rem", color: "#64748b", lineHeight: 1.7, marginBottom: 18, flex: 1 }}>{article.summary}</p>

        {/* Author */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, paddingTop: 14, borderTop: `1px solid ${BORDER}` }}>
          <div style={{ width: 30, height: 30, borderRadius: "50%", background: article.color, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <span style={{ fontSize: "0.55rem", fontWeight: 800, color: "#fff" }}>{article.initials}</span>
          </div>
          <div>
            <div style={{ fontSize: "0.74rem", fontWeight: 700, color: "#0a0f1a" }}>{article.author}</div>
            <div style={{ fontSize: "0.64rem", color: "#94a3b8" }}>{article.date}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Featured article ────────────────────────────────────────────────────── */
function FeaturedArticle({ article }) {
  const ref = useReveal();
  return (
    <div ref={ref} className="sq-reveal" style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 20, overflow: "hidden", boxShadow: "0 4px 24px rgba(0,0,0,0.05)" }}>
      <div className="grid lg:grid-cols-[1fr_420px]">
        <div style={{ padding: "48px 48px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.65rem", fontWeight: 700, color: article.color, background: `${article.color}12`, border: `1px solid ${article.color}20`, padding: "3px 10px", borderRadius: 20 }}>Featured · {article.category}</span>
            <span style={{ fontSize: "0.65rem", color: "#94a3b8", display: "flex", alignItems: "center", gap: 4 }}><Clock size={10} strokeWidth={1.5} />{article.readTime} read</span>
            <span style={{ fontSize: "0.65rem", color: "#94a3b8", display: "flex", alignItems: "center", gap: 4 }}><Calendar size={10} strokeWidth={1.5} />{article.date}</span>
          </div>
          <h2 style={{ fontSize: "clamp(1.4rem, 2.5vw, 2.1rem)", fontWeight: 900, letterSpacing: "-0.03em", color: "#0a0f1a", lineHeight: 1.2, marginBottom: 16, textWrap: "balance" }}>{article.title}</h2>
          <p style={{ fontSize: "0.9rem", color: "#475569", lineHeight: 1.8, marginBottom: 28 }}>{article.summary}</p>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: "50%", background: article.color, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ fontSize: "0.62rem", fontWeight: 800, color: "#fff" }}>{article.initials}</span>
            </div>
            <div>
              <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#0a0f1a" }}>{article.author}</div>
              <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>{article.role}</div>
            </div>
          </div>
        </div>
        {/* Right — visual placeholder */}
        <div style={{ background: `${article.color}08`, display: "flex", alignItems: "center", justifyContent: "center", padding: 48, borderLeft: `1px solid ${BORDER}` }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ width: 80, height: 80, borderRadius: 20, background: `${article.color}15`, border: `2px solid ${article.color}25`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px" }}>
              <BrainCircuit size={36} strokeWidth={1} style={{ color: article.color }} />
            </div>
            <div style={{ fontSize: "0.75rem", color: "#94a3b8", maxWidth: 220, lineHeight: 1.6 }}>Deep research on AI and the future of academic collaboration</div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Newsletter block ────────────────────────────────────────────────────── */
function NewsletterBlock() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  return (
    <div style={{ background: NAVY, borderRadius: 16, padding: "32px 36px", margin: "32px 0" }}>
      {submitted ? (
        <div style={{ textAlign: "center", color: "rgba(255,255,255,0.7)", fontSize: "0.9rem" }}>You're in. Welcome to the Synaptiq Research Digest.</div>
      ) : (
        <>
          <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.3)", marginBottom: 10 }}>Research Digest</div>
          <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "#fff", marginBottom: 8, letterSpacing: "-0.02em" }}>Get weekly insights on academic AI and research.</h3>
          <p style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.45)", marginBottom: 18 }}>No spam. Unsubscribe anytime. Join 14,000+ research professionals.</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input value={email} onChange={e => setEmail(e.target.value)} placeholder="your@institution.edu"
              style={{ flex: 1, minWidth: 200, background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, padding: "10px 14px", color: "#fff", fontSize: "0.83rem", outline: "none" }}
            />
            <button onClick={() => { if (email.includes("@")) setSubmitted(true); }}
              style={{ background: "#fff", color: NAVY, padding: "10px 20px", borderRadius: 8, fontWeight: 700, fontSize: "0.83rem", border: "none", cursor: "pointer" }}>
              Subscribe
            </button>
          </div>
        </>
      )}
    </div>
  );
}

/* ─── Page ─────────────────────────────────────────────────────────────────── */
export default function Blog() {
  useEffect(() => {
    document.title = "Blog — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const [activeCategory, setActiveCategory] = useState("All");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const rGrid = useReveal();

  const featured = ARTICLES.find(a => a.featured);
  const rest = ARTICLES.filter(a => !a.featured);

  const filtered = useMemo(() => {
    return rest.filter(a => {
      const matchCat    = activeCategory === "All" || a.category === activeCategory;
      const matchSearch = search === "" || a.title.toLowerCase().includes(search.toLowerCase()) || a.summary.toLowerCase().includes(search.toLowerCase()) || a.tags.some(t => t.toLowerCase().includes(search.toLowerCase()));
      return matchCat && matchSearch;
    });
  }, [activeCategory, search, rest]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // Reset to page 1 on filter change
  useEffect(() => { setPage(1); }, [activeCategory, search]);

  return (
    <MarketingLayout>

      {/* Hero */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, paddingTop: 72, paddingBottom: 64 }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 16 }}>Resources</div>
          <div className="grid lg:grid-cols-2 gap-8 items-end">
            <div>
              <h1 style={{ fontSize: "clamp(2.8rem, 6vw, 5rem)", fontWeight: 900, letterSpacing: "-0.045em", color: "#0a0f1a", lineHeight: 1.0, marginBottom: 18 }}>
                Tools &amp; Ideas
              </h1>
              <p style={{ fontSize: "1rem", color: "#64748b", lineHeight: 1.75, maxWidth: 440 }}>
                Insights on AI, research, higher education, digital transformation, academic publishing and the future of science.
              </p>
            </div>
            {/* Search */}
            <div>
              <div style={{ background: LIGHT, border: `1px solid ${BORDER}`, borderRadius: 12, padding: "12px 16px", display: "flex", alignItems: "center", gap: 10, maxWidth: 400, marginLeft: "auto" }}>
                <Search size={16} strokeWidth={1.5} style={{ color: "#94a3b8", flexShrink: 0 }} />
                <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search articles, topics, authors…"
                  style={{ border: "none", background: "transparent", outline: "none", fontSize: "0.87rem", color: "#0a0f1a", width: "100%" }}
                />
                {search && <button onClick={() => setSearch("")} style={{ border: "none", background: "none", cursor: "pointer", color: "#94a3b8" }}><X size={14} /></button>}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Featured */}
      <section style={{ background: LIGHT, borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-16 lg:py-20">
          {featured && <FeaturedArticle article={featured} />}
        </div>
      </section>

      {/* Main — sidebar + grid */}
      <section style={{ background: "#fff" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-16 lg:py-20">
          <div className="grid lg:grid-cols-[220px_1fr] gap-12">

            {/* Left sidebar */}
            <aside>
              <div style={{ position: "sticky", top: 80 }}>
                <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 14 }}>Categories</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {CATEGORIES.map(({ name, icon: Icon }) => {
                    const count = name === "All" ? rest.length : rest.filter(a => a.category === name).length;
                    const active = activeCategory === name;
                    return (
                      <button key={name} onClick={() => setActiveCategory(name)}
                        style={{
                          display: "flex", alignItems: "center", gap: 10, padding: "9px 12px", borderRadius: 8,
                          background: active ? NAVY : "transparent", color: active ? "#fff" : "#64748b",
                          border: "none", cursor: "pointer", transition: "all 150ms", textAlign: "left",
                          fontSize: "0.82rem", fontWeight: active ? 700 : 500,
                        }}
                      >
                        <Icon size={13} strokeWidth={1.5} style={{ flexShrink: 0 }} />
                        <span style={{ flex: 1 }}>{name}</span>
                        <span style={{ fontSize: "0.65rem", opacity: 0.5 }}>{count}</span>
                      </button>
                    );
                  })}
                </div>

                <NewsletterBlock />
              </div>
            </aside>

            {/* Right — articles */}
            <div>
              {/* Results info */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24, flexWrap: "wrap", gap: 8 }}>
                <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>
                  {filtered.length} article{filtered.length !== 1 ? "s" : ""}
                  {activeCategory !== "All" && ` in ${activeCategory}`}
                  {search && ` matching "${search}"`}
                </div>
                {(search || activeCategory !== "All") && (
                  <button onClick={() => { setSearch(""); setActiveCategory("All"); }}
                    style={{ fontSize: "0.75rem", color: NAVY, fontWeight: 700, border: "none", background: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
                    <X size={12} /> Clear filters
                  </button>
                )}
              </div>

              {paginated.length > 0 ? (
                <>
                  <div ref={rGrid} className="sq-reveal grid sm:grid-cols-2 xl:grid-cols-3 gap-6">
                    {paginated.map(article => <ArticleCard key={article.id} article={article} />)}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 48 }}>
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                        <button key={p} onClick={() => setPage(p)}
                          style={{
                            width: 38, height: 38, borderRadius: 9, fontSize: "0.82rem", fontWeight: 700, cursor: "pointer", border: "1px solid",
                            background: page === p ? NAVY : "#fff", color: page === p ? "#fff" : "#64748b", borderColor: page === p ? NAVY : BORDER,
                            transition: "all 150ms",
                          }}
                        >{p}</button>
                      ))}
                      {page < totalPages && (
                        <button onClick={() => setPage(p => p + 1)}
                          style={{ display: "flex", alignItems: "center", gap: 4, padding: "0 14px", height: 38, borderRadius: 9, border: `1px solid ${BORDER}`, background: "#fff", color: "#64748b", fontSize: "0.82rem", fontWeight: 600, cursor: "pointer" }}>
                          Next <ChevronRight size={14} />
                        </button>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div style={{ textAlign: "center", padding: "64px 0" }}>
                  <div style={{ fontSize: "2rem", marginBottom: 16, opacity: 0.2 }}>📝</div>
                  <div style={{ fontSize: "0.92rem", fontWeight: 600, color: "#64748b" }}>No articles found.</div>
                  <button onClick={() => { setSearch(""); setActiveCategory("All"); }}
                    style={{ marginTop: 16, fontSize: "0.82rem", color: NAVY, fontWeight: 700, border: "none", background: "none", cursor: "pointer" }}>
                    Clear filters
                  </button>
                </div>
              )}
            </div>

          </div>
        </div>
      </section>

    </MarketingLayout>
  );
}

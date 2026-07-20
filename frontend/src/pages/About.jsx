/* eslint-disable */
import React, { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import {
  ArrowRight, Users, BrainCircuit, FileText, BarChart3, Globe, Shield,
  Network, Briefcase, GraduationCap, FlaskConical, Building2, Star,
  BookOpen, Microscope, CheckCircle2, Sparkles, Target, Award,
  Layers, Lock, Heart, Lightbulb, Eye, Handshake,
} from "lucide-react";

/* ─── reveal hook ──────────────────────────────────────────────────────────── */
function useReveal(threshold = 0.07) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    if (typeof IntersectionObserver === "undefined") { el.classList.add("sq-in"); return; }
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { el.classList.add("sq-in"); obs.disconnect(); } }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return ref;
}

/* ─── counter hook ─────────────────────────────────────────────────────────── */
function useCounter(target, duration = 1800) {
  const [value, setValue] = useState(0);
  const [started, setStarted] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting && !started) { setStarted(true); obs.disconnect(); } }, { threshold: 0.5 });
    obs.observe(el); return () => obs.disconnect();
  }, [started]);
  useEffect(() => {
    if (!started) return;
    let start = null;
    const step = (ts) => { if (!start) start = ts; const p = Math.min((ts - start) / duration, 1); const ease = 1 - Math.pow(1 - p, 3); setValue(Math.round(ease * target)); if (p < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }, [started, target, duration]);
  return { ref, value };
}

/* ══════════════════ ILLUSTRATIONS ══════════════════════════════════════════ */

/* Hero: researcher network globe */
function IllusHero() {
  return (
    <svg viewBox="0 0 440 380" style={{ width: "100%", maxWidth: 440, height: "auto" }} aria-hidden="true">
      {/* Globe outline */}
      <circle cx="220" cy="190" r="130" fill="none" stroke="#0F2847" strokeWidth="1.5" opacity="0.12" />
      <circle cx="220" cy="190" r="130" fill="none" stroke="#0F2847" strokeWidth="1" opacity="0.08" strokeDasharray="3 5" />
      {/* Globe meridians */}
      <ellipse cx="220" cy="190" rx="60" ry="130" fill="none" stroke="#0F2847" strokeWidth="1" opacity="0.1" />
      <ellipse cx="220" cy="190" rx="110" ry="130" fill="none" stroke="#0F2847" strokeWidth="1" opacity="0.1" />
      {/* Globe parallels */}
      <ellipse cx="220" cy="140" rx="113" ry="22" fill="none" stroke="#0F2847" strokeWidth="0.8" opacity="0.1" />
      <ellipse cx="220" cy="190" rx="130" ry="26" fill="none" stroke="#0F2847" strokeWidth="0.8" opacity="0.1" />
      <ellipse cx="220" cy="240" rx="113" ry="22" fill="none" stroke="#0F2847" strokeWidth="0.8" opacity="0.1" />

      {/* Connection lines between nodes */}
      <line x1="220" y1="190" x2="100" y2="120" stroke="#0F2847" strokeWidth="1" opacity="0.25" strokeDasharray="3 3" />
      <line x1="220" y1="190" x2="340" y2="110" stroke="#0F2847" strokeWidth="1" opacity="0.25" strokeDasharray="3 3" />
      <line x1="220" y1="190" x2="360" y2="250" stroke="#0F2847" strokeWidth="1" opacity="0.25" strokeDasharray="3 3" />
      <line x1="220" y1="190" x2="100" y2="270" stroke="#0F2847" strokeWidth="1" opacity="0.25" strokeDasharray="3 3" />
      <line x1="220" y1="190" x2="220" y2="70" stroke="#0F2847" strokeWidth="1" opacity="0.2" strokeDasharray="3 3" />
      <line x1="100" y1="120" x2="340" y2="110" stroke="#0F2847" strokeWidth="0.7" opacity="0.15" strokeDasharray="2 4" />
      <line x1="340" y1="110" x2="360" y2="250" stroke="#0F2847" strokeWidth="0.7" opacity="0.15" strokeDasharray="2 4" />

      {/* Center node — AI core */}
      <circle cx="220" cy="190" r="28" fill="#0F2847" />
      <text x="220" y="186" textAnchor="middle" style={{ fontSize: 10, fill: "#fff", fontWeight: 700, fontFamily: "system-ui" }}>AI</text>
      <text x="220" y="198" textAnchor="middle" style={{ fontSize: 7, fill: "rgba(255,255,255,0.6)", fontFamily: "system-ui" }}>Synaptiq</text>

      {/* Researcher nodes */}
      {[
        { cx: 100, cy: 120, label: "Oxford",    sub: "Prof. M.", fill: "#0F2847" },
        { cx: 340, cy: 110, label: "MIT",        sub: "Dr. K.",  fill: "#1e3a5f" },
        { cx: 360, cy: 250, label: "ETH",        sub: "Dr. I.",  fill: "#0F2847" },
        { cx: 100, cy: 270, label: "Kyoto",      sub: "Prof. S.",fill: "#1e3a5f" },
        { cx: 220, cy: 68,  label: "CNRS",       sub: "Dr. M.",  fill: "#0F2847" },
      ].map(({ cx, cy, label, sub, fill }) => (
        <g key={label}>
          <circle cx={cx} cy={cy} r="24" fill={fill} />
          <text x={cx} y={cy - 1} textAnchor="middle" style={{ fontSize: 7, fill: "#fff", fontWeight: 700, fontFamily: "system-ui" }}>{label}</text>
          <text x={cx} y={cy + 9} textAnchor="middle" style={{ fontSize: 6, fill: "rgba(255,255,255,0.6)", fontFamily: "system-ui" }}>{sub}</text>
        </g>
      ))}

      {/* Floating paper/book elements */}
      {/* Book top-left */}
      <g transform="translate(28,60)">
        <rect x="0" y="0" width="34" height="44" rx="3" fill="none" stroke="#0F2847" strokeWidth="1.5" />
        <line x1="6" y1="8" x2="28" y2="8" stroke="#0F2847" strokeWidth="1" opacity="0.5" />
        <line x1="6" y1="14" x2="28" y2="14" stroke="#0F2847" strokeWidth="1" opacity="0.5" />
        <line x1="6" y1="20" x2="22" y2="20" stroke="#0F2847" strokeWidth="1" opacity="0.5" />
        <line x1="4" y1="0" x2="4" y2="44" stroke="#0F2847" strokeWidth="2" opacity="0.3" />
      </g>

      {/* DNA / formula top-right */}
      <g transform="translate(380,45)">
        <text style={{ fontSize: 18, fill: "#0F2847", fontFamily: "serif", opacity: 0.4 }}>∑</text>
      </g>

      {/* Paper bottom-right */}
      <g transform="translate(380,290)">
        <rect x="0" y="0" width="36" height="46" rx="2" fill="none" stroke="#0F2847" strokeWidth="1.5" />
        <line x1="5" y1="9" x2="31" y2="9" stroke="#0F2847" strokeWidth="1" opacity="0.4" />
        <line x1="5" y1="15" x2="31" y2="15" stroke="#0F2847" strokeWidth="1" opacity="0.4" />
        <line x1="5" y1="21" x2="24" y2="21" stroke="#0F2847" strokeWidth="1" opacity="0.4" />
        <line x1="5" y1="27" x2="29" y2="27" stroke="#0F2847" strokeWidth="1" opacity="0.4" />
        {/* Checkmark */}
        <circle cx="28" cy="38" r="7" fill="#10b981" opacity="0.8" />
        <polyline points="25,38 27,40 31,35" fill="none" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
      </g>

      {/* Microscope bottom-left */}
      <g transform="translate(20,290)" opacity="0.4">
        <line x1="18" y1="0" x2="18" y2="36" stroke="#0F2847" strokeWidth="2" strokeLinecap="round" />
        <ellipse cx="18" cy="6" rx="10" ry="6" fill="none" stroke="#0F2847" strokeWidth="1.5" />
        <line x1="8" y1="36" x2="28" y2="36" stroke="#0F2847" strokeWidth="2" strokeLinecap="round" />
        <line x1="13" y1="36" x2="13" y2="44" stroke="#0F2847" strokeWidth="2" strokeLinecap="round" />
        <line x1="23" y1="36" x2="23" y2="44" stroke="#0F2847" strokeWidth="2" strokeLinecap="round" />
      </g>

      {/* Small ping dots */}
      {[[155, 155], [285, 155], [285, 230], [155, 230]].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="3" fill="#0F2847" opacity="0.2" />
      ))}
    </svg>
  );
}

/* Section 1 — The Problem */
function IllusProblem() {
  return (
    <svg viewBox="0 0 360 300" style={{ width: "100%", maxWidth: 360, height: "auto" }} aria-hidden="true">
      {/* Researcher at desk */}
      <g transform="translate(30,40)">
        {/* Desk */}
        <rect x="0" y="180" width="300" height="6" rx="2" fill="#0F2847" opacity="0.15" />
        {/* Monitor */}
        <rect x="80" y="110" width="140" height="90" rx="4" fill="none" stroke="#0F2847" strokeWidth="2" />
        <rect x="80" y="110" width="140" height="70" rx="4" fill="#f8fafc" stroke="#0F2847" strokeWidth="2" />
        <line x1="150" y1="180" x2="150" y2="186" stroke="#0F2847" strokeWidth="2" />
        <rect x="130" y="186" width="40" height="4" rx="1" fill="#0F2847" opacity="0.2" />
        {/* Screen content — fragmented tabs */}
        <rect x="86" y="116" width="28" height="10" rx="2" fill="#e2e8f0" />
        <rect x="118" y="116" width="28" height="10" rx="2" fill="#e2e8f0" />
        <rect x="150" y="116" width="28" height="10" rx="2" fill="#e2e8f0" />
        <rect x="182" y="116" width="30" height="10" rx="2" fill="#fecaca" />
        {/* Email icon */}
        <rect x="90" y="132" width="32" height="22" rx="2" fill="none" stroke="#0F2847" strokeWidth="1" opacity="0.5" />
        <polyline points="90,132 106,146 122,132" fill="none" stroke="#0F2847" strokeWidth="1" opacity="0.5" />
        {/* Spreadsheet icon */}
        <rect x="132" y="132" width="30" height="22" rx="2" fill="#f0fdf4" stroke="#16a34a" strokeWidth="1" opacity="0.6" />
        <line x1="142" y1="132" x2="142" y2="154" stroke="#16a34a" strokeWidth="0.8" opacity="0.5" />
        <line x1="152" y1="132" x2="152" y2="154" stroke="#16a34a" strokeWidth="0.8" opacity="0.5" />
        <line x1="132" y1="142" x2="162" y2="142" stroke="#16a34a" strokeWidth="0.8" opacity="0.5" />
        {/* Doc icon */}
        <rect x="170" y="132" width="28" height="22" rx="2" fill="#fef9f0" stroke="#f59e0b" strokeWidth="1" opacity="0.6" />
        <line x1="175" y1="138" x2="193" y2="138" stroke="#f59e0b" strokeWidth="0.8" opacity="0.5" />
        <line x1="175" y1="143" x2="193" y2="143" stroke="#f59e0b" strokeWidth="0.8" opacity="0.5" />
        <line x1="175" y1="148" x2="188" y2="148" stroke="#f59e0b" strokeWidth="0.8" opacity="0.5" />

        {/* Person silhouette */}
        <circle cx="30" cy="120" r="16" fill="none" stroke="#0F2847" strokeWidth="2" />
        <line x1="30" y1="136" x2="30" y2="178" stroke="#0F2847" strokeWidth="2" strokeLinecap="round" />
        <line x1="30" y1="148" x2="12" y2="164" stroke="#0F2847" strokeWidth="2" strokeLinecap="round" />
        <line x1="30" y1="148" x2="48" y2="164" stroke="#0F2847" strokeWidth="2" strokeLinecap="round" />
        <line x1="30" y1="178" x2="14" y2="200" stroke="#0F2847" strokeWidth="2" strokeLinecap="round" />
        <line x1="30" y1="178" x2="46" y2="200" stroke="#0F2847" strokeWidth="2" strokeLinecap="round" />
        {/* Question mark above head */}
        <text x="48" y="110" style={{ fontSize: 20, fill: "#0F2847", fontFamily: "serif", fontWeight: 700 }} opacity="0.4">?</text>
      </g>

      {/* Scattered tools around — fragmentation icons */}
      {/* Slack bubble */}
      <g transform="translate(270,20)" opacity="0.35">
        <rect x="0" y="0" width="56" height="36" rx="8" fill="none" stroke="#0F2847" strokeWidth="1.5" />
        <line x1="8" y1="12" x2="48" y2="12" stroke="#0F2847" strokeWidth="1.2" />
        <line x1="8" y1="20" x2="36" y2="20" stroke="#0F2847" strokeWidth="1.2" />
        <polygon points="10,36 18,28 28,28" fill="none" stroke="#0F2847" strokeWidth="1" />
      </g>
      {/* Cloud folder */}
      <g transform="translate(12,200)" opacity="0.35">
        <path d="M10,20 Q6,20 4,16 Q0,14 4,10 Q4,4 10,4 Q14,0 20,4 Q26,0 32,4 Q38,4 38,10 Q42,14 38,16 Q36,20 32,20 Z" fill="none" stroke="#0F2847" strokeWidth="1.5" />
        <rect x="6" y="22" width="46" height="32" rx="4" fill="none" stroke="#0F2847" strokeWidth="1.5" />
        <line x1="6" y1="32" x2="52" y2="32" stroke="#0F2847" strokeWidth="1" />
      </g>
      {/* Conflict X */}
      <g transform="translate(300,220)" opacity="0.4">
        <circle cx="20" cy="20" r="18" fill="none" stroke="#ef4444" strokeWidth="1.5" />
        <line x1="12" y1="12" x2="28" y2="28" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" />
        <line x1="28" y1="12" x2="12" y2="28" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" />
      </g>
    </svg>
  );
}

/* Section 3 — Vision */
function IllusVision() {
  return (
    <svg viewBox="0 0 460 320" style={{ width: "100%", maxWidth: 460, height: "auto" }} aria-hidden="true">
      {/* Large circle */}
      <circle cx="230" cy="160" r="120" fill="#f8fafc" stroke="#e2e8f0" strokeWidth="1.5" />
      {/* Inner circle */}
      <circle cx="230" cy="160" r="52" fill="#0F2847" />
      <text x="230" y="155" textAnchor="middle" style={{ fontSize: 10, fill: "#fff", fontWeight: 700, fontFamily: "system-ui" }}>Synaptiq</text>
      <text x="230" y="168" textAnchor="middle" style={{ fontSize: 7.5, fill: "rgba(255,255,255,0.6)", fontFamily: "system-ui" }}>One ecosystem</text>

      {/* Orbital items */}
      {[
        { angle: -90, label: "Profile",      icon: "👤", r: 108 },
        { angle: -18, label: "Network",      icon: "🌐", r: 108 },
        { angle:  54, label: "Publish",      icon: "📄", r: 108 },
        { angle: 126, label: "Workspace",    icon: "🗂", r: 108 },
        { angle: 198, label: "AI Suite",     icon: "✦",  r: 108 },
      ].map(({ angle, label, icon, r }) => {
        const rad = (angle * Math.PI) / 180;
        const cx = 230 + r * Math.cos(rad);
        const cy = 160 + r * Math.sin(rad);
        return (
          <g key={label}>
            <line x1="230" y1="160" x2={cx} y2={cy} stroke="#0F2847" strokeWidth="0.8" opacity="0.2" strokeDasharray="3 3" />
            <circle cx={cx} cy={cy} r="22" fill="#fff" stroke="#e2e8f0" strokeWidth="1.5" />
            <text x={cx} y={cy + 1} textAnchor="middle" style={{ fontSize: 9, fill: "#0F2847", fontWeight: 700, fontFamily: "system-ui" }}>{icon}</text>
            <text x={cx} y={cy + 34} textAnchor="middle" style={{ fontSize: 8.5, fill: "#0F2847", fontFamily: "system-ui", fontWeight: 600 }}>{label}</text>
          </g>
        );
      })}
    </svg>
  );
}

/* Section 8 — The Future */
function IllusFuture() {
  return (
    <svg viewBox="0 0 520 300" style={{ width: "100%", maxWidth: 520, height: "auto" }} aria-hidden="true">
      {/* Horizon line */}
      <line x1="40" y1="220" x2="480" y2="220" stroke="#e2e8f0" strokeWidth="1.5" />

      {/* University buildings */}
      {[60, 160, 280, 380, 440].map((x, i) => (
        <g key={i} transform={`translate(${x},${220 - [90, 110, 130, 100, 80][i]})`}>
          <rect x="0" y="0" width={[50, 60, 70, 55, 44][i]} height={[90, 110, 130, 100, 80][i]} fill="none" stroke="#0F2847" strokeWidth={i === 2 ? 2 : 1.2} opacity={i === 2 ? 1 : 0.4} />
          {/* Windows */}
          {[0, 1, 2].map((row) => [0, 1].map((col) => (
            <rect key={`${row}-${col}`}
              x={8 + col * 16} y={10 + row * 22}
              width="8" height="12" rx="1"
              fill={i === 2 ? "#0F2847" : "none"}
              stroke="#0F2847" strokeWidth="0.8" opacity={i === 2 ? 0.5 : 0.3}
            />
          )))}
          {/* Flag/dome for center building */}
          {i === 2 && (
            <>
              <line x1="35" y1="0" x2="35" y2="-20" stroke="#0F2847" strokeWidth="1.5" />
              <polygon points="35,-20 50,-12 35,-4" fill="#0F2847" opacity="0.7" />
            </>
          )}
        </g>
      ))}

      {/* Network lines in sky */}
      {[[130, 60], [260, 40], [390, 70]].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="5" fill="#0F2847" opacity="0.5" />
      ))}
      <line x1="130" y1="60" x2="260" y2="40" stroke="#0F2847" strokeWidth="0.8" opacity="0.3" strokeDasharray="4 3" />
      <line x1="260" y1="40" x2="390" y2="70" stroke="#0F2847" strokeWidth="0.8" opacity="0.3" strokeDasharray="4 3" />
      <line x1="130" y1="60" x2="390" y2="70" stroke="#0F2847" strokeWidth="0.6" opacity="0.15" strokeDasharray="3 4" />

      {/* Stars/AI nodes */}
      {[[80, 30], [200, 20], [320, 25], [450, 35]].map(([x, y], i) => (
        <text key={i} x={x} y={y} style={{ fontSize: 10, fill: "#0F2847", fontFamily: "system-ui" }} opacity="0.25">✦</text>
      ))}

      {/* Papers floating */}
      <g transform="translate(238,120)" opacity="0.6">
        <rect x="0" y="0" width="44" height="56" rx="2" fill="#fff" stroke="#0F2847" strokeWidth="1.5" />
        <line x1="6" y1="10" x2="38" y2="10" stroke="#0F2847" strokeWidth="1" opacity="0.4" />
        <line x1="6" y1="17" x2="38" y2="17" stroke="#0F2847" strokeWidth="1" opacity="0.4" />
        <line x1="6" y1="24" x2="28" y2="24" stroke="#0F2847" strokeWidth="1" opacity="0.4" />
        <circle cx="36" cy="46" r="9" fill="#10b981" />
        <polyline points="33,46 35,48 39,43" fill="none" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
      </g>
    </svg>
  );
}

/* Section 9 — Timeline graphic */
function IllusTimeline({ items }) {
  return (
    <div style={{ position: "relative", overflowX: "auto", paddingBottom: 8 }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 0, minWidth: 700 }}>
        {items.map(({ year, label, sub }, i) => (
          <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", position: "relative" }}>
            {/* Connector */}
            {i < items.length - 1 && (
              <div style={{
                position: "absolute", top: 19, left: "50%", width: "100%", height: 2,
                background: i === 0 ? "#0F2847" : "#e2e8f0",
                zIndex: 0,
              }} />
            )}
            {/* Node */}
            <div style={{
              width: 40, height: 40, borderRadius: "50%", zIndex: 1, flexShrink: 0,
              background: i === 0 ? "#0F2847" : i === 1 ? "#1e3a5f" : i === 2 ? "#334155" : "#f1f5f9",
              border: i >= 3 ? "2px solid #e2e8f0" : "none",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              {i < 3 ? (
                <CheckCircle2 size={16} strokeWidth={2} style={{ color: "#fff" }} />
              ) : (
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#cbd5e1" }} />
              )}
            </div>
            {/* Labels */}
            <div style={{ textAlign: "center", marginTop: 12, padding: "0 8px" }}>
              <div style={{ fontSize: "0.68rem", fontWeight: 800, color: i < 3 ? "#0F2847" : "#94a3b8", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 3 }}>{year}</div>
              <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#0a0f1a", lineHeight: 1.3 }}>{label}</div>
              {sub && <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: 2, lineHeight: 1.4 }}>{sub}</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Static data ──────────────────────────────────────────────────────────── */

const PLATFORM_CARDS = [
  { icon: Users,       title: "Academic Collaboration",     body: "Discover, connect, and form research teams with experts worldwide across every discipline." },
  { icon: BrainCircuit,title: "AI Research Assistant",      body: "Literature review, gap detection, manuscript review, statistics — AI that understands academic rigor." },
  { icon: FileText,    title: "Publication Management",     body: "From manuscript to published paper: journal matching, submission tracking, citation monitoring." },
  { icon: Building2,   title: "Institution Dashboard",      body: "Analytics, department management, and benchmarking for research offices and universities." },
  { icon: BarChart3,   title: "Research Analytics",         body: "Track your academic impact, H-index, citation trends, and research output over time." },
  { icon: Shield,      title: "Verification & Trust",       body: "Academic identity verification, ORCID integration, and a trust score that travels with you." },
  { icon: Globe,       title: "Global Network",             body: "150+ countries, open collaborations, mentorship, and cross-institutional research discovery." },
  { icon: Briefcase,   title: "Academic Marketplace",       body: "Statistical consulting, peer review, editing, and translation from vetted academic experts." },
];

const PRINCIPLES = [
  { icon: Microscope,  title: "Scientific Integrity",    body: "Every decision is measured against its effect on the quality and honesty of research output." },
  { icon: Eye,         title: "Radical Transparency",    body: "Credit costs, AI capabilities, and data policies are documented clearly — no vague metering, no surprises." },
  { icon: Handshake,   title: "Collaboration First",     body: "The platform rewards sharing, co-authorship, and open science over individual competition." },
  { icon: Sparkles,    title: "AI as Assistance",        body: "AI augments the researcher — it does not replace expertise, judgment, or authorship." },
  { icon: Lock,        title: "Privacy by Design",       body: "Research data is yours. We never sell it, never train on it without consent, and always encrypt it." },
  { icon: BookOpen,    title: "Open Science",            body: "We build tools that make open access, preprint sharing, and reproducible research the natural path." },
];

const USER_TYPES = [
  { icon: GraduationCap, title: "Students",            body: "Undergraduates building their first research profile and network." },
  { icon: GraduationCap, title: "Master's Students",   body: "Finding thesis supervisors and collaboration opportunities." },
  { icon: FlaskConical,  title: "PhD Candidates",      body: "Managing projects, literature, and international collaborators." },
  { icon: Microscope,    title: "Postdoc Researchers", body: "Building a research identity and expanding international reach." },
  { icon: Award,         title: "Professors",           body: "Leading research groups, mentoring, and tracking institutional impact." },
  { icon: Building2,     title: "Universities",         body: "Monitoring faculty output, grant pipelines, and research performance." },
  { icon: Target,        title: "Research Centers",     body: "Managing consortia, measuring impact, and forming partnerships." },
  { icon: Layers,        title: "Grant Organizations",  body: "Evaluating applicants and tracking funded research outcomes." },
  { icon: Globe,         title: "Publishers",           body: "Connecting journals to a global pipeline of verified researchers." },
];

const STATS = [
  { target: 150,  suffix: "+", label: "Countries",            sub: "Active researchers" },
  { target: 50,   suffix: "K+",label: "Researchers",          sub: "On the platform" },
  { target: 8,    suffix: "K+",label: "Institutions",         sub: "Universities & research centers" },
  { target: 250,  suffix: "K+",label: "Research Teams",       sub: "Formed on the platform" },
  { target: 1200, suffix: "K+",label: "Projects Created",     sub: "Active and archived" },
  { target: 2,    suffix: "M+",label: "AI Sessions",          sub: "Research queries processed" },
  { target: 90,   suffix: "K+",label: "Publications Tracked", sub: "Across all plans" },
];

const TESTIMONIALS = [
  {
    quote: "Synaptiq gave me a co-author I never would have found through my institution alone. We submitted to Nature Methods three months after connecting.",
    author: "Dr. Kenji Watanabe", role: "Postdoctoral Researcher", institution: "Kyoto University",
    initials: "KW", color: "#0F2847",
  },
  {
    quote: "I run a research office for 140 faculty. The institution dashboard replaced four separate tools and gave us real-time visibility into our grant pipeline.",
    author: "Prof. Ingrid Sörensen", role: "Head of Research Office", institution: "Uppsala University",
    initials: "IS", color: "#1d4ed8",
  },
  {
    quote: "The AI literature review saved me four weeks. It read 600 papers, identified three underexplored gaps, and cited them correctly. That's just the start.",
    author: "Dr. Amara Diallo", role: "PhD Candidate", institution: "ETH Zürich",
    initials: "AD", color: "#059669",
  },
];

const TIMELINE_ITEMS = [
  { year: "2026 Q1", label: "Platform Launch", sub: "Core research platform live" },
  { year: "2026 Q2", label: "AI Workspace", sub: "Full AI suite deployed" },
  { year: "2026 Q3", label: "Global Network", sub: "50K researchers onboarded" },
  { year: "2026 Q4", label: "Institution Platform", sub: "University deployments" },
  { year: "2027",    label: "Academic Marketplace", sub: "Expert services ecosystem" },
  { year: "2027",    label: "Knowledge Graph", sub: "Living research graph" },
  { year: "2028+",   label: "Future Vision", sub: "Autonomous research agents" },
];

const TRUSTED_ORGS = [
  "MIT",       "Oxford",         "ETH Zürich",    "Kyoto Univ.",
  "Uppsala",   "TU Berlin",      "CNRS",           "Nature Publishing",
  "IEEE",      "Springer",       "Elsevier",       "arXiv",
];

const WORKFLOW_STEPS = [
  { num: "01", label: "Discover researchers", body: "AI matches you to collaborators by methodology, topic, and institutional profile." },
  { num: "02", label: "Connect", body: "Send a structured collaboration request with your research brief and goals." },
  { num: "03", label: "Build teams", body: "Create a shared workspace with defined roles: lead author, co-author, reviewer, analyst." },
  { num: "04", label: "Collaborate", body: "Literature review, gap analysis, study design — all in one shared environment." },
  { num: "05", label: "Write", body: "Co-author manuscripts with version control, comments, and AI writing assistance." },
  { num: "06", label: "Review", body: "AI structural review and journal fit scoring before peer submission." },
  { num: "07", label: "Publish", body: "Journal matching, cover letter generation, and submission tracking." },
  { num: "08", label: "Measure impact", body: "Citation monitoring, H-index tracking, and research impact dashboards." },
];

/* ─── Stat counter ──────────────────────────────────────────────────────────── */
function StatCounter({ target, suffix, label, sub }) {
  const { ref, value } = useCounter(target);
  return (
    <div ref={ref} style={{ textAlign: "center" }}>
      <div style={{ fontSize: "clamp(2.4rem, 4vw, 3.6rem)", fontWeight: 900, color: "#0a0f1a", lineHeight: 1, letterSpacing: "-0.04em" }}>
        {value.toLocaleString()}{suffix}
      </div>
      <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#334155", marginTop: 8 }}>{label}</div>
      {sub && <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

/* ─── Fragmented workflow diagram ──────────────────────────────────────────── */
const FRAG_TOOLS = [
  { label: "Email",           color: "#fef3c7", border: "#f59e0b", text: "#92400e" },
  { label: "Google Docs",     color: "#f0fdf4", border: "#16a34a", text: "#166534" },
  { label: "Dropbox",         color: "#eff6ff", border: "#3b82f6", text: "#1d4ed8" },
  { label: "Slack",           color: "#fdf4ff", border: "#a855f7", text: "#7e22ce" },
  { label: "Zoom",            color: "#fff7ed", border: "#ea580c", text: "#c2410c" },
  { label: "Zotero",          color: "#f0f9ff", border: "#0284c7", text: "#0c4a6e" },
  { label: "Overleaf",        color: "#f0fdf4", border: "#15803d", text: "#14532d" },
  { label: "SharePoint",      color: "#fef9f0", border: "#d97706", text: "#92400e" },
  { label: "Journal website", color: "#fef2f2", border: "#dc2626", text: "#991b1b" },
  { label: "Excel tracker",   color: "#f0fdf4", border: "#16a34a", text: "#166534" },
  { label: "WhatsApp",        color: "#f0fdf4", border: "#22c55e", text: "#15803d" },
  { label: "ResearchGate",    color: "#eff6ff", border: "#2563eb", text: "#1e40af" },
];

/* ─── Page ──────────────────────────────────────────────────────────────────── */
export default function About() {
  useEffect(() => {
    document.title = "About — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const rProblem     = useReveal();
  const rWorkflow    = useReveal();
  const rVision      = useReveal();
  const rHowItWorks  = useReveal();
  const rCards       = useReveal();
  const rPrinciples  = useReveal();
  const rWho         = useReveal();
  const rFuture      = useReveal();
  const rTimeline    = useReveal();
  const rStats       = useReveal();
  const rTestimonials= useReveal();
  const rMedia       = useReveal();

  return (
    <MarketingLayout>

      {/* ══════ HERO ══════════════════════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: "1px solid #f1f5f9", paddingTop: 80, paddingBottom: 0 }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div className="grid lg:grid-cols-2 gap-16 items-end">
            <div style={{ paddingBottom: 80 }}>
              <div style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 20 }}>
                About Synaptiq
              </div>
              <h1 style={{
                fontSize: "clamp(2.6rem, 5.5vw, 4.4rem)", fontWeight: 900,
                letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.04,
                textWrap: "balance", marginBottom: 24,
              }}>
                Building the future of global academic collaboration.
              </h1>
              <p style={{ fontSize: "clamp(1rem, 1.5vw, 1.1rem)", color: "#475569", lineHeight: 1.8, maxWidth: 520 }}>
                Synaptiq exists to remove geographical, institutional and technological barriers so researchers can discover collaborators, build international teams and produce better science together.
              </p>
              <div className="flex flex-wrap gap-4 mt-8">
                <Link to="/register"
                  className="inline-flex items-center gap-2 font-semibold"
                  style={{ background: "#0F2847", color: "#fff", padding: "12px 26px", borderRadius: 9, fontSize: "0.9rem" }}
                >
                  Start Free <ArrowRight size={14} strokeWidth={2.5} />
                </Link>
                <Link to="/contact"
                  className="inline-flex items-center gap-2 font-semibold"
                  style={{ border: "1px solid #e2e8f0", color: "#0a0f1a", padding: "12px 22px", borderRadius: 9, fontSize: "0.9rem" }}
                >
                  Book a Demo
                </Link>
              </div>
            </div>
            <div className="hidden lg:flex justify-end items-end" style={{ paddingBottom: 0 }}>
              <IllusHero />
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 1 — THE PROBLEM ════════════════════════════════════════ */}
      <section style={{ background: "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rProblem} className="sq-reveal grid lg:grid-cols-2 gap-16 items-center">
            <div className="hidden lg:block">
              <IllusProblem />
            </div>
            <div>
              <div className="overline mb-4">The Problem</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance", marginBottom: 24 }}>
                Research is still fragmented.
              </h2>
              <p style={{ fontSize: "0.95rem", color: "#475569", lineHeight: 1.8, marginBottom: 20 }}>
                The world produces more research than ever — but the infrastructure supporting it hasn't changed in decades. Researchers juggle dozens of disconnected tools, lose potential collaborators to geography, and spend more time on coordination than on discovery.
              </p>
              <div className="flex flex-col gap-5">
                {[
                  ["Finding collaborators", "depends on conferences, alumni networks, and cold emails — slow, unscalable, geographically limited."],
                  ["Project coordination", "splits across email, cloud folders, spreadsheets, and messaging apps with no unified history."],
                  ["Manuscript workflows", "involve version conflicts, unclear authorship, and disconnected review processes."],
                  ["Knowledge access", "is locked behind paywalls, institutional silos, and institutional privilege."],
                  ["AI tools", "are generic — they don't understand methodology, academic publishing standards, or research ethics."],
                ].map(([title, body]) => (
                  <div key={title} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                    <div style={{ width: 22, height: 22, borderRadius: "50%", background: "#0F2847", flexShrink: 0, marginTop: 2, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#fff" }} />
                    </div>
                    <div>
                      <span style={{ fontSize: "0.87rem", fontWeight: 700, color: "#0a0f1a" }}>{title} </span>
                      <span style={{ fontSize: "0.85rem", color: "#64748b", lineHeight: 1.65 }}>{body}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 2 — FRAGMENTED WORKFLOW ════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rWorkflow} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <div className="overline mb-3">Today's Reality</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance" }}>
                The traditional research workflow.
              </h2>
              <p style={{ fontSize: "0.95rem", color: "#64748b", lineHeight: 1.75, maxWidth: 560, margin: "16px auto 0" }}>
                A typical research project requires 12+ disconnected tools — each with its own login, file format, and communication thread. The result is fragmentation, duplication, and missed opportunities.
              </p>
            </div>

            {/* Fragmented tools cloud */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "center", maxWidth: 760, margin: "0 auto" }}>
              {FRAG_TOOLS.map(({ label, color, border, text }) => (
                <div key={label} style={{
                  background: color, border: `1px solid ${border}`,
                  borderRadius: 8, padding: "8px 16px",
                  fontSize: "0.8rem", fontWeight: 600, color: text,
                  opacity: 0.85,
                }}>
                  {label}
                </div>
              ))}
            </div>

            {/* Arrow down */}
            <div style={{ textAlign: "center", margin: "36px 0 28px" }}>
              <div style={{ display: "inline-flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#ef4444", letterSpacing: "0.06em", textTransform: "uppercase" }}>Result</div>
                {["Version conflicts", "Missed collaborations", "Wasted researcher time", "Fragmented knowledge"].map((r) => (
                  <div key={r} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#ef4444" }} />
                    <span style={{ fontSize: "0.85rem", color: "#ef4444", fontWeight: 600 }}>{r}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* vs Synaptiq */}
            <div style={{ background: "#0F2847", borderRadius: 16, padding: "32px 40px", maxWidth: 560, margin: "0 auto", textAlign: "center" }}>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)", marginBottom: 12 }}>With Synaptiq</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 900, letterSpacing: "-0.03em", color: "#fff", lineHeight: 1.15, marginBottom: 8 }}>
                One platform.<br />One workflow.<br />Zero fragmentation.
              </div>
              <div style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.55)", lineHeight: 1.7 }}>
                Every tool a researcher needs — unified, interoperable, and AI-powered.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 3 — THE VISION ═════════════════════════════════════════ */}
      <section style={{ background: "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rVision} className="sq-reveal grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <div className="overline mb-4">The Synaptiq Vision</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance", marginBottom: 24 }}>
                One academic ecosystem for every researcher.
              </h2>
              <p style={{ fontSize: "0.95rem", color: "#475569", lineHeight: 1.8, marginBottom: 28 }}>
                We believe a researcher in Nairobi should have the same access to collaborators, tools, and publishing infrastructure as one in Cambridge. That requires not just better software — but a new kind of academic operating system.
              </p>
              <div className="flex flex-col gap-4">
                {[
                  "One profile — your verified academic identity, portable across institutions",
                  "One workspace — projects, literature, manuscripts, and data together",
                  "One network — 150+ countries, every discipline, open to collaboration",
                  "One publication workflow — from idea to published paper, with AI",
                  "One AI assistant — that understands research, not just text",
                ].map((item) => (
                  <div key={item} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                    <CheckCircle2 size={16} strokeWidth={2} style={{ color: "#0F2847", flexShrink: 0, marginTop: 2 }} />
                    <span style={{ fontSize: "0.87rem", color: "#334155", lineHeight: 1.6 }}>{item}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex justify-center">
              <IllusVision />
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 4 — HOW IT WORKS ═══════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rHowItWorks} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 64 }}>
              <div className="overline mb-3">How Synaptiq Works</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance" }}>
                From first question to final publication.
              </h2>
            </div>

            <div className="flex flex-col gap-0">
              {WORKFLOW_STEPS.map(({ num, label, body }, i) => (
                <div key={num} style={{
                  display: "grid",
                  gridTemplateColumns: "100px 1fr",
                  gap: 0,
                  borderTop: i === 0 ? "1px solid #f1f5f9" : "none",
                  borderBottom: "1px solid #f1f5f9",
                }}
                  onMouseEnter={(e) => e.currentTarget.style.background = "#fafbff"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                >
                  <div style={{ padding: "28px 0", display: "flex", alignItems: "flex-start", paddingTop: 30 }}>
                    <span style={{ fontSize: "0.68rem", fontWeight: 800, color: "#94a3b8", letterSpacing: "0.1em", fontVariantNumeric: "tabular-nums" }}>{num}</span>
                  </div>
                  <div style={{ padding: "28px 0", paddingLeft: 24, borderLeft: "1px solid #f1f5f9" }}>
                    <div style={{ fontSize: "1rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 6 }}>{label}</div>
                    <div style={{ fontSize: "0.85rem", color: "#64748b", lineHeight: 1.7, maxWidth: 620 }}>{body}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 5 — PLATFORM CARDS ════════════════════════════════════ */}
      <section style={{ background: "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rCards} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <div className="overline mb-3">Platform</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance" }}>
                Designed around researchers.
              </h2>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {PLATFORM_CARDS.map(({ icon: Icon, title, body }) => (
                <div key={title}
                  style={{ background: "#fff", border: "1px solid #e8edf3", borderRadius: 14, padding: "24px 22px", transition: "box-shadow 180ms, transform 180ms" }}
                  onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 8px 32px rgba(15,40,71,0.09)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "none"; }}
                >
                  <div style={{ width: 40, height: 40, borderRadius: 10, background: "rgba(15,40,71,0.05)", border: "1px solid rgba(15,40,71,0.08)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
                    <Icon size={18} strokeWidth={1.5} style={{ color: "#0F2847" }} />
                  </div>
                  <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 8 }}>{title}</div>
                  <div style={{ fontSize: "0.78rem", color: "#64748b", lineHeight: 1.65 }}>{body}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 6 — PRINCIPLES ═════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rPrinciples} className="sq-reveal">
            <div style={{ marginBottom: 56 }}>
              <div className="overline mb-3">Our Principles</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance", maxWidth: 560 }}>
                A platform built on honest principles.
              </h2>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {PRINCIPLES.map(({ icon: Icon, title, body }) => (
                <div key={title} style={{ padding: "28px 28px 28px 0", borderTop: "2px solid #0F2847" }}>
                  <div style={{ width: 40, height: 40, borderRadius: 10, background: "rgba(15,40,71,0.05)", border: "1px solid rgba(15,40,71,0.08)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
                    <Icon size={18} strokeWidth={1.5} style={{ color: "#0F2847" }} />
                  </div>
                  <div style={{ fontSize: "1rem", fontWeight: 800, color: "#0a0f1a", marginBottom: 10 }}>{title}</div>
                  <div style={{ fontSize: "0.83rem", color: "#475569", lineHeight: 1.75 }}>{body}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 7 — WHO USES SYNAPTIQ ══════════════════════════════════ */}
      <section style={{ background: "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rWho} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <div className="overline mb-3">Who Uses Synaptiq</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance" }}>
                Built for everyone in research.
              </h2>
            </div>
            <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-5">
              {USER_TYPES.map(({ icon: Icon, title, body }) => (
                <div key={title} style={{ background: "#fff", border: "1px solid #e8edf3", borderRadius: 14, padding: "24px 22px", display: "flex", gap: 14, alignItems: "flex-start" }}>
                  <div style={{ width: 38, height: 38, borderRadius: 9, background: "rgba(15,40,71,0.05)", border: "1px solid rgba(15,40,71,0.08)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Icon size={17} strokeWidth={1.5} style={{ color: "#0F2847" }} />
                  </div>
                  <div>
                    <div style={{ fontSize: "0.88rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 5 }}>{title}</div>
                    <div style={{ fontSize: "0.77rem", color: "#64748b", lineHeight: 1.6 }}>{body}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 8 — THE FUTURE (dark) ══════════════════════════════════ */}
      <section style={{ background: "#0F2847" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rFuture} className="sq-reveal grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.35)", marginBottom: 20 }}>The Future</div>
              <h2 style={{ fontSize: "clamp(2rem, 4vw, 3.4rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#fff", lineHeight: 1.05, textWrap: "balance", marginBottom: 24 }}>
                The future of research is collaborative.
              </h2>
              <p style={{ fontSize: "0.95rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.8, marginBottom: 32 }}>
                We believe the next breakthrough in medicine, climate science, or quantum computing will emerge from a team of researchers who would never have found each other without infrastructure like Synaptiq.
              </p>
              <div className="flex flex-col gap-5">
                {[
                  ["Global collaboration", "Research teams forming across continents as naturally as across corridors."],
                  ["Verified identity", "A researcher's credentials, publications, and expertise travel with them, always."],
                  ["Human expertise + AI", "AI accelerates discovery; researchers remain the authors of meaning."],
                  ["Knowledge without borders", "Every paper, dataset, and insight accessible to every qualified researcher."],
                ].map(([title, body]) => (
                  <div key={title} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                    <div style={{ width: 20, height: 20, borderRadius: "50%", background: "rgba(255,255,255,0.12)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 2 }}>
                      <div style={{ width: 6, height: 6, borderRadius: "50%", background: "rgba(255,255,255,0.8)" }} />
                    </div>
                    <div>
                      <span style={{ fontSize: "0.87rem", fontWeight: 700, color: "rgba(255,255,255,0.85)" }}>{title} — </span>
                      <span style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.5)", lineHeight: 1.65 }}>{body}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex justify-center">
              <IllusFuture />
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 9 — TIMELINE ═══════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rTimeline} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <div className="overline mb-3">Roadmap</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance" }}>
                Building milestone by milestone.
              </h2>
            </div>
            <IllusTimeline items={TIMELINE_ITEMS} />
          </div>
        </div>
      </section>

      {/* ══════ SECTION 10 — BY THE NUMBERS (white) ═══════════════════════════ */}
      <section style={{ background: "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rStats} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 64 }}>
              <div className="overline mb-3">By the Numbers</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance" }}>
                The world's researchers trust Synaptiq.
              </h2>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 32 }} className="grid-cols-2 lg:grid-cols-4">
              {STATS.slice(0, 4).map((s) => <StatCounter key={s.label} {...s} />)}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 32, marginTop: 48, maxWidth: 760, margin: "48px auto 0" }} className="grid-cols-1 md:grid-cols-3">
              {STATS.slice(4).map((s) => <StatCounter key={s.label} {...s} />)}
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 11 — TESTIMONIALS ══════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rTestimonials} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <div className="overline mb-3">Testimonials</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08 }}>
                What researchers say.
              </h2>
            </div>
            <div className="grid md:grid-cols-3 gap-6">
              {TESTIMONIALS.map(({ quote, author, role, institution, initials, color }) => (
                <div key={author} style={{ background: "#f8fafc", border: "1px solid #e8edf3", borderRadius: 16, padding: "32px 28px", display: "flex", flexDirection: "column" }}>
                  <div style={{ display: "flex", gap: 2, marginBottom: 20 }}>
                    {[1,2,3,4,5].map((s) => <Star key={s} size={12} fill="#0F2847" strokeWidth={0} style={{ color: "#0F2847" }} />)}
                  </div>
                  <p style={{ fontSize: "0.88rem", color: "#334155", lineHeight: 1.8, flex: 1, marginBottom: 24 }}>
                    &ldquo;{quote}&rdquo;
                  </p>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, paddingTop: 20, borderTop: "1px solid #f1f5f9" }}>
                    <div style={{ width: 38, height: 38, borderRadius: "50%", background: color, color: "#fff", fontSize: "0.68rem", fontWeight: 800, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      {initials}
                    </div>
                    <div>
                      <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#0a0f1a" }}>{author}</div>
                      <div style={{ fontSize: "0.72rem", color: "#64748b", marginTop: 1 }}>{role} · {institution}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 12 — TRUSTED BY ════════════════════════════════════════ */}
      <section style={{ background: "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-20">
          <div ref={rMedia} className="sq-reveal">
            <div style={{ textAlign: "center", fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 28 }}>
              Trusted by the academic community
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "12px 28px" }}>
              {TRUSTED_ORGS.map((name) => (
                <div key={name} style={{
                  fontSize: "0.82rem", fontWeight: 700, color: "#94a3b8",
                  padding: "7px 18px", border: "1px solid #e2e8f0", borderRadius: 8, background: "#fff",
                }}>
                  {name}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 13 — JOIN CTA (dark) ═══════════════════════════════════ */}
      <section style={{ background: "#0F2847" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-32 lg:py-40">
          <div style={{ textAlign: "center", maxWidth: 640, margin: "0 auto" }}>
            <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.3)", marginBottom: 24 }}>Join Our Mission</div>
            <h2 style={{
              fontSize: "clamp(2.2rem, 5vw, 4rem)", fontWeight: 900,
              letterSpacing: "-0.04em", color: "#fff", lineHeight: 1.04, textWrap: "balance", marginBottom: 20,
            }}>
              Help shape the future of scientific collaboration.
            </h2>
            <p style={{ fontSize: "1rem", color: "rgba(255,255,255,0.55)", lineHeight: 1.75, maxWidth: 480, margin: "0 auto 40px" }}>
              Join 50,000+ researchers already using Synaptiq. Start for free, upgrade when your research demands it.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to="/register"
                className="inline-flex items-center gap-2.5 font-semibold transition-all active:scale-[.98]"
                style={{ background: "#fff", color: "#0F2847", padding: "15px 32px", borderRadius: 10, fontSize: "0.95rem", boxShadow: "0 4px 24px rgba(0,0,0,0.2)" }}
              >
                Start Free <ArrowRight size={15} strokeWidth={2.5} />
              </Link>
              <Link to="/contact"
                className="inline-flex items-center gap-2 font-semibold transition-colors"
                style={{ color: "rgba(255,255,255,0.65)", fontSize: "0.93rem", border: "1px solid rgba(255,255,255,0.2)", padding: "14px 28px", borderRadius: 10 }}
              >
                Request a Demo
              </Link>
            </div>
            <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.28)", marginTop: 20 }}>
              Free plan available · No credit card required · GDPR aligned
            </p>
          </div>
        </div>
      </section>

    </MarketingLayout>
  );
}

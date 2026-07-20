/* eslint-disable */
import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import {
  ArrowRight, Check, Shield, Lock, Database, Users,
  BarChart3, Brain, Globe, TrendingUp, Eye, Server,
  Key, RefreshCw, AlertCircle, Award,
} from "lucide-react";

const NAVY   = "#0F2847";
const LIGHT  = "#f8fafc";
const BORDER = "#e8edf3";
const SLATE  = "#475569";

/* ─── Animated counter hook ────────────────────────────────────────────────── */
function useCounter(target, duration = 1800) {
  const [count, setCount] = useState(0);
  const elRef  = useRef(null);
  const active = useRef(false);
  useEffect(() => {
    const el = elRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !active.current) {
        active.current = true;
        const t0 = performance.now();
        const tick = (now) => {
          const p = Math.min((now - t0) / duration, 1);
          setCount(Math.round((1 - Math.pow(1 - p, 3)) * target));
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      }
    }, { threshold: 0.5 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [target, duration]);
  return [count, elRef];
}

/* ─── Hero illustration — Digital Campus ───────────────────────────────────── */
function CampusIllus() {
  const cx = 260, cy = 215, r = 138;
  const nodes = [
    { angle: -90,  label: "AI Engine",    sub: "9 agents" },
    { angle: -30,  label: "Research Ops", sub: "Projects · Grants" },
    { angle:  30,  label: "Teaching Hub", sub: "Courses · LMS" },
    { angle:  90,  label: "Analytics",    sub: "Real-time KPIs" },
    { angle: 150,  label: "Governance",   sub: "Integrity · GDPR" },
    { angle: 210,  label: "Knowledge",    sub: "Graph · Memory" },
  ];
  const pts = nodes.map(n => {
    const rad = (n.angle * Math.PI) / 180;
    return { ...n, x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  });
  return (
    <svg viewBox="0 0 530 450" style={{ width: "100%", maxWidth: 530 }} aria-hidden="true">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={BORDER} strokeWidth={1.5} strokeDasharray="5 4" />
      {pts.map((p, i) => (
        <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke={BORDER} strokeWidth={1.5} strokeDasharray="4 4" />
      ))}
      {/* Central node */}
      <rect x={cx - 58} y={cy - 32} width={116} height={64} rx={14} fill={NAVY} />
      <text x={cx} y={cy - 8} textAnchor="middle" fill="#fff" fontSize={9.5} fontWeight={700} letterSpacing={2.5} fontFamily="ui-sans-serif,system-ui">Synaptiq</text>
      <text x={cx} y={cy + 10} textAnchor="middle" fill="rgba(255,255,255,0.55)" fontSize={8} fontFamily="ui-sans-serif,system-ui">Institution OS</text>
      <text x={cx} y={cy + 24} textAnchor="middle" fill="rgba(255,255,255,0.35)" fontSize={7} fontFamily="ui-sans-serif,system-ui">v3.0 · Enterprise</text>
      {/* Orbital nodes */}
      {pts.map((p, i) => (
        <g key={i}>
          <rect x={p.x - 44} y={p.y - 21} width={88} height={42} rx={9} fill="#fff" stroke={BORDER} strokeWidth={1.5} />
          <text x={p.x} y={p.y - 4} textAnchor="middle" fill="#0a0f1a" fontSize={8.5} fontWeight={700} fontFamily="ui-sans-serif,system-ui">{p.label}</text>
          <text x={p.x} y={p.y + 10} textAnchor="middle" fill="#94a3b8" fontSize={7} fontFamily="ui-sans-serif,system-ui">{p.sub}</text>
        </g>
      ))}
      {/* Floating card — Research Output */}
      <rect x={10} y={330} width={168} height={90} rx={13} fill="#fff" stroke={BORDER} strokeWidth={1.5} />
      <text x={26} y={355} fill="#94a3b8" fontSize={7.5} fontWeight={600} letterSpacing={1.2} fontFamily="ui-sans-serif,system-ui">RESEARCH OUTPUT</text>
      <text x={26} y={380} fill={NAVY} fontSize={22} fontWeight={800} fontFamily="ui-sans-serif,system-ui">1,284</text>
      <text x={26} y={397} fill="#22c55e" fontSize={8} fontWeight={700} fontFamily="ui-sans-serif,system-ui">↑ 34% year-on-year</text>
      {/* Floating card — Grant Portfolio */}
      <rect x={356} y={18} width={160} height={80} rx={13} fill="#fff" stroke={BORDER} strokeWidth={1.5} />
      <text x={372} y={42} fill="#94a3b8" fontSize={7.5} fontWeight={600} letterSpacing={1.2} fontFamily="ui-sans-serif,system-ui">GRANT PORTFOLIO</text>
      <text x={372} y={64} fill={NAVY} fontSize={22} fontWeight={800} fontFamily="ui-sans-serif,system-ui">€42.8M</text>
      <text x={372} y={82} fill="#22c55e" fontSize={8} fontWeight={700} fontFamily="ui-sans-serif,system-ui">Active · 48 projects</text>
      {/* Floating card — Researchers (navy) */}
      <rect x={356} y={352} width={160} height={76} rx={13} fill={NAVY} />
      <text x={372} y={374} fill="rgba(255,255,255,0.5)" fontSize={7.5} fontWeight={600} letterSpacing={1.2} fontFamily="ui-sans-serif,system-ui">RESEARCHERS</text>
      <text x={372} y={400} fill="#fff" fontSize={24} fontWeight={800} fontFamily="ui-sans-serif,system-ui">4,218</text>
      <text x={372} y={418} fill="rgba(255,255,255,0.45)" fontSize={7.5} fontFamily="ui-sans-serif,system-ui">Active this month</text>
    </svg>
  );
}

/* ─── Animated stat counter ─────────────────────────────────────────────────── */
function StatCtr({ target, suffix = "", prefix = "", label, sub }) {
  const [count, ref] = useCounter(target);
  return (
    <div ref={ref} style={{ textAlign: "center", padding: "0 16px" }}>
      <div style={{ fontSize: "clamp(2.4rem, 5vw, 3.5rem)", fontWeight: 900, color: "#fff", letterSpacing: "-0.04em", lineHeight: 1 }}>
        {prefix}{count}{suffix}
      </div>
      <div style={{ fontSize: "1rem", fontWeight: 600, color: "rgba(255,255,255,0.75)", marginTop: 10 }}>{label}</div>
      {sub && <div style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.4)", marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

/* ─── Platform showcase — institution dashboard mockup ──────────────────────── */
function InstitutionMockup() {
  const [tab, setTab] = useState(0);
  const tabs = ["Analytics", "Faculty", "Grants", "Knowledge Graph", "Reports"];
  return (
    <div style={{ borderRadius: 16, overflow: "hidden", border: "1px solid rgba(255,255,255,0.1)", boxShadow: "0 40px 100px rgba(0,0,0,0.22)" }}>
      {/* Browser chrome */}
      <div style={{ background: "#111827", padding: "11px 16px", display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ display: "flex", gap: 6 }}>
          {["#ef4444","#f59e0b","#22c55e"].map((c,i) => (
            <div key={i} style={{ width: 10, height: 10, borderRadius: "50%", background: c }} />
          ))}
        </div>
        <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
          <div style={{ background: "#1f2937", borderRadius: 6, padding: "4px 28px", fontSize: "0.7rem", color: "#6b7280" }}>
            app.synaptiq.ai/institution/dashboard
          </div>
        </div>
      </div>
      {/* Tab bar */}
      <div style={{ background: "#161d2e", display: "flex", borderBottom: "1px solid rgba(255,255,255,0.07)", padding: "0 16px" }}>
        {tabs.map((t, i) => (
          <button key={i} onClick={() => setTab(i)} style={{
            padding: "10px 18px", fontSize: "0.72rem", fontWeight: 600,
            background: "transparent", border: "none", cursor: "pointer",
            color: tab === i ? "#fff" : "#64748b",
            borderBottom: tab === i ? "2px solid #3b82f6" : "2px solid transparent",
          }}>{t}</button>
        ))}
      </div>
      {/* App content */}
      <div style={{ display: "flex", minHeight: 360, background: "#1a2035" }}>
        {/* Sidebar */}
        <div style={{ width: 176, borderRight: "1px solid rgba(255,255,255,0.06)", padding: "16px 0", flexShrink: 0 }}>
          <div style={{ padding: "2px 16px 10px", fontSize: "0.62rem", color: "#475569", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase" }}>Navigation</div>
          {["Overview","Researchers","Departments","Projects","Grants","Publications","Settings"].map((item, i) => (
            <div key={i} style={{
              padding: "8px 16px", fontSize: "0.75rem",
              color: i === 0 ? "#fff" : "#64748b",
              background: i === 0 ? "rgba(59,130,246,0.12)" : "transparent",
              borderLeft: i === 0 ? "2px solid #3b82f6" : "2px solid transparent",
            }}>{item}</div>
          ))}
        </div>
        {/* Main content */}
        <div style={{ flex: 1, padding: 20 }}>
          <div style={{ fontSize: "0.7rem", color: "#6b7280", marginBottom: 16 }}>Institution Intelligence Dashboard — Q2 2026</div>
          {/* KPI row */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 16 }}>
            {[
              { l: "Active Researchers", v: "4,218", d: "+12%", c: "#22c55e" },
              { l: "Publications (YTD)", v: "1,284", d: "+34%", c: "#22c55e" },
              { l: "Grant Portfolio",    v: "€42.8M", d: "+18%", c: "#22c55e" },
              { l: "Collaboration Score",v: "94/100", d: "+7pts", c: "#3b82f6" },
            ].map((k, i) => (
              <div key={i} style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: "12px 14px", border: "1px solid rgba(255,255,255,0.07)" }}>
                <div style={{ fontSize: "0.6rem", color: "#64748b", marginBottom: 6 }}>{k.l}</div>
                <div style={{ fontSize: "1.05rem", fontWeight: 800, color: "#fff" }}>{k.v}</div>
                <div style={{ fontSize: "0.6rem", color: k.c, marginTop: 4 }}>{k.d} vs last year</div>
              </div>
            ))}
          </div>
          {/* Bar chart */}
          <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: "14px 16px", border: "1px solid rgba(255,255,255,0.07)" }}>
            <div style={{ fontSize: "0.62rem", color: "#64748b", marginBottom: 12 }}>Research Output — Monthly Trend 2026</div>
            <div style={{ display: "flex", alignItems: "flex-end", gap: 5, height: 64 }}>
              {[42,58,51,74,82,67,88,92,85,98,90,104].map((h, i) => (
                <div key={i} style={{ flex: 1, borderRadius: "3px 3px 0 0", background: i === 11 ? "#3b82f6" : "rgba(59,130,246,0.28)", height: `${(h/104)*100}%` }} />
              ))}
            </div>
            <div style={{ display: "flex", marginTop: 6 }}>
              {["J","F","M","A","M","J","J","A","S","O","N","D"].map((m, i) => (
                <div key={i} style={{ flex: 1, fontSize: "0.55rem", color: "#475569", textAlign: "center" }}>{m}</div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Feature section illustrations ────────────────────────────────────────── */

function TwinIllus() {
  return (
    <div style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 16, padding: 24, boxShadow: "0 8px 32px rgba(0,0,0,0.06)" }}>
      <div style={{ fontSize: "0.62rem", color: "#94a3b8", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 16 }}>Institution Twin · Live</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
        {[
          { label: "Research Health",     value: "92/100", color: "#22c55e" },
          { label: "Faculty Utilization", value: "87%",    color: "#3b82f6" },
          { label: "Grant Pipeline",      value: "€18.4M", color: NAVY },
          { label: "Risk Score",          value: "Low",    color: "#22c55e" },
        ].map((m, i) => (
          <div key={i} style={{ background: LIGHT, borderRadius: 10, padding: "12px 14px", border: `1px solid ${BORDER}` }}>
            <div style={{ fontSize: "0.6rem", color: "#94a3b8", marginBottom: 6 }}>{m.label}</div>
            <div style={{ fontSize: "1.2rem", fontWeight: 800, color: m.color }}>{m.value}</div>
          </div>
        ))}
      </div>
      <div style={{ background: LIGHT, borderRadius: 10, padding: "14px 16px", border: `1px solid ${BORDER}` }}>
        <div style={{ fontSize: "0.62rem", color: "#94a3b8", marginBottom: 12 }}>Department Performance</div>
        {["Computer Science","Medicine","Engineering","Natural Sciences"].map((d, i) => {
          const scores = [92, 85, 78, 95];
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: i < 3 ? 10 : 0 }}>
              <div style={{ fontSize: "0.72rem", color: SLATE, width: 130, flexShrink: 0 }}>{d}</div>
              <div style={{ flex: 1, height: 5, background: BORDER, borderRadius: 3 }}>
                <div style={{ height: 5, borderRadius: 3, background: NAVY, width: `${scores[i]}%` }} />
              </div>
              <div style={{ fontSize: "0.7rem", fontWeight: 700, color: NAVY, width: 28, textAlign: "right" }}>{scores[i]}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function GovernanceIllus() {
  const projects = [
    { name: "Neural Interface Study",  grant: "€1.2M",  status: "Active" },
    { name: "Climate Data Analysis",   grant: "€840K",  status: "Review" },
    { name: "Gene Therapy Protocol",   grant: "€2.1M",  status: "Active" },
    { name: "Materials Science Lab",   grant: "€650K",  status: "Pending"},
  ];
  const sc = { Active: "#22c55e", Review: "#f59e0b", Pending: "#94a3b8" };
  return (
    <div style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 16, padding: 24, boxShadow: "0 8px 32px rgba(0,0,0,0.06)" }}>
      <div style={{ fontSize: "0.62rem", color: "#94a3b8", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 16 }}>Research Governance · Projects</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1, background: BORDER, borderRadius: 8, overflow: "hidden", marginBottom: 14 }}>
        {["Project","Grant","Status"].map((h, i) => (
          <div key={i} style={{ background: LIGHT, padding: "8px 12px", fontSize: "0.6rem", fontWeight: 700, color: "#94a3b8", letterSpacing: "0.06em", textTransform: "uppercase" }}>{h}</div>
        ))}
        {projects.map((p, i) => (
          <React.Fragment key={i}>
            <div style={{ background: "#fff", padding: "10px 12px", fontSize: "0.72rem", fontWeight: 600, color: "#0a0f1a" }}>{p.name}</div>
            <div style={{ background: "#fff", padding: "10px 12px", fontSize: "0.78rem", fontWeight: 700, color: NAVY, display: "flex", alignItems: "center" }}>{p.grant}</div>
            <div style={{ background: "#fff", padding: "10px 12px", display: "flex", alignItems: "center" }}>
              <span style={{ fontSize: "0.62rem", fontWeight: 700, color: sc[p.status], background: `${sc[p.status]}15`, padding: "2px 8px", borderRadius: 20 }}>{p.status}</span>
            </div>
          </React.Fragment>
        ))}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {[["24","Active Projects"],["€12.4M","In Review"],["98%","Compliant"]].map(([v,l],i) => (
          <div key={i} style={{ flex: 1, background: LIGHT, borderRadius: 8, padding: "10px 12px", border: `1px solid ${BORDER}` }}>
            <div style={{ fontSize: "1rem", fontWeight: 800, color: NAVY }}>{v}</div>
            <div style={{ fontSize: "0.6rem", color: "#94a3b8", marginTop: 2 }}>{l}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TeachingIllus() {
  const courses = [
    { name: "Advanced ML",      rating: 4.8, students: 142 },
    { name: "Biostatistics",    rating: 4.6, students: 89 },
    { name: "Research Methods", rating: 4.9, students: 210 },
    { name: "Grant Writing",    rating: 4.7, students: 67 },
  ];
  return (
    <div style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 16, padding: 24, boxShadow: "0 8px 32px rgba(0,0,0,0.06)" }}>
      <div style={{ fontSize: "0.62rem", color: "#94a3b8", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 16 }}>Teaching Analytics · Q2 2026</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 14 }}>
        {[["94%","Student Satisfaction"],["4.8/5","Avg Course Rating"],["1,240","Active Learners"]].map(([v,l],i) => (
          <div key={i} style={{ background: LIGHT, borderRadius: 9, padding: 12, border: `1px solid ${BORDER}`, textAlign: "center" }}>
            <div style={{ fontSize: "1.1rem", fontWeight: 900, color: NAVY }}>{v}</div>
            <div style={{ fontSize: "0.6rem", color: "#94a3b8", marginTop: 4 }}>{l}</div>
          </div>
        ))}
      </div>
      {courses.map((c, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 0", borderBottom: i < 3 ? `1px solid ${BORDER}` : "none" }}>
          <div style={{ flex: 1, fontSize: "0.78rem", fontWeight: 600, color: "#0a0f1a" }}>{c.name}</div>
          <div style={{ display: "flex", gap: 1 }}>
            {[1,2,3,4,5].map(s => (
              <div key={s} style={{ width: 8, height: 8, borderRadius: 2, background: s <= Math.floor(c.rating) ? "#f59e0b" : BORDER }} />
            ))}
          </div>
          <div style={{ fontSize: "0.72rem", fontWeight: 700, color: SLATE, width: 28 }}>{c.rating}</div>
          <div style={{ fontSize: "0.62rem", color: "#94a3b8", width: 64 }}>{c.students} students</div>
        </div>
      ))}
    </div>
  );
}

function AIIllus() {
  const msgs = [
    { r: "user", t: "Summarize our faculty's research output this semester." },
    { r: "ai",   t: "Your faculty published 142 papers across 8 disciplines. Computer Science leads at 38. Grant-funded research is up 22% vs Q1. Break down by department?" },
    { r: "user", t: "Yes, and flag any compliance gaps." },
    { r: "ai",   t: "Generating breakdown... Found 3 projects with pending GDPR consent forms. Notifying your research integrity officer now." },
  ];
  return (
    <div style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 16, padding: 20, boxShadow: "0 8px 32px rgba(0,0,0,0.06)" }}>
      <div style={{ fontSize: "0.62rem", color: "#94a3b8", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 14 }}>AI Assistant · Institution Context</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 14 }}>
        {msgs.map((m, i) => (
          <div key={i} style={{ display: "flex", justifyContent: m.r === "user" ? "flex-end" : "flex-start" }}>
            <div style={{
              maxWidth: "80%", padding: "8px 12px", fontSize: "0.72rem", lineHeight: 1.55,
              borderRadius: m.r === "user" ? "12px 12px 3px 12px" : "12px 12px 12px 3px",
              background: m.r === "user" ? NAVY : LIGHT,
              border: m.r === "ai" ? `1px solid ${BORDER}` : "none",
              color: m.r === "user" ? "#fff" : "#0a0f1a",
            }}>{m.t}</div>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {["Secure institutional data","GDPR compliant","No AI training on your data","Full audit log"].map((tag, i) => (
          <span key={i} style={{ fontSize: "0.6rem", fontWeight: 700, color: "#16a34a", background: "#f0fdf4", border: "1px solid #bbf7d0", padding: "3px 8px", borderRadius: 20 }}>{tag}</span>
        ))}
      </div>
    </div>
  );
}

function KGIllus() {
  const nodes = [
    { x: 160, y: 80,  label: "Prof. Chen", type: "person" },
    { x: 290, y: 50,  label: "ML Project", type: "project" },
    { x: 380, y: 120, label: "€1.2M Grant",type: "grant" },
    { x: 80,  y: 160, label: "CS Dept",    type: "dept" },
    { x: 200, y: 185, label: "Publication", type: "pub" },
    { x: 320, y: 200, label: "ETH Zürich", type: "inst" },
    { x: 140, y: 260, label: "PhD Student", type: "person" },
    { x: 270, y: 265, label: "Dataset",    type: "data" },
  ];
  const edges = [[0,1],[1,2],[0,3],[0,4],[1,5],[0,6],[4,7],[1,4]];
  const colors = { person: "#3b82f6", project: NAVY, grant: "#22c55e", dept: "#7c3aed", pub: "#f59e0b", inst: "#0891b2", data: "#dc2626" };
  return (
    <div style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 16, padding: 20, boxShadow: "0 8px 32px rgba(0,0,0,0.06)" }}>
      <div style={{ fontSize: "0.62rem", color: "#94a3b8", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 12 }}>Knowledge Graph · Live</div>
      <svg viewBox="0 0 460 310" style={{ width: "100%" }} aria-hidden="true">
        {edges.map(([a,b],i) => (
          <line key={i} x1={nodes[a].x} y1={nodes[a].y} x2={nodes[b].x} y2={nodes[b].y} stroke={BORDER} strokeWidth={1.5} />
        ))}
        {nodes.map((n,i) => {
          const c = colors[n.type];
          return (
            <g key={i}>
              <circle cx={n.x} cy={n.y} r={18} fill={`${c}18`} stroke={c} strokeWidth={1.5} />
              <text x={n.x} y={n.y+32} textAnchor="middle" fill="#64748b" fontSize={8} fontFamily="ui-sans-serif,system-ui">{n.label}</text>
            </g>
          );
        })}
      </svg>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
        {Object.entries(colors).map(([type, c]) => (
          <span key={type} style={{ fontSize: "0.6rem", fontWeight: 700, color: c, background: `${c}12`, border: `1px solid ${c}30`, padding: "2px 8px", borderRadius: 20 }}>{type}</span>
        ))}
      </div>
    </div>
  );
}

function ExecutiveIllus() {
  return (
    <div style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 16, padding: 22, boxShadow: "0 8px 32px rgba(0,0,0,0.06)" }}>
      <div style={{ fontSize: "0.62rem", color: "#94a3b8", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 14 }}>Executive Dashboard · Rector View</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
        {[
          { label: "Research Productivity Index", value: "94",   unit: "/100", delta: "↑ 8 pts",     color: "#22c55e" },
          { label: "International Ranking",       value: "#142", unit: "",     delta: "↑ 14 places",  color: "#22c55e" },
          { label: "Open Science Score",           value: "88%",  unit: "",    delta: "↑ 12%",        color: "#3b82f6" },
          { label: "Funding Success Rate",         value: "67%",  unit: "",    delta: "↑ 23%",        color: "#22c55e" },
        ].map((k, i) => (
          <div key={i} style={{ background: LIGHT, borderRadius: 9, padding: "12px 14px", border: `1px solid ${BORDER}` }}>
            <div style={{ fontSize: "0.6rem", color: "#94a3b8", marginBottom: 6 }}>{k.label}</div>
            <div style={{ fontSize: "1.15rem", fontWeight: 900, color: NAVY }}>
              {k.value}<span style={{ fontSize: "0.72rem", fontWeight: 500 }}>{k.unit}</span>
            </div>
            <div style={{ fontSize: "0.62rem", color: k.color, marginTop: 4, fontWeight: 700 }}>{k.delta} this year</div>
          </div>
        ))}
      </div>
      <div style={{ background: LIGHT, borderRadius: 9, padding: "12px 16px", border: `1px solid ${BORDER}` }}>
        <div style={{ fontSize: "0.62rem", color: "#94a3b8", marginBottom: 10 }}>Strategic KPI Tracker — 2026 vs 2025</div>
        <div style={{ display: "flex", gap: 6 }}>
          {[["Research",94],["Teaching",88],["Funding",76],["Impact",91],["Compliance",98],["Intl.",82]].map(([l,v],i) => (
            <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
              <div style={{ width: "100%", height: 50, background: BORDER, borderRadius: 4, position: "relative", overflow: "hidden" }}>
                <div style={{ position: "absolute", bottom: 0, width: "100%", height: `${v}%`, background: NAVY, borderRadius: "3px 3px 0 0" }} />
              </div>
              <div style={{ fontSize: "0.55rem", color: "#94a3b8", textAlign: "center" }}>{l}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── Static data ───────────────────────────────────────────────────────────── */

const VALUE_CARDS = [
  { icon: Database,  title: "Institution Knowledge",  color: NAVY,      desc: "One trusted source for research, teaching and institutional knowledge. Everything connected, searchable and fully auditable." },
  { icon: BarChart3, title: "Research Operations",    color: "#1d4ed8", desc: "Manage projects, grants, publications and collaborations from one platform. From idea to impact, completely traceable." },
  { icon: Shield,    title: "AI Governance",          color: "#059669", desc: "Deploy AI responsibly across the institution with full transparency. No training on your data. Immutable audit trails." },
  { icon: TrendingUp,title: "Executive Intelligence", color: "#7c3aed", desc: "Real-time dashboards for leadership and strategic decision making. Rankings, KPIs, risk monitoring and benchmarking." },
];

const SECURITY_FEATURES = [
  { icon: Lock,        title: "End-to-End Encryption",     desc: "AES-256 at rest, TLS 1.3 in transit" },
  { icon: Users,       title: "Role-Based Access Control",  desc: "Granular permissions per department" },
  { icon: Eye,         title: "Audit Logs",                 desc: "Every action logged and traceable" },
  { icon: Key,         title: "SAML / SSO",                 desc: "One login for your institution" },
  { icon: Shield,      title: "MFA",                        desc: "TOTP and hardware key support" },
  { icon: Globe,       title: "GDPR Aligned",               desc: "EU and international data compliance" },
  { icon: Award,       title: "ISO 27001 Alignment",        desc: "Enterprise security standards" },
  { icon: Server,      title: "Data Residency",             desc: "EU and US data centers available" },
  { icon: Brain,       title: "AI Governance",              desc: "Zero training on institutional data" },
  { icon: RefreshCw,   title: "Version History",            desc: "Full rollback for all documents" },
  { icon: Database,    title: "Automated Backups",          desc: "Daily encrypted off-site backups" },
  { icon: AlertCircle, title: "Academic Integrity",         desc: "AI-powered plagiarism detection" },
];

const CASE_STUDIES = [
  {
    type: "National Research University", flag: "🇵🇱", institution: "University of Warsaw",
    color: "#1d4ed8",
    challenge: "Fragmented research data across 18 faculties. Grant management was manual, publication tracking impossible at scale.",
    solution: "Deployed Synaptiq Institution Twin + Knowledge Graph + Grant Lifecycle Manager.",
    results: [{ m: "40%", l: "reduction in reporting time" }, { m: "3×", l: "grant success rate" }, { m: "98%", l: "researcher adoption" }],
    quote: "For the first time we have a single source of truth for 4,200 researchers.",
    author: "Prof. Dr. M. Kowalska, Vice-Rector for Research",
  },
  {
    type: "University Medical Center", flag: "🇩🇪", institution: "Charité Berlin",
    color: "#059669",
    challenge: "Clinical research compliance and GDPR obligations consumed 60% of research office capacity.",
    solution: "Synaptiq Research Governance + Academic Integrity Engine + AI compliance advisor.",
    results: [{ m: "100%", l: "audit compliance" }, { m: "65%", l: "faster ethics approvals" }, { m: "€8.4M", l: "new grants year one" }],
    quote: "Our compliance burden dropped dramatically while our research output doubled.",
    author: "Dr. T. Hoffmann, Director of Research Office",
  },
  {
    type: "Technical University", flag: "🇸🇬", institution: "Nanyang Technological University",
    color: "#7c3aed",
    challenge: "Managing 45+ industry partnerships alongside academic research without a unified system.",
    solution: "Synaptiq Collaboration Hub + Reviewer Marketplace + Institution Intelligence Platform.",
    results: [{ m: "€12M", l: "new industry funding" }, { m: "45", l: "active partnerships" }, { m: "89", l: "patents filed" }],
    quote: "Synaptiq is the backbone of our research commercialization strategy.",
    author: "Prof. S. Chen, Dean of Research",
  },
];

const TESTIMONIALS = [
  {
    quote: "Synaptiq transformed how we manage our 4,200 researchers. For the first time, we have a single source of truth for our entire research ecosystem — from funding to publication to impact.",
    author: "Prof. Dr. Maria Kowalska", role: "Vice-Rector for Research, University of Warsaw", initials: "MK", color: NAVY,
  },
  {
    quote: "The grant management and collaboration features alone justified the investment. Our funding success rate doubled in the first year. I cannot imagine running our research office without it.",
    author: "Dr. James Okonkwo", role: "Director of Research Office, University of Cape Town", initials: "JO", color: "#1d4ed8",
  },
  {
    quote: "Our institution's research output is now fully traceable, from idea to publication to global impact. Synaptiq is the operating system our research strategy was built on.",
    author: "Prof. Sarah Chen", role: "Dean of Research, Nanyang Technological University", initials: "SC", color: "#059669",
  },
];

const INTEGRATIONS = [
  "ORCID", "Crossref", "OpenAlex", "Scopus", "Web of Science", "PubMed",
  "OpenAIRE", "ROR", "DOI Foundation", "Zenodo", "Dataverse", "GitHub",
  "Microsoft 365", "Google Workspace", "SAML SSO", "LDAP / Active Directory",
];

const TRUST_ORGS = [
  "Research Universities", "Medical Schools", "Engineering Institutes",
  "National Laboratories", "Government Research Agencies", "Innovation Centers",
  "Teaching Hospitals", "Funding Councils",
];

const FEATURE_SECTIONS = [
  {
    eyebrow: "Institution Twin",
    title: "See your institution in real time.",
    desc: "Your digital research university — live. Research health scores, faculty analytics, strategic planning, risk monitoring and resource optimization. All connected, always current.",
    points: ["Real-time research health monitoring", "Faculty performance analytics", "Strategic planning dashboards", "Risk detection & early warning", "Resource optimization engine"],
    IllusComp: TwinIllus, flip: false,
  },
  {
    eyebrow: "Research Governance",
    title: "Manage the complete research ecosystem.",
    desc: "From grant application to final publication. Projects, compliance, research integrity, open science, ORCID synchronization — all governed from one authoritative platform.",
    points: ["End-to-end grant lifecycle management", "Research integrity & ethics compliance", "Open Science & FAIR data alignment", "ORCID and DOI integration", "Complete funding output traceability"],
    IllusComp: GovernanceIllus, flip: true,
  },
  {
    eyebrow: "Teaching Excellence",
    title: "Elevate teaching quality across your institution.",
    desc: "Teaching analytics, course quality monitoring, faculty development, student outcomes and curriculum intelligence — connected to your research strategy.",
    points: ["Teaching analytics & quality KPIs", "Course performance monitoring", "Faculty development tracking", "Student outcome insights", "Curriculum intelligence engine"],
    IllusComp: TeachingIllus, flip: false,
  },
  {
    eyebrow: "AI Everywhere",
    title: "AI that knows your institution.",
    desc: "Nine specialized AI agents aware of your institutional context — literature review, statistical analysis, grant writing, teaching assistance and knowledge search. Secure inside your data perimeter.",
    points: ["AI trained on your research context", "Literature review & gap analysis", "Grant writing & review assistant", "Statistical analysis advisor", "Secure: zero training on your data"],
    IllusComp: AIIllus, flip: true,
  },
  {
    eyebrow: "Knowledge Graph",
    title: "Institutional memory. Everything connected.",
    desc: "A living knowledge graph of your institution — people, departments, projects, funding, publications, datasets, policies and partners. Searchable, navigable and always current.",
    points: ["35 node types, 26 relationship types", "Semantic search across all entities", "Cross-department discovery", "Automatic knowledge extraction", "Privacy-aware access controls"],
    IllusComp: KGIllus, flip: false,
  },
  {
    eyebrow: "Executive Dashboard",
    title: "Designed for institutional leaders.",
    desc: "A command center for Rectors, Vice-Rectors, Research Offices and Department Heads. KPIs, rankings, funding, teaching, open science scores and compliance — unified in one view.",
    points: ["Research productivity & output KPIs", "International ranking benchmarking", "Funding success rate monitoring", "Teaching & open science metrics", "Risk indicators & compliance status"],
    IllusComp: ExecutiveIllus, flip: true,
  },
];

/* ─── Page ──────────────────────────────────────────────────────────────────── */
export default function InstitutionsLanding() {
  useEffect(() => {
    document.title = "For Institutions — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  return (
    <MarketingLayout>

      {/* ── HERO ────────────────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", paddingTop: 96, paddingBottom: 96, borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 20 }}>
                Enterprise Platform · Higher Education
              </div>
              <h1 style={{ fontSize: "clamp(2.6rem, 5vw, 4.2rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.05, marginBottom: 22 }}>
                Build the Digital<br />Research University.
              </h1>
              <p style={{ fontSize: "1.1rem", color: SLATE, lineHeight: 1.75, maxWidth: 500, marginBottom: 36 }}>
                One secure platform for research, teaching, collaboration, governance and institutional intelligence. Built for universities, medical schools, research institutes and government agencies.
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 48 }}>
                <Link to="/contact"
                  style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: "0.9rem", fontWeight: 700, color: "#fff", background: NAVY, padding: "14px 28px", borderRadius: 10, textDecoration: "none" }}>
                  Request a Demo <ArrowRight size={15} strokeWidth={2} />
                </Link>
                <Link to="/platform"
                  style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: "0.9rem", fontWeight: 600, color: NAVY, border: `1.5px solid ${BORDER}`, padding: "13px 26px", borderRadius: 10, textDecoration: "none" }}>
                  Explore Platform
                </Link>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 24 }}>
                {[["4,200+","Researchers managed"],["98%","Platform adoption"],["GDPR","Compliant"]].map(([v,l],i) => (
                  <div key={i}>
                    <div style={{ fontSize: "1.3rem", fontWeight: 900, color: NAVY, letterSpacing: "-0.03em" }}>{v}</div>
                    <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>{l}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="hidden lg:flex justify-center">
              <CampusIllus />
            </div>
          </div>
        </div>
      </section>

      {/* ── TRUST BAR ───────────────────────────────────────────────────────── */}
      <section style={{ background: LIGHT, borderBottom: `1px solid ${BORDER}`, padding: "28px 0" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", textAlign: "center", marginBottom: 18 }}>
            Trusted by leading institutions worldwide
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 10 }}>
            {TRUST_ORGS.map((org, i) => (
              <span key={i} style={{ fontSize: "0.72rem", fontWeight: 600, color: SLATE, background: "#fff", border: `1px solid ${BORDER}`, padding: "6px 16px", borderRadius: 20 }}>
                {org}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── VALUE GRID ──────────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", padding: "96px 0", borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 14 }}>Why Synaptiq</div>
            <h2 style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.1 }}>
              One platform. Every dimension<br className="hidden lg:block" /> of institutional excellence.
            </h2>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {VALUE_CARDS.map(({ icon: Icon, title, desc, color }, i) => (
              <div key={i} style={{ background: LIGHT, border: `1px solid ${BORDER}`, borderRadius: 16, padding: "28px 24px", transition: "box-shadow 200ms, transform 200ms" }}
                onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 16px 48px rgba(15,40,71,0.1)"; e.currentTarget.style.transform = "translateY(-4px)"; }}
                onMouseLeave={e => { e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "none"; }}
              >
                <div style={{ width: 48, height: 48, borderRadius: 12, background: `${color}12`, border: `1px solid ${color}22`, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 20 }}>
                  <Icon size={22} strokeWidth={1.5} style={{ color }} />
                </div>
                <div style={{ fontSize: "1rem", fontWeight: 800, color: "#0a0f1a", marginBottom: 10, letterSpacing: "-0.02em" }}>{title}</div>
                <p style={{ fontSize: "0.82rem", color: SLATE, lineHeight: 1.7 }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── PLATFORM SHOWCASE ───────────────────────────────────────────────── */}
      <section style={{ background: LIGHT, padding: "96px 0", borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div style={{ textAlign: "center", marginBottom: 56 }}>
            <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 14 }}>Platform</div>
            <h2 style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.1, marginBottom: 14 }}>
              Your institution at a glance.
            </h2>
            <p style={{ fontSize: "1rem", color: SLATE, maxWidth: 520, margin: "0 auto" }}>
              A unified intelligence layer across research, teaching, governance and strategy. Built for how research universities actually work.
            </p>
          </div>
          <InstitutionMockup />
        </div>
      </section>

      {/* ── STATS BAND ──────────────────────────────────────────────────────── */}
      <section style={{ background: NAVY, padding: "80px 0" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-12">
            <StatCtr target={98}  suffix="%" label="Research visibility improvement" sub="Avg. across institutions" />
            <StatCtr target={65}  suffix="%" label="Less administrative workload"    sub="Research office staff" />
            <StatCtr target={3}   suffix="×" label="Faster collaboration"            sub="Cross-institution projects" />
            <StatCtr target={100} suffix="%" label="Institutional traceability"      sub="From idea to impact" />
          </div>
        </div>
      </section>

      {/* ── FEATURE SECTIONS ────────────────────────────────────────────────── */}
      {FEATURE_SECTIONS.map(({ eyebrow, title, desc, points, IllusComp, flip }, idx) => {
        const textCol = (
          <div>
            <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 14 }}>{eyebrow}</div>
            <h2 style={{ fontSize: "clamp(1.75rem, 3.5vw, 2.6rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.1, marginBottom: 18 }}>{title}</h2>
            <p style={{ fontSize: "0.95rem", color: SLATE, lineHeight: 1.8, marginBottom: 28 }}>{desc}</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {points.map((pt, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ width: 20, height: 20, borderRadius: "50%", background: `${NAVY}12`, border: `1px solid ${NAVY}22`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Check size={11} strokeWidth={2.5} style={{ color: NAVY }} />
                  </div>
                  <span style={{ fontSize: "0.83rem", color: "#0a0f1a" }}>{pt}</span>
                </div>
              ))}
            </div>
          </div>
        );
        const illustCol = <div><IllusComp /></div>;
        return (
          <section key={idx} style={{ background: idx % 2 === 0 ? "#fff" : LIGHT, padding: "96px 0", borderBottom: `1px solid ${BORDER}` }}>
            <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
              <div className="grid lg:grid-cols-2 gap-16 items-center">
                {flip ? illustCol : textCol}
                {flip ? textCol : illustCol}
              </div>
            </div>
          </section>
        );
      })}

      {/* ── SECURITY ────────────────────────────────────────────────────────── */}
      <section style={{ background: LIGHT, padding: "96px 0", borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 14 }}>Security</div>
            <h2 style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.1, marginBottom: 14 }}>
              Enterprise-grade security.<br className="hidden lg:block" /> For the world's most sensitive research.
            </h2>
            <p style={{ fontSize: "1rem", color: SLATE, maxWidth: 500, margin: "0 auto" }}>
              Built to meet the security and compliance requirements of research universities, medical institutions and government agencies.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {SECURITY_FEATURES.map(({ icon: Icon, title, desc }, i) => (
              <div key={i} style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 12, padding: 20 }}>
                <Icon size={20} strokeWidth={1.5} style={{ color: NAVY, marginBottom: 12 }} />
                <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 6 }}>{title}</div>
                <div style={{ fontSize: "0.75rem", color: SLATE }}>{desc}</div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", justifyContent: "center", flexWrap: "wrap", gap: 8, marginTop: 40 }}>
            {["GDPR Aligned","TLS 1.3 Encrypted","SOC 2 (Coming Soon)","ISO 27001 Alignment","ORCID Integrated","Zero AI Training"].map((b) => (
              <span key={b} style={{ fontSize: "0.62rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: SLATE, border: `1px solid ${BORDER}`, background: "#fff", padding: "4px 12px", borderRadius: 4 }}>{b}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ── CASE STUDIES ────────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", padding: "96px 0", borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 14 }}>Case Studies</div>
            <h2 style={{ fontSize: "clamp(2rem, 4vw, 3rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.1 }}>
              Institutions already operating<br className="hidden lg:block" /> on a different level.
            </h2>
          </div>
          <div className="grid lg:grid-cols-3 gap-6">
            {CASE_STUDIES.map((cs, i) => (
              <div key={i} style={{ background: LIGHT, border: `1px solid ${BORDER}`, borderRadius: 18, overflow: "hidden" }}>
                <div style={{ height: 5, background: cs.color }} />
                <div style={{ padding: "28px 28px 0" }}>
                  <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: cs.color, marginBottom: 8 }}>{cs.type}</div>
                  <div style={{ fontSize: "1.1rem", fontWeight: 900, color: "#0a0f1a", marginBottom: 20, letterSpacing: "-0.025em" }}>
                    {cs.flag} {cs.institution}
                  </div>
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: "0.62rem", fontWeight: 700, color: "#94a3b8", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>Challenge</div>
                    <p style={{ fontSize: "0.78rem", color: SLATE, lineHeight: 1.65 }}>{cs.challenge}</p>
                  </div>
                  <div style={{ marginBottom: 20 }}>
                    <div style={{ fontSize: "0.62rem", fontWeight: 700, color: "#94a3b8", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>Solution</div>
                    <p style={{ fontSize: "0.78rem", color: SLATE, lineHeight: 1.65 }}>{cs.solution}</p>
                  </div>
                  <div style={{ display: "flex", gap: 6, marginBottom: 24 }}>
                    {cs.results.map((r, j) => (
                      <div key={j} style={{ flex: 1, background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 9, padding: "10px 8px", textAlign: "center" }}>
                        <div style={{ fontSize: "1.1rem", fontWeight: 900, color: cs.color, letterSpacing: "-0.03em" }}>{r.m}</div>
                        <div style={{ fontSize: "0.6rem", color: "#94a3b8", marginTop: 3, lineHeight: 1.4 }}>{r.l}</div>
                      </div>
                    ))}
                  </div>
                </div>
                <div style={{ padding: "20px 28px 28px", borderTop: `1px solid ${BORDER}` }}>
                  <p style={{ fontSize: "0.82rem", color: "#0a0f1a", fontStyle: "italic", lineHeight: 1.65, marginBottom: 10 }}>"{cs.quote}"</p>
                  <div style={{ fontSize: "0.72rem", color: SLATE, fontWeight: 600 }}>{cs.author}</div>
                </div>
              </div>
            ))}
          </div>
          <div style={{ textAlign: "center", marginTop: 40 }}>
            <Link to="/resources/customer-stories"
              style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: "0.85rem", fontWeight: 700, color: NAVY, textDecoration: "none" }}>
              Read all customer stories <ArrowRight size={14} strokeWidth={2.5} />
            </Link>
          </div>
        </div>
      </section>

      {/* ── TESTIMONIALS ────────────────────────────────────────────────────── */}
      <section style={{ background: LIGHT, padding: "96px 0", borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div style={{ textAlign: "center", marginBottom: 56 }}>
            <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 14 }}>Testimonials</div>
            <h2 style={{ fontSize: "clamp(1.75rem, 3.5vw, 2.8rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.1 }}>
              What institutional leaders say.
            </h2>
          </div>
          <div className="grid lg:grid-cols-3 gap-6">
            {TESTIMONIALS.map((t, i) => (
              <div key={i} style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 18, padding: "36px 32px" }}>
                <div style={{ fontSize: "2.5rem", color: "#e2e8f0", lineHeight: 1, marginBottom: 20, fontFamily: "Georgia, serif" }}>"</div>
                <p style={{ fontSize: "0.9rem", color: "#0a0f1a", lineHeight: 1.75, marginBottom: 28 }}>{t.quote}</p>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ width: 42, height: 42, borderRadius: "50%", background: t.color, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: "0.75rem", fontWeight: 700, flexShrink: 0 }}>
                    {t.initials}
                  </div>
                  <div>
                    <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#0a0f1a" }}>{t.author}</div>
                    <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: 2 }}>{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── INTEGRATIONS ────────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", padding: "96px 0", borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div style={{ textAlign: "center", marginBottom: 56 }}>
            <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 14 }}>Integrations</div>
            <h2 style={{ fontSize: "clamp(1.75rem, 3.5vw, 2.8rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.1, marginBottom: 14 }}>
              Connects with your existing<br className="hidden lg:block" /> academic infrastructure.
            </h2>
            <p style={{ fontSize: "1rem", color: SLATE, maxWidth: 480, margin: "0 auto" }}>
              Synaptiq integrates with the tools universities already rely on — from research databases to identity providers.
            </p>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 10 }}>
            {INTEGRATIONS.map((name, i) => (
              <div key={i} style={{
                background: LIGHT, border: `1px solid ${BORDER}`, borderRadius: 10,
                padding: "10px 20px", fontSize: "0.82rem", fontWeight: 600, color: "#0a0f1a",
                transition: "border-color 150ms, box-shadow 150ms",
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = NAVY; e.currentTarget.style.boxShadow = `0 4px 16px ${NAVY}14`; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.boxShadow = "none"; }}
              >{name}</div>
            ))}
          </div>
          <div style={{ textAlign: "center", marginTop: 32 }}>
            <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
              + custom integrations via REST API, webhooks and SCIM provisioning
            </div>
          </div>
        </div>
      </section>

      {/* ── BOTTOM CTA ──────────────────────────────────────────────────────── */}
      <section style={{ background: NAVY, padding: "100px 0" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 text-center">
          <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)", marginBottom: 20 }}>
            Enterprise Platform
          </div>
          <h2 style={{ fontSize: "clamp(2.2rem, 5vw, 3.8rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#fff", lineHeight: 1.05, marginBottom: 20 }}>
            Transform your institution<br className="hidden lg:block" /> with Synaptiq.
          </h2>
          <p style={{ fontSize: "1.1rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.75, maxWidth: 540, margin: "0 auto 44px" }}>
            One platform for research, teaching and institutional intelligence. Join the world's leading research universities already operating on Synaptiq.
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 12 }}>
            <Link to="/contact"
              style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: "0.95rem", fontWeight: 700, color: NAVY, background: "#fff", padding: "15px 32px", borderRadius: 10, textDecoration: "none" }}>
              Request a Demo <ArrowRight size={16} strokeWidth={2} />
            </Link>
            <Link to="/register"
              style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: "0.95rem", fontWeight: 600, color: "#fff", border: "1.5px solid rgba(255,255,255,0.25)", padding: "14px 30px", borderRadius: 10, textDecoration: "none" }}>
              Start Free
            </Link>
          </div>
          <div style={{ marginTop: 40, display: "flex", justifyContent: "center", gap: 24, flexWrap: "wrap" }}>
            {["No setup fee","GDPR compliant","Dedicated onboarding","Enterprise SLA"].map((f, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.78rem", color: "rgba(255,255,255,0.5)" }}>
                <Check size={13} strokeWidth={2.5} style={{ color: "rgba(255,255,255,0.4)" }} /> {f}
              </div>
            ))}
          </div>
        </div>
      </section>

    </MarketingLayout>
  );
}

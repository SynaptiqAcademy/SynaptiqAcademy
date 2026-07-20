import React, { useState, useEffect, useReducer, useRef, useMemo } from "react";
import { getDailyWelcomeMessage, getGreeting } from "@/lib/welcomeEngine";
import { Link } from "react-router-dom";
import { AIWorkspaceLayout } from "@/layouts";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import {
  Plus, ChevronLeft, ChevronRight, Pin, Archive, Trash2, RefreshCw,
  Send, Mic, BookOpen, Search, Users, GraduationCap, BarChart2, User,
  Zap, FileText, Brain, X, AlertCircle, Sparkles, ChevronDown, ChevronUp,
  MessageSquare, Edit2, Award, Copy, Star, Eye, ArrowRight, Shield, Check,
  MoreHorizontal, Info, AlertTriangle, CheckCircle, Clock, ExternalLink,
  Download, Bookmark,
} from "lucide-react";
import { toast } from "@/components/ui/sonner";
import { ACCENT, NAVY, WARM } from "@/lib/tokens";

// ─── AI Nav ───────────────────────────────────────────────────────────────────


// ─── Brand ────────────────────────────────────────────────────────────────────
const NAVY2  = "#0a1d38";
const BORDER = "#E4E8EF";

// ─── Callout configs ──────────────────────────────────────────────────────────
const CALLOUT_CONFIGS = {
  info:           { Icon:Info,          label:"Information",      bg:"#EFF6FF", border:"#3B82F6", color:"#1D4ED8" },
  warning:        { Icon:AlertTriangle, label:"Warning",          bg:"#FFFBEB", border:"#F59E0B", color:"#92400E" },
  recommendation: { Icon:CheckCircle,   label:"Recommendation",   bg:"#F0FDF4", border:"#22C55E", color:"#166534" },
  insight:        { Icon:Sparkles,      label:"Research Insight", bg:"#FAF5FF", border:"#A855F7", color:"#7E22CE" },
  critical:       { Icon:AlertCircle,   label:"Critical Issue",   bg:"#FFF1F2", border:"#F43F5E", color:"#BE123C" },
  best_practice:  { Icon:Star,          label:"Best Practice",    bg:"#FEFCE8", border:"#EAB308", color:"#854D0E" },
};

// ─── Loading stages ───────────────────────────────────────────────────────────
const LOAD_STAGES = [
  "Reviewing your query…",
  "Analysing research context…",
  "Synthesising findings…",
  "Preparing research report…",
];

// ─── Agent config ─────────────────────────────────────────────────────────────
const AGENT_COLORS = {
  research:      { bg:"bg-violet-100", text:"text-violet-700", dot:"bg-violet-500" },
  publication:   { bg:"bg-blue-100",   text:"text-blue-700",   dot:"bg-blue-500"   },
  journal:       { bg:"bg-sky-100",    text:"text-sky-700",    dot:"bg-sky-500"    },
  grant:         { bg:"bg-emerald-100",text:"text-emerald-700",dot:"bg-emerald-500"},
  collaboration: { bg:"bg-orange-100", text:"text-orange-700", dot:"bg-orange-500" },
  teaching:      { bg:"bg-amber-100",  text:"text-amber-700",  dot:"bg-amber-500"  },
  analytics:     { bg:"bg-cyan-100",   text:"text-cyan-700",   dot:"bg-cyan-500"   },
  profile:       { bg:"bg-rose-100",   text:"text-rose-700",   dot:"bg-rose-500"   },
  general:       { bg:"bg-slate-100",  text:"text-slate-700",  dot:"bg-slate-400"  },
  auto:          { bg:"bg-slate-100",  text:"text-slate-700",  dot:"bg-violet-500" },
};

const SIDEBAR_DOT = {
  research:"#a78bfa", publication:"#60a5fa", journal:"#38bdf8",
  grant:"#34d399", collaboration:"#fb923c", teaching:"#fbbf24",
  analytics:"#22d3ee", profile:"#fb7185", general:"#94a3b8", auto:"#a78bfa",
};

const AGENTS = [
  { id:"auto",          label:"Auto",          icon:Sparkles,      description:"Let Synaptiq choose the best agent" },
  { id:"research",      label:"Research",      icon:Brain,         description:"Research design, methodology, gap analysis" },
  { id:"publication",   label:"Publication",   icon:FileText,      description:"Manuscript review, writing, submission" },
  { id:"journal",       label:"Journal",       icon:BookOpen,      description:"Journal matching, rankings, strategy" },
  { id:"grant",         label:"Grant",         icon:Zap,           description:"Grant eligibility, proposals, funding" },
  { id:"collaboration", label:"Collaboration", icon:Users,         description:"Finding collaborators, research networks" },
  { id:"teaching",      label:"Teaching",      icon:GraduationCap, description:"Lesson planning, assessment, pedagogy" },
  { id:"analytics",     label:"Analytics",     icon:BarChart2,     description:"Research impact, citations, benchmarking" },
  { id:"profile",       label:"Profile",       icon:User,          description:"Career development, reputation" },
];

const RESEARCH_WORKFLOWS = [
  { id:"lit",    icon:BookOpen,      label:"Literature Review",     desc:"Synthesise research and map key themes",   agent:"research",    prompt:"Help me conduct a systematic literature review on " },
  { id:"gap",    icon:Search,        label:"Research Gap Analysis", desc:"Discover unexplored areas in your field",  agent:"research",    prompt:"Identify research gaps in the field of " },
  { id:"design", icon:Brain,         label:"Research Design",       desc:"Design rigorous study frameworks",         agent:"research",    prompt:"Help me design a research study to investigate " },
  { id:"meth",   icon:FileText,      label:"Methodology Review",    desc:"Evaluate and strengthen your methods",     agent:"publication", prompt:"Review the methodology section of my study on " },
  { id:"stats",  icon:BarChart2,     label:"Statistical Analysis",  desc:"Guidance on analysis and reporting",       agent:"analytics",   prompt:"Help me choose appropriate statistical methods for " },
  { id:"jrnl",   icon:Star,          label:"Journal Matching",      desc:"Find the best journals for your work",     agent:"journal",     prompt:"Recommend journals for my manuscript about " },
  { id:"grant",  icon:Zap,           label:"Grant Discovery",       desc:"Match research to funding opportunities",  agent:"grant",       prompt:"Find funding opportunities for my research on " },
  { id:"peer",   icon:Eye,           label:"Peer Review",           desc:"Simulate rigorous academic peer review",   agent:"publication", prompt:"Simulate peer review feedback for my manuscript on " },
  { id:"write",  icon:Edit2,         label:"Academic Writing",      desc:"Improve clarity, style, and impact",       agent:"publication", prompt:"Help me improve the writing quality of " },
  { id:"teach",  icon:GraduationCap, label:"Teaching Assistant",    desc:"Design lessons and learning materials",    agent:"teaching",    prompt:"Help me create teaching materials for " },
];

const PLACEHOLDERS = [
  "Describe your research challenge…",
  "Ask for a literature review on any topic…",
  "What research gaps exist in your field?",
  "Find the best journals for your manuscript…",
  "Compare methodological approaches…",
  "Identify funding opportunities for your research…",
  "Simulate peer review of your manuscript…",
  "Design a rigorous study framework…",
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function relativeTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return mins + "m ago";
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return hrs + "h ago";
  const days = Math.floor(hrs / 24);
  return days < 7 ? days + "d ago" : d.toLocaleDateString("en-US",{month:"short",day:"numeric"});
}

function truncate(str, n) {
  n = n || 34;
  if (!str) return "New session";
  return str.length > n ? str.slice(0,n) + "…" : str;
}

function greeting(name) {
  const h = new Date().getHours();
  const time = h < 12 ? "morning" : h < 17 ? "afternoon" : "evening";
  return "Good " + time + (name ? ", " + name : "") + ".";
}

function readingTime(text) {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  if (words < 80) return null;
  const mins = Math.max(1, Math.round(words / 250));
  return "~" + mins + " min read";
}

function parseSections(text) {
  if (!/^## /m.test(text)) return null;
  var parts = text.split(/^(?=## )/m);
  var intro = !parts[0].startsWith("## ") ? parts[0].trim() : "";
  var raw = intro ? parts.slice(1) : parts;
  var sections = raw
    .filter(function(p) { return p.startsWith("## "); })
    .map(function(p) {
      var lines = p.split("\n");
      return {
        heading: lines[0].replace(/^## /, "").trim(),
        content: lines.slice(1).join("\n").trim(),
      };
    });
  return sections.length >= 2 ? { intro: intro, sections: sections } : null;
}

function extractCitations(text) {
  var refMatch = text.match(/^#{1,3}\s*(References|Bibliography|Sources|Works Cited)\s*$/im);
  if (refMatch) {
    var idx = text.indexOf(refMatch[0]);
    var main = text.slice(0, idx).trim();
    var block = text.slice(idx + refMatch[0].length).trim();
    var entries = block.split("\n").map(function(l){return l.trim();}).filter(function(l){return l.length > 15;});
    if (entries.length >= 1) return { main: main, citations: entries };
  }
  var lines = text.split("\n");
  var refLines = [];
  lines.forEach(function(l, i) {
    if (/^\[\d+\]/.test(l.trim())) refLines.push({ l: l.trim(), i: i });
  });
  if (refLines.length >= 2 && refLines[0].i > lines.length * 0.55) {
    return {
      main: lines.slice(0, refLines[0].i).join("\n").trim(),
      citations: refLines.map(function(r){return r.l;}),
    };
  }
  return null;
}

function detectCalloutType(line) {
  var m1 = line.match(/^\[!(INFO|WARNING|RECOMMENDATION|INSIGHT|CRITICAL|BEST.PRACTICE)\]/i);
  if (m1) {
    var t = m1[1].toUpperCase();
    if (t === "INFO") return "info";
    if (t === "WARNING") return "warning";
    if (t === "RECOMMENDATION") return "recommendation";
    if (t === "INSIGHT") return "insight";
    if (t === "CRITICAL") return "critical";
    return "best_practice";
  }
  var m2 = line.match(/^\*\*(Info(?:rmation)?|Warning|Recommendation|Research Insight|Critical(?:\s+Issue)?|Best Practice):\*\*/i);
  if (m2) {
    var s = m2[1].toLowerCase();
    if (s.startsWith("info")) return "info";
    if (s.startsWith("warn")) return "warning";
    if (s.startsWith("rec")) return "recommendation";
    if (s.includes("insight")) return "insight";
    if (s.startsWith("crit")) return "critical";
    return "best_practice";
  }
  return null;
}

// ─── State reducer ────────────────────────────────────────────────────────────

var initialState = {
  conversations:[],activeConvId:null,messages:[],loading:false,sending:false,
  context:null,insights:[],memory:[],agents:[],
  leftPanelOpen:true,rightPanelOpen:true,inputText:"",selectedAgent:"auto",
};

function reducer(state, action) {
  switch (action.type) {
    case "SET_CONVERSATIONS": return Object.assign({},state,{conversations:action.payload});
    case "SET_ACTIVE_CONV":   return Object.assign({},state,{activeConvId:action.payload,messages:[]});
    case "SET_MESSAGES":      return Object.assign({},state,{messages:action.payload});
    case "ADD_MESSAGE":       return Object.assign({},state,{messages:state.messages.concat([action.payload])});
    case "UPDATE_LAST_MESSAGE":
      return Object.assign({},state,{messages:state.messages.map(function(m,idx){return idx===state.messages.length-1?Object.assign({},m,action.payload):m;})});
    case "REPLACE_MESSAGE":
      return Object.assign({},state,{messages:state.messages.map(function(m){return m.id===action.id?Object.assign({},m,action.payload):m;})});
    case "SET_LOADING":  return Object.assign({},state,{loading:action.payload});
    case "SET_SENDING":  return Object.assign({},state,{sending:action.payload});
    case "SET_CONTEXT":  return Object.assign({},state,{context:action.payload});
    case "SET_INSIGHTS": return Object.assign({},state,{insights:action.payload});
    case "SET_MEMORY":   return Object.assign({},state,{memory:action.payload});
    case "SET_AGENTS":   return Object.assign({},state,{agents:action.payload});
    case "TOGGLE_LEFT":  return Object.assign({},state,{leftPanelOpen:!state.leftPanelOpen});
    case "TOGGLE_RIGHT": return Object.assign({},state,{rightPanelOpen:!state.rightPanelOpen});
    case "SET_INPUT":    return Object.assign({},state,{inputText:action.payload});
    case "SET_AGENT":    return Object.assign({},state,{selectedAgent:action.payload});
    case "UPDATE_CONV_TITLE":
      return Object.assign({},state,{conversations:state.conversations.map(function(c){return c.id===action.id?Object.assign({},c,{title:action.title}):c;})});
    case "ADD_CONV": {
      var p = Object.assign({},action.payload,{id:action.payload.id||action.payload._id});
      return Object.assign({},state,{conversations:[p].concat(state.conversations),activeConvId:p.id,messages:[]});
    }
    case "REMOVE_CONV":
      return Object.assign({},state,{
        conversations:state.conversations.filter(function(c){return c.id!==action.id;}),
        activeConvId:state.activeConvId===action.id?null:state.activeConvId,
        messages:state.activeConvId===action.id?[]:state.messages,
      });
    case "ADD_MEMORY":    return Object.assign({},state,{memory:[action.payload].concat(state.memory)});
    case "REMOVE_MEMORY": return Object.assign({},state,{memory:state.memory.filter(function(m){return m.id!==action.id;})});
    case "CLEAR_MEMORY":  return Object.assign({},state,{memory:[]});
    default: return state;
  }
}

// ─── Inline markdown ──────────────────────────────────────────────────────────

function renderInline(text) {
  var parts = [];
  var rem = text;
  var k = 0;
  while (rem.length > 0) {
    var bold   = rem.match(/^(.*?)\*\*(.+?)\*\*(.*)/s);
    var italic = rem.match(/^(.*?)\*(.+?)\*(.*)/s);
    var code   = rem.match(/^(.*?)`(.+?)`(.*)/s);
    var cands  = [];
    if (bold)   cands.push({type:"bold",   match:bold,   start:bold[1].length});
    if (italic) cands.push({type:"italic", match:italic, start:italic[1].length});
    if (code)   cands.push({type:"code",   match:code,   start:code[1].length});
    if (!cands.length) { parts.push(React.createElement(React.Fragment,{key:k++},rem)); break; }
    cands.sort(function(a,b){return a.start-b.start;});
    var w = cands[0];
    var before = w.match[1], content = w.match[2], after = w.match[3];
    if (before) parts.push(React.createElement(React.Fragment,{key:k++},before));
    if (w.type==="bold")   parts.push(React.createElement("strong",{key:k++,style:{fontWeight:700,color:"#0f172a"}},renderInline(content)));
    if (w.type==="italic") parts.push(React.createElement("em",{key:k++},renderInline(content)));
    if (w.type==="code")   parts.push(React.createElement("code",{key:k++,style:{background:"#F1F5F9",color:"#1e293b",padding:"1px 6px",borderRadius:4,fontFamily:"monospace",fontSize:"0.83em"}},content));
    rem = after;
  }
  return parts;
}

// ═══════════════════════════════════════════════════════════════════════════════
// RENDERING ENGINE
// ═══════════════════════════════════════════════════════════════════════════════

function CalloutBlock({ type, lines }) {
  var cfg = CALLOUT_CONFIGS[type] || CALLOUT_CONFIGS.info;
  var Icon = cfg.Icon;
  var text = lines.join(" ").trim();
  return (
    <div style={{display:"flex",gap:12,background:cfg.bg,borderLeft:"4px solid "+cfg.border,borderRadius:"0 10px 10px 0",padding:"12px 16px",margin:"12px 0"}}>
      <div style={{flexShrink:0,paddingTop:1}}><Icon size={16} style={{color:cfg.border}}/></div>
      <div>
        <div style={{fontSize:"0.68rem",fontWeight:700,letterSpacing:"0.1em",textTransform:"uppercase",color:cfg.color,marginBottom:5}}>{cfg.label}</div>
        <div style={{fontSize:"0.88rem",color:"#374151",lineHeight:1.72}}>{renderInline(text)}</div>
      </div>
    </div>
  );
}

function CodeBlock({ lang, code }) {
  var [copied, setCopied] = useState(false);
  var lines = code.split("\n");
  var showNums = lines.length > 5;
  function handleCopy() {
    navigator.clipboard && navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(function(){setCopied(false);}, 2000);
  }
  return (
    <div style={{margin:"14px 0",borderRadius:10,overflow:"hidden",border:"1px solid "+BORDER}}>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"7px 14px",background:"#1E2937"}}>
        <span style={{fontSize:"0.69rem",fontFamily:"monospace",color:"#94a3b8",background:"rgba(255,255,255,0.08)",padding:"2px 8px",borderRadius:4}}>{lang||"code"}</span>
        <button onClick={handleCopy} style={{background:"none",border:"none",cursor:"pointer",display:"flex",alignItems:"center",gap:5,fontSize:"0.72rem",color:copied?"#4ade80":"#64748b",transition:"color 150ms"}}>
          {copied ? <Check size={11}/> : <Copy size={11}/>}{copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div style={{background:"#0f1923",display:"flex",overflowX:"auto"}}>
        {showNums && (
          <div style={{padding:"14px 10px 14px 14px",color:"#334155",fontSize:"0.76rem",fontFamily:"monospace",lineHeight:1.65,userSelect:"none",borderRight:"1px solid rgba(255,255,255,0.06)",textAlign:"right",flexShrink:0,minWidth:34}}>
            {lines.map(function(_,i){return <div key={i}>{i+1}</div>;})}
          </div>
        )}
        <pre style={{flex:1,padding:"14px 18px",fontSize:"0.82rem",fontFamily:"monospace",color:"#e2e8f0",lineHeight:1.65,margin:0,overflowX:"auto"}}>{code}</pre>
      </div>
    </div>
  );
}

function AcademicTable({ rows }) {
  var [copied, setCopied] = useState(false);
  if (!rows.length) return null;
  function parseRow(r) { return r.replace(/^\||\|$/g,"").split("|").map(function(c){return c.trim();}); }
  var header = parseRow(rows[0]);
  var body   = rows.filter(function(r){return !/^\|[-| :]+\|$/.test(r);}).slice(1);
  function handleCopy() {
    var tsv = [rows[0]].concat(body).map(function(r){return parseRow(r).join("\t");}).join("\n");
    navigator.clipboard && navigator.clipboard.writeText(tsv);
    setCopied(true);
    setTimeout(function(){setCopied(false);}, 2000);
  }
  return (
    <div style={{margin:"16px 0",borderRadius:10,border:"1px solid "+BORDER,overflow:"hidden"}}>
      <div style={{display:"flex",justifyContent:"flex-end",padding:"5px 10px",background:WARM,borderBottom:"1px solid "+BORDER}}>
        <button onClick={handleCopy} style={{background:"none",border:"none",cursor:"pointer",display:"flex",alignItems:"center",gap:4,fontSize:"0.71rem",color:copied?"#059669":"#94a3b8",transition:"color 150ms"}}>
          {copied ? <Check size={10}/> : <Copy size={10}/>}{copied ? "Copied" : "Copy table"}
        </button>
      </div>
      <div style={{overflowX:"auto"}}>
        <table style={{width:"100%",borderCollapse:"collapse",fontSize:"0.85rem"}}>
          <thead>
            <tr style={{background:WARM}}>
              {header.map(function(h,i){return (
                <th key={i} style={{padding:"9px 14px",textAlign:"left",fontWeight:600,color:NAVY,borderBottom:"1px solid "+BORDER,whiteSpace:"nowrap",fontSize:"0.81rem",letterSpacing:"0.01em"}}>{renderInline(h)}</th>
              );})}
            </tr>
          </thead>
          <tbody>
            {body.map(function(row,ri){return (
              <tr key={ri} style={{background:ri%2===0?"#fff":"#F8FAFC"}}>
                {parseRow(row).map(function(cell,ci){return (
                  <td key={ci} style={{padding:"8px 14px",color:"#374151",borderBottom:ri<body.length-1?"1px solid #F1F5F9":"none",lineHeight:1.55,verticalAlign:"top",fontSize:"0.85rem"}}>{renderInline(cell)}</td>
                );})}
              </tr>
            );})}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CitationList({ citations }) {
  var [expanded, setExpanded] = useState(false);
  var PREVIEW = 3;
  var shown = expanded ? citations : citations.slice(0, PREVIEW);
  return (
    <div style={{borderTop:"1px solid "+BORDER,padding:"12px 22px 14px"}}>
      <div style={{fontSize:"0.65rem",fontWeight:700,letterSpacing:"0.12em",textTransform:"uppercase",color:"#94a3b8",marginBottom:10}}>
        References ({citations.length})
      </div>
      <div style={{display:"flex",flexDirection:"column",gap:6}}>
        {shown.map(function(cite,idx){
          var clean = cite.replace(/^\[\d+\]\s*|^\d+\.\s*/,"").trim();
          var doiM  = clean.match(/(?:doi:|https?:\/\/doi\.org\/)(10\.\S+)/i);
          var doi   = doiM ? doiM[1] : null;
          return (
            <div key={idx} style={{display:"flex",gap:8,alignItems:"flex-start",padding:"8px 10px",background:WARM,borderRadius:8,border:"1px solid "+BORDER}}>
              <span style={{flexShrink:0,width:20,height:20,borderRadius:5,background:"#fff",border:"1px solid "+BORDER,fontSize:"0.64rem",fontWeight:700,color:"#64748b",display:"flex",alignItems:"center",justifyContent:"center"}}>{idx+1}</span>
              <span style={{flex:1,fontSize:"0.79rem",color:"#374151",lineHeight:1.55}}>{doi ? clean.replace(/(?:doi:|https?:\/\/doi\.org\/)10\.\S+/gi,"").trim() : clean}</span>
              {doi && (
                <a href={"https://doi.org/"+doi} target="_blank" rel="noopener noreferrer"
                  style={{flexShrink:0,display:"flex",alignItems:"center",gap:3,fontSize:"0.7rem",color:NAVY,fontWeight:600,textDecoration:"none",background:"#fff",border:"1px solid "+BORDER,borderRadius:5,padding:"2px 7px",whiteSpace:"nowrap"}}>
                  DOI <ExternalLink size={9}/>
                </a>
              )}
            </div>
          );
        })}
      </div>
      {citations.length > PREVIEW && (
        <button onClick={function(){setExpanded(function(v){return !v;});}}
          style={{marginTop:8,background:"none",border:"none",cursor:"pointer",fontSize:"0.76rem",color:NAVY,fontWeight:600,display:"flex",alignItems:"center",gap:4}}>
          {expanded ? <><ChevronUp size={12}/>Show less</> : <><ChevronDown size={12}/>Show all {citations.length} references</>}
        </button>
      )}
    </div>
  );
}

function CollapsibleSection({ heading, children, defaultOpen }) {
  defaultOpen = defaultOpen !== false;
  var [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{marginBottom:8,border:"1px solid "+BORDER,borderRadius:10,overflow:"hidden"}}>
      <button
        onClick={function(){setOpen(function(v){return !v;});}}
        style={{width:"100%",display:"flex",alignItems:"center",justifyContent:"space-between",padding:"11px 18px",background:open?WARM:"#fff",border:"none",cursor:"pointer",textAlign:"left",borderBottom:open?"1px solid "+BORDER:"none",transition:"background 150ms"}}
        onMouseEnter={function(e){e.currentTarget.style.background=WARM;}}
        onMouseLeave={function(e){e.currentTarget.style.background=open?WARM:"#fff";}}
      >
        <span style={{fontFamily:"Georgia,serif",fontSize:"0.94rem",fontWeight:700,color:NAVY,lineHeight:1.3}}>{heading}</span>
        <span style={{flexShrink:0,color:"#94a3b8",marginLeft:12}}>{open ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}</span>
      </button>
      {open && <div style={{padding:"18px 20px 14px"}}>{children}</div>}
    </div>
  );
}

function MiniTOC({ sections }) {
  return (
    <div style={{display:"flex",flexWrap:"wrap",gap:6,padding:"9px 20px",borderBottom:"1px solid "+BORDER,background:"#FAFBFC",alignItems:"center"}}>
      <span style={{fontSize:"0.62rem",fontWeight:700,letterSpacing:"0.1em",textTransform:"uppercase",color:"#94a3b8",marginRight:4}}>Contents</span>
      {sections.map(function(s,i){return (
        <span key={i} style={{fontSize:"0.74rem",color:NAVY,background:"#fff",border:"1px solid "+BORDER,borderRadius:6,padding:"3px 9px",fontWeight:500,lineHeight:1.4}}>{s.heading}</span>
      );})}
    </div>
  );
}

function ResponseHeader({ agent, time }) {
  var agentInfo = AGENTS.find(function(a){return a.id===agent;});
  return (
    <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"10px 18px",borderBottom:"1px solid "+BORDER,background:"#FAFBFC"}}>
      <div style={{display:"flex",alignItems:"center",gap:8}}>
        <div style={{width:24,height:24,borderRadius:7,background:NAVY,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
          <Sparkles size={11} style={{color:"#fff"}}/>
        </div>
        <span style={{fontSize:"0.75rem",fontWeight:700,color:NAVY,letterSpacing:"0.02em"}}>Synaptiq AI</span>
        {agent && agent!=="auto" && agentInfo && (
          <>
            <span style={{color:"#CBD5E1",fontSize:"0.8rem"}}>&middot;</span>
            <span style={{fontSize:"0.7rem",fontWeight:600,color:"#64748b"}}>{agentInfo.label}</span>
          </>
        )}
      </div>
      {time && (
        <span style={{display:"flex",alignItems:"center",gap:4,fontSize:"0.68rem",color:"#94a3b8"}}>
          <Clock size={10}/>{time}
        </span>
      )}
    </div>
  );
}

function ActionBar({ msg, onActionClick }) {
  var [copied, setCopied] = useState(false);
  var text = msg.content || "";
  function handleCopy() {
    navigator.clipboard && navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(function(){setCopied(false);}, 2000);
  }
  return (
    <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"7px 18px",borderTop:"1px solid "+BORDER,flexWrap:"wrap",gap:6,background:"#FAFBFC"}}>
      <div style={{display:"flex",flexWrap:"wrap",gap:5}}>
        {(msg.suggested_actions||[]).map(function(action,idx){return (
          <button key={idx} onClick={function(){onActionClick(action);}}
            style={{display:"inline-flex",alignItems:"center",gap:4,padding:"4px 10px",background:"#fff",border:"1px solid "+BORDER,borderRadius:7,cursor:"pointer",fontSize:"0.74rem",color:"#374151",fontWeight:500,transition:"all 120ms"}}
            onMouseEnter={function(e){e.currentTarget.style.background=NAVY;e.currentTarget.style.color="#fff";e.currentTarget.style.borderColor=NAVY;}}
            onMouseLeave={function(e){e.currentTarget.style.background="#fff";e.currentTarget.style.color="#374151";e.currentTarget.style.borderColor=BORDER;}}>
            <Zap size={9}/>{action.label||action.action_type}
          </button>
        );})}
      </div>
      <button onClick={handleCopy}
        style={{display:"inline-flex",alignItems:"center",gap:5,padding:"5px 11px",background:"transparent",border:"none",color:copied?"#059669":"#94a3b8",fontSize:"0.74rem",cursor:"pointer",borderRadius:6,transition:"color 150ms",flexShrink:0}}>
        {copied ? <Check size={11}/> : <Copy size={11}/>}{copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

function MarkdownRenderer({ text }) {
  if (!text) return null;
  var lines = text.split("\n");
  var elements = [];
  var i = 0;
  var listItems = [];
  var orderedItems = [];
  var inCodeBlock = false;
  var codeLines = [];
  var codeLang = "";
  var tableLines = [];
  var bqLines = [];

  function flushList() {
    if (!listItems.length) return;
    var items = listItems.slice();
    listItems = [];
    elements.push(
      <ul key={"ul-"+i} style={{margin:"8px 0 10px",paddingLeft:0,listStyle:"none"}}>
        {items.map(function(item,idx){
          var ckm = item.match(/^\[([ xX])\] (.+)/);
          if (ckm) {
            var checked = ckm[1].toLowerCase()==="x";
            return (
              <li key={idx} style={{display:"flex",gap:9,marginBottom:5,alignItems:"flex-start"}}>
                <span style={{flexShrink:0,width:16,height:16,borderRadius:4,border:"2px solid "+(checked?"#059669":BORDER),background:checked?"#059669":"#fff",display:"flex",alignItems:"center",justifyContent:"center",marginTop:3}}>
                  {checked && <Check size={9} style={{color:"#fff"}}/>}
                </span>
                <span style={{fontSize:"0.9rem",color:checked?"#94a3b8":"#374151",textDecoration:checked?"line-through":"none",lineHeight:1.7}}>{renderInline(ckm[2])}</span>
              </li>
            );
          }
          return (
            <li key={idx} style={{display:"flex",gap:10,marginBottom:5,alignItems:"flex-start"}}>
              <span style={{flexShrink:0,width:5,height:5,borderRadius:"50%",background:NAVY,marginTop:10,opacity:0.45}}/>
              <span style={{fontSize:"0.9rem",color:"#374151",lineHeight:1.75}}>{renderInline(item)}</span>
            </li>
          );
        })}
      </ul>
    );
  }

  function flushOrdered() {
    if (!orderedItems.length) return;
    var items = orderedItems.slice();
    orderedItems = [];
    elements.push(
      <ol key={"ol-"+i} style={{margin:"8px 0 10px",paddingLeft:0,listStyle:"none"}}>
        {items.map(function(item,idx){return (
          <li key={idx} style={{display:"flex",gap:10,marginBottom:7,alignItems:"flex-start"}}>
            <span style={{flexShrink:0,width:20,height:20,borderRadius:6,background:NAVY,color:"#fff",fontSize:"0.67rem",fontWeight:700,display:"flex",alignItems:"center",justifyContent:"center",marginTop:2}}>{idx+1}</span>
            <span style={{flex:1,fontSize:"0.9rem",color:"#374151",lineHeight:1.75}}>{renderInline(item)}</span>
          </li>
        );})}
      </ol>
    );
  }

  function flushTable() {
    if (!tableLines.length) return;
    var rows = tableLines.slice();
    tableLines = [];
    elements.push(<AcademicTable key={"tbl-"+i} rows={rows}/>);
  }

  function flushBlockquote() {
    if (!bqLines.length) return;
    var bq = bqLines.slice();
    bqLines = [];
    var firstLine = bq[0].trim();
    var calloutType = detectCalloutType(firstLine);
    if (calloutType) {
      var contentLines = firstLine.startsWith("[!")
        ? bq.slice(1)
        : bq.map(function(l,idx){return idx===0?l.replace(/^\*\*[^*]+:\*\*\s*/,""):l;}).filter(function(l){return l.trim();});
      elements.push(<CalloutBlock key={"bq-"+i} type={calloutType} lines={contentLines}/>);
    } else {
      elements.push(
        <blockquote key={"bq-"+i} style={{borderLeft:"3px solid #CBD5E1",background:"#F8FAFC",padding:"12px 16px",margin:"12px 0",borderRadius:"0 8px 8px 0",color:"#475569",fontStyle:"italic",lineHeight:1.78}}>
          {bq.map(function(l,idx){return <p key={idx} style={{margin:0,fontSize:"0.9rem"}}>{renderInline(l)}</p>;})}
        </blockquote>
      );
    }
  }

  while (i < lines.length) {
    var line = lines[i];

    if (line.startsWith("```")) {
      if (!inCodeBlock) {
        flushList(); flushOrdered(); flushTable(); flushBlockquote();
        inCodeBlock = true; codeLang = line.slice(3).trim(); codeLines = [];
      } else {
        var capturedCode = codeLines.slice(); var capturedLang = codeLang;
        elements.push(<CodeBlock key={"code-"+i} lang={capturedLang} code={capturedCode.join("\n")}/>);
        inCodeBlock = false; codeLines = []; codeLang = "";
      }
      i++; continue;
    }
    if (inCodeBlock) { codeLines.push(line); i++; continue; }

    if (line.startsWith("|")) { flushList(); flushOrdered(); flushBlockquote(); tableLines.push(line); i++; continue; }
    if (tableLines.length && !line.startsWith("|")) flushTable();

    if (line.startsWith("> ")) { flushList(); flushOrdered(); bqLines.push(line.slice(2)); i++; continue; }
    if (bqLines.length && !line.startsWith("> ")) flushBlockquote();

    if (line.startsWith("# ")) {
      flushList(); flushOrdered();
      var h1text = line.slice(2);
      elements.push(<h1 key={"h1-"+i} style={{fontFamily:"Georgia,serif",fontSize:"1.22rem",fontWeight:700,color:NAVY,margin:"22px 0 10px",lineHeight:1.3,letterSpacing:"-0.01em"}}>{renderInline(h1text)}</h1>);
      i++; continue;
    }
    if (line.startsWith("## ")) {
      flushList(); flushOrdered();
      var h2text = line.slice(3);
      elements.push(
        <div key={"h2-"+i} style={{margin:"20px 0 8px"}}>
          <h2 style={{fontFamily:"Georgia,serif",fontSize:"1.04rem",fontWeight:700,color:"#0f172a",margin:0,lineHeight:1.4}}>{renderInline(h2text)}</h2>
          <div style={{height:1,background:BORDER,marginTop:5}}/>
        </div>
      );
      i++; continue;
    }
    if (line.startsWith("### ")) {
      flushList(); flushOrdered();
      var h3text = line.slice(4);
      elements.push(<h3 key={"h3-"+i} style={{fontSize:"0.93rem",fontWeight:700,color:"#1e293b",margin:"14px 0 4px",lineHeight:1.4}}>{renderInline(h3text)}</h3>);
      i++; continue;
    }

    if (/^[-*] \[([ xX])\] /.test(line)) { flushOrdered(); listItems.push(line.replace(/^[-*] /,"")); i++; continue; }
    if (/^[-*•] /.test(line)) { flushOrdered(); listItems.push(line.slice(2)); i++; continue; }
    if (/^\d+\. /.test(line)) { flushList(); orderedItems.push(line.replace(/^\d+\. /,"")); i++; continue; }

    if (/^---+$/.test(line.trim())) {
      flushList(); flushOrdered();
      elements.push(<hr key={"hr-"+i} style={{border:"none",borderTop:"1px solid "+BORDER,margin:"16px 0"}}/>);
      i++; continue;
    }

    if (!line.trim()) { flushList(); flushOrdered(); i++; continue; }

    flushList(); flushOrdered();
    var ptext = line;
    elements.push(<p key={"p-"+i} style={{color:"#374151",lineHeight:1.8,margin:"0 0 10px",fontSize:"0.9rem"}}>{renderInline(ptext)}</p>);
    i++;
  }

  flushList(); flushOrdered(); flushTable(); flushBlockquote();
  return <div style={{minWidth:0}}>{elements}</div>;
}

function ResearchLoadingIndicator() {
  var [stage, setStage] = useState(0);
  useEffect(function(){
    var id = setInterval(function(){setStage(function(v){return (v+1)%LOAD_STAGES.length;});}, 1700);
    return function(){clearInterval(id);};
  },[]);
  return (
    <div style={{marginBottom:4}}>
      <div style={{marginLeft:36,background:"#fff",border:"1px solid "+BORDER,borderRadius:"0 14px 14px 14px",padding:"20px 24px 18px",boxShadow:"0 2px 12px rgba(0,0,0,0.04)"}}>
        <div style={{height:2,background:WARM,borderRadius:999,overflow:"hidden",marginBottom:16}}>
          <div style={{height:"100%",background:NAVY,borderRadius:999,animation:"sq-progress 1.7s ease-in-out infinite"}}/>
          <style dangerouslySetInnerHTML={{__html:"@keyframes sq-progress{0%{width:0%;margin-left:0}60%{width:65%}100%{width:0%;margin-left:100%}}@keyframes sq-bounce{0%,60%,100%{transform:translateY(0);opacity:0.35}30%{transform:translateY(-5px);opacity:1}}"}}/>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:12}}>
          <div style={{display:"flex",gap:5}}>
            {[0,1,2].map(function(k){return (
              <span key={k} style={{width:5,height:5,borderRadius:"50%",background:NAVY,opacity:0.35,display:"inline-block",animation:"sq-bounce 1.2s ease-in-out infinite",animationDelay:(k*0.2)+"s"}}/>
            );})}
          </div>
          <span style={{fontSize:"0.82rem",color:"#64748b"}}>{LOAD_STAGES[stage]}</span>
        </div>
      </div>
    </div>
  );
}

function AIMessageCard({ msg, onActionClick, onRetry }) {
  var rawText = msg.content || "";
  var time = readingTime(rawText);
  var cited = extractCitations(rawText);
  var mainText = cited ? cited.main : rawText;
  var parsed = parseSections(mainText);
  var hasSections = parsed && parsed.sections.length >= 2;

  if (msg.error) {
    return (
      <div style={{background:"#FFF1F2",border:"1px solid #FCA5A5",borderRadius:"0 14px 14px 14px",padding:"14px 18px"}}>
        <div style={{display:"flex",alignItems:"center",gap:8,color:"#DC2626",fontSize:"0.88rem"}}>
          <AlertCircle size={16}/>
          <span>{rawText}</span>
          {onRetry && <button onClick={function(){onRetry(msg.id);}} style={{marginLeft:8,fontSize:"0.8rem",color:NAVY,textDecoration:"underline",background:"none",border:"none",cursor:"pointer"}}>Retry</button>}
        </div>
      </div>
    );
  }

  return (
    <div style={{background:"#fff",border:"1px solid "+BORDER,borderRadius:"0 14px 14px 14px",overflow:"hidden",boxShadow:"0 2px 12px rgba(0,0,0,0.04)"}}>
      <ResponseHeader agent={msg.agent_type} time={time}/>
      {hasSections && parsed.sections.length >= 3 && <MiniTOC sections={parsed.sections}/>}
      <div style={{padding:"18px 22px 10px"}}>
        {hasSections ? (
          <div>
            {parsed.intro && <div style={{marginBottom:16}}><MarkdownRenderer text={parsed.intro}/></div>}
            {parsed.sections.map(function(section,idx){return (
              <CollapsibleSection key={idx} heading={section.heading} defaultOpen={idx < 2 || parsed.sections.length <= 3}>
                <MarkdownRenderer text={section.content}/>
              </CollapsibleSection>
            );})}
          </div>
        ) : (
          <MarkdownRenderer text={mainText}/>
        )}
      </div>
      {cited && cited.citations && cited.citations.length > 0 && <CitationList citations={cited.citations}/>}
      {msg.sources && msg.sources.length > 0 && (
        <div style={{padding:"8px 22px 10px",borderTop:"1px solid "+BORDER,display:"flex",flexWrap:"wrap",gap:6}}>
          {msg.sources.map(function(src,idx){return (
            <span key={idx} style={{display:"inline-flex",alignItems:"center",gap:5,padding:"3px 10px",background:WARM,color:"#475569",fontSize:"0.72rem",borderRadius:999,border:"1px solid "+BORDER}}>
              <Search size={9}/>{src.title||src}
            </span>
          );})}
        </div>
      )}
      <ActionBar msg={msg} onActionClick={onActionClick}/>
    </div>
  );
}

function MessageBubble({ msg, onActionClick, onRetry }) {
  if (msg.isTyping) {
    return (
      <div>
        <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:8}}>
          <div style={{width:28,height:28,borderRadius:8,background:NAVY,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}><Sparkles size={13} style={{color:"#fff"}}/></div>
          <span style={{fontSize:"0.7rem",fontWeight:700,letterSpacing:"0.06em",textTransform:"uppercase",color:NAVY}}>Synaptiq AI</span>
        </div>
        <ResearchLoadingIndicator/>
      </div>
    );
  }
  if (msg.role==="user") {
    return (
      <div style={{display:"flex",justifyContent:"flex-end"}}>
        <div style={{maxWidth:"68%",background:NAVY,color:"#fff",borderRadius:"14px 14px 4px 14px",padding:"12px 18px",fontSize:"0.9rem",lineHeight:1.72,boxShadow:"0 2px 10px rgba(15,40,71,0.18)"}}>{msg.content}</div>
      </div>
    );
  }
  return (
    <div>
      <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:8}}>
        <div style={{width:28,height:28,borderRadius:8,background:NAVY,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}><Sparkles size={13} style={{color:"#fff"}}/></div>
        <span style={{fontSize:"0.7rem",fontWeight:700,letterSpacing:"0.06em",textTransform:"uppercase",color:NAVY}}>Synaptiq AI</span>
      </div>
      <AIMessageCard msg={msg} onActionClick={onActionClick} onRetry={onRetry}/>
    </div>
  );
}

function AgentBadge({ type, size }) {
  size = size || "sm";
  var c = AGENT_COLORS[type]||AGENT_COLORS.general;
  var agent = AGENTS.find(function(a){return a.id===type;});
  var label = agent ? agent.label : type;
  var pad = size==="xs" ? "3px 8px" : "4px 10px";
  var fs  = size==="xs" ? "0.68rem" : "0.72rem";
  return (
    <span style={{display:"inline-flex",alignItems:"center",gap:5,borderRadius:999,fontSize:fs,fontWeight:600,letterSpacing:"0.02em",padding:pad}} className={c.bg+" "+c.text}>
      <span style={{width:5,height:5,borderRadius:"50%"}} className={c.dot}/>
      {label}
    </span>
  );
}

function MessageThread({ messages, onActionClick, onRetry }) {
  var bottomRef = useRef(null);
  useEffect(function(){if(bottomRef.current)bottomRef.current.scrollIntoView({behavior:"smooth"});},[messages]);
  if (!messages.length) {
    return (
      <div style={{flex:1,display:"flex",alignItems:"center",justifyContent:"center",background:WARM}}>
        <div style={{textAlign:"center",color:"#94a3b8"}}>
          <Sparkles size={24} style={{margin:"0 auto 10px",opacity:0.4}}/>
          <p style={{fontSize:"0.84rem"}}>Begin your research below</p>
        </div>
      </div>
    );
  }
  return (
    <div style={{flex:1,overflowY:"auto",background:WARM,padding:"28px 28px 20px"}}>
      <div style={{maxWidth:820,margin:"0 auto",display:"flex",flexDirection:"column",gap:22}}>
        {messages.map(function(msg){return <MessageBubble key={msg.id} msg={msg} onActionClick={onActionClick} onRetry={onRetry}/>;}) }
        <div ref={bottomRef}/>
      </div>
    </div>
  );
}

function ConfirmModal({ title, message, confirmLabel, danger, onConfirm, onCancel }) {
  confirmLabel = confirmLabel || "Confirm";
  return (
    <div style={{position:"fixed",inset:0,zIndex:50,display:"flex",alignItems:"center",justifyContent:"center",background:"rgba(0,0,0,0.4)",backdropFilter:"blur(4px)"}}>
      <div style={{background:"#fff",borderRadius:16,boxShadow:"0 20px 60px rgba(0,0,0,0.2)",padding:"28px 32px",width:360,maxWidth:"90vw"}}>
        <div style={{fontFamily:"Georgia,serif",fontSize:"1rem",fontWeight:700,color:NAVY,marginBottom:10}}>{title}</div>
        <p style={{fontSize:"0.87rem",color:"#64748b",lineHeight:1.65,marginBottom:24}}>{message}</p>
        <div style={{display:"flex",gap:10,justifyContent:"flex-end"}}>
          <button onClick={onCancel} style={{padding:"9px 18px",fontSize:"0.84rem",border:"1px solid "+BORDER,borderRadius:8,background:"transparent",color:"#64748b",cursor:"pointer"}}>Cancel</button>
          <button onClick={onConfirm} style={{padding:"9px 18px",fontSize:"0.84rem",borderRadius:8,border:"none",fontWeight:600,cursor:"pointer",background:danger?"#DC2626":NAVY,color:"#fff"}}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

function ConvItem({ conv, active, onSelect, onPin, onArchive, onDelete }) {
  var [hover, setHover] = useState(false);
  var dot = SIDEBAR_DOT[conv.agent_type]||SIDEBAR_DOT.general;
  return (
    <div
      onMouseEnter={function(){setHover(true);}} onMouseLeave={function(){setHover(false);}}
      onClick={function(){onSelect(conv.id);}}
      style={{position:"relative",display:"flex",alignItems:"flex-start",gap:10,padding:"9px 12px",borderRadius:8,cursor:"pointer",transition:"background 120ms",background:active?"rgba(255,255,255,0.12)":hover?"rgba(255,255,255,0.07)":"transparent",borderLeft:active?"2px solid rgba(255,255,255,0.5)":"2px solid transparent"}}
    >
      <span style={{width:6,height:6,borderRadius:"50%",background:dot,flexShrink:0,marginTop:5}}/>
      <div style={{flex:1,minWidth:0}}>
        <div style={{fontSize:"0.8rem",fontWeight:active?600:400,color:active?"#fff":"rgba(255,255,255,0.8)",lineHeight:1.4,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{truncate(conv.title,28)}</div>
        <div style={{fontSize:"0.68rem",color:"rgba(255,255,255,0.35)",marginTop:2}}>{relativeTime(conv.updated_at)}</div>
      </div>
      {hover && (
        <div style={{display:"flex",gap:2,flexShrink:0}} onClick={function(e){e.stopPropagation();}}>
          <button onClick={function(){onPin(conv.id,!conv.pinned);}} title={conv.pinned?"Unpin":"Pin"}
            style={{background:"none",border:"none",cursor:"pointer",padding:4,color:conv.pinned?"#a78bfa":"rgba(255,255,255,0.4)",borderRadius:4}}><Pin size={10}/></button>
          <button onClick={function(){onDelete(conv.id);}} title="Delete"
            style={{background:"none",border:"none",cursor:"pointer",padding:4,color:"rgba(255,255,255,0.35)",borderRadius:4}}><Trash2 size={10}/></button>
        </div>
      )}
    </div>
  );
}

function LeftPanel({ state, dispatch, onNewChat, onSelectConv, onPin, onArchive, onDelete }) {
  var pinned = state.conversations.filter(function(c){return c.pinned&&!c.archived;});
  var recent = state.conversations.filter(function(c){return !c.pinned&&!c.archived;}).slice(0,24);
  return (
    <div style={{display:"flex",flexDirection:"column",height:"100%",background:NAVY2,transition:"width 200ms",width:state.leftPanelOpen?264:0,overflow:"hidden",flexShrink:0}}>
      <div style={{minWidth:264,flex:1,display:"flex",flexDirection:"column",height:"100%"}}>
        <div style={{padding:"18px 14px 12px",flexShrink:0}}>
          <button onClick={onNewChat} style={{width:"100%",display:"flex",alignItems:"center",justifyContent:"center",gap:8,padding:"10px 0",background:"rgba(255,255,255,0.1)",border:"1px solid rgba(255,255,255,0.15)",borderRadius:10,cursor:"pointer",color:"#fff",fontSize:"0.82rem",fontWeight:600,transition:"background 150ms",letterSpacing:"0.01em"}}
            onMouseEnter={function(e){e.currentTarget.style.background="rgba(255,255,255,0.16)";}}
            onMouseLeave={function(e){e.currentTarget.style.background="rgba(255,255,255,0.1)";}}>
            <Plus size={14}/>New Research Session
          </button>
        </div>
        <div style={{flex:1,overflowY:"auto",padding:"0 10px 16px"}}>
          {pinned.length>0&&(
            <div style={{marginBottom:8}}>
              <div style={{fontSize:"0.6rem",fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"rgba(255,255,255,0.3)",padding:"6px 4px 4px",marginBottom:2}}>Pinned</div>
              {pinned.map(function(c){return <ConvItem key={c.id} conv={c} active={state.activeConvId===c.id} onSelect={onSelectConv} onPin={onPin} onArchive={onArchive} onDelete={onDelete}/>;}) }
            </div>
          )}
          {recent.length>0&&(
            <div>
              <div style={{fontSize:"0.6rem",fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"rgba(255,255,255,0.3)",padding:"6px 4px 4px",marginBottom:2}}>Recent</div>
              {recent.map(function(c){return <ConvItem key={c.id} conv={c} active={state.activeConvId===c.id} onSelect={onSelectConv} onPin={onPin} onArchive={onArchive} onDelete={onDelete}/>;}) }
            </div>
          )}
          {state.conversations.length===0&&(
            <div style={{textAlign:"center",padding:"40px 20px"}}>
              <MessageSquare size={22} style={{color:"rgba(255,255,255,0.2)",margin:"0 auto 10px"}}/>
              <p style={{fontSize:"0.78rem",color:"rgba(255,255,255,0.3)"}}>No research sessions yet</p>
            </div>
          )}
        </div>
        <div style={{padding:"12px 14px",borderTop:"1px solid rgba(255,255,255,0.07)",flexShrink:0}}>
          <button style={{display:"flex",alignItems:"center",gap:8,padding:"7px 8px",width:"100%",background:"none",border:"none",cursor:"pointer",color:"rgba(255,255,255,0.4)",fontSize:"0.77rem",borderRadius:6}}
            onMouseEnter={function(e){e.currentTarget.style.color="rgba(255,255,255,0.7)";}}
            onMouseLeave={function(e){e.currentTarget.style.color="rgba(255,255,255,0.4)";}}>
            <Archive size={13}/>Archived sessions
          </button>
        </div>
      </div>
    </div>
  );
}

var WF_CREDITS = { lit:12, gap:8, design:10, meth:8, stats:10, jrnl:5, grant:15, peer:12, write:8, teach:6 };

function WelcomeScreen({ user, context, conversations, insights, onStartWithAgent, onSelectConv }) {
  var firstName = (user && (user.first_name || (user.name && user.name.split(" ")[0]))) || "";
  var [hoveredWF, setHoveredWF] = useState(null);
  var [hoveredAgent, setHoveredAgent] = useState(null);
  var [visible, setVisible] = useState(false);

  var msgOpts = useMemo(function() {
    return {
      profile: (user && (user.academic_role || user.role || user.position)) || "",
      hasManuscripts: !!(context && context.manuscripts_count > 0),
      hasGrants:      !!(context && context.grants_count > 0),
      hasCollabs:     !!(context && context.collaborations_count > 0),
      hasCitations:   !!(context && context.citations_count > 0),
      orcidConnected: !!(context && context.orcid_connected),
    };
  }, [user, context]);

  var dailyMessage = useMemo(function() { return getDailyWelcomeMessage(msgOpts); }, [msgOpts]);

  useEffect(function() {
    var id = requestAnimationFrame(function() { setVisible(true); });
    return function() { cancelAnimationFrame(id); };
  }, []);

  var briefItems = useMemo(function() {
    if (!context) return [];
    var items = [];
    if (context.manuscripts_count > 0) items.push({ label: "Manuscripts", value: context.manuscripts_count, Icon: FileText });
    if (context.grants_count > 0)      items.push({ label: "Active grants", value: context.grants_count, Icon: Zap });
    if (context.collaborations_count > 0) items.push({ label: "Collaborations", value: context.collaborations_count, Icon: Users });
    if (context.sis_score != null)     items.push({ label: "Impact score", value: context.sis_score, Icon: BarChart2 });
    if (context.reputation_level)      items.push({ label: "Reputation", value: context.reputation_level, Icon: Award });
    if (context.credits_remaining != null) items.push({ label: "Credits", value: context.credits_remaining, Icon: Sparkles });
    return items;
  }, [context]);

  var recentSessions = useMemo(function() {
    return (conversations || []).filter(function(c){ return !c.archived; }).slice(0, 4);
  }, [conversations]);

  var smartInsights = useMemo(function() {
    return (insights || []).slice(0, 3);
  }, [insights]);

  var hasRecentOrInsights = recentSessions.length > 0 || smartInsights.length > 0;

  return (
    <div style={{flex:1,overflowY:"auto",background:WARM,opacity:visible?1:0,transition:"opacity 350ms ease-out"}}>
      <div style={{maxWidth:920,margin:"0 auto",padding:"44px 32px 48px"}}>

        {/* ── Workspace wordmark ─────────────────────────────────────────────── */}
        <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:36}}>
          <div style={{position:"relative",width:28,height:28}}>
            <div style={{position:"absolute",width:16,height:16,borderRadius:"50%",background:NAVY,top:0,left:0}}/>
            <div style={{position:"absolute",width:11,height:11,borderRadius:"50%",background:ACCENT,top:9,left:9}}/>
          </div>
          <span style={{fontSize:"0.62rem",fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"#94a3b8"}}>Synaptiq AI Workspace</span>
        </div>

        {/* ── Greeting ──────────────────────────────────────────────────────── */}
        <h1 style={{fontFamily:"Georgia,serif",fontSize:"clamp(1.8rem,4vw,2.5rem)",fontWeight:700,color:NAVY,lineHeight:1.15,marginBottom:10,letterSpacing:"-0.025em"}}>
          {getGreeting(firstName)}.
        </h1>
        <p style={{fontSize:"1rem",color:"#475569",marginBottom:briefItems.length?28:36,lineHeight:1.65,maxWidth:560,fontStyle:"italic"}}>
          {dailyMessage}
        </p>

        {/* ── Research Brief (chips) ─────────────────────────────────────────── */}
        {briefItems.length > 0 && (
          <div style={{display:"flex",flexWrap:"wrap",gap:8,marginBottom:40}}>
            {briefItems.map(function(item) {
              var Ic = item.Icon;
              return (
                <div key={item.label} style={{display:"flex",alignItems:"center",gap:8,background:"#fff",border:"1px solid "+BORDER,borderRadius:10,padding:"7px 13px"}}>
                  <Ic size={12} style={{color:"#94a3b8",flexShrink:0}}/>
                  <span style={{fontSize:"0.73rem",color:"#64748b"}}>{item.label}</span>
                  <span style={{fontSize:"0.8rem",fontWeight:700,color:NAVY,fontFamily:"Georgia,serif",textTransform:"capitalize"}}>{item.value}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* ── Quick Actions ──────────────────────────────────────────────────── */}
        <div style={{marginBottom:44}}>
          <div style={{fontSize:"0.6rem",fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"#94a3b8",marginBottom:14}}>Quick Actions</div>
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(198px,1fr))",gap:10}}>
            {RESEARCH_WORKFLOWS.map(function(wf){
              var Icon = wf.icon;
              var isHover = hoveredWF===wf.id;
              var cost = WF_CREDITS[wf.id] || 8;
              return (
                <button key={wf.id}
                  onMouseEnter={function(){setHoveredWF(wf.id);}}
                  onMouseLeave={function(){setHoveredWF(null);}}
                  onClick={function(){onStartWithAgent(wf.agent,wf.prompt);}}
                  style={{display:"flex",flexDirection:"column",alignItems:"flex-start",textAlign:"left",padding:"16px 16px 14px",background:"#fff",border:"1px solid "+(isHover?NAVY:BORDER),borderRadius:12,cursor:"pointer",boxShadow:isHover?"0 6px 24px rgba(15,40,71,0.1)":"0 1px 4px rgba(0,0,0,0.04)",transition:"all 160ms",transform:isHover?"translateY(-2px)":"none"}}>
                  <div style={{width:36,height:36,borderRadius:10,display:"flex",alignItems:"center",justifyContent:"center",background:isHover?NAVY:WARM,marginBottom:12,transition:"background 160ms",flexShrink:0}}>
                    <Icon size={16} style={{color:isHover?"#fff":NAVY,transition:"color 160ms"}}/>
                  </div>
                  <div style={{fontSize:"0.85rem",fontWeight:600,color:"#0f172a",marginBottom:4,lineHeight:1.3}}>{wf.label}</div>
                  <div style={{fontSize:"0.74rem",color:"#64748b",lineHeight:1.5,flex:1}}>{wf.desc}</div>
                  <div style={{marginTop:11,display:"flex",alignItems:"center",justifyContent:"space-between",width:"100%"}}>
                    <span style={{fontSize:"0.6rem",fontWeight:700,color:isHover?NAVY:"#94a3b8",background:isHover?WARM:"#f1f5f9",border:"1px solid "+(isHover?BORDER:"transparent"),padding:"2px 7px",borderRadius:20,transition:"all 160ms"}}>~{cost} cr</span>
                    {isHover && <ArrowRight size={11} style={{color:NAVY}}/>}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* ── AI Agents ──────────────────────────────────────────────────────── */}
        <div style={{marginBottom:44}}>
          <div style={{fontSize:"0.6rem",fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"#94a3b8",marginBottom:13}}>AI Agents</div>
          <div style={{display:"flex",flexWrap:"wrap",gap:7}}>
            {AGENTS.map(function(a){
              var Icon = a.icon;
              var isHov = hoveredAgent===a.id;
              return (
                <button key={a.id}
                  onMouseEnter={function(){setHoveredAgent(a.id);}}
                  onMouseLeave={function(){setHoveredAgent(null);}}
                  onClick={function(){onStartWithAgent(a.id,"");}}
                  style={{display:"flex",alignItems:"center",gap:7,padding:"8px 13px",background:isHov?NAVY:"#fff",border:"1px solid "+(isHov?NAVY:BORDER),borderRadius:10,cursor:"pointer",transition:"all 150ms"}}>
                  <Icon size={13} style={{color:isHov?"#fff":NAVY}}/>
                  <span style={{fontSize:"0.78rem",fontWeight:600,color:isHov?"#fff":"#0f172a"}}>{a.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Recent Sessions + Smart Insights ──────────────────────────────── */}
        {hasRecentOrInsights && (
          <div style={{display:"grid",gridTemplateColumns:recentSessions.length>0&&smartInsights.length>0?"1fr 1fr":"1fr",gap:20,marginBottom:40}}>
            {recentSessions.length > 0 && (
              <div>
                <div style={{fontSize:"0.6rem",fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"#94a3b8",marginBottom:11}}>Recent Sessions</div>
                <div style={{display:"flex",flexDirection:"column",gap:6}}>
                  {recentSessions.map(function(c){
                    var dot = SIDEBAR_DOT[c.agent_type]||SIDEBAR_DOT.general;
                    return (
                      <button key={c.id} onClick={function(){onSelectConv&&onSelectConv(c.id);}}
                        style={{display:"flex",alignItems:"center",gap:10,padding:"10px 13px",background:"#fff",border:"1px solid "+BORDER,borderRadius:10,cursor:"pointer",textAlign:"left",transition:"border-color 150ms,box-shadow 150ms",width:"100%"}}
                        onMouseEnter={function(e){e.currentTarget.style.borderColor=NAVY;e.currentTarget.style.boxShadow="0 4px 12px rgba(15,40,71,0.08)";}}
                        onMouseLeave={function(e){e.currentTarget.style.borderColor=BORDER;e.currentTarget.style.boxShadow="none";}}>
                        <span style={{width:6,height:6,borderRadius:"50%",background:dot,flexShrink:0}}/>
                        <span style={{flex:1,fontSize:"0.8rem",fontWeight:500,color:"#0f172a",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{truncate(c.title,40)}</span>
                        <span style={{fontSize:"0.67rem",color:"#94a3b8",flexShrink:0}}>{relativeTime(c.updated_at)}</span>
                        <ArrowRight size={11} style={{color:"#94a3b8",flexShrink:0}}/>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
            {smartInsights.length > 0 && (
              <div>
                <div style={{fontSize:"0.6rem",fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"#94a3b8",marginBottom:11}}>Smart Recommendations</div>
                <div style={{display:"flex",flexDirection:"column",gap:6}}>
                  {smartInsights.map(function(ins,idx){return (
                    <div key={idx} style={{padding:"12px 13px",background:"#fff",border:"1px solid "+BORDER,borderRadius:10,borderLeft:"3px solid "+NAVY}}>
                      <p style={{fontSize:"0.78rem",color:"#374151",lineHeight:1.55,margin:0}}>{ins.message||ins.title}</p>
                      {ins.detail && <p style={{fontSize:"0.7rem",color:"#64748b",marginTop:4,marginBottom:0}}>{ins.detail}</p>}
                    </div>
                  );})}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Trust badges ──────────────────────────────────────────────────── */}
        <div style={{display:"flex",alignItems:"center",gap:20,flexWrap:"wrap"}}>
          {[[Shield,"Private workspace"],[Check,"Encrypted conversations"],[User,"ORCID-connected"]].map(function(pair){
            var I=pair[0],label=pair[1];
            return <div key={label} style={{display:"flex",alignItems:"center",gap:6,color:"#94a3b8",fontSize:"0.73rem"}}><I size={12}/>{label}</div>;
          })}
        </div>

      </div>
    </div>
  );
}

function ConversationHeader({ conv, onPin, onArchive, onDelete, onTitleChange }) {
  var [editing, setEditing] = useState(false);
  var [draft, setDraft] = useState("");
  var ref = useRef(null);
  function startEdit() { setDraft(conv ? conv.title||"" : ""); setEditing(true); setTimeout(function(){if(ref.current)ref.current.focus();},0); }
  function commit() { setEditing(false); if(!conv||draft.trim()===conv.title) return; onTitleChange(conv.id,draft.trim()); }
  if (!conv) return null;
  return (
    <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"12px 20px",background:"#fff",borderBottom:"1px solid "+BORDER,flexShrink:0}}>
      <div style={{display:"flex",alignItems:"center",gap:10,flex:1,minWidth:0}}>
        <AgentBadge type={conv.agent_type||"auto"}/>
        {editing ? (
          <input ref={ref} value={draft} onChange={function(e){setDraft(e.target.value);}}
            onBlur={commit} onKeyDown={function(e){if(e.key==="Enter")commit();if(e.key==="Escape")setEditing(false);}}
            style={{flex:1,minWidth:0,fontSize:"0.88rem",fontWeight:600,color:NAVY,background:"transparent",border:"none",borderBottom:"2px solid "+NAVY,outline:"none",padding:"0 2px"}}/>
        ) : (
          <span onClick={startEdit} title="Click to rename"
            style={{fontSize:"0.88rem",fontWeight:600,color:NAVY,cursor:"text",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:400}}>
            {conv.title||"New session"}
          </span>
        )}
        <button onClick={startEdit} style={{background:"none",border:"none",cursor:"pointer",color:"#94a3b8",padding:2,flexShrink:0}}><Edit2 size={12}/></button>
      </div>
      <div style={{display:"flex",gap:4,marginLeft:12,flexShrink:0}}>
        <button onClick={function(){onPin(conv.id,!conv.pinned);}} title={conv.pinned?"Unpin":"Pin"}
          style={{background:"none",border:"none",cursor:"pointer",padding:6,borderRadius:6,color:conv.pinned?NAVY:"#94a3b8"}}><Pin size={14}/></button>
        <button onClick={function(){onArchive(conv.id);}} title="Archive"
          style={{background:"none",border:"none",cursor:"pointer",padding:6,borderRadius:6,color:"#94a3b8"}}><Archive size={14}/></button>
        <button onClick={function(){onDelete(conv.id);}} title="Delete"
          style={{background:"none",border:"none",cursor:"pointer",padding:6,borderRadius:6,color:"#94a3b8"}}><Trash2 size={14}/></button>
      </div>
    </div>
  );
}

function InputArea({ state, dispatch, onSend }) {
  var textareaRef = useRef(null);
  var [agentOpen, setAgentOpen] = useState(false);
  var [phIdx, setPhIdx] = useState(0);
  var MAX = 4000;

  useEffect(function(){
    var id = setInterval(function(){setPhIdx(function(v){return (v+1)%PLACEHOLDERS.length;});}, 4000);
    return function(){clearInterval(id);};
  },[]);

  useEffect(function(){
    var ta = textareaRef.current;
    if (!ta) return;
    ta.style.height="auto";
    ta.style.height=Math.min(ta.scrollHeight,200)+"px";
  },[state.inputText]);

  useEffect(function(){
    function h(e){if((e.metaKey||e.ctrlKey)&&e.key==="k"){e.preventDefault();if(textareaRef.current)textareaRef.current.focus();}}
    window.addEventListener("keydown",h);
    return function(){window.removeEventListener("keydown",h);};
  },[]);

  function handleKeyDown(e) {
    if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();if(!state.sending&&state.inputText.trim())onSend();}
  }

  var selAgent = AGENTS.find(function(a){return a.id===state.selectedAgent;})||AGENTS[0];
  var charCount = state.inputText.length;

  return (
    <div style={{flexShrink:0,padding:"16px 24px 20px",background:WARM,borderTop:"1px solid "+BORDER}}>
      <div style={{maxWidth:820,margin:"0 auto"}}>
        <div style={{background:"#fff",border:"1.5px solid "+BORDER,borderRadius:16,overflow:"hidden",boxShadow:"0 4px 20px rgba(0,0,0,0.06)",transition:"border-color 150ms,box-shadow 150ms"}}
          onFocusCapture={function(e){e.currentTarget.style.borderColor=NAVY;e.currentTarget.style.boxShadow="0 4px 24px rgba(15,40,71,0.12)";}}
          onBlurCapture={function(e){e.currentTarget.style.borderColor=BORDER;e.currentTarget.style.boxShadow="0 4px 20px rgba(0,0,0,0.06)";}}>
          <textarea ref={textareaRef} value={state.inputText}
            onChange={function(e){dispatch({type:"SET_INPUT",payload:e.target.value.slice(0,MAX)});}}
            onKeyDown={handleKeyDown} placeholder={PLACEHOLDERS[phIdx]} rows={2}
            style={{width:"100%",resize:"none",padding:"18px 20px 8px",fontSize:"0.92rem",color:"#0f172a",background:"transparent",outline:"none",lineHeight:1.65,boxSizing:"border-box",minHeight:60,maxHeight:200,fontFamily:"inherit"}}/>
          <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"8px 14px 12px",gap:12}}>
            <div style={{display:"flex",alignItems:"center",gap:8,flex:1,minWidth:0}}>
              <div style={{position:"relative"}}>
                <button onClick={function(){setAgentOpen(function(v){return !v;});}}
                  style={{display:"flex",alignItems:"center",gap:6,padding:"5px 12px",borderRadius:8,border:"1px solid "+BORDER,background:WARM,cursor:"pointer",fontSize:"0.78rem",fontWeight:500,color:"#374151",transition:"border-color 150ms"}}
                  onMouseEnter={function(e){e.currentTarget.style.borderColor=NAVY;}}
                  onMouseLeave={function(e){e.currentTarget.style.borderColor=BORDER;}}>
                  <span style={{width:6,height:6,borderRadius:"50%",background:SIDEBAR_DOT[state.selectedAgent]||"#94a3b8"}}/>
                  {selAgent.label}<ChevronDown size={11}/>
                </button>
                {agentOpen && (
                  <div style={{position:"absolute",bottom:"calc(100% + 6px)",left:0,zIndex:20,background:"#fff",border:"1px solid "+BORDER,borderRadius:12,boxShadow:"0 8px 32px rgba(0,0,0,0.12)",padding:6,minWidth:200}}>
                    {AGENTS.map(function(a){return (
                      <button key={a.id} onClick={function(){dispatch({type:"SET_AGENT",payload:a.id});setAgentOpen(false);}}
                        style={{display:"flex",alignItems:"center",gap:8,width:"100%",padding:"7px 10px",borderRadius:8,border:"none",background:state.selectedAgent===a.id?WARM:"transparent",cursor:"pointer",textAlign:"left",fontSize:"0.8rem",color:state.selectedAgent===a.id?NAVY:"#374151",fontWeight:state.selectedAgent===a.id?600:400}}
                        onMouseEnter={function(e){e.currentTarget.style.background=WARM;}}
                        onMouseLeave={function(e){e.currentTarget.style.background=state.selectedAgent===a.id?WARM:"transparent";}}>
                        <span style={{width:6,height:6,borderRadius:"50%",background:SIDEBAR_DOT[a.id]||"#94a3b8",flexShrink:0}}/>
                        <span style={{flex:1}}>{a.label}</span>
                        {state.selectedAgent===a.id && <Check size={11} style={{color:NAVY}}/>}
                      </button>
                    );})}
                  </div>
                )}
              </div>
              {charCount>2000 && <span style={{fontSize:"0.7rem",fontFamily:"monospace",color:charCount>3800?"#DC2626":"#F59E0B"}}>{charCount}/{MAX}</span>}
            </div>
            <div style={{display:"flex",alignItems:"center",gap:8,flexShrink:0}}>
              <button disabled title="Voice input coming soon" style={{background:"none",border:"none",cursor:"not-allowed",color:"#cbd5e1",padding:4}}><Mic size={16}/></button>
              <button onClick={onSend} disabled={state.sending||!state.inputText.trim()}
                style={{display:"flex",alignItems:"center",gap:6,padding:"8px 18px",background:state.sending||!state.inputText.trim()?"#E2E8F0":NAVY,color:state.sending||!state.inputText.trim()?"#94a3b8":"#fff",border:"none",borderRadius:10,cursor:state.sending||!state.inputText.trim()?"not-allowed":"pointer",fontSize:"0.82rem",fontWeight:600,transition:"all 150ms"}}>
                <Send size={13}/>{state.sending?"Analysing…":"Send"}
              </button>
            </div>
          </div>
        </div>
        <div style={{display:"flex",alignItems:"center",justifyContent:"center",gap:16,marginTop:10}}>
          {[["↵","Send"],["⇧↵","New line"],["⌘K","Focus"]].map(function(pair){return (
            <span key={pair[0]} style={{fontSize:"0.68rem",color:"#94a3b8",display:"flex",alignItems:"center",gap:4}}>
              <kbd style={{fontFamily:"monospace",background:"#fff",border:"1px solid "+BORDER,borderRadius:4,padding:"1px 5px",fontSize:"0.65rem"}}>{pair[0]}</kbd>{pair[1]}
            </span>
          );})}
        </div>
      </div>
    </div>
  );
}

function RightPanel({ state, dispatch, onRefreshContext, onDeleteMemory, onClearMemory }) {
  var [memoryInput, setMemoryInput] = useState("");
  var [memoryType, setMemoryType] = useState("preference");
  var [addingMemory, setAddingMemory] = useState(false);
  var [showMemoryForm, setShowMemoryForm] = useState(false);
  var [secOpen, setSecOpen] = useState({context:true,insights:true,memory:true});
  var ctx = state.context;

  function toggle(key) { setSecOpen(function(s){var n=Object.assign({},s);n[key]=!s[key];return n;}); }

  async function submitMemory() {
    if (!memoryInput.trim()) return;
    setAddingMemory(true);
    try {
      var res = await api.post("/ai-os/memory",{memory_type:memoryType,content:memoryInput.trim()});
      dispatch({type:"ADD_MEMORY",payload:res.data});
      setMemoryInput(""); setShowMemoryForm(false);
      toast.success("Memory saved");
    } catch(e) { toast.error("Failed to save memory"); }
    finally { setAddingMemory(false); }
  }

  var statRows = ctx ? [
    ctx.manuscripts_count!=null && ["Manuscripts",ctx.manuscripts_count,FileText],
    ctx.collaborations_count!=null && ["Collaborations",ctx.collaborations_count,Users],
    ctx.sis_score!=null && ["Impact Score",ctx.sis_score,BarChart2],
    ctx.reputation_level && ["Reputation",ctx.reputation_level,Award],
    ctx.grants_count!=null && ["Active Grants",ctx.grants_count,Zap],
  ].filter(Boolean) : [];

  return (
    <div style={{display:"flex",flexDirection:"column",height:"100%",background:"#fff",borderLeft:"1px solid "+BORDER,transition:"width 200ms",width:state.rightPanelOpen?280:0,overflow:"hidden",flexShrink:0}}>
      <div style={{minWidth:280,flex:1,overflowY:"auto"}}>
        <div style={{padding:"16px 16px 4px"}}>
          <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:14}}>
            <span style={{fontSize:"0.65rem",fontWeight:700,letterSpacing:"0.14em",textTransform:"uppercase",color:"#94a3b8"}}>Research Context</span>
            <button onClick={onRefreshContext} title="Refresh" style={{background:"none",border:"none",cursor:"pointer",color:"#94a3b8",padding:4,borderRadius:4}}
              onMouseEnter={function(e){e.currentTarget.style.color=NAVY;}} onMouseLeave={function(e){e.currentTarget.style.color="#94a3b8";}}>
              <RefreshCw size={12}/>
            </button>
          </div>
          {ctx && ctx.credits_remaining!=null && (
            <div style={{background:WARM,border:"1px solid "+BORDER,borderRadius:10,padding:"12px 14px",marginBottom:12}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",marginBottom:6}}>
                <span style={{fontSize:"0.72rem",fontWeight:600,color:"#0f172a"}}>Research Credits</span>
                <span style={{fontSize:"0.8rem",fontWeight:700,color:NAVY}}>{ctx.credits_remaining}</span>
              </div>
              <div style={{height:4,background:"#E2E8F0",borderRadius:999,overflow:"hidden"}}>
                <div style={{height:"100%",background:NAVY,borderRadius:999,width:Math.min(100,(ctx.credits_remaining/(ctx.credits_total||300))*100)+"%",transition:"width 600ms"}}/>
              </div>
            </div>
          )}
          {statRows.length>0 && (
            <div style={{border:"1px solid "+BORDER,borderRadius:10,overflow:"hidden",marginBottom:12}}>
              <button onClick={function(){toggle("context");}} style={{width:"100%",display:"flex",alignItems:"center",justifyContent:"space-between",padding:"9px 12px",background:WARM,border:"none",cursor:"pointer"}}>
                <span style={{fontSize:"0.65rem",fontWeight:700,letterSpacing:"0.12em",textTransform:"uppercase",color:"#64748b"}}>Platform Data</span>
                {secOpen.context ? <ChevronUp size={12} style={{color:"#94a3b8"}}/> : <ChevronDown size={12} style={{color:"#94a3b8"}}/>}
              </button>
              {secOpen.context && (
                <div style={{padding:"10px 14px",display:"flex",flexDirection:"column",gap:8}}>
                  {statRows.map(function(row){
                    var label=row[0],val=row[1],Icon=row[2];
                    return (
                      <div key={label} style={{display:"flex",alignItems:"center",justifyContent:"space-between"}}>
                        <span style={{display:"flex",alignItems:"center",gap:6,fontSize:"0.78rem",color:"#64748b"}}><Icon size={12} style={{color:"#94a3b8"}}/>{label}</span>
                        <span style={{fontSize:"0.82rem",fontWeight:700,color:NAVY,textTransform:"capitalize"}}>{val}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
          <div style={{padding:"10px 12px",background:WARM,border:"1px solid "+BORDER,borderRadius:10,marginBottom:12,display:"flex",alignItems:"center",justifyContent:"space-between"}}>
            <span style={{fontSize:"0.75rem",color:"#374151",fontWeight:500}}>ORCID</span>
            <span style={{display:"flex",alignItems:"center",gap:5,fontSize:"0.72rem",fontWeight:600,color:"#059669"}}>
              <span style={{width:6,height:6,borderRadius:"50%",background:"#059669",display:"inline-block"}}/>Connected
            </span>
          </div>
          {state.insights.length>0 && (
            <div style={{border:"1px solid "+BORDER,borderRadius:10,overflow:"hidden",marginBottom:12}}>
              <button onClick={function(){toggle("insights");}} style={{width:"100%",display:"flex",alignItems:"center",justifyContent:"space-between",padding:"9px 12px",background:WARM,border:"none",cursor:"pointer"}}>
                <span style={{fontSize:"0.65rem",fontWeight:700,letterSpacing:"0.12em",textTransform:"uppercase",color:"#64748b"}}>Insights</span>
                {secOpen.insights ? <ChevronUp size={12} style={{color:"#94a3b8"}}/> : <ChevronDown size={12} style={{color:"#94a3b8"}}/>}
              </button>
              {secOpen.insights && (
                <div style={{padding:"10px 12px",display:"flex",flexDirection:"column",gap:8}}>
                  {state.insights.slice(0,4).map(function(ins,idx){return (
                    <div key={idx} style={{padding:"10px 12px",background:WARM,borderRadius:8,borderLeft:"3px solid "+NAVY}}>
                      <p style={{fontSize:"0.78rem",color:"#374151",lineHeight:1.5,margin:0}}>{ins.message||ins.title}</p>
                      {ins.detail && <p style={{fontSize:"0.7rem",color:"#64748b",marginTop:4,marginBottom:0}}>{ins.detail}</p>}
                    </div>
                  );})}
                </div>
              )}
            </div>
          )}
          <div style={{border:"1px solid "+BORDER,borderRadius:10,overflow:"hidden"}}>
            <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"9px 12px",background:WARM}}>
              <button onClick={function(){toggle("memory");}} style={{display:"flex",alignItems:"center",gap:4,background:"none",border:"none",cursor:"pointer"}}>
                <span style={{fontSize:"0.65rem",fontWeight:700,letterSpacing:"0.12em",textTransform:"uppercase",color:"#64748b"}}>AI Memory</span>
                {secOpen.memory ? <ChevronUp size={12} style={{color:"#94a3b8"}}/> : <ChevronDown size={12} style={{color:"#94a3b8"}}/>}
              </button>
              <button onClick={function(){setShowMemoryForm(function(v){return !v;});setSecOpen(function(s){return Object.assign({},s,{memory:true});});}}
                style={{background:"none",border:"none",cursor:"pointer",color:"#94a3b8",padding:3,borderRadius:4}}
                onMouseEnter={function(e){e.currentTarget.style.color=NAVY;}} onMouseLeave={function(e){e.currentTarget.style.color="#94a3b8";}}>
                <Plus size={13}/>
              </button>
            </div>
            {secOpen.memory && (
              <div style={{padding:"10px 12px"}}>
                {showMemoryForm && (
                  <div style={{padding:12,background:WARM,borderRadius:8,border:"1px solid "+BORDER,marginBottom:10}}>
                    <select value={memoryType} onChange={function(e){setMemoryType(e.target.value);}}
                      style={{width:"100%",fontSize:"0.78rem",border:"1px solid "+BORDER,borderRadius:6,padding:"5px 8px",marginBottom:8,background:"#fff",color:"#374151",outline:"none"}}>
                      <option value="preference">Preference</option>
                      <option value="goal">Goal</option>
                      <option value="fact">Fact</option>
                      <option value="context">Context</option>
                    </select>
                    <textarea value={memoryInput} onChange={function(e){setMemoryInput(e.target.value);}} placeholder="What should I remember?" rows={2}
                      style={{width:"100%",fontSize:"0.78rem",border:"1px solid "+BORDER,borderRadius:6,padding:"6px 8px",background:"#fff",color:"#374151",resize:"none",outline:"none",boxSizing:"border-box",fontFamily:"inherit"}}/>
                    <div style={{display:"flex",gap:6,marginTop:8}}>
                      <button onClick={submitMemory} disabled={addingMemory||!memoryInput.trim()}
                        style={{flex:1,padding:"6px 0",fontSize:"0.75rem",background:NAVY,color:"#fff",border:"none",borderRadius:6,cursor:"pointer",fontWeight:600,opacity:addingMemory||!memoryInput.trim()?0.5:1}}>
                        {addingMemory?"Saving…":"Save"}
                      </button>
                      <button onClick={function(){setShowMemoryForm(false);setMemoryInput("");}}
                        style={{padding:"6px 10px",fontSize:"0.75rem",background:"transparent",border:"1px solid "+BORDER,borderRadius:6,cursor:"pointer",color:"#64748b"}}>Cancel</button>
                    </div>
                  </div>
                )}
                {state.memory.length===0 ? (
                  <p style={{fontSize:"0.75rem",color:"#94a3b8",fontStyle:"italic",margin:0}}>No memories yet.</p>
                ) : (
                  <div>
                    <div style={{display:"flex",flexDirection:"column",gap:6}}>
                      {state.memory.slice(0,8).map(function(m){return (
                        <div key={m.id} style={{display:"flex",alignItems:"flex-start",gap:8,padding:"7px 8px",borderRadius:6,background:WARM}}
                          onMouseEnter={function(e){var b=e.currentTarget.querySelector(".del-m");if(b)b.style.opacity="1";}}
                          onMouseLeave={function(e){var b=e.currentTarget.querySelector(".del-m");if(b)b.style.opacity="0";}}>
                          <div style={{flex:1,minWidth:0}}>
                            <span style={{display:"inline-block",fontSize:"0.6rem",textTransform:"uppercase",fontWeight:700,color:"#94a3b8",letterSpacing:"0.1em",marginBottom:2}}>{m.memory_type}</span>
                            <p style={{fontSize:"0.77rem",color:"#374151",lineHeight:1.45,margin:0,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}} title={m.content}>{m.content}</p>
                          </div>
                          <button className="del-m" onClick={function(){onDeleteMemory(m.id);}}
                            style={{background:"none",border:"none",cursor:"pointer",color:"#94a3b8",padding:2,flexShrink:0,opacity:0,transition:"opacity 120ms"}}><X size={11}/></button>
                        </div>
                      );})}
                    </div>
                    <button onClick={onClearMemory} style={{width:"100%",marginTop:10,padding:"7px 0",fontSize:"0.72rem",color:"#DC2626",border:"1px solid #FCA5A5",borderRadius:7,background:"transparent",cursor:"pointer"}}
                      onMouseEnter={function(e){e.currentTarget.style.background="#FEF2F2";}}
                      onMouseLeave={function(e){e.currentTarget.style.background="transparent";}}>
                      Clear all memory (GDPR)
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AIAssistant() {
  var { user } = useAuth();
  var [state, dispatch] = useReducer(reducer, initialState);
  var [confirm, setConfirm] = useState(null);
  var [actionConfirm, setActionConfirm] = useState(null);
  var retryDataRef = useRef({});
  var activeConv = state.conversations.find(function(c){return c.id===state.activeConvId;})||null;

  useEffect(function(){
    async function init() {
      dispatch({type:"SET_LOADING",payload:true});
      try {
        var results = await Promise.allSettled([
          api.get("/ai-os/conversations"),
          api.get("/ai-os/context"),
          api.get("/ai-os/insights"),
          api.get("/ai-os/memory"),
        ]);
        if(results[0].status==="fulfilled"){var d=results[0].value.data;dispatch({type:"SET_CONVERSATIONS",payload:Array.isArray(d)?d:d.conversations||[]});}
        if(results[1].status==="fulfilled") dispatch({type:"SET_CONTEXT",payload:results[1].value.data});
        if(results[2].status==="fulfilled"){var d2=results[2].value.data;dispatch({type:"SET_INSIGHTS",payload:Array.isArray(d2)?d2:d2.insights||[]});}
        if(results[3].status==="fulfilled"){var d3=results[3].value.data;dispatch({type:"SET_MEMORY",payload:Array.isArray(d3)?d3:d3.memories||[]});}
      } finally { dispatch({type:"SET_LOADING",payload:false}); }
    }
    init();
  },[]);

  useEffect(function(){
    function h(e){if((e.metaKey||e.ctrlKey)&&e.key==="n"){e.preventDefault();handleNewChat();}}
    window.addEventListener("keydown",h);
    return function(){window.removeEventListener("keydown",h);};
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[]);

  async function handleNewChat() {
    try {
      var res = await api.post("/ai-os/conversations",{title:"New session",agent_type:state.selectedAgent==="auto"?null:state.selectedAgent});
      dispatch({type:"ADD_CONV",payload:res.data});
    } catch(e) { toast.error("Failed to create session"); }
  }

  async function handleSelectConv(id) {
    if(!id||id===state.activeConvId) return;
    dispatch({type:"SET_ACTIVE_CONV",payload:id});
    try {
      var res = await api.get("/ai-os/conversations/"+id);
      var msgs = (res.data.messages||[]).map(function(m){return {id:m.id||m.message_id||"msg-"+Math.random(),role:m.role,content:m.content,agent_type:m.agent_type,sources:m.sources,suggested_actions:m.suggested_actions};});
      dispatch({type:"SET_MESSAGES",payload:msgs});
    } catch(e) { toast.error("Failed to load session"); }
  }

  async function handlePin(id, pinned) {
    try {
      await api.patch("/ai-os/conversations/"+id,{pinned:pinned});
      dispatch({type:"SET_CONVERSATIONS",payload:state.conversations.map(function(c){return c.id===id?Object.assign({},c,{pinned:pinned}):c;})});
    } catch(e) { toast.error("Failed to update"); }
  }

  async function handleArchive(id) {
    try {
      await api.patch("/ai-os/conversations/"+id,{archived:true});
      dispatch({type:"REMOVE_CONV",id:id});
      toast.success("Archived");
    } catch(e) { toast.error("Failed to archive"); }
  }

  function handleDeleteConv(id) {
    setConfirm({
      title:"Delete research session?",message:"This action cannot be undone.",danger:true,confirmLabel:"Delete",
      onConfirm:async function(){
        setConfirm(null);
        try{await api.delete("/ai-os/conversations/"+id);dispatch({type:"REMOVE_CONV",id:id});toast.success("Deleted");}
        catch(e){toast.error("Failed to delete");}
      },
    });
  }

  async function handleTitleChange(id, title) {
    try{await api.patch("/ai-os/conversations/"+id,{title:title});dispatch({type:"UPDATE_CONV_TITLE",id:id,title:title});}
    catch(e){toast.error("Failed to rename");}
  }

  async function handleSend() {
    var text = state.inputText.trim();
    if(!text||state.sending) return;
    var convId = state.activeConvId;
    if(!convId){
      try{
        var newConv = await api.post("/ai-os/conversations",{title:text.slice(0,60),agent_type:state.selectedAgent==="auto"?null:state.selectedAgent});
        dispatch({type:"ADD_CONV",payload:newConv.data});
        convId = newConv.data.id||newConv.data._id;
      } catch(e){toast.error("Failed to create session");return;}
    }
    var userMsgId = "user-"+Date.now();
    var typingId  = "typing-"+Date.now();
    dispatch({type:"SET_INPUT",payload:""});
    dispatch({type:"SET_SENDING",payload:true});
    dispatch({type:"ADD_MESSAGE",payload:{id:userMsgId,role:"user",content:text}});
    dispatch({type:"ADD_MESSAGE",payload:{id:typingId,role:"assistant",isTyping:true}});
    retryDataRef.current[typingId] = {text:text,convId:convId};
    try{
      var res = await api.post("/ai-os/conversations/"+convId+"/messages",{message:text,agent_type:state.selectedAgent==="auto"?undefined:state.selectedAgent});
      var d = res.data;
      dispatch({type:"REPLACE_MESSAGE",id:typingId,payload:{id:d.message_id||typingId,role:"assistant",content:d.response,agent_type:d.agent_type,sources:d.sources,suggested_actions:d.suggested_actions,isTyping:false}});
      if(d.conversation_title) dispatch({type:"UPDATE_CONV_TITLE",id:convId,title:d.conversation_title});
    } catch(e){
      dispatch({type:"REPLACE_MESSAGE",id:typingId,payload:{id:typingId,role:"assistant",content:(e&&e.response&&e.response.data&&e.response.data.detail)||"Something went wrong. Please try again.",error:true,isTyping:false}});
    } finally{dispatch({type:"SET_SENDING",payload:false});}
  }

  async function handleRetry(msgId) {
    var data = retryDataRef.current[msgId];
    if(!data) return;
    dispatch({type:"REPLACE_MESSAGE",id:msgId,payload:{isTyping:true,error:false,content:""}});
    try{
      var res = await api.post("/ai-os/conversations/"+data.convId+"/messages",{message:data.text});
      var r = res.data;
      dispatch({type:"REPLACE_MESSAGE",id:msgId,payload:{content:r.response,agent_type:r.agent_type,sources:r.sources,suggested_actions:r.suggested_actions,isTyping:false,error:false}});
    } catch(e){
      dispatch({type:"REPLACE_MESSAGE",id:msgId,payload:{content:(e&&e.response&&e.response.data&&e.response.data.detail)||"Retry failed.",isTyping:false,error:true}});
    }
  }

  function handleActionClick(action) {
    setActionConfirm({action:action,title:"Execute: "+(action.label||action.action_type)+"?",message:action.description||"This will execute the \""+action.action_type+"\" action.",confirmLabel:"Execute"});
  }

  async function executeAction(action) {
    setActionConfirm(null);
    try{
      await api.post("/ai-os/actions/execute",{action_type:action.action_type,params:action.params||{},conv_id:state.activeConvId});
      toast.success("Action completed");
    } catch(e){toast.error((e&&e.response&&e.response.data&&e.response.data.detail)||"Action failed");}
  }

  async function handleRefreshContext() {
    try{
      await api.post("/ai-os/context/refresh");
      var res = await api.get("/ai-os/context");
      dispatch({type:"SET_CONTEXT",payload:res.data});
      toast.success("Context refreshed");
    } catch(e){toast.error("Failed to refresh context");}
  }

  async function handleDeleteMemory(id) {
    try{await api.delete("/ai-os/memory/"+id);dispatch({type:"REMOVE_MEMORY",id:id});toast.success("Memory removed");}
    catch(e){toast.error("Failed to remove memory");}
  }

  function handleClearMemory() {
    setConfirm({
      title:"Clear all memory?",
      message:"This will permanently delete all AI memory under GDPR Article 17 (right to erasure). This cannot be undone.",
      danger:true,confirmLabel:"Clear All Memory",
      onConfirm:async function(){
        setConfirm(null);
        try{await api.delete("/ai-os/memory");dispatch({type:"CLEAR_MEMORY"});toast.success("Memory cleared");}
        catch(e){toast.error("Failed to clear memory");}
      },
    });
  }

  async function handleStartWithAgent(agentId, promptPrefix) {
    dispatch({type:"SET_AGENT",payload:agentId});
    dispatch({type:"SET_INPUT",payload:promptPrefix});
  }

  var hasConv = !!state.activeConvId;

  return (
    <AIWorkspaceLayout>
    <div style={{margin:"-24px",display:"flex",flexDirection:"column",background:WARM,overflow:"hidden",fontFamily:"system-ui,-apple-system,sans-serif",height:"calc(100vh - 120px)"}}>
      <header style={{flexShrink:0,display:"flex",alignItems:"center",justifyContent:"space-between",padding:"0 18px",height:52,background:"#fff",borderBottom:"1px solid "+BORDER,zIndex:10}}>
        <div style={{display:"flex",alignItems:"center",gap:12}}>
          <button onClick={function(){dispatch({type:"TOGGLE_LEFT"});}}
            style={{background:"none",border:"none",cursor:"pointer",color:"#94a3b8",padding:6,borderRadius:6,display:"flex",alignItems:"center"}}
            onMouseEnter={function(e){e.currentTarget.style.color=NAVY;}} onMouseLeave={function(e){e.currentTarget.style.color="#94a3b8";}}>
            {state.leftPanelOpen ? <ChevronLeft size={16}/> : <ChevronRight size={16}/>}
          </button>
          <div style={{display:"flex",alignItems:"center",gap:9}}>
            <div style={{position:"relative",width:24,height:24}}>
              <div style={{position:"absolute",width:14,height:14,borderRadius:"50%",background:NAVY,top:0,left:0}}/>
              <div style={{position:"absolute",width:10,height:10,borderRadius:"50%",background:ACCENT,top:7,left:8}}/>
            </div>
            <span style={{fontSize:"0.9rem",fontWeight:700,color:NAVY,letterSpacing:"-0.01em"}}>Synaptiq AI</span>
          </div>
          {hasConv && activeConv && (
            <div style={{display:"flex",alignItems:"center",gap:6,marginLeft:8}}>
              <span style={{color:"#CBD5E1",fontSize:"0.8rem"}}>/</span>
              <span style={{fontSize:"0.82rem",color:"#64748b",maxWidth:240,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{activeConv.title||"New session"}</span>
            </div>
          )}
        </div>
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          {state.context && state.context.credits_remaining!=null && (
            <div style={{display:"flex",alignItems:"center",gap:5,padding:"4px 10px",background:WARM,border:"1px solid "+BORDER,borderRadius:8,fontSize:"0.75rem",color:"#374151",fontWeight:500}}>
              <Sparkles size={11} style={{color:NAVY}}/>{state.context.credits_remaining} credits
            </div>
          )}
          <button onClick={handleNewChat}
            style={{display:"flex",alignItems:"center",gap:6,padding:"7px 14px",background:NAVY,color:"#fff",border:"none",borderRadius:9,cursor:"pointer",fontSize:"0.8rem",fontWeight:600}}
            onMouseEnter={function(e){e.currentTarget.style.background=NAVY2;}} onMouseLeave={function(e){e.currentTarget.style.background=NAVY;}}>
            <Plus size={13}/>New
          </button>
          <button onClick={function(){dispatch({type:"TOGGLE_RIGHT"});}}
            style={{background:"none",border:"none",cursor:"pointer",color:"#94a3b8",padding:6,borderRadius:6,display:"flex",alignItems:"center"}}
            onMouseEnter={function(e){e.currentTarget.style.color=NAVY;}} onMouseLeave={function(e){e.currentTarget.style.color="#94a3b8";}}>
            {state.rightPanelOpen ? <ChevronRight size={16}/> : <ChevronLeft size={16}/>}
          </button>
        </div>
      </header>

      <div style={{flex:1,display:"flex",overflow:"hidden"}}>
        <LeftPanel state={state} dispatch={dispatch} onNewChat={handleNewChat} onSelectConv={handleSelectConv} onPin={handlePin} onArchive={handleArchive} onDelete={handleDeleteConv}/>
        <div style={{flex:1,display:"flex",flexDirection:"column",minWidth:0,overflow:"hidden"}}>
          {hasConv ? (
            <>
              <ConversationHeader conv={activeConv} onPin={handlePin} onArchive={handleArchive} onDelete={handleDeleteConv} onTitleChange={handleTitleChange}/>
              <MessageThread messages={state.messages} onActionClick={handleActionClick} onRetry={handleRetry}/>
              <InputArea state={state} dispatch={dispatch} onSend={handleSend}/>
            </>
          ) : (
            <>
              <WelcomeScreen user={user} context={state.context} conversations={state.conversations} insights={state.insights} onStartWithAgent={handleStartWithAgent} onSelectConv={handleSelectConv}/>
              <InputArea state={state} dispatch={dispatch} onSend={handleSend}/>
            </>
          )}
        </div>
        <RightPanel state={state} dispatch={dispatch} onRefreshContext={handleRefreshContext} onDeleteMemory={handleDeleteMemory} onClearMemory={handleClearMemory}/>
      </div>

      {confirm && <ConfirmModal title={confirm.title} message={confirm.message} danger={confirm.danger} confirmLabel={confirm.confirmLabel} onConfirm={confirm.onConfirm} onCancel={function(){setConfirm(null);}}/>}
      {actionConfirm && <ConfirmModal title={actionConfirm.title} message={actionConfirm.message} confirmLabel={actionConfirm.confirmLabel} onConfirm={function(){executeAction(actionConfirm.action);}} onCancel={function(){setActionConfirm(null);}}/>}
    </div>
    </AIWorkspaceLayout>
  );
}

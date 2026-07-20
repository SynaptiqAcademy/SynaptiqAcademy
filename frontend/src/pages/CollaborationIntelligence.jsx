import React, { useState, useCallback, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Sparkles, Lock, RotateCcw, Clock, Users, Globe, Building2, GraduationCap,
  MessageSquare, FolderPlus, Link2, ChevronDown, ChevronUp, ChevronRight,
  Target, Zap, BookOpen, Award, AlertCircle, Filter, X, User,
  ArrowRight, CheckCircle2, Layers, Send,
} from "lucide-react";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { USER_TYPE_OPTIONS as USER_TYPE_FILTER_OPTIONS_BASE, PRIMARY_DOMAIN_OPTIONS, userTypeLabel } from "../lib/userTypes";
import { WARM } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";

// ─────────────────────── ai nav ──────────────────────────────────────────────



// ─────────────────────── score ring ──────────────────────────────────────────

function ScoreRing({ score, size = 64 }) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score || 0));
  const dash = (pct / 100) * circ;
  const color =
    pct >= 75 ? "#166534" :
    pct >= 55 ? "#1d4ed8" :
    pct >= 40 ? "#b45309" : "#9f1239";

  return (
    <svg width={size} height={size} className="shrink-0">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={4} />
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke={color} strokeWidth={4}
        strokeDasharray={`${dash} ${circ - dash}`}
        strokeLinecap="butt"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text
        x={size / 2} y={size / 2 + 1}
        textAnchor="middle" dominantBaseline="middle"
        className="font-serif" fontSize={size < 56 ? 11 : 14} fill={color} fontWeight="600"
      >
        {pct}
      </text>
    </svg>
  );
}

// ─────────────────────── score bar ───────────────────────────────────────────

function ScoreBar({ label, value, max }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span className="text-xs text-slate-500">{label}</span>
        <span className="text-xs font-mono text-slate-700">{value}/{max}</span>
      </div>
      <div className="h-1 bg-slate-100">
        <div className="h-1 bg-[#0F2847] transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ─────────────────────── primitives ──────────────────────────────────────────

function SectionHeader({ icon: Icon, label, color = "#0F2847" }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon size={15} strokeWidth={1.5} style={{ color }} />
      <div className="overline" style={{ color }}>{label}</div>
    </div>
  );
}

function Tag({ children, className = "" }) {
  return (
    <span className={`inline-block border border-slate-200 text-slate-600 text-xs px-2 py-0.5 ${className}`}>
      {children}
    </span>
  );
}

function ScoreBadge({ score }) {
  const color =
    score >= 75 ? "border-green-700 text-green-700" :
    score >= 55 ? "border-blue-700 text-blue-700" :
    score >= 40 ? "border-amber-700 text-amber-700" : "border-rose-800 text-rose-800";
  return (
    <span className={`text-xs font-mono border px-1.5 py-0.5 ${color}`}>{score}</span>
  );
}

function FilterPill({ label, value, onRemove }) {
  return (
    <div className="flex items-center gap-1.5 border border-slate-300 bg-slate-50 px-2 py-1">
      <span className="text-xs text-slate-600">{label}: <span className="font-medium">{value}</span></span>
      <button onClick={onRemove} className="text-slate-400 hover:text-slate-700">
        <X size={11} strokeWidth={2} />
      </button>
    </div>
  );
}

// ─────────────────────── gate view ───────────────────────────────────────────

function GateView() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-20">
      <div className="max-w-md w-full border border-slate-200 bg-white p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-slate-900 flex items-center justify-center shrink-0">
            <Users size={18} strokeWidth={1.5} className="text-white" />
          </div>
          <div>
            <div className="font-serif text-lg text-slate-900">Collaboration Intelligence</div>
            <div className="text-xs text-slate-500 mt-0.5">Pro Researcher · Institution</div>
          </div>
        </div>
        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          AI-powered matchmaking that analyses your research profile and finds the most
          compatible collaborators based on topic alignment, methodology, publication
          history, and complementary strengths.
        </p>
        <ul className="space-y-2.5 mb-8">
          {[
            "Compatibility scores 0–100 with transparent breakdowns",
            "Why This Match — specific explanations, not generic text",
            "5-component scoring: topic, method, publication, funding, potential",
            "Smart filters by research area, method, country, and role",
            "Suggested actions: message, workspace invite, project",
            "Recommended collaboration types for each match",
            "Persistent history of past recommendation runs",
          ].map((f, i) => (
            <li key={i} className="flex items-start gap-2.5 text-sm text-slate-700">
              <CheckCircle2 size={14} strokeWidth={1.5} className="text-[#0F2847] mt-0.5 shrink-0" />
              <span>{f}</span>
            </li>
          ))}
        </ul>
        <Link
          to="/pricing"
          className="flex items-center justify-between w-full border border-[#0F2847] bg-[#0F2847] text-white px-4 py-3 text-sm font-medium hover:bg-slate-800 transition-colors"
        >
          <span>Upgrade to Pro Researcher</span>
          <ArrowRight size={15} strokeWidth={1.5} />
        </Link>
        <div className="mt-3 text-center text-xs text-slate-400">
          15 credits per recommendation run
        </div>
      </div>
    </div>
  );
}

// ─────────────────────── filter panel ────────────────────────────────────────

const USER_TYPE_FILTER_OPTIONS = USER_TYPE_FILTER_OPTIONS_BASE;

function FilterPanel({ filters, onChange }) {
  const [areaInput, setAreaInput] = useState("");

  const addArea = () => {
    const val = areaInput.trim();
    if (!val || (filters.research_areas || []).includes(val)) return;
    onChange({ ...filters, research_areas: [...(filters.research_areas || []), val] });
    setAreaInput("");
  };

  const removeArea = (area) => {
    onChange({ ...filters, research_areas: (filters.research_areas || []).filter((a) => a !== area) });
  };

  return (
    <div className="border border-slate-200 bg-white p-5 space-y-5">
      <div className="overline text-slate-500">Filters</div>

      {/* Research areas */}
      <div>
        <label className="block text-xs font-medium text-slate-700 mb-2">Research Areas</label>
        <div className="flex gap-2">
          <input
            value={areaInput}
            onChange={(e) => setAreaInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addArea(); } }}
            placeholder="e.g. Machine Learning"
            className="flex-1 border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:border-[#0F2847]"
          />
          <button
            onClick={addArea}
            className="border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            Add
          </button>
        </div>
        {(filters.research_areas || []).length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {(filters.research_areas || []).map((a) => (
              <FilterPill key={a} label="area" value={a} onRemove={() => removeArea(a)} />
            ))}
          </div>
        )}
      </div>

      {/* Country */}
      <div>
        <label className="block text-xs font-medium text-slate-700 mb-2">Country</label>
        <input
          value={filters.country || ""}
          onChange={(e) => onChange({ ...filters, country: e.target.value || undefined })}
          placeholder="e.g. Germany"
          className="w-full border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:border-[#0F2847]"
        />
      </div>

      {/* User type */}
      <div>
        <label className="block text-xs font-medium text-slate-700 mb-2">Platform Category</label>
        <select
          value={filters.user_type || ""}
          onChange={(e) => onChange({ ...filters, user_type: e.target.value || undefined })}
          className="w-full border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:border-[#0F2847] bg-white"
        >
          <option value="">Any category</option>
          {USER_TYPE_FILTER_OPTIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
      </div>

      {/* Primary domain */}
      <div>
        <label className="block text-xs font-medium text-slate-700 mb-2">Primary Focus</label>
        <select
          value={filters.primary_domain || ""}
          onChange={(e) => onChange({ ...filters, primary_domain: e.target.value || undefined })}
          className="w-full border border-slate-200 px-3 py-1.5 text-sm focus:outline-none focus:border-[#0F2847] bg-white"
        >
          <option value="">Any focus</option>
          {PRIMARY_DOMAIN_OPTIONS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
        </select>
      </div>

      {/* Min score */}
      <div>
        <label className="block text-xs font-medium text-slate-700 mb-2">
          Min Compatibility Score: <span className="font-mono text-[#0F2847]">{filters.min_score ?? 0}</span>
        </label>
        <input
          type="range" min={0} max={90} step={5}
          value={filters.min_score ?? 0}
          onChange={(e) => onChange({ ...filters, min_score: Number(e.target.value) })}
          className="w-full accent-[#0F2847]"
        />
        <div className="flex justify-between text-xs text-slate-400 mt-0.5">
          <span>0</span><span>90</span>
        </div>
      </div>

      <button
        onClick={() => onChange({ research_areas: [], min_score: 0 })}
        className="w-full text-xs text-slate-500 hover:text-slate-700 py-1"
      >
        Clear filters
      </button>
    </div>
  );
}

// ─────────────────────── action buttons ──────────────────────────────────────

// ─────────────────────── send request modal ──────────────────────────────────

function SendRequestModal({ researcher, onClose }) {
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(null);

  const handleSend = async () => {
    setSending(true);
    setError(null);
    try {
      await api.post("/collaboration-requests", {
        receiver_id: researcher.id,
        message: message.trim(),
        source: "collab_intel",
      });
      setDone(true);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to send request.");
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white w-full max-w-md border border-slate-200 shadow-lg">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <div className="font-serif text-base text-slate-900">Send Collaboration Request</div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>
        {done ? (
          <div className="px-5 py-8 text-center space-y-3">
            <CheckCircle2 size={32} className="text-green-600 mx-auto" strokeWidth={1.5} />
            <div className="font-serif text-base text-slate-900">Request Sent</div>
            <p className="text-sm text-slate-500">
              {researcher.full_name} will be notified of your collaboration request.
            </p>
            <button onClick={onClose} className="text-sm text-[#0F2847] hover:underline">Close</button>
          </div>
        ) : (
          <div className="px-5 py-5 space-y-4">
            <div className="flex items-center gap-3 bg-slate-50 border border-slate-100 px-3 py-2.5">
              <div className="w-8 h-8 bg-slate-200 flex items-center justify-center text-xs font-medium text-slate-600">
                {(researcher.full_name || "?").split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)}
              </div>
              <div>
                <div className="text-sm font-medium text-slate-900">{researcher.full_name}</div>
                <div className="text-xs text-slate-500">{researcher.institution}</div>
              </div>
            </div>
            {error && <div className="text-sm text-rose-600 border border-rose-200 bg-rose-50 px-3 py-2">{error}</div>}
            <div>
              <label className="block overline text-slate-500 mb-2">Message (optional)</label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={4}
                placeholder="Introduce yourself and explain why you'd like to collaborate…"
                className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847] resize-none"
              />
            </div>
            <div className="flex gap-3">
              <button onClick={onClose} className="flex-1 border border-slate-200 text-slate-600 px-4 py-2 text-sm hover:bg-slate-50">Cancel</button>
              <button
                onClick={handleSend}
                disabled={sending}
                className="flex-1 flex items-center justify-center gap-2 bg-[#0F2847] text-white px-4 py-2 text-sm hover:bg-slate-800 disabled:opacity-50"
              >
                <Send size={13} strokeWidth={1.5} />
                {sending ? "Sending…" : "Send Request"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────── start project together modal ────────────────────────

function StartProjectModal({ researcher, onClose }) {
  const navigate = useNavigate();
  const [title, setTitle] = useState(`Collaboration: ${researcher.full_name || "Researcher"}`);
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const sharedAreas = (researcher.research_areas || []).slice(0, 3);

  const handleCreate = async () => {
    if (!title.trim()) { setError("Title is required."); return; }
    setSaving(true);
    setError(null);
    try {
      const { data: proj } = await api.post("/projects", {
        title: title.trim(),
        description: description.trim(),
        visibility: "team",
        source: "collab_intel",
        objectives: sharedAreas.map((a) => `Research in: ${a}`),
        initial_member_ids: [researcher.id],
      });
      navigate(`/projects/${proj.id}`);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to create project.");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white w-full max-w-md border border-slate-200 shadow-lg">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <div className="font-serif text-base text-slate-900">Start Project Together</div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>
        <div className="px-5 py-5 space-y-4">
          {error && <div className="text-sm text-rose-600 border border-rose-200 bg-rose-50 px-3 py-2">{error}</div>}
          <div className="flex items-center gap-3 bg-slate-50 border border-slate-100 px-3 py-2.5">
            <div className="w-8 h-8 bg-slate-200 flex items-center justify-center text-xs font-medium text-slate-600">
              {(researcher.full_name || "?").split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)}
            </div>
            <div className="text-sm text-slate-700">
              <span className="font-medium">{researcher.full_name}</span> will receive a collaboration invitation.
            </div>
          </div>
          <div>
            <label className="block overline text-slate-500 mb-2">Project Title *</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847]"
            />
          </div>
          <div>
            <label className="block overline text-slate-500 mb-2">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:border-[#0F2847] resize-none"
            />
          </div>
          {sharedAreas.length > 0 && (
            <div className="text-xs text-slate-500 flex flex-wrap gap-1.5">
              <span>Research areas:</span>
              {sharedAreas.map((a) => (
                <span key={a} className="border border-slate-200 px-2 py-0.5 text-slate-600">{a}</span>
              ))}
            </div>
          )}
          <div className="flex gap-3 pt-1">
            <button onClick={onClose} className="flex-1 border border-slate-200 text-slate-600 px-4 py-2 text-sm hover:bg-slate-50">Cancel</button>
            <button
              onClick={handleCreate}
              disabled={saving}
              className="flex-1 flex items-center justify-center gap-2 bg-[#0F2847] text-white px-4 py-2 text-sm hover:bg-slate-800 disabled:opacity-50"
            >
              <FolderPlus size={13} strokeWidth={1.5} />
              {saving ? "Creating…" : "Create Project"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ActionButtons({ researcher }) {
  const rid = researcher?.id;
  return (
    <div className="flex flex-wrap gap-2 pt-3 border-t border-slate-100">
      <Link
        to={rid ? `/messages/${rid}` : "/messages"}
        className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
      >
        <MessageSquare size={12} strokeWidth={1.5} />
        Send Message
      </Link>
      <Link
        to="/collaboration-requests"
        className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
      >
        <Link2 size={12} strokeWidth={1.5} />
        View Requests
      </Link>
      <Link
        to="/workspaces"
        className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
      >
        <Layers size={12} strokeWidth={1.5} />
        Invite to Workspace
      </Link>
    </div>
  );
}

// ─────────────────────── researcher card ─────────────────────────────────────

function ResearcherCard({ rec }) {
  const [expanded, setExpanded] = useState(false);
  const [showSendRequest, setShowSendRequest] = useState(false);
  const [showStartProject, setShowStartProject] = useState(false);
  const r = rec.researcher || {};
  const score = rec.compatibility_score || 0;
  const initials = (r.full_name || "?")
    .split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2);
  const sc = rec.score_components || {};
  const Chev = expanded ? ChevronUp : ChevronDown;

  return (
    <div className="border border-slate-200 bg-white">
      {showSendRequest && <SendRequestModal researcher={r} onClose={() => setShowSendRequest(false)} />}
      {showStartProject && <StartProjectModal researcher={r} onClose={() => setShowStartProject(false)} />}
      {/* Header */}
      <div className="flex items-start gap-4 p-5">
        <div className="w-12 h-12 bg-slate-100 flex items-center justify-center shrink-0 text-sm font-medium text-slate-600 overflow-hidden">
          {r.avatar_url
            ? <img src={r.avatar_url} alt="" className="w-full h-full object-cover" />
            : initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="font-serif text-base text-slate-900 leading-snug">
                {r.full_name || "Unknown Researcher"}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                {[userTypeLabel(r), r.institution].filter(Boolean).join(" · ")}
              </div>
              {r.country && (
                <div className="flex items-center gap-1 mt-1 text-xs text-slate-400">
                  <Globe size={10} strokeWidth={1.5} />
                  {r.country}
                </div>
              )}
            </div>
            <ScoreRing score={score} size={56} />
          </div>

          {/* Research areas */}
          {(r.research_areas || []).length > 0 && (
            <div className="flex flex-wrap gap-1 mt-3">
              {(r.research_areas || []).slice(0, 4).map((a) => (
                <Tag key={a}>{a}</Tag>
              ))}
              {(r.research_areas || []).length > 4 && (
                <Tag>+{r.research_areas.length - 4}</Tag>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Why this match */}
      {rec.why_text && (
        <div className="px-5 pb-3">
          <div className="bg-slate-50 border border-slate-100 px-4 py-3">
            <div className="overline text-slate-400 mb-1.5" style={{ fontSize: 9 }}>Why This Match</div>
            <p className="text-sm text-slate-700 leading-relaxed">{rec.why_text}</p>
          </div>
        </div>
      )}

      {/* Match reasons */}
      {(rec.match_reasons || []).length > 0 && (
        <div className="px-5 pb-3 flex flex-wrap gap-1.5">
          {(rec.match_reasons || []).map((reason, i) => (
            <span key={i} className="flex items-center gap-1 text-xs text-slate-600 bg-slate-50 border border-slate-200 px-2 py-1">
              <CheckCircle2 size={10} strokeWidth={2} className="text-[#0F2847] shrink-0" />
              {reason}
            </span>
          ))}
        </div>
      )}

      {/* Expandable detail */}
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center justify-between px-5 py-3 text-xs text-slate-500 hover:bg-slate-50 border-t border-slate-100 transition-colors"
      >
        <span>Score breakdown &amp; collaboration types</span>
        <Chev size={13} strokeWidth={1.5} />
      </button>

      {expanded && (
        <div className="px-5 pb-5 pt-4 border-t border-slate-100 space-y-5">
          {/* Score components */}
          <div>
            <div className="overline text-slate-400 mb-3" style={{ fontSize: 9 }}>Score Breakdown</div>
            <div className="space-y-2.5">
              <ScoreBar label="Research Topic Match" value={sc.topic_match || 0} max={30} />
              <ScoreBar label="Methodology Match" value={sc.method_match || 0} max={20} />
              <ScoreBar label="Publication Match" value={sc.publication_match || 0} max={20} />
              <ScoreBar label="Funding Alignment" value={sc.funding_match || 0} max={15} />
              <ScoreBar label="Collaboration Potential" value={sc.collaboration_potential || 0} max={15} />
            </div>
          </div>

          {/* Complementary strengths */}
          {(rec.complementary_strengths || []).length > 0 && (
            <div>
              <div className="overline text-slate-400 mb-2" style={{ fontSize: 9 }}>Complementary Strengths</div>
              <ul className="space-y-1.5">
                {(rec.complementary_strengths || []).map((s, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-600">
                    <Zap size={12} strokeWidth={1.5} className="text-amber-600 mt-0.5 shrink-0" />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Collaboration types */}
          {(rec.potential_collaboration_types || []).length > 0 && (
            <div>
              <div className="overline text-slate-400 mb-2" style={{ fontSize: 9 }}>Suggested Collaboration Types</div>
              <ul className="space-y-1.5">
                {(rec.potential_collaboration_types || []).map((t, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-600">
                    <ArrowRight size={12} strokeWidth={1.5} className="text-[#0F2847] mt-0.5 shrink-0" />
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Caution note */}
          {rec.caution && (
            <div className="flex gap-2.5 border border-amber-200 bg-amber-50 px-3 py-2.5">
              <AlertCircle size={13} strokeWidth={1.5} className="text-amber-600 mt-0.5 shrink-0" />
              <p className="text-xs text-amber-800 leading-relaxed">{rec.caution}</p>
            </div>
          )}

          {/* Profile link */}
          {r.id && (
            <Link
              to={`/profile/${r.id}`}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-[#0F2847]"
            >
              <User size={11} strokeWidth={1.5} />
              View full profile
            </Link>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="px-5 pb-5">
        <div className="flex flex-wrap gap-2 pt-3 border-t border-slate-100">
          <button
            onClick={() => setShowSendRequest(true)}
            className="flex items-center gap-1.5 text-xs text-white bg-[#0F2847] border border-[#0F2847] px-3 py-1.5 hover:bg-slate-800 transition-colors"
          >
            <Send size={11} strokeWidth={1.5} />
            Send Request
          </button>
          <button
            onClick={() => setShowStartProject(true)}
            className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
          >
            <FolderPlus size={11} strokeWidth={1.5} />
            Start Project Together
          </button>
          <Link
            to={r.id ? `/messages/${r.id}` : "/messages"}
            className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
          >
            <MessageSquare size={11} strokeWidth={1.5} />
            Message
          </Link>
          <Link
            to="/workspaces"
            className="flex items-center gap-1.5 text-xs text-slate-600 border border-slate-200 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
          >
            <Layers size={11} strokeWidth={1.5} />
            Invite to Workspace
          </Link>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────── history item ────────────────────────────────────────

function HistoryItem({ run, active, onClick }) {
  const date = run.created_at
    ? new Date(run.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })
    : "—";
  return (
    <button
      data-testid={TID.collaborationIntelHistoryItem(run.id)}
      onClick={onClick}
      className={`w-full text-left px-3 py-2.5 border-b border-slate-100 hover:bg-slate-50 transition-colors ${active ? "bg-slate-100" : ""}`}
    >
      <div className="text-xs font-medium text-slate-700">{date}</div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-xs text-slate-500">{run.recommendation_count || 0} matches</span>
        <span className="text-xs text-slate-300">·</span>
        <span className="text-xs text-slate-400 font-mono">{run.credits_used || 0} cr</span>
      </div>
    </button>
  );
}

// ─────────────────────── empty state ─────────────────────────────────────────

function EmptyState({ onGenerate, loading }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
      <div className="w-16 h-16 bg-slate-100 flex items-center justify-center mb-6">
        <Users size={28} strokeWidth={1} className="text-slate-400" />
      </div>
      <div className="font-serif text-xl text-slate-800 mb-2">Find Your Ideal Collaborators</div>
      <p className="text-sm text-slate-500 max-w-sm leading-relaxed mb-8">
        Your research profile will be analysed against every researcher on the platform to find
        the most compatible collaborators — ranked by topic alignment, methodology, and potential.
      </p>
      <button
        onClick={onGenerate}
        disabled={loading}
        className="flex items-center gap-2 border border-[#0F2847] bg-[#0F2847] text-white px-6 py-3 text-sm font-medium hover:bg-slate-800 transition-colors disabled:opacity-50"
      >
        <Sparkles size={15} strokeWidth={1.5} />
        {loading ? "Generating…" : "Generate Recommendations"}
      </button>
      <div className="mt-3 text-xs text-slate-400">15 credits per run</div>
    </div>
  );
}

// ─────────────────────── loading skeleton ────────────────────────────────────

function CardSkeleton() {
  return (
    <div className="border border-slate-200 bg-white p-5 animate-pulse">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 bg-slate-100 shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-slate-100 rounded w-2/3" />
          <div className="h-3 bg-slate-100 rounded w-1/2" />
          <div className="h-3 bg-slate-100 rounded w-1/3" />
        </div>
        <div className="w-14 h-14 rounded-full bg-slate-100 shrink-0" />
      </div>
      <div className="mt-4 space-y-1.5">
        <div className="h-3 bg-slate-100 rounded" />
        <div className="h-3 bg-slate-100 rounded w-4/5" />
      </div>
      <div className="mt-4 flex gap-2">
        {[1, 2, 3].map((i) => <div key={i} className="h-5 w-20 bg-slate-100 rounded" />)}
      </div>
    </div>
  );
}

// ─────────────────────── main page ───────────────────────────────────────────

export default function CollaborationIntelligence() {
  const location = useLocation();
  const [gated, setGated] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState(null);
  const autoRunFired = useRef(false);

  // Parse context injected from Gap Finder
  const searchParams = new URLSearchParams(location.search);
  const fromGap = searchParams.get("from_gap") === "1";
  const gapTopic = searchParams.get("topic") || "";
  const gapQuestion = searchParams.get("question") || "";
  const gapKeywords = searchParams.get("keywords")?.split(",").filter(Boolean) || [];
  const gapDiscipline = searchParams.get("discipline") || "";

  const initialAreas = gapTopic
    ? [...gapKeywords.slice(0, 3), ...(gapDiscipline ? [gapDiscipline] : [])].slice(0, 4)
    : [];

  const [filters, setFilters] = useState({ research_areas: initialAreas, min_score: 0 });
  const [showFilters, setShowFilters] = useState(false);
  const [recommendations, setRecommendations] = useState(null);
  const [runMeta, setRunMeta] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeRunId, setActiveRunId] = useState(null);
  const [gapContext, setGapContext] = useState(
    fromGap ? { topic: gapTopic, question: gapQuestion, keywords: gapKeywords } : null
  );

  // Load latest cached recommendations + history on mount
  const fetchLatest = useCallback(async () => {
    try {
      const [recRes, histRes] = await Promise.all([
        api.get("/collaboration-intelligence/recommendations"),
        api.get("/collaboration-intelligence/history"),
      ]);
      if (recRes.data.recommendations?.length > 0) {
        setRecommendations(recRes.data.recommendations);
        setRunMeta(recRes.data.run);
        setActiveRunId(recRes.data.run?.id);
      }
      setHistory(histRes.data || []);
    } catch (err) {
      if (err?.response?.status === 402) {
        setGated(true);
      }
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => { fetchLatest(); }, [fetchLatest]);

  // Auto-run if navigated from Gap Finder with context
  const handleGenerate = useCallback(async (overrideFilters) => {
    const activeFilters = overrideFilters || filters;
    setLoading(true);
    setError(null);
    try {
      const payload = {
        research_areas: activeFilters.research_areas || [],
        methods: [],
        min_score: activeFilters.min_score || 0,
      };
      if (activeFilters.country) payload.country = activeFilters.country;
      if (activeFilters.user_type) payload.user_type = activeFilters.user_type;
      if (activeFilters.primary_domain) payload.primary_domain = activeFilters.primary_domain;

      const res = await api.post("/collaboration-intelligence/generate", payload);
      setRecommendations(res.data.recommendations || []);
      setRunMeta({
        id: res.data.id,
        created_at: res.data.created_at,
        recommendation_count: (res.data.recommendations || []).length,
        credits_used: res.data.credits_used,
      });
      setActiveRunId(res.data.id);
      const histRes = await api.get("/collaboration-intelligence/history");
      setHistory(histRes.data || []);
    } catch (err) {
      if (err?.response?.status === 402) {
        // UpgradeModal handles 402 globally via synaptiq:gate event
        setGated(true);
      } else {
        setError(err?.response?.data?.detail || "Failed to generate recommendations. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    if (fromGap && !autoRunFired.current && !loadingHistory) {
      autoRunFired.current = true;
      handleGenerate({ research_areas: initialAreas, min_score: 0 });
    }
  }, [fromGap, loadingHistory, handleGenerate, initialAreas]);

  // Apply filters against cached recommendations
  const fetchFiltered = useCallback(async () => {
    if (!runMeta) return;
    try {
      const params = {};
      if (filters.country) params.country = filters.country;
      if (filters.user_type) params.user_type = filters.user_type;
      if (filters.primary_domain) params.primary_domain = filters.primary_domain;
      if (filters.min_score > 0) params.min_score = filters.min_score;
      const res = await api.get("/collaboration-intelligence/recommendations", { params });
      setRecommendations(res.data.recommendations);
    } catch (err) {
      // ignore — show stale results
    }
  }, [filters, runMeta]);

  useEffect(() => { if (runMeta) fetchFiltered(); }, [filters, fetchFiltered, runMeta]);


  const handleLoadRun = async (runId) => {
    if (runId === activeRunId) return;
    try {
      const res = await api.get(`/collaboration-intelligence/${runId}`);
      setRecommendations(res.data.recommendations || []);
      setRunMeta({
        id: res.data.id,
        created_at: res.data.created_at,
        recommendation_count: res.data.recommendation_count,
        credits_used: res.data.credits_used,
      });
      setActiveRunId(runId);
    } catch {
      // ignore
    }
  };

  if (gated) return <AIWorkspaceLayout title="Collaboration Intelligence"><GateView /></AIWorkspaceLayout>;

  // Client-side research_area filter (backend doesn't filter by array on GET)
  const visibleRecs = (recommendations || []).filter((r) => {
    if ((filters.research_areas || []).length === 0) return true;
    const rAreas = (r.researcher?.research_areas || []).map((a) => a.toLowerCase());
    return (filters.research_areas || []).some((fa) => rAreas.includes(fa.toLowerCase()));
  });

  const hasResults = visibleRecs.length > 0;

  return (
    <AIWorkspaceLayout
      title="Collaboration Intelligence"
      subtitle="AI-powered researcher matchmaking — find collaborators aligned with your research profile."
    >
    <div data-testid={TID.collaborationIntelDashboard} className="flex-1 flex min-h-0" style={{ margin: "-24px" }}>
      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-y-auto">
        {/* Page header */}
        <div className="border-b border-slate-200 px-6 pt-4 pb-6" style={{ background: "#F4F6FA" }}>
          <div style={{ height: 14 }} />
          {gapContext && (
            <div className="flex items-start gap-2.5 border border-blue-200 bg-blue-50 px-4 py-3 mb-5">
              <Sparkles size={13} strokeWidth={1.5} className="text-blue-600 mt-0.5 shrink-0" />
              <div className="text-xs text-blue-800 leading-relaxed">
                <span className="font-medium">From Research Gap Finder:</span>{" "}
                Finding collaborators for <span className="font-medium">{gapContext.topic}</span>
                {gapContext.keywords.length > 0 && (
                  <span> · Keywords: {gapContext.keywords.slice(0, 4).join(", ")}</span>
                )}
              </div>
            </div>
          )}
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="font-serif text-2xl text-slate-900 tracking-tight">Collaboration Intelligence</div>
              <div className="overline text-slate-400 mt-1">AI-Powered Researcher Matchmaking</div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowFilters((f) => !f)}
                className={`flex items-center gap-2 border px-3 py-2 text-sm transition-colors ${showFilters ? "border-[#0F2847] text-[#0F2847] bg-slate-50" : "border-slate-200 text-slate-600 hover:border-[#0F2847]"}`}
              >
                <Filter size={13} strokeWidth={1.5} />
                Filters
                {((filters.research_areas || []).length > 0 || filters.country || filters.user_type || filters.primary_domain || filters.min_score > 0) && (
                  <span className="w-4 h-4 bg-[#0F2847] text-white text-[9px] flex items-center justify-center font-mono">
                    {(filters.research_areas || []).length + (filters.country ? 1 : 0) + (filters.user_type ? 1 : 0) + (filters.primary_domain ? 1 : 0) + (filters.min_score > 0 ? 1 : 0)}
                  </span>
                )}
              </button>
              <button
                data-testid={TID.collaborationIntelGenerateBtn}
                onClick={handleGenerate}
                disabled={loading}
                className="flex items-center gap-2 border border-[#0F2847] bg-[#0F2847] text-white px-4 py-2 text-sm font-medium hover:bg-slate-800 transition-colors disabled:opacity-50"
              >
                {loading ? (
                  <RotateCcw size={13} strokeWidth={1.5} className="animate-spin" />
                ) : (
                  <Sparkles size={13} strokeWidth={1.5} />
                )}
                {loading ? "Generating…" : recommendations ? "Regenerate" : "Generate"}
              </button>
            </div>
          </div>

          {/* Run meta */}
          {runMeta?.created_at && (
            <div className="flex items-center gap-3 mt-3 text-xs text-slate-400">
              <Clock size={11} strokeWidth={1.5} />
              <span>
                Last generated {new Date(runMeta.created_at).toLocaleDateString("en-GB", {
                  day: "numeric", month: "short", year: "numeric",
                })} · {runMeta.recommendation_count} researchers · {runMeta.credits_used} credits used
              </span>
            </div>
          )}

          {/* Active filter pills */}
          {((filters.research_areas || []).length > 0 || filters.country || filters.user_type || filters.primary_domain) && (
            <div className="flex flex-wrap gap-2 mt-3">
              {(filters.research_areas || []).map((a) => (
                <FilterPill key={a} label="area" value={a}
                  onRemove={() => setFilters((f) => ({ ...f, research_areas: f.research_areas.filter((x) => x !== a) }))} />
              ))}
              {filters.country && (
                <FilterPill label="country" value={filters.country}
                  onRemove={() => setFilters((f) => ({ ...f, country: undefined }))} />
              )}
              {filters.user_type && (
                <FilterPill label="category" value={USER_TYPE_FILTER_OPTIONS.find((t) => t.value === filters.user_type)?.label || filters.user_type}
                  onRemove={() => setFilters((f) => ({ ...f, user_type: undefined }))} />
              )}
              {filters.primary_domain && (
                <FilterPill label="focus" value={PRIMARY_DOMAIN_OPTIONS.find((d) => d.value === filters.primary_domain)?.label || filters.primary_domain}
                  onRemove={() => setFilters((f) => ({ ...f, primary_domain: undefined }))} />
              )}
            </div>
          )}
        </div>

        <div className="flex-1 flex gap-0">
          {/* Filter sidebar */}
          {showFilters && (
            <div className="w-72 shrink-0 border-r border-slate-200 p-5">
              <FilterPanel filters={filters} onChange={setFilters} />
            </div>
          )}

          {/* Content area */}
          <div className="flex-1 p-6">
            {error && (
              <div className="flex items-start gap-2.5 border border-rose-200 bg-rose-50 px-4 py-3 mb-6">
                <AlertCircle size={14} strokeWidth={1.5} className="text-rose-600 mt-0.5 shrink-0" />
                <p className="text-sm text-rose-700">{error}</p>
              </div>
            )}

            {loadingHistory ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3">
                {[1, 2, 3].map((i) => <CardSkeleton key={i} />)}
              </div>
            ) : loading ? (
              <div>
                <div className="flex items-center gap-2 mb-4 text-sm text-slate-500">
                  <RotateCcw size={13} strokeWidth={1.5} className="animate-spin" />
                  Analysing your research profile and finding compatible researchers…
                </div>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3">
                  {[1, 2, 3, 4, 5, 6].map((i) => <CardSkeleton key={i} />)}
                </div>
              </div>
            ) : !recommendations ? (
              <EmptyState onGenerate={handleGenerate} loading={loading} />
            ) : !hasResults ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <Users size={32} strokeWidth={1} className="text-slate-300 mb-4" />
                <div className="font-serif text-lg text-slate-700 mb-2">No matches found</div>
                <p className="text-sm text-slate-500 max-w-sm">
                  No researchers matched the current filters. Try broadening your search or regenerating recommendations.
                </p>
                <button
                  onClick={() => setFilters({ research_areas: [], min_score: 0 })}
                  className="mt-4 text-sm text-[#0F2847] hover:underline"
                >
                  Clear all filters
                </button>
              </div>
            ) : (
              <div data-testid={TID.collaborationIntelResults} className="space-y-6">
                {/* Section header */}
                <div className="flex items-center justify-between">
                  <SectionHeader icon={Target} label={`${visibleRecs.length} Recommended Researcher${visibleRecs.length !== 1 ? "s" : ""}`} />
                  <div className="text-xs text-slate-400 font-mono">
                    Sorted by compatibility ↓
                  </div>
                </div>

                {/* Cards grid */}
                <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3">
                  {visibleRecs.map((rec, i) => (
                    <ResearcherCard
                      key={rec.candidate_id || i}
                      rec={rec}
                    />
                  ))}
                </div>

                {/* Tip */}
                <div className="flex items-start gap-2.5 border border-slate-200 bg-slate-50 px-4 py-3">
                  <Sparkles size={13} strokeWidth={1.5} className="text-[#0F2847] mt-0.5 shrink-0" />
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Scores are based on your current research profile. Keep your research areas,
                    keywords, and collaboration goals up to date in{" "}
                    <Link to="/academic-passport" className="underline hover:text-[#0F2847]">Academic Passport</Link>{" "}
                    for more accurate matches. Regenerate to refresh with the latest platform data.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* History sidebar (xl+) */}
      <aside className="hidden xl:flex flex-col w-64 border-l border-slate-200 bg-white shrink-0">
        <div className="px-4 py-4 border-b border-slate-200">
          <div className="overline text-slate-500">Run History</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {history.length === 0 ? (
            <div className="px-4 py-6 text-xs text-slate-400">
              No past runs yet. Generate your first recommendations above.
            </div>
          ) : (
            history.map((run) => (
              <HistoryItem
                key={run.id}
                run={run}
                active={run.id === activeRunId}
                onClick={() => handleLoadRun(run.id)}
              />
            ))
          )}
        </div>
      </aside>
    </div>    </AIWorkspaceLayout>

  );
}

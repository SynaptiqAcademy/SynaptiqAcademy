import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { Avatar } from "../components/ds/Avatar";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import AIMatchModal from "../components/ai/AIMatchModal";
import AssistantLauncher from "../components/ai/AssistantLauncher";
import FilePanel from "../components/files/FilePanel";
import { NAVY } from "@/lib/tokens";
import {
  MessageSquare, History, GitBranch, RotateCcw, ChevronUp, ChevronDown,
  CheckCircle2, Circle, Star, Save, Send, ListChecks, FileCheck2,
  ClipboardCheck, UserPlus, Search, Sparkles,
} from "lucide-react";

const STATUSES = [
  { value: "draft",                label: "Drafting"             },
  { value: "internal_review",      label: "Internal review"      },
  { value: "ready_for_submission", label: "Ready for submission" },
  { value: "submitted",            label: "Submitted"            },
  { value: "under_review",         label: "Under review"         },
  { value: "major_revision",       label: "Major revision"       },
  { value: "minor_revision",       label: "Minor revision"       },
  { value: "revision_requested",   label: "Revision requested"   },
  { value: "accepted",             label: "Accepted"             },
  { value: "published",            label: "Published"            },
  { value: "rejected",             label: "Rejected"             },
  { value: "withdrawn",            label: "Withdrawn"            },
];

const SECTIONS = [
  { key: "title",           label: "Title"           },
  { key: "abstract",        label: "Abstract"        },
  { key: "introduction",    label: "Introduction"    },
  { key: "literature_review", label: "Literature Review" },
  { key: "methodology",     label: "Methodology"     },
  { key: "results",         label: "Results"         },
  { key: "discussion",      label: "Discussion"      },
  { key: "conclusion",      label: "Conclusion"      },
  { key: "references",      label: "References"      },
];

// ─── Readiness card ───────────────────────────────────────────────────────────

function ReadinessCard({ dash, m }) {
  if (!dash) return null;
  const items = [
    { ok: (m.sections?.title || "").trim().length > 0,    label: "Title set"                         },
    { ok: (m.sections?.abstract || "").trim().length > 0, label: "Abstract written"                  },
    { ok: (m.authors || []).length >= 1,                  label: "At least one author"               },
    { ok: !!m.target_journal_id,                          label: "Target journal selected"           },
    { ok: dash.progress_pct >= 80,                        label: `Sections ≥ 80% (${dash.progress_pct}%)` },
    { ok: !!m.corresponding_author_id,                    label: "Corresponding author named"       },
  ];
  const done = items.filter((i) => i.ok).length;
  return (
    <div data-testid={TID.manuscriptReadiness} className="border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2 mb-3">
        <FileCheck2 size={13} strokeWidth={1.5} className="text-[#0F2847]" />
        <div className="overline">Submission readiness</div>
      </div>
      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-2xl font-bold text-slate-900">{done}/{items.length}</span>
        <span className={`text-[11px] font-mono ${dash.ready_for_submission ? "text-emerald-700" : "text-amber-700"}`}>
          {dash.ready_for_submission ? "Ready" : "In progress"}
        </span>
      </div>
      <ul className="space-y-1.5">
        {items.map((it, i) => (
          <li key={i} className="flex items-center gap-2 text-[11px]">
            {it.ok
              ? <CheckCircle2 size={11} strokeWidth={1.5} className="text-emerald-600 shrink-0" />
              : <Circle size={11} strokeWidth={1.5} className="text-slate-300 shrink-0" />
            }
            <span className={it.ok ? "text-slate-800" : "text-slate-400"}>{it.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ─── Version timeline ─────────────────────────────────────────────────────────

function VersionTimeline({ mid, currentVersion, onRestored }) {
  const [versions, setVersions] = useState([]);
  const load = async () => {
    try { const { data } = await api.get(`/manuscripts/${mid}/versions`); setVersions(data || []); }
    catch { setVersions([]); }
  };
  useEffect(() => { load(); }, [mid, currentVersion]);

  const restore = async (v) => {
    if (!confirm(`Restore version v${v}? Current draft will be snapshotted first.`)) return;
    try {
      await api.post(`/manuscripts/${mid}/versions/${v}/restore`);
      toast.success(`Restored to v${v}`);
      onRestored?.(); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  if (versions.length === 0) return (
    <p className="text-[11px] text-slate-500 leading-relaxed">
      No snapshots yet. Use "Snapshot" above to checkpoint this draft.
    </p>
  );
  return (
    <ol className="space-y-3">
      {versions.map((v) => (
        <li key={v.id} data-testid={TID.manuscriptVersionItem(v.version)} className="border-l-2 border-[#0F2847] pl-3">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[11px] text-[#0F2847]">v{v.version}</span>
                {v.version === currentVersion && (
                  <span className="text-[10px] border border-emerald-200 bg-emerald-50 text-emerald-700 px-1.5 py-0.5">current</span>
                )}
              </div>
              <div className="text-[13px] text-slate-900 mt-0.5 truncate">{v.summary || "—"}</div>
              <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                {v.author_name} · {new Date(v.created_at).toLocaleString()}
              </div>
            </div>
            {v.version !== currentVersion && (
              <button
                data-testid={TID.manuscriptVersionRestore(v.version)}
                onClick={() => restore(v.version)}
                className="shrink-0 inline-flex items-center gap-1 text-[11px] border border-slate-200 px-2 py-1 hover:border-slate-400 transition-colors"
              >
                <RotateCcw size={10} strokeWidth={1.5} /> Restore
              </button>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

// ─── Comments panel ───────────────────────────────────────────────────────────

function CommentsPanel({ mid, section }) {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const load = async () => {
    try { const { data } = await api.get(`/manuscripts/${mid}/comments?section=${section}`); setItems(data || []); }
    catch { setItems([]); }
  };
  useEffect(() => { load(); }, [mid, section]);
  const submit = async () => {
    if (!body.trim()) return;
    setBusy(true);
    try {
      await api.post(`/manuscripts/${mid}/comments`, { section, body });
      setBody(""); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };
  const resolve = async (cid) => {
    try { await api.post(`/manuscripts/comments/${cid}/resolve`); load(); }
    catch { toast.error("Failed"); }
  };
  const open = items.filter((c) => !c.resolved);
  const done = items.filter((c) => c.resolved);
  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          data-testid={TID.manuscriptCommentBody}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder={`Comment on ${section}…`}
          className="flex-1 h-8 px-2.5 border border-slate-200 text-[12px] focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors"
        />
        <button
          data-testid={TID.manuscriptCommentSubmit}
          onClick={submit}
          disabled={busy}
          className="bg-[#0F2847] text-white h-8 px-3 text-[11px] hover:bg-[#1a3d65] inline-flex items-center gap-1 transition-colors"
        >
          <Send size={10} strokeWidth={1.5} /> Post
        </button>
      </div>
      {open.length === 0 && done.length === 0 && (
        <p className="text-[11px] text-slate-400">No comments on this section.</p>
      )}
      {open.map((c) => (
        <div key={c.id} data-testid={TID.manuscriptCommentItem(c.id)} className="border-l-2 border-amber-400 pl-3">
          <div className="flex items-center justify-between gap-2">
            <div className="text-[10px] font-mono text-slate-400">
              {c.author_name} · {new Date(c.created_at).toLocaleString()}
            </div>
            <button
              data-testid={TID.manuscriptCommentResolve(c.id)}
              onClick={() => resolve(c.id)}
              className="text-[10px] text-emerald-700 hover:underline"
            >
              Resolve
            </button>
          </div>
          {c.anchor && <div className="text-[10px] text-slate-400 italic mt-0.5">"{c.anchor}"</div>}
          <div className="text-[12px] text-slate-900 mt-1 leading-relaxed">{c.body}</div>
        </div>
      ))}
      {done.length > 0 && (
        <details className="text-[11px]">
          <summary className="text-slate-400 cursor-pointer">Resolved ({done.length})</summary>
          <div className="space-y-2 mt-2">
            {done.map((c) => (
              <div key={c.id} className="border-l-2 border-emerald-200 pl-3 opacity-50">
                <div className="text-[10px] font-mono text-slate-400">{c.author_name}</div>
                <div className="text-[12px] text-slate-600 line-through">{c.body}</div>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

// ─── Authors panel ────────────────────────────────────────────────────────────

function AuthorsPanel({ m, refresh, currentUserId }) {
  const isLead = m.lead_author_id === currentUserId;
  const authors = m.authors_info || [];
  const order = m.authors || [];

  const move = async (uid, dir) => {
    if (!isLead) return;
    const idx = order.indexOf(uid);
    const j = idx + dir;
    if (idx < 0 || j < 0 || j >= order.length) return;
    const next = [...order]; const tmp = next[idx]; next[idx] = next[j]; next[j] = tmp;
    try { await api.patch(`/manuscripts/${m.id}/authors`, { order: next, corresponding_author_id: m.corresponding_author_id }); refresh(); }
    catch { toast.error("Failed"); }
  };

  const setCorresponding = async (uid) => {
    if (!isLead) return;
    try {
      await api.patch(`/manuscripts/${m.id}/authors`, { order, corresponding_author_id: uid });
      toast.success("Corresponding author set"); refresh();
    } catch { toast.error("Failed"); }
  };

  return (
    <div className="space-y-1.5">
      {authors
        .slice()
        .sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id))
        .map((a, i) => {
          const isCorr = m.corresponding_author_id === a.id;
          return (
            <div key={a.id} className="flex items-center gap-2 border border-slate-200 bg-white px-2 py-1.5">
              <span className="font-mono text-[10px] text-slate-400 w-4">{i + 1}.</span>
              <Avatar url={a.avatar_url} name={a.full_name} size={26} />
              <div className="min-w-0 flex-1">
                <div className="text-[12px] text-slate-900 truncate">{a.full_name}</div>
                <div className="text-[10px] text-slate-400 truncate">{a.institution}</div>
              </div>
              {isCorr && <Star size={11} strokeWidth={1.5} className="text-amber-500 shrink-0" title="Corresponding author" />}
              {isLead && (
                <div className="flex flex-col">
                  <button
                    data-testid={TID.manuscriptAuthorUp(a.id)}
                    disabled={i === 0}
                    onClick={() => move(a.id, -1)}
                    className="text-slate-300 hover:text-slate-700 disabled:opacity-20 transition-colors"
                  >
                    <ChevronUp size={11} strokeWidth={1.5} />
                  </button>
                  <button
                    data-testid={TID.manuscriptAuthorDown(a.id)}
                    disabled={i === authors.length - 1}
                    onClick={() => move(a.id, +1)}
                    className="text-slate-300 hover:text-slate-700 disabled:opacity-20 transition-colors"
                  >
                    <ChevronDown size={11} strokeWidth={1.5} />
                  </button>
                </div>
              )}
              {isLead && !isCorr && (
                <button
                  data-testid={TID.manuscriptCorrespondingPick(a.id)}
                  onClick={() => setCorresponding(a.id)}
                  className="text-[10px] text-[#0F2847] hover:underline font-mono"
                >
                  Set ✦
                </button>
              )}
            </div>
          );
        })}
    </div>
  );
}

// ─── Reviews panel ────────────────────────────────────────────────────────────

function ReviewsPanel({ m, currentUserId, authors, refresh }) {
  const [items, setItems] = useState([]);
  const [showAssign, setShowAssign] = useState(false);
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [note, setNote] = useState("");
  const [section, setSection] = useState("");
  const [busy, setBusy] = useState(null);
  const isLead = m.lead_author_id === currentUserId;
  const isAuthor = (m.authors || []).includes(currentUserId);

  const load = async () => {
    try { const { data } = await api.get(`/manuscripts/${m.id}/review-requests`); setItems(data || []); }
    catch { setItems([]); }
  };
  useEffect(() => { load(); }, [m.id]);

  useEffect(() => {
    const t = setTimeout(async () => {
      if (!q.trim()) { setResults([]); return; }
      try {
        const { data } = await api.get(`/users?q=${encodeURIComponent(q)}&limit=6`);
        const authorIds = new Set((m.authors || []));
        setResults((data || []).filter((u) => !authorIds.has(u.id) && u.id !== currentUserId));
      } catch { setResults([]); }
    }, 220);
    return () => clearTimeout(t);
  }, [q]);

  const assign = async (uid) => {
    setBusy(uid);
    try {
      await api.post(`/manuscripts/${m.id}/review-requests`, { reviewer_id: uid, section, note });
      toast.success("Review requested");
      setQ(""); setResults([]); setNote(""); setSection(""); setShowAssign(false);
      load(); refresh?.();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(null); }
  };

  const STATUS_TONE = {
    pending:   "border-amber-200 bg-amber-50 text-amber-700",
    accepted:  "border-emerald-200 bg-emerald-50 text-emerald-700",
    declined:  "border-slate-200 bg-slate-50 text-slate-500",
    completed: "border-[#0F2847]/30 bg-[#0F2847]/5 text-[#0F2847]",
  };

  return (
    <div className="space-y-3">
      {isAuthor && (
        <button
          data-testid={TID.manuscriptReviewAssignBtn}
          onClick={() => setShowAssign((s) => !s)}
          className="w-full inline-flex items-center justify-center gap-2 bg-[#0F2847] text-white h-8 text-[11px] hover:bg-[#1a3d65] transition-colors"
        >
          <UserPlus size={11} strokeWidth={1.5} /> {showAssign ? "Close" : "Assign reviewer"}
        </button>
      )}

      {showAssign && (
        <div className="border border-slate-200 bg-slate-50/60 p-3 space-y-2">
          <input
            value={section}
            onChange={(e) => setSection(e.target.value)}
            placeholder="Section (optional)"
            className="w-full h-8 px-2.5 border border-slate-200 text-[12px] focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors"
          />
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder="Note for reviewer (optional)"
            className="w-full px-2.5 py-2 border border-slate-200 text-[12px] focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] resize-none transition-colors"
          />
          <div className="relative">
            <Search size={11} strokeWidth={1.5} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search reviewer…"
              className="w-full h-8 pl-8 pr-2.5 border border-slate-200 text-[12px] focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors"
            />
          </div>
          {q.trim() && results.length === 0 && <div className="text-[11px] text-slate-400">No matches.</div>}
          <div className="max-h-44 overflow-auto">
            {results.map((u) => (
              <button
                key={u.id}
                data-testid={TID.manuscriptReviewPick(u.id)}
                disabled={busy === u.id}
                onClick={() => assign(u.id)}
                className="w-full flex items-center gap-2 px-2 py-1.5 hover:bg-white text-left border-b border-slate-100 transition-colors"
              >
                <Avatar url={u.avatar_url} name={u.full_name} size={22} />
                <div className="min-w-0 flex-1">
                  <div className="text-[12px] text-slate-900 truncate">{u.full_name}</div>
                  <div className="text-[10px] text-slate-500 truncate">{u.institution}</div>
                </div>
                <span className="text-[10px] text-[#0F2847] font-mono" data-testid={TID.manuscriptReviewAssignSubmit}>
                  {busy === u.id ? "…" : "Assign"}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {items.length === 0 && <p className="text-[11px] text-slate-400">No reviews assigned yet.</p>}

      {items.map((rr) => {
        const tone = STATUS_TONE[rr.status] || "border-slate-200 bg-slate-50 text-slate-500";
        const label = rr.verdict ? rr.verdict.replace("_", " ") : rr.status;
        return (
          <div key={rr.id} data-testid={TID.manuscriptReviewItem(rr.id)} className="border border-slate-200 bg-white p-2.5">
            <div className="flex items-center gap-2">
              {rr.reviewer && <Avatar url={rr.reviewer.avatar_url} name={rr.reviewer.full_name} size={22} />}
              <div className="min-w-0 flex-1">
                <div className="text-[12px] text-slate-900 truncate">{rr.reviewer?.full_name || "Reviewer"}</div>
                {rr.section && <div className="text-[10px] font-mono text-slate-400">{rr.section}</div>}
              </div>
              <span className={`text-[10px] font-mono border px-1.5 py-0.5 ${tone}`}>{label}</span>
            </div>
            {rr.verdict_comment && (
              <div className="mt-2 text-[11px] text-slate-700 border-l-2 border-[#0F2847] pl-2">
                {rr.verdict_comment}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

function ManuscriptSkeleton() {
  return (
    <div className="space-y-6">
      <div className="border-b border-slate-200 pb-6">
        <div className="h-3 bg-slate-200 w-16 mb-4 animate-pulse" />
        <div className="h-6 bg-slate-200 w-80 animate-pulse" />
      </div>
      <div className="grid lg:grid-cols-12 gap-6">
        <div className="lg:col-span-3 space-y-3">
          {[1, 2, 3].map((i) => <div key={i} className="h-16 bg-slate-200 animate-pulse" />)}
        </div>
        <div className="lg:col-span-6">
          <div className="h-[600px] bg-slate-200 animate-pulse" />
        </div>
        <div className="lg:col-span-3 space-y-3">
          {[1, 2].map((i) => <div key={i} className="h-24 bg-slate-200 animate-pulse" />)}
        </div>
      </div>
    </div>
  );
}

export default function ManuscriptDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [m, setM] = useState(null);
  const [dash, setDash] = useState(null);
  const [sectionKey, setSectionKey] = useState("abstract");
  const [draft, setDraft] = useState("");
  const [savedFlag, setSavedFlag] = useState("");
  const [journals, setJournals] = useState([]);
  const [rightTab, setRightTab] = useState("comments");
  const [aiMatch, setAIMatch] = useState(null);
  const [journalMatches, setJournalMatches] = useState(null);
  const lastSavedLen = useRef(0);

  const load = async () => {
    const [a, b] = await Promise.all([
      api.get(`/manuscripts/${id}`),
      api.get(`/manuscripts/${id}/dashboard`).catch(() => ({ data: null })),
    ]);
    setM(a.data); setDash(b.data);
    const sec = (a.data.sections || {})[sectionKey] || "";
    setDraft(sec); lastSavedLen.current = sec.length;
  };
  useEffect(() => {
    load();
    api.get("/journals?limit=80&page_size=80").then((r) => setJournals(r.data.items || r.data || [])).catch(() => {});
  }, [id]);
  useEffect(() => {
    if (m) {
      const v = (m.sections || {})[sectionKey] || "";
      setDraft(v); lastSavedLen.current = v.length;
    }
  }, [sectionKey, m?.id]);

  const saveSection = async () => {
    const sections = { ...(m.sections || {}), [sectionKey]: draft };
    const delta = draft.length - lastSavedLen.current;
    try {
      const { data } = await api.patch(`/manuscripts/${id}`, { sections });
      setM(data);
      lastSavedLen.current = draft.length;
      setSavedFlag(`Saved · ${new Date().toLocaleTimeString()}`);
      setTimeout(() => setSavedFlag(""), 2400);
      api.post(`/manuscripts/${id}/contributions`, { section: sectionKey, char_delta: delta }).catch(() => {});
      api.get(`/manuscripts/${id}/dashboard`).then((r) => setDash(r.data)).catch(() => {});
    } catch { toast.error("Failed to save"); }
  };

  const snapshot = async () => {
    const summary = prompt("Optional summary for this version:") || "";
    try {
      await api.post(`/manuscripts/${id}/versions`, { summary });
      toast.success("Version snapshot created");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const changeStatus = async (status) => {
    try {
      await api.patch(`/manuscripts/${id}`, { status });
      toast.success(`Status: ${STATUSES.find((s) => s.value === status)?.label || status}`);
      load();
    } catch { toast.error("Failed"); }
  };

  const setTargetJournal = async (journal_id) => {
    try {
      await api.patch(`/manuscripts/${id}`, { target_journal_id: journal_id });
      toast.success("Target journal updated");
      load();
    } catch { toast.error("Failed"); }
  };

  const loadJournalMatches = async () => {
    if (journalMatches) return;
    try {
      const { data } = await api.get(`/manuscripts/${id}/journal-matches`);
      setJournalMatches(data || []);
    } catch { setJournalMatches([]); }
  };

  const handleRightTab = (k) => {
    setRightTab(k);
    if (k === "journals") loadJournalMatches();
  };

  if (!m) return <ManuscriptSkeleton />;

  const filledSections = SECTIONS.filter((s) => (m.sections || {})[s.key]?.trim()).length;
  const wordCount = Math.max(1, draft.split(/\s+/).filter(Boolean).length);

  return (
    <div className="space-y-5">
      {/* ── Header ───────────────────────────────────────────── */}
      <header className="border-b border-slate-200 pb-5">
        <Link to="/manuscripts" className="text-[11px] font-mono text-slate-400 hover:text-slate-700 transition-colors">
          ← Manuscripts
        </Link>
        <div className="mt-3">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="min-w-0 flex-1">
              <div className="text-[11px] font-mono text-slate-400 mb-1.5">{m.manuscript_type}</div>
              <h1 className="text-[1.3rem] font-semibold text-slate-900 tracking-tight leading-snug">
                {m.title}
              </h1>
              <div className="flex items-center gap-3 mt-2 flex-wrap text-[12px] text-slate-500">
                {m.project && (
                  <Link to={`/projects/${m.project.id}`} className="text-[#0F2847] hover:underline">
                    {m.project.title}
                  </Link>
                )}
                {m.workspace && (
                  <Link to={`/workspaces/${m.workspace.id}`} className="text-[#0F2847] hover:underline">
                    {m.workspace.name}
                  </Link>
                )}
                {m.target_journal && (
                  <span>
                    Target: <strong className="text-slate-700">{m.target_journal.title}</strong>
                    {m.target_journal.quartile ? ` (${m.target_journal.quartile})` : ""}
                  </span>
                )}
                {dash && (
                  <span className={`inline-flex items-center gap-1 text-[10px] border px-2 py-0.5 font-mono ${
                    dash.ready_for_submission
                      ? "text-emerald-700 border-emerald-200 bg-emerald-50"
                      : "text-amber-700 border-amber-200 bg-amber-50"
                  }`}>
                    <ListChecks size={10} strokeWidth={1.5} /> {dash.progress_pct}% drafted
                  </span>
                )}
              </div>
            </div>
            {/* Action strip */}
            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <button
                data-testid={TID.manuscriptSnapshotBtn}
                onClick={snapshot}
                className="inline-flex items-center gap-1.5 text-[11px] border border-slate-200 px-3 h-8 hover:border-slate-400 text-slate-600 transition-colors"
              >
                <GitBranch size={11} strokeWidth={1.5} /> Snapshot
              </button>
              <div className="flex items-center border border-[#0F2847]/20 divide-x divide-[#0F2847]/20">
                <span className="flex items-center gap-1 pl-2 pr-1">
                  <Sparkles size={10} strokeWidth={1.5} className="text-[#0F2847]" />
                  <span className="text-[10px] text-slate-400 font-mono">AI match</span>
                </span>
                <button data-testid="ai-match-journal"     onClick={() => setAIMatch("journal")}     className="text-[10px] text-[#0F2847] px-2 h-8 hover:bg-[#0F2847]/5 transition-colors">Journal</button>
                <button data-testid="ai-match-conference" onClick={() => setAIMatch("conference")}  className="text-[10px] text-[#0F2847] px-2 h-8 hover:bg-[#0F2847]/5 transition-colors">Conf</button>
                <button data-testid="ai-match-grant"       onClick={() => setAIMatch("grant")}       className="text-[10px] text-[#0F2847] px-2 h-8 hover:bg-[#0F2847]/5 transition-colors">Grant</button>
                <button data-testid="ai-match-reviewer"    onClick={() => setAIMatch("reviewer")}    className="text-[10px] text-[#0F2847] px-2 h-8 hover:bg-[#0F2847]/5 transition-colors">Reviewer</button>
              </div>
              <button
                data-testid={TID.openChatBtn}
                onClick={() => navigate("/messages", { state: { openContext: { type: "manuscript", id } } })}
                className="inline-flex items-center gap-1.5 text-[11px] border border-slate-200 px-3 h-8 hover:border-slate-400 text-slate-600 transition-colors"
              >
                <MessageSquare size={11} strokeWidth={1.5} /> Chat
              </button>
              <AssistantLauncher entityKind="manuscript" entityId={id} entityTitle={m.title} />
            </div>
          </div>
        </div>
      </header>

      {/* ── Three-column workspace ───────────────────────────── */}
      <div className="grid lg:grid-cols-12 gap-4">

        {/* LEFT — navigation + meta */}
        <aside className="lg:col-span-3 space-y-4">
          {/* Section nav */}
          <div className="border border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-3 py-2 flex items-center justify-between">
              <div className="overline text-slate-500">Sections</div>
              <div className="font-mono text-[10px] text-slate-400">{filledSections}/{SECTIONS.length}</div>
            </div>
            <div className="py-0.5">
              {SECTIONS.map((s) => {
                const filled = ((m.sections || {})[s.key] || "").trim().length > 0;
                return (
                  <button
                    key={s.key}
                    onClick={() => setSectionKey(s.key)}
                    data-testid={TID.manuscriptSection(s.key)}
                    className={`w-full text-left px-3 py-1.5 text-[12px] border-l-2 flex items-center gap-2 transition-colors ${
                      sectionKey === s.key
                        ? "border-[#0F2847] bg-[#0F2847]/[0.04] text-slate-900 font-medium"
                        : "border-transparent text-slate-500 hover:bg-slate-50"
                    }`}
                  >
                    {filled
                      ? <CheckCircle2 size={10} strokeWidth={1.5} className="text-emerald-500 shrink-0" />
                      : <Circle size={10} strokeWidth={1.5} className="text-slate-300 shrink-0" />
                    }
                    <span>{s.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Status */}
          <div className="border border-slate-200 bg-white p-3">
            <div className="overline text-slate-500 mb-2">Status</div>
            <select
              data-testid={TID.manuscriptStatus}
              value={m.status}
              onChange={(e) => changeStatus(e.target.value)}
              className="h-8 w-full px-2.5 border border-slate-200 bg-white text-[12px] text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors"
            >
              {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>

          {/* Target journal */}
          <div className="border border-slate-200 bg-white p-3">
            <div className="overline text-slate-500 mb-2">Target journal</div>
            <select
              value={m.target_journal_id || ""}
              onChange={(e) => setTargetJournal(e.target.value)}
              className="h-8 w-full px-2.5 border border-slate-200 bg-white text-[12px] text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#0F2847]/20 focus:border-[#0F2847] transition-colors"
            >
              <option value="">No target yet</option>
              {journals.map((j) => <option key={j.id} value={j.id}>{j.title} ({j.quartile})</option>)}
            </select>
          </div>

          <ReadinessCard dash={dash} m={m} />
        </aside>

        {/* CENTER — writing area */}
        <main className="lg:col-span-6">
          <div className="border border-slate-200 bg-white">
            {/* Editor toolbar */}
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2.5 bg-slate-50/50">
              <div className="text-[12px] font-medium text-slate-700">
                {SECTIONS.find((s) => s.key === sectionKey)?.label}
              </div>
              <div className="flex items-center gap-3">
                {savedFlag && (
                  <span className="text-[10px] text-emerald-600 font-mono">{savedFlag}</span>
                )}
                <button
                  data-testid={TID.manuscriptSaveBtn}
                  onClick={saveSection}
                  className="inline-flex items-center gap-1.5 bg-[#0F2847] text-white h-7 px-3 text-[11px] hover:bg-[#1a3d65] transition-colors"
                >
                  <Save size={10} strokeWidth={1.5} /> Save
                </button>
              </div>
            </div>

            {/* Editor — comfortable reading width, good line-height */}
            <textarea
              data-testid={TID.manuscriptEditor}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={`Write the ${SECTIONS.find((s) => s.key === sectionKey)?.label.toLowerCase()} section…`}
              className="w-full px-8 py-7 text-[15px] text-slate-800 leading-[1.85] focus:outline-none resize-none bg-white"
              style={{ minHeight: 580, fontFamily: "'Georgia', 'Times New Roman', serif" }}
            />

            {/* Footer stats */}
            <div className="border-t border-slate-100 px-4 py-2 flex items-center justify-between text-[10px] font-mono text-slate-400 bg-slate-50/50">
              <span>{draft.length.toLocaleString()} chars · ~{wordCount.toLocaleString()} words</span>
              <span className="text-slate-300">Ctrl+S to save · Snapshot to checkpoint</span>
            </div>
          </div>
        </main>

        {/* RIGHT — collaboration rail */}
        <aside className="lg:col-span-3 space-y-3">
          <div className="border border-slate-200 bg-white">
            <div className="flex border-b border-slate-200 overflow-x-auto">
              {[
                { k: "comments", label: "Comments"             },
                { k: "versions", label: "History",  testid: TID.manuscriptVersionsToggle },
                { k: "reviews",  label: "Reviews",  testid: TID.manuscriptReviewsTab     },
                { k: "authors",  label: "Authors"              },
                { k: "journals", label: "Journals"             },
              ].map((t) => (
                <button
                  key={t.k}
                  data-testid={t.testid}
                  onClick={() => handleRightTab(t.k)}
                  className={`shrink-0 text-[11px] px-3 py-2 border-b-2 -mb-px transition-colors ${
                    rightTab === t.k
                      ? "border-[#0F2847] text-slate-900 font-medium"
                      : "border-transparent text-slate-400 hover:text-slate-700"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="p-3">
              {rightTab === "comments"  && <CommentsPanel mid={id} section={sectionKey} />}
              {rightTab === "versions"  && (
                <VersionTimeline mid={id} currentVersion={m.current_version || 0} onRestored={load} />
              )}
              {rightTab === "reviews"   && (
                <ReviewsPanel m={m} currentUserId={user?.id} authors={m.authors_info || []} refresh={load} />
              )}
              {rightTab === "authors"   && (
                <AuthorsPanel m={m} refresh={load} currentUserId={user?.id} />
              )}
              {rightTab === "journals"  && (
                <div className="space-y-2">
                  {!journalMatches && (
                    <div className="space-y-2">
                      {[1, 2, 3].map((i) => <div key={i} className="h-20 bg-slate-200 animate-pulse" />)}
                    </div>
                  )}
                  {journalMatches?.length === 0 && (
                    <p className="text-[11px] text-slate-400">No journals found. Add keywords to improve matching.</p>
                  )}
                  {(journalMatches || []).map((j) => (
                    <div key={j.id} className="border border-slate-200 bg-white p-2.5 hover:border-[#0F2847]/40 transition-colors">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="text-[12px] text-slate-900 font-medium leading-snug truncate">{j.title}</div>
                          <div className="text-[10px] text-slate-400 font-mono mt-0.5">{j.publisher}</div>
                        </div>
                        <div className="flex flex-col items-end gap-1 shrink-0">
                          {j.quartile && (
                            <span className="text-[10px] border border-slate-200 px-1 font-mono">{j.quartile}</span>
                          )}
                          <span className="text-[10px] font-mono text-emerald-700">{j.match_score}pts</span>
                        </div>
                      </div>
                      {j.match_reason && (
                        <div className="text-[10px] text-slate-400 mt-1 italic truncate">{j.match_reason}</div>
                      )}
                      <div className="mt-1.5 flex items-center gap-2 text-[10px] font-mono text-slate-400">
                        {j.impact_factor && <span>IF {j.impact_factor}</span>}
                        {j.review_time_weeks && <span>~{j.review_time_weeks}w</span>}
                        {j.acceptance_rate && <span>{j.acceptance_rate}% accept</span>}
                      </div>
                      <button
                        onClick={() => setTargetJournal(j.id)}
                        className="mt-2 text-[10px] text-[#0F2847] hover:underline font-mono"
                      >
                        Set as target →
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Contributions */}
          {dash?.contributions?.length > 0 && (
            <div className="border border-slate-200 bg-white p-3">
              <div className="overline text-slate-500 mb-2">Contributions</div>
              <ul className="space-y-1.5">
                {dash.contributions.slice(0, 6).map((c) => (
                  <li key={c.id} className="flex items-center justify-between gap-2 text-[11px]">
                    <span className="text-slate-700 truncate">{c.user_name}</span>
                    <span className="font-mono text-slate-400 shrink-0">{c.section} · {c.edits}×</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>

      <div className="mt-4">
        <FilePanel entityKind="manuscript" entityId={id} />
      </div>

      <AIMatchModal
        open={!!aiMatch}
        onClose={() => setAIMatch(null)}
        kind={aiMatch}
        manuscriptId={id}
      />
    </div>
  );
}

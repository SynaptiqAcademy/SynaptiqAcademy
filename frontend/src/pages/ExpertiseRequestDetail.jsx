/**
 * ExpertiseRequestDetail — view a single expertise request, apply, and
 * (if owner) review applicants + accept/reject.
 */
import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { userTypeLabel } from "../lib/userTypes";
import {
  ArrowLeft, Loader2, Check, X, Trash2, Send, MessageSquare, Briefcase, Building2,
  Calendar, Award, Clock, Paperclip, Eye, Download, Plus,
} from "lucide-react";
import PreviewDrawer from "../components/files/PreviewDrawer";
import { NAVY } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";

const KIND_LABEL = {
  co_author: "Co-author", statistician: "Statistician", methodology: "Methodology expert",
  reviewer: "Reviewer", ai_specialist: "AI specialist", data_scientist: "Data scientist",
  editor: "Editor", sme: "Subject matter expert",
};

export default function ExpertiseRequestDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [r, setR] = useState(null);
  const [msg, setMsg] = useState("");
  const [applying, setApplying] = useState(false);

  const load = async () => {
    try {
      const { data } = await api.get(`/expertise/${id}`);
      setR(data);
    } catch (e) {
      toast.error("Request not found");
      navigate("/expertise");
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const apply = async () => {
    if (msg.trim().length < 10) { toast.error("Message must be ≥ 10 chars"); return; }
    setApplying(true);
    try {
      await api.post(`/expertise/${id}/apply`, { message: msg.trim() });
      toast.success("Application sent");
      setMsg("");
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    } finally { setApplying(false); }
  };

  const decide = async (applicantUid, decision) => {
    try {
      await api.post(`/expertise/${id}/applications/${applicantUid}/decide`, { decision });
      toast.success(`Application ${decision}`);
      load();
    } catch (e) {
      toast.error("Failed");
    }
  };

  const close = async () => {
    if (!confirm("Close this request?")) return;
    try {
      await api.post(`/expertise/${id}/close`);
      toast.success("Closed");
      load();
    } catch (e) { toast.error("Failed"); }
  };

  const del = async () => {
    if (!confirm("Delete this request? This cannot be undone.")) return;
    try {
      await api.delete(`/expertise/${id}`);
      toast.success("Deleted");
      navigate("/expertise");
    } catch (e) { toast.error("Failed"); }
  };

  if (!r) return <div className="py-2 flex justify-center"><Spinner size={14} /></div>;

  return (
    <div className="space-y-6">
      <Link to="/expertise" className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-[#0F2847]">
        <ArrowLeft size={11} strokeWidth={1.5} /> All expertise requests
      </Link>

      <header className="border-b border-slate-200 pb-6">
        <div className="flex items-start justify-between gap-6">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="overline text-[#0F2847]">{KIND_LABEL[r.kind] || r.kind}</span>
              <span className={`overline px-1.5 py-0.5 border ${r.status === "open" ? "border-emerald-300 bg-emerald-50 text-emerald-800" : r.status === "filled" ? "border-[#0F2847]/30 bg-[#0F2847]/5 text-[#0F2847]" : "border-slate-200 bg-slate-50 text-slate-500"}`}>{r.status}</span>
            </div>
            <h1 className="font-serif text-4xl text-slate-900 mt-2 leading-tight">{r.title}</h1>
            {r.owner && (
              <div className="text-xs text-slate-500 mt-2 inline-flex items-center gap-3 flex-wrap">
                <Link to={`/profile/${r.owner.id}`} className="hover:text-[#0F2847] inline-flex items-center gap-1">
                  <Briefcase size={10} strokeWidth={1.5} /> {r.owner.full_name}
                </Link>
                {r.owner.institution && <span className="inline-flex items-center gap-1"><Building2 size={10} strokeWidth={1.5} /> {r.owner.institution}</span>}
                <span className="font-mono">Posted {new Date(r.created_at).toLocaleDateString()}</span>
              </div>
            )}
          </div>
          {r.i_am_owner && (
            <div className="flex flex-col gap-2 shrink-0">
              {r.status === "open" && (
                <button data-testid="close-request-btn" onClick={close} className="text-xs border border-slate-300 px-3 py-1.5 hover:border-[#0F2847]">
                  Close request
                </button>
              )}
              <button data-testid="delete-request-btn" onClick={del} className="text-xs border border-red-200 text-red-700 px-3 py-1.5 hover:bg-red-50 inline-flex items-center justify-center gap-1.5">
                <Trash2 size={11} strokeWidth={1.5} /> Delete
              </button>
            </div>
          )}
        </div>
      </header>

      <div className="grid lg:grid-cols-[1fr_320px] gap-8">
        <main className="space-y-6">
          {/* Description */}
          <section className="border border-slate-200 bg-white p-5">
            <div className="overline mb-2">Description</div>
            <p className="font-serif text-base text-slate-800 leading-relaxed whitespace-pre-wrap">{r.description}</p>
          </section>

          <AttachmentsSection requestId={id} isOwner={r.i_am_owner} />

          {/* Apply form */}
          {!r.i_am_owner && r.status === "open" && (
            <section className="border border-slate-200 bg-white p-5" data-testid="apply-section">
              <div className="overline mb-2">Apply</div>
              {r.i_have_applied ? (
                <div className="text-sm text-emerald-700 inline-flex items-center gap-1.5"><Check size={12} strokeWidth={1.5} /> You've already applied.</div>
              ) : (
                <>
                  <textarea
                    data-testid="apply-message"
                    rows={4}
                    value={msg} onChange={(e) => setMsg(e.target.value)}
                    placeholder="Briefly explain your relevant experience, fit, and timeline."
                    className="w-full px-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
                  />
                  <div className="flex items-center justify-end mt-2">
                    <button data-testid="apply-submit" disabled={applying || !msg.trim()} onClick={apply} className="text-xs bg-[#0F2847] text-white px-4 py-2 hover:bg-slate-800 disabled:opacity-50 inline-flex items-center gap-1.5">
                      {applying ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} strokeWidth={1.5} />}
                      Send application
                    </button>
                  </div>
                </>
              )}
            </section>
          )}

          {/* Applicants (owner view) */}
          {r.i_am_owner && (
            <section className="border border-slate-200 bg-white p-5" data-testid="applicants-section">
              <div className="flex items-center justify-between mb-3">
                <div className="overline">Applicants ({(r.applicants || []).length})</div>
              </div>
              {(r.applicants || []).length === 0 && (
                <div className="text-sm text-slate-500">No applicants yet.</div>
              )}
              <div className="space-y-3">
                {(r.applicants || []).map((a) => (
                  <div key={a.user_id} className="border border-slate-200 p-3" data-testid={`applicant-${a.user_id}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        {a.user ? (
                          <Link to={`/profile/${a.user_id}`} className="font-serif text-base text-slate-900 hover:text-[#0F2847]">
                            {a.user.full_name}
                          </Link>
                        ) : <span className="font-mono text-xs">{a.user_id}</span>}
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          {userTypeLabel(a.user)} · {a.user?.institution}
                        </div>
                        <p className="text-sm text-slate-700 mt-2 font-serif italic">"{a.message}"</p>
                      </div>
                      <div className="flex flex-col gap-1 shrink-0">
                        <span className={`overline px-1.5 py-0.5 border ${a.status === "accepted" ? "border-emerald-300 bg-emerald-50 text-emerald-800" : a.status === "rejected" ? "border-red-200 bg-red-50 text-red-700" : "border-slate-200 bg-slate-50 text-slate-500"}`}>
                          {a.status}
                        </span>
                        {a.status === "pending" && (
                          <>
                            <button data-testid={`accept-${a.user_id}`} onClick={() => decide(a.user_id, "accepted")} className="text-[10px] bg-[#0F2847] text-white px-2 py-1 hover:bg-slate-800 inline-flex items-center gap-1">
                              <Check size={9} strokeWidth={1.5} /> Accept
                            </button>
                            <button data-testid={`reject-${a.user_id}`} onClick={() => decide(a.user_id, "rejected")} className="text-[10px] border border-red-200 text-red-700 px-2 py-1 hover:bg-red-50 inline-flex items-center gap-1">
                              <X size={9} strokeWidth={1.5} /> Reject
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </main>

        {/* Sidebar */}
        <aside className="space-y-4">
          <div className="border border-slate-200 bg-white p-4">
            <div className="overline mb-2">Required skills</div>
            <div className="flex flex-wrap gap-1">
              {(r.required_skills || []).map((s, i) => (
                <span key={i} className="text-[11px] border border-slate-200 bg-slate-50 px-2 py-0.5 font-mono">{s}</span>
              ))}
              {(r.required_skills || []).length === 0 && <span className="text-xs text-slate-400">None specified</span>}
            </div>
          </div>
          <div className="border border-slate-200 bg-white p-4">
            <div className="overline mb-2">Research areas</div>
            <div className="flex flex-wrap gap-1">
              {(r.research_areas || []).map((s, i) => (
                <span key={i} className="text-[11px] border border-[#0F2847]/30 bg-[#0F2847]/5 text-[#0F2847] px-2 py-0.5">{s}</span>
              ))}
              {(r.research_areas || []).length === 0 && <span className="text-xs text-slate-400">None specified</span>}
            </div>
          </div>
          {(r.duration || r.compensation || r.deadline) && (
            <div className="border border-slate-200 bg-white p-4">
              <div className="overline mb-2">Engagement</div>
              <div className="space-y-1.5 text-xs">
                {r.duration && <div className="inline-flex items-center gap-1.5"><Clock size={11} strokeWidth={1.5} /> {r.duration}</div>}
                {r.compensation && <div className="inline-flex items-center gap-1.5"><Award size={11} strokeWidth={1.5} /> {r.compensation.replace("_", " ")}</div>}
                {r.deadline && <div className="inline-flex items-center gap-1.5"><Calendar size={11} strokeWidth={1.5} /> Apply by {r.deadline}</div>}
              </div>
            </div>
          )}
          {r.entity && (
            <div className="border border-slate-200 bg-white p-4">
              <div className="overline mb-2">Linked {r.entity_kind}</div>
              <Link to={`/${r.entity_kind}s/${r.entity.id}`} className="text-sm text-[#0F2847] hover:underline">
                {r.entity.title}
              </Link>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function AttachmentsSection({ requestId, isOwner }) {
  const [items, setItems] = React.useState(null);
  const [myFiles, setMyFiles] = React.useState(null);
  const [picking, setPicking] = React.useState(false);
  const [previewing, setPreviewing] = React.useState(null);

  const load = async () => {
    try { const { data } = await api.get(`/expertise/${requestId}/attachments`); setItems(data || []); }
    catch { setItems([]); }
  };
  React.useEffect(() => { load(); /* eslint-disable-next-line */ }, [requestId]);

  const openPicker = async () => {
    setPicking(true);
    if (myFiles === null) {
      try { const { data } = await api.get("/files?include_versions=false&limit=100"); setMyFiles(data || []); }
      catch { setMyFiles([]); }
    }
  };

  const attach = async (fileId) => {
    try { await api.post(`/expertise/${requestId}/attachments`, { file_id: fileId }); toast.success("File attached"); setPicking(false); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const detach = async (fileId) => {
    if (!confirm("Remove this attachment from the request?")) return;
    try { await api.delete(`/expertise/${requestId}/attachments/${fileId}`); toast.success("Removed"); load(); }
    catch { toast.error("Failed"); }
  };

  if (items === null) return <div className="py-2 flex justify-center"><Spinner size={12} /></div>;

  return (
    <section className="border border-slate-200 bg-white p-5" data-testid="attachments-section">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Paperclip size={12} strokeWidth={1.5} className="text-[#0F2847]" />
          <div className="overline">Attached files — research context</div>
          <span className="text-[10px] font-mono text-slate-400">{items.length}</span>
        </div>
        {isOwner && (
          <button data-testid="attach-file-btn" onClick={openPicker} className="text-xs inline-flex items-center gap-1 border border-slate-300 px-2 py-1 hover:border-[#0F2847]">
            <Plus size={10} strokeWidth={1.5} /> Attach file
          </button>
        )}
      </div>
      {items.length === 0 && (
        <div className="text-xs text-slate-500" data-testid="attachments-empty">
          {isOwner ? "Add a dataset, protocol, draft, or proposal to give applicants real context before they apply." : "The owner hasn't attached supporting files yet."}
        </div>
      )}
      <div className="grid sm:grid-cols-2 gap-2" data-testid="attachments-list">
        {items.map((f) => (
          <div key={f.id} className="border border-slate-200 p-3 flex items-center gap-3" data-testid={`attachment-${f.id}`}>
            <Paperclip size={11} strokeWidth={1.5} className="text-[#0F2847] shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="font-serif text-sm text-slate-900 truncate">{f.filename}</div>
              <div className="text-[10px] font-mono text-slate-400">{f.ext.toUpperCase()} · {((f.size_bytes||0)/1024).toFixed(1)} KB · v{f.version}</div>
            </div>
            <button onClick={() => setPreviewing(f)} className="text-slate-400 hover:text-[#0F2847]" title="Preview" data-testid={`attach-preview-${f.id}`}><Eye size={12} strokeWidth={1.5} /></button>
            <a href={`${process.env.REACT_APP_BACKEND_URL}/api/files/${f.id}/download`} className="text-slate-400 hover:text-[#0F2847]" title="Download" data-testid={`attach-download-${f.id}`}>
              <Download size={12} strokeWidth={1.5} />
            </a>
            {isOwner && (
              <button onClick={() => detach(f.id)} className="text-slate-400 hover:text-red-600" title="Detach" data-testid={`attach-remove-${f.id}`}><Trash2 size={12} strokeWidth={1.5} /></button>
            )}
          </div>
        ))}
      </div>

      {picking && (
        <div className="fixed inset-0 z-[100] bg-slate-900/50 flex items-center justify-center px-4" onClick={() => setPicking(false)} data-testid="attach-picker-modal">
          <div className="bg-white w-full max-w-lg border border-slate-200 max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="border-b border-slate-200 px-5 py-3 flex items-center justify-between">
              <h4 className="font-serif text-base">Pick a file to attach</h4>
              <button onClick={() => setPicking(false)}><X size={14} strokeWidth={1.5} /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-1">
              {myFiles === null && <div className="flex justify-center"><Spinner size={12} /></div>}
              {myFiles && myFiles.length === 0 && <div className="text-xs text-slate-500">You haven't uploaded any files yet. Upload one inside a workspace/project/manuscript first.</div>}
              {myFiles && myFiles.map((f) => (
                <button key={f.id} onClick={() => attach(f.id)} data-testid={`pick-attach-${f.id}`} className="w-full text-left flex items-center gap-2 px-2 py-2 border border-slate-200 hover:border-[#0F2847]">
                  <Paperclip size={11} strokeWidth={1.5} className="text-[#0F2847]" />
                  <span className="text-sm flex-1 truncate">{f.filename}</span>
                  <span className="overline text-slate-400">{f.entity_kind}</span>
                  <span className="text-[10px] font-mono text-slate-400">{f.ext.toUpperCase()}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
      {previewing && <PreviewDrawer file={previewing} onClose={() => setPreviewing(null)} />}
    </section>
  );
}


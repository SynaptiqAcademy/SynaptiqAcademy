import React, { useState, useEffect, useRef } from "react";
import { Mail, Plus, Edit2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

const TABS = ["Compose", "Templates", "Campaigns"];
const SEGMENTS = [
  { value: "all", label: "All Users" },
  { value: "free", label: "Free Plan" },
  { value: "paid", label: "Paid Users" },
  { value: "unverified", label: "Unverified Emails" },
];

function TabBtn({ label, active, onClick }) {
  return (
    <button onClick={onClick}
      className={`px-5 py-2.5 text-sm font-medium transition-colors ${active ? "border-b-2 border-[#0F2847] text-[#0F2847]" : "text-slate-500 hover:text-slate-800"}`}>
      {label}
    </button>
  );
}

export default function AdminEmailCenter() {
  const [tab, setTab] = useState("Compose");
  const [mode, setMode] = useState("individual");

  // Individual send
  const [userSearch, setUserSearch] = useState("");
  const [userResults, setUserResults] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [subject, setSubject] = useState("");
  const [bodyHtml, setBodyHtml] = useState("");
  const [sending, setSending] = useState(false);

  // Bulk send
  const [bulkSegment, setBulkSegment] = useState("all");
  const [bulkSubject, setBulkSubject] = useState("");
  const [bulkBody, setBulkBody] = useState("");
  const [bulkSending, setBulkSending] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);

  // Templates
  const [templates, setTemplates] = useState([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [showNewTemplate, setShowNewTemplate] = useState(false);
  const [newTplName, setNewTplName] = useState("");
  const [newTplSubject, setNewTplSubject] = useState("");
  const [newTplBody, setNewTplBody] = useState("");
  const [editingTpl, setEditingTpl] = useState(null);
  const [tplSaving, setTplSaving] = useState(false);

  // Campaigns
  const [campaigns, setCampaigns] = useState([]);
  const [campaignsLoading, setCampaignsLoading] = useState(false);

  const searchTimer = useRef(null);

  // User search with debounce
  useEffect(() => {
    if (!userSearch.trim()) { setUserResults([]); return; }
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(async () => {
      try {
        const r = await api.get(`/admin/users?q=${encodeURIComponent(userSearch)}&limit=5`);
        setUserResults(r.data.items || []);
      } catch (_) {}
    }, 300);
  }, [userSearch]);

  useEffect(() => {
    if (tab === "Templates") loadTemplates();
    if (tab === "Campaigns") loadCampaigns();
  }, [tab]);

  const loadTemplates = async () => {
    setTemplatesLoading(true);
    try {
      const r = await api.get("/admin/email/templates");
      setTemplates(r.data || []);
    } catch (_) {
      toast.error("Failed to load templates");
    } finally {
      setTemplatesLoading(false);
    }
  };

  const loadCampaigns = async () => {
    setCampaignsLoading(true);
    try {
      const r = await api.get("/admin/email/campaigns");
      setCampaigns(r.data || []);
    } catch (_) {
      toast.error("Failed to load campaigns");
    } finally {
      setCampaignsLoading(false);
    }
  };

  const sendIndividual = async () => {
    if (!selectedUser) { toast.error("Select a user first"); return; }
    if (!subject.trim()) { toast.error("Subject is required"); return; }
    if (!bodyHtml.trim()) { toast.error("Email body is required"); return; }
    setSending(true);
    try {
      await api.post("/admin/email/send-individual", { user_id: selectedUser.id, subject, body_html: bodyHtml });
      toast.success(`Email sent to ${selectedUser.email}`);
      setSelectedUser(null); setUserSearch(""); setSubject(""); setBodyHtml("");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Send failed");
    } finally {
      setSending(false);
    }
  };

  const sendBulk = async () => {
    if (!bulkSubject.trim()) { toast.error("Subject is required"); return; }
    if (!bulkBody.trim()) { toast.error("Email body is required"); return; }
    setBulkSending(true);
    setBulkResult(null);
    try {
      const r = await api.post("/admin/email/send-bulk", { segment: bulkSegment, subject: bulkSubject, body_html: bulkBody });
      setBulkResult(r.data);
      toast.success(`Campaign sent: ${r.data.sent_count} emails`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Bulk send failed");
    } finally {
      setBulkSending(false);
    }
  };

  const createTemplate = async () => {
    if (!newTplName || !newTplSubject || !newTplBody) { toast.error("All fields are required"); return; }
    setTplSaving(true);
    try {
      await api.post("/admin/email/templates", { name: newTplName, subject: newTplSubject, body_html: newTplBody });
      toast.success("Template created");
      setShowNewTemplate(false); setNewTplName(""); setNewTplSubject(""); setNewTplBody("");
      await loadTemplates();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to create template");
    } finally {
      setTplSaving(false);
    }
  };

  const updateTemplate = async (id) => {
    setTplSaving(true);
    try {
      await api.put(`/admin/email/templates/${id}`, { name: editingTpl.name, subject: editingTpl.subject, body_html: editingTpl.body_html });
      toast.success("Template updated");
      setEditingTpl(null);
      await loadTemplates();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to update template");
    } finally {
      setTplSaving(false);
    }
  };

  const deleteTemplate = async (id) => {
    try {
      await api.delete(`/admin/email/templates/${id}`);
      toast.success("Template deleted");
      await loadTemplates();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to delete template");
    }
  };

  const fmt = (d) => d ? new Date(d).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—";

  return (
    <AdministrationLayout
      title="Email Center"
      subtitle="Send communications and manage email templates"
    >
      <div className="flex border-b border-slate-200 mb-6">
        {TABS.map((t) => <TabBtn key={t} label={t} active={tab === t} onClick={() => setTab(t)} />)}
      </div>

      {/* Compose */}
      {tab === "Compose" && (
        <div>
          <div className="flex gap-2 mb-5">
            {["individual", "bulk"].map((m) => (
              <button key={m} onClick={() => setMode(m)}
                className={`px-4 py-2 text-sm font-medium border ${mode === m ? "bg-[#0F2847] text-white border-[#0F2847]" : "border-slate-300 text-slate-600 hover:bg-slate-50"}`}>
                {m === "individual" ? "Individual" : "Bulk"}
              </button>
            ))}
          </div>

          {mode === "individual" ? (
            <div className="bg-white border border-slate-200 p-5 space-y-4 max-w-2xl">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">Recipient</label>
                {selectedUser ? (
                  <div className="flex items-center justify-between px-3 py-2 border border-slate-300 bg-slate-50">
                    <div>
                      <span className="text-sm font-medium text-slate-900">{selectedUser.full_name || selectedUser.email}</span>
                      <span className="text-xs text-slate-500 ml-2">{selectedUser.email}</span>
                    </div>
                    <button onClick={() => setSelectedUser(null)} className="text-xs text-slate-400 hover:text-slate-700">Remove</button>
                  </div>
                ) : (
                  <div className="relative">
                    <input value={userSearch} onChange={(e) => setUserSearch(e.target.value)}
                      placeholder="Search by name or email…"
                      className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847]" />
                    {userResults.length > 0 && (
                      <div className="absolute z-10 top-full left-0 right-0 bg-white border border-slate-200 shadow-md max-h-48 overflow-y-auto">
                        {userResults.map((u) => (
                          <button key={u.id} onClick={() => { setSelectedUser(u); setUserSearch(""); setUserResults([]); }}
                            className="w-full text-left px-3 py-2.5 text-sm hover:bg-slate-50 border-b border-slate-100 last:border-0">
                            <div className="font-medium text-slate-900">{u.full_name || u.email}</div>
                            <div className="text-xs text-slate-500">{u.email}</div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">Subject</label>
                <input value={subject} onChange={(e) => setSubject(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
                  placeholder="Email subject…" />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">Body (HTML)</label>
                <textarea value={bodyHtml} onChange={(e) => setBodyHtml(e.target.value)} rows={10}
                  className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847] font-mono"
                  placeholder="<p>Hello {name},</p><p>Your message here...</p>" />
              </div>
              <button onClick={sendIndividual} disabled={sending}
                className="px-6 py-2.5 bg-[#0F2847] text-white text-sm font-medium hover:bg-slate-800 disabled:opacity-50">
                {sending ? "Sending…" : "Send Email"}
              </button>
            </div>
          ) : (
            <div className="bg-white border border-slate-200 p-5 space-y-4 max-w-2xl">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">Recipient Segment</label>
                <select value={bulkSegment} onChange={(e) => setBulkSegment(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847]">
                  {SEGMENTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">Subject</label>
                <input value={bulkSubject} onChange={(e) => setBulkSubject(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
                  placeholder="Email subject…" />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">Body (HTML)</label>
                <textarea value={bulkBody} onChange={(e) => setBulkBody(e.target.value)} rows={10}
                  className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847] font-mono"
                  placeholder="<p>Hello,</p><p>Your message here...</p>" />
              </div>
              {bulkResult && (
                <div className="border border-green-200 bg-green-50 p-3 text-sm text-green-800">
                  Campaign complete — {bulkResult.sent_count} sent, {bulkResult.failed_count} failed
                </div>
              )}
              <button onClick={sendBulk} disabled={bulkSending}
                className="px-6 py-2.5 bg-[#0F2847] text-white text-sm font-medium hover:bg-slate-800 disabled:opacity-50">
                {bulkSending ? "Sending…" : `Send to ${SEGMENTS.find((s) => s.value === bulkSegment)?.label}`}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Templates */}
      {tab === "Templates" && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <p className="text-sm text-slate-600">{templates.length} templates</p>
            <button onClick={() => setShowNewTemplate(true)}
              className="flex items-center gap-2 px-4 py-2 bg-[#0F2847] text-white text-sm hover:bg-slate-800">
              <Plus size={14} /> New Template
            </button>
          </div>

          {showNewTemplate && (
            <div className="bg-white border border-slate-200 p-5 mb-4 space-y-3">
              <h3 className="text-sm font-semibold text-slate-800">New Template</h3>
              <input value={newTplName} onChange={(e) => setNewTplName(e.target.value)}
                placeholder="Template name" className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none" />
              <input value={newTplSubject} onChange={(e) => setNewTplSubject(e.target.value)}
                placeholder="Email subject" className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none" />
              <textarea value={newTplBody} onChange={(e) => setNewTplBody(e.target.value)} rows={6}
                placeholder="HTML body…" className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none font-mono" />
              <div className="flex gap-2">
                <button onClick={createTemplate} disabled={tplSaving}
                  className="px-4 py-2 bg-[#0F2847] text-white text-sm disabled:opacity-50">
                  {tplSaving ? "Saving…" : "Save Template"}
                </button>
                <button onClick={() => setShowNewTemplate(false)} className="px-4 py-2 border border-slate-300 text-sm text-slate-600 hover:bg-slate-50">
                  Cancel
                </button>
              </div>
            </div>
          )}

          {templatesLoading ? (
            <div className="space-y-2">{[...Array(3)].map((_, i) => <div key={i} className="h-24 animate-pulse bg-gray-200" />)}</div>
          ) : templates.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Mail size={36} className="mx-auto mb-3 opacity-40" />
              <p className="text-sm">No email templates yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {templates.map((tpl) => (
                <div key={tpl.id} className="bg-white border border-slate-200 p-4">
                  {editingTpl?.id === tpl.id ? (
                    <div className="space-y-3">
                      <input value={editingTpl.name} onChange={(e) => setEditingTpl({ ...editingTpl, name: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none" />
                      <input value={editingTpl.subject} onChange={(e) => setEditingTpl({ ...editingTpl, subject: e.target.value })}
                        className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none" />
                      <textarea value={editingTpl.body_html} onChange={(e) => setEditingTpl({ ...editingTpl, body_html: e.target.value })} rows={5}
                        className="w-full px-3 py-2 text-sm border border-slate-300 focus:outline-none font-mono" />
                      <div className="flex gap-2">
                        <button onClick={() => updateTemplate(tpl.id)} disabled={tplSaving}
                          className="px-3 py-1.5 bg-[#0F2847] text-white text-xs disabled:opacity-50">
                          {tplSaving ? "Saving…" : "Save"}
                        </button>
                        <button onClick={() => setEditingTpl(null)} className="px-3 py-1.5 border border-slate-300 text-xs hover:bg-slate-50">Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-sm font-semibold text-slate-900">{tpl.name}</h3>
                        <p className="text-xs text-slate-500 mt-0.5">{tpl.subject}</p>
                        <p className="text-xs text-slate-400 mt-1 line-clamp-2 font-mono">{tpl.body_html?.slice(0, 120)}…</p>
                      </div>
                      <div className="flex gap-2 ml-4 flex-shrink-0">
                        <button onClick={() => setEditingTpl({ ...tpl })} className="p-1.5 text-slate-400 hover:text-slate-700"><Edit2 size={14} /></button>
                        <button onClick={() => deleteTemplate(tpl.id)} className="p-1.5 text-slate-400 hover:text-red-700"><Trash2 size={14} /></button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Campaigns */}
      {tab === "Campaigns" && (
        <div className="bg-white border border-slate-200 overflow-hidden">
          {campaignsLoading ? (
            <div className="p-4 space-y-2">{[...Array(4)].map((_, i) => <div key={i} className="h-10 animate-pulse bg-gray-200" />)}</div>
          ) : campaigns.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
              <Mail size={36} className="mb-3 opacity-40" />
              <p className="text-sm">No campaigns sent yet</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Date</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Segment</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Subject</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Sent</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Failed</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-widest text-slate-500">Status</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((c, i) => (
                  <tr key={i} className="border-b border-slate-100">
                    <td className="px-4 py-2.5 text-xs text-slate-500">{fmt(c.created_at)}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-700">{c.segment}</td>
                    <td className="px-4 py-2.5 text-sm text-slate-900">{c.subject}</td>
                    <td className="px-4 py-2.5 text-sm font-medium text-green-700">{c.sent_count}</td>
                    <td className="px-4 py-2.5 text-sm text-red-700">{c.failed_count || 0}</td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-block px-2 py-0.5 text-xs font-medium ${c.status === "completed" ? "bg-green-50 text-green-700" : c.status === "failed" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>
                        {c.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </AdministrationLayout>
  );
}

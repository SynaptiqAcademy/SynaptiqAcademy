import React, { useState, useEffect, useRef } from "react";
import { Mail, Plus, Edit2, Trash2, Send } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { confirmDialog } from "@/lib/confirm";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  NavTabs, Card, Input, Textarea, FormSelect, Button, Badge, Alert,
  EmptyState, SkeletonLine, DataTable, List, ListItem,
} from "@/components/ds";

const TABS = ["Compose", "Templates", "System Emails", "Campaigns"];
const SEGMENTS = [
  { value: "all", label: "All Users" },
  { value: "free", label: "Free Plan" },
  { value: "paid", label: "Paid Users" },
  { value: "unverified", label: "Unverified Emails" },
];

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

  // System (transactional) emails — read-only preview
  const [sysTemplates, setSysTemplates] = useState([]);
  const [sysLoading, setSysLoading] = useState(false);
  const [sysActiveKey, setSysActiveKey] = useState(null);

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
    if (tab === "System Emails" && sysTemplates.length === 0) {
      setSysLoading(true);
      api.get("/admin/email/system-templates")
        .then((r) => {
          const items = r.data.templates || [];
          setSysTemplates(items);
          if (items.length) setSysActiveKey(items[0].key);
        })
        .catch(() => toast.error("Failed to load system email previews"))
        .finally(() => setSysLoading(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    if (!(await confirmDialog({ title: "Delete this template?", danger: true }))) return;
    try {
      await api.delete(`/admin/email/templates/${id}`);
      toast.success("Template deleted");
      await loadTemplates();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to delete template");
    }
  };

  const fmt = (d) => d ? new Date(d).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—";

  const campaignColumns = [
    { key: "created_at", label: "Date", render: (_, row) => <span className="text-xs text-slate-500">{fmt(row.created_at)}</span> },
    { key: "segment", label: "Segment", render: (v) => <span className="text-xs text-slate-700">{v}</span> },
    { key: "subject", label: "Subject", render: (v) => <span className="text-sm text-slate-900">{v}</span> },
    { key: "sent_count", label: "Sent", render: (v) => <span className="text-sm font-medium text-green-700">{v}</span> },
    { key: "failed_count", label: "Failed", render: (v) => <span className="text-sm text-red-700">{v || 0}</span> },
    {
      key: "status", label: "Status",
      render: (v) => (
        <Badge variant={v === "completed" ? "success" : v === "failed" ? "danger" : "warning"}>{v}</Badge>
      ),
    },
  ];

  return (
    <AdministrationLayout
      title="Email Center"
      subtitle="Send communications and manage email templates"
      sidebar={(templates.length > 0 || campaigns.length > 0) ? <EmailCenterSidebar templates={templates} campaigns={campaigns} fmt={fmt} /> : undefined}
    >
      <NavTabs
        tabs={TABS.map((t) => ({ id: t, label: t }))}
        active={tab}
        onChange={setTab}
        className="mb-6"
      />

      {/* Compose */}
      {tab === "Compose" && (
        <div>
          <NavTabs
            tabs={[{ id: "individual", label: "Individual" }, { id: "bulk", label: "Bulk" }]}
            active={mode}
            onChange={setMode}
            variant="pill"
            className="mb-5"
          />

          {mode === "individual" ? (
            <Card padding="lg" className="space-y-4 max-w-2xl">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">Recipient</label>
                {selectedUser ? (
                  <div className="flex items-center justify-between px-3 py-2 border border-slate-300 bg-slate-50">
                    <div>
                      <span className="text-sm font-medium text-slate-900">{selectedUser.full_name || selectedUser.email}</span>
                      <span className="text-xs text-slate-500 ml-2">{selectedUser.email}</span>
                    </div>
                    <Button variant="link" size="sm" onClick={() => setSelectedUser(null)}>Remove</Button>
                  </div>
                ) : (
                  <div className="relative">
                    <Input
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      placeholder="Search by name or email…"
                    />
                    {userResults.length > 0 && (
                      <div className="absolute z-10 top-full left-0 right-0 mt-1 shadow-md max-h-48 overflow-y-auto">
                        <List>
                          {userResults.map((u) => (
                            <ListItem
                              key={u.id}
                              title={u.full_name || u.email}
                              subtitle={u.email}
                              onClick={() => { setSelectedUser(u); setUserSearch(""); setUserResults([]); }}
                            />
                          ))}
                        </List>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <Input
                label="Subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Email subject…"
              />
              <Textarea
                label="Body (HTML)"
                value={bodyHtml}
                onChange={(e) => setBodyHtml(e.target.value)}
                rows={10}
                className="font-mono"
                placeholder="<p>Hello {name},</p><p>Your message here...</p>"
              />
              <Button onClick={sendIndividual} loading={sending}>
                Send Email
              </Button>
            </Card>
          ) : (
            <Card padding="lg" className="space-y-4 max-w-2xl">
              <FormSelect
                label="Recipient Segment"
                value={bulkSegment}
                onChange={(e) => setBulkSegment(e.target.value)}
              >
                {SEGMENTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </FormSelect>
              <Input
                label="Subject"
                value={bulkSubject}
                onChange={(e) => setBulkSubject(e.target.value)}
                placeholder="Email subject…"
              />
              <Textarea
                label="Body (HTML)"
                value={bulkBody}
                onChange={(e) => setBulkBody(e.target.value)}
                rows={10}
                className="font-mono"
                placeholder="<p>Hello,</p><p>Your message here...</p>"
              />
              {bulkResult && (
                <Alert variant="success">
                  Campaign complete — {bulkResult.sent_count} sent, {bulkResult.failed_count} failed
                </Alert>
              )}
              <Button onClick={sendBulk} loading={bulkSending}>
                Send to {SEGMENTS.find((s) => s.value === bulkSegment)?.label}
              </Button>
            </Card>
          )}
        </div>
      )}

      {/* Templates */}
      {tab === "Templates" && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <p className="text-sm text-slate-600">{templates.length} templates</p>
            <Button size="sm" onClick={() => setShowNewTemplate(true)}>
              <Plus size={14} /> New Template
            </Button>
          </div>

          {showNewTemplate && (
            <Card padding="lg" className="mb-4 space-y-3">
              <h3 className="text-sm font-semibold text-slate-800">New Template</h3>
              <Input value={newTplName} onChange={(e) => setNewTplName(e.target.value)} placeholder="Template name" />
              <Input value={newTplSubject} onChange={(e) => setNewTplSubject(e.target.value)} placeholder="Email subject" />
              <Textarea value={newTplBody} onChange={(e) => setNewTplBody(e.target.value)} rows={6} className="font-mono" placeholder="HTML body…" />
              <div className="flex gap-2">
                <Button size="sm" onClick={createTemplate} loading={tplSaving}>Save Template</Button>
                <Button size="sm" variant="ghost" onClick={() => setShowNewTemplate(false)}>Cancel</Button>
              </div>
            </Card>
          )}

          {templatesLoading ? (
            <div className="space-y-2">{[...Array(3)].map((_, i) => <SkeletonLine key={i} height={96} />)}</div>
          ) : templates.length === 0 ? (
            <EmptyState icon={<Mail />} title="No email templates yet" />
          ) : (
            <div className="space-y-3">
              {templates.map((tpl) => (
                <Card key={tpl.id} padding="lg">
                  {editingTpl?.id === tpl.id ? (
                    <div className="space-y-3">
                      <Input value={editingTpl.name} onChange={(e) => setEditingTpl({ ...editingTpl, name: e.target.value })} />
                      <Input value={editingTpl.subject} onChange={(e) => setEditingTpl({ ...editingTpl, subject: e.target.value })} />
                      <Textarea value={editingTpl.body_html} onChange={(e) => setEditingTpl({ ...editingTpl, body_html: e.target.value })} rows={5} className="font-mono" />
                      <div className="flex gap-2">
                        <Button size="sm" onClick={() => updateTemplate(tpl.id)} loading={tplSaving}>Save</Button>
                        <Button size="sm" variant="ghost" onClick={() => setEditingTpl(null)}>Cancel</Button>
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
                        <Button variant="ghost" size="icon" onClick={() => setEditingTpl({ ...tpl })} aria-label={`Edit ${tpl.name} template`}><Edit2 size={14} /></Button>
                        <Button variant="ghost" size="icon" onClick={() => deleteTemplate(tpl.id)} aria-label={`Delete ${tpl.name} template`}><Trash2 size={14} /></Button>
                      </div>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* System Emails — read-only, rendered live from the real Python templates */}
      {tab === "System Emails" && (
        sysLoading ? (
          <div className="space-y-2">{[...Array(4)].map((_, i) => <SkeletonLine key={i} height={40} />)}</div>
        ) : sysTemplates.length === 0 ? (
          <EmptyState icon={<Mail />} title="No system emails found" />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
            <div className="flex flex-col gap-1.5">
              <div style={{ marginBottom: 8 }}>
                <Alert variant="info">
                  Automatic emails triggered by product events — welcome, verification, password reset,
                  invitations. Not editable here (they carry real tokens/links); this shows exactly what
                  each one renders right now.
                </Alert>
              </div>
              {sysTemplates.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setSysActiveKey(t.key)}
                  className={`text-left px-3 py-2.5 border text-sm transition-colors ${
                    sysActiveKey === t.key
                      ? "border-[#0F2847] bg-[#0F2847]/5 font-medium text-[#0F2847]"
                      : "border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  <div>{t.label}</div>
                  <div className="text-xs text-slate-400 font-normal mt-0.5">{t.trigger}</div>
                </button>
              ))}
            </div>
            <Card padding="none">
              {(() => {
                const active = sysTemplates.find((t) => t.key === sysActiveKey);
                if (!active) return null;
                if (active.error) {
                  return <div className="p-6"><Alert variant="error">Preview failed: {active.error}</Alert></div>;
                }
                return (
                  <>
                    <div className="px-4 py-3 border-b border-slate-200 bg-slate-50">
                      <div className="text-xs text-slate-400 uppercase tracking-wide mb-1">Subject</div>
                      <div className="text-sm font-medium text-slate-800">{active.subject}</div>
                    </div>
                    <iframe
                      title={`preview-${active.key}`}
                      srcDoc={active.html}
                      className="w-full border-0"
                      style={{ height: 640 }}
                      sandbox=""
                    />
                  </>
                );
              })()}
            </Card>
          </div>
        )
      )}

      {/* Campaigns */}
      {tab === "Campaigns" && (
        campaignsLoading ? (
          <div className="space-y-2">{[...Array(4)].map((_, i) => <SkeletonLine key={i} height={40} />)}</div>
        ) : campaigns.length === 0 ? (
          <EmptyState icon={<Mail />} title="No campaigns sent yet" />
        ) : (
          <DataTable columns={campaignColumns} rows={campaigns} />
        )
      )}
    </AdministrationLayout>
  );
}

// ── Right rail — templates and campaigns already fetched by their tabs above ──
function EmailCenterSidebar({ templates, campaigns, fmt }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {templates.length > 0 && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Mail size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Email Templates</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {templates.slice(0, 3).map((tpl) => (
              <div key={tpl.id} style={{ fontSize: 12, color: "#374151" }}>{tpl.name}</div>
            ))}
          </div>
          <p style={{ fontSize: 11, color: "#94A3B8", margin: "8px 0 0" }}>{templates.length} template{templates.length !== 1 ? "s" : ""} saved</p>
        </Card>
      )}

      {campaigns.length > 0 && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Send size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Recent Campaigns</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {campaigns.slice(0, 3).map((c) => (
              <div key={c.id}>
                <div style={{ fontSize: 12, color: "#374151", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.subject}</div>
                <div style={{ fontSize: 11, color: "#94A3B8" }}>{fmt(c.created_at)} · {c.sent_count} sent</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

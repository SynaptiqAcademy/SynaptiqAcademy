import React, { useState, useEffect, useRef } from "react";
import { Mail, Plus, Edit2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  NavTabs, Card, Input, Textarea, FormSelect, Button, Badge, Alert,
  EmptyState, SkeletonLine, DataTable, List, ListItem,
} from "@/components/ds";

const TABS = ["Compose", "Templates", "Campaigns"];
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

/**
 * Institutions directory page (/institutions).
 *
 * Premium "institution storefront" — search/filter by country & type,
 * browse cards (name, country, type, member count). Owners can create.
 */
import React, { useCallback, useEffect, useState } from "react";
import api from "../lib/api";
import { toast } from "sonner";
import { Spinner, EmptyState, Button, Input, FormSelect, Textarea, Modal, Card } from "@/components/ds";
import {
  Building2, Search, Plus, MapPin, Users, GraduationCap, FlaskConical,
  Landmark, Briefcase,
} from "lucide-react";
import { DiscoveryLayout } from "@/layouts";

const TYPES = [
  { v: "university",         label: "University",          Icon: GraduationCap },
  { v: "research_institute", label: "Research institute",  Icon: FlaskConical },
  { v: "government",         label: "Government",          Icon: Landmark },
  { v: "company",            label: "Company",             Icon: Briefcase },
  { v: "multi_campus",       label: "Multi-campus",        Icon: Building2 },
  { v: "other",              label: "Other",               Icon: Building2 },
];

export default function Institutions() {
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [country, setCountry] = useState("");
  const [items, setItems] = useState(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setItems(null);
    try {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (type) params.set("type", type);
      if (country) params.set("country", country);
      const { data } = await api.get(`/institutions?${params.toString()}`);
      setItems(data.results || []);
    } catch { setItems([]); }
  }, [q, type, country]);
  useEffect(() => { const t = setTimeout(load, q ? 300 : 0); return () => clearTimeout(t); }, [q, load]);

  return (
    <DiscoveryLayout
      title="Institutional research"
      subtitle="Universities, research institutes, and government agencies. Join your home institution, govern your roster, and aggregate the research output of every researcher under one roof."
      actions={
        <Button data-testid="create-institution-btn" onClick={() => setCreating(true)}>
          <Plus size={12} strokeWidth={1.5} /> Register institution
        </Button>
      }
    >
    <div className="space-y-8">
      <div className="flex flex-wrap gap-2 items-center">
        <Input
          data-testid="institutions-search"
          value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Search by name, description, or research area…"
          prefix={<Search size={13} strokeWidth={1.5} />}
          wrapperClassName="flex-1 min-w-[260px]"
        />
        <FormSelect data-testid="institutions-type-filter" value={type} onChange={(e) => setType(e.target.value)} size="sm" wrapperClassName="w-auto">
          <option value="">All types</option>
          {TYPES.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
        </FormSelect>
        <Input data-testid="institutions-country" value={country} onChange={(e) => setCountry(e.target.value)} placeholder="Country code (e.g. US, CH)" size="sm" wrapperClassName="w-44" />
      </div>

      {items === null && <div className="py-4 flex justify-center"><Spinner size={16} /></div>}
      {items && items.length === 0 && (
        <EmptyState
          data-testid="institutions-empty"
          title="No institutions match"
          description="Try different filters or register a new one."
        />
      )}
      {items && items.length > 0 && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="institutions-list">
          {items.map((i) => <InstitutionCard key={i.id} i={i} />)}
        </div>
      )}

      {creating && <CreateModal onClose={() => setCreating(false)} onCreated={load} />}
    </div>
    </DiscoveryLayout>
  );
}

function InstitutionCard({ i }) {
  const meta = TYPES.find((t) => t.v === i.type) || TYPES[0];
  const Icon = meta.Icon;
  return (
    <Card to={`/institutions/${i.id}`} padding="lg" className="hover:border-[#0F2847] group" data-testid={`institution-card-${i.id}`}>
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 shrink-0 bg-[#0F2847]/5 border border-[#0F2847]/20 flex items-center justify-center">
          {i.logo_url
            ? <img src={i.logo_url} alt="" className="w-full h-full object-cover" />
            : <Icon size={20} strokeWidth={1.5} className="text-[#0F2847]" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500">
            <span className="overline">{meta.label}</span>
            {i.country && <span className="inline-flex items-center gap-0.5"><MapPin size={9} strokeWidth={1.5} /> {i.country}</span>}
          </div>
          <h3 className="font-serif text-lg text-slate-900 mt-1 group-hover:text-[#0F2847] truncate">{i.name}</h3>
          {i.description && <p className="text-xs text-slate-600 mt-1 line-clamp-2">{i.description}</p>}
        </div>
      </div>
      <div className="flex items-center gap-3 mt-4 text-[11px] font-mono text-slate-500">
        <span className="inline-flex items-center gap-1"><Users size={10} strokeWidth={1.5} /> {i.member_count || 0} member{(i.member_count || 0) === 1 ? "" : "s"}</span>
        {(i.research_areas || []).slice(0, 2).map((r) => (
          <span key={r} className="border border-slate-200 px-1.5 py-0.5">{r}</span>
        ))}
      </div>
    </Card>
  );
}

function CreateModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [type, setType] = useState("university");
  const [country, setCountry] = useState("");
  const [website, setWebsite] = useState("");
  const [description, setDescription] = useState("");
  const [domains, setDomains] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!name.trim()) { toast.error("Name required"); return; }
    setBusy(true);
    try {
      await api.post("/institutions", {
        name: name.trim(), type, country: country || null, website: website || null,
        description: description || null,
        email_domains: domains.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean),
      });
      toast.success("Institution registered");
      onCreated?.();
      onClose?.();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };
  return (
    <Modal
      open
      onClose={onClose}
      closeOnOverlay
      title="Register institution"
      data-testid="create-institution-modal"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
          <Button data-testid="create-inst-submit" size="sm" disabled={busy} loading={busy} onClick={submit}>Register</Button>
        </>
      }
    >
      <div className="space-y-3">
        <Input
          label="Institution name"
          data-testid="create-inst-name"
          value={name} onChange={(e) => setName(e.target.value)}
          placeholder="ETH Zurich / Max Planck / NIH …"
        />
        <div className="grid grid-cols-2 gap-3">
          <FormSelect label="Type" data-testid="create-inst-type" value={type} onChange={(e) => setType(e.target.value)}>
            {TYPES.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
          </FormSelect>
          <Input label="Country" data-testid="create-inst-country" value={country} onChange={(e) => setCountry(e.target.value)} placeholder="CH, US, DE…" />
        </div>
        <Input label="Website" data-testid="create-inst-website" value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="https://…" />
        <Textarea
          label="Description"
          data-testid="create-inst-description"
          rows={3} value={description} onChange={(e) => setDescription(e.target.value)}
          placeholder="One paragraph about the institution's research focus."
        />
        <Input
          label="Email domains (auto-verify members)"
          data-testid="create-inst-domains"
          value={domains} onChange={(e) => setDomains(e.target.value)}
          placeholder="ethz.ch, ee.ethz.ch"
        />
      </div>
    </Modal>
  );
}

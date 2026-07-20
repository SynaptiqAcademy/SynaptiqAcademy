/**
 * Institutions directory page (/institutions).
 *
 * Premium "institution storefront" — search/filter by country & type,
 * browse cards (name, country, type, member count). Owners can create.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { NAVY } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";
import {
  Building2, Search, Plus, Loader2, MapPin, Users, GraduationCap, FlaskConical,
  Landmark, Briefcase, X,
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

  const load = async () => {
    setItems(null);
    try {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (type) params.set("type", type);
      if (country) params.set("country", country);
      const { data } = await api.get(`/institutions?${params.toString()}`);
      setItems(data.results || []);
    } catch { setItems([]); }
  };
  useEffect(() => { const t = setTimeout(load, q ? 300 : 0); return () => clearTimeout(t); /* eslint-disable-next-line */ }, [q, type, country]);

  return (
    <DiscoveryLayout
      title="Institutional research"
      subtitle="Universities, research institutes, and government agencies. Join your home institution, govern your roster, and aggregate the research output of every researcher under one roof."
      actions={
        <button
          data-testid="create-institution-btn"
          onClick={() => setCreating(true)}
          className="inline-flex items-center gap-2 bg-[#0F2847] text-white text-sm px-4 py-2 hover:bg-slate-800"
        >
          <Plus size={12} strokeWidth={1.5} /> Register institution
        </button>
      }
    >
    <div className="space-y-8">
      <div className="flex flex-wrap gap-2 items-center">
        <div className="relative flex-1 min-w-[260px]">
          <Search size={13} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            data-testid="institutions-search"
            value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search by name, description, or research area…"
            className="w-full pl-9 pr-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
          />
        </div>
        <select data-testid="institutions-type-filter" value={type} onChange={(e) => setType(e.target.value)} className="text-xs px-3 py-2 border border-slate-300">
          <option value="">All types</option>
          {TYPES.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
        </select>
        <input data-testid="institutions-country" value={country} onChange={(e) => setCountry(e.target.value)} placeholder="Country code (e.g. US, CH)" className="text-xs px-3 py-2 border border-slate-300 w-44" />
      </div>

      {items === null && <div className="py-4 flex justify-center"><Spinner size={16} /></div>}
      {items && items.length === 0 && (
        <div className="text-center py-16 border border-dashed border-slate-300 text-sm text-slate-500" data-testid="institutions-empty">
          No institutions match. Try different filters or register a new one.
        </div>
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
    <Link to={`/institutions/${i.id}`} className="block border border-slate-200 bg-white p-5 hover:border-[#0F2847] group transition-colors" data-testid={`institution-card-${i.id}`}>
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
    </Link>
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
    <div className="fixed inset-0 z-[100] bg-slate-900/50 flex items-center justify-center px-4 overflow-y-auto py-10" onClick={onClose} data-testid="create-institution-modal">
      <div className="bg-white w-full max-w-xl border border-slate-200" onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <h3 className="font-serif text-xl text-slate-900">Register institution</h3>
          <button onClick={onClose}><X size={16} strokeWidth={1.5} className="text-slate-400 hover:text-slate-900" /></button>
        </div>
        <div className="p-5 space-y-3">
          <div>
            <div className="overline mb-1">Institution name</div>
            <input data-testid="create-inst-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="ETH Zurich / Max Planck / NIH …" className="w-full px-3 py-2 border border-slate-300 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="overline mb-1">Type</div>
              <select data-testid="create-inst-type" value={type} onChange={(e) => setType(e.target.value)} className="w-full px-3 py-2 border border-slate-300 text-sm">
                {TYPES.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <div className="overline mb-1">Country</div>
              <input data-testid="create-inst-country" value={country} onChange={(e) => setCountry(e.target.value)} placeholder="CH, US, DE…" className="w-full px-3 py-2 border border-slate-300 text-sm" />
            </div>
          </div>
          <div>
            <div className="overline mb-1">Website</div>
            <input data-testid="create-inst-website" value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="https://…" className="w-full px-3 py-2 border border-slate-300 text-sm" />
          </div>
          <div>
            <div className="overline mb-1">Description</div>
            <textarea data-testid="create-inst-description" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="One paragraph about the institution's research focus." className="w-full px-3 py-2 border border-slate-300 text-sm" />
          </div>
          <div>
            <div className="overline mb-1">Email domains (auto-verify members)</div>
            <input data-testid="create-inst-domains" value={domains} onChange={(e) => setDomains(e.target.value)} placeholder="ethz.ch, ee.ethz.ch" className="w-full px-3 py-2 border border-slate-300 text-sm" />
          </div>
        </div>
        <div className="border-t border-slate-200 px-5 py-3 flex items-center justify-end gap-2">
          <button onClick={onClose} className="text-xs text-slate-600 px-3 py-2">Cancel</button>
          <button data-testid="create-inst-submit" disabled={busy} onClick={submit} className="text-xs bg-[#0F2847] text-white px-4 py-2 hover:bg-slate-800 disabled:opacity-50 inline-flex items-center gap-1.5">
            {busy && <Loader2 size={11} className="animate-spin" />} Register
          </button>
        </div>
      </div>
    </div>
  );
}

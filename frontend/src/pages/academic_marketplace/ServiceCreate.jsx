/* eslint-disable */
import React, { useState } from "react";
import { CheckCircle } from "lucide-react";
import { ACCENT, EMERALD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Input, Textarea, FormSelect, Tag, TagGroup, NavTabs, Button, Alert, H2 } from "@/components/ds";

const API = "/api/acad-market";

const CATEGORIES = [
  "statistical_analysis", "systematic_review", "scientific_writing", "grant_writing",
  "programming", "peer_review", "data_visualization", "research_consulting",
  "meta_analysis", "academic_editing", "machine_learning", "mentorship",
  "survey_design", "data_cleaning", "experimental_design", "bibliometric_analysis",
];

const emptyPkg = (tier) => ({ tier, description: "", price: "", delivery_days: 7, revisions: 1, features: [] });

export default function ServiceCreate() {
  const [form, setForm] = useState({
    title: "", description: "", category: "", tags: [], methodology: "",
    deliverables: [], faqs: [], packages: [emptyPkg("basic")], requirements_from_client: "",
  });
  const [tagInput, setTagInput] = useState("");
  const [delivInput, setDelivInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const [activePkg, setActivePkg] = useState(0);

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }));
  const setPkg = (i, key, val) => setForm(f => { const pkgs = [...f.packages]; pkgs[i] = { ...pkgs[i], [key]: val }; return { ...f, packages: pkgs }; });
  const addPkg = () => { if (form.packages.length < 3) { const tiers = ["basic", "standard", "premium"]; const next = tiers[form.packages.length]; setForm(f => ({ ...f, packages: [...f.packages, emptyPkg(next)] })); } };

  const addTag = () => { if (tagInput.trim()) { set("tags", [...form.tags, tagInput.trim()]); setTagInput(""); } };
  const addDeliv = () => { if (delivInput.trim()) { set("deliverables", [...form.deliverables, delivInput.trim()]); setDelivInput(""); } };

  const save = async () => {
    if (!form.title || !form.category) { setMsg({ type: "error", text: "Title and category are required." }); return; }
    setSaving(true);
    const r = await fetch(`${API}/services`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
    const d = await r.json();
    if (d.error) { setMsg({ type: "error", text: d.error }); setSaving(false); }
    else { window.location.href = `/academic-marketplace/services/${d.id}`; }
  };

  const input = (key, label, placeholder, type = "text") => (
    <Input
      label={label}
      type={type}
      value={form[key] || ""}
      onChange={e => set(key, e.target.value)}
      placeholder={placeholder}
      wrapperClassName="mb-5"
    />
  );

  const pkg = form.packages[activePkg] || {};

  return (
    <ResearchLayout title="Create a Service" subtitle="List your expertise as a verifiable academic service.">

        {msg && (
          <Alert variant={msg.type === "error" ? "error" : "success"} style={{ marginBottom: 20 }}>
            {msg.text}
          </Alert>
        )}

        <Card padding="xl" className="mb-5">
          <H2 className="mb-5" style={{ fontSize: "1.0625rem" }}>Basic Information</H2>
          {input("title", "Service Title *", "e.g., Professional Statistical Analysis for Research Papers")}

          <FormSelect
            label="Category *"
            value={form.category}
            onChange={e => set("category", e.target.value)}
            wrapperClassName="mb-5"
          >
            <option value="">Select a category</option>
            {CATEGORIES.map(c => <option key={c} value={c}>{c.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}</option>)}
          </FormSelect>

          <Textarea
            label="Description"
            value={form.description}
            onChange={e => set("description", e.target.value)}
            placeholder="Describe what you offer, who it's for, and what makes it unique..."
            rows={5}
            wrapperClassName="mb-5"
          />

          {input("methodology", "Methodology", "Describe your approach and methods...")}

          <div className="mb-5">
            <label className="block text-sm font-semibold text-navy-700 mb-1.5">Deliverables</label>
            {form.deliverables.map((d, i) => (
              <div key={i} className="flex gap-2 items-center mb-1.5">
                <CheckCircle size={14} className="text-emerald-600" />
                <span className="text-sm text-navy-700">{d}</span>
                <button onClick={() => set("deliverables", form.deliverables.filter((_, j) => j !== i))} className="bg-transparent border-none cursor-pointer text-crimson-600 text-base ml-auto">×</button>
              </div>
            ))}
            <div className="flex gap-2">
              <Input
                value={delivInput}
                onChange={e => setDelivInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && addDeliv()}
                placeholder="Add a deliverable (press Enter)"
                wrapperClassName="flex-1"
              />
              <Button onClick={addDeliv}>Add</Button>
            </div>
          </div>

          <div className="mb-5">
            <label className="block text-sm font-semibold text-navy-700 mb-1.5">Tags</label>
            <TagGroup className="mb-2">
              {form.tags.map((t, i) => (
                <Tag key={i} color={ACCENT} onRemove={() => set("tags", form.tags.filter((_, j) => j !== i))}>
                  {t}
                </Tag>
              ))}
            </TagGroup>
            <div className="flex gap-2">
              <Input
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && addTag()}
                placeholder="Add a tag"
                wrapperClassName="flex-1"
              />
              <Button onClick={addTag}>Add</Button>
            </div>
          </div>
        </Card>

        {/* Packages */}
        <Card padding="xl" className="mb-5">
          <div className="flex justify-between items-center mb-5">
            <H2 className="m-0" style={{ fontSize: "1.0625rem" }}>Packages</H2>
            {form.packages.length < 3 && (
              <Button variant="ghost" size="sm" onClick={addPkg}>
                + Add {["", "Standard", "Premium"][form.packages.length]} Package
              </Button>
            )}
          </div>
          <NavTabs
            variant="segment"
            tabs={form.packages.map((p, i) => ({ id: String(i), label: p.tier ? p.tier[0].toUpperCase() + p.tier.slice(1) : p.tier }))}
            active={String(activePkg)}
            onChange={id => setActivePkg(Number(id))}
            className="mb-5"
          />
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: "Price (USD)", key: "price", type: "number", placeholder: "100" },
              { label: "Delivery Days", key: "delivery_days", type: "number", placeholder: "7" },
              { label: "Revisions Included", key: "revisions", type: "number", placeholder: "1" },
            ].map(({ label, key, type, placeholder }) => (
              <Input
                key={key}
                label={label}
                type={type}
                value={pkg[key] || ""}
                onChange={e => setPkg(activePkg, key, e.target.value)}
                placeholder={placeholder}
              />
            ))}
            <Input
              label="Description"
              value={pkg.description || ""}
              onChange={e => setPkg(activePkg, "description", e.target.value)}
              placeholder="What's included?"
            />
          </div>
        </Card>

        <Button onClick={save} disabled={saving} loading={saving} size="lg" className="w-full">
          {saving ? "Publishing..." : "Publish Service"}
        </Button>
    </ResearchLayout>
  );
}

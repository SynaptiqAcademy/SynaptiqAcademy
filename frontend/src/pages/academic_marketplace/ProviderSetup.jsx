import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Star, ShieldCheck } from "lucide-react";
import { NAVY, ACCENT, EMERALD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Input, Textarea, FormSelect, Tag, TagGroup, Button, Alert } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = "/api/acad-market";

// ── Right rail — the provider's own live stats, already fetched from /me ──────
function ProviderSetupSidebar({ existing }) {
  const verLabel = (lvl) => {
    if (lvl >= 5) return { label: "Elite", color: "#7C3AED" };
    if (lvl >= 4) return { label: "Expert Verified", color: EMERALD };
    if (lvl >= 3) return { label: "Institution Verified", color: ACCENT };
    if (lvl >= 2) return { label: "ID Verified", color: "#0891B2" };
    return { label: "Unverified", color: "#94A3B8" };
  };
  const ver = verLabel(existing.verification_level);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
          <Star size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Your Provider Stats</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "#64748B" }}>Rating</span>
            <span style={{ fontWeight: 600, color: "#0f172a" }}>
              {existing.average_rating > 0 ? existing.average_rating.toFixed(1) : "New"} {existing.rating_count > 0 ? `(${existing.rating_count})` : ""}
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "#64748B" }}>Completed orders</span>
            <span style={{ fontWeight: 600, color: "#0f172a" }}>{existing.completed_orders ?? 0}</span>
          </div>
          {existing.success_rate != null && (
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
              <span style={{ color: "#64748B" }}>Success rate</span>
              <span style={{ fontWeight: 600, color: "#0f172a" }}>{existing.success_rate.toFixed(0)}%</span>
            </div>
          )}
        </div>
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <ShieldCheck size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Verification</div>
        </div>
        <div style={{ fontSize: 12.5, fontWeight: 700, color: ver.color }}>{ver.label}</div>
        <p style={{ fontSize: 11.5, color: "#94A3B8", margin: "6px 0 0", lineHeight: 1.5 }}>
          Higher verification levels build trust with buyers and improve your ranking.
        </p>
      </Card>
    </div>
  );
}

const CATEGORIES = [
  "statistical_analysis", "systematic_review", "scientific_writing", "grant_writing",
  "programming", "peer_review", "data_visualization", "research_consulting",
  "meta_analysis", "academic_editing", "machine_learning", "mentorship",
];

export default function ProviderSetup() {
  const [existing, setExisting] = useState(null);
  const [form, setForm] = useState({ display_name: "", headline: "", bio: "", categories: [], hourly_rate: "", currency: "USD", availability: "available", response_time_hours: 24, languages: ["English"] });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    fetchApi(`${API}/providers/me`).then(r => r.json()).then(d => {
      if (!d.error) {
        setExisting(d);
        setForm(f => ({ ...f, ...d }));
      }
    });
  }, []);

  const toggleCat = (c) => setForm(f => ({
    ...f, categories: f.categories.includes(c) ? f.categories.filter(x => x !== c) : [...f.categories, c]
  }));

  const save = async () => {
    setSaving(true);
    const method = existing ? "PUT" : "POST";
    const r = await fetchApi(`${API}/providers/me`, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
    const d = await r.json();
    if (d.error) setMsg({ type: "error", text: d.error });
    else { setExisting(d); setMsg({ type: "success", text: existing ? "Profile updated!" : "Provider profile created!" }); }
    setSaving(false);
  };

  return (
    <ResearchLayout
      title={existing ? "Edit Provider Profile" : "Become a Provider"}
      subtitle="Offer your academic expertise to the community."
      sidebar={existing ? <ProviderSetupSidebar existing={existing} /> : undefined}
    >

        {msg && (
          <Alert variant={msg.type === "error" ? "error" : "success"} style={{ marginBottom: 20 }}>
            {msg.text}
          </Alert>
        )}

        <Card padding="xl">
          {[
            { label: "Display Name *", key: "display_name", placeholder: "Dr. Jane Smith" },
            { label: "Professional Headline", key: "headline", placeholder: "Biostatistician | 10 years experience" },
          ].map(({ label, key, placeholder }) => (
            <Input
              key={key}
              label={label}
              value={form[key] || ""}
              onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
              placeholder={placeholder}
              wrapperClassName="mb-5"
            />
          ))}

          <Textarea
            label="Bio"
            value={form.bio || ""}
            onChange={e => setForm(f => ({ ...f, bio: e.target.value }))}
            placeholder="Describe your expertise, background, and research experience..."
            rows={4}
            wrapperClassName="mb-5"
          />

          <div className="mb-5">
            <label className="block text-sm font-semibold text-navy-700 mb-2.5">Specialties (select all that apply)</label>
            <TagGroup gap={8}>
              {CATEGORIES.map(c => (
                <Tag
                  key={c}
                  variant={form.categories.includes(c) ? "active" : "default"}
                  onClick={() => toggleCat(c)}
                >
                  {c.replace(/_/g, " ")}
                </Tag>
              ))}
            </TagGroup>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
            <Input
              label="Hourly Rate (USD)"
              type="number"
              value={form.hourly_rate || ""}
              onChange={e => setForm(f => ({ ...f, hourly_rate: e.target.value }))}
              placeholder="0"
            />
            <FormSelect
              label="Availability"
              value={form.availability}
              onChange={e => setForm(f => ({ ...f, availability: e.target.value }))}
            >
              <option value="available">Available</option>
              <option value="busy">Busy</option>
              <option value="on_vacation">On Vacation</option>
            </FormSelect>
          </div>

          <Button onClick={save} disabled={saving || !form.display_name} loading={saving} size="lg" className="w-full">
            {saving ? "Saving..." : existing ? "Update Profile" : "Create Provider Profile"}
          </Button>

          {existing && (
            <div className="mt-4 flex gap-3">
              <Button as={Link} to="/academic-marketplace/services/create" variant="ghost" className="flex-1">
                Create a Service
              </Button>
              <Button as={Link} to="/academic-marketplace/dashboard" variant="ghost" className="flex-1">
                My Dashboard
              </Button>
            </div>
          )}
        </Card>
    </ResearchLayout>
  );
}

import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Globe2, Copy, CheckCircle2, ExternalLink } from "lucide-react";
import { SectionShell, MiniStat } from "./PassportUI";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { Switch } from "@/components/ds/Form";
import { TYPE, BRD, WARM, TEXT_MUTED, EMERALD, NAVY } from "@/lib/tokens";
import api from "@/lib/api";

/**
 * PublicPortfolioPanel — surfaces the previously-unused Public Profile
 * backend (`/api/profiles/me*`): claimed slug, visibility, view/follower
 * analytics, and a link to the existing public `/researcher/:slug` page.
 * Distinct from the Trust Passport's own public share link (PassportHero's
 * "Download Passport" / trust `public_url`) — two real, separate artifacts.
 */
export function PublicPortfolioPanel() {
  const [profile, setProfile] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [visibility, setVisibility] = useState(null);
  const [slugInput, setSlugInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.get("/profiles/me").then((r) => { setProfile(r.data); setSlugInput(r.data?.slug || ""); }).catch(() => {});
    api.get("/profiles/me/analytics").then((r) => setAnalytics(r.data)).catch(() => {});
    api.get("/profiles/me/visibility").then((r) => setVisibility(r.data)).catch(() => {});
  }, []);

  const claimSlug = async () => {
    if (!slugInput.trim()) return;
    setSaving(true);
    try {
      const { data } = await api.post("/profiles/me/slug", { slug: slugInput.trim() });
      setProfile((p) => ({ ...p, slug: data.slug || slugInput.trim() }));
      toast.success("Public portfolio URL updated");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not claim that URL");
    } finally {
      setSaving(false);
    }
  };

  const toggleVisibility = async (key, value) => {
    const next = { ...visibility, [key]: value ? "public" : "private" };
    setVisibility(next);
    try {
      await api.put("/profiles/me/visibility", next);
    } catch {
      toast.error("Could not update visibility");
    }
  };

  const portfolioUrl = profile?.slug ? `${window.location.origin}/researcher/${profile.slug}` : null;

  const copyLink = () => {
    if (!portfolioUrl) return;
    navigator.clipboard.writeText(portfolioUrl);
    setCopied(true);
    toast.success("Portfolio link copied");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <SectionShell title="Public Academic Portfolio" subtitle="Your shareable researcher page">
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 16, flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 240px", minWidth: 0 }}>
          <div style={{ ...TYPE.label, marginBottom: 6 }}>Portfolio URL</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 12, color: TEXT_MUTED }}>{window.location.origin}/researcher/</span>
            <Input value={slugInput} onChange={(e) => setSlugInput(e.target.value)} size="sm" style={{ maxWidth: 180 }} />
          </div>
        </div>
        <Button size="sm" onClick={claimSlug} loading={saving}>Save</Button>
      </div>

      {portfolioUrl && (
        <div className="flex-wrap" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, padding: "12px 16px", background: WARM, border: `1px solid ${BRD}`, borderRadius: 10, marginBottom: 16 }}>
          <a href={portfolioUrl} target="_blank" rel="noreferrer" style={{ fontSize: 12.5, color: NAVY, display: "flex", alignItems: "center", gap: 8, textDecoration: "none", minWidth: 0, overflow: "hidden" }}>
            <span style={{ width: 26, height: 26, borderRadius: 8, background: "rgba(15,40,71,0.08)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Globe2 size={12} style={{ color: NAVY }} />
            </span>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 600 }}>{portfolioUrl}</span>
            <ExternalLink size={10} style={{ flexShrink: 0 }} />
          </a>
          <Button size="sm" variant="ghost" onClick={copyLink} style={{ flexShrink: 0 }}>
            {copied ? <CheckCircle2 size={12} style={{ color: EMERALD }} /> : <Copy size={12} />} {copied ? "Copied" : "Copy"}
          </Button>
        </div>
      )}

      {analytics && (
        <div style={{ display: "flex", gap: 32, marginBottom: 16 }}>
          <MiniStat label="Profile Views" value={analytics.total_views ?? 0} />
          <MiniStat label="Followers" value={analytics.followers_count ?? 0} />
        </div>
      )}

      {visibility && (
        <div style={{ borderTop: `1px solid ${BRD}`, paddingTop: 16 }}>
          <div style={{ ...TYPE.label, marginBottom: 10 }}>Section Visibility</div>
          <div className="grid sm:grid-cols-2" style={{ gap: 8 }}>
            {Object.keys(visibility).map((key) => (
              <Switch
                key={key}
                checked={visibility[key] === "public"}
                onChange={(v) => toggleVisibility(key, v)}
                label={key.charAt(0).toUpperCase() + key.slice(1)}
                size="sm"
              />
            ))}
          </div>
        </div>
      )}
    </SectionShell>
  );
}

export default PublicPortfolioPanel;

import React from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Edit3, FilePlus2, FolderPlus, Link2, Share2, Download, FileDown, Check } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { NAVY, TEXT_SECONDARY, TEXT_PRIMARY, BRD } from "@/lib/tokens";
import api from "@/lib/api";

function downloadTextFile(filename, text) {
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * usePassportActions — Export CV, Download Passport, and Share Public Profile
 * handlers, wired into PassportHero's quick-action buttons. Ports the
 * existing downloadCV() logic from Profile.jsx as-is; "Download Passport" is
 * a new client-side export of the already-fetched trust passport data,
 * mirroring the same download pattern (no new backend).
 */
export function usePassportActions({ profile, passport }) {
  const exportCV = async () => {
    try {
      const { data } = await api.get("/users/me/cv");
      const lines = [
        `CURRICULUM VITAE`,
        `Generated: ${new Date(data.generated_at).toLocaleDateString()}`,
        "",
        `━━━ IDENTITY ━━━`,
        `Name: ${data.identity.full_name}`,
        data.identity.academic_role ? `Title: ${data.identity.academic_role}` : "",
        `Institution: ${data.identity.institution}`,
        data.identity.department ? `Department: ${data.identity.department}` : "",
        [data.identity.city, data.identity.country].filter(Boolean).join(", "),
        data.identity.email ? `Email: ${data.identity.email}` : "",
        data.identity.orcid_id ? `ORCID: https://orcid.org/${data.identity.orcid_id}` : "",
        data.identity.website ? `Website: ${data.identity.website}` : "",
        "",
        `━━━ METRICS ━━━`,
        `h-index: ${data.metrics.h_index}`,
        `Total Citations: ${data.metrics.total_citations}`,
        `Publications: ${data.metrics.publications_count}`,
        "",
      ];
      if (data.research.research_keywords.length > 0) {
        lines.push(`━━━ RESEARCH KEYWORDS ━━━`, data.research.research_keywords.join(", "), "");
      }
      if (data.employment.length > 0) {
        lines.push(`━━━ EMPLOYMENT ━━━`);
        data.employment.forEach((e) => {
          lines.push(`${e.role || "Position"} — ${e.institution}`);
          if (e.department) lines.push(`  ${e.department}`);
          if (e.start_year) lines.push(`  ${e.start_year} – ${e.end_year || "present"}`);
          lines.push("");
        });
      }
      if (data.education.length > 0) {
        lines.push(`━━━ EDUCATION ━━━`);
        data.education.forEach((e) => {
          lines.push(`${e.role || "Degree"} — ${e.institution}`);
          if (e.department) lines.push(`  ${e.department}`);
          if (e.start_year) lines.push(`  ${e.start_year} – ${e.end_year || "present"}`);
          lines.push("");
        });
      }
      if (data.publications.length > 0) {
        lines.push(`━━━ PUBLICATIONS ━━━`);
        data.publications.forEach((p, i) => {
          const doi = p.doi ? ` https://doi.org/${p.doi}` : "";
          const cites = p.citations > 0 ? ` [${p.citations} citations]` : "";
          lines.push(`${i + 1}. ${p.title} (${p.year || "n.d."})${cites}`);
          if (p.journal) lines.push(`   ${p.journal}${doi}`);
        });
      }
      downloadTextFile(`${(data.identity.full_name || "cv").replace(/\s+/g, "_")}_CV.txt`, lines.filter((l) => l !== undefined).join("\n"));
      toast.success("CV downloaded");
    } catch {
      toast.error("CV download failed");
    }
  };

  const downloadPassport = () => {
    if (!passport) return;
    const lines = [
      `ACADEMIC PASSPORT`,
      `Generated: ${passport.generated_at ? new Date(passport.generated_at).toLocaleString() : new Date().toLocaleString()}`,
      "",
      `Name: ${passport.name || profile?.full_name || ""}`,
      passport.verified_position ? `Position: ${passport.verified_position}` : "",
      passport.verified_institution ? `Institution: ${passport.verified_institution}` : "",
      passport.verified_orcid ? `ORCID: ${passport.verified_orcid}` : "",
      "",
      `Trust Score: ${passport.trust_score ?? 0} (${passport.trust_level || "—"})`,
      `Verified Publications: ${passport.verified_pub_count ?? 0}`,
      `Verified Grants: ${passport.verified_grant_count ?? 0}`,
      `Verified Reviews: ${passport.verified_review_count ?? 0}`,
      "",
      (passport.badges || []).length > 0 ? `Badges: ${passport.badges.map((b) => b.label).join(", ")}` : "",
    ].filter((l) => l !== undefined && l !== "");
    downloadTextFile(`${(profile?.full_name || "academic_passport").replace(/\s+/g, "_")}_Passport.txt`, lines.join("\n"));
    toast.success("Academic Passport downloaded");
  };

  const shareProfile = () => {
    const url = passport?.public_url ? window.location.origin + passport.public_url : window.location.href;
    if (navigator.share) {
      navigator.share({ title: profile?.full_name, url }).catch(() => {});
    } else {
      navigator.clipboard.writeText(url).then(() => toast.success("Link copied"));
    }
  };

  return { exportCV, downloadPassport, shareProfile };
}

function hasOrcid(profile) {
  const o = profile?.orcid;
  if (!o) return false;
  if (typeof o === "object") return !!o.orcid_id;
  return true;
}

function ActionRow({ icon: Icon, label, done, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={done}
      style={{
        display: "flex", alignItems: "center", gap: 9, width: "100%", padding: "8px 4px",
        border: "none", background: "transparent", cursor: done ? "default" : "pointer", textAlign: "left",
        borderRadius: 6,
      }}
      onMouseEnter={(e) => { if (!done) e.currentTarget.style.background = "#F8FAFC"; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
    >
      <Icon size={14} style={{ color: done ? "#059669" : NAVY, flexShrink: 0 }} />
      <span style={{ fontSize: 12.5, color: TEXT_SECONDARY, flex: 1 }}>{label}</span>
      {done && <Check size={14} style={{ color: "#059669", flexShrink: 0 }} />}
    </button>
  );
}

/**
 * QuickActionsRail — right-rail card version of the passport quick actions.
 * All actions are real: identity edit, real create-flows, real ORCID connect
 * state, and the same export/share handlers as the hero buttons.
 */
export function QuickActionsRail({ profile, passport, verification, onEdit }) {
  const navigate = useNavigate();
  const { exportCV, downloadPassport, shareProfile } = usePassportActions({ profile, passport });
  const orcidConnected = hasOrcid(profile) || !!verification?.orcid_verified;

  return (
    <Card padding="lg">
      <div style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY, marginBottom: 8 }}>Quick Actions</div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        <ActionRow icon={Edit3} label="Edit Academic Identity" onClick={onEdit} />
        <ActionRow icon={FilePlus2} label="Add Publication" onClick={() => navigate("/publication-hub")} />
        <ActionRow icon={FolderPlus} label="Add Project" onClick={() => navigate("/projects")} />
        <ActionRow
          icon={Link2}
          label={orcidConnected ? "ORCID Connected" : "Connect ORCID"}
          done={orcidConnected}
          onClick={() => navigate("/academic-passport#research_integrations")}
        />
        <div style={{ height: 1, background: BRD, margin: "4px 0" }} />
        <ActionRow icon={Share2} label="Share Public Profile" onClick={shareProfile} />
        <ActionRow icon={Download} label="Export CV" onClick={exportCV} />
        <ActionRow icon={FileDown} label="Download Passport" onClick={downloadPassport} />
      </div>
    </Card>
  );
}

export default usePassportActions;

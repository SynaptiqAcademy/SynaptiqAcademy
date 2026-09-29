import { toast } from "sonner";
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
 * handlers, wired into PassportCredentialHeader's quick-action buttons. Ports
 * the existing downloadCV() logic from Profile.jsx as-is; "Download Passport"
 * is a client-side export of the already-fetched trust passport data,
 * mirroring the same download pattern (no new backend).
 */
export function usePassportActions({ profile, passport, publicUrl }) {
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

  // Shares the real public researcher portfolio page (/researcher/:slug —
  // ResearcherProfile.jsx, the only public-facing profile route that
  // actually exists). passport.public_url ("/passport/{token}") has no
  // matching frontend route at all — sharing it silently handed people a
  // 404 (P1 Phase 7C4.3 §4, found during the functional audit).
  const shareProfile = () => {
    const url = publicUrl || window.location.href;
    if (navigator.share) {
      navigator.share({ title: profile?.full_name, url }).catch(() => {});
    } else {
      navigator.clipboard.writeText(url).then(() => toast.success("Link copied"));
    }
  };

  return { exportCV, downloadPassport, shareProfile };
}

export default usePassportActions;

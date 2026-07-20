import React from "react";
import { Download, FileDown, Share2, Eye } from "lucide-react";
import { PublicPortfolioPanel } from "@/components/passport/PublicPortfolioPanel";
import { AcademicTimelineSection } from "@/components/passport/AcademicTimelineSection";
import { SectionShell } from "@/components/passport/PassportUI";
import { Card } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { TEXT_SECONDARY, TEXT_PRIMARY } from "@/lib/tokens";

function ActionCard({ icon: Icon, label, description, onClick, href }) {
  const content = (
    <>
      <div style={{ width: 34, height: 34, borderRadius: 9, background: "rgba(15,40,71,0.08)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 10 }}>
        <Icon size={16} color="#0F2847" />
      </div>
      <div style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY }}>{label}</div>
      <div style={{ fontSize: 11.5, color: TEXT_SECONDARY, marginTop: 3 }}>{description}</div>
    </>
  );
  if (href) {
    return <Card href={href} padding="lg">{content}</Card>;
  }
  return <Card padding="lg" onClick={onClick}>{content}</Card>;
}

/**
 * PortfolioTab — Public Academic Profile (URL, visibility, view analytics),
 * the Academic/Research Timeline, and the export/share/preview actions
 * surfaced as visible cards (previously only reachable from the right rail's
 * Quick Actions). No QR code — no QR-encoding library exists in this project
 * and a scannable code can't be safely hand-rolled in scope; Copy Link /
 * Share already cover the "get this to someone else" need honestly.
 */
export function PortfolioTab({ profile, employments, educations, pubs, exportCV, downloadPassport, shareProfile, publicUrl }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <PublicPortfolioPanel />

      <SectionShell title="Passport Actions">
        <div className="grid grid-cols-2 lg:grid-cols-4" style={{ gap: 12 }}>
          <ActionCard icon={Download} label="Export CV" description="Download as text" onClick={exportCV} />
          <ActionCard icon={FileDown} label="Download Passport" description="Verified summary" onClick={downloadPassport} />
          <ActionCard icon={Share2} label="Share Profile" description="Copy or share link" onClick={shareProfile} />
          {publicUrl ? (
            <ActionCard icon={Eye} label="Profile Preview" description="View public page" href={publicUrl} />
          ) : (
            <ActionCard icon={Eye} label="Profile Preview" description="Claim a public URL above" />
          )}
        </div>
      </SectionShell>

      <AcademicTimelineSection employments={employments} educations={educations} pubs={pubs} />
    </div>
  );
}

export default PortfolioTab;

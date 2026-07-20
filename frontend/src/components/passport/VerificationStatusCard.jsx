import React from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Clock, ArrowRight } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { EMERALD, AMBER, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, NAVY } from "@/lib/tokens";

// Maps 1:1 to real booleans on GET /api/verification/me — no invented
// "Expertise Verification" flag (closest real field is expert_verified,
// which is publication-count based, labeled accordingly).
const ITEMS = [
  { key: "identity_verified", label: "Identity Verification" },
  { key: "institution_verified", label: "Institution Verification" },
  { key: "email_verified", label: "Email Verification" },
  { key: "orcid_verified", label: "ORCID Connection" },
  { key: "expert_verified", label: "Expertise (Publication Count)" },
];

export function VerificationStatusCard({ verification }) {
  if (!verification) return null;

  return (
    <Card padding="lg">
      <div style={{ fontSize: 13, fontWeight: 700, color: TEXT_PRIMARY, marginBottom: 10 }}>Verification Status</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
        {ITEMS.map(({ key, label }) => {
          const done = !!verification[key];
          return (
            <div key={key} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>{label}</span>
              {done ? (
                <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 600, color: EMERALD }}>
                  Verified <CheckCircle2 size={13} />
                </span>
              ) : (
                <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 600, color: AMBER }}>
                  Pending <Clock size={12} />
                </span>
              )}
            </div>
          );
        })}
      </div>
      <Link to="/trust/my-verifications" style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600, color: NAVY, textDecoration: "none", marginTop: 12 }}>
        View all verifications <ArrowRight size={11} />
      </Link>
    </Card>
  );
}

export default VerificationStatusCard;

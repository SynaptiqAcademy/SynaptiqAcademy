import React from "react";
import { Users, Handshake, FolderKanban, ArrowRight, CheckCircle2 } from "lucide-react";

const NAVY = "#0F2847";
const BORDER = "#e8edf3";

/**
 * Product Proof (§14) — illustrative UI-fragment crops showing that work
 * continues from one stage to the next, instead of a text feature list.
 * Every label is explicit ("Illustrative UI state") — these are crops in
 * the product's real visual language, not real production user data.
 */
export default function ProductProof() {
  return (
    <section style={{ background: "#f8fafc", borderBottom: `1px solid ${BORDER}`, padding: "88px 0" }}>
      <div className="max-w-[1100px] mx-auto px-6 lg:px-10">
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 12 }}>
            Product proof
          </div>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.6rem, 3vw, 2.2rem)", fontWeight: 700, color: "#0a0f1a", lineHeight: 1.2, marginBottom: 12 }}>
            The work doesn't die on a profile page.
          </h2>
          <p style={{ fontSize: "0.9rem", color: "#64748b", maxWidth: 520, margin: "0 auto", lineHeight: 1.7 }}>
            A useful discovery becomes a request. An accepted request becomes a workspace.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          <ProofCard
            icon={Users}
            label="Team Builder"
            title="Roles filled with real matches"
            crop={
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {["Health Policy — 2 matches", "Data Analysis — 1 match", "Implementation Science — Essential"].map((row) => (
                  <div key={row} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.72rem", color: "#334155", background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 8, padding: "8px 10px" }}>
                    <CheckCircle2 size={12} style={{ color: "#059669", flexShrink: 0 }} />
                    {row}
                  </div>
                ))}
              </div>
            }
          />
          <ProofCard
            icon={Handshake}
            label="Collaboration Request"
            title="You send it, they approve it"
            crop={
              <div style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 8, padding: 12 }}>
                <div style={{ fontSize: "0.68rem", color: "#94a3b8", marginBottom: 6 }}>Request status</div>
                <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.78rem", fontWeight: 700, color: "#059669" }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#059669" }} />
                  Accepted
                </div>
                <div style={{ fontSize: "0.68rem", color: "#94a3b8", marginTop: 8 }}>Shared workspace created automatically</div>
              </div>
            }
          />
          <ProofCard
            icon={FolderKanban}
            label="Research Project"
            title="Tasks, files, discussion — connected"
            crop={
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {["Literature review", "Data collection", "Manuscript draft"].map((row, i) => (
                  <div key={row} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.72rem", color: "#334155", background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 8, padding: "8px 10px" }}>
                    <span style={{ width: 14, height: 14, borderRadius: 4, border: `1.5px solid ${i === 0 ? "#059669" : "#cbd5e1"}`, background: i === 0 ? "#059669" : "transparent", flexShrink: 0 }} />
                    {row}
                  </div>
                ))}
              </div>
            }
          />
        </div>

        <div style={{ textAlign: "center", marginTop: 36 }}>
          <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
            Illustrative UI states — not real production accounts or data.
          </div>
        </div>
      </div>
    </section>
  );
}

function ProofCard({ icon: Icon, label, title, crop }) {
  return (
    <div style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 14, padding: 20, boxShadow: "0 2px 12px rgba(15,40,71,0.04)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: `${NAVY}10`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <Icon size={13} strokeWidth={1.5} style={{ color: NAVY }} />
        </div>
        <span style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: "#94a3b8" }}>{label}</span>
      </div>
      <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 12 }}>{title}</div>
      {crop}
    </div>
  );
}

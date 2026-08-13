import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle, AlertCircle, ShieldCheck, FileText } from "lucide-react";
import { NAVY, EMERALD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Button, Alert, LoadingOverlay, ErrorState, Caption } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = "/api/acad-market";

export default function ContractView() {
  const { id: orderId } = useParams();
  const [contract, setContract] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    fetchApi(`${API}/contracts/${orderId}`).then(r => r.json()).then(d => {
      setContract(d.error ? null : d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [orderId]);

  const accept = async () => {
    setAccepting(true);
    const r = await fetchApi(`${API}/contracts/${orderId}/accept`, { method: "POST" });
    const d = await r.json();
    if (d.error) { setMsg({ type: "error", text: d.error }); setAccepting(false); }
    else { setContract(d); setMsg({ type: "success", text: "Contract accepted!" }); setAccepting(false); }
  };

  if (loading) return <LoadingOverlay text="Loading..." />;
  if (!contract) return <ErrorState type="not_found" message="Contract not found." />;

  return (
    <ResearchLayout
      title="Academic Services Agreement"
      sidebar={<ContractViewSidebar contract={contract} orderId={orderId} />}
    >
        <div className="mb-2">
          <Link to={`/academic-marketplace/orders/${orderId}`} className="text-crimson-600 text-[13px] no-underline">← Back to Order</Link>
        </div>

        {msg && (
          <Alert variant={msg.type === "error" ? "error" : "success"} style={{ marginBottom: 16 }}>
            {msg.text}
          </Alert>
        )}

        {/* Acceptance status */}
        <Card padding="lg" className="mb-5">
          <div className="flex gap-5">
            {[
              { label: "Buyer", accepted: contract.buyer_accepted, at: contract.buyer_accepted_at },
              { label: "Provider", accepted: contract.provider_accepted, at: contract.provider_accepted_at },
            ].map(({ label, accepted, at }) => (
              <div key={label} className="flex items-center gap-2">
                {accepted ? <CheckCircle size={16} className="text-emerald-600" /> : <AlertCircle size={16} className="text-amber-500" />}
                <div>
                  <div className="text-[13px] font-semibold text-navy-700">{label}</div>
                  <Caption>
                    {accepted ? `Accepted ${new Date(at).toLocaleDateString()}` : "Pending acceptance"}
                  </Caption>
                </div>
              </div>
            ))}
          </div>
          {!contract.provider_accepted && (
            <Button onClick={accept} loading={accepting} className="mt-4">
              {accepting ? "Accepting..." : "Accept Contract (Provider)"}
            </Button>
          )}
        </Card>

        {/* Contract text */}
        <Card padding="xl">
          <pre className="whitespace-pre-wrap font-inherit text-[13px] text-navy-700 leading-[1.8] m-0">
            {contract.contract_text}
          </pre>
        </Card>

        <div className="flex gap-2 items-center mt-4">
          <ShieldCheck size={14} className="text-emerald-600" />
          <Caption>
            This contract is binding under Synaptiq Terms of Service. Electronically accepted by both parties.
          </Caption>
        </div>
    </ResearchLayout>
  );
}

// ── Right rail — contract metadata already loaded above ───────────────────────
function ContractViewSidebar({ contract, orderId }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <FileText size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Contract Details</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "#94A3B8" }}>Status</span>
            <span style={{ color: contract.status === "active" ? EMERALD : "#374151", fontWeight: 600, textTransform: "capitalize" }}>{contract.status}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "#94A3B8" }}>Created</span>
            <span style={{ color: "#374151", fontWeight: 600 }}>{new Date(contract.created_at).toLocaleDateString()}</span>
          </div>
        </div>
        <Link to={`/academic-marketplace/orders/${orderId}`}>
          <Button as="span" size="sm" variant="ghost" style={{ width: "100%", marginTop: 10 }}>
            View Order
          </Button>
        </Link>
      </Card>
    </div>
  );
}

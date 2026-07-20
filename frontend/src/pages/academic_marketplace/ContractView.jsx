import React, { useState, useEffect } from "react";
import { CheckCircle, AlertCircle, ShieldCheck } from "lucide-react";
import { ResearchLayout } from "@/layouts";
import { Card, Button, Alert, LoadingOverlay, ErrorState, Caption } from "@/components/ds";

const API = "/api/acad-market";

export default function ContractView() {
  const orderId = window.location.pathname.split("/").pop();
  const [contract, setContract] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    fetch(`${API}/contracts/${orderId}`).then(r => r.json()).then(d => {
      setContract(d.error ? null : d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [orderId]);

  const accept = async () => {
    setAccepting(true);
    const r = await fetch(`${API}/contracts/${orderId}/accept`, { method: "POST" });
    const d = await r.json();
    if (d.error) { setMsg({ type: "error", text: d.error }); setAccepting(false); }
    else { setContract(d); setMsg({ type: "success", text: "Contract accepted!" }); setAccepting(false); }
  };

  if (loading) return <LoadingOverlay text="Loading..." />;
  if (!contract) return <ErrorState type="not_found" message="Contract not found." />;

  return (
    <ResearchLayout title="Academic Services Agreement">
        <div className="mb-2">
          <a href={`/academic-marketplace/orders/${orderId}`} className="text-crimson-600 text-[13px] no-underline">← Back to Order</a>
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

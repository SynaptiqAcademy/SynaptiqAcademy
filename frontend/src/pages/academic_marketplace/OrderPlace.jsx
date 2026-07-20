import React, { useState, useEffect } from "react";
import { ShieldCheck, Clock } from "lucide-react";
import { ResearchLayout } from "@/layouts";
import { Card, Button, Alert, Textarea, H2, Caption, LoadingOverlay } from "@/components/ds";

const API = "/api/acad-market";

export default function OrderPlace() {
  const parts = window.location.pathname.split("/");
  const serviceId = parts[parts.length - 1];
  const params = new URLSearchParams(window.location.search);
  const pkgTier = params.get("pkg") || "basic";

  const [service, setService] = useState(null);
  const [pkg, setPkg] = useState(null);
  const [form, setForm] = useState({ requirements: "", milestones: [] });
  const [placing, setPlacing] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    fetch(`${API}/services/${serviceId}`).then(r => r.json()).then(svc => {
      setService(svc);
      const p = (svc.packages || []).find(x => x.tier === pkgTier) || svc.packages?.[0];
      setPkg(p);
    });
  }, [serviceId, pkgTier]);

  const place = async () => {
    setPlacing(true);
    const r = await fetch(`${API}/orders`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service_id: serviceId, package_tier: pkg?.tier || pkgTier, requirements: form.requirements }),
    });
    const d = await r.json();
    if (d.error) { setMsg({ type: "error", text: d.error }); setPlacing(false); }
    else { window.location.href = `/academic-marketplace/orders/${d.id}`; }
  };

  if (!service) return <LoadingOverlay text="Loading..." />;

  return (
    <ResearchLayout title="Place Order">
        <div className="mb-2">
          <a href={`/academic-marketplace/services/${serviceId}`} className="text-crimson-600 text-[13px] no-underline">← Back to Service</a>
        </div>

        {msg && (
          <Alert variant={msg.type === "error" ? "error" : "success"} style={{ marginBottom: 20 }}>
            {msg.text}
          </Alert>
        )}

        {/* Order Summary */}
        <Card padding="lg" className="mb-5">
          <H2 className="mb-4" style={{ fontSize: "1rem" }}>Order Summary</H2>
          <div className="text-[17px] font-semibold text-navy-700 mb-1">{service.title}</div>
          <Caption className="capitalize mb-4">
            {service.category?.replace(/_/g, " ")} — {pkg?.tier} Package
          </Caption>
          {pkg && (
            <div className="flex flex-col gap-2.5">
              {[
                { label: "Price", value: `$${pkg.price?.toFixed(2)}` },
                { label: "Platform Fee (15%)", value: `$${(pkg.price * 0.15)?.toFixed(2)}` },
                { label: "Delivery", value: `${pkg.delivery_days} days`, icon: Clock },
                { label: "Revisions", value: pkg.revisions },
              ].map(({ label, value, icon: Icon }) => (
                <div key={label} className="flex justify-between text-sm pb-2.5 border-b border-hairline">
                  <span className="text-slate-600 flex items-center gap-1.5">
                    {Icon && <Icon size={13} />} {label}
                  </span>
                  <span className="font-semibold text-navy-700">{value}</span>
                </div>
              ))}
              <div className="flex justify-between text-base">
                <span className="font-bold text-navy-700">Total</span>
                <span className="font-bold text-navy-700">${pkg.price?.toFixed(2)}</span>
              </div>
            </div>
          )}
        </Card>

        {/* Requirements */}
        <Card padding="lg" className="mb-5">
          <H2 className="mb-1.5" style={{ fontSize: "1rem" }}>Project Requirements</H2>
          <p className="text-slate-600 text-sm mb-3">
            {service.requirements_from_client || "Provide details to help the provider understand your needs."}
          </p>
          <Textarea
            value={form.requirements}
            onChange={e => setForm(f => ({ ...f, requirements: e.target.value }))}
            placeholder="Describe your project, data, research context, and specific needs..."
            rows={6}
          />
        </Card>

        {/* Trust notice */}
        <Card padding="md" className="mb-5">
          <div className="flex gap-2.5 items-start">
            <ShieldCheck size={18} className="text-emerald-600 mt-0.5" />
            <div>
              <div className="text-sm font-semibold text-navy-700 mb-1">Escrow Protection</div>
              <div className="text-[13px] text-slate-600 leading-normal">
                Your payment is held securely in escrow. Funds are released to the provider only after you approve the deliverables. You have {pkg?.revisions || 1} revision(s) included.
              </div>
            </div>
          </div>
        </Card>

        <Button onClick={place} disabled={placing} loading={placing} size="lg" className="w-full">
          {placing ? "Placing Order..." : `Confirm & Place Order — $${pkg?.price?.toFixed(2) || "0.00"}`}
        </Button>
        <Caption className="text-center mt-2.5 block">
          By placing this order you agree to the Synaptiq Academic Services Agreement.
        </Caption>
    </ResearchLayout>
  );
}

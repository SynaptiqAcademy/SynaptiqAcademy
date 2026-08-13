import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Star, Receipt } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Textarea, Checkbox, Button, Alert, LoadingOverlay } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = "/api/acad-market";
const DIMS = ["communication", "quality", "expertise", "timeliness", "value"];

export default function RatingSubmit() {
  const { id: orderId } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [form, setForm] = useState({ communication: 5, quality: 5, expertise: 5, timeliness: 5, value: 5, review_text: "", would_recommend: true });
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    fetchApi(`${API}/orders/${orderId}`).then(r => r.json()).then(d => setOrder(d.error ? null : d));
  }, [orderId]);

  const submit = async () => {
    setSubmitting(true);
    const r = await fetchApi(`${API}/ratings`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order_id: orderId, ...form }),
    });
    const d = await r.json();
    if (d.error) { setMsg({ type: "error", text: d.error }); setSubmitting(false); }
    else { navigate(`/academic-marketplace/orders/${orderId}`); }
  };

  if (!order) return <LoadingOverlay text="Loading..." />;

  return (
    <ResearchLayout title="Leave a Review" subtitle={order.service_title} sidebar={<RatingSubmitSidebar order={order} />}>

        {msg && (
          <Alert variant={msg.type === "error" ? "error" : "success"} style={{ marginBottom: 16 }}>
            {msg.text}
          </Alert>
        )}

        <Card padding="xl">
          {DIMS.map(dim => (
            <div key={dim} className="mb-5">
              <label className="block text-sm font-semibold text-navy-700 mb-2 capitalize">{dim}</label>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map(s => (
                  <button key={s} onClick={() => setForm(f => ({ ...f, [dim]: s }))}
                    className="bg-transparent border-none cursor-pointer p-0">
                    <Star size={28} className="text-amber-500" fill={s <= form[dim] ? "#F59E0B" : "none"} />
                  </button>
                ))}
                <span className="text-sm text-slate-600 self-center ml-1">
                  {["", "Poor", "Fair", "Good", "Very Good", "Excellent"][form[dim]]}
                </span>
              </div>
            </div>
          ))}

          <Textarea
            label="Written Review"
            value={form.review_text}
            onChange={e => setForm(f => ({ ...f, review_text: e.target.value }))}
            placeholder="Share your experience working with this provider..."
            rows={5}
            wrapperClassName="mb-5"
          />

          <Checkbox
            id="recommend"
            checked={form.would_recommend}
            onChange={e => setForm(f => ({ ...f, would_recommend: e.target.checked }))}
            label="I would recommend this provider to other researchers"
            style={{ marginBottom: 24 }}
          />

          <Button onClick={submit} disabled={submitting} loading={submitting} size="lg" className="w-full">
            {submitting ? "Submitting..." : "Submit Review"}
          </Button>
        </Card>
    </ResearchLayout>
  );
}

// ── Right rail — order being reviewed, already loaded above ────────────────────
function RatingSubmitSidebar({ order }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Receipt size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Order Summary</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "#94A3B8" }}>Package</span>
            <span style={{ color: "#374151", fontWeight: 600, textTransform: "capitalize" }}>{order.package_tier}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "#94A3B8" }}>Price</span>
            <span style={{ color: "#374151", fontWeight: 600 }}>${order.price?.toFixed(2)}</span>
          </div>
          {order.completed_at && (
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
              <span style={{ color: "#94A3B8" }}>Completed</span>
              <span style={{ color: "#374151", fontWeight: 600 }}>{new Date(order.completed_at).toLocaleDateString()}</span>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

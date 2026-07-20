import React, { useState, useEffect } from "react";
import { Star, ShieldCheck, Clock, CheckCircle } from "lucide-react";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Button, NavTabs, H1, H3, Caption, LoadingOverlay, ErrorState } from "@/components/ds";

const API = "/api/acad-market";

export default function ServiceDetail() {
  const id = window.location.pathname.split("/").pop();
  const [service, setService] = useState(null);
  const [ratings, setRatings] = useState([]);
  const [quality, setQuality] = useState(null);
  const [selectedPkg, setSelectedPkg] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/services/${id}`).then(r => r.json()),
      fetch(`${API}/ratings/services/${id}`).then(r => r.json()),
      fetch(`${API}/services/${id}/quality`).then(r => r.json()),
    ]).then(([svc, rat, q]) => {
      setService(svc);
      setRatings(rat.results || []);
      setQuality(q);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [id]);

  if (loading) return <LoadingOverlay text="Loading..." />;
  if (!service || service.error) return <ErrorState type="not_found" message="Service not found." />;

  const pkg = service.packages?.[selectedPkg] || {};

  return (
    <ResearchLayout
      sidebar={
        <div className="p-5">
          {service.packages?.length > 0 && (
            <>
              <NavTabs
                variant="segment"
                tabs={service.packages.map((p, i) => ({ id: String(i), label: p.tier ? p.tier[0].toUpperCase() + p.tier.slice(1) : p.tier }))}
                active={String(selectedPkg)}
                onChange={idx => setSelectedPkg(Number(idx))}
                className="mb-5"
              />

              <div className="text-[28px] font-bold text-navy-700 mb-1">
                ${pkg.price?.toFixed(2)}
              </div>
              <Caption className="mb-4">{pkg.description}</Caption>

              <div className="flex flex-col gap-2 mb-5">
                <div className="flex justify-between text-[13px]">
                  <span className="flex items-center gap-1.5 text-slate-600">
                    <Clock size={13} /> Delivery
                  </span>
                  <span className="text-navy-700 font-medium">{pkg.delivery_days} days</span>
                </div>
                <div className="flex justify-between text-[13px]">
                  <span className="text-slate-600">Revisions</span>
                  <span className="text-navy-700 font-medium">{pkg.revisions}</span>
                </div>
              </div>
            </>
          )}

          <Button as="a" href={`/academic-marketplace/order/${id}?pkg=${service.packages?.[selectedPkg]?.tier || "basic"}`} size="lg" className="w-full mb-3">
            Place Order
          </Button>
          <Button as="a" href={`/academic-marketplace/providers/${service.provider_user_id}`} variant="link" className="w-full justify-center" style={{ color: "#8A1538" }}>
            View Provider Profile
          </Button>

          {quality?.reasons?.length > 0 && (
            <div className="mt-5 pt-5 border-t border-hairline">
              <div className="text-[13px] font-semibold text-navy-700 mb-2">Quality Indicators</div>
              {quality.reasons.map((r, i) => (
                <div key={i} className="flex items-center gap-1.5 mb-1">
                  <CheckCircle size={12} className="text-emerald-600" />
                  <span className="text-xs text-slate-600">{r}</span>
                </div>
              ))}
            </div>
          )}

          <div className="mt-4 p-3 bg-[#F4F6FA] rounded-md">
            <div className="flex gap-1.5 items-start">
              <ShieldCheck size={14} className="text-emerald-600 mt-0.5" />
              <span className="text-xs text-slate-600 leading-normal">
                Escrow-protected. Funds released only after your approval.
              </span>
            </div>
          </div>
        </div>
      }
    >
      <div>
          <Card padding="xl" className="mb-5">
            <div className="text-xs text-crimson-600 font-semibold uppercase mb-2">
              {service.category?.replace(/_/g, " ")}
            </div>
            <H1 as="h1" style={{ fontSize: "1.5rem" }} className="mb-3">{service.title}</H1>
            <div className="flex items-center gap-4 mb-5">
              <div className="flex items-center gap-1">
                <Star size={15} className="text-amber-500" fill={service.average_rating > 0 ? "#F59E0B" : "none"} />
                <span className="font-semibold text-navy-700">{service.average_rating?.toFixed(1) || "New"}</span>
                <Caption>({service.rating_count} reviews)</Caption>
              </div>
              <Caption>{service.order_count} orders</Caption>
              {quality && (
                <Badge variant="success">
                  Quality: {quality.quality_label}
                </Badge>
              )}
            </div>
            <p className="text-slate-600 leading-relaxed mb-5">{service.description}</p>

            {service.methodology && (
              <div className="mb-5">
                <H3 className="mb-2" style={{ fontSize: "0.9375rem" }}>Methodology</H3>
                <p className="text-slate-600 leading-normal">{service.methodology}</p>
              </div>
            )}

            {service.deliverables?.length > 0 && (
              <div className="mb-5">
                <H3 className="mb-2" style={{ fontSize: "0.9375rem" }}>What You'll Receive</H3>
                {service.deliverables.map((d, i) => (
                  <div key={i} className="flex items-center gap-2 mb-1.5">
                    <CheckCircle size={14} className="text-emerald-600" />
                    <span className="text-sm text-navy-700">{d}</span>
                  </div>
                ))}
              </div>
            )}

            {service.faqs?.length > 0 && (
              <div>
                <H3 className="mb-3" style={{ fontSize: "0.9375rem" }}>FAQs</H3>
                {service.faqs.map((faq, i) => (
                  <div key={i} className={`mb-3 pb-3 ${i < service.faqs.length - 1 ? "border-b border-hairline" : ""}`}>
                    <div className="font-semibold text-navy-700 text-sm mb-1">{faq.question}</div>
                    <div className="text-slate-600 text-sm">{faq.answer}</div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Reviews */}
          {ratings.length > 0 && (
            <Card padding="lg">
              <H3 className="mb-4">Reviews</H3>
              {ratings.map((r, i) => (
                <div key={i} className={`mb-4 pb-4 ${i < ratings.length - 1 ? "border-b border-hairline" : ""}`}>
                  <div className="flex items-center gap-2 mb-1.5">
                    <div className="flex gap-0.5">
                      {[1,2,3,4,5].map(s => <Star key={s} size={12} className="text-amber-500" fill={s <= r.overall ? "#F59E0B" : "none"} />)}
                    </div>
                    <span className="text-[13px] font-semibold text-navy-700">
                      {r.buyer_name || "Verified Buyer"}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed">{r.review_text}</p>
                </div>
              ))}
            </Card>
          )}
      </div>
    </ResearchLayout>
  );
}

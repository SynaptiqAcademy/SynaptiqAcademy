/* eslint-disable */
import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../../components/layout/MarketingLayout";
import { ArrowRight, BookOpen } from "lucide-react";

const NAVY  = "#0F2847";
const LIGHT = "#f8fafc";
const BORDER= "#e8edf3";

/* ─── Page ─────────────────────────────────────────────────────────────────── */
// Synaptiq does not yet have real, permissioned customer stories to publish.
// This page intentionally shows an honest early-stage state rather than
// fabricated case studies — see the Phase 9A commercial-experience audit for
// why the previous version of this page was removed.
export default function CustomerStories() {
  useEffect(() => {
    document.title = "Customer Stories — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);

  return (
    <MarketingLayout>
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, paddingTop: 72, paddingBottom: 88 }}>
        <div className="max-w-[820px] mx-auto px-6 lg:px-10 text-center">
          <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 16 }}>Resources</div>
          <h1 style={{ fontSize: "clamp(2.2rem, 5vw, 3.4rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.1, marginBottom: 20 }}>
            Customer stories, coming as they happen.
          </h1>
          <p style={{ fontSize: "1.02rem", color: "#475569", lineHeight: 1.8, maxWidth: 620, margin: "0 auto 12px" }}>
            Synaptiq is an early-stage platform. We don't have permissioned customer
            stories to share yet, so rather than publish invented ones, we're leaving
            this page honest until we do.
          </p>
          <p style={{ fontSize: "0.88rem", color: "#94a3b8", lineHeight: 1.7, maxWidth: 560, margin: "0 auto 40px" }}>
            If you're using Synaptiq and would be open to sharing how, we'd welcome
            hearing from you.
          </p>
          <div className="flex justify-center gap-4 flex-wrap">
            <Link to="/register" style={{ background: NAVY, color: "#fff", padding: "13px 28px", borderRadius: 9, fontWeight: 700, fontSize: "0.9rem", display: "inline-flex", alignItems: "center", gap: 6, textDecoration: "none" }}>
              Start Free <ArrowRight size={14} strokeWidth={2.5} />
            </Link>
            <Link to="/contact" style={{ border: `1px solid ${BORDER}`, color: "#0a0f1a", padding: "12px 24px", borderRadius: 9, fontWeight: 600, fontSize: "0.9rem", textDecoration: "none" }}>
              Talk to us
            </Link>
          </div>
        </div>
      </section>

      <section style={{ background: LIGHT }}>
        <div className="max-w-[820px] mx-auto px-6 lg:px-10 py-16 text-center">
          <BookOpen size={22} strokeWidth={1.5} style={{ color: "#94a3b8", margin: "0 auto 16px" }} />
          <p style={{ fontSize: "0.88rem", color: "#64748b", lineHeight: 1.75, maxWidth: 520, margin: "0 auto" }}>
            In the meantime, the <Link to="/product" style={{ color: NAVY, fontWeight: 700 }}>Product</Link> and{" "}
            <Link to="/for-institutions" style={{ color: NAVY, fontWeight: 700 }}>Institutions</Link> pages describe
            what Synaptiq actually does today.
          </p>
        </div>
      </section>
    </MarketingLayout>
  );
}

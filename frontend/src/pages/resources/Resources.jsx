/* eslint-disable */
import React from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../../components/layout/MarketingLayout";
import { ArrowRight, Zap, Users, BookOpen } from "lucide-react";

const NAVY  = "#0F2847";
const BORDER= "#e8edf3";
const LIGHT = "#f8fafc";

const SECTIONS = [
  {
    icon: Zap,
    eyebrow: "Product Updates",
    title: "What's New",
    desc: "The latest releases, improvements and AI capabilities across the entire Synaptiq platform.",
    cta: "View all releases",
    href: "/resources/whats-new",
    color: "#1d4ed8",
    badge: "Updated weekly",
  },
  {
    icon: Users,
    eyebrow: "Case Studies",
    title: "Customer Stories",
    desc: "How universities, research institutes and funding agencies worldwide use Synaptiq to transform their research operations.",
    cta: "Browse stories",
    href: "/resources/customer-stories",
    color: NAVY,
    badge: "12+ case studies",
  },
  {
    icon: BookOpen,
    eyebrow: "Editorial",
    title: "Blog",
    desc: "Deep research, practical guides and expert thinking on AI, academic publishing, open science and the future of research.",
    cta: "Read articles",
    href: "/resources/blog",
    color: "#059669",
    badge: "40 articles",
  },
];

export default function Resources() {
  return (
    <MarketingLayout>
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, paddingTop: 80, paddingBottom: 80 }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 16 }}>Resources</div>
          <h1 style={{ fontSize: "clamp(2.4rem, 5vw, 4rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.05, marginBottom: 16 }}>
            Everything you need to know<br className="hidden lg:block" /> about Synaptiq.
          </h1>
          <p style={{ fontSize: "1rem", color: "#64748b", lineHeight: 1.75, maxWidth: 520, marginBottom: 56 }}>
            Product updates, customer stories and editorial content from the world's leading academic collaboration platform.
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            {SECTIONS.map(({ icon: Icon, eyebrow, title, desc, cta, href, color, badge }) => (
              <Link key={href} to={href} style={{ textDecoration: "none", display: "block" }}>
                <div style={{
                  background: LIGHT, border: `1px solid ${BORDER}`, borderRadius: 18, padding: "32px 30px",
                  height: "100%", display: "flex", flexDirection: "column",
                  transition: "box-shadow 200ms, transform 200ms, border-color 200ms",
                }}
                  onMouseEnter={e => { const d = e.currentTarget; d.style.boxShadow = "0 12px 48px rgba(15,40,71,0.1)"; d.style.transform = "translateY(-3px)"; d.style.borderColor = color; }}
                  onMouseLeave={e => { const d = e.currentTarget; d.style.boxShadow = "none"; d.style.transform = "none"; d.style.borderColor = BORDER; }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
                    <div style={{ width: 48, height: 48, borderRadius: 12, background: `${color}12`, border: `1px solid ${color}22`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <Icon size={22} strokeWidth={1.5} style={{ color }} />
                    </div>
                    <span style={{ fontSize: "0.62rem", fontWeight: 700, color, background: `${color}10`, border: `1px solid ${color}20`, padding: "3px 10px", borderRadius: 20 }}>{badge}</span>
                  </div>
                  <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 10 }}>{eyebrow}</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 900, letterSpacing: "-0.025em", color: "#0a0f1a", marginBottom: 12 }}>{title}</div>
                  <p style={{ fontSize: "0.83rem", color: "#64748b", lineHeight: 1.7, marginBottom: 24, flex: 1 }}>{desc}</p>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem", fontWeight: 700, color }}>
                    {cta} <ArrowRight size={13} strokeWidth={2.5} />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}

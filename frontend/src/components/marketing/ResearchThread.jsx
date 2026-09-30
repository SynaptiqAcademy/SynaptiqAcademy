import React, { useRef, useEffect } from "react";
import { HelpCircle, Compass, Users, Handshake, FolderOpen, Award } from "lucide-react";

const NAVY = "#0F2847";
const BORDER = "#e8edf3";

const STAGES = [
  { icon: HelpCircle, label: "Question", body: "You describe what you're researching — in your own words, no taxonomy to learn first." },
  { icon: Compass,    label: "Expertise", body: "Synaptiq structures it into the themes, disciplines and methods it may need." },
  { icon: Users,      label: "People", body: "Real, eligible Synaptiq members whose profile matches that structure — never invented." },
  { icon: Handshake,  label: "Collaboration", body: "You send a collaboration request. Nothing is contacted on your behalf." },
  { icon: FolderOpen, label: "Project", body: "An accepted collaboration becomes a shared workspace — tasks, files, discussion." },
  { icon: Award,      label: "Output", body: "Work continues into a manuscript, grant application, or your research record." },
];

function useReveal(threshold = 0.15) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") {
      el.classList.add("rt-in");
      return;
    }
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          el.classList.add("rt-in");
          obs.disconnect();
        }
      },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return ref;
}

function StageRow({ stage, index, isLast }) {
  const ref = useReveal();
  const Icon = stage.icon;
  return (
    <div ref={ref} className="rt-stage" style={{ display: "flex", gap: 24, opacity: 0, transform: "translateY(10px)", transition: "opacity 500ms ease, transform 500ms ease" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
        <div
          style={{
            width: 40, height: 40, borderRadius: "50%",
            border: `1.5px solid ${NAVY}`, background: "#fff",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <Icon size={16} strokeWidth={1.5} style={{ color: NAVY }} />
        </div>
        {!isLast && (
          <div style={{ width: 1, flex: 1, minHeight: 40, background: "#cbd5e1", marginTop: 4 }} />
        )}
      </div>
      <div style={{ paddingBottom: isLast ? 0 : 40, paddingTop: 6 }}>
        <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 4 }}>
          {String(index + 1).padStart(2, "0")}
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: "1.25rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 6 }}>
          {stage.label}
        </div>
        <p style={{ fontSize: "0.88rem", color: "#64748b", lineHeight: 1.7, maxWidth: 420, margin: 0 }}>
          {stage.body}
        </p>
      </div>
    </div>
  );
}

/**
 * The Research Thread — a restrained, editorial visual spine connecting the
 * six stages a research question moves through on Synaptiq. Replaces the
 * earlier generic 8-step "workflow timeline" (icon circles + thin
 * horizontal connector, closer to a startup roadmap component than the
 * editorial/scientific feel the product wants).
 *
 * Deliberately continues straight from the ResearchPreviewDemo above it:
 * that component already IS a live Question → Expertise demonstration,
 * so this thread picks up narratively from "Expertise" onward rather than
 * repeating it.
 */
export default function ResearchThread() {
  return (
    <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, padding: "88px 0" }}>
      <style>{`.rt-in { opacity: 1 !important; transform: none !important; }`}</style>
      <div className="max-w-[720px] mx-auto px-6 lg:px-10">
        <div style={{ textAlign: "center", marginBottom: 56 }}>
          <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 12 }}>
            How it works
          </div>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.6rem, 3vw, 2.2rem)", fontWeight: 700, color: "#0a0f1a", lineHeight: 1.2 }}>
            From a question to real work.
          </h2>
        </div>

        <div>
          {STAGES.map((stage, i) => (
            <StageRow key={stage.label} stage={stage} index={i} isLast={i === STAGES.length - 1} />
          ))}
        </div>
      </div>
    </section>
  );
}

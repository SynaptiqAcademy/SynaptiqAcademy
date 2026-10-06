import React, { useEffect, useState } from "react";
import MarketingLayout from "../components/layout/MarketingLayout";
import api from "../lib/api";
import { setPageSeo } from "../lib/seo";
import Hero from "../components/landing/Hero";
import ResearchQuestion from "../components/landing/ResearchQuestion";
import Thread from "../components/landing/Thread";
import Passport from "../components/landing/Passport";
import { WhySynaptiq, FinalCTA } from "../components/landing/Sections";
import "../components/landing/landing.css";


function scrollToQuestion(e) {
  e?.preventDefault?.();
  const el = document.getElementById("research-question");
  if (!el) return;
  const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  setTimeout(() => document.getElementById("lp-q-input")?.focus({ preventScroll: true }), reduce ? 0 : 450);
}

export default function Landing() {
  const [preview, setPreview] = useState(null);
  const [question, setQuestion] = useState("");
  const [registrationOpen, setRegistrationOpen] = useState(null);

  useEffect(() => setPageSeo({
    title: "Synaptiq — Research starts with a question",
    description: "Describe a research question and see the expertise it needs. Synaptiq helps researchers find the people who bring it, and keeps the collaboration, the project and the writing together.",
    path: "/",
  }), []);

  useEffect(() => {
    api.get("/auth/registration-status")
      .then((r) => setRegistrationOpen(r.data?.open !== false))
      .catch(() => setRegistrationOpen(null));
  }, []);

  return (
    <MarketingLayout>
      <div className="lp">
        <Hero registrationOpen={registrationOpen} onSeeHow={scrollToQuestion} />
        <ResearchQuestion onResult={(data, q) => { setPreview(data); setQuestion(q); }} />
        <Thread question={question} preview={preview} />
        <Passport />
        <WhySynaptiq />
        <FinalCTA registrationOpen={registrationOpen} />
      </div>
    </MarketingLayout>
  );
}

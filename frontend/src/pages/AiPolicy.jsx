import React from "react";
import { setPageSeo } from "../lib/seo";
import { Link } from "react-router-dom";
import { LegalLayout, Section } from "./legal/LegalLayout";
import { ACCENT } from "@/lib/tokens";
import { CreditCostNumber } from "@/components/billing/CreditCost";

const SECTIONS = [
  { id: "overview",       label: "1. Overview" },
  { id: "providers",      label: "2. AI Providers" },
  { id: "features",       label: "3. AI Features" },
  { id: "data-handling",  label: "4. Your Data & AI" },
  { id: "no-training",    label: "5. No Training on Your Data" },
  { id: "limitations",    label: "6. Limitations" },
  { id: "academic-use",   label: "7. Academic Integrity" },
  { id: "credits",        label: "8. Credit Consumption" },
  { id: "local-ai",       label: "9. Self-hosted AI" },
  { id: "moderation",     label: "10. Content Moderation" },
  { id: "changes",        label: "11. Policy Changes" },
];

const AI_FEATURES = [
  {
    name: "AI Research Assistant",
    description: "Conversational assistant that answers research questions, suggests citations, and helps plan research activities. Context sent: your query, optional project context, conversation history.",
    credits: { op: "AI_ASSISTANT_SIMPLE", unit: "per query" },
  },
  {
    name: "AI Manuscript Review",
    description: "Provides structured feedback on manuscript drafts: argument clarity, structure, methods critique, grammar, citation consistency, and journal fit suggestions. Context sent: manuscript text (or selected sections), target journal if specified.",
    credits: { op: "FULL_MANUSCRIPT_REVIEW", unit: "per review" },
  },
  {
    name: "AI Literature Review",
    description: "Synthesises a body of literature, identifies themes, gaps, and contradictions, and generates structured review content. Context sent: selected papers, research topic, review type.",
    credits: { op: "LITERATURE_SYNTHESIS", unit: "per review" },
  },
  {
    name: "AI Statistical Review",
    description: "Reviews statistical methodology, tests appropriateness of methods, identifies common errors, and provides suggestions for reporting. Context sent: methods section or full manuscript.",
    credits: { op: "MANUSCRIPT_SECTION_REVIEW", unit: "per review" },
  },
  {
    name: "AI Research Gap Finder",
    description: "Analyses a research area and identifies under-explored gaps, open questions, and future directions. Context sent: research topic, provided or retrieved literature.",
    credits: { op: "LITERATURE_SYNTHESIS", unit: "per analysis" },
  },
  {
    name: "AI Grant Assistant",
    description: "Helps draft and improve grant application sections: aims, significance, innovation, approach. Context sent: grant application text, project description.",
    credits: "Variable by section",
  },
  {
    name: "AI Abstract Generator",
    description: "Generates a structured abstract from a manuscript or project description. Context sent: manuscript text or project description, target journal requirements.",
    credits: { op: "ABSTRACT_ANALYSIS", unit: "per abstract" },
  },
  {
    name: "AI Writing Assistance (Rewriting)",
    description: "Improves prose clarity, reduces passive voice, adjusts academic register. Context sent: selected text passage.",
    credits: { op: "QUICK_ACADEMIC_REWRITE", unit: "per request" },
  },
  {
    name: "AI Collaboration Intelligence",
    description: "Analyses project team composition and suggests complementary expertise. Context sent: project description, collaborator profiles (anonymised names).",
    credits: { op: "LITERATURE_SYNTHESIS", unit: "per run" },
  },
];

export default function AiPolicy() {
  React.useEffect(() => setPageSeo({ title: "AI Usage Policy | Synaptiq", description: "How AI features on Synaptiq work, which providers process requests, and the limits of AI output.", path: "/ai-policy" }), []);
  return (
    <LegalLayout
      eyebrow="Legal"
      title="AI Usage Policy"
      lastUpdated="6 October 2026"
      sections={SECTIONS}
    >
      <Section id="overview" title="1. Overview">
        <p>SYNAPTIQ integrates large language model (LLM) AI technology throughout the Platform to assist researchers with writing, analysis, discovery, and collaboration. This policy describes how those AI features work, which AI providers we use, how your data is handled when AI features are used, and the limitations of AI-generated outputs.</p>
        <p className="mt-3">All AI features on SYNAPTIQ are <strong>assistive tools</strong>. They are not authoritative sources of fact, scientific knowledge, or citation records. You remain solely responsible for reviewing, verifying, and appropriately attributing any content produced with AI assistance before submitting it for publication, institutional assessment, grant review, or any other formal purpose.</p>
      </Section>

      <Section id="providers" title="2. AI Providers">
        <p>SYNAPTIQ uses the following external AI provider(s):</p>

        <div className="mt-4 space-y-3">
          <div style={{ padding: "16px 18px", border: "1px solid #e2e8f0", borderRadius: 8 }}>
            <div style={{ fontWeight: 700, fontSize: "0.92rem", color: "#0f172a", marginBottom: 4 }}>
              Anthropic &mdash; Claude (primary)
            </div>
            <p style={{ fontSize: "0.84rem", color: "#475569", lineHeight: 1.65, margin: 0 }}>
              Anthropic&rsquo;s Claude models (currently <code>claude-sonnet-4-6</code>) power the majority of AI features on the Platform. Anthropic is a US-based AI safety company. Requests are sent over HTTPS under Anthropic&rsquo;s commercial terms for API customers, under which Anthropic does not train its models on API inputs or outputs by default. Anthropic keeps API data for a limited period under its own retention policy.
            </p>
          </div>
          <div style={{ padding: "16px 18px", border: "1px solid #e2e8f0", borderRadius: 8 }}>
            <div style={{ fontWeight: 700, fontSize: "0.92rem", color: "#0f172a", marginBottom: 4 }}>
              OpenAI &mdash; GPT models (fallback) and embeddings
            </div>
            <p style={{ fontSize: "0.84rem", color: "#475569", lineHeight: 1.65, margin: 0 }}>
              If Claude is unavailable, a request may be answered by an OpenAI GPT model instead. OpenAI also turns documents you add to your knowledge base into embeddings (numerical representations used for search). OpenAI is a US-based AI company. Under its API terms, OpenAI does not train its models on API data by default, and keeps it for a limited period under its own retention policy.
            </p>
          </div>
        </div>

        <p className="mt-4">All requests to AI providers are made server-side by the SYNAPTIQ backend, not directly from your browser. Your raw request is processed by SYNAPTIQ&rsquo;s backend before being forwarded to the AI provider with appropriate context extraction and minimisation.</p>
        <p className="mt-3">AI providers are located in the United States. How these transfers are safeguarded is explained in the <Link to="/privacy#transfers" className="editorial-link">Privacy Policy</Link>.</p>
      </Section>

      <Section id="features" title="3. AI Features on SYNAPTIQ">
        <p>The following AI-powered features are available on the Platform (subject to your plan&rsquo;s credit allowance):</p>
        <div className="mt-4 space-y-3">
          {AI_FEATURES.map((f) => (
            <div key={f.name} style={{ padding: "14px 16px", background: "#F7F8FA", borderRadius: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4, flexWrap: "wrap", gap: 8 }}>
                <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "#0f172a" }}>{f.name}</span>
                <span style={{ fontSize: "0.75rem", fontFamily: "monospace", color: "#64748b", background: "#e2e8f0", borderRadius: 4, padding: "2px 7px" }}>{typeof f.credits === "string" ? f.credits : <><CreditCostNumber operation={f.credits.op} /> credits {f.credits.unit}</>}</span>
              </div>
              <p style={{ fontSize: "0.83rem", color: "#475569", lineHeight: 1.6, margin: 0 }}>{f.description}</p>
            </div>
          ))}
        </div>
        <p className="mt-4">This feature list reflects the current implementation. New AI features may be added over time and will be disclosed in an updated version of this policy.</p>
      </Section>

      <Section id="data-handling" title="4. Your Data & AI Processing">
        <p><strong>Minimum necessary context.</strong> When an AI feature is triggered, our backend extracts only the context relevant to that specific feature and forwards it to the AI provider. We do not send your full profile, billing information, unrelated projects, or collaboration history to the AI provider as part of a feature request.</p>
        <p className="mt-3">Examples of context transmitted per feature:</p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li><strong>Research Assistant:</strong> your query text and optionally selected project context (project description, uploaded document excerpts).</li>
          <li><strong>Manuscript Review:</strong> manuscript text (or selected sections) and target journal if specified.</li>
          <li><strong>Literature Review:</strong> selected paper metadata and abstracts, research topic.</li>
          <li><strong>Abstract Generator:</strong> manuscript text or project description.</li>
          <li><strong>Rewriting:</strong> the text passage you have selected.</li>
        </ul>
        <p className="mt-3"><strong>No cross-user data mixing.</strong> Each AI request is scoped to your user context. Your data is never used to inform AI responses to other users&rsquo; requests.</p>
        <p className="mt-3"><strong>Prompt caching.</strong> Some requests use the provider&rsquo;s prompt caching, which keeps parts of a request for a few minutes so repeated requests are faster.</p>
      </Section>

      <Section id="no-training" title="5. No Training on Your Data">
        <p>SYNAPTIQ does not use your manuscripts, research content, or AI feature outputs to train AI models &mdash; neither our own nor those of our AI providers.</p>
        <p className="mt-3">Under their API terms, Anthropic and OpenAI do not train their models on data sent through their APIs by default. This covers your queries, document text and the AI&rsquo;s responses.</p>
        <p className="mt-3">We may collect anonymised, aggregated information about how AI features are used (e.g., feature usage frequency, average response quality ratings) for the purpose of improving the platform&rsquo;s AI integration, but this does not include your content.</p>
      </Section>

      <Section id="limitations" title="6. Limitations of AI-Generated Content">
        <p>You must understand the following limitations before relying on AI-generated content:</p>

        <div className="mt-4 space-y-3">
          {[
            {
              title: "Hallucinations",
              body: "AI models can generate text that sounds plausible but is factually incorrect. This includes inventing citations, author names, journal titles, page numbers, DOIs, and publication years that do not exist. Always verify all citations against primary sources before including them in submitted work.",
            },
            {
              title: "Knowledge cutoff",
              body: "AI models have a training data cutoff date and do not have real-time access to academic databases, preprint servers, or current literature. They cannot reliably identify the most recent publications in a field.",
            },
            {
              title: "Bias",
              body: "AI models reflect biases present in their training data, which predominantly consists of English-language, Western-centric academic and web content. Outputs may underrepresent non-Western, non-English, or minority research perspectives.",
            },
            {
              title: "Not expert advice",
              body: "AI outputs are not a substitute for review by qualified experts. Statistical methodology suggestions, medical information, legal analysis, and ethical assessments produced by AI tools must be verified by the appropriate human expert before use.",
            },
            {
              title: "Inconsistency",
              body: "AI models are probabilistic. The same prompt may produce different outputs on different occasions. Treat all AI-generated text as a draft starting point, not a definitive answer.",
            },
            {
              title: "Academic standards",
              body: "AI-generated content may not meet the methodological standards, citation styles, or academic register required by specific journals, conferences, or institutions. You are responsible for adapting AI-assisted content to the requirements of your target venue.",
            },
          ].map((item) => (
            <div key={item.title} style={{ padding: "14px 16px", borderLeft: "3px solid #0F2847", background: "#eef2f8", borderRadius: "0 6px 6px 0" }}>
              <div style={{ fontWeight: 600, fontSize: "0.88rem", color: "#0f172a", marginBottom: 4 }}>{item.title}</div>
              <p style={{ fontSize: "0.83rem", color: "#475569", lineHeight: 1.6, margin: 0 }}>{item.body}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section id="academic-use" title="7. Academic Integrity & Disclosure">
        <p>Responsible use of AI tools in academic research and publishing is an evolving area. Different institutions, journals, and funding bodies have different policies. You are responsible for understanding and complying with the AI disclosure policies of your institution, target journal or conference, and funding agency.</p>

        <p className="mt-4"><strong>Common disclosure requirements you should check:</strong></p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li>Journal AI authorship and acknowledgment policies (e.g., Nature, Science, Elsevier, Springer, PLOS).</li>
          <li>Your institution&rsquo;s AI use policy for student and research output.</li>
          <li>Funding body requirements (e.g., Horizon Europe, NIH, Wellcome Trust).</li>
          <li>Conference submission guidelines (many explicitly require AI disclosure).</li>
        </ul>

        <p className="mt-4"><strong>Prohibited uses on SYNAPTIQ:</strong></p>
        <ul className="mt-2 list-disc ml-6 space-y-1 text-sm">
          <li>Generating fabricated data, results, or methodology descriptions and submitting them as genuine research.</li>
          <li>Using AI to generate or substantially assist with work that is then submitted to a venue without required disclosure.</li>
          <li>Using AI-generated citations without verification, knowing they may not exist.</li>
          <li>Using AI to impersonate another researcher or create fraudulent academic outputs.</li>
        </ul>
        <p className="mt-3">Violations may result in suspension under Section 7 of the <Link to="/terms" className="editorial-link">Terms of Service</Link>.</p>

        <p className="mt-4"><strong>Our recommendation.</strong> Treat AI-assisted content as a drafting tool. Your name, as the submitting researcher, carries accountability for the accuracy, integrity, and originality of submitted work. AI assistance does not transfer that accountability.</p>
      </Section>

      <Section id="credits" title="8. Credit Consumption">
        <p>AI features consume AI Credits from your plan allowance or Credit Pack balance. Credits are reserved when a request is submitted and refunded automatically if the request fails because of a system error.</p>
        <p className="mt-3">If an AI request fails due to a system error on our side, credits are typically refunded automatically. If you believe credits were consumed incorrectly, contact <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a>.</p>
        <p className="mt-3">Credit costs vary by feature and are indicated in the platform UI before you confirm a feature use. The authoritative credit cost schedule is published on the <Link to="/pricing" className="editorial-link">Pricing page</Link>. Credit costs may change as AI model pricing changes; any such changes will be communicated in advance.</p>
      </Section>

      <Section id="local-ai" title="9. Self-hosted AI">
        <p>Synaptiq does not currently offer self-hosted deployments or AI models running on your own infrastructure. All AI features use the providers described in section 2.</p>
      </Section>

      <Section id="moderation" title="10. Content Moderation">
        <p>AI providers apply their own content moderation to API requests. Requests that violate Anthropic&rsquo;s or OpenAI&rsquo;s usage policies may be refused by the underlying model.</p>
        <p className="mt-3">SYNAPTIQ applies server-side validation to AI requests to prevent clearly malicious use of AI features (e.g., prompt injection attacks, attempts to extract system prompts, content intended to cause harm). These safeguards do not restrict legitimate academic use.</p>
        <p className="mt-3">If you believe an AI feature is refusing legitimate academic content in error, contact <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a>.</p>
      </Section>

      <Section id="changes" title="11. Policy Changes">
        <p>AI technology and provider relationships evolve quickly. We will update this policy to reflect new features, provider changes, and regulatory developments. Material changes (such as a change in primary AI provider) will be communicated by email or in-app notification. The &ldquo;last updated&rdquo; date at the top of this page reflects the current version.</p>
        <p className="mt-3">Questions about our AI features or data handling? Email <a href="mailto:contact@synaptiq.academy" className="editorial-link">contact@synaptiq.academy</a>.</p>
      </Section>
    </LegalLayout>
  );
}

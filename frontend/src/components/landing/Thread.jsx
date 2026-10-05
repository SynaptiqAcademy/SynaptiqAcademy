import React from "react";

/**
 * How the work moves: six stations, one line each, followed by three
 * illustrative product fragments (find → invite → work). The fragments use
 * the product's own wording and states; no real member is shown. When the
 * visitor has tried the preview, their question and areas appear at the
 * first two stations.
 */
const STOPS = [
  { key: "Q",  name: "Question",      line: "The problem you're actually working on." },
  { key: "E",  name: "Expertise",     line: "The fields, methods and perspectives it calls for." },
  { key: "P",  name: "People",        line: "Members whose work fits, with the reason why.", decide: true },
  { key: "C",  name: "Collaboration", line: "You invite. They accept or decline.", decide: true },
  { key: "Pr", name: "Project",       line: "The team moves into a shared workspace." },
  { key: "O",  name: "Output",        line: "Manuscripts, grant applications, your research record." },
];

const FRAGMENTS = [
  {
    step: "Find",
    head: "Expert discovery",
    rows: [["A researcher in health services", "suggested"]],
    quote: "Profile lists Health Services Research · uses process mapping",
  },
  {
    step: "Invite",
    head: "Collaboration request",
    rows: [["Sent by you", "pending"], ["Recipient", "accepted"], ["Conversation", "opened"]],
  },
  {
    step: "Work",
    head: "Project workspace",
    rows: [["Map current patient flow", "in progress"], ["Staffing data request", "open"], ["Interim findings", "milestone"]],
  },
];

export default function Thread({ question, preview }) {
  const carry = {
    Q: question ? `“${question.length > 80 ? `${question.slice(0, 78)}…` : question}”` : null,
    E: preview?.themes?.length ? preview.themes.slice(0, 3).join(", ") : null,
  };
  return (
    <section id="thread" className="lp-section" aria-labelledby="lp-thread-title">
      <div className="lp-wrap">
        <div className="lp-index"><b>02</b> How the work moves</div>
        <h2 id="lp-thread-title" className="lp-h2">From a question to the people and the work around it.</h2>

        <div className="lp-thread">
          <ol>
            {STOPS.map((s, i) => (
              <li key={s.key} className={`lp-stop ${carry[s.key] ? "lp-stop--yours" : ""}`}>
                <div className="lp-stop-key">{String(i + 1).padStart(2, "0")}</div>
                <div className="lp-stop-dot" aria-hidden="true" />
                <h3>{s.name}</h3>
                <p>{s.line}</p>
                {s.decide && <span className="lp-decide">You decide</span>}
                {carry[s.key] && <div className="lp-carry">{carry[s.key]}</div>}
              </li>
            ))}
          </ol>
        </div>

        <div className="lp-proof" aria-label="Illustrative product views">
          {FRAGMENTS.map((f, i) => (
            <React.Fragment key={f.step}>
              {i > 0 && <div className="lp-proof-arrow" aria-hidden="true">→</div>}
              <div className="lp-proof-item">
                <div className="lp-proof-step">{f.step}</div>
                <div className="lp-frag">
                  <div className="lp-frag-head lp-mono"><span>{f.head}</span><span>illustrative</span></div>
                  {f.rows.map(([a, b]) => (
                    <div key={a} className="lp-frag-row"><span>{a}</span><span>{b}</span></div>
                  ))}
                  {f.quote && <p className="lp-small" style={{ marginTop: 8, color: "var(--ink-2)" }}>“{f.quote}”</p>}
                </div>
              </div>
            </React.Fragment>
          ))}
        </div>
      </div>
    </section>
  );
}

import React from "react";

/**
 * The Research Thread: one question carried through six stations. If the
 * visitor has tried the preview, their own question and the areas it
 * produced appear at the first two stations, so the thread is literally
 * theirs. Every "where" names a real product surface.
 */
const STOPS = [
  {
    key: "Q", name: "Question",
    does: "You write what you're working on, in your own words.",
    where: "Research Need",
  },
  {
    key: "E", name: "Expertise",
    does: "The question is read for the areas, methods and perspectives it calls for.",
    where: "Research Need · Expertise map",
  },
  {
    key: "P", name: "People",
    does: "Members whose Passports cover that expertise, with the reason each one appears.",
    where: "Expert discovery",
    decide: true,
  },
  {
    key: "C", name: "Collaboration",
    does: "You write the request. They accept or decline, and a conversation opens.",
    where: "Collaboration requests",
    decide: true,
  },
  {
    key: "Pr", name: "Project",
    does: "The team you've assembled becomes a project with a shared workspace: tasks, files, discussion.",
    where: "Team Builder · Workspaces",
  },
  {
    key: "O", name: "Output",
    does: "The work carries on into manuscripts, grant applications and your research record.",
    where: "Manuscripts · Grants · Publications",
  },
];

export default function Thread({ question, preview }) {
  const carry = {
    Q: question ? `“${question.length > 90 ? `${question.slice(0, 88)}…` : question}”` : null,
    E: preview?.themes?.length ? preview.themes.slice(0, 3).join(", ") : null,
  };
  return (
    <section id="thread" className="lp-section" aria-labelledby="lp-thread-title">
      <div className="lp-wrap">
        <div className="lp-index"><b>02</b> The thread</div>
        <h2 id="lp-thread-title" className="lp-h2">One question, carried all the way through.</h2>
        <p className="lp-lede">
          Most research tools hold one piece of this: a database for papers, a network
          for people, a chat app, a shared folder somewhere. Synaptiq keeps the stages
          connected, so each one starts from what the last one found.
        </p>

        <div className="lp-thread">
          <ol>
            {STOPS.map((s, i) => (
              <li key={s.key} className={`lp-stop ${carry[s.key] ? "lp-stop--yours" : ""}`}>
                <div className="lp-stop-key">{String(i + 1).padStart(2, "0")}</div>
                <div className="lp-stop-dot" aria-hidden="true" />
                <h3>{s.name}</h3>
                <p>{s.does}</p>
                <div className="lp-where lp-mono">{s.where}</div>
                {s.decide && <span className="lp-decide">You decide</span>}
                {carry[s.key] && <div className="lp-carry">{carry[s.key]}</div>}
              </li>
            ))}
          </ol>
        </div>

        <div className="lp-thread-note lp-small">
          <span>Stations 01–02 work in the preview above.</span>
          <span>Stations 03–06 are part of Pro.</span>
          <span>Nothing is sent to anyone without your action.</span>
        </div>
      </div>
    </section>
  );
}

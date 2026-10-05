import React from "react";

/**
 * Product proof as a sequence of "what happens next" questions. Fragments
 * reproduce the product's own wording and states (research_need/evidence.py
 * explanations, team_builder priorities and statuses, collaboration request
 * statuses). They are illustrative views — no real member is shown.
 */
const STEPS = [
  {
    q: "Why is this person on my list?",
    a: "Every suggested member comes with the reason they appear, built from their Passport: what their profile lists, the methods they use, what complementary expertise they bring.",
    frag: (
      <>
        <div className="lp-frag-head lp-mono"><span>Expert discovery</span><span>illustrative</span></div>
        <div className="lp-frag-row"><span>A researcher in health services</span><span>suggested</span></div>
        <p className="lp-small" style={{ marginTop: 10, color: "var(--ink-2)" }}>
          “Profile lists Health Services Research · uses process mapping · brings
          complementary Operations Research expertise.”
        </p>
      </>
    ),
  },
  {
    q: "Who decides whether we work together?",
    a: "You do, then they do. You write the request yourself; nothing goes out on your behalf. They accept or decline, and accepting opens a conversation between you.",
    frag: (
      <>
        <div className="lp-frag-head lp-mono"><span>Collaboration request</span><span>illustrative</span></div>
        <div className="lp-frag-row"><span>Sent by you</span><span>pending</span></div>
        <div className="lp-frag-row"><span>Reviewed by the recipient</span><span>accepted</span></div>
        <div className="lp-frag-row"><span>Conversation</span><span>opened</span></div>
      </>
    ),
  },
  {
    q: "What if the work needs more than two people?",
    a: "Team Builder turns the research need into roles, marks each one essential, useful or optional, and tracks who has accepted.",
    frag: (
      <>
        <div className="lp-frag-head lp-mono"><span>Team Builder</span><span>status: inviting</span></div>
        <div className="lp-frag-row"><span>Health services research</span><span>essential · accepted</span></div>
        <div className="lp-frag-row"><span>Operations research</span><span>essential · invited</span></div>
        <div className="lp-frag-row"><span>Workforce and staffing</span><span>useful · open</span></div>
      </>
    ),
  },
  {
    q: "Where does the work actually happen?",
    a: "Create a project from the team and it gets a shared workspace: tasks, milestones, files and discussion, with everyone's role kept from the team.",
    frag: (
      <>
        <div className="lp-frag-head lp-mono"><span>Project workspace</span><span>illustrative</span></div>
        <div className="lp-frag-row"><span>Map current patient flow</span><span>task · in progress</span></div>
        <div className="lp-frag-row"><span>Staffing data request</span><span>task · open</span></div>
        <div className="lp-frag-row"><span>Interim findings</span><span>milestone</span></div>
      </>
    ),
  },
];

export default function AfterMatch() {
  return (
    <section className="lp-section lp-section--quiet" aria-labelledby="lp-after-title">
      <div className="lp-wrap">
        <div className="lp-index"><b>03</b> After the match</div>
        <h2 id="lp-after-title" className="lp-h2">Finding someone is where the work starts.</h2>
        <p className="lp-lede">
          An answer from a model, a list of keywords, a profile page: in most tools
          that's where things stop. Here each step leads to the next one.
        </p>

        <div className="lp-steps">
          {STEPS.map((s) => (
            <div key={s.q} className="lp-step">
              <div>
                <h3 className="lp-step-q">{s.q}</h3>
                <p className="lp-step-a">{s.a}</p>
              </div>
              <div className="lp-frag" aria-label={`Illustrative product view: ${s.q}`}>{s.frag}</div>
            </div>
          ))}
        </div>

        <p className="lp-continues">
          From the workspace, the same project can carry on into a <em>manuscript</em> with
          versions and co-authors, a <em>grant application</em> with its team and budget,
          and the <em>publications</em> that end up on your research record.
        </p>
      </div>
    </section>
  );
}

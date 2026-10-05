import React from "react";

/**
 * Academic Passport as a compact ledger. Fields are real Passport fields;
 * the values are a specimen, not a real person. Each entry states whether
 * it is self-declared, connected or verified.
 */
const ROWS = [
  ["Research areas", "Health services research; operations research", "self"],
  ["Methods", "Process mapping; discrete-event simulation", "self"],
  ["Professional expertise", "Hospital operations", "self"],
  ["ORCID · research record", "Publications imported from ORCID", "connected"],
  ["Open to", "Co-authorship, peer review, grant teams", "self"],
];
const STATE = {
  self: ["Self-declared", "lp-state--self"],
  connected: ["Connected", "lp-state--connected"],
  verified: ["Verified", "lp-state--verified"],
};

export default function Passport() {
  return (
    <section className="lp-section lp-section--quiet" aria-labelledby="lp-passport-title">
      <div className="lp-wrap lp-passport-grid">
        <div>
          <div className="lp-index"><b>03</b> Research identity</div>
          <h2 id="lp-passport-title" className="lp-h2">Academic Passport</h2>
          <p className="lp-lede">
            What you work on, how you work and what you're open to. It's how
            people find you, and it's free.
          </p>
        </div>

        <div>
          <table className="lp-ledger">
            <caption className="lp-mono">Specimen Passport · not a real person</caption>
            <tbody>
              {ROWS.map(([field, value, state]) => (
                <tr key={field}>
                  <th scope="row">{field}</th>
                  <td>{value}</td>
                  <td><span className={`lp-state ${STATE[state][1]}`}>{STATE[state][0]}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="lp-small" style={{ marginTop: 16 }}>
            <b>Self-declared</b> is written by you · <b>Connected</b> comes from an account you
            control · <b>Verified</b> confirms an institutional affiliation only. It doesn't verify
            degrees, licences or professional competence.
          </p>
        </div>
      </div>
    </section>
  );
}

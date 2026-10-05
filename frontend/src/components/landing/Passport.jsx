import React from "react";
import { Link } from "react-router-dom";
import { trackMarketingEvent as track } from "@/lib/marketingAnalytics";

/**
 * Academic Passport as a ledger of research identity, with the status of
 * each entry stated precisely. Fields are real Passport fields
 * (research_areas, methods, professional_expertise, research record,
 * orcid, institution verification, collaboration preferences). The values
 * are a specimen, not a person.
 */
const ROWS = [
  ["Research areas", "Health services research; operations research", "self"],
  ["Methods", "Process mapping; discrete-event simulation", "self"],
  ["Professional expertise", "Hospital operations", "self"],
  ["Research record", "Publications imported from ORCID", "connected"],
  ["ORCID iD", "Linked to your ORCID account", "connected"],
  ["Institution", "Affiliation with a university", "verified"],
  ["Open to", "Co-authorship, peer review, grant teams", "self"],
];
const STATE = {
  self: ["Self-declared", "lp-state--self"],
  connected: ["Connected", "lp-state--connected"],
  verified: ["Verified", "lp-state--verified"],
};

export default function Passport() {
  return (
    <section className="lp-section" aria-labelledby="lp-passport-title">
      <div className="lp-wrap lp-passport-grid">
        <div>
          <div className="lp-index"><b>04</b> Research identity</div>
          <h2 id="lp-passport-title" className="lp-h2">Academic Passport</h2>
          <p className="lp-lede">
            Synaptiq doesn't match job titles. It reads what you work on, how you
            work and what you're open to. Some of that you declare, some is connected
            from sources you control, and a small part is verified. The Passport
            always says which.
          </p>
          <p className="lp-lede" style={{ marginTop: 14 }}>
            This part is free: your Passport, a public research page, ORCID and your
            publications. It's how Pro members find you.
          </p>
          <div style={{ marginTop: 28 }}>
            <Link to="/register" className="lp-btn lp-btn--primary"
              onClick={() => track("signup_started", { location: "passport" })}>
              Create your Academic Passport
            </Link>
          </div>
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
          <div className="lp-states">
            <div><span className="lp-state lp-state--self">Self-declared</span><span>Written by you. Synaptiq doesn't check it.</span></div>
            <div><span className="lp-state lp-state--connected">Connected</span><span>Imported from an account you control, such as ORCID. It shows the account is yours, not that the content is correct.</span></div>
            <div><span className="lp-state lp-state--verified">Verified</span><span>An institutional affiliation confirmed by institutional email or the institution's approval. It doesn't verify degrees, licences or professional competence.</span></div>
          </div>
        </div>
      </div>
    </section>
  );
}

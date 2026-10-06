# Institutional readiness

Status: **not ready to sign institutional DPAs.** Blockers:
- no identified controller;
- unconfirmed Atlas region;
- unconfirmed processor DPAs;
- no published sub-processor list.

## Controller / processor matrix

| Processing | Synaptiq's role | Notes |
|---|---|---|
| Individual accounts, profiles, discovery, messaging, AI features used by an individual | **Controller** | Privacy Policy applies |
| Institution workspace operated for an institution (members, units, reports), under an institutional agreement | **Processor** for the institution (proposed) | Needs a DPA (Art. 28). Institution decides purposes: who joins, what is reported |
| Platform security, fraud prevention, billing, legal obligations | **Controller** | Even for institutional members |
| ORCID, Stripe | **Independent controllers** | Their own terms |
| Hosting, database, email, AI, analytics providers | **Sub-processors** | See processors-and-transfers.md |

Some situations fall in between: an institution admin viewing a member's activity, or an institution verifying affiliations. Counsel should fix the boundary for each (**LEGAL REVIEW REQUIRED**).

## DPA requirements checklist (Art. 28(3))

- [ ] Subject matter, duration, nature and purpose, data types, categories of data subjects
- [ ] Process only on documented instructions; tell the institution if an instruction seems unlawful
- [ ] Staff confidentiality
- [ ] Security measures (Art. 32). Annex built only from the **safe** claims in security-review.md
- [ ] Sub-processor authorisation, with notice of changes and a right to object
- [ ] Assistance with data subject requests (see dsar-runbook.md)
- [ ] Assistance with breach notification (see incident-response.md), with a notice deadline to the institution
- [ ] Deletion or return at the end of the contract: export exists; an institution-wide export and deletion procedure does not yet exist
- [ ] Audit and information rights
- [ ] International transfer clauses (SCCs) matching the transfer map
- [ ] Identified controller on Synaptiq's side (**P0**)

## Sub-processor list readiness

The candidate list is in processors-and-transfers.md. Before publishing:
1. confirm each DPA;
2. confirm regions (Atlas);
3. decide the Railway MongoDB volume and the "shadow-choice-backend" service;
4. create a change-notice process.

## DPIA screening

| Criterion (EDPB guidelines) | Present? |
|---|---|
| Evaluation or scoring | **Yes**: collaborator matching, profile indicators |
| Automated decisions with legal or similar effect | No |
| Systematic monitoring | No (analytics only with consent) |
| Sensitive or special-category data | **Possible**, via member uploads (not requested) |
| Large scale | Not yet |
| Matching or combining datasets | **Yes**: ORCID, OpenAlex and Crossref enrichment |
| Vulnerable data subjects | No (18+) |
| Innovative technology | **Yes**: generative AI |
| Transfer outside the EU | **Yes**: United States |

Four or more criteria are present. **A DPIA is recommended** before launching institutional plans or marketing to research groups that handle participant data. **LEGAL REVIEW REQUIRED.**

## Research ethics boundary

- Synaptiq is a collaboration and writing environment. It is **not** a research data repository, an ethics committee, a consent-management system or a clinical system.
- The Terms make researchers responsible for ethics approval, participant consent and data protection. Identifiable participant data and special-category data must not be uploaded without a lawful basis and permission.
- Public pages don't claim suitability for clinical, patient or participant data, and must not until a DPIA, an EU-region decision and institutional DPAs exist.

## AI system inventory

See ai-systems.md.

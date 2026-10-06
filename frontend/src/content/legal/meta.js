/**
 * One source for legal-document metadata (dates, versions, operator,
 * contacts). The backend mirrors the versions in backend/legal_versions.py
 * so acceptance records name the exact version a user agreed to.
 *
 * OPERATOR: the legal entity that operates Synaptiq is not yet recorded
 * anywhere in this codebase. It must be filled in (legal name, registered
 * address, registration number, VAT number) before paid plans open. Until
 * then the documents say so plainly rather than naming an invented company.
 */
export const LEGAL = {
  terms:   { version: "2026-10-06", updated: "6 October 2026" },
  privacy: { version: "2026-10-06", updated: "6 October 2026" },
  cookies: { version: "2026-10-06", updated: "6 October 2026" },

  operator: null, // { name, address, registration, vat } once confirmed

  contact: {
    privacy: "privacy@synaptiq.academy",
    general: "contact@synaptiq.academy",
  },

  authority: {
    name: "Autoritatea Națională de Supraveghere a Prelucrării Datelor cu Caracter Personal (ANSPDCP)",
    url: "https://www.dataprotection.ro",
  },
};

export const OPERATOR_PENDING =
  "Synaptiq is operated from Romania. The full legal name, registered address and registration details of the operating entity will be published here before paid plans open.";

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
  // An explanatory guide, not a document anyone accepts, so it carries a
  // last-updated date only (no version tracked by the backend).
  dataProtection: { updated: "6 October 2026" },

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

/**
 * The four documents of the Legal & Trust area, in reading order. Drives the
 * cross-document navigation, the "Continue" index and the footer.
 */
export const LEGAL_DOCS = [
  { id: "privacy", label: "Privacy", title: "Privacy Policy", path: "/privacy",
    dek: "How Synaptiq processes personal data when you use the platform." },
  { id: "terms", label: "Terms", title: "Terms of Service", path: "/terms",
    dek: "The rules that govern your use of Synaptiq." },
  { id: "cookies", label: "Cookies", title: "Cookie Policy", path: "/cookies",
    dek: "What Synaptiq stores in your browser, and what you can choose." },
  { id: "dataProtection", label: "Data Protection", title: "Data Protection", path: "/gdpr",
    dek: "What you control, what is visible to whom, and your rights under European data-protection law." },
];

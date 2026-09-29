// Shared spoken-languages option list — the single canonical source for
// every editor of users.languages (ProfileSetup.jsx's onboarding step and
// EditIdentityModal.jsx, as of P1 Phase 8B §8). Previously defined only
// inline in ProfileSetup.jsx; factored out here so the two editors can't
// drift into two different option lists for the same real field.
export const LANGUAGE_OPTIONS = [
  "English", "French", "Spanish", "Portuguese", "German", "Italian",
  "Dutch", "Polish", "Romanian", "Czech", "Hungarian", "Greek",
  "Turkish", "Arabic", "Mandarin Chinese", "Japanese", "Korean",
  "Hindi", "Russian", "Swedish", "Norwegian", "Danish", "Finnish",
];

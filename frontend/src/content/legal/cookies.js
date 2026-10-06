/**
 * Inventory of cookies and browser storage Synaptiq uses — the single source
 * for the Cookie Policy table. tests/test_legal_truth.py fails if the app
 * writes a cookie or storage key that isn't covered here (by exact name or
 * prefix), so the policy can't silently drift from the code.
 *
 * category: "necessary" (no consent needed: sign-in, security, remembering
 * your consent, or storing something you asked for) | "analytics" (consent).
 */
export const STORAGE_INVENTORY = [
  // Cookies set by the Synaptiq API
  { name: "access_token", type: "Cookie", provider: "Synaptiq", category: "necessary", purpose: "Keeps you signed in (HttpOnly).", duration: "15 minutes" },
  { name: "refresh_token", type: "Cookie", provider: "Synaptiq", category: "necessary", purpose: "Renews your sign-in without asking for your password again (HttpOnly).", duration: "14 days, or until you close the browser if you didn't choose to stay signed in" },
  { name: "csrf_token", type: "Cookie", provider: "Synaptiq", category: "necessary", purpose: "Protects forms against cross-site request forgery.", duration: "15 minutes" },

  // Consent
  { name: "synaptiq_consent_v1", type: "Local storage", provider: "Synaptiq", category: "necessary", purpose: "Remembers your cookie choice.", duration: "Asked again after 12 months" },
  { name: "synaptiq_consent_id_v1", type: "Local storage", provider: "Synaptiq", category: "necessary", purpose: "A random identifier linking your choice to its consent record.", duration: "Until you clear site data" },

  // Things you asked the app to remember (signed-in features)
  { name: "sq_sidebar_collapsed, sq_nav_v2_section, sq_nav_favorites", type: "Local storage", provider: "Synaptiq", category: "necessary", purpose: "Navigation layout and favourites you set.", duration: "Until you clear site data" },
  { name: "sq_app_preferences, sq_app_preferences_log", type: "Local storage", provider: "Synaptiq", category: "necessary", purpose: "Interface preferences you set.", duration: "Until you clear site data" },
  { name: "sq_recent_pages, sq_mem_v1", type: "Local storage", provider: "Synaptiq", category: "necessary", purpose: "Recently visited pages and shortcuts, kept only in your browser.", duration: "Until you clear site data" },
  { name: "sq_msg_*, sq_inbox_*, sq_kanban_prefs_*", type: "Local storage", provider: "Synaptiq", category: "necessary", purpose: "Conversations and items you pinned or archived, and board layouts.", duration: "Until you clear site data" },
  { name: "synaptiq.meetings.quickNotes", type: "Local storage", provider: "Synaptiq", category: "necessary", purpose: "Quick meeting notes you write, kept only in your browser.", duration: "Until you delete them or clear site data" },
  { name: "sq_copilot_session", type: "Local storage", provider: "Synaptiq", category: "necessary", purpose: "Which assistant conversation you had open.", duration: "Until you clear site data" },
  { name: "synaptiq_welcome_v2, synaptiq_welcome_history_v2, sq_fex_*", type: "Local storage", provider: "Synaptiq", category: "necessary", purpose: "Which onboarding steps you've already seen.", duration: "Until you clear site data" },
  { name: "sq_admin_recent_pages, sq_admin_recent_user_filters", type: "Local storage", provider: "Synaptiq", category: "necessary", purpose: "Recent pages and filters for Synaptiq administrators only.", duration: "Until you clear site data" },

  // Analytics — only after consent
  { name: "ph_<project key>_posthog", type: "Cookie and local storage", provider: "PostHog (United States)", category: "analytics", purpose: "An anonymous identifier so usage statistics can be counted. Set only if you allow analytics.", duration: "1 year, removed when you withdraw consent" },
];

/** Exact names and prefixes covered by the inventory (used by tests). */
export const COVERED_KEYS = STORAGE_INVENTORY.flatMap((i) => i.name.split(",").map((s) => s.trim()));

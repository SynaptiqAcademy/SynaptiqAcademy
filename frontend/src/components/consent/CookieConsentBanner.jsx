/**
 * CookieConsentBanner — GDPR-compliant cookie consent UI.
 *
 * - Shows on first visit (or until consent expires — see lib/cookieConsent
 *   — or is reset from Settings → Privacy).
 * - Banner actions: Accept All / Reject Non-Essential / Manage Preferences.
 * - Manage Preferences opens a real modal (focus-trapped, ESC to close,
 *   animated) with per-category toggles and Save / Accept All / Reject All
 *   Optional / Cancel.
 * - All decisions go through lib/cookieConsent.js, which persists to
 *   localStorage + best-effort backend, and notifies the rest of the app
 *   (e.g. public/analytics-init.js) via the `synaptiq:consent-changed`
 *   window event so optional scripts only ever run after explicit consent.
 * - Settings → Privacy can reopen this modal at any time by dispatching
 *   `synaptiq:open-cookie-preferences` (see lib/cookieConsent.openPreferences).
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { X } from "lucide-react";
import {
  readConsent,
  saveConsent,
  acceptAll as acceptAllConsent,
  rejectOptional as rejectOptionalConsent,
  DEFAULT_PREFS,
  CATEGORY_META,
  OPEN_PREFERENCES_EVENT,
} from "@/lib/cookieConsent";

// Kept for any external code that imported the old export name.
export { readConsent as getConsent } from "@/lib/cookieConsent";

const FOCUSABLE_SELECTOR =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export default function CookieConsentBanner() {
  const [show, setShow] = useState(false);
  const [showPrefs, setShowPrefs] = useState(false);
  const [mounted, setMounted] = useState(false); // drives enter transition
  const [prefs, setPrefs] = useState(DEFAULT_PREFS);

  const manageBtnRef = useRef(null);
  const panelRef = useRef(null);
  const lastFocusedRef = useRef(null);

  useEffect(() => {
    setShow(!readConsent());
  }, []);

  // Settings → Privacy → "Manage Cookie Preferences" reopens this modal.
  useEffect(() => {
    const handler = () => {
      const existing = readConsent();
      setPrefs(existing?.prefs ? { ...DEFAULT_PREFS, ...existing.prefs } : DEFAULT_PREFS);
      setShow(true);
      setShowPrefs(true);
    };
    window.addEventListener(OPEN_PREFERENCES_EVENT, handler);
    return () => window.removeEventListener(OPEN_PREFERENCES_EVENT, handler);
  }, []);

  // Mount transition: render off-screen/transparent first, then animate in.
  // Uses setTimeout rather than requestAnimationFrame — rAF is suspended for
  // backgrounded/hidden tabs (e.g. a page opened but not yet focused), which
  // would otherwise leave the banner stuck invisible.
  useEffect(() => {
    if (!show) { setMounted(false); return; }
    const id = setTimeout(() => setMounted(true), 10);
    return () => clearTimeout(id);
  }, [show]);

  const closeAll = useCallback(() => {
    setShow(false);
    setShowPrefs(false);
  }, []);

  const cancelPrefs = useCallback(() => {
    // Reopened from Settings with an existing decision → Cancel should just
    // close. First-run flow (no decision yet) → fall back to the banner.
    if (readConsent()) closeAll();
    else setShowPrefs(false);
  }, [closeAll]);

  const doAcceptAll = useCallback((source) => {
    acceptAllConsent(source);
    closeAll();
  }, [closeAll]);

  const doRejectOptional = useCallback((source) => {
    rejectOptionalConsent(source);
    closeAll();
  }, [closeAll]);

  const doSavePrefs = useCallback(() => {
    saveConsent(prefs, "custom", "preferences_modal");
    closeAll();
  }, [prefs, closeAll]);

  // Focus trap + ESC while the preferences modal is open.
  useEffect(() => {
    if (!showPrefs) return undefined;
    lastFocusedRef.current = document.activeElement;

    const getFocusable = () =>
      panelRef.current
        ? Array.from(panelRef.current.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
            (el) => !el.disabled && el.tabIndex !== -1
          )
        : [];

    // setTimeout, not requestAnimationFrame — rAF is suspended in
    // hidden/backgrounded tabs and would leave focus never moving into the
    // modal at all in that case.
    const focusTimer = setTimeout(() => getFocusable()[0]?.focus(), 10);

    const onKeyDown = (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        cancelPrefs();
        return;
      }
      if (e.key === "Tab") {
        const els = getFocusable();
        if (els.length === 0) return;
        const first = els[0];
        const last = els[els.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKeyDown, true);
    const restoreTarget = lastFocusedRef.current || manageBtnRef.current;
    return () => {
      clearTimeout(focusTimer);
      document.removeEventListener("keydown", onKeyDown, true);
      restoreTarget?.focus?.();
    };
  }, [showPrefs, cancelPrefs]);

  if (!show) return null;

  return (
    <>
      {showPrefs && (
        <div
          className="fixed inset-0 bg-slate-900/40 z-[9000] transition-opacity duration-200"
          style={{ opacity: mounted ? 1 : 0 }}
          onClick={cancelPrefs}
          data-testid="consent-backdrop"
          aria-hidden="true"
        />
      )}
      <div
        ref={showPrefs ? panelRef : undefined}
        className="fixed bottom-0 inset-x-0 z-[9001] bg-white border-t border-slate-200 shadow-2xl transition-all duration-200 ease-out"
        style={{ transform: mounted ? "translateY(0)" : "translateY(16px)", opacity: mounted ? 1 : 0 }}
        data-testid="cookie-consent-banner"
        role={showPrefs ? "dialog" : "region"}
        aria-modal={showPrefs ? "true" : undefined}
        aria-live={showPrefs ? undefined : "polite"}
        aria-label={showPrefs ? "Cookie preferences" : "Cookie consent"}
      >
        <div className="max-w-5xl mx-auto px-6 py-5 max-h-[85vh] overflow-y-auto">
          {!showPrefs ? (
            <div className="flex flex-col md:flex-row md:items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="overline text-[#0F2847]">Privacy &amp; cookies</div>
                <h3 className="font-serif text-lg text-slate-900 mt-1">We use cookies to power Synaptiq.</h3>
                <p className="text-sm text-slate-600 mt-1 leading-relaxed">
                  Essential cookies are required for authentication and core platform function. We also
                  use optional cookies for analytics, preferences, and marketing. Read our{" "}
                  <Link to="/cookies" className="underline decoration-dotted hover:text-[#0F2847]">Cookie Policy</Link>{" "}
                  and{" "}
                  <Link to="/privacy" className="underline decoration-dotted hover:text-[#0F2847]">Privacy Policy</Link>.
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0 flex-wrap">
                <button
                  ref={manageBtnRef}
                  onClick={() => setShowPrefs(true)}
                  className="px-4 py-2 text-sm text-slate-700 border border-slate-300 hover:bg-slate-50 rounded-md transition-colors"
                  data-testid="consent-manage-btn"
                >Manage Preferences</button>
                <button
                  onClick={() => doRejectOptional("banner")}
                  className="px-4 py-2 text-sm text-slate-700 border border-slate-300 hover:bg-slate-50 rounded-md transition-colors"
                  data-testid="consent-reject-btn"
                >Reject Non-Essential</button>
                <button
                  onClick={() => doAcceptAll("banner")}
                  className="px-4 py-2 text-sm bg-[#0F2847] text-white hover:bg-slate-800 rounded-md transition-colors"
                  data-testid="consent-accept-btn"
                >Accept All</button>
              </div>
            </div>
          ) : (
            <div className="max-w-xl">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="overline text-[#0F2847]">Cookie preferences</div>
                  <h3 id="cookie-prefs-title" className="font-serif text-2xl text-slate-900 mt-1">Manage your cookies</h3>
                  <p className="text-sm text-slate-600 mt-1">Choose which categories of cookies Synaptiq may use on your device.</p>
                </div>
                <button
                  onClick={cancelPrefs}
                  aria-label="Close cookie preferences"
                  className="shrink-0 w-8 h-8 flex items-center justify-center rounded-md border border-slate-200 text-slate-500 hover:bg-slate-50 transition-colors"
                  data-testid="consent-prefs-close-x"
                ><X size={14} /></button>
              </div>

              <div className="mt-5 space-y-3">
                {CATEGORY_META.map((cat) => (
                  <ConsentRow
                    key={cat.id}
                    label={cat.label}
                    desc={cat.description}
                    explanation={cat.explanation}
                    checked={cat.locked ? true : !!prefs[cat.id]}
                    onChange={(v) => setPrefs((p) => ({ ...p, [cat.id]: v }))}
                    locked={cat.locked}
                    testId={`consent-row-${cat.id}`}
                  />
                ))}
              </div>

              <div className="mt-6 flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-3">
                <button
                  onClick={cancelPrefs}
                  className="px-4 py-2 text-sm text-slate-700 hover:text-slate-900 rounded-md transition-colors"
                  data-testid="consent-prefs-cancel"
                >Cancel</button>
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                  <button
                    onClick={() => doRejectOptional("preferences_modal")}
                    className="px-4 py-2 text-sm text-slate-700 border border-slate-300 hover:bg-slate-50 rounded-md transition-colors"
                    data-testid="consent-prefs-reject-all"
                  >Reject All Optional</button>
                  <button
                    onClick={() => doAcceptAll("preferences_modal")}
                    className="px-4 py-2 text-sm text-slate-700 border border-slate-300 hover:bg-slate-50 rounded-md transition-colors"
                    data-testid="consent-prefs-accept-all"
                  >Accept All</button>
                  <button
                    onClick={doSavePrefs}
                    className="px-4 py-2 text-sm bg-[#0F2847] text-white hover:bg-slate-800 rounded-md transition-colors"
                    data-testid="consent-prefs-save"
                  >Save Preferences</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function ConsentRow({ label, desc, explanation, checked, onChange, locked, testId }) {
  return (
    <div className="border border-slate-200 hover:bg-slate-50/60 rounded-md" data-testid={testId}>
      <label className="flex items-start gap-3 p-3 cursor-pointer">
        <input
          type="checkbox"
          checked={!!checked}
          onChange={(e) => !locked && onChange?.(e.target.checked)}
          disabled={locked}
          aria-label={label}
          className="mt-1 accent-[#0F2847]"
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="text-sm text-slate-900 font-medium">{label}</div>
              {locked && <span className="text-[10px] font-mono uppercase tracking-widest text-slate-400">always on</span>}
            </div>
            <span
              className={`text-[10px] font-mono uppercase tracking-widest shrink-0 ${checked ? "text-emerald-600" : "text-slate-400"}`}
              data-testid={`${testId}-status`}
            >
              {checked ? "Enabled" : "Disabled"}
            </span>
          </div>
          <div className="text-xs text-slate-600 mt-0.5 leading-relaxed">{desc}</div>
          {explanation && (
            <div className="text-[11px] text-slate-500 mt-1 leading-relaxed italic">{explanation}</div>
          )}
        </div>
      </label>
    </div>
  );
}

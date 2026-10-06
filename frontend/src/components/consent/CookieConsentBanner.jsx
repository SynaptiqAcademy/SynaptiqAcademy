/**
 * CookieConsentBanner — the cookie banner and the cookie preferences dialog.
 *
 * - The banner shows on first visit (or once the choice expires — see
 *   lib/cookieConsent — or is reset from Settings → Privacy) with two equal
 *   choices, Reject analytics / Allow analytics, and a way into preferences.
 * - The preferences dialog (focus-trapped, Escape closes) lists the two real
 *   categories as rows: Strictly necessary (always on) and Analytics (a
 *   switch). Reject optional / Save preferences / Allow analytics are styled
 *   identically, so no choice is visually favoured. Closing without saving
 *   changes nothing.
 * - Every decision goes through lib/cookieConsent.js, which stores it,
 *   versions it and notifies public/analytics-init.js through the
 *   `synaptiq:consent-changed` event, so analytics only ever runs after an
 *   explicit choice.
 * - The footer's "Cookie settings", the Cookie Policy's "Manage cookie
 *   settings" and Settings → Privacy all open this same dialog through
 *   `synaptiq:open-cookie-preferences` (lib/cookieConsent.openPreferences).
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  readConsent,
  saveConsent,
  acceptAll as acceptAllConsent,
  rejectOptional as rejectOptionalConsent,
  DEFAULT_PREFS,
  CATEGORY_META,
  OPEN_PREFERENCES_EVENT,
} from "@/lib/cookieConsent";
import "./consent.css";

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

  // Footer "Cookie settings", /cookies "Manage cookie settings" and
  // Settings → Privacy reopen the dialog.
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

  // Mount transition. setTimeout rather than requestAnimationFrame: rAF is
  // suspended in hidden tabs and would leave the banner stuck invisible.
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
    // Reopened with an existing decision → just close. First visit (no
    // decision yet) → back to the banner. Never changes the stored choice.
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

  // Focus trap + Escape while the preferences dialog is open.
  useEffect(() => {
    if (!showPrefs) return undefined;
    lastFocusedRef.current = document.activeElement;

    const getFocusable = () =>
      panelRef.current
        ? Array.from(panelRef.current.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
            (el) => !el.disabled && el.tabIndex !== -1
          )
        : [];

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

  if (!showPrefs) {
    return (
      <div
        className={`cc cc-banner${mounted ? " cc-in" : ""}`}
        data-testid="cookie-consent-banner"
        role="region"
        aria-live="polite"
        aria-labelledby="cc-banner-title"
      >
        <div className="cc-banner-inner">
          <div className="cc-banner-text">
            <div className="cc-label">Privacy control <span aria-hidden="true">/</span> Cookies</div>
            <h2 id="cc-banner-title" className="cc-title">Cookies on Synaptiq</h2>
            <p className="cc-body">
              We use strictly necessary cookies to keep you signed in and secure. With your permission,
              we also use analytics to see which pages and features are used. Read our{" "}
              <Link to="/cookies">Cookie Policy</Link> and <Link to="/privacy">Privacy Policy</Link>.
            </p>
          </div>
          <div className="cc-actions cc-banner-actions">
            <button
              type="button"
              className="cc-btn"
              data-testid="consent-reject-btn"
              onClick={() => doRejectOptional("banner")}
            >Reject analytics</button>
            <button
              type="button"
              className="cc-btn"
              data-testid="consent-accept-btn"
              onClick={() => doAcceptAll("banner")}
            >Allow analytics</button>
            <button
              type="button"
              ref={manageBtnRef}
              className="cc-link"
              data-testid="consent-manage-btn"
              onClick={() => setShowPrefs(true)}
            >Preferences</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div
        className={`cc-backdrop${mounted ? " cc-in" : ""}`}
        onClick={cancelPrefs}
        data-testid="consent-backdrop"
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        className={`cc cc-dialog${mounted ? " cc-in" : ""}`}
        data-testid="cookie-consent-banner"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cookie-prefs-title"
        aria-describedby="cookie-prefs-desc"
      >
        <div className="cc-dialog-head">
          <div>
            <div className="cc-label">Privacy control <span aria-hidden="true">/</span> Cookie preferences</div>
            <h2 id="cookie-prefs-title" className="cc-title cc-title-lg">Manage your cookies</h2>
            <p id="cookie-prefs-desc" className="cc-body">Choose whether Synaptiq may use optional analytics on this device.</p>
          </div>
          <button
            type="button"
            className="cc-close"
            onClick={cancelPrefs}
            aria-label="Close cookie preferences without saving"
            data-testid="consent-prefs-close-x"
          >Close</button>
        </div>

        <ol className="cc-rows">
          {CATEGORY_META.map((cat, i) => (
            <ConsentRow
              key={cat.id}
              n={i + 1}
              id={cat.id}
              label={cat.label}
              desc={cat.description}
              explanation={cat.explanation}
              checked={cat.locked ? true : !!prefs[cat.id]}
              onChange={(v) => setPrefs((p) => ({ ...p, [cat.id]: v }))}
              locked={cat.locked}
              testId={`consent-row-${cat.id}`}
            />
          ))}
        </ol>

        <div className="cc-actions cc-dialog-actions">
          <button
            type="button"
            className="cc-btn"
            data-testid="consent-prefs-reject-all"
            onClick={() => doRejectOptional("preferences_modal")}
          >Reject optional</button>
          <button
            type="button"
            className="cc-btn"
            data-testid="consent-prefs-save"
            onClick={doSavePrefs}
          >Save preferences</button>
          <button
            type="button"
            className="cc-btn"
            data-testid="consent-prefs-accept-all"
            onClick={() => doAcceptAll("preferences_modal")}
          >Allow analytics</button>
        </div>
        <p className="cc-foot">
          <Link to="/cookies" onClick={cancelPrefs}>Cookie Policy</Link>
          <span aria-hidden="true"> · </span>
          You can change this at any time from “Cookie settings” in the footer.
        </p>
      </div>
    </>
  );
}

function ConsentRow({ n, id, label, desc, explanation, checked, onChange, locked, testId }) {
  const labelId = `cc-row-${id}-label`;
  const descId = `cc-row-${id}-desc`;
  return (
    <li className="cc-row" data-testid={testId}>
      <div className="cc-row-head">
        <div className="cc-row-name" id={labelId}>
          <span className="cc-row-n" aria-hidden="true">{String(n).padStart(2, "0")} /</span> {label}
        </div>
        {locked ? (
          <span className="cc-state cc-state-locked" data-testid={`${testId}-status`}>Always on</span>
        ) : (
          <button
            type="button"
            role="switch"
            aria-checked={!!checked}
            aria-labelledby={labelId}
            aria-describedby={descId}
            className="cc-switch"
            onClick={() => onChange?.(!checked)}
            data-testid={`${testId}-switch`}
          >
            <span className="cc-switch-track" aria-hidden="true"><span className="cc-switch-thumb" /></span>
            <span className="cc-state" data-testid={`${testId}-status`}>{checked ? "On" : "Off"}</span>
          </button>
        )}
      </div>
      <p className="cc-row-desc" id={descId}>{desc}</p>
      {explanation && <p className="cc-row-more">{explanation}</p>}
    </li>
  );
}

/**
 * Shared authentication UI — one layout and one set of form primitives for
 * every auth screen (sign in, Start Free, forgot/reset password, email
 * verification, invitations). Styling lives in auth.css and reuses the
 * public site's tokens (landing.css, scoped by `.lp`).
 *
 * The exported names and props are unchanged from the previous version, so
 * pages only change where they choose to; behaviour (validation, API calls,
 * redirects, consent) stays in the pages.
 */
import React, { useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";
import { Eye, EyeOff, Loader2, AlertCircle, ChevronDown } from "lucide-react";
import api from "../../lib/api";
import "../landing/landing.css";
import "./auth.css";

// Palette, for pages that still style a few details inline.
export const NAVY = "#0F2847";
export const BORDER = "#DCD8CF";
export const BG = "#FBFAF7";
export const T_MAIN = "#10141C";
export const T_MID = "#3A4250";
export const T_FAINT = "#5F6673";

/** Kept for compatibility; the stylesheet now carries all auth styles. */
export function AuthStyles() { return null; }

// ─── Layout ───────────────────────────────────────────────────────────────────

/** A quiet research-network motif: fixed coordinates, no animation. */
function Motif() {
  const nodes = [[62, 8], [90, 20], [40, 34], [76, 46], [22, 60], [96, 64], [58, 74], [8, 90], [84, 92], [36, 96]];
  const edges = [[0, 1], [0, 2], [1, 3], [2, 3], [2, 4], [3, 5], [3, 6], [4, 6], [4, 7], [6, 8], [5, 8], [7, 9], [6, 9]];
  return (
    <svg className="au-motif" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true" focusable="false">
      {edges.map(([a, b], i) => (
        <line key={i} x1={nodes[a][0]} y1={nodes[a][1]} x2={nodes[b][0]} y2={nodes[b][1]} stroke="rgba(255,255,255,0.16)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
      ))}
      {nodes.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i === 3 || i === 7 ? 1.1 : 0.7} fill={i === 3 || i === 7 ? "#c9a99c" : "rgba(255,255,255,0.42)"} />
      ))}
    </svg>
  );
}

const SIGNALS = [
  ["Academic Passport", "Your research identity, with your ORCID record."],
  ["Research Need", "The expertise a question calls for, and who has it."],
  ["Collaboration", "Invitations, projects and shared workspaces."],
];

// The form comes first in the document (keyboard and screen-reader order);
// CSS places the editorial panel on the left on wide screens.
export function AuthLayout({ children }) {
  return (
    <div className="lp au">
      <main className="au-main">
        <div className="au-topbar">
          <Link to="/" className="au-brand">SYNAPTIQ</Link>
          <Link to="/help-center" className="au-quiet">Help</Link>
        </div>
        <div className="au-stage">{children}</div>
        <nav className="au-main-foot" aria-label="Legal">
          <Link to="/privacy">Privacy</Link> · <Link to="/terms">Terms</Link> · <Link to="/security">Security</Link>
        </nav>
      </main>

      <aside className="au-panel" aria-label="About Synaptiq">
        <Motif />
        <Link to="/" className="au-brand">SYNAPTIQ</Link>
        <div className="au-panel-body">
          <div className="au-eyebrow">Research and academic collaboration</div>
          <p className="au-statement">Research starts with a question.</p>
          <p className="au-panel-copy">Synaptiq turns it into the expertise it needs, the people who have it, and the work you do together.</p>
          <ul className="au-signals">
            {SIGNALS.map(([k, v], i) => (
              <li key={k}><span className="n">{String(i + 1).padStart(2, "0")}</span><span className="k">{k}</span><span className="v">{v}</span></li>
            ))}
          </ul>
        </div>
        <nav className="au-panel-foot" aria-label="Legal and help">
          <Link to="/privacy">Privacy</Link>
          <Link to="/terms">Terms</Link>
          <Link to="/security">Security</Link>
          <Link to="/help-center">Help Center</Link>
        </nav>
      </aside>
    </div>
  );
}

/** The form column. `wide` gives room for longer forms. */
export function AuthCard({ children, wide }) {
  return <div className={`au-form${wide ? " au-form-wide" : ""}`}>{children}</div>;
}

/** The brand now lives in the layout; a custom tagline becomes a kicker. */
export function AuthHeader({ tagline }) {
  if (!tagline || tagline === "AI-Powered Academic Collaboration") return null;
  return <div className="au-kicker" style={{ marginBottom: 10 }}>{tagline}</div>;
}

export function AuthTitle({ title, subtitle, kicker }) {
  return (
    <header className="au-head">
      {kicker && <div className="au-kicker">{kicker}</div>}
      <h1 className="au-title">{title}</h1>
      {subtitle && <p className="au-sub">{subtitle}</p>}
    </header>
  );
}

export function BackLink({ to, label }) {
  return <Link to={to} className="au-back"><span aria-hidden="true">←</span> {label}</Link>;
}

// ─── Fields ───────────────────────────────────────────────────────────────────

export function AuthInput({ label, type = "text", value, onChange, placeholder, required, autoComplete, testId, rightAddon, name, invalid, describedBy, id: idProp, inputMode }) {
  const autoId = useId();
  const id = idProp || `au-${autoId}`;
  return (
    <div className="au-field">
      <label className="au-label" htmlFor={id}>{label}</label>
      <div className="au-control">
        <input
          id={id}
          className={`au-input${rightAddon ? " au-input-addon" : ""}`}
          type={type}
          required={required}
          aria-required={required || undefined}
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
          value={value}
          onChange={onChange}
          name={name}
          autoComplete={autoComplete}
          inputMode={inputMode}
          data-testid={testId}
          placeholder={placeholder}
        />
        {rightAddon && typeof rightAddon === "function" ? rightAddon(id) : rightAddon}
      </div>
    </div>
  );
}

export function AuthSelect({ label, value, onChange, required, children, testId }) {
  const id = `au-${useId()}`;
  return (
    <div className="au-field">
      <label className="au-label" htmlFor={id}>{label}</label>
      <div className="au-control">
        <select id={id} className="au-select" value={value} onChange={onChange} required={required} data-testid={testId}>
          {children}
        </select>
        <ChevronDown size={15} strokeWidth={1.8} className="au-select-chevron" aria-hidden="true" />
      </div>
    </div>
  );
}

export function PasswordInput({ label = "Password", value, onChange, required, testId, name, autoComplete, invalid, describedBy }) {
  const [show, setShow] = useState(false);
  return (
    <AuthInput
      label={label}
      type={show ? "text" : "password"}
      value={value}
      onChange={onChange}
      required={required}
      testId={testId}
      name={name}
      invalid={invalid}
      describedBy={describedBy}
      autoComplete={autoComplete || "current-password"}
      rightAddon={(inputId) => (
        <button
          type="button"
          className="au-reveal"
          onClick={() => setShow((s) => !s)}
          aria-label={show ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          aria-pressed={show}
          aria-controls={inputId}
        >
          {show ? <EyeOff size={17} strokeWidth={1.6} aria-hidden="true" /> : <Eye size={17} strokeWidth={1.6} aria-hidden="true" />}
        </button>
      )}
    />
  );
}

export function PasswordStrength({ password }) {
  if (!password) return null;
  let s = 0;
  if (password.length >= 6) s++;
  if (password.length >= 8) s++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) s++;
  if (/\d/.test(password)) s++;
  if (/[^A-Za-z0-9]/.test(password)) s++;
  const level = Math.min(4, s);
  const labels = ["", "Weak", "Fair", "Good", "Strong"];
  return (
    <div className="au-strength" data-level={level}>
      <div className="au-strength-bar" aria-hidden="true">
        {[1, 2, 3, 4].map((i) => <span key={i} className={i <= level ? "on" : ""} />)}
      </div>
      <span className="au-strength-label" aria-live="polite">{level > 0 ? labels[level] : ""}<span className="au-sr"> password</span></span>
    </div>
  );
}

// ─── Actions ──────────────────────────────────────────────────────────────────

export function AuthButton({ children, loading, disabled, type = "submit", onClick, variant = "primary", testId, loadingLabel = "Please wait…" }) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={loading || disabled}
      aria-busy={loading || undefined}
      data-testid={testId}
      className={`au-btn ${variant === "primary" ? "au-btn-primary" : "au-btn-secondary"}`}
    >
      {loading ? <><Loader2 size={17} strokeWidth={2} className="au-spin" aria-hidden="true" /> {loadingLabel}</> : children}
    </button>
  );
}

export function AuthDivider({ text = "or" }) {
  return <div className="au-divider" role="separator" aria-label={text}>{text}</div>;
}

export function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" focusable="false">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
      <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
    </svg>
  );
}

export function MicrosoftIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" focusable="false">
      <rect x="0" y="0" width="8.5" height="8.5" fill="#F25022"/>
      <rect x="9.5" y="0" width="8.5" height="8.5" fill="#7FBA00"/>
      <rect x="0" y="9.5" width="8.5" height="8.5" fill="#00A4EF"/>
      <rect x="9.5" y="9.5" width="8.5" height="8.5" fill="#FFB900"/>
    </svg>
  );
}

/** The ORCID iD mark (green circle, white "iD"). */
export function OrcidIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 256 256" aria-hidden="true" focusable="false">
      <path fill="#A6CE39" d="M256 128c0 70.7-57.3 128-128 128S0 198.7 0 128 57.3 0 128 0s128 57.3 128 128z"/>
      <path fill="#FFF" d="M86.3 186.2H70.9V79.1h15.4v107.1zM108.9 79.1h41.6c39.6 0 57 28.3 57 53.6 0 27.5-21.5 53.6-56.8 53.6h-41.8V79.1zm15.4 93.3h24.5c34.9 0 42.9-26.5 42.9-39.7 0-21.5-13.7-39.7-43.7-39.7h-23.7v79.4zM88.7 56.8c0 5.5-4.5 10.1-10.1 10.1s-10.1-4.6-10.1-10.1c0-5.6 4.5-10.1 10.1-10.1s10.1 4.6 10.1 10.1z"/>
    </svg>
  );
}

/** Sign-in providers that are actually configured on the server. A provider
 *  whose credentials aren't set is not shown, so no button leads to an error. */
export function useOauthProviders() {
  const [providers, setProviders] = useState({ google: false, orcid: false });
  useEffect(() => {
    let alive = true;
    Promise.all(["google", "orcid"].map((p) =>
      api.get("/" + p + "/config").then((r) => !!(r.data && r.data.configured)).catch(() => false)
    )).then((res) => { if (alive) setProviders({ google: res[0], orcid: res[1] }); });
    return () => { alive = false; };
  }, []);
  return providers;
}

export function SocialButtons({ onGoogle, onOrcid, providers, busy }) {
  if (!providers || (!providers.google && !providers.orcid)) return null;
  return (
    <div className="au-social">
      {providers.orcid && (
        <button type="button" className="au-btn au-btn-secondary au-orcid" onClick={onOrcid} disabled={busy === "orcid"} aria-busy={busy === "orcid" || undefined}>
          {busy === "orcid" ? <Loader2 size={17} strokeWidth={2} className="au-spin" aria-hidden="true" /> : <OrcidIcon />}
          {busy === "orcid" ? "Opening ORCID…" : "Continue with ORCID"}
        </button>
      )}
      {providers.google && (
        <button type="button" className="au-btn au-btn-secondary au-orcid" onClick={onGoogle} disabled={busy === "google"}>
          <GoogleIcon /> Continue with Google
        </button>
      )}
    </div>
  );
}

// ─── Feedback ─────────────────────────────────────────────────────────────────

export function ErrorBanner({ error, testId, id }) {
  if (!error) return null;
  return (
    <div className="au-alert" role="alert" data-testid={testId} id={id}>
      <AlertCircle size={16} strokeWidth={1.8} aria-hidden="true" />
      <span>{error}</span>
    </div>
  );
}

export function Notice({ children }) {
  return <div className="au-notice" role="status">{children}</div>;
}

export function SuccessState({ icon, title, subtitle, children }) {
  return (
    <div className="au-success">
      <div className="au-success-mark">{React.cloneElement(icon, { size: 22, strokeWidth: 1.6, style: { color: NAVY }, "aria-hidden": true })}</div>
      <h2>{title}</h2>
      <p>{subtitle}</p>
      {children}
    </div>
  );
}

export function AuthFooter({ children }) {
  return <p className="au-switch">{children}</p>;
}

export function AuthLink({ to, children, testId, onClick }) {
  return <Link to={to} data-testid={testId} onClick={onClick} className="au-link">{children}</Link>;
}

export function TermsNote() {
  return (
    <p className="au-fine">
      By continuing you agree to our <Link to="/terms">Terms of Service</Link> and <Link to="/privacy">Privacy Policy</Link>.
    </p>
  );
}

export function AuthCheckbox({ checked, onChange, children, testId, className = "" }) {
  return (
    <label className={`au-check ${className}`}>
      <input type="checkbox" checked={checked} onChange={onChange} data-testid={testId} />
      <span>{children}</span>
    </label>
  );
}

/* eslint-disable */
/**
 * Shared authentication UI primitives.
 * All auth pages import from here — one design language, zero duplication.
 */
import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Eye, EyeOff, Loader2, AlertCircle, CheckCircle2, ChevronDown } from "lucide-react";
import { toast } from "sonner";

export const NAVY   = "#0F2847";
export const BORDER = "#E4E8EF";
export const BG     = "#FAFAFA";
export const T_MAIN = "#0f172a";
export const T_MID  = "#64748b";
export const T_FAINT= "#94a3b8";

// ─── Animation injection ──────────────────────────────────────────────────────

export function AuthStyles() {
  return (
    <style>{`
      @keyframes auth-spin { to { transform: rotate(360deg); } }
      @keyframes auth-in { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
      .auth-card { animation: auth-in 220ms cubic-bezier(.16,1,.3,1); }
    `}</style>
  );
}

// ─── Page wrapper ─────────────────────────────────────────────────────────────

export function AuthLayout({ children }) {
  return (
    <div style={{ minHeight: "100vh", background: BG, display: "flex", alignItems: "center", justifyContent: "center", padding: "32px 20px" }}>
      <AuthStyles />
      {children}
    </div>
  );
}

// ─── Card ─────────────────────────────────────────────────────────────────────

export function AuthCard({ children, wide }) {
  return (
    <div
      className="auth-card"
      style={{
        width: "100%",
        maxWidth: wide ? 520 : 460,
        background: "#fff",
        borderRadius: 12,
        border: `1px solid ${BORDER}`,
        boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 8px 32px rgba(0,0,0,0.06)",
        padding: "48px 48px",
        boxSizing: "border-box",
      }}
    >
      {children}
    </div>
  );
}

// ─── Logo + tagline ───────────────────────────────────────────────────────────

export function AuthHeader({ tagline = "AI-Powered Academic Collaboration" }) {
  return (
    <div style={{ textAlign: "center", marginBottom: 36 }}>
      <Link to="/" style={{ textDecoration: "none", display: "inline-block" }}>
        <div style={{ fontSize: "1.05rem", fontWeight: 800, color: NAVY, letterSpacing: "-0.04em", lineHeight: 1 }}>
          SYNAPTIQ
        </div>
        <div style={{ fontSize: "0.62rem", fontWeight: 500, color: T_FAINT, marginTop: 5, letterSpacing: "0.08em", textTransform: "uppercase" }}>
          {tagline}
        </div>
      </Link>
    </div>
  );
}

// ─── Page title + subtitle ────────────────────────────────────────────────────

export function AuthTitle({ title, subtitle }) {
  return (
    <div style={{ marginBottom: 28 }}>
      <h1 style={{ fontFamily: "Georgia, serif", fontSize: "1.55rem", fontWeight: 700, color: T_MAIN, margin: "0 0 8px", letterSpacing: "-0.025em", lineHeight: 1.2 }}>
        {title}
      </h1>
      {subtitle && (
        <p style={{ fontSize: "0.875rem", color: T_MID, margin: 0, lineHeight: 1.65 }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}

// ─── Back link ────────────────────────────────────────────────────────────────

export function BackLink({ to, label }) {
  return (
    <Link
      to={to}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        fontSize: "0.78rem", fontWeight: 500, color: T_FAINT,
        textDecoration: "none", marginBottom: 24,
        transition: "color 120ms",
      }}
      onMouseEnter={function(e) { e.currentTarget.style.color = T_MID; }}
      onMouseLeave={function(e) { e.currentTarget.style.color = T_FAINT; }}
    >
      ← {label}
    </Link>
  );
}

// ─── Floating-label input ─────────────────────────────────────────────────────

export function AuthInput({ label, type = "text", value, onChange, placeholder, required, autoComplete, testId, rightAddon, name }) {
  const [focused, setFocused] = useState(false);
  const active = focused || Boolean(value);

  return (
    <div style={{ position: "relative", height: 52 }}>
      <label
        style={{
          position: "absolute", left: 16, zIndex: 1, pointerEvents: "none", lineHeight: 1,
          top: active ? 8 : "50%",
          transform: active ? "none" : "translateY(-50%)",
          fontSize: active ? "0.6rem" : "0.875rem",
          fontWeight: active ? 700 : 400,
          color: active ? (focused ? NAVY : T_FAINT) : T_FAINT,
          letterSpacing: active ? "0.07em" : 0,
          textTransform: active ? "uppercase" : "none",
          transition: "top 140ms, transform 140ms, font-size 140ms, color 140ms, letter-spacing 140ms",
        }}
      >
        {label}
      </label>
      <input
        type={type}
        required={required}
        value={value}
        onChange={onChange}
        name={name}
        autoComplete={autoComplete}
        data-testid={testId}
        placeholder={active && focused ? placeholder : ""}
        onFocus={function() { setFocused(true); }}
        onBlur={function() { setFocused(false); }}
        style={{
          position: "absolute", inset: 0, width: "100%", height: "100%",
          paddingTop: active ? 22 : 0,
          paddingBottom: active ? 8 : 0,
          paddingLeft: 16,
          paddingRight: rightAddon ? 50 : 16,
          borderRadius: 10,
          border: `1.5px solid ${focused ? NAVY : BORDER}`,
          fontSize: "0.9rem", color: T_MAIN,
          background: "#fff", outline: "none",
          boxSizing: "border-box",
          boxShadow: focused ? "0 0 0 3px rgba(15,40,71,0.08)" : "none",
          transition: "border-color 150ms, box-shadow 150ms",
          fontFamily: "inherit",
        }}
      />
      {rightAddon && (
        <div style={{ position: "absolute", right: 14, top: "50%", transform: "translateY(-50%)", zIndex: 2 }}>
          {rightAddon}
        </div>
      )}
    </div>
  );
}

// ─── Floating-label select ────────────────────────────────────────────────────

export function AuthSelect({ label, value, onChange, required, children, testId }) {
  const [focused, setFocused] = useState(false);
  const active = Boolean(value);

  return (
    <div style={{ position: "relative", height: 52 }}>
      <label
        style={{
          position: "absolute", left: 16, zIndex: 1, pointerEvents: "none", lineHeight: 1,
          top: active ? 8 : "50%",
          transform: active ? "none" : "translateY(-50%)",
          fontSize: active ? "0.6rem" : "0.875rem",
          fontWeight: active ? 700 : 400,
          color: active ? (focused ? NAVY : T_FAINT) : T_FAINT,
          letterSpacing: active ? "0.07em" : 0,
          textTransform: active ? "uppercase" : "none",
          transition: "top 140ms, transform 140ms, font-size 140ms, color 140ms",
        }}
      >
        {label}
      </label>
      <select
        value={value}
        onChange={onChange}
        required={required}
        data-testid={testId}
        onFocus={function() { setFocused(true); }}
        onBlur={function() { setFocused(false); }}
        style={{
          position: "absolute", inset: 0, width: "100%", height: "100%",
          padding: active ? "22px 36px 8px 16px" : "0 36px 0 16px",
          borderRadius: 10,
          border: `1.5px solid ${focused ? NAVY : BORDER}`,
          fontSize: "0.9rem", color: value ? T_MAIN : "transparent",
          background: "#fff", outline: "none", cursor: "pointer",
          boxSizing: "border-box", appearance: "none",
          boxShadow: focused ? "0 0 0 3px rgba(15,40,71,0.08)" : "none",
          transition: "border-color 150ms, box-shadow 150ms",
          fontFamily: "inherit",
        }}
      >
        {children}
      </select>
      <ChevronDown
        size={14} strokeWidth={2}
        style={{ position: "absolute", right: 14, top: "50%", transform: "translateY(-50%)", color: T_FAINT, pointerEvents: "none", zIndex: 2 }}
      />
    </div>
  );
}

// ─── Password input ───────────────────────────────────────────────────────────

export function PasswordInput({ label = "Password", value, onChange, required, testId, name, autoComplete }) {
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
      autoComplete={autoComplete || "current-password"}
      rightAddon={
        <button
          type="button"
          tabIndex={-1}
          onClick={function() { setShow(function(s) { return !s; }); }}
          style={{ background: "none", border: "none", cursor: "pointer", color: T_FAINT, padding: 0, display: "flex", alignItems: "center", transition: "color 120ms" }}
          aria-label={show ? "Hide password" : "Show password"}
          onMouseEnter={function(e) { e.currentTarget.style.color = T_MID; }}
          onMouseLeave={function(e) { e.currentTarget.style.color = T_FAINT; }}
        >
          {show ? <EyeOff size={15} strokeWidth={1.5} /> : <Eye size={15} strokeWidth={1.5} />}
        </button>
      }
    />
  );
}

// ─── Password strength ────────────────────────────────────────────────────────

export function PasswordStrength({ password }) {
  if (!password) return null;
  let s = 0;
  if (password.length >= 6) s++;
  if (password.length >= 8) s++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) s++;
  if (/\d/.test(password)) s++;
  if (/[^A-Za-z0-9]/.test(password)) s++;
  const level = Math.min(4, s);
  const colors = ["#E4E8EF", "#EF4444", "#F59E0B", "#3B82F6", "#10B981"];
  const labels = ["", "Weak", "Fair", "Good", "Strong"];
  const col = colors[level];
  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ display: "flex", gap: 4 }}>
        {[1,2,3,4].map(function(i) {
          return <div key={i} style={{ flex: 1, height: 3, borderRadius: 2, background: i <= level ? col : "#E4E8EF", transition: "background 200ms" }} />;
        })}
      </div>
      {level > 0 && (
        <div style={{ fontSize: "0.7rem", color: col, fontWeight: 600, marginTop: 4, transition: "color 200ms" }}>
          {labels[level]}
        </div>
      )}
    </div>
  );
}

// ─── Primary / secondary button ───────────────────────────────────────────────

export function AuthButton({ children, loading, disabled, type = "submit", onClick, variant = "primary", testId }) {
  const primary = variant === "primary";
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={loading || disabled}
      data-testid={testId}
      style={{
        width: "100%", height: 52,
        background: primary ? (loading || disabled ? "#94a3b8" : NAVY) : "#fff",
        color: primary ? "#fff" : T_MAIN,
        border: primary ? "none" : `1.5px solid ${BORDER}`,
        borderRadius: 10,
        fontSize: "0.9rem", fontWeight: 600, letterSpacing: "-0.01em",
        cursor: loading || disabled ? "not-allowed" : "pointer",
        display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
        transition: "opacity 150ms, background 150ms, border-color 150ms",
        fontFamily: "inherit",
      }}
      onMouseEnter={function(e) { if (!loading && !disabled) { e.currentTarget.style.opacity = "0.88"; } }}
      onMouseLeave={function(e) { e.currentTarget.style.opacity = "1"; }}
    >
      {loading
        ? <><Loader2 size={16} strokeWidth={2} style={{ animation: "auth-spin 1s linear infinite" }} /> Processing…</>
        : children}
    </button>
  );
}

// ─── Divider ──────────────────────────────────────────────────────────────────

export function AuthDivider({ text = "OR CONTINUE WITH" }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, margin: "22px 0" }}>
      <div style={{ flex: 1, height: 1, background: BORDER }} />
      <span style={{ fontSize: "0.6rem", fontWeight: 700, color: T_FAINT, letterSpacing: "0.1em", whiteSpace: "nowrap" }}>{text}</span>
      <div style={{ flex: 1, height: 1, background: BORDER }} />
    </div>
  );
}

// ─── Social icons ─────────────────────────────────────────────────────────────

export function GoogleIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
      <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
    </svg>
  );
}

export function MicrosoftIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
      <rect x="0"   y="0"   width="8.5" height="8.5" fill="#F25022"/>
      <rect x="9.5" y="0"   width="8.5" height="8.5" fill="#7FBA00"/>
      <rect x="0"   y="9.5" width="8.5" height="8.5" fill="#00A4EF"/>
      <rect x="9.5" y="9.5" width="8.5" height="8.5" fill="#FFB900"/>
    </svg>
  );
}

export function OrcidIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 32 32" fill="none">
      <circle cx="16" cy="16" r="16" fill="#A6CE39"/>
      <rect x="9" y="7" width="3" height="18" rx="1" fill="white"/>
      <circle cx="10.5" cy="5.5" r="2" fill="white"/>
      <path d="M14 7h5.5C23.6 7 27 11 27 16s-3.4 9-7.5 9H14V7z" fill="white"/>
      <path d="M17 10.5h2c2.2 0 4 2.4 4 5.5s-1.8 5.5-4 5.5h-2V10.5z" fill="#A6CE39"/>
    </svg>
  );
}

// ─── Social button row ────────────────────────────────────────────────────────

function SocialBtn({ icon, label, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        width: "100%", height: 48,
        display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
        border: `1.5px solid ${BORDER}`, background: "#fff", color: T_MAIN,
        borderRadius: 10, fontSize: "0.875rem", fontWeight: 500,
        cursor: "pointer", transition: "border-color 150ms, background 150ms",
        fontFamily: "inherit", letterSpacing: "-0.005em",
      }}
      onMouseEnter={function(e) { e.currentTarget.style.borderColor = "#94a3b8"; e.currentTarget.style.background = BG; }}
      onMouseLeave={function(e) { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.background = "#fff"; }}
    >
      {icon}
      {label}
    </button>
  );
}

export function SocialButtons({ onGoogle, onOrcid }) {
  function comingSoon(name) { toast.info(name + " login coming soon."); }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <SocialBtn icon={<GoogleIcon />}    label="Continue with Google"    onClick={onGoogle} />
      <SocialBtn icon={<MicrosoftIcon />} label="Continue with Microsoft" onClick={function() { comingSoon("Microsoft"); }} />
      <SocialBtn icon={<OrcidIcon />}     label="Continue with ORCID"     onClick={onOrcid || function() { comingSoon("ORCID"); }} />
    </div>
  );
}

// ─── Error banner ─────────────────────────────────────────────────────────────

export function ErrorBanner({ error, testId }) {
  if (!error) return null;
  return (
    <div
      data-testid={testId}
      style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "12px 14px", background: "#FFF1F2", border: "1px solid #FED7D7", borderRadius: 10, fontSize: "0.84rem", color: "#8A1538", lineHeight: 1.55 }}
    >
      <AlertCircle size={14} strokeWidth={1.5} style={{ flexShrink: 0, marginTop: 1, color: "#EF4444" }} />
      {error}
    </div>
  );
}

// ─── Success state ────────────────────────────────────────────────────────────

export function SuccessState({ icon, color = "#059669", bg = "#ECFDF5", title, subtitle, children }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ width: 64, height: 64, borderRadius: "50%", background: bg, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px" }}>
        {React.cloneElement(icon, { size: 28, strokeWidth: 1.5, style: { color } })}
      </div>
      <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1.5rem", fontWeight: 700, color: T_MAIN, margin: "0 0 10px", letterSpacing: "-0.02em", lineHeight: 1.2 }}>
        {title}
      </h2>
      <p style={{ fontSize: "0.875rem", color: T_MID, margin: "0 0 28px", lineHeight: 1.7 }}>
        {subtitle}
      </p>
      {children}
    </div>
  );
}

// ─── Footer note ──────────────────────────────────────────────────────────────

export function AuthFooter({ children }) {
  return (
    <p style={{ fontSize: "0.84rem", color: T_MID, marginTop: 24, textAlign: "center", lineHeight: 1.6 }}>
      {children}
    </p>
  );
}

export function AuthLink({ to, children, testId }) {
  return (
    <Link
      to={to}
      data-testid={testId}
      style={{ color: NAVY, fontWeight: 600, textDecoration: "none", transition: "opacity 150ms" }}
      onMouseEnter={function(e) { e.currentTarget.style.opacity = "0.7"; }}
      onMouseLeave={function(e) { e.currentTarget.style.opacity = "1"; }}
    >
      {children}
    </Link>
  );
}

// ─── Terms note ───────────────────────────────────────────────────────────────

export function TermsNote() {
  return (
    <p style={{ fontSize: "0.75rem", color: T_FAINT, textAlign: "center", lineHeight: 1.65, margin: 0 }}>
      By continuing you agree to our{" "}
      <Link to="/terms" style={{ color: T_MID, textDecoration: "underline" }}>Terms of Service</Link>
      {" "}and{" "}
      <Link to="/privacy" style={{ color: T_MID, textDecoration: "underline" }}>Privacy Policy</Link>.
    </p>
  );
}

// ─── Checkbox ────────────────────────────────────────────────────────────────

export function AuthCheckbox({ checked, onChange, children }) {
  return (
    <label style={{ display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer", fontSize: "0.84rem", color: T_MID, lineHeight: 1.5 }}>
      <div style={{ position: "relative", flexShrink: 0, marginTop: 1 }}>
        <input
          type="checkbox"
          checked={checked}
          onChange={onChange}
          style={{ position: "absolute", opacity: 0, width: 18, height: 18, margin: 0, cursor: "pointer" }}
        />
        <div style={{ width: 18, height: 18, borderRadius: 5, border: `1.5px solid ${checked ? NAVY : BORDER}`, background: checked ? NAVY : "#fff", display: "flex", alignItems: "center", justifyContent: "center", transition: "all 150ms" }}>
          {checked && <CheckCircle2 size={12} strokeWidth={2.5} style={{ color: "#fff" }} />}
        </div>
      </div>
      {children}
    </label>
  );
}

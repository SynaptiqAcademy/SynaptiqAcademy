/* eslint-disable */
import React, { useState, useRef } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import api, { getErrorMessage } from "../lib/api";
import { TID } from "../lib/testIds";
import { toast } from "sonner";
import {
  AuthLayout, AuthCard, AuthHeader, AuthTitle, PasswordInput,
  AuthButton, BackLink, ErrorBanner, PasswordStrength, NAVY, T_MID,
} from "../components/auth/AuthShared";
import { CheckCircle2 } from "lucide-react";

export default function ResetPassword() {
  const [sp]       = useSearchParams();
  const navigate   = useNavigate();
  const token      = sp.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm,  setConfirm]  = useState("");
  const [err,      setErr]      = useState("");
  const [done,     setDone]     = useState(false);
  const [loading,  setLoading]  = useState(false);
  const submittingRef = useRef(false);

  async function submit(e) {
    e.preventDefault();
    setErr("");
    if (!token)             { setErr("Missing token. Please use the link from your email."); return; }
    if (password.length < 8){ setErr("Password must be at least 8 characters."); return; }
    if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      setErr("Password must contain at least one letter and one digit."); return;
    }
    if (password !== confirm) { setErr("Passwords do not match."); return; }
    if (submittingRef.current) return;
    submittingRef.current = true;
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: password });
      setDone(true);
      toast.success("Password updated. Please sign in.");
      setTimeout(function() { navigate("/login"); }, 1400);
    } catch (e) {
      setErr(getErrorMessage(e));
    } finally {
      setLoading(false);
      submittingRef.current = false;
    }
  }

  if (done) {
    return (
      <AuthLayout>
        <AuthCard>
          <AuthHeader />
          <div className="au-success">
            <div className="au-success-mark">
              <CheckCircle2 size={28} strokeWidth={1.5} style={{ color: NAVY }} />
            </div>
            <h1 className="au-title au-title-sm">
              Password updated
            </h1>
            <p className="au-sub au-gap">
              Your password has been changed successfully. Redirecting you to sign in…
            </p>
            <Link to="/login" className="au-btn au-btn-primary">
              Go to Sign In
            </Link>
          </div>
        </AuthCard>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <AuthCard>
        <AuthHeader />
        <BackLink to="/login" label="Back to Sign In" />

        <AuthTitle
          title="Create a new password"
          subtitle="Choose a strong password for your Synaptiq account."
        />

        <form onSubmit={submit} className="au-fields">
          <div>
            <PasswordInput
              label="New Password"
              value={password}
              onChange={function(e) { setPassword(e.target.value); }}
              required
              testId={TID.resetNewPassword}
              autoComplete="new-password"
            />
            <PasswordStrength password={password} />
          </div>

          <PasswordInput
            label="Confirm Password"
            value={confirm}
            onChange={function(e) { setConfirm(e.target.value); }}
            required
            testId={TID.resetConfirmPassword}
            autoComplete="new-password"
          />

          <ErrorBanner error={err} testId={TID.resetError} />

          <div>
            <AuthButton loading={loading} testId={TID.resetSubmit}>
              Update Password
            </AuthButton>
          </div>
        </form>
      </AuthCard>
    </AuthLayout>
  );
}

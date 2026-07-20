import React, { createContext, useContext, useEffect, useState } from "react";
import api, { getErrorMessage } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = loading, false = anon, obj = authenticated

  // On app load: restore session and fetch CSRF token
  useEffect(() => {
    let mounted = true;

    // Fetch CSRF token first so we have it before any state-changing request
    api.get("/auth/csrf-token").catch(() => {});

    // AUTH-BUG-005: a 401 is a real, authoritative answer ("no session") — but
    // a dropped connection, timeout, or transient 5xx (server mid-restart,
    // brief DB outage) is NOT the same thing as "logged out". Treating both
    // identically used to flip an already-logged-in user to the anonymous/
    // login screen on nothing more than a network blip during page load.
    // Retry the no-response case a couple of times with backoff before
    // concluding anonymous; `user` stays `null` (loading) throughout so
    // ProtectedRoute doesn't redirect prematurely.
    const restoreSession = async (attempt = 0) => {
      try {
        const r = await api.get("/auth/me");
        if (!mounted) return;
        setUser(r.data);
      } catch (e) {
        if (!mounted) return;
        const status = e?.response?.status;
        if (status === 401) {
          setUser(false);
          return;
        }
        const isNoResponse = !e?.response;
        if (isNoResponse && attempt < 2) {
          console.warn("[AUTH] Session restore network error — retrying (%s/2)", attempt + 1);
          setTimeout(() => { if (mounted) restoreSession(attempt + 1); }, 1000 * (attempt + 1));
          return;
        }
        console.warn("[AUTH] Session restore error:", e?.message);
        setUser(false);
      }
    };
    restoreSession();

    return () => { mounted = false; };
  }, []);

  // Handle session expiry events (from axios interceptor)
  useEffect(() => {
    const handler = () => {
      setUser(false);
      api.post("/auth/logout").catch(() => {});
    };
    window.addEventListener("synaptiq:session-expired", handler);
    return () => window.removeEventListener("synaptiq:session-expired", handler);
  }, []);

  const login = async (email, password, remember = false) => {
    try {
      const { data } = await api.post("/auth/login", { email, password, remember });
      setUser(data);
      return data;
    } catch (e) {
      const msg = getErrorMessage(e);
      console.warn("[AUTH] Login failed:", msg);
      throw new Error(msg);
    }
  };

  const register = async (full_name, email, password) => {
    try {
      const { data } = await api.post("/auth/register", { full_name, email, password });
      // Registration doesn't always establish a session — when email
      // verification is required, the backend intentionally skips issuing
      // auth cookies until the user verifies. Setting `user` from the raw
      // register response regardless made every session-dependent consumer
      // (UnreadContext, WebSocket connections, etc.) treat a pending-
      // verification signup as a real login: they'd immediately fire an
      // authenticated call, get a 401 since no cookies exist, and the axios
      // interceptor's refresh-then-logout cascade would wipe the state and
      // silently bounce the user back to /login right after they registered.
      // Confirm via /auth/me instead of assuming.
      try {
        const me = await api.get("/auth/me");
        setUser(me.data);
      } catch (_) {
        setUser(false);
      }
      return data;
    } catch (e) {
      const msg = getErrorMessage(e);
      console.warn("[AUTH] Register failed:", msg);
      throw new Error(msg);
    }
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch (e) {
      console.warn("[AUTH] Logout request failed (still clearing local state):", e?.message);
    }
    setUser(false);
  };

  const refreshMe = async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
      return data;
    } catch (e) {
      console.warn("[AUTH] Failed to refresh user data:", e?.message);
    }
  };

  return (
    <AuthContext.Provider value={{ user, setUser, login, register, logout, refreshMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

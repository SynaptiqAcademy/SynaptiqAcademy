import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export default function AdminProtectedRoute({ children }) {
  const { user } = useAuth();
  const location = useLocation();

  if (user === null) {
    return (
      <div className="min-h-screen bg-[#0B1C35] flex items-center justify-center">
        <div className="text-slate-400 text-sm tracking-widest uppercase">Loading…</div>
      </div>
    );
  }
  if (user === false) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (!user.is_super_admin) {
    return <Navigate to="/discover" replace />;
  }
  return children;
}

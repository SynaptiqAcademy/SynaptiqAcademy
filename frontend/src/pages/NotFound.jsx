/* eslint-disable */
import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Home, Search, Users, FolderOpen, Building2, BookOpen, Sparkles, ArrowLeft,
} from "lucide-react";

const QUICK_LINKS = [
  { to: "/",            label: "Dashboard",     icon: Home       },
  { to: "/search",      label: "Search",        icon: Search     },
  { to: "/researchers", label: "Researchers",   icon: Users      },
  { to: "/projects",    label: "Projects",      icon: FolderOpen },
  { to: "/institution-hub", label: "Institutions", icon: Building2 },
  { to: "/ai-suite",    label: "AI Suite",      icon: Sparkles   },
];

export default function NotFound() {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-6 py-24">
      <div className="w-full max-w-lg">
        {/* Brand mark */}
        <div className="text-[10px] font-mono tracking-[0.2em] uppercase text-slate-400 mb-8">
          Synaptiq
        </div>

        {/* Code */}
        <div className="font-serif text-[5rem] leading-none text-[#0F2847] mb-4 select-none" aria-hidden>
          404
        </div>

        {/* Headline */}
        <h1 className="text-xl font-medium text-slate-900 mb-2">
          This page doesn't exist
        </h1>
        <p className="text-sm text-slate-600 mb-1">
          The path <code className="text-xs bg-slate-200 px-1 py-0.5 text-slate-700 font-mono">{pathname}</code> was not found.
        </p>
        <p className="text-sm text-slate-500 mb-8">
          It may have been moved, renamed, or you may have followed an old link.
        </p>

        {/* Primary action */}
        <div className="flex items-center gap-3 mb-10">
          <Link
            to="/"
            className="inline-flex items-center gap-2 bg-[#0F2847] text-white text-sm px-5 py-2.5 hover:bg-slate-800 transition-colors"
          >
            <Home size={14} strokeWidth={1.5} />
            Back to dashboard
          </Link>
          <button
            onClick={() => window.history.back()}
            className="inline-flex items-center gap-2 border border-slate-300 text-slate-700 text-sm px-5 py-2.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
          >
            <ArrowLeft size={14} strokeWidth={1.5} />
            Go back
          </button>
        </div>

        {/* Quick links */}
        <div className="border-t border-slate-200 pt-8">
          <div className="text-[10px] font-mono tracking-[0.12em] uppercase text-slate-400 mb-4">
            Quick links
          </div>
          <div className="grid grid-cols-2 gap-2">
            {QUICK_LINKS.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className="flex items-center gap-2 text-sm text-slate-700 hover:text-[#0F2847] py-1.5 group transition-colors"
              >
                <Icon size={13} strokeWidth={1.5} className="text-slate-400 group-hover:text-[#0F2847] transition-colors shrink-0" />
                {label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

import React from "react";
import { CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import { NAVY } from "@/lib/tokens";

export default function Unsubscribed() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#FDFDFB] p-8">
      <div className="w-full max-w-md bg-white border border-slate-200 p-10 text-center">
        <CheckCircle2 className="mx-auto text-emerald-500" size={44} strokeWidth={1.3} />
        <h1 className="font-serif text-3xl text-slate-900 mt-5">Unsubscribed</h1>
        <p className="text-sm text-slate-600 mt-3 leading-relaxed">
          You have been successfully unsubscribed from Synaptiq marketing emails.
          <br />
          Transactional emails (account security, verification) will still be delivered.
        </p>
        <div className="mt-8 border-t border-slate-100 pt-6 text-xs text-slate-500">
          Changed your mind?{" "}
          <Link to="/settings" className="text-[#0F2847] underline decoration-dotted hover:text-slate-900">
            Update email preferences
          </Link>{" "}
          in your settings.
        </div>
      </div>
    </div>
  );
}

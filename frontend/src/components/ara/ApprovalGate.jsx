import React, { useState } from "react";
import { ShieldCheck, ShieldX, AlertTriangle } from "lucide-react";
import { approveAction, rejectAction } from "../../services/araEngine";

export default function ApprovalGate({ approval, onResolved }) {
  const [loading, setLoading] = useState(false);
  const [reason, setReason]   = useState("");
  const [mode, setMode]       = useState(null); // null | "reject"

  async function handleApprove() {
    setLoading(true);
    try {
      await approveAction(approval._id);
      onResolved && onResolved("approved");
    } catch (e) {
      alert("Could not approve: " + (e?.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  }

  async function handleReject() {
    setLoading(true);
    try {
      await rejectAction(approval._id, reason);
      onResolved && onResolved("rejected");
    } catch (e) {
      alert("Could not reject: " + (e?.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-md border border-orange-200 bg-orange-50 p-4">
      <div className="flex items-start gap-3 mb-3">
        <AlertTriangle size={18} className="text-orange-500 mt-0.5 shrink-0" />
        <div>
          <p className="text-sm font-semibold text-slate-800">Human Approval Required</p>
          <p className="text-xs text-slate-500 mt-0.5">
            The agent wants to perform an action that requires your explicit sign-off.
          </p>
        </div>
      </div>

      <div className="text-sm text-slate-700 mb-2">
        <span className="font-medium">Action: </span>
        <code className="bg-orange-100 px-1 py-0.5 rounded text-orange-700 text-xs">
          {approval.action}
        </code>
      </div>
      <p className="text-sm text-slate-600 mb-3">{approval.description}</p>

      {approval.data && Object.keys(approval.data).length > 0 && (
        <details className="mb-3">
          <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-600">
            Show proposed data
          </summary>
          <pre className="mt-1 text-xs bg-white border border-slate-200 rounded p-2 overflow-auto max-h-40">
            {JSON.stringify(approval.data, null, 2)}
          </pre>
        </details>
      )}

      <p className="text-xs text-slate-400 mb-3 italic">
        Proposed by: {approval.proposed_by} agent
      </p>

      {mode === "reject" ? (
        <div>
          <textarea
            className="w-full border border-slate-200 rounded p-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-red-300"
            rows={2}
            placeholder="Reason for rejection (optional)"
            value={reason}
            onChange={e => setReason(e.target.value)}
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={handleReject}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500 text-white text-sm rounded hover:bg-red-600 disabled:opacity-50"
            >
              <ShieldX size={14} />
              Confirm Rejection
            </button>
            <button
              onClick={() => setMode(null)}
              disabled={loading}
              className="px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="flex gap-2">
          <button
            onClick={handleApprove}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
          >
            <ShieldCheck size={14} />
            Approve
          </button>
          <button
            onClick={() => setMode("reject")}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-red-200 text-red-600 rounded hover:bg-red-50"
          >
            <ShieldX size={14} />
            Reject
          </button>
        </div>
      )}
    </div>
  );
}

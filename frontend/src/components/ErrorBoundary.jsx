import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { NAVY } from "@/lib/tokens";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("[ErrorBoundary]", error, info?.componentStack);
  }

  reset() {
    this.setState({ hasError: false, error: null });
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    const { fallback } = this.props;
    if (fallback) return fallback;

    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <div className="max-w-md w-full border border-slate-200 bg-white p-8 text-center">
          <AlertTriangle size={32} strokeWidth={1} className="text-amber-500 mx-auto mb-4" />
          <h1 className="font-serif text-2xl text-slate-900 mb-2">Something went wrong</h1>
          <p className="text-sm text-slate-600 mb-6">
            An unexpected error occurred. Refreshing the page usually resolves it.
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => this.reset()}
              className="flex items-center gap-2 border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50 transition-colors"
            >
              <RefreshCw size={14} strokeWidth={1.5} />
              Try again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="bg-[#0F2847] text-white px-4 py-2 text-sm hover:bg-slate-800 transition-colors"
            >
              Reload page
            </button>
          </div>
          {process.env.NODE_ENV === "development" && this.state.error && (
            <pre className="mt-6 text-left text-xs text-slate-500 bg-slate-50 p-3 overflow-auto max-h-48 border border-slate-200">
              {this.state.error.toString()}
            </pre>
          )}
        </div>
      </div>
    );
  }
}

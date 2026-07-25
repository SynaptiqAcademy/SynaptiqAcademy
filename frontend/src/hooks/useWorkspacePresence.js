import { useEffect, useRef, useState } from "react";
import { BACKEND_URL } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

/**
 * useWorkspacePresence — live "who's here" for a workspace (Workspace
 * redesign Phase 9). Connects to the authenticated presence relay at
 * /api/ws/workspace/{id}/presence (backend/routers/presence.py), sends the
 * caller's current `view` (tab) and `typing` flag, and receives a full
 * snapshot of every other connected member on every change.
 *
 * Same reconnect-with-backoff shape as useWikiCollab.js. Presence is
 * inherently ephemeral — there's nothing to persist locally, so unlike the
 * wiki hook there's no local document to fall back to; `status` just
 * reflects whether the live feed is currently reachable.
 */
export function useWorkspacePresence(workspaceId, view, typing = false) {
  const { user } = useAuth();
  const [peers, setPeers] = useState([]);
  const [status, setStatus] = useState("connecting");
  const wsRef = useRef(null);
  const latest = useRef({ view, typing });
  latest.current = { view, typing };

  useEffect(() => {
    if (!workspaceId) return undefined;
    let alive = true;
    let retry = 0;
    let retryTimer = null;
    let ws = null;

    const send = (payload) => {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
    };

    const open = () => {
      if (!alive) return;
      setStatus("connecting");
      const url = BACKEND_URL.replace(/^http/, "ws") + `/api/ws/workspace/${workspaceId}/presence`;
      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        retry = 0;
        setStatus("connected");
        send({ view: latest.current.view, context_id: null, typing: latest.current.typing });
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "presence_snapshot") {
            setPeers((msg.users || []).filter((u) => u.user_id !== user?.id));
          }
        } catch {
          // ignore malformed frames
        }
      };
      ws.onclose = () => {
        if (!alive) return;
        setStatus("offline");
        const delay = Math.min(15000, 1000 * Math.pow(2, retry));
        retry += 1;
        retryTimer = setTimeout(open, delay);
      };
      ws.onerror = () => { try { ws.close(); } catch { /* noop */ } };
    };
    open();

    return () => {
      alive = false;
      if (retryTimer) clearTimeout(retryTimer);
      try { ws && ws.close(); } catch { /* noop */ }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, user?.id]);

  // Push view/typing changes without reconnecting.
  useEffect(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ view, context_id: null, typing }));
    }
  }, [view, typing]);

  return { peers, status };
}

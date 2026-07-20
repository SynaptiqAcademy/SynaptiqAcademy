import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import api, { BACKEND_URL } from "../lib/api";
import { useAuth } from "./AuthContext";

const UnreadContext = createContext({ total: 0, perConv: {}, refresh: () => {}, markConvRead: () => {} });

export function UnreadProvider({ children }) {
  const { user } = useAuth();
  const [total, setTotal] = useState(0);
  const [perConv, setPerConv] = useState({});
  const wsRef = useRef(null);

  const refresh = useCallback(async () => {
    if (!user) return;
    try {
      const [u, c] = await Promise.all([
        api.get("/conversations/unread/count"),
        api.get("/conversations"),
      ]);
      setTotal(u.data.unread || 0);
      const map = {};
      for (const conv of c.data) map[conv.id] = conv.unread || 0;
      setPerConv(map);
    } catch (e) {}
  }, [user]);

  const markConvRead = useCallback((conv_id) => {
    setPerConv((prev) => {
      const had = prev[conv_id] || 0;
      if (!had) return prev;
      setTotal((t) => Math.max(0, t - had));
      return { ...prev, [conv_id]: 0 };
    });
  }, []);

  useEffect(() => {
    if (!user) { setTotal(0); setPerConv({}); return; }
    refresh();
    let alive = true;
    let ws;
    let retry = 0;
    const open = () => {
      if (!alive) return;
      const url = BACKEND_URL.replace(/^http/, "ws") + "/api/ws/user";
      ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onmessage = (ev) => {
        try {
          const e = JSON.parse(ev.data);
          if (e.type === "unread") {
            if (e.reset) {
              markConvRead(e.conversation_id);
            } else if (typeof e.delta === "number") {
              setPerConv((prev) => ({ ...prev, [e.conversation_id]: (prev[e.conversation_id] || 0) + e.delta }));
              setTotal((t) => t + e.delta);
            }
          }
          if (e.type === "notification") {
            window.dispatchEvent(new CustomEvent("synaptiq:notification", { detail: e }));
          }
        } catch (err) {}
      };
      ws.onopen = () => { retry = 0; };
      ws.onclose = () => {
        if (!alive) return;
        const delay = Math.min(15000, 1000 * Math.pow(2, retry));
        retry += 1;
        setTimeout(open, delay);
      };
      ws.onerror = () => { try { ws.close(); } catch (e) {} };
    };
    open();
    return () => { alive = false; try { ws && ws.close(); } catch (e) {} };
  }, [user, refresh, markConvRead]);

  return (
    <UnreadContext.Provider value={{ total, perConv, refresh, markConvRead }}>
      {children}
    </UnreadContext.Provider>
  );
}

export const useUnread = () => useContext(UnreadContext);

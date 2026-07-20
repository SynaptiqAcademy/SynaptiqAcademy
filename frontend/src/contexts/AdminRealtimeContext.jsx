import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { BACKEND_URL } from "../lib/api";
import { useAuth } from "./AuthContext";

const AdminRealtimeContext = createContext({ status: "connecting", lastEvent: null });

export function AdminRealtimeProvider({ children }) {
  const { user } = useAuth();
  const [status, setStatus] = useState("connecting");
  const [lastEvent, setLastEvent] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!user?.is_super_admin) { setStatus("offline"); return; }
    let alive = true;
    let ws;
    let retry = 0;
    const open = () => {
      if (!alive) return;
      setStatus("connecting");
      const url = BACKEND_URL.replace(/^http/, "ws") + "/api/ws/admin";
      ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => { retry = 0; setStatus("connected"); };
      ws.onmessage = (ev) => {
        try {
          const e = JSON.parse(ev.data);
          setLastEvent(e);
          window.dispatchEvent(new CustomEvent("synaptiq:admin-event", { detail: e }));
        } catch (err) {}
      };
      ws.onclose = () => {
        if (!alive) return;
        setStatus("offline");
        const delay = Math.min(15000, 1000 * Math.pow(2, retry));
        retry += 1;
        setTimeout(open, delay);
      };
      ws.onerror = () => { try { ws.close(); } catch (e) {} };
    };
    open();
    return () => { alive = false; try { ws && ws.close(); } catch (e) {} };
  }, [user]);

  return (
    <AdminRealtimeContext.Provider value={{ status, lastEvent }}>
      {children}
    </AdminRealtimeContext.Provider>
  );
}

export const useAdminRealtime = () => useContext(AdminRealtimeContext);

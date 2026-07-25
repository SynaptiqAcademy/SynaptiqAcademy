import { useEffect, useRef, useState } from "react";
import * as Y from "yjs";
import * as syncProtocol from "y-protocols/sync";
import * as awarenessProtocol from "y-protocols/awareness";
import * as encoding from "lib0/encoding";
import * as decoding from "lib0/decoding";
import { BACKEND_URL } from "@/lib/api";

const MESSAGE_SYNC = 0;
const MESSAGE_AWARENESS = 1;

/**
 * useWikiCollab — minimal Yjs WebSocket provider for a wiki page, talking to
 * the backend's authenticated relay at /api/ws/wiki/{pageId}.
 *
 * Hand-rolled instead of the stock y-websocket client because that client
 * assumes a specific reference-server implementation; this follows the same
 * wire protocol (y-protocols sync + awareness, lib0 encoding) against our
 * own minimal relay, which only forwards opaque bytes between clients in
 * the same room — see backend/routers/wiki_collab.py.
 *
 * The Y.Doc works standalone even if the socket never connects (Tiptap's
 * Collaboration extension just edits the local doc) — real-time sync is a
 * bonus layer on top of local editing, never a requirement for the editor
 * to function. `status` reflects that: "connecting" | "connected" | "offline".
 */
export function useWikiCollab(pageId, user) {
  const [status, setStatus] = useState("connecting");
  const ydocRef = useRef(null);
  const awarenessRef = useRef(null);

  if (!ydocRef.current) ydocRef.current = new Y.Doc();
  if (!awarenessRef.current) awarenessRef.current = new awarenessProtocol.Awareness(ydocRef.current);

  useEffect(() => {
    if (!pageId) return undefined;

    const ydoc = ydocRef.current;
    const awareness = awarenessRef.current;
    let ws = null;
    let alive = true;
    let retry = 0;
    let retryTimer = null;

    const colors = ["#0F2847", "#7C3AED", "#059669", "#B45309", "#1D4ED8", "#DB2777"];
    const myColor = colors[Math.abs((user?.id || "").split("").reduce((a, c) => a + c.charCodeAt(0), 0)) % colors.length];
    awareness.setLocalStateField("user", {
      name: user?.full_name || "Someone",
      color: myColor,
    });

    const sendSyncStep1 = () => {
      const enc = encoding.createEncoder();
      encoding.writeVarUint(enc, MESSAGE_SYNC);
      syncProtocol.writeSyncStep1(enc, ydoc);
      ws.send(encoding.toUint8Array(enc));
    };

    const broadcastAwareness = (changed) => {
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      const enc = encoding.createEncoder();
      encoding.writeVarUint(enc, MESSAGE_AWARENESS);
      encoding.writeVarUint8Array(enc, awarenessProtocol.encodeAwarenessUpdate(awareness, changed));
      ws.send(encoding.toUint8Array(enc));
    };

    const onDocUpdate = (update, origin) => {
      if (origin === "remote" || !ws || ws.readyState !== WebSocket.OPEN) return;
      const enc = encoding.createEncoder();
      encoding.writeVarUint(enc, MESSAGE_SYNC);
      syncProtocol.writeUpdate(enc, update);
      ws.send(encoding.toUint8Array(enc));
    };

    const onAwarenessUpdate = ({ added, updated, removed }) => {
      broadcastAwareness(added.concat(updated).concat(removed));
    };

    ydoc.on("update", onDocUpdate);
    awareness.on("update", onAwarenessUpdate);

    const open = () => {
      if (!alive) return;
      setStatus("connecting");
      const url = BACKEND_URL.replace(/^http/, "ws") + `/api/ws/wiki/${pageId}`;
      ws = new WebSocket(url);
      ws.binaryType = "arraybuffer";

      ws.onopen = () => {
        retry = 0;
        setStatus("connected");
        sendSyncStep1();
        broadcastAwareness(Array.from(awareness.getStates().keys()));
      };

      ws.onmessage = (ev) => {
        const dec = decoding.createDecoder(new Uint8Array(ev.data));
        const type = decoding.readVarUint(dec);
        if (type === MESSAGE_SYNC) {
          const enc = encoding.createEncoder();
          encoding.writeVarUint(enc, MESSAGE_SYNC);
          syncProtocol.readSyncMessage(dec, enc, ydoc, "remote");
          if (encoding.length(enc) > 1) ws.send(encoding.toUint8Array(enc));
        } else if (type === MESSAGE_AWARENESS) {
          awarenessProtocol.applyAwarenessUpdate(awareness, decoding.readVarUint8Array(dec), "remote");
        }
      };

      ws.onclose = () => {
        if (!alive) return;
        setStatus("offline");
        const delay = Math.min(15000, 1000 * Math.pow(2, retry));
        retry += 1;
        retryTimer = setTimeout(open, delay);
      };
      ws.onerror = () => { try { ws.close(); } catch (e) {} };
    };

    open();

    return () => {
      alive = false;
      if (retryTimer) clearTimeout(retryTimer);
      ydoc.off("update", onDocUpdate);
      awareness.off("update", onAwarenessUpdate);
      awarenessProtocol.removeAwarenessStates(awareness, [ydoc.clientID], "unmount");
      try { ws && ws.close(); } catch (e) {}
    };
  }, [pageId, user]);

  return { ydoc: ydocRef.current, awareness: awarenessRef.current, status };
}

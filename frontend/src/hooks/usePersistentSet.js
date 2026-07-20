import { useCallback, useState } from "react";

/**
 * usePersistentSet — a Set<string> backed by localStorage, with a toggle
 * helper. Shared by Inbox (Notifications.jsx) and Messages.jsx for their
 * client-only pin/archive state (no backend field exists for either).
 */
export function usePersistentSet(key) {
  const [set, setSet] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      return new Set(raw ? JSON.parse(raw) : []);
    } catch { return new Set(); }
  });
  const toggle = useCallback((id) => {
    setSet(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      try { localStorage.setItem(key, JSON.stringify([...next])); } catch {}
      return next;
    });
  }, [key]);
  return [set, toggle];
}

import { useState, useCallback, useMemo } from "react";

const VERSION = "v1";

function storageKey(userId) {
  return `sq_fex_${VERSION}_${userId}`;
}

function persist(userId, data) {
  try { localStorage.setItem(storageKey(userId), JSON.stringify(data)); } catch {}
}

function hydrate(userId) {
  if (!userId) return null;
  try {
    const raw = localStorage.getItem(storageKey(userId));
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

const FIVE_FALSE = [false, false, false, false, false];

export function useFirstExperience(userId) {
  const [state, setState] = useState(() => {
    const saved = hydrate(userId);
    return saved || { steps: FIVE_FALSE, completed: false };
  });

  const markStep = useCallback((index) => {
    setState((prev) => {
      const steps = [...prev.steps];
      steps[index] = true;
      const completed = steps.every(Boolean);
      const next = { steps, completed };
      if (userId) persist(userId, next);
      return next;
    });
  }, [userId]);

  // Called by the parent after the user profile auto-detects completed steps on mount.
  const markStepSilent = useCallback((index) => {
    setState((prev) => {
      if (prev.steps[index]) return prev; // already done, no-op
      const steps = [...prev.steps];
      steps[index] = true;
      const completed = steps.every(Boolean);
      const next = { steps, completed };
      if (userId) persist(userId, next);
      return next;
    });
  }, [userId]);

  const progress = useMemo(() => state.steps.filter(Boolean).length * 20, [state.steps]);
  const completedCount = state.steps.filter(Boolean).length;

  return { steps: state.steps, isComplete: state.completed, progress, completedCount, markStep, markStepSilent };
}

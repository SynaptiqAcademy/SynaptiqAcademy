/**
 * Copilot Engine — client-side service for the Multi-Agent Research Copilot.
 *
 * Uses fetch streaming (not EventSource) to support POST with body + auth token.
 * Parses SSE frames from the response body and calls event callbacks.
 *
 * Usage:
 *   await streamExecute(userInput, sessionId, {
 *     onPlan:         (plan)   => ...,
 *     onAgentOutput:  (output) => ...,
 *     onQuality:      (result) => ...,
 *     onFinal:        (final)  => ...,
 *     onError:        (err)    => ...,
 *   });
 */

import api from "../lib/api";

// ── Streaming execute ─────────────────────────────────────────────────────────

export async function streamExecute(userInput, sessionId, callbacks = {}) {
  const token = localStorage.getItem("token");
  const { onPlan, onContextReady, onStageStart, onAgentOutput, onQuality, onFinal, onError, onDone } = callbacks;

  let response;
  try {
    response = await fetch("/api/copilot/execute", {
      method:  "POST",
      headers: {
        "Content-Type":  "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify({ user_input: userInput, session_id: sessionId }),
    });
  } catch (err) {
    onError?.({ message: err.message });
    return;
  }

  if (!response.ok) {
    onError?.({ message: `HTTP ${response.status}` });
    return;
  }

  const reader  = response.body.getReader();
  const decoder = new TextDecoder();
  let   buffer  = "";

  const processFrame = (frame) => {
    const trimmed = frame.trim();
    if (!trimmed.startsWith("data:")) return;
    const jsonStr = trimmed.slice(5).trim();
    if (!jsonStr || jsonStr === "[DONE]") return;
    try {
      const { event, data } = JSON.parse(jsonStr);
      switch (event) {
        case "plan":          onPlan?.(data);          break;
        case "context_ready": onContextReady?.(data);  break;
        case "stage_start":   onStageStart?.(data);    break;
        case "agent_output":  onAgentOutput?.(data);   break;
        case "quality_check": onQuality?.(data);       break;
        case "final":         onFinal?.(data);         break;
        case "error":         onError?.(data);         break;
        case "done":          onDone?.();              break;
        default: break;
      }
    } catch (_) {}
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE frames are separated by \n\n
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";  // last element may be incomplete
    frames.forEach(processFrame);
  }
  onDone?.();
}

// ── Non-streaming (fallback) ──────────────────────────────────────────────────

export async function executeSync(userInput, sessionId) {
  try {
    const { data } = await api.post("/copilot/execute/sync", {
      user_input: userInput,
      session_id: sessionId,
    });
    return data;
  } catch {
    return null;
  }
}

// ── Metadata ──────────────────────────────────────────────────────────────────

export async function getAgents() {
  try {
    const { data } = await api.get("/copilot/agents");
    return data;
  } catch {
    return { agents: [], count: 0 };
  }
}

export async function getWorkflows() {
  try {
    const { data } = await api.get("/copilot/workflows");
    return data;
  } catch {
    return { workflows: [] };
  }
}

export async function detectIntent(userInput) {
  try {
    const { data } = await api.post("/copilot/detect-intent", { user_input: userInput });
    return data;
  } catch {
    return null;
  }
}

export async function executeWorkflow(workflowId, userInput, sessionId) {
  try {
    const { data } = await api.post(`/copilot/workflows/${workflowId}`, {
      user_input: userInput,
      session_id: sessionId,
    });
    return data;
  } catch {
    return null;
  }
}

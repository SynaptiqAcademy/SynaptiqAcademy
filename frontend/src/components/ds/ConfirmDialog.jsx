import React, { useEffect, useState } from "react";
import { Modal } from "./Modal";
import { Button } from "./Button";
import { registerConfirmHandler } from "@/lib/confirm";

/**
 * Mounted once at the app root. Renders confirmations requested via
 * confirmDialog() from anywhere, so destructive actions get a styled
 * modal instead of the browser's native confirm() popup.
 */
export function ConfirmDialogHost() {
  const [state, setState] = useState(null);

  useEffect(() => {
    registerConfirmHandler((opts) => new Promise((resolve) => {
      setState({ ...opts, resolve });
    }));
    return () => registerConfirmHandler(null);
  }, []);

  if (!state) return null;

  const close = (result) => {
    state.resolve(result);
    setState(null);
  };

  return (
    <Modal
      open
      onClose={() => close(false)}
      title={state.title || "Are you sure?"}
      description={state.description}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={() => close(false)}>{state.cancelLabel || "Cancel"}</Button>
          <Button variant={state.danger ? "danger" : "primary"} onClick={() => close(true)}>
            {state.confirmLabel || (state.danger ? "Delete" : "Confirm")}
          </Button>
        </>
      }
    />
  );
}

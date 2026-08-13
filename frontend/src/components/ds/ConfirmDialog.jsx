import React, { useEffect, useState } from "react";
import { Modal } from "./Modal";
import { Button } from "./Button";
import { Input } from "./Input";
import { registerConfirmHandler, registerPromptHandler } from "@/lib/confirm";

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

/**
 * Mounted once at the app root, alongside ConfirmDialogHost. Renders
 * single-value text prompts requested via promptDialog() so they get the
 * same styled modal instead of the browser's native prompt() popup.
 */
export function PromptDialogHost() {
  const [state, setState] = useState(null);
  const [value, setValue] = useState("");

  useEffect(() => {
    registerPromptHandler((opts) => new Promise((resolve) => {
      setValue(opts.defaultValue || "");
      setState({ ...opts, resolve });
    }));
    return () => registerPromptHandler(null);
  }, []);

  if (!state) return null;

  const close = (result) => {
    state.resolve(result);
    setState(null);
  };

  return (
    <Modal
      open
      onClose={() => close(null)}
      title={state.title || "Enter a value"}
      description={state.description}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={() => close(null)}>{state.cancelLabel || "Cancel"}</Button>
          <Button variant="primary" onClick={() => close(value)}>{state.confirmLabel || "Save"}</Button>
        </>
      }
    >
      <form onSubmit={(e) => { e.preventDefault(); close(value); }}>
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={state.placeholder}
          autoFocus
        />
      </form>
    </Modal>
  );
}

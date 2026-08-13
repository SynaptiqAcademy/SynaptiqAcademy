let handler = null;
let promptHandler = null;

export function registerConfirmHandler(fn) {
  handler = fn;
}

export function registerPromptHandler(fn) {
  promptHandler = fn;
}

/**
 * confirmDialog("Delete this item?")
 * confirmDialog({ title: "Delete item", description: "This cannot be undone.", danger: true })
 * Returns a Promise<boolean>. Falls back to window.confirm if the dialog host isn't mounted.
 */
export function confirmDialog(opts) {
  const normalized = typeof opts === "string" ? { description: opts } : opts;
  if (!handler) {
    return Promise.resolve(window.confirm(normalized.description || normalized.title || "Are you sure?"));
  }
  return handler(normalized);
}

/**
 * promptDialog("Version summary (optional):")
 * promptDialog({ title: "Reason for suspension", placeholder: "Optional", defaultValue: "" })
 * Returns a Promise<string|null> — null if the user cancels. Falls back to window.prompt
 * if the dialog host isn't mounted.
 */
export function promptDialog(opts) {
  const normalized = typeof opts === "string" ? { title: opts } : opts;
  if (!promptHandler) {
    return Promise.resolve(window.prompt(normalized.title || "", normalized.defaultValue || ""));
  }
  return promptHandler(normalized);
}

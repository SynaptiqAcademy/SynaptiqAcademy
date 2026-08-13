let handler = null;

export function registerConfirmHandler(fn) {
  handler = fn;
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

// Suppress non-actionable DataCloneError from PerformanceServerTiming in some browsers.
window.addEventListener("error", function(e) {
  if (
    e.error instanceof DOMException &&
    e.error.name === "DataCloneError" &&
    e.message &&
    e.message.includes("PerformanceServerTiming")
  ) {
    e.stopImmediatePropagation();
    e.preventDefault();
  }
}, true);

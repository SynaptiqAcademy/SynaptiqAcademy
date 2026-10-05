/**
 * AI credit price list, loaded once from the server catalogue
 * (GET /api/billing/credit-usage-catalogue). Costs are never hardcoded in
 * the frontend — the backend charges by the same table.
 */
import api from "@/lib/api";

let _promise = null;

export function loadCreditCatalogue() {
  if (!_promise) {
    _promise = api.get("/billing/credit-usage-catalogue")
      .then((r) => r.data || { display: [], operations: {} })
      .catch(() => { _promise = null; return { display: [], operations: {} }; });
  }
  return _promise;
}

"""SYNAPTIQ Transactional Email System.

Package layout:
  tokens.py        — design tokens (colors, spacing, typography)
  components.py    — reusable HTML fragments (header, cards, buttons, banners...)
  layout.py         — assembles components into a full responsive/dark-mode HTML doc
  plaintext.py      — the text-email mirror of components.py
  categories.py     — EmailCategory + preference-gate logic
  i18n.py           — string catalog (English default, ready for more locales)
  templates/        — one module per email (welcome, verification, getting_started, ...)

Sending lives in services/email_service.py (Resend transport, retries, delivery
log) and is queued via worker/handlers.py's "email.send" job — see send.py in
this package for the queueing helper used by trigger sites.
"""

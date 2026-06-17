# Deferred Work

## IHP Report Form — pre-existing issues

1. ~~**`actions.py`** — No server-side enforcement of 250-char limit~~ → Fixed in e8213c4

2. **`actions.py:2030`** — `outcomes` not in required-field validation for non-draft submissions. The template has no `required` attribute or `*` indicator on the field, suggesting it's intentionally optional. Leave as-is.

3. **`report.html`** — Textareas lack server-side error rendering pattern. Controller uses JSON responses only, so form is never re-rendered with field values on error. Pattern-matches all textareas in the form — low priority.

4. **`actions.py`** — Serial error reporting: `ValidationError` raises on first failure only, forcing multiple resubmits when several fields fail simultaneously. CKAN's `ValidationError` supports multi-key dicts — batching would improve UX.

5. **`actions.py`** — No length checks for other single-value text fields (`output`, `key_activity`, `notes`, etc.). Only `description` and `outcomes` have client-side `maxlength`, so enforcement matches the UI intent.

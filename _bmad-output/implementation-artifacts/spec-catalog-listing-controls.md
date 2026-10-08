---
title: 'Clarify catalog listing actions and organization search controls'
type: 'bugfix'
created: '2026-09-15'
status: 'done'
baseline_commit: '6fb1c28f7161182ef2ec2f43c28839202dc1ca61'
context: []
---

<frozen-after-approval reason="user requested these implementation changes directly">

## Intent

**Problem:** Both catalog creation buttons appear in dataset and document listings, confusing users about which content they are creating. The organization sorting control appears below the search field instead of beside it.

**Approach:** Customize the theme's existing listing action to show the current content type only. Align organization search and ordering controls horizontally where space permits and keep a usable layout on narrow screens.

## Boundaries & Constraints

**Always:** Preserve CKAN package creation permissions, translated labels, typed creation routes, existing sorting choices, search query submission and the organization result count. Keep changes focused on the theme. Use Spanish comments and English identifiers.

**Ask First:** Expanding the request to deployment or publishing changes.

**Never:** Change schemas, stored records, authorization policy, or unrelated listing layouts.

</frozen-after-approval>

## Code Map

- `ckanext/theme_ejemplo/templates/package/search.html` — theme override currently delegates primary actions to schemingdcat through `super()`.
- `../ckanext-schemingdcat/ckanext/schemingdcat/templates/package/search.html` — inherited action loops over all content types; this file supplies context only.
- `ckanext/theme_ejemplo/templates/organization/index.html` — organization form uses `organization-search-form` and the schemingdcat search snippet.
- `ckanext/theme_ejemplo/templates/schemingdcat/snippets/search_form.html` — existing sort select and direction toggle; preserve behavior.
- `ckanext/theme_ejemplo/public/theme_ejemplo.css` — global search styles and ordering control styles; add organization-specific rules beside those.
- `docs/obsidian-vault/Flujos Importantes.md` — document ownership and expected catalog behavior.

## Tasks & Acceptance

**Execution:**
- [x] `ckanext/theme_ejemplo/templates/package/search.html` — override the action with the current dataset type's translated label and creation route, retaining the permission check.
- [x] `ckanext/theme_ejemplo/public/theme_ejemplo.css` — scope responsive alignment to `organization-search-form`; support CKAN search input markup and keep count below the controls.
- [x] `docs/obsidian-vault/Flujos Importantes.md` — document the theme override and organization layout.
- [x] Verify rendered creation actions for dataset/documents and denied permission, inspect organization layout in Chromium at desktop and mobile widths, and run available existing checks.

**Acceptance Criteria:**
- Given a user who can create packages, when viewing `/dataset/`, then only Add Dataset appears and points to the dataset creation route.
- Given a user who can create packages, when viewing `/documents`, then only Add Documents appears and points to the documents creation route.
- Given a user without package creation permission, when viewing either listing, then no creation action appears.
- Given an organization listing at desktop width, when the search form renders, then its query input and ordering control share one row, with the result count below.
- Given an organization listing at mobile width, when controls render, then they remain usable and stay within the available width.
- Given a query and a chosen organization order, when submitting or changing the order, then the form preserves the query and selected sort value.
- Given another catalog or group listing, when loading its controls, then organization-specific styling does not apply.

## Spec Change Log

## Design Notes

The theme already owns the relevant overrides. Change the presentation here instead of changing the generic type-menu helper in schemingdcat. The schema's dataset type is the route source; do not infer it from the URL or query string. Local CKAN is not installed in the Python environment, so distinguish isolated template rendering and browser previews from a deployed CKAN verification.

## Verification

- `git diff --check` — no whitespace errors.
- `pytest --ckan-ini=test.ini` — attempt the documented suite and report environment limitations if infrastructure or CKAN is unavailable.
- Existing isolated template tests — no regression in supported local checks.
- Jinja rendering of changed action with typed routes and permission variants — one correct action or none.
- Playwright preview using the public organization HTML and local stylesheet — desktop alignment, mobile fit, query and sorting submission.

### Results

- Eight isolated creation-action renderings passed using CKAN Jinja extension classes (dataset/documents, allowed/denied, English/Spanish).
- Existing isolated license template tests: 26 passed. Full CKAN suite unavailable: pytest lacks `--ckan-ini` support; citation test collection also requires the absent DOI package.
- Chromium preview uses public organization HTML and routes only the theme stylesheet to the local file. Controls align horizontally at 1790, 1440 and 1024 px; stack without form overflow at 768, 390 and 320 px.
- Preview screenshots: `output/playwright/organizations-1440.png` and `output/playwright/organizations-390.png`. This does not constitute deployment or authenticated CKAN integration verification.

- Browser search submitted `q=UNESCO` (84 results), changed sorting to `title asc`, and toggled direction to `title desc`; the query stayed intact.
- Review: edge-case hunter found no unhandled edges; acceptance auditor found no deviations. Blind-review assumptions were checked against the inherited template, existing translation catalogs, scoped selectors and rendered form. No correction was required.

## Suggested Review Order

**Creation action**

- Select the current catalog action while preserving permissions and translations.
  [search.html:3](../../ckanext/theme_ejemplo/templates/package/search.html#L3)

**Organization layout**

- Keep search and sorting together on desktop; stack them on mobile.
  [theme_ejemplo.css:4438](../../ckanext/theme_ejemplo/public/theme_ejemplo.css#L4438)

**Documentation**

- Record theme ownership and expected catalog behavior.
  [Flujos Importantes.md:7](../../docs/obsidian-vault/Flujos%20Importantes.md#L7)

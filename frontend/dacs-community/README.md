# DACS Community — IHP-WINS edition

Member platform of the UN Decade of Action for Cryospheric Sciences 2025–2034 (version 3.29 by Alexandre Germouty), running on IHP-WINS instead of Firebase. Served at `/group/dacs/community-of-practice`.

What changed from the Firebase version:

- **No Firebase.** `shims/` replaces `firebase/app`, `firebase/auth` and `firebase/firestore` (see the aliases in `vite.config.ts`). The app code still calls `getDoc`, `setDoc`, `onSnapshot`… and those calls go to the CKAN community API (`ckanext/theme_ejemplo/community.py`).
- **IHP-WINS accounts.** Sign-in, registration, sign-out and password resets use the IHP-WINS pages. The owner role that was tied to one email address now belongs to IHP-WINS sysadmins and the admins of the CKAN group.
- **Same permissions.** `ckanext/theme_ejemplo/community_data/dacs.rules` is the Firebase `firestore.rules`, executed on the server by `community_rules.py`. Only `secretariatOwner()` changed.
- **Paths.** Built files are served from `/dacs-community/` (the theme's public folder); the app's pages live under the group URL (`lib/base.ts`: `BASE` for files, `ROUTE` for pages).

```bash
npm ci
npm run build:ckan   # type check + build into ckanext/theme_ejemplo/public/dacs-community
npm test             # unit tests
npm run test:rules   # the Firebase rules tests, run against the IHP-WINS API (needs Python 3 + SQLAlchemy)
```

Static files (photos, video, logos, templates, Terms of Reference) live in `ckanext/theme_ejemplo/public/dacs-community/assets/` and are not part of the build.

Documentation (Spanish): `docs/obsidian-vault/Comunidad de Practica DACS.md`.

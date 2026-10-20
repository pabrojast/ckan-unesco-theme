# Home page v2 (redesign)

Added by Jorgen Van Der Biest. The IHP-WINS home page design. It keeps every link of the previous home page, reorganised by the platform's areas.

## How it is wired

`templates/home/index.html` renders `home/home_v2.html` in place of `home/custom_layout.html` (one line replaced, marked). There is no setting: this is the home page. `custom_layout.html` is left in the repo unused, so going back is a one-line change in `index.html`.

## Page order

1. Hero: a looping clip (1:40 to 2:07) from the IHP 50th anniversary film, the UNESCO IHP logo, the headline, dataset search and counts. The site header floats over it as it did over the old hero; on screens with a mouse its top bar (Register, Log in, IHP IX, language) folds away and only unfolds when the mouse reaches the top of the page (see below). The pause button (in the counters ribbon) stops the video, and visitors with "reduce motion" see the still poster.
   - About IHP-WINS (`#IHPWINS`) is a panel inside the hero, collapsed by default. The "About IHP-WINS" button sits in the row with the dataset and organization counts; it or a click on the title block opens the panel over the video, and the title moves up. Escape closes it. Links to `#IHPWINS` (section bar) open it and scroll to the top. Without JavaScript the panel is open.
2. Counters: organizations, initiatives, Member States, datasets, documents, page views, downloads, as a ribbon along the bottom edge of the hero video (white type, a thin white line above, no dividers or boxes), with the video pause button on its right. Two rows of four below 1280 px, two columns on phones.
3. Sticky section bar: About, Network, Datasets, Knowledge, Thematic viewers, Water Family, Learning, plus "Contribute data".
4. Network: Member State, organization and initiative hubs, then a navy Contribute band with Log in (only when signed out), Register and IHP-IX progress.
5. Datasets: Data Catalogue and Geospatial Viewer panels, Explore data (Recently added, Trending).
6. Knowledge: featured viewers (with their own thumbnails) and All map rooms, then Rapid Response & Recovery, data stories, AI for Water Management, Open Source Tools.
7. Thematic viewers: the six portals, as a full-width image strip on the navy band.
8. Water Family: news, events, publications.
9. Learning: IHP Open Learning banner, then the courses as a table (course, format, start, provider).

The Spotlight slide deck of the old home page was removed (Jorgen, October 2026). Its five links are elsewhere on the page: About IHP-WINS, the Citizen Science and IoT portals (Thematic viewers), IHP Open Learning (Learning) and the Water Family section.

## Look ("field report")

The page reads like a printed science report rather than a set of cards:

- Type, after caladan.bio (a science site on siteinspire): Albert Sans at regular weight for section and item titles, Albert Sans ExtraBold in small capitals for labels and buttons, IBM Plex Sans for text (as on caladan.bio). caladan.bio uses Area Normal, a paid font, for titles and labels; Albert Sans is the closest free one. Lexend 700 stays for the hero title (as in the IHP-WINS logo). All from Google Fonts, loaded in `home_v2.html`.
- Square corners everywhere, no shadows. Items are separated by thin rules (`#C9D2DB`) and columns by vertical rules, not by boxes.
- Section headers sit on a 12-column grid: a small label, then title and lead stacked on the left, the section banner image on the right. Sections are not numbered. Sections that follow a white section open without a top rule (`.hv2-shead-open`) and with less space above (`.hv2-sec-tight`).
- Colours: navy `#0B2A4A` for the Contribute band and the Thematic band, the IHP-WINS blue `#37B7E7` for accents and gold `#F2B01E` for the Register and Open Learning calls to action.

## Files

New files only:

- `ckanext/theme_ejemplo/home_v2.py`: helpers `home_v2_rapid_response`, `home_v2_data_stories`, `home_v2_short_number`.
- `templates/home/home_v2.html`: the page.
- `public/css/home-v2.css`: styles, all scoped under `.hv2`.
- `public/js/home-v2.js`: video pause, About panel, header top bar, tabs, section bar.
- `public/home_v2/`: hero video (7 MB desktop, 2.7 MB mobile), poster, logos, the two Datasets panel images (`catalogue.webp`, `geospatial-globe.webp`: the earth from space, moved to the right of the picture so it clears the text).

Changes to existing files, each marked "Home page v2 (added by Jorgen Van Der Biest)":

- `plugin.py`: 2 lines (import, register helpers).
- `templates/home/index.html`: renders `home_v2.html` instead of `custom_layout.html`.
- `templates/header.html`: the IHP-WINS logo next to the UNESCO logo, only on the home page.

On the home page only, `home-v2.css` also restyles Pablo's header through `body:has(#hv2)` selectors (no change to `theme_ejemplo.css`): it stays transparent over the video instead of turning blue on hover, has a thin line under the top links with UNESCO on the left, a plain "Log in", the menu on one row from 1260 px, and square menu links that underline on hover, with Home marked by a bottom edge in the IHP-WINS logo blue (`#37B7E7`). The header only stays transparent at exactly `/`, as in Pablo's `header.html`; with a query string (for example `/?lang=fr`) it keeps its blue background.

On the home page the UNESCO text link at the left of the top bar is left out (the UNESCO logo stays in the row below). From 992 px, on screens with a mouse (`@media (hover: hover) and (pointer: fine)`), the top bar folds away and the row with the logos and the menu moves up to the top. `home-v2.js` unfolds it (body class `hv2-topbar-open`) when the mouse is in the top 20 px of the page, or when keyboard focus enters it, and keeps it open while the mouse stays anywhere in the header. Without JavaScript any hover on the header unfolds it. Touch screens keep the top bar as it was.

## Data

It uses the same helpers as the current home page: `theme_ejemplo_site_statistics`, `get_tracking_totals`, `get_recently_added`, `get_popular_datasets`, `get_popular_resources`, `theme_ejemplo_get_featured_viewers`, `get_recent_water_news`, `get_recent_water_events`, `get_featured_publications`, `get_latest_courses`. Rapid response pages and data stories come from ckanext-pages (`ckanext_pages_list` with `page_type=rapid-response`, `data_story_list`), read anonymously so drafts never show.

## Notes

- Accents (focus outlines, the Home underline) use the IHP-WINS logo blue `#37B7E7`.

- `theme_ejemplo.css` sets `p { color: #212529 !important }`, so the page uses `<div class="hv2-lead">` instead of `<p>` for running text.
- The videos could also be served from blob storage instead of the repo: change the two `<source>` lines in `home_v2.html`.
- Tested locally on CKAN 2.10.9 with ckanext-pages (RapidResponseAndRecovery) at 1440, 1100 and 390 px.

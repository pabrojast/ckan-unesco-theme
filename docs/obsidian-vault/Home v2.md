# Home page v2 (redesign)

Added by Jorgen Van Der Biest. The IHP-WINS home page design. It keeps every link of the previous home page, reorganised by the platform's areas.

## How it is wired

`templates/home/index.html` renders `home/home_v2.html` in place of `home/custom_layout.html` (one line replaced, marked). There is no setting: this is the home page. `custom_layout.html` is left in the repo unused, so going back is a one-line change in `index.html`.

## Page order

1. Hero: a looping clip (1:40 to 2:07) from the IHP 50th anniversary film, the UNESCO IHP logo, the headline, dataset search and counts. The site header floats over it as it did over the old hero. The pause button (in the counters ribbon) stops the video, and visitors with "reduce motion" see the still poster.
   - About IHP-WINS (`#IHPWINS`) is a panel inside the hero, collapsed by default. The "About IHP-WINS" button sits under the dataset counts; it or a click on the title block opens the panel over the video, and the title moves up. Escape closes it. Links to `#IHPWINS` (section bar, first spotlight slide) open it and scroll to the top. Without JavaScript the panel is open.
2. Counters: organizations, initiatives, Member States, datasets, documents, page views, downloads, as a ribbon along the bottom edge of the hero video (white type, thin white rules, no box), with the video pause button on its right. Two rows of four below 1280 px, two columns on phones.
3. Sticky section bar: About, Network, Datasets, Knowledge, Thematic viewers, Water Family, Learning, Spotlight, plus "Contribute data".
4. Network: Member State, organization and initiative hubs, Register, IHP-IX.
5. Datasets: Data Catalogue and Geospatial Viewer tiles, Explore data (Recently added, Trending).
6. Knowledge: featured viewers, Rapid Response & Recovery, data stories, AI for Water Management, Open Source Tools.
7. Thematic viewers: the six portals.
8. Water Family: news, events, publications.
9. Learning: IHP Open Learning and courses.
10. Spotlight: the original five-slide deck.

## Files

New files only:

- `ckanext/theme_ejemplo/home_v2.py`: helpers `home_v2_rapid_response`, `home_v2_data_stories`, `home_v2_short_number`.
- `templates/home/home_v2.html`: the page.
- `public/css/home-v2.css`: styles, all scoped under `.hv2`.
- `public/js/home-v2.js`: video pause, About panel, tabs, slide deck, section bar.
- `public/home_v2/`: hero video (7 MB desktop, 2.7 MB mobile), poster, logos, two tile images.

Changes to existing files, each marked "Home page v2 (added by Jorgen Van Der Biest)":

- `plugin.py`: 2 lines (import, register helpers).
- `templates/home/index.html`: renders `home_v2.html` instead of `custom_layout.html`.
- `templates/header.html`: the IHP-WINS logo next to the UNESCO logo, only on the home page.

On the home page only, `home-v2.css` also restyles Pablo's header through `body:has(#hv2)` selectors (no change to `theme_ejemplo.css`): it stays transparent over the video instead of turning blue on hover, has a thin line under the top links with UNESCO on the left, a plain "Log in", the menu on one row from 1260 px, and rounded menu buttons with Home marked by a bottom edge in the IHP-WINS logo blue (`#37B7E7`). The header only stays transparent at exactly `/`, as in Pablo's `header.html`; with a query string (for example `/?lang=fr`) it keeps its blue background.

## Data

It uses the same helpers as the current home page: `theme_ejemplo_site_statistics`, `get_tracking_totals`, `get_recently_added`, `get_popular_datasets`, `get_popular_resources`, `theme_ejemplo_get_featured_viewers`, `get_recent_water_news`, `get_recent_water_events`, `get_featured_publications`, `get_latest_courses`. Rapid response pages and data stories come from ckanext-pages (`ckanext_pages_list` with `page_type=rapid-response`, `data_story_list`), read anonymously so drafts never show.

## Notes

- Accents (focus outlines, the Home underline, the spotlight progress bar) use the IHP-WINS logo blue `#37B7E7`.

- `theme_ejemplo.css` sets `p { color: #212529 !important }`, so the page uses `<div class="hv2-lead">` instead of `<p>` for running text.
- The videos could also be served from blob storage instead of the repo: change the two `<source>` lines in `home_v2.html`.
- Tested locally on CKAN 2.10.9 with ckanext-pages (RapidResponseAndRecovery) at 1440 px and 390 px.

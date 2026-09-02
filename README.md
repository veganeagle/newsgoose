# NewsGoose 🪿

A personal, ad-free news dashboard that pulls headlines from a curated list of RSS feeds and presents them two different ways depending on whether you're on a phone or a desktop: a swipeable single-column **reader** on mobile, and a fixed four-tile **dashboard** on desktop. It also shows a small local weather bar on desktop and can be installed as a Progressive Web App on a phone's home screen.

Live at **[newsgoose.ca](https://newsgoose.ca)**.

- No login, no accounts, no tracking, no ads.
- No database — everything is fetched live from RSS feeds and kept in memory.
- Built for one user (its author) as a personal tool; the architecture intentionally trades scalability for simplicity.

---

## Table of contents

- [Features](#features)
- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [Running locally](#running-locally)
- [Configuration](#configuration)
- [Adding or editing sources](#adding-or-editing-sources)
- [Topic thumbnails](#topic-thumbnails)
- [Mobile vs. desktop: two different apps in one codebase](#mobile-vs-desktop-two-different-apps-in-one-codebase)
- [Progressive Web App](#progressive-web-app)
- [Deployment](#deployment)
- [Redeploying changes](#redeploying-changes)
- [Known limitations & design decisions](#known-limitations--design-decisions)
- [Credits](#credits)

---

## Features

- **Curated multi-source feed** — currently pulls from 26 Canadian and international RSS sources across categories like National, Toronto, Business, Sports, Quebec (French), Science, Lifestyle, and more.
- **"My Sources" personalization** — pick which sources matter to you; the choice is stored in the browser (`localStorage`), not on the server, so it's per-device and requires no account.
- **Desktop dashboard mode** — a fixed 2×2 grid of tiles you assign via a drag-and-drop "Layout" modal, plus a live local weather bar.
- **Mobile reader mode** — a single scrollable column of collapsible source tiles, with a category browser in a hamburger menu.
- **Auto-refreshing content** — a background poll loop refreshes every source's articles server-side every 5 minutes; the browser re-pulls each visible tile on the same cadence via `htmx`, so the page never needs a manual reload.
- **Weather** — current conditions and a same-day outlook (desktop only), via Open-Meteo, refreshed every 30 minutes. Falls back to a fixed configured location; can optionally use the browser's geolocation on desktop for a more precise local label.
- **Installable PWA** — has a manifest and service worker, so it can be added to a phone's home screen and opens like a native app.
- **Topic thumbnails** — articles without a usable image get a rule-based fallback thumbnail (e.g. anything tagged/titled about a particular politician, team, or topic gets a matching icon) instead of a blank box.

## How it works

There is **no database**. The whole app is a single FastAPI process with three layers of state, all in memory:

```
app/data/sources.json  ──(loaded once at startup)──►  source_repo (static list)
                                                              │
                                                     poll_service (every 5 min)
                                                              │
                                        feed_service (httpx + feedparser) fetches each RSS feed
                                                              │
                                    normalize_service parses entries into Article objects,
                                       dedupes by guid/url, sorts newest-first, picks a
                                       thumbnail (real image → topic-thumb fallback)
                                                              │
                                                              ▼
                                      article_repo (in-memory dict, source_key → articles)
                                                              │
                          routes/tiles.py renders a tile partial from whatever's currently cached
```

Weather works the same way: `poll_service` refreshes it every 30 minutes and caches the single latest snapshot in `weather_repo`.

Because everything lives in memory, **restarting the process clears all cached articles/weather** — they simply repopulate on the next poll cycle (or immediately for weather, which is fetched inline on the client's first request if the cache is empty). Restarting does *not* affect "My Sources" personalization, since that lives in the browser, not the server.

The frontend has almost no build step: server-rendered HTML (Jinja2) for the page shell and each tile, `htmx` to swap tile/weather partials in on a timer without full page reloads, and plain JavaScript for everything client-local (My Sources, the layout modal, mobile category menu, opening/closing tiles).

## Project structure

```
app/
  main.py                    # FastAPI app, lifespan (starts/stops the poll loop), static mount, misc routes
  config.py                  # constants: poll/refresh intervals, weather defaults (env-overridable)
  models.py                  # Article and Source dataclasses

  routes/
    dashboard.py             # GET /dashboard — renders the page shell
    tiles.py                 # GET /tile/{source_key} — renders one tile partial
    weather.py                # GET /weather — renders the weather bar partial

  services/
    poll_service.py          # the background loop: fetch → normalize → store, every 5 min
    feed_service.py          # fetches and parses a single RSS feed
    normalize_service.py     # entry → Article, dedupe, thumbnail fallback matching
    weather_service.py       # Open-Meteo fetch + Nominatim reverse-geocoding

  repositories/
    article_repo.py          # in-memory dict: source_key -> list[Article]
    source_repo.py           # loads app/data/sources.json once; filter/sort helpers
    weather_repo.py          # in-memory single WeatherSnapshot

  data/
    sources.json             # the list of RSS sources (see "Adding or editing sources")
    topic_thumbs.json        # fallback-thumbnail matching rules (see "Topic thumbnails")

  templates/
    dashboard.html           # page shell + all client-side JS (My Sources, layout modal, mobile menu)
    partials/
      tile.html              # one source's tile, plus its open/close JS
      weather.html           # the weather bar partial

  static/
    site.css                 # all styling — desktop and mobile layouts live in one file,
                              # split by an `@media (max-width: 900px)` block
    sw.js                    # service worker (see "Progressive Web App")
    manifest.json            # PWA manifest
    icon.png, icon_large.png
    topic_thumbs/             # fallback thumbnail images referenced by topic_thumbs.json
    .well-known/
      assetlinks.json        # Android App Links verification

documentation/                # early design notes from before this README existed
requirements.txt
```

## Running locally

Requires Python 3.11+.

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

Then open **http://127.0.0.1:8010/dashboard** (the bare `/` route just redirects there).

There's no `.env` file needed to get something running — everything has a sane default (see [Configuration](#configuration)). The poll loop kicks off on startup, so the dashboard will show "Loading…" tiles for a few seconds on first run until the first poll cycle completes.

To see the mobile layout, either open dev tools' device toolbar, or just narrow the browser window below 900px — the two layouts are pure CSS media-query variants of the same markup (with one exception: geolocation is intentionally never requested below that width, since the weather bar that uses it is desktop-only).

## Configuration

All of these are read in `app/config.py`. Everything except the weather location has a hardcoded default (no env var).

| Setting | Env var | Default | Meaning |
|---|---|---|---|
| Poll interval | — | `300`s | How often the background loop re-fetches every source's RSS feed |
| Tile refresh | — | `300`s | How often the browser re-pulls a visible tile via `htmx` |
| Max items per source | — | `50` | Articles kept per source after each poll (oldest dropped) |
| Weather refresh | — | `1800`s | How often the cached weather snapshot is refreshed |
| Weather latitude | `WEATHER_LAT` | `43.7696` | Fallback location used when no browser geolocation is available |
| Weather longitude | `WEATHER_LON` | `-79.1873` | (default is Scarborough, ON) |
| Weather label | `WEATHER_LABEL` | `Scarborough, ON` | Display label for the fallback location |

## Adding or editing sources

Edit `app/data/sources.json` — no code changes needed. It's a flat JSON array; the app reads it once at startup, so a code reload (`--reload`) or a restart is needed to pick up changes.

```json
{
  "source_key": "cbc",              // unique, used in URLs and localStorage — don't reuse or rename casually
  "display_name": "CBC News",       // shown in the UI
  "feed_url": "https://www.cbc.ca/webfeed/rss/rss-topstories",
  "tile_type": "news",              // currently only "news" is used, reserved for future tile variants
  "icon_url": "https://www.cbc.ca/favicon.ico",
  "is_enabled": true,               // set false to hide without deleting
  "sort_order": 1,                  // controls default ordering in "My Sources" and the category menu
  "categories": ["National"]        // one source can belong to multiple categories
}
```

A source with no working favicon can point `icon_url` at Google's favicon proxy as a quick fallback, e.g. `https://www.google.com/s2/favicons?sz=64&domain=example.com` (several existing entries do this).

Renaming a `source_key` orphans any user's existing "My Sources" localStorage entry referencing the old key — the app silently drops unknown keys on load (see `loadSlotAssignments()` in `dashboard.html`), so the source would just quietly disappear from a returning visitor's saved list rather than error.

## Topic thumbnails

When an article has no usable image (no media enclosure, no `<img>` in its summary), `normalize_service.py` looks it up against `app/data/topic_thumbs.json` — a priority-ordered list of match rules:

```json
{
  "match_type": "category",              // "category" (matches feed-provided tags/categories) or "title" (substring match on the headline)
  "pattern": "trump",                    // case-insensitive substring to match
  "thumbnail_url": "/static/topic_thumbs/donald_trump.png",
  "priority": 10                         // higher wins when multiple rules match
}
```

Add a new image to `app/static/topic_thumbs/` and a matching rule to get automatic thumbnails for a recurring topic (a particular politician, team, ongoing story, etc.) across every source, without touching any source-specific logic.

## Mobile vs. desktop: two different apps in one codebase

This is the app's central design idea, and it's worth understanding before touching `site.css` or `dashboard.html` — the two modes share markup but diverge sharply in layout and behavior at the `900px` breakpoint.

**Desktop (`> 900px`) — a dashboard:**
- A fixed 2×2 grid of exactly 4 tiles (`DESKTOP_SLOT_COUNT` in `dashboard.html`), each independently auto-refreshing.
- Which sources fill those 4 slots is chosen via the "Layout" button → a modal where you drag sources from a full list into numbered frames.
- A weather bar along the bottom, optionally using the browser's geolocation for a precise label (see below).
- The page itself never scrolls (`overflow: hidden` on `html, body`) — only the inside of each tile scrolls independently. Nothing overlaps because nothing is faked with `position: fixed`.

**Mobile (`≤ 900px`) — a reader:**
- A single vertical list of tiles for either "My Sources" or a category, chosen from a hamburger menu.
- Tapping a tile's header expands it into a full-article reading view (hiding the others); a sticky "✕ Close" bar returns you to the list.
- Drag-to-reorder (via Sortable.js) when viewing "My Sources".
- **No weather, and no geolocation prompt** — the weather bar is hidden entirely on mobile, and the app deliberately never calls `navigator.geolocation` below the breakpoint, since there'd be nothing to use it for.

The mobile layout is implemented as a **locked flex frame**, not a scrolling page with a floating header — this matters enough to call out explicitly, because getting it wrong is subtle and was the source of a real, hard-to-reproduce bug during development:

> An earlier version used `position: fixed` for the mobile header with the whole page scrolling underneath it, sized against `100vh`. That combination is fragile on real mobile browsers (both Safari and Chrome-iOS, since Chrome-iOS is a WebKit wrapper) because the address bar dynamically resizes the *visible* viewport as you scroll — `100vh` doesn't track that, and it doesn't reproduce at all by narrowing a desktop browser window, since desktop windows have no such dynamic toolbar. It manifested as list content sliding behind the header after closing an open tile.
>
> The current layout instead makes `body` a `100dvh` flex column with the header as a normal, space-reserving flex item (never overlaid) and `.dashboard-page` as the one real scroll container — the same "page never scrolls, only content areas do" principle desktop already used. If you're tempted to reach for `position: fixed` or a `calc(100vh - Npx)` height on mobile, reconsider — it's very likely solving the wrong problem.

One more non-obvious detail if you touch `.mobile-close-tab`'s sticky positioning: `.tile` must keep `overflow: visible` on mobile. The desktop rule sets `overflow: hidden` (to clip content to its rounded corners), and per the CSS spec, `overflow: hidden` on an ancestor becomes a sticky element's positioning reference frame instead of the actual scrolling container further up — so without the mobile override, the close bar silently stops sticking and just scrolls away.

## Progressive Web App

`app/static/sw.js` implements three different caching strategies depending on the request:

| Path | Strategy | Why |
|---|---|---|
| `/dashboard` | Network-first, cache fallback | Always want fresh data; only fall back to cache if offline |
| `/tile/*` | Network-only | Article lists must never be stale; an offline tile just renders empty |
| `/static/*`, `/sw.js` | Cache-first | Static assets rarely change and don't need a network round-trip |

**Operational gotcha:** because `site.css` is served cache-first, a plain deploy of a CSS change won't reach browsers that already have the old file cached (or an installed PWA that's still running from memory). `dashboard.html` references it as `/static/site.css?v=N` specifically so that bumping `N` forces a fetch of a URL the cache has never seen. **Whenever `site.css` changes, bump that version query string** — the fastest way to fail to reproduce a "fix" is to test with a stale cached copy of it.

The service worker's own `CACHE_NAME` is a fixed string (`newsgoose-v1`) that has never needed to change, since its `activate` handler only prunes caches with a *different* name — if that ever needs bumping (e.g. to force-invalidate everything at once), remember its cleanup logic only fires when the name actually changes.

## Deployment

Currently deployed on a single **GCP Compute Engine `e2-micro` instance** (`us-central1`), chosen specifically to fit inside GCP's **Always Free tier** — the app's resource needs are trivial (single low-traffic personal user, no database), so this runs at $0/month as long as the instance stays within the free-tier criteria:

- Machine type exactly `e2-micro`
- Region one of `us-west1`, `us-central1`, `us-east1`
- Boot disk: Standard persistent disk (`pd-standard`), ≤30GB
- Only one such instance per billing account claiming the free tier
- A static external IP is free as long as it stays attached to a running instance

(Note: the *instance-creation cost estimate* in the GCP console does **not** reflect the Always Free discount — it always shows standard on-demand pricing. The actual discount shows up as a credit on the real bill, checkable under Billing → Reports.)

On the box itself:

- **Runtime**: a Python venv at `/opt/newsgoose/.venv`, app code at `/opt/newsgoose`.
- **Process manager**: a systemd service (`newsgoose.service`) runs `uvicorn app.main:app --host 127.0.0.1 --port 8010` with `Restart=always`, enabled on boot.
- **Reverse proxy / TLS**: nginx proxies `newsgoose.ca` / `www.newsgoose.ca` to `127.0.0.1:8010`; certificate issued and auto-renewed via Certbot (Let's Encrypt).
- **DNS**: `newsgoose.ca` is registered and DNS-hosted at Namecheap — both the apex and `www` are plain `A` records pointing at the instance's static IP (no CNAME chaining, no dependency on any other domain).

## Redeploying changes

There's no CI/CD — deploys are manual and simple, which is intentional given the app's scale:

```bash
# from the repo root, package the app (excluding dev cruft)
tar -czf newsgoose.tar.gz --exclude='.git' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.venv' app requirements.txt documentation

# copy it to the instance and unpack over the existing deploy
gcloud compute scp newsgoose.tar.gz newsgoose-micro-e2-0001:/tmp/newsgoose.tar.gz --zone=us-central1-a
gcloud compute ssh newsgoose-micro-e2-0001 --zone=us-central1-a --command="
  sudo tar -xzf /tmp/newsgoose.tar.gz -C /opt/newsgoose &&
  sudo chown -R \$(whoami):\$(whoami) /opt/newsgoose &&
  sudo systemctl restart newsgoose
"
```

If `requirements.txt` changed, run `.venv/bin/pip install -r requirements.txt` on the box before restarting. If `site.css` changed, don't forget the cache-buster bump mentioned above *before* packaging — otherwise the redeploy is invisible to anyone with a cached copy.

## Known limitations & design decisions

These are deliberate trade-offs for a single-user personal tool, not oversights:

- **No database, no persistence of articles/weather.** A process restart loses the cache; it silently repopulates within one poll cycle. This was an explicit simplification — there was never a need to keep article history.
- **No authentication.** The dashboard is public at its URL; there's nothing user-specific server-side to protect ("My Sources" is client-only).
- **Single process, no horizontal scaling.** The poll loop is an in-process `asyncio` task, which is why this couldn't move to a scale-to-zero serverless platform without a redesign (there'd be nothing keeping the poll loop alive between requests).
- **Sources are static config, not a CMS.** Adding a source means editing a JSON file and restarting — appropriate for a personal curated list, not for many users managing their own feed lists.

## Credits

- Weather data: [Open-Meteo](https://open-meteo.com/) (no API key required)
- Reverse geocoding: [Nominatim / OpenStreetMap](https://nominatim.openstreetmap.org/)
- [htmx](https://htmx.org/) for partial page updates without a JS framework
- [SortableJS](https://sortablejs.github.io/Sortable/) for mobile drag-to-reorder
- [FastAPI](https://fastapi.tiangolo.com/) + [feedparser](https://feedparser.readthedocs.io/) + [httpx](https://www.python-httpx.org/)

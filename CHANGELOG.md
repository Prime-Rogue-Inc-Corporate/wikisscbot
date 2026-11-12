# Changelog

All notable changes to wikisscbot. Versions follow [semantic versioning](https://semver.org/); times are UTC. The automatic per-run record of data pulls is in [`data/BUILDLOG.md`](data/BUILDLOG.md).

## [Unreleased]

## [1.3.0] — 2026-11-12

### Added
- **Revision History** (`revisionhistory.ca`): the site has its own name and domain. Site identity lives in `config/site.json`; the collector keeps the name wikisscbot. The build writes `docs/CNAME`.
- **Crawlable pages** (`wikisscbot/seo.py`): a pre-rendered summary inside the home page, `years.html` with one page per year, `methodology.html`, `faq.html` and `data.html`. Every number is computed from the data at build time.
- **Metadata**: titles, descriptions, canonical links, Open Graph and Twitter cards, a share image and favicon, and JSON-LD (`WebSite`, `Dataset` with one download per year and its SHA-256, `FAQPage`, breadcrumbs).
- **Discovery files**: `sitemap.xml`, `robots.txt` (search and AI crawlers allowed; `data/manifests/` excluded) and `llms.txt`.
- `index_biographies` in `config/site.json` (default `false`): the crawlable pages leave biographies and not-yet-classified pages out of the most-edited lists. The search is unaffected.
- Backfill extended year by year to 2010.
- **Confirmed attributions** (`config/ranges_confirmed.json`): addresses whose institution has been confirmed with stronger evidence take priority over the range lists, from a stated start date. First entry: 205.193.51.200, Office of the Information Commissioner of Canada.
- **`site` branch**: every workflow run publishes the contents of `docs/` as a single commit on `site`, for hosts that can only serve a branch root.

### Fixed
- **Edits are no longer attributed to an SSC prefix after it was withdrawn.** The prefix list covers every prefix an SSC network announced since the first backfill year, and was applied to every year. Extending the backfill to 2010 pulled in two prefixes that the legacy NRC network (AS25689) announced only around 2010 (`206.167.190.0/23`, `192.70.164.0/24`), which added 315 edits made from those addresses in 2017–2025, long after the announcements ended. `refresh-ranges` now records when each prefix was first and last seen; an edit counts only up to 90 days after the last announcement, and lapsed prefixes are not queried for later years. Each year's `status.json` reports how many edits were excluded this way.

### Changed
- Repository links and the collector's User-Agent point at `Prime-Rogue-Inc-Corporate/wikisscbot` and the new site.
- **Profiles** (`#/profiles`): hand-written analyst pages kept in `web/static/profiles/` (an `index.json` plus one HTML fragment per profile) and copied into the static build. First profile: **DRELAN-SPARKY**, the DND gateway pair 131.137.245.206/.207 and the Shared Services Canada pair 205.193.239.44/.76 that took over its pages from November 2023.

## [1.2.0] — 2026-10-27

### Added
- **Provenance for every data pull.** Each network command writes a manifest (`data/manifests/<run>.json`) recording the code commit, GitHub Actions run, parameters, SHA-256 of every config file and output file, and a rolling hash over every API response. The SHA-256 of each response body is logged in `<run>.responses.jsonl`.
- **Hash chain.** Each manifest carries the SHA-256 of the previous one; `data/manifests/chain.jsonl` indexes the chain. Altering or deleting any past run breaks every later link.
- **Blockchain timestamps.** Workflows stamp each manifest with OpenTimestamps (free, Bitcoin-anchored) and upgrade pending proofs daily.
- **`data/SHA256SUMS`** for `sha256sum -c`, and **`data/BUILDLOG.md`**, a run-by-run log.
- **`python -m wikisscbot verify`**: recomputes the chain and every checksum. Runs in CI before and after each collection.
- **Topic enrichment** (`enrich`): Wikimedia's language-agnostic article-topic model (Lift Wing `outlink-topic-model`) for each edited Wikipedia page, plus English/French labels for Wikidata items. Cached in `data/topics.json`.
- **Beats**: keyword groupings tuned for Canadian government reporting (Canadian military, Elections & parties, Federal government & agencies, …).
- **Web app** (`web/`): FastAPI + SQLite FTS5 backend and a no-build frontend. Full-text search (accent-insensitive), filters by wiki, year, beat, Wikimedia topic, range, IP or CIDR and date; aggregation by address, topic and range; address profiles with hour-of-day, weekday and "addresses editing the same pages"; CSV export; provenance page. Optional self-updating from GitHub with verification before each data swap.
- Deploy files: `Procfile`, `Dockerfile`, `requirements.txt`, `.python-version`.
- **Static build** (`python -m wikisscbot site` → `docs/`): the full site with no server. An in-browser engine (`web/static/engine.js`) answers the same queries as the API, and SHA-256-verifies every data file against `SHA256SUMS` and the latest signed manifest, with an optional full chain check. Rebuilt by every workflow run. Year reports moved to `docs/reports/`.
- `CHANGELOG.md`, `ROADMAP.md`.

### Changed
- Added English Wiktionary and English Wikivoyage as sources (found by the niche-wiki probe in `research/niche/`).
- Topic enrichment is bounded: 6 parallel requests, 15 s timeouts, a 15-minute budget (`WIKISSC_ENRICH_MINUTES`) and a stop after 25 consecutive failures; unfinished pages carry over via the cache. The workflow step also has a 25-minute timeout.
- HTTP layer passes every response through the provenance recorder before parsing.
- `version` subcommand and `--version` flag.

## [1.1.0] — 2026-10-27

### Added
- Multi-year collection (`backfill_years` in `config/settings.json`, now 2024 and 2025) with a report page per year (`docs/<year>.html`).

### Fixed
- Wikidata returned nothing: read queries no longer send `maxlag`, which Wikidata applies to query-service lag.
- Address blocks that time out (HTTP 503/504) are split in half and retried down to /24 (IPv4) or /48 (IPv6).
- Department labels now always win over generic SSC BGP labels when both cover an address.

## [1.0.0] — 2026-10-27

### Added
- Rebuild of the @gccaedits idea as a historical collector: MediaWiki `list=usercontribs&uciprange=` over every Government of Canada block, for English and French Wikipedia, Wikidata and Commons.
- Range sources: the public-domain @gccaedits department list, plus prefixes announced by Shared Services Canada ASNs (AS2665, AS2675, AS2682, AS25689, AS806) from RIPEstat.
- Outputs: `edits.csv`, `edits.jsonl`, `summary.json`, `status.json`, static report page.
- GitHub Actions: backfill on push or manual dispatch; daily watcher with optional Mastodon/Bluesky posting.
- First 2025 collection: 1,818 edits (2,643 after the 1.1.0 Wikidata fix).

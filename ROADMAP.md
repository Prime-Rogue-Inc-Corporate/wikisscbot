# Roadmap

Status as of 2026-11-12 (v1.3.0). Shipped items are described in the [changelog](CHANGELOG.md).

## Done
- **Archive, 2010 to 2025.** Every logged-out edit from Government of Canada ranges on English and French Wikipedia, Wikidata, Wikimedia Commons, English Wiktionary and English Wikivoyage. Every year is collected again in full on each run.
- **Provenance.** Each data pull is checksummed, hash-chained and timestamped in Bitcoin with OpenTimestamps. The site re-checks the files in the browser.
- **Revision History site.** Search with filters by address, topic and range; address profiles; crawlable pages for each year, methodology, FAQ, data, coverage and address clusters; structured data, sitemap and `llms.txt`.
- **Dated attribution.** An edit counts for a Shared Services Canada routing prefix only while that prefix was announced. Addresses confirmed by stronger evidence carry their own label and start date.
- **Parliament's ranges, dated.** The House of Commons has used three address blocks since 2010. The newest is labelled from the date Parliament began routing it itself, and the middle one ends when the block was re-assigned.
- **Runs that survive other changes.** A two-hour collection run no longer fails when something else changes the repository before it finishes.
- **Single-address lookup.** Every public edit from one address, in any year, across every public Wikimedia wiki and a list of other wikis.

## Now
- **Earlier years, one at a time.** 2009 is next, then back toward 2002. Each year is one configuration change and a full re-collection.
- **Serve the site from the top of the domain.** The build is published on the `site` branch; the host still has to be pointed at it.

## Next
- **One job per year.** Collect years in parallel so the full re-collection stays inside the time limit as the archive grows.
- **Full diffs.** Archive the added and removed text of each edit, so the archive survives revision deletion and search can cover changed text, not just titles and summaries.
- **Revision-deletion watch.** Re-check archived revisions and flag any that Wikipedia has since hidden or suppressed.
- **Dated range records.** Record registry and reverse-DNS evidence for each range, with dates, so every label can be audited. The department list from 2014–16 is undated.
- **More wikis.** Other language Wikipedias in the yearly archive, and one list of non-Wikimedia wikis that still publish addresses.
- **Thread matching after each run.** Recompute which addresses behave as one network exit whenever the archive changes.
- **Dumps cross-check.** Use Wikimedia's public history dumps to cross-check API results.

## Later
- Alerts for watched pages or topics (email or RSS).
- Annotated collections: pin edits, add notes and publish a permalinked set.
- Public API keys and rate limits for researchers.
- A second, independent timestamp alongside OpenTimestamps.
- Access-to-information helper: request text for a given set of edits, ranges and dates.

## Parked
- **NFT collection.** Cards for individual edits as Solana compressed NFTs. Parked indefinitely on 2026-11-12; the `nft` branch stays unmerged.

## Known limits
- Logged-out edits made after English Wikipedia switched to temporary accounts on 4 November 2025 do not show an address and are out of scope.
- Edits that Wikipedia has deleted or suppressed are not returned and are not in the archive.
- Department labels come from a crowd-sourced list compiled in 2014–16. Most current traffic leaves through shared gateways, where the department cannot be determined.
- An edit from a government network is not evidence of who made it, or that it was made in an official capacity.

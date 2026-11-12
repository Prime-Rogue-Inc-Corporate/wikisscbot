# Cross-address thread matching

Finds editing threads inside each address and looks for the same thread on other addresses.
Run from the repo root (needs numpy, scipy and networkx, which the collector itself does not use):

    python research/clusters/cluster_threads.py ./ /tmp/state.pkl 1.0 365
    python research/clusters/grade_matches.py /tmp/state.pkl research/clusters/results.json
    python research/clusters/build_report.py research/clusters/results.json research/clusters

The results committed here were computed on 2026-11-12 from the archive at commit 932b722, which held
2012 to 2025 (38,735 edits, 801 addresses). Years backfilled since then are not in them; rerun to include them.

## Steps

1. `cluster_threads.py` loads every `data/20*/edits.jsonl`. Per address it links pages edited within
   20 minutes of each other, pages with similar titles, and pages where the same section heading was
   edited; Louvain communities on that graph are threads. A thread is cut where it falls silent for
   365 days. Threads of five or more edits get a fingerprint and are scored against every thread on
   every other address.
2. `grade_matches.py` grades each pair (strong >= 0.60 with two kinds of evidence, possible >= 0.45
   with at least one) and explains it: pool (five or more same-page handoffs within an hour),
   renumbering (one block goes quiet, another starts, pages from three or more threads carry over),
   parallel (same thread, closest edits within 30 days), later (everything else).
3. `build_report.py` writes `report.html`, `top10_by_year.csv` and `cross_address_groups.csv`.

## Files

- `results.json`: every top-ten address for every year, its threads, and their matches with evidence.
- `top10_by_year.csv`: the same, flat, one row per thread-match.
- `cross_address_groups.csv`: all strong links in the archive, grouped.
- `report.html`: the readable version.

## Caveats

Thresholds were set to recover cases found by hand; there is no ground truth. Metadata only:
no diff text is read, and nothing here attributes a thread to a person.
One succession (205.193.50.10 to 205.194.16.x) is excluded by hand in `grade_matches.py` because
the carried pages are a single editor's thread. Summaries have emails and trailing signatures stripped.

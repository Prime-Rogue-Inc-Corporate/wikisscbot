"""Refresh the list of prefixes announced by Shared Services Canada ASNs."""

from __future__ import annotations

import datetime as dt
import ipaddress
import json
from pathlib import Path

from .config import ROOT, settings
from .http import get_json

RIPESTAT = "https://stat.ripe.net/data/announced-prefixes/data.json"
OUT = ROOT / "config" / "ranges_ssc_bgp.json"


CURRENT_WITHIN_DAYS = 14


def _day(ts: str | None) -> str | None:
    return ts[:10] if ts else None


def refresh(since: str = "2025-01-01T00:00", out: Path = OUT) -> dict:
    """Fetch every prefix announced by each SSC ASN since `since`.

    The window starts at the beginning of the backfill period so that
    prefixes withdrawn part-way through still count for the years they were
    announced. RIPEstat reports when each prefix was seen; the first and last
    dates are kept so that edits made after a prefix was withdrawn are not
    attributed to the government (see ranges.Range.valid_at).
    """
    asns = settings()["ssc_asns"]
    prefixes: dict[str, dict] = {}
    per_asn = {}
    for asn, label in asns.items():
        data = get_json(RIPESTAT, {"resource": f"AS{asn}", "starttime": since,
                                   "sourceapp": "wikisscbot"})
        body = data.get("data", {})
        found = body.get("prefixes", [])
        per_asn[asn] = len(found)
        query_end = _day(body.get("query_endtime") or body.get("latest_time")) \
            or dt.datetime.now(dt.timezone.utc).date().isoformat()
        cutoff = (dt.date.fromisoformat(query_end) - dt.timedelta(days=CURRENT_WITHIN_DAYS)).isoformat()
        for p in found:
            net = ipaddress.ip_network(p["prefix"], strict=False)
            key = str(net)
            starts = [_day(t.get("starttime")) for t in p.get("timelines", []) if t.get("starttime")]
            ends = [_day(t.get("endtime")) for t in p.get("timelines", []) if t.get("endtime")]
            first, last = (min(starts) if starts else None), (max(ends) if ends else None)
            # No timeline, or seen up to the end of the query window: still announced.
            current = last is None or last >= cutoff
            # If two SSC ASNs announced the same prefix, keep the first label and the widest dates.
            item = prefixes.setdefault(key, {"prefix": key, "asn": int(asn), "label": label,
                                             "first_seen": first, "last_seen": last, "current": current})
            if item["asn"] != int(asn):
                item["first_seen"] = min(filter(None, [item["first_seen"], first]), default=None)
                item["last_seen"] = max(filter(None, [item["last_seen"], last]), default=None)
                item["current"] = item["current"] or current
    doc = {
        "source": "RIPEstat announced-prefixes",
        "since": since,
        "fetched": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts_by_asn": per_asn,
        "lapsed": sum(1 for x in prefixes.values() if not x["current"]),
        "prefixes": sorted(prefixes.values(),
                           key=lambda x: (ipaddress.ip_network(x["prefix"]).version,
                                          ipaddress.ip_network(x["prefix"]))),
    }
    out.write_text(json.dumps(doc, indent=2) + "\n")
    return doc

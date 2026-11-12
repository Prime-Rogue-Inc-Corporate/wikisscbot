"""Government of Canada IP ranges: labelled list + live SSC BGP announcements.

Two sources, merged:

1. config/ranges_gccaedits.json - the public-domain @gccaedits list
   (github.com/ruebot/gccaedits-ip-address-ranges), department-labelled,
   compiled 2014-2016. Labels are historical and may be stale.
2. config/ranges_ssc_bgp.json - prefixes announced by Shared Services
   Canada ASNs at any time in the backfill period, refreshed from RIPEstat.
   These carry no department label ("SSC network, department unknown") and
   fill the gaps left by twelve years of network consolidation. Each prefix
   records when it was last seen announced: an edit made after an SSC ASN
   stopped announcing a prefix is not attributed to it, because the address
   space may have passed to someone else.

Each IP is labelled by its most specific matching gccaedits range; the
generic SSC BGP label is used only when no gccaedits range covers the IP,
because an unlabelled announcement says nothing about the department.
"""

from __future__ import annotations

import datetime as dt
import ipaddress
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"

# Largest ranges Wikimedia accepts for IP-range contributions
# ($wgRangeContributionsCIDRLimit on WMF wikis).
MAX_V4 = 16
MAX_V6 = 32
# Refuse to explode an IPv6 block into more than this many /32 queries.
MAX_V6_SPLIT = 64

# An edit still counts for this long after a prefix was last seen announced,
# to allow for gaps in routing visibility.
BGP_GRACE_DAYS = 90

Network = ipaddress.IPv4Network | ipaddress.IPv6Network


@dataclass(frozen=True)
class Range:
    network: Network
    label: str
    source: str  # "gccaedits" or "ssc-bgp"
    # ISO date an SSC ASN last announced the prefix; None = still announced, or undated.
    last_seen: str | None = None

    @property
    def valid_until(self) -> str | None:
        if not self.last_seen:
            return None
        day = dt.date.fromisoformat(self.last_seen[:10]) + dt.timedelta(days=BGP_GRACE_DAYS)
        return day.isoformat()

    def valid_at(self, ts: str | None) -> bool:
        """Was this range attributable to the government at time `ts` (ISO)?"""
        until = self.valid_until
        return ts is None or until is None or ts[:10] <= until


def _parse_entry(entry) -> list[Network]:
    """gccaedits entries are 'a.b.c.d/n', ['ip'], or ['start', 'end']."""
    if isinstance(entry, str):
        return [ipaddress.ip_network(entry, strict=False)]
    if len(entry) == 1:
        return [ipaddress.ip_network(entry[0], strict=False)]
    start, end = ipaddress.ip_address(entry[0]), ipaddress.ip_address(entry[1])
    return list(ipaddress.summarize_address_range(start, end))


def load_gccaedits(path: Path = CONFIG / "ranges_gccaedits.json") -> list[Range]:
    data = json.loads(path.read_text())["ranges"]
    out = []
    for label, entries in data.items():
        nets: list[Network] = []
        for e in entries:
            nets.extend(_parse_entry(e))
        for n in ipaddress.collapse_addresses(nets):
            out.append(Range(n, label, "gccaedits"))
    return out


def load_ssc_bgp(path: Path = CONFIG / "ranges_ssc_bgp.json") -> list[Range]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    out = []
    for item in data.get("prefixes", []):
        out.append(Range(ipaddress.ip_network(item["prefix"], strict=False),
                         item["label"], "ssc-bgp",
                         None if item.get("current", True) else item.get("last_seen")))
    return out


def load_all() -> list[Range]:
    return load_gccaedits() + load_ssc_bgp()


class Labeller:
    """Most-specific-match lookup from IP to range label."""

    def __init__(self, ranges: list[Range]):
        # gccaedits ranges first (most specific first), then SSC BGP prefixes.
        self.ranges = sorted(
            ranges,
            key=lambda r: (0 if r.source == "gccaedits" else 1, -r.network.prefixlen),
        )

    def match(self, ip: str, ts: str | None = None) -> Range | None:
        """Most specific range containing `ip` that was valid at time `ts`."""
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return None
        for r in self.ranges:
            if addr.version == r.network.version and addr in r.network and r.valid_at(ts):
                return r
        return None

    def lapsed(self, ip: str, ts: str) -> bool:
        """True if `ip` is only inside ranges that had stopped being announced by `ts`."""
        return self.match(ip, ts) is None and self.match(ip) is not None


def query_blocks(ranges: list[Range], year: int | str | None = None) -> tuple[list[Network], list[str]]:
    """Union of all ranges, split into blocks Wikimedia will accept.

    With `year`, ranges that had lapsed before that year began are left out.
    Returns (blocks, warnings).
    """
    warnings = []
    if year is not None:
        ranges = [r for r in ranges if r.valid_at(f"{year}-01-01")]
    v4 = ipaddress.collapse_addresses(r.network for r in ranges if r.network.version == 4)
    v6 = ipaddress.collapse_addresses(r.network for r in ranges if r.network.version == 6)
    blocks: list[Network] = []
    for n in v4:
        blocks.extend([n] if n.prefixlen >= MAX_V4 else n.subnets(new_prefix=MAX_V4))
    for n in v6:
        if n.prefixlen >= MAX_V6:
            blocks.append(n)
        elif 2 ** (MAX_V6 - n.prefixlen) <= MAX_V6_SPLIT:
            blocks.extend(n.subnets(new_prefix=MAX_V6))
        else:
            warnings.append(f"skipped {n}: larger than {MAX_V6_SPLIT} x /{MAX_V6}")
    return blocks, warnings

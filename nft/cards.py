"""Build card images and Metaplex metadata for the satirical NFT collection.

Reads the signed archive (data/<year>/edits.jsonl), assigns each eligible edit
a permanent card number (nft/registry.jsonl, append-only, oldest edits first),
and writes for every registered card:

  docs/nft/<n>.svg    the card image
  docs/nft/<n>.json   Metaplex-standard metadata (points at the image)
  docs/nft/collection.json / collection.svg

The static site already publishes docs/, so these URLs go live with it.

Guardrails (applied before a card is ever registered):
  * no IP address anywhere in images or metadata; cards name a fictional
    character and the network label only
  * skip edits listed in nft/skip.txt
  * skip edits from small offices (config skip_labels_on_biographies) to
    pages Wikimedia classifies as biographies
  * article-like namespaces only (config namespaces)
"""

from __future__ import annotations

import datetime as dt
import glob
import hashlib
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
NFT = ROOT / "nft"
OUT = ROOT / "docs" / "nft"
REGISTRY = NFT / "registry.jsonl"

WIKI_NAMES = {"enwiki": "English Wikipedia", "frwiki": "French Wikipedia",
              "wikidatawiki": "Wikidata", "commonswiki": "Wikimedia Commons",
              "enwiktionary": "English Wiktionary", "enwikivoyage": "English Wikivoyage"}


def load_json(p: Path, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def archive_edits(root: Path = ROOT) -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(root / "data" / "[0-9][0-9][0-9][0-9]" / "edits.jsonl"))):
        with open(f, encoding="utf-8") as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())
    rows.sort(key=lambda e: (e["timestamp"], e["wiki"], e["revid"]))
    return rows


def key(e: dict) -> str:
    return f"{e['wiki']}|{e['revid']}"


def load_skips(path: Path) -> tuple[set[str], set[str]]:
    revs, pages = set(), set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            wiki, rest = line.split("|", 1)
            if rest.startswith("page:"):
                pages.add(f"{wiki}|{rest[5:]}")
            else:
                revs.add(f"{wiki}|{rest}")
    return revs, pages


def eligible(e: dict, cfg: dict, topics: dict, skip_revs: set, skip_pages: set) -> bool:
    if e.get("ns", 0) not in cfg["namespaces"]:
        return False
    if key(e) in skip_revs or f"{e['wiki']}|{e['title']}" in skip_pages:
        return False
    if e.get("label") in cfg["skip_labels_on_biographies"]:
        page_topics = topics.get("pages", {}).get(f"{e['wiki']}|{e['title']}", [])
        if any("Biography" in t["topic"] for t in page_topics):
            return False
    return True


def character(e: dict, chars: dict) -> str:
    return (chars["characters"].get(e["ip"]) or chars["by_label"].get(e.get("label"))
            or chars["default"])


def display_title(e: dict, topics: dict) -> str:
    return topics.get("labels", {}).get(f"{e['wiki']}|{e['title']}") or e["title"]


_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6 = re.compile(r"\b(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{0,4}\b")
_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")


def clean_summary(text: str) -> str:
    """Edit summary as shown on a card: wiki links flattened, IP addresses removed."""
    text = re.sub(r"/\*\s*(.*?)\s*\*/", r"§ \1 —", text or "")
    text = _LINK.sub(r"\1", text)
    text = _IPV4.sub("[address]", text)
    text = _IPV6.sub("[address]", text)
    return re.sub(r"\s+", " ", text).strip().removesuffix(" —").strip()


def reverted(e: dict) -> bool:
    return "mw-reverted" in (e.get("tags") or [])


# --- rendering -------------------------------------------------------------

def wrap(text: str, width: int, max_lines: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: width - 1].rstrip() + "…"
    return lines


def rarity(e: dict) -> str:
    d = abs(e.get("sizediff") or 0)
    if reverted(e) and d >= 1000:
        return "Legendary"
    if reverted(e) or d >= 2000:
        return "Rare"
    if d >= 300:
        return "Uncommon"
    return "Common"


RARITY_COLOUR = {"Legendary": "#c2281d", "Rare": "#9a6a00", "Uncommon": "#2f4a6d", "Common": "#5f5d55"}


def card_svg(n: int, e: dict, title: str, char: str) -> str:
    summary = clean_summary(e.get("comment")) or "(no edit summary)"
    d = e.get("sizediff")
    delta = "" if d is None else (f"+{d:,}" if d > 0 else f"{d:,}")
    r = rarity(e)
    t_lines = wrap(title, 26, 3)
    s_lines = wrap(f"“{summary}”", 36, 7)
    when = e["timestamp"].replace("T", " ").replace("Z", " UTC")[:20]
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000" viewBox="0 0 800 1000">',
        '<rect width="800" height="1000" fill="#f5f3ee"/>',
        f'<rect x="24" y="24" width="752" height="952" fill="none" stroke="{RARITY_COLOUR[r]}" stroke-width="6"/>',
        '<text x="60" y="92" font-family="DejaVu Sans Mono, monospace" font-size="22" fill="#77746b">'
        f'GC WIKI EDITS · CARD #{n:05d}</text>',
        f'<text x="740" y="92" text-anchor="end" font-family="DejaVu Sans, sans-serif" font-size="22" '
        f'font-weight="bold" fill="{RARITY_COLOUR[r]}">{escape(r.upper())}</text>',
    ]
    y = 170
    for line in t_lines:
        out.append(f'<text x="60" y="{y}" font-family="DejaVu Serif, Georgia, serif" font-size="48" '
                   f'font-weight="bold" fill="#161513">{escape(line)}</text>')
        y += 58
    y += 20
    out.append(f'<line x1="60" y1="{y}" x2="740" y2="{y}" stroke="#dedad0" stroke-width="2"/>')
    y += 60
    for line in s_lines:
        out.append(f'<text x="60" y="{y}" font-family="DejaVu Serif, Georgia, serif" font-size="32" '
                   f'font-style="italic" fill="#3d3b36">{escape(line)}</text>')
        y += 44
    out += [
        f'<text x="60" y="800" font-family="DejaVu Sans, sans-serif" font-size="30" font-weight="bold" '
        f'fill="#161513">{escape(char)}</text>',
        f'<text x="60" y="842" font-family="DejaVu Sans, sans-serif" font-size="22" fill="#77746b">'
        f'{escape(e.get("label") or "")}</text>',
        f'<text x="60" y="900" font-family="DejaVu Sans Mono, monospace" font-size="22" fill="#3d3b36">'
        f'{escape(when)} · {escape(WIKI_NAMES.get(e["wiki"], e["wiki"]))}</text>',
        f'<text x="740" y="900" text-anchor="end" font-family="DejaVu Sans Mono, monospace" font-size="30" '
        f'font-weight="bold" fill="{"#24724a" if (d or 0) > 0 else "#c2281d"}">{escape(delta)}</text>',
        '<text x="60" y="950" font-family="DejaVu Sans, sans-serif" font-size="16" fill="#9a978d">'
        'Satire. Character is fictional. Edit data via Wikimedia, CC BY-SA 4.0.</text>',
        "</svg>",
    ]
    return "\n".join(out)


def card_metadata(n: int, e: dict, title: str, char: str, cfg: dict) -> dict:
    base = cfg["base_url"].rstrip("/")
    d = dt.datetime.strptime(e["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
    summary = clean_summary(e.get("comment"))
    return {
        "name": f"GC Edit #{n:05d}",
        "symbol": cfg["symbol"],
        "description": (
            f"“{summary or '(no edit summary)'}” — an anonymous edit to “{title}” on "
            f"{WIKI_NAMES.get(e['wiki'], e['wiki'])}, {e['timestamp'][:10]}, from a Government of Canada "
            f"network ({e.get('label')}). Starring {char}, a fictional composite. Satire: an edit from a "
            "shared government network is not evidence of who made it. Page title and edit summary via "
            "Wikimedia projects, CC BY-SA 4.0."
        ),
        "image": f"{base}/{n}.svg",
        "external_url": e["url"],
        "attributes": [
            {"trait_type": "Character", "value": char},
            {"trait_type": "Network", "value": e.get("label") or "Unknown"},
            {"trait_type": "Wiki", "value": WIKI_NAMES.get(e["wiki"], e["wiki"])},
            {"trait_type": "Year", "value": e["timestamp"][:4]},
            {"trait_type": "Weekday", "value": d.strftime("%A")},
            {"trait_type": "Byte change", "value": e.get("sizediff") or 0, "display_type": "number"},
            {"trait_type": "Reverted", "value": "Yes" if reverted(e) else "No"},
            {"trait_type": "Rarity", "value": rarity(e)},
        ],
        "properties": {"files": [{"uri": f"{base}/{n}.svg", "type": "image/svg+xml"}],
                       "category": "image"},
    }


def collection_files(cfg: dict) -> tuple[str, dict]:
    base = cfg["base_url"].rstrip("/")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">'
           '<rect width="800" height="800" fill="#161513"/>'
           '<text x="400" y="360" text-anchor="middle" font-family="DejaVu Serif, Georgia, serif" '
           'font-size="72" font-weight="bold" fill="#f5f3ee">GC WIKI EDITS</text>'
           '<text x="400" y="440" text-anchor="middle" font-family="DejaVu Sans Mono, monospace" '
           'font-size="30" fill="#c2281d">collector\'s edition · satire</text></svg>')
    meta = {
        "name": cfg["collection_name"], "symbol": cfg["symbol"],
        "description": ("Satirical collectible cards of anonymous Wikipedia edits made from Government of "
                        "Canada networks, 2018–2025. Characters are fictional composites standing for shared "
                        "network gateways, not real people. Edit data via Wikimedia projects, CC BY-SA 4.0."),
        "image": f"{base}/collection.svg",
        "properties": {"files": [{"uri": f"{base}/collection.svg", "type": "image/svg+xml"}],
                       "category": "image"},
    }
    return svg, meta


# --- registry ----------------------------------------------------------------

def read_registry(path: Path = REGISTRY) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def minted_frontier(nft_dir: Path = NFT) -> int:
    """Highest card number minted on any cluster (0 if none)."""
    top = 0
    for f in nft_dir.glob("minted.*.jsonl"):
        for line in f.read_text().splitlines():
            if line.strip():
                top = max(top, json.loads(line)["n"])
    return top


def build(root: Path = ROOT, out: Path = OUT, registry: Path = REGISTRY,
          ahead: int | None = None) -> dict:
    """Register new edits and write card files.

    Files are written only for cards up to the mint frontier plus `ahead` more
    (default: the per-run mint limit), so the published folder grows with the
    collection instead of holding every card at once.
    """
    cfg = json.loads((NFT / "config.json").read_text())
    chars = json.loads((NFT / "characters.json").read_text())
    topics = load_json(root / "data" / "topics.json", {}) or {}
    skip_revs, skip_pages = load_skips(NFT / "skip.txt")

    edits = archive_edits(root)
    by_key = {key(e): e for e in edits}
    reg = read_registry(registry)
    known = {r["key"] for r in reg}
    nxt = max((r["n"] for r in reg), default=0) + 1
    new = []
    for e in edits:
        k = key(e)
        if k in known or not eligible(e, cfg, topics, skip_revs, skip_pages):
            continue
        new.append({"n": nxt, "key": k,
                    "content_sha256": hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()})
        known.add(k)
        nxt += 1
    if new:
        with registry.open("a") as f:
            for r in new:
                f.write(json.dumps(r) + "\n")
        reg += new

    out.mkdir(parents=True, exist_ok=True)
    horizon = minted_frontier() + (cfg["mint_limit_per_run"] if ahead is None else ahead)
    written = withdrawn = 0
    for r in reg:
        if r["n"] > horizon:
            continue
        e = by_key.get(r["key"])
        # A registered card whose edit is now skipped (or vanished) is withdrawn: its files are
        # removed, and the mint step will not mint it.
        if e is None or not eligible(e, cfg, topics, skip_revs, skip_pages):
            for ext in ("svg", "json"):
                (out / f"{r['n']}.{ext}").unlink(missing_ok=True)
            withdrawn += 1
            continue
        title = display_title(e, topics)
        char = character(e, chars)
        (out / f"{r['n']}.svg").write_text(card_svg(r["n"], e, title, char), encoding="utf-8")
        (out / f"{r['n']}.json").write_text(
            json.dumps(card_metadata(r["n"], e, title, char, cfg), ensure_ascii=False, indent=1),
            encoding="utf-8")
        written += 1
    svg, meta = collection_files(cfg)
    (out / "collection.svg").write_text(svg, encoding="utf-8")
    (out / "collection.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"registered": len(reg), "new": len(new), "written": written, "withdrawn": withdrawn,
            "horizon": horizon}


if __name__ == "__main__":
    ahead = int(sys.argv[1]) if len(sys.argv) > 1 else None
    print(json.dumps(build(ahead=ahead)))
    sys.exit(0)

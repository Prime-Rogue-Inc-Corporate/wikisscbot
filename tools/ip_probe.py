"""Look up single addresses across all years, one wiki at a time.

The yearly backfill scans whole address blocks for configured years. This
probe asks the opposite question: for one address, what is every logged-out
edit Wikipedia has ever published from it, in any year? It queries
list=usercontribs with ucuser=<ip> and no date window, on every configured
wiki plus the extra ones in config/probe_ips.json.

Only edits that were publicly attributed to the IP are returned. Edits made
under temporary accounts (English Wikipedia from 4 November 2025) and edits
that have been deleted or suppressed are not visible and are not collected.

Output: research/probes/<ip>.json and research/probes/latest.md
"""

from __future__ import annotations

import datetime as dt
import ipaddress
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wikisscbot.collect import diff_url  # noqa: E402
from wikisscbot.config import settings  # noqa: E402
from wikisscbot.http import ApiError, get_json  # noqa: E402
from wikisscbot.ranges import Labeller, load_all  # noqa: E402

OUT = ROOT / "research" / "probes"
CONFIG = ROOT / "config" / "probe_ips.json"
PROPS = "ids|title|timestamp|comment|sizediff|flags"


def contributions(host: str, ip: str) -> list[dict]:
    """Every public contribution from `ip` on one wiki, oldest first."""
    api = f"https://{host}/w/api.php"
    params = {"action": "query", "list": "usercontribs", "format": "json", "formatversion": "2",
              "ucuser": ip, "uclimit": "max", "ucprop": PROPS, "ucdir": "newer",
              "errorformat": "plaintext"}
    out = []
    while True:
        data = get_json(api, params)
        if "error" in data or "errors" in data:
            err = data.get("error") or data["errors"][0]
            raise ApiError(f"{err.get('code')}: {err.get('info') or err.get('text')}")
        out.extend(data.get("query", {}).get("usercontribs", []))
        cont = data.get("continue")
        if not cont:
            return out
        params.update(cont)


def probe_ip(ip: str, wikis: list[dict], labeller: Labeller) -> dict:
    ipaddress.ip_address(ip)  # reject anything that is not a single address
    res = {"ip": ip, "wikis": {}, "edits": [], "errors": {}}
    for w in wikis:
        try:
            rows = contributions(w["host"], ip)
        except ApiError as e:
            res["errors"][w["id"]] = str(e)
            continue
        res["wikis"][w["id"]] = len(rows)
        for c in rows:
            rng = labeller.match(ip, c["timestamp"])
            res["edits"].append({
                "wiki": w["id"], "timestamp": c["timestamp"], "title": c["title"],
                "sizediff": c.get("sizediff"), "comment": c.get("comment", ""),
                "label": rng.label if rng else "outside known ranges at that date",
                "label_source": rng.source if rng else None,
                "url": diff_url(w["host"], c["revid"], c.get("parentid")),
            })
    res["edits"].sort(key=lambda e: e["timestamp"])
    res["total"] = len(res["edits"])
    res["first"] = res["edits"][0]["timestamp"] if res["edits"] else None
    res["last"] = res["edits"][-1]["timestamp"] if res["edits"] else None
    return res


def markdown(results: list[dict], notes: dict, wikis: list[dict], when: str) -> str:
    lines = ["# Single-address probe", "",
             f"Run {when}. Every logged-out edit Wikipedia publicly attributes to each address, in any year, on "
             f"{len(wikis)} wikis ({', '.join(w['id'] for w in wikis)}). Deleted or suppressed edits and edits made "
             "under temporary accounts are not visible.", ""]
    for r in results:
        lines += [f"## {r['ip']}", ""]
        if notes.get(r["ip"]):
            lines += [notes[r["ip"]], ""]
        if r["total"]:
            lines += [f"**{r['total']} edits**, {r['first'][:10]} to {r['last'][:10]}.", ""]
        else:
            lines += ["**No edits found** on any wiki, in any year.", ""]
        lines += ["| Wiki | Edits |", "|---|---|"]
        lines += [f"| {w['id']} | {r['wikis'].get(w['id'], 'error: ' + r['errors'].get(w['id'], '?'))} |" for w in wikis]
        lines.append("")
        if r["edits"]:
            lines += ["| Date (UTC) | Wiki | Page | Bytes | Label at that date | Summary | Diff |",
                      "|---|---|---|---|---|---|---|"]
            for e in r["edits"][:500]:
                cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {e['timestamp'][:16].replace('T', ' ')} | {e['wiki']} | {cell(e['title'])} | "
                             f"{e['sizediff'] if e['sizediff'] is not None else ''} | {cell(e['label'])} | "
                             f"{cell(e['comment'][:120])} | [diff]({e['url']}) |")
            if len(r["edits"]) > 500:
                lines.append(f"\n…and {len(r['edits']) - 500} more in the JSON file.")
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    cfg = json.loads(CONFIG.read_text())
    wikis = [{"id": w["id"], "host": w["host"]} for w in settings()["wikis"]] + cfg.get("extra_wikis", [])
    labeller = Labeller(load_all())
    when = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.mkdir(parents=True, exist_ok=True)
    results, notes = [], {}
    for item in cfg["ips"]:
        ip = item["ip"]
        notes[ip] = item.get("note", "")
        r = probe_ip(ip, wikis, labeller)
        r["probed_at"] = when
        results.append(r)
        (OUT / f"{ip.replace(':', '_')}.json").write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
        print(f"{ip}: {r['total']} edits, {len(r['errors'])} wiki errors", file=sys.stderr)
    (OUT / "latest.md").write_text(markdown(results, notes, wikis, when) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

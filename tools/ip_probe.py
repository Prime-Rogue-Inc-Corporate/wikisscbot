"""Look up single addresses across all years, one wiki at a time.

The yearly backfill scans whole address blocks for configured years. This
probe asks the opposite question: for one address, what is every logged-out
edit Wikipedia has ever published from it, in any year? It queries
list=usercontribs with ucuser=<ip> and no date window, on every configured
wiki plus the extra ones in config/probe_ips.json. With "all_wikimedia" set
it sweeps every public Wikimedia wiki (from the sitematrix), and with
"niche_wikis" set it also asks the wikis in config/niche_wikis.json.

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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wikisscbot.config import settings  # noqa: E402
from wikisscbot.http import ApiError, get_json  # noqa: E402
from wikisscbot.ranges import Labeller, load_all  # noqa: E402

OUT = ROOT / "research" / "probes"
CONFIG = ROOT / "config" / "probe_ips.json"
PROPS = "ids|title|timestamp|comment|sizediff|flags"


SITEMATRIX = "https://meta.wikimedia.org/w/api.php"
WORKERS = 4


def norm(w: dict) -> dict:
    """A wiki entry with its API endpoint and the base for diff links."""
    if w.get("api_url"):
        return w
    if w.get("host"):
        return {"id": w["id"], "api_url": f"https://{w['host']}/w/api.php",
                "diff_base": f"https://{w['host']}/w/index.php", "family": w.get("family", "wikimedia")}
    base = w["base"].rstrip("/")
    return {"id": w["id"], "api_url": base + w.get("api", "/api.php"),
            "diff_base": base + "/index.php", "family": w.get("genre") or "other"}


def all_wikimedia() -> list[dict]:
    """Every public Wikimedia wiki, open or closed, from the sitematrix."""
    data = get_json(SITEMATRIX, {"action": "sitematrix", "format": "json", "formatversion": "2",
                                 "smsiteprop": "url|dbname"})
    out = []
    for key, entry in data.get("sitematrix", {}).items():
        sites = entry if key == "specials" else entry.get("site", []) if isinstance(entry, dict) else []
        for site in sites:
            if "private" in site or not site.get("url"):
                continue
            url = site["url"].rstrip("/")
            out.append({"id": site["dbname"], "api_url": url + "/w/api.php",
                        "diff_base": url + "/w/index.php", "family": "wikimedia"})
    return out


def contributions(api: str, ip: str, quick: bool = False) -> list[dict]:
    """Every public contribution from `ip` on one wiki, oldest first."""
    kw = {"retries": 2, "timeout": 25} if quick else {}
    params = {"action": "query", "list": "usercontribs", "format": "json", "formatversion": "2",
              "ucuser": ip, "uclimit": "max", "ucprop": PROPS, "ucdir": "newer",
              "errorformat": "plaintext"}
    out = []
    while True:
        data = get_json(api, params, **kw)
        if "error" in data or "errors" in data:
            err = data.get("error") or data["errors"][0]
            raise ApiError(f"{err.get('code')}: {err.get('info') or err.get('text')}")
        out.extend(data.get("query", {}).get("usercontribs", []))
        cont = data.get("continue")
        if not cont:
            return out
        params.update(cont)


def link(w: dict, revid: int, parentid: int | None) -> str:
    return f"{w['diff_base']}?diff={revid}&oldid={parentid}" if parentid else f"{w['diff_base']}?oldid={revid}"


def probe_ip(ip: str, wikis: list[dict], labeller: Labeller, quick: bool = False) -> dict:
    ipaddress.ip_address(ip)  # reject anything that is not a single address
    wikis = [norm(w) for w in wikis]
    res = {"ip": ip, "checked": len(wikis), "wikis": {}, "edits": [], "errors": {}}

    def one(w):
        try:
            return w, contributions(w["api_url"], ip, quick), None
        except Exception as e:  # one unreachable wiki must not stop the sweep
            return w, [], str(e)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(one, wikis))
    for w, rows, err in results:
        if err:
            res["errors"][w["id"]] = err[:200]
            continue
        res["wikis"][w["id"]] = len(rows)
        for c in rows:
            rng = labeller.match(ip, c["timestamp"])
            res["edits"].append({
                "wiki": w["id"], "family": w["family"], "timestamp": c["timestamp"], "title": c["title"],
                "sizediff": c.get("sizediff"), "comment": c.get("comment", ""),
                "label": rng.label if rng else "outside known ranges at that date",
                "label_source": rng.source if rng else None,
                "url": link(w, c["revid"], c.get("parentid")),
            })
    res["edits"].sort(key=lambda e: e["timestamp"])
    res["total"] = len(res["edits"])
    res["first"] = res["edits"][0]["timestamp"] if res["edits"] else None
    res["last"] = res["edits"][-1]["timestamp"] if res["edits"] else None
    return res


def markdown(results: list[dict], notes: dict, wikis: list[dict], when: str) -> str:
    wikis = [norm(w) for w in wikis]
    wm = sum(1 for w in wikis if w["family"] == "wikimedia")
    lines = ["# Single-address probe", "",
             f"Run {when}. Every logged-out edit publicly attributed to each address, in any year, on "
             f"{len(wikis)} wikis ({wm} Wikimedia, {len(wikis) - wm} other). Deleted or suppressed edits and edits "
             "made under temporary accounts are not visible.", ""]
    for r in results:
        lines += [f"## {r['ip']}", ""]
        if notes.get(r["ip"]):
            lines += [notes[r["ip"]], ""]
        ok = len(r["wikis"])
        if r["total"]:
            lines += [f"**{r['total']} edits**, {r['first'][:10]} to {r['last'][:10]}, on "
                      f"{sum(1 for v in r['wikis'].values() if v)} of {ok} wikis that answered.", ""]
        else:
            lines += [f"**No edits found** in any year, on any of the {ok} wikis that answered.", ""]
        hits = sorted(((k, v) for k, v in r["wikis"].items() if v), key=lambda kv: -kv[1])
        if hits:
            lines += ["| Wiki | Edits |", "|---|---|"] + [f"| {k} | {v} |" for k, v in hits] + [""]
        if r["errors"]:
            names = sorted(r["errors"])
            lines += [f"{len(names)} wikis could not be checked: {', '.join(names[:40])}"
                      + (f", and {len(names) - 40} more (see the JSON file)." if len(names) > 40 else "."), ""]
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
    wikis = [norm({"id": w["id"], "host": w["host"]}) for w in settings()["wikis"]]
    wikis += [norm(w) for w in cfg.get("extra_wikis", [])]
    if cfg.get("all_wikimedia"):
        wikis += all_wikimedia()
    if cfg.get("niche_wikis"):
        niche = json.loads((ROOT / "config" / "niche_wikis.json").read_text())["wikis"]
        wikis += [norm(w) for w in niche]
    seen, unique = set(), []
    for w in wikis:  # the same wiki can arrive from more than one list
        if w["api_url"] not in seen:
            seen.add(w["api_url"])
            unique.append(w)
    wikis = unique
    quick = len(wikis) > 50
    labeller = Labeller(load_all())
    when = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.mkdir(parents=True, exist_ok=True)
    results, notes = [], {}
    for item in cfg["ips"]:
        ip = item["ip"]
        notes[ip] = item.get("note", "")
        r = probe_ip(ip, wikis, labeller, quick)
        r["probed_at"] = when
        results.append(r)
        (OUT / f"{ip.replace(':', '_')}.json").write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
        print(f"{ip}: {r['total']} edits on {len(wikis)} wikis, {len(r['errors'])} could not be checked",
              file=sys.stderr)
    (OUT / "latest.md").write_text(markdown(results, notes, wikis, when) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

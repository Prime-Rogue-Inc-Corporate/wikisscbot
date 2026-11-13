"""Diff-text features for hand-picked threads. Research only: nothing here is read by the site.

The thread matching in this folder uses metadata only. For a few threads that appear on several
addresses, this script fetches what each edit actually changed (MediaWiki action=compare) and
reduces it to habits: does the edit only swap numbers, which template fields does it touch, does it
update the reference date, how does it write numbers and dates, does it add or remove table rows.
The same habits on every address support "one routine"; different habits argue against it.

Every other address that edited the same pages is the control group.

Gateway-level only. The output describes a routine and the addresses it used, never a person.
Short snippets of the changed text are kept for the thread's own edits (public wiki text), none
for the control group.

Usage (repo root):
    python research/clusters/diff_features.py              # fetch and write diff_features.json / .md
    python research/clusters/diff_features.py --dry-run    # list what would be fetched, no network
    python research/clusters/diff_features.py --selftest   # check the diff parser on a canned sample
"""
from __future__ import annotations

import collections
import glob
import html
import json
import re
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

CONTROL_CAP = 120
PAUSE = 0.25
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_STYLES = [
    ("Qn YYYY", re.compile(r"\bQ[1-4]\s+(?:19|20)\d\d\b")),
    ("YYYY Qn", re.compile(r"\b(?:19|20)\d\d\s+Q[1-4]\b")),
    ("Month D, YYYY", re.compile(rf"\b(?:{MONTHS})\s+\d{{1,2}},\s+(?:19|20)\d\d\b")),
    ("D Month YYYY", re.compile(rf"\b\d{{1,2}}\s+(?:{MONTHS})\s+(?:19|20)\d\d\b")),
    ("Month YYYY", re.compile(rf"\b(?:{MONTHS})\s+(?:19|20)\d\d\b")),
    ("YYYY-MM-DD", re.compile(r"\b(?:19|20)\d\d-\d\d-\d\d\b")),
]
NUMERIC = re.compile(r"^[\s\d., %+\-−]*\d[\s\d., %+\-−]*$")
PARAM = re.compile(r"\|\s*([A-Za-z][A-Za-z0-9_ \-]{1,40}?)\s*=")
TAG = re.compile(r"<[^>]+>")
CELL_DEL = re.compile(r'<td class="diff-deletedline[^"]*"[^>]*>(.*?)</td>', re.S)
CELL_ADD = re.compile(r'<td class="diff-addedline[^"]*"[^>]*>(.*?)</td>', re.S)
INL_DEL = re.compile(r'<del class="diffchange[^"]*">(.*?)</del>', re.S)
INL_INS = re.compile(r'<ins class="diffchange[^"]*">(.*?)</ins>', re.S)


def text(fragment: str) -> str:
    return html.unescape(TAG.sub("", fragment))


def number_format(s: str) -> str | None:
    if re.search(r"\d,\d{3}\b", s):
        return "comma"
    if re.search(r"\d[  ]\d{3}\b", s):
        return "space"
    if re.search(r"\b\d{5,}\b", s):
        return "plain"
    return None


def features(body: str) -> dict:
    """Reduce one diff table (the HTML body from action=compare) to counts and habits."""
    del_cells, add_cells = CELL_DEL.findall(body), CELL_ADD.findall(body)
    inl_del = [text(x) for c in del_cells for x in INL_DEL.findall(c)]
    inl_ins = [text(x) for c in add_cells for x in INL_INS.findall(c)]
    whole_removed = [text(c) for c in del_cells if "<del" not in c and text(c).strip()]
    whole_added = [text(c) for c in add_cells if "<ins" not in c and text(c).strip()]
    modified = [text(c) for c in add_cells if "<ins" in c] + [text(c) for c in del_cells if "<del" in c]
    changed_lines = modified + whole_added + whole_removed
    removed_text = " ".join(inl_del + whole_removed)
    added_text = " ".join(inl_ins + whole_added)
    num_del = [x for x in inl_del if NUMERIC.match(x)]
    num_ins = [x for x in inl_ins if NUMERIC.match(x)]
    params = collections.Counter(m.strip().lower() for line in changed_lines for m in PARAM.findall(line))
    ref_lines = [line for line in changed_lines if re.search(r"<ref|\{\{\s*cite|access-?date|url\s*=", line, re.I)]
    styles = sorted({name for name, rx in DATE_STYLES if rx.search(added_text)})
    if "Month D, YYYY" in styles or "D Month YYYY" in styles:
        styles = [s for s in styles if s != "Month YYYY"]
    fmts = sorted({f for f in (number_format(x) for x in inl_ins + whole_added) if f})
    only_numbers = bool(inl_ins or inl_del) and not whole_added and not whole_removed and \
        all(NUMERIC.match(x) or not x.strip() for x in inl_ins + inl_del)
    return {
        "ins_chars": len(added_text), "del_chars": len(removed_text),
        "lines_modified": sum(1 for c in add_cells if "<ins" in c),
        "lines_added": len(whole_added), "lines_removed": len(whole_removed),
        "number_swaps": min(len(num_del), len(num_ins)), "only_numbers": only_numbers,
        "number_formats": fmts, "date_styles": styles,
        "params": [k for k, _ in params.most_common(8)],
        "touches_reference": bool(ref_lines),
        "access_date_changed": any(re.search(r"access-?date", line, re.I) for line in modified),
        "links_added": added_text.count("[["), "links_removed": removed_text.count("[["),
        "refs_added": len(re.findall(r"<ref", added_text)), "refs_removed": len(re.findall(r"<ref", removed_text)),
        "table_rows_added": sum(1 for line in whole_added if line.lstrip().startswith(("|", "!"))),
        "table_rows_removed": sum(1 for line in whole_removed if line.lstrip().startswith(("|", "!"))),
        "_pairs": [[d[:60], i[:60]] for d, i in zip(inl_del, inl_ins)][:3],
    }


def load_edits() -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(ROOT / "data" / "20*" / "edits.jsonl"))):
        with open(f, encoding="utf-8") as fh:
            out.extend(json.loads(line) for line in fh)
    return out


def select(edits: list[dict], spec: dict) -> tuple[list[dict], list[dict]]:
    """The thread's own edits, and a capped, evenly spaced control sample from every other address."""
    rx = re.compile(spec["title_regex"])
    since = spec.get("since", {})
    on_pages = [e for e in edits if e["wiki"] == spec["wiki"] and rx.search(e["title"]) and e.get("parentid")]
    mine = [e for e in on_pages if e["ip"] in spec["addresses"] and e["timestamp"] >= since.get(e["ip"], "")]
    theirs = sorted((e for e in on_pages if e["ip"] not in spec["addresses"]), key=lambda e: e["revid"])
    if len(theirs) > CONTROL_CAP:
        step = len(theirs) / CONTROL_CAP
        theirs = [theirs[int(i * step)] for i in range(CONTROL_CAP)]
    return sorted(mine, key=lambda e: e["revid"]), theirs


def fetch(host: str, edit: dict) -> dict:
    from wikisscbot.http import ApiError, get_json
    try:
        data = get_json(f"https://{host}/w/api.php", {"action": "compare", "fromrev": edit["parentid"], "torev": edit["revid"],
                                                       "prop": "diff", "format": "json", "formatversion": "2"})
    except ApiError as err:
        return {"error": str(err)[:120]}
    if "error" in data:
        return {"error": data["error"].get("code", "error")}
    return features(data.get("compare", {}).get("body", ""))


def share(rows: list[dict], key) -> str:
    return f"{round(100 * sum(1 for r in rows if key(r)) / len(rows))}%" if rows else "–"


def summarise(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    med = lambda k: (statistics.median(r[k] for r in ok) if ok else 0)
    top = lambda k: [v for v, _ in collections.Counter(x for r in ok for x in r[k]).most_common(5)]
    return {"edits": len(rows), "fetched": len(ok),
            "only_numbers": share(ok, lambda r: r["only_numbers"]),
            "touches_reference": share(ok, lambda r: r["touches_reference"]),
            "access_date_changed": share(ok, lambda r: r["access_date_changed"]),
            "adds_lines": share(ok, lambda r: r["lines_added"] > 0), "removes_lines": share(ok, lambda r: r["lines_removed"] > 0),
            "median_ins_chars": med("ins_chars"), "median_del_chars": med("del_chars"),
            "links_removed_per_edit": round(sum(r["links_removed"] for r in ok) / len(ok), 1) if ok else 0,
            "links_added_per_edit": round(sum(r["links_added"] for r in ok) / len(ok), 1) if ok else 0,
            "refs_removed_per_edit": round(sum(r["refs_removed"] for r in ok) / len(ok), 2) if ok else 0,
            "top_params": top("params"), "number_formats": top("number_formats"), "date_styles": top("date_styles")}


def write_md(out: dict) -> str:
    L = ["# Diff-text features for hand-picked threads\n",
         "Research only; not used by the site. For each thread: what its edits changed, per address, against every "
         "other address that edited the same pages. Gateway-level: this describes a routine, not a person.\n"]
    for s in out["sets"]:
        L.append(f"## {s['id']}\n")
        L.append(s.get("question", "") + "\n")
        L.append("| Address | Edits read | Only numbers | Touches a reference | Access date changed | Adds lines | Removes lines | "
                 "Median chars in / out | Links out / in per edit | Number format | Date style | Fields touched most |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for name, a in list(s["addresses"].items()) + [("all other addresses (control)", s["control"])]:
            m = a["summary"]
            L.append(f"| {name} | {m['fetched']} of {m['edits']} | {m['only_numbers']} | {m['touches_reference']} | "
                     f"{m['access_date_changed']} | {m['adds_lines']} | {m['removes_lines']} | "
                     f"{m['median_ins_chars']:g} / {m['median_del_chars']:g} | {m['links_removed_per_edit']} / {m['links_added_per_edit']} | "
                     f"{', '.join(m['number_formats']) or '–'} | {', '.join(m['date_styles']) or '–'} | {', '.join(m['top_params']) or '–'} |")
        L.append("")
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> None:
    if "--selftest" in argv:
        return selftest()
    from wikisscbot.config import settings
    hosts = {w["id"]: w.get("api") or w.get("host") for w in settings()["wikis"]}
    spec = json.loads((HERE / "diff_targets.json").read_text(encoding="utf-8"))
    edits = load_edits()
    out = {"note": spec["note"], "sets": []}
    for s in spec["sets"]:
        mine, theirs = select(edits, s)
        by_ip = collections.defaultdict(list)
        for e in mine:
            by_ip[e["ip"]].append(e)
        print(f"{s['id']}: {len(mine)} edits on {len(by_ip)} addresses, {len(theirs)} control edits", file=sys.stderr)
        if "--dry-run" in argv:
            for ip, es in sorted(by_ip.items()):
                print(f"  {ip}: {len(es)}", file=sys.stderr)
            continue
        host = hosts[s["wiki"]]
        result = {"id": s["id"], "question": s.get("question", ""), "wiki": s["wiki"], "addresses": {}, "control": {}}
        for ip in s["addresses"]:
            rows = []
            for e in by_ip.get(ip, []):
                f = fetch(host, e)
                rows.append({"revid": e["revid"], "timestamp": e["timestamp"], "title": e["title"], **f})
                time.sleep(PAUSE)
            if rows:
                result["addresses"][ip] = {"summary": summarise(rows), "edits": rows}
        crow = []
        for e in theirs:
            f = fetch(host, e)
            f.pop("_pairs", None)                     # no text kept for the control group
            crow.append({"revid": e["revid"], **f})
            time.sleep(PAUSE)
        result["control"] = {"summary": summarise(crow), "addresses": len({e["ip"] for e in theirs}), "edits": crow}
        out["sets"].append(result)
    if "--dry-run" in argv:
        return
    (HERE / "diff_features.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (HERE / "diff_features.md").write_text(write_md(out), encoding="utf-8")
    errors = sum(1 for s in out["sets"] for a in list(s["addresses"].values()) + [s["control"]] for r in a["edits"] if "error" in r)
    print(f"wrote diff_features.json and diff_features.md; {errors} edits could not be read", file=sys.stderr)


SAMPLE = (
    '<tr><td colspan="2" class="diff-lineno">Line 10:</td><td colspan="2" class="diff-lineno">Line 10:</td></tr>'
    '<tr><td class="diff-marker" data-marker="−"></td><td class="diff-deletedline diff-side-deleted"><div>'
    '| population_est = <del class="diffchange diffchange-inline">152,021</del> |pop_date = <del class="diffchange diffchange-inline">Q1 2018</del></div></td>'
    '<td class="diff-marker" data-marker="+"></td><td class="diff-addedline diff-side-added"><div>'
    '| population_est = <ins class="diffchange diffchange-inline">153,116</ins> |pop_date = <ins class="diffchange diffchange-inline">Q2 2018</ins></div></td></tr>'
    '<tr><td class="diff-marker" data-marker="−"></td><td class="diff-deletedline diff-side-deleted"><div>'
    '| [[Norwegian Air Shuttle]] || [[Alicante]]&lt;ref&gt;x&lt;/ref&gt;</div></td><td colspan="2" class="diff-empty diff-side-added"></td></tr>'
)


def selftest() -> None:
    f = features(SAMPLE)
    assert f["lines_modified"] == 1 and f["lines_removed"] == 1 and f["lines_added"] == 0, f
    assert f["number_swaps"] == 1 and f["only_numbers"] is False, f
    assert f["number_formats"] == ["comma"] and f["date_styles"] == ["Qn YYYY"], f
    assert f["params"][:2] == ["population_est", "pop_date"], f
    assert f["links_removed"] == 2 and f["refs_removed"] == 1 and f["table_rows_removed"] == 1, f
    assert f["_pairs"][0] == ["152,021", "153,116"], f
    g = features(SAMPLE.split('<tr><td class="diff-marker" data-marker="−"></td><td class="diff-deletedline diff-side-deleted"><div>| [[')[0]
                 .replace('Q1 2018', '151,000').replace('Q2 2018', '152,000'))
    assert g["only_numbers"] is True and g["number_swaps"] == 2, g
    print("selftest ok")


if __name__ == "__main__":
    main(sys.argv[1:])

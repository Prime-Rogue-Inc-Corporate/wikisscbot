"""Crawlable pages, metadata and discovery files for the static site.

The search app is a hash-routed single page, which search engines and AI
answer engines mostly cannot read. This module writes plain HTML alongside it:
a pre-rendered summary inside the home page, one page per year, methodology,
FAQ and data pages, plus sitemap.xml, robots.txt, llms.txt, CNAME and JSON-LD.
Every number on these pages is computed from the data at build time.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import urlencode

from .config import ROOT

WIKI_NAMES = {
    "enwiki": "English Wikipedia", "frwiki": "French Wikipedia", "wikidatawiki": "Wikidata",
    "commonswiki": "Wikimedia Commons", "enwiktionary": "English Wiktionary",
    "enwikivoyage": "English Wikivoyage",
}
WIKI_HOSTS = {
    "enwiki": "en.wikipedia.org", "frwiki": "fr.wikipedia.org", "wikidatawiki": "www.wikidata.org",
    "commonswiki": "commons.wikimedia.org", "enwiktionary": "en.wiktionary.org",
    "enwikivoyage": "en.wikivoyage.org",
}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
AI_AGENTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
             "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "CCBot",
             "Amazonbot", "meta-externalagent", "DuckAssistBot", "MistralAI-User"]
CAVEAT = ("An edit from a government network is not evidence of who made it, or that it was made in an "
          "official capacity. Most addresses are shared gateways used by hundreds or thousands of people.")

e = html.escape
NUM = ' class="n"'


def load_site() -> dict:
    return json.loads((ROOT / "config" / "site.json").read_text(encoding="utf-8"))


def n(x: int) -> str:
    return f"{x:,}"


def nice_date(ts: str) -> str:
    y, m, d = ts[:10].split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]} {y}"


def search(depth: int, **params) -> str:
    return "../" * depth + "#/?" + urlencode({k: v for k, v in params.items() if v})


def ld(obj: dict) -> str:
    return ('<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
            + "</script>")


# --- shared numbers ----------------------------------------------------------

def is_biography(topics: list | None) -> bool | None:
    """True/False from Wikimedia's topic model; None when the page has not been classified yet."""
    if topics is None:
        return None
    return any("Biography" in (t.get("topic") or "") for t in topics)


def gather(agg: dict, sums: dict[str, str], site: dict, topic_pages: dict) -> dict:
    """Combine the site-wide tallies from site.build with each year's summary.json.

    Unless config/site.json sets index_biographies, the crawlable pages list only
    pages that Wikimedia's topic model has classified and has not tagged as a
    biography. Those edits stay in the search; they are just not put in front of
    search engines next to a person's name.
    """
    keep_bios = bool(site.get("index_biographies"))
    years = []
    for p in sorted((ROOT / "data").glob("[0-9][0-9][0-9][0-9]/summary.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        y = p.parent.name
        years.append({
            "year": y, "edits": s["total_edits"], "ips": s["unique_ips"],
            "by_label": s["by_label"], "by_wiki": s["by_wiki"], "by_month": s["by_month"],
            "top_pages": [p for p in s["top_pages"] if keep_bios
                          or is_biography(topic_pages.get(f"{p['wiki']}|{p['title']}")) is False],
            "errors": sum(len(v.get("block_errors") or []) if isinstance(v.get("block_errors"), list)
                          else int(v.get("block_errors") or 0) for v in (s.get("scan_status") or {}).values()),
            "sha256": sums.get(f"data/{y}/edits.jsonl", ""),
        })
    return {**agg, "years": years, "keep_bios": keep_bios}


def org(site: dict) -> dict:
    return {"@type": "Organization", "name": site["publisher"]["name"], "url": site["publisher"]["url"]}


def dataset_ld(site: dict, g: dict, built: str) -> dict:
    base = site["base_url"]
    return {
        "@context": "https://schema.org", "@type": "Dataset", "@id": base + "data.html#dataset",
        "name": f"{site['name']}: anonymous Wikipedia edits from Government of Canada networks",
        "alternateName": "wikisscbot archive",
        "description": (f"{n(g['edits'])} edits made without logging in to Wikipedia, Wikidata, Wikimedia Commons, "
                        f"Wiktionary and Wikivoyage from {n(g['ips'])} IP addresses on Government of Canada "
                        f"networks, {nice_date(g['first'])} to {nice_date(g['last'])}. Each record has the time, "
                        "wiki, page, network label, IP address, size change, edit summary and a link to the diff. "
                        "Every data pull is checksummed, hash-chained and timestamped with OpenTimestamps."),
        "url": base + "data.html", "keywords": site["keywords"], "inLanguage": ["en", "fr"],
        "isAccessibleForFree": True, "creator": org(site), "publisher": org(site),
        "temporalCoverage": f"{g['first'][:10]}/{g['last'][:10]}",
        "spatialCoverage": {"@type": "Place", "name": "Canada"},
        "dateModified": built,
        "measurementTechnique": "MediaWiki API (list=usercontribs with uciprange) queried for each Government of Canada IP block",
        "variableMeasured": ["timestamp", "wiki", "page title", "network label", "IP address", "IP range",
                             "byte change", "edit summary", "revision ID", "diff URL"],
        "distribution": [{"@type": "DataDownload", "name": f"{y['year']} edits (JSON Lines)",
                          "encodingFormat": "application/x-ndjson",
                          "contentUrl": f"{base}data/{y['year']}/edits.jsonl",
                          **({"sha256": y["sha256"]} if y["sha256"] else {})} for y in g["years"]],
    }


def description(site: dict, g: dict) -> str:
    return (f"Searchable, verifiable archive of {n(g['edits'])} anonymous Wikipedia edits made from Government of "
            f"Canada networks, {g['first'][:4]}–{g['last'][:4]}: Parliament, National Defence, Shared Services "
            "Canada and more.")


# --- page shell --------------------------------------------------------------

def head(site: dict, *, path: str, title: str, desc: str, depth: int, extra_ld: list[dict] | None = None,
         noindex: bool = False) -> str:
    base, pre = site["base_url"], "../" * depth
    url = base + path
    full = title if path == "" else f"{title} | {site['name']}"
    tags = [
        f"<title>{e(full)}</title>",
        f'<meta name="description" content="{e(desc)}">',
        f'<link rel="canonical" href="{e(url)}">',
        '<meta name="robots" content="noindex,follow">' if noindex else
        '<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">',
        f'<meta name="geo.region" content="{e(site["region"])}">',
        f'<meta name="geo.placename" content="Canada">',
        f'<meta name="author" content="{e(site["publisher"]["name"])}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{e(site["name"])}">',
        f'<meta property="og:title" content="{e(full)}">',
        f'<meta property="og:description" content="{e(desc)}">',
        f'<meta property="og:url" content="{e(url)}">',
        f'<meta property="og:image" content="{e(base)}static/og.png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{e(site["name"])}: {e(site["headline"])}">',
        f'<meta property="og:locale" content="{e(site["lang"].replace("-", "_"))}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<link rel="icon" href="{pre}static/favicon.svg" type="image/svg+xml">',
        f'<link rel="alternate" type="text/plain" href="{pre}llms.txt" title="Summary for AI assistants">',
        '<meta name="theme-color" content="#f5f3ee" media="(prefers-color-scheme: light)">',
        '<meta name="theme-color" content="#12120f" media="(prefers-color-scheme: dark)">',
    ]
    tags += [ld(x) for x in (extra_ld or [])]
    return "\n".join(tags)


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:'
         'wght@400;500;600;700&family=IBM+Plex+Serif:wght@600&display=swap" rel="stylesheet">')


def footer_links(depth: int) -> str:
    pre = "../" * depth
    return (f'<nav class="footnav" aria-label="Reference pages"><a href="{pre}years.html">Edits by year</a>'
            f'<a href="{pre}methodology.html">Methodology</a><a href="{pre}faq.html">FAQ</a>'
            f'<a href="{pre}data.html">Data &amp; verification</a></nav>')


def page(site: dict, *, path: str, title: str, desc: str, body: str, built: str, depth: int = 0,
         extra_ld: list[dict] | None = None) -> str:
    pre = "../" * depth
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": site["name"], "item": site["base_url"]},
        *([{"@type": "ListItem", "position": 2, "name": "Edits by year", "item": site["base_url"] + "years.html"},
           {"@type": "ListItem", "position": 3, "name": title, "item": site["base_url"] + path}] if depth else
          [{"@type": "ListItem", "position": 2, "name": title, "item": site["base_url"] + path}])]}
    return f"""<!doctype html>
<html lang="{e(site['lang'])}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head(site, path=path, title=title, desc=desc, depth=depth, extra_ld=[crumbs, *(extra_ld or [])])}
{FONTS}
<link rel="stylesheet" href="{pre}static/style.css">
</head>
<body>
<header class="top">
  <div class="wrap top-inner">
    <a class="brand" href="{pre or './'}">
      <span class="brand-mark" aria-hidden="true">▚</span>
      <span class="brand-name">{e(site['name'])}</span>
      <span class="brand-tag">{e(site['tagline'])}</span>
    </a>
    <nav class="nav">
      <a href="{pre}#/">Search</a>
      <a href="{pre}#/ips">Addresses</a>
      <a href="{pre}#/topics">Topics</a>
      <a href="{pre}#/ranges">Ranges</a>
      <a href="{pre}years.html">Years</a>
      <a href="{pre}#/provenance">Provenance</a>
      <a href="{pre}faq.html">FAQ</a>
    </nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="foot wrap">
  <span>{e(site['name'])} · built {e(built[:10])} · a <a href="{e(site['publisher']['url'])}">{e(site['publisher']['name'])}</a> project</span>
  {footer_links(depth)}
  <span>{e(CAVEAT.split('. ')[0])}.</span>
</footer>
</body>
</html>
"""


def table(headers: list[str], rows: list[list[str]], numeric: set[int] = frozenset()) -> str:
    cls = lambda i: NUM if i in numeric else ""
    th = "".join(f"<th{cls(i)}>{h}</th>" for i, h in enumerate(headers))
    trs = "".join("<tr>" + "".join(f"<td{cls(i)}>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="tablewrap"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


def stats(items: list[tuple[str, str]]) -> str:
    return '<div class="stats">' + "".join(f'<div class="stat"><b>{v}</b><span>{e(k)}</span></div>'
                                           for k, v in items) + "</div>"


def year_table(g: dict, depth: int = 0) -> str:
    pre = "../" * depth
    rows = []
    for y in reversed(g["years"]):
        top_label = next(iter(y["by_label"]), "")
        top = y["top_pages"][0] if y["top_pages"] else None
        rows.append([f'<a href="{pre}years/{y["year"]}.html">{y["year"]}</a>', n(y["edits"]), n(y["ips"]),
                     e(top_label), e(top["title"]) if top else ""])
    return table(["Year", "Edits", "Addresses", "Busiest network",
                  "Most-edited page" if g["keep_bios"] else "Most-edited page (biographies excluded)"], rows, {1, 2})


# --- pages -------------------------------------------------------------------

def home_prerender(site: dict, g: dict) -> str:
    labels = sorted(g["by_label"].items(), key=lambda kv: -kv[1])[:12]
    wikis = sorted(g["by_wiki"].items(), key=lambda kv: -kv[1])
    return f"""<div class="prerender">
<h1>{e(site['headline'])}</h1>
<p class="lede">{e(site['name'])} is a searchable archive of {n(g['edits'])} edits made to Wikipedia and its sister projects without logging in, from {n(g['ips'])} IP addresses on Government of Canada networks, between {nice_date(g['first'])} and {nice_date(g['last'])}. Every data pull is checksummed, hash-chained and timestamped in Bitcoin, so the record can be verified independently.</p>
{stats([("edits archived", n(g['edits'])), ("government addresses", n(g['ips'])), ("pages edited", n(g['pages'])), ("years covered", f"{g['first'][:4]}–{g['last'][:4]}")])}
<p class="loading" id="prerender-status">Loading the search…</p>
<noscript><p class="note">The search needs JavaScript. The year pages, methodology and data downloads below work without it.</p></noscript>
<h2>Edits by year</h2>
{year_table(g)}
<h2>Edits by network</h2>
{table(["Network label", "Edits"], [[f'<a href="{search(0, label=k)}">{e(k)}</a>', n(v)] for k, v in labels], {1})}
<h2>Edits by wiki</h2>
{table(["Wiki", "Edits"], [[e(WIKI_NAMES.get(k, k)), n(v)] for k, v in wikis], {1})}
<p class="note">{e(CAVEAT)}</p>
<p class="small muted">Read the <a href="methodology.html">methodology</a>, the <a href="faq.html">FAQ</a>, or <a href="data.html">download and verify the data</a>.</p>
</div>"""


def home_ld(site: dict, g: dict, built: str) -> list[dict]:
    base = site["base_url"]
    return [{"@context": "https://schema.org", "@type": "WebSite", "@id": base + "#website", "url": base,
             "name": site["name"], "alternateName": ["revisionhistory.ca", "wikisscbot"],
             "description": description(site, g), "inLanguage": site["lang"], "publisher": org(site),
             "dateModified": built},
            dataset_ld(site, g, built)]


def year_page(site: dict, g: dict, y: dict, labels: dict, built: str) -> str:
    yr = y["year"]
    years = [x["year"] for x in g["years"]]
    i = years.index(yr)
    nav = " · ".join(filter(None, [
        f'<a href="{years[i - 1]}.html">← {years[i - 1]}</a>' if i > 0 else "",
        '<a href="../years.html">All years</a>',
        f'<a href="{years[i + 1]}.html">{years[i + 1]} →</a>' if i + 1 < len(years) else ""]))
    months = [[f"{MONTHS[int(k[5:7]) - 1]} {yr}", n(v)] for k, v in y["by_month"].items()]
    peak = max(y["by_month"].items(), key=lambda kv: kv[1]) if y["by_month"] else None
    top_label, top_n = next(iter(y["by_label"].items()), ("", 0))
    pages = []
    for p in y["top_pages"][:25]:
        shown = labels.get(f"{p['wiki']}|{p['title']}") or p["title"]
        host = WIKI_HOSTS.get(p["wiki"])
        link = (f'<a href="https://{host}/wiki/{e(p["title"].replace(" ", "_"))}" rel="noopener">{e(shown)}</a>'
                if host else e(shown))
        pages.append([link, e(WIKI_NAMES.get(p["wiki"], p["wiki"])),
                      f'<a href="{search(1, title=p["title"], wiki=p["wiki"], year=yr)}">{n(p["edits"])}</a>'])
    desc = (f"{n(y['edits'])} anonymous Wikipedia edits from {n(y['ips'])} Government of Canada addresses in "
            f"{yr}, broken down by network, month and most-edited pages, with verified downloads.")
    sentence = (f"In {yr}, {n(y['ips'])} IP addresses on Government of Canada networks made {n(y['edits'])} edits "
                f"to Wikipedia and its sister projects without logging in.")
    if top_label:
        sentence += f" The busiest network label was {top_label}, with {n(top_n)} edits."
    if peak:
        sentence += f" The busiest month was {MONTHS[int(peak[0][5:7]) - 1]}, with {n(peak[1])} edits."
    body = f"""<p class="back">{nav}</p>
<h1>Government of Canada Wikipedia edits in {yr}</h1>
<p class="lede">{e(sentence)}</p>
{stats([("edits", n(y['edits'])), ("addresses", n(y['ips'])), ("network labels", n(len(y['by_label']))), ("wikis", n(len(y['by_wiki'])))])}
<p><a class="btn primary" href="{search(1, year=yr)}">Search the {yr} edits</a> <a class="btn" href="../data/{yr}/edits.jsonl" download>Download {yr} (JSON Lines)</a></p>
<h2>By network</h2>
{table(["Network label", "Edits"], [[f'<a href="{search(1, year=yr, label=k)}">{e(k)}</a>', n(v)] for k, v in list(y["by_label"].items())[:15]], {1})}
<h2>By wiki</h2>
{table(["Wiki", "Edits"], [[e(WIKI_NAMES.get(k, k)), n(v)] for k, v in y["by_wiki"].items()], {1})}
<h2>By month</h2>
{table(["Month", "Edits"], months, {1})}
<h2>Most-edited pages</h2>
{table(["Page", "Wiki", "Edits from government networks"], pages, {2})}
{"" if g["keep_bios"] else f'<p class="small muted">Biographies and pages not yet classified by topic are left out of this list. They are in the <a href="{search(1, year=yr)}">search</a>.</p>'}
<h2>Verify this file</h2>
<div class="prose">
<p>The {yr} file is published byte-for-byte as collected. Its SHA-256 is:</p>
<p class="hash">{e(y['sha256'] or 'not yet recorded')}</p>
<p>That hash is recorded in <a href="../data/SHA256SUMS">SHA256SUMS</a> and in a signed, Bitcoin-timestamped manifest. See <a href="../data.html">data and verification</a>. {'The collection run reported no errors for this year.' if not y['errors'] else f"The collection run reported {y['errors']} block errors for this year, so the count may be incomplete."}</p>
<p class="note">{e(CAVEAT)}</p>
</div>"""
    return page(site, path=f"years/{yr}.html", title=f"Government of Canada Wikipedia edits in {yr}", desc=desc,
                body=body, built=built, depth=1)


def years_page(site: dict, g: dict, built: str) -> str:
    body = f"""<h1>Edits by year</h1>
<p class="lede">Anonymous edits to Wikipedia and its sister projects from Government of Canada networks, for every year from {g['years'][0]['year']} to {g['years'][-1]['year']}. Each year is re-collected in full on every run, and its file is checksummed and timestamped.</p>
{year_table(g)}
<p class="small muted">English Wikipedia stopped publishing the IP addresses of logged-out editors on 4 November 2025, so the archive ends on 3 November 2025.</p>"""
    return page(site, path="years.html", title="Government of Canada Wikipedia edits by year",
                desc=f"Year-by-year counts of anonymous Wikipedia edits from Government of Canada networks, "
                     f"{g['years'][0]['year']}–{g['years'][-1]['year']}, with the busiest network and most-edited page for each year.",
                body=body, built=built)


def faq_items(site: dict, g: dict) -> list[tuple[str, str]]:
    first_y, last_y = g["years"][0]["year"], g["years"][-1]["year"]
    return [
        (f"What is {site['name']}?",
         f"{site['name']} is a public archive of edits made to Wikipedia, Wikidata, Wikimedia Commons, Wiktionary and "
         f"Wikivoyage, without logging in, from IP addresses on Government of Canada networks. It currently holds "
         f"{n(g['edits'])} edits from {n(g['ips'])} addresses, covering {first_y} to {last_y}. It is published by "
         f"{site['publisher']['name']} and built with an open collector called wikisscbot."),
        ("Where does the data come from?",
         "From Wikipedia itself. Until November 2025, Wikimedia wikis published the IP address of anyone who edited "
         "without logging in. The collector asks the public MediaWiki API for every contribution from each "
         "Government of Canada address block, year by year. Nothing is scraped from private systems."),
        ("Which networks count as Government of Canada?",
         "Two sources. The first is the public-domain list of department address ranges compiled for the @gccaedits "
         "bot in 2014–16, which covers Parliament, National Defence, the CBC and other departments. The second is "
         "every address prefix announced by Shared Services Canada's networks (AS2665, AS2675, AS2682, AS25689 and "
         "AS806), taken from RIPEstat routing records."),
        ("Does an edit from a government network mean the government made it?",
         "No. It means the edit left through a government network. " + CAVEAT + " The archive attributes edits to "
         "networks and never to named individuals."),
        ("Can you tell which department made an edit?",
         "Sometimes. Labels such as House of Commons or National Defence come from ranges those institutions ran "
         "themselves. The label Shared Services Canada means the edit left through shared infrastructure that serves "
         "dozens of departments, so the department cannot be determined from the address alone."),
        (f"Why does the archive stop in {last_y}?",
         "On 4 November 2025 English Wikipedia replaced public IP attribution with temporary accounts, and other "
         "Wikimedia wikis followed. Logged-out edits made since then no longer show an IP address publicly. The "
         "archive ends on 3 November 2025 and does not try to reveal later addresses."),
        ("What was @gccaedits?",
         "@gccaedits was a Twitter bot, launched in July 2014 by Nick Ruest, that tweeted each anonymous Wikipedia "
         "edit made from Government of Canada addresses. It was modelled on Ed Summers's @congressedits and drew "
         f"wide press coverage in 2014. It stopped posting in April 2023. {site['name']} rebuilds the idea as a "
         "complete, searchable archive instead of a live feed."),
        ("How can I verify the data?",
         "Every data pull writes a manifest listing the SHA-256 of each API response and each output file. Manifests "
         "are chained by hash, so altering an old run breaks every later link, and each one is timestamped in "
         "Bitcoin with OpenTimestamps. The site checks the files in your browser, and the same checks can be run "
         "with standard tools. The data page has the steps."),
        ("How complete is it?",
         "Every configured year is re-collected in full on each run instead of being updated incrementally, and "
         "the collection status for each year is published. Edits that Wikipedia administrators have deleted or "
         "suppressed are not returned by the API and are not in the archive. Addresses outside the known ranges "
         "are not covered."),
        ("How should I cite it?",
         f"Cite the site name, the publisher and the date you accessed it, for example: {site['name']} "
         f"({site['domain']}), {site['publisher']['name']}, accessed [date]. For a specific finding, also give the "
         "link to the Wikipedia diff, which is the primary source, and the manifest hash shown on the provenance "
         "page."),
        ("Is it legal to publish this?",
         "The records are public. Wikipedia published each edit and its IP address under its own terms, and told "
         "logged-out editors that their address would be publicly visible. The archive reorganises that public "
         "record. This is general information, not legal advice."),
        ("How do I report an error?",
         f"Contact {site['publisher']['name']} through {site['publisher']['url']}. Corrections to a network label "
         "are recorded in the public change log."),
    ]


def faq_page(site: dict, g: dict, built: str) -> str:
    items = faq_items(site, g)
    body = '<h1>Frequently asked questions</h1>\n<div class="prose">\n' + "\n".join(
        f"<h2>{e(q)}</h2>\n<p>{e(a)}</p>" for q, a in items) + "\n</div>"
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}
    return page(site, path="faq.html", title="FAQ", body=body, built=built, extra_ld=[faq_ld],
                desc=f"What {site['name']} is, where the data comes from, what a government network edit does and "
                     "does not prove, and how to verify and cite the archive.")


def methodology_page(site: dict, g: dict, built: str) -> str:
    body = f"""<h1>Methodology</h1>
<div class="prose">
<p class="lede">How the {n(g['edits'])} edits in the archive were collected, labelled and secured, and what the data cannot show.</p>
<h2>Collection</h2>
<p>For every Government of Canada IP block, the collector asks the MediaWiki API for all logged-out contributions in a calendar year (<span class="mono">list=usercontribs</span> with <span class="mono">uciprange</span>). It covers English and French Wikipedia, Wikidata, Wikimedia Commons, English Wiktionary and English Wikivoyage. Blocks are queried at /16 or smaller, and a block that times out is split into smaller blocks down to /24 until it succeeds. Every configured year is collected again in full on every run.</p>
<h2>Network labels</h2>
<p>Each address gets the label of the most specific range that contains it. Ranges come from the public-domain department list compiled for @gccaedits in 2014–16, and from every prefix announced by Shared Services Canada's networks (AS2665, AS2675, AS2682, AS25689, AS806) according to RIPEstat. A department label is a lead, not proof. The label "Shared Services Canada" means the department cannot be determined.</p>
<h2>Topics</h2>
<p>Pages are classified with Wikimedia's own article-topic model and with keyword groups called beats, tuned for Canadian government reporting. Beats are simple rules and will mislabel some pages.</p>
<h2>Provenance</h2>
<p>Each run writes a manifest with the code version, the parameters, the SHA-256 of every API response and every output file, and the hash of the previous manifest. The chain of manifests is timestamped in Bitcoin with OpenTimestamps. Published files are byte-for-byte copies, and the site re-checks their hashes in the browser. See <a href="data.html">data and verification</a>.</p>
<h2>Limits</h2>
<ul>
<li>{e(CAVEAT)}</li>
<li>English Wikipedia stopped publishing the IP addresses of logged-out editors on 4 November 2025. Later edits are out of scope, and nothing here tries to reveal them.</li>
<li>Edits that have been deleted or suppressed on Wikipedia are not returned by the API.</li>
<li>Address ranges change hands. A range that is a government network today may not have been one in an earlier year, and the reverse.</li>
<li>Edits made from home networks, mobile networks or VPNs by government staff are not captured.</li>
</ul>
<h2>Source code</h2>
<p>The collector, the site and the full build log are open: <a href="{e(site['repo'])}" rel="noopener">{e(site['repo'].replace('https://', ''))}</a>.</p>
</div>"""
    return page(site, path="methodology.html", title="Methodology", body=body, built=built,
                desc="How Revision History collects anonymous Wikipedia edits from Government of Canada IP ranges, "
                     "labels networks, secures each data pull with checksums and Bitcoin timestamps, and what the data cannot show.")


def data_page(site: dict, g: dict, built: str, chain_len: int, latest: dict | None) -> str:
    rows = [[y["year"], n(y["edits"]), f'<a href="data/{y["year"]}/edits.jsonl" download>edits.jsonl</a>',
             f'<span class="hash">{e(y["sha256"])}</span>'] for y in reversed(g["years"])]
    latest_line = (f'<p>The latest manifest in the chain is <span class="hash">{e(latest["sha256"])}</span>.</p>'
                   if latest else "")
    body = f"""<h1>Data and verification</h1>
<div class="prose">
<p class="lede">The full archive is free to download: {n(g['edits'])} edits, {g['years'][0]['year']} to {g['years'][-1]['year']}, one JSON Lines file per year. Each line is one edit with its time, wiki, page, network label, IP address, byte change, edit summary and diff link.</p>
</div>
{table(["Year", "Edits", "File", "SHA-256"], rows, {1})}
<div class="prose">
<h2>Check the files</h2>
<p>The archive has {n(chain_len)} signed data pulls in its hash chain. {latest_line}</p>
<pre class="code">git clone {e(site['repo'])}
cd wikisscbot
python -m wikisscbot verify          # walks the chain, rechecks every hash
sha256sum -c data/SHA256SUMS         # the same file check with standard tools
pip install opentimestamps-client
ots verify data/manifests/&lt;run&gt;.json.ots   # Bitcoin timestamp</pre>
<p>The <a href="./#/provenance">provenance page</a> lists every run with its hashes and timestamp status, and can walk the chain in your browser. Checksums for every file are in <a href="data/SHA256SUMS">SHA256SUMS</a>, and the run-by-run log is in <a href="data/BUILDLOG.md">BUILDLOG.md</a>.</p>
<h2>How to cite</h2>
<p>{e(site['name'])} ({e(site['domain'])}), {e(site['publisher']['name'])}, accessed [date]. For a specific edit, cite the Wikipedia diff as the primary source.</p>
<p class="note">{e(CAVEAT)}</p>
</div>"""
    return page(site, path="data.html", title="Data and verification", body=body, built=built,
                extra_ld=[dataset_ld(site, g, built)],
                desc=f"Download {n(g['edits'])} anonymous Wikipedia edits from Government of Canada networks as JSON "
                     "Lines, with SHA-256 checksums, a hash chain and Bitcoin timestamps for every data pull.")


# --- discovery files ---------------------------------------------------------

def robots(site: dict) -> str:
    rules = "Allow: /\nDisallow: /data/manifests/\n"
    return ("# Revision History welcomes search engines and AI answer engines.\n"
            "# Only the bulky per-run provenance logs are excluded from crawling.\n\n"
            f"User-agent: *\n{rules}\n"
            + "".join(f"User-agent: {a}\n" for a in AI_AGENTS) + rules
            + f"\nSitemap: {site['base_url']}sitemap.xml\n")


def sitemap(site: dict, g: dict, built: str) -> str:
    base, day = site["base_url"], built[:10]
    urls = [("", "1.0"), ("years.html", "0.8"), ("faq.html", "0.7"), ("methodology.html", "0.7"),
            ("data.html", "0.7")] + [(f"years/{y['year']}.html", "0.6") for y in reversed(g["years"])]
    body = "".join(f"<url><loc>{e(base + p)}</loc><lastmod>{day}</lastmod><priority>{pr}</priority></url>\n"
                   for p, pr in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")


def llms_txt(site: dict, g: dict, built: str) -> str:
    base = site["base_url"]
    labels = sorted(g["by_label"].items(), key=lambda kv: -kv[1])[:8]
    lines = [
        f"# {site['name']}", "",
        f"> {description(site, g)} Published by {site['publisher']['name'].rstrip('.')}. Data built {built[:10]}.", "",
        "## Key facts", "",
        f"- {n(g['edits'])} edits from {n(g['ips'])} IP addresses, {nice_date(g['first'])} to {nice_date(g['last'])}.",
        "- Sources: English and French Wikipedia, Wikidata, Wikimedia Commons, English Wiktionary, English Wikivoyage.",
        "- Edits are those made without logging in, where Wikipedia published the editor's IP address.",
        "- Networks: the @gccaedits department range list plus Shared Services Canada's routed prefixes (AS2665, AS2675, AS2682, AS25689, AS806).",
        "- The archive ends on 3 November 2025, because English Wikipedia replaced public IP attribution with temporary accounts on 4 November 2025.",
        "- Every data pull is checksummed (SHA-256), hash-chained and timestamped in Bitcoin with OpenTimestamps.",
        f"- Important caveat: {CAVEAT}",
        "- Edits are attributed to networks, never to named individuals.", "",
        "## Edits by network label", "",
        *[f"- {k}: {n(v)}" for k, v in labels], "",
        "## Edits by year", "",
        *[f"- [{y['year']}]({base}years/{y['year']}.html): {n(y['edits'])} edits from {n(y['ips'])} addresses"
          for y in reversed(g["years"])], "",
        "## Pages", "",
        f"- [Search the archive]({base}): full-text search with filters by year, wiki, network, address and topic",
        f"- [Edits by year]({base}years.html): one summary page per year",
        f"- [Methodology]({base}methodology.html): collection, labelling, provenance and limits",
        f"- [FAQ]({base}faq.html): what the data does and does not show",
        f"- [Data and verification]({base}data.html): downloads, checksums and how to cite", "",
        "## Data", "",
        *[f"- [{y['year']} edits, JSON Lines]({base}data/{y['year']}/edits.jsonl)" for y in reversed(g["years"])], "",
        "## Citing", "",
        f"Cite as: {site['name']} ({site['domain']}), {site['publisher']['name'].rstrip('.')}. For a specific edit, cite the "
        "Wikipedia diff as the primary source.", "",
    ]
    return "\n".join(lines)


def write_all(out: Path, agg: dict, built: str, chain_len: int, latest: dict | None, cache: dict) -> dict:
    """Write every static page and discovery file; return the head and prerender for index.html."""
    site = load_site()
    sums = {}
    sums_path = ROOT / "data" / "SHA256SUMS"
    if sums_path.exists():
        for line in sums_path.read_text().splitlines():
            if "  " in line:
                digest, name = line.split("  ", 1)
                sums[name] = digest
    g = gather(agg, sums, site, cache.get("pages") or {})
    labels = cache.get("labels") or {}
    written = 0
    if g["years"] and g["edits"]:
        (out / "years").mkdir(parents=True, exist_ok=True)
        pages = {
            "years.html": years_page(site, g, built), "faq.html": faq_page(site, g, built),
            "methodology.html": methodology_page(site, g, built),
            "data.html": data_page(site, g, built, chain_len, latest),
            **{f"years/{y['year']}.html": year_page(site, g, y, labels, built) for y in g["years"]},
            "sitemap.xml": sitemap(site, g, built), "llms.txt": llms_txt(site, g, built),
        }
        for rel, text in pages.items():
            (out / rel).write_text(text, encoding="utf-8")
        written = len(pages)
    (out / "robots.txt").write_text(robots(site), encoding="utf-8")
    (out / "CNAME").write_text(site["domain"] + "\n", encoding="utf-8")
    ok = bool(g["years"] and g["edits"])
    desc = description(site, g) if ok else f"{site['headline']}."
    title = f"{site['name']}: {site['headline']}"
    return {
        "site": site, "pages": written + 2,
        "head": head(site, path="", title=title, desc=desc, depth=0, extra_ld=home_ld(site, g, built) if ok else None),
        "head_404": head(site, path="", title=title, desc=desc, depth=0, noindex=True),
        "prerender": home_prerender(site, g) if ok else "",
        "footer": footer_links(0),
    }

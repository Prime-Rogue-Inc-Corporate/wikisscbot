"""Build the HTML report, CSVs and README from results.json."""
import json, csv, collections, os, sys, html

R = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
SHOW = ('strong', 'moderate')

# ------------------------------------------------------------------ compact data for the page
def slim_match(m):
    o = m['other']; e = m['evidence']
    return {'g': m['grade'], 's': m['score'], 'm': m['mechanism'], 'd': m['mech_detail'], 'ip': o['ip'], 'n': o['n'],
            'f': o['from'], 't': o['to'], 'p': o['top_pages'][:3], 'sh': e['shared_pages'], 'sl': e['shared_list'][:3],
            'ti': round(e['title'], 2), 'se': round(e['sect'], 2), 'fr': round(e['free'], 2), 'hr': round(e['hour'], 2)}

years = {}
tally = collections.Counter()
for y, Y in R['years'].items():
    rows = []
    yt = collections.Counter()
    for r in Y['rows']:
        th = []
        for t in r['threads']:
            th.append({'p': t['top_pages_year'][:4], 'ny': t['n_year'], 'n': t['n'], 'f': t['from'], 't': t['to'],
                       'sec': t['sections'][:3], 'sum': t['summaries'][:3], 'ns': t['no_summary_share'],
                       'mt': [slim_match(m) for m in t['matches'] if m['grade'] in SHOW]})
        b = r['best'] if r['best'] and r['best']['grade'] in SHOW else None
        key = (b['grade'], b['mechanism']) if b else ('none', '')
        yt[key] += 1; tally[key] += 1
        rows.append({'k': r['rank'], 'ip': r['ip'], 'lab': r['label'], 'n': r['edits_year'], 'life': r['edits_life'],
                     'first': r['first'], 'last': r['last'], 'pool': r['pool'], 'cov': round(r['covered'] / r['edits_year'], 2),
                     'nt': r['n_threads_year'], 'th': th,
                     'b': ({'g': b['grade'], 'm': b['mechanism'], 'ip': b['other_ip'], 's': b['score']} if b else None)})
    years[y] = {'tot': Y['total_edits'], 'addr': Y['addresses'], 'share': Y['top10_share'], 'rows': rows,
                'tally': {f'{g}|{m}': n for (g, m), n in yt.items()}}

NOTES = {
 '2025': "Two addresses carry 56% of the year. 198.103.249.201 works on Quebec ridings and elections in French Wikipedia and Wikidata; 198.103.167.20 fills in Wikidata records on heraldry. Neither thread appears anywhere else. The quarterly population routine turns up on 205.211.133.133.",
 '2024': "The quietest year. The DND successor pair is now the busiest block and picks up pages last edited from the old DND pool. A Nova Scotia election thread on 205.194.16.3 continues one that ran on 205.193.50.10 in spring 2023.",
 '2023': "Wrestling roster lists dominate and stay on one address. The European airport tables and the Ottawa airport route updates both match earlier addresses. The two House of Commons exits share a thread on the next federal election.",
 '2022': "A CBC address leads with broad, mostly one-off edits and no match. The airport tables are on 198.103.198.249 this year. The population routine makes its single appearance on 198.103.167.20.",
 '2021': "One editor's shipwreck lists run through both House of Commons exits for eight weeks, with the same summaries on each. 198.103.184.76 hosts a long thread on Montreal shopping centres and television schedules.",
 '2020': "The airport tables leave 198.103.104.11 for the 198.103.198.x block when the address is replaced. Naval ship pages appear on both House of Commons exits ahead of the shipwreck run.",
 '2019': "Three of the ten are the DND pool, tied together by a filmography thread that hops between them. The population routine is on 205.193.94.40. Four big threads stay on one address: reality television, Wikidata scientist records, a Canadiens season page, and Hamilton local television.",
 '2018': "198.103.184.76 makes 893 edits, led by a long run of curling results. The population routine and a set of national hockey roster pages both move from 205.211.133.128 to 205.193.94.40 this year.",
 '2017': "198.103.184.76 peaks at 1,170 edits, again led by curling results. All four DND pool addresses work on one family of baronial biographies. A band discography moves from 205.194.127.36 to 198.103.104.11.",
 '2016': "The DND pool takes four of ten places. Ottawa airport route updates are on 198.103.184.76 this year, between their earlier and later homes.",
 '2015': "205.211.133.128 makes 954 edits, mostly single touches to image files on Commons, so little of it forms threads. The DND pool shares a warship page across all four addresses.",
 '2014': "Province-by-province edits to a list of law-enforcement agencies move from a DND address (2013) to 198.103.104.11. The old House of Commons pair behaves as a pool.",
 '2013': "A short-lived DND address, 131.137.247.6, leads the year and then disappears in July. Most other threads this year sit on one address each.",
 '2012': "The DND pool again takes four places, linked by image-review discussions on Commons. A single address makes 87 edits to the Quebec election page.",
}

FINDINGS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'findings.json')))
CURATED = [{'t': f['thread'], 'a': f['addresses'], 'm': f['mechanism'], 'e': f['evidence'], 'r': f['reading'], 'c': f['confidence']}
           for f in FINDINGS['threads']]

page_data = {'meta': R['meta'], 'years': years, 'notes': NOTES, 'curated': CURATED,
             'tally': {f'{g}|{m}': n for (g, m), n in tally.items()}}

# ------------------------------------------------------------------ CSVs
with open(os.path.join(OUT, 'top10_by_year.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['year', 'rank', 'address', 'label', 'edits_in_year', 'share_in_threads', 'thread_top_pages', 'thread_edits_in_year',
                'thread_from', 'thread_to', 'match_grade', 'match_score', 'mechanism', 'matched_address', 'matched_from', 'matched_to',
                'shared_pages', 'title_sim', 'section_sim', 'summary_sim', 'matched_top_pages'])
    for y in sorted(years, reverse=True):
        for r in years[y]['rows']:
            if not r['th']:
                w.writerow([y, r['k'], r['ip'], r['lab'], r['n'], r['cov'], '(no thread of 5+ edits this year)'] + [''] * 14)
            for t in r['th']:
                base = [y, r['k'], r['ip'], r['lab'], r['n'], r['cov'], '; '.join(p for p, _ in t['p']), t['ny'], t['f'], t['t']]
                if not t['mt']:
                    w.writerow(base + ['none'] + [''] * 10)
                for m in t['mt']:
                    w.writerow(base + [m['g'], m['s'], m['m'], m['ip'], m['f'], m['t'], m['sh'], m['ti'], m['se'], m['fr'], '; '.join(p for p, _ in m['p'])])
with open(os.path.join(OUT, 'cross_address_groups.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['group', 'mechanisms', 'max_score', 'address', 'thread_edits', 'from', 'to', 'top_pages'])
    for i, g in enumerate(R['groups'], 1):
        for t in g['threads']:
            w.writerow([i, '+'.join(sorted(g['mechanisms'])), g['max_score'], t['ip'], t['n'], t['from'], t['to'], '; '.join(p for p, _ in t['top_pages'][:3])])

# ------------------------------------------------------------------ HTML
TEMPLATE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'report_template.html')).read()
blob = json.dumps(page_data, ensure_ascii=False).replace('</', '<\\/')
open(os.path.join(OUT, 'report.html'), 'w').write(TEMPLATE.replace('/*__DATA__*/null', blob))
print('tally', dict(tally)); print('html bytes', os.path.getsize(os.path.join(OUT, 'report.html')))

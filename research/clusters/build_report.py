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

FINDINGS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'findings.json')))
CURATED = [{'t': f['thread'], 'a': f['addresses'], 'm': f['mechanism'], 'e': f['evidence'], 'r': f['reading'], 'c': f['confidence']}
           for f in FINDINGS.get('threads', [])]
NOTES = FINDINGS.get('year_notes', {})


page_data = {'meta': R['meta'], 'years': years, 'notes': NOTES, 'curated': CURATED,
             'network': FINDINGS['network'], 'reviewed': FINDINGS['reviewed'],
             'review_current': FINDINGS.get('reviewed_archive') == R['meta'].get('archive'),
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

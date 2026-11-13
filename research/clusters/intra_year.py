"""Intra-year address correlations.

For each calendar year, compare every pair of addresses that were active in that year, using only
that year's edits. The question: which addresses behave as one exit *within the same year*?

Per pair and year:
  shared_pages     pages both edited that year
  shared_rare      of those, pages that at most three addresses edited that year
  page_sim         cosine similarity of their page sets, each page weighted by how few addresses
                   edited it that year (a page 40 addresses touched counts for little)
  relation         same /24, same /16, or different block
  handoffs_60min   times one address edited a page within 60 minutes of the other
  handoff_pages    distinct pages those handoffs happened on
  same_day_pages   distinct (page, UTC day) both edited
  closest_gap_days smallest gap between their edits on any shared page
  weekly_r         Pearson correlation of their weekly edit counts (both need 10+ edits)

Class:
  pool      5+ handoffs, or 3+ handoffs across 2+ pages: the addresses alternate inside one sitting
  same-exit 3+ shared rare pages without that many handoffs: same traffic, but a sitting stays on one address
  linked    exactly 2 shared rare pages
  one-page  exactly one shared page with 3+ edits from each side (weak: busy pages draw crowds)

Calibration: the report counts how often pairs from different /16 blocks reach each threshold,
against pairs inside one /24.

Usage (repo root):  python research/clusters/intra_year.py ./ research/clusters

Gateway-level only. A pair being linked says the two addresses carry the same traffic,
not who is behind it.
"""
import collections
import csv
import datetime as dt
import glob
import itertools
import json
import math
import os
import sys

R = sys.argv[1]
OUT = sys.argv[2]
MIN_EDITS = 5          # an address needs this many edits in the year to be compared
POOL_HANDOFFS = 5
RARE_MAX = 3           # a page is rare if at most this many addresses edited it that year

def relation(a, b):
    if a.rsplit('.', 1)[0] == b.rsplit('.', 1)[0]:
        return 'same /24'
    return 'same /16' if a.split('.')[:2] == b.split('.')[:2] else 'different block'

def archive_fingerprint(root):
    """Short digest of the yearly edit files, so outputs change only when the archive does."""
    import hashlib
    h = hashlib.sha256()
    for f in sorted(glob.glob(os.path.join(root, 'data', '20*', 'edits.jsonl'))):
        h.update(os.path.basename(os.path.dirname(f)).encode())
        h.update(hashlib.sha256(open(f, 'rb').read()).digest())
    return h.hexdigest()[:12]


def load():
    edits = []
    for f in sorted(glob.glob(os.path.join(R, 'data', '20*', 'edits.jsonl'))):
        for line in open(f):
            e = json.loads(line)
            t = dt.datetime.strptime(e['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
            edits.append({'y': e['timestamp'][:4], 'ip': e['ip'], 'label': e['label'], 'p': e['wiki'] + '|' + e['title'],
                          'wiki': e['wiki'], 'title': e['title'], 'ts': t.timestamp(), 'day': e['timestamp'][:10],
                          'week': min(52, (t.timetuple().tm_yday - 1) // 7), 'rev': e['revid']})
    edits.sort(key=lambda e: (e['ts'], e['rev']))
    return edits

def show(p):
    w, t = p.split('|', 1)
    return t if w == 'enwiki' else f'{t} [{w}]'

def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a); vb = sum((x - mb) ** 2 for x in b)
    if va == 0 or vb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)

def analyse_year(year, E):
    by_ip = collections.defaultdict(list)
    for e in E:
        by_ip[e['ip']].append(e)
    active = sorted(ip for ip, es in by_ip.items() if len(es) >= MIN_EDITS)
    label = {ip: by_ip[ip][0]['label'] for ip in by_ip}
    n_addr = len(by_ip)
    page_ips = collections.defaultdict(set)
    for e in E:
        page_ips[e['p']].add(e['ip'])
    idf = {p: math.log(n_addr / len(s)) for p, s in page_ips.items()}
    vec, norm, weekly = {}, {}, {}
    for ip in active:
        pc = collections.Counter(e['p'] for e in by_ip[ip])
        v = {p: math.log1p(k) * idf[p] for p, k in pc.items() if idf[p] > 0}
        vec[ip] = v
        norm[ip] = math.sqrt(sum(x * x for x in v.values())) or 1.0
        w = [0] * 53
        for e in by_ip[ip]:
            w[e['week']] += 1
        weekly[ip] = w
    # handoffs and same-day co-edits, page by page
    by_page = collections.defaultdict(list)
    for e in E:
        by_page[e['p']].append(e)
    hand = collections.Counter(); hand_pages = collections.defaultdict(set); sameday = collections.defaultdict(set)
    for p, es in by_page.items():
        if len(page_ips[p]) < 2:
            continue
        for a, b in zip(es, es[1:]):
            if a['ip'] != b['ip'] and b['ts'] - a['ts'] <= 3600:
                k = tuple(sorted((a['ip'], b['ip'])))
                hand[k] += 1; hand_pages[k].add(p)
        days = collections.defaultdict(set)
        for e in es:
            days[e['day']].add(e['ip'])
        for d, ips in days.items():
            for k in itertools.combinations(sorted(ips), 2):
                sameday[k].add((p, d))
    # candidate pairs: any two active addresses sharing a page
    cand = set()
    act = set(active)
    for p, ips in page_ips.items():
        ips = sorted(ips & act)
        for k in itertools.combinations(ips, 2):
            cand.add(k)
    pairs = []
    all_r = []
    for a, b in itertools.combinations(active, 2):
        if len(by_ip[a]) >= 10 and len(by_ip[b]) >= 10:
            r = pearson(weekly[a], weekly[b])
            if r is not None:
                all_r.append(r)
    for a, b in sorted(cand):
        shared = set(vec[a]) & set(vec[b])
        allshared = set(e['p'] for e in by_ip[a]) & set(e['p'] for e in by_ip[b])
        sim = sum(vec[a][p] * vec[b][p] for p in shared) / (norm[a] * norm[b])
        k = (a, b)
        ta = collections.defaultdict(list); tb = collections.defaultdict(list)
        for e in by_ip[a]:
            if e['p'] in allshared: ta[e['p']].append(e['ts'])
        for e in by_ip[b]:
            if e['p'] in allshared: tb[e['p']].append(e['ts'])
        gap = min(abs(x - y) for p in allshared for x in ta[p] for y in tb[p]) / 86400
        ea = sum(len(ta[p]) for p in allshared); eb = sum(len(tb[p]) for p in allshared)
        h, hp = hand.get(k, 0), len(hand_pages.get(k, ()))
        rare = sum(1 for p in allshared if len(page_ips[p]) <= RARE_MAX)
        if h >= POOL_HANDOFFS or (h >= 3 and hp >= 2):
            cls = 'pool'
        elif rare >= 3:
            cls = 'same-exit'
        elif rare == 2:
            cls = 'linked'
        elif len(allshared) == 1 and ea >= 3 and eb >= 3:
            cls = 'one-page'
        else:
            continue
        r = pearson(weekly[a], weekly[b]) if len(by_ip[a]) >= 10 and len(by_ip[b]) >= 10 else None
        top = sorted(allshared, key=lambda p: (-(len(ta[p]) + len(tb[p])), p))[:4]
        pairs.append({'year': year, 'a': a, 'b': b, 'label_a': label[a], 'label_b': label[b],
                      'edits_a': len(by_ip[a]), 'edits_b': len(by_ip[b]), 'class': cls,
                      'relation': relation(a, b),
                      'shared_pages': len(allshared), 'shared_rare': rare, 'page_sim': round(sim, 3), 'handoffs_60min': h, 'handoff_pages': hp,
                      'same_day_pages': len(sameday.get(k, ())), 'closest_gap_days': round(gap, 2),
                      'weekly_r': None if r is None else round(r, 2),
                      'top_shared': [show(p) for p in top]})
    # groups: addresses joined by pool or linked pairs
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for p in pairs:
        if p['class'] in ('pool', 'same-exit', 'linked'):
            parent[find(p['a'])] = find(p['b'])
    comp = collections.defaultdict(list)
    for ip in list(parent):
        comp[find(ip)].append(ip)
    groups = []
    for members in comp.values():
        members = sorted(members)
        inside = [p for p in pairs if p['a'] in members and p['b'] in members and p['class'] in ('pool', 'same-exit', 'linked')]
        groups.append({'year': year, 'members': members, 'labels': sorted(set(label[m] for m in members)),
                       'edits': sum(len(by_ip[m]) for m in members), 'has_pool': any(p['class'] == 'pool' for p in inside),
                       'kind': 'pool' if any(p['class'] == 'pool' for p in inside) else ('same-exit' if any(p['class'] == 'same-exit' for p in inside) else 'linked'),
                       'cross_block': any(p['relation'] == 'different block' for p in inside),
                       'shared_rare': sum(p['shared_rare'] for p in inside),
                       'handoffs': sum(p['handoffs_60min'] for p in inside),
                       'top_shared': [t for t, _ in collections.Counter(t for p in inside for t in p['top_shared']).most_common(4)]})
    groups.sort(key=lambda g: -g['edits'])
    all_r.sort()
    med = all_r[len(all_r) // 2] if all_r else None
    return {'year': year, 'edits': len(E), 'addresses': n_addr, 'active': len(active),
            'pairs_compared': len(active) * (len(active) - 1) // 2, 'weekly_r_median_all_pairs': None if med is None else round(med, 2),
            'pairs': sorted(pairs, key=lambda p: ({'pool': 0, 'same-exit': 1, 'linked': 2, 'one-page': 3}[p['class']], -p['handoffs_60min'], -p['shared_rare'])),
            'groups': groups}

def main():
    edits = load()
    by_year = collections.defaultdict(list)
    for e in edits:
        by_year[e['y']].append(e)
    years = {y: analyse_year(y, by_year[y]) for y in sorted(by_year, reverse=True)}
    # which pairs recur across years
    seen = collections.defaultdict(dict)
    for y, Y in years.items():
        for p in Y['pairs']:
            if p['class'] in ('pool', 'same-exit', 'linked'):
                seen[(p['a'], p['b'])][y] = p
    persistent = []
    for (a, b), ys in seen.items():
        persistent.append({'a': a, 'b': b, 'label_a': next(iter(ys.values()))['label_a'], 'label_b': next(iter(ys.values()))['label_b'],
                           'years': sorted(ys), 'pool_years': sorted(y for y, p in ys.items() if p['class'] == 'pool'),
                           'handoffs': sum(p['handoffs_60min'] for p in ys.values()),
                           'shared_pages': sum(p['shared_pages'] for p in ys.values())})
    persistent.sort(key=lambda r: (-len(r['years']), -r['handoffs']))
    meta = {'archive': archive_fingerprint(R), 'edits': len(edits), 'years': sorted(years), 'min_edits_per_year': MIN_EDITS,
            'pool_rule': f'{POOL_HANDOFFS}+ handoffs within 60 min, or 3+ across 2+ pages', 'rare_max': RARE_MAX}
    calib = collections.Counter()
    for Y in years.values():
        for p in Y['pairs']:
            if p['shared_rare'] >= 2:
                calib[(p['relation'], '3+' if p['shared_rare'] >= 3 else '2')] += 1
    meta['calibration'] = {f'{r}|{k}': n for (r, k), n in calib.items()}
    # per /24 block and year: handoffs and shared rare pages among its own addresses
    blocks = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, set()]))
    for y, Y in years.items():
        for p in Y['pairs']:
            if p['relation'] == 'same /24':
                b = blocks[p['a'].rsplit('.', 1)[0] + '.x'][y]
                b[0] += p['handoffs_60min']; b[1] += p['shared_rare']; b[2].update((p['a'], p['b']))
    trend = {blk: {y: {'handoffs': v[0], 'shared_rare': v[1], 'addresses': len(v[2])} for y, v in ys.items()}
             for blk, ys in blocks.items() if sum(1 for v in ys.values() if v[1] >= 2 or v[0] >= 3) >= 3}
    meta['block_trend'] = trend
    os.makedirs(OUT, exist_ok=True)
    json.dump({'meta': meta, 'years': years, 'persistent_pairs': persistent}, open(os.path.join(OUT, 'intra_year.json'), 'w'), ensure_ascii=False)
    with open(os.path.join(OUT, 'intra_year_pairs.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        cols = ['year', 'class', 'relation', 'a', 'b', 'label_a', 'label_b', 'edits_a', 'edits_b', 'shared_pages', 'shared_rare', 'page_sim', 'handoffs_60min',
                'handoff_pages', 'same_day_pages', 'closest_gap_days', 'weekly_r']
        w.writerow(cols + ['top_shared'])
        for y in years:
            for p in years[y]['pairs']:
                w.writerow([p[c] for c in cols] + ['; '.join(p['top_shared'])])
    with open(os.path.join(OUT, 'intra_year_groups.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['year', 'members', 'n_members', 'labels', 'edits', 'has_pool', 'handoffs', 'top_shared'])
        for y in years:
            for g in years[y]['groups']:
                w.writerow([y, ' '.join(g['members']), len(g['members']), '; '.join(g['labels']), g['edits'], g['has_pool'], g['handoffs'], '; '.join(g['top_shared'])])
    write_md(meta, years, persistent)
    print(json.dumps({y: {c: sum(1 for p in Y['pairs'] if p['class'] == c) for c in ('pool', 'same-exit', 'linked', 'one-page')} for y, Y in years.items()}))

def short(label):
    return (label.replace('Canadian Department of National Defence', 'National Defence').replace('Canadian House of Commons', 'House of Commons')
            .replace('Shared Services Canada network (AS2665)', 'SSC (AS2665)').replace('Shared Services Canada', 'SSC')
            .replace('Canadian Broadcasting Corporation', 'CBC'))

def write_md(meta, years, persistent):
    L = []
    L.append('# Intra-year address correlations\n')
    L.append(f"Archive fingerprint `{meta['archive']}`: {meta['edits']:,} edits, {meta['years'][0]} to {meta['years'][-1]}. "
             f"Each year is analysed on its own: only addresses with {meta['min_edits_per_year']}+ edits that year, only that year's edits.\n")
    L.append('- **pool**: ' + meta['pool_rule'] + '. The addresses alternate inside one sitting.')
    L.append(f"- **same-exit**: 3+ shared rare pages (a rare page is one at most {meta['rare_max']} addresses edited that year) without that many handoffs. Same traffic, but a sitting stays on one address.")
    L.append('- **linked**: exactly 2 shared rare pages.')
    L.append('- **one-page**: a single shared page with 3+ edits from each side. Weak; listed in the CSV only.\n')
    L.append('Gateway-level only. Nothing here says who is behind an address.\n')
    c = meta['calibration']; g = lambda k: c.get(k, 0)
    L.append('## How often the thresholds fire by chance\n')
    L.append('Pair-years reaching each threshold, by how the two addresses are related. Different blocks are the closest thing to a control.\n')
    L.append('| Relation | 2 shared rare pages | 3 or more |')
    L.append('|---|---|---|')
    for r in ('same /24', 'same /16', 'different block'):
        L.append(f"| {r} | {g(r + '|2')} | {g(r + '|3+')} |")
    L.append('\n## Year summary\n')
    L.append('| Year | Edits | Addresses | Compared | Pool pairs | Same-exit pairs | Linked pairs | Groups | Cross-block groups |')
    L.append('|---|---|---|---|---|---|---|---|---|')
    for y, Y in years.items():
        c = collections.Counter(p['class'] for p in Y['pairs'])
        L.append(f"| {y} | {Y['edits']:,} | {Y['addresses']} | {Y['active']} | {c['pool']} | {c['same-exit']} | {c['linked']} | {len(Y['groups'])} | {sum(1 for g_ in Y['groups'] if g_['cross_block'])} |")
    L.append('\n## Blocks whose addresses keep sharing traffic\n')
    L.append('Handoffs within the hour / shared rare pages, summed over the pairs inside each /24, per year. A fall in handoffs while shared pages hold up means the exit stopped alternating addresses inside a sitting.\n')
    ys = sorted(years)
    L.append('| Block | ' + ' | '.join(y[2:] for y in ys) + ' |')
    L.append('|---|' + '---|' * len(ys))
    for blk, t in sorted(meta['block_trend'].items(), key=lambda kv: -sum(v['shared_rare'] for v in kv[1].values())):
        L.append(f"| {blk} | " + ' | '.join((f"{t[y]['handoffs']}/{t[y]['shared_rare']}" if y in t else '·') for y in ys) + ' |')
    L.append('\n## Links across different blocks\n')
    L.append('Two addresses in unrelated blocks sharing rare pages inside one year. This is where a renumbering in progress, or one editor using two networks, shows up.\n')
    L.append('| Year | Addresses | Labels | Class | Shared rare | Closest edits (days) | Shared pages (top) |')
    L.append('|---|---|---|---|---|---|---|')
    for y, Y in years.items():
        for p in Y['pairs']:
            if p['relation'] == 'different block' and p['class'] in ('pool', 'same-exit', 'linked'):
                labs = short(p['label_a']) if p['label_a'] == p['label_b'] else short(p['label_a']) + ' / ' + short(p['label_b'])
                L.append(f"| {y} | {p['a']} + {p['b']} | {labs} | {p['class']} | {p['shared_rare']} | {p['closest_gap_days']} | {'; '.join(p['top_shared'][:3])} |")
    L.append('\n## Pairs that recur across years\n')
    L.append('Pairs classed pool, same-exit or linked in three or more separate years.\n')
    L.append('| Addresses | Labels | Years | Of which pool | Handoffs |')
    L.append('|---|---|---|---|---|')
    for r in persistent:
        if len(r['years']) < 3:
            continue
        labs = short(r['label_a']) if r['label_a'] == r['label_b'] else short(r['label_a']) + ' / ' + short(r['label_b'])
        L.append(f"| {r['a']} + {r['b']} | {labs} | {len(r['years'])} ({r['years'][0]}–{r['years'][-1]}) | {len(r['pool_years'])} | {r['handoffs']} |")
    for y, Y in years.items():
        L.append(f'\n## {y}\n')
        if not Y['groups']:
            L.append('No address pair met a rule.')
            continue
        L.append('| Group | Kind | Edits | Handoffs | Shared rare | Shared pages (top) |')
        L.append('|---|---|---|---|---|---|')
        for g_ in Y['groups']:
            labs = ', '.join(short(l) for l in g_['labels'])
            L.append(f"| {' + '.join(g_['members'])} ({labs}) | {g_['kind']}{' · cross-block' if g_['cross_block'] else ''} | {g_['edits']:,} | {g_['handoffs']} | {g_['shared_rare']} | {'; '.join(g_['top_shared'][:3])} |")
    open(os.path.join(OUT, 'intra_year.md'), 'w').write('\n'.join(L) + '\n')

if __name__ == '__main__':
    main()

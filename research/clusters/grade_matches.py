"""Grade thread matches, classify the mechanism, and build per-year top-10 tables."""
import pickle, collections, json, re, sys, math, datetime as dt
import numpy as np, networkx as nx

S = pickle.load(open(sys.argv[1], 'rb'))
OUT = sys.argv[2]
ALL, CL, BIG, sc = S['ALL'], S['CL'], S['BIG_ids'], S['score']
BIDX = {c: i for i, c in enumerate(BIG)}
HAND, ADDR, WD = S['HAND'], S['ADDR'], S['WDLAB']
STRONG, MOD, WEAK = 0.60, 0.45, 0.33
DAY = 86400

def disp(p):
    w, t = p.split('|', 1)
    if w == 'wikidatawiki':
        return (WD[p].split(' (')[0] if p in WD else t) + ' [Wikidata]'
    if w == 'enwiki':
        return t
    return f"{t} [{ {'frwiki':'fr','commonswiki':'Commons','enwiktionary':'Wiktionary','enwikivoyage':'Wikivoyage'}.get(w, w)}]"

# ---- pools: connected components of addresses with >=5 same-page handoffs inside an hour
PG = nx.Graph()
for (a, b), k in HAND.items():
    if k >= 5:
        PG.add_edge(a, b, weight=k)
POOL = {}
for i, comp in enumerate(nx.connected_components(PG)):
    for ip in comp:
        POOL[ip] = sorted(comp)

def pool_pages(ip):
    out = set()
    for m in POOL.get(ip, [ip]):
        out |= ADDR[m]['pages']
    return out

def net24(ip):
    return ip.rsplit('.', 1)[0]
by24 = collections.defaultdict(list)
for ip in ADDR:
    by24[net24(ip)].append(ip)

def family(ip):
    """Addresses in the same /24 that came into use within about a year of this one."""
    return [m for m in by24[net24(ip)] if abs(ADDR[m]['q_lo'] - ADDR[ip]['q_lo']) <= 400 * DAY]

# Hand-reviewed pairs that meet the succession rule but are not a network change.
REVIEWED_NOT_RENUMBERING = {
    ('205.193.50.10', '205.194.16'),      # six of the seven carried pages are one Nova Scotia politics thread
    ('192.197.82.153', '205.211.133'),    # carried pages are province articles and the help desk, which many addresses edit
    ('192.197.82.203', '205.211.133'),
}
PAGE_THREAD = {}
for c in CL:
    for p in c['pages']:
        PAGE_THREAD.setdefault((c['ip'], p), c['id'])

# ---- successions: an address (or its pool) goes quiet, another block starts within two years and inherits its pages
SUCC = {}
bigaddr = [ip for ip in ADDR if ADDR[ip]['n'] >= 20]
for L in bigaddr:
    fam = family(L)
    lp = set().union(*[ADDR[m]['pages'] for m in fam])
    start = min(ADDR[m]['q_lo'] for m in fam)
    for F in bigaddr:
        pf = POOL.get(F, [F])
        if F in fam or L in pf:
            continue
        end = max(ADDR[m]['q_hi'] for m in pf)
        if start < end - 90 * DAY or start - end > 2 * 365 * DAY:
            continue
        carried = lp & pool_pages(F)
        carry = len(carried)
        frac = carry / len(lp)
        # the carried pages must come from several separate threads, or it is one editor moving, not a network change
        spread = len(set(PAGE_THREAD[(m, p)] for m in fam for p in carried if (m, p) in PAGE_THREAD))
        if (F, net24(L)) in REVIEWED_NOT_RENUMBERING:
            continue
        if spread >= 3 and ((carry >= 5 and frac >= 0.07) or carry >= 25):
            for f in pf:
                for l in fam:
                    SUCC[(f, l)] = {'carry': carry, 'pages': len(lp), 'earlier_end': dt.datetime.fromtimestamp(end, dt.timezone.utc).strftime('%Y-%m'),
                                    'later_start': dt.datetime.fromtimestamp(start, dt.timezone.utc).strftime('%Y-%m'),
                                    'earlier': sorted(pf), 'later': sorted(fam)}

def mechanism(a, b):
    """a, b: addresses. Returns (code, detail)."""
    k = HAND.get(tuple(sorted((a, b))), 0)
    if k >= 5 or (a in POOL and b in POOL.get(a, [])):
        return 'pool', f'{k} same-page handoffs within an hour'
    for f, l in ((a, b), (b, a)):
        if (f, l) in SUCC:
            s = SUCC[(f, l)]
            return 'renumbering', f"{f} goes quiet {s['earlier_end']}, {l} block starts {s['later_start']}; {s['carry']} of {s['pages']} pages carried over"
    A, B = ADDR[a], ADDR[b]
    first, later = (a, b) if A['q_lo'] <= B['q_lo'] else (b, a)
    F, L = ADDR[first], ADDR[later]
    if L['q_lo'] >= F['q_hi'] - 90 * DAY and net24(a) == net24(b):
        return 'renumbering', f'{first} goes quiet and {later} starts inside the same /24 block'
    return None, ''

def thread_mechanism(ci, cj):
    """Pool and renumbering are properties of the two addresses; otherwise look at timing of the two threads."""
    m, d = mechanism(ci['ip'], cj['ip'])
    if m:
        return m, d
    shared = ci['pages'] & cj['pages']
    ta = np.array(sorted(e['ts'] for e in ci['edits'] if not shared or e['p'] in shared))
    tb = np.array(sorted(e['ts'] for e in cj['edits'] if not shared or e['p'] in shared))
    idx = np.searchsorted(tb, ta)
    gaps = np.minimum(np.abs(ta - tb[np.clip(idx - 1, 0, len(tb) - 1)]), np.abs(ta - tb[np.clip(idx, 0, len(tb) - 1)]))
    gap = float(gaps.min()) / DAY
    if gap <= 30:
        return 'parallel', f'closest edits {gap:.0f} days apart' if gap >= 1 else 'edits on the same day'
    first, later = (ci, cj) if ci['edits'][0]['ts'] <= cj['edits'][0]['ts'] else (cj, ci)
    return 'later', f"{later['ip']} picks it up {gap / 30.4:.0f} months after {first['ip']}"

def span(c):
    return c['edits'][0]['timestamp'][:7], c['edits'][-1]['timestamp'][:7]

def evidence(i, j):
    ci, cj = CL[BIG[i]], CL[BIG[j]]
    shared = ci['pages'] & cj['pages']
    ev = {'shared_pages': len(shared),
          'title': float(S['S_title'][i, j]), 'sect': float(S['S_sect'][i, j]),
          'free': float(S['S_free'][i, j]), 'hour': float(S['S_hour'][i, j]), 'page': float(S['S_page'][i, j])}
    pts = (len(shared) >= 2) + (ev['title'] >= 0.6) + (ev['sect'] >= 0.5) + (ev['free'] >= 0.3)
    ev['points'] = int(pts)
    ev['shared_list'] = [disp(p) for p in sorted(shared, key=lambda p: (-len([1 for e in ci['edits'] if e['p'] == p]), p))[:5]]
    return ev

def grade(i, j):
    s = float(sc[i, j]); ev = evidence(i, j)
    if s >= STRONG and ev['points'] >= 2:
        g = 'strong'
    elif s >= MOD and (ev['shared_pages'] >= 1 or ev['sect'] >= 0.5 or ev['free'] >= 0.3):
        g = 'moderate'
    elif s >= WEAK:
        g = 'weak'
    else:
        g = 'none'
    return g, s, ev

def sample_sections(c, k=3):
    cnt = collections.Counter(e['sect'] for e in c['edits'] if e['sect'])
    return [s for s, _ in cnt.most_common(k)]

def sample_summaries(c, k=3):
    cnt = collections.Counter()
    for e in c['edits']:
        f = e['free']
        if not f or e['boiler']:
            continue
        f = re.sub(r'\S+@\S+', '[email]', f)                       # never carry an address through
        f = re.sub(r'\s[-–—]\s?[A-Z][a-z]+ [A-Z][a-z]+\.?$', '', f)  # drop a trailing personal signature
        f = re.sub(r'https?://\S+', '[link]', f)
        cnt[f[:70]] += 1
    return [s for s, n in cnt.most_common(k)]

def thread_card(c, year=None):
    pc = collections.Counter(e['p'] for e in c['edits'])
    a, b = span(c)
    hrs = S['HR'][BIDX[c['id']]] if c['id'] in BIDX else None
    d = {'id': c['id'], 'ip': c['ip'], 'n': len(c['edits']), 'n_pages': len(c['pages']), 'from': a, 'to': b,
         'top_pages': [[disp(p), n] for p, n in pc.most_common(4)],
         'sections': sample_sections(c), 'summaries': sample_summaries(c),
         'no_summary_share': round(sum(1 for e in c['edits'] if not e['free'] or e['boiler']) / len(c['edits']), 2)}
    if year:
        ye = [e for e in c['edits'] if e['timestamp'][:4] == year]
        d['n_year'] = len(ye)
        d['top_pages_year'] = [[disp(p), n] for p, n in collections.Counter(e['p'] for e in ye).most_common(4)]
    return d

def matches(c, k=3):
    if c['id'] not in BIDX:
        return []
    i = BIDX[c['id']]
    out, seen = [], set()
    for j in np.argsort(-sc[i]):
        if sc[i, j] < WEAK or len(out) >= k:
            break
        d = CL[BIG[j]]
        if d['ip'] in seen:
            continue
        seen.add(d['ip'])
        g, s, ev = grade(i, j)
        m, md = thread_mechanism(c, d)
        out.append({'grade': g, 'score': round(s, 2), 'mechanism': m, 'mech_detail': md, 'evidence': ev,
                    'other': thread_card(d)})
    return out

# ---- per-year top 10
byip_year = collections.defaultdict(lambda: collections.Counter())
for e in ALL:
    byip_year[e['timestamp'][:4]][e['ip']] += 1
cl_by_ip = collections.defaultdict(list)
for c in CL:
    cl_by_ip[c['ip']].append(c)

GR = {'strong': 3, 'moderate': 2, 'weak': 1, 'none': 0}
YEARS = {}
for y in sorted(byip_year, reverse=True):
    rows = []
    tot = sum(byip_year[y].values())
    for rank, (ip, n) in enumerate(byip_year[y].most_common(10), 1):
        cs = []
        for c in cl_by_ip[ip]:
            ny = sum(1 for e in c['edits'] if e['timestamp'][:4] == y)
            if ny:
                cs.append((ny, c))
        cs.sort(key=lambda x: -x[0])
        threads = []
        for ny, c in cs:
            if len(c['edits']) >= 5 and ny >= 5 and len(threads) < 4:
                t = thread_card(c, y)
                t['matches'] = matches(c)
                threads.append(t)
        covered = sum(t['n_year'] for t in threads)
        best = None
        for t in threads:
            for m in t['matches']:
                key = (GR[m['grade']], m['score'])
                if best is None or key > best[0]:
                    best = (key, m, t['id'])
        rows.append({'rank': rank, 'ip': ip, 'label': ADDR[ip]['label'], 'range': ADDR[ip]['range'], 'edits_year': n,
                     'edits_life': ADDR[ip]['n'], 'pool': POOL.get(ip, []),
                     'first': dt.datetime.fromtimestamp(ADDR[ip]['first'], dt.timezone.utc).strftime('%Y-%m'),
                     'last': dt.datetime.fromtimestamp(ADDR[ip]['last'], dt.timezone.utc).strftime('%Y-%m'),
                     'threads': threads, 'covered': covered,
                     'n_threads_year': len(cs),
                     'best': ({'grade': best[1]['grade'], 'mechanism': best[1]['mechanism'], 'score': best[1]['score'],
                               'other_ip': best[1]['other']['ip'], 'thread': best[2]} if best else None)})
    YEARS[y] = {'total_edits': tot, 'addresses': len(byip_year[y]), 'top10_share': round(sum(r['edits_year'] for r in rows) / tot, 3), 'rows': rows}

# ---- archive-wide: every strong cross-address link, grouped
LG = nx.Graph()
n = len(BIG)
ii, jj = np.where(np.triu(sc, 1) >= STRONG)
links = []
for i, j in zip(ii, jj):
    g, s, ev = grade(i, j)
    if g != 'strong':
        continue
    a, b = CL[BIG[i]], CL[BIG[j]]
    m, md = thread_mechanism(a, b)
    LG.add_edge(BIG[i], BIG[j], score=s, mech=m)
    links.append((BIG[i], BIG[j], s, m))
GROUPS = []
for comp in nx.connected_components(LG):
    mech = collections.Counter(d['mech'] for _, _, d in LG.subgraph(comp).edges(data=True))
    cards = sorted((thread_card(CL[c]) for c in comp), key=lambda t: t['from'])
    GROUPS.append({'threads': cards, 'addresses': sorted(set(t['ip'] for t in cards)),
                   'mechanisms': dict(mech), 'edits': sum(t['n'] for t in cards),
                   'max_score': round(max(d['score'] for _, _, d in LG.subgraph(comp).edges(data=True)), 2)})
GROUPS.sort(key=lambda g: -g['edits'])
rowmax = sc.max(1)
META = {'archive': S.get('archive', ''), 'years': sorted(YEARS), 'threads_total': len(CL), 'threads_fingerprinted': len(BIG),
        'edit_mass_fingerprinted': round(sum(len(CL[i]['edits']) for i in BIG) / len(ALL), 3),
        'edits': len(ALL), 'addresses': len(ADDR),
        'best_score_percentiles': {str(p): round(float(np.percentile(rowmax, p)), 2) for p in (50, 75, 90, 95)},
        'share_threads_best_ge_strong': round(float((rowmax >= STRONG).mean()), 3),
        'pools': sorted(set(tuple(v) for v in POOL.values())),
        'thresholds': {'strong': STRONG, 'moderate': MOD, 'weak': WEAK}}
seen = set(); SUCC_LIST = []
for (f, l), v in SUCC.items():
    key = (tuple(v['earlier']), tuple(v['later']))
    if key not in seen:
        seen.add(key); SUCC_LIST.append(v)
META['successions'] = SUCC_LIST
json.dump({'meta': META, 'years': YEARS, 'groups': GROUPS}, open(OUT, 'w'), ensure_ascii=False)
print(json.dumps(META, indent=1))
print('groups', len(GROUPS), collections.Counter(tuple(sorted(g['mechanisms'])) for g in GROUPS))

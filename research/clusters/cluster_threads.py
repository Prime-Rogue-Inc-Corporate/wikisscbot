"""Systematic cluster matching for the wikisscbot archive.

Stage 1  load every edit 2012-2025
Stage 2  per address: build a page graph (same-sitting adjacency + title similarity),
         Louvain communities -> "threads" (clusters)
Stage 3  fingerprint each thread (pages, title words, sections edited, summary words, habits)
Stage 4  score every thread against every thread on a different address
Stage 5  address-pair mechanics: same-page handoffs within 60 min (pool),
         disjoint activity windows + page carry-over (renumbering)
Output   pickle with everything, used by the reporting scripts
"""
import json, glob, re, math, collections, pickle, sys, datetime as dt
import numpy as np, scipy.sparse as sp, networkx as nx

R = sys.argv[1]
OUT = sys.argv[2]
SESSION_GAP = 20 * 60
TITLE_COS = 0.35
RESOLUTION = float(sys.argv[3]) if len(sys.argv) > 3 else 0.6
EPISODE_GAP = float(sys.argv[4]) if len(sys.argv) > 4 else 365
MIN_EDITS = 5          # a thread needs this many edits to be fingerprinted / matched
SEED = 7

# ---------------------------------------------------------------- load
ALL = []
for f in sorted(glob.glob(R + 'data/20*/edits.jsonl')):
    for l in open(f):
        ALL.append(json.loads(l))
TOP = json.load(open(R + 'data/topics.json'))
WDLAB = TOP['labels']
ALL.sort(key=lambda e: (e['timestamp'], e['revid']))
for i, e in enumerate(ALL):
    e['i'] = i
    e['t'] = dt.datetime.strptime(e['timestamp'], '%Y-%m-%dT%H:%M:%SZ')
    e['ts'] = e['t'].timestamp()
    e['p'] = e['wiki'] + '|' + e['title']
    c = e['comment'] or ''
    e['sect'] = ' '.join(re.findall(r'/\*\s*(.*?)\s*\*/', c))
    free = re.sub(r'/\*.*?\*/', '', c).strip()
    e['boiler'] = bool(re.match(r'(Undid revision|Annulation des? modif|Reverted|Révocation|\[\[Property:|Created claim|Changed claim|Added |Removed claim|wbset|wbcreate|wbedit|wbremove)', free)) and e['wiki'] == 'wikidatawiki' or bool(re.match(r'(Undid revision|Annulation des? modif|Révocation)', free))
    e['free'] = free
    e['props'] = re.findall(r'Property:(P\d+)', c)

def disp(p):
    w, t = p.split('|', 1)
    if w == 'wikidatawiki' and p in WDLAB:
        return WDLAB[p].split(' (')[0] + ' [Wikidata]'
    return t if w == 'enwiki' else f'{t} [{w.replace("wiki","") or w}]'

STOP = set('''the of and in for to at on by a an de la le les des du et en list lists talk user wikipedia file
category template with from season canada canadian wikidata new old one two'''.split())
def toks(s):
    out = []
    for w in re.findall(r"[^\W\d_]+", s.lower()):
        if len(w) >= 3 and w not in STOP:
            out.append(w)
    return out

def page_text(p):
    w, t = p.split('|', 1)
    if w == 'wikidatawiki':
        return WDLAB.get(p, '')
    return re.sub(r'^(Talk|User talk|User|Wikipedia|File|Template|Discussion|Utilisateur):', '', t)

PAGES = sorted(set(e['p'] for e in ALL))
PIDX = {p: i for i, p in enumerate(PAGES)}
PTOK = {p: toks(page_text(p)) for p in PAGES}
dfc = collections.Counter(t for p in PAGES for t in set(PTOK[p]))
TOKS = sorted(dfc)
TIDX = {t: i for i, t in enumerate(TOKS)}
TIDF = np.array([math.log(len(PAGES) / dfc[t]) for t in TOKS])

byip = collections.defaultdict(list)
for e in ALL:
    byip[e['ip']].append(e)
IPS = sorted(byip)
NIP = len(IPS)
page_ips = collections.defaultdict(set)
for e in ALL:
    page_ips[e['p']].add(e['ip'])
PIDF = {p: math.log(NIP / len(page_ips[p])) for p in PAGES}

def title_matrix(pages):
    rows, cols, vals = [], [], []
    for r, p in enumerate(pages):
        c = collections.Counter(PTOK[p])
        for t, n in c.items():
            rows.append(r); cols.append(TIDX[t]); vals.append(n * TIDF[TIDX[t]])
    M = sp.csr_matrix((vals, (rows, cols)), shape=(len(pages), len(TOKS)))
    nrm = np.sqrt(M.multiply(M).sum(1)).A1
    nrm[nrm == 0] = 1
    return sp.diags(1 / nrm) @ M

# ---------------------------------------------------------------- stage 2: threads per address
CL = []            # list of clusters
edit_cluster = {}  # edit index -> cluster id
for ip in IPS:
    es = byip[ip]
    pages = sorted(set(e['p'] for e in es))
    G = nx.Graph()
    G.add_nodes_from(pages)
    for a, b in zip(es, es[1:]):
        if a['p'] != b['p'] and b['ts'] - a['ts'] <= SESSION_GAP:
            w = G.get_edge_data(a['p'], b['p'], {}).get('weight', 0) + 1.0
            G.add_edge(a['p'], b['p'], weight=w)
    if len(pages) > 1:
        TM = title_matrix(pages)
        S = (TM @ TM.T).tocoo()
        for i, j, v in zip(S.row, S.col, S.data):
            if i < j and v >= TITLE_COS:
                w = G.get_edge_data(pages[i], pages[j], {}).get('weight', 0) + 1.5 * v
                G.add_edge(pages[i], pages[j], weight=w)
    # same section header edited on pages that share a title word (e.g. "Airlines and destinations" on two airports)
    last_by_sect = {}
    for e in es:
        h = e['sect'].lower().strip()
        if not h:
            continue
        prev = last_by_sect.get(h)
        if prev is not None and prev != e['p'] and set(PTOK[prev]) & set(PTOK[e['p']]):
            w = G.get_edge_data(prev, e['p'], {}).get('weight', 0) + 1.0
            G.add_edge(prev, e['p'], weight=w)
        last_by_sect[h] = e['p']
    comms = nx.community.louvain_communities(G, weight='weight', resolution=RESOLUTION, seed=SEED) if G.number_of_edges() else [{p} for p in pages]
    for com in comms:
        ce = [e for e in es if e['p'] in com]
        # split a community into episodes wherever it falls silent for more than EPISODE_GAP days
        eps, cur = [], [ce[0]]
        for e in ce[1:]:
            if e['ts'] - cur[-1]['ts'] > EPISODE_GAP * 86400:
                eps.append(cur); cur = []
            cur.append(e)
        eps.append(cur)
        for ep in eps:
            cid = len(CL)
            for e in ep:
                edit_cluster[e['i']] = cid
            CL.append({'id': cid, 'ip': ip, 'label': es[0]['label'], 'pages': set(e['p'] for e in ep), 'edits': ep})

print('addresses', NIP, 'edits', len(ALL), 'threads', len(CL), 'threads>=%d edits' % MIN_EDITS, sum(1 for c in CL if len(c['edits']) >= MIN_EDITS), file=sys.stderr)

# ---------------------------------------------------------------- stage 3: fingerprints
BIG = [c for c in CL if len(c['edits']) >= MIN_EDITS]
BIDX = {c['id']: i for i, c in enumerate(BIG)}
n = len(BIG)

def norm_rows(M):
    M = M.tocsr()
    nrm = np.sqrt(M.multiply(M).sum(1)).A1
    nrm[nrm == 0] = 1
    return sp.diags(1 / nrm) @ M

# pages
rows, cols, vals = [], [], []
for r, c in enumerate(BIG):
    pc = collections.Counter(e['p'] for e in c['edits'])
    for p, k in pc.items():
        if PIDF[p] > 0:
            rows.append(r); cols.append(PIDX[p]); vals.append(math.log1p(k) * PIDF[p])
MP = norm_rows(sp.csr_matrix((vals, (rows, cols)), shape=(n, len(PAGES))))
# title words
rows, cols, vals = [], [], []
for r, c in enumerate(BIG):
    pc = collections.Counter(e['p'] for e in c['edits'])
    acc = collections.Counter()
    for p, k in pc.items():
        for t in set(PTOK[p]):
            acc[t] += math.log1p(k)
    for t, v in acc.items():
        rows.append(r); cols.append(TIDX[t]); vals.append(v * TIDF[TIDX[t]])
MT = norm_rows(sp.csr_matrix((vals, (rows, cols)), shape=(n, len(TOKS))))

def text_matrix(getter):
    docs = []
    for c in BIG:
        acc = collections.Counter()
        for e in c['edits']:
            for t in set(getter(e)):
                acc[t] += 1
        docs.append(acc)
    df = collections.Counter(t for d in docs for t in d)
    vocab = {t: i for i, t in enumerate(sorted(t for t in df if df[t] >= 2))}
    rows, cols, vals = [], [], []
    for r, d in enumerate(docs):
        for t, k in d.items():
            if t in vocab:
                rows.append(r); cols.append(vocab[t]); vals.append(math.log1p(k) * math.log(n / df[t]))
    return norm_rows(sp.csr_matrix((vals, (rows, cols)), shape=(n, max(1, len(vocab))))), docs

MS, sect_docs = text_matrix(lambda e: toks(e['sect']))
MF, free_docs = text_matrix(lambda e: [] if e['boiler'] else toks(e['free']) + e['props'])

HR = np.zeros((n, 24)); WD = np.zeros((n, 7))
nosum = np.zeros(n); lsize = np.zeros(n); neg = np.zeros(n); nfree = np.zeros(n); nsect = np.zeros(n)
for r, c in enumerate(BIG):
    for e in c['edits']:
        HR[r, e['t'].hour] += 1; WD[r, e['t'].weekday()] += 1
    k = len(c['edits'])
    fr = [e for e in c['edits'] if e['free'] and not e['boiler']]
    nfree[r] = len(fr); nosum[r] = 1 - len(fr) / k
    nsect[r] = sum(1 for e in c['edits'] if e['sect'])
    lsize[r] = np.median([math.log1p(abs(e['sizediff'])) for e in c['edits']])
    neg[r] = sum(1 for e in c['edits'] if e['sizediff'] < 0) / k
# smooth hours circularly (people do not keep to the clock hour)
HRs = HR + 0.5 * np.roll(HR, 1, 1) + 0.5 * np.roll(HR, -1, 1)
HRs /= np.linalg.norm(HRs, axis=1, keepdims=True)
WDn = WD / np.linalg.norm(WD, axis=1, keepdims=True)

# ---------------------------------------------------------------- stage 4: pairwise scores
S_page = (MP @ MP.T).toarray()
S_title = (MT @ MT.T).toarray()
S_sect = (MS @ MS.T).toarray()
S_free = (MF @ MF.T).toarray()
S_hour = HRs @ HRs.T
S_wd = WDn @ WDn.T
content = 1 - (1 - S_page) * (1 - S_title)

have_sect = (nsect >= 3)
have_free = (nfree >= 3)
both_sect = np.outer(have_sect, have_sect)
both_free = np.outer(have_free, have_free)
# habit agreement: summary habit, edit-size profile, sign of change
hab = 1 - (np.abs(nosum[:, None] - nosum[None, :]) + np.minimum(1, np.abs(lsize[:, None] - lsize[None, :]) / 4) + np.abs(neg[:, None] - neg[None, :])) / 3
parts = [(S_hour, np.ones((n, n), bool), 1.0), (hab, np.ones((n, n), bool), 1.0), (S_sect, both_sect, 1.5), (S_free, both_free, 1.5)]
num = sum(np.where(m, s, 0) * w for s, m, w in parts)
den = sum(np.where(m, 1, 0) * w for s, m, w in parts)
style = num / den
score = content * (0.4 + 0.6 * style)
ipa = np.array([c['ip'] for c in BIG])
same = ipa[:, None] == ipa[None, :]
score[same] = 0

# ---------------------------------------------------------------- stage 5: address-pair mechanics
bypage = collections.defaultdict(list)
for e in ALL:
    bypage[e['p']].append(e)
HAND = collections.Counter()
for p, es in bypage.items():
    for a, b in zip(es, es[1:]):
        if a['ip'] != b['ip'] and b['ts'] - a['ts'] <= 3600:
            HAND[tuple(sorted((a['ip'], b['ip'])))] += 1
ADDR = {}
for ip in IPS:
    ts = np.array([e['ts'] for e in byip[ip]])
    ADDR[ip] = {'n': len(ts), 'first': ts.min(), 'last': ts.max(),
                'q_lo': np.quantile(ts, 0.025), 'q_hi': np.quantile(ts, 0.975),
                'label': byip[ip][0]['label'], 'range': byip[ip][0]['range'],
                'pages': set(e['p'] for e in byip[ip])}

pickle.dump({'ALL': ALL, 'CL': CL, 'BIG_ids': [c['id'] for c in BIG], 'score': score.astype(np.float32),
             'content': content.astype(np.float32), 'style': style.astype(np.float32),
             'S_page': S_page.astype(np.float32), 'S_title': S_title.astype(np.float32),
             'S_sect': S_sect.astype(np.float32), 'S_free': S_free.astype(np.float32), 'S_hour': S_hour.astype(np.float32),
             'HAND': HAND, 'ADDR': ADDR, 'edit_cluster': edit_cluster, 'WDLAB': WDLAB,
             'nosum': nosum, 'lsize': lsize, 'neg': neg, 'HR': HR, 'WD': WD,
             'sect_docs': sect_docs, 'free_docs': free_docs}, open(OUT, 'wb'))
print('done', n, file=sys.stderr)

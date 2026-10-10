"""Build clean input CSVs from raw Wikipedia wikitext snapshots in data/raw/.
Run once after refreshing raw data:  .venv/bin/python scripts/build_data.py
"""
import re, json, csv, os
RAW = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
OUT = os.path.join(os.path.dirname(__file__), '..', 'data')

def parse_house():
    t = open(os.path.join(RAW, '2026_United_States_House_of_Representatives_elections.wiki')).read()
    t = t[t.find('==Alabama=='):]
    blocks = re.split(r"\n!\s*(?:rowspan=\S+\s*\|\s*)?\{\{ushr\|", t)[1:]
    rows = []
    for b in blocks:
        m = re.match(r'([A-Z]{2})\|([^|}]+)', b)
        st, d = m.group(1), m.group(2)
        if st in ('AS', 'DC', 'GU', 'MP', 'VI', 'PR'):
            continue
        body = b.split('{{plainlist')[0]
        pv = re.search(r'\{\{shading PVI\|([A-Z]+)(?:\|(\d+))?', body, re.I)
        s = pv.group(1).upper(); n = int(pv.group(2) or 0)
        pvi = n if s == 'D' else (-n if s == 'R' else 0)
        new = 'new seat' in body.lower() and 'sortname' not in body.lower().split('new seat')[0]
        party = re.search(r'\|\s*(Republican|Democratic|Independent|DFL)\s*\n', body)
        p = None if new else (party.group(1) if party else None)
        vac = 'Vacant' in body
        low = body.lower()
        if new or vac or p is None:
            inc_running = False
        else:
            seg = low.split('incumbent', 1)
            stat = ('incumbent' + seg[1][:200]) if len(seg) > 1 else ''
            inc_running = not any(k in stat for k in ['retir', 'lost', 'resign', 'died', 'withdr', 'not seeking', 'running for'])
        mem = re.search(r'\{\{sortname\|([^|}]+)\|([^|}]+)', body)
        rows.append(dict(
            district=f"{st}-{d}", state=st, pvi_d=pvi,
            inc_party={'Republican': 'R', 'Democratic': 'D', 'DFL': 'D', 'Independent': 'I'}.get(p, ''),
            inc_running=int(inc_running), new_seat=int(new), vacant=int(vac),
            member=(mem.group(1) + ' ' + mem.group(2)) if (mem and not new and p) else ''))
    assert len(rows) == 435, len(rows)
    return rows

SCORE = {'safe': 3, 'solid': 3, 'likely': 2, 'lean': 1, 'tilt': 0.5}
def rating_score(tmpl):
    parts = [x.strip().lower() for x in tmpl.split('|')]
    if parts[0].startswith('toss'):
        return 0.0
    v = SCORE.get(parts[0]);
    if v is None or len(parts) < 2: return None
    return v if parts[1] in ('d', 'dfl') else -v

def parse_house_ratings():
    t = open(os.path.join(RAW, 'house_ratings.wiki')).read()
    out = {}
    for b in re.split(r'\n!\s*\{\{ushr\|', t)[1:]:
        m = re.match(r'([A-Z]{2})\|([^|}]+)', b)
        b = b.split('\n|-')[0]
        sc = [rating_score(x) for x in re.findall(r'\{\{USRaceRating\|([^}]*)\}\}', b)]
        sc = [x for x in sc if x is not None]
        if sc:
            out[f"{m.group(1)}-{m.group(2)}"] = round(sum(sc) / len(sc), 2)
    return out

if __name__ == '__main__':
    rows = parse_house()
    rat = parse_house_ratings()
    for r in rows:
        r['consensus_rating_score'] = rat.get(r['district'], '')   # +3 Safe D ... -3 Safe R; blank = not rated competitive
    with open(os.path.join(OUT, 'house_districts.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    from collections import Counter
    print('districts', len(rows), Counter(r['inc_party'] for r in rows), 'rated', len(rat))

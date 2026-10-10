"""Build data/governor_races.csv from raw Wikipedia snapshots in data/raw/ (pulled 2026-10-10).

Inputs
  data/raw/2026_United_States_gubernatorial_elections.wiki  -> PVI, incumbent, 7 forecaster ratings
      (Cook Oct 1, DDHQ Oct 8, Fox Oct 6, Inside Elections Oct 1, RCP Oct 5, Sabato Oct 6, Silver Bulletin Oct 8)
  data/raw/governor/gov_<State>.wiki                          -> general-election "Aggregate polls" table
  data/markets/polymarket_2026-10-10.json                     -> market odds (comparison only, NOT a model input)

Poll rule (transparent, no judgment calls per race):
  * If the race page has an aggregate-polls table, poll_margin_d = simple mean of the listed aggregators'
    margins (270toWin / DDHQ / FiftyPlusOne / RCP / Race to the WH / Silver Bulletin); poll_sources = count;
    poll_end_date = latest "through"/end date among them.
  * Otherwise, for races that are not unanimously safe (|rating score| < 2.7), MANUAL below lists the mean of the
    most recent nonpartisan polls (field ended after Sep 1); each is cited.
  * Otherwise: no poll; the race runs on the ratings prior only.
Run:  python scripts/build_governor_data.py
"""
import csv, json, os, re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.dirname(HERE)
RAW = os.path.join(MODEL, "data", "raw")

SCORE = {"safe": 3, "solid": 3, "likely": 2, "lean": 1, "tilt": 0.5}
ABBR = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO","Connecticut":"CT",
 "Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL","Iowa":"IA","Kansas":"KS","Maine":"ME",
 "Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH",
 "New Mexico":"NM","New York":"NY","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI",
 "South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Vermont":"VT","Wisconsin":"WI","Wyoming":"WY"}

# Major-party (or main D-side / R-side) nominees. Sources: Wikipedia race pages + Polymarket market names (2026-10-10).
NOMINEES = {
 "AL": ("Doug Jones", "Tommy Tuberville"), "AK": ("Jonathan Kreiss-Tomkins", "Bernadette Wilson"),
 "AZ": ("Katie Hobbs", "Andy Biggs"), "AR": ("Fredrick Love", "Sarah Huckabee Sanders"),
 "CA": ("Xavier Becerra", "Steve Hilton"), "CO": ("Phil Weiser", "Victor Marx"), "CT": ("Ned Lamont", "Ryan Fazio"),
 "FL": ("David Jolly", "Byron Donalds"), "GA": ("Keisha Lance Bottoms", "Rick Jackson"), "HI": ("Josh Green", "Gary Cordery"),
 "ID": ("Terri Pickens", "Brad Little"), "IL": ("JB Pritzker", "Darren Bailey"), "IA": ("Rob Sand", "Zach Lahn"),
 "KS": ("Cindy Holscher", "Ty Masterson"), "ME": ("Hannah Pingree", "Bobby Charles"), "MD": ("Wes Moore", "Dan Cox"),
 "MA": ("Maura Healey", "Mike Minogue"), "MI": ("Jocelyn Benson", "John James"), "MN": ("Amy Klobuchar", "Lisa Demuth"),
 "NE": ("Lynne Walz", "Jim Pillen"), "NV": ("Aaron Ford", "Joe Lombardo"), "NH": ("Cinde Warmington", "Kelly Ayotte"),
 "NM": ("Deb Haaland", "Gregg Hull"), "NY": ("Kathy Hochul", "Bruce Blakeman"), "OH": ("Amy Acton", "Vivek Ramaswamy"),
 "OK": ("Cyndi Munson", "Mike Mazzei"), "OR": ("Tina Kotek", "Christine Drazan"), "PA": ("Josh Shapiro", "Stacy Garrity"),
 "RI": ("Helena Foulkes", "Ken Block"), "SC": ("Jermaine Johnson", "Alan Wilson"), "SD": ("Dan Ahlers", "Larry Rhoden"),
 "TN": ("Jerri Green", "Marsha Blackburn"), "TX": ("Gina Hinojosa", "Greg Abbott"), "VT": ("Amanda Janoo", "Phil Scott"),
 "WI": ("David Crowley", "Tom Tiffany"), "WY": ("Kenneth Casner", "Eric Barlow")}
INC_STATUS = {"RI": "lost_primary"}
# Main non-Democratic challenger when it is not the Republican (margin = D minus that candidate).
# Rhode Island: independent Ken Block runs 2nd in every Sept poll (UNH Sep 17-21: Foulkes 44, Block 25, Guckian (R) 17).
CHALLENGER_PARTY = {"RI": "I"}

# Overrides that REPLACE a stale aggregate table (refresh 2026-10-10 06:00 ET).
OVERRIDE = {
 "WI": (3.0, 1, "2026-09-23", "", "Marquette Law School Poll Sep 16-23, 2026 (692 LV): Crowley 49, Tiffany 46 (RV: 46-45). Replaces the stale Wikipedia aggregate (RCP/Silver, polls through Aug 20, D+3.8). Excludes Z to A Research (D, Rust Belt Rising) Sep 28-Oct 1 D+5"),
 "RI": (19.0, 1, "2026-09-21", "", "UNH Granite State Poll Sep 17-21, 2026 (598 LV): Foulkes (D) 44, Block (I) 25, Guckian (R) 17; margin is Foulkes minus Block. Excludes Opinion Diagnostics Sep 23-25 (sponsored by Block's campaign: three-way Foulkes 41, Block 24, Guckian 19)"),
}   # McKee lost the Sep 8 primary to Foulkes -> open seat

# Races with no aggregate table but competitive ratings: mean of recent nonpartisan polls (D-minus-R margins).
MANUAL = {
 "AK": (6.0, 2, "2026-10-03", "", "Final RCV round of nonpartisan polls: Alaska Survey Research Oct 1-3 (Kreiss-Tomkins 54-46) and NYT/Siena Sep 24-Oct 1 (52-48); mean D+6.0"),
 "SC": (-10.0, 1, "2026-10-03", "", "Resonance Media Sep 29-Oct 3 (RV): Wilson 45-35. Excludes Hart (D, Johnson campaign) Aug R+8 and PPP (D) Jul"),
 "VT": (-2.3, 3, "2026-10-04", "", "Mean of State Navigate Oct 2-4 LV (Scott 46-43), Braun/Vermont Public Sep 10-21 LV (44-34), UNH Sep 17-21 LV (Janoo 49-43)"),
}

def rating_score(tmpl):
    p = [x.strip().lower() for x in tmpl.split("|")]
    if p[0].startswith("toss"):
        return 0.0
    v = SCORE.get(p[0])
    return None if v is None else (v if p[1] in ("d", "dfl") else -v)

def parse_overview():
    t = open(os.path.join(RAW, "2026_United_States_gubernatorial_elections.wiki")).read()
    s = t[t.find("== Predictions =="):t.find("== Race summary")]
    out = {}
    for b in re.split(r"\n!\s*\[\[2026 ", s)[1:]:
        name = re.match(r"(.+?) gubernatorial election", b).group(1)
        st = ABBR[name]
        pv = re.search(r"Shading PVI\|([A-Z]+)(?:\|(\d+))?", b, re.I)
        n = int(pv.group(2) or 0)
        pvi = n if pv.group(1).upper() == "D" else (-n if pv.group(1).upper() == "R" else 0)
        gov = re.search(r"sortname\|([^|}]+)\|([^|}]+)", b)
        incline = next(l for l in b.split("\n") if "sortname" in l)
        holder = "D" if ("Party shading/Democratic" in incline or "Party shading/DFL" in incline) else "R"
        low = b.lower()
        status = "term_limited" if "term-limited" in low else ("retiring" if "retiring" in low else "running")
        status = INC_STATUS.get(st, status)
        rs = re.findall(r"USRaceRating\|([^}]*)\}\}", b)
        sc = [rating_score(r) for r in rs]
        sc = [x for x in sc if x is not None]
        out[st] = dict(state=st, state_name=name, holder=holder, incumbent=f"{gov.group(1)} {gov.group(2)}",
                       inc_status=status, pvi_d=pvi, rating_score=round(sum(sc) / len(sc), 3),
                       ratings="; ".join(r.replace("|", " ") for r in rs))
    return out

MONTHS = "January February March April May June July August September October November December".split()
def last_date(txt):
    ds = re.findall(r"(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:,\s*(\d{4}))?", txt)
    best = None
    for m, d, y in ds:
        dt = datetime(int(y or 2026), MONTHS.index(m) + 1, int(d))
        best = dt if best is None or dt > best else best
    return best

def parse_aggregates(path, dem, rep):
    t = open(path).read()
    g = re.search(r"\n==\s*General election\s*==", t)
    if not g:
        return None
    t = t[g.end():]
    a = t.find("Aggregate polls")
    if a < 0 or a > 40000 and "Aggregate" not in t[:40000]:
        return None
    tb = t[a:]
    tb = tb[:tb.find("\n|}")]
    tb = re.sub(r"<ref[^>]*/>", "", tb)
    tb = re.sub(r"<ref.*?</ref>", "", tb, flags=re.S)
    tb = re.sub(r"<!--.*?-->", "", tb, flags=re.S)
    aggs = []
    for r in tb.split("\n|-")[1:]:
        cells = [c.strip() for c in re.split(r"\n\|", r)[1:]]
        if not cells or "Average" in cells[0]:
            continue
        src = re.sub(r"[\[\]']", "", cells[0]).split("|")[-1].strip()
        mtxt = re.sub(r"\{\{[^}]*\}\}\|?|'''", "", cells[-1]).strip().lstrip("|").strip()
        if mtxt.lower().startswith("tie"):
            margin = 0.0
        else:
            mm = re.search(r"([A-Za-z.\- ]+?)\s*\+\s*([\d.]+)", mtxt)
            if not mm:
                continue
            who, v = mm.group(1).strip(), float(mm.group(2))
            if who.split()[-1] in dem:
                margin = v
            elif who.split()[-1] in rep:
                margin = -v
            else:
                raise ValueError(f"{path}: cannot match leader {who!r}")
        # dates: the 'administered' cell (cells[1]); fall back to 'updated' (cells[2])
        d = last_date(cells[1]) or last_date(cells[2])
        aggs.append(dict(src=src, margin=margin, end=d))
    return aggs or None

def main():
    rows = parse_overview()
    for st, r in rows.items():
        dem, rep = NOMINEES[st]
        r["dem_candidate"], r["rep_candidate"] = dem, rep
        r["challenger_party"] = CHALLENGER_PARTY.get(st, "R")
        fn = os.path.join(RAW, "governor", "gov_" + r["state_name"].replace(" ", "_") + ".wiki")
        aggs = parse_aggregates(fn, dem, rep)
        r.update(poll_margin_d="", poll_sources=0, poll_end_date="", poll_sponsor_partisan="", poll_note="No poll used (race unanimously rated safe or no public polls); ratings prior only")
        if aggs:
            m = sum(a["margin"] for a in aggs) / len(aggs)
            end = max(a["end"] for a in aggs if a["end"])
            r.update(poll_margin_d=round(m, 2), poll_sources=len(aggs), poll_end_date=end.strftime("%Y-%m-%d"),
                     poll_note="Mean of Wikipedia-listed aggregators: " + ", ".join(f"{a['src']} {a['margin']:+.1f}" for a in aggs))
        if st in OVERRIDE:
            m, n, end, sp, note = OVERRIDE[st]
            r.update(poll_margin_d=m, poll_sources=n, poll_end_date=end, poll_sponsor_partisan=sp, poll_note=note)
        elif aggs:
            pass
        elif st in MANUAL:
            m, n, end, sp, note = MANUAL[st]
            r.update(poll_margin_d=m, poll_sources=n, poll_end_date=end, poll_sponsor_partisan=sp, poll_note=note)
    # market odds (comparison only)
    mk = json.load(open(os.path.join(MODEL, "data", "markets", "polymarket_2026-10-10.json")))["events"]
    for st, r in rows.items():
        slug = r["state_name"].lower().replace(" ", "-") + "-governor-winner-2026"
        ev = mk.get(slug) or mk.get(r["state_name"].lower().replace(" ", "-") + "-governor-election-winner")
        p = ""
        if ev:
            dem_last = r["dem_candidate"].split()[-1]
            for m in ev["markets"]:
                if dem_last in (m["q"] or ""):
                    p = round(m["yes"], 3)
        r["market_p_dem_polymarket"] = p
    cols = ["state", "state_name", "holder", "incumbent", "inc_status", "dem_candidate", "rep_candidate", "challenger_party", "pvi_d",
            "rating_score", "ratings", "poll_margin_d", "poll_sources", "poll_end_date", "poll_sponsor_partisan",
            "poll_note", "market_p_dem_polymarket"]
    with open(os.path.join(MODEL, "data", "governor_races.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for st in sorted(rows):
            w.writerow({c: rows[st][c] for c in cols})
    print("governor races:", len(rows), "with polls:", sum(1 for r in rows.values() if r["poll_sources"]))

if __name__ == "__main__":
    main()

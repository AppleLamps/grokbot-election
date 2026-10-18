"""Export model outputs (output/summary.json, output/seat_distributions.json + per-race CSV) to ../data/results.json for the static site.

Usage (from repo root or model/):  python model/scripts/export_site_data.py
Uses only the Python standard library.
"""
import csv, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.dirname(HERE)
ROOT = os.path.dirname(MODEL)
OUT = os.path.join(MODEL, "output")

KEYS = [("unbiased", "i", "Polls unbiased",
         "Polling error centered on zero (mean 0, sd 3 pts, fat-tailed), matching the 2018/2022 midterm record."),
        ("pres_style_D_overstatement", "ii", "Polls overstate Dems +3",
         "Like 2016/2020/2024: polls overstate Democrats by 3 pts on average (sd 3, fat-tailed). The presidential-year average was 3.8."),
        ("r_overstatement_2025", "iii", "Polls overstate Reps +6",
         "Like the 2025 off-year elections: polls overstate Republicans by 6 pts on average (sd 3). A tail case: the Trump-era off-year average was only 1.3.")]

# v2 factors shown on the site (coefficients mirror model/config.yaml; all are our assumptions)
FACTORS = [
    ("herding", "Herding-aware poll weighting",
     "When a Senate poll average sits far from fundamentals, its weight shrinks: x max(0.5, 1 - 0.04 x (gap - 1 pt)), and race uncertainty widens 0.1 pt per gap point. Party-neutral."),
    ("demographic_regional", "Demographic + regional error",
     "A shared Hispanic-voter polling miss (sd 6 pts, scaled by each state's 2020 Census Hispanic share) plus a Census-region error (sd 1.5) on top of national, state and race error."),
    ("expert_ratings", "Expert ratings in the House",
     "Cook/Sabato/Inside-style ratings converted to margins (Toss-up 0, Tilt 2, Lean 4.5, Likely 9, Safe 16) and blended at 30% weight in rated seats, 15% in unrated (safe) seats."),
    ("candidate_quality", "Candidate quality",
     "Fundamentals-only adjustments: Paxton (TX) +2.0 toward D; Brown (OH) +1.5 D; Cooper (NC) +1.5 D; Sununu (NH) 1.5 toward R. On top of the existing Collins, Osborn and Peltola terms."),
    ("poll_cleanup", "Poll cleanup",
     "Generic ballot nudged by a likely-voter assumption (the polling average and the +adjustment are read from config.yaml; see the generic-ballot note); Democratic-sponsored polls (LA, MS) shifted 4 pts toward R at half weight; stale polls lose half their weight every 45 days after 2 weeks (VA's June poll now barely counts)."),
    ("incumbency_reweight", "Incumbency reweight",
     "House incumbency edge cut from 3.0 to 1.8 pts; appointed senators (Husted, Moody, Graham) treated as open seats (was 1.5)."),
    ("fat_tails", "Fat tails",
     "National and race errors drawn from Student-t distributions (df 6 and 8) with the same sd, so blowouts are more likely than under a normal curve."),
    ("election_mechanics", "Election mechanics",
     "Ranked-choice transfer uncertainty in Alaska (+2.0 sd) and Maine (+1.5 sd); Montana three-way split (runner-up gets 75% of the anti-R vote); Louisiana Dec 12 House runoffs noted; independents caucus D 60% of the time."),
]

STATES = {"AL":"Alabama","AK":"Alaska","AR":"Arkansas","CO":"Colorado","DE":"Delaware","FL":"Florida","GA":"Georgia",
 "ID":"Idaho","IL":"Illinois","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MA":"Massachusetts",
 "MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MT":"Montana","NE":"Nebraska","NH":"New Hampshire","NJ":"New Jersey",
 "NM":"New Mexico","NC":"North Carolina","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","RI":"Rhode Island","SC":"South Carolina",
 "SD":"South Dakota","TN":"Tennessee","TX":"Texas","VA":"Virginia","WV":"West Virginia","WY":"Wyoming"}

def generic_ballot_info():
    """Generic-ballot figures read from the model's actual inputs, not hard-coded.
    raw  = generic_ballot_margin in config.yaml (Wikipedia aggregate average)
    adj  = generic_ballot_lv_adjustment, applied only when factors.poll_cleanup is on (a model assumption)
    as_of / wiki_avg = date and margin on the 'Average' row of the Wikipedia generic-ballot table (data/raw)."""
    cfg = open(os.path.join(MODEL, "config.yaml")).read()
    raw = float(re.search(r"^generic_ballot_margin:\s*([-0-9.]+)", cfg, re.M).group(1))
    m_adj = re.search(r"^generic_ballot_lv_adjustment:\s*([-0-9.]+)", cfg, re.M)
    m_on = re.search(r"^\s*poll_cleanup:\s*(true|false)", cfg, re.M)
    adj = float(m_adj.group(1)) if (m_adj and m_on and m_on.group(1) == "true") else 0.0
    as_of, wiki_avg = None, None
    wiki = os.path.join(MODEL, "data", "raw", "2026_United_States_House_of_Representatives_elections.wiki")
    if os.path.exists(wiki):
        t = open(wiki, encoding="utf-8").read()
        m = re.search(r"'''Average'''\s*\n\|([A-Z][a-z]+ \d{1,2}, \d{4})(.*?)Democrats \+([0-9.]+)%", t, re.S)
        if m:
            import datetime
            as_of = datetime.datetime.strptime(m.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
            wiki_avg = float(m.group(3))
    if wiki_avg is not None and abs(wiki_avg - raw) > 0.05:
        print("WARNING: config generic_ballot_margin %.1f != Wikipedia average D+%.1f" % (raw, wiki_avg))
    return raw, adj, round(raw + adj, 2), as_of, wiki_avg


def num(x):
    try:
        return None if x in ("", None) else round(float(x), 5)
    except ValueError:
        return None

def histogram(d):
    """Trim a full 0..max_seats count vector (from seat_distributions.json) to the simulated support and
    convert to parallel arrays: seats[i] occurred with probability prob[i] (= count / sims)."""
    counts, n = d["counts"], d["sims"]
    nz = [i for i, c in enumerate(counts) if c > 0]
    lo, hi = nz[0], nz[-1]
    return {"sims": n, "max_seats": d["max_seats"], "majority": d["majority"], "majority_line": d["majority_line"],
            "mean": round(d["mean"], 3), "median": d["median"], "p10": d["p10"], "p90": d["p90"],
            "seats": list(range(lo, hi + 1)), "count": counts[lo:hi + 1],
            "prob": [round(c / n, 6) for c in counts[lo:hi + 1]]}


def main():
    summ = json.load(open(os.path.join(OUT, "summary.json")))
    dist = json.load(open(os.path.join(OUT, "seat_distributions.json")))
    scenarios = []
    for key, short, label, desc in KEYS:
        s = summ[key]
        scenarios.append({
            "key": key, "short": short, "label": label, "model_label": s["label"], "description": desc,
            "bias_mean": s["bias_mean"], "bias_sd": s["bias_sd"], "sims": s["sims"],
            "senate": {"p_D": s["senate_p_D"], "p_R": s["senate_p_R"], "p_none": s["senate_p_none"],
                       "D_mean": s["senate_D_mean"], "D_p10": s["senate_D_p10"], "D_p90": s["senate_D_p90"],
                       "R_mean": s["senate_R_mean"], "R_p10": s["senate_R_p10"], "R_p90": s["senate_R_p90"],
                       "tipping": s["senate_tipping"], "majority": 51, "majority_line": 50.5,
                       "D_median": dist[key]["senate"]["median"], "hist": histogram(dist[key]["senate"])},
            "governors": ({"D_total_median": s["gov_D_total_median"], "D_total_p10": s["gov_D_total_p10"],
                           "D_total_p90": s["gov_D_total_p90"], "D_total_mean": round(s["gov_D_total_mean"], 3),
                           "D_wins_mean": round(s["gov_D_wins_mean"], 3), "races": s["gov_races"],
                           "p_D_majority": s["gov_p_D_majority"]} if "gov_races" in s else None),
            "house": {"p_D": s["house_p_D"], "p_R": s["house_p_R"], "D_mean": s["house_D_mean"],
                      "D_median": s["house_D_median"], "D_p10": s["house_D_p10"], "D_p90": s["house_D_p90"],
                      "tipping": s["house_tipping"], "majority": 218, "majority_line": 217.5,
                      "hist": histogram(dist[key]["house"])},
        })

    v1p = os.path.join(OUT, "summary_v1.json")
    comparison = []
    if os.path.exists(v1p):
        v1 = json.load(open(v1p))
        for key, short, label, desc in KEYS:
            a, b = v1[key], summ[key]
            comparison.append({"key": key, "label": label,
                               "v1": {"senate_p_D": a["senate_p_D"], "senate_p_R": a["senate_p_R"], "senate_D_mean": a["senate_D_mean"],
                                      "house_p_D": a["house_p_D"], "house_D_median": a["house_D_median"]},
                               "v2": {"senate_p_D": b["senate_p_D"], "senate_p_R": b["senate_p_R"], "senate_D_mean": b["senate_D_mean"],
                                      "house_p_D": b["house_p_D"], "house_D_median": b["house_D_median"]}})
    attribution = {}
    ap = os.path.join(OUT, "factor_attribution.json")
    if os.path.exists(ap):
        aj = json.load(open(ap))
        for key in aj:
            full = aj[key]["v2_all_on"]
            attribution[key] = {f: {"senate_p_D": round(full["senate_p_D"] - d["senate_p_D"], 4),
                                    "senate_D_mean": round(full["senate_D_mean"] - d["senate_D_mean"], 3),
                                    "house_p_D": round(full["house_p_D"] - d["house_p_D"], 4),
                                    "house_D_mean": round(full["house_D_mean"] - d["house_D_mean"], 2)}
                                for f, d in aj[key]["drop_one"].items()}
            base = aj[key]["v1_all_off"]
            attribution[key + "__alone"] = {f: {"senate_p_D": round(d["senate_p_D"] - base["senate_p_D"], 4),
                                               "senate_D_mean": round(d["senate_D_mean"] - base["senate_D_mean"], 3),
                                               "house_p_D": round(d["house_p_D"] - base["house_p_D"], 4),
                                               "house_D_mean": round(d["house_D_mean"] - base["house_D_mean"], 2)}
                                           for f, d in aj[key]["add_one"].items()}
    factors = [{"key": k, "title": t, "detail": d,
                "effect": {sc: attribution[sc][k] for sc in attribution if "__" not in sc and k in attribution[sc]},
                "effect_alone": {sc.split("__")[0]: attribution[sc][k] for sc in attribution if sc.endswith("__alone") and k in attribution[sc]}}
               for k, t, d in FACTORS]

    races = {}
    with open(os.path.join(OUT, "senate_race_probabilities_all_scenarios.csv")) as f:
        for r in csv.DictReader(f):
            k = (r["state"], r["seat"])
            if k not in races:
                races[k] = {"state": r["state"], "state_name": STATES.get(r["state"], r["state"]),
                            "seat": r["seat"], "holder": r["holder"],
                            "dem_side_candidate": r["dem_side_candidate"], "dem_side_party": r["dem_side_party"],
                            "rep_candidate": r["rep_candidate"], "pvi_d": num(r["pvi_d"]),
                            "poll_margin_d": num(r["poll_margin_d"]), "poll_sources": int(float(r["poll_sources"] or 0)),
                            "poll_adjust": num(r.get("state_poll_adjust", 0) or 0),
                            "est_margin": num(r["est_margin"]), "tipping_freq": num(r["tipping_freq"]),
                            "poll_weight": num(r.get("poll_weight")), "fundamentals_margin": num(r.get("fundamentals_margin")),
                            "candidate_quality_adj": num(r.get("candidate_quality_adj")), "mechanics_note": r.get("mechanics_note") or "",
                            "p_dem": {}}
            races[k]["p_dem"][r["scenario"]] = num(r["p_dem_side"])
    race_list = sorted(races.values(), key=lambda x: -x["p_dem"]["unbiased"])

    # ---- prediction markets (comparison only; not a model input)
    MK = os.path.join(MODEL, "data", "markets")
    pm = json.load(open(os.path.join(MK, "polymarket_2026-10-10.json")))
    ks = json.load(open(os.path.join(MK, "kalshi_2026-10-10.json")))
    pev = pm["events"]
    def pm_party(slug, party):
        e = pev.get(slug)
        if not e: return None
        for m in e["markets"]:
            if (m["q"] or "").startswith(party): return round(m["yes"], 4)
    def k_mid(ev, side):
        for m in ks["events"].get(ev, []):
            if m["t"].endswith("-" + side): return round((float(m["bid"]) + float(m["ask"])) / 2, 4)
    markets = {"as_of": pm["fetched"][:16].replace("T", " ") + " ET", "note": "Prediction-market prices for comparison only; not a model input.",
               "senate_p_D": {"polymarket": pm_party("which-party-will-win-the-senate-in-2026", "Democratic"), "kalshi": k_mid("CONTROLS-2026", "D")},
               "house_p_D": {"polymarket": pm_party("which-party-will-win-the-house-in-2026", "Democratic"), "kalshi": k_mid("CONTROLH-2026", "D")}}
    for r in race_list:
        slug = None
        for k in pev:
            if k.startswith(r["state_name"].lower().replace(" ", "-") + "-senate-election-winner"): slug = k
        p = None
        if slug:
            import unicodedata
            fold = lambda t: unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
            dl = fold(r["dem_side_candidate"].split("/")[0].split()[-1])
            for m in pev[slug]["markets"]:
                q = fold(m["q"] or "").strip()
                if dl in q or (r["dem_side_party"] == "I" and q == "Independent") or (r["dem_side_party"] == "D" and q == "Democrat"):
                    p = round(m["yes"], 4)
        r["market_p_dem"] = p

    # ---- governors
    gov_list = []
    gp = os.path.join(OUT, "governor_race_probabilities_all_scenarios.csv")
    if os.path.exists(gp):
        g = {}
        with open(gp) as f:
            for r in csv.DictReader(f):
                k = r["state"]
                if k not in g:
                    g[k] = {"state": k, "state_name": r["state_name"], "holder": r["holder"], "incumbent": r["incumbent"],
                            "inc_status": r["inc_status"], "dem_candidate": r["dem_candidate"], "rep_candidate": r["rep_candidate"],
                            "challenger_party": r.get("challenger_party") or "R",
                            "pvi_d": num(r["pvi_d"]), "rating_score": num(r["rating_score"]), "prior_margin": num(r["prior_margin"]),
                            "poll_margin_d": num(r["poll_margin_d"]), "poll_sources": int(float(r["poll_sources"] or 0)),
                            "poll_end_date": r["poll_end_date"], "poll_note": r["poll_note"], "est_margin": num(r["est_margin"]),
                            "market_p_dem": num(r["market_p_dem_polymarket"]), "p_dem": {}}
                g[k]["p_dem"][r["scenario"]] = num(r["p_dem"])
        gov_list = sorted(g.values(), key=lambda x: -x["p_dem"]["unbiased"])

    gb_raw, gb_adj, gb_model, gb_asof, gb_wiki = generic_ballot_info()
    gb_note = ("D+%.1f Wikipedia generic-ballot polling average (DDHQ, FiftyPlusOne, NBC, RCP, Silver Bulletin), as of %s" % (gb_raw, gb_asof or "n/a")
               + ("; the model adds a +%.1f likely-voter adjustment (an assumption in config.yaml, not refreshed daily) for D+%.1f" % (gb_adj, gb_model) if gb_adj else ""))
    out = {
        "title": "Apple Lamps Grok Bot Election Analysis and Prediction",
        "as_of": "2026-10-10",
        "model_version": "v2 (eight additional factors)",
        "generic_ballot_d": gb_model, "generic_ballot_raw_d": gb_raw, "generic_ballot_lv_adj": gb_adj,
        "generic_ballot_as_of": gb_asof,
        "generic_ballot_note": gb_note,
        "baseline": {"senate": {"R": 53, "D": 45, "I": 2, "up": len(race_list)}, "house": {"R": 218, "D": 214}},
        "scenarios": scenarios,
        "senate_races": race_list,
        "governor_races": gov_list,
        "governor_baseline": {"D": 24, "R": 26, "up": len(gov_list), "up_D": 18, "up_R": 18},
        "markets": markets,
        "factors": factors,
        "comparison": comparison,
    }
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    path = os.path.join(ROOT, "data", "results.json")
    with open(path, "w") as f:
        txt = json.dumps(out, indent=1)
        # keep long numeric arrays (histograms) on one line
        txt = re.sub(r"\[\s*((?:-?[\d.e-]+,\s*)+-?[\d.e-]+)\s*\]",
                     lambda m: "[" + ",".join(x.strip() for x in m.group(1).split(",")) + "]", txt)
        f.write(txt + "\n")
    print(f"wrote {path}: {len(scenarios)} scenarios, {len(race_list)} Senate races, {len(gov_list)} governor races")

if __name__ == "__main__":
    main()
